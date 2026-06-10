# ✅ Copilot Instructions Generated

## Summary
Created `.github/copilot-instructions.md` - a comprehensive guide for AI agents working in the NTN Podcast Creator codebase.

## Document Structure (221 lines)

### 1. **Project Overview**
- Clear explanation of what NTN Podcast Creator does
- Key architecture pattern (3-tier: UI → Logic → Data)
- Tech stack and primary user context

### 2. **Critical Knowledge** (5 sections)
Essential patterns that AI agents MUST understand:

#### Section 1: Application Entry & UI Structure (app.py)
- Why this is ~2400 lines and structured as generator handlers
- Gradio 6.0 specific constraints (no `visible=False`, no `gr.update()`)
- Critical pattern: Yield exactly 7 values for output components
- Global state management (`console_log`)
- Directory structure requirements

#### Section 2: Audio Processing Pipeline
- Complete workflow: Denoise → Enhance → Trim → Mix → Normalize → Transcribe
- 3 denoising methods with specific use cases:
  - `audio_denoiser`: AI-based (chunks >8MB files)
  - `spectral`: Fast gating (0.5s noise profile)
  - `rnnoise`: FFmpeg integration
- Mixing strategy: 1-second overlaps
- LUFS normalization: 2-pass FFmpeg

#### Section 3: Configuration Persistence
- Single ConfigManager instance pattern
- Auto-loading from `audios/` folders
- Per-track volume tracking vs. master volume
- Config file location and structure

#### Section 4: Gradio 6.0 Compatibility
- Specific workarounds for broken API
- Pattern for HTML components with inline display control
- Example code showing correct pattern

#### Section 5: Logging System
- Global `console_log` array usage
- Real-time display functions
- Callback pattern for audio processors

### 3. **Developer Workflows**
Ready-to-copy commands:
- Dev container quick start
- Test commands (core + integration)
- Syntax validation
- Testing with real audio files

### 4. **Project-Specific Patterns**
Code patterns unique to this project:
- Audio duration calculation pattern
- Generator-based event handlers
- Background music building with per-track volumes
- Large file chunking strategy
- Config key naming conventions

### 5. **File Structure Reference**
Visual map of important files/directories with their purpose

### 6. **Common Pitfalls & Workarounds**
Quick reference table addressing real issues encountered:
- Progress bar display issues
- Console log persistence
- Large file failures
- Gradio yield count errors
- Config persistence
- File path handling

### 7. **Quick Reference: Key Functions**
Most important functions organized by module

### 8. **Questions for AI Agents**
5 checkpoint questions agents should ask before making changes

---

## Key Discoveries in This Codebase

### Architectural Decisions Worth Noting
1. **Generator-based handlers**: Unlike typical request/response, uses `yield` for streaming progress updates
2. **Global console_log**: Deliberately global for real-time sharing between threads
3. **ConfigManager singleton**: All config changes auto-persist
4. **Gradio 6.0 constraints**: Required workarounds documented explicitly
5. **Threading + queue pattern**: Real-time log updates via thread-safe queues

### Project-Specific Conventions
- Yield statement format is strict: must be exactly 7 values, in specific order
- All config keys must be pre-defined in `_default_config()`
- Audio files auto-scanned from `audios/` subdirectories
- Large files (>8MB) auto-chunked without user awareness
- Three denoising methods with different tradeoffs

### Integration Points
- Gradio 6.0: UI framework with strict output/input matching
- FFmpeg: 2-pass LUFS normalization, RNNoise option
- Playwright: Browser automation for Adobe Enhance
- PyTorch: AI-based denoising backend
- Whisper: Transcription with 99+ language support
- pydub: Audio mixing and manipulation

### Testing Approach
- Core tests: 7 tests, ~60 seconds (no full processing)
- Integration tests: Full workflows with real audio (5-10 min)
- Test audio: 18.1MB file to exercise chunking code path
- Tests run from project root, verify imports work

---

## How Agents Should Use This Document

**Checklist for any change:**
1. Read Section 1 (Project Overview) to understand context
2. Read Section 2 (Critical Knowledge) relevant to the change
3. Check Section 6 (Common Pitfalls) for gotchas
4. Refer to Section 8 (Questions) before implementing
5. Use Section 3 (Developer Workflows) to test changes

**Examples of agent decisions informed by this document:**
- Adding a new audio processing stage → Must integrate into pipeline in audio_processor.py
- Adding a UI control → Must match yield count (7 values) in handler
- Adding config option → Must add to `_default_config()` and create handler for persistence
- Working with large files → Use chunking pattern from audio_denoiser_processor.py
- Testing changes → Run syntax check + core tests (60s) before full integration tests

---

## Coverage Analysis

### What's Documented
✅ Architecture (why 3-tier design)
✅ UI Framework (Gradio 6.0 specific workarounds)
✅ Audio Processing (complete pipeline with 5 stages)
✅ Data Persistence (ConfigManager pattern)
✅ Logging (global console + threading)
✅ Testing (commands + test audio location)
✅ Common Pitfalls (table of real issues)
✅ Key Functions (organized by module)
✅ File Structure (visual map)

### What's NOT Documented (aspirational, not discoverable)
- Future performance optimizations
- Planned UI redesign features
- Potential deployment strategies beyond Docker

---

## File Location
`.github/copilot-instructions.md` (221 lines)

This file is now visible to GitHub Copilot and VS Code copilot extensions when working in this repository.
