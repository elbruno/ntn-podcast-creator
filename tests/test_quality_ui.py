"""QC UI regressions; run this file in isolation from legacy global ML stubs.

Real Gradio, report dataclasses and on-disk configuration are exercised. Only
the heavy processor/denoiser imports and network lookups are replaced.
"""

import ast
import importlib.util
import inspect
import json
import shutil
import sys
import tempfile
import threading
import types
from dataclasses import asdict, replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ui(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "core").mkdir()
    from features.config_manager import ConfigManager
    from features import audio_processor as real_processor
    processor_module = types.ModuleType("features.audio_processor")
    processor_module.AudioProcessor = type("AudioProcessor", (), {})
    for name in ("_quality_file_identity", "_quality_preview_identity",
                 "_register_quality_preview", "_cleanup_quality_preview",
                 "_read_quality_sidecar", "_write_quality_sidecar"):
        setattr(processor_module, name, getattr(real_processor, name))
    denoiser_module = types.ModuleType("features.audio_denoiser_processor")
    denoiser_module.denoise_audio_file = lambda *args, **kwargs: None
    monkeypatch.setitem(
        sys.modules, "features.audio_processor", processor_module)
    monkeypatch.setitem(
        sys.modules, "features.audio_denoiser_processor", denoiser_module)
    spec = importlib.util.spec_from_file_location(
        "_quality_ui_under_test", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "fetch_rss_episode_info",
                        lambda *args, **kwargs: (None, None, None))
    return module


def make_report(ui, **kwargs):
    path = Path("outputs/episode.mp3").resolve()
    path.write_bytes(b"test render")
    return ui.AudioQualityReport(file_path=str(path), analysis_complete=True, **kwargs)


def save_report(ui, report, enabled=True, started_ns=10):
    ui.save_render_quality_report(
        report.file_path, enabled, report, started_ns)
    return Path(report.file_path + ".quality.json")


@pytest.mark.parametrize("thresholds,seed", [
    ("[]", 0), ("not JSON", 0), ('{"window_ms":0}', 0),
    ('{"window_ms":true}', 0), ('{"vmr_failure_db":30}', 0),
    ('{"vmr_warnng_db":10}', 0), ('{"preview_seconds":NaN}', 0),
    ("{}", 1.5), ("{}", float("inf")), ("{}", True), ("{}", 2**53),
])
def test_settings_invalid_without_partial_save(ui, thresholds, seed):
    before = dict(ui.config_manager.config)
    message = ui.save_quality_settings(True, thresholds, seed)
    assert "not saved" in message
    assert ui.config_manager.config == before


def test_settings_persist_and_lufs_slider_wins(ui):
    ui.config_manager.set_target_lufs(-14)
    message = ui.save_quality_settings(
        True, '{"window_ms":750,"target_lufs":-20}', 37)
    assert "saved" in message and "LUFS slider" in message
    persisted = ui.ConfigManager()
    assert persisted.get("audio_quality")["window_ms"] == 750
    assert persisted.get("audio_quality")["target_lufs"] == -14
    assert persisted.get("music_seed") == 37
    assert persisted.get("quality_gate_enabled") is True
    enabled, thresholds, seed = ui.quality_settings_values()
    assert enabled and seed == 37
    assert json.loads(thresholds) == asdict(
        ui.config_manager.get_audio_quality_config())


def test_checkbox_persists_independently(ui):
    assert "enabled" in ui.set_quality_gate_enabled(True)
    assert ui.ConfigManager().get("quality_gate_enabled") is True
    ui.set_quality_gate_enabled(False)
    assert ui.ConfigManager().get("quality_gate_enabled") is False


@pytest.mark.parametrize("raw", [{"window_ms": 0}, {"vmr_failure_db": 30}, ["broken"], "bad config"])
def test_invalid_saved_config_ui_starts_with_raw_json_for_repair(ui, raw):
    ui.config_manager.set("quality_gate_enabled", True)
    ui.config_manager.set("audio_quality", raw)
    before = Path("core/config.json").read_bytes()
    enabled, thresholds, _ = ui.quality_settings_values()
    assert enabled and json.loads(thresholds) == raw
    blocks = ui.create_ui()
    try:
        controls = {item["props"].get("label"): item["props"]
                    for item in blocks.config["components"]}
        assert json.loads(
            controls["Audio quality thresholds (JSON)"]["value"]) == raw
        assert controls["Final Audio Quality Gate"]["value"] is True
        assert Path("core/config.json").read_bytes() == before
        assert "Repair the raw JSON" in ui.get_console_log()
    finally:
        blocks.close()


