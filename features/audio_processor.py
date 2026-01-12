"""Audio processing for podcast creation."""

import os
import random
import math
import tempfile
from typing import List, Optional, Callable, Tuple
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from .audio_denoiser_processor import denoise_audio_file
from .noise_reducer import reduce_noise
from .lufs_normalizer import normalize_audio_lufs


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

    def concatenate_audio_files(
        self,
        audio_files: List[str],
        output_path: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Concatenate multiple audio files into a single file.

        Args:
            audio_files: List of paths to audio files to concatenate
            output_path: Optional path for output file. If None, creates temp file.
            log_callback: Optional callback function for logging

        Returns:
            Path to concatenated audio file

        Raises:
            ValueError: If audio_files is empty or contains invalid files
            Exception: If concatenation fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not audio_files:
            raise ValueError("No audio files provided for concatenation")

        # If only one file, return it directly
        if len(audio_files) == 1:
            log(f"Single file provided: {os.path.basename(audio_files[0])}")
            return audio_files[0]

        log(f"Concatenating {len(audio_files)} audio files...")

        # Load all audio files
        audio_segments = []
        for i, file_path in enumerate(audio_files, 1):
            if not os.path.exists(file_path):
                raise ValueError(f"Audio file not found: {file_path}")

            try:
                log(f"Loading file {i}/{len(audio_files)}: {os.path.basename(file_path)}")
                audio = self.load_audio(file_path)
                audio_segments.append(audio)
                duration_seconds = len(audio) / 1000.0
                log(f"  Duration: {duration_seconds:.2f}s")
            except Exception as e:
                raise Exception(f"Error loading audio file {file_path}: {e}")

        # Concatenate all segments
        log("Concatenating audio segments...")
        concatenated = audio_segments[0]
        for i, segment in enumerate(audio_segments[1:], 2):
            concatenated = concatenated + segment
            log(f"  Merged {i}/{len(audio_segments)} segments")

        # Calculate total duration
        total_duration_seconds = len(concatenated) / 1000.0
        log(f"Total concatenated duration: {total_duration_seconds:.2f}s")

        # Export to file
        if output_path is None:
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(
                temp_dir, f"concatenated_{os.getpid()}.mp3")

        log(f"Exporting concatenated audio to: {os.path.basename(output_path)}")
        concatenated.export(output_path, format="mp3")
        log("Concatenation complete!")

        return output_path

    def trim_silence(self, audio: AudioSegment, silence_threshold: int = -35) -> AudioSegment:
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

    def fade_out(self, audio: AudioSegment, duration_ms: int) -> AudioSegment:
        """Apply fade-out effect to audio.

        Args:
            audio: AudioSegment to process
            duration_ms: Duration of fade-out in milliseconds

        Returns:
            AudioSegment with fade-out applied
        """
        if duration_ms <= 0 or len(audio) <= 0:
            return audio

        fade_duration = min(duration_ms, len(audio))
        return audio.fade_out(fade_duration)

    def fade_in(self, audio: AudioSegment, duration_ms: int) -> AudioSegment:
        """Apply fade-in effect to audio.

        Args:
            audio: AudioSegment to process
            duration_ms: Duration of fade-in in milliseconds

        Returns:
            AudioSegment with fade-in applied
        """
        if duration_ms <= 0 or len(audio) <= 0:
            return audio

        fade_duration = min(duration_ms, len(audio))
        return audio.fade_in(fade_duration)

    def create_looped_background(
        self,
        background_files: List[str],
        target_duration_ms: int,
        volume_percent: int = 10,
        track_volumes: Optional[dict] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[AudioSegment]:
        """Create looped background music from randomly selected tracks.

        Randomly selects tracks and concatenates them until the target duration is reached.

        Args:
            background_files: List of background music file paths
            target_duration_ms: Target duration in milliseconds
            volume_percent: Default volume percentage for background (0-100)
            track_volumes: Optional dict mapping track paths to individual volumes
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

                # Use individual track volume if available, otherwise use default
                if track_volumes and selected_file in track_volumes:
                    track_volume = track_volumes[selected_file]
                else:
                    track_volume = volume_percent

                # Reduce volume of this track
                track = self.reduce_volume(track, track_volume)

                # Append to background
                background += track
                tracks_used.append(f"{track_name} ({track_volume}%)")

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
        track_volumes: Optional[dict] = None,
        output_file: str = "output.mp3",
        trim_silence: bool = False,
        denoise_audio: bool = True,
        denoise_method: str = "audio_denoiser",
        normalize_lufs: bool = False,
        target_lufs: float = -16.0,
        intro_voice_overlap: bool = True,
        voice_outro_overlap: bool = False,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Create complete podcast with intro, outro, and background music.

        Args:
            voice_file: Path to main voice recording
            intro_file: Path to intro audio (optional)
            outro_file: Path to outro audio (optional)
            background_files: List of background music files (optional)
            background_volume: Default volume percentage for background (0-100)
            track_volumes: Optional dict mapping track paths to individual volumes
            output_file: Path for output file
            trim_silence: Whether to trim silence from voice recording
            denoise_audio: Whether to denoise audio (optional)
            denoise_method: Denoising method ("audio_denoiser", "spectral", "rnnoise")
            normalize_lufs: Whether to normalize to target LUFS level
            target_lufs: Target LUFS level (-14 or -16 recommended)
            intro_voice_overlap: Whether to enable 1-second overlap between intro and voice
            voice_outro_overlap: Whether to enable 1-second overlap between voice and outro
            log_callback: Optional callback function for logging

        Returns:
            Tuple of (path to output file, path to denoised audio or None, None)

        Raises:
            Exception: If processing fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        log("Starting podcast creation...")

        # Store processed file paths
        denoised_file_path = None

        # Noise reduction (multiple methods available)
        voice_file_to_process = voice_file
        if denoise_audio:
            if denoise_method == "audio_denoiser":
                log("Denoising audio using audio-denoiser (AI-based)...")
                denoised_file = denoise_audio_file(
                    voice_file,
                    enabled=True,
                    auto_scale=True,
                    log_callback=log
                )
            elif denoise_method == "spectral":
                log("Denoising audio using spectral gating (noisereduce)...")
                denoised_file = reduce_noise(
                    voice_file,
                    method="spectral",
                    log_callback=log
                )
            elif denoise_method == "rnnoise":
                log("Denoising audio using FFmpeg RNNoise...")
                denoised_file = reduce_noise(
                    voice_file,
                    method="rnnoise",
                    log_callback=log
                )
            else:
                log(f"Unknown denoise method '{denoise_method}', using audio_denoiser")
                denoised_file = denoise_audio_file(
                    voice_file,
                    enabled=True,
                    auto_scale=True,
                    log_callback=log
                )

            if denoised_file and denoised_file != voice_file:
                voice_file_to_process = denoised_file
                denoised_file_path = denoised_file
                log(f"Using denoised audio: {os.path.basename(denoised_file)}")
            else:
                log("Using original audio (denoising not available or failed)")

        # Load main voice recording
        log(f"Loading main voice: {os.path.basename(voice_file_to_process)}")
        voice = self.load_audio(voice_file_to_process)

        # Trim silence if requested
        if trim_silence:
            log("Trimming silence from voice recording...")
            original_duration = len(voice)
            voice = self.trim_silence(voice)
            trimmed_duration = len(voice)
            saved_ms = original_duration - trimmed_duration
            log(f"Trimmed {saved_ms/1000:.2f} seconds of silence")

        # Build the podcast sequence with overlaps
        # Overlap duration: 1 second (1000ms)
        overlap_ms = 1000

        intro_duration = 0
        outro_duration = 0

        # Add intro if provided (no background music)
        if intro_file and os.path.exists(intro_file):
            log(f"Adding intro: {os.path.basename(intro_file)}")
            intro = self.load_audio(intro_file)
            intro_duration = len(intro)
        else:
            intro = None

        # Add main voice with background music
        log("Adding main voice recording")
        voice_with_bg = voice

        # Add background music only to voice section
        if background_files:
            log(
                f"Creating background music for voice (volume: {background_volume}%)")
            background = self.create_looped_background(
                background_files,
                len(voice),
                background_volume,
                track_volumes=track_volumes,
                log_callback=log
            )
            if background:
                log("Mixing background music with voice recording")
                voice_with_bg = self.mix_audio(voice, background)

        # Add outro if provided (no background music)
        if outro_file and os.path.exists(outro_file):
            log(f"Adding outro: {os.path.basename(outro_file)}")
            outro = self.load_audio(outro_file)
            outro_duration = len(outro)
        else:
            outro = None

        # Build podcast with overlaps (configurable)
        podcast = AudioSegment.empty()

        if intro:
            podcast += intro
            # Conditional overlap: intro's last second overlaps with voice's first second
            if intro_voice_overlap and len(podcast) >= overlap_ms:
                log(f"Applying {overlap_ms}ms overlap between intro and voice")
                # Remove last second from intro
                podcast = podcast[:-overlap_ms]

        # Add voice with background (overlays with end of intro if overlap is enabled)
        if intro and intro_voice_overlap and len(intro) >= overlap_ms:
            # Extract the last second of intro to mix with first second of voice
            intro_tail = intro[-overlap_ms:]
            voice_head = voice_with_bg[:overlap_ms]
            voice_tail = voice_with_bg[overlap_ms:]

            # Mix the overlapping parts
            overlapped_section = intro_tail.overlay(voice_head)
            podcast += overlapped_section + voice_tail
        else:
            podcast += voice_with_bg

        # Add outro after voice
        if outro:
            if voice_outro_overlap:
                # Apply overlap between voice and outro
                log(f"Adding outro with {overlap_ms}ms overlap")
                # Extract the last second of voice+bg to mix with first second of outro
                if len(podcast) >= overlap_ms and len(outro) >= overlap_ms:
                    # Remove last second from current podcast
                    podcast = podcast[:-overlap_ms]
                    # Get the last second of original podcast and first second of outro
                    voice_tail = voice_with_bg[-overlap_ms:] if intro else podcast[-overlap_ms:]
                    outro_head = outro[:overlap_ms]
                    outro_tail = outro[overlap_ms:]
                    
                    # Mix the overlapping parts
                    overlapped_section = voice_tail.overlay(outro_head)
                    podcast += overlapped_section + outro_tail
                else:
                    # Not enough audio for overlap, just append
                    podcast += outro
            else:
                # No overlap - apply fade-in to outro for smooth transition
                log(f"Adding outro without overlap (with fade-in)")
                outro_with_fade = self.fade_in(outro, 200)
                
                # If we have background music, fade it out in the last 500ms before outro
                if background_files and background and not voice_outro_overlap:
                    fade_duration = 500  # 500ms fade-out
                    # Apply fade-out to background in final section
                    if len(podcast) >= fade_duration:
                        # The voice+background has already been added to podcast
                        # So we need to fade out the last 500ms of it
                        fade_start = len(podcast) - fade_duration
                        if fade_start >= 0:
                            podcast_before_fade = podcast[:fade_start]
                            podcast_fade_section = podcast[fade_start:].fade_out(
                                fade_duration)
                            podcast = podcast_before_fade + podcast_fade_section
                            log(f"Applied {fade_duration}ms fade-out to background music before outro")
                
                podcast += outro_with_fade
        else:
            log("No outro file provided")

        # Export final podcast
        log(f"Exporting to: {output_file}")
        podcast.export(output_file, format="mp3")

        # Phase 2: LUFS Normalization (after mixing, before final export)
        if normalize_lufs:
            log(f"Normalizing audio to {target_lufs} LUFS...")
            # Create temporary WAV for normalization
            import tempfile
            temp_wav = tempfile.NamedTemporaryFile(
                delete=False, suffix=".wav").name
            podcast.export(temp_wav, format="wav")

            # Normalize
            normalized_file = normalize_audio_lufs(
                temp_wav,
                output_file=None,
                target_lufs=target_lufs,
                log_callback=log
            )

            if normalized_file and normalized_file != temp_wav:
                # Re-export as MP3
                normalized_audio = self.load_audio(normalized_file)
                normalized_audio.export(output_file, format="mp3")
                log(f"✓ Applied LUFS normalization to final output")

                # Clean up temp files
                try:
                    os.remove(temp_wav)
                    if os.path.exists(normalized_file):
                        os.remove(normalized_file)
                except Exception:
                    pass
            else:
                log("LUFS normalization skipped or failed")

        log("Podcast creation complete!")

        return output_file, denoised_file_path, None
