"""Test script to create a podcast using the test audio file."""

import os
import sys
from audio_processor import AudioProcessor
from config_manager import ConfigManager


def main():
    print("=" * 60)
    print("Testing Podcast Creation")
    print("=" * 60)

    # Initialize components
    config_manager = ConfigManager()
    audio_processor = AudioProcessor()

    # Test file
    test_voice_file = "audios/test/test_brunos_project.mp3"

    if not os.path.exists(test_voice_file):
        print(f"❌ Error: Test file not found: {test_voice_file}")
        return 1

    print(f"✓ Found test file: {test_voice_file}")

    # Get configuration
    intro_path = config_manager.get_intro()
    outro_path = config_manager.get_outro()
    background_tracks = config_manager.get_background_tracks()
    volume = config_manager.get_volume()

    print(f"\nConfiguration:")
    print(f"  Intro: {intro_path if intro_path else 'None'}")
    print(f"  Outro: {outro_path if outro_path else 'None'}")
    print(
        f"  Background tracks: {len(background_tracks) if background_tracks else 0}")
    print(f"  Volume: {volume}%")

    # Output file
    output_file = "outputs/test_podcast.mp3"
    os.makedirs("outputs", exist_ok=True)

    print(f"\nCreating podcast...")
    print(f"Output: {output_file}")
    print("-" * 60)

    try:
        # Create podcast with trim_silence enabled
        result = audio_processor.create_podcast(
            voice_file=test_voice_file,
            intro_file=intro_path,
            outro_file=outro_path,
            background_files=background_tracks if background_tracks else None,
            background_volume=volume,
            output_file=output_file,
            trim_silence=True
        )

        print("-" * 60)
        print(f"✓ SUCCESS! Podcast created: {result}")

        # Check file size - result is now a tuple (podcast_path, denoised_path)
        podcast_path = result[0] if isinstance(result, tuple) else result
        if os.path.exists(podcast_path):
            size_mb = os.path.getsize(podcast_path) / (1024 * 1024)
            print(f"✓ File size: {size_mb:.2f} MB")

        # Check if denoised file was created
        if isinstance(result, tuple) and len(result) > 1:
            denoised_path = result[1]
            if denoised_path and os.path.exists(denoised_path):
                denoised_size_mb = os.path.getsize(
                    denoised_path) / (1024 * 1024)
                print(f"✓ Denoised file created: {denoised_size_mb:.2f} MB")

        print("=" * 60)
        return 0

    except Exception as e:
        print("-" * 60)
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
