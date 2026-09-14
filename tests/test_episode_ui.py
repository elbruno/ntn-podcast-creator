"""Episode-first UI contracts using a real Gradio component/event tree."""

import ast
import asyncio
import inspect
import json
from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_quality_ui import ui, make_report, save_report, handler_args


@pytest.fixture
def screen(ui):
    blocks = ui.create_ui()
    yield blocks
    blocks.close()


def handlers(screen):
    return {entry.fn.__name__: entry for entry in screen.fns.values() if entry.fn}


def ancestors(screen):
    parents = {}

    def visit(node, chain):
        parents[node["id"]] = chain
        for child in node.get("children", []):
            visit(child, chain + [node["id"]])

    visit(screen.config["layout"], [])
    return parents


def test_two_primary_tabs_and_actual_parent_membership(ui, screen):
    components = screen.config["components"]
    tabs = [c for c in components if c["type"] == "tabitem"]
    assert [(c["props"]["label"], c["props"]["id"]) for c in tabs] == [
        ("Create Episode", "create"), ("Settings", "settings")]
    create, settings = [c["id"] for c in tabs]
    parents = ancestors(screen)
    nodes = {c["id"]: c for c in components}
    for label in ("Upload recordings", "Episode name", "Recording order", "Your episode"):
        node = next(c for c in components if c["props"].get("label") == label)
        assert create in parents[node["id"]
                                 ] and settings not in parents[node["id"]]
    save = handlers(screen)["save_episode_settings"]
    assert len(save.inputs) == len(ui.SETTINGS_FIELDS) + 1
    for component in save.inputs[:-1]:
        assert settings in parents[component._id]
    for label in ("Tools", "Help & appearance", "Theme", "Templates & settings files"):
        node = next(c for c in components if c["props"].get("label") == label)
        assert settings in parents[node["id"]]
        if node["type"] == "accordion":
            assert node["props"]["open"] is False
    background = next(c for c in components if c["props"].get(
        "label") == "Per-recording background")
    assert any(nodes[p]["props"].get(
        "label") == "Episode options" for p in parents[background["id"]] if p in nodes)


def test_idle_sentinels_empty_results_and_css_contract(ui, screen):
    # Gradio Group does not emit elem_id/elem_classes in the browser. State
    # containers must be Columns (or another real DOM-emitting layout).
    for component in screen.config["components"]:
        props = component["props"]
        if props.get("elem_id") in {"episode-order", "episode-results", "episode-qc-actions"} or "available-only" in (props.get("elem_classes") or []):
            assert component["type"] == "column"
    by_label = {c["props"].get("label"): c["props"]
                for c in screen.config["components"]}
    assert by_label["Episode name"]["interactive"] is False
    assert by_label["Your episode"]["interactive"] is False
    assert by_label["Your episode"].get("value") is None
    for label in ("Episode options", "Timeline & premix details", "Technical details"):
        assert by_label[label]["open"] is False
    assert '#episode-results:not(:has([data-state="ready"]))' in ui.EPISODE_CSS
    assert '#episode-create:not(:has(#upload-state [data-state="multiple"])) #episode-order' in ui.EPISODE_CSS
    assert '.available-only:not(:has([data-state="available"]))' in ui.EPISODE_CSS
    tree = ast.parse(inspect.getsource(ui.create_ui))
    assert not any(isinstance(n, ast.keyword) and n.arg ==
                   "visible" for n in ast.walk(tree))
    assert "gr.update" not in inspect.getsource(ui.create_ui)
    assert "<script>" not in inspect.getsource(ui.create_ui)
    assert all("position: fixed" not in value for value in (
        ui.get_progress_html(.2, "<script>"), ui.get_bottom_console_html("<script>"), ui.EPISODE_CSS))
    assert "&lt;script&gt;" in ui.get_bottom_console_html("<script>")
    assert "<details" in ui.get_bottom_console_html("log")


