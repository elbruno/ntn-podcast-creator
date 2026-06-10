"""UI Tests for NTN Podcast Creator Application.

Tests the Gradio UI components and user workflows for podcast creation,
audio enhancement, and settings management.
"""

from features.config_manager import ConfigManager
from app import (
    create_ui,
    create_podcast_handler_with_progress,
    denoise_audio_only_handler,
    enhance_audio_only_handler,
    get_console_log,
    log_message,
    get_background_tracks_display,
    get_intro_info,
    get_outro_info,
)
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPodcastCreationUI:
    """Test podcast creation UI functionality."""

    @pytest.fixture
    def setup_test_env(self):
        """Set up test environment with test audio files."""
        self.test_audio_dir = Path(__file__).parent.parent / "audios" / "test"
        self.test_voice_file = str(
            self.test_audio_dir / "251121-ntn443-Recording.m4a")

        # Create temporary output directory for tests
        self.temp_output_dir = tempfile.mkdtemp()

        assert os.path.exists(
            self.test_voice_file), f"Test audio file not found: {self.test_voice_file}"

        yield

        # Cleanup
        if os.path.exists(self.temp_output_dir):
            shutil.rmtree(self.temp_output_dir)

    def test_ui_creation(self):
        """Test that the UI can be created without errors."""
        try:
            app = create_ui()
            assert app is not None, "UI creation failed"
            print("✓ UI creation successful")
        except Exception as e:
            pytest.fail(f"UI creation failed: {str(e)}")

    def test_podcast_creation_with_voice_file(self, setup_test_env):
        """Test podcast creation with voice file."""
        print(
            f"\n📝 Testing podcast creation with voice file: {self.test_voice_file}")

        # Clear console log
        import app as app_module
        app_module.console_log.clear()

        output_name = "test_podcast_ui"

        try:
            # Simulate UI inputs
            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name=output_name,
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=True,
                target_lufs=-16,
                generate_transcript=False,
                whisper_model="base"
            ):
                results.append(result)
                if len(result) >= 1:
                    print(f"  Status: {result[0]}")

            # Check final result
            final_result = results[-1]
            assert final_result[0] is not None, "Status message is None"
            assert "✓" in final_result[0] or "Error" not in final_result[
                0], f"Unexpected status: {final_result[0]}"

            # Check that we have 7 values (status, audio, denoised, transcript, console, progress_bar, bottom_console)
            assert len(
                final_result) == 7, f"Expected 7 return values, got {len(final_result)}"

            console_log = get_console_log()
            assert console_log != "", "Console log should not be empty"

            print(f"✓ Podcast creation test passed")
            print(f"  Console log entries: {len(console_log.split(chr(10)))}")

        except Exception as e:
            pytest.fail(f"Podcast creation failed: {str(e)}")

    def test_podcast_creation_minimal_settings(self, setup_test_env):
        """Test podcast creation with minimal settings."""
        print(f"\n📝 Testing podcast creation with minimal settings")

        import app as app_module
        app_module.console_log.clear()

        output_name = "test_minimal"

        try:
            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name=output_name,
                delete_voice=False,
                trim_silence=False,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=False,
                target_lufs=-16,
                generate_transcript=False,
                whisper_model="base"
            ):
                results.append(result)

            final_result = results[-1]
            assert final_result[0] is not None, "Status message is None"
            assert len(
                final_result) == 7, f"Expected 7 return values, got {len(final_result)}"

            print(f"✓ Minimal settings test passed")

        except Exception as e:
            pytest.fail(f"Minimal settings test failed: {str(e)}")

    def test_podcast_creation_with_all_features(self, setup_test_env):
        """Test podcast creation with all features enabled."""
        print(f"\n📝 Testing podcast creation with all features enabled")

        import app as app_module
        app_module.console_log.clear()

        output_name = "test_all_features"

        try:
            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name=output_name,
                delete_voice=False,
                trim_silence=True,
                denoise_audio=True,
                denoise_method="audio_denoiser",
                enhance_audio=False,  # Skip Adobe enhance in tests
                normalize_lufs=True,
                target_lufs=-16,
                generate_transcript=False,  # Skip transcription in quick tests
                whisper_model="tiny"
            ):
                results.append(result)

            final_result = results[-1]
            assert final_result[0] is not None, "Status message is None"
            assert len(
                final_result) == 7, f"Expected 7 return values, got {len(final_result)}"

            print(f"✓ All features test passed")

        except Exception as e:
            pytest.fail(f"All features test failed: {str(e)}")

    def test_no_voice_file_error_handling(self):
        """Test error handling when no voice file is provided."""
        print(f"\n⚠️  Testing error handling with no voice file")

        import app as app_module
        app_module.console_log.clear()

        try:
            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=None,
                output_name="test_error",
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=True,
                target_lufs=-16,
                generate_transcript=False,
                whisper_model="base"
            ):
                results.append(result)

            final_result = results[-1]
            assert "Error" in final_result[0] or "❌" in final_result[
                0], f"Expected error message, got: {final_result[0]}"
            assert len(
                final_result) == 7, f"Expected 7 return values even for errors, got {len(final_result)}"

            print(f"✓ Error handling test passed")

        except Exception as e:
            pytest.fail(f"Error handling test failed: {str(e)}")

    def test_console_log_tracking(self, setup_test_env):
        """Test that console logs are properly tracked during processing."""
        print(f"\n📋 Testing console log tracking")

        import app as app_module
        app_module.console_log.clear()

        initial_log = get_console_log()
        assert initial_log == "", "Console log should start empty"

        try:
            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="test_logging",
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=False,
                generate_transcript=False,
                whisper_model="base"
            ):
                results.append(result)
                # Check that console log grows during processing
                if len(result) >= 5:
                    console_text = result[4]
                    if console_text and len(console_text) > 0:
                        print(
                            f"  Log updated with {len(console_text)} characters")

            final_log = get_console_log()
            assert final_log != "", "Console log should have entries after processing"
            assert "🎬" in final_log or "Starting" in final_log or "Podcast" in final_log, "Console log should have expected messages"

            print(f"✓ Console log tracking test passed")
            print(f"  Total log size: {len(final_log)} characters")

        except Exception as e:
            pytest.fail(f"Console log tracking test failed: {str(e)}")

    def test_progress_bar_output(self, setup_test_env):
        """Test that progress bar HTML is generated correctly."""
        print(f"\n📊 Testing progress bar output")

        import app as app_module
        app_module.console_log.clear()

        try:
            progress_bar_found = False

            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="test_progress",
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=False,
                generate_transcript=False,
                whisper_model="base"
            ):
                # Check for progress bar HTML in result
                if len(result) >= 7:
                    # progress_bar is 7th element (index 6)
                    progress_html = result[6]
                    if progress_html and "<div" in progress_html:
                        progress_bar_found = True
                        print(
                            f"  Progress bar HTML found: {len(progress_html)} bytes")

            assert progress_bar_found, "No progress bar HTML was generated"

            print(f"✓ Progress bar output test passed")

        except Exception as e:
            pytest.fail(f"Progress bar test failed: {str(e)}")

    def test_bottom_console_output(self, setup_test_env):
        """Test that bottom console HTML is generated correctly."""
        print(f"\n📋 Testing bottom console output")

        import app as app_module
        app_module.console_log.clear()

        try:
            bottom_console_found = False

            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="test_console",
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=False,
                generate_transcript=False,
                whisper_model="base"
            ):
                # Check for bottom console HTML in result
                if len(result) >= 8:
                    # bottom_console is 8th element (index 7)
                    bottom_console = result[7]
                    if bottom_console and "Processing Log" in bottom_console:
                        bottom_console_found = True
                        print(
                            f"  Bottom console HTML found: {len(bottom_console)} bytes")

            assert bottom_console_found, "No bottom console HTML was generated"

            print(f"✓ Bottom console output test passed")

        except Exception as e:
            pytest.fail(f"Bottom console test failed: {str(e)}")


