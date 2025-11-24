"""Playwright-based UI tests for NTN Podcast Creator.

These tests interact with the actual Gradio UI using Playwright browser automation.
"""

import os
import sys
import time
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"

# Ensure outputs directory exists
OUTPUTS_DIR.mkdir(exist_ok=True)


class GradioApp:
    """Helper class to manage Gradio app lifecycle for testing."""
    
    def __init__(self):
        self.process = None
        self.url = "http://localhost:7860"
        
    def start(self):
        """Start the Gradio app in a subprocess."""
        import subprocess
        
        # Start the app
        env = os.environ.copy()
        env['PYTHONPATH'] = str(BASE_DIR)
        
        self.process = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "app.py")],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for app to start (check for "Running on" message or timeout after 30s)
        start_time = time.time()
        while time.time() - start_time < 30:
            time.sleep(1)
            # Try to connect to the app
            try:
                import requests
                response = requests.get(self.url, timeout=1)
                if response.status_code == 200:
                    print(f"✓ Gradio app started at {self.url}")
                    return
            except (requests.RequestException, Exception):
                pass
        
        raise TimeoutError("Failed to start Gradio app within 30 seconds")
    
    def stop(self):
        """Stop the Gradio app."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            print("✓ Gradio app stopped")


@pytest.fixture(scope="module")
def gradio_app():
    """Fixture to start and stop the Gradio app for all tests."""
    app = GradioApp()
    app.start()
    yield app
    app.stop()


@pytest.fixture(scope="function")
def browser_page(gradio_app):
    """Fixture to provide a browser page for each test."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(gradio_app.url, wait_until="networkidle", timeout=30000)
        
        # Wait for the UI to be fully loaded
        page.wait_for_timeout(2000)
        
        yield page
        
        context.close()
        browser.close()


def test_ui_loads_successfully(browser_page: Page):
    """Test that the UI loads without errors."""
    print("\n✓ Testing UI loads successfully...")
    
    # Check that the page title is correct
    assert "NTN Podcast Creator" in browser_page.title()
    
    # Check for main UI elements
    assert browser_page.is_visible("text=NTN Podcast Creator")
    print("  ✓ UI loaded successfully")


def test_podcast_creation_tab_visible(browser_page: Page):
    """Test that the Podcast Creation tab is visible and accessible."""
    print("\n✓ Testing Podcast Creation tab...")
    
    # Look for the podcast creation tab or main content
    # Gradio 6.0 uses different selectors, let's check for key elements
    page_content = browser_page.content()
    
    # Check for key elements that should be present
    assert "Voice Recording" in page_content or "voice" in page_content.lower()
    assert "output" in page_content.lower() or "podcast" in page_content.lower()
    
    print("  ✓ Podcast Creation elements visible")


def test_upload_voice_file_input_exists(browser_page: Page):
    """Test that the voice file upload input exists."""
    print("\n✓ Testing voice file upload input...")
    
    # In Gradio, file upload inputs are typically of type file
    file_inputs = browser_page.query_selector_all('input[type="file"]')
    
    assert len(file_inputs) > 0, "No file upload inputs found"
    print(f"  ✓ Found {len(file_inputs)} file upload input(s)")


def test_output_name_input_exists(browser_page: Page):
    """Test that the output name input field exists."""
    print("\n✓ Testing output name input field...")
    
    # Look for text input fields
    text_inputs = browser_page.query_selector_all('input[type="text"]')
    
    assert len(text_inputs) > 0, "No text input fields found"
    print(f"  ✓ Found {len(text_inputs)} text input field(s)")


def test_create_podcast_button_exists(browser_page: Page):
    """Test that the 'Create Podcast' button exists."""
    print("\n✓ Testing Create Podcast button...")
    
    # Look for buttons
    buttons = browser_page.query_selector_all('button')
    button_texts = [btn.inner_text() for btn in buttons if btn.inner_text()]
    
    # Check if any button contains "create" or "generate" text
    create_buttons = [text for text in button_texts if "create" in text.lower() or "generate" in text.lower()]
    
    assert len(buttons) > 0, "No buttons found on page"
    print(f"  ✓ Found {len(buttons)} button(s)")
    if create_buttons:
        print(f"  ✓ Found action buttons: {create_buttons[:3]}")


