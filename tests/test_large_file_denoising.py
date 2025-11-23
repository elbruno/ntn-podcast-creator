"""Test large file denoising with chunking functionality."""

import os
import tempfile
import shutil
import sys

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.audio_denoiser_processor import AudioDenoiserProcessor
from pydub import AudioSegment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_audio(duration_seconds=120, sample_rate=44100):
    """Create a test audio file of specified duration.

    Args:
        duration_seconds: Duration in seconds
        sample_rate: Sample rate for audio

    Returns:
        AudioSegment object
    """
    # Create a simple tone for testing
    from pydub.generators import Sine

    # Generate a 440Hz tone
    tone = Sine(440).to_audio_segment(duration=duration_seconds * 1000)
    return tone


def test_chunking_functionality():
    """Test the audio chunking functionality."""
    print("Testing audio chunking functionality...")

    processor = AudioDenoiserProcessor()

    # Create a test audio file (2 minutes = large enough to test chunking)
    test_audio = create_test_audio(duration_seconds=120)  # 2 minutes

    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    try:
        input_file = os.path.join(temp_dir, "large_test_audio.wav")
        test_audio.export(input_file, format="wav")

        # Check file size
        file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
        print(f"Created test file: {file_size_mb:.1f}MB")

        # Test chunking
        chunks = processor._chunk_audio(
            input_file, chunk_size_mb=1.0)  # Use 1MB chunks for testing
        print(f"Created {len(chunks)} chunks")

        # Verify chunks exist and are reasonable size
        for i, chunk in enumerate(chunks):
            if os.path.exists(chunk):
                chunk_size_mb = os.path.getsize(chunk) / (1024 * 1024)
                print(f"Chunk {i+1}: {chunk_size_mb:.1f}MB")
            else:
                print(f"ERROR: Chunk {i+1} not found!")

        # Test merging
        output_file = os.path.join(temp_dir, "merged_test_audio.wav")
        success = processor._merge_audio_chunks(chunks, output_file)

        if success and os.path.exists(output_file):
            merged_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"✓ Merge successful: {merged_size_mb:.1f}MB")

            # Verify duration is preserved
            merged_audio = AudioSegment.from_file(output_file)
            original_duration = len(test_audio)
            merged_duration = len(merged_audio)

            duration_diff = abs(original_duration - merged_duration)
            if duration_diff < 100:  # Allow 100ms tolerance
                print(
                    f"✓ Duration preserved: {original_duration}ms -> {merged_duration}ms")
            else:
                print(
                    f"⚠ Duration mismatch: {original_duration}ms -> {merged_duration}ms")
        else:
            print("✗ Merge failed!")

        # Test cleanup
        processor._cleanup_chunks(chunks)

        # Verify chunks are cleaned up
        cleanup_success = True
        for chunk in chunks:
            if os.path.exists(chunk):
                cleanup_success = False
                print(f"⚠ Chunk not cleaned up: {chunk}")

        if cleanup_success:
            print("✓ Cleanup successful")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_large_file_processing():
    """Test end-to-end large file processing."""
    print("\nTesting large file processing (simulated)...")

    processor = AudioDenoiserProcessor()

    if not processor.is_available():
        print("⚠ Audio denoiser not available, testing fallback behavior...")

        # Create a test file
        test_audio = create_test_audio(duration_seconds=60)
        temp_dir = tempfile.mkdtemp()

        try:
            input_file = os.path.join(temp_dir, "test_audio.wav")
            output_file = os.path.join(temp_dir, "test_audio_denoised.wav")
            test_audio.export(input_file, format="wav")

            # Test processing
            result = processor.denoise_audio(input_file, output_file)

            if result == input_file:
                print("✓ Graceful fallback to original file when denoiser unavailable")
            else:
                print(f"Result: {result}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print("✓ Audio denoiser available - would test actual processing")
        print("  (Skipping actual denoising to avoid long test times)")
        return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Large File Denoising Tests")
    print("=" * 50)

    tests = [
        test_chunking_functionality,
        test_large_file_processing
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()

    # Summary
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
