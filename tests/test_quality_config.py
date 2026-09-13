"""Shared thresholds persist without requiring migration of old configs."""

import json
from dataclasses import asdict

import pytest

from features.audio_quality import AudioQualityConfig
from features.config_manager import ConfigManager


def test_old_config_gets_quality_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"target_lufs": -14}', encoding="utf-8")
    manager = ConfigManager(str(path))
    assert manager.get_audio_quality_config().target_lufs == -14
    assert manager.get_audio_quality_config().vmr_failure_db == 8
    assert manager.get_template_settings()["quality_gate_enabled"] is False


def test_new_defaults(tmp_path):
    manager = ConfigManager(str(tmp_path / "config.json"))
    assert manager.get("audio_quality") == asdict(AudioQualityConfig())
    assert manager.get("quality_gate_enabled") is False
    assert manager.get("music_seed") == 0


def test_quality_template_round_trip(tmp_path):
    source = ConfigManager(str(tmp_path / "source.json"))
    source.set("audio_quality", {"window_ms": 750, "ducking_attack_ms": 75})
    source.set("quality_gate_enabled", True)
    source.set("music_seed", 567)
    source.set_target_lufs(-14)
    target = ConfigManager(str(tmp_path / "target.json"))
    target.apply_template_settings(source.get_template_settings())
    reloaded = ConfigManager(target.config_file)
    assert reloaded.get_audio_quality_config() == source.get_audio_quality_config()
    assert reloaded.get("music_seed") == 567
    assert reloaded.get("quality_gate_enabled") is True


@pytest.mark.parametrize("settings", [
    {"audio_quality": {"window_ms": 0}}, {"audio_quality": []},
    {"music_seed": True}, {"music_seed": 1.5}, {
        "quality_gate_enabled": "false"},
])
def test_invalid_template_does_not_partially_apply(tmp_path, settings):
    manager = ConfigManager(str(tmp_path / "config.json"))
    before = json.dumps(manager.config, sort_keys=True)
    with pytest.raises(ValueError):
        manager.apply_template_settings(dict(settings, background_volume=33))
    assert json.dumps(manager.config, sort_keys=True) == before


def test_invalid_saved_config_is_explicit(tmp_path):
    manager = ConfigManager(str(tmp_path / "config.json"))
    manager.set("audio_quality", {"vmr_failure_db": 40})
    with pytest.raises(ValueError):
        manager.get_audio_quality_config()
