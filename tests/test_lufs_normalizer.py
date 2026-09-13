"""Regression tests for loudnorm parsing and measured two-pass normalization."""

import json
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from features import lufs_normalizer
from features.lufs_normalizer import LUFSNormalizer, normalize_audio_lufs


STATS = {
    "input_i": "-23.45",
    "input_tp": "-4.32",
    "input_lra": "3.21",
    "input_thresh": "-33.54",
    "target_offset": "0.12",
}


def report(stats):
    return "FFmpeg progress\n[Parsed_loudnorm_0] \n" + json.dumps(stats, indent=4) + "\n"


def filter_options(command):
    value = command[command.index("-af") + 1]
    return dict(option.split("=", 1) for option in value.split("=", 1)[1].split(":"))


class TestExtractLoudnormJSON(unittest.TestCase):
    def test_multiline_with_log_noise_and_braces_in_strings(self):
        stats = dict(STATS, note='braces { } and escaped "quotes"')
        self.assertEqual(
            lufs_normalizer.extract_loudnorm_json(
                "noise {not JSON}\n" + report(stats)),
            stats,
        )

    def test_malformed_missing_and_unrelated_objects(self):
        for text in ("", "no stats", '{"input_i":', '{"other": 1}', "[]"):
            with self.subTest(text=text):
                self.assertIsNone(lufs_normalizer.extract_loudnorm_json(text))
        for key in STATS:
            stats = {name: value for name,
                     value in STATS.items() if name != key}
            with self.subTest(missing=key):
                self.assertIsNone(
                    lufs_normalizer.extract_loudnorm_json(report(stats)))

    def test_last_complete_loudnorm_object_wins(self):
        last = dict(STATS, input_i="-18.0")
        text = report(STATS) + '{broken\n' + report(last)
        text += '\n{"unrelated": true}\n{"input_i": "-99"}\n{"input_i":'
        self.assertEqual(lufs_normalizer.extract_loudnorm_json(text), last)

    def test_nonfinite_stats_remain_available_for_qc(self):
        silence = dict(STATS, input_i="-inf",
                       input_tp="-inf", target_offset="inf")
        self.assertEqual(lufs_normalizer.extract_loudnorm_json(
            report(silence)), silence)
        # Do not silently replace the latest (silent) measurement with an older one.
        self.assertEqual(
            lufs_normalizer.extract_loudnorm_json(
                report(STATS) + report(silence)), silence
        )


