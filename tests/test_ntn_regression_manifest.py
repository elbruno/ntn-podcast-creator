"""Manifest safety tests only; temporary bytes are NOT production audio fixtures."""

import copy
import json

import pytest

from tests.test_ntn_quality_regression import (
    EPISODES, _assert_complete_metrics, _load_manifest, validate_manifest,
)


@pytest.fixture
def manifest_inputs(tmp_path):
    root = tmp_path / "audio"
    root.mkdir()
    for name in ("recording-one.wav", "recording-two.m4a", "intro.wav", "outro.wav", "music.wav"):
        (root / name).write_bytes(b"validation only; not decodable audio")
    baseline = {
        "intro_file": "intro.wav", "outro_file": "outro.wav",
        "background_files": ["music.wav"], "background_segments": None,
        "background_volume": 10, "track_volumes": {"music.wav": 5},
        "trim_silence": False, "denoise_audio": False,
        "enhance_voice_enabled": False, "generate_transcript": False,
        "normalize_lufs": False, "target_lufs": -16,
        "intro_voice_overlap": True, "voice_outro_overlap": False,
        "auto_balance_levels": False, "min_voice_music_separation_db": 18,
        "auto_ducking": False, "music_seed": 7, "quality_config": {},
    }
    item = {
        "approved_for_testing": True, "originals_confirmed": True,
        "original_recordings": ["recording-two.m4a", "recording-one.wav"],
        "baseline_settings": baseline,
        "fixed_settings": dict(baseline, normalize_lufs=True, auto_balance_levels=True),
        # An arbitrary validator input, NOT an asserted NTN incident diagnosis.
        "expected_baseline_failure_codes": ["LOUDNESS_TOO_LOW"],
    }
    return root, {episode: copy.deepcopy(item) for episode in EPISODES}


def test_valid_manifest_preserves_order_settings_and_input_mapping(manifest_inputs):
    root, manifest = manifest_inputs
    before = copy.deepcopy(manifest)
    parsed = validate_manifest(manifest, root)
    assert manifest == before
    assert parsed["ntn567"]["original_recordings"] == [
        str(root / "recording-two.m4a"), str(root / "recording-one.wav")]
    assert parsed["ntn567"]["fixed_settings"]["track_volumes"] == {
        str(root / "music.wav"): 5}


def test_absolute_mounted_original_and_music_paths_are_supported(manifest_inputs, tmp_path):
    root, manifest = manifest_inputs
    mounted = tmp_path / "mounted-recording.wav"
    mounted.write_bytes(b"not production audio")
    manifest["ntn567"]["original_recordings"] = [str(mounted)]
    for key in ("baseline_settings", "fixed_settings"):
        manifest["ntn567"][key]["background_files"] = [str(root / "music.wav")]
    assert validate_manifest(manifest, root)[
        "ntn567"]["original_recordings"] == [str(mounted)]


@pytest.mark.parametrize("key,value", [
    ("output_file", "/do/not/overwrite.mp3"), ("voice_file", "final.mp3"),
    ("quality_gate_enabled", False), ("quality_report_callback", None),
    ("log_callback", None), ("denoise_method", "audio_denoiser"),
    ("generate_transcript", True), ("denoise_audio", True),
    ("enhance_voice_enabled", True), ("auto_ducking", "false"),
    ("background_volume", True), ("background_volume", 101),
    ("music_seed", False), ("target_lufs", float("nan")),
    ("quality_config", {"unknown": 1}), ("quality_config", {"window_ms": 0}),
    ("quality_config", {"target_lufs": -19}
     ), ("quality_config", {"window_ms": None}),
    ("background_segments", [[0, -1]]
     ), ("background_segments", [[False, 100]]),
    ("background_files", "music.wav"), ("track_volumes", {"intro.wav": 10}),
    ("min_voice_music_separation_db", -1),
])
def test_rejects_unsafe_or_invalid_settings(manifest_inputs, key, value):
    root, manifest = manifest_inputs
    manifest["ntn567"]["baseline_settings"][key] = value
    with pytest.raises(ValueError):
        validate_manifest(manifest, root)


@pytest.mark.parametrize("key", ["music_seed", "intro_file", "outro_file", "background_files",
                                 "target_lufs", "quality_config"])
def test_rejects_unmatched_pair_inputs_seed_or_thresholds(manifest_inputs, key):
    root, manifest = manifest_inputs
    replacements = {"music_seed": 8, "intro_file": None, "outro_file": None,
                    "background_files": ["music.wav", "intro.wav"], "target_lufs": -17,
                    "quality_config": {"loudness_failure_lu": 3}}
    manifest["ntn567"]["fixed_settings"][key] = replacements[key]
    with pytest.raises(ValueError, match="must share"):
        validate_manifest(manifest, root)


@pytest.mark.parametrize("path", ["../outside.wav", "missing.wav", "denoised.wav",
                                  "concatenated.mp3", "ntn567-fix.mp3", "final.mp3",
                                  "outputs/recording.wav", "c:\\od\\recording.wav"])