def test_disabled_clears_previous_report_preview_and_download(ui):
    report = make_report(ui, failures=["MUSIC_MASKING_VOICE"])
    save_report(ui, report)
    sidecar = save_report(ui, report, enabled=False, started_ns=20)
    data = json.loads(sidecar.read_text())
    assert data["ui"]["enabled"] is False
    assert "report" not in data and "failures" not in data
    assert "analysis_complete" not in data and "metadata" not in data
    card, preview, download = ui.render_final_quality_inspector(
        report.file_path, 15)
    assert "disabled" in card and "MUSIC_MASKING_VOICE" not in card
    assert preview is None and download is None


def test_clear_before_render_and_missing_audio(ui):
    card, preview, download, action, stamp = ui.clear_final_quality_inspector()
    assert (card, preview, download, action) == ("", None, None, "")
    assert stamp > 0
    assert ui.render_final_quality_inspector(None) == ("", None, None)


@pytest.mark.parametrize("failure", ["missing", "malformed", "old_render", "replaced_audio", "wrong_path", "invalid_notes"])
def test_missing_or_stale_sidecar_never_certifies(ui, failure):
    report = make_report(ui)
    sidecar = save_report(ui, report)
    started = 0
    if failure == "missing":
        sidecar.unlink()
    elif failure == "malformed":
        sidecar.write_text("{broken", encoding="utf-8")
    elif failure == "old_render":
        started = 11
    elif failure == "replaced_audio":
        Path(report.file_path).write_bytes(b"different export")
    else:
        data = json.loads(sidecar.read_text())
        if failure == "wrong_path":
            data["file_path"] = "/etc/passwd"
        else:
            data["failures"] = "not a list"
        sidecar.write_text(json.dumps(data))
    card, preview, download = ui.render_final_quality_inspector(
        report.file_path, started)
    assert "QC unavailable" in card
    assert "Ready to publish" not in card
    assert preview is None and download is None


@pytest.mark.parametrize("status,color", [("PASS", "#059669"), ("WARN", "#d97706"), ("FAIL", "#dc2626")])
def test_final_report_colors_and_escaping(ui, status, color):
    report = make_report(ui, recommendations=['<script>alert("bad")</script>'])
    if status == "WARN":
        report.warnings = ["SILENCE_TOO_LONG"]
    elif status == "FAIL":
        report.failures = ["MUSIC_MASKING_VOICE"]
    report.worst_voice_music_ratio_db = 3.2
    save_report(ui, report)
    card, _, download = ui.render_final_quality_inspector(report.file_path)
    assert color in card and status in card
    assert "<script>" not in card and "&lt;script&gt;" in card
    assert "3.2" in card  # Stem metrics survive the sidecar round-trip.
    assert download.endswith(".quality.json")
    assert not Path(report.file_path + ".quality-ui.json").exists()


def test_enabled_without_report_is_not_pass(ui):
    report = make_report(ui)
    ui.save_render_quality_report(report.file_path, True, None, 10)
    card, preview, download = ui.render_final_quality_inspector(
        report.file_path)
    assert "QC unavailable" in card
    assert preview is None and download is None


def test_preview_requires_produced_receipt_and_unchanged_file(ui):
    report = make_report(ui)
    with tempfile.NamedTemporaryFile(prefix="audio_quality_preview_", suffix=".wav") as clip:
        clip.write(b"preview")
        clip.flush()
        report.preview_file = clip.name
        save_report(ui, report)
        assert ui.render_final_quality_inspector(report.file_path)[
            1] == clip.name
        Path(clip.name).write_bytes(b"replacement preview")
        assert ui.render_final_quality_inspector(report.file_path)[1] is None
    report.preview_file = report.file_path
    save_report(ui, report)
    assert ui.render_final_quality_inspector(report.file_path)[1] is None


