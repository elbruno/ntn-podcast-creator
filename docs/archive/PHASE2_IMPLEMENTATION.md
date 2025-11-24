# Phase 2 Audio Processing Implementation

This document describes the Phase 2 advanced audio processing features implemented in the NTN Podcast Creator.

## Overview

Phase 2 adds professional-grade audio processing capabilities to transform podcast production into a fully automated workflow with broadcast-quality output.

## Features Implemented

### 1. Multiple Noise Reduction Methods

Three distinct noise reduction algorithms are now available, each with different characteristics:

#### A. AI Denoiser (audio-denoiser) - **Recommended**
- **Technology**: 38-million parameter deep learning model
- **Best for**: General speech enhancement and background noise removal
- **Speed**: Fast (typically < 30 seconds)
- **Quality**: Excellent for most use cases
- **Special features**: 
  - Automatic chunking for large files (>10MB)
  - Works completely offline
  - Preserves speech quality while removing noise

#### B. Spectral Gating (noisereduce)
- **Technology**: Spectral subtraction and gating
- **Best for**: Stationary background noise (hums, fans, etc.)
- **Speed**: Very fast
- **Quality**: Good for specific noise types
- **How it works**: Uses the first 0.5 seconds as a noise profile

#### C. FFmpeg RNNoise
- **Technology**: Recurrent neural network for noise suppression
- **Best for**: Real-time noise reduction
- **Speed**: Fast
- **Quality**: Good for speech
- **Note**: Requires FFmpeg built with RNNoise support

### 2. LUFS Normalization

Professional audio loudness normalization to broadcast standards.

#### What is LUFS?

LUFS (Loudness Units relative to Full Scale) is the international standard for measuring audio loudness. It ensures consistent volume across all episodes and matches podcast platform standards.

#### Features:
- **Two-pass normalization**: For maximum accuracy
- **Configurable target**: -16 LUFS (podcast standard) or -14 LUFS (louder content)
- **True peak limiting**: Prevents clipping at -1.5 dBTP
- **Loudness range control**: Maintains dynamic range (LRA=7)

#### Recommended Settings:
- **Podcasts**: -16 LUFS (industry standard)
- **Audiobooks**: -18 LUFS
- **Streaming platforms**: -14 LUFS
- **Broadcast radio**: -23 LUFS (EBU R128)

### 3. Automatic Transcription with Whisper

Generate accurate transcripts using OpenAI's Whisper speech recognition model.

#### Model Sizes:
| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| Tiny | 39MB | Fastest | Good | Quick drafts, testing |
| Base | 74MB | Fast | Better | **Recommended for most users** |
| Small | 244MB | Moderate | Great | High-quality transcripts |
| Medium | 769MB | Slow | Excellent | Professional use |
| Large | 1.5GB | Very Slow | Best | Maximum accuracy needed |

#### Features:
- **Automatic language detection**: Works with 99+ languages
- **Timestamped transcripts**: Includes word-level timing
- **High accuracy**: State-of-the-art speech recognition
- **Offline processing**: Runs locally (after initial model download)

#### Output Formats:
1. **Plain text**: Simple transcript for reading
2. **Timestamped**: Includes time markers for each segment

## User Interface

### Location
All Phase 2 features are in the **"Phase 2: Advanced Audio Processing"** accordion on the main "Create Podcast" tab.

### Controls

#### Noise Reduction Section
- **Enable checkbox**: Turn noise reduction on/off
- **Method dropdown**: Choose between AI Denoiser, Spectral Gating, or RNNoise

#### Audio Enhancement Section
- **Adobe Enhance checkbox**: Optional cloud-based enhancement

#### Volume Normalization Section
- **Enable checkbox**: Turn LUFS normalization on/off
- **Target slider**: Set target LUFS level (-20 to -10, default: -16)

#### Automatic Transcription Section
- **Enable checkbox**: Generate transcript
- **Model dropdown**: Choose Whisper model size

## Workflow

### Recommended Processing Order

The system automatically processes audio in this optimal order:

1. **Noise Reduction** (if enabled)
   - Removes background noise first for cleaner input
   
2. **Adobe Enhance** (if enabled)
   - Further enhances audio quality
   
3. **Trim Silence** (if enabled)
   - Removes dead air from start and end
   
4. **Mix Audio**
   - Combines intro, voice, outro, and background music
   
5. **LUFS Normalization** (if enabled)
   - Normalizes final mix to target loudness
   
6. **Export to MP3**
   - Saves final podcast
   
7. **Generate Transcript** (if enabled)
   - Creates transcript in parallel

### Best Practices

#### For Quick Processing:
- Use AI Denoiser (default)
- Skip Adobe Enhance
- Skip LUFS normalization for first draft
- Use Tiny Whisper model for quick transcripts

#### For Best Quality:
- Use AI Denoiser or Spectral Gating
- Enable Adobe Enhance (adds 2-5 minutes)
- Enable LUFS normalization to -16 LUFS
- Use Base or Small Whisper model

#### For Professional Production:
- Test noise reduction methods and pick best for your environment
- Always enable LUFS normalization
- Use Medium Whisper model for final transcript
- Review and edit transcript for accuracy

