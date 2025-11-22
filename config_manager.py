"""Configuration management for podcast creator application."""

import json
import os
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
            "last_output_name": "podcast_output"
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
            volume: Volume percentage (0-100)
        """
        self.set("background_volume", max(0, min(100, volume)))
    
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
