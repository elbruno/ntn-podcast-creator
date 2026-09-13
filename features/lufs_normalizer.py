"""Audio normalization using FFmpeg loudnorm filter for LUFS compliance."""

import os
import json
import math
import re
import subprocess
from typing import Optional, Callable, Dict


_MEASURED_KEYS = ("input_i", "input_tp", "input_lra",
                  "input_thresh", "target_offset")


def extract_loudnorm_json(stderr: str) -> Optional[Dict]:
    """Return the last complete loudnorm JSON object embedded in FFmpeg logs.

    All five measured fields must be present. Values are returned unchanged,
    including nonfinite measurements such as silence's ``"-inf"``, for QC.
    Suitability for normalization is validated separately before the second pass.
    Malformed objects and unrelated JSON are ignored.
    """
    decoder = json.JSONDecoder()
    stats = None
    position = 0
    while True:
        start = stderr.find("{", position)
        if start < 0:
            return stats
        try:
            candidate, end = decoder.raw_decode(stderr, start)
        except json.JSONDecodeError:
            position = start + 1
            continue
        position = end
        if isinstance(candidate, dict) and all(key in candidate for key in _MEASURED_KEYS):
            stats = candidate


def _finite_measured_stats(stats: Optional[Dict]) -> Optional[Dict]:
    """Convert all required measurements to finite numbers, without defaults."""
    if not isinstance(stats, dict):
        return None
    measured = {}
    for key in _MEASURED_KEYS:
        value = stats.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return None
        try:
            number = float(value)
        except (ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        measured[key] = number
    return measured


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
        log_callback: Optional[Callable[[str], None]] = None,
        true_peak: float = -1.5,
        lra: float = 7.0
    ) -> Optional[Dict]:
        """Measure audio loudness (first pass for two-pass normalization).

        Args:
            input_file: Path to input audio file
            target_lufs: Target LUFS level
            log_callback: Optional callback for logging
            true_peak: Maximum true peak in dBTP (same as the second pass)
            lra: Target loudness range in LU (same as the second pass)

        Returns:
            Raw loudness statistics (possibly nonfinite for silence), or None
            if FFmpeg failed or no complete loudnorm JSON object was found.
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
                "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=json",
                "-f", "null",
                "-"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                log(
                    f"Warning: FFmpeg loudness analysis failed (exit {result.returncode}): {result.stderr}")
                return None

            stats = extract_loudnorm_json(result.stderr)
            if stats is not None:
                log(f"Measured loudness: {stats.get('input_i', 'N/A')} LUFS")
                return stats
            else:
                log("Warning: Could not parse loudness statistics")
                return None

        except subprocess.TimeoutExpired:
            log("Error: Loudness analysis timed out")
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
                stats = self._get_loudness_stats(
                    input_file, target_lufs, log_callback, true_peak=true_peak, lra=lra
                )
                measured = _finite_measured_stats(stats)

                if measured is not None:
                    # Second pass: apply normalization with measured values
                    log("Applying loudness normalization (pass 2/2)...")

                    measured_i = measured["input_i"]
                    measured_tp = measured["input_tp"]
                    measured_lra = measured["input_lra"]
                    measured_thresh = measured["input_thresh"]
                    offset = measured["target_offset"]

                    cmd = [
                        "ffmpeg",
                        "-i", input_file,
                        "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
                        f"measured_I={measured_i}:measured_TP={measured_tp}:"
                        f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
                        f"offset={offset}:linear=true:print_format=summary",
                        "-ar", "44100",
                        "-y",
                        output_file
                    ]
                else:
                    log("Warning: Using single-pass normalization fallback "
                        "(measured stats unavailable, missing, nonnumeric, or nonfinite)")
                    two_pass = False

            if not two_pass:
                # Single-pass normalization (fallback)
                cmd = [
                    "ffmpeg",
                    "-i", input_file,
                    "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=summary",
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
                # Two passes do not guarantee linear processing: FFmpeg may use
                # dynamic mode when the LRA or true-peak constraints require it.
                modes = re.findall(
                    r"Normalization Type:\s*(linear|dynamic)\b", result.stderr, re.IGNORECASE)
                mode = f"FFmpeg {modes[-1].lower()} mode" if modes else "FFmpeg mode not reported"
                passes = "two-pass (measured)" if two_pass else "single-pass"
                log(f"✓ LUFS normalization complete: {passes}, {mode}: "
                    f"{os.path.basename(output_file)} ({output_size_mb:.1f}MB)")
                log(f"Target: {target_lufs} LUFS, True Peak: {true_peak} dBTP")
                return output_file
            else:
                log(f"FFmpeg normalization failed (exit {result.returncode} or output missing): "
                    f"{result.stderr}. Using original audio.")
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
    log_callback: Optional[Callable[[str], None]] = None,
    true_peak: float = -1.5,
    lra: float = 7.0
) -> Optional[str]:
    """Convenience function to normalize audio to target LUFS.

    Args:
        input_file: Path to input audio file
        output_file: Path for output (auto-generated if None)
        target_lufs: Target LUFS level (-14 or -16 recommended)
        log_callback: Optional callback for logging
        true_peak: Maximum true peak in dBTP (-1.5 recommended)
        lra: Target loudness range in LU (7.0 recommended)

    Returns:
        Path to normalized audio file, or original if failed
    """
    normalizer = LUFSNormalizer()
    return normalizer.normalize_lufs(
        input_file,
        output_file,
        target_lufs=target_lufs,
        log_callback=log_callback,
        true_peak=true_peak,
        lra=lra
    )
