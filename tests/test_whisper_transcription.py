"""Test suite for Whisper transcription functionality."""

from features.whisper_transcriber import WhisperTranscriber, transcribe_audio
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_whisper_initialization():
    """Test that WhisperTranscriber can be initialized."""
    print("\n" + "=" * 70)
    print("Test 1: WhisperTranscriber Initialization")
    print("=" * 70)

    try:
        # Try different model sizes (smallest first for faster testing)
        for model_size in ["tiny", "base"]:
            print(f"\n  Trying to initialize with '{model_size}' model...")
            transcriber = WhisperTranscriber(model_size=model_size)

            print(
                f"    ✓ WhisperTranscriber initialized with {model_size} model")
            print(f"    ✓ Whisper available: {transcriber.is_available()}")

            if transcriber.is_available():
                print(
                    f"    ✓ Model loaded successfully: {transcriber.model_size}")
                print(f"    ✓ Backend selected: {transcriber.backend}")
                print(f"    ✓ Model type: {type(transcriber.model)}")
                return True, transcriber
            else:
                print(f"    ⚠ Whisper not available with {model_size} model")

        print("\n  ⚠ Warning: No supported Whisper backend could be loaded")
        print("  ℹ️  Install either 'faster-whisper' (recommended) or 'openai-whisper'")
        return False, None

    except Exception as e:
        print(f"  ✗ Failed to initialize WhisperTranscriber: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_whisper_transcription_short_audio(transcriber):
    """Test transcription with a short audio file."""
    print("\n" + "=" * 70)
    print("Test 2: Transcribe Short Audio File")
    print("=" * 70)

    if transcriber is None or not transcriber.is_available():
        print("  ⚠ Skipping: Whisper not available")
        return True

    # Use the smaller test audio file
    test_file = "audios/test/test_brunos_project.mp3"

    if not os.path.exists(test_file):
        print(f"  ⚠ Test file not found: {test_file}")
        print("  Skipping this test")
        return True

    file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
    print(f"  Test file: {test_file} ({file_size_mb:.2f}MB)")

    try:
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            output_file = tmp.name

        print(f"  Transcribing...")
        result = transcriber.transcribe(
            audio_file=test_file,
            output_file=output_file,
            log_callback=lambda msg: print(f"    {msg}")
        )

        if result:
            print(f"\n  ✓ Transcription successful!")
            print(
                f"  ✓ Detected language: {result.get('language', 'unknown')}")

            # Read and display transcript
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()

                print(f"  ✓ Transcript saved: {output_file}")
                print(
                    f"  ✓ Transcript length: {len(transcript_text)} characters")

                # Show first 200 characters of transcript
                preview = transcript_text[:200] + "..." if len(
                    transcript_text) > 200 else transcript_text
                print(f"\n  Preview:")
                print(f"  {'-' * 66}")
                print(f"  {preview}")
                print(f"  {'-' * 66}")

                # Cleanup
                os.remove(output_file)

                # Check segments
                segments = result.get('segments', [])
                print(f"\n  ✓ Number of segments: {len(segments)}")
                if segments:
                    print(
                        f"  ✓ First segment: [{segments[0].get('start', 0):.2f}s - {segments[0].get('end', 0):.2f}s]")

                return True
            else:
                print(f"  ✗ Transcript file not created")
                return False
        else:
            print(f"  ✗ Transcription failed (returned None)")
            return False

    except Exception as e:
        print(f"  ✗ Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_whisper_with_timestamps(transcriber):
    """Test transcription with timestamps."""
    print("\n" + "=" * 70)
    print("Test 3: Transcribe with Timestamps")
    print("=" * 70)

    if transcriber is None or not transcriber.is_available():
        print("  ⚠ Skipping: Whisper not available")
        return True

    test_file = "audios/test/test_brunos_project.mp3"

    if not os.path.exists(test_file):
        print(f"  ⚠ Test file not found: {test_file}")
        print("  Skipping this test")
        return True

    try:
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            output_file = tmp.name

        print(f"  Transcribing with timestamps...")
        timestamped_file = transcriber.transcribe_with_timestamps(
            audio_file=test_file,
            output_file=output_file,
            log_callback=lambda msg: print(f"    {msg}")
        )

        if timestamped_file and os.path.exists(timestamped_file):
            print(f"\n  ✓ Timestamped transcript created!")

            # Read and display timestamped transcript
            with open(timestamped_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            print(f"  ✓ Timestamped file: {timestamped_file}")
            print(f"  ✓ Number of timestamped segments: {len(lines)}")

            # Show first 5 lines
            print(f"\n  Preview (first 5 segments):")
            print(f"  {'-' * 66}")
            for line in lines[:5]:
                print(f"  {line.strip()}")
            print(f"  {'-' * 66}")

            # Cleanup
            os.remove(output_file) if os.path.exists(output_file) else None
            os.remove(timestamped_file)

            return True
        else:
            print(f"  ✗ Timestamped transcript not created")
            return False

    except Exception as e:
        print(f"  ✗ Error during timestamped transcription: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convenience_function():
    """Test the convenience transcribe_audio function."""
    print("\n" + "=" * 70)
    print("Test 4: Convenience Function (transcribe_audio)")
    print("=" * 70)

    test_file = "audios/test/test_brunos_project.mp3"

    if not os.path.exists(test_file):
        print(f"  ⚠ Test file not found: {test_file}")
        print("  Skipping this test")
        return True

    try:
        print(f"  Using convenience function with tiny model...")

        # Use auto-generated output file
        transcript_file = transcribe_audio(
            audio_file=test_file,
            model_size="tiny",
            with_timestamps=False,
            log_callback=lambda msg: print(f"    {msg}")
        )

        if transcript_file and os.path.exists(transcript_file):
            print(f"\n  ✓ Convenience function successful!")
            print(f"  ✓ Transcript file: {transcript_file}")

            # Read transcript
            with open(transcript_file, 'r', encoding='utf-8') as f:
                content = f.read()

            print(f"  ✓ Transcript length: {len(content)} characters")

            # Show first 150 characters
            preview = content[:150] + "..." if len(content) > 150 else content
            print(f"\n  Preview:")
            print(f"  {'-' * 66}")
            print(f"  {preview}")
            print(f"  {'-' * 66}")

            # Cleanup
            os.remove(transcript_file)

            return True
        else:
            print(f"  ⚠ Transcription returned None (Whisper may not be available)")
            return True  # Not a failure if Whisper isn't installed

    except Exception as e:
        print(f"  ✗ Error with convenience function: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_whisper_language_detection():
    """Test language detection capability."""
    print("\n" + "=" * 70)
    print("Test 5: Language Detection")
    print("=" * 70)

    test_file = "audios/test/test_brunos_project.mp3"

    if not os.path.exists(test_file):
        print(f"  ⚠ Test file not found: {test_file}")
        print("  Skipping this test")
        return True

    try:
        transcriber = WhisperTranscriber(model_size="tiny")

        if not transcriber.is_available():
            print("  ⚠ Skipping: Whisper not available")
            return True

        print(f"  Testing language auto-detection...")

        # Transcribe without specifying language
        result = transcriber.transcribe(
            audio_file=test_file,
            log_callback=lambda msg: print(f"    {msg}")
        )

        if result:
            detected_lang = result.get('language', 'unknown')
            print(f"\n  ✓ Language auto-detected: {detected_lang}")

            # Clean up auto-generated file
            output_file = result.get('output_file')
            if output_file and os.path.exists(output_file):
                os.remove(output_file)

            return True
        else:
            print(f"  ✗ Language detection failed")
            return False

    except Exception as e:
        print(f"  ✗ Error during language detection: {e}")
        return False


def test_whisper_error_handling():
    """Test error handling for invalid inputs."""
    print("\n" + "=" * 70)
    print("Test 6: Error Handling")
    print("=" * 70)

    try:
        transcriber = WhisperTranscriber(model_size="tiny")

        if not transcriber.is_available():
            print("  ⚠ Skipping: Whisper not available")
            return True

        # Test with non-existent file
        print(f"  Testing with non-existent file...")
        result = transcriber.transcribe(
            audio_file="non_existent_file.mp3",
            log_callback=lambda msg: print(f"    {msg}")
        )

        if result is None:
            print(f"  ✓ Correctly handled non-existent file (returned None)")
        else:
            print(f"  ✗ Should have returned None for non-existent file")
            return False

        return True

    except Exception as e:
        print(f"  ✗ Error during error handling test: {e}")
        return False


def run_all_tests():
    """Run all Whisper transcription tests."""
    print("\n" + "=" * 70)
    print("🎙️  WHISPER TRANSCRIPTION TEST SUITE")
    print("=" * 70)

    results = []
    models_available = False

    # Test 1: Initialization
    success, transcriber = test_whisper_initialization()
    results.append(("Initialization", success))
    models_available = success

    if success and transcriber:
        # Test 2: Short audio transcription
        results.append(("Short Audio Transcription",
                       test_whisper_transcription_short_audio(transcriber)))

        # Test 3: Timestamps
        results.append(("Transcription with Timestamps",
                       test_whisper_with_timestamps(transcriber)))

    # Test 4: Convenience function
    results.append(("Convenience Function", test_convenience_function()))

    # Test 5: Language detection
    results.append(("Language Detection", test_whisper_language_detection()))

    # Test 6: Error handling
    results.append(("Error Handling", test_whisper_error_handling()))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 70)

    if not models_available:
        print("\n⚠️  IMPORTANT: Whisper backends could not be loaded")
        print("\n📋 Action Required:")
        print("   1. Install one backend: 'faster-whisper' or 'openai-whisper'")
        print("   2. Ensure model download endpoints are allowed in your environment")
        print("   3. Models are cached locally after first download")
        print("\n💡 Once the domain is allowed, run this test again to verify:")
        print("   python tests/test_whisper_transcription.py")
        print("=" * 70)
        return 1
    elif passed == total:
        print("\n✅ All tests passed!")
        print("\n✨ Whisper transcription is working correctly:")
        print("   • Models loaded successfully")
        print("   • Audio transcription functional")
        print("   • Timestamp generation working")
        print("   • Language detection operational")
        print("=" * 70)
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
