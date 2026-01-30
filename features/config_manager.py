"""Configuration management for podcast creator application."""

import json
import os
import glob
from typing import Dict, List, Any, Optional


DEFAULT_RSS_FEED_URL = "https://feeds.ivoox.com/feed_fg_f1277993_filtro_1.xml"


class ConfigManager:
    """Manages application configuration with persistent storage."""

    def __init__(self, config_file: str = "core/config.json"):
        """Initialize configuration manager.

        Args:
            config_file: Path to the configuration JSON file
        """
        self.config_file = config_file
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
                return self._default_config()
        return self._default_config()

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
            # Template feature
            "active_template": None  # Currently active template name
        }

    def save_config(self) -> None:
        """Save current configuration to file."""
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

    def load_default_audio_files(self) -> None:
        """Load default audio files from dedicated directories.

        Scans audios/intro_audio/, audios/outro_audio/, and audios/background_music/ directories
        for audio files and automatically populates the configuration.

        For intro and outro: Uses the first audio file found in each directory.
        For background music: Loads all audio files found in the directory.
        """
        # Supported audio extensions
        audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.ogg', '*.flac']

        # Load intro audio (first file found)
        intro_files = []
        for ext in audio_extensions:
            intro_files.extend(
                glob.glob(os.path.join('audios', 'intro_audio', ext)))
        if intro_files:
            intro_file = intro_files[0]
            if os.path.exists(intro_file):
                self.update_intro(intro_file)
                print(f"Loaded default intro: {os.path.basename(intro_file)}")

        # Load outro audio (first file found)
        outro_files = []
        for ext in audio_extensions:
            outro_files.extend(
                glob.glob(os.path.join('audios', 'outro_audio', ext)))
        if outro_files:
            outro_file = outro_files[0]
            if os.path.exists(outro_file):
                self.update_outro(outro_file)
                print(f"Loaded default outro: {os.path.basename(outro_file)}")

        # Load all background music files
        background_files = []
        for ext in audio_extensions:
            background_files.extend(
                glob.glob(os.path.join('audios', 'background_music', ext)))

        if background_files:
            # Validate files exist and update config
            valid_files = [f for f in background_files if os.path.exists(f)]
            if valid_files:
                self.update_background_tracks(valid_files)
                print(
                    f"Loaded {len(valid_files)} default background music track(s)")

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
            "denoise_audio": self.get_denoise_audio(),
            "denoise_method": self.get_denoise_method(),
            "normalize_lufs": self.get_normalize_lufs(),
            "target_lufs": self.get_target_lufs(),
            "intro_voice_overlap": self.get_intro_voice_overlap(),
            "voice_outro_overlap": self.get_voice_outro_overlap()
        }

    def apply_template_settings(self, settings: Dict[str, Any]) -> None:
        """Apply settings from a template to current configuration.

        Args:
            settings: Dictionary of settings to apply
        """
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
            valid_tracks = [t for t in tracks if os.path.exists(t)] if tracks else []
            self.update_background_tracks(valid_tracks)

        # Volumes
        if "background_volume" in settings:
            self.update_volume(settings["background_volume"])

        if "track_volumes" in settings:
            self.set("track_volumes", settings["track_volumes"])

        # Processing options
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