def test_wrong_callback_report_cannot_be_saved(ui):
    report = make_report(ui)
    with pytest.raises(ValueError, match="different audio"):
        ui.save_render_quality_report("outputs/another.mp3", True, report, 10)


def test_override_acknowledgement_persists_without_erasing_failure(ui):
    report = make_report(ui, failures=["MUSIC_MASKING_VOICE"])
    sidecar = save_report(ui, report)
    before = json.loads(sidecar.read_text())
    card, message = ui.acknowledge_quality_override(report.file_path)
    after = json.loads(sidecar.read_text())
    assert after["ui"]["override"] is True
    before["ui"]["override"] = True
    assert after == before
    assert "FAIL" in card and "Override acknowledged" in card
    assert "QC remains FAIL" in message
    assert Path(report.file_path).read_bytes() == b"test render"


@pytest.mark.parametrize("matching", [True, False])
@pytest.mark.parametrize("callback", [True, False])
def test_save_uses_callback_metrics_and_only_matching_producer_metadata(ui, matching, callback):
    report = make_report(ui, failures=["MUSIC_MASKING_VOICE"])
    producer = report.to_dict()
    producer.update(schema="ntn-quality-v1", output_path=report.file_path,
                    identity=ui._quality_file_identity(report.file_path),
                    metadata={"music_seed": 19, "settings": {"normalize_lufs": False},
                              "selected_tracks": [{"path": "music.wav", "start_ms": 0}]})
    producer["failures"] = []  # Disk must not override callback findings.
    if not matching:
        producer["identity"]["size"] += 1
    sidecar = Path(report.file_path + ".quality.json")
    sidecar.write_text(json.dumps(producer))
    ui.save_render_quality_report(
        report.file_path, True, report if callback else None, 23)
    data = json.loads(sidecar.read_text())
    assert "report" not in data
    assert data["ui"] == {"identity": ui._quality_file_identity(report.file_path),
                          "started_ns": 23, "enabled": True,
                          "preview_identity": None, "override": False}
    if matching:
        assert data["metadata"] == producer["metadata"]
    else:
        assert "metadata" not in data
    if callback:
        assert data["failures"] == report.failures
        assert data["status"] == "FAIL"
    else:
        assert "analysis_complete" not in data
        assert "QC unavailable" in ui.render_final_quality_inspector(report.file_path)[
            0]


def test_clear_retires_session_preview_even_when_next_output_differs(ui):
    report = make_report(ui)
    with tempfile.NamedTemporaryFile(prefix="audio_quality_preview_", suffix=".wav", delete=False) as clip:
        clip.write(b"original preview")
    report.preview_file = clip.name
    save_report(ui, report)
    receipt = ui.remember_quality_preview(report.file_path)
    assert receipt["path"] == clip.name
    try:
        assert ui.clear_final_quality_inspector(
            receipt)[:4] == ("", None, None, "")
        assert not Path(clip.name).exists()
        other = Path("outputs/other.mp3").resolve()
        other.write_bytes(b"next output")
        assert ui.remember_quality_preview(str(other)) is None
    finally:
        Path(clip.name).unlink(missing_ok=True)


@pytest.mark.parametrize("unsafe", ["outside", "prefix", "symlink", "replaced", "bare"])
def test_clear_never_deletes_unowned_or_replaced_previews(ui, unsafe, tmp_path):
    with tempfile.NamedTemporaryFile(prefix="audio_quality_preview_", suffix=".wav", delete=False) as clip:
        clip.write(b"preview")
    path = Path(clip.name)
    try:
        if unsafe == "outside":
            path = tmp_path / path.name
            path.write_bytes(b"outside temp root")
        elif unsafe == "prefix":
            path = Path(clip.name + ".unowned.wav")
            path.write_bytes(b"wrong suffix")
            # A non-QC prefix even though the file is in the temp directory.
            renamed = path.with_name("not_qc_" + path.name)
            path.rename(renamed)
            path = renamed
        elif unsafe == "symlink":
            path = Path(clip.name + "_link.wav")
            path.symlink_to(clip.name)
        receipt = {"path": str(
            path), "identity": ui._quality_file_identity(path)}
        if unsafe == "replaced":
            path.write_bytes(b"changed preview")
        ui.clear_final_quality_inspector(
            str(path) if unsafe == "bare" else receipt)
        assert path.exists()
        assert Path(clip.name).exists()
    finally:
        path.unlink(missing_ok=True)
        Path(clip.name).unlink(missing_ok=True)


