# NTN Podcast Creator - User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Interface Overview](#interface-overview)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [Features in Detail](#features-in-detail)
6. [Tips and Best Practices](#tips-and-best-practices)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Introduction

Welcome to **NTN Podcast Creator**! Combine voice recordings with intro/outro audio and background music in a local, browser-based application. The upload-first workflow uses **saved defaults**, not unsaved Settings edits.

This guide describes the active `create_ui()` in `app.py`. The retained `_legacy_create_ui()` is unused; older screenshots and reports may show tabs or controls that are no longer part of the active interface.

### What Can You Do?

- Upload one or more recordings, review their order, and edit the suggested episode name.
- Create an episode from a snapshot of saved defaults; change them deliberately with **Save settings** or **Discard changes**.
- Set per-recording background music and a one-time intro without changing saved defaults.
- Use optional noise reduction, voice enhancement, normalization, transcription, and final quality checks.
- Manage audio assets, templates, and JSON settings files in **Settings**.
- Listen and download the exported MP3; reports, previews, cleaned voice, and transcripts appear only when available.

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
3. Start with Docker Compose from the `deployment/` directory:
   ```bash
   cd deployment
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
Run these commands from the `deployment/` directory:
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

There are two tabs: **Create Episode** and **Settings**. Standalone cleaning and
help are accordions in Settings, not separate tabs. Historical screenshots under
`docs/images/` are not a reference for the current layout.

### Create Episode

- **Upload recordings** accepts one or more audio files and lists their names and durations.
- **Recording order** appears only for multiple recordings; edit the numeric order, not the filenames.
- **Episode name** starts read-only with a suggested name. Click **Edit** to change it.
- **Create Episode** starts rendering. The **Saved settings** summary shows music count/global volume, intro/outro on/off, normalization target, and quality-check status. It is a compact summary, not every setting in the snapshot.
- **Change settings** switches to Settings.
- **Episode options** appears after upload: per-recording background music switches and **Custom intro for this episode only**.
- **Timeline & premix details** appears after upload and remains collapsed until opened. Its balance advice is not final-file QC.
- Progress and the expandable **Processing log** are inline, not floating overlays or a Console Log tab.
- Results appear after a successful export: **Your episode**, **Download episode**, **Create another**, and a quality summary. Additional files and previews are conditional.

### Settings: saved defaults versus drafts

Ordinary controls are drafts until **Save settings** succeeds. **Discard changes**
reloads saved values, including per-track volume drafts. Each episode takes a
detached snapshot of saved defaults when rendering starts; unsaved edits are not
used, and later settings changes do not alter that render.

The active UI organizes controls into the five Settings accordions below.
**Per-track volume drafts** is a separate accordion, described after these groups.

#### Podcast sound

- **Default intro** / **Default outro**: select an existing asset, or **None** to disable it, then save.
- **Default Background Music Volume (%)**: global volume, 0–50%.
- **Intro-voice overlap (1 second)** and **Voice-outro overlap (1 second)**.

#### Voice processing

- **Auto-balance voice & music levels (Recommended)** and **Auto-ducking**.
- **Trim silence from voice recording**.
- **Enable noise reduction**; select its **Noise Reduction Method** in **Advanced**.
- **Enable professional voice enhancement**; select its **Enhancement Preset** in **Advanced**. This is local voice processing, not an Adobe Enhance tab.

#### Output & quality

- **Normalize audio to professional LUFS level** and **Target LUFS Level** (−30 to −10; −16 is a typical podcast target).
- **Final Audio Quality Gate**: optional and disabled by default. Save before rendering to enable it.
- **Generate transcript with Whisper AI**: optional; download appears only if a transcript becomes available.
- **Delete voice recording after creation**: uploaded working copies may be removed. Keep your own originals for rerendering.

#### Naming & RSS

- **RSS Feed URL** supports the suggested episode name; it does not publish the episode to your feed.
- **Prefer Recording.m4a first** affects the initial order of multi-file uploads. Always review **Recording order**.
- To change this episode's name, return to **Create Episode** and click **Edit**. Do not rely on the legacy date-plus-upload-filename naming instructions.

#### Advanced

Processing choices, models, thresholds, and seed settings are grouped here:

- **Noise Reduction Method**: `audio_denoiser`, `spectral`, or `rnnoise`.
- **Enhancement Preset**: `podcast`, `light`, or `aggressive`.
- **Whisper Model**: `tiny`, `base`, `small`, `medium`, or `large`.
- **Minimum voice/music separation (dB)**: 0–40.
- **Audio quality thresholds (JSON)** (`audio_quality`): directly in **Advanced**, with no nested accordion; an empty object uses defaults.
- **Music seed**: reproducible track selection with the same ordered pool, sources, and settings, not a guarantee of identical encoded files across environments.

Save these controls along with the rest of the form. Invalid values produce
**Settings not saved** rather than applying part of the draft. See the
[quality guide](AUDIO_QUALITY_GATE.md) for threshold meanings and validation limits.

### Per-track volume drafts

In this separate Settings accordion, select **Background track**, adjust
**Selected Track Volume (%)**, or **Stage global volume for all tracks**. These
changes still require **Save settings**; there is no per-track preview player
in the active Settings UI.

### Actions that apply immediately

These are explicit exceptions to ordinary draft editing:

| Action | Effect |
|---|---|
| **Audio library — actions apply immediately → Add to library now** | Copies the asset into the library now. Background tracks join the saved pool immediately. Adding intro/outro assets does not select a saved default: select it and **Save settings**. |
| **Remove selected background track now** | Immediately removes the selected track from the saved pool; the underlying file is preserved. Select it in **Per-track volume drafts** first. |
| **Load and apply template** | Immediately applies template settings and refreshes the form from saved values, replacing drafts. |
| **Import and apply settings** | Immediately applies valid JSON settings and refreshes the form from saved values, replacing drafts. Uploading the JSON alone is not the apply action. |
| **Apply suggested settings for next render** | Saves QC-recommended defaults immediately and refreshes the form. Does not change current audio or rerender automatically. |

**Discard changes cannot undo these already applied actions.** After a library
action, review intro/outro selections before saving. Save any draft you want to
keep before loading a template, importing settings, or applying QC suggestions.

### Templates, Tools, and Help

- **Templates & settings files** contains template load/save/delete and JSON import/export. **Save saved settings as template** and **Export saved settings** use saved values, never an unsaved draft. Exported settings refer to audio paths; they do not bundle audio files.
- **Tools** offers **Recording to clean → Clean audio → Cleaned audio download**, plus status and a tool log. This standalone denoiser uses the saved upload-deletion setting and does not mix an episode.
- **Help & appearance** contains workflow reminders and **Theme** (`System`, `Light`, `Dark`). Theme changes apply to the current page; this guide does not promise persistence across reloads.

---

## Step-by-Step Guide

### 1. Upload and review episode inputs

In **Create Episode**, upload your edited source recordings. For multiple files,
review **Recording order** and change the numeric positions as needed. Review the
suggested **Episode name** and click **Edit** if necessary.

Open **Episode options** to turn background music on/off for each recording or
upload a one-time custom intro. These are episode inputs, not saved defaults.
The app combines recordings; it is not a waveform editor.

### 2. Check saved defaults

Review **Saved settings**. If changes are needed, click **Change settings**, edit
the relevant controls, and click **Save settings**. Wait for the success message;
validation errors leave the previous defaults in place. **Discard changes**
restores the saved form instead. Return to **Create Episode**.

To add music or intro/outro assets, use the explicitly immediate library actions
described above. To reuse a template or JSON file, use **Load and apply template**
or **Import and apply settings**; both replace drafts with saved values immediately.

### 3. Render

Optionally inspect **Timeline & premix details**, then click **Create Episode**.
Episode input controls are disabled while rendering. Follow inline status and
progress; expand **Processing log** for details. Processing time depends on
recording length, selected features, hardware, and available models.

### 4. Review quality and download

Listen in **Your episode** and use **Download episode**. The quality summary is:

| State | Meaning |
|---|---|
| PASS / green | **Ready to publish** means the measured checks passed, not that all production validation is complete. |
| WARN / yellow | **Review recommended**; listen to the flagged section and review details. |
| FAIL / red | **Quality check failed — review before publishing**. |
| Disabled | Final QC was not requested for this render; no PASS is implied. |
| Unavailable | The report could not certify this export; no PASS is implied. |

**Download episode remains available for an existing export in every QC state.**
For WARN/FAIL, **Download anyway — acknowledge warning** records your deliberate
acknowledgement, but does not erase findings, change the result to PASS, or unlock
a previously blocked download. Use **Download episode** to retrieve the file.

**Apply suggested settings for next render** immediately saves appropriate
defaults and refreshes the Settings form, replacing drafts. It does not fix the
current export or start another render. Keep or re-upload original recordings
before rerendering; normalization cannot repair clipping baked into a source.

**Preview worst section** appears only if a preview exists. Open **Technical
details** for the inspector and available **Download quality report (JSON)**,
**Cleaned voice**, and **Transcript** files. Disabled/unavailable QC has no report
download. Use **Check for background transcript** if transcription finishes later.

The original NTN567/NTN568 recordings are not available in this Linux container.
Historical output measurements and synthetic tests do **not** establish
original-recording production verification. See [Required production evidence](AUDIO_QUALITY_GATE.md#required-production-evidence).

### 5. Start another episode

Click **Create another** to clear episode uploads, order, one-time intro, results,
logs, and QC display, and get a fresh suggested name. Saved defaults and the
exported audio file are retained. This resets episode inputs/results, not a
Settings draft; use **Discard changes** explicitly for that.

---

## Features in Detail

### AI Audio Denoising

**What is it?**
AI Audio Denoising is a machine learning-powered feature that automatically removes background noise from your voice recordings.

**Multiple Denoising Methods**
In **Settings → Advanced**, choose a **Noise Reduction Method**, enable noise
reduction in **Voice processing**, and click **Save settings** before rendering:

1. **AI Denoiser (Recommended)**:
   - Uses a 38-million parameter deep learning model
   - Best for general speech enhancement
   - Supports large files with automatic chunking

2. **Spectral Gating**:
   - Uses spectral subtraction
   - Best for stationary noise like fans or hums
   - Very fast processing

3. **FFmpeg RNNoise**:
   - Uses Recurrent Neural Network noise suppression
   - Good for real-time style noise reduction

**Key Features:**

1. **Automatic Noise Removal:**
   - Removes background hum, air conditioning, fan noise
   - Eliminates microphone handling noise
   - Reduces electrical interference and buzzing
   - Preserves speech quality while cleaning audio

2. **Large File Support:**
   - AI denoising uses chunking for large recordings.
   - Processing remains limited by available memory, disk space, and dependencies; chunking is not a guarantee for arbitrary file sizes.
   - See the [denoising implementation guide](implementation/AUDIO_DENOISING_IMPLEMENTATION.md) for technical details.

**When to Use AI Denoising:**

- ✅ Noisy recordings that benefit from cleanup; compare with the original before publishing
- ✅ Home recording setups with background noise
- ✅ Interview recordings in non-studio environments
- ✅ Large files (>10MB) that need noise reduction
- ✅ Long-form content (hours of audio)
- ✅ Quick noise reduction without cloud services

### Volume Normalization (LUFS)

**What is it?**
Audio loudness normalization toward a chosen target. In **Settings → Output & quality**, enable
**Normalize audio to professional LUFS level**, choose **Target LUFS Level**, and
click **Save settings**. Verify the result by listening and, optionally, final QC.

**Settings:**
- **Enable**: Turn on/off (recommended: On)
- **Target Level**:
  - **-16 LUFS**: Standard for podcasts (Recommended)
  - **-14 LUFS**: Standard for streaming platforms (Spotify, etc.)
  - **-23 LUFS**: Standard for broadcast radio

**Benefits:**
- Consistent volume across all episodes
- No need to manually adjust volume for each recording
- Prevents audio from being too quiet or too loud
- Helps target platform loudness expectations; does not guarantee compliance or repair source clipping

### Automatic Transcription (Whisper)

**What is it?**
Generate accurate text transcripts of your podcast using OpenAI's Whisper model.

**Features:**
- **High Accuracy**: State-of-the-art speech recognition
- **Timestamped**: Includes timing for each segment
- **Multiple Models**: Choose the balance between speed and accuracy
  - **Tiny**: Fastest, good for drafts
  - **Base**: Recommended balance
  - **Small/Medium/Large**: Higher accuracy, slower processing

**How to use:**
1. In **Settings → Output & quality**, check **Generate transcript with Whisper AI** (optional, disabled by default).
2. In **Advanced**, select **Whisper Model** and click **Save settings**.
3. Return to **Create Episode** and render.
4. Download **Transcript** under **Technical details** when available. If it finishes in the background, click **Check for background transcript**. Transcription failure does not invalidate an existing audio export.

**Note:** The first time you use a model, it will be downloaded automatically (requires internet). Subsequent runs work offline.

### Voice enhancement and legacy Adobe integration

The active **Settings → Voice processing** group offers **Enable professional
voice enhancement**. Choose **Enhancement Preset** in **Advanced**:
`podcast`, `light`, or `aggressive` for EQ, compression, and de-essing.
Save your choice before rendering. For standalone denoising, use **Settings → Tools**.

Adobe browser-automation code remains in the repository but is not exposed by
the active two-tab UI. Historical instructions for an Adobe tab or automatic
Adobe checkbox do not apply here. If you use Adobe separately, it sends audio to
Adobe's servers and requires connectivity; do not confuse that service with the
local voice enhancement controls.

### Settings Persistence

**What is it?**
Saved defaults persist in `core/config.json`. Ordinary Settings edits are drafts
until **Save settings** succeeds; they are not autosaved. **Discard changes**
restores saved values. Explicit library/template/import actions and QC suggestions
apply immediately as described in [Actions that apply immediately](#actions-that-apply-immediately).

**Startup audio discovery:**
The app scans `audios/intro_audio/`, `audios/outro_audio/`, and
`audios/background_music/` only to fill missing `intro_file`, `outro_file`, or
`background_tracks` configuration keys. Saved file choices survive restart and
are not replaced by discovered files. Explicit **None** intro/outro selections
(`null` in JSON) and an empty background pool (`[]`) also survive restart; they
are intentional choices, not missing keys. Adding files to these folders and
restarting does not override saved selections or repopulate an explicitly empty pool.

**What gets saved:**
- ✅ Intro audio file path
- ✅ Outro audio file path
- ✅ All background music track paths
- ✅ Background music volume setting
- ✅ Per-track volumes, processing options, QC thresholds, music seed, and RSS preference
- ✅ Last output filename

**How it helps:**
- No need to re-upload intro/outro for each episode
- Maintain consistent branding across episodes
- Quick podcast creation for regular shows

**Backups and missing files:**
- Back up `core/config.json`, templates in `core/templates/`, and your audio assets.
- Moving a referenced audio file can make it unavailable; importing JSON does not restore missing audio.
- **Create another** clears episode inputs/results, not saved defaults.

### Background Music System

**Random Selection:**
The mixer selects and concatenates tracks from the saved background pool to fill
the required duration. The saved **Music seed** makes selection reproducible for
the same ordered pool, inputs, and settings; do not assume a different track will
be chosen on every render.

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
         (background music follows per-recording switches and mix settings)
```

### File Management

**Upload Directory:**
All uploaded files are stored in `uploads/` directory:
- Organized storage
- Working copies may be deleted after processing or cleaned on startup
- Keep original recordings separately; do not use this folder as your only backup

**Output Directory:**
Generated podcasts are saved in `outputs/` directory:
- All your created podcasts in one place
- Named according to your specification
- Use distinct episode names and back up exports you want to retain

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
   - Select defaults, set volumes and processing options, then **Save settings**
   - Create multiple episodes quickly

2. **Organize your audio files**
   - Keep source files separate from outputs
   - Use consistent naming (episode_001.mp3, episode_002.mp3)
   - Back up `core/config.json` and the referenced audio assets

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

1. Open **Settings → Per-track volume drafts**.
2. Select **Background track** and adjust **Selected Track Volume (%)** (0–50%).
3. Repeat for other tracks. Alternatively, set **Default Background Music Volume (%)** and click **Stage global volume for all tracks** to replace the per-track draft values.
4. Click **Save settings** to persist the draft, or **Discard changes** to reload saved values.
5. Render a short test and listen. The active Settings UI has no per-track audio preview player.

Start with modest music levels (for example 10%), then assess speech clarity.
In **Create Episode**, **Timeline & premix details** is advisory; final QC and
listening to the exported file are separate checks.

---

### Settings Export and Import

Save and load your entire configuration, making it easy to:
- Backup your settings
- Share configurations with team members
- Switch between different podcast styles
- Recreate a specific setup quickly

#### Exporting Settings

1. Configure defaults and click **Save settings**. Export does not include unsaved drafts.
2. Open **Settings → Templates & settings files** and click **Export saved settings**.
3. Download the generated JSON from **Saved settings download**.

The export includes default intro/outro paths, background tracks and volumes,
processing settings, QC settings, music seed, and naming/RSS preferences. It does
not bundle audio files or the current episode's uploads, custom intro, order, or
edited episode name.

#### Importing Settings

1. Keep the referenced audio files available on the machine running the app.
2. In **Settings → Templates & settings files**, upload a JSON object (maximum 1 MB) to **Settings JSON**.
3. Click **Import and apply settings**. A successful import immediately applies saved values and refreshes the form, replacing drafts; no additional save is required.
4. Check the status and refreshed controls. Any subsequent edits are new drafts and require **Save settings**.

Template loading follows the same immediate apply model: select **Template** and
click **Load and apply template**. To create a template, save your Settings edits
first, enter **Template name**, then click **Save saved settings as template**.

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

This abbreviated JSON example illustrates audio settings; a current export also
includes the processing and quality fields described above:
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
   }
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
1. Adjust global/per-track volume in **Settings**, then **Save settings**
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

