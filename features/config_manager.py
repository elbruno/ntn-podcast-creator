"""Configuration management for podcast creator application."""

import json
import os
import glob
import math
import tempfile
from copy import deepcopy
from dataclasses import asdict
from threading import RLock
from typing import Dict, List, Any, Optional
from .audio_quality import AudioQualityConfig


DEFAULT_RSS_FEED_URL = "https://feeds.ivoox.com/feed_fg_f1277993_filtro_1.xml"


class ConfigManager:
    """Manages application configuration with persistent storage."""

    def __init__(self, config_file: str = "core/config.json"):
        """Initialize configuration manager.

        Args:
            config_file: Path to the configuration JSON file
        """
        self.config_file = config_file
        self._lock = RLock()
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default config.

        Returns:
            Configuration dictionary
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
        defaults = self._default_config()
        # Missing audio keys mean discovery is allowed; None/[] mean an
        # explicit selection. Keep fallback defaults out of that distinction.
        # Legacy getters and snapshot() still supply the same audio defaults.
        for key in ("intro_file", "outro_file", "background_tracks"):
            defaults.pop(key)
        return defaults

    def _default_config(self) -> Dict[str, Any]:
        """Create default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "intro_file": None,
            "outro_file": None,
            "background_tracks": [],
            "background_volume": 10,
            "track_volumes": {},  # Individual volumes per track
            "last_output_name": "podcast_output",
            "rss_feed_url": DEFAULT_RSS_FEED_URL,
            "prioritize_recording_filename": True,
            "delete_voice": True,
            "trim_silence": True,
            # Audio denoising feature (enabled by default)
            "denoise_audio": True,
            "denoise_method": "audio_denoiser",  # audio_denoiser, spectral, rnnoise
            # Voice enhancement feature (disabled by default)
            "enhance_voice": False,
            "voice_enhancement_preset": "podcast",  # podcast, light, aggressive
            # LUFS normalization
            "normalize_lufs": False,
            "target_lufs": -16.0,  # Target LUFS level
            # Overlap settings
            "intro_voice_overlap": True,  # Enable 1-second overlap between intro and voice
            "voice_outro_overlap": False,  # Enable 1-second overlap between voice and outro
            # Audio balance & level safety
            "auto_balance_levels": True,  # Auto-balance voice & music to prevent masking
            # Minimum dB separation between voice and background music
            "min_voice_music_separation_db": 18.0,
            "auto_ducking": True,  # Dynamically lower background music during speech
            "quality_gate_enabled": False,  # Opt-in; export is never blocked
            "audio_quality": asdict(AudioQualityConfig()),
            "music_seed": 0,  # Reproducible music selection per render
            # Whisper transcription feature (disabled by default)
            "generate_transcript": False,
            "whisper_model": "base",  # tiny, base, small, medium, large
            # Template feature
            "active_template": None  # Currently active template name
        }

    def snapshot(self) -> Dict[str, Any]:
        """Return detached defaults merged with saved values, without writing.

        Only missing fields (including audio_quality fields) receive defaults.
        Invalid saved values and unknown keys remain visible for UI repair.
        Unlike a save, this does not override the saved quality LUFS target.
        """
        with self._lock:
            result = self._default_config()
            result.update(deepcopy(self.config))
            if isinstance(result["audio_quality"], dict):
                quality = asdict(AudioQualityConfig())
                quality.update(result["audio_quality"])
                result["audio_quality"] = quality
            return result

    @staticmethod
    def _validate_number(key: str, value: Any) -> None:
        """Reject coercion, booleans, nonfinite values and oversized numbers."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be numeric")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{key} must be finite")

    def _validate_setting(self, key: str, value: Any, defaults: Dict[str, Any]) -> None:
        """Validate a known recurring setting without changing its value."""
        if isinstance(defaults[key], bool):
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be boolean")
        elif key in ("intro_file", "outro_file", "active_template"):
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{key} must be a string or None")
        elif key in ("last_output_name", "rss_feed_url"):
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
        elif key in ("denoise_method", "voice_enhancement_preset", "whisper_model"):
            choices = {
                "denoise_method": ("audio_denoiser", "spectral", "rnnoise"),
                "voice_enhancement_preset": ("podcast", "light", "aggressive"),
                "whisper_model": ("tiny", "base", "small", "medium", "large"),
            }
            if not isinstance(value, str) or value not in choices[key]:
                raise ValueError(f"Invalid {key}: {value!r}")
        elif key == "background_tracks":
            if not isinstance(value, list) or any(not isinstance(path, str) for path in value):
                raise ValueError("background_tracks must be a list of strings")
        elif key == "track_volumes":
            if not isinstance(value, dict):
                raise ValueError("track_volumes must be a settings object")
            for path, volume in value.items():
                if not isinstance(path, str):
                    raise ValueError("track_volumes keys must be strings")
                self._validate_setting("background_volume", volume, defaults)
        elif key == "music_seed":
            if type(value) is not int or abs(value) > 2**53 - 1:
                raise ValueError(
                    "music_seed must be an integer within +/- (2**53 - 1)")
        elif key in ("target_lufs", "background_volume", "min_voice_music_separation_db"):
            self._validate_number(key, value)
            if key == "target_lufs" and not -70 <= value <= -5:
                raise ValueError("target_lufs must be between -70 and -5")
            if key == "background_volume" and not 0 <= value <= 50:
                raise ValueError("background_volume must be between 0 and 50")
            if key == "min_voice_music_separation_db" and value < 0:
                raise ValueError(
                    "min_voice_music_separation_db must be nonnegative")
        elif key == "audio_quality":
            if not isinstance(value, dict):
                raise ValueError("audio_quality must be a settings object")
            for name, number in value.items():
                if name in defaults["audio_quality"]:
                    self._validate_number(f"audio_quality.{name}", number)
        else:
            raise ValueError(f"No validation defined for {key!r}")

    def update_settings(self, settings: dict) -> None:
        """Validate and atomically persist one batch for the explicit Save UI.

        Accept only default configuration keys and known, flat audio_quality
        fields. Merge partial quality updates; retain unknown *stored* keys.
        Validate the complete candidate, so invalid legacy settings must be
        repaired before saving. The main target_lufs explicitly overrides the
        quality target. Audio paths need not exist on this machine.

        Raise ValueError for invalid settings and propagate write errors. Neither
        memory nor the existing file changes unless replacement succeeds.
        """
        with self._lock:
            if not isinstance(settings, dict):
                raise ValueError("settings must be a settings object")
            settings = deepcopy(settings)
            defaults = self._default_config()
            for key, value in settings.items():
                if key not in defaults:
                    raise ValueError(f"Unknown setting: {key!r}")
                self._validate_setting(key, value, defaults)
                if key == "audio_quality":
                    for name in value:
                        if name not in defaults["audio_quality"]:
                            raise ValueError(
                                f"Unknown audio_quality setting: {name!r}")

            candidate = self.snapshot()
            for key, value in settings.items():
                if key == "audio_quality":
                    quality = candidate[key]
                    if not isinstance(quality, dict):
                        quality = deepcopy(defaults[key])
                    quality.update(value)
                    candidate[key] = quality
                else:
                    candidate[key] = value
            if isinstance(candidate["audio_quality"], dict):
                candidate["audio_quality"]["target_lufs"] = candidate["target_lufs"]
            for key in defaults:
                self._validate_setting(key, candidate[key], defaults)
            # Use the strict constructor, not from_mapping's string coercion or
            # null-as-default behavior. Preserve unknown legacy quality fields.
            AudioQualityConfig(**{key: candidate["audio_quality"][key]
                                  for key in defaults["audio_quality"]})
            self._write_settings(candidate)
            self.config = candidate

    def _write_settings(self, settings: Dict[str, Any]) -> None:
        """Stage next to the destination so os.replace is an atomic commit."""
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', delete=False,
                    dir=os.path.dirname(os.path.abspath(self.config_file)),
                    prefix='.config-', suffix='.tmp') as temporary:
                temporary_path = temporary.name
                json.dump(settings, temporary, indent=2, allow_nan=False)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.config_file)
        finally:
            if temporary_path is not None and os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def save_config(self) -> None:
        """Save current configuration to file."""
        with self._lock:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2)
            except IOError as e:
                print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save.

        Args:
            key: Configuration key
            value: Value to set
        """
        with self._lock:
            self.config[key] = value
            self.save_config()

    def update_intro(self, file_path: Optional[str]) -> None:
        """Update intro file path.

        Args:
            file_path: Path to intro audio file
        """
        self.set("intro_file", file_path)

    def update_outro(self, file_path: Optional[str]) -> None:
        """Update outro file path.

        Args:
            file_path: Path to outro audio file
        """
        self.set("outro_file", file_path)

    def update_background_tracks(self, file_paths: List[str]) -> None:
        """Update background music tracks.

        Args:
            file_paths: List of paths to background music files
        """
        self.set("background_tracks", file_paths)

    def add_background_track(self, file_path: str) -> None:
        """Add a background music track.

        Args:
            file_path: Path to background music file
        """
        tracks = self.get("background_tracks", [])
        if file_path not in tracks:
            tracks.append(file_path)
            self.set("background_tracks", tracks)

    def remove_background_track(self, file_path: str) -> None:
        """Remove a background music track.

        Args:
            file_path: Path to background music file to remove
        """
        tracks = self.get("background_tracks", [])
        if file_path in tracks:
            tracks.remove(file_path)
            self.set("background_tracks", tracks)

    def update_volume(self, volume: int) -> None:
        """Update background music volume.

        Args:
            volume: Volume percentage (0-50)
        """
        self.set("background_volume", max(0, min(50, volume)))

    def get_intro(self) -> Optional[str]:
        """Get intro file path.

        Returns:
            Path to intro file or None
        """
        return self.get("intro_file")

    def get_outro(self) -> Optional[str]:
        """Get outro file path.

        Returns:
            Path to outro file or None
        """
        return self.get("outro_file")

    def get_background_tracks(self) -> List[str]:
        """Get background music tracks.

        Returns:
            List of background music file paths
        """
        return self.get("background_tracks", [])

    def get_volume(self) -> int:
        """Get background music volume.

        Returns:
            Volume percentage
        """
        return self.get("background_volume", 10)

    def get_last_output_name(self) -> str:
        """Get last used output filename.

        Returns:
            Last output filename
        """
        return self.get("last_output_name", "podcast_output")

    def get_prioritize_recording_filename(self) -> bool:
        """Get default upload ordering preference.

        Returns:
            True if Recording.m4a should be placed first by default
        """
        return self.get("prioritize_recording_filename", True)

    def set_prioritize_recording_filename(self, enabled: bool) -> None:
        """Set default upload ordering preference.

        Args:
            enabled: True to prioritize Recording.m4a as the first voice file
        """
        self.set("prioritize_recording_filename", enabled)

    def update_last_output_name(self, name: str) -> None:
        """Update last used output filename.

        Args:
            name: Output filename
        """
        self.set("last_output_name", name)

    def get_rss_feed_url(self) -> str:
        """Get the configured RSS feed URL for episode suggestions.

        Returns:
            RSS feed URL string
        """
        return self.get("rss_feed_url", DEFAULT_RSS_FEED_URL)

    def set_rss_feed_url(self, url: str) -> None:
        """Update RSS feed URL used for episode suggestions.

        Args:
            url: RSS feed URL
        """
        cleaned_url = (url or DEFAULT_RSS_FEED_URL).strip()
        self.set("rss_feed_url", cleaned_url)

    def get_track_volume(self, track_path: str) -> int:
        """Get volume setting for a specific track.

        Args:
            track_path: Path to the track file

        Returns:
            Volume percentage for the track (defaults to global volume)
        """
        if not track_path or not track_path.strip():
            return self.get_volume()
        track_volumes = self.get("track_volumes", {})
        return track_volumes.get(track_path, self.get_volume())

    def set_track_volume(self, track_path: str, volume: int) -> None:
        """Set volume for a specific track.

        Args:
            track_path: Path to the track file
            volume: Volume percentage (0-50)
        """
        track_volumes = self.get("track_volumes", {})
        track_volumes[track_path] = max(0, min(50, volume))
        self.set("track_volumes", track_volumes)

    def apply_volume_to_all_tracks(self, volume: int) -> None:
        """Apply volume setting to all background tracks.

        Args:
            volume: Volume percentage (0-50)
        """
        volume = max(0, min(50, volume))
        tracks = self.get_background_tracks()
        track_volumes = {}
        for track in tracks:
            track_volumes[track] = volume
        self.set("track_volumes", track_volumes)
        # Also update global volume
        self.update_volume(volume)

    def get_all_track_volumes(self) -> Dict[str, int]:
        """Get all track volumes.

        Returns:
            Dictionary mapping track paths to volumes
        """
        return self.get("track_volumes", {})

    def get_denoise_audio(self) -> bool:
        """Get audio denoising setting.

        Returns:
            True if audio denoising is enabled, False otherwise
        """
        return self.get("denoise_audio", True)

    def set_denoise_audio(self, enabled: bool) -> None:
        """Set audio denoising setting.

        Args:
            enabled: True to enable audio denoising, False to disable
        """
        self.set("denoise_audio", enabled)

    def get_denoise_method(self) -> str:
        """Get noise reduction method.

        Returns:
            Denoise method: 'audio_denoiser', 'spectral', or 'rnnoise'
        """
        return self.get("denoise_method", "audio_denoiser")

    def set_denoise_method(self, method: str) -> None:
        """Set noise reduction method.

        Args:
            method: Denoise method ('audio_denoiser', 'spectral', 'rnnoise')
        """
        self.set("denoise_method", method)

    def get_normalize_lufs(self) -> bool:
        """Get LUFS normalization setting.

        Returns:
            True if LUFS normalization is enabled, False otherwise
        """
        return self.get("normalize_lufs", False)

    def set_normalize_lufs(self, enabled: bool) -> None:
        """Set LUFS normalization setting.

        Args:
            enabled: True to enable LUFS normalization, False to disable
        """
        self.set("normalize_lufs", enabled)

    def get_target_lufs(self) -> float:
        """Get target LUFS level.

        Returns:
            Target LUFS level
        """
        return self.get("target_lufs", -16.0)

    def set_target_lufs(self, target: float) -> None:
        """Set target LUFS level.

        Args:
            target: Target LUFS level (-14 or -16 recommended)
        """
        self.set("target_lufs", target)

    def get_intro_voice_overlap(self) -> bool:
        """Get intro-voice overlap setting.

        Returns:
            True if intro-voice overlap is enabled, False otherwise
        """
        return self.get("intro_voice_overlap", True)

    def set_intro_voice_overlap(self, enabled: bool) -> None:
        """Set intro-voice overlap setting.

        Args:
            enabled: True to enable intro-voice overlap, False to disable
        """
        self.set("intro_voice_overlap", enabled)

    def get_voice_outro_overlap(self) -> bool:
        """Get voice-outro overlap setting.

        Returns:
            True if voice-outro overlap is enabled, False otherwise
        """
        return self.get("voice_outro_overlap", False)

    def set_voice_outro_overlap(self, enabled: bool) -> None:
        """Set voice-outro overlap setting.

        Args:
            enabled: True to enable voice-outro overlap, False to disable
        """
        self.set("voice_outro_overlap", enabled)

    def get_auto_balance_levels(self) -> bool:
        """Get auto-balance audio levels setting.

        Returns:
            True if auto-balance is enabled, False otherwise
        """
        return self.get("auto_balance_levels", True)

    def set_auto_balance_levels(self, enabled: bool) -> None:
        """Set auto-balance audio levels setting.

        Args:
            enabled: True to enable auto-balance, False to disable
        """
        self.set("auto_balance_levels", enabled)

    def get_min_voice_music_separation_db(self) -> float:
        """Get minimum voice-to-music separation in dB.

        Returns:
            Separation in dB (e.g. 18.0)
        """
        return float(self.get("min_voice_music_separation_db", 18.0))

    def set_min_voice_music_separation_db(self, value: float) -> None:
        """Set minimum voice-to-music separation in dB.

        Args:
            value: Minimum separation in dB
        """
        self.set("min_voice_music_separation_db", float(value))

    def get_auto_ducking(self) -> bool:
        """Get auto-ducking setting.

        Returns:
            True if auto-ducking is enabled, False otherwise
        """
        return self.get("auto_ducking", True)

    def get_audio_quality_config(self) -> AudioQualityConfig:
        """Merge legacy configuration with shared defaults; LUFS slider wins.

        Invalid saved thresholds raise ValueError rather than silently certifying
        an episode with different thresholds. Loading older configs is supported.
        """
        settings = self.get("audio_quality", {})
        if not isinstance(settings, dict):
            raise ValueError("audio_quality must be a settings object")
        settings = dict(settings)
        settings["target_lufs"] = self.get_target_lufs()
        return AudioQualityConfig.from_mapping(settings)

    def set_auto_ducking(self, enabled: bool) -> None:
        """Set auto-ducking setting.

        Args:
            enabled: True to enable auto-ducking, False to disable
        """
        self.set("auto_ducking", enabled)

    def get_generate_transcript(self) -> bool:
        """Get transcription generation setting.

        Returns:
            True if transcription generation is enabled, False otherwise
        """
        return self.get("generate_transcript", False)

    def set_generate_transcript(self, enabled: bool) -> None:
        """Set transcription generation setting.

        Args:
            enabled: True to enable transcription generation, False to disable
        """
        self.set("generate_transcript", enabled)

    def get_whisper_model(self) -> str:
        """Get Whisper model size setting.

        Returns:
            Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        """
        return self.get("whisper_model", "base")

    def set_whisper_model(self, model: str) -> None:
        """Set Whisper model size setting.

        Args:
            model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.set("whisper_model", model)

    def load_default_audio_files(self) -> None:
        """Discover audio files only for keys absent from the configuration.

        Saved selections, including None and empty lists, always win. New or
        incomplete configurations use the first intro/outro and all background
        tracks found in their dedicated directories.
        """
        audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.ogg', '*.flac']
        with self._lock:
            for key, directory in (("intro_file", "intro_audio"),
                                   ("outro_file", "outro_audio"),
                                   ("background_tracks", "background_music")):
                if key in self.config:
                    continue
                files = []
                for ext in audio_extensions:
                    files.extend(
                        glob.glob(os.path.join('audios', directory, ext)))
                valid_files = [path for path in files if os.path.exists(path)]
                if not valid_files:
                    continue
                if key == "background_tracks":
                    self.update_background_tracks(valid_files)
                    print(
                        f"Loaded {len(valid_files)} default background music track(s)")
                elif key == "intro_file":
                    self.update_intro(valid_files[0])
                    print(
                        f"Loaded default intro: {os.path.basename(valid_files[0])}")
                else:
                    self.update_outro(valid_files[0])
                    print(
                        f"Loaded default outro: {os.path.basename(valid_files[0])}")

    def get_active_template(self) -> Optional[str]:
        """Get the currently active template name.

        Returns:
            Active template name or None
        """
        return self.get("active_template")

    def set_active_template(self, template_name: Optional[str]) -> None:
        """Set the currently active template.

        Args:
            template_name: Name of the active template or None
        """
        self.set("active_template", template_name)

    def get_template_settings(self) -> Dict[str, Any]:
        """Get all settings that should be saved in a template.

        Returns:
            Dictionary of template-saveable settings
        """
        return {
            "intro_file": self.get_intro(),
            "outro_file": self.get_outro(),
            "background_tracks": self.get_background_tracks(),
            "background_volume": self.get_volume(),
            "track_volumes": self.get_all_track_volumes(),
            "delete_voice": self.get("delete_voice", True),
            "trim_silence": self.get("trim_silence", True),
            "denoise_audio": self.get_denoise_audio(),
            "denoise_method": self.get_denoise_method(),
            "enhance_voice": self.get("enhance_voice", False),
            "voice_enhancement_preset": self.get("voice_enhancement_preset", "podcast"),
            "normalize_lufs": self.get_normalize_lufs(),
            "target_lufs": self.get_target_lufs(),
            "intro_voice_overlap": self.get_intro_voice_overlap(),
            "voice_outro_overlap": self.get_voice_outro_overlap(),
            "auto_balance_levels": self.get_auto_balance_levels(),
            "min_voice_music_separation_db": self.get_min_voice_music_separation_db(),
            "auto_ducking": self.get_auto_ducking(),
            "quality_gate_enabled": self.get("quality_gate_enabled", False),
            "audio_quality": asdict(self.get_audio_quality_config()),
            "music_seed": self.get("music_seed", 0),
            "generate_transcript": self.get_generate_transcript(),
            "whisper_model": self.get_whisper_model()
        }

    def apply_template_settings(self, settings: Dict[str, Any]) -> None:
        """Apply settings from a template to current configuration.

        Args:
            settings: Dictionary of settings to apply
        """
        # Validate QC before applying any part of the template.
        quality = None
        if "audio_quality" in settings:
            values = settings["audio_quality"]
            if not isinstance(values, dict):
                raise ValueError("audio_quality must be a settings object")
            values = dict(values)
            values["target_lufs"] = settings.get(
                "target_lufs", self.get_target_lufs())
            quality = asdict(AudioQualityConfig.from_mapping(values))
        if "music_seed" in settings and (isinstance(settings["music_seed"], bool)
                                         or not isinstance(settings["music_seed"], int)):
            raise ValueError("music_seed must be an integer")
        if "quality_gate_enabled" in settings and not isinstance(settings["quality_gate_enabled"], bool):
            raise ValueError("quality_gate_enabled must be boolean")
        for key in ("delete_voice", "trim_silence"):
            if key in settings and not isinstance(settings[key], bool):
                raise ValueError(f"{key} must be boolean")

        # Audio files
        if "intro_file" in settings:
            intro = settings["intro_file"]
            if intro and os.path.exists(intro):
                self.update_intro(intro)
            elif not intro:
                self.update_intro(None)

        if "outro_file" in settings:
            outro = settings["outro_file"]
            if outro and os.path.exists(outro):
                self.update_outro(outro)
            elif not outro:
                self.update_outro(None)

        if "background_tracks" in settings:
            tracks = settings["background_tracks"]
            # Filter to only existing files
            valid_tracks = [t for t in tracks if os.path.exists(t)] if tracks else [
            ]
            self.update_background_tracks(valid_tracks)

        # Volumes
        if "background_volume" in settings:
            self.update_volume(settings["background_volume"])

        if "track_volumes" in settings:
            self.set("track_volumes", settings["track_volumes"])

        # Processing options
        for key in ("delete_voice", "trim_silence"):
            if key in settings:
                self.set(key, settings[key])

        if "denoise_audio" in settings:
            self.set_denoise_audio(settings["denoise_audio"])

        if "denoise_method" in settings:
            self.set_denoise_method(settings["denoise_method"])

        if "normalize_lufs" in settings:
            self.set_normalize_lufs(settings["normalize_lufs"])

        if "target_lufs" in settings:
            self.set_target_lufs(settings["target_lufs"])

        # Overlap settings
        if "intro_voice_overlap" in settings:
            self.set_intro_voice_overlap(settings["intro_voice_overlap"])

        if "voice_outro_overlap" in settings:
            self.set_voice_outro_overlap(settings["voice_outro_overlap"])

        # Audio balance & ducking settings
        if "auto_balance_levels" in settings:
            self.set_auto_balance_levels(settings["auto_balance_levels"])

        if "min_voice_music_separation_db" in settings:
            self.set_min_voice_music_separation_db(
                settings["min_voice_music_separation_db"])

        if "auto_ducking" in settings:
            self.set_auto_ducking(settings["auto_ducking"])

        if quality is not None:
            self.set("audio_quality", quality)
        for key in ("quality_gate_enabled", "music_seed"):
            if key in settings:
                self.set(key, settings[key])

        if "enhance_voice" in settings:
            self.set("enhance_voice", settings["enhance_voice"])

        if "voice_enhancement_preset" in settings:
            self.set("voice_enhancement_preset",
                     settings["voice_enhancement_preset"])

        if "generate_transcript" in settings:
            self.set_generate_transcript(settings["generate_transcript"])

        if "whisper_model" in settings:
            self.set_whisper_model(settings["whisper_model"])
