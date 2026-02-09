#!/usr/bin/env python3
"""Quick test script for voice enhancement feature."""

import os
import sys

# Add features to path
sys.path.insert(0, os.path.dirname(__file__))

from features.voice_enhancer import VoiceEnhancer, enhance_voice


def test_voice_enhancer_initialization():
    """Test that VoiceEnhancer initializes correctly."""
    print("Testing VoiceEnhancer initialization...")
    enhancer = VoiceEnhancer()
    
    # Check if FFmpeg is available
    ffmpeg_available = enhancer.is_available()
    print(f"  FFmpeg available: {ffmpeg_available}")
    
    if not ffmpeg_available:
        print("  ⚠️  FFmpeg not available - voice enhancement will be disabled")
    else:
        print("  ✓ VoiceEnhancer initialized successfully")
    
    return ffmpeg_available


def test_filter_chain_generation():
    """Test that filter chains are generated correctly."""
    print("\nTesting filter chain generation...")
    enhancer = VoiceEnhancer()
    
    presets = ["podcast", "light", "aggressive"]
    for preset in presets:
        chain = enhancer._build_filter_chain(preset)
        print(f"  {preset} preset: {len(chain)} characters")
        
        # Verify it contains expected filters
        assert "highpass" in chain, f"Missing highpass filter in {preset} preset"
        assert "lowpass" in chain, f"Missing lowpass filter in {preset} preset"
        assert "equalizer" in chain, f"Missing equalizer in {preset} preset"
        assert "compand" in chain, f"Missing compand in {preset} preset"
        
        if preset in ["podcast", "aggressive"]:
            assert "deesser" in chain, f"Missing deesser in {preset} preset"
    
    print("  ✓ All filter chains generated correctly")


def test_convenience_function():
    """Test the convenience function."""
    print("\nTesting convenience function...")
    
    # Just verify the function is accessible
    assert callable(enhance_voice), "enhance_voice function not callable"
    print("  ✓ Convenience function accessible")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Voice Enhancement Feature - Quick Test")
    print("=" * 60)
    
    try:
        # Test initialization
        ffmpeg_available = test_voice_enhancer_initialization()
        
        # Test filter chain generation (always works, doesn't need FFmpeg)
        test_filter_chain_generation()
        
        # Test convenience function
        test_convenience_function()
        
        print("\n" + "=" * 60)
        if ffmpeg_available:
            print("✅ All tests passed! Voice enhancement is ready to use.")
        else:
            print("⚠️  Tests passed, but FFmpeg is not available.")
            print("   Voice enhancement will be disabled at runtime.")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
