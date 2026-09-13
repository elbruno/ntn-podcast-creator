"""Short real-FFmpeg pipeline regressions; no model downloads or global stubs.

Run with test_smooth_ducking, audio_quality and lufs_normalizer tests; run the
legacy test_audio_balance separately because it replaces real modules in sys.modules.
"""

import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from pydub import AudioSegment

from features import audio_processor as pipeline
from features.audio_processor import AudioProcessor
from features.audio_quality import AudioQualityAnalyzer, AudioQualityConfig, AudioQualityReport
from features.lufs_normalizer import LUFSNormalizer
from tests.test_smooth_ducking import silence, tone


class PipelineCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.processor = AudioProcessor()
        self.reports = []
        self.logs = []
        self.voice = self.write(tone(3000), "voice.wav")

    def tearDown(self):
        reports = self.reports + [self.processor.last_quality_report]
        for report in reports:
            if report and report.preview_file and os.path.exists(report.preview_file):
                os.unlink(report.preview_file)

    def write(self, audio, name):
        path = str(self.root / name)
        with audio.export(path, format="wav"):
            pass
        return path

    def render(self, **kwargs):
        options = dict(voice_file=self.voice, output_file=str(self.root / "episode.mp3"),
                       denoise_audio=False, auto_balance_levels=False, auto_ducking=False,
                       quality_gate_enabled=True, quality_report_callback=self.reports.append,
                       log_callback=self.logs.append)
        options.update(kwargs)
        return self.processor.create_podcast(**options)

    def sidecar(self, path=None):
        return json.loads(Path((path or str(self.root / "episode.mp3")) + ".quality.json").read_text())

    @staticmethod
    def finish_mix(_analyzer, path, mix_report=None):
        # Most alignment tests need real mix analysis, not repeated loudnorm.
        report = copy.deepcopy(mix_report)
        report.file_path = os.fspath(path)
        report.analysis_kind = "file"
        return report


