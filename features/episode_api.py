"""Queued, upload-only CLI API for saved-setting episode production."""

import copy
import os
import queue
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

import gradio as gr
from gradio.utils import get_upload_folder
from pydub import AudioSegment

from .audio_quality import AudioQualityConfig
from .audio_processor import _read_quality_sidecar, _write_quality_sidecar, _quality_file_identity
from .episode_naming import next_rss_name, reserve_output
from .episode_service import persist_quality_report, render_audio, render_lock


@dataclass(frozen=True)
class EpisodeRequest:
    recording: str
    name: str = ""
    background: bool = True
    transcribe: bool = False


def file_reference(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    return {"path": str(Path(path).resolve()), "orig_name": Path(path).name,
            "meta": {"_type": "gradio.FileData"}}


def render_saved_episode(manager, processor, request: EpisodeRequest,
                         log: Callable[[str], None]) -> Dict[str, Any]:
    """Own staging and publication; never modify the supplied recording."""
    warnings = []

    def record(message: str) -> None:
        log(message)
        if any(word in message.lower() for word in
               ("warning", "failed", "unavailable", "could not", "error")):
            warnings.append(message)

    with render_lock():
        settings = manager.snapshot()
        defaults = manager._default_config()
        for key in defaults:
            manager._validate_setting(key, settings[key], defaults)
        settings["quality_config"] = AudioQualityConfig.from_mapping(
            dict(settings["audio_quality"], target_lufs=settings["target_lufs"]))
        settings["generate_transcript"] = request.transcribe
        for key in ("intro_file", "outro_file"):
            if settings[key] and not Path(settings[key]).is_file():
                raise FileNotFoundError(f"Saved {key} is missing: {settings[key]}")
        if request.background:
            for track in settings["background_tracks"]:
                if not Path(track).is_file():
                    raise FileNotFoundError(f"Saved background track is missing: {track}")
        source = Path(request.recording)
        if not source.is_file():
            raise FileNotFoundError("Uploaded recording is missing")
        automatic = not request.name
        name = next_rss_name(settings["rss_feed_url"]) if automatic else request.name
        with reserve_output(Path("outputs"), name, automatic) as output:
            record(f"Episode name: {output.stem}")
            record(f"Background music: {'enabled' if request.background else 'disabled'}")
            record(f"Intro: {settings['intro_file'] or 'none'}; outro: {settings['outro_file'] or 'none'}")
            record(f"Saved background tracks: {len(settings['background_tracks'])}; "
                   f"master volume: {settings['background_volume']}%")
            record(f"Transcription: {'enabled' if request.transcribe else 'disabled'}")
            os.makedirs("uploads", exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="episode-", dir="uploads") as inputs, \
                    tempfile.TemporaryDirectory(prefix=".episode-", dir="outputs") as staging:
                voice = Path(inputs) / source.name
                shutil.copyfile(source, voice)
                if len(AudioSegment.from_file(voice)) == 0:
                    raise ValueError("Recording contains no audio")
                staged_output = Path(staging) / output.name
                reports = []
                started = time.time_ns()
                rendered, cleaned, _ = render_audio(
                    processor, settings, voice_file=str(voice),
                    output_file=str(staged_output), background_enabled=request.background,
                    log_callback=record, quality_report_callback=lambda report: reports.append(
                        copy.deepcopy(report)),
                )
                if Path(rendered).resolve() != staged_output.resolve() or not staged_output.is_file():
                    raise RuntimeError("Processor did not create the requested MP3")
                if staged_output.stat().st_size == 0:
                    raise RuntimeError("Processor exported an empty MP3")
                producer = None
                if settings["quality_gate_enabled"]:
                    try:
                        producer = _read_quality_sidecar(str(staged_output))
                    except FileNotFoundError:
                        pass
                    except (OSError, ValueError, TypeError) as error:
                        record(f"Warning: Producer quality metadata unavailable: {error}.")
                # Hard-link publication is atomic and cannot replace an existing path.
                os.link(staged_output, output)
                # Unlink before binding QC identity: dropping a hard link changes ctime.
                staged_output.unlink()
                output = output.resolve()
                quality_path = None
                qc = "DISABLED"
                if settings["quality_gate_enabled"]:
                    report = reports[0] if reports else None
                    qc = report.status if report else "UNAVAILABLE"
                    try:
                        if producer is not None:
                            producer.update(output_path=str(output),
                                            identity=_quality_file_identity(str(output)))
                            _write_quality_sidecar(str(output) + ".quality.json", producer)
                        if report is not None:
                            report.file_path = str(output)
                        persist_quality_report(str(output), True, report, started, record)
                        quality_path = str(output) + ".quality.json"
                    except (OSError, ValueError, TypeError, AttributeError) as error:
                        qc = "UNAVAILABLE"
                        record(f"Warning: Quality report could not be saved: {error}. MP3 is available.")
                cleaned_path = None
                if cleaned and Path(cleaned).is_file():
                    cleaned_output = output.with_name(output.stem + "_denoised.wav")
                    try:
                        # Denoisers may emit WAV or another format; retain the real suffix.
                        cleaned_output = cleaned_output.with_suffix(Path(cleaned).suffix)
                        with tempfile.NamedTemporaryFile(dir=staging, suffix=".cleaned") as staged_cleaned:
                            with open(cleaned, "rb") as audio:
                                shutil.copyfileobj(audio, staged_cleaned)
                            staged_cleaned.flush()
                            os.link(staged_cleaned.name, cleaned_output)
                        cleaned_path = str(cleaned_output)
                    except OSError as error:
                        record(f"Warning: Cleaned voice could not be saved: {error}. MP3 is available.")
                try:
                    manager.update_settings({"last_output_name": output.stem})
                except (OSError, ValueError, TypeError) as error:
                    record(f"Warning: Last episode name could not be saved: {error}. MP3 is available.")
                transcript = None
                if request.transcribe:
                    record("Transcribing exported episode...")
                    try:
                        transcript = processor.transcribe_podcast(
                            audio_file=str(output), whisper_model=settings["whisper_model"],
                            log_callback=record)
                        if not transcript or not Path(transcript).is_file():
                            transcript = None
                            record("Transcription failed. Continuing with the exported MP3.")
                    except Exception as error:
                        record(f"Transcription failed: {error}. Continuing with the exported MP3.")
                record(f"Export complete: {output}")
                return {
                    "schema": "ntn-episode-v1", "state": "complete", "success": True,
                    "episode_name": output.stem, "output_path": str(output),
                    "warnings": warnings, "qc_status": qc,
                    "mp3": file_reference(str(output)),
                    "denoised": file_reference(cleaned_path),
                    "transcript": file_reference(transcript),
                    "quality_report": file_reference(quality_path),
                }


def episode_events(manager, processor, request: EpisodeRequest) -> Iterator[Dict[str, Any]]:
    """Stream complete JSON snapshots; do not rely on Gradio UI console state."""
    messages = queue.Queue()
    result = {}
    logs = []

    def run():
        try:
            result.update(render_saved_episode(manager, processor, request, messages.put))
        except Exception as error:
            result.update(schema="ntn-episode-v1", state="error", success=False,
                          error=str(error))
            messages.put(f"Episode failed: {error}")

    worker = threading.Thread(target=run, name="cli-episode")
    worker.start()
    try:
        while worker.is_alive():
            try:
                logs.append(messages.get(timeout=0.2))
                while not messages.empty():
                    logs.append(messages.get_nowait())
                yield {"schema": "ntn-episode-v1", "state": "processing",
                       "success": False, "logs": list(logs)}
            except queue.Empty:
                continue
        worker.join()
        while not messages.empty():
            logs.append(messages.get_nowait())
        yield dict(result, logs=logs)
    finally:
        # Disconnecting must not release the queue slot while rendering continues.
        worker.join()


def register_episode_api(manager, processor):
    def create_episode(recording: gr.FileData, name: str = "",
                       background: bool = True, transcribe: bool = False) -> Iterator[dict]:
        # gr.api does not preprocess components; explicitly limit paths to uploads.
        data = gr.FileData.model_validate(recording)
        path = Path(data.path).resolve()
        if not isinstance(name, str) or type(background) is not bool or type(transcribe) is not bool:
            yield {"schema": "ntn-episode-v1", "state": "error", "success": False,
                   "error": "Name must be a string; background and transcribe must be booleans."}
            return
        if not path.is_relative_to(Path(get_upload_folder()).resolve()) or not path.is_file():
            yield {"schema": "ntn-episode-v1", "state": "error", "success": False,
                   "error": "Upload the recording using /gradio_api/upload first."}
            return
        yield from episode_events(manager, processor, EpisodeRequest(
            str(path), name, background, transcribe))

    return gr.api(create_episode, api_name="create_episode",
                  api_description="Upload one recording and render with saved settings. "
                  "Music defaults on; transcription defaults off.",
                  concurrency_id="episode-render", concurrency_limit=1)