class TestLUFSNormalizer(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.input_file = str(Path(self.directory.name) / "input.wav")
        self.output_file = str(Path(self.directory.name) / "output.wav")
        Path(self.input_file).touch()
        with patch.object(LUFSNormalizer, "_check_availability"):
            self.normalizer = LUFSNormalizer()
        self.normalizer.ffmpeg_available = True
        self.logs = []

    def fake_run(self, stats=STATS, analysis_code=0, output_code=0, mode="linear"):
        def run(command, **kwargs):
            if command[-1] == "-":
                return subprocess.CompletedProcess(command, analysis_code, "", report(stats))
            if output_code == 0:
                Path(command[-1]).write_bytes(b"test output")
            return subprocess.CompletedProcess(
                command, output_code, "", f"Normalization Type:   {mode}\n"
            )
        return run

    def test_measurement_old_positional_callback_and_raw_silence(self):
        silence = dict(STATS, input_i="-inf",
                       input_tp="-inf", target_offset="inf")
        with patch.object(subprocess, "run", side_effect=self.fake_run(silence)) as run:
            measured = self.normalizer._get_loudness_stats(
                self.input_file, -18.0, self.logs.append
            )
        self.assertEqual(measured, silence)
        self.assertTrue(
            any("Measured loudness: -inf" in line for line in self.logs))
        options = filter_options(run.call_args.args[0])
        self.assertEqual(options["I"], "-18.0")
        self.assertEqual(float(options["TP"]), -1.5)
        self.assertEqual(float(options["LRA"]), 7.0)

    def test_measurement_new_targets_follow_positional_callback(self):
        with patch.object(subprocess, "run", side_effect=self.fake_run()) as run:
            self.assertEqual(self.normalizer._get_loudness_stats(
                self.input_file, -20.0, self.logs.append, -2.0, 11.0
            ), STATS)
        options = filter_options(run.call_args.args[0])
        self.assertEqual((options["I"], options["TP"], options["LRA"]),
                         ("-20.0", "-2.0", "11.0"))

    def test_measurement_nonzero_exit_rejects_even_valid_json(self):
        with patch.object(subprocess, "run", side_effect=self.fake_run(analysis_code=1)):
            self.assertIsNone(self.normalizer._get_loudness_stats(
                self.input_file, log_callback=self.logs.append
            ))
        self.assertTrue(any("failed" in line.lower() for line in self.logs))

    def test_measured_values_offset_target_parity_and_modes(self):
        for mode in ("linear", "dynamic"):
            with self.subTest(mode=mode):
                self.logs.clear()
                with patch.object(subprocess, "run", side_effect=self.fake_run(mode=mode)) as run:
                    result = self.normalizer.normalize_lufs(
                        self.input_file, self.output_file, -19.0, -2.5, 11.0,
                        log_callback=self.logs.append
                    )
                self.assertEqual(result, self.output_file)
                self.assertEqual(run.call_count, 2)
                first, second = [filter_options(
                    call.args[0]) for call in run.call_args_list]
                for key, expected in (("I", -19.0), ("TP", -2.5), ("LRA", 11.0)):
                    self.assertEqual(first[key], second[key])
                    self.assertEqual(float(first[key]), expected)
                for key, measured in (("measured_I", "input_i"), ("measured_TP", "input_tp"),
                                      ("measured_LRA", "input_lra"),
                                      ("measured_thresh", "input_thresh"),
                                      ("offset", "target_offset")):
                    self.assertEqual(
                        float(second[key]), float(STATS[measured]))
                self.assertEqual(second["linear"], "true")
                self.assertTrue(any("two-pass" in line and "complete" in line.lower()
                                    and mode in line for line in self.logs))
                self.assertFalse(
                    any("single-pass" in line for line in self.logs))

    def test_missing_nonnumeric_and_nonfinite_values_fall_back(self):
        invalid_values = (None, True, [], {}, "bad", "-inf", "inf", "nan",
                          float("inf"), float("nan"), "1e999", "0:TP=0")
        for key in STATS:
            for value in invalid_values:
                with self.subTest(key=key, value=value):
                    stats = dict(STATS, **{key: value})
                    self.assert_single_pass_fallback(stats)
            with self.subTest(missing=key):
                self.assert_single_pass_fallback(
                    {k: v for k, v in STATS.items() if k != key})

    def assert_single_pass_fallback(self, stats):
        self.logs.clear()
        with patch.object(subprocess, "run", side_effect=self.fake_run()) as run:
            with patch.object(self.normalizer, "_get_loudness_stats", return_value=stats):
                result = self.normalizer.normalize_lufs(
                    self.input_file, self.output_file, log_callback=self.logs.append
                )
        self.assertEqual(result, self.output_file)
        options = filter_options(run.call_args.args[0])
        self.assertNotIn("measured_I", options)
        self.assertNotIn("offset", options)
        self.assertTrue(any("single-pass" in line and "fallback" in line.lower()
                            for line in self.logs))
        self.assertTrue(any("single-pass" in line and "complete" in line.lower()
                            for line in self.logs))
        self.assertFalse(any("two-pass" in line and "complete" in line.lower()
                             for line in self.logs))

    def test_json_numeric_measurements_are_accepted(self):
        stats = {key: float(value) for key, value in STATS.items()}
        with patch.object(subprocess, "run", side_effect=self.fake_run(stats)) as run:
            self.normalizer.normalize_lufs(self.input_file, self.output_file)
        self.assertIn("measured_I", filter_options(run.call_args.args[0]))

    def test_analysis_failure_falls_back(self):
        with patch.object(subprocess, "run", side_effect=self.fake_run(analysis_code=1)) as run:
            result = self.normalizer.normalize_lufs(
                self.input_file, self.output_file, log_callback=self.logs.append
            )
        self.assertEqual(result, self.output_file)
        self.assertEqual(run.call_count, 2)
        self.assertNotIn("measured_I", filter_options(run.call_args.args[0]))
        self.assertTrue(any("fallback" in line.lower() for line in self.logs))

    def test_explicit_single_pass_does_not_measure_or_claim_fallback(self):
        with patch.object(subprocess, "run", side_effect=self.fake_run()) as run:
            self.normalizer.normalize_lufs(
                self.input_file, self.output_file, two_pass=False, log_callback=self.logs.append
            )
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("measured_I", filter_options(run.call_args.args[0]))
        self.assertTrue(any("single-pass" in line and "complete" in line.lower()
                            for line in self.logs))
        self.assertFalse(any("fallback" in line.lower() for line in self.logs))

    def test_normalization_failure_does_not_claim_success_with_stale_output(self):
        Path(self.output_file).touch()
        with patch.object(subprocess, "run", side_effect=self.fake_run(output_code=1)):
            result = self.normalizer.normalize_lufs(
                self.input_file, self.output_file, log_callback=self.logs.append
            )
        self.assertEqual(result, self.input_file)
        self.assertFalse(any("complete" in line.lower() for line in self.logs))

    def test_success_exit_without_output_is_failure(self):
        result = subprocess.CompletedProcess([], 0, "", report(STATS))
        with patch.object(subprocess, "run", return_value=result):
            self.assertEqual(self.normalizer.normalize_lufs(
                self.input_file, self.output_file, log_callback=self.logs.append
            ), self.input_file)
        self.assertFalse(any("complete" in line.lower() for line in self.logs))

    def test_analysis_timeout_falls_back_and_output_timeout_returns_original(self):
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 300)):
            self.assertEqual(self.normalizer.normalize_lufs(
                self.input_file, self.output_file, log_callback=self.logs.append
            ), self.input_file)
        self.assertTrue(any("fallback" in line.lower() for line in self.logs))
        self.assertTrue(any("timed out" in line for line in self.logs))

    def test_convenience_api_keeps_callback_position_and_appends_targets(self):
        callback = self.logs.append
        with patch.object(LUFSNormalizer, "_check_availability"):
            with patch.object(LUFSNormalizer, "normalize_lufs", return_value=self.output_file) as normalize:
                self.assertEqual(normalize_audio_lufs(
                    self.input_file, self.output_file, -18.0, callback, -2.0, 11.0
                ), self.output_file)
        normalize.assert_called_once_with(
            self.input_file, self.output_file, target_lufs=-18.0,
            log_callback=callback, true_peak=-2.0, lra=11.0
        )


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for integration tests")
class TestRealFFmpeg(unittest.TestCase):
    def test_normal_wav_uses_actual_measured_two_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            source = str(Path(directory) / "normal.wav")
            output = str(Path(directory) / "normalized.wav")
            sample_rate = 44100
            with wave.open(source, "wb") as audio:
                audio.setparams(
                    (1, 2, sample_rate, 0, "NONE", "not compressed"))
                audio.writeframes(b"".join(
                    struct.pack("<h", int(32767 * (0.08 + 0.03 * math.sin(
                        2 * math.pi * index / sample_rate / 6
                    )) * math.sin(2 * math.pi * 440 * index / sample_rate)))
                    for index in range(sample_rate * 12)
                ))
            normalizer = LUFSNormalizer()
            logs = []
            with patch.object(subprocess, "run", wraps=subprocess.run) as run:
                result = normalizer.normalize_lufs(
                    source, output, -18.0, -2.0, 11.0, log_callback=logs.append
                )
            self.assertEqual(result, output, logs)
            self.assertGreater(Path(output).stat().st_size, 44)
            self.assertEqual(run.call_count, 2)
            first, second = [filter_options(call.args[0])
                             for call in run.call_args_list]
            for key in ("I", "TP", "LRA"):
                self.assertEqual(first[key], second[key])
            for key in ("measured_I", "measured_TP", "measured_LRA", "measured_thresh", "offset"):
                self.assertTrue(math.isfinite(float(second[key])))
            self.assertTrue(any("two-pass" in line and "complete" in line.lower()
                                and ("linear" in line or "dynamic" in line) for line in logs), logs)
            self.assertFalse(any("single-pass" in line for line in logs), logs)
            measured = normalizer._get_loudness_stats(
                output, -18.0, logs.append, -2.0, 11.0)
            self.assertIsNotNone(measured, logs)
            self.assertAlmostEqual(
                float(measured["input_i"]), -18.0, delta=0.5)
            self.assertLessEqual(float(measured["input_tp"]), -1.9)

    def test_silent_wav_preserves_raw_qc_stats_and_uses_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = str(Path(directory) / "silence.wav")
            output = str(Path(directory) / "normalized.wav")
            with wave.open(source, "wb") as audio:
                audio.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
                audio.writeframes(b"\x00\x00" * 44100 * 4)
            normalizer = LUFSNormalizer()
            logs = []
            stats = normalizer._get_loudness_stats(source, -16.0, logs.append)
            self.assertIsNotNone(stats, logs)
            self.assertFalse(math.isfinite(float(stats["input_i"])))
            with patch.object(subprocess, "run", wraps=subprocess.run) as run:
                result = normalizer.normalize_lufs(
                    source, output, log_callback=logs.append)
            self.assertEqual(result, output, logs)
            self.assertNotIn(
                "measured_I", filter_options(run.call_args.args[0]))
            self.assertTrue(any("fallback" in line.lower()
                            for line in logs), logs)


if __name__ == "__main__":
    unittest.main()