class TestAudioEnhancementUI:
    """Test audio enhancement UI functionality."""

    @pytest.fixture
    def setup_test_env(self):
        """Set up test environment."""
        self.test_audio_dir = Path(__file__).parent.parent / "audios" / "test"
        self.test_voice_file = str(
            self.test_audio_dir / "251121-ntn443-Recording.m4a")

        assert os.path.exists(
            self.test_voice_file), f"Test audio file not found: {self.test_voice_file}"

        yield

    def test_denoise_audio_handler(self, setup_test_env):
        """Test audio denoising handler."""
        print(f"\n🔧 Testing audio denoising handler")

        import app as app_module
        app_module.console_log.clear()

        try:
            result = denoise_audio_only_handler(
                voice_file=self.test_voice_file,
                delete_voice=False
            )

            assert result is not None, "Denoise handler returned None"
            assert len(
                result) >= 3, f"Expected at least 3 return values, got {len(result)}"

            status = result[0]
            assert status is not None, "Status should not be None"

            print(f"✓ Audio denoising test passed")
            print(f"  Status: {status}")

        except Exception as e:
            pytest.fail(f"Audio denoising test failed: {str(e)}")


class TestSettingsUI:
    """Test settings UI functionality."""

    def test_config_manager_initialization(self):
        """Test that ConfigManager initializes correctly."""
        print(f"\n⚙️  Testing ConfigManager initialization")

        try:
            config = ConfigManager()
            assert config is not None, "ConfigManager initialization failed"

            # Check that default values are accessible
            intro = config.get_intro()
            outro = config.get_outro()
            background_tracks = config.get_background_tracks()

            print(f"✓ ConfigManager initialization test passed")
            print(f"  Intro: {intro if intro else 'Not set'}")
            print(f"  Outro: {outro if outro else 'Not set'}")
            print(
                f"  Background tracks: {len(background_tracks) if background_tracks else 0}")

        except Exception as e:
            pytest.fail(f"ConfigManager test failed: {str(e)}")

    def test_get_intro_info(self):
        """Test getting intro info."""
        print(f"\n📁 Testing get_intro_info")

        try:
            intro_name, intro_path = get_intro_info()

            assert intro_name is not None, "Intro name should not be None"
            assert intro_path is not None, "Intro path should not be None"

            print(f"✓ Get intro info test passed")
            print(f"  Intro: {intro_name}")

        except Exception as e:
            pytest.fail(f"Get intro info test failed: {str(e)}")

    def test_get_outro_info(self):
        """Test getting outro info."""
        print(f"\n📁 Testing get_outro_info")

        try:
            outro_name, outro_path = get_outro_info()

            assert outro_name is not None, "Outro name should not be None"
            assert outro_path is not None, "Outro path should not be None"

            print(f"✓ Get outro info test passed")
            print(f"  Outro: {outro_name}")

        except Exception as e:
            pytest.fail(f"Get outro info test failed: {str(e)}")

    def test_background_tracks_display(self):
        """Test background tracks display formatting."""
        print(f"\n📁 Testing background tracks display")

        try:
            display_text = get_background_tracks_display()

            assert display_text is not None, "Background tracks display should not be None"
            assert isinstance(
                display_text, str), "Background tracks display should be a string"

            print(f"✓ Background tracks display test passed")
            print(f"  Display text length: {len(display_text)} characters")

        except Exception as e:
            pytest.fail(f"Background tracks display test failed: {str(e)}")


