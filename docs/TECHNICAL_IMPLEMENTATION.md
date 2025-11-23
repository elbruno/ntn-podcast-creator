# NTN Podcast Creator - Technical Implementation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [System Components](#system-components)
4. [Data Flow](#data-flow)
5. [Audio Processing Pipeline](#audio-processing-pipeline)
6. [Configuration Management](#configuration-management)
7. [User Interface](#user-interface)
8. [File Structure](#file-structure)
9. [API Reference](#api-reference)
10. [Deployment](#deployment)

---

## Architecture Overview

NTN Podcast Creator follows a modular, three-tier architecture:

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│              (Gradio Web Interface)                      │
│  - User Input Forms                                      │
│  - Audio Players                                         │
│  - Visual Timeline                                       │
│  - Download/Upload Controls                              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Business Logic Layer                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   app.py     │  │config_manager│  │audio_processor│ │
│  │              │  │    .py       │  │     .py       │ │
│  │ UI Handlers  │  │              │  │              │ │
│  │ Orchestration│  │ Settings     │  │ Audio Mixing │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Data Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  config.json │  │ audios/      │  │  outputs/    │  │
│  │              │  │ - intro      │  │              │  │
│  │ User Settings│  │ - outro      │  │ Generated    │  │
│  │ Track Volumes│  │ - background │  │ Podcasts     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Modularity**: Components are loosely coupled and can be modified independently
- **Persistence**: All user preferences are automatically saved
- **User-Friendly**: Intuitive interface with visual feedback and previews

---

## Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Core programming language |
| **Gradio** | 6.0.0 | Web-based user interface framework |
| **pydub** | 0.25.1 | Audio processing and manipulation |
| **FFmpeg** | Latest | Audio codec handling and conversion |
| **huggingface-hub** | 1.1.5 | Dependency for Gradio |

### Audio Processing Stack

```
User Audio Files
      ↓
   pydub (AudioSegment)
      ↓
   FFmpeg (Codec Processing)
      ↓
   Volume Adjustment
      ↓
   Audio Concatenation
      ↓
   Overlay/Mixing
      ↓
   MP3 Export
```

---

## System Components

### 1. app.py - Main Application

**Responsibilities:**
- Gradio UI creation and management
- Event handler routing
- User interaction orchestration
- File upload/download management
- Timeline visualization generation

**Key Functions:**
- `create_ui()`: Builds the Gradio interface
- `create_podcast_handler()`: Orchestrates podcast creation
- `generate_timeline_chart()`: Creates visual timeline preview
- `export_settings()`: Exports configuration to JSON
- `import_settings()`: Imports configuration from JSON

### 2. audio_processor.py - Audio Processing Engine

**Responsibilities:**
- Audio file loading and validation
- Volume adjustment with logarithmic scaling
- Audio segment trimming (silence removal)
- Background music looping and concatenation
- Audio mixing and overlaying
- Final podcast assembly with overlaps

**Key Classes:**
```python
class AudioProcessor:
    def load_audio(file_path) -> AudioSegment
    def trim_silence(audio, threshold=-40) -> AudioSegment
    def reduce_volume(audio, volume_percent) -> AudioSegment
    def create_looped_background(files, duration, volume, track_volumes) -> AudioSegment
    def mix_audio(main_audio, background) -> AudioSegment
    def create_podcast(...) -> str
```

**Audio Processing Pipeline:**
1. Load voice recording
2. Optional: Trim silence from voice
3. Load intro/outro (if provided)
4. Create looped background music (if provided)
5. Apply individual track volumes
6. Mix background with voice
7. Concatenate: intro → voice+background → outro
8. Apply 1-second crossfade overlaps
9. Export to MP3

### 3. config_manager.py - Configuration Management

**Responsibilities:**
- Persistent storage of user preferences
- Track-specific volume management
- Audio file path management
- Auto-loading default audio files
- Settings import/export

**Key Classes:**
```python
class ConfigManager:
    def __init__(config_file="config.json")
    def save_config()
    def get/set(key, value)
    def update_intro/outro(file_path)
    def update_background_tracks(file_paths)
    def get_track_volume(track_path) -> int
    def set_track_volume(track_path, volume)
    def apply_volume_to_all_tracks(volume)
    def load_default_audio_files()
```

**Configuration Schema:**
```json
{
  "intro_file": "audios/intro_audio/intro.mp3",
  "outro_file": "audios/outro_audio/outro.mp3",
  "background_tracks": [
    "audios/background_music/track1.mp3",
    "audios/background_music/track2.mp3"
  ],
  "background_volume": 10,
  "track_volumes": {
    "audios/background_music/track1.mp3": 10,
    "audios/background_music/track2.mp3": 15
  },
  "last_output_name": "podcast_output"
}
```

---

## Data Flow

### Podcast Creation Flow

```
┌─────────────┐
│ User Upload │
│ Voice File  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Load Config     │
│ - Intro         │
│ - Outro         │
│ - BG Tracks     │
│ - Volumes       │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Audio Processor │
│ - Trim Silence  │
│ - Load Assets   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Create BG Music │
│ - Random Select │
│ - Apply Volume  │
│ - Loop to Fill  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Mix Audio       │
│ - Voice + BG    │
│ - Apply Overlaps│
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Assemble Final  │
│ Intro → Voice   │
│ → Outro         │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Export MP3      │
│ outputs/        │
└─────────────────┘
```

### Settings Import/Export Flow

```
Export:
User Click → Gather Config → Create JSON → Save to outputs/ → Return File

Import:
User Upload JSON → Parse & Validate → Update ConfigManager → Refresh UI
```

---

## Audio Processing Pipeline

### Volume Adjustment Algorithm

The application uses logarithmic scaling for natural volume perception:

```python
# Convert percentage to dB
db_change = 20 * log10(volume_percent / 100)

# Apply to audio
adjusted_audio = original_audio + db_change
```

**Volume Scale:**
- 100% = 0 dB (original)
- 50% = -6 dB
- 10% = -20 dB
- 0% = -60 dB (near silence)

### Background Music Looping

Background tracks are randomly selected and concatenated until the target duration is reached:

```python
while len(background) < target_duration:
    track = random.choice(valid_files)
    track_audio = load_audio(track)
    volume = track_volumes.get(track, default_volume)
    track_audio = reduce_volume(track_audio, volume)
    background += track_audio

background = background[:target_duration]  # Trim to exact length
```

### Crossfade Overlaps

1-second overlaps create smooth transitions:

```
Intro:  |████████████████|
                    |████████████████████| Voice
                                   |████████████| Outro

Overlap zones (lighter):
        Intro-Voice: 1s
                    Voice-Outro: 1s
```

Implementation:
```python
# Extract overlapping sections
intro_tail = intro[-1000ms:]
voice_head = voice[:1000ms]

# Mix overlapping parts
overlapped = intro_tail.overlay(voice_head)

# Concatenate
podcast = intro[:-1000ms] + overlapped + voice[1000ms:]
```

---

## Configuration Management

### Auto-Loading Audio Files

On startup, the application automatically scans for audio files:

```python
audios/
├── intro_audio/     → First file becomes default intro
├── outro_audio/     → First file becomes default outro
└── background_music/ → All files loaded as background tracks
```

Supported formats: MP3, WAV, M4A, OGG, FLAC

### Persistence Strategy

- **Automatic Saving**: All changes immediately persisted to `config.json`
- **Lazy Loading**: Configuration loaded once at startup
- **Validation**: File paths validated before use
- **Cleanup**: Invalid paths automatically removed

---

## User Interface

### Tab Structure

1. **Create Podcast**
   - Voice recording upload
   - Output filename input
   - Options: delete voice after creation, trim silence
   - Timeline preview (visual representation)
   - Create button
   - Audio output player
   - Download settings button
   - Import settings control

2. **Settings**
   - Intro audio management
   - Outro audio management
   - Background music management
     - Add/delete tracks
     - Track selector dropdown
     - Individual track audio player
     - Global volume slider
     - Individual track volume slider
     - "Apply to All" button
     - Preview with applied volume
   - Current configuration display

3. **Console Log**
   - Real-time processing logs
   - Error messages
   - Refresh/clear controls

### Visual Components

**Timeline Chart:**
- Color-coded segments (intro, voice, outro)
- Background music overlay visualization
- Duration labels
- Overlap indicators
- Legend with track volumes

**Volume Controls:**
- Global slider (0-50%)
- Per-track sliders (0-50%)
- Apply to all functionality
- Live preview generation

---

## File Structure

```
ntn-podcast-creator/
├── app.py                      # Main application
├── audio_processor.py          # Audio processing logic
├── config_manager.py           # Configuration management
├── requirements.txt            # Python dependencies
├── README.md                   # Project overview
├── LICENSE                     # MIT License
│
├── docs/                       # Documentation
│   ├── USER_MANUAL.md          # User guide
│   └── TECHNICAL_IMPLEMENTATION.md  # This document
│
├── .devcontainer/              # VS Code dev container config
│   ├── devcontainer.json
│   └── README.md
│
├── audios/                     # Audio assets
│   ├── intro_audio/            # Intro files
│   ├── outro_audio/            # Outro files
│   └── background_music/       # Background tracks
│
├── uploads/                    # Temporary uploads (gitignored)
├── outputs/                    # Generated podcasts (gitignored)
└── config.json                 # User settings (gitignored)
```

---

## API Reference

### AudioProcessor Methods

```python
load_audio(file_path: str) -> AudioSegment
    """Load audio file with validation"""

trim_silence(audio: AudioSegment, silence_threshold: int = -40) -> AudioSegment
    """Remove silence from start and end"""

reduce_volume(audio: AudioSegment, volume_percent: int) -> AudioSegment
    """Apply logarithmic volume reduction"""

create_looped_background(
    background_files: List[str],
    target_duration_ms: int,
    volume_percent: int = 10,
    track_volumes: Optional[dict] = None,
    log_callback: Optional[Callable] = None
) -> Optional[AudioSegment]
    """Create looped background with individual track volumes"""

create_podcast(
    voice_file: str,
    intro_file: Optional[str] = None,
    outro_file: Optional[str] = None,
    background_files: Optional[List[str]] = None,
    background_volume: int = 10,
    track_volumes: Optional[dict] = None,
    output_file: str = "output.mp3",
    trim_silence: bool = False,
    log_callback: Optional[Callable] = None
) -> str
    """Create complete podcast with all components"""
```

### ConfigManager Methods

```python
get(key: str, default: Any = None) -> Any
    """Get configuration value"""

set(key: str, value: Any) -> None
    """Set configuration value and save"""

update_intro/outro(file_path: Optional[str]) -> None
    """Update intro/outro file path"""

update_background_tracks(file_paths: List[str]) -> None
    """Update background music tracks"""

get_track_volume(track_path: str) -> int
    """Get volume for specific track"""

set_track_volume(track_path: str, volume: int) -> None
    """Set volume for specific track"""

apply_volume_to_all_tracks(volume: int) -> None
    """Apply volume to all tracks"""

load_default_audio_files() -> None
    """Auto-load audio from audios/ directories"""
```

---

## Deployment

### Local Installation

```bash
# Clone repository
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator

# Install FFmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
# Windows: Download from https://ffmpeg.org/

# Install Python dependencies
pip install -r requirements.txt

# Run application
python app.py

# Access at http://127.0.0.1:7860
```

### Docker Deployment (Dev Container)

```bash
# Open in VS Code with Dev Containers extension
# Container includes:
# - Python 3.12 (compatible with Python 3.8+ requirements)
# - FFmpeg pre-installed
# - All Python dependencies

# Or build manually:
docker build -t ntn-podcast-creator .
docker run -p 7860:7860 ntn-podcast-creator
```

### Production Considerations

1. **File Storage**: Configure persistent volumes for `audios/`, `outputs/`, and `config.json`
2. **Security**: 
   - Add authentication layer if deploying publicly
   - Validate uploaded file types
   - Set file size limits
3. **Performance**:
   - Consider async processing for large files
   - Add queue system for multiple concurrent users
4. **Monitoring**: Add logging and error tracking
5. **Backup**: Regular backups of `config.json` and `audios/` directory

---

## Future Enhancements

### Planned Features
- [ ] Multi-language support
- [ ] Audio effects (reverb, EQ, compression)
- [ ] Batch processing
- [ ] Cloud storage integration
- [ ] API endpoints for programmatic access
- [ ] Real-time collaboration
- [ ] Audio waveform visualization
- [ ] Custom fade durations
- [ ] Chapter markers
- [ ] Metadata tagging

### Performance Optimizations
- [ ] Caching processed audio segments
- [ ] Parallel audio processing
- [ ] Streaming output for large files
- [ ] Progressive audio loading

---

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Install FFmpeg for your platform
# Verify installation: ffmpeg -version
```

**Audio file not loading:**
- Check file format (MP3, WAV, M4A, OGG, FLAC supported)
- Verify file is not corrupted
- Check file permissions

**Volume too low/high:**
- Recommended range: 10-12% for background music
- Individual track volumes override global setting
- Use "Apply to All" to reset all tracks

**Settings not persisting:**
- Check `config.json` file permissions
- Verify write access to application directory

---

## Contributing

### Development Setup

```bash
# Fork and clone repository
git clone https://github.com/YOUR_USERNAME/ntn-podcast-creator.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests (if available)
python -m pytest

# Make changes and submit PR
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document functions with docstrings
- Add logging for debugging

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/elbruno/ntn-podcast-creator/issues
- Pull Requests: https://github.com/elbruno/ntn-podcast-creator/pulls

---

**Document Version:** 1.0  
**Last Updated:** November 2025  
**Author:** NTN Podcast Creator Team
