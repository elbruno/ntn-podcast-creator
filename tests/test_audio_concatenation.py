"""Tests for audio concatenation functionality."""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.audio_processor import AudioProcessor
from pydub import AudioSegment
from pydub.generators import Sine


def create_test_audio_file(duration_ms: int, frequency: int = 440) -> str:
    """Create a test audio file with a sine wave.
    
    Args:
        duration_ms: Duration in milliseconds
        frequency: Frequency in Hz
        
    Returns:
        Path to created test file
    """
    # Generate sine wave
    sine_wave = Sine(frequency).to_audio_segment(duration=duration_ms)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    # Export to file
    sine_wave.export(temp_path, format="mp3")
    
    return temp_path


def test_concatenate_single_file():
    """Test concatenation with a single file (should return same file)."""
    print("\n✓ Testing concatenation with single file...")
    
    processor = AudioProcessor()
    
    # Create a test audio file
    test_file = create_test_audio_file(1000)  # 1 second
    
    try:
        # Concatenate single file
        result = processor.concatenate_audio_files([test_file])
        
        # Should return the same file
        assert result == test_file, f"Expected {test_file}, got {result}"
        print("  ✓ Single file concatenation works correctly")
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {str(e)}")
        return False
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_concatenate_multiple_files():
    """Test concatenation with multiple files."""
    print("\n✓ Testing concatenation with multiple files...")
    
    processor = AudioProcessor()
    
    # Create multiple test audio files with different durations
    test_files = [
        create_test_audio_file(1000, 440),  # 1 second at 440Hz
        create_test_audio_file(1500, 880),  # 1.5 seconds at 880Hz
        create_test_audio_file(2000, 660),  # 2 seconds at 660Hz
    ]
    
    output_file = None
    
    try:
        # Calculate expected duration
        expected_duration = sum(len(AudioSegment.from_file(f)) for f in test_files)
        
        # Concatenate files
        output_file = processor.concatenate_audio_files(test_files)
        
        # Check that output file exists
        assert os.path.exists(output_file), f"Output file not found: {output_file}"
        
        # Check duration
        result_audio = AudioSegment.from_file(output_file)
        result_duration = len(result_audio)
        
        # Allow 100ms tolerance for encoding differences
        duration_diff = abs(result_duration - expected_duration)
        assert duration_diff < 100, f"Duration mismatch: expected {expected_duration}ms, got {result_duration}ms (diff: {duration_diff}ms)"
        
        print(f"  ✓ Concatenated {len(test_files)} files successfully")
        print(f"  ✓ Total duration: {result_duration}ms (expected: {expected_duration}ms)")
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {str(e)}")
        return False
    finally:
        # Cleanup
        for test_file in test_files:
            if os.path.exists(test_file):
                os.remove(test_file)
        if output_file and os.path.exists(output_file):
            os.remove(output_file)


def test_concatenate_with_callback():
    """Test concatenation with logging callback."""
    print("\n✓ Testing concatenation with logging callback...")
    
    processor = AudioProcessor()
    
    # Create test audio files
    test_files = [
        create_test_audio_file(500, 440),
        create_test_audio_file(500, 880),
    ]
    
    output_file = None
    log_messages = []
    
    def log_callback(message: str):
        log_messages.append(message)
    
    try:
        # Concatenate with callback
        output_file = processor.concatenate_audio_files(
            test_files, 
            log_callback=log_callback
        )
        
        # Check that we got log messages
        assert len(log_messages) > 0, "No log messages received"
        
        # Check that output file exists
        assert os.path.exists(output_file), f"Output file not found: {output_file}"
        
        print(f"  ✓ Received {len(log_messages)} log messages")
        print(f"  ✓ Sample log: {log_messages[0]}")
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {str(e)}")
        return False
    finally:
        # Cleanup
        for test_file in test_files:
            if os.path.exists(test_file):
                os.remove(test_file)
        if output_file and os.path.exists(output_file):
            os.remove(output_file)


def test_concatenate_empty_list():
    """Test concatenation with empty list (should raise error)."""
    print("\n✓ Testing concatenation with empty list...")
    
    processor = AudioProcessor()
    
    try:
        # Try to concatenate empty list
        processor.concatenate_audio_files([])
        print("  ✗ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {str(e)}")
        return True
    except Exception as e:
        print(f"  ✗ Unexpected error: {str(e)}")
        return False


def test_concatenate_with_custom_output():
    """Test concatenation with custom output path."""
    print("\n✓ Testing concatenation with custom output path...")
    
    processor = AudioProcessor()
    
    # Create test audio files
    test_files = [
        create_test_audio_file(500, 440),
        create_test_audio_file(500, 880),
    ]
    
    # Create temporary output path
    output_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    
    try:
        # Concatenate with custom output
        result = processor.concatenate_audio_files(test_files, output_path=output_file)
        
        # Check that result matches output_file
        assert result == output_file, f"Expected {output_file}, got {result}"
        
        # Check that file exists
        assert os.path.exists(output_file), f"Output file not found: {output_file}"
        
        print(f"  ✓ Custom output path works correctly")
        return True
    except Exception as e:
        print(f"  ✗ Test failed: {str(e)}")
        return False
    finally:
        # Cleanup
        for test_file in test_files:
            if os.path.exists(test_file):
                os.remove(test_file)
        if os.path.exists(output_file):
            os.remove(output_file)


def run_all_tests():
    """Run all concatenation tests."""
    print("=" * 60)
    print("Audio Concatenation Tests")
    print("=" * 60)
    
    tests = [
        test_concatenate_single_file,
        test_concatenate_multiple_files,
        test_concatenate_with_callback,
        test_concatenate_empty_list,
        test_concatenate_with_custom_output,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test crashed: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