def test_settings_accordion_membership_and_form_order(ui, screen):
    groups = {
        "Podcast sound": ("intro_file", "outro_file", "background_tracks", "background_volume",
                          "intro_voice_overlap", "voice_outro_overlap"),
        "Voice processing": ("trim_silence", "denoise_audio", "enhance_voice",
                             "auto_balance_levels", "auto_ducking"),
        "Output & quality": ("normalize_lufs", "target_lufs", "quality_gate_enabled",
                             "generate_transcript", "delete_voice"),
        "Naming & RSS": ("prioritize_recording_filename", "rss_feed_url"),
        "Advanced": ("denoise_method", "voice_enhancement_preset", "whisper_model",
                     "min_voice_music_separation_db", "audio_quality", "music_seed"),
    }
    fields = [key for keys in groups.values() for key in keys]
    assert len(fields) == len(set(fields)) == len(ui.SETTINGS_FIELDS)
    assert set(fields) == set(ui.SETTINGS_FIELDS)
    parents = ancestors(screen)
    accordions = {c["props"]["label"]: c for c in screen.config["components"]
                  if c["type"] == "accordion"}
    form = handlers(screen)["save_episode_settings"].inputs[:-1]
    for key, component in zip(ui.SETTINGS_FIELDS, form):
        group = next(name for name, keys in groups.items() if key in keys)
        assert accordions[group]["id"] in parents[component._id]
        assert accordions[group]["props"]["open"] is (group == "Podcast sound")
    # The visual order differs, but all event arrays still use SETTINGS_FIELDS.
    assert [component.label for component in form] == [
        "Default intro", "Default outro", "Background tracks", "Master background level (%)",
        "Delete voice recording after creation", "Trim silence from voice recording",
        "Prefer Recording.m4a first", "RSS Feed URL", "Intro-voice overlap (1 second)",
        "Voice-outro overlap (1 second)", "Enable noise reduction", "Noise Reduction Method",
        "Enable professional voice enhancement", "Enhancement Preset",
        "Normalize audio to professional LUFS level", "Target LUFS Level",
        "Auto-balance voice & music levels (Recommended)", "Minimum voice/music separation (dB)",
        "Auto-ducking", "Generate transcript with Whisper AI", "Whisper Model",
        "Final Audio Quality Gate", "Audio quality thresholds (JSON)", "Music seed",
    ]


def test_library_choices_filter_files_and_keep_external_selections(ui):
    extensions = (".mp3", ".wav", ".m4a", ".ogg", ".flac",
                  ".aac", ".aiff", ".wma", ".MP3")
    libraries = []
    for folder in ("intro_audio", "outro_audio", "background_music"):
        directory = Path("audios") / folder
        paths = [directory / ("track" + extension) for extension in extensions]
        for path in paths:
            path.write_bytes(b"audio")
        (directory / "README.md").write_text("not audio")
        (directory / "directory.wav").mkdir()
        external = Path(folder + "_external.wav").resolve()
        external.write_bytes(b"audio")
        libraries.append({str(path) for path in paths} | {str(external)})
    intro, outro, background = libraries
    ui.config_manager.update_settings({
        "intro_file": str(Path("intro_audio_external.wav").resolve()),
        "outro_file": str(Path("outro_audio_external.wav").resolve()),
        "background_tracks": sorted(background | {"audios/background_music/README.md",
                                                  "audios/background_music/directory.wav"}),
    })
    before = ui.config_manager.snapshot()
    blocks = ui.create_ui()
    try:
        components = {c.label: c for c in blocks.blocks.values()
                      if hasattr(c, "label")}
        for label, expected in zip(("Default intro", "Default outro", "Fine-tune selected track"), libraries):
            assert {value for _,
                    value in components[label].choices if value} == expected
        refreshed = handlers(blocks)["refresh_asset_controls"].fn()
        for update, expected in zip((refreshed[0], refreshed[2], refreshed[5]), libraries):
            assert {value for _, value in update.choices if value} == expected
        assert [refreshed[0].value, refreshed[2].value] == [
            before["intro_file"], before["outro_file"]]
        assert refreshed[4].value == before["background_tracks"]
        assert ui.config_manager.snapshot() == before
    finally:
        blocks.close()


