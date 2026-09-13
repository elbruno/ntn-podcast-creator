"""Deterministic, local audio QC; this module never modifies the source audio.

Mix analysis requires separate, already gain-adjusted voice/music stems. It is an
energy-based activity estimate, not speech recognition or source separation.
Final-file analysis measures the exact supplied render, not a normalized copy.
"""

import copy
import html
import math
import os
import subprocess
import tempfile
import wave
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

import numpy as np
from pydub import AudioSegment

from .lufs_normalizer import LUFSNormalizer

try:
    import soundfile as sf
except ImportError:
    sf = None


@dataclass(frozen=True)
class AudioQualityConfig:
    """Shared thresholds. Unknown mapping keys are ignored; invalid values raise."""

    target_lufs: float = -16.0
    target_true_peak_dbtp: float = -1.5
    loudness_warning_lu: float = 1.0
    loudness_failure_lu: float = 2.0
    true_peak_failure_dbtp: float = -1.0
    voice_target_dbfs: float = -18.0
    voice_optimal_min_dbfs: float = -22.0
    voice_optimal_max_dbfs: float = -14.0
    vmr_excellent_db: float = 18.0
    vmr_warning_db: float = 12.0
    vmr_failure_db: float = 8.0
    vmr_critical_db: float = 0.0
    speech_threshold_dbfs: float = -42.0
    speech_relative_db: float = 14.0
    window_ms: int = 500
    silence_warning_seconds: float = 5.0
    silence_failure_seconds: float = 10.0
    silence_threshold_dbfs: float = -50.0
    ducking_reduction_db: float = 12.0
    ducking_attack_ms: int = 100
    ducking_release_ms: int = 450
    preview_seconds: float = 15.0
    lra: float = 7.0

    @classmethod
    def from_mapping(cls, mapping: Optional[Mapping[str, Any]] = None) -> "AudioQualityConfig":
        """Accept a flat settings mapping, including numeric strings/extra keys."""
        if mapping is None:
            return cls()
        values = {}
        for item in fields(cls):
            value = mapping.get(item.name)
            if value is None:
                continue
            if isinstance(value, bool):
                raise ValueError(
                    "{} must be numeric, not boolean".format(item.name))
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("{} must be finite".format(item.name))
            if item.type is int:
                if not number.is_integer():
                    raise ValueError("{} must be an integer".format(item.name))
                number = int(number)
            values[item.name] = number
        return cls(**values)

    def __post_init__(self):
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("{} must be numeric".format(item.name))
            if not math.isfinite(value):
                raise ValueError("{} must be finite".format(item.name))
            if item.type is int and not isinstance(value, int):
                raise ValueError("{} must be an integer".format(item.name))
        if not (0 <= self.loudness_warning_lu <= self.loudness_failure_lu):
            raise ValueError(
                "Loudness tolerances must be nonnegative and ordered")
        if not (-70 <= self.target_lufs <= -5 and 1 <= self.lra <= 50):
            raise ValueError(
                "LUFS/LRA targets are outside FFmpeg's supported range")
        if not (-9 <= self.target_true_peak_dbtp <= self.true_peak_failure_dbtp <= 0):
            raise ValueError(
                "True peak thresholds must be ordered between -9 and 0")
        if not (self.voice_optimal_min_dbfs <= self.voice_target_dbfs
                <= self.voice_optimal_max_dbfs <= 0):
            raise ValueError("Voice target must be inside the optimal range")
        if not (self.vmr_critical_db < self.vmr_failure_db
                <= self.vmr_warning_db <= self.vmr_excellent_db):
            raise ValueError("VMR thresholds must be ordered")
        if not (0 <= self.silence_warning_seconds <= self.silence_failure_seconds):
            raise ValueError(
                "Silence thresholds must be nonnegative and ordered")
        if self.window_ms <= 0 or not 0 < self.preview_seconds <= 20:
            raise ValueError(
                "Window must be positive; preview must be in (0, 20]")
        if min(self.speech_relative_db, self.ducking_reduction_db,
               self.ducking_attack_ms, self.ducking_release_ms) < 0:
            raise ValueError(
                "Relative threshold and ducking settings cannot be negative")
        if max(self.silence_threshold_dbfs, self.speech_threshold_dbfs) > 0:
            raise ValueError(
                "Activity thresholds cannot exceed digital full scale")


