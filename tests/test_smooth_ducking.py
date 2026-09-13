"""Real PCM ducking tests. Run separately from legacy global-mock suites."""

import unittest

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

from features.audio_processor import AudioProcessor


def tone(duration=1000, dbfs=-18, frequency=440, rate=16000):
    audio = Sine(frequency, sample_rate=rate).to_audio_segment(
        duration=duration)
    return audio.apply_gain(dbfs - audio.dBFS)


def silence(duration):
    return AudioSegment.silent(duration=duration, frame_rate=16000)


def constant(duration, channels=1, width=2, rate=16000):
    # A DC test signal exposes the gain envelope without sine zero crossings.
    level = 2 ** (width * 8 - 3)
    data = np.full((round(duration * rate / 1000), channels), level,
                   dtype=np.dtype("i{}".format(width)))
    return AudioSegment(data.tobytes(), sample_width=width, frame_rate=rate, channels=channels)


def gains(audio, original):
    dtype = np.dtype("i{}".format(audio.sample_width))
    return (np.frombuffer(audio.raw_data, dtype=dtype).astype(float) /
            np.frombuffer(original.raw_data, dtype=dtype))


class TestSmoothDucking(unittest.TestCase):
    def setUp(self):
        self.processor = AudioProcessor()

    def test_continuous_attack_release_and_default_reduction(self):
        voice = silence(200) + tone(1400) + silence(2000)
        music = constant(len(voice))
        ducked = self.processor.apply_ducking(voice, music)
        gain = gains(ducked, music)
        def at(ms): return gain[round(ms * 16)]
        self.assertEqual(len(ducked.raw_data), len(music.raw_data))
        np.testing.assert_array_equal(gain[:3200], np.ones(3200))
        self.assertGreater(at(200), at(250))
        self.assertGreater(at(250), at(300))
        self.assertGreater(at(300), at(800))
        self.assertAlmostEqual(at(1400), 10 ** (-12 / 20), delta=0.001)
        self.assertGreater(at(1700), at(1600))
        self.assertGreater(at(2000), at(1700))
        self.assertGreater(at(3500), 0.98)
        # No gain jump at activity boundaries or old 250ms block boundaries.
        self.assertLess(float(np.max(np.abs(np.diff(gain)))), 0.001)

    def test_configurable_time_constants_and_reduction(self):
        music = constant(3000)
        voice = tone(1000) + silence(2000)
        ducked = self.processor.apply_ducking(
            voice, music, duck_db=8, attack_ms=50, release_ms=600)
        gain = gains(ducked, music)
        target = 10 ** (-8 / 20)
        self.assertAlmostEqual(
            gain[799], target + (1 - target) / np.e, delta=0.001)
        self.assertAlmostEqual(gain[15999], target, delta=0.001)
        self.assertAlmostEqual(
            gain[25599], 1 + (target - 1) / np.e, delta=0.001)

    def test_caller_chunk_window_is_honored_but_capped(self):
        voice = silence(105) + tone(60) + silence(235)
        music = constant(400)
        fine = self.processor.apply_ducking(voice, music, chunk_ms=5)
        twenty = self.processor.apply_ducking(voice, music, chunk_ms=20)
        coarse = self.processor.apply_ducking(voice, music, chunk_ms=1000)
        self.assertEqual(twenty.raw_data, coarse.raw_data)
        self.assertNotEqual(fine.raw_data, coarse.raw_data)
        fine_gain = gains(fine, music)
        self.assertEqual(fine_gain[104 * 16], 1)
        self.assertLess(fine_gain[110 * 16], 1)
        self.assertLess(gains(coarse, music)[140 * 16], 1)

    def test_release_continues_after_voice_ends(self):
        music = constant(2000)
        ducked = self.processor.apply_ducking(tone(500), music)
        gain = gains(ducked, music)
        self.assertLess(abs(gain[8000] - gain[7999]), 0.001)
        self.assertLess(gain[8016], 0.3)
        self.assertGreater(gain[-1], 0.96)

    def test_silence_empty_inputs_zero_reduction_and_invalid_chunk(self):
        music = constant(300)
        for voice, reduction in ((silence(300), 12), (AudioSegment.empty(), 12), (tone(300), 0)):
            with self.subTest(reduction=reduction, duration=len(voice)):
                self.assertEqual(self.processor.apply_ducking(
                    voice, music, duck_db=reduction).raw_data, music.raw_data)
        self.assertEqual(len(self.processor.apply_ducking(
            tone(), AudioSegment.empty())), 0)
        for chunk in (0, -1):
            self.assertEqual(len(self.processor.apply_ducking(
                tone(300), music, chunk_ms=chunk)), 300)

    def test_stereo_and_sample_widths_preserve_format_and_channels(self):
        for width in (1, 2, 4):
            for rate in (16000, 44100, 48000):
                with self.subTest(width=width, rate=rate):
                    music = constant(537, channels=2, width=width, rate=rate)
                    result = self.processor.apply_ducking(tone(537), music)
                    self.assertEqual((result.sample_width, result.channels, result.frame_rate),
                                     (width, 2, rate))
                    self.assertEqual(len(result.raw_data), len(music.raw_data))
                    samples = np.frombuffer(
                        result.raw_data, dtype=np.dtype("i{}".format(width)))
                    np.testing.assert_array_equal(samples[::2], samples[1::2])
                    self.assertGreaterEqual(int(samples.min()), 0)
                    self.assertLessEqual(
                        int(samples.max()), 2 ** (width * 8 - 3))

    def test_antiphase_voice_still_triggers_ducking_and_zero_times_work(self):
        mono = tone(1000)
        voice = AudioSegment.from_mono_audiosegments(mono, mono.invert_phase())
        music = constant(1000, channels=2)
        ducked = self.processor.apply_ducking(
            voice, music, attack_ms=0, release_ms=0)
        np.testing.assert_allclose(
            gains(ducked, music), 10 ** (-12 / 20), atol=0.001)

    def test_original_positional_arguments_remain_usable(self):
        voice, music = tone(700), constant(700)
        result = self.processor.apply_ducking(
            voice, music, 6, 10, -42, lambda _: None)
        self.assertAlmostEqual(gains(result, music)
                               [-1], 10 ** (-6 / 20), delta=0.001)


if __name__ == "__main__":
    unittest.main()
