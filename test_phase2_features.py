#!/usr/bin/env python3
"""Test script for Phase 2 audio processing features."""

import os
import sys
import tempfile
from features.noise_reducer import NoiseReducer, reduce_noise
from features.lufs_normalizer import LUFSNormalizer, normalize_audio_lufs
from features.whisper_transcriber import WhisperTranscriber, transcribe_audio

# Test file configuration
TEST_AUDIO_FILE = "audios/test/test_brunos_project.mp3"

def test_noise_reducer():
    """Test noise reduction with different methods."""
    print("\n" + "="*60)
    print("Testing Noise Reduction")
    print("="*60)
    
    # Use test audio file
    if not os.path.exists(TEST_AUDIO_FILE):
        print(f"✗ Test file not found: {TEST_AUDIO_FILE}")
        return False
    
    reducer = NoiseReducer()
    temp_dir = tempfile.mkdtemp()
    
    # Test spectral method
    if reducer.is_noisereduce_available():
        print("\n1. Testing Spectral Gating (noisereduce)...")
        output = os.path.join(temp_dir, "test_spectral.wav")
        result = reducer.reduce_noise_spectral(TEST_AUDIO_FILE, output)
        if result and os.path.exists(result):
            size = os.path.getsize(result) / (1024 * 1024)
            print(f"✓ Spectral reduction succeeded: {size:.2f}MB")
        else:
            print("✗ Spectral reduction failed")
    else:
        print("✗ noisereduce not available")
    
    # Test RNNoise method
    if reducer.is_ffmpeg_rnnoise_available():
        print("\n2. Testing FFmpeg RNNoise...")
        output = os.path.join(temp_dir, "test_rnnoise.wav")
        result = reducer.reduce_noise_rnnoise(TEST_AUDIO_FILE, output)
        if result and os.path.exists(result):
            size = os.path.getsize(result) / (1024 * 1024)
            print(f"✓ RNNoise reduction succeeded: {size:.2f}MB")
        else:
            print("✗ RNNoise reduction failed")
    else:
        print("✗ FFmpeg RNNoise not available")
    
    return True

def test_lufs_normalizer():
    """Test LUFS normalization."""
    print("\n" + "="*60)
    print("Testing LUFS Normalization")
    print("="*60)
    
    if not os.path.exists(TEST_AUDIO_FILE):
        print(f"✗ Test file not found: {TEST_AUDIO_FILE}")
        return False
    
    normalizer = LUFSNormalizer()
    if not normalizer.is_available():
        print("✗ FFmpeg not available for LUFS normalization")
        return False
    
    print("\nNormalizing to -16 LUFS (podcast standard)...")
    temp_dir = tempfile.mkdtemp()
    output = os.path.join(temp_dir, "test_normalized.wav")
    
    result = normalizer.normalize_lufs(
        TEST_AUDIO_FILE,
        output,
        target_lufs=-16.0,
        two_pass=True
    )
    
    if result and os.path.exists(result):
        size = os.path.getsize(result) / (1024 * 1024)
        print(f"✓ LUFS normalization succeeded: {size:.2f}MB")
        return True
    else:
        print("✗ LUFS normalization failed")
        return False

def test_whisper_transcriber():
    """Test Whisper transcription."""
    print("\n" + "="*60)
    print("Testing Whisper Transcription")
    print("="*60)
    
    if not os.path.exists(TEST_AUDIO_FILE):
        print(f"✗ Test file not found: {TEST_AUDIO_FILE}")
        return False
    
    print("\nInitializing Whisper (tiny model for quick test)...")
    print("Note: First run will download the model (~40MB)")
    
    try:
        transcriber = WhisperTranscriber(model_size="tiny")
        if not transcriber.is_available():
            print("✗ Whisper not available")
            return False
        
        print("\nTranscribing audio (this may take a minute)...")
        temp_dir = tempfile.mkdtemp()
        output = os.path.join(temp_dir, "test_transcript.txt")
        
        result = transcriber.transcribe(TEST_AUDIO_FILE, output)
        
        if result and os.path.exists(result.get("output_file", "")):
            with open(result["output_file"], 'r') as f:
                transcript = f.read()
            print(f"✓ Transcription succeeded!")
            print(f"  Language: {result.get('language', 'unknown')}")
            print(f"  Text length: {len(transcript)} characters")
            print(f"  Preview: {transcript[:200]}...")
            return True
        else:
            print("✗ Transcription failed")
            return False
    except Exception as e:
        print(f"✗ Transcription failed with error: {e}")
        return False

def main():
    """Run all Phase 2 tests."""
    print("\n" + "="*60)
    print("Phase 2 Audio Processing Features - Test Suite")
    print("="*60)
    
    results = {
        "Noise Reducer": test_noise_reducer(),
        "LUFS Normalizer": test_lufs_normalizer(),
        "Whisper Transcriber": test_whisper_transcriber()
    }
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for feature, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{feature}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All Phase 2 features are working correctly!")
        return 0
    else:
        print("\n✗ Some features failed. Check logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
