# NTN Podcast Creator

A local Python application with a user-friendly web interface for editing podcast audio. This tool helps you create professional-sounding podcasts by combining your voice recordings with intro/outro audio and background music, with advanced individual volume controls for each track.

## 📖 Documentation

- **[User Manual](docs/USER_MANUAL.md)** - Complete guide with step-by-step instructions and screenshots
- **[Phase 2 Features](docs/PHASE2_IMPLEMENTATION.md)** - **NEW!** Advanced audio processing with multiple noise reduction methods, LUFS normalization, and Whisper transcription
- **[Docker Deployment Guide](docs/DOCKER.md)** - Run with Docker in minutes (no Python/FFmpeg install needed)
- **[Technical Implementation](docs/TECHNICAL_IMPLEMENTATION.md)** - Architecture, technical details, and API reference
- **[Dev Container Guide](.devcontainer/README.md)** - Setup instructions for containerized development
- **[AI Denoising Implementation](docs/AUDIO_DENOISING_IMPLEMENTATION.md)** - Complete documentation of the AI denoising feature
- **[Release Notes](docs/RELEASE_NOTES_CHUNKING.md)** - Latest feature updates and enhancements

## Features

- **Intuitive Multi-Tab Interface**: Easy navigation with dedicated tabs for podcast creation, Adobe Enhance, settings, and logs
- **Smart Episode Naming**: Automatically suggests episode names with date (yymmdd) + your file name
- **Upload podcast voice file**: Upload your pre-recorded podcast audio
- **AI Audio Denoising (Latest)**:
  - Automatically clean voice recordings using machine learning
  - Removes background noise using the `audio-denoiser` library
  - 38-million parameter deep learning model for speech enhancement
  - **NEW**: Supports files of any size with automatic chunking for large files (>10MB)
  - **NEW**: Intelligent chunk processing with seamless audio reconstruction
  - Enabled by default for all podcast creations
  - Download the cleaned audio separately for other uses
  - Graceful fallback to original audio if library unavailable
  - Dedicated **🤖 AI Denoiser** tab for standalone processing
- **Adobe Enhance Audio**:
  - Clean and enhance audio quality using Adobe's AI-powered Enhance Speech service
  - Available in dedicated **✨ Adobe Enhance** tab for standalone processing
  - Optional checkbox in main tab for automatic enhancement during podcast creation
  - Removes background noise, reduces echo, and improves speech clarity
  - Browser automation via Playwright (2-5 minute processing time)
  - Optional feature with automatic fallback to original audio
- **Intro & Outro**: Set custom intro and outro audio files
- **Background Music**: Add background music tracks that automatically loop to match your podcast duration
- **Individual Volume Control**: Set different volume levels for each background track
- **Apply to All**: Quickly apply the same volume setting to all background tracks
- **Preview with Volume**: Listen to tracks with applied volume settings before creating the podcast
- **Volume Control**: Adjustable background music volume (default: 10-12% of original)
- **Visual Timeline**: See exactly how your intro, voice, and outro segments are arranged with overlap indicators
- **Background Track Display**: View all background tracks with their volume settings in the timeline
- **Settings Persistence**: All settings are automatically saved for future sessions
- **Export/Import Settings**: Save and load your configuration as JSON files
- **Easy Export**: Generate final podcast as MP3 file
- **Download Options**: Download both generated podcasts, cleaned audio, and configuration settings

## ✨ What's New in Latest Version

### 🎛️ Phase 2: Advanced Audio Processing

Professional-grade audio processing features for broadcast-quality podcasts:

- **🎚️ Multiple Noise Reduction Methods**:
  - **AI Denoiser** (Recommended): 38M-parameter deep learning model
  - **Spectral Gating**: Fast spectral subtraction for stationary noise
  - **FFmpeg RNNoise**: RNN-based noise suppression
  - Choose the best method for your recording environment

- **📊 LUFS Normalization**:
  - Professional loudness normalization to broadcast standards
  - Two-pass processing for maximum accuracy
  - Configurable target: -16 LUFS (podcast standard) or -14 LUFS
  - Ensures consistent volume across all episodes

- **📝 Automatic Transcription with Whisper**:
  - Generate accurate transcripts using OpenAI's Whisper
  - 5 model sizes from Tiny (fast) to Large (best quality)
  - Timestamped transcripts with word-level timing
  - Supports 99+ languages with automatic detection
  - Completely offline after initial model download

- **🎛️ Modular Architecture**:
  - Mix and match processing methods
  - Optimized processing order for best results
  - All settings automatically saved
  - Ready for future API integrations

### 🚀 Large File Support for AI Denoising

The AI denoiser now supports **files of any size** through intelligent automatic chunking:

- **🎯 No File Size Limits**: Process recordings of any length (previously limited to 10MB)
- **🧠 Intelligent Chunking**: Large files automatically split into 8MB chunks for optimal processing
- **🔄 Seamless Reconstruction**: Processed chunks merged back with perfect audio continuity
- **💾 Memory Efficient**: Process 100MB+ files without memory issues
- **🧹 Auto Cleanup**: Temporary files automatically removed after processing
- **📊 Progress Tracking**: Real-time updates during chunk processing
- **🛡️ Robust Error Handling**: Graceful fallback if any chunk fails
- **⚡ Performance Optimized**: Faster processing for large files vs. cloud alternatives

**Perfect for:**
- Long-form podcasts (1+ hours)
- Interview recordings
- Conference presentations
- Educational content
- Any high-quality audio file >10MB

**Example Processing Times:**
- 50MB file (30 minutes): ~2-3 minutes
- 100MB file (60 minutes): ~5-7 minutes
- 200MB file (2 hours): ~10-12 minutes

The feature is completely transparent - upload any size file and the system automatically handles the complexity!

## Requirements

- Python 3.8 or higher
- FFmpeg (required for audio processing)
- PyTorch and audio-denoiser (optional, for AI audio denoising feature)
- Playwright and Chromium browser (optional, for Adobe Enhance audio feature)
- (Optional) Docker and VS Code with Dev Containers extension for containerized development

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

