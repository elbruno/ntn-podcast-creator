"""Explicit settings saves are validated transactions; reads never migrate disk."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import Mock

import pytest

from features import config_manager as config_module
from features.audio_quality import AudioQualityConfig
from features.config_manager import ConfigManager


@pytest.fixture
def manager(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "background_volume": 12,
        "target_lufs": -14,
        "audio_quality": {"window_ms": 750, "future_threshold": {"value": 1}},
        "future_setting": {"items": [1, 2]},
    }), encoding="utf-8")
    return ConfigManager(str(path))


def test_missing_file_defaults_do_not_write(tmp_path):
    path = tmp_path / "config.json"
    manager = ConfigManager(str(path))
    snapshot = manager.snapshot()
    assert snapshot == manager._default_config()
    assert snapshot["delete_voice"] is True
    assert snapshot["trim_silence"] is True
    assert snapshot["audio_quality"] == asdict(AudioQualityConfig())
    assert not path.exists()


@pytest.fixture
def audio_library(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    library = {}
    for key, directory in (("intro_file", "intro_audio"),
                           ("outro_file", "outro_audio"),
                           ("background_tracks", "background_music")):
        folder = tmp_path / "audios" / directory
        folder.mkdir(parents=True)
        paths = []
        for name in ("default.mp3", "alternative.wav"):
            path = folder / name
            path.write_bytes(b"dummy audio; discovery does not decode files")
            paths.append(str(path.relative_to(tmp_path)))
        library[key] = paths
    return library


@pytest.mark.parametrize("initial", [None, "{}", "{broken json"])
def test_audio_discovery_initializes_unconfigured_assets(tmp_path, audio_library, initial):
    path = tmp_path / "config.json"
    if initial is not None:
        path.write_text(initial, encoding="utf-8")
    manager = ConfigManager(str(path))
    manager.load_default_audio_files()
    expected = {key: paths if key == "background_tracks" else paths[0]
                for key, paths in audio_library.items()}
    assert {key: manager.get(key) for key in expected} == expected
    restarted = ConfigManager(str(path))
    restarted.load_default_audio_files()
    assert {key: restarted.get(key) for key in expected} == expected


@pytest.mark.parametrize("selection", ["disabled", "alternative", "unavailable"])
def test_saved_audio_selections_survive_startup(tmp_path, audio_library, selection):
    manager = ConfigManager(str(tmp_path / "config.json"))
    if selection == "disabled":
        settings = {"intro_file": None,
                    "outro_file": None, "background_tracks": []}
    else:
        settings = {key: paths[1:] if key == "background_tracks" else paths[1]
                    for key, paths in audio_library.items()}
        if selection == "unavailable":
            for paths in audio_library.values():
                (tmp_path / paths[1]).unlink()
    manager.update_settings(settings)
    saved_bytes = (tmp_path / "config.json").read_bytes()
    # Saving before the first discovery must also suppress discovery in memory.
    for current in (manager, ConfigManager(manager.config_file)):
        current.load_default_audio_files()
        assert {key: current.get(key) for key in settings} == settings
    assert (tmp_path / "config.json").read_bytes() == saved_bytes


@pytest.mark.parametrize("missing_key", ["intro_file", "outro_file", "background_tracks"])
def test_audio_discovery_only_fills_missing_saved_keys(tmp_path, audio_library, missing_key):
    path = tmp_path / "config.json"
    saved = {"intro_file": None, "outro_file": None, "background_tracks": [],
             "background_volume": 23, "future_setting": {"keep": True}}
    del saved[missing_key]
    path.write_text(json.dumps(saved), encoding="utf-8")
    manager = ConfigManager(str(path))
    # Merged snapshot defaults must not mask the missing raw config key.
    manager.snapshot()
    manager.load_default_audio_files()
    paths = audio_library[missing_key]
    expected = dict(
        saved, **{missing_key: paths if missing_key == "background_tracks" else paths[0]})
    assert manager.config == expected
    restarted = ConfigManager(str(path))
    restarted.load_default_audio_files()
    assert restarted.config == expected


@pytest.mark.parametrize("remove_all", [False, True])
def test_removed_background_tracks_stay_removed_without_deleting_files(
        tmp_path, audio_library, remove_all):
    manager = ConfigManager(str(tmp_path / "config.json"))
    manager.load_default_audio_files()
    tracks = audio_library["background_tracks"]
    for track in tracks if remove_all else tracks[:1]:
        manager.remove_background_track(track)
    expected = [] if remove_all else tracks[1:]
    restarted = ConfigManager(manager.config_file)
    restarted.load_default_audio_files()
    assert restarted.get_background_tracks() == expected
    assert all((tmp_path / track).is_file() for track in tracks)


def test_audio_discovery_without_files_does_not_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "config.json"
    manager = ConfigManager(str(path))
    manager.load_default_audio_files()
    assert manager.snapshot() == manager._default_config()
    assert manager.get_intro() is None
    assert manager.get_outro() is None
    assert manager.get_background_tracks() == []
    assert not path.exists()


def test_old_config_defaults_merge_without_migration(manager):
    before = deepcopy(manager.config)
    path = config_module.os.fspath(manager.config_file)
    with open(path, "rb") as source:
        original_bytes = source.read()
    snapshot = manager.snapshot()
    assert snapshot["delete_voice"] is True
    assert snapshot["trim_silence"] is True
    assert snapshot["background_volume"] == 12
    assert snapshot["audio_quality"]["window_ms"] == 750
    assert snapshot["audio_quality"]["vmr_failure_db"] == 8
    assert snapshot["future_setting"] == {"items": [1, 2]}
    assert manager.config == before
    with open(path, "rb") as source:
        assert source.read() == original_bytes


@pytest.mark.parametrize("quality", [None, [], "bad", {
    "window_ms": "broken", "target_lufs": None,
}])
def test_snapshot_preserves_invalid_saved_values(tmp_path, quality):
    path = tmp_path / "config.json"
    raw = {"denoise_audio": "false", "background_volume": 500,
           "trim_silence": None, "audio_quality": quality}
    path.write_text(json.dumps(raw), encoding="utf-8")
    manager = ConfigManager(str(path))
    snapshot = manager.snapshot()
    assert snapshot["denoise_audio"] == "false"
    assert snapshot["background_volume"] == 500
    assert snapshot["trim_silence"] is None
    if isinstance(quality, dict):
        assert snapshot["audio_quality"]["window_ms"] == "broken"
        assert snapshot["audio_quality"]["target_lufs"] is None
    else:
        assert snapshot["audio_quality"] == quality
    assert manager.config == raw
    assert json.loads(path.read_text(encoding="utf-8")) == raw


def test_snapshots_are_deep_copies_and_remain_stable(manager):
    first = manager.snapshot()
    original = deepcopy(first)
    other = manager.snapshot()
    other["background_tracks"].append("other.wav")
    other["track_volumes"]["other.wav"] = 25
    other["audio_quality"]["future_threshold"]["value"] = 2
    other["future_setting"]["items"].append(3)
    assert manager.snapshot() == original
    manager.update_settings({"background_volume": 30})
    assert first == original


def test_batch_writes_once_after_validation_and_before_memory_commit(manager, monkeypatch):
    before = deepcopy(manager.config)
    original_replace = config_module.os.replace
    original_dump = config_module.json.dump
    dump = Mock(wraps=original_dump)
    legacy_save = Mock(side_effect=AssertionError("must not use legacy save"))

    def replace(source, destination):
        assert manager.config == before
        assert config_module.os.path.dirname(
            source) == config_module.os.path.dirname(destination)
        with open(source, encoding="utf-8") as staged:
            assert json.load(staged)["background_volume"] == 25
        original_replace(source, destination)

    replacement = Mock(side_effect=replace)
    monkeypatch.setattr(config_module.json, "dump", dump)
    monkeypatch.setattr(config_module.os, "replace", replacement)
    monkeypatch.setattr(manager, "save_config", legacy_save)
    incoming = {"background_volume": 25, "track_volumes": {"missing.wav": 0},
                "background_tracks": ["missing.wav"], "intro_file": "missing-intro.wav",
                "outro_file": None, "target_lufs": -14, "delete_voice": False,
                "trim_silence": False, "audio_quality": {"ducking_attack_ms": 75}}
    manager.update_settings(incoming)
    assert dump.call_count == replacement.call_count == 1
    legacy_save.assert_not_called()
    saved = ConfigManager(manager.config_file).snapshot()
    assert saved == manager.snapshot()
    assert saved["audio_quality"]["window_ms"] == 750
    assert saved["audio_quality"]["ducking_attack_ms"] == 75
    assert saved["audio_quality"]["target_lufs"] == -14
    assert saved["future_setting"] == before["future_setting"]
    assert saved["audio_quality"]["future_threshold"] == {"value": 1}
    incoming["track_volumes"]["missing.wav"] = 50
    incoming["background_tracks"].clear()
    incoming["audio_quality"]["ducking_attack_ms"] = 900
    assert manager.snapshot() == saved


def test_all_default_keys_can_be_saved(tmp_path):
    manager = ConfigManager(str(tmp_path / "config.json"))
    settings = manager.snapshot()
    settings.update(active_template="Weekly", last_output_name="episode",
                    rss_feed_url="  custom feed  ", intro_file="intro.wav",
                    outro_file="outro.wav", background_volume=50,
                    track_volumes={"track.wav": 50}, background_tracks=["track.wav"],
                    min_voice_music_separation_db=0)
    manager.update_settings(settings)
    assert manager.snapshot() == settings
    manager.update_settings({"active_template": None, "intro_file": None,
                             "rss_feed_url": "", "last_output_name": ""})
    assert manager.snapshot()["rss_feed_url"] == ""


@pytest.mark.parametrize("key,choices", [
    ("denoise_method", ["audio_denoiser", "spectral", "rnnoise"]),
    ("voice_enhancement_preset", ["podcast", "light", "aggressive"]),
    ("whisper_model", ["tiny", "base", "small", "medium", "large"]),
    ("target_lufs", [-70, -5, -14]),
    ("background_volume", [0, 50, 12.5]),
    ("music_seed", [-(2**53 - 1), 0, 2**53 - 1]),
])
def test_valid_choices_and_boundaries(manager, key, choices):
    for value in choices:
        manager.update_settings({key: value})
        assert manager.snapshot()[key] == value


@pytest.mark.parametrize("settings", [
    None, [], "settings", {"unknown_setting": True}, {"future_setting": {}},
    {"denoise_method": "other"}, {"denoise_method": []},
    {"voice_enhancement_preset": "other"}, {"whisper_model": "other"},
    {"rss_feed_url": None}, {"rss_feed_url": 3}, {"last_output_name": []},
    {"active_template": False}, {"intro_file": 1}, {"outro_file": []},
    {"background_tracks": "track.wav"}, {"background_tracks": [None]},
    {"background_tracks": ("track.wav",)}, {"track_volumes": []},
    {"track_volumes": {1: 5}}, {"track_volumes": {"track.wav": -1}},
    {"track_volumes": {"track.wav": 51}}, {
        "track_volumes": {"track.wav": True}},
    {"track_volumes": {"track.wav": "5"}},
    {"track_volumes": {"track.wav": float("inf")}},
    {"background_volume": -1}, {"background_volume": 51},
    {"background_volume": True}, {"background_volume": "10"},
    {"background_volume": float("nan")}, {"target_lufs": -71},
    {"target_lufs": -4}, {"target_lufs": float("inf")},
    {"target_lufs": "-14"}, {"target_lufs": False},
    {"target_lufs": 10**400}, {"min_voice_music_separation_db": -1},
    {"min_voice_music_separation_db": float("nan")},
    {"min_voice_music_separation_db": "18"}, {"music_seed": True},
    {"music_seed": 1.0}, {"music_seed": 1.5}, {"music_seed": "1"},
    {"music_seed": 2**53}, {"music_seed": -(2**53)},
    {"audio_quality": []}, {"audio_quality": None},
    {"audio_quality": {"unknown": 1}},
    {"audio_quality": {"future_threshold": 1}},
    {"audio_quality": {"window_ms": {"value": 500}}},
    {"audio_quality": {"window_ms": "500"}},
    {"audio_quality": {"window_ms": None}},
    {"audio_quality": {"window_ms": True}},
    {"audio_quality": {"window_ms": 500.5}},
    {"audio_quality": {"window_ms": 0}},
    {"audio_quality": {"preview_seconds": float("nan")}},
    {"audio_quality": {"ducking_attack_ms": float("inf")}},
    {"audio_quality": {"vmr_failure_db": 40}},
])
def test_invalid_batch_leaves_memory_and_disk_unchanged(manager, monkeypatch, settings):
    before = deepcopy(manager.config)
    with open(manager.config_file, "rb") as source:
        original_bytes = source.read()
    write = Mock(side_effect=AssertionError("invalid batch must not write"))
    monkeypatch.setattr(manager, "_write_settings", write)
    if isinstance(settings, dict):
        settings = dict({"delete_voice": False}, **settings)
    with pytest.raises(ValueError):
        manager.update_settings(settings)
    assert manager.config == before
    with open(manager.config_file, "rb") as source:
        assert source.read() == original_bytes
    write.assert_not_called()


@pytest.mark.parametrize("invalid", ["false", "true", 0, 1, None, []])
def test_all_boolean_settings_require_actual_booleans(manager, invalid):
    before = deepcopy(manager.config)
    for key, default in manager._default_config().items():
        if isinstance(default, bool):
            with pytest.raises(ValueError, match=key):
                manager.update_settings({key: invalid})
            assert manager.config == before


def test_quality_target_follows_main_target_only_on_save(manager):
    assert manager.snapshot()["audio_quality"]["target_lufs"] == -16
    manager.update_settings({"audio_quality": {"target_lufs": -20}})
    assert manager.snapshot()["audio_quality"]["target_lufs"] == -14
    manager.update_settings(
        {"target_lufs": -18, "audio_quality": {"target_lufs": -12}})
    assert manager.snapshot()["audio_quality"]["target_lufs"] == -18
    manager.update_settings({"target_lufs": -16})
    assert manager.snapshot()["audio_quality"]["target_lufs"] == -16


def test_invalid_legacy_settings_can_be_explicitly_repaired(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"audio_quality": null, "background_volume": "bad"}', encoding="utf-8")
    manager = ConfigManager(str(path))
    with pytest.raises(ValueError):
        manager.update_settings({"background_volume": 10})
    assert manager.snapshot()["background_volume"] == "bad"
    manager.update_settings({"background_volume": 10, "audio_quality": {}})
    assert manager.snapshot() == manager._default_config()


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("failure_point", ["create", "dump", "fsync", "replace"])
def test_io_failure_is_atomic_and_cleans_up(tmp_path, monkeypatch, exists, failure_point):
    path = tmp_path / "config.json"
    original_bytes = b'{"background_volume":12}'
    if exists:
        path.write_bytes(original_bytes)
    manager = ConfigManager(str(path))
    before = deepcopy(manager.config)
    target, name = {
        "create": (config_module.tempfile, "NamedTemporaryFile"),
        "dump": (config_module.json, "dump"),
        "fsync": (config_module.os, "fsync"),
        "replace": (config_module.os, "replace"),
    }[failure_point]

    def fail(*args, **kwargs):
        if failure_point == "dump":
            args[1].write('{"partial":')
        raise OSError("injected failure")

    monkeypatch.setattr(target, name, fail)
    with pytest.raises(OSError, match="injected failure"):
        manager.update_settings(
            {"background_volume": 30, "delete_voice": False})
    assert manager.config == before
    if exists:
        assert path.read_bytes() == original_bytes
    else:
        assert not path.exists()
    assert list(tmp_path.iterdir()) == ([path] if exists else [])


@pytest.mark.parametrize("operation", ["snapshot", "update_settings", "set"])
def test_snapshot_batch_and_legacy_set_share_lock(manager, operation):
    started = threading.Event()
    finished = threading.Event()

    def worker():
        started.set()
        if operation == "snapshot":
            manager.snapshot()
        elif operation == "update_settings":
            manager.update_settings({"background_volume": 30})
        else:
            manager.set("background_volume", 30)
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with manager._lock:
            future = pool.submit(worker)
            assert started.wait(timeout=2)
            assert not finished.wait(timeout=0.05)
            assert manager.config["background_volume"] == 12
        future.result(timeout=2)
    assert finished.is_set()


def test_legacy_set_still_calls_save_without_arguments(manager, monkeypatch):
    save = Mock()
    monkeypatch.setattr(manager, "save_config", save)
    manager.set("legacy_unknown", "unvalidated")
    save.assert_called_once_with()
    assert manager.config["legacy_unknown"] == "unvalidated"


@pytest.mark.parametrize("enabled", [True, False])
def test_templates_carry_trim_and_delete(tmp_path, enabled):
    source = ConfigManager(str(tmp_path / "source.json"))
    source.update_settings({"delete_voice": enabled, "trim_silence": enabled})
    template = source.get_template_settings()
    assert template["delete_voice"] is enabled
    assert template["trim_silence"] is enabled
    target = ConfigManager(str(tmp_path / "target.json"))
    target.apply_template_settings(template)
    reloaded = ConfigManager(target.config_file).snapshot()
    assert reloaded["delete_voice"] is enabled
    assert reloaded["trim_silence"] is enabled


def test_old_templates_preserve_trim_and_delete_defaults(manager):
    template = manager.get_template_settings()
    assert template["delete_voice"] is True
    assert template["trim_silence"] is True
    manager.apply_template_settings({"background_volume": 10})
    assert manager.snapshot()["delete_voice"] is True
    assert manager.snapshot()["trim_silence"] is True
    manager.update_settings({"delete_voice": False, "trim_silence": False})
    manager.apply_template_settings({"background_volume": 15})
    assert manager.snapshot()["delete_voice"] is False
    assert manager.snapshot()["trim_silence"] is False


@pytest.mark.parametrize("key", ["trim_silence", "delete_voice"])
def test_invalid_new_template_toggle_does_not_partially_apply(manager, key):
    before = deepcopy(manager.config)
    with pytest.raises(ValueError, match=key):
        manager.apply_template_settings(
            {"background_volume": 25, key: "false"})
    assert manager.config == before