def _json_safe(value):
    """Convert nonfinite measurements to null, including nested window values."""
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    return value


@dataclass
class AudioQualityReport:
    """Metrics plus stable reason codes. WARN permits review; FAIL does not pass.

    None means unavailable/not applicable, never zero. An uncompleted analysis
    cannot PASS. A file report without mix_report makes no claim about VMR.
    """

    file_path: Optional[str] = None
    preview_file: Optional[str] = None
    analysis_kind: str = "file"
    analysis_complete: bool = False
    duration_seconds: Optional[float] = None
    integrated_lufs: Optional[float] = None
    true_peak_dbtp: Optional[float] = None
    clipped_samples: Optional[int] = None
    clipped_percentage: Optional[float] = None
    longest_silence_seconds: Optional[float] = None
    voice_level_dbfs: Optional[float] = None
    speech_active_seconds: float = 0.0
    music_present: bool = False
    median_voice_music_ratio_db: Optional[float] = None
    p10_voice_music_ratio_db: Optional[float] = None
    worst_voice_music_ratio_db: Optional[float] = None
    speech_below_warning_percentage: Optional[float] = None
    speech_below_failure_percentage: Optional[float] = None
    suggested_music_reduction_db: float = 0.0
    worst_section_start_seconds: Optional[float] = None
    worst_section_end_seconds: Optional[float] = None
    worst_section_voice_music_ratio_db: Optional[float] = None
    windows: List[Dict[str, Any]] = field(default_factory=list)
    silence_sections: List[Dict[str, float]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analysis_errors: List[str] = field(default_factory=list)
    preview_seconds: float = 15.0

    @property
    def passed(self) -> bool:
        return self.analysis_complete and not self.failures

    @property
    def status(self) -> str:
        if not self.passed:
            return "FAIL"
        return "WARN" if self.warnings else "PASS"

    @property
    def worst_section(self) -> Optional[Dict[str, Any]]:
        if self.worst_section_start_seconds is None:
            return None
        return {
            "start_seconds": self.worst_section_start_seconds,
            "end_seconds": self.worst_section_end_seconds,
            # The lowest individual window, NOT an average of the preview.
            "voice_music_ratio_db": self.worst_section_voice_music_ratio_db,
        }

    @property
    def metrics(self) -> Dict[str, Any]:
        excluded = {"file_path", "preview_file", "analysis_kind", "analysis_complete",
                    "windows", "silence_sections", "warnings", "failures",
                    "recommendations", "analysis_errors", "preview_seconds"}
        return _json_safe({item.name: getattr(self, item.name)
                           for item in fields(self) if item.name not in excluded})

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result.update(status=self.status, passed=self.passed,
                      metrics=self.metrics, worst_section=self.worst_section)
        return _json_safe(result)

    def to_html(self) -> str:
        """Render text only: paths, errors, codes and recommendations are escaped."""
        def escape(value): return html.escape(str(value), quote=True)
        rows = "".join("<tr><th>{}</th><td>{}</td></tr>".format(
            escape(key), escape("N/A" if value is None else value))
            for key, value in self.metrics.items())
        notes = self.failures + self.warnings + \
            self.analysis_errors + self.recommendations
        if not self.analysis_complete:
            notes = ["ANALYSIS_UNAVAILABLE"] + notes
        section = ""
        if self.worst_section_start_seconds is not None and self.worst_section_end_seconds is not None:
            def timestamp(seconds):
                minutes, remainder = divmod(max(0, int(seconds)), 60)
                return "{:02d}:{:02d}".format(minutes, remainder)
            label = ("Possible music masking detected" if "MUSIC_MASKING_VOICE" in self.failures + self.warnings
                     else "Worst section — review recommended")
            section = "<p><strong>{}</strong><br>{} – {}</p>".format(
                escape(label), timestamp(self.worst_section_start_seconds),
                timestamp(self.worst_section_end_seconds))
        return ('<section class="audio-quality"><h3>Audio quality: {}</h3>'
                '<p>{}</p>{}<table>{}</table><ul>{}</ul></section>').format(
                    escape(self.status), escape(
                        self.file_path or self.analysis_kind),
                    section, rows, "".join("<li>{}</li>".format(escape(note)) for note in notes))


def _finite(value) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _level(audio: AudioSegment) -> float:
    # Preserve channel energy: downmixing anti-phase stereo would cancel speech.
    # View existing PCM and accumulate in bounded blocks, even for long episodes.
    samples = np.frombuffer(audio.raw_data, dtype=np.dtype(
        "i{}".format(audio.sample_width)))
    if not samples.size:
        return -math.inf
    energy = 0.0
    for start in range(0, samples.size, 65536):
        block = samples[start:start +
                        65536].astype(np.float64) / audio.max_possible_amplitude
        energy += float(np.sum(block * block))
    rms = math.sqrt(energy / samples.size)
    return 20 * math.log10(rms) if rms > 0 else -math.inf


def _load_audio(path) -> AudioSegment:
    # Own the handle: pydub's path-based decoder can leave it open on exceptions.
    with open(os.fspath(path), "rb") as source:
        return AudioSegment.from_file(source)


def _bounds(center: float, duration: float, length: float,
            offset: float = 0.0) -> Tuple[float, float]:
    length = min(length, duration)
    start = min(max(offset, center - length / 2), offset + duration - length)
    return start, start + length


def _weighted_quantile(values, weights, quantile: float) -> float:
    """Duration-weighted empirical quantile (no interpolation across infinity)."""
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(np.asarray(weights)[order])
    index = np.searchsorted(cumulative, quantile * cumulative[-1], side="left")
    return float(np.asarray(values)[order][index])


def _count_clipping(blocks, positive_full_scale: float) -> Tuple[int, int]:
    clipped, total = 0, 0
    for block in blocks:
        if not np.isfinite(block).all():
            raise ValueError("Decoded audio contains nonfinite samples")
        clipped += int(np.count_nonzero((block >=
                       positive_full_scale) | (block <= -1.0)))
        # Channel samples, not frames or downmixed samples.
        total += int(block.size)
    if total == 0:
        raise ValueError("Decoded audio has no samples")
    return clipped, total


def _measure_clipping(path: str) -> Tuple[int, int]:
    """Read floats without saturating; include both rails of integer PCM.

    Soundfile is streamed in blocks. Unsupported codecs fall back to FFmpeg
    float64 output in a temporary file, avoiding a full float copy in RAM.
    """
    if sf is not None:
        try:
            with sf.SoundFile(path) as source:
                bits = {"PCM_U8": 8, "PCM_S8": 8, "PCM_16": 16,
                        "PCM_24": 24, "PCM_32": 32}.get(source.subtype)
                positive = 1.0 - 2.0 ** (1 - bits) if bits else 1.0
                return _count_clipping(source.blocks(blocksize=65536, dtype="float64"),
                                       positive)
        except (RuntimeError, OSError):
            pass  # Unsupported by libsndfile; FFmpeg may still decode it.
    positive = 1.0
    try:
        with wave.open(path, "rb") as source:
            positive -= 2.0 ** (1 - 8 * source.getsampwidth())
    except (wave.Error, EOFError):
        pass  # Compressed or float data uses normalized floating full scale.
    with tempfile.TemporaryFile() as decoded:
        result = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-map", "0:a:0",
             "-vn", "-f", "f64le", "-acodec", "pcm_f64le", "-"],
            stdout=decoded, stderr=subprocess.PIPE, timeout=300)
        if result.returncode:
            raise RuntimeError("FFmpeg float decoding failed: " +
                               result.stderr.decode("utf-8", errors="replace"))
        decoded.seek(0)

        def blocks():
            while True:
                block = np.fromfile(decoded, dtype="<f8", count=65536)
                if not block.size:
                    break
                yield block

        return _count_clipping(blocks(), positive)


