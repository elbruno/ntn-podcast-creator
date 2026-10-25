"""Select a pending OneDrive episode and render it through Docker."""

import argparse
import http.client
import json
import os
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features.episode_client import EpisodeClient
from features.episode_discovery import discover_episodes, inspect_episode
from features.episode_naming import reserve_local_output


def open_episode_audio(path: Path, log: Callable[[str], None]) -> None:
    try:
        path = path.resolve(strict=True)
        if sys.platform == "win32":
            os.startfile(str(path))
        else:
            command = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.run([command, str(path)], check=True, timeout=30)
        log(f"Abierto en el reproductor predeterminado: {path}")
    except (OSError, subprocess.SubprocessError) as error:
        log(f"Advertencia: El episodio esta guardado en {path}, pero no se pudo abrir "
            f"el reproductor: {error}. Abralo manualmente o use --no-play.")


def main(argv=None, *, input_fn: Callable[[str], str] = input,
         log: Callable[[str], None] = print) -> int:
    with ExitStack() as reservations:
        return _main(argv, input_fn=input_fn, log=log, reservations=reservations)


def _main(argv, *, input_fn, log, reservations) -> int:
    parser = argparse.ArgumentParser(description="Crear un episodio pendiente desde OneDrive.")
    parser.add_argument("--root", type=Path, default=Path(r"C:\od\OneDrive\Podcast"))
    parser.add_argument("--server-url", default="http://localhost:7860")
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--include-generated", action="store_true",
                        help="Permitir regenerar episodios con finales existentes.")
    parser.add_argument("--no-auto-start", action="store_true")
    parser.add_argument("--no-play", action="store_true",
                        help="No abrir el MP3 al finalizar.")
    args = parser.parse_args(argv)
    try:
        episodes, warnings = discover_episodes(args.root.resolve())
        for warning in warnings:
            log(f"Advertencia: {warning}")
        for episode in episodes:
            for problem in episode.problems:
                log(f"Advertencia [{episode.path.name}]: {problem}")
            if not episode.finals and not episode.recordings:
                log(f"Sin grabaciones: {episode.path.name}")
        pending = [episode for episode in episodes
                   if episode.selectable and (args.include_generated or episode.pending)]
        for index, episode in enumerate(pending, 1):
            state = " [regeneracion]" if episode.finals else ""
            log(f"{index}. {episode.path.name} ({len(episode.recordings)} grabaciones){state}")
        if not pending:
            log("No hay episodios pendientes seleccionables.")
            return 0
        if args.list_only:
            return 0
        while True:
            choice = input_fn("Seleccione un episodio (Enter para cancelar): ").strip()
            if not choice:
                log("Cancelado; no se enviaron grabaciones.")
                return 0
            if choice.isdecimal() and 1 <= int(choice) <= len(pending):
                selected = pending[int(choice) - 1]
                break
            log("Seleccion invalida.")
        selected = inspect_episode(selected.path)
        if not selected.selectable or (selected.finals and not args.include_generated):
            raise RuntimeError("La carpeta cambio y ya no es seleccionable.")
        identities = [(path.stat().st_size, path.stat().st_mtime_ns)
                      for path in selected.recordings]
        log("Grabaciones candidatas (revise musica, duplicados y audios derivados):")
        for index, path in enumerate(selected.recordings, 1):
            log(f"  {index}. {path.name}")
        while True:
            choice = input_fn(
                "Grabaciones en orden (Enter: todas; ej. 3,1; q: cancelar): ").strip()
            if choice.casefold() == "q":
                log("Cancelado; no se enviaron grabaciones.")
                return 0
            if not choice:
                recordings = selected.recordings
                break
            parts = [part.strip() for part in choice.split(",")]
            if all(part.isdecimal() for part in parts):
                indices = [int(part) for part in parts]
                if (len(set(indices)) == len(indices)
                        and all(1 <= index <= len(selected.recordings) for index in indices)):
                    recordings = tuple(selected.recordings[index - 1] for index in indices)
                    break
            log("Seleccion invalida: use indices unicos separados por comas.")
        client = EpisodeClient(args.server_url)
        client.ensure_server(ROOT, not args.no_auto_start, log)
        settings = client.settings()
        output = reservations.enter_context(
            reserve_local_output(selected.path, Path(selected.output_name).stem))
        log("Grabaciones en orden:\n" +
            "\n".join(f"  {index}. {path.name}" for index, path in enumerate(recordings, 1)))
        log(f"Destino: {output}")
        log("Configuracion guardada del servidor:\n" +
            json.dumps(settings, ensure_ascii=False, indent=2))
        while True:
            confirmation = input_fn(
                "Crear episodio? YES/NO (y/n) [YES]: ").strip().casefold()
            if confirmation in ("", "y", "yes"):
                break
            if confirmation in ("n", "no"):
                log("Cancelado; no se enviaron grabaciones.")
                return 0
            log("Respuesta invalida. Use YES/NO o y/n; Enter confirma YES.")
        current = inspect_episode(selected.path)
        current_identities = [(path.stat().st_size, path.stat().st_mtime_ns)
                              for path in current.recordings]
        if current != selected or current_identities != identities:
            raise RuntimeError("La carpeta cambio despues de la seleccion. Revise y ejecute otra vez.")
        if any(not path.stat().st_size for path in recordings):
            raise ValueError("Hay una grabacion vacia.")
        uploads = []
        for path in recordings:
            log(f"Subiendo {path.name}...")
            uploads.append(client.upload(path))
        result = client.render(uploads, output.stem, settings, log)
        log(f"Resultado del servidor: {result['output_path']}")
        downloaded_mp3 = None
        try:
            for kind in ("mp3", "transcript", "quality_report", "denoised"):
                artifact = result.get(kind)
                if artifact:
                    downloaded = client.download(artifact, selected.path)
                    if kind == "mp3":
                        downloaded_mp3 = downloaded
                    log(f"Descargado: {downloaded}")
        except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
            raise RuntimeError(
                f"{error}. El resultado sigue en {result['output_path']}. "
                f"Recuperelo desde {client.server}/gradio_api/file="
                f"{result['mp3']['path']}; no regenere el episodio."
            ) from error
        for warning in result.get("warnings", []):
            log(f"Advertencia: {warning}")
        log(f"Episodio {result['episode_name']} guardado. QC: {result['qc_status']}")
        if downloaded_mp3 is not None and not args.no_play:
            open_episode_audio(downloaded_mp3, log)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
            http.client.HTTPException) as error:
        log(f"Error: {error}")
        return 1
    except (KeyboardInterrupt, EOFError):
        log("Cancelado. Si ya se envio un trabajo, revise outputs antes de volver a enviarlo.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
