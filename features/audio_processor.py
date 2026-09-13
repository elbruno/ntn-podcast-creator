"""Audio processing for podcast creation."""

import os
import random
import math
import tempfile
import json
import atexit
from dataclasses import asdict
from typing import List, Optional, Callable, Tuple, Dict, Any, Union
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from .audio_denoiser_processor import denoise_audio_file
from .noise_reducer import reduce_noise
from .lufs_normalizer import normalize_audio_lufs
from .voice_enhancer import enhance_voice
from .audio_quality import (
    AudioQualityAnalyzer, AudioQualityConfig, AudioQualityReport, create_preview,
)


_quality_previews = {}


def _quality_file_identity(path):
    info = os.stat(path)
    return {"size": info.st_size, "mtime_ns": info.st_mtime_ns,
            "ctime_ns": info.st_ctime_ns, "device": info.st_dev, "inode": info.st_ino}


def _quality_preview_identity(path):
    """Recognize only regular, non-symlink QC previews in the temp directory."""
    if (isinstance(path, str)
            and os.path.dirname(os.path.abspath(path)) == os.path.realpath(tempfile.gettempdir())
            and os.path.realpath(path) == os.path.abspath(path)
            and os.path.basename(path).startswith("audio_quality_preview_")
            and path.endswith(".wav") and not os.path.islink(path)
            and os.path.isfile(path)):
        return _quality_file_identity(path)
    return None


def _register_quality_preview(path, output_path):
    identity = _quality_preview_identity(path)
    if identity is not None:
        _quality_previews[path] = (identity, os.path.realpath(output_path))
    return identity


def _cleanup_quality_preview(path, identity=None):
    """Delete only an unchanged owned preview; never trust a bare input path."""
    if not isinstance(path, str):
        return
    if identity is None:
        identity = _quality_previews.get(path, (None, None))[0]
    try:
        if identity is not None and _quality_preview_identity(path) == identity:
            os.unlink(path)
        _quality_previews.pop(path, None)
    except OSError:
        pass  # Retain the registry entry for another attempt at normal exit.


def _cleanup_quality_previews():
    for path, (identity, _) in list(_quality_previews.items()):
        _cleanup_quality_preview(path, identity)


atexit.register(_cleanup_quality_previews)


def _read_quality_sidecar(output_path):
    output_path = os.path.realpath(output_path)
    sidecar = output_path + ".quality.json"
    if os.path.islink(sidecar) or os.path.getsize(sidecar) > 32 * 1024 * 1024:
        raise ValueError("Invalid quality sidecar")
    with open(sidecar, encoding="utf-8") as source:
        data = json.load(source)
    if (not isinstance(data, dict) or data.get("schema") != "ntn-quality-v1"
            or data.get("output_path") != output_path
            or data.get("identity") != _quality_file_identity(output_path)):
        raise ValueError("Stale quality report; render again to refresh it")
    return data


def _write_quality_sidecar(path, data):
    """Publish complete JSON atomically, replacing rather than following symlinks."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json",
                                         dir=os.path.dirname(
                                             os.path.abspath(path)),
                                         delete=False) as output:
            temporary = output.name
            json.dump(data, output, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _invalidate_quality_sidecar(output_path, log):
    """A new render retires only this output's prior preview and certification."""
    output_path = os.path.realpath(output_path)
    for path, (identity, owner) in list(_quality_previews.items()):
        if owner == output_path:
            _cleanup_quality_preview(path, identity)
    try:
        previous = _read_quality_sidecar(output_path)
        _cleanup_quality_preview(previous.get("preview_file"),
                                 previous.get("preview_identity"))
    except (OSError, ValueError, TypeError):
        pass  # Missing/legacy/malformed receipts cannot authorize deletion.
    try:
        os.unlink(output_path + ".quality.json")
    except FileNotFoundError:
        pass
    except OSError as error:
        log(f"Warning: Could not invalidate old quality report: {error}")


