# NTN Podcast Creator – Audio Processing Implementation Plan

## Overview
This document outlines the implementation plan for enhancing the NTN Podcast Creator with:
- Background noise removal
- Volume normalization
- Local AI-based audio enhancement (Whisper)
- M4A input support
- Interactive per‑episode processing

The plan also prepares for future API integrations (Dolby.io, Descript).

---

## Phase 1 Features

### 1. Background Noise Removal
Two local methods should be implemented:
- **Noisereduce** (Python spectral gating)
- **FFmpeg RNNoise (arnndn)** filter

**Integration point:** Immediately after user uploads the voice recording (input M4A → WAV).

#### Noisereduce Example
```python
import noisereduce as nr
import soundfile as sf
import numpy as np

def reduce_background_noise(input_path, output_path):
    data, rate = sf.read(input_path)
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    noise_len = int(rate * 0.5)
    noise_clip = data[:noise_len]

    cleaned = nr.reduce_noise(audio_clip=data, noise_clip=noise_clip)
    sf.write(output_path, cleaned, rate)
```

#### FFmpeg RNNoise Example
```bash
ffmpeg -i input.wav -filter:a arnndn -c:a pcm_s16le output.wav
```

---

### 2. Volume Normalization (LUFS)
Normalize the final mixed audio to **-14 or -16 LUFS**, using FFmpeg's *loudnorm* filter.

**Integration point:** After mixing intro/outro/background tracks and before MP3 export.

#### FFmpeg Loudnorm Example
Two-pass recommended:
```bash
ffmpeg -i draft.wav -af loudnorm=I=-16:print_format=json -f null -
ffmpeg -i draft.wav -af loudnorm=I=-16:TP=-1.5:LRA=7:measured_I=...:measured_TP=...:measured_LRA=...:measured_thresh=... output.wav
```

---

### 3. Whisper Transcription (Local)
Used for:
- Automatic transcript generation
- Quality validation
- Future Descript integration

**Integration point:** After noise removal but independent of mixing.

#### Whisper Example
```python
import whisper

def transcribe_audio(path):
    model = whisper.load_model("small")
    result = model.transcribe(path)
    return result["text"]
```

---

## Phase 1 UI / Workflow (Interactive Per Episode)

1. **Upload Voice Recording (M4A supported)**
2. **Options:**
   - ✔ Noise Removal (Basic / AI / RNNoise)
   - ✔ Loudness Normalization
   - ✔ Transcription (Whisper)
3. **Process Steps:**
   - Convert M4A → WAV
   - Noise reduction
   - Silence trimming (existing)
   - Mix intro/outro/background
   - LUFS normalization
   - Export MP3
   - Generate transcript (async)
4. **Outputs:**
   - Final MP3
   - Cleaned voice WAV
   - Transcript TXT

---

## CLI Mode (Optional for Phase 1)
A simple step-by-step terminal workflow:

```
Enter voice file:
Apply noise reduction? (Y/n)
Normalize volume? (Y/n)
Generate transcript? (y/N)
...
```

---

## Phase 2 Preparations (API Hooks)

### Modular Architecture
Design functions so they can switch between:
- Local noise reduction → Dolby.io API
- Local transcription → Descript API
- Local mastering → Dolby.io mastering pipelines

### Recommended Hooks
- `denoise_audio(method="local_basic"|"local_ai"|"dolby")`
- `normalize_audio(method="ffmpeg"|"dolby")`
- `transcribe_audio(method="whisper"|"descript")`

### Future UI Options
- Dolby.io API key field
- Descript “Send to Project” button

---

## Summary
Phase 1 provides:
- Clean, consistent, normalized audio
- Fully local processing
- Better professional quality workflows
- A foundation for Phase 2 AI/cloud integrations

This plan ensures NTN Podcast Creator evolves into a fully automated podcast production tool with modern audio engineering standards. 🎙️