def test_rejects_nonoriginal_missing_and_unsafe_voice_paths(manifest_inputs, path):
    root, manifest = manifest_inputs
    if path not in ("missing.wav", "c:\\od\\recording.wav"):
        candidate = root / path
        candidate.parent.mkdir(exist_ok=True)
        candidate.write_bytes(b"not an original")
    manifest["ntn567"]["original_recordings"] = [path]
    with pytest.raises(ValueError):
        validate_manifest(manifest, root)


def test_rejects_relative_symlink_escape(manifest_inputs, tmp_path):
    root, manifest = manifest_inputs
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"outside")
    (root / "link.wav").symlink_to(outside)
    manifest["ntn567"]["original_recordings"] = ["link.wav"]
    with pytest.raises(ValueError, match="stay inside"):
        validate_manifest(manifest, root)


@pytest.mark.parametrize("codes", [None, [], [""], ["guessed code"], ["ANALYSIS_UNAVAILABLE"],
                                   ["MIX_ANALYSIS_UNAVAILABLE"], ["NO_VOICE", "NO_VOICE"]])
def test_failure_codes_must_be_explicit_signal_expectations(manifest_inputs, codes):
    root, manifest = manifest_inputs
    manifest["ntn567"]["expected_baseline_failure_codes"] = codes
    with pytest.raises(ValueError, match="explicit"):
        validate_manifest(manifest, root)


@pytest.mark.parametrize("change", ["episode", "approval", "provenance", "recordings", "duplicate",
                                    "setting", "identical", "duration", "unknown", "missing_codes"])
def test_rejects_incomplete_or_invalid_episode(manifest_inputs, change):
    root, manifest = manifest_inputs
    # Validate the other episode too, before any render.
    item = manifest["ntn568"]
    if change == "episode":
        del manifest["ntn568"]
    elif change == "approval":
        item["approved_for_testing"] = False
    elif change == "provenance":
        item["originals_confirmed"] = False
    elif change == "recordings":
        item["original_recordings"] = []
    elif change == "duplicate":
        item["original_recordings"] *= 2
    elif change == "setting":
        del item["fixed_settings"]["auto_ducking"]
    elif change == "identical":
        item["fixed_settings"] = copy.deepcopy(item["baseline_settings"])
    elif change == "duration":
        item["expected_original_duration_seconds"] = 0
    elif change == "unknown":
        item["render"] = "old-stem-contract.mp3"
    else:
        del item["expected_baseline_failure_codes"]
    with pytest.raises(ValueError):
        validate_manifest(manifest, root)


@pytest.mark.parametrize("segments", [None, [], [[0, 1000], [2000, 3000]]])
def test_accepts_explicit_selective_music_modes(manifest_inputs, segments):
    root, manifest = manifest_inputs
    manifest["ntn567"]["fixed_settings"]["background_segments"] = segments
    manifest["ntn567"]["expected_original_duration_seconds"] = 123.4
    parsed = validate_manifest(manifest, root)
    assert parsed["ntn567"]["fixed_settings"]["background_segments"] == segments


def test_only_absent_manifest_skips(tmp_path):
    with pytest.raises(pytest.skip.Exception, match="Original NTN"):
        _load_manifest(tmp_path / "manifest.json")


@pytest.mark.parametrize("content", ["{broken", "{}", '{"ntn567": {}, "ntn567": {}}'])
def test_configured_bad_json_fails_not_skips(tmp_path, content):
    path = tmp_path / "manifest.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        _load_manifest(path)


@pytest.mark.parametrize("asset", ["recording-one.wav", "intro.wav", "outro.wav", "music.wav"])
def test_configured_missing_asset_fails_not_skips(manifest_inputs, asset):
    root, manifest = manifest_inputs
    (root / asset).unlink()
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing"):
        _load_manifest(path)


def test_dangling_manifest_symlink_fails_not_skips(tmp_path):
    path = tmp_path / "manifest.json"
    path.symlink_to(tmp_path / "absent.json")
    with pytest.raises(FileNotFoundError):
        _load_manifest(path)


@pytest.mark.parametrize("music_ms", [0, 500, 2500, 5000])
def test_metric_assertions_handle_music_coverage_at_quantile_boundaries(music_ms):
    # Synthetic, in-memory assertion-helper test, never an NTN render/fixture.
    from pydub.generators import Sine
    from features.audio_quality import AudioQualityAnalyzer

    voice = Sine(440).to_audio_segment(duration=5000).apply_gain(-20)
    music = Sine(220).to_audio_segment(
        duration=music_ms).apply_gain(-40) if music_ms else None
    report = AudioQualityAnalyzer().analyze_mix(voice, music, offset_seconds=0.2)
    # Stand-ins for final-file fields: this unit test only checks nullability,
    # not mastering correctness (covered separately by real pipeline tests).
    report.integrated_lufs = -16.0
    report.true_peak_dbtp = -2.0
    report.clipped_samples = 0
    report.clipped_percentage = 0.0
    report.longest_silence_seconds = 0.0
    _assert_complete_metrics(report)
    report.integrated_lufs = None
    with pytest.raises(AssertionError):
        _assert_complete_metrics(report)