@unittest.skipUnless(shutil.which("ffmpeg"), "Requires real ffmpeg")
class TestFinalQualityPipeline(PipelineCase):
    def test_exact_exported_mp3_is_analyzed_after_real_normalization(self):
        voice = self.write(tone(4000, -32), "quiet.wav")
        calls = []
        normalize = pipeline.normalize_audio_lufs
        analyze = AudioQualityAnalyzer.analyze_file
        output = str(self.root / "episode.mp3")
        before = []
        measured = []

        def normalize_spy(*args, **kwargs):
            before.append(hashlib.sha256(
                Path(output).read_bytes()).hexdigest())
            calls.append("normalize")
            self.assertEqual(kwargs["true_peak"], -2)
            self.assertEqual(kwargs["target_lufs"], -17)
            self.assertEqual(kwargs["lra"], 8)
            return normalize(*args, **kwargs)

        def analyze_spy(analyzer, path, mix_report=None):
            calls.append("analyze")
            self.assertEqual(path, output)
            measured.append(hashlib.sha256(
                Path(path).read_bytes()).hexdigest())
            return analyze(analyzer, path, mix_report=mix_report)

        with patch.object(pipeline, "normalize_audio_lufs", side_effect=normalize_spy), \
                patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=analyze_spy):
            result = self.render(voice_file=voice, normalize_lufs=True,
                                 quality_config={"target_lufs": -17, "target_true_peak_dbtp": -2, "lra": 8})
        self.assertEqual(result, (output, None, None))
        self.assertEqual(calls, ["normalize", "analyze"])
        self.assertNotEqual(before, measured)
        self.assertEqual(measured[0], hashlib.sha256(
            Path(output).read_bytes()).hexdigest())
        report = self.reports[0]
        actual = LUFSNormalizer()._get_loudness_stats(
            output, -17, self.logs.append, true_peak=-2, lra=8)
        self.assertTrue(report.analysis_complete, report.to_dict())
        self.assertEqual(report.integrated_lufs, float(actual["input_i"]))
        self.assertEqual(report.true_peak_dbtp, float(actual["input_tp"]))
        # MP3 encoding shifts the mastered WAV's loudness (~0.45 LU here).
        # Exact final-file measurement above, not an ideal target, is the contract.
        self.assertAlmostEqual(report.integrated_lufs, -17, delta=0.6)
        self.assertIs(self.processor.last_quality_report, report)
        data = self.sidecar()
        self.assertEqual(data["schema"], "ntn-quality-v1")
        self.assertEqual(data["identity"],
                         pipeline._quality_file_identity(output))
        self.assertEqual(data["output_path"], os.path.realpath(output))
        self.assertNotIn("report", data)
        self.assertNotIn("ui", data)
        self.assertEqual(data["preview_file"], report.preview_file)
        self.assertEqual(data["preview_identity"],
                         pipeline._quality_file_identity(report.preview_file))
        self.assertTrue(Path(report.preview_file).is_file())
        self.assertEqual(data["metadata"]["settings"]
                         ["quality_config"]["target_true_peak_dbtp"], -2)
        with open(output, "rb") as source, open(report.preview_file, "rb") as preview:
            self.assertEqual(AudioSegment.from_file(source).raw_data,
                             AudioSegment.from_file(preview).raw_data)
        self.assertEqual(list(self.root.glob("podcast_normalize_*")), [])

    def test_disabled_resets_legacy_report_and_never_constructs_analyzer(self):
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            self.render()
        previous_preview = self.reports[-1].preview_file
        self.assertTrue(Path(previous_preview).is_file())
        self.assertTrue(
            Path(str(self.root / "episode.mp3") + ".quality.json").is_file())
        callback = Mock()
        with patch.object(pipeline, "AudioQualityAnalyzer", side_effect=AssertionError("disabled")) as analyzer, \
                patch.object(pipeline, "create_preview", side_effect=AssertionError("disabled")) as preview:
            result = self.render(quality_gate_enabled=False,
                                 quality_report_callback=callback)
        self.assertEqual(len(result), 3)
        self.assertTrue(Path(result[0]).is_file())
        self.assertIsNone(self.processor.last_quality_report)
        analyzer.assert_not_called()
        preview.assert_not_called()
        callback.assert_not_called()
        self.assertFalse(Path(result[0] + ".quality.json").exists())
        self.assertFalse(Path(previous_preview).exists())

    def test_rerender_retires_only_same_output_preview_and_leaves_new_alive(self):
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            output, _, _ = self.render()
            previous_preview = self.reports[-1].preview_file
            self.render(output_file=str(self.root / "other.mp3"))
            other_preview = self.reports[-1].preview_file
            self.assertTrue(Path(previous_preview).exists())
            # Simulate a new process: on-disk identity, not instance state,
            # authorizes retiring the prior preview.
            with patch.dict(pipeline._quality_previews, {}, clear=True):
                self.processor = AudioProcessor()
                self.render()
                new_preview = self.reports[-1].preview_file
                self.assertFalse(Path(previous_preview).exists())
                self.assertTrue(Path(new_preview).exists())
                self.assertTrue(Path(other_preview).exists())
                self.assertEqual(self.sidecar(output)[
                                 "preview_file"], new_preview)

    def test_failed_new_render_also_invalidates_old_certification(self):
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            output, _, _ = self.render()
        preview = self.reports[-1].preview_file
        with self.assertRaises(FileNotFoundError):
            self.render(voice_file=str(self.root / "missing.wav"),
                        quality_gate_enabled=False)
        self.assertFalse(Path(output + ".quality.json").exists())
        self.assertFalse(Path(preview).exists())

    def test_exit_registry_cleans_preview_even_when_sidecar_save_fails(self):
        with patch.dict(pipeline._quality_previews, {}, clear=True), \
                patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix), \
                patch.object(pipeline, "_write_quality_sidecar", side_effect=OSError("disk full")):
            self.render()
            preview = self.reports[-1].preview_file
            self.assertTrue(Path(preview).exists())
            pipeline._cleanup_quality_previews()
            self.assertFalse(Path(preview).exists())

    def test_preview_registered_before_report_serialization(self):
        with patch.dict(pipeline._quality_previews, {}, clear=True), \
                patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix), \
                patch.object(AudioQualityReport, "to_dict", side_effect=ValueError("cannot serialize")):
            output, _, _ = self.render()
            preview = self.reports[-1].preview_file
            self.assertTrue(Path(preview).exists())
            self.assertFalse(Path(output + ".quality.json").exists())
            pipeline._cleanup_quality_previews()
            self.assertFalse(Path(preview).exists())

    def test_rerender_does_not_delete_replaced_preview(self):
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            self.render()
        preview = self.reports[-1].preview_file
        Path(preview).write_bytes(b"not the original preview")
        self.render(quality_gate_enabled=False)
        self.assertEqual(Path(preview).read_bytes(),
                         b"not the original preview")

    def test_qc_exceptions_fail_closed_but_keep_export_and_callback(self):
        for stage in ("constructor", "mix", "file"):
            with self.subTest(stage=stage):
                if stage == "constructor":
                    failure = patch.object(
                        pipeline, "AudioQualityAnalyzer", side_effect=RuntimeError(stage))
                else:
                    failure = patch.object(
                        AudioQualityAnalyzer, "analyze_" + stage, side_effect=RuntimeError(stage))
                with failure:
                    result = self.render()
                report = self.reports[-1]
                self.assertEqual(result[1:], (None, None))
                self.assertGreater(Path(result[0]).stat().st_size, 0)
                self.assertEqual(report.status, "FAIL")
                self.assertIn("ANALYSIS_UNAVAILABLE", report.failures)
                self.assertIn(stage, report.analysis_errors[0])
                self.assertEqual(self.sidecar()["status"], "FAIL")
                self.assertTrue(
                    any("ANALYSIS_UNAVAILABLE" in text for text in self.logs))
                final = [
                    message for message in self.logs if "[AudioQC] RESULT:" in message][-1]
                self.assertIn("FAIL", final)
                self.assertIn("ANALYSIS_UNAVAILABLE", final)

    def test_incomplete_analysis_and_invalid_config_cannot_pass(self):
        with patch.object(AudioQualityAnalyzer, "analyze_file", return_value=AudioQualityReport()):
            self.render()
        self.assertIn("ANALYSIS_UNAVAILABLE", self.reports[-1].failures)
        result = self.render(quality_config={"ducking_attack_ms": -1})
        self.assertTrue(Path(result[0]).is_file())
        self.assertIn("ANALYSIS_UNAVAILABLE", self.reports[-1].failures)

    def test_preview_sidecar_and_callback_failures_do_not_stop_export(self):
        # A directory at the sidecar location gives a real save error, without
        # globally mocking open() used by FFmpeg and the preview helper.
        (self.root / "episode.mp3.quality.json").mkdir()
        callback = Mock(side_effect=RuntimeError("callback failed"))
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix), \
                patch.object(pipeline, "create_preview", side_effect=OSError("preview failed")):
            result = self.render(quality_report_callback=callback)
        self.assertTrue(Path(result[0]).is_file())
        callback.assert_called_once_with(self.processor.last_quality_report)
        self.assertTrue(self.processor.last_quality_report.analysis_complete)
        for text in ("preview failed", "Could not save quality report", "callback failed"):
            self.assertTrue(
                any(text in message for message in self.logs), self.logs)
        final = [
            message for message in self.logs if "[AudioQC] RESULT:" in message][-1]
        self.assertIn(self.processor.last_quality_report.status, final)
        self.assertIn("PREVIEW_UNAVAILABLE", final)

    def test_normalization_failures_remove_partial_files_and_keep_original_mp3(self):
        for mode in ("raise", "none", "original", "bad_wav", "mp3_export"):
            with self.subTest(mode=mode):
                original_bytes = []
                temporary_paths = []

                def failing_normalizer(source, output_file=None, **kwargs):
                    original_bytes.append(
                        (self.root / "episode.mp3").read_bytes())
                    temporary_paths.extend([source, output_file])
                    Path(output_file).write_bytes(b"partial WAV")
                    if mode == "raise":
                        raise RuntimeError("normalization failed")
                    if mode == "none":
                        return None
                    if mode == "original":
                        return source
                    return output_file

                original_load = self.processor.load_audio

                def load(path):
                    if mode == "mp3_export" and path.endswith("normalized.wav"):
                        broken = Mock()

                        def broken_export(path, **kwargs):
                            Path(path).write_bytes(b"partial MP3")
                            temporary_paths.append(path)
                            raise OSError("encoding failed")
                        broken.export.side_effect = broken_export
                        return broken
                    return original_load(path)

                with patch.object(pipeline, "normalize_audio_lufs", side_effect=failing_normalizer), \
                        patch.object(self.processor, "load_audio", side_effect=load):
                    result = self.render(
                        normalize_lufs=True, quality_gate_enabled=False)
                self.assertEqual(
                    Path(result[0]).read_bytes(), original_bytes[0])
                self.assertTrue(all(not Path(path).exists()
                                for path in temporary_paths))
                self.assertFalse(list(self.root.glob("podcast_normalize_*")))
                self.assertTrue(
                    any("Using unnormalized export" in log for log in self.logs))

    def test_legacy_target_lufs_is_used_when_config_has_no_target(self):
        with patch.object(pipeline, "normalize_audio_lufs", side_effect=lambda source, **_: source) as normalize:
            self.render(normalize_lufs=True, target_lufs=-19,
                        quality_config={}, quality_gate_enabled=False)
        self.assertEqual(normalize.call_args.kwargs["target_lufs"], -19)

    def test_request_callback_keeps_report_even_if_shared_legacy_slot_is_overwritten(self):
        captured = []

        def callback(report):
            captured.append(report)
            self.reports.append(report)
            self.render(quality_gate_enabled=False,
                        output_file=str(self.root / "other.mp3"))

        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            self.render(quality_report_callback=callback)
        self.assertEqual(len(captured), 1)
        self.assertIsNone(self.processor.last_quality_report)
        self.assertEqual(captured[0].file_path, str(self.root / "episode.mp3"))
        self.assertEqual(self.sidecar()["file_path"], captured[0].file_path)

    def test_optional_trailing_api_and_nonempty_return_triple_are_preserved(self):
        parameters = list(inspect.signature(
            AudioProcessor.create_podcast).parameters.values())
        self.assertEqual([param.name for param in parameters[-5:]],
                         ["log_callback", "quality_gate_enabled", "quality_config", "music_seed", "quality_report_callback"])
        self.assertEqual(
            [param.default for param in parameters[-4:]], [False, None, 0, None])
        self.assertTrue(all(
            param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for param in parameters))
        denoised = self.write(tone(3000, -20), "denoised.wav")
        transcript = str(self.root / "transcript.txt")
        with patch.object(pipeline, "denoise_audio_file", return_value=denoised), \
                patch.object(self.processor, "transcribe_podcast", return_value=transcript) as transcribe, \
                patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            result = self.render(denoise_audio=True, generate_transcript=True)
        self.assertEqual(
            result, (str(self.root / "episode.mp3"), denoised, transcript))
        self.assertEqual(transcribe.call_args.kwargs["audio_file"], result[0])

    def test_worst_preview_comes_from_final_episode_at_offset(self):
        voice = self.write(tone(22000), "long.wav")
        intro = self.write(tone(2000, -55, frequency=330), "intro.wav")
        music = self.write(tone(1000, -22, frequency=220), "loud_music.wav")
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            output, _, _ = self.render(voice_file=voice, intro_file=intro,
                                       background_files=[
                                           music], background_volume=100,
                                       background_segments=[(19000, 20000)])
        report = self.reports[-1]
        self.assertIn("MUSIC_MASKING_VOICE", report.failures)
        self.assertLessEqual(report.worst_section_start_seconds, 20)
        self.assertGreaterEqual(report.worst_section_end_seconds, 21)
        with open(output, "rb") as source, open(report.preview_file, "rb") as preview:
            rendered = AudioSegment.from_file(source)
            clip = AudioSegment.from_file(preview)
        self.assertEqual(len(clip), 15000)
        self.assertEqual(clip.raw_data, rendered[-15000:].raw_data)
        self.assertEqual(self.sidecar()["preview_file"], report.preview_file)


