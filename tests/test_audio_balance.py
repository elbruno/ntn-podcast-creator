#!/usr/bin/env python3
"""Unit and integration tests for audio level analysis, auto-balancing, and voice protection."""

import os
import sys
import json
import unittest
import tempfile
from unittest.mock import MagicMock, patch

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock external ML/audio dependencies before any internal imports
for mod in ['torch', 'torchaudio', 'whisper', 'soundfile', 'noisereduce', 'audio_denoiser', 'pydub', 'pydub.silence', 'gradio', 'numpy']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from features.config_manager import ConfigManager
from features.template_manager import TemplateManager


class MockAudioSegment:
    """Mock AudioSegment for deterministic audio level math testing."""

    def __init__(self, duration_ms=10000, dbfs=-25.0, max_dbfs=-6.0):
        self.duration_ms = duration_ms
        self._dbfs = dbfs
        self._max_dbfs = max_dbfs

    @property
    def dBFS(self):
        return self._dbfs

    @property
    def max_dBFS(self):
        return self._max_dbfs

    def __len__(self):
        return self.duration_ms

    def __getitem__(self, val):
        if isinstance(val, slice):
            start = val.start or 0
            stop = val.stop or self.duration_ms
            return MockAudioSegment(duration_ms=max(0, stop - start), dbfs=self._dbfs, max_dbfs=self._max_dbfs)
        return self

    def __add__(self, other):
        if isinstance(other, MockAudioSegment):
            return MockAudioSegment(duration_ms=self.duration_ms + len(other), dbfs=self._dbfs, max_dbfs=self._max_dbfs)
        elif isinstance(other, (int, float)):
            return MockAudioSegment(duration_ms=self.duration_ms, dbfs=self._dbfs + other, max_dbfs=self._max_dbfs + other)
        return self

    def __sub__(self, gain_db):
        return MockAudioSegment(duration_ms=self.duration_ms, dbfs=self._dbfs - gain_db, max_dbfs=self._max_dbfs - gain_db)

    def apply_gain(self, gain_db):
        return MockAudioSegment(duration_ms=self.duration_ms, dbfs=self._dbfs + gain_db, max_dbfs=self._max_dbfs + gain_db)

    def overlay(self, other, position=0):
        return MockAudioSegment(duration_ms=max(self.duration_ms, position + len(other)), dbfs=max(self._dbfs, other.dBFS), max_dbfs=max(self._max_dbfs, other.max_dBFS))


