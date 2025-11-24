"""Simple standalone test to verify Playwright test structure.

This test verifies that the Playwright test module loads correctly
and has the expected test functions defined.
"""

import os
import sys
import importlib.util

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_playwright_module_imports():
    """Test that the Playwright test module can be imported."""
    print("\n✓ Testing Playwright test module imports...")
    
    test_module_path = os.path.join(
        os.path.dirname(__file__), 
        "test_ui_playwright.py"
    )
    
    spec = importlib.util.spec_from_file_location("test_ui_playwright", test_module_path)
    module = importlib.util.module_from_spec(spec)
    
    spec.loader.exec_module(module)
    print("  ✓ Playwright test module imported successfully")
    assert module is not None


def test_playwright_test_functions_exist():
    """Test that expected test functions are defined in the Playwright module."""
    print("\n✓ Testing Playwright test functions exist...")
    
    test_module_path = os.path.join(
        os.path.dirname(__file__), 
        "test_ui_playwright.py"
    )
    
    spec = importlib.util.spec_from_file_location("test_ui_playwright", test_module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    expected_tests = [
        "test_ui_loads_successfully",
        "test_podcast_creation_tab_visible",
        "test_upload_voice_file_input_exists",
        "test_output_name_input_exists",
        "test_create_podcast_button_exists",
        "test_volume_slider_exists",
        "test_checkboxes_exist",
        "test_page_has_no_console_errors",
        "test_responsive_layout",
        "test_intro_outro_sections_exist",
        "test_background_music_section_exists",
        "test_audio_processing_options_exist",
        "test_ui_accessibility_basics",
    ]
    
    found_tests = []
    for test_name in expected_tests:
        if hasattr(module, test_name):
            found_tests.append(test_name)
            print(f"  ✓ Found test: {test_name}")
    
    print(f"\n  ✓ Found {len(found_tests)}/{len(expected_tests)} expected test functions")
    assert len(found_tests) == len(expected_tests)


def test_playwright_fixtures_exist():
    """Test that Playwright fixtures are properly defined."""
    print("\n✓ Testing Playwright fixtures...")
    
    test_module_path = os.path.join(
        os.path.dirname(__file__), 
        "test_ui_playwright.py"
    )
    
    spec = importlib.util.spec_from_file_location("test_ui_playwright", test_module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Check for fixture functions
    has_gradio_app_fixture = hasattr(module, "gradio_app")
    has_browser_page_fixture = hasattr(module, "browser_page")
    
    print(f"  ✓ gradio_app fixture: {has_gradio_app_fixture}")
    print(f"  ✓ browser_page fixture: {has_browser_page_fixture}")
    
    assert has_gradio_app_fixture and has_browser_page_fixture


def test_gradio_app_class_exists():
    """Test that GradioApp helper class exists."""
    print("\n✓ Testing GradioApp helper class...")
    
    test_module_path = os.path.join(
        os.path.dirname(__file__), 
        "test_ui_playwright.py"
    )
    
    spec = importlib.util.spec_from_file_location("test_ui_playwright", test_module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    assert hasattr(module, "GradioApp"), "GradioApp class not found"
    
    gradio_app_class = getattr(module, "GradioApp")
    has_start = hasattr(gradio_app_class, "start")
    has_stop = hasattr(gradio_app_class, "stop")
    print(f"  ✓ GradioApp class found")
    print(f"  ✓ start method: {has_start}")
    print(f"  ✓ stop method: {has_stop}")
    assert has_start and has_stop


if __name__ == "__main__":
    """Run verification tests."""
    print("=" * 70)
    print("🧪 Playwright Test Structure Verification")
    print("=" * 70)
    
    results = []
    results.append(("Module imports", test_playwright_module_imports()))
    results.append(("Test functions exist", test_playwright_test_functions_exist()))
    results.append(("Fixtures exist", test_playwright_fixtures_exist()))
    results.append(("GradioApp class", test_gradio_app_class_exists()))
    
    print("\n" + "=" * 70)
    print("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"  ✓ Passed: {passed}/{total}")
    if passed < total:
        print(f"  ✗ Failed: {total - passed}/{total}")
    print("=" * 70)
    
    sys.exit(0 if passed == total else 1)