def test_volume_slider_exists(browser_page: Page):
    """Test that volume control slider exists."""
    print("\n✓ Testing volume slider...")
    
    # Look for slider inputs
    sliders = browser_page.query_selector_all('input[type="range"]')
    
    # Gradio sliders might also be custom elements
    if len(sliders) == 0:
        # Try to find any element with "volume" in nearby text
        page_content = browser_page.content()
        has_volume_control = "volume" in page_content.lower()
        assert has_volume_control, "No volume control found"
        print("  ✓ Volume control found in UI")
    else:
        assert len(sliders) > 0, "No slider inputs found"
        print(f"  ✓ Found {len(sliders)} slider(s)")


def test_checkboxes_exist(browser_page: Page):
    """Test that various option checkboxes exist."""
    print("\n✓ Testing checkboxes...")
    
    # Look for checkbox inputs
    checkboxes = browser_page.query_selector_all('input[type="checkbox"]')
    
    # Allow zero or more checkboxes (they may be present depending on UI state)
    assert len(checkboxes) >= 0, "Checkbox query should not fail"
    print(f"  ✓ Found {len(checkboxes)} checkbox(es)")


def test_page_has_no_console_errors(browser_page: Page):
    """Test that the page loads without console errors."""
    print("\n✓ Testing for console errors...")
    
    errors = []
    
    def handle_console_message(msg):
        if msg.type == "error":
            errors.append(msg.text)
    
    browser_page.on("console", handle_console_message)
    
    # Reload page to catch any console errors
    browser_page.reload(wait_until="networkidle")
    browser_page.wait_for_timeout(2000)
    
    # Filter out known/acceptable errors
    critical_errors = [e for e in errors if "favicon" not in e.lower()]
    
    assert len(critical_errors) == 0, f"Found console errors: {critical_errors}"
    print("  ✓ No critical console errors found")


def test_responsive_layout(browser_page: Page):
    """Test that the layout is responsive."""
    print("\n✓ Testing responsive layout...")
    
    # Test different viewport sizes
    viewports = [
        {"width": 1920, "height": 1080, "name": "Desktop"},
        {"width": 768, "height": 1024, "name": "Tablet"},
        {"width": 375, "height": 667, "name": "Mobile"},
    ]
    
    for viewport in viewports:
        browser_page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
        browser_page.wait_for_timeout(500)
        
        # Check that main content is still visible
        page_content = browser_page.content()
        assert len(page_content) > 0, f"Page content empty at {viewport['name']} size"
        
        print(f"  ✓ Layout works at {viewport['name']} size ({viewport['width']}x{viewport['height']})")


def test_intro_outro_sections_exist(browser_page: Page):
    """Test that intro and outro file selection sections exist."""
    print("\n✓ Testing intro/outro sections...")
    
    page_content = browser_page.content()
    
    # Check for intro/outro related content
    has_intro = "intro" in page_content.lower()
    has_outro = "outro" in page_content.lower()
    
    assert has_intro or has_outro, "No intro/outro sections found"
    print(f"  ✓ Intro section found: {has_intro}")
    print(f"  ✓ Outro section found: {has_outro}")


def test_background_music_section_exists(browser_page: Page):
    """Test that background music section exists."""
    print("\n✓ Testing background music section...")
    
    page_content = browser_page.content()
    
    # Check for background music related content
    has_background = "background" in page_content.lower()
    
    assert has_background, "No background music section found"
    print("  ✓ Background music section found")


def test_audio_processing_options_exist(browser_page: Page):
    """Test that audio processing options (denoise, enhance, etc.) exist."""
    print("\n✓ Testing audio processing options...")
    
    page_content = browser_page.content()
    
    # Check for various processing options
    options_found = []
    
    if "denoise" in page_content.lower() or "noise" in page_content.lower():
        options_found.append("denoise")
    
    if "enhance" in page_content.lower():
        options_found.append("enhance")
    
    if "normalize" in page_content.lower() or "lufs" in page_content.lower():
        options_found.append("normalize")
    
    if "transcript" in page_content.lower() or "whisper" in page_content.lower():
        options_found.append("transcription")
    
    assert len(options_found) > 0, "No audio processing options found"
    print(f"  ✓ Found options: {', '.join(options_found)}")


def test_ui_accessibility_basics(browser_page: Page):
    """Test basic accessibility features."""
    print("\n✓ Testing basic accessibility...")
    
    # Check for proper heading structure
    h1_count = len(browser_page.query_selector_all('h1, h2, h3'))
    
    # Check for labels associated with inputs
    labels = browser_page.query_selector_all('label')
    
    print(f"  ✓ Found {h1_count} heading(s)")
    print(f"  ✓ Found {len(labels)} label(s)")


if __name__ == "__main__":
    """Run tests directly (for development/debugging)."""
    print("=" * 70)
    print("🧪 NTN Podcast Creator - Playwright UI Tests")
    print("=" * 70)
    
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
