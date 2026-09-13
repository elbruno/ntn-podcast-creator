"""Synthetic DSP regressions; no production audio or fabricated NTN fixtures.

Run independently with: python -m unittest tests.test_audio_quality -v
Some legacy test modules replace numpy/pydub globally with mocks at collection.
This suite intentionally uses real dependencies and does not install those mocks.
"""

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import asdict
from unittest.mock import patch

import numpy as np
from pydub import AudioSegment
import soundfile as sf

from features import audio_quality as quality
from features.audio_quality import (
    AudioQualityAnalyzer, AudioQualityConfig, AudioQualityReport, create_preview,
)


FFMPEG = shutil.which("ffmpeg")


def tone(seconds=2.0, dbfs=-18.0, frequency=440, sample_rate=16000):
    """A deterministic PCM tone with the requested RMS, not peak, level."""
    time = np.arange(int(round(seconds * sample_rate))) / sample_rate
    samples = np.sin(2 * np.pi * frequency * time) * \
        math.sqrt(2) * 10 ** (dbfs / 20)
    pcm = np.rint(samples * 32767).astype("<i2")
    return AudioSegment(pcm.tobytes(), sample_width=2, frame_rate=sample_rate, channels=1)


def silence(seconds):
    return AudioSegment.silent(duration=int(round(seconds * 1000)), frame_rate=16000)


def read_audio(path):
    with open(path, "rb") as source:
        return AudioSegment.from_file(source)


