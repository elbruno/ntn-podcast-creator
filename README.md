# NTN Podcast Creator

A local Python application with a user-friendly web interface for editing podcast audio. This tool helps you create professional-sounding podcasts by combining your voice recordings with intro/outro audio and background music, with advanced individual volume controls for each track.

## 📖 Documentation

- **[User Manual](docs/USER_MANUAL.md)** - Complete guide with step-by-step instructions and screenshots
- **[Docker Deployment Guide](docs/DOCKER.md)** - Run with Docker in minutes (no Python/FFmpeg install needed)
- **[Technical Implementation](docs/TECHNICAL_IMPLEMENTATION.md)** - Architecture, technical details, and API reference
- **[Dev Container Guide](.devcontainer/README.md)** - Setup instructions for containerized development
- **[Release Notes](docs/RELEASE_NOTES_CHUNKING.md)** - Latest feature updates and enhancements

## Features

- **Intuitive Multi-Tab Interface**: Easy navigation with dedicated tabs for podcast creation, audio processing, settings, and logs
- **Smart Episode Naming**: Automatically suggests episode names with date (yymmdd) + your file name
- **Professional Audio Processing**:
  - **Multiple Noise Reduction Methods**: Choose between AI Denoiser, Spectral Gating, or FFmpeg RNNoise
  - **LUFS Normalization**: Professional loudness normalization to broadcast standards (-16 LUFS)
  - **Automatic Transcription**: Generate accurate transcripts with OpenAI Whisper (99+ languages)
  - **Adobe Enhance Integration**: Optional cloud-based AI audio enhancement
- **Advanced Audio Mixing**:
  - Custom intro and outro audio files
  - Background music that automatically loops to match podcast duration
  - Individual volume control for each background track
  - Visual timeline showing audio segment arrangement
- **Large File Support**:
  - Process files of any size with automatic chunking (>10MB)
  - Intelligent chunk processing with seamless audio reconstruction
  - Memory-efficient processing for long-form content
- **Settings Persistence**: All settings automatically saved for future sessions
- **Export/Import Settings**: Save and load configuration as JSON files
- **Professional Output**: Generate broadcast-quality MP3 files

## ✨ Key Features

### 🎚️ Professional Audio Processing

**Multiple Noise Reduction Methods:**
- **AI Denoiser** (Recommended): 38M-parameter deep learning model for general speech enhancement
- **Spectral Gating**: Fast spectral subtraction ideal for stationary noise (fans, hums)
- **FFmpeg RNNoise**: RNN-based noise suppression for real-time style processing

**LUFS Normalization:**
- Professional loudness normalization to broadcast standards
- Two-pass processing for maximum accuracy
- Configurable targets: -16 LUFS (podcasts), -14 LUFS (streaming), -23 LUFS (radio)
- Ensures consistent volume across all episodes

**Automatic Transcription:**
- Generate accurate transcripts using OpenAI's Whisper
- 5 model sizes: Tiny (fast) to Large (best quality)
- Timestamped transcripts with word-level timing
- 99+ languages with automatic detection
- Completely offline after initial model download

### 🚀 Large File Support

Process audio files of any size with intelligent automatic chunking:

- **No File Size Limits**: Handle recordings of any length
- **Intelligent Chunking**: Large files (>10MB) automatically split into 8MB chunks
- **Seamless Reconstruction**: Processed chunks merged with perfect audio continuity
- **Memory Efficient**: Process 100MB+ files without memory issues
- **Progress Tracking**: Real-time updates during processing
- **Robust Error Handling**: Graceful fallback if any chunk fails

**Perfect for:**
- Long-form podcasts (1+ hours)
- Interview recordings and conference presentations
- Educational content and audiobooks

**Processing Times (approximate):**
- 50MB file (30 minutes): ~2-3 minutes
- 100MB file (60 minutes): ~5-7 minutes
- 200MB file (2 hours): ~10-12 minutes

## Requirements

- Python 3.8 or higher
- FFmpeg 4.0+ (required for audio processing, LUFS normalization)
- **Audio Processing Libraries** (included in requirements.txt):
  - `audio-denoiser` - AI-powered noise removal
  - `noisereduce` - Spectral gating noise reduction
  - `openai-whisper` - Automatic transcription
  - PyTorch and torchaudio - Deep learning framework
- **Optional**: Playwright and Chromium browser (for Adobe Enhance feature)
- **Optional**: Docker and VS Code with Dev Containers extension (for containerized development)

### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH.

## Installation

### Option 1: Using Docker (Recommended for Easy Setup)

The fastest way to get started is with Docker. No need to install Python or FFmpeg manually!

```bash
# Clone the repository
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator

# Start with Docker Compose
cd deployment
docker-compose up -d

# Access the application at http://localhost:7860
```

