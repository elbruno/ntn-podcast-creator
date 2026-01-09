"""Unit tests for NTN Podcast Creator core functionality."""

from features.audio_processor import AudioProcessor
from features.config_manager import ConfigManager
import unittest
import os
import sys
import tempfile
import json
import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock dependencies that might not be available
sys.modules['soundfile'] = MagicMock()
sys.modules['noisereduce'] = MagicMock()
sys.modules['audio_denoiser'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['torchaudio'] = MagicMock()
sys.modules['whisper'] = MagicMock()


class TestConfigManager(unittest.TestCase):
    """Unit tests for ConfigManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_config_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.json')
        self.temp_config_file.close()
        self.config_manager = ConfigManager(
            config_file=self.temp_config_file.name)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_config_file.name):
            os.unlink(self.temp_config_file.name)

    def test_default_config_creation(self):
        """Test that default config is created with expected values."""
        config = self.config_manager._default_config()
        self.assertIsNone(config['intro_file'])
        self.assertIsNone(config['outro_file'])
        self.assertEqual(config['background_volume'], 10)
        self.assertEqual(config['background_tracks'], [])
        self.assertTrue(config['denoise_audio'])
        self.assertEqual(config['denoise_method'], 'audio_denoiser')

    def test_get_set_value(self):
        """Test getting and setting configuration values."""
        test_key = 'test_key'
        test_value = 'test_value'

        self.config_manager.set(test_key, test_value)
        retrieved_value = self.config_manager.get(test_key)

        self.assertEqual(retrieved_value, test_value)

    def test_volume_management(self):
        """Test volume getter and setter."""
        test_volume = 25
        self.config_manager.update_volume(test_volume)
        self.assertEqual(self.config_manager.get_volume(), test_volume)

    def test_intro_outro_management(self):
        """Test intro and outro file management."""
        intro_path = '/path/to/intro.mp3'
        outro_path = '/path/to/outro.mp3'

        self.config_manager.update_intro(intro_path)
        self.config_manager.update_outro(outro_path)

        self.assertEqual(self.config_manager.get_intro(), intro_path)
        self.assertEqual(self.config_manager.get_outro(), outro_path)

    def test_background_tracks_management(self):
        """Test background tracks list management."""
        track1 = '/path/to/track1.mp3'
        track2 = '/path/to/track2.mp3'

        self.config_manager.add_background_track(track1)
        self.config_manager.add_background_track(track2)

        tracks = self.config_manager.get_background_tracks()
        self.assertEqual(len(tracks), 2)
        self.assertIn(track1, tracks)
        self.assertIn(track2, tracks)

    def test_track_volume_management(self):
        """Test individual track volume management."""
        track_path = '/path/to/track.mp3'
        volume = 15

        self.config_manager.set_track_volume(track_path, volume)
        retrieved_volume = self.config_manager.get_track_volume(track_path)

        self.assertEqual(retrieved_volume, volume)

    def test_config_persistence(self):
        """Test that configuration persists to file."""
        test_volume = 30
        self.config_manager.update_volume(test_volume)
        self.config_manager.save_config()

        # Create new config manager with same file
        new_config_manager = ConfigManager(
            config_file=self.temp_config_file.name)

        self.assertEqual(new_config_manager.get_volume(), test_volume)

    def test_denoise_settings(self):
        """Test denoising configuration management."""
        self.config_manager.set_denoise_audio(False)
        self.assertFalse(self.config_manager.get_denoise_audio())

        self.config_manager.set_denoise_method('spectral')
        self.assertEqual(self.config_manager.get_denoise_method(), 'spectral')

    def test_lufs_settings(self):
        """Test LUFS normalization settings."""
        self.config_manager.set_normalize_lufs(True)
        self.assertTrue(self.config_manager.get_normalize_lufs())

        target_lufs = -14.0
        self.config_manager.set_target_lufs(target_lufs)
        self.assertEqual(self.config_manager.get_target_lufs(), target_lufs)

    def test_whisper_settings(self):
        """Test Whisper transcription settings."""
        self.config_manager.set_generate_transcript(True)
        self.assertTrue(self.config_manager.get_generate_transcript())

        model = 'small'
        self.config_manager.set_whisper_model(model)
        self.assertEqual(self.config_manager.get_whisper_model(), model)


class TestAudioProcessor(unittest.TestCase):
    """Unit tests for AudioProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = AudioProcessor()

    def test_initialization(self):
        """Test AudioProcessor initialization."""
        self.assertIsNotNone(self.processor)

    def test_reduce_volume_max(self):
        """Test volume reduction at maximum (100%)."""
        mock_audio = Mock()
        result = self.processor.reduce_volume(mock_audio, 100)
        self.assertEqual(result, mock_audio)

    def test_reduce_volume_zero(self):
        """Test volume reduction at zero (silence)."""
        mock_audio = Mock()
        mock_audio.__sub__ = Mock(return_value=mock_audio)
        result = self.processor.reduce_volume(mock_audio, 0)
        mock_audio.__sub__.assert_called_once_with(60)

    @patch('features.audio_processor.AudioSegment')
    def test_load_audio_file_not_found(self, mock_audio_segment):
        """Test loading non-existent audio file raises error."""
        with self.assertRaises(FileNotFoundError):
            self.processor.load_audio('/nonexistent/path/to/file.mp3')

    def test_trim_silence(self):
        """Test silence trimming functionality."""
        # Create a mock AudioSegment
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=10000)
        mock_audio.reverse = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)

        with patch('features.audio_processor.detect_leading_silence', return_value=100):
            result = self.processor.trim_silence(mock_audio)
            self.assertIsNotNone(result)


class TestAppFunctions(unittest.TestCase):
    """Unit tests for app.py helper functions."""

    def setUp(self):
        """Set up test fixtures."""
        sys.path.insert(0, os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

    def test_suggest_podcast_name_with_file(self):
        """Test podcast name suggestion with a file (now uses ntn### format)."""
        from app import suggest_podcast_name
        import re

        # Mock a file path (file parameter is kept for API compatibility but not used)
        mock_file = '/path/to/my_recording.mp3'
        suggested_name = suggest_podcast_name(mock_file)

        # Should match RSS-first pattern (ntn###) or minimal default slug
        self.assertTrue(re.match(r'^(?i:ntn\d+)$', suggested_name),
                        f"Name '{suggested_name}' should match ntn### format")

    def test_suggest_podcast_name_no_file(self):
        """Test podcast name suggestion without a file (uses ntn### format)."""
        from app import suggest_podcast_name
        import re

        suggested_name = suggest_podcast_name(None)

        self.assertTrue(re.match(r'^(?i:ntn\d+)$', suggested_name),
                        f"Name '{suggested_name}' should match ntn### format")

    def test_log_message(self):
        """Test log message creation."""
        from app import log_message, console_log

        # Clear console log
        console_log.clear()

        test_message = "Test log entry"
        log_message(test_message)

        self.assertEqual(len(console_log), 1)
        self.assertIn(test_message, console_log[0])

    def test_get_console_log(self):
        """Test getting console log."""
        from app import get_console_log, log_message, console_log

        console_log.clear()
        log_message("Line 1")
        log_message("Line 2")

        log_text = get_console_log()
        self.assertIn("Line 1", log_text)
        self.assertIn("Line 2", log_text)

    def test_clear_console_log(self):
        """Test clearing console log."""
        from app import clear_console_log, log_message, get_console_log

        log_message("Test")
        clear_console_log()

        log_text = get_console_log()
        self.assertEqual(log_text, "No logs yet")


if __name__ == '__main__':
    unittest.main()
