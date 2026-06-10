"""Unit tests for long-form transcription pipeline helpers.

These tests are backend-agnostic and do not require downloading Whisper models.
"""

import tempfile
import unittest

from features.whisper_transcriber import WhisperTranscriber


def _make_transcriber_without_init() -> WhisperTranscriber:
    """Create a transcriber instance without backend initialization."""
    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    return transcriber


class TestTranscriptionLongFormPipeline(unittest.TestCase):
    def test_merge_overlapped_segments_drops_full_duplicates(self):
        transcriber = _make_transcriber_without_init()

        existing = [
            {"start": 0.0, "end": 5.0, "text": "hola"},
            {"start": 5.0, "end": 10.0, "text": "mundo"},
        ]
        new = [
            # Fully duplicated by overlap window
            {"start": 8.0, "end": 9.8, "text": "mundo"},
            # New content after overlap
            {"start": 10.0, "end": 14.0, "text": "nuevo"},
        ]

        merged = transcriber._merge_overlapped_segments(existing, new)

        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[-1]["text"], "nuevo")
        self.assertEqual(merged[-1]["start"], 10.0)

    def test_merge_overlapped_segments_clips_partial_boundary_overlap(self):
        transcriber = _make_transcriber_without_init()

        existing = [{"start": 0.0, "end": 10.0, "text": "segment-a"}]
        new = [{"start": 9.5, "end": 12.0, "text": "segment-b"}]

        merged = transcriber._merge_overlapped_segments(existing, new)

        self.assertEqual(len(merged), 2)
        # start should be clipped to the last known end
        self.assertEqual(merged[-1]["start"], 10.0)
        self.assertEqual(merged[-1]["end"], 12.0)

    def test_segments_to_text_joins_clean_text_only(self):
        transcriber = _make_transcriber_without_init()

        segments = [
            {"text": "  hola  "},
            {"text": ""},
            {"text": "mundo"},
        ]

        self.assertEqual(transcriber._segments_to_text(segments), "hola mundo")

    def test_transcribe_with_timestamps_uses_generated_output_path(self):
        transcriber = _make_transcriber_without_init()

        with tempfile.TemporaryDirectory() as temp_dir:
            generated_output = f"{temp_dir}/episode_transcript.txt"
            with open(generated_output, "w", encoding="utf-8") as output_file:
                output_file.write("contenido")

            # Monkeypatch instance method
            transcriber.transcribe = lambda *args, **kwargs: {
                "output_file": generated_output,
                "segments": [{"start": 0.0, "end": 1.0, "text": "hola"}],
            }

            timestamped = transcriber.transcribe_with_timestamps(
                audio_file="dummy.wav",
                output_file=None,
            )

            self.assertIsNotNone(timestamped)
            self.assertTrue(timestamped.endswith("_timestamped.txt"))


if __name__ == "__main__":
    unittest.main()
