"""
NTN Podcast Creator - Core Module

This package contains core application functionality:
- Configuration files
- Application constants
- Shared utilities

The core package provides centralized access to application-wide
configuration and common functionality.
"""

import os

# Application constants
APP_NAME = "NTN Podcast Creator"
APP_VERSION = "2.0.0"
CONFIG_FILE = "core/config.json"

# Directory paths
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
AUDIOS_DIR = os.path.join(PROJECT_ROOT, "audios")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

# Audio file extensions supported
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']


def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        AUDIOS_DIR,
        OUTPUTS_DIR,
        UPLOADS_DIR,
        os.path.join(AUDIOS_DIR, "intro_audio"),
        os.path.join(AUDIOS_DIR, "outro_audio"),
        os.path.join(AUDIOS_DIR, "background_music"),
        os.path.join(AUDIOS_DIR, "test")
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


__all__ = [
    'APP_NAME',
    'APP_VERSION',
    'CONFIG_FILE',
    'CORE_DIR',
    'PROJECT_ROOT',
    'AUDIOS_DIR',
    'OUTPUTS_DIR',
    'UPLOADS_DIR',
    'DOCS_DIR',
    'SUPPORTED_AUDIO_FORMATS',
    'ensure_directories'
]
