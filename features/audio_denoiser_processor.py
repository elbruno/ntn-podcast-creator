"""Audio denoising processor using audio-denoiser library."""

import os
import tempfile
import shutil
from typing import Optional, Callable, List
from pydub import AudioSegment


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
            device = torch.device(
                'cuda:0') if torch.cuda.is_available() else torch.device('cpu')
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

    def _chunk_audio(
        self,
        input_file: str,
        chunk_size_mb: float = 8.0,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> List[str]:
        """Split audio file into smaller chunks for processing.

        Args:
            input_file: Path to input audio file
            chunk_size_mb: Target size for chunks in MB (default 8.0)
            log_callback: Optional callback function for logging

        Returns:
            List of paths to audio chunk files
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        try:
            # Load the audio file
            audio = AudioSegment.from_file(input_file)
            duration_ms = len(audio)
            file_size_mb = os.path.getsize(input_file) / (1024 * 1024)

            # Calculate chunk duration based on target size
            chunk_duration_ms = int(
                (duration_ms * chunk_size_mb) / file_size_mb)

            # Ensure minimum chunk duration (10 seconds)
            min_chunk_duration_ms = 10 * 1000
            chunk_duration_ms = max(chunk_duration_ms, min_chunk_duration_ms)

            log(f"Splitting {file_size_mb:.1f}MB file into ~{chunk_size_mb:.1f}MB chunks")
            log(f"Chunk duration: {chunk_duration_ms / 1000:.1f} seconds")

            chunks = []
            chunk_count = 0

            for start_ms in range(0, duration_ms, chunk_duration_ms):
                end_ms = min(start_ms + chunk_duration_ms, duration_ms)
                chunk = audio[start_ms:end_ms]

                # Create temporary file for chunk
                temp_dir = tempfile.gettempdir()
                chunk_filename = f"chunk_{chunk_count:03d}_{os.path.basename(input_file)}"
                chunk_path = os.path.join(temp_dir, chunk_filename)

                # Export chunk
                chunk.export(chunk_path, format="wav")
                chunks.append(chunk_path)

                chunk_size_mb_actual = os.path.getsize(
                    chunk_path) / (1024 * 1024)
                log(f"Created chunk {chunk_count + 1}: {chunk_size_mb_actual:.1f}MB")

                chunk_count += 1

            log(f"Split into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            log(f"Error chunking audio: {e}")
            return []

    def _merge_audio_chunks(
        self,
        chunk_files: List[str],
        output_file: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Merge processed audio chunks back into a single file with crossfading.

        Args:
            chunk_files: List of paths to processed chunk files
            output_file: Path for merged output file
            log_callback: Optional callback function for logging

        Returns:
            True if merge successful, False otherwise
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        try:
            log(f"Merging {len(chunk_files)} chunks with crossfading...")

            # Load all chunks first to validate they're readable
            loaded_chunks = []
            for i, chunk_file in enumerate(chunk_files):
                try:
                    chunk = AudioSegment.from_file(chunk_file)
                    loaded_chunks.append(chunk)
                except Exception as e:
                    log(f"Error loading chunk {i + 1}: {e}")
                    raise Exception(f"Failed to load chunk {i + 1}")

            # Start with first chunk
            merged_audio = loaded_chunks[0]

            # Crossfade duration at chunk boundaries (50ms for smooth transitions)
            crossfade_duration_ms = 50

            # Append remaining chunks with crossfading
            for i in range(1, len(loaded_chunks)):
                chunk = loaded_chunks[i]

                # Apply crossfade at chunk boundary to smooth the transition
                # This prevents clicks and artifacts from denoising boundary effects
                if len(merged_audio) >= crossfade_duration_ms and len(chunk) >= crossfade_duration_ms:
                    # Get tail of merged audio (last 50ms) and head of new chunk (first 50ms)
                    merged_tail = merged_audio[-crossfade_duration_ms:]
                    chunk_head = chunk[:crossfade_duration_ms]
                    chunk_tail = chunk[crossfade_duration_ms:]

                    # Remove last 50ms from merged audio
                    merged_audio = merged_audio[:-crossfade_duration_ms]

                    # Apply crossfade: fade-out on merged tail, fade-in on chunk head
                    crossfaded_section = merged_tail.fade_out(crossfade_duration_ms).overlay(
                        chunk_head.fade_in(crossfade_duration_ms)
                    )

                    # Combine: merged + crossfaded section + rest of chunk
                    merged_audio += crossfaded_section + chunk_tail
                else:
                    # If chunks are too small for crossfading, just concatenate
                    merged_audio += chunk

                log(f"Merged chunk {i + 1}/{len(loaded_chunks)}")

            # Export merged audio
            merged_audio.export(output_file, format="wav")

            merged_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            log(f"Merged audio saved: {os.path.basename(output_file)} ({merged_size_mb:.1f}MB)")

            return True

        except Exception as e:
            log(f"Error merging audio chunks: {e}")
            return False

    def _cleanup_chunks(self, chunk_files: List[str]):
        """Clean up temporary chunk files.

        Args:
            chunk_files: List of chunk file paths to delete
        """
        for chunk_file in chunk_files:
            try:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
            except Exception as e:
                print(
                    f"Warning: Could not remove chunk file {chunk_file}: {e}")

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

        # Check file size - implement chunking for large files
        file_size_mb = os.path.getsize(input_file) / (1024 * 1024)

        if file_size_mb > 10:
            log(f"Large file detected: {file_size_mb:.1f}MB. Using chunked processing...")
            return self._denoise_large_file(input_file, output_file, auto_scale, log_callback)

        log(
            f"Starting audio denoising for: {os.path.basename(input_file)} ({file_size_mb:.1f}MB)")

        try:
            # Process the audio file
            self.denoiser.process_audio_file(
                input_file,
                output_file,
                auto_scale=auto_scale
            )

            if os.path.exists(output_file):
                output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                log(
                    f"✓ Audio denoising complete: {os.path.basename(output_file)} ({output_size_mb:.1f}MB)")
                return output_file
            else:
                log("Denoising failed, using original audio")
                return input_file

        except Exception as e:
            log(f"Error during denoising: {e}")
            log("Falling back to original audio")
            return input_file

    def _denoise_large_file(
        self,
        input_file: str,
        output_file: str,
        auto_scale: bool = True,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Denoise a large audio file using chunking strategy.

        Args:
            input_file: Path to input audio file
            output_file: Path for denoised output
            auto_scale: Whether to auto-scale the audio
            log_callback: Optional callback function for logging

        Returns:
            Path to denoised audio file, or original file if chunking fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
        log(f"Processing large file ({file_size_mb:.1f}MB) with chunked denoising...")

        # Step 1: Split audio into chunks
        chunk_files = self._chunk_audio(
            input_file, chunk_size_mb=8.0, log_callback=log_callback)

        if not chunk_files:
            log("Failed to chunk audio, falling back to original file")
            return input_file

        try:
            # Step 2: Process each chunk
            processed_chunks = []

            for i, chunk_file in enumerate(chunk_files):
                log(f"Processing chunk {i + 1}/{len(chunk_files)}...")

                # Generate output path for processed chunk
                chunk_output = chunk_file.replace(".wav", "_denoised.wav")

                try:
                    # Process the chunk
                    self.denoiser.process_audio_file(
                        chunk_file,
                        chunk_output,
                        auto_scale=auto_scale
                    )

                    if os.path.exists(chunk_output):
                        processed_chunks.append(chunk_output)
                        chunk_size = os.path.getsize(
                            chunk_output) / (1024 * 1024)
                        log(f"✓ Chunk {i + 1} processed: {chunk_size:.1f}MB")
                    else:
                        log(f"Warning: Chunk {i + 1} processing failed, using original chunk")
                        processed_chunks.append(chunk_file)

                except Exception as e:
                    log(f"Error processing chunk {i + 1}: {e}, using original chunk")
                    processed_chunks.append(chunk_file)

            # Step 3: Merge processed chunks
            if self._merge_audio_chunks(processed_chunks, output_file, log_callback):
                output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                log(
                    f"✓ Large file denoising complete: {os.path.basename(output_file)} ({output_size_mb:.1f}MB)")

                # Step 4: Cleanup temporary files
                log("Cleaning up temporary chunk files...")
                # Clean up both original chunks and processed chunks
                all_temp_chunks = set(chunk_files + processed_chunks)
                self._cleanup_chunks(list(all_temp_chunks))

                return output_file
            else:
                log("Failed to merge chunks, falling back to original file")
                # Clean up both original chunks and processed chunks when merge fails
                all_temp_chunks = set(chunk_files + processed_chunks)
                self._cleanup_chunks(list(all_temp_chunks))
                return input_file

        except Exception as e:
            log(f"Error during chunked denoising: {e}")
            log("Cleaning up and falling back to original file")
            # Clean up all temporary files on exception
            all_temp_chunks = set(
                chunk_files + [pc for pc in processed_chunks if pc])
            self._cleanup_chunks(list(all_temp_chunks))
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
