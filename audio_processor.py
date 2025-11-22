"""Audio processing for podcast creation."""

import os
import random
import math
from typing import List, Optional, Callable
from pydub import AudioSegment
from pydub.silence import detect_leading_silence


class AudioProcessor:
    """Handles audio mixing and processing for podcast creation."""

    def __init__(self):
        """Initialize audio processor."""
        pass

    def load_audio(self, file_path: str) -> AudioSegment:
        """Load audio file.

        Args:
            file_path: Path to audio file

        Returns:
            AudioSegment object

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If file cannot be loaded
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            # Try to load the audio file
            audio = AudioSegment.from_file(file_path)
            return audio
        except Exception as e:
            raise Exception(f"Error loading audio file {file_path}: {e}")

    def trim_silence(self, audio: AudioSegment, silence_threshold: int = -40) -> AudioSegment:
        """Trim silence from the beginning and end of audio.

        Args:
            audio: AudioSegment to process
            silence_threshold: Threshold in dB for what is considered silence

        Returns:
            AudioSegment with silence trimmed
        """
        # Detect leading silence
        start_trim = detect_leading_silence(
            audio, silence_threshold=silence_threshold)

        # Detect trailing silence by reversing the audio
        end_trim = detect_leading_silence(
            audio.reverse(), silence_threshold=silence_threshold)

        # Calculate duration
        duration = len(audio)

        # Trim the audio
        trimmed = audio[start_trim:duration-end_trim]

        return trimmed

    def reduce_volume(self, audio: AudioSegment, volume_percent: int) -> AudioSegment:
        """Reduce audio volume.

        Args:
            audio: AudioSegment to process
            volume_percent: Target volume as percentage (0-100)

        Returns:
            AudioSegment with reduced volume
        """
        if volume_percent >= 100:
            return audio

        if volume_percent <= 0:
            # Silence
            return audio - 60

        # Convert percentage to dB using logarithmic scaling
        # volume_percent of 100 = 0 dB, 50 = -6 dB, 10 = -20 dB
        db_change = 20 * math.log10(volume_percent / 100)
        return audio + db_change

    def create_looped_background(
        self,
        background_files: List[str],
        target_duration_ms: int,
        volume_percent: int = 10,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[AudioSegment]:
        """Create looped background music from randomly selected tracks.

        Randomly selects tracks and concatenates them until the target duration is reached.

        Args:
            background_files: List of background music file paths
            target_duration_ms: Target duration in milliseconds
            volume_percent: Volume percentage for background (0-100)
            log_callback: Optional callback function for logging

        Returns:
            AudioSegment with concatenated background music or None if no files
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not background_files:
            return None

        # Filter out files that don't exist
        valid_files = [f for f in background_files if os.path.exists(f)]
        if not valid_files:
            log("Warning: No valid background music files found")
            return None

        log(
            f"Building background music from {len(valid_files)} available track(s)")

        # Build background by randomly selecting and concatenating tracks
        background = AudioSegment.empty()
        tracks_used = []

        while len(background) < target_duration_ms:
            # Randomly select a track
            selected_file = random.choice(valid_files)
            track_name = os.path.basename(selected_file)

            try:
                track = self.load_audio(selected_file)
                # Reduce volume of this track
                track = self.reduce_volume(track, volume_percent)

                # Append to background
                background += track
                tracks_used.append(track_name)

            except Exception as e:
                log(f"Error loading background track {track_name}: {e}")
                continue

        # Trim to exact duration
        background = background[:target_duration_ms]

        # Show which tracks were used
        if tracks_used:
            log(f"Background music created using: {', '.join(tracks_used)}")

        return background

    def mix_audio(
        self,
        main_audio: AudioSegment,
        background: Optional[AudioSegment] = None
    ) -> AudioSegment:
        """Mix main audio with background music.

        Args:
            main_audio: Main audio track
            background: Background music (optional)

        Returns:
            Mixed audio
        """
        if background is None:
            return main_audio

        # Overlay background music on main audio
        return main_audio.overlay(background)

    def create_podcast(
        self,
        voice_file: str,
        intro_file: Optional[str] = None,
        outro_file: Optional[str] = None,
        background_files: Optional[List[str]] = None,
        background_volume: int = 10,
        output_file: str = "output.mp3",
        trim_silence: bool = False,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Create complete podcast with intro, outro, and background music.

        Args:
            voice_file: Path to main voice recording
            intro_file: Path to intro audio (optional)
            outro_file: Path to outro audio (optional)
            background_files: List of background music files (optional)
            background_volume: Volume percentage for background (0-100)
            output_file: Path for output file
            trim_silence: Whether to trim silence from voice recording
            log_callback: Optional callback function for logging

        Returns:
            Path to output file

        Raises:
            Exception: If processing fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        log("Starting podcast creation...")

        # Load main voice recording
        log(f"Loading main voice: {os.path.basename(voice_file)}")
        voice = self.load_audio(voice_file)

        # Trim silence if requested
        if trim_silence:
            log("Trimming silence from voice recording...")
            original_duration = len(voice)
            voice = self.trim_silence(voice)
            trimmed_duration = len(voice)
            saved_ms = original_duration - trimmed_duration
            log(f"Trimmed {saved_ms/1000:.2f} seconds of silence")

        # Build the podcast sequence
        podcast = AudioSegment.empty()

        # Add intro if provided
        if intro_file and os.path.exists(intro_file):
            log(f"Adding intro: {os.path.basename(intro_file)}")
            intro = self.load_audio(intro_file)
            podcast += intro

        # Add main voice
        log("Adding main voice recording")
        podcast += voice

        # Add outro if provided
        if outro_file and os.path.exists(outro_file):
            log(f"Adding outro: {os.path.basename(outro_file)}")
            outro = self.load_audio(outro_file)
            podcast += outro

        # Add background music if provided
        if background_files:
            log(f"Creating background music (volume: {background_volume}%)")
            background = self.create_looped_background(
                background_files,
                len(podcast),
                background_volume,
                log_callback=log
            )
            if background:
                log("Mixing background music with podcast")
                podcast = self.mix_audio(podcast, background)

        # Export final podcast
        log(f"Exporting to: {output_file}")
        podcast.export(output_file, format="mp3")
        log("Podcast creation complete!")

        return output_file
