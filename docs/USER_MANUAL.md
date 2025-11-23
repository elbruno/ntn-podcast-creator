# NTN Podcast Creator - User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Interface Overview](#interface-overview)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [Features in Detail](#features-in-detail)
6. [Tips and Best Practices](#tips-and-best-practices)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Introduction

Welcome to the **NTN Podcast Creator**! This application helps you create professional-sounding podcasts by combining your voice recordings with intro/outro audio and background music. All settings are automatically saved, making it easy to maintain consistency across multiple podcast episodes.

### What Can You Do?

- ✅ Add custom intro and outro audio to your podcast
- ✅ Mix background music that automatically loops to match your recording
- ✅ Control background music volume with precision - both globally and per-track
- ✅ Apply different volume levels to each background music file
- ✅ Preview tracks with applied volume settings before creating your podcast
- ✅ Save and export your configuration settings as JSON files
- ✅ Import previously saved settings to quickly recreate your setup
- ✅ View all background tracks and their volumes in the visual timeline
- ✅ Save all settings automatically for future podcast episodes
- ✅ Export professional MP3 files ready for distribution

---

## Getting Started

### Prerequisites

Before using the NTN Podcast Creator, ensure you have:

- **Python 3.8 or higher** installed on your system
- **FFmpeg** installed (required for audio processing)
- Audio files ready (your podcast recording, optional intro/outro, optional background music)

### Installation Methods

#### Option 1: Using Docker (Fastest & Easiest)

No need to install Python or FFmpeg! Docker handles everything:

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Clone the repository:
   ```bash
   git clone https://github.com/elbruno/ntn-podcast-creator.git
   cd ntn-podcast-creator
   ```
3. Start with Docker Compose:
   ```bash
   docker-compose up -d
   ```
4. Open your browser to `http://localhost:7860`

**📖 See [Docker Deployment Guide](DOCKER.md) for detailed instructions**

#### Option 2: Using Dev Container (For VS Code Users)

If you use Visual Studio Code:

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. Open the repository in VS Code
4. Click "Reopen in Container" when prompted
5. Everything installs automatically!

#### Option 3: Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/elbruno/ntn-podcast-creator.git
   cd ntn-podcast-creator
   ```

2. **Install FFmpeg:**
   
   - **Ubuntu/Debian:**
     ```bash
     sudo apt-get update && sudo apt-get install ffmpeg
     ```
   
   - **macOS:**
     ```bash
     brew install ffmpeg
     ```
   
   - **Windows:** Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Starting the Application

#### If Using Docker:
```bash
# Start (if not already running)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access at `http://localhost:7860`

#### If Using Local Installation:
1. Open a terminal in the project directory
2. Run the application:
   ```bash
   python app.py
   ```
3. Open your web browser and navigate to: `http://127.0.0.1:7860`
4. The interface will load automatically

---

## Interface Overview

![NTN Podcast Creator Interface](https://github.com/user-attachments/assets/84e1807d-889c-4546-8614-6aef13d2c798)

The interface is divided into 6 main sections:

### 1. Upload Your Podcast Voice Recording
- **Purpose:** Upload your main podcast audio file
- **Supported formats:** MP3, WAV, M4A, OGG, and other common audio formats
- **Options:** 
  - Upload a file from your computer
  - Record audio directly (if your browser supports it)

### 2. Optional: Set Intro Audio
- **Purpose:** Add audio that plays before your main recording
- **Use cases:** Theme music, podcast intro jingle, sponsor message
- **Status display:** Shows confirmation when intro is uploaded

### 3. Optional: Set Outro Audio
- **Purpose:** Add audio that plays after your main recording
- **Use cases:** Closing music, call-to-action, credits
- **Status display:** Shows confirmation when outro is uploaded

### 4. Optional: Add Background Music
- **Purpose:** Add background music tracks that play throughout your podcast
- **Features:**
  - Upload multiple tracks
  - Random selection (one track chosen per podcast creation)
  - Automatic looping to match your podcast duration
  - View list of all uploaded background tracks
  - Clear all tracks with one button

### 5. Configure Background Volume
- **Purpose:** Adjust how loud the background music is relative to your voice
- **Range:** 0% to 50%
- **Recommended:** 10-12% for clear voice quality
- **Live preview:** Shows current volume setting

### 6. Create Your Podcast
- **Output filename:** Choose the name for your final podcast (without .mp3 extension)
- **Create button:** Process and mix all audio elements
- **Status:** Real-time feedback during processing
- **Download:** Play or download your finished podcast

---

## Step-by-Step Guide

### Basic Workflow: Creating Your First Podcast

#### Step 1: Upload Your Main Voice Recording

1. Click on the **"Main Voice Recording"** upload area
2. Select your podcast audio file from your computer
3. Wait for the upload to complete
4. You'll see a waveform or audio player appear

**💡 Tip:** Make sure your voice recording is already edited and ready. This tool combines audio but doesn't edit individual tracks.

#### Step 2: (Optional) Add an Intro

1. Click on the **"Intro Audio"** upload area
2. Select your intro audio file
3. The "Intro Status" field will confirm the upload
4. Your intro will play before your main recording

**💡 Tip:** Keep intros short (10-30 seconds) to maintain listener engagement.

#### Step 3: (Optional) Add an Outro

1. Click on the **"Outro Audio"** upload area
2. Select your outro audio file
3. The "Outro Status" field will confirm the upload
4. Your outro will play after your main recording

**💡 Tip:** Use outros to encourage listeners to subscribe, rate, or visit your website.

#### Step 4: (Optional) Add Background Music

1. Click on the **"Upload Background Music Track"** area
2. Select a music file
3. Click the **"Add Background Track"** button
4. The track appears in the "Current Background Tracks" list
5. Repeat to add more tracks (optional)

**💡 Tip:** Upload multiple tracks for variety. The app randomly selects one each time you create a podcast.

**Features:**
- **Random selection:** One track is chosen randomly from your library
- **Automatic looping:** The selected track repeats to fill your entire podcast duration
- **Track management:** View all uploaded tracks and clear them if needed

#### Step 5: Adjust Background Music Volume

1. Use the slider under **"Background Music Volume (%)"**
2. Drag left to decrease, right to increase
3. Recommended: 10-12% for clear voice
4. The "Volume Status" updates as you adjust

**Volume Guidelines:**
- **5-8%:** Very subtle background ambiance
- **10-12%:** Recommended for most podcasts (clear voice, pleasant background)
- **15-20%:** More prominent music (ensure voice remains clear)
- **25%+:** Only for segments without speaking

#### Step 6: Create Your Podcast

1. Enter a filename in **"Output Filename"** (without .mp3)
   - Example: `episode_001` or `my_awesome_podcast`
   
2. Click the **"🎬 Create Podcast"** button

3. Wait while the application:
   - Loads all audio files
   - Adds intro (if provided)
   - Adds your main voice recording
   - Adds outro (if provided)
   - Creates and loops background music
   - Mixes background at your specified volume
   - Exports as MP3

4. Progress updates appear in the "Status" field

#### Step 7: Download Your Podcast

1. Once processing completes, a success message appears
2. An audio player shows your finished podcast
3. Click the download button to save the MP3 file
4. Test the audio to ensure quality

**💡 Tip:** Listen to the entire podcast before publishing to ensure all elements mixed correctly.

---

## Features in Detail

### Settings Persistence

**What is it?**
All your settings are automatically saved to a `config.json` file in the application directory.

**What gets saved:**
- ✅ Intro audio file path
- ✅ Outro audio file path
- ✅ All background music track paths
- ✅ Background music volume setting
- ✅ Last output filename

**How it helps:**
- No need to re-upload intro/outro for each episode
- Maintain consistent branding across episodes
- Quick podcast creation for regular shows

**When settings reset:**
- If you delete `config.json`
- If you move audio files to different locations
- If you explicitly clear settings

### Background Music System

**Random Selection:**
When you have multiple background tracks uploaded, the application randomly selects one each time you create a podcast. This adds variety to your episodes without manual work.

**Automatic Looping:**
The selected background music automatically repeats (loops) to match the exact duration of your podcast. You don't need to worry about:
- Music being too short
- Music being too long
- Timing the music to your voice

**Volume Adjustment:**
Background music volume is reduced using professional audio techniques:
- Uses logarithmic scaling for natural sound
- 10% volume = -20 dB reduction
- 50% volume = -6 dB reduction

### Audio Processing

**Supported Input Formats:**
- MP3 (MPEG Audio Layer 3)
- WAV (Waveform Audio File Format)
- M4A (MPEG-4 Audio)
- OGG (Ogg Vorbis)
- FLAC (Free Lossless Audio Codec)
- And many more supported by FFmpeg

**Output Format:**
- Always exports as MP3 for maximum compatibility
- Maintains good quality while keeping file size reasonable
- Ready for upload to podcast platforms

**Audio Sequence:**
```
[Intro] → [Main Voice] → [Outro]
         (with background music underneath entire podcast)
```

### File Management

**Upload Directory:**
All uploaded files are stored in `uploads/` directory:
- Organized storage
- Files persist between sessions
- Easy to manage and backup

**Output Directory:**
Generated podcasts are saved in `outputs/` directory:
- All your created podcasts in one place
- Named according to your specification
- Never overwrites existing files automatically

---

## Tips and Best Practices

### Audio Quality Tips

1. **Record in a quiet environment**
   - Minimize background noise in your voice recording
   - The mixer can't remove noise from your original audio

2. **Use consistent audio levels**
   - Normalize your voice recording before upload
   - Avoid recordings that are too quiet or too loud

3. **Choose appropriate background music**
   - Instrumental works best (no competing vocals)
   - Avoid music with dramatic volume changes
   - Use royalty-free music to avoid copyright issues

4. **Test volume levels**
   - Start with 10% background volume
   - Create a test podcast and listen
   - Adjust if needed

### Workflow Efficiency

1. **Set up once, reuse many times**
   - Upload your intro/outro once
   - Add all your background music tracks
   - Set your preferred volume
   - Create multiple episodes quickly

2. **Organize your audio files**
   - Keep source files separate from outputs
   - Use consistent naming (episode_001.mp3, episode_002.mp3)
   - Back up your config.json file

3. **Quality check before publishing**
   - Always listen to the full podcast
   - Check intro/outro transitions
   - Verify background music isn't too loud or too quiet
   - Test on different devices (headphones, speakers, phone)

### Background Music Strategy

1. **Build a library**
   - Upload 3-5 different background tracks
   - Provides variety across episodes
   - Keeps your podcast fresh

2. **Match the mood**
   - Upbeat music for energetic podcasts
   - Calm music for informative content
   - Match music style to your brand

3. **Consider your audience**
   - Some listeners prefer no background music
   - Others enjoy subtle ambiance
   - Survey your audience for preferences

---

## Advanced Features

### Individual Volume Control for Background Tracks

**New in Latest Version!**

You can now set different volume levels for each background music file, giving you precise control over how your podcast sounds.

#### How to Use Individual Volume Control

1. **Navigate to Settings Tab**
   - Click on the "Settings" tab
   - Scroll down to the "Background Music" section

2. **Select a Track**
   - In the dropdown menu labeled "Select Track to Play or Delete"
   - Choose the background track you want to adjust
   - The track will load in the audio player

3. **Adjust Individual Volume**
   - Use the "Selected Track Volume (%)" slider
   - Range: 0-50% (recommended: 10-12%)
   - Changes are saved immediately
   - Preview the track with the new volume in "Preview Track with Applied Volume"

4. **Apply to All Tracks**
   - Set the "Default Background Music Volume (%)" slider to your desired level
   - Click the "📢 Apply Volume to All Tracks" button
   - All background tracks will now use this volume level

#### Volume Control Tips

- **Different moods**: Use lower volume (5-8%) for intense, dramatic sections
- **Variety**: Use higher volume (12-15%) for intros/outros, lower for main content
- **Consistency**: Use "Apply to All" when you want uniform background volume
- **Preview first**: Always listen to the preview before creating your final podcast

#### Visual Timeline Display

The timeline preview now shows:
- **All background tracks** that will be used in your podcast
- **Volume level** for each track
- **Color-coded segments** for easy identification

Example:
```
🎼 Background Tracks:
  • track1.mp3 - Volume: 10%
  • track2.mp3 - Volume: 15%
  • track3.mp3 - Volume: 8%
```

---

### Settings Export and Import

**New in Latest Version!**

Save and load your entire configuration, making it easy to:
- Backup your settings
- Share configurations with team members
- Switch between different podcast styles
- Recreate a specific setup quickly

#### Exporting Settings

1. **Create Your Perfect Setup**
   - Configure intro, outro, and background tracks
   - Adjust all volume levels
   - Test and refine until satisfied

2. **Export Configuration**
   - In the "Create Podcast" tab
   - Click "💾 Download Settings"
   - A JSON file will be generated with a timestamp
   - Save this file to your computer

3. **What Gets Exported**
   - Intro file path
   - Outro file path
   - All background music tracks
   - Global volume setting
   - Individual track volumes
   - Last output filename
   - Export date/time

#### Importing Settings

1. **Prepare Settings File**
   - Locate your previously exported JSON settings file
   - Ensure audio files referenced still exist in the same locations

2. **Import Configuration**
   - In the "Create Podcast" tab
   - Under "Import Settings"
   - Click "Upload Settings File (JSON)"
   - Select your JSON file
   - Wait for "Import Status" to confirm success

3. **Verify Imported Settings**
   - Go to the "Settings" tab
   - Check that all audio files loaded correctly
   - Verify volume levels
   - Make any necessary adjustments

#### Use Cases for Export/Import

**Different Podcast Series:**
```
- Weekly_News_Show_Settings.json (low background, formal intro)
- Interview_Series_Settings.json (moderate background, friendly intro)
- Story_Time_Settings.json (high background, dramatic intro)
```

**Team Collaboration:**
```
- Share settings with co-hosts
- Maintain consistent branding
- New team members can quickly get started
```

**Backup and Recovery:**
```
- Regular backups before major changes
- Restore previous configurations
- Version control for your podcast setup
```

#### Settings File Format

The exported JSON file looks like this:
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
  "last_output_name": "podcast_output",
  "export_date": "YYYY-MM-DDTHH:MM:SS"
}
```

**💡 Tip:** Keep a folder of settings files for different podcast types or seasons!

---

## Troubleshooting

### Common Issues and Solutions

#### App Won't Start

**Problem:** Error when running `python app.py`

**Solutions:**
1. Check Python version: `python --version` (need 3.8+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check for FFmpeg: `ffmpeg -version`
4. Review error messages in terminal

#### FFmpeg Not Found

**Problem:** "FFmpeg not found" or similar error

**Solutions:**
1. **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
2. **macOS:** `brew install ffmpeg`
3. **Windows:** Download from ffmpeg.org and add to PATH
4. Verify installation: `ffmpeg -version`

#### Upload Fails

**Problem:** Audio file won't upload

**Solutions:**
1. Check file format (use common formats: MP3, WAV)
2. Check file size (very large files may timeout)
3. Check file permissions (can the app read the file?)
4. Try a different file to isolate the issue

#### Background Music Too Loud/Quiet

**Problem:** Background music overpowers voice or is barely audible

**Solutions:**
1. Adjust the volume slider
2. Recommended range: 10-12%
3. Create test podcasts to find your sweet spot
4. Consider your source audio levels

#### Output File Not Created

**Problem:** Podcast creation finishes but no file appears

**Solutions:**
1. Check the `outputs/` directory
2. Look for error messages in the Status field
3. Verify all input files exist and are readable
4. Check disk space
5. Try with a simpler podcast (voice only, no extras)

#### Settings Not Saving

**Problem:** Need to re-upload files each time

**Solutions:**
1. Check if `config.json` file exists
2. Check file permissions (can the app write?)
3. Don't move uploaded files after adding them
4. Don't delete the `uploads/` directory

#### Browser Can't Connect

**Problem:** Can't access http://127.0.0.1:7860

**Solutions:**
1. Verify app is running (check terminal)
2. Check if port 7860 is available
3. Try http://localhost:7860 instead
4. Check firewall settings
5. Try a different browser

---

## FAQ

### General Questions

**Q: Do I need an internet connection?**
A: No, the app runs entirely locally on your machine. No internet required after installation.

**Q: Is my audio data sent anywhere?**
A: No, all processing happens on your local machine. Your audio never leaves your computer.

**Q: What audio formats are supported?**
A: Most common formats: MP3, WAV, M4A, OGG, FLAC, and more. If FFmpeg can read it, the app can use it.

**Q: Can I use copyrighted music?**
A: This is a legal question. Use only music you have rights to use. Consider royalty-free music libraries.

**Q: How large can my audio files be?**
A: Limited only by your computer's RAM and disk space. However, very large files (>1 GB) may process slowly.

### Technical Questions

**Q: What is FFmpeg and why do I need it?**
A: FFmpeg is an audio/video processing library. It handles the actual audio encoding and decoding. The app uses it to read, process, and export audio files.

**Q: Can I use this in a Docker container?**
A: Yes! There's a dev container configuration included. See the .devcontainer/ directory.

**Q: Does it work on Windows/Mac/Linux?**
A: Yes, the app works on all platforms that support Python 3.8+ and FFmpeg.

**Q: Can I modify the code?**
A: Yes! It's open source (MIT License). Fork it, modify it, make it your own.

**Q: Where are my files stored?**
A:
- Uploaded files: `uploads/` directory
- Output podcasts: `outputs/` directory  
- Settings: `config.json` file
- All in the application directory

### Usage Questions

**Q: Can I skip intro/outro/background music?**
A: Yes, all three are optional. Upload only your voice recording if you prefer.

**Q: Can I use the same intro/outro for multiple episodes?**
A: Yes! That's the point of settings persistence. Upload once, use for all episodes.

**Q: How do I change my intro/outro?**
A: Just upload a new file. It will replace the previous one.

**Q: Can I remove background music after adding it?**
A: Yes, click "Clear All Background Tracks" button. Or create the podcast without uploading any background music.

**Q: What if I want different volumes for different episodes?**
A: You can now:
1. Set different volumes for each background track individually
2. Export your settings for each episode type
3. Import the appropriate settings when creating each episode

**Q: Can I use different volumes for different background music tracks?**
A: Yes! The new individual volume control feature allows you to:
1. Go to Settings tab
2. Select each background track
3. Adjust its volume independently
4. Preview the track with the applied volume

**Q: How do I save my settings for different podcast styles?**
A: Use the Export/Import feature:
1. Set up your configuration (intro, outro, volumes)
2. Click "💾 Download Settings"
3. Save the JSON file with a descriptive name
4. Import it later when you need that configuration

**Q: Can I share my settings with a team member?**
A: Yes! Export your settings as a JSON file and share it. Your team member can import it, but they'll need access to the same audio files (or files in the same locations).

**Q: Can I edit my voice recording in this app?**
A: No, this app mixes audio, it doesn't edit. Use audio editing software (Audacity, Adobe Audition) to edit your voice recording first.

**Q: How do I make a podcast series with consistent branding?**
A: 
1. Upload your intro/outro once
2. Add background music tracks
3. Set your preferred volumes (global or per-track)
4. Export these settings for backup
5. Create each episode by just uploading new voice recordings

**Q: Can I preview before creating the final file?**
A: Yes! You can:
1. Preview each background track with its applied volume in the Settings tab
2. View the timeline preview to see how segments will be arranged
3. Create a test podcast with a short voice recording

**Q: Why would I want different volumes for different tracks?**
A: Different scenarios:
- One track for intense moments (lower volume)
- Another for transitions (higher volume)
- Variety in long podcasts to maintain listener interest
- Match track energy to content (calm vs. upbeat)

### Troubleshooting Questions

**Q: The app is running but I can't see it in my browser**
A: Make sure you're going to the correct URL: http://127.0.0.1:7860 or http://localhost:7860

**Q: Processing is very slow**
A: 
- Large files take longer to process
- Close other applications to free up resources
- Consider using shorter audio files for testing
- Background music looping is calculated and may take a moment

**Q: My output sounds distorted**
A:
- Lower the background music volume
- Check if your source audio is too loud (clipping)
- Ensure source files are good quality

**Q: Can I cancel podcast creation once started?**
A: Yes, you can refresh the page or close the app. No partial files are created.

---

## Additional Resources

### Learn More

- **GitHub Repository:** [github.com/elbruno/ntn-podcast-creator](https://github.com/elbruno/ntn-podcast-creator)
- **Report Issues:** Use GitHub Issues for bug reports and feature requests
- **FFmpeg Documentation:** [ffmpeg.org/documentation.html](https://ffmpeg.org/documentation.html)
- **Gradio Documentation:** [gradio.app/docs](https://gradio.app/docs)

### Royalty-Free Music Sources

Looking for background music? Try these royalty-free sources:
- YouTube Audio Library
- Free Music Archive
- Incompetech
- Purple Planet Music
- Bensound

*Always check licensing terms before using any music in your podcast.*

### Community

Share your experiences, ask questions, and connect with other users:
- GitHub Discussions
- Issue tracker for bugs and features
- Pull requests welcome!

---

## Conclusion

Congratulations! You now know how to use the NTN Podcast Creator to create professional-sounding podcasts with intro/outro audio and background music. 

Remember:
- Start simple (voice only) and add features as you get comfortable
- Settings are saved automatically for efficiency
- Quality source audio leads to quality output
- Experiment with different background music volumes
- Listen to your output before publishing

Happy podcasting! 🎙️

---

*Last updated: November 2025*
*Version: 1.0*