@unittest.skipUnless(shutil.which("ffmpeg"), "Requires real ffmpeg")
class TestMixStems(PipelineCase):
    def capture_render(self, **kwargs):
        stems = []
        real = AudioQualityAnalyzer.analyze_mix

        def capture(analyzer, voice, music=None, offset_seconds=0):
            stems.append((voice, music, offset_seconds))
            return real(analyzer, voice, music, offset_seconds)

        with patch.object(AudioQualityAnalyzer, "analyze_mix", autospec=True, side_effect=capture), \
                patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            self.render(**kwargs)
        return stems[0]

    def test_selective_post_duck_music_intro_outro_and_episode_offsets(self):
        voice = tone(4000)
        music = tone(1000, -35, frequency=220)
        intro = tone(2000, -28, frequency=330)
        outro = tone(2000, -30, frequency=550)
        music_path = self.write(music, "music.wav")
        actual_voice, actual_music, offset = self.capture_render(
            voice_file=self.write(voice, "long.wav"),
            intro_file=self.write(intro, "intro.wav"),
            outro_file=self.write(outro, "outro.wav"), voice_outro_overlap=True,
            background_files=[music_path], background_volume=100,
            background_segments=[(-100, 1000), (2000, 3000),
                                 (None, 200), (5000, 6000)],
            auto_ducking=True, quality_config=AudioQualityConfig(window_ms=250))
        self.assertEqual(offset, 1)
        self.assertEqual(actual_voice.raw_data, voice.raw_data)
        self.assertEqual(len(actual_music), 4000)
        expected = silence(4000)
        ducked = self.processor.apply_ducking(voice[:1000], music)
        expected = expected.overlay(ducked).overlay(ducked, position=2000)
        expected = expected.overlay(
            intro[-1000:]).overlay(outro[:1000], position=3000)
        self.assertEqual(actual_music.raw_data, expected.raw_data)
        self.assertEqual(actual_music[1000:2000].rms, 0)
        report = self.reports[-1]
        self.assertEqual(report.windows[0]["timestamp_start"], 1)
        self.assertEqual(report.windows[-1]["timestamp_end"], 5)
        tracks = self.sidecar()["metadata"]["selected_tracks"]
        self.assertEqual([track["start_ms"] for track in tracks], [0, 2000])
        self.assertEqual([track["episode_start_ms"]
                         for track in tracks], [1000, 3000])
        self.assertEqual([track["episode_end_ms"]
                         for track in tracks], [2000, 4000])
        with open(self.root / "episode.mp3", "rb") as source:
            self.assertEqual(len(AudioSegment.from_file(source)), 6000)

    def test_balancing_selective_quiet_voice_does_not_use_ignored_regain(self):
        voice = tone(1000, -18) + tone(1000, -36)
        music_path = self.write(tone(1000, -24, frequency=220), "music.wav")
        actual_voice, music, _ = self.capture_render(
            voice_file=self.write(voice, "varying.wav"), background_files=[music_path],
            background_volume=100, background_segments=[(1000, 2000)], auto_balance_levels=True)
        globally_balanced, _, _ = self.processor.auto_balance_audio(
            voice, apply_ducking=False)
        self.assertEqual(actual_voice.raw_data, globally_balanced.raw_data)
        self.assertAlmostEqual(
            actual_voice[1000:].dBFS - music[1000:].dBFS, 18, delta=0.2)
        self.assertEqual(music[:1000].rms, 0)

    def test_ducking_without_auto_balance_full_and_selective(self):
        music_path = self.write(tone(3000, -30, frequency=220), "music.wav")
        cfg = AudioQualityConfig(
            ducking_reduction_db=9, ducking_attack_ms=50, ducking_release_ms=600)
        for ranges in (None, [(0, 3000)]):
            with self.subTest(ranges=ranges):
                voice, music, _ = self.capture_render(background_files=[music_path], background_volume=100,
                                                      background_segments=ranges, auto_ducking=True,
                                                      quality_config=cfg)
                expected = self.processor.apply_ducking(voice, tone(3000, -30, frequency=220),
                                                        duck_db=9, attack_ms=50, release_ms=600)
                self.assertEqual(music.raw_data, expected.raw_data)
                self.assertAlmostEqual(music[2000:].dBFS, -39, delta=0.1)

    def test_nonoverlap_outro_fades_only_music_not_voice(self):
        voice = tone(3000, -24)
        music_path = self.write(tone(3000, -30, frequency=220), "music.wav")
        actual_voice, music, offset = self.capture_render(
            voice_file=self.write(voice, "unchanged.wav"), background_files=[music_path],
            background_volume=100, outro_file=self.write(tone(1000, -24), "outro.wav"))
        self.assertEqual(offset, 0)
        self.assertEqual(actual_voice.raw_data, voice.raw_data)
        expected = tone(3000, -30, frequency=220).fade_out(500)
        self.assertEqual(music.raw_data, expected.raw_data)
        self.assertLess(music[-50:].dBFS, music[:50].dBFS - 15)
        self.assertEqual(self.sidecar()["metadata"]["outro_offset_ms"], 3000)

    def test_outro_without_intro_keeps_actual_last_second_of_voice(self):
        voice = tone(1000, -25, frequency=440) + tone(1000, -25, frequency=880)
        outro = tone(1500, -32, frequency=220)
        captured = []
        export = AudioSegment.export

        def spy(audio, path, *args, **kwargs):
            if os.fspath(path) == str(self.root / "episode.mp3"):
                captured.append(audio)
            return export(audio, path, *args, **kwargs)

        with patch.object(AudioSegment, "export", autospec=True, side_effect=spy):
            self.capture_render(voice_file=self.write(voice, "changing.wav"),
                                outro_file=self.write(outro, "outro.wav"), voice_outro_overlap=True)
        expected = silence(2500).overlay(outro, position=1000).overlay(voice)
        self.assertEqual(captured[0].raw_data, expected.raw_data)

    def test_short_voice_intro_overlap_and_nonoverlap_offsets(self):
        for overlap, expected_offset, expected_duration in ((True, 1750, 2000), (False, 2000, 2250)):
            with self.subTest(overlap=overlap):
                _, music, offset = self.capture_render(
                    voice_file=self.write(tone(250), "short.wav"),
                    intro_file=self.write(tone(2000, -30), "intro.wav"), intro_voice_overlap=overlap)
                self.assertEqual(offset * 1000, expected_offset)
                self.assertEqual(len(music), 250)
                with open(self.root / "episode.mp3", "rb") as source:
                    self.assertEqual(
                        len(AudioSegment.from_file(source)), expected_duration)

    def test_overlapping_selected_ranges_are_measured_as_actually_summed(self):
        music = tone(1000, -32, frequency=220)
        music_path = self.write(music, "music.wav")
        _, actual, _ = self.capture_render(background_files=[music_path], background_volume=100,
                                           background_segments=[(0, 1000), (500, 1500)])
        expected = silence(3000).overlay(music).overlay(music, position=500)
        self.assertEqual(actual.raw_data, expected.raw_data)