def test_missing_report_actions_do_not_change_settings(ui):
    report = make_report(ui)
    before = dict(ui.config_manager.config)
    _, message = ui.acknowledge_quality_override(report.file_path)
    assert "Cannot acknowledge" in message
    result = ui.apply_quality_suggested_settings(report.file_path)
    assert "not applied" in result[0]
    assert ui.config_manager.config == before


def test_suggested_settings_are_allowlisted_persisted_and_require_rerender(ui):
    for key in ("auto_balance_levels", "auto_ducking", "normalize_lufs"):
        ui.config_manager.set(key, False)
    report = make_report(ui, failures=["MUSIC_MASKING_VOICE", "LOUDNESS_TOO_LOW"],
                         recommendations=["Set denoise_audio to true; delete all sources"])
    sidecar = save_report(ui, report)
    before = sidecar.read_bytes()
    message, balance, ducking, normalize = ui.apply_quality_suggested_settings(
        report.file_path)
    assert balance and ducking and normalize
    persisted = ui.ConfigManager()
    assert all(persisted.get(key) for key in (
        "auto_balance_levels", "auto_ducking", "normalize_lufs"))
    assert "Rerender required" in message and "Re-upload" in message
    assert sidecar.read_bytes() == before
    assert Path(report.file_path).read_bytes() == b"test render"


def test_clipping_does_not_silently_enable_normalization(ui):
    ui.config_manager.set_normalize_lufs(False)
    report = make_report(ui, failures=["CLIPPING_DETECTED"])
    save_report(ui, report)
    message, _, _, normalize = ui.apply_quality_suggested_settings(
        report.file_path)
    assert not normalize and "cannot repair clipping" in message


def handler_args(voice, transcription=False):
    return [voice, "episode", False, False, False, "spectral", False,
            "podcast", False, -14, False, False, transcription, "base",
            False, False, None, None]


@pytest.mark.parametrize("enabled,transcription,callback", [(False, False, True), (True, False, True), (True, True, True), (True, False, False)])
def test_handler_snapshot_local_callback_and_seven_outputs(ui, monkeypatch, enabled, transcription, callback):
    source = Path("source.wav").resolve()
    source.write_bytes(b"source")
    ui.config_manager.set("quality_gate_enabled", enabled)
    ui.config_manager.set("music_seed", 17)
    ui.config_manager.set("audio_quality", {"window_ms": 750})
    monkeypatch.setattr(ui, "get_audio_duration_seconds", lambda path: 1)
    observed = {}
    transcribed = threading.Event()

    def process(**kwargs):
        observed.update(kwargs)
        Path(kwargs["output_file"]).write_bytes(b"export")
        report = ui.AudioQualityReport(file_path=kwargs["output_file"], analysis_complete=True,
                                       failures=["MUSIC_MASKING_VOICE"])
        if callback:
            kwargs["quality_report_callback"](report)
            report.failures.clear()  # Callback must have made its own copy.
        ui.audio_processor.last_quality_report = ui.AudioQualityReport(
            analysis_complete=True)
        return kwargs["output_file"], None, None

    monkeypatch.setattr(ui.audio_processor,
                        "create_podcast", process, raising=False)
    monkeypatch.setattr(ui.audio_processor, "transcribe_podcast",
                        lambda **kwargs: transcribed.set(), raising=False)
    generator = ui.create_podcast_handler_with_progress(*handler_args(str(source), transcription),
                                                        progress=lambda *args: None)
    results = [next(generator)]
    # Changes after first yield must not affect the in-flight render.
    ui.config_manager.set("quality_gate_enabled", not enabled)
    ui.config_manager.set("music_seed", 99)
    ui.config_manager.set("audio_quality", {"window_ms": 1000})
    results.extend(generator)
    assert all(len(row) == 7 for row in results)
    assert observed["quality_gate_enabled"] is enabled
    assert observed["music_seed"] == 17
    assert observed["quality_config"].window_ms == 750
    assert observed["quality_config"].target_lufs == -14
    assert observed["defer_transcription"] is True
    assert "Exported" in results[-1][0]
    if enabled:
        assert (
            "QC: FAIL" if callback else "QC: UNAVAILABLE") in results[-1][0]
    else:
        assert "QC:" not in results[-1][0]
        assert "disabled" in ui.render_final_quality_inspector(
            results[-1][1])[0]
    if transcription:
        assert transcribed.wait(2)


