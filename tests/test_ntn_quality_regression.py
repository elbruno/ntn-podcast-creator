"""Opt-in ORIGINAL-recording pipeline regressions; contract: tests/audio/README.md."""

import json
import math
import re
import shutil
from dataclasses import fields
from pathlib import Path, PureWindowsPath

import pytest

from features.audio_quality import AudioQualityConfig


ROOT = Path(__file__).parent / "audio"
MANIFEST = ROOT / "manifest.json"
EPISODES = ("ntn567", "ntn568")
BOOL_SETTINGS = {
    "trim_silence", "denoise_audio", "enhance_voice_enabled", "normalize_lufs",
    "intro_voice_overlap", "voice_outro_overlap", "auto_balance_levels",
    "auto_ducking", "generate_transcript",
}
REQUIRED_SETTINGS = BOOL_SETTINGS | {
    "intro_file", "outro_file", "background_files", "background_segments",
    "background_volume", "track_volumes", "target_lufs",
    "min_voice_music_separation_db", "music_seed", "quality_config",
}
SHARED_SETTINGS = (
    "intro_file", "outro_file", "background_files", "music_seed",
    "target_lufs", "quality_config",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _input_path(value, root, original=False):
    _require(isinstance(value, str) and bool(value.strip()),
             "Input path must be a nonempty string")
    path = Path(value)
    _require(not PureWindowsPath(value).drive or path.is_absolute(),
             "Windows source is not mounted here; supply a native absolute mounted path")
    _require(".." not in path.parts, "Input path traversal is forbidden")
    if not path.is_absolute():
        _require("\\" not in value,
                 "Use native relative paths, not Windows backslashes")
    resolved = (root / path).resolve()
    if not path.is_absolute():
        _require(root.resolve() in resolved.parents,
                 "Relative inputs must stay inside tests/audio")
    _require(resolved.is_file() and resolved.stat().st_size > 0,
             "Missing or empty input file: " + str(resolved))
    if original:
        for candidate in (path, resolved):
            _require(not any(part.lower() == "outputs" for part in candidate.parts),
                     "Final episodes in outputs cannot be original recordings")
            _require(not re.search(r"denois|noisereduce|rnnoise|enhanced|concatenat|processed|render|final",
                                   candidate.stem, re.IGNORECASE)
                     and not re.fullmatch(r"ntn[-_ ]?56[78](?:[-_ ].*)?", candidate.stem, re.IGNORECASE),
                     "Processed intermediates/final episodes cannot be original recordings")
    return str(resolved)


def _settings(value, root):
    _require(isinstance(value, dict), "Settings must be an object")
    _require(set(value) == REQUIRED_SETTINGS,
             "Settings keys mismatch; missing={}, unknown/forbidden={}".format(
                 sorted(REQUIRED_SETTINGS - set(value)), sorted(set(value) - REQUIRED_SETTINGS)))
    result = dict(value)
    for key in BOOL_SETTINGS:
        _require(type(value[key]) is bool, key + " must be boolean")
    for key in ("denoise_audio", "enhance_voice_enabled", "generate_transcript"):
        _require(value[key] is False, key +
                 " must be false: local DSP only, no source pre-processing")
    _require(type(value["music_seed"]) is int, "music_seed must be an integer")
    _require(_number(value["background_volume"]) and 0 <= value["background_volume"] <= 100,
             "background_volume must be in [0, 100]")
    _require(_number(value["target_lufs"]) and -70 <= value["target_lufs"] <= -5,
             "target_lufs must be in [-70, -5]")
    _require(_number(value["min_voice_music_separation_db"])
             and value["min_voice_music_separation_db"] >= 0,
             "min_voice_music_separation_db must be finite and nonnegative")
    config = value["quality_config"]
    _require(isinstance(config, dict),
             "quality_config must be an object ({} uses current defaults)")
    _require(set(config) <= {item.name for item in fields(AudioQualityConfig)},
             "Unknown quality_config key")
    _require(all(_number(number) for number in config.values()),
             "quality_config values must be finite numbers, not strings/null/booleans")
    AudioQualityConfig.from_mapping(
        dict(config, target_lufs=value["target_lufs"]))
    _require(config.get("target_lufs", value["target_lufs"]) == value["target_lufs"],
             "Conflicting target_lufs values")
    for key in ("intro_file", "outro_file"):
        result[key] = None if value[key] is None else _input_path(
            value[key], root)
    _require(isinstance(value["background_files"], list),
             "background_files must be a list (empty is allowed)")
    result["background_files"] = [_input_path(
        path, root) for path in value["background_files"]]
    _require(isinstance(value["track_volumes"], dict),
             "track_volumes must be an object (empty is allowed)")
    volumes = {}
    for path, volume in value["track_volumes"].items():
        resolved = _input_path(path, root)
        _require(resolved in result["background_files"] and resolved not in volumes,
                 "track_volumes keys must identify distinct background_files")
        _require(_number(volume) and 0 <= volume <= 100,
                 "Track volume must be in [0, 100]")
        volumes[resolved] = volume
    result["track_volumes"] = volumes
    segments = value["background_segments"]
    _require(segments is None or isinstance(segments, list),
             "background_segments must be null or a list")
    for pair in segments or []:
        _require(isinstance(pair, list) and len(pair) == 2
                 and all(type(number) is int for number in pair) and 0 <= pair[0] < pair[1],
                 "Each background segment must be [start_ms, end_ms], integers with 0 <= start < end")
    return result


def validate_manifest(manifest, root=ROOT):
    """Validate BOTH episodes before any pipeline writes; never infer incident labels."""
    _require(isinstance(manifest, dict) and set(manifest) == set(EPISODES),
             "Manifest must contain exactly ntn567 and ntn568")
    validated = {}
    required = {"approved_for_testing", "originals_confirmed", "original_recordings",
                "baseline_settings", "fixed_settings", "expected_baseline_failure_codes"}
    for episode, item in manifest.items():
        _require(isinstance(item, dict) and required <= set(item)
                 and set(item) <= required | {"expected_original_duration_seconds"},
                 episode + ": missing or unknown episode keys")
        _require(item["approved_for_testing"] is True and item["originals_confirmed"] is True,
                 episode + ": approval and original-recording provenance must be confirmed")
        recordings = item["original_recordings"]
        _require(isinstance(recordings, list) and recordings,
                 "original_recordings must be an ordered nonempty list")
        recordings = [_input_path(path, root, original=True)
                      for path in recordings]
        _require(len(set(recordings)) == len(recordings),
                 "Duplicate original recordings")
        codes = item["expected_baseline_failure_codes"]
        _require(isinstance(codes, list) and bool(codes)
                 and all(isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", code)
                         and not code.endswith("UNAVAILABLE") for code in codes)
                 and len(set(codes)) == len(codes),
                 "Supply explicit, unique baseline failure codes; analysis-unavailable is not an incident")
        duration = item.get("expected_original_duration_seconds")
        _require("expected_original_duration_seconds" not in item or (_number(duration) and duration > 0),
                 "expected_original_duration_seconds must be positive and finite")
        baseline = _settings(item["baseline_settings"], root)
        fixed = _settings(item["fixed_settings"], root)
        for key in SHARED_SETTINGS:
            _require(baseline[key] == fixed[key],
                     "Baseline/fixed must share " + key)
        _require(baseline != fixed,
                 "Supply distinct baseline and fixed settings, not invented labels")
        validated[episode] = dict(item, original_recordings=recordings,
                                  baseline_settings=baseline, fixed_settings=fixed)
    return validated


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def _load_manifest(path=MANIFEST):
    # lexists semantics: a dangling symlink/directory is a configured error, not a skip.
    if not path.exists() and not path.is_symlink():
        pytest.skip(
            "Original NTN recordings and explicit baseline/fixed manifest not supplied; see tests/audio/README.md")
    return validate_manifest(json.loads(path.read_text(encoding="utf-8"),
                                        object_pairs_hook=_unique_object), path.parent)


def _identity(path):
    info = Path(path).stat()
    # No atime: decoding legitimately reads files. Avoid hashing full episodes.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _assert_complete_metrics(report):
    data = report.to_dict()
    assert report.analysis_complete and not report.analysis_errors, data
    for key in ("duration_seconds", "integrated_lufs", "true_peak_dbtp", "clipped_samples",
                "clipped_percentage", "longest_silence_seconds", "voice_level_dbfs",
                "speech_active_seconds", "speech_below_warning_percentage",
                "speech_below_failure_percentage", "suggested_music_reduction_db"):
        assert _number(data[key]), (key, data)
    assert data["duration_seconds"] > 0 and data["speech_active_seconds"] > 0, data
    assert report.windows, data
    for window in report.windows:
        for key in ("timestamp_start", "timestamp_end", "voice_level_dbfs"):
            assert _number(window[key]), (key, window)
        assert window["timestamp_end"] > window["timestamp_start"], window
        for key in ("music_level_dbfs", "voice_music_ratio_db"):
            assert (_number(window[key]) if window["music_present"]
                    else window[key] is None), window
    # Music-free windows have infinite VMR, serialized as null. Selective music
    # may therefore make even the median/p10 legitimately null, not incomplete.
    # Recover the pipeline's integer-ms grid: 0.7 - 0.2 can be < 0.5 in floats.
    music_ms = sum(round((window["timestamp_end"] - window["timestamp_start"]) * 1000)
                   for window in report.windows if window["music_present"])
    speech_ms = round(report.speech_active_seconds * 1000)
    assert report.music_present == (music_ms > 0), data
    for key, quantile in (("median_voice_music_ratio_db", 0.5),
                          ("p10_voice_music_ratio_db", 0.1),
                          ("worst_voice_music_ratio_db", 0)):
        applicable = music_ms > 0 and music_ms >= quantile * speech_ms
        assert (_number(data[key])
                if applicable else data[key] is None), (key, data)
    if report.music_present:
        for key in ("worst_section_start_seconds", "worst_section_end_seconds",
                    "worst_section_voice_music_ratio_db"):
            assert _number(data[key]), (key, data)


@pytest.mark.parametrize("episode,variant", [
    ("ntn567", "bad"), ("ntn567", "fixed"),
    ("ntn568", "bad"), ("ntn568", "fixed"),
], ids=["ntn567_bad", "ntn567_fixed", "ntn568_bad", "ntn568_fixed"])
def test_original_ntn_pipeline(episode, variant, tmp_path):
    item = _load_manifest()[episode]
    # Import the real pipeline only after opt-in; do not stub modules or download models.
    from features.audio_processor import AudioProcessor, _cleanup_quality_preview

    assert shutil.which("ffmpeg") and shutil.which(
        "ffprobe"), "Configured regressions require local FFmpeg/ffprobe"
    settings = item["baseline_settings" if variant ==
                    "bad" else "fixed_settings"]
    recordings = item["original_recordings"]
    sources = set(recordings)
    for options in (item["baseline_settings"], item["fixed_settings"]):
        sources.update(options["background_files"])
        sources.update(options[key] for key in (
            "intro_file", "outro_file") if options[key])
    before = {path: _identity(path) for path in sources}
    processor, reports, logs = AudioProcessor(), [], []
    try:
        # Validate complete, decodable assets instead of accepting optional-stage fallbacks.
        durations = {path: len(processor.load_audio(path)) for path in sources}
        assert all(duration > 0 for duration in durations.values()
                   ), "Empty decoded source audio"
        if "expected_original_duration_seconds" in item:
            assert sum(durations[path] for path in recordings) / 1000 == pytest.approx(
                item["expected_original_duration_seconds"], abs=0.1, rel=0)
        voice = recordings[0]
        if len(recordings) > 1:
            voice = processor.concatenate_audio_files(
                recordings, output_path=str(tmp_path / "ordered-originals.mp3"), log_callback=logs.append)
        output = tmp_path / (episode + "_" + variant + ".mp3")
        result = processor.create_podcast(
            **settings, voice_file=voice, output_file=str(output),
            quality_gate_enabled=True, quality_report_callback=reports.append, log_callback=logs.append)
        assert result == (str(output), None, None), logs
        assert output.is_file() and output.stat().st_size > 0, logs
        assert len(reports) == 1, logs
        report = reports[0]
        assert report.file_path == str(output), report.to_dict()
        _assert_complete_metrics(report)
        if variant == "bad":
            assert report.status == "FAIL", report.to_dict()
            assert set(report.failures) == set(
                item["expected_baseline_failure_codes"]), report.to_dict()
        else:
            assert report.status == "PASS", report.to_dict()
    finally:
        try:
            # Cleanup only this run's owned preview, including after assertion failure.
            for report in reports + [processor.last_quality_report]:
                if report is not None:
                    _cleanup_quality_preview(report.preview_file)
        finally:
            assert {path: _identity(
                path) for path in sources} == before, "Source file identity changed"
