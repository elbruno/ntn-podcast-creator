"""Standard-library client, interactive selection, and download safety."""

import importlib.util
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock

import pytest

from features.episode_client import EpisodeClient

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ntn-create-pending.py"
spec = importlib.util.spec_from_file_location("pending_cli", SCRIPT)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


@pytest.fixture
def http_server():
    state = {"uploads": [], "data": None, "payload": b"valid mp3", "disconnect": False,
             "endpoint_missing": False, "download_partial": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_body(self, value, content_type="application/json"):
            body = json.dumps(value).encode() if content_type == "application/json" else value
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.path.endswith("/upload"):
                state["uploads"].append(body)
                self.send_body([f"/uploads/{len(state['uploads'])}.wav"])
            else:
                state["data"] = json.loads(body)["data"]
                self.send_body({"event_id": "job-1"})

        def do_GET(self):
            if self.path == "/config":
                names = [] if state["endpoint_missing"] else [
                    "create_folder_episode", "folder_episode_settings"]
                self.send_body({"dependencies": [{"api_name": name} for name in names]})
            elif "/file=" in self.path:
                self.send_response(200)
                self.send_header("Content-Length", str(len(state["payload"]) +
                                                      (10 if state["download_partial"] else 0)))
                self.end_headers()
                self.wfile.write(state["payload"])
            else:
                settings = "/folder_episode_settings/" in self.path
                result = {"generate_transcript": True} if settings else {
                    "schema": "ntn-episode-v1", "state": "complete", "success": True,
                    "episode_name": "ntn580", "mp3": {"path": "/out/ntn580.mp3",
                                                     "orig_name": "ntn580.mp3"}}
                event = "event: generating\r\ndata: " + json.dumps(
                    [{"logs": ["mezclando"]}]) + "\r\n\r\n"
                if not state["disconnect"]:
                    # Multi-line data and UTF-8 exercise the SSE parser.
                    event += "event: complete\r\ndata: [\r\ndata: " + json.dumps(result) + "\r\ndata: ]\r\n\r\n"
                self.send_body(event.encode(), "text/event-stream")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield EpisodeClient(f"http://127.0.0.1:{server.server_port}"), state
    server.shutdown()
    server.server_close()
    thread.join()


def test_direct_client_upload_sse_and_download(http_server, tmp_path):
    client, state = http_server
    client.ensure_server(tmp_path, False, print)
    settings = client.settings()
    assert settings["generate_transcript"]
    files = []
    for index in (1, 2):
        source = tmp_path / f"Recording ({index}).wav"
        source.write_bytes(bytes([index]) * 1024)
        files.append(client.upload(source))
        assert source.read_bytes() == bytes([index]) * 1024
    messages = []
    result = client.render(files, "ntn580", settings, messages.append)
    assert state["data"] == [files, "ntn580", settings]
    assert len(state["uploads"]) == 2 and b'name="files"' in state["uploads"][0]
    assert messages == ["mezclando"]
    output = client.download(result["mp3"], tmp_path)
    assert output.read_bytes() == state["payload"]
    with pytest.raises(FileExistsError):
        client.download(result["mp3"], tmp_path)
    assert not list(tmp_path.glob("*.part"))


def test_disconnect_is_not_retried(http_server):
    client, state = http_server
    state["disconnect"] = True
    with pytest.raises(RuntimeError, match="no reenvie"):
        client.render([], "ntn580", {}, print)
    assert client.job_id == "job-1"


def test_missing_endpoint_requires_explicit_update(http_server, tmp_path):
    client, state = http_server
    state["endpoint_missing"] = True
    with pytest.raises(RuntimeError, match="actualizarse") as error:
        client.ensure_server(tmp_path, True, print)
    assert r"docker compose -f .\deployment\docker-compose.yml up -d --build" in str(error.value)
    assert not state["uploads"]


def test_partial_download_never_published(http_server, tmp_path):
    client, state = http_server
    state["download_partial"] = True
    with pytest.raises((RuntimeError, OSError)):
        client.download({"path": "/out/ntn580.mp3", "orig_name": "ntn580.mp3"}, tmp_path)
    assert not (tmp_path / "ntn580.mp3").exists()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", ["../evil.mp3", r"..\evil.mp3", "a:b.mp3", ".", "file."])
def test_unsafe_download_names(http_server, tmp_path, name):
    client, _ = http_server
    with pytest.raises(ValueError, match="inseguro"):
        client.download({"path": "/out/a", "orig_name": name}, tmp_path)


def test_external_download_rejected(http_server, tmp_path):
    client, _ = http_server
    with pytest.raises(ValueError, match="fuera"):
        client.download({"path": "/out/a", "orig_name": "a.mp3",
                         "url": "https://example.com/a"}, tmp_path)


@pytest.mark.parametrize("name", ["26 10 11 NTN 580 Test",
                                 "NTN 999 De Compaq a la PS5 clonar con IA"])
def test_list_only_requires_no_audio_dependencies(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    (path / "Recording.m4a").write_bytes(b"original")
    result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--root", str(tmp_path),
                             "--list-only"], capture_output=True, text=True, timeout=10,
                            cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert name in result.stdout
    assert "(1 grabaciones)" in result.stdout


def test_cancel_and_no_pending_do_not_start_server(tmp_path, monkeypatch):
    client = Mock()
    monkeypatch.setattr(cli, "EpisodeClient", client)
    assert cli.main(["--root", str(tmp_path)], log=lambda _: None) == 0
    path = tmp_path / "26 10 11 NTN 580"
    path.mkdir()
    (path / "Recording.m4a").write_bytes(b"original")
    assert cli.main(["--root", str(tmp_path)], input_fn=lambda _: "",
                    log=lambda _: None) == 0
    client.assert_not_called()


def test_change_after_confirmation_blocks_upload(tmp_path, monkeypatch):
    path = tmp_path / "26 10 11 NTN 580"
    path.mkdir()
    source = path / "Recording.m4a"
    source.write_bytes(b"original")
    client = Mock()
    client.settings.return_value = {"generate_transcript": False}
    monkeypatch.setattr(cli, "EpisodeClient", lambda _: client)

    def answer(prompt):
        if "Seleccione" in prompt:
            return "1"
        source.write_bytes(b"changed original")
        return "y"

    logs = []
    assert cli.main(["--root", str(tmp_path)], input_fn=answer, log=logs.append) == 1
    assert "cambio" in logs[-1]
    client.upload.assert_not_called()


def test_docker_autostart_only_for_refused_default(tmp_path, monkeypatch):
    import urllib.error

    client = EpisodeClient()
    config = {"dependencies": [{"api_name": name} for name in
                               ("folder_episode_settings", "create_folder_episode")]}
    monkeypatch.setattr(client, "_json", Mock(side_effect=[
        urllib.error.URLError(ConnectionRefusedError()), config]))
    monkeypatch.setattr("features.episode_client.shutil.which", lambda _: "docker")
    run = Mock(return_value=subprocess.CompletedProcess([], 0, stdout="ntn-podcast-creator\n"))
    monkeypatch.setattr("features.episode_client.subprocess.run", run)
    client.ensure_server(tmp_path, True, print)
    assert run.call_args_list[-1].args[0] == ["docker", "start", "ntn-podcast-creator"]


def test_server_failure_never_starts_docker_for_custom_url(tmp_path, monkeypatch):
    import urllib.error
    client = EpisodeClient("http://127.0.0.1:9876")
    monkeypatch.setattr(client, "_json", Mock(side_effect=urllib.error.URLError(
        ConnectionRefusedError())))
    run = Mock()
    monkeypatch.setattr("features.episode_client.subprocess.run", run)
    with pytest.raises(RuntimeError, match="conectar"):
        client.ensure_server(tmp_path, True, print)
    run.assert_not_called()


def test_upload_failure_and_terminal_error_visible(http_server, tmp_path):
    client, state = http_server
    empty = tmp_path / "Recording.wav"
    empty.touch()
    with pytest.raises(ValueError, match="vacia"):
        client.upload(empty)
    assert not state["uploads"]
    client._events = Mock(return_value={"schema": "ntn-episode-v1", "state": "error",
                                      "success": False, "error": "bad audio"})
    with pytest.raises(RuntimeError, match="bad audio"):
        client.render([], "ntn580", {}, print)


def test_menu_success_cancel_and_recovery(tmp_path, monkeypatch):
    path = tmp_path / "26 10 11 NTN 580"
    path.mkdir()
    (path / "Recording.m4a").write_bytes(b"original")
    client = Mock()
    client.server = "http://localhost:7860"
    client.settings.return_value = {"generate_transcript": False}
    client.render.return_value = {
        "episode_name": "ntn580", "output_path": "/outputs/ntn580.mp3",
        "mp3": {"path": "/outputs/ntn580.mp3", "orig_name": "ntn580.mp3"},
        "qc_status": "DISABLED",
    }
    monkeypatch.setattr(cli, "EpisodeClient", lambda _: client)
    opened = Mock()
    monkeypatch.setattr(cli, "open_episode_audio", opened)
    answers = iter(["wrong", "1", "n"])
    assert cli.main(["--root", str(tmp_path)], input_fn=lambda _: next(answers),
                    log=lambda _: None) == 0
    client.upload.assert_not_called()
    answers = iter(["1", "yes"])
    client.download.side_effect = OSError("disk unavailable")
    logs = []
    assert cli.main(["--root", str(tmp_path)], input_fn=lambda _: next(answers),
                    log=logs.append) == 1
    assert "no regenere" in logs[-1]
    assert (path / "Recording.m4a").read_bytes() == b"original"
    opened.assert_not_called()


@pytest.mark.parametrize("no_play", [False, True])
@pytest.mark.parametrize("confirmation", ["", "y", "YES", "yes", " Y ", "  "])
def test_menu_opens_downloaded_mp3_only_after_downloads(
        tmp_path, monkeypatch, no_play, confirmation):
    folder = tmp_path / "26 10 11 NTN 580"
    folder.mkdir()
    (folder / "Recording.m4a").write_bytes(b"original")
    client = Mock()
    client.settings.return_value = {"generate_transcript": False}
    client.render.return_value = {
        "episode_name": "ntn580", "output_path": "/outputs/ntn580.mp3",
        "mp3": {"orig_name": "ntn580.mp3"},
        "transcript": {"orig_name": "ntn580_transcript.txt"},
        "qc_status": "DISABLED",
    }

    def download(artifact, destination):
        path = destination / artifact["orig_name"]
        path.write_bytes(b"downloaded")
        return path

    client.download.side_effect = download
    monkeypatch.setattr(cli, "EpisodeClient", lambda _: client)
    opened = Mock()
    monkeypatch.setattr(cli, "open_episode_audio", opened)
    answers = iter(["1", confirmation])
    logs = []
    args = ["--root", str(tmp_path)] + (["--no-play"] if no_play else [])
    assert cli.main(args, input_fn=lambda _: next(answers), log=logs.append) == 0
    assert (folder / "ntn580_transcript.txt").exists()
    if no_play:
        opened.assert_not_called()
    else:
        opened.assert_called_once_with(folder / "ntn580.mp3", logs.append)


@pytest.mark.parametrize("confirmation", ["n", "NO", "no", " N "])
def test_confirmation_rejects_invalid_input_then_cancels(tmp_path, monkeypatch, confirmation):
    folder = tmp_path / "NTN 999 Draft"
    folder.mkdir()
    (folder / "Recording.mp3").write_bytes(b"original")
    client = Mock()
    client.settings.return_value = {}
    monkeypatch.setattr(cli, "EpisodeClient", lambda _: client)
    answers = iter(["1", "maybe", confirmation])
    prompts = []
    logs = []

    def answer(prompt):
        prompts.append(prompt)
        return next(answers)

    assert cli.main(["--root", str(tmp_path)], input_fn=answer, log=logs.append) == 0
    assert prompts[1:] == ["Crear episodio? YES/NO (y/n) [YES]: "] * 2
    assert any("Respuesta invalida" in message for message in logs)
    assert logs[-1] == "Cancelado; no se enviaron grabaciones."
    client.upload.assert_not_called()
    client.render.assert_not_called()


@pytest.mark.parametrize("failure", [False, True])
def test_windows_default_player_launch_and_warning(tmp_path, monkeypatch, failure):
    path = tmp_path / "episodio con espacios.mp3"
    path.write_bytes(b"saved")
    monkeypatch.setattr(cli.sys, "platform", "win32")
    launcher = Mock(side_effect=OSError("no player") if failure else None)
    monkeypatch.setattr(cli.os, "startfile", launcher, raising=False)
    logs = []
    cli.open_episode_audio(path, logs.append)
    launcher.assert_called_once_with(str(path.resolve()))
    assert ("Advertencia" in logs[-1]) is failure
    assert path.read_bytes() == b"saved"


@pytest.mark.parametrize("platform,command", [("darwin", "open"), ("linux", "xdg-open")])
def test_other_platform_player_launch(tmp_path, monkeypatch, platform, command):
    path = tmp_path / "episode.mp3"
    path.write_bytes(b"saved")
    monkeypatch.setattr(cli.sys, "platform", platform)
    launcher = Mock()
    monkeypatch.setattr(cli.subprocess, "run", launcher)
    cli.open_episode_audio(path, lambda _: None)
    launcher.assert_called_once_with([command, str(path.resolve())], check=True, timeout=30)
