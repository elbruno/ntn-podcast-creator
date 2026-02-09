# Voice Enhancement Implementation Guide

## Overview

The Voice Enhancement feature provides professional audio processing for podcast recordings using FFmpeg's advanced audio filters. It applies EQ, compression, and de-essing to improve voice clarity and listening quality.

## Architecture

### Files Involved

- **`features/voice_enhancer.py`**: Core voice enhancement module (NEW)
- **`features/audio_processor.py`**: Integration point in podcast creation pipeline (UPDATED)
- **`features/config_manager.py`**: Configuration persistence (UPDATED)
- **`app.py`**: UI controls and event handlers (UPDATED)

### Processing Pipeline Position

Voice enhancement is applied **after denoising** and **before mixing**:

```
Voice Recording
    ↓
[Noise Reduction] (if enabled)
    ↓
[Voice Enhancement] (if enabled) ← NEW STEP
    ↓
[Silence Trimming] (if enabled)
    ↓
[Audio Mixing]
    ↓
[LUFS Normalization] (if enabled)
    ↓
Final Podcast
```

## Technical Details

### FFmpeg Filters Used

The voice enhancement applies a chain of FFmpeg audio filters:

1. **High-pass Filter** (`highpass`): Removes low-frequency rumble
2. **Low-pass Filter** (`lowpass`): Removes harsh high frequencies
3. **Equalizer** (`equalizer`): Boosts voice presence and clarity
4. **De-esser** (`deesser`): Reduces harsh sibilance (S/SH sounds)
5. **Compander** (`compand`): Dynamic range compression for consistent volume

### Enhancement Presets

#### Podcast (Default - Balanced)
**Use case**: Standard podcast recordings in typical environments

**Filter chain**:
```
highpass=f=85,
lowpass=f=11000,
equalizer=f=180:t=q:w=1:g=-3,      # Reduce mud at 180Hz
equalizer=f=2800:t=q:w=2:g=4,      # Boost presence at 2.8kHz
equalizer=f=4500:t=q:w=1:g=2,      # Add clarity at 4.5kHz
deesser=i=0.07:m=0.5:f=6000:s=o,   # Moderate de-essing
compand=attacks=0.2:decays=0.6:points=-80/-80|-48/-32|-28/-22|0/-11:soft-knee=6:gain=6
```

**Characteristics**:
- Removes rumble below 85Hz
- Cuts harsh highs above 11kHz
- Moderate presence boost (4dB at 2.8kHz)
- Gentle compression (6dB makeup gain)

#### Light (Gentle Processing)
**Use case**: Clean recordings in quiet environments, minimal processing needed

**Filter chain**:
```
highpass=f=80,
lowpass=f=12000,
equalizer=f=200:t=q:w=1:g=-2,      # Light mud reduction
equalizer=f=3000:t=q:w=2:g=3,      # Gentle presence boost
compand=attacks=0.3:decays=0.8:points=-80/-80|-45/-30|-27/-20|0/-10:soft-knee=6:gain=5
```

**Characteristics**:
- Preserves more of the original sound
- Gentle EQ adjustments
- Light compression (5dB makeup gain)
- No de-esser (preserves natural sibilance)

#### Aggressive (Strong Processing)
**Use case**: Very noisy recordings, poor acoustic environments

**Filter chain**:
```
highpass=f=100,
lowpass=f=10000,
equalizer=f=150:t=q:w=1:g=-4,      # Strong mud reduction
equalizer=f=2500:t=q:w=2:g=5,      # Strong presence boost
equalizer=f=5000:t=q:w=1:g=3,      # Clarity boost
deesser=i=0.1:m=0.5:f=6000:s=o,    # Strong de-essing
compand=attacks=0.1:decays=0.5:points=-80/-80|-50/-35|-30/-25|0/-12:soft-knee=6:gain=8
```

**Characteristics**:
- More aggressive filtering (100Hz - 10kHz)
- Strong presence boost (5dB at 2.5kHz)
- Strong compression (8dB makeup gain)
- Aggressive de-essing

## API Reference

### VoiceEnhancer Class

```python
from features.voice_enhancer import VoiceEnhancer

enhancer = VoiceEnhancer()
```

#### Methods

##### `is_available() -> bool`
Check if FFmpeg is available for voice enhancement.

```python
if enhancer.is_available():
    # FFmpeg is installed and ready
    pass
```

##### `enhance_voice(input_file, output_file=None, preset="podcast", log_callback=None) -> Optional[str]`
Apply comprehensive voice enhancement.

**Parameters**:
- `input_file` (str): Path to input audio file
- `output_file` (str, optional): Path for output. If None, creates temp file
- `preset` (str): Enhancement preset - "podcast", "light", or "aggressive"
- `log_callback` (callable, optional): Callback function for logging progress

**Returns**: Path to enhanced audio file, or None if failed

**Example**:
```python
enhanced = enhancer.enhance_voice(
    input_file="recording.mp3",
    output_file="enhanced.wav",
    preset="podcast",
    log_callback=print
)
```

##### `apply_high_pass_filter(input_file, output_file=None, cutoff_freq=80, log_callback=None) -> Optional[str]`
Apply only high-pass filter to remove low-frequency rumble.

##### `apply_dynamic_compression(input_file, output_file=None, strength="medium", log_callback=None) -> Optional[str]`
Apply only dynamic range compression.

### Convenience Function

```python
from features.voice_enhancer import enhance_voice

# Quick enhancement with defaults
enhanced = enhance_voice(
    input_file="recording.mp3",
    preset="podcast"
)
```

