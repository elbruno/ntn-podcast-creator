# NTN Podcast Creator - AI Agent Instructions

## Project Overview
NTN Podcast Creator is a Gradio-based web application for professional podcast production with AI-powered audio processing. It combines voice recordings with intro/outro audio and background music, applying advanced processing (denoising, enhancement, LUFS normalization, transcription).

**Key Architecture**: 3-tier (Gradio UI → Business Logic → Data Layer)
**Tech Stack**: Python 3.8+, Gradio 6.0.0, pydub, PyTorch, FFmpeg
**Primary User**: "No Tiene Nombre" podcast production workflow

---

## Critical Knowledge

### 1. Application Entry & UI Structure (app.py)
- **Main file**: `app.py` (~2400 lines) - Gradio UI orchestration
- **Pattern**: Generator-based event handlers with `yield` statements
- **Key constraint**: Gradio 6.0 specific - NO `visible` parameter, NO `gr.update()`, use direct HTML with inline `display: none/block` styles
- **Example**: Progress bar yields 7 values exactly: `(status, audio, denoised, transcript, console, progress_html, bottom_html)`
- **Global state**: `console_log = []` for logging, UI components access it directly
- **Important dirs to create**: `uploads/`, `outputs/`, `audios/intro_audio/`, `audios/outro_audio/`, `audios/background_music/`

### 2. Audio Processing Pipeline (features/audio_processor.py)
The core workflow orchestrates 5 optional stages:
```
Input Audio → [Denoise] → [Enhance] → [Trim Silence] → [Mix] → [Normalize] → [Transcribe]
```
- **Denoising**: 3 methods via `denoise_audio_checkbox` + `denoise_method_dropdown`
  - `audio_denoiser`: AI-based via PyTorch (auto-chunks files >8MB)
  - `spectral`: Fast spectral gating (uses first 0.5s as noise profile)
  - `rnnoise`: FFmpeg RNNoise (when available)
- **Enhancement**: Browser automation via Playwright (`adobe_audio_enhancer.py`)
- **Mixing**: pydub `AudioSegment` with 1-second overlaps between intro/voice/outro
- **Normalization**: FFmpeg 2-pass `loudnorm` (target -16 LUFS for podcasts)
- **Transcription**: Parallel `whisper_transcriber.py` with 99+ languages

### 3. Configuration Persistence (features/config_manager.py)
- **Location**: `core/config.json`
- **Pattern**: Single `ConfigManager` instance shared across app
- **Auto-load**: `load_default_audio_files()` scans `audios/` folders at startup
- **Track volumes**: Dict mapping per-track volumes separately from master volume
- **Settings saved**: Last output name, all feature toggles, model choices (e.g., `whisper_model: "base"`)

### 4. Gradio 6.0 Compatibility Issues & Workarounds
**What breaks**:
- `visible=False` parameter → Use inline CSS `display: none` in HTML value instead
- `gr.update(visible=True)` → Yield HTML with `display: block` inline style
- `theme=gr.themes.Default()` → Removed completely

**Pattern**: HTML components with controlled display
```python
# Initialize with empty display
html_component = gr.HTML(value='<div style="display: none;"></div>')
# In event handler, yield full HTML (generator)
yield "status", ..., '<div style="display: block; ...">Progress</div>'
```

### 5. Logging System
- **Global**: `console_log = []` (list of strings)
- **Functions**: `log_message(text)`, `get_console_log()`, `get_bottom_console_html()`
- **Real-time**: Logs displayed in bottom console during processing (last 10 entries)
- **Pattern**: Handlers pass `log_callback=threaded_log_callback` to audio processor

### 6. Error Handling Philosophy
**Core Principle**: Always move forward with available resources. Failed optional features should never stop the pipeline.

**Error Strategy by Feature**:
- **Denoising failure**: Log warning, use original audio, continue
- **Adobe enhancement failure**: Log warning, use non-enhanced audio, continue
- **Transcription failure**: Log error in console, generate podcast without transcript, continue
- **LUFS normalization failure**: Log warning, export without normalization, continue
- **Critical failures** (stop pipeline):
  - Voice file missing/invalid
  - Audio mixing failure
  - Final export/write failure
  - Output file cannot be created

**Logging Pattern**: Every failure must produce a console log entry explaining what happened and what fallback was used. Users should always see "Continue anyway? Yes" behavior, not error screens.

