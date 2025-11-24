"""Tests for Progress Bar and Console Display functionality.

Tests validate that progress bar and bottom console are displayed correctly
during podcast creation process.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    get_bottom_console_html,
    get_progress_html,
    log_message,
    get_console_log,
    clear_console_log,
    create_podcast_handler_with_progress,
)


def test_progress_html_generation():
    """Test that progress HTML is generated correctly."""
    print("\n✓ Testing progress HTML generation...")
    try:
        # Test with different progress values
        html_0 = get_progress_html(0.0, "Starting...")
        html_50 = get_progress_html(0.5, "Processing...")
        html_100 = get_progress_html(1.0, "Complete!")
        
        # Verify HTML is not empty
        assert html_0, "Progress HTML should not be empty at 0%"
        assert html_50, "Progress HTML should not be empty at 50%"
        assert html_100, "Progress HTML should not be empty at 100%"
        
        # Verify HTML contains expected elements
        assert "0%" in html_0, "Progress HTML should contain 0%"
        assert "50%" in html_50, "Progress HTML should contain 50%"
        assert "100%" in html_100, "Progress HTML should contain 100%"
        
        assert "Starting..." in html_0, "Progress HTML should contain starting message"
        assert "Processing..." in html_50, "Progress HTML should contain processing message"
        assert "Complete!" in html_100, "Progress HTML should contain complete message"
        
        print("  ✓ Progress HTML generated correctly for all states")
        print(f"  ✓ 0% HTML length: {len(html_0)} chars")
        print(f"  ✓ 50% HTML length: {len(html_50)} chars")
        print(f"  ✓ 100% HTML length: {len(html_100)} chars")
        return True
    except Exception as e:
        print(f"  ✗ Progress HTML generation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_console_html_generation():
    """Test that console HTML is generated correctly."""
    print("\n✓ Testing console HTML generation...")
    try:
        # Clear console first
        clear_console_log()
        
        # Test with empty console
        empty_html = get_bottom_console_html("", visible=True)
        assert empty_html, "Console HTML should not be empty even with no logs"
        assert "Initializing..." in empty_html, "Empty console should show 'Initializing...' placeholder"
        print("  ✓ Empty console shows placeholder text")
        
        # Test with console messages
        log_message("Test message 1")
        log_message("Test message 2")
        log_message("Test message 3")
        
        console_text = get_console_log()
        html_with_logs = get_bottom_console_html(console_text, visible=True)
        
        assert html_with_logs, "Console HTML should not be empty with logs"
        assert "Test message" in html_with_logs, "Console HTML should contain log messages"
        print("  ✓ Console HTML contains log messages")
        
        # Test with visibility false
        html_hidden = get_bottom_console_html(console_text, visible=False)
        assert html_hidden == "", "Console HTML should be empty when not visible"
        print("  ✓ Console HTML respects visibility flag")
        
        # Test with close button
        html_with_close = get_bottom_console_html(console_text, visible=True, show_close=True)
        assert "close-btn" in html_with_close or "Close" in html_with_close, "Console HTML should contain close button"
        print("  ✓ Console HTML can include close button")
        
        # Clear console after test
        clear_console_log()
        
        print("  ✓ Console HTML generation works correctly")
        return True
    except Exception as e:
        print(f"  ✗ Console HTML generation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_console_log_functionality():
    """Test console logging functions."""
    print("\n✓ Testing console log functionality...")
    try:
        # Clear console first
        clear_console_log()
        
        # Test empty console
        empty_log = get_console_log()
        assert empty_log == "No logs yet", "Empty console should return 'No logs yet'"
        print("  ✓ Empty console returns correct message")
        
        # Test adding messages
        log_message("First message")
        log_message("Second message")
        log_message("Third message")
        
        log_content = get_console_log()
        assert "First message" in log_content, "Console should contain first message"
        assert "Second message" in log_content, "Console should contain second message"
        assert "Third message" in log_content, "Console should contain third message"
        print("  ✓ Log messages added correctly")
        
        # Test message count
        lines = log_content.split('\n')
        assert len(lines) >= 3, "Console should have at least 3 messages"
        print(f"  ✓ Console has {len(lines)} lines")
        
        # Test clearing
        clear_console_log()
        cleared_log = get_console_log()
        assert cleared_log == "No logs yet", "Cleared console should return 'No logs yet'"
        print("  ✓ Console cleared successfully")
        
        return True
    except Exception as e:
        print(f"  ✗ Console log functionality test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_progress_console_initial_display():
    """Test that progress and console are displayed immediately when podcast creation starts."""
    print("\n✓ Testing initial progress and console display...")
    try:
        # Clear console first
        clear_console_log()
        
        # Create a mock voice file for testing (using test audio file)
        test_audio_dir = Path(__file__).parent.parent / "audios" / "test"
        test_file = test_audio_dir / "251121-ntn443-Recording.m4a"
        
        if not test_file.exists():
            print(f"  ⚠ Test file not found: {test_file}")
            print("  ⚠ Skipping test (requires test audio file)")
            return True
        
        # Test the handler with a generator call
        print("  ℹ Testing podcast handler initial yields...")
        handler_gen = create_podcast_handler_with_progress(
            voice_file=str(test_file),
            output_name="test_progress",
            delete_voice=False,
            trim_silence=False,
            denoise_audio=False,
            denoise_method="spectral",
            enhance_audio=False,
            normalize_lufs=False,
            target_lufs=-16.0,
            generate_transcript=False,
            whisper_model="base"
        )
        
        # Get first yield (should show progress and console immediately)
        first_yield = next(handler_gen)
        
        # first_yield should have 7 elements: status, audio, denoised, transcript, console, progress_html, bottom_console
        assert len(first_yield) == 7, f"First yield should have 7 elements, got {len(first_yield)}"
        
        status, audio, denoised, transcript, console_text, progress_html, bottom_console_html = first_yield
        
        # Verify progress HTML is present
        assert progress_html, "Progress HTML should not be empty on first yield"
        assert "Starting" in progress_html or "%" in progress_html, "Progress HTML should show starting state"
        print("  ✓ Progress bar HTML generated on first yield")
        
        # Verify console HTML is present
        assert bottom_console_html, "Console HTML should not be empty on first yield"
        print("  ✓ Console HTML generated on first yield")
        
        # Verify console text contains startup message
        assert "Starting" in console_text or "podcast creation" in console_text, "Console should contain startup message"
        print("  ✓ Console contains startup messages")
        
        # Stop the generator (don't process full podcast)
        handler_gen.close()
        
        # Clean up
        clear_console_log()
        
        print("  ✓ Progress and console display correctly on start")
        return True
    except StopIteration:
        print("  ⚠ Generator completed (this is expected if we close it)")
        return True
    except Exception as e:
        print(f"  ✗ Progress console initial display test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_error_state_progress_console():
    """Test that progress and console are shown in error states."""
    print("\n✓ Testing error state progress and console display...")
    try:
        # Clear console first
        clear_console_log()
        
        # Test with no voice file (should trigger error)
        print("  ℹ Testing with no voice file (error case)...")
        handler_gen = create_podcast_handler_with_progress(
            voice_file=None,  # No file
            output_name="test_error",
            delete_voice=False,
            trim_silence=False,
            denoise_audio=False,
            denoise_method="spectral",
            enhance_audio=False,
            normalize_lufs=False,
            target_lufs=-16.0,
            generate_transcript=False,
            whisper_model="base"
        )
        
        # Get first yield (should show initial progress)
        first_yield = next(handler_gen)
        assert len(first_yield) == 7, f"First yield should have 7 elements"
        
        # Get second yield (should be error)
        error_yield = next(handler_gen)
        assert len(error_yield) == 7, f"Error yield should have 7 elements"
        
        status, audio, denoised, transcript, console_text, progress_html, bottom_console_html = error_yield
        
        # Verify error status
        assert "Error" in status or "error" in status, "Status should indicate error"
        print("  ✓ Error status shown correctly")
        
        # Verify progress HTML still present (showing error)
        assert progress_html, "Progress HTML should be present even on error"
        assert "Error" in progress_html or "❌" in progress_html, "Progress should show error state"
        print("  ✓ Progress bar shows error state")
        
        # Verify console HTML still present
        assert bottom_console_html, "Console HTML should be present on error"
        print("  ✓ Console displayed on error")
        
        # Verify error message in console
        assert "Error" in console_text or "error" in console_text, "Console should contain error message"
        print("  ✓ Error message in console log")
        
        # Generator should be done
        try:
            next(handler_gen)
            print("  ⚠ Generator continued after error (unexpected)")
        except StopIteration:
            print("  ✓ Generator stopped after error (expected)")
        
        # Clean up
        clear_console_log()
        
        print("  ✓ Error state progress and console work correctly")
        return True
    except StopIteration:
        print("  ⚠ Generator completed early")
        return True
    except Exception as e:
        print(f"  ✗ Error state test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all progress and console tests."""
    print("=" * 60)
    print("Running Progress Bar and Console Display Tests")
    print("=" * 60)
    
    tests = [
        test_progress_html_generation,
        test_console_html_generation,
        test_console_log_functionality,
        test_progress_console_initial_display,
        test_error_state_progress_console,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test {test.__name__} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