## Integration with AudioProcessor

The voice enhancement is integrated into `AudioProcessor.create_podcast()`:

```python
audio_processor.create_podcast(
    voice_file="recording.mp3",
    # ... other parameters ...
    enhance_voice_enabled=True,          # Enable voice enhancement
    voice_enhancement_preset="podcast",   # Choose preset
    # ... other parameters ...
)
```

### Processing Order

1. **Noise Reduction** (if enabled)
   - AI Denoiser / Spectral / RNNoise
2. **Voice Enhancement** (if enabled) ← NEW
   - High-pass, EQ, De-esser, Compression
3. **Load into AudioSegment**
4. **Trim Silence** (if enabled)
5. **Mix with intro/outro/background**
6. **LUFS Normalization** (if enabled)

## Configuration

### Config Keys

```python
# features/config_manager.py
{
    "enhance_voice": False,                    # Enable/disable feature
    "voice_enhancement_preset": "podcast"      # Default preset
}
```

### UI Controls

Located in `app.py` under "Audio Processing" tab:

```python
enhance_voice_checkbox = gr.Checkbox(
    label="Enable professional voice enhancement",
    value=config_manager.get("enhance_voice", False),
    info="Apply EQ, compression, and de-essing for clearer voice"
)

voice_enhancement_preset_dropdown = gr.Dropdown(
    label="Enhancement Preset",
    choices=[
        ("Podcast (Balanced)", "podcast"),
        ("Light (Gentle)", "light"),
        ("Aggressive (Strong)", "aggressive")
    ],
    value=config_manager.get("voice_enhancement_preset", "podcast"),
    info="Choose enhancement strength"
)
```

## Performance

### Processing Time

For a 15-minute podcast voice recording:
- **Light preset**: ~30-45 seconds
- **Podcast preset**: ~45-60 seconds
- **Aggressive preset**: ~60-90 seconds

Processing time varies based on:
- Audio file size and duration
- CPU speed
- Audio format (WAV processes faster than MP3)

### Resource Usage

- **CPU**: Single-threaded FFmpeg process
- **Memory**: ~50-100MB during processing
- **Disk**: Temporary files equal to input file size

## Error Handling

Voice enhancement failures do NOT stop podcast creation:

```python
if enhance_voice_enabled:
    enhanced_file = enhance_voice(voice_file, preset=preset, log_callback=log)

    if enhanced_file and enhanced_file != voice_file:
        # Use enhanced audio
        voice_file_to_process = enhanced_file
    else:
        # Enhancement failed - continue with original audio
        log("Voice enhancement failed, continuing with current audio")
```

## Testing

### Unit Tests

Run the voice enhancement test suite:

```bash
python tests/test_voice_enhancement.py
```

Tests verify:
- VoiceEnhancer initialization
- FFmpeg availability detection
- Filter chain generation for all presets
- Convenience function accessibility

### Manual Testing

Test with a real audio file:

```python
from features.voice_enhancer import enhance_voice

# Test enhancement
enhanced = enhance_voice(
    input_file="audios/test/sample.mp3",
    output_file="outputs/test_enhanced.wav",
    preset="podcast",
    log_callback=print
)

if enhanced:
    print(f"✓ Enhancement successful: {enhanced}")
else:
    print("✗ Enhancement failed")
```

## Usage Recommendations

### When to Use Each Preset

| Recording Quality | Environment | Recommended Preset |
|------------------|-------------|-------------------|
| Clean, professional mic | Quiet room | Light |
| Standard USB mic | Home office | Podcast (default) |
| Laptop mic | Some background noise | Podcast |
| Phone recording | Noisy environment | Aggressive |

### Best Practices

1. **Always denoise first**: Apply noise reduction before voice enhancement
2. **Start with defaults**: Try "podcast" preset first
3. **A/B compare**: Listen to before/after to verify improvement
4. **Don't over-process**: If recording is already good, use "light" or skip enhancement
5. **Combine with LUFS**: Use LUFS normalization after enhancement for consistent loudness

### Common Issues

**Issue**: Enhancement makes voice sound "thin" or "hollow"
- **Solution**: Switch to "light" preset or reduce presence boost

**Issue**: S sounds are too dull after processing
- **Solution**: Use "light" preset (no de-esser)

**Issue**: Voice sounds "compressed" or unnatural
- **Solution**: Use "light" preset or disable enhancement

## FFmpeg Requirements

- **Minimum version**: FFmpeg 4.0+
- **Required filters**: highpass, lowpass, equalizer, deesser, compand
- **Installation**: See main README for installation instructions

### Checking FFmpeg Availability

```python
from features.voice_enhancer import VoiceEnhancer

enhancer = VoiceEnhancer()
if enhancer.is_available():
    print("✓ FFmpeg is available")
else:
    print("✗ FFmpeg not found - install from ffmpeg.org")
```

## Future Enhancements

Potential future improvements:
- [ ] Custom preset editor (user-defined EQ curves)
- [ ] Adaptive enhancement based on audio analysis
- [ ] Noise gate for cleaner backgrounds
- [ ] Stereo width enhancement
- [ ] Spectral analysis visualization
- [ ] Preset import/export

## References

- [FFmpeg Audio Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters)
- [Audio EQ Cookbook](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html)
- [Dynamic Range Compression](https://en.wikipedia.org/wiki/Dynamic_range_compression)
- [De-essing Techniques](https://www.izotope.com/en/learn/the-basics-of-de-essing.html)