class TestUIInputValidation:
    """Test UI input validation."""

    @pytest.fixture
    def setup_test_env(self):
        """Set up test environment."""
        self.test_audio_dir = Path(__file__).parent.parent / "audios" / "test"
        self.test_voice_file = str(
            self.test_audio_dir / "251121-ntn443-Recording.m4a")

        yield

    def test_empty_output_name_handling(self, setup_test_env):
        """Test handling of empty output name."""
        print(f"\n📝 Testing empty output name handling")

        import app as app_module
        app_module.console_log.clear()

        try:
            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="",  # Empty output name
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=False,
                generate_transcript=False,
                whisper_model="base"
            ):
                results.append(result)

            final_result = results[-1]
            # Should handle empty name gracefully by using default
            assert final_result[0] is not None, "Should handle empty name"
            assert len(
                final_result) == 8, "Should return correct number of values"

            print(f"✓ Empty output name handling test passed")

        except Exception as e:
            pytest.fail(f"Empty output name test failed: {str(e)}")

    def test_different_lufs_values(self, setup_test_env):
        """Test different LUFS normalization values."""
        print(f"\n📊 Testing different LUFS values")

        import app as app_module

        lufs_values = [-23, -16, -14]

        for target_lufs in lufs_values:
            app_module.console_log.clear()

            try:
                results = []
                for result in create_podcast_handler_with_progress(
                    voice_file=self.test_voice_file,
                    output_name=f"test_lufs_{target_lufs}",
                    delete_voice=False,
                    trim_silence=False,
                    denoise_audio=False,
                    denoise_method="audio_denoiser",
                    enhance_audio=False,
                    normalize_lufs=True,
                    target_lufs=target_lufs,
                    generate_transcript=False,
                    whisper_model="base"
                ):
                    results.append(result)

                final_result = results[-1]
                assert final_result[0] is not None, f"Failed for LUFS {target_lufs}"

                print(f"  ✓ LUFS {target_lufs} test passed")

            except Exception as e:
                pytest.fail(f"LUFS {target_lufs} test failed: {str(e)}")


if __name__ == "__main__":
    print("🧪 NTN Podcast Creator - UI Tests")
    print("=" * 60)

    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
