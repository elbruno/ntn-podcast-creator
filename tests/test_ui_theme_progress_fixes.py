"""Tests for UI theme toggle and progress bar display fixes.

This module validates that:
- Dark mode theme can be applied and persists correctly
- Progress bar displays during podcast creation
- Bottom console log displays live updates during processing
"""

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


def test_bottom_console_with_important():
    """Test that bottom console uses !important for display style."""
    html = get_bottom_console_html("Test", visible=True)
    assert "display: block !important" in html, "Console must use !important for display"
    print("✓ Bottom console !important test passed")
    return True


def test_dark_theme_css():
    """Test that dark theme CSS is properly defined in app.py."""
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


def test_dark_theme_javascript():
    """Test that dark theme JavaScript function is properly defined."""
    with open('/workspaces/ntn-podcast-creator/app.py', 'r') as f:
        content = f.read()

    # Check for applyTheme function
    assert "function applyTheme(theme)" in content, "applyTheme JavaScript function must be defined"

    # Check that it applies to document.documentElement
    assert "root.classList.add('dark-theme')" in content, "Theme must apply to document.documentElement"

    # Check that it applies to body element
    assert "body.classList.add('dark-theme')" in content, "Theme must apply to body element"

    # Check localStorage usage
    assert "localStorage.setItem('ntn-theme'" in content, "Theme must persist to localStorage"

    print("✓ Dark theme JavaScript test passed")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("Testing UI Theme Toggle and Progress Bar Display Fixes")
    print("=" * 70)

    try:
        test_progress_html()
        test_bottom_console_html()
        test_bottom_console_with_important()
        test_dark_theme_css()
        test_dark_theme_javascript()

        print("=" * 70)
        print("✓ All UI theme and progress bar fix tests passed!")
        print("=" * 70)
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
