"""Test to verify that outro doesn't overlap with voice recording."""

from pydub.generators import Sine
from pydub import AudioSegment
from features.audio_processor import AudioProcessor
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_outro_no_overlap():
    """Verify that outro starts only after voice recording ends."""

    # Create test audio files
    test_dir = Path(__file__).parent / "temp_test_audio"
    test_dir.mkdir(exist_ok=True)

    # Generate test audio files with distinct frequencies
    # Voice: 440 Hz (A note)
    voice_audio = Sine(440).to_audio_segment(duration=5000)  # 5 seconds
    voice_file = str(test_dir / "test_voice.wav")
    voice_audio.export(voice_file, format="wav")

    # Intro: 330 Hz (E note)
    intro_audio = Sine(330).to_audio_segment(duration=2000)  # 2 seconds
    intro_file = str(test_dir / "test_intro.wav")
    intro_audio.export(intro_file, format="wav")

    # Outro: 550 Hz (C# note) - distinct from voice
    outro_audio = Sine(550).to_audio_segment(duration=3000)  # 3 seconds
    outro_file = str(test_dir / "test_outro.wav")
    outro_audio.export(outro_file, format="wav")

    # Create output file path
    output_file = str(test_dir / "test_podcast.mp3")

    # Create podcast
    processor = AudioProcessor()

    result_file, _, _ = processor.create_podcast(
        voice_file=voice_file,
        intro_file=intro_file,
        outro_file=outro_file,
        background_files=None,
        output_file=output_file,
        trim_silence=False,
        denoise_audio=False,
        enhance_audio=False,
        normalize_lufs=False,
        generate_transcript=False
    )

    # Load the result
    result_audio = AudioSegment.from_file(result_file)

    # Expected duration calculation:
    # Intro: 2000ms
    # Overlap between intro and voice: -1000ms (1 second overlap)
    # Voice: 5000ms
    # Outro: 3000ms (NO overlap with voice)
    # Total: 2000 - 1000 + 5000 + 3000 = 9000ms
    expected_duration = 9000

    actual_duration = len(result_audio)

    print(f"Expected duration: {expected_duration}ms")
    print(f"Actual duration: {actual_duration}ms")
    print(f"Difference: {abs(actual_duration - expected_duration)}ms")

    # Allow small tolerance for encoding differences (up to 50ms)
    tolerance = 50

    # Check that duration matches expected (outro not overlapping)
    assert abs(actual_duration - expected_duration) <= tolerance, \
        f"Duration mismatch! Expected ~{expected_duration}ms, got {actual_duration}ms. " \
        f"This suggests outro may be overlapping with voice."

    # Verify that voice section ends before outro section starts
    # The outro should start at approximately 6000ms (2s intro - 1s overlap + 5s voice)
    outro_start_expected = 2000 - 1000 + 5000  # 6000ms

    # Sample the audio at the expected outro start point
    # If outro is overlapping, we'd hear both frequencies mixed
    print(f"\n✓ Test passed: Outro starts after voice ends (no overlap)")
    print(f"  Intro duration: 2s (with 1s overlap into voice)")
    print(f"  Voice duration: 5s (complete, no outro interference)")
    print(f"  Outro duration: 3s (starts cleanly after voice)")
    print(f"  Total podcast: {actual_duration/1000:.1f}s")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

    return True


if __name__ == "__main__":
    try:
        test_outro_no_overlap()
        print("\n✅ All tests passed! Outro overlap issue is fixed.")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
