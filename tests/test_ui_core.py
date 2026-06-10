"""Quick UI Tests for NTN Podcast Creator - Core Functionality Tests.

Tests the core UI components without waiting for full podcast processing.
"""

from features.config_manager import ConfigManager
from app import (
    create_ui,
    get_intro_info,
    get_outro_info,
    get_background_tracks_display,
    get_console_log,
    denoise_audio_only_handler,
    log_message,
)
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ui_creation():
    """Test that the UI can be created without errors."""
    print("\n✓ Testing UI creation...")
    try:
        app = create_ui()
        assert app is not None, "UI creation failed"
        print("  ✓ UI created successfully")
        return True
    except Exception as e:
        print(f"  ✗ UI creation failed: {str(e)}")
        return False


def test_config_manager():
    """Test ConfigManager initialization."""
    print("\n✓ Testing ConfigManager...")
    try:
        config = ConfigManager()
        assert config is not None, "ConfigManager initialization failed"

        intro = config.get_intro()
        outro = config.get_outro()
        background_tracks = config.get_background_tracks()
        volume = config.get_volume()

        print(f"  ✓ Intro: {intro if intro else 'Not set'}")
        print(f"  ✓ Outro: {outro if outro else 'Not set'}")
        print(
            f"  ✓ Background tracks: {len(background_tracks) if background_tracks else 0}")
        print(f"  ✓ Volume: {volume}%")
        return True
    except Exception as e:
        print(f"  ✗ ConfigManager test failed: {str(e)}")
        return False


def test_get_intro_info():
    """Test getting intro info."""
    print("\n✓ Testing get_intro_info...")
    try:
        intro_name, intro_path = get_intro_info()
        assert intro_name is not None, "Intro name should not be None"
        assert intro_path is not None, "Intro path should not be None"
        print(f"  ✓ Intro: {intro_name}")
        print(f"  ✓ Path: {intro_path}")
        return True
    except Exception as e:
        print(f"  ✗ get_intro_info test failed: {str(e)}")
        return False


def test_get_outro_info():
    """Test getting outro info."""
    print("\n✓ Testing get_outro_info...")
    try:
        outro_name, outro_path = get_outro_info()
        assert outro_name is not None, "Outro name should not be None"
        assert outro_path is not None, "Outro path should not be None"
        print(f"  ✓ Outro: {outro_name}")
        print(f"  ✓ Path: {outro_path}")
        return True
    except Exception as e:
        print(f"  ✗ get_outro_info test failed: {str(e)}")
        return False


def test_background_tracks_display():
    """Test background tracks display."""
    print("\n✓ Testing background_tracks_display...")
    try:
        display_text = get_background_tracks_display()
        assert display_text is not None, "Should return display text"
        assert isinstance(display_text, str), "Should be a string"
        print(f"  ✓ Display text generated ({len(display_text)} chars)")
        return True
    except Exception as e:
        print(f"  ✗ background_tracks_display test failed: {str(e)}")
        return False


def test_console_logging():
    """Test console log functionality."""
    print("\n✓ Testing console logging...")
    try:
        import app as app_module
        app_module.console_log.clear()

        # After clearing, the log should be empty
        log_message("Test message 1")
        log_text = get_console_log()
        assert "Test message 1" in log_text, "Log should contain first message"

        log_message("Test message 2")
        log_text = get_console_log()
        assert "Test message 1" in log_text, "Log should contain first message"
        assert "Test message 2" in log_text, "Log should contain second message"

        print(f"  ✓ Console logging works ({len(log_text)} chars logged)")
        return True
    except Exception as e:
        print(f"  ✗ console logging test failed: {str(e)}")
        return False


def test_denoise_handler():
    """Test denoise audio handler."""
    print("\n✓ Testing denoise_audio_only_handler...")
    try:
        test_audio_dir = Path(__file__).parent.parent / "audios" / "test"
        test_voice_file = str(test_audio_dir / "251121-ntn443-Recording.m4a")

        if not os.path.exists(test_voice_file):
            print(f"  ⚠ Test audio not found: {test_voice_file}")
            return True  # Skip test if audio not available

        result = denoise_audio_only_handler(
            voice_file=test_voice_file,
            delete_after=False
        )

        assert result is not None, "Handler should return result"
        assert len(result) >= 3, "Should return at least 3 values"
        print(f"  ✓ Denoise handler completed: {result[0]}")
        return True
    except Exception as e:
        print(f"  ✗ denoise handler test failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 NTN Podcast Creator - Quick Core Functionality Tests")
    print("=" * 70)

    tests = [
        test_ui_creation,
        test_config_manager,
        test_get_intro_info,
        test_get_outro_info,
        test_background_tracks_display,
        test_console_logging,
        test_denoise_handler,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test {test.__name__} crashed: {str(e)}")
            results.append(False)

    # Print summary
    passed = sum(results)
    failed = len(results) - passed

    print("\n" + "=" * 70)
    print(f"📊 Test Summary:")
    print(f"  ✓ Passed: {passed}/{len(results)}")
    print(f"  ✗ Failed: {failed}/{len(results)}")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