**Problem:** The next render does not use the edited controls

**Solutions:**
1. Click **Save settings** and check for a success or validation-error message; switching tabs does not save.
2. Check write permissions for `core/config.json`.
3. Check that referenced library files still exist. Adding intro/outro assets alone does not select them as defaults.
4. Remember that template/import/suggestion actions replace the draft with saved values; **Discard changes** cannot undo an already applied action.

#### Missing Quality Report, Cleaned Voice, or Transcript

Downloads appear only when their files are available. Disabled or unavailable QC
has no report download and does not imply a PASS. Check **Processing log** and
**Technical details**; use **Check for background transcript** if needed.
An existing audio export remains downloadable regardless of QC status. To enable
QC for another render, change **Final Audio Quality Gate** in Settings and save.

#### Browser Can't Connect

**Problem:** Can't access http://127.0.0.1:7860

**Solutions:**
1. Verify app is running (check terminal)
2. Check if port 7860 is available
3. Try http://localhost:7860 instead
4. Check firewall settings
5. Try a different browser

#### Can't Find a Legacy Tab or Control

The active interface has only **Create Episode** and **Settings**. Use **Settings
→ Tools** for standalone cleaning, **Help & appearance** for the theme, and the
inline **Processing log** for render details. There is no active Adobe Enhance
tab, Audio Files tab, or separate Console Log tab. Older screenshots describe a
different UI.