@pytest.mark.parametrize("kind,remove", [("intro", False), ("outro", False),
                                         ("background", False), ("background", True), ("intro", None)])
def test_library_updates_preserve_default_drafts(ui, kind, remove):
    from gradio.state_holder import SessionState

    selections = []
    for folder in ("intro_audio", "outro_audio"):
        external = Path(folder + "_saved.wav").resolve()
        external.write_bytes(b"audio")
        selections.append(str(external))
        directory = Path("audios") / folder
        (directory / "draft.wav").write_bytes(b"draft")
        (directory / "README.md").write_text("not audio")
        (directory / "directory.wav").mkdir()
    music = Path("external_music.wav").resolve()
    music.write_bytes(b"audio")
    (Path("audios/background_music") / "README.md").write_text("not audio")
    (Path("audios/background_music") / "directory.wav").mkdir()
    ui.config_manager.update_settings({
        **dict(zip(("intro_file", "outro_file"), selections)),
        "background_tracks": [str(music), "audios/background_music/README.md",
                              "audios/background_music/directory.wav"],
    })
    blocks = ui.create_ui()
    try:
        action = handlers(blocks)["library_action"]
        asset = Path("new.wav")
        asset.write_bytes(b"audio")
        updates = action.fn(
            kind, str(asset) if remove is not None else None, str(music), bool(remove))
        assert ("failed" in updates[0]) is (remove is None)
        # Exercise Gradio's real wire update: no value key means the current
        # browser selection survives, including unsaved drafts and explicit None.
        wire = asyncio.run(blocks.postprocess_data(
            action, updates, SessionState(blocks)))
        for index, saved in enumerate(selections, start=2):
            assert wire[index]["__type__"] == "update"
            assert "value" not in wire[index]
            choices = {value for _, value in wire[index]["choices"]}
            assert saved in choices and None in choices
            assert not any(value and (value.endswith("README.md") or value.endswith("directory.wav"))
                           for value in choices)
            draft = f"audios/{'intro_audio' if index == 2 else 'outro_audio'}/draft.wav"
            for current in (saved, draft, None):
                assert current in choices
                assert dict(value=current, **wire[index])["value"] == current
            expected_music = set() if remove else {str(music)}
            if kind == "background" and remove is False:
                expected_music.add("audios/background_music/new.wav")
            assert {value for _, value in wire[4]["choices"]} == expected_music
            assert {value for _, value in wire[5]["choices"]} == (
                set() if remove else {str(music)})
            # Removing a library entry never deletes its file.
            assert music.is_file()
        assert [ui.config_manager.get(key) for key in (
            "intro_file", "outro_file")] == selections
    finally:
        blocks.close()


def test_no_scalar_autosave_and_wrapper_has_only_episode_inputs(ui, screen):
    functions = handlers(screen)
    form_ids = {c._id for c in functions["save_episode_settings"].inputs[:-1]}
    for dependency in screen.config["dependencies"]:
        if any(target[0] in form_ids and target[1] in {"change", "input"}
               for target in dependency["targets"]):
            assert screen.fns[dependency["id"]].fn.__name__ in {
                "<lambda>", "background_level_description", "stage_background_selection"}
    render = functions["create_episode_from_saved"]
    assert [c.label for c in render.inputs if hasattr(c, "label")] == [
        "Upload recordings", "Episode name", None, "Custom intro for this episode only"]
    assert not form_ids.intersection(c._id for c in render.inputs)
    assert len(render.outputs) == 7
    assert list(inspect.signature(ui.create_episode_from_saved).parameters) == [
        "voice", "name", "order", "intro_override", "progress"]
    assert render.concurrency_id == "episode-render" and render.concurrency_limit == 1


