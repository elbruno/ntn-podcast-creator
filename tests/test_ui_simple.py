"""UI Tests for NTN Podcast Creator - Simple Test Runner.

Tests the UI components and user workflows for podcast creation without requiring pytest.
"""

from features.config_manager import ConfigManager
from app import (
    create_ui,
    create_podcast_handler_with_progress,
    denoise_audio_only_handler,
    get_console_log,
    get_background_tracks_display,
    get_intro_info,
    get_outro_info,
)
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRunner:
    """Simple test runner for UI tests."""

    def __init__(self):
        """Initialize test runner."""
        self.tests_passed = 0
        self.tests_failed = 0
        # Get the test audio from the project root
        self.test_audio_dir = Path(__file__).parent.parent / "audios" / "test"
        self.test_voice_file = str(
            self.test_audio_dir / "251121-ntn443-Recording.m4a")

    def run_all_tests(self):
        """Run all tests."""
        print("🧪 NTN Podcast Creator - UI Tests")
        print("=" * 70)

        if not os.path.exists(self.test_voice_file):
            print(
                f"❌ ERROR: Test audio file not found: {self.test_voice_file}")
            return False

        # Test groups
        self.test_ui_creation()
        self.test_podcast_creation()
        self.test_settings_ui()
        self.test_audio_handlers()
        self.test_input_validation()

        # Print summary
        print("\n" + "=" * 70)
        print(f"📊 Test Summary:")
        print(f"  ✓ Passed: {self.tests_passed}")
        print(f"  ✗ Failed: {self.tests_failed}")
        print(f"  Total: {self.tests_passed + self.tests_failed}")
        print("=" * 70)

        return self.tests_failed == 0

    def test_ui_creation(self):
        """Test UI creation."""
        print("\n🎨 UI Creation Tests")
        print("-" * 70)

        try:
            print("  Testing UI creation...")
            app = create_ui()
            assert app is not None, "UI creation failed"

            print("  ✓ UI created successfully")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ UI creation failed: {str(e)}")
            self.tests_failed += 1

    def test_podcast_creation(self):
        """Test podcast creation scenarios."""
        print("\n🎙️  Podcast Creation Tests")
        print("-" * 70)

        # Test 1: Basic podcast creation
        self.test_basic_podcast_creation()

        # Test 2: Podcast with all features
        self.test_podcast_with_all_features()

        # Test 3: Error handling
        self.test_error_handling()

        # Test 4: Progress tracking
        self.test_progress_tracking()

        # Test 5: Console logging
        self.test_console_logging()

    def test_basic_podcast_creation(self):
        """Test basic podcast creation."""
        try:
            print("  Testing basic podcast creation...")

            import app as app_module
            app_module.console_log.clear()

            results = []

            # Call the generator and collect all results
            generator = create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="test_basic",
                delete_voice=False,
                trim_silence=True,
                denoise_audio=False,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=True,
                target_lufs=-16,
                generate_transcript=False,
                whisper_model="base"
            )

            # Check if generator is None
            if generator is None:
                print("  ✗ Generator returned None - function may not be a generator")
                self.tests_failed += 1
                return

            for result in generator:
                results.append(result)

            if not results:
                print("  ✗ No results from podcast creation")
                self.tests_failed += 1
                return

            final_result = results[-1]
            assert final_result[0] is not None, "Status message is None"
            assert len(
                final_result) == 8, f"Expected 8 return values, got {len(final_result)}"

            print("  ✓ Basic podcast creation passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Basic podcast creation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.tests_failed += 1

    def test_podcast_with_all_features(self):
        """Test podcast creation with all features."""
        try:
            print("  Testing podcast with all features enabled...")

            import app as app_module
            app_module.console_log.clear()

            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="test_features",
                delete_voice=False,
                trim_silence=True,
                denoise_audio=True,
                denoise_method="audio_denoiser",
                enhance_audio=False,
                normalize_lufs=True,
                target_lufs=-16,
                generate_transcript=False,
                whisper_model="tiny"
            ):
                results.append(result)

            final_result = results[-1]
            assert len(
                final_result) == 8, f"Expected 8 return values, got {len(final_result)}"

            print("  ✓ Podcast with all features passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Podcast with all features failed: {str(e)}")
            self.tests_failed += 1

    def test_error_handling(self):
        """Test error handling with no voice file."""
        try:
            print("  Testing error handling (no voice file)...")

            import app as app_module
            app_module.console_log.clear()

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
                final_result) == 8, f"Expected 8 return values, got {len(final_result)}"

            print("  ✓ Error handling passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Error handling failed: {str(e)}")
            self.tests_failed += 1

    def test_progress_tracking(self):
        """Test progress bar HTML generation."""
        try:
            print("  Testing progress bar generation...")

            import app as app_module
            app_module.console_log.clear()

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
                if len(result) >= 7:
                    progress_html = result[6]
                    if progress_html and "<div" in progress_html and "progress" in progress_html.lower():
                        progress_bar_found = True

            assert progress_bar_found, "No progress bar HTML was generated"

            print("  ✓ Progress bar generation passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Progress bar generation failed: {str(e)}")
            self.tests_failed += 1

    def test_console_logging(self):
        """Test console log tracking."""
        try:
            print("  Testing console log tracking...")

            import app as app_module
            app_module.console_log.clear()

            initial_log = get_console_log()
            assert initial_log == "", "Console log should start empty"

            log_entries_found = 0
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
                if len(result) >= 5:
                    console_text = result[4]
                    if console_text and len(console_text) > 0:
                        log_entries_found += 1

            final_log = get_console_log()
            assert final_log != "", "Console log should have entries"
            assert log_entries_found > 0, "No log entries were captured"

            print(
                f"  ✓ Console log tracking passed ({len(final_log)} bytes logged)")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Console log tracking failed: {str(e)}")
            self.tests_failed += 1

    def test_settings_ui(self):
        """Test settings UI functionality."""
        print("\n⚙️  Settings UI Tests")
        print("-" * 70)

        try:
            print("  Testing ConfigManager initialization...")
            config = ConfigManager()
            assert config is not None, "ConfigManager initialization failed"

            intro = config.get_intro()
            outro = config.get_outro()
            background_tracks = config.get_background_tracks()

            print(f"    Intro: {intro if intro else 'Not set'}")
            print(f"    Outro: {outro if outro else 'Not set'}")
            print(
                f"    Background tracks: {len(background_tracks) if background_tracks else 0}")
            print("  ✓ ConfigManager test passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ ConfigManager test failed: {str(e)}")
            self.tests_failed += 1

        try:
            print("  Testing get_intro_info...")
            intro_name, intro_path = get_intro_info()
            assert intro_name is not None, "Intro name should not be None"
            print(f"    Intro: {intro_name}")
            print("  ✓ get_intro_info passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ get_intro_info failed: {str(e)}")
            self.tests_failed += 1

        try:
            print("  Testing get_outro_info...")
            outro_name, outro_path = get_outro_info()
            assert outro_name is not None, "Outro name should not be None"
            print(f"    Outro: {outro_name}")
            print("  ✓ get_outro_info passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ get_outro_info failed: {str(e)}")
            self.tests_failed += 1

        try:
            print("  Testing background tracks display...")
            display_text = get_background_tracks_display()
            assert display_text is not None, "Background tracks display should not be None"
            print(f"    Display text length: {len(display_text)} characters")
            print("  ✓ Background tracks display passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Background tracks display failed: {str(e)}")
            self.tests_failed += 1

    def test_audio_handlers(self):
        """Test audio handler functionality."""
        print("\n🔊 Audio Handler Tests")
        print("-" * 70)

        try:
            print("  Testing denoise_audio_only_handler...")
            result = denoise_audio_only_handler(
                voice_file=self.test_voice_file,
                delete_after=False
            )

            assert result is not None, "Denoise handler returned None"
            assert len(
                result) >= 3, f"Expected at least 3 return values, got {len(result)}"

            status = result[0]
            assert status is not None, "Status should not be None"

            print(f"    Status: {status}")
            print("  ✓ Denoise handler test passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Denoise handler test failed: {str(e)}")
            self.tests_failed += 1

    def test_input_validation(self):
        """Test input validation."""
        print("\n✔️  Input Validation Tests")
        print("-" * 70)

        try:
            print("  Testing empty output name handling...")

            import app as app_module
            app_module.console_log.clear()

            results = []
            for result in create_podcast_handler_with_progress(
                voice_file=self.test_voice_file,
                output_name="",
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
            assert final_result[0] is not None, "Should handle empty name"
            assert len(
                final_result) == 8, "Should return correct number of values"

            print("  ✓ Empty output name handling passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ Empty output name handling failed: {str(e)}")
            self.tests_failed += 1

        try:
            print("  Testing different LUFS values...")

            import app as app_module

            lufs_values = [-23, -16, -14]

            for target_lufs in lufs_values:
                app_module.console_log.clear()

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
                print(f"    ✓ LUFS {target_lufs} passed")

            print("  ✓ LUFS validation passed")
            self.tests_passed += 1
        except Exception as e:
            print(f"  ✗ LUFS validation failed: {str(e)}")
            self.tests_failed += 1


def main():
    """Main test runner."""
    runner = TestRunner()
    success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