---

## FAQ

### General Questions

**Q: Do I need an internet connection?**
A: Core audio processing runs locally, but initial model downloads and RSS lookups require connectivity. Model-based processing can work offline once the required models are installed. Adobe, if used separately, is a cloud service.

**Q: Is my audio data sent anywhere?**
A: Uploads go to the machine hosting the app. The active UI's audio processing is local to that host. Using Adobe separately sends audio to Adobe's servers; it is not a control in this UI.

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
- Settings: `core/config.json`; templates: `core/templates/`
- Library assets: `audios/intro_audio/`, `audios/outro_audio/`, and `audios/background_music/`
- All in the application directory

### Usage Questions

**Q: Can I skip intro/outro/background music?**
A: Yes. Select **None** for the saved intro/outro and save, and disable music per recording in **Episode options** (or remove tracks from the saved pool). Uploading only voice does not disable existing saved music or intro/outro defaults.

**Q: Can I use the same intro/outro for multiple episodes?**
A: Yes! That's the point of settings persistence. Upload once, use for all episodes.

**Q: How do I change my intro/outro?**
A: Add it through **Audio library — actions apply immediately**, then select **Default intro** or **Default outro** and **Save settings**. A one-time intro belongs in **Create Episode → Episode options**.

**Q: Can I remove background music after adding it?**
A: Select a **Background track** in **Per-track volume drafts**, then click **Remove selected background track now** in the audio library accordion. This immediately removes it from the saved pool but preserves the file. For just one episode, use the per-recording music switches instead.

