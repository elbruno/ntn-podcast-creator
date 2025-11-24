"""Quick test to validate theme and progress bar fixes."""

from app import get_progress_html, get_bottom_console_html
import sys
sys.path.insert(0, '/workspaces/ntn-podcast-creator')


def test_progress_html():
    """Test that progress bar HTML includes display: block."""
    html = get_progress_html(0.5, "Testing progress")

    # Should contain display: block
    assert "display: block" in html or "display:block" in html, "Progress bar must have display: block"

    # Should show percentage
    assert "50%" in html, "Progress bar must show percentage"

    # Should show message
    assert "Testing progress" in html, "Progress bar must show message"

    print("✓ Progress bar HTML test passed")
    return True


def test_bottom_console_html():
    """Test that bottom console HTML displays correctly."""
    # Test visible console
    html_visible = get_bottom_console_html(
        "Test log message", visible=True, show_close=False)
    assert "display: block" in html_visible or "display:block" in html_visible, "Visible console must have display: block"
    assert "Test log message" in html_visible, "Console must contain log message"

    # Test hidden console
    html_hidden = get_bottom_console_html(
        "Test log message", visible=False, show_close=False)
    assert "display: none" in html_hidden or "display:none" in html_hidden, "Hidden console must have display: none"

    # Test with close button
    html_close = get_bottom_console_html(
        "Test log", visible=True, show_close=True)
    assert "Close" in html_close, "Console with close button must show Close text"

    print("✓ Bottom console HTML test passed")
    return True


def test_dark_theme_css():
    """Test that dark theme CSS is present in app.py."""
    with open('/workspaces/ntn-podcast-creator/app.py', 'r') as f:
        content = f.read()

    # Check for dark theme class
    assert ".dark-theme {" in content, "Dark theme CSS class must be defined"

    # Check for dark theme background variables
    assert "--bg-primary: #1e1e1e" in content, "Dark theme must define bg-primary variable"

    # Check for gradio-container dark theme styling
    assert ".dark-theme .gradio-container" in content, "Dark theme must style gradio-container"

    print("✓ Dark theme CSS test passed")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Progress Bar and Theme Fixes")
    print("=" * 60)

    try:
        test_progress_html()
        test_bottom_console_html()
        test_dark_theme_css()

        print("=" * 60)
        print("✓ All fix validation tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