**📖 For detailed Docker instructions, see [Docker Deployment Guide](docs/DOCKER.md)**

### Option 2: Using Dev Container (For Development)

If you use Visual Studio Code, you can use the included dev container:

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code
3. Clone this repository and open it in VS Code
4. When prompted, click "Reopen in Container" (or press F1 and select "Dev Containers: Reopen in Container")
5. Wait for the container to build - FFmpeg and all dependencies will be installed automatically
6. Run `python app.py` in the VS Code terminal

The dev container includes everything you need: Python 3.12, FFmpeg, and all Python dependencies.

### Option 3: Local Installation

1. Clone this repository:
```bash
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator
```

2. Run the setup script (recommended):
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Or install manually:
3. Install FFmpeg (see instructions below)
4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

#### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH.

## Usage

### Quick Start

#### If Using Docker:
```bash
# Start the application (if not already running)
cd deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

Access the application at http://localhost:7860

#### If Using Local Installation:
1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to http://127.0.0.1:7860

### Creating Your Podcast

3. Follow the interface steps in the **🎙️ Create Podcast** tab:
   - Upload your main podcast voice recording
   - The episode name is auto-suggested with today's date (yymmdd) + your file name
   - Adjust options in the accordion (denoise, trim silence, Adobe Enhance)
   - Click "Create Podcast"
   - Download your finished podcast and cleaned audio
   - (Optional) Configure intro, outro, and background music in the **⚙️ Settings** tab
   - (Optional) Use the **✨ Adobe Enhance** tab to clean audio files before creating podcasts

**📖 For detailed instructions with screenshots, see the [User Manual](docs/USER_MANUAL.md)**

### Interface Preview

![NTN Podcast Creator Interface](https://github.com/user-attachments/assets/d4d6010f-fec0-4a44-b15c-a2fe40809dc6)

The interface features multiple tabs for easy navigation:
- **🎙️ Create Podcast**: Main tab for uploading voice and creating podcasts
- **✨ Adobe Enhance**: Standalone audio enhancement tool
- **⚙️ Settings**: Configure intro, outro, and background music
- **📋 Console Log**: View detailed processing logs

## New Features

### Improved UI/UX (Latest)
- **Multi-Tab Interface**: Organized tabs with emoji icons for easy navigation
  - 🎙️ **Create Podcast**: Main tab for podcast creation
  - ✨ **Adobe Enhance**: Dedicated tab for standalone audio enhancement
  - ⚙️ **Settings**: Configure audio files and volumes
  - 📋 **Console Log**: View detailed processing logs
- **Smart Episode Naming**: Automatically suggests episode names with date (yymmdd) + your file name
- **Simplified Main Tab**: Cleaner interface with options in an accordion
- **Improved Adobe Enhance Workflow**: Separate tab with clear instructions and dedicated upload

### AI Audio Denoising
- **Machine Learning Audio Cleanup**: Automatically clean voice recordings before podcast creation
  - Uses a 38-million parameter deep learning model
  - Removes background noise, hum, and ambient sounds
  - Works offline once the model is downloaded
  - Significantly improves speech clarity
- **Enabled by Default**: Audio denoising runs automatically for all podcasts
- **Download Cleaned Audio**: Get the denoised voice file separately for other projects
- **Graceful Fallback**: Continues with original audio if denoising library unavailable
- **Processing Chain**: Denoising runs first, then optionally Adobe Enhance, then podcast mixing
- **Fast Processing**: Typically completes in seconds (much faster than Adobe Enhance)

### Adobe Enhance Audio
- **AI-Powered Audio Cleanup**: Enhance voice recordings using Adobe Podcast Enhance Speech
  - Removes background noise and echo
  - Enhances speech clarity and audio quality
  - Normalizes audio levels automatically
- **Two Usage Modes**:
  - **Integrated Mode**: Checkbox to automatically enhance during podcast creation
  - **Standalone Mode**: Dedicated **✨ Adobe Enhance** tab with preview and download
- **Browser Automation**: Uses Playwright to interact with Adobe's web service
- **Progress Monitoring**: Detailed logs show upload, processing, and download status
- **Automatic Fallback**: Gracefully uses original audio if enhancement service is unavailable
- **Flexible Configuration**: Optional Adobe credentials via `.env` file
- **Processing Time**: Typically 2-5 minutes depending on file size

### Individual Volume Controls
- **Per-Track Volume**: Set different volume levels for each background music file
- **Global Volume**: Apply a single volume setting to all tracks at once
- **Preview with Volume**: Listen to each track with the applied volume before creating your podcast
- **Timeline Display**: See all background tracks and their volume settings in the visual timeline

### Settings Management
- **Export Settings**: Save your current configuration (intro, outro, background tracks, and volumes) as a JSON file
- **Import Settings**: Load previously saved configurations to quickly recreate your setup
- **Automatic Backup**: Settings are automatically saved, but you can create manual backups for different podcast styles

## Configuration

Settings are automatically saved to `config.json` in the application directory. This includes:
- Paths to intro/outro files
- Background music track paths
- Global volume settings
- Individual track volume settings
- Last used output filename
- Audio denoising preference (enabled/disabled, defaults to enabled)
- Audio enhancement preference (enabled/disabled)

Adobe Enhance credentials (optional) are stored in `.env` file:
```env
ADOBE_EMAIL=your-email@example.com
ADOBE_PASSWORD=your-password
ADOBE_ENHANCE_HEADLESS=true  # false to see browser (requires X server)
```

These settings persist between sessions, so you don't need to reconfigure each time. You can also export settings to share with others or backup for different podcast configurations.

## Project Structure

```
ntn-podcast-creator/
├── 📱 app.py                   # Main application entry point
├── 📄 requirements.txt         # Python dependencies
├── 📜 README.md                # Project overview and quick start
├── 📄 LICENSE                  # License file
│
├── 🔧 core/                    # Core application data
│   ├── __init__.py             # Core utilities and constants
│   └── config.json             # Application configuration
│
├── ⚙️ features/                # Feature implementations
│   ├── __init__.py             # Features package exports
│   ├── audio_processor.py      # Audio mixing and processing
│   ├── audio_denoiser_processor.py # AI denoising with chunking
│   ├── adobe_audio_enhancer.py # Adobe AI enhancement
│   └── config_manager.py       # Configuration management
│
├── 🧪 tests/                   # Test suite
│   ├── __init__.py             # Test package
│   ├── README.md               # Testing documentation
│   ├── test_audio_denoising.py # AI denoising tests
│   ├── test_audio_enhancement.py # Adobe enhancement tests
│   ├── test_large_file_denoising.py # Large file chunking tests
│   └── test_podcast_creation.py # End-to-end tests
│
├── 📚 docs/                    # Documentation
│   ├── README.md               # Documentation index
│   ├── USER_MANUAL.md          # Complete user guide
│   ├── TECHNICAL_IMPLEMENTATION.md # Technical architecture
│   ├── AUDIO_DENOISING_IMPLEMENTATION.md # AI denoising guide
│   ├── docs/STRUCTURE_IMPROVEMENTS.md # Project organization guide
│   └── RELEASE_NOTES_CHUNKING.md # Latest release notes
│
├── 🚀 scripts/                 # Utility scripts
│   ├── setup.sh               # Environment setup and verification
│   └── test_docker.sh          # Docker testing script
│
├── 🐳 deployment/              # Deployment configurations
│   ├── docker-compose.yml      # Docker Compose setup
│   ├── Dockerfile              # Container definition
│   ├── .dockerignore           # Docker ignore rules
│   └── .env.sample             # Environment variables template
│
├── 🎵 audios/                  # Audio assets
│   ├── intro_audio/            # Intro audio files
│   ├── outro_audio/            # Outro audio files
│   ├── background_music/       # Background music tracks
│   └── test/                   # Test audio files
│
├── 📤 outputs/                 # Generated podcasts (auto-generated)
├── 📥 uploads/                 # Temporary uploaded files (auto-generated)
└── 🔧 .devcontainer/           # VS Code dev container config
```

## Technical Details

For developers and those interested in the technical implementation:
- See [TECHNICAL_IMPLEMENTATION.md](docs/TECHNICAL_IMPLEMENTATION.md) for detailed architecture, API reference, and technical specifications
- Built with Python, Gradio, pydub, and FFmpeg
- Modular architecture with separation of concerns
- Logarithmic volume scaling for natural sound perception
- Random track selection with looping for varied background music
- 1-second crossfade overlaps between segments for smooth transitions

## 🧪 Testing

Comprehensive test suite available in the `tests/` folder:

### Running Tests
```bash
# Individual tests
python tests/test_audio_denoising.py
python tests/test_podcast_creation.py
python tests/test_large_file_denoising.py
python tests/test_audio_enhancement.py

# Docker deployment test
chmod +x tests/test_docker.sh
./tests/test_docker.sh
```

### Test Coverage
- ✅ AI audio denoising (including large file chunking)
- ✅ Podcast creation workflow
- ✅ Audio processing and mixing
- ✅ Configuration management
- ✅ Adobe enhancement integration
- ✅ Docker deployment validation
- ✅ Error handling and graceful degradation

See [tests/README.md](tests/README.md) for detailed testing information.

## License

MIT License - see LICENSE file for details