class TestConfigAndReport(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(asdict(AudioQualityConfig()), {
            "target_lufs": -16.0, "target_true_peak_dbtp": -1.5,
            "loudness_warning_lu": 1.0, "loudness_failure_lu": 2.0,
            "true_peak_failure_dbtp": -1.0, "voice_target_dbfs": -18.0,
            "voice_optimal_min_dbfs": -22.0, "voice_optimal_max_dbfs": -14.0,
            "vmr_excellent_db": 18.0, "vmr_warning_db": 12.0,
            "vmr_failure_db": 8.0, "vmr_critical_db": 0.0,
            "speech_threshold_dbfs": -42.0, "speech_relative_db": 14.0,
            "window_ms": 500, "silence_warning_seconds": 5.0,
            "silence_failure_seconds": 10.0, "silence_threshold_dbfs": -50.0,
            "ducking_reduction_db": 12.0, "ducking_attack_ms": 100,
            "ducking_release_ms": 450, "preview_seconds": 15.0, "lra": 7.0,
        })

    def test_mapping_converts_numbers_ignores_unrelated_settings(self):
        config = AudioQualityConfig.from_mapping({
            "target_lufs": "-17", "window_ms": "1000", "preview_seconds": None,
            "last_output_name": "ignored",
        })
        self.assertEqual(config.target_lufs, -17)
        self.assertEqual(config.window_ms, 1000)
        self.assertEqual(config.preview_seconds, 15)
        self.assertEqual(AudioQualityConfig.from_mapping(),
                         AudioQualityConfig())

    def test_invalid_config_rejected(self):
        for settings in (
            {"window_ms": 0}, {"window_ms": 100.5}, {"window_ms": True},
            {"target_lufs": "nan"}, {"target_lufs": -100},
            {"loudness_warning_lu": 3}, {"vmr_failure_db": 20},
            {"voice_optimal_min_dbfs": -10}, {"silence_warning_seconds": 20},
            {"preview_seconds": 0}, {"preview_seconds": 21},
            {"ducking_attack_ms": -1}, {"speech_relative_db": -1},
            {"target_true_peak_dbtp": -0.5}, {"speech_threshold_dbfs": 1},
        ):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                AudioQualityConfig.from_mapping(settings)

    def test_report_incomplete_never_passes_and_warn_is_reviewable(self):
        report = AudioQualityReport()
        self.assertFalse(report.passed)
        self.assertEqual(report.status, "FAIL")
        report.analysis_complete = True
        self.assertEqual(report.status, "PASS")
        report.warnings.append("REVIEW")
        self.assertEqual(report.status, "WARN")
        self.assertTrue(report.passed)
        report.failures.append("CLIPPING_DETECTED")
        self.assertEqual(report.status, "FAIL")

    def test_safe_json_html_and_independent_lists(self):
        dangerous = '<script>alert("x")</script>'
        report = AudioQualityReport(file_path=Path(dangerous), integrated_lufs=-math.inf,
                                    true_peak_dbtp=math.nan, clipped_samples=np.int64(2))
        report.windows.append({"voice_music_ratio_db": math.inf})
        report.failures.append(dangerous)
        report.recommendations.append(dangerous)
        report.analysis_errors.append(dangerous)
        result = json.loads(json.dumps(report.to_dict(), allow_nan=False))
        self.assertIsNone(result["integrated_lufs"])
        self.assertIsNone(result["metrics"]["true_peak_dbtp"])
        self.assertIsNone(result["windows"][0]["voice_music_ratio_db"])
        self.assertEqual(result["clipped_samples"], 2)
        self.assertFalse(result["passed"])
        rendered = report.to_html()
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertEqual(AudioQualityReport().failures, [])

    def test_python38_grammar(self):
        for module in (quality.__file__, __file__):
            with open(module, encoding="utf-8") as source:
                ast.parse(source.read(), feature_version=(3, 8))


class TestMixQuality(unittest.TestCase):
    def test_worst_section_has_readable_episode_timestamps(self):
        report = AudioQualityReport(worst_section_start_seconds=872.5,
                                    worst_section_end_seconds=887.5,
                                    failures=["MUSIC_MASKING_VOICE"])
        self.assertIn("14:32 – 14:47", report.to_html())
        self.assertIn("Possible music masking detected", report.to_html())

    def setUp(self):
        self.analyzer = AudioQualityAnalyzer()

    def test_good_voice_over_music(self):
        report = self.analyzer.analyze_mix(tone(), tone(dbfs=-40))
        self.assertEqual(report.status, "PASS")
        self.assertAlmostEqual(
            report.worst_voice_music_ratio_db, 22, delta=0.03)
        self.assertEqual(report.speech_below_warning_percentage, 0)
        self.assertEqual(len(report.windows), 4)
        self.assertTrue(report.music_present)

    def test_warning_failure_and_critical_reason_codes(self):
        for music_dbfs, status, critical in ((-28, "WARN", False), (-24, "FAIL", False),
                                             (-18, "FAIL", True), (-16, "FAIL", True)):
            with self.subTest(music_dbfs=music_dbfs):
                report = self.analyzer.analyze_mix(
                    tone(), tone(dbfs=music_dbfs))
                self.assertEqual(report.status, status)
                self.assertIn("MUSIC_MASKING_VOICE",
                              report.failures + report.warnings)
                self.assertEqual(
                    "MUSIC_DOMINATES_VOICE" in report.failures, critical)
                self.assertAlmostEqual(report.suggested_music_reduction_db,
                                       18 - report.worst_voice_music_ratio_db)
                self.assertTrue(
                    any("Reduce music by" in text for text in report.recommendations))

    def test_custom_vmr_and_window_thresholds(self):
        analyzer = AudioQualityAnalyzer(
            {"vmr_warning_db": 15, "window_ms": 1000})
        report = analyzer.analyze_mix(tone(), tone(dbfs=-32))
        self.assertEqual(report.status, "WARN")
        self.assertEqual(len(report.windows), 2)

    def test_no_music_empty_music_and_silent_music(self):
        for music in (None, AudioSegment.empty(), silence(2)):
            with self.subTest(music=type(music).__name__):
                report = self.analyzer.analyze_mix(tone(), music)
                self.assertEqual(report.status, "PASS")
                self.assertFalse(report.music_present)
                self.assertIsNone(report.worst_voice_music_ratio_db)
                self.assertEqual(report.speech_below_failure_percentage, 0)
                json.dumps(report.to_dict(), allow_nan=False)

    def test_no_voice_empty_voice_and_inaudible_voice(self):
        for voice in (None, AudioSegment.empty(), silence(3), tone(dbfs=-55)):
            with self.subTest(voice=type(voice).__name__):
                report = self.analyzer.analyze_mix(voice, tone(dbfs=-24))
                self.assertFalse(report.passed)
                self.assertIn("NO_VOICE", report.failures)
                self.assertIsNone(report.worst_voice_music_ratio_db)

    def test_low_and_loud_voice_optimal_range(self):
        low = self.analyzer.analyze_mix(tone(dbfs=-30))
        high = self.analyzer.analyze_mix(tone(dbfs=-11))
        self.assertIn("VOICE_TOO_QUIET", low.failures)
        self.assertIn("VOICE_TOO_LOUD", high.warnings)
        self.assertEqual(high.status, "WARN")
        self.assertEqual(self.analyzer.analyze_mix(
            tone(dbfs=-20)).status, "PASS")

    def test_speech_gaps_excluded(self):
        voice = tone(0.5) + silence(1) + tone(0.5)
        music = tone(0.5, -40) + tone(1, -10) + tone(0.5, -40)
        report = self.analyzer.analyze_mix(voice, music)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.speech_active_seconds, 1)
        self.assertEqual(len(report.windows), 2)
        self.assertEqual(report.windows[-1]["timestamp_start"], 1.5)

    def test_relative_activity_threshold_excludes_quiet_background(self):
        voice = tone(1, -18) + tone(0.5, -40)
        report = self.analyzer.analyze_mix(voice, tone(1.5, -40))
        self.assertEqual(report.speech_active_seconds, 1)
        self.assertEqual(report.status, "PASS")

    def test_short_clip_smaller_than_window(self):
        report = self.analyzer.analyze_mix(tone(0.025), tone(0.025, -24))
        self.assertEqual(len(report.windows), 1)
        self.assertEqual(report.speech_active_seconds, 0.025)
        self.assertEqual(report.worst_section_start_seconds, 0)
        self.assertEqual(report.worst_section_end_seconds, 0.025)
        self.assertIn("MUSIC_MASKING_VOICE", report.failures)

    def test_partial_window_percentages_and_percentiles_are_duration_weighted(self):
        report = self.analyzer.analyze_mix(
            tone(0.6), tone(0.5, -40) + tone(0.1, -20))
        self.assertAlmostEqual(report.speech_below_failure_percentage, 100 / 6)
        self.assertAlmostEqual(report.speech_below_warning_percentage, 100 / 6)
        self.assertAlmostEqual(
            report.median_voice_music_ratio_db, 22, delta=0.03)
        self.assertAlmostEqual(report.p10_voice_music_ratio_db, 2, delta=0.03)

    def test_one_short_masked_section_is_not_hidden_by_healthy_median(self):
        voice = tone(60)
        music = tone(29.5, -40) + tone(0.5, -22) + tone(30, -40)
        report = self.analyzer.analyze_mix(voice, music, offset_seconds=7)
        self.assertEqual(report.status, "FAIL")
        self.assertAlmostEqual(
            report.median_voice_music_ratio_db, 22, delta=0.03)
        self.assertAlmostEqual(
            report.worst_voice_music_ratio_db, 4, delta=0.03)
        self.assertAlmostEqual(
            report.speech_below_failure_percentage, 100 * 0.5 / 60)
        section = report.worst_section
        self.assertLessEqual(section["start_seconds"], 36.5)
        self.assertGreaterEqual(section["end_seconds"], 37)
        self.assertEqual(section["end_seconds"] - section["start_seconds"], 15)
        self.assertEqual(section["voice_music_ratio_db"],
                         report.worst_voice_music_ratio_db)
        self.assertAlmostEqual(
            report.suggested_music_reduction_db, 14, delta=0.03)

    def test_worst_section_bounds_at_both_edges(self):
        for music in (tone(0.5, -22) + tone(29.5, -40),
                      tone(29.5, -40) + tone(0.5, -22)):
            report = self.analyzer.analyze_mix(
                tone(30), music, offset_seconds=8)
            self.assertGreaterEqual(report.worst_section_start_seconds, 8)
            self.assertLessEqual(report.worst_section_end_seconds, 38)
            self.assertEqual(report.worst_section_end_seconds -
                             report.worst_section_start_seconds, 15)

    def test_short_music_tail_is_silence_not_looped_or_repeated(self):
        report = self.analyzer.analyze_mix(tone(1), tone(0.1, -24))
        # 100 ms of music in a 500 ms window: 6 + 10*log10(5) dB separation.
        self.assertAlmostEqual(
            report.worst_voice_music_ratio_db, 6 + 10 * math.log10(5), delta=0.03)
        self.assertFalse(report.windows[-1]["music_present"])
        self.assertEqual(report.status, "PASS")

    def test_antiphase_stereo_does_not_cancel_speech(self):
        mono = tone()
        stereo = AudioSegment.from_mono_audiosegments(
            mono, mono.invert_phase())
        report = self.analyzer.analyze_mix(stereo, tone(dbfs=-40))
        self.assertEqual(report.status, "PASS")
        self.assertAlmostEqual(report.voice_level_dbfs, -18, delta=0.03)

    def test_rms_uses_pcm_view_and_is_independent_of_sample_width(self):
        for width in (1, 2, 4):
            audio = tone().set_sample_width(width)
            with patch.object(AudioSegment, "get_array_of_samples", side_effect=AssertionError("Full copy")):
                report = self.analyzer.analyze_mix(audio)
            self.assertEqual(report.status, "PASS")
            self.assertAlmostEqual(report.voice_level_dbfs, -18, delta=0.1)

    def test_repeat_analysis_is_deterministic(self):
        voice, music = tone(3), tone(3, -24)
        first = self.analyzer.analyze_mix(voice, music).to_dict()
        second = self.analyzer.analyze_mix(voice, music).to_dict()
        self.assertEqual(first, second)

    def test_invalid_path_and_offset_cannot_pass(self):
        missing = self.analyzer.analyze_mix("/nonexistent/audio.wav")
        self.assertIn("MIX_ANALYSIS_UNAVAILABLE", missing.failures)
        for offset in (-1, math.nan, math.inf):
            self.assertFalse(self.analyzer.analyze_mix(
                tone(), offset_seconds=offset).passed)


class FileTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.analyzer = AudioQualityAnalyzer()

    def write(self, audio, name="render.wav"):
        path = os.path.join(self.temp.name, name)
        with audio.export(path, format="wav"):
            pass
        return path

    def measure(self, path, integrated=-16, peak=-2, mix_report=None):
        with patch.object(quality.LUFSNormalizer, "_get_loudness_stats", return_value={
            "input_i": str(integrated), "input_tp": str(peak),
        }):
            return self.analyzer.analyze_file(path, mix_report=mix_report)


class TestFinalFileQuality(FileTestCase):
    def test_good_final_file_and_exact_stats_api(self):
        path = self.write(tone())
        with patch.object(quality.LUFSNormalizer, "_get_loudness_stats", return_value={
            "input_i": "-16.1", "input_tp": "-2.0",
        }) as stats:
            report = self.analyzer.analyze_file(Path(path))
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.integrated_lufs, -16.1)
        self.assertEqual(report.file_path, path)
        self.assertEqual(report.clipped_samples, 0)
        self.assertEqual(report.longest_silence_seconds, 0)
        self.assertIsNone(report.worst_voice_music_ratio_db)
        args, kwargs = stats.call_args
        self.assertEqual(args, (path,))
        self.assertEqual(kwargs["target_lufs"], -16)
        self.assertEqual(kwargs["true_peak"], -1.5)
        self.assertEqual(kwargs["lra"], 7)
        self.assertTrue(callable(kwargs["log_callback"]))

    def test_loudness_threshold_boundaries(self):
        path = self.write(tone())
        for loudness, status in ((-16, "PASS"), (-17, "PASS"), (-18, "WARN"),
                                 (-18.01, "FAIL"), (-14, "WARN"), (-13.99, "FAIL")):
            with self.subTest(loudness=loudness):
                report = self.measure(path, integrated=loudness)
                self.assertEqual(report.status, status)
                if status != "PASS":
                    code = "LOUDNESS_TOO_LOW" if loudness < -16 else "LOUDNESS_TOO_HIGH"
                    self.assertIn(code, report.failures + report.warnings)

    def test_true_peak_threshold_boundaries(self):
        path = self.write(tone())
        for peak, status in ((-1.5, "PASS"), (-1.49, "WARN"), (-1, "WARN"), (-0.99, "FAIL")):
            with self.subTest(peak=peak):
                report = self.measure(path, peak=peak)
                self.assertEqual(report.status, status)
                if status != "PASS":
                    self.assertIn("TRUE_PEAK_TOO_HIGH",
                                  report.warnings + report.failures)

    def test_configurable_loudness_and_silence_thresholds(self):
        self.analyzer = AudioQualityAnalyzer({"target_lufs": -18, "silence_warning_seconds": 0.5,
                                              "silence_failure_seconds": 1})
        report = self.measure(self.write(
            tone() + silence(1.1) + tone()), integrated=-18)
        self.assertIn("SILENCE_TOO_LONG", report.failures)
        self.assertNotIn("LOUDNESS_TOO_LOW", report.warnings + report.failures)

    def test_clipping_counts_both_pcm_rails_and_channel_denominator(self):
        samples = np.zeros((16000, 2), dtype=np.int16)
        samples[:3, 0] = 32767
        samples[:5, 1] = -32768
        audio = AudioSegment(samples.tobytes(), sample_width=2,
                             frame_rate=16000, channels=2)
        report = self.measure(self.write(audio))
        self.assertEqual(report.clipped_samples, 8)
        self.assertEqual(report.clipped_percentage, 100 * 8 / 32000)
        self.assertIn("CLIPPING_DETECTED", report.failures)

    def test_float_overloads_not_hidden_by_integer_saturation(self):
        path = os.path.join(self.temp.name, "float.wav")
        samples = np.array(
            [[1.2, -1.2], [1.0, -1.0], [0.99999, -0.99999]], dtype=np.float32)
        sf.write(path, samples, 16000, subtype="FLOAT")
        clipped, total = quality._measure_clipping(path)
        self.assertEqual((clipped, total), (4, 6))

    def test_high_bit_depth_pcm_rails(self):
        samples = np.array([2147483647, -2147483648, 0, 10000], dtype=np.int32)
        for subtype in ("PCM_24", "PCM_32"):
            path = os.path.join(self.temp.name, subtype + ".wav")
            sf.write(path, samples, 16000, subtype=subtype)
            self.assertEqual(quality._measure_clipping(path), (2, 4))

    def test_nonfinite_audio_samples_fail_measurement(self):
        path = os.path.join(self.temp.name, "nonfinite.wav")
        sf.write(path, np.array([0, np.nan, np.inf]), 16000, subtype="FLOAT")
        with self.assertRaises(ValueError):
            quality._measure_clipping(path)

    def test_internal_silence_warn_fail_and_edges_ignored(self):
        for seconds, status in ((5, "PASS"), (6, "WARN"), (10, "WARN"), (11, "FAIL")):
            with self.subTest(seconds=seconds):
                path = self.write(silence(12) + tone(1) +
                                  silence(seconds) + tone(1) + silence(12))
                report = self.measure(path)
                self.assertEqual(report.status, status)
                self.assertAlmostEqual(
                    report.longest_silence_seconds, seconds, delta=0.02)
                self.assertEqual(len(report.silence_sections), 1)
                if status != "PASS":
                    self.assertIn("SILENCE_TOO_LONG",
                                  report.failures + report.warnings)
                    self.assertIsNotNone(report.worst_section)

    def test_only_edge_silence_does_not_warn(self):
        report = self.measure(self.write(silence(12) + tone(1) + silence(12)))
        self.assertEqual(report.longest_silence_seconds, 0)
        self.assertEqual(report.status, "PASS")

    def test_all_silence_fails_even_with_good_mocked_lufs(self):
        for seconds in (0.1, 12):
            report = self.measure(self.write(silence(seconds)))
            self.assertIn("NO_VOICE", report.failures)
            self.assertFalse(report.passed)
            self.assertEqual(report.longest_silence_seconds, seconds)

    def test_missing_empty_and_invalid_files_never_pass(self):
        missing = os.path.join(self.temp.name, "missing.wav")
        empty = self.write(AudioSegment.empty(), "empty.wav")
        invalid = os.path.join(self.temp.name, "invalid.wav")
        Path(invalid).write_bytes(b"not audio")
        for path in (missing, empty, invalid, None):
            with self.subTest(path=path):
                report = self.analyzer.analyze_file(path)
                self.assertFalse(report.passed)
                self.assertIn("FILE_ANALYSIS_UNAVAILABLE", report.failures)

    def test_unavailable_and_partial_loudness_never_pass(self):
        path = self.write(tone())
        for stats in (None, {}, {"input_i": "nan", "input_tp": "-2"},
                      {"input_i": "-inf", "input_tp": "-inf"},
                      {"input_i": "-16", "input_tp": "invalid"}):
            with self.subTest(stats=stats), patch.object(
                    quality.LUFSNormalizer, "_get_loudness_stats", return_value=stats):
                report = self.analyzer.analyze_file(path)
                self.assertFalse(report.passed)
                self.assertFalse(report.analysis_complete)
                json.dumps(report.to_dict(), allow_nan=False)

    def test_loudness_exception_and_clipping_unavailable(self):
        path = self.write(tone())
        with patch.object(quality.LUFSNormalizer, "_get_loudness_stats", side_effect=RuntimeError("offline")):
            report = self.analyzer.analyze_file(path)
        self.assertIn("LOUDNESS_ANALYSIS_UNAVAILABLE", report.failures)
        with patch.object(quality, "_measure_clipping", side_effect=RuntimeError("decoder unavailable")):
            report = self.measure(path)
        self.assertIn("CLIPPING_ANALYSIS_UNAVAILABLE", report.failures)
        self.assertIsNone(report.clipped_samples)
        self.assertFalse(report.passed)

    def test_mix_failures_preserved_without_mutating_mix_report(self):
        mix = self.analyzer.analyze_mix(tone(), tone(dbfs=-22))
        original = mix.to_dict()
        report = self.measure(self.write(tone()), mix_report=mix)
        self.assertIn("MUSIC_MASKING_VOICE", report.failures)
        self.assertEqual(report.integrated_lufs, -16)
        self.assertEqual(report.worst_section, mix.worst_section)
        report.windows[0]["timestamp_start"] = 99
        report.recommendations.append("new")
        self.assertEqual(mix.to_dict(), original)

    def test_incomplete_or_mismatched_mix_never_passes(self):
        path = self.write(tone())
        incomplete = AudioQualityReport(analysis_kind="mix")
        self.assertIn("MIX_ANALYSIS_UNAVAILABLE", self.measure(
            path, mix_report=incomplete).failures)
        out_of_bounds = self.analyzer.analyze_mix(
            tone(), tone(dbfs=-22), offset_seconds=50)
        self.assertIn("FILE_ANALYSIS_UNAVAILABLE", self.measure(
            path, mix_report=out_of_bounds).failures)
        self.assertFalse(self.measure(path, mix_report={}).passed)

    def test_logs_include_measured_values_and_reason(self):
        messages = []
        self.analyzer = AudioQualityAnalyzer(log_callback=messages.append)
        self.measure(self.write(tone()), integrated=-25)
        self.assertTrue(any("-25.00 LUFS" in message for message in messages))
        self.assertTrue(
            any("RESULT: FAIL - LOUDNESS_TOO_LOW" in message for message in messages))

    def test_mix_accepts_paths(self):
        voice = self.write(tone(), "voice.wav")
        music = self.write(tone(dbfs=-40), "music.wav")
        self.assertEqual(self.analyzer.analyze_mix(
            Path(voice), music).status, "PASS")