**Q: What if I want different volumes for different episodes?**
A: You can now:
1. Set per-track volumes and click **Save settings**
2. Export saved settings or save them as a template for each episode type
3. Load and apply the appropriate template/settings before rendering

**Q: Can I use different volumes for different background music tracks?**
A: Yes. In **Settings → Per-track volume drafts**, select each track and adjust its volume, then **Save settings**. Render a short test to listen to the mix.

**Q: How do I save my settings for different podcast styles?**
A: Save your defaults, then use **Templates & settings files → Export saved settings** or **Save saved settings as template**. **Import and apply settings** and **Load and apply template** immediately replace saved values and refresh the form, discarding drafts.

**Q: Can I share my settings with a team member?**
A: Yes! Export your settings as a JSON file and share it. Your team member can import it, but they'll need access to the same audio files (or files in the same locations).

**Q: Can I edit my voice recording in this app?**
A: The app orders and mixes recordings and offers optional voice processing. Use a waveform editor for detailed cuts. Standalone denoising is available in **Settings → Tools**.

**Q: How does Adobe Enhance work?**
A: The repository retains browser-automation integration code, but the active UI does not expose it. Adobe is a separate cloud service, not the local **Enable professional voice enhancement** option. If you use Adobe outside this workflow, review its account requirements and privacy terms before uploading audio.

**Q: How do I make a podcast series with consistent branding?**
A:
1. Upload your intro/outro once
2. Add background music tracks
3. Set your preferred volumes (global or per-track)
4. Click **Save settings**, then export saved settings for backup
5. Create each episode by just uploading new voice recordings

**Q: Can I preview before creating the final file?**
A: **Timeline & premix details** shows arrangement and advisory balance information. To hear the mix, create a short test episode. A final-QC **Preview worst section** appears only when one has been generated.

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
A: There is no cancel button in the active UI. Refreshing or closing the browser is not a reliable way to stop server processing and may lose the result display. Keep originals and do not assume an interrupted process leaves no temporary files.

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
- Click **Save settings** for drafts; explicitly labelled library/template/import actions apply immediately
- Quality source audio leads to quality output
- Experiment with different background music volumes
- Listen to your output before publishing

Happy podcasting! 🎙️

---

*Last updated: September 13, 2026 — upload-first UI with grouped Settings and restart-safe saved audio choices.*