def test_upload_single_multiple_order_and_background_drafts(ui, monkeypatch):
    monkeypatch.setattr(ui, "get_audio_duration", lambda path: "01:23")
    first = ui.episode_upload_details(["a.wav"])
    assert 'data-state="single"' in first[-1]
    assert "a.wav · 01:23" in first[-2]
    assert first[0] == [[1, "a.wav", False]]
    enabled = ui.stage_episode_background([["a.wav", True]], first[0])
    assert enabled == [[1, "a.wav", True]] and first[0][0][2] is False
    rows, *_ = ui.episode_upload_details(["a.wav", "Recording.m4a"])
    assert rows[0][1] == "Recording.m4a"
    reordered, table, background = ui.stage_episode_order(
        [[2, "Recording.m4a"], [1, "a.wav"]], rows, ["a.wav", "Recording.m4a"])
    assert reordered == [[1, "a.wav", False], [2, "Recording.m4a", True]]
    assert table == [[1, "a.wav"], [2, "Recording.m4a"]]
    assert background == [["a.wav", False], ["Recording.m4a", True]]
    assert 'data-state="multiple"' in ui.episode_upload_details(
        ["a.wav", "b.wav"])[-1]
    assert 'data-state="empty"' in ui.episode_upload_details(None)[-1]


def capture_render(ui, monkeypatch):
    source = Path("Recording.wav").resolve()
    source.write_bytes(b"source")
    observed = {}
    monkeypatch.setattr(ui, "get_audio_duration_seconds", lambda path: 1)

    def process(**kwargs):
        observed.update(kwargs)
        Path(kwargs["output_file"]).write_bytes(b"export")
        return kwargs["output_file"], None, None

    monkeypatch.setattr(ui.audio_processor,
                        "create_podcast", process, raising=False)
    return str(source), observed


def test_saved_wrapper_ignores_drafts_and_freezes_every_setting(ui, monkeypatch):
    voice, observed = capture_render(ui, monkeypatch)
    saved = {"intro_file": "intro.wav", "outro_file": "outro.wav", "background_tracks": ["music.wav"],
             "track_volumes": {"music.wav": 12}, "background_volume": 14, "music_seed": 17,
             "min_voice_music_separation_db": 19, "quality_gate_enabled": True,
             "audio_quality": {"window_ms": 750}, "target_lufs": -15, "denoise_audio": False,
             "delete_voice": False, "trim_silence": False, "auto_balance_levels": False,
             "auto_ducking": False, "normalize_lufs": True, "enhance_voice": True,
             "voice_enhancement_preset": "light", "whisper_model": "small"}
    ui.config_manager.update_settings(saved)
    draft = list(ui.settings_form_values())
    draft[ui.SETTINGS_FIELDS.index("target_lufs")] = -20
    draft[-1]["music.wav"] = 49
    rows = [[1, "Recording.wav", True]]
    generator = ui.create_episode_from_saved(
        [voice], "episode", rows, None, progress=lambda *args: None)
    results = [next(generator)]
    rows[0][2] = False
    changed = dict(saved, intro_file="new.wav", outro_file=None, background_tracks=[], track_volumes={},
                   background_volume=1, music_seed=99, min_voice_music_separation_db=30,
                   quality_gate_enabled=False, audio_quality={"window_ms": 1000}, target_lufs=-20,
                   delete_voice=True, trim_silence=True, auto_balance_levels=True, auto_ducking=True)
    ui.config_manager.update_settings(changed)
    results.extend(generator)
    assert all(len(row) == 7 for row in results)
    assert Path("uploads/Recording.wav").exists()  # Frozen delete_voice=False.
    for processor_key, saved_key in {
        "intro_file": "intro_file", "outro_file": "outro_file", "background_files": "background_tracks",
        "track_volumes": "track_volumes", "background_volume": "background_volume", "music_seed": "music_seed",
        "min_voice_music_separation_db": "min_voice_music_separation_db", "target_lufs": "target_lufs",
        "trim_silence": "trim_silence", "denoise_audio": "denoise_audio", "normalize_lufs": "normalize_lufs",
        "auto_balance_levels": "auto_balance_levels", "auto_ducking": "auto_ducking",
        "enhance_voice_enabled": "enhance_voice", "voice_enhancement_preset": "voice_enhancement_preset",
        "whisper_model": "whisper_model", "quality_gate_enabled": "quality_gate_enabled",
    }.items():
        assert observed[processor_key] == saved[saved_key]
    assert observed["quality_config"].window_ms == 750
    assert observed["quality_config"].target_lufs == -15


