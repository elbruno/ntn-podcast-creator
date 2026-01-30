"""Advanced voice enhancement using FFmpeg filters for professional podcast quality.

This module provides additional audio processing methods beyond basic noise reduction:
- High-pass filter: Remove low-frequency rumble and background noise
- De-esser: Reduce harsh sibilance (S and SH sounds)
- Dynamic compression: Even out volume levels for consistent listening
- EQ enhancement: Boost voice clarity and presence
"""

import os
import subprocess
import tempfile
from typing import Optional, Callable


class VoiceEnhancer:
    """Handles professional voice enhancement using FFmpeg audio filters."""

    def __init__(self):
        """Initialize voice enhancer."""
        self.ffmpeg_available = False
        self._check_availability()

    def _check_availability(self):
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            self.ffmpeg_available = (result.returncode == 0)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.ffmpeg_available = False

    def is_available(self) -> bool:
        """Check if FFmpeg is available for enhancement."""
        return self.ffmpeg_available

    def enhance_voice(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        preset: str = "podcast",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Apply comprehensive voice enhancement processing.

        Args:
            input_file: Path to input audio file
            output_file: Optional path for output file. If None, creates temp file.
            preset: Enhancement preset - "podcast", "light", or "aggressive"
            log_callback: Optional callback for logging

        Returns:
            Path to enhanced audio file, or None if failed

        Presets:
            - podcast (default): Balanced enhancement for podcast voices
            - light: Gentle enhancement, preserves natural sound
            - aggressive: Strong processing for very noisy recordings
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_available():
            log("ERROR: FFmpeg not available for voice enhancement")
            return None

        if not os.path.exists(input_file):
            log(f"ERROR: Input file not found: {input_file}")
            return None

        # Create output file if not provided
        if output_file is None:
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(
                temp_dir, 
                f"enhanced_{os.path.basename(input_file)}"
            )

        try:
            log(f"Enhancing voice with preset: {preset}")
            
            # Build filter chain based on preset
            filter_chain = self._build_filter_chain(preset)
            
            log(f"Applying filters: {filter_chain}")

            # Run FFmpeg with the filter chain
            command = [
                "ffmpeg",
                "-i", input_file,
                "-af", filter_chain,
                "-c:a", "pcm_s16le",
                "-y",
                output_file
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                log(f"ERROR: FFmpeg enhancement failed: {result.stderr}")
                return None

            log(f"✓ Voice enhancement complete: {os.path.basename(output_file)}")
            return output_file

        except subprocess.TimeoutExpired:
            log("ERROR: Voice enhancement timed out after 5 minutes")
            return None
        except Exception as e:
            log(f"ERROR: Voice enhancement failed: {str(e)}")
            return None

    def _build_filter_chain(self, preset: str) -> str:
        """Build FFmpeg filter chain based on preset.

        Args:
            preset: Enhancement preset name

        Returns:
            FFmpeg filter chain string
        """
        if preset == "light":
            # Light enhancement: gentle processing
            return (
                "highpass=f=80,"                    # Remove rumble below 80Hz
                "lowpass=f=12000,"                  # Remove harsh highs above 12kHz
                "equalizer=f=200:t=q:w=1:g=-2,"    # Reduce mud at 200Hz
                "equalizer=f=3000:t=q:w=2:g=3,"    # Boost presence at 3kHz
                "compand=attacks=0.3:decays=0.8:"  # Gentle compression
                "points=-80/-80|-45/-30|-27/-20|0/-10:soft-knee=6:gain=5"
            )
        
        elif preset == "aggressive":
            # Aggressive enhancement: strong noise reduction and processing
            return (
                "highpass=f=100,"                   # Remove rumble below 100Hz
                "lowpass=f=10000,"                  # Remove harsh highs above 10kHz
                "equalizer=f=150:t=q:w=1:g=-4,"    # Strong mud reduction
                "equalizer=f=2500:t=q:w=2:g=5,"    # Strong presence boost
                "equalizer=f=5000:t=q:w=1:g=3,"    # Clarity boost
                "deesser=i=0.1:m=0.5:f=6000:s=o,"  # Strong de-essing
                "compand=attacks=0.1:decays=0.5:"  # Strong compression
                "points=-80/-80|-50/-35|-30/-25|0/-12:soft-knee=6:gain=8"
            )
        
        else:  # "podcast" (default)
            # Balanced enhancement: professional podcast quality
            return (
                "highpass=f=85,"                    # Remove rumble below 85Hz
                "lowpass=f=11000,"                  # Remove harsh highs above 11kHz
                "equalizer=f=180:t=q:w=1:g=-3,"    # Reduce muddiness at 180Hz
                "equalizer=f=2800:t=q:w=2:g=4,"    # Boost voice presence at 2.8kHz
                "equalizer=f=4500:t=q:w=1:g=2,"    # Add clarity at 4.5kHz
                "deesser=i=0.07:m=0.5:f=6000:s=o," # Moderate de-essing at 6kHz
                "compand=attacks=0.2:decays=0.6:"  # Moderate compression
                "points=-80/-80|-48/-32|-28/-22|0/-11:soft-knee=6:gain=6"
            )

    def apply_high_pass_filter(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        cutoff_freq: int = 80,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Apply high-pass filter to remove low-frequency rumble.

        Args:
            input_file: Path to input audio file
            output_file: Optional path for output file. If None, creates temp file.
            cutoff_freq: Frequency below which audio is attenuated (Hz)
            log_callback: Optional callback for logging

        Returns:
            Path to filtered audio file, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_available():
            log("ERROR: FFmpeg not available")
            return None

        if output_file is None:
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(
                temp_dir,
                f"highpass_{os.path.basename(input_file)}"
            )

        try:
            log(f"Applying high-pass filter (cutoff: {cutoff_freq}Hz)")
            
            command = [
                "ffmpeg",
                "-i", input_file,
                "-af", f"highpass=f={cutoff_freq}",
                "-c:a", "pcm_s16le",
                "-y",
                output_file
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                log(f"ERROR: High-pass filter failed: {result.stderr}")
                return None

            log(f"✓ High-pass filter applied: {os.path.basename(output_file)}")
            return output_file

        except Exception as e:
            log(f"ERROR: High-pass filter failed: {str(e)}")
            return None

    def apply_dynamic_compression(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        strength: str = "medium",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Apply dynamic range compression for consistent volume.

        Args:
            input_file: Path to input audio file
            output_file: Optional path for output file. If None, creates temp file.
            strength: Compression strength - "light", "medium", or "strong"
            log_callback: Optional callback for logging

        Returns:
            Path to compressed audio file, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_available():
            log("ERROR: FFmpeg not available")
            return None

        if output_file is None:
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(
                temp_dir,
                f"compressed_{os.path.basename(input_file)}"
            )

        # Define compression parameters based on strength
        compand_params = {
            "light": "attacks=0.3:decays=0.8:points=-80/-80|-45/-35|-30/-25|0/-12:soft-knee=6:gain=3",
            "medium": "attacks=0.2:decays=0.6:points=-80/-80|-48/-38|-30/-25|0/-12:soft-knee=6:gain=5",
            "strong": "attacks=0.1:decays=0.5:points=-80/-80|-50/-40|-30/-28|0/-15:soft-knee=6:gain=8"
        }

        compand = compand_params.get(strength, compand_params["medium"])

        try:
            log(f"Applying dynamic compression (strength: {strength})")
            
            command = [
                "ffmpeg",
                "-i", input_file,
                "-af", f"compand={compand}",
                "-c:a", "pcm_s16le",
                "-y",
                output_file
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                log(f"ERROR: Compression failed: {result.stderr}")
                return None

            log(f"✓ Dynamic compression applied: {os.path.basename(output_file)}")
            return output_file

        except Exception as e:
            log(f"ERROR: Compression failed: {str(e)}")
            return None


# Convenience function for easy integration
def enhance_voice(
    input_file: str,
    output_file: Optional[str] = None,
    preset: str = "podcast",
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Apply voice enhancement with specified preset.

    This is a convenience function that creates a VoiceEnhancer instance
    and applies enhancement with the specified preset.

    Args:
        input_file: Path to input audio file
        output_file: Optional path for output file
        preset: Enhancement preset - "podcast", "light", or "aggressive"
        log_callback: Optional callback for logging

    Returns:
        Path to enhanced audio file, or None if failed
    """
    enhancer = VoiceEnhancer()
    return enhancer.enhance_voice(input_file, output_file, preset, log_callback)