class TestAudioBalanceConfig(unittest.TestCase):
    """Test config manager persistence for audio balance features."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.cfg = ConfigManager(config_file=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_default_balance_settings(self):
        """Test default values for audio balance settings."""
        self.assertTrue(self.cfg.get_auto_balance_levels())
        self.assertTrue(self.cfg.get_auto_ducking())
        self.assertEqual(self.cfg.get_min_voice_music_separation_db(), 18.0)

    def test_update_balance_settings(self):
        """Test updating audio balance settings."""
        self.cfg.set_auto_balance_levels(False)
        self.assertFalse(self.cfg.get_auto_balance_levels())

        self.cfg.set_auto_ducking(False)
        self.assertFalse(self.cfg.get_auto_ducking())

        self.cfg.set_min_voice_music_separation_db(22.0)
        self.assertEqual(self.cfg.get_min_voice_music_separation_db(), 22.0)

    def test_template_includes_balance_settings(self):
        """Test that templates persist and apply balance settings."""
        template_settings = self.cfg.get_template_settings()
        self.assertIn("auto_balance_levels", template_settings)
        self.assertIn("auto_ducking", template_settings)
        self.assertIn("min_voice_music_separation_db", template_settings)

        # Modify and reapply
        template_settings["auto_balance_levels"] = False
        template_settings["min_voice_music_separation_db"] = 20.0
        self.cfg.apply_template_settings(template_settings)

        self.assertFalse(self.cfg.get_auto_balance_levels())
        self.assertEqual(self.cfg.get_min_voice_music_separation_db(), 20.0)


class TestAudioProcessorBalance(unittest.TestCase):
    """Test audio processor level analysis and auto-balancing logic."""

    def setUp(self):
        # Dynamically import AudioProcessor with pydub mocked if necessary
        if 'pydub' not in sys.modules:
            mock_pydub = MagicMock()
            mock_pydub.AudioSegment = MockAudioSegment
            sys.modules['pydub'] = mock_pydub
            sys.modules['pydub.silence'] = MagicMock()

        from features.audio_processor import AudioProcessor
        self.processor = AudioProcessor()

    def test_analyze_levels_low_voice_and_loud_music(self):
        """Test level analysis when voice is low (-34 dBFS) and music is loud (-26 dBFS)."""
        low_voice = MockAudioSegment(duration_ms=60000, dbfs=-34.0, max_dbfs=-18.0)

        with patch.object(self.processor, 'load_audio') as mock_load:
            # When loading bg track, return -26 dBFS
            mock_load.return_value = MockAudioSegment(duration_ms=60000, dbfs=-6.0, max_dbfs=-1.0)

            with patch('os.path.exists', return_value=True):
                analysis = self.processor.analyze_levels(
                    voice_audio=low_voice,
                    background_files=['track1.mp3'],
                    background_volume=10
                )

        self.assertEqual(analysis["overall_status"], "danger")
        self.assertEqual(analysis["voice_status"], "very_low")
        self.assertIn("La música de fondo tapará tu voz", " ".join(analysis["warnings"]))
        self.assertGreater(analysis["suggested_voice_gain_db"], 10.0)

    def test_analyze_levels_optimal_voice(self):
        """Test level analysis when voice is in optimal range (-17 dBFS)."""
        good_voice = MockAudioSegment(duration_ms=60000, dbfs=-17.0, max_dbfs=-3.0)

        analysis = self.processor.analyze_levels(
            voice_audio=good_voice,
            background_files=None
        )

        self.assertEqual(analysis["overall_status"], "optimal")
        self.assertEqual(analysis["voice_status"], "optimal")
        self.assertEqual(len(analysis["warnings"]), 0)

    def test_auto_balance_audio_pre_gain(self):
        """Test that auto_balance_audio applies pre-gain to bring quiet voice to -18 dBFS."""
        quiet_voice = MockAudioSegment(duration_ms=60000, dbfs=-32.0, max_dbfs=-15.0)

        balanced_voice, _, info = self.processor.auto_balance_audio(
            voice=quiet_voice,
            background=None,
            target_voice_dbfs=-18.0
        )

        self.assertAlmostEqual(info["voice_gain_applied_db"], 14.0, delta=0.5)
        self.assertAlmostEqual(balanced_voice.dBFS, -18.0, delta=0.5)

    def test_auto_balance_audio_music_attenuation(self):
        """Test that auto_balance_audio attenuates background music when VMR is under minimum separation."""
        voice = MockAudioSegment(duration_ms=60000, dbfs=-18.0, max_dbfs=-2.0)
        loud_bg = MockAudioSegment(duration_ms=60000, dbfs=-24.0, max_dbfs=-8.0)  # Only 6 dB below voice

        balanced_voice, balanced_bg, info = self.processor.auto_balance_audio(
            voice=voice,
            background=loud_bg,
            min_separation_db=18.0,
            apply_ducking=False
        )

        # Expected reduction: 18 - 6 = 12 dB
        self.assertAlmostEqual(info["bg_attenuation_applied_db"], 12.0, delta=0.5)
        self.assertAlmostEqual(balanced_bg.dBFS, -36.0, delta=0.5)
        self.assertAlmostEqual(balanced_voice.dBFS - balanced_bg.dBFS, 18.0, delta=0.5)


class TestRenderAudioHealthCard(unittest.TestCase):
    """Test rendering of the HTML health card component."""

    def test_render_no_voice(self):
        from app import render_audio_health_card
        html = render_audio_health_card(None)
        self.assertIn("Inspector de Balance de Audio", html)

    def test_render_danger_alert(self):
        from app import render_audio_health_card
        analysis = {
            "overall_status": "danger",
            "badge_icon": "🔴",
            "title": "Alerta de Balance",
            "voice_dbfs": -32.5,
            "voice_status_label": "Voz muy baja",
            "bg_dbfs": -25.0,
            "voice_to_music_ratio_db": -7.5,
            "balance_status_label": "Peligro: La música tapará la voz",
            "warnings": ["La música tapará tus palabras"],
            "recommendations": ["Auto-balance solucionará esto automáticamente"],
            "suggested_voice_gain_db": 14.5
        }
        html = render_audio_health_card(analysis)
        self.assertIn("🔴 Alerta de Balance", html)
        self.assertIn("-32.5 dBFS", html)
        self.assertIn("La música tapará tus palabras", html)


if __name__ == '__main__':
    unittest.main()
