"""CLI defaults, safe publication, and the real Gradio HTTP contract."""

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock

import gradio as gr
import pytest
import requests
from pydub import AudioSegment
from pydub.generators import Sine

from features.config_manager import ConfigManager
from features.episode_api import (
    EpisodeRequest, episode_events, register_episode_api, render_saved_episode,
)
from features.episode_naming import extract_ntn_number, next_rss_name, reserve_output, validate_name
from features.episode_service import render_lock


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "core").mkdir()
    manager = ConfigManager()
    recording = tmp_path / "S recording 3.wav"
    Sine(440).to_audio_segment(duration=250).export(recording, format="wav")
    processor = Mock()

    def render(**kwargs):
        processor.settings_seen = kwargs
        kwargs["log_callback"]("Mixing audio...")
        AudioSegment.from_file(kwargs["voice_file"]).export(kwargs["output_file"], format="mp3")
        return kwargs["output_file"], None, None

    processor.create_podcast.side_effect = render
    return manager, processor, recording


def test_cli_defaults_and_original_preserved(setup):
    manager, processor, recording = setup
    music = recording.with_name("music.wav")
    shutil.copyfile(recording, music)
    manager.update_settings({
        "generate_transcript": True, "delete_voice": True,
        "background_tracks": [str(music)], "track_volumes": {str(music): 7},
        "background_volume": 4,
    })
    before = recording.read_bytes()
    result = render_saved_episode(
        manager, processor, EpisodeRequest(str(recording), "ntn568"), lambda _: None)
    assert result["success"] and result["state"] == "complete"
    assert processor.settings_seen["background_files"] == [str(music)]
    assert processor.settings_seen["track_volumes"] == {str(music): 7}
    assert processor.settings_seen["generate_transcript"] is False
    processor.transcribe_podcast.assert_not_called()
    assert manager.snapshot()["generate_transcript"] is True
    assert recording.read_bytes() == before
    assert not list(Path("uploads").iterdir())
    assert AudioSegment.from_file(result["mp3"]["path"]).duration_seconds > 0
    assert manager.snapshot()["last_output_name"] == "ntn568"


def test_cli_overrides_are_request_local(setup):
    manager, processor, recording = setup
    manager.update_settings({"whisper_model": "small", "background_tracks": ["missing.wav"]})

    def transcribe(**kwargs):
        path = Path(kwargs["audio_file"]).with_name("ntn569_transcript.txt")
        path.write_text("hello", encoding="utf-8")
        return str(path)

    processor.transcribe_podcast.side_effect = transcribe
    result = render_saved_episode(manager, processor,
                                  EpisodeRequest(str(recording), "ntn569", False, True),
                                  lambda _: None)
    assert result["transcript"]["orig_name"] == "ntn569_transcript.txt"
    assert processor.settings_seen["background_files"] is None
    assert processor.transcribe_podcast.call_args.kwargs["whisper_model"] == "small"
    assert manager.snapshot()["generate_transcript"] is False


def test_real_processor_exports_mix_and_bound_quality_report(setup):
    from features.audio_processor import AudioProcessor, _read_quality_sidecar
    manager, _, recording = setup
    intro = recording.with_name("intro.wav")
    outro = recording.with_name("outro.wav")
    music = recording.with_name("music.wav")
    for path, frequency in ((intro, 220), (outro, 660), (music, 880)):
        Sine(frequency).to_audio_segment(duration=250).export(path, format="wav")
    manager.update_settings({
        "intro_file": str(intro), "outro_file": str(outro),
        "background_tracks": [str(music)], "intro_voice_overlap": False,
        "voice_outro_overlap": False, "quality_gate_enabled": True,
    })
    result = render_saved_episode(manager, AudioProcessor(),
                                  EpisodeRequest(str(recording), "ntn573"), lambda _: None)
    output = result["mp3"]["path"]
    assert 0.70 < AudioSegment.from_file(output).duration_seconds < 0.80
    assert result["quality_report"] is not None
    receipt = _read_quality_sidecar(output)
    assert receipt["output_path"] == output
    assert receipt["ui"]["enabled"] is True
    assert receipt["metadata"]["settings"]["intro_file"] == str(intro)


def test_transcription_failure_keeps_export(setup):
    manager, processor, recording = setup
    processor.transcribe_podcast.side_effect = RuntimeError("model unavailable")
    result = render_saved_episode(manager, processor,
                                  EpisodeRequest(str(recording), "ntn570", transcribe=True),
                                  lambda _: None)
    assert result["success"] and result["transcript"] is None
    assert any("model unavailable" in warning for warning in result["warnings"])


def test_cleaned_voice_survives_staging_cleanup(setup):
    manager, processor, recording = setup
    original = processor.create_podcast.side_effect

    def render_cleaned(**kwargs):
        rendered, _, _ = original(**kwargs)
        cleaned = Path(kwargs["voice_file"]).with_name("cleaned.wav")
        shutil.copyfile(kwargs["voice_file"], cleaned)
        return rendered, str(cleaned), None

    processor.create_podcast.side_effect = render_cleaned
    result = render_saved_episode(manager, processor,
                                  EpisodeRequest(str(recording), "ntn579"), lambda _: None)
    assert Path(result["denoised"]["path"]).read_bytes() == recording.read_bytes()
    assert not list(Path("uploads").iterdir())


