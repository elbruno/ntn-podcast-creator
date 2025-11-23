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
