"""Portable first-run settings never replace an existing local configuration."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from features.config_manager import ConfigManager


def test_initial_settings_are_validated_and_persisted_once(tmp_path):
    path = tmp_path / "config.json"
    initial = tmp_path / "config.initial.json"
    initial.write_text(json.dumps({
        "intro_file": "audios/intro_audio/intro.mp3",
        "outro_file": None,
        "background_tracks": [],
        "background_volume": 5,
        "normalize_lufs": True,
        "target_lufs": -16,
    }), encoding="utf-8")
    manager = ConfigManager(str(path))
    assert manager.get_volume() == 5
    assert manager.get_normalize_lufs() is True
    assert manager.get_intro() == str(Path("audios") / "intro_audio" / "intro.mp3")
    assert manager.get_outro() is None
    assert manager.get_background_tracks() == []
    assert json.loads(path.read_text(encoding="utf-8")) == manager.snapshot()

    manager.update_settings({"background_volume": 9})
    before = path.read_bytes()
    initial.write_text('{"background_volume": 20}', encoding="utf-8")
    restarted = ConfigManager(str(path))
    assert restarted.get_volume() == 9
    assert path.read_bytes() == before


@pytest.mark.parametrize("local", [
    '{"intro_file": null, "outro_file": null, "background_tracks": []}',
    "{}",
    "{broken json",
])
def test_existing_configuration_never_reads_initial_settings(tmp_path, local):
    path = tmp_path / "config.json"
    path.write_text(local, encoding="utf-8")
    (tmp_path / "config.initial.json").write_text("{invalid seed", encoding="utf-8")
    before = path.read_bytes()
    ConfigManager(str(path))
    assert path.read_bytes() == before


@pytest.mark.parametrize("initial", [
    "{broken json",
    "[]",
    '{"unknown_setting": true}',
    '{"background_volume": "quiet"}',
    '{"audio_quality": {"window_ms": 0}}',
])
def test_invalid_initial_settings_fail_without_creating_local_file(tmp_path, initial):
    path = tmp_path / "config.json"
    (tmp_path / "config.initial.json").write_text(initial, encoding="utf-8")
    with pytest.raises(ValueError):
        ConfigManager(str(path))
    assert not path.exists()
    assert not list(tmp_path.glob(".config-*.tmp"))


def test_initial_settings_write_failure_is_explicit(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    (tmp_path / "config.initial.json").write_text(
        '{"background_volume": 5}', encoding="utf-8")
    monkeypatch.setattr(
        "features.config_manager.os.replace",
        Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        ConfigManager(str(path))
    assert not path.exists()
    assert not list(tmp_path.glob(".config-*.tmp"))


def test_unseeded_configuration_keeps_previous_behavior(tmp_path):
    path = tmp_path / "config.json"
    manager = ConfigManager(str(path))
    assert manager.snapshot() == manager._default_config()
    assert not path.exists()
    assert "intro_file" not in manager.config


def test_shipped_settings_and_library_are_portable(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    initial = root / "core" / "config.initial.json"
    settings = json.loads(initial.read_text(encoding="utf-8"))
    monkeypatch.chdir(root)
    (tmp_path / "config.initial.json").write_bytes(initial.read_bytes())
    manager = ConfigManager(str(tmp_path / "config.json"))
    assert set(settings) == set(manager._default_config())
    assert manager.snapshot() == manager._normalize_audio_settings(settings)
    assert manager.get_volume() == 5
    assert manager.get_target_lufs() == -16
    assert manager.get_generate_transcript() is False
    assert len(settings["background_tracks"]) == 6
    paths = [settings["intro_file"], settings["outro_file"],
             *settings["background_tracks"], *settings["track_volumes"]]
    for path in paths:
        assert path.startswith("audios/")
        assert "\\" not in path
        assert not Path(path).is_absolute()
        assert (root / path).is_file()
        assert (root / path).stat().st_size > 0