def test_render_snapshot_and_quality_share_one_generation(ui, monkeypatch):
    voice, observed = capture_render(ui, monkeypatch)
    ui.config_manager.update_settings({"target_lufs": -15, "audio_quality": {"window_ms": 750},
                                       "music_seed": 17, "quality_gate_enabled": True, "delete_voice": False})
    original_snapshot = ui.saved_settings_snapshot
    original = original_snapshot()

    def snapshot_then_update():
        snapshot = original_snapshot()
        ui.config_manager.update_settings({"target_lufs": -20, "audio_quality": {"window_ms": 1000},
                                           "music_seed": 99, "quality_gate_enabled": False})
        return snapshot

    monkeypatch.setattr(ui, "saved_settings_snapshot", snapshot_then_update)
    snapshot = ui._render_snapshot()
    assert {key: snapshot[key] for key in original} == original
    assert snapshot["quality_config"].target_lufs == snapshot["target_lufs"] == -15
    assert snapshot["quality_config"].window_ms == snapshot["audio_quality"]["window_ms"] == 750
    assert ui.config_manager.get_target_lufs() == -20
    ui.config_manager.update_settings(original)
    list(ui.create_episode_from_saved(
        [voice], "episode", [], None, progress=lambda *args: None))
    assert observed["quality_config"].target_lufs == observed["target_lufs"] == -15
    assert observed["quality_config"].window_ms == 750
    assert observed["music_seed"] == 17 and observed["quality_gate_enabled"] is True


@pytest.mark.parametrize("background_enabled", [False, True])
def test_single_recording_background_override_reaches_processor(ui, monkeypatch, background_enabled):
    voice, observed = capture_render(ui, monkeypatch)
    ui.config_manager.update_settings(
        {"background_tracks": ["music.wav"], "delete_voice": False})
    list(ui.create_episode_from_saved([voice], "episode", [[1, "Recording.wav", background_enabled]], None,
                                      progress=lambda *args: None))
    assert observed["background_files"] == (
        ["music.wav"] if background_enabled else None)


def test_legacy_explicit_positional_choices_still_win(ui, monkeypatch):
    voice, observed = capture_render(ui, monkeypatch)
    ui.config_manager.update_settings(
        {"target_lufs": -19, "trim_silence": True, "denoise_audio": True})
    list(ui.create_podcast_handler_with_progress(
        *handler_args(voice), progress=lambda *args: None))
    assert observed["target_lufs"] == -14
    assert observed["trim_silence"] is False and observed["denoise_audio"] is False


def form_with(ui, **changes):
    values = list(ui.settings_form_values())
    for key, value in changes.items():
        values[ui.SETTINGS_FIELDS.index(key)] = value
    return values


