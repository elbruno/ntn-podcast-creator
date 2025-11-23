# NTN Podcast Creator

A local Python application with a user-friendly web interface for editing podcast audio. This tool helps you create professional-sounding podcasts by combining your voice recordings with intro/outro audio and background music, with advanced individual volume controls for each track.

## 📖 Documentation

- **[User Manual](docs/USER_MANUAL.md)** - Complete guide with step-by-step instructions and screenshots
- **[Docker Deployment Guide](docs/DOCKER.md)** - Run with Docker in minutes (no Python/FFmpeg install needed)
- **[Technical Implementation](docs/TECHNICAL_IMPLEMENTATION.md)** - Architecture, technical details, and API reference
- **[Dev Container Guide](.devcontainer/README.md)** - Setup instructions for containerized development

## Features

- **Upload podcast voice file**: Upload your pre-recorded podcast audio
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
- **Download Options**: Download both generated podcasts and configuration settings

## Requirements

- Python 3.8 or higher
- FFmpeg (required for audio processing)
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

2. Install FFmpeg (see instructions below)

3. Install Python dependencies:
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

3. Follow the interface steps:
   - Upload your main podcast voice recording
   - (Optional) Upload intro audio file
   - (Optional) Upload outro audio file
   - (Optional) Upload background music tracks
   - Adjust global or individual track volume settings (default: 10%)
   - Preview tracks with applied volume
   - Enter output filename
   - Click "Create Podcast"
   - Download your finished podcast
   - (Optional) Download or import settings

**📖 For detailed instructions with screenshots, see the [User Manual](docs/USER_MANUAL.md)**

### Interface Preview

![NTN Podcast Creator Interface](https://github.com/user-attachments/assets/84e1807d-889c-4546-8614-6aef13d2c798)

The interface guides you through simple steps to create your podcast with advanced volume controls.

## New Features

### Individual Volume Controls (Latest)
- **Per-Track Volume**: Set different volume levels for each background music file
- **Global Volume**: Apply a single volume setting to all tracks at once
- **Preview with Volume**: Listen to each track with the applied volume before creating your podcast
- **Timeline Display**: See all background tracks and their volume settings in the visual timeline

### Settings Management (Latest)
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

These settings persist between sessions, so you don't need to reconfigure each time. You can also export settings to share with others or backup for different podcast configurations.

## Project Structure

```
ntn-podcast-creator/
├── .devcontainer/          # Dev container configuration
│   ├── devcontainer.json   # Container setup
│   └── README.md           # Dev container documentation
├── docs/                   # Documentation
│   ├── USER_MANUAL.md      # Complete user guide with screenshots
│   └── TECHNICAL_IMPLEMENTATION.md  # Technical details and architecture
├── app.py                  # Main application with Gradio UI
├── audio_processor.py      # Audio processing logic
├── config_manager.py       # Configuration persistence
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── LICENSE                 # License information
├── audios/                 # Audio assets directory
│   ├── intro_audio/        # Intro audio files
│   ├── outro_audio/        # Outro audio files
│   └── background_music/   # Background music tracks
├── config.json            # User settings (auto-generated)
├── uploads/               # Uploaded files (auto-generated)
└── outputs/               # Generated podcasts (auto-generated)
```

## Technical Details

For developers and those interested in the technical implementation:
- See [TECHNICAL_IMPLEMENTATION.md](docs/TECHNICAL_IMPLEMENTATION.md) for detailed architecture, API reference, and technical specifications
- Built with Python, Gradio, pydub, and FFmpeg
- Modular architecture with separation of concerns
- Logarithmic volume scaling for natural sound perception
- Random track selection with looping for varied background music
- 1-second crossfade overlaps between segments for smooth transitions

## License

MIT License - see LICENSE file for details

