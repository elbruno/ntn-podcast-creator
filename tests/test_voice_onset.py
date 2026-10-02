"""Opening-word audibility regressions with real FFmpeg processing."""

import shutil
import subprocess
from unittest.mock import patch

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from features.voice_onset import level_voice_onset


pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="Requires FFmpeg")


def voice_with_quiet_opening():
    quiet = Sine(440).to_audio_segment(duration=500).apply_gain(-47)
    normal = Sine(440).to_audio_segment(duration=7000).apply_gain(-20)
    return AudioSegment.silent(duration=1000, frame_rate=44100) + quiet + normal


def test_first_words_are_audible_not_just_scaled_by_the_same_gain():
    source = voice_with_quiet_opening()
    logs = []
    result = level_voice_onset(source, logs.append)
    assert result[1000:1250].dBFS - source[1000:1250].dBFS > 20
    assert result[1500:1750].dBFS - result[1000:1250].dBFS < 8
    assert len(result) == len(source)
    assert result[:500].rms == 0
    assert result[5000:].raw_data == source[5000:].raw_data
    assert result.frame_rate == source.frame_rate
    assert result.sample_width == source.sample_width
    assert any("Corrected quiet opening words" in message for message in logs)

def test_recording_start_is_leveled_without_a_fade_in():
    source = (Sine(440).to_audio_segment(duration=500).apply_gain(-47)
              + Sine(440).to_audio_segment(duration=7000).apply_gain(-20))
    result = level_voice_onset(source, lambda _: None)
    assert result[:200].dBFS > source[:200].dBFS + 20
    assert result[1000:1200].dBFS - result[:200].dBFS < 8


@pytest.mark.parametrize("duration", [100, 300, 1500, 4500])
def test_short_recording_duration_is_preserved(duration):
    source = Sine(440).to_audio_segment(duration=duration).apply_gain(-20)
    result = level_voice_onset(source, lambda _: None)
    assert len(result) == len(source)


def test_silence_stays_silent_and_reports_why_correction_was_skipped():
    source = AudioSegment.silent(duration=7000)
    logs = []
    assert level_voice_onset(source, logs.append).raw_data == source.raw_data
    assert any("no usable speech-level reference" in message for message in logs)


def test_stereo_channels_are_coupled_without_changing_later_samples():
    mono = voice_with_quiet_opening()
    stereo = AudioSegment.from_mono_audiosegments(mono, mono - 6)
    result = level_voice_onset(stereo, lambda _: None)
    left, right = result.split_to_mono()
    assert result.channels == 2
    assert left[1000:1250].dBFS - right[1000:1250].dBFS == pytest.approx(6, abs=0.2)
    assert result[5000:].raw_data == stereo[5000:].raw_data


def test_ffmpeg_failure_is_not_silently_accepted():
    with patch("features.voice_onset.subprocess.run",
               side_effect=subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"failed")):
        with pytest.raises(subprocess.CalledProcessError):
            level_voice_onset(voice_with_quiet_opening(), lambda _: None)
