"""Audio transcription with long-form support.

Implements a robust pipeline for long audio:
- VAD filtering (when faster-whisper backend is available)
- Chunking with overlap
- Timestamp-preserving merge/stitch
- Graceful fallback to openai-whisper
"""

import os
import shutil
import tempfile
from typing import Optional, Callable, Dict, Any, List, Tuple

from pydub import AudioSegment


class WhisperTranscriber:
    """Handles audio transcription using Whisper."""

    def __init__(
        self,
        model_size: str = "base",
        chunk_length_s: int = 30,
        chunk_overlap_s: int = 2,
        long_form_threshold_s: int = 120,
        vad_filter: bool = True
    ):
        """Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            chunk_length_s: Chunk length (seconds) for long-form chunking
            chunk_overlap_s: Overlap (seconds) between chunks
            long_form_threshold_s: Audio duration threshold for long-form mode
            vad_filter: Enable VAD filtering when backend supports it
        """
        self.model = None
        self.model_size = model_size
        self.chunk_length_s = max(10, int(chunk_length_s))
        self.chunk_overlap_s = max(0, int(chunk_overlap_s))
        self.long_form_threshold_s = max(30, int(long_form_threshold_s))
        self.vad_filter = bool(vad_filter)

        self.available = False
        self.backend = None
        self._initialize_whisper()

    def _initialize_whisper(self):
        """Initialize transcription backend if available.

        Backend preference:
        1) faster-whisper (optimized, VAD support)
        2) openai-whisper (fallback)
        """
        # Preferred: faster-whisper
        try:
            from faster_whisper import WhisperModel
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            self.model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type
            )
            self.backend = "faster-whisper"
            self.available = True
            return
        except ImportError:
            pass
        except Exception as e:
            print(f"Warning: Could not initialize faster-whisper: {e}")

        # Fallback: openai-whisper
        try:
            import whisper
            self.model = whisper.load_model(self.model_size)
            self.backend = "openai-whisper"
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

    def _get_audio_duration_s(self, audio_file: str) -> float:
        """Return audio duration in seconds, or 0 on failure."""
        try:
            audio = AudioSegment.from_file(audio_file)
            return len(audio) / 1000.0
        except Exception:
            return 0.0

    def _build_overlapping_chunks(
        self,
        audio_file: str,
        chunk_length_s: int,
        overlap_s: int
    ) -> Tuple[List[Tuple[str, float, float]], str]:
        """Create overlapping chunk files and return metadata.

        Returns:
            (chunks, temp_dir) where chunks is list of
            (chunk_path, chunk_start_s, chunk_end_s)
        """
        audio = AudioSegment.from_file(audio_file)
        duration_ms = len(audio)

        chunk_ms = int(max(10, chunk_length_s) * 1000)
        overlap_ms = int(max(0, overlap_s) * 1000)
        step_ms = max(1000, chunk_ms - overlap_ms)

        temp_dir = tempfile.mkdtemp(prefix="ntn_transcribe_chunks_")
        chunks: List[Tuple[str, float, float]] = []

        index = 0
        start_ms = 0
        while start_ms < duration_ms:
            end_ms = min(start_ms + chunk_ms, duration_ms)
            chunk = audio[start_ms:end_ms]

            chunk_path = os.path.join(temp_dir, f"chunk_{index:04d}.wav")
            chunk.export(chunk_path, format="wav")

            chunks.append((chunk_path, start_ms / 1000.0, end_ms / 1000.0))

            if end_ms >= duration_ms:
                break

            start_ms += step_ms
            index += 1

        return chunks, temp_dir

    def _normalize_segment(
        self,
        segment: Any,
        start_offset_s: float = 0.0
    ) -> Dict[str, Any]:
        """Normalize backend segment object to common dictionary format."""
        if isinstance(segment, dict):
            start = float(segment.get("start", 0.0) or 0.0)
            end = float(segment.get("end", 0.0) or 0.0)
            text = str(segment.get("text", "") or "")
            raw_words = segment.get("words", []) or []
        else:
            start = float(getattr(segment, "start", 0.0) or 0.0)
            end = float(getattr(segment, "end", 0.0) or 0.0)
            text = str(getattr(segment, "text", "") or "")
            raw_words = getattr(segment, "words", []) or []

        words = []
        for word in raw_words:
            if isinstance(word, dict):
                w_start = word.get("start")
                w_end = word.get("end")
                w_text = str(word.get("word", "") or "")
            else:
                w_start = getattr(word, "start", None)
                w_end = getattr(word, "end", None)
                w_text = str(getattr(word, "word", "") or "")

            if w_start is None or w_end is None:
                continue

            words.append({
                "start": float(w_start) + start_offset_s,
                "end": float(w_end) + start_offset_s,
                "word": w_text,
            })

        return {
            "start": start + start_offset_s,
            "end": end + start_offset_s,
            "text": text,
            "words": words,
        }

    def _merge_overlapped_segments(
        self,
        existing_segments: List[Dict[str, Any]],
        new_segments: List[Dict[str, Any]],
        dedupe_tolerance_s: float = 0.15
    ) -> List[Dict[str, Any]]:
        """Merge chunk segments while deduplicating overlap region content."""
        if not existing_segments:
            return list(new_segments)

        merged = list(existing_segments)
        last_end = float(merged[-1].get("end", 0.0) or 0.0)

        for segment in new_segments:
            start = float(segment.get("start", 0.0) or 0.0)
            end = float(segment.get("end", 0.0) or 0.0)
            text = str(segment.get("text", "") or "").strip()

            if not text:
                continue

            # Fully inside already merged timeline (duplicate from overlap)
            if end <= (last_end + dedupe_tolerance_s):
                continue

            # Partially overlapping boundary: clip start forward
            if start < last_end:
                segment = dict(segment)
                segment["start"] = last_end

            merged.append(segment)
            last_end = float(segment.get("end", last_end) or last_end)

        return merged

    def _segments_to_text(self, segments: List[Dict[str, Any]]) -> str:
        """Join segment texts into a full transcript string."""
        parts = []
        for segment in segments:
            text = str(segment.get("text", "") or "").strip()
            if text:
                parts.append(text)
        return " ".join(parts).strip()

    def _transcribe_with_faster_whisper(
        self,
        audio_file: str,
        language: Optional[str],
        task: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """Transcribe with faster-whisper, using chunk+overlap for long-form audio."""
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        duration_s = self._get_audio_duration_s(audio_file)
        long_form_mode = duration_s >= self.long_form_threshold_s

        base_kwargs: Dict[str, Any] = {
            "task": task,
            "word_timestamps": True,
            "condition_on_previous_text": True,
        }

        if language:
            base_kwargs["language"] = language

        if self.vad_filter:
            base_kwargs["vad_filter"] = True

        # Short/regular path: let backend handle full audio directly
        if not long_form_mode:
            segments_iter, info = self.model.transcribe(
                audio_file, **base_kwargs)
            segments = [self._normalize_segment(s) for s in segments_iter]

            return {
                "text": self._segments_to_text(segments),
                "segments": segments,
                "language": getattr(info, "language", language or "unknown"),
            }

        # Long-form path: chunk with overlap + stitch
        log(
            f"Long-form transcription enabled ({duration_s:.1f}s). "
            f"Chunking into {self.chunk_length_s}s windows with {self.chunk_overlap_s}s overlap..."
        )

        chunks = []
        temp_dir = None
        try:
            chunks, temp_dir = self._build_overlapping_chunks(
                audio_file,
                self.chunk_length_s,
                self.chunk_overlap_s
            )

            all_segments: List[Dict[str, Any]] = []
            detected_language = None
            rolling_prompt = ""

            for index, (chunk_path, chunk_start_s, _) in enumerate(chunks, 1):
                chunk_kwargs = dict(base_kwargs)

                # Carry context between chunks to improve continuity
                if rolling_prompt:
                    chunk_kwargs["initial_prompt"] = rolling_prompt[-500:]

                log(f"Transcribing chunk {index}/{len(chunks)}...")
                chunk_segments_iter, info = self.model.transcribe(
                    chunk_path,
                    **chunk_kwargs
                )

                normalized_chunk_segments = [
                    self._normalize_segment(
                        segment, start_offset_s=chunk_start_s)
                    for segment in chunk_segments_iter
                ]

                all_segments = self._merge_overlapped_segments(
                    all_segments,
                    normalized_chunk_segments,
                    dedupe_tolerance_s=0.15
                )

                chunk_text = self._segments_to_text(normalized_chunk_segments)
                if chunk_text:
                    rolling_prompt = f"{rolling_prompt} {chunk_text}".strip()

                if detected_language is None:
                    detected_language = getattr(info, "language", None)

            return {
                "text": self._segments_to_text(all_segments),
                "segments": all_segments,
                "language": detected_language or language or "unknown",
            }

        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    def _transcribe_with_openai_whisper(
        self,
        audio_file: str,
        language: Optional[str],
        task: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """Transcribe with openai-whisper fallback."""
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        options: Dict[str, Any] = {
            "task": task,
            "word_timestamps": True,
            "condition_on_previous_text": True,
            "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
            "compression_ratio_threshold": 1.35,
            "logprob_threshold": -1.0,
            "no_speech_threshold": 0.6,
        }
        if language:
            options["language"] = language

        result = self.model.transcribe(audio_file, **options)

        normalized_segments: List[Dict[str, Any]] = []
        for segment in result.get("segments", []) or []:
            normalized_segments.append(self._normalize_segment(segment))

        log("OpenAI Whisper transcription completed.")

        return {
            "text": result.get("text", self._segments_to_text(normalized_segments)),
            "segments": normalized_segments,
            "language": result.get("language", language or "unknown"),
        }

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
            duration_s = self._get_audio_duration_s(audio_file)
            mode = "long-form" if duration_s >= self.long_form_threshold_s else "standard"
            log(
                f"Transcribing audio with {self.backend or 'whisper'} "
                f"({self.model_size} model, {mode} mode): {os.path.basename(audio_file)}"
            )

            if self.backend == "faster-whisper":
                result = self._transcribe_with_faster_whisper(
                    audio_file=audio_file,
                    language=language,
                    task=task,
                    log_callback=log_callback
                )
            else:
                result = self._transcribe_with_openai_whisper(
                    audio_file=audio_file,
                    language=language,
                    task=task,
                    log_callback=log_callback
                )

            if not result:
                return None

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

        result = self.transcribe(
            audio_file, output_file, log_callback=log_callback)

        resolved_output_file = None
        if result:
            resolved_output_file = result.get("output_file") or output_file

        if result and resolved_output_file:
            # Generate timestamped version with safe extension replacement
            base_name = os.path.splitext(resolved_output_file)[0]
            timestamped_file = f"{base_name}_timestamped.txt"

            try:
                with open(timestamped_file, 'w', encoding='utf-8') as f:
                    for segment in result.get("segments", []):
                        start = segment.get("start", 0)
                        end = segment.get("end", 0)
                        text = segment.get("text", "")
                        f.write(f"[{start:.2f}s - {end:.2f}s] {text}\n")

                log(
                    f"✓ Timestamped transcript saved: {os.path.basename(timestamped_file)}")
                return timestamped_file

            except Exception as e:
                log(f"Error creating timestamped transcript: {e}")
                return resolved_output_file

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