def test_handler_missing_source_and_processor_error_keep_contract(ui, monkeypatch):
    results = list(ui.create_podcast_handler_with_progress(
        *handler_args(None), progress=lambda *args: None))
    assert all(len(row) == 7 for row in results)
    assert results[-1][1] is None
    source = Path("source.wav")
    source.write_bytes(b"source")
    monkeypatch.setattr(ui, "get_audio_duration_seconds", lambda path: 1)

    def fail(**kwargs):
        raise RuntimeError("mix failed")

    monkeypatch.setattr(ui.audio_processor,
                        "create_podcast", fail, raising=False)
    results = list(ui.create_podcast_handler_with_progress(
        *handler_args(str(source)), progress=lambda *args: None))
    assert all(len(row) == 7 for row in results)
    assert "mix failed" in results[-1][0] and results[-1][1] is None


def test_positional_api_and_all_yield_expressions(ui):
    expected = ["voice_file", "output_name", "delete_voice", "trim_silence", "denoise_audio",
                "denoise_method", "enhance_voice", "voice_enhancement_preset", "normalize_lufs",
                "target_lufs", "intro_voice_overlap", "voice_outro_overlap", "generate_transcript",
                "whisper_model", "auto_balance_levels", "auto_ducking", "voice_order_table",
                "intro_override_file", "progress"]
    assert list(inspect.signature(
        ui.create_podcast_handler_with_progress).parameters) == expected
    node = ast.parse(inspect.getsource(
        ui.create_podcast_handler_with_progress))
    yields = [item for item in ast.walk(node) if isinstance(item, ast.Yield)]
    assert yields and all(isinstance(item.value, ast.Tuple) and len(
        item.value.elts) == 7 for item in yields)


def test_invalid_saved_config_cannot_certify_export(ui, monkeypatch):
    ui.config_manager.set("quality_gate_enabled", True)

    def invalid_config():
        raise ValueError("broken thresholds")

    monkeypatch.setattr(ui.config_manager,
                        "get_audio_quality_config", invalid_config)
    monkeypatch.setattr(ui, "get_audio_duration_seconds", lambda path: 1)
    source = Path("source.wav")
    source.write_bytes(b"source")

    def process(**kwargs):
        Path(kwargs["output_file"]).write_bytes(b"export")
        kwargs["quality_report_callback"](ui.AudioQualityReport(
            file_path=kwargs["output_file"], analysis_complete=True))
        return kwargs["output_file"], None, None

    monkeypatch.setattr(ui.audio_processor,
                        "create_podcast", process, raising=False)
    results = list(ui.create_podcast_handler_with_progress(
        *handler_args(str(source)), progress=lambda *args: None))
    assert "Exported" in results[-1][0] and "QC: FAIL" in results[-1][0]
    assert "INVALID_QUALITY_CONFIG" in ui.render_final_quality_inspector(
        results[-1][1])[0]


