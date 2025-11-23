"""Audio denoising processor using audio-denoiser library."""

import os
from typing import Optional, Callable


class AudioDenoiserProcessor:
    """Handles audio denoising using the audio-denoiser library.
    
    This class provides integration with the audio-denoiser library to clean
    audio recordings by removing background noise before podcast creation.
    """

    def __init__(self):
        """Initialize the audio denoiser processor."""
        self.denoiser = None
        self.available = False
        self._initialize_denoiser()

    def _initialize_denoiser(self):
        """Initialize the audio-denoiser library if available."""
        try:
            import torch
            from audio_denoiser.AudioDenoiser import AudioDenoiser
            
            # Check if CUDA is available, otherwise use CPU
            device = torch.device('cuda:0') if torch.cuda.is_available() else torch.device('cpu')
            self.denoiser = AudioDenoiser(device=device)
            self.available = True
        except ImportError as e:
            print(f"Warning: audio-denoiser not available: {e}")
            self.available = False
        except Exception as e:
            print(f"Warning: Could not initialize audio-denoiser: {e}")
            self.available = False

    def is_available(self) -> bool:
        """Check if the audio denoiser is available.
        
        Returns:
            True if audio-denoiser is available, False otherwise
        """
        return self.available

    def denoise_audio(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        auto_scale: bool = True,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Denoise an audio file using audio-denoiser.
        
        Args:
            input_file: Path to input audio file
            output_file: Path for denoised output (auto-generated if None)
            auto_scale: Whether to auto-scale the audio (recommended for low volume)
            log_callback: Optional callback function for logging
            
        Returns:
            Path to denoised audio file, or None if denoising fails
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            Exception: If denoising fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        # Validate input file
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Check if denoiser is available
        if not self.is_available():
            log("Warning: audio-denoiser not available, skipping denoising")
            return input_file

        # Generate output file path if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(
                os.path.dirname(input_file),
                f"{base_name}_denoised.wav"
            )

        log(f"Starting audio denoising for: {os.path.basename(input_file)}")

        try:
            # Process the audio file
            self.denoiser.process_audio_file(
                input_file,
                output_file,
                auto_scale=auto_scale
            )
            
            if os.path.exists(output_file):
                log(f"✓ Audio denoising complete: {os.path.basename(output_file)}")
                return output_file
            else:
                log("Denoising failed, using original audio")
                return input_file

        except Exception as e:
            log(f"Error during denoising: {e}")
            log("Falling back to original audio")
            return input_file


def denoise_audio_file(
    input_file: str,
    output_file: Optional[str] = None,
    enabled: bool = True,
    auto_scale: bool = True,
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Convenience function to denoise an audio file.
    
    Args:
        input_file: Path to input audio file
        output_file: Path for denoised output (auto-generated if None)
        enabled: Whether denoising is enabled (if False, returns original)
        auto_scale: Whether to auto-scale the audio
        log_callback: Optional callback function for logging
        
    Returns:
        Path to denoised audio file (or original if denoising disabled/failed)
    """
    def log(message: str):
        if log_callback:
            log_callback(message)
        else:
            print(message)

    if not enabled:
        log("Audio denoising is disabled")
        return input_file

    try:
        processor = AudioDenoiserProcessor()
        return processor.denoise_audio(
            input_file,
            output_file,
            auto_scale,
            log_callback
        )
    except Exception as e:
        log(f"Denoising failed: {e}")
        return input_file