class AudioProcessor:
    """Handles audio mixing and processing for podcast creation."""

    def __init__(self):
        """Initialize audio processor."""
        # Legacy UI convenience only; concurrent callers should use the callback.
        self.last_quality_report = None

    @staticmethod
    def _quality_config(config=None) -> AudioQualityConfig:
        return (config if isinstance(config, AudioQualityConfig)
                else AudioQualityConfig.from_mapping(config))

    def load_audio(self, file_path: str) -> AudioSegment:
        """Load audio file.

        Args:
            file_path: Path to audio file

        Returns:
            AudioSegment object

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If file cannot be loaded
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            # Try to load the audio file
            audio = AudioSegment.from_file(file_path)
            return audio
        except Exception as e:
            raise Exception(f"Error loading audio file {file_path}: {e}")

    def concatenate_audio_files(
        self,
        audio_files: List[str],
        output_path: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Concatenate multiple audio files into a single file.

        Args:
            audio_files: List of paths to audio files to concatenate
            output_path: Optional path for output file. If None, creates temp file.
            log_callback: Optional callback function for logging

        Returns:
            Path to concatenated audio file

        Raises:
            ValueError: If audio_files is empty or contains invalid files
            Exception: If concatenation fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not audio_files:
            raise ValueError("No audio files provided for concatenation")

        # If only one file, return it directly
        if len(audio_files) == 1:
            log(f"Single file provided: {os.path.basename(audio_files[0])}")
            return audio_files[0]

        log(f"Concatenating {len(audio_files)} audio files...")

        # Load all audio files
        audio_segments = []
        for i, file_path in enumerate(audio_files, 1):
            if not os.path.exists(file_path):
                raise ValueError(f"Audio file not found: {file_path}")

            try:
                log(f"Loading file {i}/{len(audio_files)}: {os.path.basename(file_path)}")
                audio = self.load_audio(file_path)
                audio_segments.append(audio)
                duration_seconds = len(audio) / 1000.0
                log(f"  Duration: {duration_seconds:.2f}s")
            except Exception as e:
                raise Exception(f"Error loading audio file {file_path}: {e}")

        # Concatenate all segments
        log("Concatenating audio segments...")
        concatenated = audio_segments[0]
        for i, segment in enumerate(audio_segments[1:], 2):
            concatenated = concatenated + segment
            log(f"  Merged {i}/{len(audio_segments)} segments")

        # Calculate total duration
        total_duration_seconds = len(concatenated) / 1000.0
        log(f"Total concatenated duration: {total_duration_seconds:.2f}s")

        # Export to file
        if output_path is None:
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(
                temp_dir, f"concatenated_{os.getpid()}.mp3")

        log(f"Exporting concatenated audio to: {os.path.basename(output_path)}")
        concatenated.export(output_path, format="mp3")
        log("Concatenation complete!")

        return output_path

    def trim_silence(self, audio: AudioSegment, silence_threshold: int = -35) -> AudioSegment:
        """Trim silence from the beginning and end of audio.

        Args:
            audio: AudioSegment to process
            silence_threshold: Threshold in dB for what is considered silence

        Returns:
            AudioSegment with silence trimmed
        """
        # Detect leading silence
        start_trim = detect_leading_silence(
            audio, silence_threshold=silence_threshold)

        # Detect trailing silence by reversing the audio
        end_trim = detect_leading_silence(
            audio.reverse(), silence_threshold=silence_threshold)

        # Calculate duration
        duration = len(audio)

        # Trim the audio
        trimmed = audio[start_trim:duration-end_trim]

        return trimmed

    def reduce_volume(self, audio: AudioSegment, volume_percent: int) -> AudioSegment:
        """Reduce audio volume.

        Args:
            audio: AudioSegment to process
            volume_percent: Target volume as percentage (0-100)

        Returns:
            AudioSegment with reduced volume
        """
        if volume_percent >= 100:
            return audio

        if volume_percent <= 0:
            # Silence
            return audio - 60

        # Convert percentage to dB using logarithmic scaling
        # volume_percent of 100 = 0 dB, 50 = -6 dB, 10 = -20 dB
        db_change = 20 * math.log10(volume_percent / 100)
        return audio + db_change

    def fade_out(self, audio: AudioSegment, duration_ms: int) -> AudioSegment:
        """Apply fade-out effect to audio.

        Args:
            audio: AudioSegment to process
            duration_ms: Duration of fade-out in milliseconds

        Returns:
            AudioSegment with fade-out applied
        """
        if duration_ms <= 0 or len(audio) <= 0:
            return audio

        fade_duration = min(duration_ms, len(audio))
        return audio.fade_out(fade_duration)

    def fade_in(self, audio: AudioSegment, duration_ms: int) -> AudioSegment:
        """Apply fade-in effect to audio.

        Args:
            audio: AudioSegment to process
            duration_ms: Duration of fade-in in milliseconds

        Returns:
            AudioSegment with fade-in applied
        """
        if duration_ms <= 0 or len(audio) <= 0:
            return audio

        fade_duration = min(duration_ms, len(audio))
        return audio.fade_in(fade_duration)

    def create_looped_background(
        self,
        background_files: List[str],
        target_duration_ms: int,
        volume_percent: int = 10,
        track_volumes: Optional[dict] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        rng: Optional[random.Random] = None,
        selected_tracks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[AudioSegment]:
        """Create looped background music from randomly selected tracks.

        Randomly selects tracks and concatenates them until the target duration is reached.

        Args:
            background_files: List of background music file paths
            target_duration_ms: Target duration in milliseconds
            volume_percent: Default volume percentage for background (0-100)
            track_volumes: Optional dict mapping track paths to individual volumes
            log_callback: Optional callback function for logging
            rng: Request-local random generator (never changes global random state)
            selected_tracks: Optional request-local list populated in playback order

        Returns:
            AudioSegment with concatenated background music or None if no files
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not background_files or target_duration_ms <= 0:
            return None

        rng = rng if rng is not None else random.Random(0)

        # Filter out files that don't exist
        valid_files = [f for f in background_files if os.path.exists(f)]
        if not valid_files:
            log("Warning: No valid background music files found")
            return None

        log(
            f"Building background music from {len(valid_files)} available track(s)")

        # Build background by randomly selecting and concatenating tracks
        background = AudioSegment.empty()
        tracks_used = []

        while valid_files and len(background) < target_duration_ms:
            # Randomly select a track
            selected_file = rng.choice(valid_files)
            track_name = os.path.basename(selected_file)

            try:
                track = self.load_audio(selected_file)
                if len(track) <= 0:
                    raise ValueError("Track has no audio duration")

                # Use individual track volume if available, otherwise use default
                if track_volumes and selected_file in track_volumes:
                    track_volume = track_volumes[selected_file]
                else:
                    track_volume = volume_percent

                # Reduce volume of this track
                track = self.reduce_volume(track, track_volume)

                # Append to background
                if selected_tracks is not None:
                    selected_tracks.append({
                        "path": os.fspath(selected_file),
                        "volume_percent": track_volume,
                        "start_ms": len(background),
                        "end_ms": min(len(background) + len(track), target_duration_ms),
                    })
                background += track
                tracks_used.append(f"{track_name} ({track_volume}%)")

            except Exception as e:
                log(f"Error loading background track {track_name}: {e}")
                # Remove every duplicate too: an invalid pool must terminate.
                valid_files = [
                    path for path in valid_files if path != selected_file]

        if not len(background):
            log("Warning: No playable background music tracks; continuing without music")
            return None

        # Trim to exact duration
        background = background[:target_duration_ms]

        # Show which tracks were used
        if tracks_used:
            log(f"Background music created using: {', '.join(tracks_used)}")

        return background

    def mix_audio(
        self,
        main_audio: AudioSegment,
        background: Optional[AudioSegment] = None
    ) -> AudioSegment:
        """Mix main audio with background music.

        Args:
            main_audio: Main audio track
            background: Background music (optional)

        Returns:
            Mixed audio
        """
        if background is None:
            return main_audio

        # Overlay background music on main audio
        return main_audio.overlay(background)

    def apply_ducking(
        self,
        voice: AudioSegment,
        background: AudioSegment,
        duck_db: float = 12.0,
        chunk_ms: int = 250,
        silence_threshold_db: float = -42.0,
        log_callback: Optional[Callable[[str], None]] = None,
        attack_ms: int = 100,
        release_ms: int = 450
    ) -> AudioSegment:
        """Dynamically attenuate background music when speech is detected.

        Args:
            voice: Voice AudioSegment
            background: Background music AudioSegment
            duck_db: Amount in dB to attenuate background music during speech
            chunk_ms: Requested activity window, capped at 20ms for speech
            silence_threshold_db: Absolute dBFS threshold for silence
            log_callback: Optional logging callback
            attack_ms: Attack time constant in milliseconds (default: 100ms)
            release_ms: Release time constant in milliseconds (default: 450ms)

        Returns:
            AudioSegment with ducked background music
        """
        if len(background) == 0 or len(voice) == 0 or duck_db <= 0:
            return background

        voice_cut = voice[:len(background)]
        voice_ref = voice_cut.dBFS if voice_cut.dBFS != - \
            float('inf') else -30.0
        active_threshold = max(silence_threshold_db, voice_ref - 14.0)
        window_ms = max(1, min(20, int(chunk_ms)))
        frames_per_window = max(
            1, round(background.frame_rate * window_ms / 1000))
        dtype = np.dtype("i{}".format(background.sample_width))
        samples = np.frombuffer(background.raw_data,
                                dtype=dtype).reshape(-1, background.channels)
        output = np.empty_like(samples)
        limits = np.iinfo(dtype)
        gain = 1.0
        speech_gain = 10 ** (-duck_db / 20)

        # The envelope's state is carried across windows, channels, and the
        # voice's end. Float work is bounded to a small window, not an episode.
        for start in range(0, len(samples), frames_per_window):
            end = min(start + frames_per_window, len(samples))
            start_ms = round(start * 1000 / background.frame_rate)
            end_ms = round(end * 1000 / background.frame_rate)
            active = voice_cut[start_ms:end_ms].dBFS > active_threshold
            target = speech_gain if active else 1.0
            time_ms = attack_ms if target < gain else release_ms
            if time_ms <= 0:
                envelope = np.full(end - start, target)
            else:
                decay = np.exp(-np.arange(1, end - start + 1) /
                               (background.frame_rate * time_ms / 1000))
                envelope = target + (gain - target) * decay
            gain = float(envelope[-1])
            block = np.rint(samples[start:end].astype(
                np.float64) * envelope[:, None])
            output[start:end] = np.clip(
                block, limits.min, limits.max).astype(dtype)

        return background._spawn(output.tobytes())

    def auto_balance_audio(
        self,
        voice: AudioSegment,
        background: Optional[AudioSegment] = None,
        target_voice_dbfs: float = -18.0,
        min_separation_db: float = 18.0,
        apply_ducking: bool = True,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[AudioSegment, Optional[AudioSegment], Dict[str, Any]]:
        """Automatically pre-normalize voice level and balance background music.

        Ensures that low voice recordings are pre-gained to standard podcast dialogue levels
        and that background music never masks or overpowers the voice.

        Args:
            voice: Voice AudioSegment
            background: Optional background music AudioSegment
            target_voice_dbfs: Target dialogue level in dBFS (-18.0 dBFS recommended)
            min_separation_db: Minimum dB separation between voice and music (default: 18.0 dB)
            apply_ducking: Whether to apply dynamic auto-ducking during speech
            log_callback: Optional logging callback

        Returns:
            Tuple of (balanced_voice, balanced_background, balance_info_dict)
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        info: Dict[str, Any] = {
            "voice_initial_dbfs": round(voice.dBFS, 1) if voice.dBFS != -float('inf') else -99.0,
            "voice_gain_applied_db": 0.0,
            "bg_attenuation_applied_db": 0.0,
            "ducking_applied": False
        }

        # Step 1: Pre-gain voice if it's too quiet
        if voice.dBFS != -float('inf') and voice.dBFS < (target_voice_dbfs - 1.0):
            gain_needed = target_voice_dbfs - voice.dBFS
            # Leave 1.0 dB headroom to prevent peak clipping
            headroom = -1.0 - voice.max_dBFS if voice.max_dBFS != - \
                float('inf') else gain_needed
            actual_gain = min(gain_needed, max(0.0, headroom))

            if actual_gain >= 0.5:
                voice = voice.apply_gain(actual_gain)
                info["voice_gain_applied_db"] = round(actual_gain, 1)
                log(
                    f"Auto-balance: Voice recording was low ({info['voice_initial_dbfs']} dBFS). Applied +{actual_gain:.1f} dB pre-gain (New RMS: {voice.dBFS:.1f} dBFS, Peak: {voice.max_dBFS:.1f} dBFS)")

        info["voice_final_dbfs"] = round(
            voice.dBFS, 1) if voice.dBFS != -float('inf') else -99.0

        # Step 2: Ensure background music sits at least min_separation_db below voice
        if background is not None and len(background) > 0 and background.dBFS != -float('inf'):
            info["bg_initial_dbfs"] = round(background.dBFS, 1)
            vmr = voice.dBFS - background.dBFS
            info["initial_vmr_db"] = round(vmr, 1)

            if vmr < min_separation_db:
                needed_attenuation = min_separation_db - vmr
                background = background - needed_attenuation
                info["bg_attenuation_applied_db"] = round(
                    needed_attenuation, 1)
                log(
                    f"Auto-balance: Background music was too prominent relative to voice (separation was {vmr:.1f} dB). Reduced background by -{needed_attenuation:.1f} dB to maintain {min_separation_db:.1f} dB separation.")

            if apply_ducking:
                background = self.apply_ducking(
                    voice, background, log_callback=log_callback)
                info["ducking_applied"] = True
                log("Auto-balance: Applied smooth auto-ducking to background music (-12.0 dB during speech).")

            info["bg_final_dbfs"] = round(
                background.dBFS, 1) if background.dBFS != -float('inf') else -99.0
            info["final_vmr_db"] = round(voice.dBFS - background.dBFS, 1)

        return voice, background, info

    def analyze_levels(
        self,
        voice_audio: Any,
        background_files: Optional[List[str]] = None,
        background_volume: int = 10,
        track_volumes: Optional[dict] = None,
        quality_config: Optional[Union[dict, AudioQualityConfig]] = None
    ) -> Dict[str, Any]:
        """Analyze voice and background music levels to detect low recording volume or masking issues.

        Args:
            voice_audio: Path to voice file, list of file paths, or AudioSegment object
            background_files: Optional list of background music file paths
            background_volume: Background volume percentage (0-100)
            track_volumes: Optional dict of track path -> volume percentage
            quality_config: Shared voice and VMR thresholds (mapping or config)

        Returns:
            Dictionary with metrics, status, warnings, recommendations, and diagnosis
        """
        try:
            cfg = self._quality_config(quality_config)
            if isinstance(voice_audio, list):
                if not voice_audio:
                    return {"overall_status": "no_voice", "title": "Sin audio de voz", "warnings": ["No se ha subido ningún archivo de voz."], "recommendations": []}
                voice = self.load_audio(voice_audio[0])
                for v_path in voice_audio[1:]:
                    if os.path.exists(v_path):
                        voice += self.load_audio(v_path)
            elif isinstance(voice_audio, str):
                if not os.path.exists(voice_audio):
                    return {"overall_status": "no_voice", "title": "Archivo no encontrado", "warnings": [f"El archivo {os.path.basename(voice_audio)} no existe."], "recommendations": []}
                voice = self.load_audio(voice_audio)
            elif hasattr(voice_audio, "dBFS"):
                voice = voice_audio
            elif isinstance(AudioSegment, type) and isinstance(voice_audio, AudioSegment):
                voice = voice_audio
            else:
                return {"overall_status": "no_voice", "title": "Sin audio", "warnings": ["Formato de audio no reconocido."], "recommendations": []}
        except Exception as e:
            return {"overall_status": "error", "title": "Error al analizar audio", "warnings": [str(e)], "recommendations": []}

        voice_dbfs = round(voice.dBFS, 1) if voice.dBFS != - \
            float('inf') else -99.0
        voice_peak = round(
            voice.max_dBFS, 1) if voice.max_dBFS != -float('inf') else -99.0

        # Keep legacy severity bands inside the configured low-voice range.
        very_low_dbfs = min(-28.0, cfg.voice_optimal_min_dbfs)
        # Voice loudness status
        if voice_dbfs <= -50.0:
            voice_status = "silent"
            voice_status_label = "Silencio / Muy bajo (-50 dBFS o menos)"
        elif voice_dbfs < very_low_dbfs:
            voice_status = "very_low"
            voice_status_label = f"Voz muy baja (< {very_low_dbfs:g} dBFS)"
        elif voice_dbfs < cfg.voice_optimal_min_dbfs:
            voice_status = "low"
            voice_status_label = f"Voz baja (< {cfg.voice_optimal_min_dbfs:g} dBFS)"
        elif voice_dbfs > cfg.voice_optimal_max_dbfs:
            voice_status = "loud"
            voice_status_label = f"Voz muy alta / posible pico (> {cfg.voice_optimal_max_dbfs:g} dBFS)"
        else:
            voice_status = "optimal"
            voice_status_label = f"Nivel de voz óptimo ({cfg.voice_optimal_min_dbfs:g} a {cfg.voice_optimal_max_dbfs:g} dBFS)"

        # Background music analysis
        bg_dbfs = None
        bg_peak = None
        vmr = None
        balance_status = "no_music"
        balance_status_label = "Sin música de fondo configurada"

        valid_bg = [f for f in (background_files or []) if os.path.exists(f)]
        if valid_bg and background_volume > 0:
            try:
                bg_sample = None
                sample_duration = min(20000, max(5000, len(voice)))
                for bg_f in valid_bg[:3]:
                    t_track = self.load_audio(bg_f)
                    vol = track_volumes.get(
                        bg_f, background_volume) if track_volumes else background_volume
                    t_track = self.reduce_volume(t_track, vol)
                    t_slice = t_track[:sample_duration]
                    if bg_sample is None:
                        bg_sample = t_slice
                    else:
                        bg_sample += t_slice

                if bg_sample is not None and len(bg_sample) > 0:
                    bg_dbfs = round(
                        bg_sample.dBFS, 1) if bg_sample.dBFS != -float('inf') else -99.0
                    bg_peak = round(
                        bg_sample.max_dBFS, 1) if bg_sample.max_dBFS != -float('inf') else -99.0
                    vmr = round(voice_dbfs - bg_dbfs, 1)

                    if vmr >= cfg.vmr_excellent_db:
                        balance_status = "optimal"
                        balance_status_label = f"Excelente (+{vmr} dB sobre la música)"
                    elif vmr >= cfg.vmr_warning_db:
                        balance_status = "optimal"
                        balance_status_label = f"Bueno (+{vmr} dB sobre la música)"
                    elif vmr >= cfg.vmr_failure_db and vmr > cfg.vmr_critical_db:
                        balance_status = "warning"
                        balance_status_label = f"Precaución (+{vmr} dB sobre la música)"
                    else:
                        balance_status = "danger"
                        severity = "Crítico" if vmr <= cfg.vmr_critical_db else "Insuficiente"
                        balance_status_label = f"{severity} ({vmr} dB - La música tapará la voz)"
            except Exception:
                pass

        warnings = []
        recommendations = []

        if voice_status in ["silent", "very_low", "low"]:
            warnings.append(
                f"El volumen de la grabación de voz ({voice_dbfs} dBFS) es bajo para podcasting (recomendado: ~ {cfg.voice_target_dbfs:g} dBFS).")
            if voice_status == "silent":
                recommendations.append(
                    "Comprueba el micrófono y proporciona una grabación de voz audible.")
            else:
                recommendations.append(
                    "Activa auto-balance para aumentar la voz, respetando el margen de los picos.")
        elif voice_status == "loud":
            warnings.append(
                f"La voz supera el máximo recomendado de {cfg.voice_optimal_max_dbfs:g} dBFS.")
            recommendations.append(
                f"Reduce la ganancia hacia {cfg.voice_target_dbfs:g} dBFS y comprueba los picos.")

        if balance_status == "danger":
            warnings.append(
                f"La separación entre voz y música es de sólo {vmr} dB (fallo por debajo de {cfg.vmr_failure_db:g} dB; recomendado +{cfg.vmr_excellent_db:g} dB). La música de fondo tapará tu voz.")
            recommendations.append(
                "El auto-balance atenuará la música automáticamente y aplicará auto-ducking durante tus intervenciones.")
        elif balance_status == "warning":
            warnings.append(
                f"La separación voz/música es de {vmr} dB (aviso por debajo de {cfg.vmr_warning_db:g} dB). La música podría competir con tu voz en fragmentos suaves.")
            recommendations.append(
                "Se recomienda activar Auto-Ducking o reducir el volumen de la música.")

        if voice_status in ["silent", "very_low"] or balance_status == "danger":
            overall_status = "danger"
            badge_icon = "🔴"
            badge_color = "#ef4444"
            title = "Alerta: Riesgo de audio bajo o enmascarado por música"
        elif voice_status in ["low", "loud"] or balance_status == "warning":
            overall_status = "warning"
            badge_icon = "🟡"
            badge_color = "#f59e0b"
            title = "Aviso: Nivel de audio o balance mejorable"
        else:
            overall_status = "optimal"
            badge_icon = "🟢"
            badge_color = "#10b981"
            title = "Niveles y Balance de Audio Óptimos"

        suggested_voice_gain = round(
            max(0.0, cfg.voice_target_dbfs - voice_dbfs), 1) if voice_dbfs > -60 else 0.0

        return {
            "overall_status": overall_status,
            "badge_icon": badge_icon,
            "badge_color": badge_color,
            "title": title,
            "voice_dbfs": voice_dbfs,
            "voice_peak": voice_peak,
            "voice_status": voice_status,
            "voice_status_label": voice_status_label,
            "bg_dbfs": bg_dbfs,
            "bg_peak": bg_peak,
            "voice_to_music_ratio_db": vmr,
            "balance_status": balance_status,
            "balance_status_label": balance_status_label,
            "warnings": warnings,
            "recommendations": recommendations,
            "suggested_voice_gain_db": suggested_voice_gain
        }

    def create_podcast(
        self,
        voice_file: str,
        intro_file: Optional[str] = None,
        outro_file: Optional[str] = None,
        background_files: Optional[List[str]] = None,
        background_segments: Optional[List[Tuple[int, int]]] = None,
        background_volume: int = 10,
        track_volumes: Optional[dict] = None,
        output_file: str = "output.mp3",
        trim_silence: bool = False,
        denoise_audio: bool = True,
        denoise_method: str = "audio_denoiser",
        enhance_voice_enabled: bool = False,
        voice_enhancement_preset: str = "podcast",
        normalize_lufs: bool = False,
        target_lufs: float = -16.0,
        intro_voice_overlap: bool = True,
        voice_outro_overlap: bool = False,
        auto_balance_levels: bool = True,
        min_voice_music_separation_db: float = 18.0,
        auto_ducking: bool = True,
        generate_transcript: bool = False,
        whisper_model: str = "base",
        defer_transcription: bool = False,
        log_callback: Optional[Callable[[str], None]] = None,
        quality_gate_enabled: bool = False,
        quality_config: Optional[Union[dict, AudioQualityConfig]] = None,
        music_seed: int = 0,
        quality_report_callback: Optional[Callable[[
            AudioQualityReport], None]] = None
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Create complete podcast with intro, outro, and background music.

        Args:
            voice_file: Path to main voice recording
            intro_file: Path to intro audio (optional)
            outro_file: Path to outro audio (optional)
            background_files: List of background music files (optional)
            background_segments: Optional list of (start_ms, end_ms) ranges where
                background music should be applied on the voice track. If None,
                background applies to the full voice section.
            background_volume: Default volume percentage for background (0-100)
            track_volumes: Optional dict mapping track paths to individual volumes
            output_file: Path for output file
            trim_silence: Whether to trim silence from voice recording
            denoise_audio: Whether to denoise audio (optional)
            denoise_method: Denoising method ("audio_denoiser", "spectral", "rnnoise")
            enhance_voice_enabled: Whether to apply voice enhancement (optional)
            voice_enhancement_preset: Enhancement preset ("podcast", "light", "aggressive")
            normalize_lufs: Whether to normalize to target LUFS level
            target_lufs: Target LUFS level (-14 or -16 recommended)
            intro_voice_overlap: Whether to enable 1-second overlap between intro and voice
            voice_outro_overlap: Whether to enable 1-second overlap between voice and outro
            generate_transcript: Whether to generate transcript using Whisper (optional)
            whisper_model: Whisper model size ("tiny", "base", "small", "medium", "large")
            defer_transcription: Whether to skip transcription during creation
            log_callback: Optional callback function for logging
            quality_gate_enabled: Opt-in QC of the exact final exported MP3
            quality_config: Shared QC/ducking thresholds; explicit targets override target_lufs
            music_seed: Local seed for reproducible music selection
            quality_report_callback: Request-local report capture; previews retire on rerender/exit

        Returns:
            Tuple of (path to output file, path to denoised audio or None, path to transcript or None)

        Raises:
            Exception: If processing fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        self.last_quality_report = None
        _invalidate_quality_sidecar(output_file, log)
        config_error = None
        try:
            settings = quality_config
            if not isinstance(settings, AudioQualityConfig):
                settings = dict(settings or {})
                if settings.get("target_lufs") is None:
                    settings["target_lufs"] = target_lufs
            cfg = self._quality_config(settings)
        except Exception as error:
            config_error = str(error)
            cfg = AudioQualityConfig()
            log(
                f"Warning: Invalid audio quality settings: {error}. Using defaults; continuing export.")
        rng = random.Random(music_seed)
        selected_tracks = []

        log("Starting podcast creation...")

        # Store processed file paths
        denoised_file_path = None

        # Noise reduction (multiple methods available)
        voice_file_to_process = voice_file
        if denoise_audio:
            if denoise_method == "audio_denoiser":
                log("Denoising audio using audio-denoiser (AI-based)...")
                denoised_file = denoise_audio_file(
                    voice_file,
                    enabled=True,
                    auto_scale=True,
                    log_callback=log
                )
            elif denoise_method == "spectral":
                log("Denoising audio using spectral gating (noisereduce)...")
                denoised_file = reduce_noise(
                    voice_file,
                    method="spectral",
                    log_callback=log
                )
            elif denoise_method == "rnnoise":
                log("Denoising audio using FFmpeg RNNoise...")
                denoised_file = reduce_noise(
                    voice_file,
                    method="rnnoise",
                    log_callback=log
                )
            else:
                log(f"Unknown denoise method '{denoise_method}', using audio_denoiser")
                denoised_file = denoise_audio_file(
                    voice_file,
                    enabled=True,
                    auto_scale=True,
                    log_callback=log
                )

            if denoised_file and denoised_file != voice_file:
                voice_file_to_process = denoised_file
                denoised_file_path = denoised_file
                log(f"Using denoised audio: {os.path.basename(denoised_file)}")
            else:
                log("Using original audio (denoising not available or failed)")

        # Voice enhancement (applied after denoising)
        if enhance_voice_enabled:
            log(
                f"Applying voice enhancement (preset: {voice_enhancement_preset})...")
            enhanced_file = enhance_voice(
                voice_file_to_process,
                output_file=None,
                preset=voice_enhancement_preset,
                log_callback=log
            )

            if enhanced_file and enhanced_file != voice_file_to_process:
                voice_file_to_process = enhanced_file
                log(f"Using enhanced audio: {os.path.basename(enhanced_file)}")
            else:
                log("Voice enhancement failed or not available, continuing with current audio")

        # Load main voice recording
        log(f"Loading main voice: {os.path.basename(voice_file_to_process)}")
        voice = self.load_audio(voice_file_to_process)

        # Trim silence if requested
        if trim_silence:
            log("Trimming silence from voice recording...")
            original_duration = len(voice)
            voice = self.trim_silence(voice)
            trimmed_duration = len(voice)
            saved_ms = original_duration - trimmed_duration
            log(f"Trimmed {saved_ms/1000:.2f} seconds of silence")

        # Auto-Balance voice level before mixing
        if auto_balance_levels:
            log("Checking voice recording level for optimal dialogue loudness...")
            voice, _, _ = self.auto_balance_audio(
                voice=voice,
                background=None,
                target_voice_dbfs=cfg.voice_target_dbfs,
                min_separation_db=min_voice_music_separation_db,
                apply_ducking=False,
                log_callback=log
            )

        # Build the podcast sequence with overlaps
        # Overlap duration: 1 second (1000ms)
        overlap_ms = 1000

        intro_duration = 0
        outro_duration = 0

        # Add intro if provided (no background music)
        if intro_file and os.path.exists(intro_file):
            log(f"Adding intro: {os.path.basename(intro_file)}")
            intro = self.load_audio(intro_file)
            intro_duration = len(intro)
        else:
            intro = None

        # Add main voice with background music
        log("Adding main voice recording")
        # Retain the actual post-balance, post-duck music, including selective
        # gaps. Never infer a stem by subtracting from a clipped/encoded mix.
        music_stem = AudioSegment.silent(
            duration=len(voice), frame_rate=voice.frame_rate)
        background_applied = False

        def prepare_background(segment_voice, duration, start_ms):
            tracks = []
            background = self.create_looped_background(
                background_files, duration, background_volume,
                track_volumes=track_volumes, log_callback=log,
                rng=rng, selected_tracks=tracks)
            for track in tracks:
                track["start_ms"] += start_ms
                track["end_ms"] += start_ms
            selected_tracks.extend(tracks)
            if background is None:
                return None
            if auto_balance_levels and math.isfinite(segment_voice.dBFS):
                # Voice was already gained globally. Using its actual level
                # prevents an ignored second pre-gain on quieter sub-segments.
                _, background, _ = self.auto_balance_audio(
                    segment_voice, background,
                    target_voice_dbfs=segment_voice.dBFS,
                    min_separation_db=min_voice_music_separation_db,
                    apply_ducking=False, log_callback=log)
            if auto_ducking:
                background = self.apply_ducking(
                    segment_voice, background,
                    duck_db=cfg.ducking_reduction_db,
                    silence_threshold_db=cfg.speech_threshold_dbfs,
                    log_callback=log,
                    attack_ms=cfg.ducking_attack_ms,
                    release_ms=cfg.ducking_release_ms)
                log(f"Applied smooth music ducking: {cfg.ducking_reduction_db:g} dB, "
                    f"{cfg.ducking_attack_ms}ms attack / {cfg.ducking_release_ms}ms release")
            return background

        # Add background music only to voice section
        if background_files:
            if background_segments is not None:
                # Apply background only on selected voice sub-segments
                valid_segments = []
                voice_len = len(voice)
                for start_ms, end_ms in background_segments:
                    if start_ms is None or end_ms is None:
                        continue
                    start = max(0, int(start_ms))
                    end = min(voice_len, int(end_ms))
                    if end > start:
                        valid_segments.append((start, end))

                if valid_segments:
                    log(
                        f"Creating selective background music for {len(valid_segments)} voice segment(s) (volume: {background_volume}%)")
                    for seg_start, seg_end in valid_segments:
                        segment_duration = seg_end - seg_start
                        segment_voice = voice[seg_start:seg_end]
                        segment_background = prepare_background(
                            segment_voice, segment_duration, seg_start)
                        if segment_background is not None:
                            music_stem = music_stem.overlay(
                                segment_background, position=seg_start)
                            background_applied = True
                    if background_applied:
                        log("Mixed background music on selected voice segments")
                    else:
                        log("No background music segments could be applied")
                else:
                    log("No valid background segments provided; skipping background music")
            else:
                log(
                    f"Creating background music for voice (volume: {background_volume}%)")
                background = prepare_background(voice, len(voice), 0)
                if background is not None:
                    log("Mixing background music with voice recording")
                    music_stem = background
                    background_applied = True

        # Add outro if provided (no background music)
        if outro_file and os.path.exists(outro_file):
            log(f"Adding outro: {os.path.basename(outro_file)}")
            outro = self.load_audio(outro_file)
            outro_duration = len(outro)
        else:
            outro = None

        # Place all stems on one timeline. This also preserves the real last
        # voice second when overlapping an outro without an intro.
        intro_overlap = (min(overlap_ms, len(voice))
                         if intro is not None and intro_voice_overlap
                         and intro_duration >= overlap_ms else 0)
        voice_offset_ms = intro_duration - intro_overlap
        outro_overlap = (overlap_ms if outro is not None and voice_outro_overlap
                         and min(len(voice), outro_duration) >= overlap_ms else 0)
        outro_offset_ms = voice_offset_ms + len(voice) - outro_overlap
        if intro_overlap:
            log(f"Applying {intro_overlap}ms overlap between intro and voice")
        if outro is not None:
            if outro_overlap:
                log(f"Adding outro with {outro_overlap}ms overlap")
            elif not voice_outro_overlap:
                outro = self.fade_in(outro, 200)
                if background_applied:
                    music_stem = self.fade_out(music_stem, 500)
                    log("Applied 500ms fade-out to music only before outro")
        else:
            log("No outro file provided")

        episode_duration = outro_offset_ms + outro_duration
        episode_music = AudioSegment.silent(
            duration=episode_duration, frame_rate=voice.frame_rate)
        episode_music = episode_music.overlay(
            music_stem, position=voice_offset_ms)
        if intro is not None:
            episode_music = episode_music.overlay(intro)
        if outro is not None:
            episode_music = episode_music.overlay(
                outro, position=outro_offset_ms)
        podcast = episode_music.overlay(voice, position=voice_offset_ms)
        for track in selected_tracks:
            track["episode_start_ms"] = voice_offset_ms + track["start_ms"]
            track["episode_end_ms"] = voice_offset_ms + track["end_ms"]

        # Export final podcast
        log(f"Exporting to: {output_file}")
        with podcast.export(output_file, format="mp3"):
            pass

        # Optional mastering never destroys the successful unnormalized export.
        # The owned directory cleans partial WAV/MP3 outputs even on failure.
        if normalize_lufs:
            try:
                log(f"Normalizing audio to {cfg.target_lufs} LUFS...")
                with tempfile.TemporaryDirectory(
                        prefix="podcast_normalize_",
                        dir=os.path.dirname(os.path.abspath(output_file))) as temp_dir:
                    temp_wav = os.path.join(temp_dir, "source.wav")
                    with podcast.export(temp_wav, format="wav"):
                        pass
                    normalized_file = normalize_audio_lufs(
                        temp_wav, output_file=os.path.join(
                            temp_dir, "normalized.wav"),
                        target_lufs=cfg.target_lufs, true_peak=cfg.target_true_peak_dbtp,
                        lra=cfg.lra, log_callback=log)
                    if normalized_file and normalized_file != temp_wav:
                        normalized_audio = self.load_audio(normalized_file)
                        temp_mp3 = os.path.join(temp_dir, "normalized.mp3")
                        with normalized_audio.export(temp_mp3, format="mp3"):
                            pass
                        os.replace(temp_mp3, output_file)
                        log("✓ Applied LUFS normalization to final output")
                    else:
                        log("Warning: LUFS normalization skipped or failed. Using unnormalized export.")
            except Exception as error:
                log(
                    f"Warning: LUFS normalization failed: {error}. Using unnormalized export.")

        if quality_gate_enabled:
            # Mix metrics describe processed stems before master normalization;
            # final loudness, clipping and silence always measure the exact MP3.
            try:
                if config_error is not None:
                    raise ValueError(config_error)
                analyzer = AudioQualityAnalyzer(cfg, log_callback=log)
                mix_report = analyzer.analyze_mix(
                    voice, episode_music[voice_offset_ms:
                                         voice_offset_ms + len(voice)],
                    offset_seconds=voice_offset_ms / 1000)
                report = analyzer.analyze_file(
                    output_file, mix_report=mix_report)
                if not report.analysis_complete:
                    if "ANALYSIS_UNAVAILABLE" not in report.failures:
                        report.failures.append("ANALYSIS_UNAVAILABLE")
                    log("[AudioQC] ANALYSIS_UNAVAILABLE: QC incomplete; keeping exported podcast.")
            except Exception as error:
                report = AudioQualityReport(
                    file_path=os.fspath(output_file), failures=["ANALYSIS_UNAVAILABLE"],
                    analysis_errors=[str(error)], preview_seconds=cfg.preview_seconds)
                log(
                    f"[AudioQC] ANALYSIS_UNAVAILABLE: {error}. Keeping exported podcast.")
            preview_identity = None
            try:
                if create_preview(output_file, report) is None:
                    log("Warning: Quality preview unavailable; keeping exported podcast.")
                preview_identity = _register_quality_preview(
                    report.preview_file, output_file)
            except Exception as error:
                report.warnings.append("PREVIEW_UNAVAILABLE")
                log(
                    f"Warning: Quality preview failed: {error}. Keeping exported podcast.")

            metadata = {
                "music_seed": music_seed,
                "selected_tracks": selected_tracks,
                "voice_offset_ms": voice_offset_ms,
                "outro_offset_ms": outro_offset_ms,
                "mix_analysis_stage": "post_gain_post_duck_pre_master",
                "settings": {
                    "quality_config": asdict(cfg),
                    "background_volume": background_volume,
                    "track_volumes": {os.fspath(k): v for k, v in (track_volumes or {}).items()},
                    "background_segments": background_segments,
                    "auto_balance_levels": auto_balance_levels,
                    "min_voice_music_separation_db": min_voice_music_separation_db,
                    "auto_ducking": auto_ducking,
                    "normalize_lufs": normalize_lufs,
                    "trim_silence": trim_silence,
                    "denoise_audio": denoise_audio,
                    "denoise_method": denoise_method,
                    "enhance_voice_enabled": enhance_voice_enabled,
                    "voice_enhancement_preset": voice_enhancement_preset,
                    "intro_file": os.fspath(intro_file) if intro_file else None,
                    "outro_file": os.fspath(outro_file) if outro_file else None,
                    "intro_voice_overlap": intro_voice_overlap,
                    "voice_outro_overlap": voice_outro_overlap,
                },
            }
            try:
                payload = report.to_dict()
                payload["metadata"] = metadata
                payload["schema"] = "ntn-quality-v1"
                payload["output_path"] = os.path.realpath(output_file)
                payload["identity"] = _quality_file_identity(output_file)
                payload["preview_identity"] = preview_identity
                _write_quality_sidecar(os.path.realpath(
                    output_file) + ".quality.json", payload)
            except Exception as error:
                log(
                    f"Warning: Could not save quality report: {error}. Keeping exported podcast.")
            self.last_quality_report = report
            if quality_report_callback is not None:
                try:
                    quality_report_callback(report)
                except Exception as error:
                    log(
                        f"Warning: Quality report callback failed: {error}. Keeping exported podcast.")
            log("[AudioQC] RESULT: {}{}".format(
                report.status, " - " +
                ", ".join(report.failures + report.warnings)
                if report.failures or report.warnings else ""))

        # Phase 3: Transcription (after final export)
        transcript_path = None
        if generate_transcript and not defer_transcription:
            transcript_path = self.transcribe_podcast(
                audio_file=output_file,
                whisper_model=whisper_model,
                log_callback=log
            )

        log("Podcast creation complete!")

        return output_file, denoised_file_path, transcript_path

    def transcribe_podcast(
        self,
        audio_file: str,
        whisper_model: str = "base",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Generate a transcript for the provided audio file.

        Args:
            audio_file: Path to the audio file to transcribe
            whisper_model: Whisper model size ("tiny", "base", "small", "medium", "large")
            log_callback: Optional callback function for logging

        Returns:
            Path to transcript file or None if transcription fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        transcript_path = None

        try:
            log(
                f"Generating transcript using Whisper ({whisper_model} model)...")
            from .whisper_transcriber import WhisperTranscriber

            transcriber = WhisperTranscriber(model_size=whisper_model)

            if transcriber.is_available():
                result = transcriber.transcribe(
                    audio_file,
                    log_callback=log
                )

                if result and "output_file" in result:
                    transcript_path = result["output_file"]
                    log(f"✓ Transcript generated: {os.path.basename(transcript_path)}")

                    if "language" in result:
                        log(f"Detected language: {result['language']}")
                else:
                    log("Warning: Transcription failed. Continuing without transcript.")
            else:
                log("Warning: Whisper not available. Install openai-whisper to enable transcription.")
        except Exception as e:
            log(f"Error during transcription: {e}. Continuing without transcript.")

        return transcript_path
