"""Configuration management for podcast creator application."""

import json
import os
import glob
from typing import Dict, List, Any, Optional


class ConfigManager:
    """Manages application configuration with persistent storage."""

    def __init__(self, config_file: str = "config.json"):
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
            "denoise_audio": True,  # Audio denoising feature (enabled by default)
            "enhance_audio": False  # Adobe audio enhancement feature
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

    def get_enhance_audio(self) -> bool:
        """Get audio enhancement setting.

        Returns:
            True if audio enhancement is enabled, False otherwise
        """
        return self.get("enhance_audio", False)

    def set_enhance_audio(self, enabled: bool) -> None:
        """Set audio enhancement setting.

        Args:
            enabled: True to enable audio enhancement, False to disable
        """
        self.set("enhance_audio", enabled)

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
