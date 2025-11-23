"""Audio normalization using FFmpeg loudnorm filter for LUFS compliance."""

import os
import json
import subprocess
import tempfile
from typing import Optional, Callable, Dict


class LUFSNormalizer:
    """Handles LUFS normalization using FFmpeg loudnorm filter."""

    def __init__(self):
        """Initialize LUFS normalizer."""
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
        """Check if FFmpeg is available for normalization."""
        return self.ffmpeg_available

    def _get_loudness_stats(
        self,
        input_file: str,
        target_lufs: float = -16.0,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[Dict]:
        """Measure audio loudness (first pass for two-pass normalization).

        Args:
            input_file: Path to input audio file
            target_lufs: Target LUFS level
            log_callback: Optional callback for logging

        Returns:
            Dictionary with loudness statistics, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        try:
            log("Analyzing audio loudness (pass 1/2)...")

            # First pass: measure loudness
            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-af", f"loudnorm=I={target_lufs}:print_format=json",
                "-f", "null",
                "-"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Parse JSON output from stderr
            stderr = result.stderr

            # Find JSON data in output
            json_start = stderr.rfind("{")
            json_end = stderr.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = stderr[json_start:json_end]
                stats = json.loads(json_str)
                log(f"Measured loudness: {stats.get('input_i', 'N/A')} LUFS")
                return stats
            else:
                log("Warning: Could not parse loudness statistics")
                return None

        except subprocess.TimeoutExpired:
            log("Error: Loudness analysis timed out")
            return None
        except json.JSONDecodeError as e:
            log(f"Error parsing loudness statistics: {e}")
            return None
        except Exception as e:
            log(f"Error measuring loudness: {e}")
            return None

    def normalize_lufs(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        target_lufs: float = -16.0,
        true_peak: float = -1.5,
        lra: float = 7.0,
        two_pass: bool = True,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Normalize audio to target LUFS level using FFmpeg loudnorm.

        Args:
            input_file: Path to input audio file
            output_file: Path for output (auto-generated if None)
            target_lufs: Target integrated loudness (-14 or -16 recommended)
            true_peak: Maximum true peak in dBTP (-1.5 recommended)
            lra: Target loudness range in LU (7.0 recommended)
            two_pass: Use two-pass normalization for better accuracy
            log_callback: Optional callback for logging

        Returns:
            Path to normalized audio file, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_available():
            log("Warning: FFmpeg not available for LUFS normalization")
            return input_file

        if not os.path.exists(input_file):
            log(f"Error: Input file not found: {input_file}")
            return None

        # Generate output file path if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(
                os.path.dirname(input_file),
                f"{base_name}_normalized.wav"
            )

        try:
            log(f"Normalizing audio to {target_lufs} LUFS: {os.path.basename(input_file)}")

            if two_pass:
                # Two-pass normalization (recommended)
                stats = self._get_loudness_stats(input_file, target_lufs, log_callback)

                if stats:
                    # Second pass: apply normalization with measured values
                    log("Applying loudness normalization (pass 2/2)...")

                    measured_i = stats.get("input_i", target_lufs)
                    measured_tp = stats.get("input_tp", true_peak)
                    measured_lra = stats.get("input_lra", lra)
                    measured_thresh = stats.get("input_thresh", "-70.0")

                    cmd = [
                        "ffmpeg",
                        "-i", input_file,
                        "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
                               f"measured_I={measured_i}:measured_TP={measured_tp}:"
                               f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
                               f"linear=true:print_format=summary",
                        "-ar", "44100",
                        "-y",
                        output_file
                    ]
                else:
                    log("Warning: Using single-pass normalization (stats unavailable)")
                    two_pass = False

            if not two_pass:
                # Single-pass normalization (fallback)
                cmd = [
                    "ffmpeg",
                    "-i", input_file,
                    "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}",
                    "-ar", "44100",
                    "-y",
                    output_file
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0 and os.path.exists(output_file):
                output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                log(f"✓ LUFS normalization complete: {os.path.basename(output_file)} ({output_size_mb:.1f}MB)")
                log(f"Target: {target_lufs} LUFS, True Peak: {true_peak} dBTP")
                return output_file
            else:
                log(f"FFmpeg normalization failed: {result.stderr}")
                return input_file

        except subprocess.TimeoutExpired:
            log("Error: FFmpeg normalization timed out")
            return input_file
        except Exception as e:
            log(f"Error during LUFS normalization: {e}")
            return input_file


def normalize_audio_lufs(
    input_file: str,
    output_file: Optional[str] = None,
    target_lufs: float = -16.0,
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Convenience function to normalize audio to target LUFS.

    Args:
        input_file: Path to input audio file
        output_file: Path for output (auto-generated if None)
        target_lufs: Target LUFS level (-14 or -16 recommended)
        log_callback: Optional callback for logging

    Returns:
        Path to normalized audio file, or original if failed
    """
    normalizer = LUFSNormalizer()
    return normalizer.normalize_lufs(
        input_file,
        output_file,
        target_lufs=target_lufs,
        log_callback=log_callback
    )
