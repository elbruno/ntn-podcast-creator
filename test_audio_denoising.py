"""Test script for audio denoising functionality."""

import os
import sys
from audio_denoiser_processor import AudioDenoiserProcessor, denoise_audio_file


def test_audio_denoiser_initialization():
    """Test that AudioDenoiserProcessor can be initialized."""
    print("\n" + "=" * 60)
    print("Test 1: AudioDenoiserProcessor Initialization")
    print("=" * 60)
    
    try:
        processor = AudioDenoiserProcessor()
        print(f"✓ AudioDenoiserProcessor initialized successfully")
        print(f"  Denoiser available: {processor.is_available()}")
        
        if not processor.is_available():
            print("  Note: audio-denoiser library not installed")
            print("  This is expected in environments without the library")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize AudioDenoiserProcessor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_denoise_with_missing_library():
    """Test that denoising gracefully handles missing library."""
    print("\n" + "=" * 60)
    print("Test 2: Graceful Handling of Missing Library")
    print("=" * 60)
    
    test_file = "audios/test/test_brunos_project.mp3"
    
    if not os.path.exists(test_file):
        print(f"⚠ Test file not found: {test_file}")
        print("  Skipping this test")
        return True
    
    try:
        # This should not fail even if library is missing
        result = denoise_audio_file(
            input_file=test_file,
            enabled=True,
            log_callback=print
        )
        
        print(f"✓ denoise_audio_file completed without error")
        print(f"  Returned: {result}")
        
        # Should return original file if library not available
        if result == test_file:
            print("  → Correctly returned original file (library not available)")
        else:
            print(f"  → Returned denoised file: {os.path.basename(result)}")
        
        return True
    except Exception as e:
        print(f"❌ denoise_audio_file failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_denoise_disabled():
    """Test that denoising respects the enabled flag."""
    print("\n" + "=" * 60)
    print("Test 3: Denoising Disabled Flag")
    print("=" * 60)
    
    test_file = "audios/test/test_brunos_project.mp3"
    
    if not os.path.exists(test_file):
        print(f"⚠ Test file not found: {test_file}")
        print("  Skipping this test")
        return True
    
    try:
        result = denoise_audio_file(
            input_file=test_file,
            enabled=False,
            log_callback=print
        )
        
        print(f"✓ denoise_audio_file with enabled=False completed")
        
        if result == test_file:
            print("  ✓ Correctly returned original file when disabled")
            return True
        else:
            print(f"  ❌ Should have returned original file, got: {result}")
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_with_audio_processor():
    """Test integration with AudioProcessor."""
    print("\n" + "=" * 60)
    print("Test 4: Integration with AudioProcessor")
    print("=" * 60)
    
    try:
        from audio_processor import AudioProcessor
        
        processor = AudioProcessor()
        print("✓ AudioProcessor imported successfully")
        
        # Check that create_podcast has the denoise_audio parameter
        import inspect
        sig = inspect.signature(processor.create_podcast)
        params = list(sig.parameters.keys())
        
        if 'denoise_audio' in params:
            print("✓ create_podcast has denoise_audio parameter")
            return True
        else:
            print("❌ create_podcast missing denoise_audio parameter")
            print(f"   Available parameters: {params}")
            return False
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager_integration():
    """Test integration with ConfigManager."""
    print("\n" + "=" * 60)
    print("Test 5: ConfigManager Integration")
    print("=" * 60)
    
    try:
        from config_manager import ConfigManager
        
        config = ConfigManager()
        print("✓ ConfigManager imported successfully")
        
        # Test get_denoise_audio method
        try:
            denoise_setting = config.get_denoise_audio()
            print(f"✓ get_denoise_audio() returned: {denoise_setting}")
            
            # Should default to True
            if denoise_setting is True:
                print("  ✓ Default value is True (as expected)")
            
        except Exception as e:
            print(f"❌ get_denoise_audio() failed: {e}")
            return False
        
        # Test set_denoise_audio method
        try:
            config.set_denoise_audio(False)
            new_setting = config.get_denoise_audio()
            
            if new_setting is False:
                print("✓ set_denoise_audio(False) works correctly")
            else:
                print(f"❌ set_denoise_audio(False) failed, got: {new_setting}")
                return False
            
            # Restore default
            config.set_denoise_audio(True)
            print("✓ Restored default setting")
            
        except Exception as e:
            print(f"❌ set_denoise_audio() failed: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ ConfigManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Audio Denoising Feature Test Suite")
    print("=" * 60)
    
    tests = [
        test_audio_denoiser_initialization,
        test_denoise_with_missing_library,
        test_denoise_disabled,
        test_integration_with_audio_processor,
        test_config_manager_integration,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