class AudioQualityAnalyzer:
    def __init__(self, config: Optional[Union[AudioQualityConfig, Mapping[str, Any]]] = None,
                 log_callback: Optional[Callable[[str], None]] = None):
        self.config = (config if isinstance(config, AudioQualityConfig)
                       else AudioQualityConfig.from_mapping(config))
        self.log_callback = log_callback or (lambda message: None)

    def _log(self, message: str):
        self.log_callback("[AudioQC] " + message)

    def _issue(self, report, code, recommendation, failure=True):
        codes = report.failures if failure else report.warnings
        if code not in codes:
            codes.append(code)
        if recommendation and recommendation not in report.recommendations:
            report.recommendations.append(recommendation)
        self._log("{}: {}".format(code, recommendation))

    def _unavailable(self, report, code, error):
        report.analysis_complete = False
        report.analysis_errors.append(str(error))
        self._issue(
            report, code, "Restore analysis support and run the quality check again.")
        self._log("Analysis unavailable: {}".format(error))

    def _finish(self, report):
        self._log("RESULT: {}{}".format(
            report.status, " - " + ", ".join(report.failures + report.warnings)
            if report.failures or report.warnings else ""))
        return report

    def analyze_mix(self, voice, music=None, offset_seconds=0) -> AudioQualityReport:
        """Analyze AudioSegments or paths to already aligned, processed stems.

        Both stems begin at local zero; short music is padded with silence and
        extra music is ignored. offset_seconds shifts report timestamps into the
        final episode (e.g. after an intro), NOT the alignment of the two stems.
        Only speech-active windows contribute; percentages and quantiles are
        weighted by their actual durations, including a partial final window.
        """
        cfg = self.config
        report = AudioQualityReport(
            analysis_kind="mix", preview_seconds=cfg.preview_seconds)
        try:
            offset = float(offset_seconds)
            if not math.isfinite(offset) or offset < 0:
                raise ValueError(
                    "offset_seconds must be finite and nonnegative")
            if voice is None:
                voice = AudioSegment.empty()
            elif not isinstance(voice, AudioSegment):
                voice = _load_audio(voice)
            if music is not None and not isinstance(music, AudioSegment):
                music = _load_audio(music)
            duration = len(voice) / 1000.0
            report.duration_seconds = offset + duration
            report.analysis_complete = True
            baseline = _level(voice)
            threshold = max(cfg.speech_threshold_dbfs,
                            baseline - cfg.speech_relative_db)
            ratios, weights, voice_powers = [], [], []
            for start in range(0, len(voice), cfg.window_ms):
                end = min(start + cfg.window_ms, len(voice))
                voice_level = _level(voice[start:end])
                if voice_level <= threshold:
                    continue
                seconds = (end - start) / 1000.0
                music_chunk = music[start:end] if music is not None else AudioSegment.empty(
                )
                music_level = _level(music_chunk)
                # Missing tail is silence, not a full window at the shorter RMS.
                if math.isfinite(music_level) and len(music_chunk) < end - start:
                    music_level += 10 * \
                        math.log10(len(music_chunk) / (end - start))
                ratio = voice_level - music_level
                ratios.append(ratio)
                weights.append(seconds)
                voice_powers.append(10 ** (voice_level / 10))
                report.windows.append({
                    "timestamp_start": offset + start / 1000.0,
                    "timestamp_end": offset + end / 1000.0,
                    "voice_level_dbfs": voice_level,
                    "music_level_dbfs": _finite(music_level),
                    "voice_music_ratio_db": _finite(ratio),
                    "speech_active": True,
                    "music_present": math.isfinite(music_level),
                })
            if not weights:
                self._issue(
                    report, "NO_VOICE", "Supply an audible voice recording; no speech activity detected.")
                return self._finish(report)
            report.speech_active_seconds = sum(weights)
            report.voice_level_dbfs = 10 * \
                math.log10(float(np.average(voice_powers, weights=weights)))
            if report.voice_level_dbfs < cfg.voice_optimal_min_dbfs:
                self._issue(report, "VOICE_TOO_QUIET", "Raise voice toward {:.1f} dBFS, checking peak headroom.".format(
                    cfg.voice_target_dbfs))
            elif report.voice_level_dbfs > cfg.voice_optimal_max_dbfs:
                self._issue(report, "VOICE_TOO_LOUD", "Reduce voice toward {:.1f} dBFS.".format(
                    cfg.voice_target_dbfs), failure=False)
            report.music_present = any(
                window["music_present"] for window in report.windows)
            report.median_voice_music_ratio_db = _finite(
                _weighted_quantile(ratios, weights, 0.5))
            report.p10_voice_music_ratio_db = _finite(
                _weighted_quantile(ratios, weights, 0.1))
            report.worst_voice_music_ratio_db = _finite(min(ratios))
            for name, limit in (("speech_below_warning_percentage", cfg.vmr_warning_db),
                                ("speech_below_failure_percentage", cfg.vmr_failure_db)):
                below = sum(weight for ratio, weight in zip(
                    ratios, weights) if ratio < limit)
                setattr(report, name, 100 * below /
                        report.speech_active_seconds)
            worst = report.worst_voice_music_ratio_db
            if worst is not None:
                window = report.windows[int(np.argmin(ratios))]
                center = (window["timestamp_start"] +
                          window["timestamp_end"]) / 2
                report.worst_section_start_seconds, report.worst_section_end_seconds = _bounds(
                    center, duration, max(10.0, min(20.0, cfg.preview_seconds)), offset)
                report.worst_section_voice_music_ratio_db = worst
                self._log("Worst VMR: {:.2f} dB at {:.2f}s".format(
                    worst, window["timestamp_start"]))
                if worst < cfg.vmr_warning_db:
                    report.suggested_music_reduction_db = max(
                        0.0, cfg.vmr_excellent_db - worst)
                    self._issue(report, "MUSIC_MASKING_VOICE",
                                "Reduce music by at least {:.1f} dB to reach {:.1f} dB separation; preview the worst section.".format(
                                    report.suggested_music_reduction_db, cfg.vmr_excellent_db),
                                failure=worst < cfg.vmr_failure_db)
                    report.recommendations.append(
                        "Consider smooth ducking: {:.1f} dB reduction, {} ms attack, {} ms release.".format(
                            cfg.ducking_reduction_db, cfg.ducking_attack_ms, cfg.ducking_release_ms))
                if worst <= cfg.vmr_critical_db:
                    self._issue(report, "MUSIC_DOMINATES_VOICE",
                                "Music equals or exceeds voice; reduce music before rendering.")
        except Exception as error:
            self._unavailable(report, "MIX_ANALYSIS_UNAVAILABLE", error)
        return self._finish(report)

    def _silence(self, audio, report):
        """10 ms RMS bins; exclude edge runs, but never exclude an all-silent file."""
        cfg = self.config
        start = None
        audible = False
        for position in range(0, len(audio), 10):
            silent = audio[position:position +
                           10].dBFS <= cfg.silence_threshold_dbfs
            if silent and start is None:
                start = position
            elif not silent:
                audible = True
                if start is not None and start > 0:
                    report.silence_sections.append({"start_seconds": start / 1000.0,
                                                   "end_seconds": position / 1000.0})
                start = None
        if not audible:
            report.longest_silence_seconds = len(audio) / 1000.0
            self._issue(
                report, "NO_VOICE", "The rendered file is silent; check the voice source and render settings.")
        else:
            report.longest_silence_seconds = max(
                (section["end_seconds"] - section["start_seconds"]
                 for section in report.silence_sections), default=0.0)
        longest = report.longest_silence_seconds
        if longest > cfg.silence_warning_seconds:
            self._issue(report, "SILENCE_TOO_LONG", "Review and trim the unexpected internal silence.",
                        failure=longest > cfg.silence_failure_seconds)
            if report.worst_section is None and report.silence_sections:
                section = max(report.silence_sections,
                              key=lambda item: item["end_seconds"] - item["start_seconds"])
                center = (section["start_seconds"] +
                          section["end_seconds"]) / 2
                report.worst_section_start_seconds, report.worst_section_end_seconds = _bounds(
                    center, len(audio) / 1000.0, max(10.0, cfg.preview_seconds))

    def analyze_file(self, path, mix_report=None) -> AudioQualityReport:
        """Measure the exact publishable file; optionally carry forward mix QC.

        Missing/invalid LUFS, true peak, PCM decoding or clipping analysis fails
        closed. No new mix claims are inferred from a single rendered waveform.
        Preview creation is explicit via create_preview(), not an automatic write.
        """
        cfg = self.config
        report = AudioQualityReport(preview_seconds=cfg.preview_seconds)
        report.analysis_complete = True
        try:
            report.file_path = os.fspath(path)
            if mix_report is not None:
                if not isinstance(mix_report, AudioQualityReport) or mix_report.analysis_kind != "mix":
                    raise ValueError(
                        "mix_report must be a mix AudioQualityReport")
                names = ("voice_level_dbfs", "speech_active_seconds", "music_present",
                         "median_voice_music_ratio_db", "p10_voice_music_ratio_db",
                         "worst_voice_music_ratio_db", "speech_below_warning_percentage",
                         "speech_below_failure_percentage", "suggested_music_reduction_db",
                         "worst_section_start_seconds", "worst_section_end_seconds",
                         "worst_section_voice_music_ratio_db", "windows", "warnings",
                         "failures", "recommendations", "analysis_errors")
                for name in names:
                    setattr(report, name, copy.deepcopy(
                        getattr(mix_report, name)))
                if not mix_report.analysis_complete:
                    self._unavailable(
                        report, "MIX_ANALYSIS_UNAVAILABLE", "Supplied mix analysis is incomplete")
            if not os.path.isfile(report.file_path):
                raise FileNotFoundError(
                    "Audio file does not exist: " + report.file_path)
            audio = _load_audio(report.file_path)
            report.duration_seconds = len(audio) / 1000.0
            if not len(audio):
                raise ValueError("Audio file is empty")
            if report.worst_section is not None:
                # A mismatched stem timeline must not silently certify the render.
                if report.worst_section_start_seconds >= report.duration_seconds:
                    raise ValueError(
                        "Mix section starts beyond the rendered file")
                report.worst_section_end_seconds = min(
                    report.duration_seconds, report.worst_section_end_seconds)
            self._silence(audio, report)
        except Exception as error:
            self._unavailable(report, "FILE_ANALYSIS_UNAVAILABLE", error)
            return self._finish(report)
        try:
            clipped, total = _measure_clipping(report.file_path)
            report.clipped_samples = clipped
            report.clipped_percentage = 100 * clipped / total
            if clipped:
                self._issue(report, "CLIPPING_DETECTED",
                            "Reduce gain before the final render; normalization cannot repair clipping.")
        except Exception as error:
            self._unavailable(report, "CLIPPING_ANALYSIS_UNAVAILABLE", error)
        try:
            self._log("Running loudness analysis on the final rendered file")
            stats = LUFSNormalizer()._get_loudness_stats(
                report.file_path, target_lufs=cfg.target_lufs,
                log_callback=self._log, true_peak=cfg.target_true_peak_dbtp, lra=cfg.lra)
            stats = stats or {}
            report.integrated_lufs = _finite(stats.get("input_i"))
            report.true_peak_dbtp = _finite(stats.get("input_tp"))
            if report.integrated_lufs is None:
                self._unavailable(report, "LOUDNESS_ANALYSIS_UNAVAILABLE",
                                  "Integrated LUFS is missing or nonfinite")
            else:
                difference = report.integrated_lufs - cfg.target_lufs
                self._log("Final loudness: {:.2f} LUFS".format(
                    report.integrated_lufs))
                if abs(difference) > cfg.loudness_warning_lu:
                    self._issue(report, "LOUDNESS_TOO_LOW" if difference < 0 else "LOUDNESS_TOO_HIGH",
                                "Run LUFS normalization to {:.1f} LUFS.".format(
                                    cfg.target_lufs),
                                failure=abs(difference) > cfg.loudness_failure_lu)
            if report.true_peak_dbtp is None:
                self._unavailable(
                    report, "TRUE_PEAK_ANALYSIS_UNAVAILABLE", "True peak is missing or nonfinite")
            else:
                self._log("True peak: {:.2f} dBTP".format(
                    report.true_peak_dbtp))
                if report.true_peak_dbtp > cfg.target_true_peak_dbtp:
                    self._issue(report, "TRUE_PEAK_TOO_HIGH",
                                "Apply a true-peak limiter or reduce output gain to {:.1f} dBTP.".format(
                                    cfg.target_true_peak_dbtp),
                                failure=report.true_peak_dbtp > cfg.true_peak_failure_dbtp)
        except Exception as error:
            self._unavailable(report, "LOUDNESS_ANALYSIS_UNAVAILABLE", error)
        return self._finish(report)