### 7. Transcription Workflow (Whisper Integration)
**Default State**:
- Transcription is **OPTIONAL** and **DISABLED by default**
- User must explicitly enable via `generate_transcript` checkbox

**Language Detection**:
- Auto-detected from audio (Whisper's automatic language detection)
- User cannot override in current implementation
- Detection happens during transcription process

**Whisper Model Selection** (`whisper_model` config key):
- **base** (default): Fast, ~1-2 minutes for 10-20 min audio, medium quality, ~1GB memory
- **small**: ~2-3 minutes for 10-20 min audio, good quality, ~2GB memory
- **medium**: ~4-5 minutes for 10-20 min audio, high quality, ~5GB memory

**Failure Behavior**:
- Transcription error logged to console
- Podcast creation continues without transcript
- No transcript file generated if process fails
- User sees notification in console: "Transcription failed: [error details]. Continuing without transcript."

**Implementation**: `features/whisper_transcriber.py` with parallel processing support

### 8. Adobe Enhancement (Browser Automation)
**Setup Requirements**:
- Adobe credentials stored in `.env` file (not in code)
- Requires valid Adobe Creative Cloud account
- Browser automation via Playwright (headless Chrome/Chromium)
- Credentials not hardcoded; environment-based for security

**Success Rate**:
- No guaranteed success rate documented
- Browser automation is inherently fragile (network, auth timeouts, UI changes)
- Treat as "best effort" feature

**Failure Behavior**:
- Enhancement fails → Log error to console
- Pipeline continues with original (non-enhanced) audio
- User sees notification: "Adobe Enhancement failed. Using original audio."
- No retry mechanism; one attempt per podcast creation

**Known Format Support**:
- MP3, WAV, M4A tested and supported
- Other formats may work (pydub supports many formats)
- Browser automation specific to Audition interface (may change with Adobe updates)

**Implementation**: `features/adobe_audio_enhancer.py` with Playwright automation

### 9. Performance Characteristics
**Target Audio Length**: 10-20 minute podcast voice recordings (optimal range)

**Processing Times per Feature** (estimated for 15-minute voice recording):
- **Denoising (audio_denoiser - AI method)**: 3-5 minutes (depends on GPU availability)
- **Denoising (spectral method)**: 20-30 seconds (fast)
- **Denoising (rnnoise method)**: 1-2 minutes (if FFmpeg available)
- **Adobe Enhancement**: 2-4 minutes (network/browser dependent, highly variable)
- **Trim Silence**: <5 seconds
- **Mixing (intro/outro/background)**: 10-30 seconds
- **LUFS Normalization**: 1-2 minutes (2-pass FFmpeg process)
- **Whisper Transcription (base)**: 2-3 minutes (15-min audio)
- **Total pipeline** (all features enabled): ~12-20 minutes

**Resource Requirements**:
- **GPU**: Optional but recommended (AI denoising 3x faster with GPU)
  - Without GPU: Uses CPU, slower but functional
  - With GPU: NVIDIA CUDA recommended, ~6GB VRAM for base denoiser
- **Memory**: 2-4GB RAM minimum for typical podcast processing
- **Disk**: 500MB-1GB temporary space for chunking and processing
- **Input file size**: Tested up to 18MB; auto-chunks >8MB via `audio_denoiser_processor.py`

**Concurrency**:
- Current implementation: Single podcast at a time (UI-based)
- Multiple concurrent uploads via UI will be queued by Gradio
- No built-in multi-processing for different podcasts simultaneously

**Temp Disk Usage**:
- Auto-chunks create temporary files (~8MB each)
- Cleaned up after merge
- Total temp space ≤ 2x input file size during peak processing

**Performance Testing Scenarios**:
- 10-minute voice recording (minimum)
- 20-minute voice recording (maximum typical)
- Large input (test with 251121-ntn443-Recording.m4a: 18MB)
- All denoising methods (audio_denoiser, spectral, rnnoise)
- Adobe enhancement enabled/disabled
- Transcription enabled/disabled
- GPU availability (test with and without)

---

## Extension Points & Future Development

### Current App Feature Status
**All features currently in app** - No "Phase 2" or "Phase 3" future work. The following are all implemented:
- Denoising (3 methods: AI, spectral, RNNoise)
- Adobe audio enhancement
- Background music mixing
- LUFS normalization
- Whisper transcription
- MIDI support (if implemented)
- Multiple audio format support

**Future Development Philosophy**: Add new features as opt-in toggles (like transcription), always maintaining graceful degradation.

### Adding a New Processing Stage

**Pattern**:
1. Create new processor file: `features/my_processor.py`
2. Implement processor class with standard interface:
   ```python
   class MyProcessor:
       def __init__(self, log_callback=None):
           self.log_callback = log_callback or (lambda x: None)

       def process(self, input_file, **kwargs):
           # Process audio, log progress
           self.log_callback(f"Processing: {input_file}")
           return output_file
   ```
3. Add config toggle to `config_manager._default_config()`:
   ```python
   "enable_my_feature": False,
   "my_feature_setting": "default_value"
   ```
4. Integrate into `audio_processor.create_podcast()`:
   - Add conditional check: `if config.get("enable_my_feature"):`
   - Call processor with proper error handling (try/except, log, continue)
5. Add UI checkbox/dropdown to `app.py` in appropriate section
6. Save feature config via `ConfigManager.set()`
7. Test with `audios/test/251121-ntn443-Recording.m4a`

### Adding a New Denoising Method

**Pattern**:
1. Create processor: `features/my_denoiser.py`
2. Implement `denoise()` function matching interface in `audio_processor.py`
3. Add method name to `denoise_method_dropdown` choices in `app.py`
4. Update `audio_processor.py` switch statement:
   ```python
   elif denoise_method == "my_method":
       from features.my_denoiser import denoise
       processed_audio = denoise(audio_file, ...)
   ```
5. Add to config defaults if needed
6. Large files: Implement chunking pattern from `audio_denoiser_processor.py` for files >8MB
7. Test with all file sizes in `audios/test/`

### Architecture for Common Extensions

**Multi-track support**:
- `audio_processor.create_looped_background()` already supports multiple tracks
- Each track has independent volume control via `track_volumes` dict
- Extend by adding new track types (e.g., parallel voice tracks, secondary narrators)

**Format support**:
- All formats supported by pydub work automatically
- Test new formats by uploading via UI
- FFmpeg handles actual conversion

**Language/locale support**:
- Whisper auto-detects languages (99+ supported)
- UI text strings in `app.py` can be internationalized (currently English only)
- No i18n infrastructure built yet

---

## Developer Workflows

### Quick Start (Dev Container)
```bash
# Already configured via .devcontainer/devcontainer.json
# FFmpeg + requirements pre-installed, port 7860 forwarded
python app.py
# Access: http://localhost:7860
```

### Running Tests
```bash
# Quick core tests (7/7 tests, ~60 seconds)
python tests/test_ui_core.py

# Full integration tests (requires pytest)
pip install pytest
python -m pytest tests/test_ui_podcast_creation.py -v -s
```

### Syntax Validation
```bash
python -m py_compile app.py  # Check for Python errors
```

### Testing with Audio
- Test audio: `audios/test/251121-ntn443-Recording.m4a` (18.1MB - triggers chunking)
- Other formats: Upload any `.m4a`, `.mp3`, `.wav` via UI

---

## Project-Specific Patterns

### Audio Duration Calculation
Always use `AudioSegment` from pydub to get durations:
```python
from pydub import AudioSegment
audio = AudioSegment.from_file(path)
duration_seconds = len(audio) / 1000.0
```

### Generator-Based Event Handlers
Handlers must be generators for progress display:
```python
def handler(..., progress=gr.Progress()):
    progress(0.1, "Starting...")
    yield value1, value2, ...
    progress(0.5, "Mid-point...")
    yield value1, value2, ...
```

### Background Music Building
Multiple tracks combined with per-track volume control:
```python
# audio_processor.create_looped_background(files, duration_ms, volume, track_volumes)
# track_volumes: {'track1.mp3': 5, 'track2.mp3': 8}  # % volumes
```

### Large File Handling (>8MB)
`audio_denoiser_processor.py` auto-chunks files:
- Split into 8MB chunks
- Process each chunk (with error fallback)
- Merge results
- **Note**: Chunk output temporarily stored in memory/temp, cleaned up after merge

### Config Keys (Must Match config_manager._default_config())
```python
# Audio processing toggles
denoise_audio: bool
denoise_method: str  # "audio_denoiser" | "spectral" | "rnnoise"
enhance_audio: bool
normalize_lufs: bool
target_lufs: float  # e.g., -16.0

# Feature toggles
generate_transcript: bool
whisper_model: str  # e.g., "base", "small", "medium"

# UI state
background_volume: int  # 0-100
track_volumes: dict  # per-track volumes
last_output_name: str
```

---

## File Structure Reference

```
app.py                          # Main UI & orchestration (~2400 lines)
features/
  ├── audio_processor.py        # Mixing, trim silence, overlap logic
  ├── config_manager.py         # Config persistence & defaults
  ├── audio_denoiser_processor.py  # AI denoising w/ chunking
  ├── adobe_audio_enhancer.py   # Playwright-based enhancement
  ├── noise_reducer.py          # Spectral gating
  ├── lufs_normalizer.py        # FFmpeg loudnorm wrapper
  └── whisper_transcriber.py    # Parallel transcription
tests/                          # All test files
  ├── test_ui_core.py           # 7 core tests
  ├── test_ui_podcast_creation.py  # Integration tests
  └── README_TESTS.md           # Testing documentation
docs/                           # Technical documentation & guides
  ├── USER_MANUAL.md            # End-user guide with screenshots
  ├── TECHNICAL_IMPLEMENTATION.md  # Architecture & API reference
  ├── DOCKER.md                 # Docker deployment guide
  ├── DOCKER_PUBLISH.md         # Docker image publishing
  ├── AUDIO_DENOISING_IMPLEMENTATION.md  # AI denoising guide
  ├── STRUCTURE_IMPROVEMENTS.md # Project organization docs
  ├── RELEASE_NOTES_CHUNKING.md # Latest features & enhancements
  └── tasks/                    # Task output & progress documents
      ├── ERROR_FIX_SUMMARY.md  # Error fixes & implementations
      ├── FIX_PROGRESS_CONSOLE.md  # Progress bar/console fixes
      ├── TESTING_REPORT.md     # Comprehensive testing report
      ├── FIX_COMPLETE_SUMMARY.md  # Completion summaries
      └── WORK_COMPLETE.md      # Overall work status
audios/
  ├── intro_audio/              # Default intro files
  ├── outro_audio/              # Default outro files
  ├── background_music/         # Background track library
  └── test/                      # Test audio files
outputs/                        # Generated podcasts
uploads/                        # Temporary uploaded files
core/config.json                # Persistent config
README.md                       # Project overview (root)
LICENSE                         # MIT license (root)
```

---

## Common Pitfalls & Workarounds

| Issue | Solution |
|-------|----------|
| Progress bar not showing | Ensure HTML value has `display: block` inline; component initialized with `display: none`; yield exactly 7 values |
| Console log stuck at old messages | Clear global `console_log` at handler start; use `log_message()` consistently |
| Large file fails silently | Check `audio_denoiser_processor.py` error fallback; files >8MB auto-chunked |
| Gradio warnings on yield | Count yield values—must match outputs list exactly (currently 7) |
| Config not persisting | Call `config_manager.save_config()` after any `set()` call |
| File upload path issues | Use `os.path.join()` for cross-platform paths; files saved in `uploads/` |

---

## Quick Reference: Key Functions

**app.py**
- `create_ui()` - Builds entire Gradio interface
- `create_podcast_handler_with_progress()` - Main generator for podcast creation
- `suggest_podcast_name()` - Auto-generates episode name with date
- `log_message()` - Appends to global console log
- `get_console_log()` - Returns console log as string

**config_manager.py**
- `ConfigManager()` - Single instance shared app-wide
- `.get(key)` / `.set(key, value)` - Get/set with auto-save
- `.load_default_audio_files()` - Scans audios/ folders at startup

**audio_processor.py**
- `.create_podcast()` - Main orchestration (handles all stages)
- `.create_looped_background()` - Mix multiple tracks with volumes
- `.trim_silence()` - Remove silence from edges

---

## Questions for AI Agents to Ask

Before making changes:
1. Does this change affect event handler `yield` count or order?
2. Does this require Gradio 6.0 compatibility adjustments?
3. Is this a new config key? Add to `_default_config()` in ConfigManager
4. Does this touch audio processing? Test with `audios/test/251121-ntn443-Recording.m4a`
5. Should this state persist? Add to `core/config.json` defaults
