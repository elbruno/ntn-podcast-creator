"""Audio transcription using OpenAI Whisper."""

import os
from typing import Optional, Callable, Dict


class WhisperTranscriber:
    """Handles audio transcription using Whisper."""

    def __init__(self, model_size: str = "base"):
        """Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.model = None
        self.model_size = model_size
        self.available = False
        self._initialize_whisper()

    def _initialize_whisper(self):
        """Initialize Whisper model if available."""
        try:
            import whisper
            self.model = whisper.load_model(self.model_size)
            self.available = True
        except ImportError:
            print("Warning: openai-whisper not available")
            self.available = False
        except Exception as e:
            print(f"Warning: Could not initialize Whisper: {e}")
            self.available = False

    def is_available(self) -> bool:
        """Check if Whisper is available."""
        return self.available

    def transcribe(
        self,
        audio_file: str,
        output_file: Optional[str] = None,
        language: Optional[str] = None,
        task: str = "transcribe",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[Dict]:
        """Transcribe audio file using Whisper.

        Args:
            audio_file: Path to audio file
            output_file: Path to save transcript (auto-generated if None)
            language: Language code (None for auto-detection)
            task: Task type ("transcribe" or "translate")
            log_callback: Optional callback for logging

        Returns:
            Dictionary with transcription results, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        if not self.is_available():
            log("Warning: Whisper not available for transcription")
            return None

        if not os.path.exists(audio_file):
            log(f"Error: Audio file not found: {audio_file}")
            return None

        # Generate output file path if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            output_file = os.path.join(
                os.path.dirname(audio_file),
                f"{base_name}_transcript.txt"
            )

        try:
            log(f"Transcribing audio with Whisper ({self.model_size} model): {os.path.basename(audio_file)}")

            # Transcribe audio
            options = {"task": task}
            if language:
                options["language"] = language

            result = self.model.transcribe(audio_file, **options)

            # Save transcript to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result["text"])

            log(f"✓ Transcription complete: {os.path.basename(output_file)}")

            # Return full result for additional processing
            return {
                "text": result["text"],
                "segments": result.get("segments", []),
                "language": result.get("language", "unknown"),
                "output_file": output_file
            }

        except Exception as e:
            log(f"Error during transcription: {e}")
            return None

    def transcribe_with_timestamps(
        self,
        audio_file: str,
        output_file: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Transcribe audio with word-level timestamps.

        Args:
            audio_file: Path to audio file
            output_file: Path to save transcript (auto-generated if None)
            log_callback: Optional callback for logging

        Returns:
            Path to transcript file, or None if failed
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        result = self.transcribe(audio_file, output_file, log_callback=log_callback)

        if result and output_file:
            # Generate timestamped version with safe extension replacement
            base_name = os.path.splitext(output_file)[0]
            timestamped_file = f"{base_name}_timestamped.txt"

            try:
                with open(timestamped_file, 'w', encoding='utf-8') as f:
                    for segment in result.get("segments", []):
                        start = segment.get("start", 0)
                        end = segment.get("end", 0)
                        text = segment.get("text", "")
                        f.write(f"[{start:.2f}s - {end:.2f}s] {text}\n")

                log(f"✓ Timestamped transcript saved: {os.path.basename(timestamped_file)}")
                return timestamped_file

            except Exception as e:
                log(f"Error creating timestamped transcript: {e}")
                return output_file

        return None


def transcribe_audio(
    audio_file: str,
    output_file: Optional[str] = None,
    model_size: str = "base",
    with_timestamps: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Convenience function to transcribe audio file.

    Args:
        audio_file: Path to audio file
        output_file: Path to save transcript (auto-generated if None)
        model_size: Whisper model size (tiny, base, small, medium, large)
        with_timestamps: Include timestamps in transcript
        log_callback: Optional callback for logging

    Returns:
        Path to transcript file, or None if failed
    """
    transcriber = WhisperTranscriber(model_size=model_size)

    if with_timestamps:
        return transcriber.transcribe_with_timestamps(
            audio_file,
            output_file,
            log_callback=log_callback
        )
    else:
        result = transcriber.transcribe(
            audio_file,
            output_file,
            log_callback=log_callback
        )
        return result.get("output_file") if result else None