def create_preview(path, report: AudioQualityReport) -> Optional[str]:
    """Extract at most 15 seconds from the final render, never a solo stem.

    Uses the worst section (or the beginning if absent), bounded to the file.
    Sets report.preview_file and returns its unique temporary WAV path. The caller
    owns cleanup after playback. Failure returns None and adds a warning code.
    """
    output = None
    report.preview_file = None
    try:
        audio = _load_audio(path)
        duration = len(audio) / 1000.0
        requested = float(report.preview_seconds)
        if not math.isfinite(requested) or requested <= 0 or duration <= 0:
            raise ValueError(
                "Cannot preview empty audio or an invalid duration")
        length = min(15.0, requested, duration)
        start = report.worst_section_start_seconds
        end = report.worst_section_end_seconds
        center = (start + end) / \
            2 if start is not None and end is not None else length / 2
        # Center on the actual lowest window, not an edge-clamped 20-second
        # section whose middle 15 seconds could omit the problem entirely.
        candidates = [window for window in report.windows
                      if _finite(window.get("voice_music_ratio_db")) is not None]
        if candidates:
            worst = min(
                candidates, key=lambda window: window["voice_music_ratio_db"])
            center = (worst["timestamp_start"] + worst["timestamp_end"]) / 2
        if not math.isfinite(center):
            raise ValueError("Invalid preview timestamp")
        start, end = _bounds(center, duration, length)
        descriptor, output = tempfile.mkstemp(
            prefix="audio_quality_preview_", suffix=".wav")
        os.close(descriptor)
        clip = audio[int(round(start * 1000)):int(round(end * 1000))]
        if not len(clip):
            raise ValueError(
                "Preview interval is shorter than one millisecond")
        with clip.export(output, format="wav"):
            pass
        report.preview_file = output
        return output
    except Exception as error:
        if output is not None and os.path.exists(output):
            os.unlink(output)
        if "PREVIEW_UNAVAILABLE" not in report.warnings:
            report.warnings.append("PREVIEW_UNAVAILABLE")
        report.analysis_errors.append("Preview unavailable: {}".format(error))
        return None
