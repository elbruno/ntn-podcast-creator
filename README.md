# NTN Podcast Creator

A local Python application with a user-friendly web interface for editing podcast audio. This tool helps you create professional-sounding podcasts by combining your voice recordings with intro/outro audio and background music.

## Features

- **Upload podcast voice file**: Upload your pre-recorded podcast audio
- **Intro & Outro**: Set custom intro and outro audio files
- **Background Music**: Add background music tracks that automatically loop to match your podcast duration
- **Volume Control**: Adjustable background music volume (default: 10-12% of original)
- **Settings Persistence**: All settings are automatically saved for future sessions
- **Easy Export**: Generate final podcast as MP3 file

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

### Option 1: Using Dev Container (Recommended)

If you use Visual Studio Code, you can use the included dev container for the easiest setup:

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code
3. Clone this repository and open it in VS Code
4. When prompted, click "Reopen in Container" (or press F1 and select "Dev Containers: Reopen in Container")
5. Wait for the container to build - FFmpeg and all dependencies will be installed automatically
6. Run `python app.py` in the VS Code terminal

The dev container includes everything you need: Python 3.12, FFmpeg, and all Python dependencies.

### Option 2: Local Installation

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

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to the URL shown in the terminal (typically http://127.0.0.1:7860)

3. Configure your podcast:
   - Upload your main podcast voice recording
   - (Optional) Upload intro audio file
   - (Optional) Upload outro audio file
   - (Optional) Upload background music tracks
   - Adjust background music volume (default: 10%)
   - Enter output filename

4. Click "Create Podcast" to generate your final podcast file

5. Download the generated MP3 file

## Configuration

Settings are automatically saved to `config.json` in the application directory. This includes:
- Paths to intro/outro files
- Background music track paths
- Volume settings

These settings persist between sessions, so you don't need to reconfigure each time.

## Project Structure

```
ntn-podcast-creator/
├── .devcontainer/          # Dev container configuration
│   ├── devcontainer.json   # Container setup
│   └── README.md           # Dev container documentation
├── app.py                  # Main application with Gradio UI
├── audio_processor.py      # Audio processing logic
├── config_manager.py       # Configuration persistence
├── requirements.txt        # Python dependencies
├── config.json            # User settings (auto-generated)
├── uploads/               # Uploaded files (auto-generated)
└── outputs/               # Generated podcasts (auto-generated)
```

## License

MIT License - see LICENSE file for details