def test_save_discard_and_session_track_drafts(ui, screen):
    before = ui.config_manager.snapshot()
    one = ui.stage_track_volume("music.wav", 22, {})
    two = ui.stage_track_volume("music.wav", 7, {})
    assert one != two and ui.config_manager.snapshot() == before
    values = form_with(ui, trim_silence=False, delete_voice=False, target_lufs=-14,
                       background_tracks=["music.wav"],
                       rss_feed_url="https://example.test/feed", prioritize_recording_filename=False,
                       audio_quality='{"window_ms":750}', music_seed=7)
    values[-1] = one
    assert "Settings saved" in ui.save_episode_settings(*values)[0]
    persisted = ui.ConfigManager().snapshot()
    assert persisted["track_volumes"] == one
    assert persisted["trim_silence"] is False and persisted["delete_voice"] is False
    assert persisted["audio_quality"]["target_lufs"] == -14
    discarded = ui.discard_episode_settings()
    assert discarded[2:] == ui.settings_form_values()
    assert len(discarded) == len(handlers(screen)[
        "discard_episode_settings"].outputs)
    assert persisted == ui.config_manager.snapshot()


def test_sound_controls_are_simple_previewable_and_use_chill_presets(ui, screen):
    components = {c["props"].get("label"): c["props"]
                  for c in screen.config["components"]}
    assert components["Background tracks"]["multiselect"] is True
    assert components["Preview intro"]["interactive"] is False
    assert components["Preview outro"]["interactive"] is False
    assert components["Preview track at this level"]["interactive"] is False
    assert components["Master background level (%)"]["step"] == 0.5
    assert "Chill" in ui.background_level_description(5)
    assert "-26 dB" in ui.background_level_description(5)
    labels = {c["props"].get("value") for c in screen.config["components"]
              if c["type"] == "button"}
    assert {"Barely audible · 2.5%", "Chill · 5%", "Present · 10%"} <= labels


@pytest.mark.parametrize("key,value", [
    ("delete_voice", "false"), ("trim_silence", 0), ("denoise_method", "bogus"),
    ("whisper_model", "bogus"), ("background_volume",
                                 51), ("target_lufs", float("nan")),
    ("music_seed", 1.5), ("music_seed", True), ("music_seed", 2**53),
    ("audio_quality", '{"unknown":4}'), ("audio_quality",
                                         '{"window_ms":true}'),
    ("audio_quality", '[]'), ("audio_quality", 'invalid'),
])
def test_save_invalid_scalar_or_quality_is_atomic(ui, key, value):
    ui.config_manager.update_settings({})
    before = ui.config_manager.snapshot()
    disk = Path("core/config.json").read_bytes()
    values = form_with(ui, background_volume=23, **
                       {key: value}) if key != "background_volume" else form_with(ui, background_volume=value)
    assert "not saved" in ui.save_episode_settings(*values)[0]
    assert ui.config_manager.snapshot() == before
    assert Path("core/config.json").read_bytes() == disk


def test_save_oserror_is_reported_without_mutation(ui, monkeypatch):
    ui.config_manager.update_settings({})
    before = ui.config_manager.snapshot()
    disk = Path("core/config.json").read_bytes()

    def fail(settings):
        raise OSError("read only disk")

    monkeypatch.setattr(ui.config_manager, "_write_settings", fail)
    assert "read only disk" in ui.save_episode_settings(
        *form_with(ui, background_volume=25))[0]
    assert ui.config_manager.snapshot() == before
    assert Path("core/config.json").read_bytes() == disk


