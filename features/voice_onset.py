"""Opt-in recovery of quiet opening words without changing the episode timeline."""

import io
import math
import subprocess
from typing import Callable

from pydub import AudioSegment


def level_voice_onset(audio: AudioSegment, log: Callable[[str], None]) -> AudioSegment:
    """Level the first five seconds, preserving silence, duration and later audio."""
    if len(audio) < 300:
        log("Opening-word correction skipped: recording is shorter than 300ms.")
        return audio
    reference = audio[:10000]
    levels = sorted(reference[start:start + 100].dBFS
                    for start in range(0, len(reference), 100)
                    if reference[start:start + 100].dBFS > -45)
    if not levels:
        log("Opening-word correction skipped: no usable speech-level reference.")
        return audio
    target_rms = 10 ** (min(-18, levels[len(levels) // 2]) / 20)
    context = audio[:7000]
    with io.BytesIO() as source:
        context.export(source, format="wav")
        source_data = source.getvalue()
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-af",
         f"dynaudnorm=f=100:g=3:r={target_rms}:p=0.85:m=40:b=1:t=0.001",
         "-f", "wav", "pipe:1"],
        input=source_data, capture_output=True, timeout=30, check=True)
    corrected = AudioSegment.from_file(io.BytesIO(result.stdout), format="wav")
    corrected = corrected.set_frame_rate(audio.frame_rate).set_channels(
        audio.channels).set_sample_width(audio.sample_width)
    if len(corrected) != len(context):
        raise ValueError("Opening-word correction changed the recording duration")
    end = min(5000, len(audio))
    blend = min(1000, end // 5)
    start = end - blend
    # Blend back to the original only after the opening words, never fade them in.
    transition = corrected[start:end].fade_out(blend).overlay(
        audio[start:end].fade_in(blend))
    log(f"Corrected quiet opening words (first {end / 1000:g}s, "
        f"reference {20 * math.log10(target_rms):.1f} dBFS). Later audio unchanged.")
    return corrected[:start] + transition + audio[end:]