class TestQualitySidecarPersistence(PipelineCase):
    def test_atomic_write_publishes_complete_json_in_same_directory(self):
        sidecar = self.root / "episode.mp3.quality.json"
        sidecar.write_text('{"old": true}')
        payload = {"metadata": {"music_seed": 23}, "identity": {"size": 5}}
        replace_file = os.replace

        def check_replace(source, destination):
            self.assertEqual(Path(source).parent, sidecar.parent)
            self.assertEqual(Path(destination), sidecar)
            self.assertEqual(json.loads(sidecar.read_text()), {"old": True})
            self.assertEqual(json.loads(Path(source).read_text()), payload)
            replace_file(source, destination)

        with patch.object(pipeline.os, "replace", side_effect=check_replace) as publish:
            pipeline._write_quality_sidecar(str(sidecar), payload)
        publish.assert_called_once()
        self.assertEqual(json.loads(sidecar.read_text()), payload)
        self.assertEqual(list(self.root.glob("*.json")), [sidecar])

    def test_failed_serialization_or_replace_removes_temp_not_previous_json(self):
        sidecar = self.root / "episode.mp3.quality.json"
        sidecar.write_text('{"old": true}')
        before = set(self.root.iterdir())
        with self.assertRaises(ValueError):
            pipeline._write_quality_sidecar(
                str(sidecar), {"bad": float("nan")})
        self.assertEqual(set(self.root.iterdir()), before)
        with patch.object(pipeline.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                pipeline._write_quality_sidecar(str(sidecar), {"new": True})
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertEqual(json.loads(sidecar.read_text()), {"old": True})

    def test_sidecar_symlink_is_rejected_and_replaced_without_touching_target(self):
        output = self.root / "episode.mp3"
        output.write_bytes(b"audio")
        target = self.root / "unrelated.json"
        target.write_text('{"do_not_change": true}')
        sidecar = Path(str(output) + ".quality.json")
        sidecar.symlink_to(target)
        with self.assertRaises(ValueError):
            pipeline._read_quality_sidecar(output)
        pipeline._write_quality_sidecar(str(sidecar), {"new": True})
        self.assertFalse(sidecar.is_symlink())
        self.assertEqual(json.loads(sidecar.read_text()), {"new": True})
        self.assertEqual(json.loads(target.read_text()),
                         {"do_not_change": True})


class TestMusicSelection(PipelineCase):
    def test_invalid_empty_duplicate_and_missing_tracks_terminate(self):
        corrupt = self.root / "corrupt.wav"
        corrupt.write_bytes(b"not audio")
        empty = self.write(AudioSegment.empty(), "empty.wav")
        missing = str(self.root / "missing.wav")
        logs = []
        with patch.object(self.processor, "load_audio", wraps=self.processor.load_audio) as load:
            result = self.processor.create_looped_background(
                [str(corrupt), str(corrupt), empty, missing], 1000, log_callback=logs.append)
        self.assertIsNone(result)
        self.assertEqual(load.call_count, 2)
        self.assertTrue(any("No playable" in log for log in logs))
        for duration in (0, -1):
            self.assertIsNone(
                self.processor.create_looped_background([empty], duration))

    def test_local_rng_reproducible_order_audio_and_global_state_unchanged(self):
        tracks = [self.write(tone(200, -30, frequency=f),
                             f"{f}.wav") for f in (220, 330, 440)]
        state = random.getstate()
        recordings = []
        orders = []
        for seed in (17, 17, 18):
            order = []
            audio = self.processor.create_looped_background(
                tracks, 1400, 100, {tracks[0]: 50}, self.logs.append,
                random.Random(seed), order)
            recordings.append(audio.raw_data)
            orders.append(order)
        self.assertEqual(recordings[0], recordings[1])
        self.assertEqual(orders[0], orders[1])
        self.assertNotEqual(orders[0], orders[2])
        self.assertEqual(random.getstate(), state)
        self.assertEqual(len(orders[0]), 7)
        self.assertEqual([item["start_ms"]
                         for item in orders[0]], list(range(0, 1400, 200)))

    @unittest.skipUnless(shutil.which("ffmpeg"), "Requires real ffmpeg")
    def test_render_seed_metadata_with_bad_track_and_repeated_render(self):
        good = self.write(tone(300, -32, frequency=220), "good.wav")
        other = self.write(tone(300, -32, frequency=550), "other.wav")
        bad = self.write(AudioSegment.empty(), "bad.wav")
        outputs = []
        state = random.getstate()
        with patch.object(AudioQualityAnalyzer, "analyze_file", autospec=True, side_effect=self.finish_mix):
            for name in ("first", "second"):
                path, _, _ = self.render(output_file=str(self.root / (name + ".mp3")),
                                         background_files=[bad, good, other], music_seed=9)
                outputs.append((Path(path).read_bytes(), self.sidecar(path)))
        self.assertEqual(outputs[0][0], outputs[1][0])
        self.assertEqual(outputs[0][1]["metadata"], outputs[1][1]["metadata"])
        self.assertEqual(outputs[0][1]["metadata"]["music_seed"], 9)
        self.assertTrue(outputs[0][1]["metadata"]["selected_tracks"])
        self.assertNotIn(
            bad, [track["path"] for track in outputs[0][1]["metadata"]["selected_tracks"]])
        self.assertEqual(random.getstate(), state)


class TestInspectorThresholds(PipelineCase):
    def test_custom_voice_range_is_not_overridden_by_legacy_very_low_band(self):
        cfg = AudioQualityConfig(voice_optimal_min_dbfs=-35, voice_target_dbfs=-30,
                                 voice_optimal_max_dbfs=-25)
        report = self.processor.analyze_levels(
            tone(dbfs=-30), quality_config=cfg)
        self.assertEqual(report["voice_status"], "optimal")
        self.assertIn("-35 a -25", report["voice_status_label"])
        self.assertFalse(report["warnings"])

    def test_named_voice_boundaries_match_labels_and_overall_warnings(self):
        for level, status in ((-22, "optimal"), (-14, "optimal"), (-11, "loud"), (-23, "low"), (-55, "silent")):
            with self.subTest(level=level):
                report = self.processor.analyze_levels(tone(dbfs=level))
                self.assertEqual(report["voice_status"], status)
                if status == "optimal":
                    self.assertIn("-22 a -14", report["voice_status_label"])
                    self.assertEqual(report["overall_status"], "optimal")
                    self.assertFalse(report["warnings"])
                else:
                    self.assertNotEqual(report["overall_status"], "optimal")
                    self.assertTrue(report["warnings"])

    def test_vmr_config_thresholds_and_text_use_same_limits(self):
        cfg = {"vmr_excellent_db": 22,
               "vmr_warning_db": 16, "vmr_failure_db": 10}
        for separation, expected in ((22, "optimal"), (18, "optimal"), (12, "warning"), (9, "danger")):
            with self.subTest(separation=separation):
                bg = self.write(tone(dbfs=-18 - separation), "music.wav")
                report = self.processor.analyze_levels(
                    tone(), [bg], 100, None, cfg)
                self.assertEqual(report["balance_status"], expected)
                self.assertEqual(report["overall_status"], expected)
                if expected == "danger":
                    self.assertIn("10 dB", report["warnings"][0])
                    self.assertIn("+22 dB", report["warnings"][0])
                elif expected == "warning":
                    self.assertIn("16 dB", report["warnings"][0])


if __name__ == "__main__":
    unittest.main()