def test_collisions_never_overwrite_and_failures_cleanup(setup):
    manager, processor, recording = setup
    Path("outputs").mkdir()
    existing = Path("outputs/ntn571.mp3")
    existing.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        render_saved_episode(manager, processor,
                             EpisodeRequest(str(recording), "ntn571"), lambda _: None)
    assert existing.read_bytes() == b"keep"
    processor.create_podcast.side_effect = RuntimeError("export failed")
    events = list(episode_events(manager, processor, EpisodeRequest(str(recording), "ntn572")))
    assert events[-1]["state"] == "error" and not events[-1]["success"]
    assert "export failed" in events[-1]["error"]
    assert not Path("outputs/ntn572.mp3").exists()
    assert not list(Path("outputs").glob(".ntn-reservation-*"))
    assert not list(Path("uploads").iterdir())


def test_publication_race_never_clobbers(setup):
    manager, processor, recording = setup
    original = processor.create_podcast.side_effect

    def competing_writer(**kwargs):
        result = original(**kwargs)
        Path("outputs/ntn576.mp3").write_bytes(b"someone else's export")
        return result

    processor.create_podcast.side_effect = competing_writer
    result = list(episode_events(manager, processor, EpisodeRequest(str(recording), "ntn576")))[-1]
    assert not result["success"]
    assert Path("outputs/ntn576.mp3").read_bytes() == b"someone else's export"


def test_optional_warning_and_missing_saved_asset(setup):
    manager, processor, recording = setup
    original = processor.create_podcast.side_effect

    def optional_failure(**kwargs):
        kwargs["log_callback"]("Warning: Denoising failed. Using original audio.")
        return original(**kwargs)

    processor.create_podcast.side_effect = optional_failure
    result = render_saved_episode(manager, processor,
                                  EpisodeRequest(str(recording), "ntn577"), lambda _: None)
    assert result["success"] and any("Denoising failed" in warning for warning in result["warnings"])
    manager.update_settings({"intro_file": "missing.wav"})
    result = list(episode_events(manager, processor, EpisodeRequest(str(recording), "ntn578")))[-1]
    assert not result["success"] and "Saved intro_file is missing" in result["error"]


@pytest.mark.parametrize("name", ["", "../episode", "/tmp/episode", r"C:\episode",
                                 "episode.mp3", "CON", "LPT1", "has space", "a" * 101])
def test_invalid_names(name):
    with pytest.raises(ValueError):
        validate_name(name)


def test_rss_and_reservations(tmp_path, monkeypatch):
    response = Mock()
    response.read.return_value = b"<rss><channel><item><title>NTN 567</title></item></channel></rss>"
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: response)
    assert next_rss_name("https://example.com/feed") == "ntn568"
    assert extract_ntn_number("Other title") is None
    monkeypatch.chdir(tmp_path)
    Path("outputs").mkdir()
    Path("outputs/ntn568.mp3").write_bytes(b"one")
    Path("outputs/ntn569.mp3.quality.json").write_text("{}")
    Path("outputs/.ntn-reservation-ntn570").write_text("abandoned")
    with render_lock(), reserve_output(Path("outputs"), "ntn568", True) as path:
        assert path.name == "ntn570.mp3"
        assert Path("outputs/.ntn-reservation-ntn570").exists()
    assert not Path("outputs/.ntn-reservation-ntn570").exists()
    response.read.return_value = b"<rss/>"
    with pytest.raises(ValueError, match="Supply -Name"):
        next_rss_name("https://example.com/feed")


def test_auto_names_and_snapshot_are_stable(setup, monkeypatch):
    manager, processor, recording = setup
    monkeypatch.setattr("features.episode_api.next_rss_name", lambda _: "ntn574")
    original = processor.create_podcast.side_effect

    def change_saved_settings(**kwargs):
        manager.update_settings({"background_volume": 33})
        return original(**kwargs)

    processor.create_podcast.side_effect = change_saved_settings
    one = render_saved_episode(manager, processor, EpisodeRequest(str(recording)), lambda _: None)
    assert one["episode_name"] == "ntn574"
    assert processor.settings_seen["background_volume"] == 2.5
    two = render_saved_episode(manager, processor, EpisodeRequest(str(recording)), lambda _: None)
    assert two["episode_name"] == "ntn575"


@pytest.fixture
def server(setup):
    manager, processor, recording = setup
    with gr.Blocks() as app:
        register_episode_api(manager, processor)
    app.queue(default_concurrency_limit=1)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    app.launch(server_name="127.0.0.1", server_port=port,
               prevent_thread_lock=True, quiet=True)
    yield f"http://127.0.0.1:{port}", manager, processor, recording, app
    app.close()