## Technical Details

### Noise Reduction Algorithms

#### Spectral Gating Process:
1. Load audio and convert to mono
2. Extract noise profile from first 0.5 seconds
3. Apply spectral subtraction across full audio
4. Export cleaned audio

#### RNNoise Process:
1. Convert audio to suitable format
2. Apply trained RNN model via FFmpeg filter
3. Export processed audio

### LUFS Normalization Process

#### Pass 1 (Measurement):
```bash
ffmpeg -i input.wav -af loudnorm=I=-16:print_format=json -f null -
```

#### Pass 2 (Normalization):
```bash
ffmpeg -i input.wav -af loudnorm=I=-16:TP=-1.5:LRA=7:measured_I=X:measured_TP=Y:measured_LRA=Z output.wav
```

### Whisper Integration

Models are downloaded on first use to `~/.cache/whisper/`:
- **Tiny**: ~40MB
- **Base**: ~74MB  
- **Small**: ~244MB
- **Medium**: ~769MB
- **Large**: ~1.5GB

## Configuration

All Phase 2 settings are automatically saved in `core/config.json`:

```json
{
  "denoise_method": "audio_denoiser",
  "normalize_lufs": false,
  "target_lufs": -16.0,
  "generate_transcript": false,
  "whisper_model": "base"
}
```

## Requirements

### Python Packages:
- `noisereduce==3.0.2` - For spectral noise reduction
- `openai-whisper==20240930` - For transcription
- `soundfile==0.12.1` - Audio I/O for noisereduce
- `numpy<2.0.0` - Required by multiple audio libraries

### System Dependencies:
- **FFmpeg 4.0+**: Required for LUFS normalization and RNNoise
- **CUDA (optional)**: Speeds up Whisper transcription significantly

### Installation:
```bash
# Python packages
pip install -r requirements.txt

# FFmpeg (Ubuntu/Debian)
sudo apt-get install ffmpeg

# FFmpeg (macOS)
brew install ffmpeg

# FFmpeg (Windows)
# Download from https://ffmpeg.org/download.html
```

## Troubleshooting

### Whisper Model Download Fails
**Issue**: First-time model download requires internet connection.

**Solution**: 
- Ensure internet connectivity
- Models are cached after first download
- Pre-download models: `whisper --model base dummy.wav`

### RNNoise Not Working
**Issue**: Standard FFmpeg builds don't include RNNoise filter.

**Solution**:
- Use AI Denoiser or Spectral Gating instead (both work excellently)
- Or build FFmpeg with `--enable-librnnoise` flag

### LUFS Normalization Slow
**Issue**: Two-pass normalization takes time for long files.

**Solution**:
- Processing time scales with file length
- Expected: ~30 seconds for 10-minute podcast
- Disable for quick drafts, enable for final output

### Out of Memory with Large Whisper Models
**Issue**: Large/Medium models require significant RAM.

**Solution**:
- Use Base or Small model (excellent quality)
- Large model only needed for maximum accuracy
- Enable CUDA/GPU acceleration if available

## Performance

Typical processing times for a 10-minute podcast:

| Operation | Time | Notes |
|-----------|------|-------|
| AI Denoiser | 15-30s | Fast, handles any size |
| Spectral Gating | 5-10s | Very fast |
| RNNoise | 10-20s | Fast (when available) |
| Adobe Enhance | 2-5min | Cloud processing |
| LUFS Normalization | 20-40s | Two-pass process |
| Whisper (Tiny) | 30-60s | Quick draft |
| Whisper (Base) | 1-2min | Recommended |
| Whisper (Small) | 2-4min | High quality |
| Whisper (Medium) | 5-10min | Excellent quality |

## API Integration (Phase 2 Prep)

The modular architecture supports future API integration:

```python
# Current: Local processing
denoise_audio(method="audio_denoiser")

# Future: API option
denoise_audio(method="dolby_api", api_key="xxx")

# Transcription
transcribe_audio(method="whisper")  # Local
transcribe_audio(method="descript_api")  # Future API
```

## Output Files

Phase 2 creates additional output files:

```
outputs/
├── podcast_episode.mp3          # Final podcast
├── voice_denoised.wav           # Cleaned voice (if denoising enabled)
└── voice_transcript.txt         # Plain transcript (if transcription enabled)
└── voice_transcript_timestamped.txt  # With timestamps
```

## CLI Usage (Future Enhancement)

Planned for future release:

```bash
# Interactive mode
python cli.py create

# Batch mode
python cli.py create \
  --voice recording.wav \
  --denoise spectral \
  --normalize \
  --transcript \
  --output episode.mp3
```

## Conclusion

Phase 2 transforms the NTN Podcast Creator into a professional podcast production system with:

✅ Multiple noise reduction methods for every scenario  
✅ Professional LUFS normalization for broadcast quality  
✅ Automatic transcription for accessibility and SEO  
✅ Modular architecture ready for API integration  
✅ All processing done locally (except optional Adobe Enhance)

The combination of these features enables fully automated, professional-quality podcast production from recording to final output with transcript.
