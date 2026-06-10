# 📋 Copilot Instructions - Feedback Questions

Based on the analysis of the NTN Podcast Creator codebase, here are clarification questions to enhance the copilot instructions:

---

## Question 1: Transcription Workflow

**Current Documentation:**
- "Parallel `whisper_transcriber.py` with 99+ languages"
- Config key: `generate_transcript: bool` and `whisper_model: str` (e.g., "base", "small", "medium")

**What we need to clarify:**

1. **Is transcription always optional?** Or are there workflows where it's required/critical?
2. **Model size tradeoffs?** Should agents know about:
   - Processing time differences (base vs small vs medium)?
   - Quality/accuracy differences?
   - Memory/resource requirements?
3. **Language selection?** How do agents specify language? Is it auto-detected or user-selected?
4. **Error handling?** What happens if transcription fails? Does it fail the entire podcast creation or is it graceful?

---

## Question 2: Adobe Enhancement Strategy

**Current Documentation:**
- "Browser automation via Playwright (`adobe_audio_enhancer.py`)"
- Feature flag: `enhance_audio: bool`

**What we need to clarify:**

1. **Success/failure rates?** How often does browser automation succeed vs fail?
2. **Fallback strategy?** If enhancement fails, does the pipeline:
   - Abort the entire podcast creation?
   - Skip enhancement and continue?
   - Retry with different approach?
3. **Audio format requirements?** Are there known issues with specific formats (mp3, wav, m4a)?
4. **Authentication?** Does this require Adobe credentials or API keys? Should agents know about setup requirements?

---

## Question 3: Error Handling Philosophy

**Current Documentation:**
- Large file denoising: "chunks >8MB auto-chunked" with "error fallback"
- No explicit guidance on graceful degradation vs critical errors

**What we need to clarify:**

1. **Graceful Degradation?** Should agents always provide fallbacks?
   - Example: Denoising fails → use original audio and continue?
   - Example: Adobe Enhancement fails → skip and continue?
   - Example: LUFS normalization fails → export without normalization?

2. **Critical vs Recoverable Errors?** Which errors should:
   - Stop the entire podcast creation?
   - Be logged but not block processing?

3. **Error Messages?** Are there specific error patterns agents should watch for or log?

---

## Question 4: Performance Characteristics

**Current Documentation:**
- Core tests: ~60 seconds
- Test audio: 18.1MB file with chunking

**What we need to clarify:**

1. **Large File Processing?** What are typical durations for:
   - Denoising a 1-hour podcast with `audio_denoiser` method?
   - Denoising the same file with `spectral` method?
   - Adobe enhancement time for similar file?
   - LUFS normalization time?
   - Whisper transcription (depends on language model)?

2. **Memory Requirements?** Should agents be aware of:
   - Maximum file size the app can handle?
   - Memory consumption during chunked processing?
   - GPU requirements for AI denoising?

3. **Resource Constraints?** Are there:
   - CPU/GPU bottlenecks agents should know about?
   - Concurrent processing limits?
   - Disk space requirements for temporary files?

---

## Question 5: Future Extension Points

**Current Documentation:**
- Covers Phase 2 features (LUFS, Whisper)
- Architecture: 3-tier pattern with modular features

**What we need to clarify:**

1. **Planned Features?** Should agents know about:
   - Phase 3 features in development?
   - Experimental features not yet in production?

2. **Extensibility?** Are there specific architectural areas designed for:
   - Adding new audio processors?
   - Adding new denoising methods?
   - Adding new feature toggles?

3. **Plugin Architecture?** Should agents know about:
   - How to add a new audio processing stage?
   - How to add a new denoising method?
   - Config pattern for new features?

---

## Your Input Needed

Please provide answers to these questions so we can update the copilot instructions to be even more helpful:

**Format suggestion for your response:**
```
## Answer 1: Transcription Workflow
1. Optional or required? [Your answer]
2. Model tradeoffs? [Your answer]
3. Language selection? [Your answer]
4. Error handling? [Your answer]

## Answer 2: Adobe Enhancement
1. Success rates? [Your answer]
2. Fallback strategy? [Your answer]
3. Format requirements? [Your answer]
4. Authentication? [Your answer]

[... continue for remaining questions]
```

---

## Next Steps

Once you provide answers, I will:
1. Update `.github/copilot-instructions.md` with the clarified information
2. Add specific performance metrics and timing data
3. Document the error handling philosophy
4. Include extension patterns for future features
5. Finalize the instructions with complete decision guidance for AI agents