def test_real_processor_to_ui_report_roundtrip(ui, monkeypatch):
    """Small real render verifies callback, encoded-file QC and preview provenance."""
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the processor round-trip")
    from pydub.generators import Sine

    for name, symbol in (("noise_reducer", "reduce_noise"), ("voice_enhancer", "enhance_voice")):
        module = types.ModuleType("features." + name)
        setattr(module, symbol, lambda path, **kwargs: path)
        monkeypatch.setitem(sys.modules, "features." + name, module)
    spec = importlib.util.spec_from_file_location("features._quality_processor_under_test",
                                                  ROOT / "features/audio_processor.py")
    processor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(processor_module)
    ui.audio_processor = processor_module.AudioProcessor()
    ui.config_manager.set("quality_gate_enabled", True)
    source = Path("source.wav")
    with Sine(440).to_audio_segment(duration=3000).apply_gain(-18).export(source, format="wav"):
        pass
    results = list(ui.create_podcast_handler_with_progress(
        *handler_args(str(source)), progress=lambda *args: None))
    output = results[-1][1]
    assert output is not None and all(len(row) == 7 for row in results)
    card, preview, download = ui.render_final_quality_inspector(output)
    try:
        assert "QC unavailable" not in card
        assert preview is not None and Path(preview).is_file()
        receipt = json.loads(Path(download).read_text())
        assert receipt["integrated_lufs"] is not None
        assert receipt["voice_level_dbfs"] is not None
        assert receipt["analysis_complete"] is True
        assert "report" not in receipt
        assert receipt["identity"] == ui._quality_file_identity(output)
        assert receipt["ui"]["identity"] == receipt["identity"]
        assert receipt["ui"]["preview_identity"] == ui._quality_file_identity(
            preview)
        processor_sidecar = Path(output + ".quality.json")
        assert Path(download) == processor_sidecar.resolve()
        assert receipt["metadata"]["music_seed"] == 0
        assert receipt["metadata"]["settings"]["quality_config"]["target_lufs"] == -14
        assert receipt["metadata"]["mix_analysis_stage"] == "post_gain_post_duck_pre_master"
        assert not Path(output + ".quality-ui.json").exists()
    finally:
        if preview:
            Path(preview).unlink(missing_ok=True)


def test_real_gradio_ui_construction_and_event_chains(ui):
    blocks = ui.create_ui()
    components = blocks.config["components"]
    labels = {item["props"].get("label") for item in components}
    assert {"Final Audio Quality Gate", "Audio quality thresholds (JSON)", "Music seed",
            "Final Audio Quality Inspector", "Preview worst section",
            "Download quality report (JSON)"} <= labels
    functions = {entry.fn: entry for entry in blocks.fns.values()
                 if entry.fn is not None}
    render = functions[ui.create_podcast_handler_with_progress]
    assert len(render.outputs) == 7 and len(render.inputs) == 18
    assert len(functions[ui.clear_final_quality_inspector].outputs) == 5
    assert len(functions[ui.clear_final_quality_inspector].inputs) == 1
    assert functions[ui.clear_final_quality_inspector].inputs == functions[ui.remember_quality_preview].outputs
    assert len(functions[ui.render_final_quality_inspector].outputs) == 3
    dependencies = blocks.config["dependencies"]
    render_dep = next(
        item for item in dependencies if item["id"] == render._id)
    clear_dep = functions[ui.clear_final_quality_inspector]
    assert render_dep["trigger_after"] == clear_dep._id
    inspector = functions[ui.render_final_quality_inspector]
    inspect_dep = next(
        item for item in dependencies if item["id"] == inspector._id)
    assert inspect_dep["trigger_after"] == render._id
    assert functions[ui.apply_quality_suggested_settings].outputs[1:] == [
        component for label in ["Auto-balance voice & music levels (Recommended)", "Auto-ducking",
                                "Normalize audio to professional LUFS level"]
        for component in blocks.blocks.values() if getattr(component, "label", None) == label]
    blocks.close()


def test_prior_inspectors_receive_shared_thresholds(ui, monkeypatch):
    ui.config_manager.set("audio_quality", {"voice_optimal_max_dbfs": -12})
    observed = []
    monkeypatch.setattr(ui, "get_audio_duration_seconds", lambda path: 1)

    def analyze(*args, **kwargs):
        observed.append(kwargs["quality_config"])
        return None

    monkeypatch.setattr(ui.audio_processor,
                        "analyze_levels", analyze, raising=False)
    blocks = ui.create_ui()
    handlers = {entry.fn.__name__: entry.fn for entry in blocks.fns.values()
                if entry.fn is not None}
    handlers["update_on_voice_upload"](["voice.wav"], None)
    handlers["update_timeline_with_order_state"](["voice.wav"], "[]", None)
    assert len(observed) == 2
    assert all(cfg.voice_optimal_max_dbfs == -12 for cfg in observed)
    blocks.close()