def test_template_and_import_refresh_every_form_control(ui, screen):
    ui.save_episode_settings(*form_with(ui, delete_voice=False, trim_silence=False,
                                        whisper_model="medium", auto_ducking=False, music_seed=21,
                                        rss_feed_url="https://example.test/podcast", prioritize_recording_filename=False))
    expected = ui.settings_form_values()
    ui.save_template_handler("Saved")
    exported = ui.export_episode_settings()
    data = json.loads(Path(exported).read_text())
    assert set(ui.SETTINGS_FIELDS) | {
        "track_volumes", "background_tracks"} == set(data)
    ui.config_manager.update_settings(
        {"delete_voice": True, "trim_silence": True, "music_seed": 99})
    loaded = ui.load_episode_template("Saved")
    assert loaded[2:] == expected
    ui.config_manager.update_settings({"music_seed": 42})
    imported = ui.import_episode_settings(exported)
    assert imported[2:] == expected
    functions = handlers(screen)
    save_inputs = functions["save_episode_settings"].inputs
    for event in ("discard_episode_settings", "load_episode_template", "import_episode_settings", "suggested_episode_settings"):
        assert functions[event].outputs[2:] == save_inputs
        assert any(dep["trigger_after"] == functions[event]._id and
                   screen.fns[dep["id"]
                              ].fn.__name__ == "refresh_asset_controls"
                   for dep in screen.config["dependencies"])


def test_prepare_finish_reset_repeated_episodes_keep_exports_and_settings(ui, screen):
    functions = handlers(screen)
    report = make_report(ui, warnings=["SILENCE_TOO_LONG"])
    save_report(ui, report)
    saved = ui.config_manager.snapshot()
    for _ in range(2):
        prepare = functions["prepare_episode"]
        cleared = prepare.fn(None, False)
        assert len(cleared) == len(prepare.outputs)
        assert cleared[1:3] == (None, None)
        assert 'data-state="empty"' in cleared[0]
        with pytest.raises(ui.gr.Error):
            prepare.fn(None, True)
        finish = functions["finish_episode"]
        result = finish.fn(report.file_path, None, None, 0)
        assert len(result) == len(finish.outputs)
        assert result[1] == result[2] == report.file_path
        assert finish.outputs[2].__class__.__name__ == "DownloadButton"
        assert 'data-state="ready"' in result[0]
        assert 'data-state="warn"' in result[13]
        reset = functions["reset_episode"]
        cleared = reset.fn(None)
        assert len(cleared) == len(reset.outputs)
        by_component = dict(zip(reset.outputs, cleared))
        assert all(
            by_component[c] is None for c in functions["create_episode_from_saved"].outputs[1:4])
        assert cleared[1] is None and cleared[2] is None
        assert Path(report.file_path).exists()
        assert ui.config_manager.snapshot() == saved
    assert functions["finish_episode"].fn(None, None, None, 0)[
        1:3] == [None, None]


@pytest.mark.parametrize("state", ["pass", "warn", "fail", "disabled", "unavailable"])
def test_short_qc_and_conditional_actions_never_certify_disabled_or_unavailable(ui, screen, state):
    report = make_report(ui, failures=["MUSIC_MASKING_VOICE"] if state == "fail" else [],
                         warnings=["SILENCE_TOO_LONG"] if state == "warn" else [])
    if state == "unavailable":
        ui.save_render_quality_report(report.file_path, True, None, 10)
    else:
        save_report(ui, report, enabled=state != "disabled")
    short, sentinel = ui.episode_quality_summary(report.file_path)
    assert f'data-state="{state}"' in sentinel
    assert ("Ready to publish" in short) == (state == "pass")
    assert "<table" not in short and "score" not in short.lower()
    if state in {"warn", "fail"}:
        result = handlers(screen)["acknowledge_episode"].fn(
            report.file_path, 0)
        assert "acknowledged" in result[2]
        assert Path(report.file_path).exists()


def test_premix_only_alerts_on_problems(ui, monkeypatch):
    monkeypatch.setattr(ui, "preview_timeline", lambda *args: "timeline")
    for status, has_alert in (("optimal", False), ("warning", True), ("danger", True)):
        monkeypatch.setattr(ui.audio_processor, "analyze_levels", lambda *args,
                            **kwargs: {"overall_status": status}, raising=False)
        assert bool(ui.episode_premix(["Recording.wav"], [
                    [1, "Recording.wav", True]], None)[2]) is has_alert
    assert ui.episode_premix(None, [], None) == ("", "", "")
