# NTN Podcast Creator — Feature Improvements Plan

**Date:** February 7, 2026
**Status:** Proposed

---

## Current State Summary

The app is a Gradio 6.0 web tool that combines voice recordings with intro/outro audio and background music into a polished podcast episode. It supports AI denoising (3 methods), LUFS normalization, multi-file upload with ordering, timeline preview, templates, and an RSS-based name suggester.

**Two major advertised features are dead code:**
- **Whisper transcription** — code exists in `features/whisper_transcriber.py` but is never called from the pipeline and has no UI controls (there's a TODO at ~line 2887 in `app.py`)
- **Adobe audio enhancement** — code exists in `features/adobe_audio_enhancer.py` but is never invoked from `create_podcast()` in `features/audio_processor.py`

---

## Proposed Improvements & Features

### Tier 1 — Fix What's Broken (High Impact, Moderate Effort)

#### 1. Wire up Whisper transcription into the pipeline and UI
- Add `generate_transcript` checkbox and `whisper_model` dropdown to the Create Podcast tab's Processing Options in `app.py`
- Add corresponding `get_generate_transcript()` / `set_whisper_model()` methods to `features/config_manager.py` (currently orphaned keys in config.json)
- Call `WhisperTranscriber.transcribe_audio()` from `create_podcast()` in `features/audio_processor.py` after final export, returning the transcript path instead of `None`
- Display transcript text in the UI after creation completes

#### 2. Wire up Adobe audio enhancement into the pipeline
- Add the enhancement step to `create_podcast()` between denoising and mixing, guarded by the existing `enhance_voice` config key
- Add a UI checkbox to enable/disable it, with proper error handling (fallback to non-enhanced audio on failure)
- Remove the orphaned reference to a non-existent "✨ Adobe Enhance" tab in the Tips section (`app.py` line ~2564)

#### 3. Fix orphaned config keys
- Align `_default_config()` in `features/config_manager.py` with the keys already present in `core/config.json`: `generate_transcript`, `whisper_model`, `enhance_voice`
- Fix failing unit test `test_whisper_settings` in `tests/test_units.py` that calls nonexistent methods

---

### Tier 2 — Audio Quality Improvements (High Impact, Moderate Effort)

#### 4. MP3 bitrate and format selection
- Let users choose output bitrate (128 / 192 / 256 / 320 kbps) and format (MP3 / WAV / FLAC)
- Currently pydub exports at its default bitrate with no user control
- Add config keys and a dropdown in the Settings tab

#### 5. Crossfade duration customization
- The 1-second overlap between intro→voice and voice→outro is hardcoded in `features/audio_processor.py`
- Expose as a slider (100ms–3000ms) in Processing Options
- Different durations for intro-voice vs voice-outro transitions

#### 6. Audio compression / dynamic range control
- Add an optional compressor/limiter stage after mixing and before LUFS normalization
- Prevents clipping and ensures consistent loudness across segments (voice vs. music)
- Can be implemented with pydub's `compress_dynamic_range()` or FFmpeg's `acompressor` filter

#### 7. High-pass filter / de-essing
- Add optional high-pass filter (e.g., 80Hz cutoff) to remove rumble/handling noise — common in podcast production
- Could use FFmpeg's `highpass` filter, minimal code addition
- De-essing (reducing harsh sibilants) via FFmpeg's `adeclick` or a sidechain approach

#### 8. A/B comparison for denoising
- After denoising, show both original and denoised audio players side-by-side so users can compare quality before proceeding to mix
- Currently denoised audio is returned but there's no easy comparison interface

---

### Tier 3 — AI-Powered Content Features (High Impact, Higher Effort)

#### 9. AI-generated show notes from transcript
- After Whisper transcription, pass the text to an LLM (OpenAI API, local model, or Ollama) to generate:
  - Episode summary (1-2 paragraphs)
  - Key topics / bullet points
  - Social media post draft
- This is a natural extension once transcription is wired up

#### 10. Chapter markers / timestamps
- Use Whisper's segment-level timestamps to detect topic boundaries
- Generate podcast chapter markers in standard formats (ID3 chapters for MP3, or a text file)
- Users could also manually add chapter names via a simple UI table

#### 11. Speaker diarization
- Integrate `pyannote-audio` or `whisperx` for speaker identification
- Label transcript segments by speaker (Speaker 1, Speaker 2, etc.)
- Essential for multi-host podcasts — "No Tiene Nombre" appears to be a multi-person show

#### 12. SRT/VTT subtitle export
- Extend `WhisperTranscriber` to output subtitles in SRT and VTT formats alongside plain text
- Useful for video podcasts or accessibility

---

### Tier 4 — UX & Workflow Improvements (Medium Impact, Low-Medium Effort)

#### 13. Preview before export
- Generate a low-quality preview of the mixed podcast (e.g., first 30 seconds) before committing to the full export
- Lets users catch volume/overlap issues without waiting for the complete pipeline

#### 14. Background music playlist control
- Currently background music is **randomly selected** from available tracks
- Add drag-and-drop ordering, allow users to choose which tracks play and in what sequence
- Support setting start/end points per track

#### 15. Volume controls beyond 50%
- Both global and per-track volumes are capped at 50% (hardcoded in `update_volume()` and `set_track_volume()`)
- Raise to at least 100% with a visual warning above certain thresholds

#### 16. Waveform visualization
- Show audio waveforms for uploaded voice, intro, outro, and the final output
- Can use a JavaScript waveform library (e.g., WaveSurfer.js) embedded in Gradio HTML components
- Much more informative than the current box-based timeline chart

#### 17. Undo / history for destructive operations
- Track state changes (file deletions, track removals) and allow undo
- At minimum, add a confirmation dialog before destructive actions

#### 18. Clean up temp files
- `generate_volume_preview()` creates temp files with `delete=False` that are never cleaned up
- Add cleanup in a `finally` block or use a temp directory that's swept periodically

---

### Tier 5 — Architecture & Code Quality (Medium Impact, Ongoing)

#### 19. Break up `app.py` (~2980 lines)
- Extract into modules: `ui/create_tab.py`, `ui/settings_tab.py`, `ui/denoiser_tab.py`, `ui/handlers.py`, `ui/components.py`
- The monolithic file makes navigation and testing difficult

#### 20. Remove dead / duplicate code
- `create_podcast_handler` (non-progress version) is defined but never wired to the UI — remove it
- Multiple implementation summary markdown files at root level (`IMPLEMENTATION_COMPLETE.md`, `IMPLEMENTATION_COMPLETE_PREVIOUS.md`, `MULTI_FILE_UPLOAD_SUMMARY.md`, `TEMPLATE_IMPLEMENTATION_SUMMARY.md`) clutter the repo — move to `docs/` or remove

#### 21. Add proper error handling per pipeline stage
- `create_podcast()` lacks try/catch around individual stages — a background file loading failure crashes the whole pipeline
- Each stage should be wrapped with fallback behavior per the project's stated philosophy

#### 22. Integration test coverage
- The unit tests for Whisper settings reference methods that don't exist
- No integration tests for the actual pipeline end-to-end
- Add tests for the full `create_podcast()` flow with mock audio files

---

## Verification Approach

For any implemented features:
- **Syntax check**: `python -m py_compile app.py` and all modified files
- **Unit tests**: `python tests/test_ui_core.py` (7 core tests)
- **Integration tests**: `python -m pytest tests/ -v`
- **Manual test**: Run `python app.py`, upload test file from `audios/test/`, verify pipeline completes
- **Audio quality**: Listen to output, compare with/without new features

---

## Prioritized Recommendation

If starting now, recommended order:

| Priority | Item | Rationale |
|----------|------|-----------|
| 1st | Items 1–3 (fix broken features) | Already built but disconnected — highest ROI |
| 2nd | Items 4–5 (bitrate + crossfade control) | Quick wins for audio quality |
| 3rd | Item 9 (AI show notes) | Differentiating feature that builds on transcription |
| 4th | Item 13 (preview before export) | Saves significant user time |
| 5th | Item 19 (break up app.py) | Enables faster development of everything else |
