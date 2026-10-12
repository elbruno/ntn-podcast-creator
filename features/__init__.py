"""
NTN Podcast Creator - Features Module

This package contains all the core feature implementations:
- Audio processing and mixing
- AI audio denoising with large file support
- Adobe AI audio enhancement
- Configuration management

Modules:
    audio_processor: Core audio processing and podcast creation
    audio_denoiser_processor: AI-powered noise removal with chunking
    adobe_audio_enhancer: Adobe AI enhancement integration
    config_manager: Settings and configuration management
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audio_processor import AudioProcessor
    from .audio_denoiser_processor import AudioDenoiserProcessor, denoise_audio_file
    from .adobe_audio_enhancer import AdobeAudioEnhancer, enhance_audio_file
    from .config_manager import ConfigManager

__all__ = [
    'AudioProcessor',
    'AudioDenoiserProcessor',
    'denoise_audio_file',
    'AdobeAudioEnhancer',
    'enhance_audio_file',
    'ConfigManager'
]


def __getattr__(name):
    # Discovery and HTTP clients must not import audio/AI dependencies on Windows.
    modules = {
        "AudioProcessor": "audio_processor",
        "AudioDenoiserProcessor": "audio_denoiser_processor",
        "denoise_audio_file": "audio_denoiser_processor",
        "AdobeAudioEnhancer": "adobe_audio_enhancer",
        "enhance_audio_file": "adobe_audio_enhancer",
        "ConfigManager": "config_manager",
    }
    if name not in modules:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{modules[name]}", __name__), name)
    globals()[name] = value
    return value
