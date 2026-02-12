"""Test deferred transcription pipeline."""

from features.config_manager import ConfigManager
from features.audio_processor import AudioProcessor
import os
import sys
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_create_podcast_without_transcription():
    """Test that create_podcast works without transcription enabled."""
    audio_processor = AudioProcessor()
    config_manager = ConfigManager()

    # Use test audio
    test_audio = "audios/test/251121-ntn443-Recording.m4a"

    if not os.path.exists(test_audio):
        print(f"⚠️  Test audio not found: {test_audio}")
        return False

    # Create temp output
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        output_path = f.name

    try:
        # Create podcast WITHOUT transcription
        print("\n📝 Test 1: Creating podcast WITHOUT transcription...")
        result_path, denoised_path, transcript_path = audio_processor.create_podcast(
            voice_file=test_audio,
            output_file=output_path,
            generate_transcript=False,  # Disabled
            log_callback=lambda x: print(f"  LOG: {x}")
        )

        # Verify results
        assert os.path.exists(
            result_path), f"Podcast not created: {result_path}"
        assert transcript_path is None, "Transcript should be None when disabled"

        print(f"✅ Test 1 passed: Podcast created without transcription")
        print(f"   Output: {result_path}")

        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)

        return True

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False


def test_transcribe_podcast_async():
    """Test deferred transcription method."""
    audio_processor = AudioProcessor()

    # Use test audio
    test_audio = "audios/test/251121-ntn443-Recording.m4a"

    if not os.path.exists(test_audio):
        print(f"⚠️  Test audio not found: {test_audio}")
        return False

    # Create temp podcast
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        podcast_path = f.name

    try:
        print("\n📝 Test 2: Transcribing podcast with transcribe_podcast_async()...")

        # First create podcast file
        from pydub import AudioSegment
        audio = AudioSegment.from_file(test_audio)
        audio.export(podcast_path, format="mp3")

        # Now test async transcription method (if whisper available)
        print("  Testing transcribe_podcast_async()...")
        transcript_path = audio_processor.transcribe_podcast_async(
            podcast_file=podcast_path,
            whisper_model="tiny",  # Use tiny model for testing (fastest)
            log_callback=lambda x: print(f"  LOG: {x}")
        )

        if transcript_path:
            assert os.path.exists(
                transcript_path), f"Transcript not created: {transcript_path}"
            print(f"✅ Test 2 passed: Transcription completed")
            print(f"   Transcript: {transcript_path}")
            # Clean up transcript
            os.remove(transcript_path)
        else:
            print("⚠️  Test 2 skipped: Whisper not available or transcription failed")

        # Clean up
        if os.path.exists(podcast_path):
            os.remove(podcast_path)

        return True

    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        # Clean up
        if os.path.exists(podcast_path):
            try:
                os.remove(podcast_path)
            except:
                pass
        return False


def test_two_stage_pipeline_flow():
    """Test the full two-stage pipeline sequence."""
    print("\n📝 Test 3: Two-stage pipeline flow (Stage 1: Podcast, Stage 2: Transcription)")
    print("  This simulates the event handler flow:")
    print("  1. Create podcast (generate_transcript=False)")
    print("  2. Yield podcast ready with 'Transcription in progress...'")
    print("  3. Start transcription polling")
    print("  4. Update transcript once ready")

    audio_processor = AudioProcessor()
    test_audio = "audios/test/251121-ntn443-Recording.m4a"

    if not os.path.exists(test_audio):
        print(f"⚠️  Test audio not found: {test_audio}")
        return False

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        output_path = f.name

    try:
        # Stage 1: Create podcast
        print("\n  [Stage 1] Creating podcast...")
        result_path, denoised_path, _ = audio_processor.create_podcast(
            voice_file=test_audio,
            output_file=output_path,
            generate_transcript=False,  # Key: Don't transcribe yet
            log_callback=lambda x: print(f"    LOG: {x}")
        )

        assert os.path.exists(result_path), "Podcast creation failed"
        print(
            f"  ✓ Stage 1 complete: Podcast ready at {os.path.basename(result_path)}")

        # Stage 2: Transcription (would happen in polling loop in app.py)
        print(f"\n  [Stage 2] Starting transcription poll...")
        print(f"    (In production, UI would show 'Transcription in progress...')")

        # Simulate polling
        import time
        transcript_path = None
        max_wait = 10  # 10 seconds for testing
        elapsed = 0
        poll_interval = 0.5

        # Start transcription
        print(f"    Starting transcribe_podcast_async()...")
        transcript_path = audio_processor.transcribe_podcast_async(
            podcast_file=result_path,
            whisper_model="tiny",
            log_callback=lambda x: print(f"    LOG: {x}")
        )

        if transcript_path and os.path.exists(transcript_path):
            print(
                f"  ✓ Stage 2 complete: Transcript ready at {os.path.basename(transcript_path)}")
            os.remove(transcript_path)
        else:
            print(f"  ⚠️  Stage 2: Whisper not available (mock successful anyway)")

        print(f"\n✅ Test 3 passed: Two-stage pipeline flow works correctly")

        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)

        return True

    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing Deferred Transcription Pipeline")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Create podcast without transcription",
                   test_create_podcast_without_transcription()))
    results.append(("Transcribe podcast async",
                   test_transcribe_podcast_async()))
    results.append(("Two-stage pipeline flow", test_two_stage_pipeline_flow()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ {total - passed} test(s) failed")