class TestPreviews(FileTestCase):
    def preview(self, path, report):
        result = create_preview(path, report)
        if result:
            self.addCleanup(lambda: os.path.exists(
                result) and os.unlink(result))
        return result

    def test_preview_is_bounded_final_render_not_stem(self):
        rendered = tone(20, -18, frequency=440) + tone(10, -20, frequency=880)
        path = self.write(rendered)
        before = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        report = AudioQualityReport(
            worst_section_start_seconds=25, worst_section_end_seconds=30)
        result = self.preview(path, report)
        self.assertEqual(result, report.preview_file)
        preview = read_audio(result)
        self.assertEqual(len(preview), 15000)
        self.assertEqual(preview.raw_data, rendered[-15000:].raw_data)
        self.assertNotEqual(result, path)
        self.assertEqual(hashlib.sha256(
            Path(path).read_bytes()).hexdigest(), before)
        second = self.preview(path, report)
        self.assertNotEqual(result, second)

    def test_short_file_and_out_of_bounds_section_are_clamped(self):
        path = self.write(tone(0.1))
        report = AudioQualityReport(
            worst_section_start_seconds=100, worst_section_end_seconds=120)
        preview = self.preview(path, report)
        self.assertEqual(len(read_audio(preview)), 100)

    def test_preview_never_exceeds_fifteen_seconds(self):
        path = self.write(tone(25))
        report = AudioQualityReport(preview_seconds=20)
        preview = self.preview(path, report)
        self.assertEqual(len(read_audio(preview)), 15000)

    def test_twenty_second_section_preview_keeps_worst_edge_window(self):
        self.analyzer = AudioQualityAnalyzer({"preview_seconds": 20})
        voice = tone(30)
        music = tone(0.5, -22) + tone(29.5, -40)
        report = self.analyzer.analyze_mix(voice, music)
        self.assertEqual(report.worst_section_end_seconds, 20)
        rendered = voice.overlay(music)
        path = self.write(rendered)
        result = self.preview(path, report)
        self.assertEqual(read_audio(result).raw_data,
                         rendered[:15000].raw_data)

    def test_invalid_preview_duration_and_missing_source_warn(self):
        path = self.write(tone())
        for seconds in (0, math.nan, math.inf, 0.0001):
            report = AudioQualityReport(preview_seconds=seconds)
            self.assertIsNone(self.preview(path, report))
            self.assertIn("PREVIEW_UNAVAILABLE", report.warnings)
        self.assertIsNone(self.preview(
            path + ".missing", AudioQualityReport()))

    def test_failed_preview_warns_without_leaking_temp_file(self):
        path = self.write(tone())
        report = AudioQualityReport(
            analysis_complete=True, preview_file="old.wav")
        descriptor, output = tempfile.mkstemp(
            dir=self.temp.name, suffix=".wav")
        with patch.object(quality.tempfile, "mkstemp", return_value=(descriptor, output)) as temporary:
            with patch.object(AudioSegment, "export", side_effect=OSError("export failed")):
                self.assertIsNone(create_preview(path, report))
            self.assertEqual(temporary.call_count, 1)
        self.assertFalse(os.path.exists(output))
        self.assertIsNone(report.preview_file)
        self.assertIn("PREVIEW_UNAVAILABLE", report.warnings)
        self.assertEqual(report.status, "WARN")


