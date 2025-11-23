"""Advanced noise reduction using noisereduce and FFmpeg RNNoise."""

import os
import subprocess
import tempfile
from typing import Optional, Callable
import soundfile as sf
import numpy as np


class NoiseReducer:
    """Handles noise reduction using multiple methods."""

    def __init__(self):
        """Initialize noise reducer."""
        self.noisereduce_available = False
        self.ffmpeg_available = False
        self._check_availability()

    def _check_availability(self):
        """Check which noise reduction methods are available."""
        # Check noisereduce
        try:
            import noisereduce as nr
            self.noisereduce_available = True
        except ImportError:
            self.noisereduce_available = False

        # Check FFmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            self.ffmpeg_available = (result.returncode == 0)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.ffmpeg_available = False

    def is_noisereduce_available(self) -> bool:
        """Check if noisereduce is available."""
        return self.noisereduce_available

    def is_ffmpeg_rnnoise_available(self) -> bool:
        """Check if FFmpeg with RNNoise is available."""
        return self.ffmpeg_available

    def reduce_noise_spectral(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        noise_duration: float = 0.5,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Reduce noise using spectral gating (noisereduce).

        Args:
            input_file: Path to input audio file
            output_file: Path for output (auto-generated if None)
            noise_duration: Duration in seconds to use as noise sample from start
            log_callback: Optional callback for logging

        Returns:
            Path to processed audio file, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_noisereduce_available():
            log("Warning: noisereduce not available")
            return input_file

        if not os.path.exists(input_file):
            log(f"Error: Input file not found: {input_file}")
            return None

        # Generate output file path if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(
                os.path.dirname(input_file),
                f"{base_name}_noisereduce.wav"
            )

        try:
            import noisereduce as nr

            log(f"Applying spectral noise reduction to: {os.path.basename(input_file)}")

            # Load audio file
            data, rate = sf.read(input_file)

            # Convert to mono if stereo
            if data.ndim > 1:
                data = np.mean(data, axis=1)
                log("Converted stereo to mono")

            # Use first noise_duration seconds as noise sample
            noise_len = int(rate * noise_duration)
            
            # Ensure we don't exceed audio length
            if noise_len > len(data):
                noise_len = min(int(rate * 0.1), len(data))  # Use 0.1s or all available
                log(f"Audio shorter than {noise_duration}s, using {noise_len/rate:.2f}s as noise profile")
            
            noise_clip = data[:noise_len]

            log(f"Using first {noise_duration}s as noise profile")

            # Apply noise reduction
            cleaned = nr.reduce_noise(
                y=data,
                sr=rate,
                y_noise=noise_clip,
                stationary=True
            )

            # Save processed audio
            sf.write(output_file, cleaned, rate)

            output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            log(f"✓ Spectral noise reduction complete: {os.path.basename(output_file)} ({output_size_mb:.1f}MB)")

            return output_file

        except Exception as e:
            log(f"Error during spectral noise reduction: {e}")
            return input_file

    def reduce_noise_rnnoise(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Reduce noise using FFmpeg RNNoise (arnndn filter).

        Args:
            input_file: Path to input audio file
            output_file: Path for output (auto-generated if None)
            log_callback: Optional callback for logging

        Returns:
            Path to processed audio file, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_ffmpeg_rnnoise_available():
            log("Warning: FFmpeg not available")
            return input_file

        if not os.path.exists(input_file):
            log(f"Error: Input file not found: {input_file}")
            return None

        # Generate output file path if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(
                os.path.dirname(input_file),
                f"{base_name}_rnnoise.wav"
            )

        try:
            log(f"Applying RNNoise reduction to: {os.path.basename(input_file)}")

            # Run FFmpeg with arnndn filter
            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-af", "arnndn",
                "-c:a", "pcm_s16le",
                "-y",  # Overwrite output file
                output_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0 and os.path.exists(output_file):
                output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                log(f"✓ RNNoise reduction complete: {os.path.basename(output_file)} ({output_size_mb:.1f}MB)")
                return output_file
            else:
                log(f"FFmpeg RNNoise failed: {result.stderr}")
                return input_file

        except subprocess.TimeoutExpired:
            log("Error: FFmpeg RNNoise timed out")
            return input_file
        except Exception as e:
            log(f"Error during RNNoise reduction: {e}")
            return input_file


def reduce_noise(
    input_file: str,
    output_file: Optional[str] = None,
    method: str = "spectral",
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Convenience function to reduce noise using specified method.

    Args:
        input_file: Path to input audio file
        output_file: Path for output (auto-generated if None)
        method: Noise reduction method ("spectral" or "rnnoise")
        log_callback: Optional callback for logging

    Returns:
        Path to processed audio file, or original if failed
    """
    reducer = NoiseReducer()

    if method == "spectral":
        return reducer.reduce_noise_spectral(input_file, output_file, log_callback=log_callback)
    elif method == "rnnoise":
        return reducer.reduce_noise_rnnoise(input_file, output_file, log_callback=log_callback)
    else:
        if log_callback:
            log_callback(f"Unknown noise reduction method: {method}")
        return input_file
