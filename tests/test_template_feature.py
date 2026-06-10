#!/usr/bin/env python3
"""Test script for template feature.

This script tests the template management functionality without requiring
the full Gradio UI or audio processing dependencies.
"""

import sys
import os
import json

# Add project to path
sys.path.insert(0, '/home/runner/work/ntn-podcast-creator/ntn-podcast-creator')

# Import template manager directly
import importlib.util
spec = importlib.util.spec_from_file_location('template_manager', 'features/template_manager.py')
template_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template_manager_module)

spec2 = importlib.util.spec_from_file_location('config_manager', 'features/config_manager.py')
config_manager_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(config_manager_module)


def test_template_manager():
    """Test template manager functionality."""
    print("=" * 60)
    print("Testing Template Manager")
    print("=" * 60)
    
    tm = template_manager_module.TemplateManager()
    print("✓ TemplateManager initialized")
    
    # Test 1: Save template
    print("\n--- Test 1: Save Template ---")
    test_settings = {
        'intro_file': 'audios/intro_audio/test.mp3',
        'outro_file': 'audios/outro_audio/test.mp3',
        'background_tracks': ['track1.mp3', 'track2.mp3'],
        'background_volume': 15,
        'track_volumes': {'track1.mp3': 10, 'track2.mp3': 20},
        'denoise_audio': True,
        'denoise_method': 'audio_denoiser',
        'enhance_audio': False,
        'normalize_lufs': True,
        'target_lufs': -16.0,
        'generate_transcript': False,
        'whisper_model': 'base'
    }
    success, msg = tm.save_template('My Weekly Podcast', test_settings)
    print(f"Save result: {success}")
    print(f"Message: {msg}")
    assert success, "Failed to save template"
    print("✓ Template saved successfully")
    
    # Test 2: List templates
    print("\n--- Test 2: List Templates ---")
    templates = tm.list_templates()
    print(f"Available templates: {templates}")
    assert 'My Weekly Podcast' in templates, "Template not in list"
    print("✓ Template appears in list")
    
    # Test 3: Get template info
    print("\n--- Test 3: Get Template Info ---")
    info = tm.get_template_info('My Weekly Podcast')
    print(f"Template info: {json.dumps(info, indent=2)}")
    assert info is not None, "Failed to get template info"
    assert info['name'] == 'My Weekly Podcast', "Template name mismatch"
    print("✓ Template info retrieved")
    
    # Test 4: Load template
    print("\n--- Test 4: Load Template ---")
    settings, msg = tm.load_template('My Weekly Podcast')
    print(f"Load result: {msg}")
    print(f"Settings keys: {list(settings.keys())}")
    assert settings is not None, "Failed to load template"
    assert settings['background_volume'] == 15, "Settings not restored correctly"
    assert settings['denoise_audio'] == True, "Denoise setting not restored"
    print("✓ Template loaded successfully")
    
    # Test 5: Save another template
    print("\n--- Test 5: Save Second Template ---")
    test_settings2 = {
        'intro_file': 'audios/intro_audio/test2.mp3',
        'outro_file': None,
        'background_tracks': [],
        'background_volume': 5,
        'denoise_audio': False,
    }
    success, msg = tm.save_template('Simple Template', test_settings2)
    print(f"Save result: {success}")
    assert success, "Failed to save second template"
    print("✓ Second template saved")
    
    # Test 6: List multiple templates
    print("\n--- Test 6: List Multiple Templates ---")
    templates = tm.list_templates()
    print(f"Available templates: {templates}")
    assert len(templates) >= 2, "Not all templates in list"
    assert 'My Weekly Podcast' in templates, "First template missing"
    assert 'Simple Template' in templates, "Second template missing"
    print("✓ Multiple templates listed")
    
    # Test 7: Delete template
    print("\n--- Test 7: Delete Template ---")
    success, msg = tm.delete_template('Simple Template')
    print(f"Delete result: {success}")
    print(f"Message: {msg}")
    assert success, "Failed to delete template"
    templates = tm.list_templates()
    assert 'Simple Template' not in templates, "Template still in list after deletion"
    print("✓ Template deleted successfully")
    
    # Cleanup
    print("\n--- Cleanup ---")
    tm.delete_template('My Weekly Podcast')
    print("✓ Cleanup complete")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


def test_config_manager_integration():
    """Test config manager template integration."""
    print("\n" + "=" * 60)
    print("Testing Config Manager Integration")
    print("=" * 60)
    
    cm = config_manager_module.ConfigManager("core/test_config.json")
    print("✓ ConfigManager initialized")
    
    # Test 1: Get template settings
    print("\n--- Test 1: Get Template Settings ---")
    settings = cm.get_template_settings()
    print(f"Template settings keys: {list(settings.keys())}")
    assert 'intro_file' in settings, "intro_file missing"
    assert 'denoise_audio' in settings, "denoise_audio missing"
    assert 'whisper_model' in settings, "whisper_model missing"
    print("✓ Template settings retrieved")
    
    # Test 2: Active template
    print("\n--- Test 2: Active Template ---")
    cm.set_active_template('Test Template')
    active = cm.get_active_template()
    print(f"Active template: {active}")
    assert active == 'Test Template', "Active template not set"
    print("✓ Active template works")
    
    # Test 3: Apply template settings
    print("\n--- Test 3: Apply Template Settings ---")
    test_settings = {
        'background_volume': 25,
        'denoise_audio': False,
        'denoise_method': 'spectral',
        'normalize_lufs': True,
        'target_lufs': -14.0
    }
    cm.apply_template_settings(test_settings)
    assert cm.get_volume() == 25, "Volume not applied"
    assert cm.get_denoise_audio() == False, "Denoise not applied"
    assert cm.get_denoise_method() == 'spectral', "Denoise method not applied"
    assert cm.get_normalize_lufs() == True, "Normalize not applied"
    assert cm.get_target_lufs() == -14.0, "Target LUFS not applied"
    print("✓ Template settings applied")
    
    # Cleanup
    if os.path.exists("core/test_config.json"):
        os.remove("core/test_config.json")
    
    print("\n" + "=" * 60)
    print("Integration tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_template_manager()
        test_config_manager_integration()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓✓✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