@unittest.skipUnless(FFMPEG, "Real FFmpeg integration requires ffmpeg on PATH")
class TestRealFFmpeg(FileTestCase):
    def test_normalized_synthetic_render_passes_and_quiet_render_fails(self):
        source = self.write(tone(4, -30, sample_rate=48000), "source.wav")
        output = os.path.join(self.temp.name, "normalized.wav")
        subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", source,
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=7", "-c:a", "pcm_s16le", output],
                       capture_output=True, check=True, timeout=60)
        good = self.analyzer.analyze_file(output)
        self.assertEqual(good.status, "PASS", good.to_dict())
        self.assertAlmostEqual(good.integrated_lufs, -16, delta=0.3)
        quiet = self.analyzer.analyze_file(source)
        self.assertIn("LOUDNESS_TOO_LOW", quiet.failures)

    def test_actual_float_clipping_and_unsafe_true_peak(self):
        path = os.path.join(self.temp.name, "overload.wav")
        sample_rate = 48000
        signal = np.sin(2 * np.pi * 1000 *
                        np.arange(sample_rate) / sample_rate) * 1.1
        sf.write(path, signal, sample_rate, subtype="FLOAT")
        report = self.analyzer.analyze_file(path)
        self.assertIn("TRUE_PEAK_TOO_HIGH", report.failures)
        self.assertIn("CLIPPING_DETECTED", report.failures)
        self.assertGreater(report.clipped_samples, 0)

    def test_silence_and_very_short_files_never_get_false_pass(self):
        silent = self.analyzer.analyze_file(self.write(silence(1)))
        self.assertIn("NO_VOICE", silent.failures)
        short = self.analyzer.analyze_file(self.write(tone(0.01)))
        self.assertFalse(short.passed)
        self.assertIn("LOUDNESS_ANALYSIS_UNAVAILABLE", short.failures)

    def test_ffmpeg_float_fallback_preserves_overloads_and_pcm_rails(self):
        floats = os.path.join(self.temp.name, "floats.wav")
        sf.write(floats, np.array(
            [1.2, -1.2, 1.0, -1.0, 0.99999]), 16000, subtype="FLOAT")
        pcm = os.path.join(self.temp.name, "pcm.wav")
        sf.write(pcm, np.array([32767, -32768, 100],
                 dtype=np.int16), 16000, subtype="PCM_16")
        with patch.object(quality, "sf", None):
            self.assertEqual(quality._measure_clipping(floats), (4, 5))
            self.assertEqual(quality._measure_clipping(pcm), (2, 3))

    def test_lossy_final_file_stats_are_not_taken_from_source(self):
        source = self.write(tone(2, -18, sample_rate=48000))
        rendered = os.path.join(self.temp.name, "final.mp3")
        subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", source,
                        "-af", "volume=-8dB", "-c:a", "libmp3lame", rendered],
                       capture_output=True, check=True, timeout=60)
        report = self.analyzer.analyze_file(rendered)
        actual = quality.LUFSNormalizer()._get_loudness_stats(
            rendered, -16, lambda message: None, true_peak=-1.5, lra=7)
        self.assertIsNotNone(actual)
        self.assertAlmostEqual(report.integrated_lufs,
                               float(actual["input_i"]))
        self.assertIn("LOUDNESS_TOO_LOW", report.failures)
        self.assertEqual(report.file_path, rendered)


if __name__ == "__main__":
    unittest.main()
