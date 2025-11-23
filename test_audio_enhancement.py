"""Test script for Adobe audio enhancement feature."""

import os
import sys
import tempfile
from adobe_audio_enhancer import AdobeAudioEnhancer, enhance_audio_file
from config_manager import ConfigManager


def test_enhancer_initialization():
    """Test AdobeAudioEnhancer initialization."""
    print("Testing AdobeAudioEnhancer initialization...")
    enhancer = AdobeAudioEnhancer()
    assert enhancer is not None
    assert enhancer.enhance_url == "https://podcast.adobe.com/enhance"
    print("✓ AdobeAudioEnhancer initialized successfully")


def test_enhancer_availability():
    """Test service availability check."""
    print("\nTesting service availability check...")
    enhancer = AdobeAudioEnhancer(playwright_available=True)
    assert enhancer.is_available() == True
    
    enhancer_unavailable = AdobeAudioEnhancer(playwright_available=False)
    assert enhancer_unavailable.is_available() == False
    print("✓ Service availability check works correctly")


def test_config_manager():
    """Test config manager enhancement settings."""
    print("\nTesting config manager enhancement settings...")
    config = ConfigManager("test_config.json")
    
    # Test default value
    assert config.get_enhance_audio() == False
    print("  ✓ Default enhancement setting is False")
    
    # Test setting to True
    config.set_enhance_audio(True)
    assert config.get_enhance_audio() == True
    print("  ✓ Can set enhancement to True")
    
    # Test setting to False
    config.set_enhance_audio(False)
    assert config.get_enhance_audio() == False
    print("  ✓ Can set enhancement to False")
    
    # Clean up test config
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    print("✓ Config manager enhancement settings work correctly")


def test_enhance_when_disabled():
    """Test enhancement when disabled."""
    print("\nTesting enhancement when disabled...")
    
    # Create a test file using tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_file = f.name
        f.write("test audio content")
    
    try:
        result = enhance_audio_file(test_file, enabled=False)
        assert result == test_file
        print("✓ Enhancement returns original file when disabled")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)


def test_enhance_with_fallback():
    """Test enhancement with fallback to original."""
    print("\nTesting enhancement with fallback...")
    
    # Create a test file using tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_file = f.name
        f.write("test audio content")
    
    try:
        # This should use fallback since we don't have actual audio processing
        result = enhance_audio_file(test_file, enabled=True)
        
        # Should return a path (either enhanced or fallback)
        assert result is not None
        print("✓ Enhancement with fallback works correctly")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        if result and result != test_file and os.path.exists(result):
            os.remove(result)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Adobe Audio Enhancement Feature")
    print("=" * 60)
    
    try:
        test_enhancer_initialization()
        test_enhancer_availability()
        test_config_manager()
        test_enhance_when_disabled()
        test_enhance_with_fallback()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
