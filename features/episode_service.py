"""Shared processor settings, render locking, and quality receipt persistence."""

import os
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional

from .audio_processor import (
    _quality_file_identity, _read_quality_sidecar, _register_quality_preview,
    _write_quality_sidecar,
)


_render_lock = threading.RLock()


@contextmanager
def render_lock() -> Iterator[None]:
    """Serialize CLI/UI processor state, including separate Linux processes."""
    with _render_lock:
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/.episode-render.lock", "a") as lock_file:
            if os.name == "posix":
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "posix":
                    fcntl.flock(lock_file, fcntl.LOCK_UN)


def render_audio(processor: Any, settings: Dict[str, Any], *,
                 voice_file: str, output_file: str,
                 background_enabled: bool, background_segments=None,
                 defer_transcription: bool = True,
                 log_callback: Optional[Callable[[str], None]] = None,
                 quality_report_callback=None):
    """One processor argument mapping for both UI and API requests."""
    return processor.create_podcast(
        voice_file=voice_file,
        intro_file=settings.get("intro_file"),
        outro_file=settings.get("outro_file"),
        background_files=settings.get("background_tracks") if background_enabled else None,
        background_segments=background_segments,
        background_volume=settings["background_volume"],
        track_volumes=settings.get("track_volumes") or None,
        output_file=output_file,
        trim_silence=settings["trim_silence"],
        denoise_audio=settings["denoise_audio"],
        denoise_method=settings["denoise_method"],
        enhance_voice_enabled=settings["enhance_voice"],
        voice_enhancement_preset=settings["voice_enhancement_preset"],
        normalize_lufs=settings["normalize_lufs"],
        target_lufs=settings["target_lufs"],
        intro_voice_overlap=settings["intro_voice_overlap"],
        voice_outro_overlap=settings["voice_outro_overlap"],
        auto_balance_levels=settings["auto_balance_levels"],
        min_voice_music_separation_db=settings["min_voice_music_separation_db"],
        auto_ducking=settings["auto_ducking"],
        generate_transcript=settings["generate_transcript"],
        whisper_model=settings["whisper_model"],
        defer_transcription=defer_transcription,
        log_callback=log_callback,
        quality_gate_enabled=settings["quality_gate_enabled"],
        quality_config=settings.get("quality_config"),
        music_seed=settings["music_seed"],
        quality_report_callback=quality_report_callback,
        level_quiet_opening=settings["level_quiet_opening"],
    )


def persist_quality_report(output_path, enabled, report, started_ns, log):
    """Bind this request's callback report and producer metadata to its export."""
    output_path = os.path.realpath(output_path)
    if report is not None and os.path.realpath(report.file_path or "") != output_path:
        raise ValueError("Quality report belongs to a different audio file")
    identity = _quality_file_identity(output_path)
    metadata = None
    try:
        producer = _read_quality_sidecar(output_path)
        if producer["identity"] == identity:
            metadata = producer.get("metadata")
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError) as error:
        log(f"Producer quality metadata unavailable: {error}")
    preview = report.preview_file if enabled and report is not None else None
    preview_identity = _register_quality_preview(preview, output_path)
    data = report.to_dict() if enabled and report is not None else {}
    if enabled and metadata is not None:
        data["metadata"] = metadata
    data.update({
        "schema": "ntn-quality-v1", "output_path": output_path,
        "identity": identity, "preview_identity": preview_identity,
        "ui": {"identity": identity, "started_ns": started_ns,
               "enabled": bool(enabled), "preview_identity": preview_identity,
               "override": False},
    })
    if _quality_file_identity(output_path) != identity:
        raise ValueError("Audio changed while saving the quality receipt")
    _write_quality_sidecar(output_path + ".quality.json", data)
