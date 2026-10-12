"""Standard-library client for the local Gradio folder-episode API."""

import http.client
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional


class EpisodeClient:
    def __init__(self, server_url: str = "http://localhost:7860"):
        parsed = urllib.parse.urlsplit(server_url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("Servidor invalido: use una URL HTTP(S) sin credenciales.")
        self.server = server_url.rstrip("/")
        self.parsed = urllib.parse.urlsplit(self.server)
        self.job_id: Optional[str] = None

    def _json(self, path: str, data=None):
        body = None if data is None else json.dumps(data).encode("utf-8")
        request = urllib.request.Request(self.server + path, data=body,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def ensure_server(self, repository: Path, auto_start: bool,
                      log: Callable[[str], None]) -> None:
        try:
            config = self._json("/config")
        except urllib.error.URLError as error:
            reason = error.reason
            refused = isinstance(reason, ConnectionRefusedError) or (
                isinstance(reason, OSError) and reason.errno in (61, 111, 10061))
            local = (self.parsed.scheme == "http"
                     and self.parsed.hostname in ("localhost", "127.0.0.1")
                     and self.parsed.port == 7860 and self.parsed.path in ("", "/"))
            if not refused or not local or not auto_start:
                raise RuntimeError(f"No se puede conectar al servidor: {error}") from error
            if shutil.which("docker") is None:
                raise RuntimeError("Se requiere Docker Desktop para iniciar el servidor.") from error
            log("Iniciando Docker sin recrear el contenedor existente...")
            subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL,
                           timeout=30)
            containers = subprocess.run(
                ["docker", "container", "ls", "--all", "--format", "{{.Names}}"],
                check=True, capture_output=True, text=True, timeout=30)
            if "ntn-podcast-creator" in containers.stdout.splitlines():
                command = ["docker", "start", "ntn-podcast-creator"]
            else:
                command = ["docker", "compose", "--ansi", "never", "-f",
                           str(repository / "deployment" / "docker-compose.yml"),
                           "up", "-d", "--no-recreate", "--yes"]
            subprocess.run(command, check=True, timeout=600)
            deadline = time.monotonic() + 180
            while True:
                try:
                    config = self._json("/config")
                    break
                except urllib.error.URLError as startup_error:
                    if isinstance(startup_error, urllib.error.HTTPError):
                        raise
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Docker no expuso la API. Revise sus logs.") from startup_error
                    time.sleep(2)
        if not isinstance(config, dict) or not isinstance(config.get("dependencies"), list):
            raise ValueError("El servidor no devolvio una configuracion Gradio valida.")
        names = {item.get("api_name") for item in config["dependencies"] if isinstance(item, dict)}
        if not {"create_folder_episode", "folder_episode_settings"} <= names:
            raise RuntimeError(
                "El servidor necesita actualizarse: reconstruya la imagen con los endpoints "
                "create_folder_episode y folder_episode_settings; no se subieron grabaciones. "
                "Cuando no haya episodios en proceso, ejecute desde el repositorio: "
                r"docker compose -f .\deployment\docker-compose.yml up -d --build"
                ". Despues vuelva a ejecutar el script.")

    def _events(self, endpoint: str, data, log: Callable[[str], None]):
        self.job_id = None
        try:
            job = self._json("/gradio_api/call/" + endpoint, {"data": data})
            job_id = job.get("event_id")
            if not isinstance(job_id, str) or not job_id or not all(
                    char.isalnum() or char in "_-" for char in job_id):
                raise ValueError("Identificador de trabajo invalido.")
            self.job_id = job_id
            event = ""
            lines: List[str] = []
            shown = 0
            url = f"{self.server}/gradio_api/call/{endpoint}/{job_id}"
            with urllib.request.urlopen(url, timeout=600) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").rstrip("\r\n")
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        lines.append(line[5:].lstrip())
                    elif not line:
                        if event == "error":
                            raise RuntimeError("Error del servidor: " + "\n".join(lines))
                        if event in ("generating", "complete"):
                            values = json.loads("\n".join(lines))
                            if not isinstance(values, list) or len(values) != 1:
                                raise ValueError("Respuesta de API invalida.")
                            value = values[0]
                            if isinstance(value, dict):
                                messages = value.get("logs", [])
                                for message in messages[shown:]:
                                    log(message)
                                shown = len(messages)
                            if event == "complete":
                                return value
                        event, lines = "", []
            raise RuntimeError("Conexion cerrada sin resultado terminal.")
        except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
            if endpoint == "create_folder_episode":
                raise RuntimeError(
                    f"{error}. El servidor puede seguir procesando; no reenvie automaticamente. "
                    f"Trabajo: {self.job_id or 'desconocido'}. Revise outputs y los logs de Docker."
                ) from error
            raise

    def settings(self) -> Dict:
        result = self._events("folder_episode_settings", [], lambda message: None)
        if not isinstance(result, dict) or "generate_transcript" not in result:
            raise ValueError("Resumen de configuracion invalido.")
        return result

    def upload(self, source: Path) -> dict:
        before = source.stat()
        if not before.st_size:
            raise ValueError(f"Grabacion vacia: {source.name}")
        if any(char in source.name for char in '"\r\n'):
            raise ValueError(f"Nombre no valido para subida: {source.name}")
        boundary = uuid.uuid4().hex
        header = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
            f"filename=\"{source.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        trailer = f"\r\n--{boundary}--\r\n".encode("ascii")
        connection_type = (http.client.HTTPSConnection if self.parsed.scheme == "https"
                           else http.client.HTTPConnection)
        connection = connection_type(self.parsed.hostname, self.parsed.port, timeout=300)
        try:
            connection.putrequest("POST", self.parsed.path + "/gradio_api/upload")
            connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
            connection.putheader("Content-Length", str(len(header) + before.st_size + len(trailer)))
            connection.endheaders()
            connection.send(header)
            with source.open("rb") as audio:
                remaining = before.st_size
                while remaining:
                    chunk = audio.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError(f"La grabacion cambio durante la subida: {source}")
                    connection.send(chunk)
                    remaining -= len(chunk)
            connection.send(trailer)
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError(f"Subida rechazada: HTTP {response.status} {response.reason}")
            paths = json.load(response)
        finally:
            connection.close()
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError(f"La grabacion cambio durante la subida: {source}")
        if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
            raise ValueError("Respuesta de subida invalida.")
        return {"path": paths[0], "orig_name": source.name, "meta": {"_type": "gradio.FileData"}}

    def render(self, recordings: List[dict], name: str, settings: Dict,
               log: Callable[[str], None]) -> Dict:
        result = self._events("create_folder_episode", [recordings, name, settings], log)
        if not isinstance(result, dict) or result.get("schema") != "ntn-episode-v1":
            raise ValueError("Resultado del episodio invalido.")
        if result.get("state") != "complete" or result.get("success") is not True:
            raise RuntimeError(f"No se creo el episodio: {result.get('error')}")
        if (not isinstance(result.get("mp3"), dict) or result.get("episode_name") != name
                or result["mp3"].get("orig_name") != f"{name}.mp3"):
            raise RuntimeError("El servidor no devolvio el MP3 con el nombre solicitado.")
        return result

    def download(self, artifact: dict, destination: Path) -> Path:
        name = artifact.get("orig_name")
        if (not isinstance(name, str) or not name or name in (".", "..")
                or any(char in name for char in '\\/:\x00') or name.endswith((".", " "))
                or Path(name).is_absolute()):
            raise ValueError("Nombre de descarga inseguro.")
        target = destination / name
        if target.exists():
            raise FileExistsError(f"No se sobrescribira: {target}")
        url = self.server + "/gradio_api/file=" + urllib.parse.quote(artifact["path"], safe="")
        if artifact.get("url"):
            url = urllib.parse.urljoin(self.server + "/", artifact["url"])
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme, parsed.netloc) != (self.parsed.scheme, self.parsed.netloc):
            raise ValueError("La descarga apunta fuera del servidor seleccionado.")
        descriptor, temporary = tempfile.mkstemp(prefix=".ntn-", suffix=".part", dir=destination)
        try:
            with os.fdopen(descriptor, "wb") as output, urllib.request.urlopen(url, timeout=300) as response:
                final_url = urllib.parse.urlsplit(response.geturl())
                if (final_url.scheme, final_url.netloc) != (self.parsed.scheme, self.parsed.netloc):
                    raise ValueError("La descarga redirigio fuera del servidor.")
                shutil.copyfileobj(response, output, length=1024 * 1024)
                size = output.tell()
                length = response.headers.get("Content-Length")
                if not size or (length is not None and size != int(length)):
                    raise RuntimeError("Descarga vacia o incompleta.")
            if os.name == "nt":
                os.rename(temporary, target)
            else:
                os.link(temporary, target)
            return target
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