def submit(server, name, background=True, transcribe=False, path=None):
    url, _, _, recording, _ = server
    if path is None:
        with recording.open("rb") as audio:
            uploaded = requests.post(url + "/gradio_api/upload",
                                     files={"files": (recording.name, audio)}, timeout=10)
        uploaded.raise_for_status()
        path = uploaded.json()[0]
    response = requests.post(url + "/gradio_api/call/create_episode",
                             json={"data": [{"path": path, "meta": {"_type": "gradio.FileData"}},
                                            name, background, transcribe]}, timeout=10)
    response.raise_for_status()
    return response.json()["event_id"]


def collect(server, event_id):
    url = server[0]
    response = requests.get(url + "/gradio_api/call/create_episode/" + event_id, timeout=30)
    response.raise_for_status()
    lines = response.text.splitlines()
    for index, line in enumerate(lines):
        if line == "event: complete":
            return json.loads(lines[index + 1].removeprefix("data: "))[0]
    raise AssertionError(response.text)


def test_actual_upload_stream_download_and_queue(server):
    active = 0
    maximum = 0
    original = server[2].create_podcast.side_effect

    def slow_render(**kwargs):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        time.sleep(0.1)
        try:
            return original(**kwargs)
        finally:
            active -= 1

    server[2].create_podcast.side_effect = slow_render
    first = submit(server, "ntn580")
    second = submit(server, "ntn581")
    one, two = collect(server, first), collect(server, second)
    assert one["success"] and two["success"]
    artifact = one["mp3"]
    url = artifact.get("url") or server[0] + "/gradio_api/file=" + artifact["path"]
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    assert len(response.content) > 0
    assert server[2].settings_seen["generate_transcript"] is False
    assert maximum == 1
    dependency = next(d for d in server[4].config["dependencies"] if d["api_name"] == "create_episode")
    assert server[4].fns[dependency["id"]].concurrency_id == "episode-render"


def test_api_rejects_server_paths_and_duplicate_names(server):
    bad = submit(server, "ntn582", path=str(server[3]))
    response = requests.get(server[0] + "/gradio_api/call/create_episode/" + bad, timeout=10)
    assert "event: error" in response.text
    server[2].create_podcast.assert_not_called()
    assert collect(server, submit(server, "ntn583"))["success"]
    duplicate = collect(server, submit(server, "ntn583"))
    assert not duplicate["success"] and "already exists" in duplicate["error"]


@pytest.mark.parametrize("transcribe,no_background", [(False, False), (True, True)])
def test_powershell_client(server, tmp_path, transcribe, no_background):
    pwsh = os.environ.get("NTN_PWSH") or shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is not installed; set NTN_PWSH to test the client")
    output = tmp_path / "download with spaces"
    server[1].update_settings({"background_tracks": [str(server[3])]})
    command = [pwsh, "-NoProfile", "-File", str(ROOT / "scripts/ntn-create.ps1"),
               str(server[3]), "-Name", "ntn590", "-ServerUrl", server[0],
               "-OutputDirectory", str(output)]
    if transcribe:
        def transcript(**kwargs):
            path = Path(kwargs["audio_file"]).with_name("ntn590_transcript.txt")
            path.write_text("hello", encoding="utf-8")
            return str(path)
        server[2].transcribe_podcast.side_effect = transcript
        command.append("-Transcribe")
    if no_background:
        command.append("-NoBackground")
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (output / "ntn590.mp3").is_file()
    assert (output / "ntn590_transcript.txt").exists() is transcribe
    assert bool(server[2].settings_seen["background_files"]) is not no_background
    assert server[3].is_file()
    repeated = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert repeated.returncode != 0
    assert not list(output.glob("*.part"))
    existing = output / "ntn591.mp3"
    existing.write_bytes(b"local file to keep")
    command[command.index("ntn590")] = "ntn591"
    blocked_download = subprocess.run(command, capture_output=True, text=True, timeout=45)
    assert blocked_download.returncode != 0
    assert existing.read_bytes() == b"local file to keep"
    assert not list(output.glob("*.part"))


@pytest.mark.parametrize("stream", ["event: generating\ndata: [{\"schema\":\"ntn-episode-v1\",\"logs\":[]}]\n\n",
                                  "event: complete\ndata: [{\"unexpected\":true}]\n\n"])
def test_powershell_disconnect_and_malformed_result(tmp_path, stream):
    pwsh = os.environ.get("NTN_PWSH") or shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is not installed")
    posts = []

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, content_type="application/json"):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/config":
                self.send(b'{"dependencies":[{"api_name":"create_episode"}]}')
            else:
                self.send(stream.encode(), "text/event-stream")

        def do_POST(self):
            posts.append(self.path)
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send(b'["/uploaded.wav"]' if self.path.endswith("/upload")
                      else b'{"event_id":"job1"}')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    recording = tmp_path / "recording with spaces.wav"
    recording.write_bytes(b"recording")
    try:
        command = [pwsh, "-NoProfile", "-File", str(ROOT / "scripts/ntn-create.ps1"),
                   str(recording), "-ServerUrl", f"http://127.0.0.1:{server.server_port}",
                   "-OutputDirectory", str(tmp_path / "downloads")]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        assert result.returncode != 0
        assert "may still be processing" in result.stdout
        assert posts.count("/gradio_api/call/create_episode") == 1
        assert recording.read_bytes() == b"recording"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
