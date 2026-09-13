# NTN Podcast Creator 🎙️

**Transform your voice recordings into professional podcasts in minutes!**

A local, browser-based app that combines your recordings with intro/outro music and optional audio processing. The upload-first interface has two tabs: **Create Episode** and **Settings**.

---

## 🎯 What Does It Do?

**In short**: Upload your recordings, review the saved defaults, click **Create Episode**, then listen and **Download episode**. Optional quality checks help identify issues; they do not guarantee production-ready audio.

**Perfect for**:
- 🎙️ Podcasters who want studio-quality sound without expensive equipment
- 🎬 Content creators making audio content
- 📻 Radio shows and interviews
- 🎓 Educational content and audiobooks

Created for the **[No Tiene Nombre](https://notienenombre.com/)** podcast production workflow.

---

## ⚡ Quick Start

### Option 1: Docker (Easiest - No Setup!)

```bash
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator/deployment
docker-compose up -d
```

Open your browser to **http://localhost:7860** and you're ready!

### Option 2: Local Installation

1. **Install Requirements**:
   ```bash
   # Install FFmpeg first
   # Ubuntu/Debian:
   sudo apt-get install ffmpeg
   # macOS:
   brew install ffmpeg
   # Windows: Download from ffmpeg.org
   ```

2. **Install & Run**:
   ```bash
   git clone https://github.com/elbruno/ntn-podcast-creator.git
   cd ntn-podcast-creator
   pip install -r requirements.txt
   python app.py
   ```

3. Open **http://localhost:7860**

---

## ✨ Key Features

### 🎵 Audio Production
- **Multi-File Upload**: Automatically combine multiple recordings
- **Smart Audio Mixing**: Add intro, outro, and background music
- **Individual Track Controls**: Adjust volume for each background music track

### 🔊 Professional Audio Quality
- **AI Noise Reduction**: Remove background noise with 3 different methods
  - AI Denoiser (Deep learning-based - recommended)
  - Spectral Gating (Fast and effective)
  - FFmpeg RNNoise (Neural network denoiser)
- **Voice Enhancement** ⭐NEW⭐: Professional EQ, compression, and de-essing
  - **Podcast preset**: Balanced enhancement for clear voice
  - **Light preset**: Gentle processing for clean recordings
  - **Aggressive preset**: Strong processing for very noisy environments
- **LUFS Normalization**: Professional loudness standards for consistent volume
- **Silence Trimming**: Automatically remove dead air

### 📝 Extras
- **Auto Transcription (Long-Form Ready)**: Generate transcripts in 99+ languages with a robust pipeline
    - VAD filtering (when supported by backend)
    - Chunking + overlap for long audio
    - Timestamp-preserving segment stitching
    - Graceful backend fallback (`faster-whisper` → `openai-whisper`)
- **Template Management**: Save and load your favorite settings
- **Final Audio Quality Gate**: Opt-in checks, with reports and worst-section previews when available; QC failures never block an existing audio export
- **Tools & Help**: Standalone audio cleaning in **Settings → Tools**; theme selection in **Help & appearance**

---

## 🎨 How It Works

### Basic Workflow

1. In **Create Episode**, use **Upload recordings**. For multiple files, review **Recording order**; use **Edit** to change the suggested episode name.
2. Review the **Saved settings** summary. **Episode options** provides per-recording background music switches and a custom intro for this episode only.
3. To change defaults, open **Settings** (or **Change settings**), edit, then choose **Save settings** or **Discard changes**. Each render uses a snapshot of saved settings, not unsaved drafts.
4. Click **Create Episode**. Follow inline progress and expand **Processing log** if needed.
5. Listen, review any QC findings, then **Download episode**. **Technical details** shows report, cleaned-voice, and transcript downloads only when available. Use **Create another** to reset episode inputs/results without deleting the export.

Settings controls are organized into five accordions:

- **Podcast sound**: default intro/outro, background volume, and overlap transitions.
- **Voice processing**: auto-balance, auto-ducking, silence trimming, noise reduction, and voice enhancement toggles.
- **Output & quality**: normalization, target LUFS, final quality gate, transcription toggle, and uploaded-recording deletion.
- **Naming & RSS**: recording-order preference and RSS feed URL.
- **Advanced**: denoise method, enhancement preset, Whisper model, minimum voice/music separation, audio quality thresholds (`audio_quality`), and music seed.

**Per-track volume drafts** is a separate Settings accordion. Startup audio discovery fills only missing configuration keys; saved file choices, explicit **None** intro/outro selections, and an empty background pool (`[]`) survive restart.

**Explicit exceptions to Save/Discard:** **Audio library — actions apply immediately** adds/removes library entries now (intro/outro default selection still needs saving). **Load and apply template** and **Import and apply settings** immediately apply saved defaults and refresh the form, replacing drafts. Template saving and JSON export use saved values, not drafts.

**QC is advisory, not a download lock:** A successful export remains downloadable when QC is disabled, unavailable, or fails. For warning/failure results, **Download anyway — acknowledge warning** records a deliberate acknowledgement without changing the findings. **Apply suggested settings for next render** saves suggested defaults immediately; it does not repair the current file. Keep originals for rerendering. NTN567/NTN568 originals remain unavailable in this container, so production regression verification is still pending; see the [quality guide](docs/AUDIO_QUALITY_GATE.md#required-production-evidence).

### Audio Processing Pipeline

Your audio goes through these optional enhancement steps:

```
Original Recording
    ↓
[Noise Reduction] ← Remove background noise (AI, Spectral, or RNNoise)
    ↓
[Voice Enhancement] ← NEW! Apply EQ, compression, de-essing
    ↓
[Silence Trimming] ← Remove dead air at start/end
    ↓
[Audio Mixing] ← Add intro, outro, background music
    ↓
[LUFS Normalization] ← Professional loudness standards
    ↓
Final Podcast Episode 🎉
```

### Transcript Pipeline (Long Audio)

When transcript generation is enabled, the app uses a long-form strategy inspired by Whisper and community best practices:

```
Final Podcast Audio
    ↓
[Voice Activity Detection] (when backend supports it)
    ↓
[Chunking + Overlap] (long recordings)
    ↓
[Whisper Decoding + Timestamps]
    ↓
[Segment Stitching / Dedup on overlaps]
    ↓
Transcript (.txt + timestamped .txt)
```

Notes:
- Preferred backend: `faster-whisper` (optimized + VAD support)
- Fallback backend: `openai-whisper`
- If a backend is unavailable, podcast creation still continues (transcript is optional)

**All steps are optional!** Enable only what you need.

---

## 🆕 What's New - Voice Enhancement

We've added **professional voice enhancement** to make your podcasts sound even better:

### What It Does:
- **High-pass filter**: Removes low-frequency rumble and background noise
- **EQ enhancement**: Boosts voice clarity and presence (2-5 kHz range)
- **De-esser**: Reduces harsh "S" and "SH" sounds
- **Dynamic compression**: Evens out volume levels for consistent listening

### When to Use:
- ✅ **Podcast preset** (default): Balanced enhancement for most recordings
- ✅ **Light preset**: For already-clean recordings in quiet environments
- ✅ **Aggressive preset**: For noisy environments or challenging recordings

### How to Use:
1. In **Settings → Voice processing**, check **Enable professional voice enhancement**.
2. In **Advanced**, choose your **Enhancement Preset** (`podcast`, `light`, or `aggressive`).
3. Click **Save settings**, then return to **Create Episode**.

**Pro tip**: Use noise reduction first, then voice enhancement for best results!

---

## 📚 Documentation

- **[User Manual](docs/USER_MANUAL.md)** - Upload-first workflow, saved defaults, library actions, and downloads
- **[Audio Quality Gate](docs/AUDIO_QUALITY_GATE.md)** - QC results, acknowledgement, rerendering, and validation limits
- **[Technical Docs](docs/TECHNICAL_IMPLEMENTATION.md)** - Architecture and API details
- **[Docker Guide](docs/DOCKER.md)** - Containerized deployment
- **[Audio Denoising Guide](docs/implementation/AUDIO_DENOISING_IMPLEMENTATION.md)** - Deep dive into AI noise reduction

---

## 🛠️ Technology Stack

**Built with**:
- **Python** - Core application
- **Gradio** - Web interface
- **FFmpeg** - Professional audio processing (EQ, compression, normalization)
- **PyTorch** - AI-powered noise reduction
- **Whisper AI** - Automatic transcription
- **Docker** - Easy deployment

---

## 💡 Tips for Best Results

1. **Start Simple**: Try creating a podcast without any processing first
2. **Layer Processing**: Enable features one at a time to hear the difference
3. **Noise Reduction**: If your recording is noisy, start with AI Denoiser
4. **Voice Enhancement**: Try the "Podcast" preset—it works great for most recordings
5. **Save Templates**: Found settings you like? Save them as a template!

---

## 🧪 Testing

Run tests to verify everything works:

```bash
python -m unittest tests.test_units -v
```

---

## 👨‍💻 Created By

**Bruno Capuano**
🔗 [https://aka.ms/elbruno](https://aka.ms/elbruno)

**For: No Tiene Nombre Podcast**
🎙️ [https://notienenombre.com](https://notienenombre.com/)

---

## 📄 License

MIT License - Free to use and modify. See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Found a bug? Have a feature idea? Open an issue or submit a pull request!

---

## ❓ FAQ

**Q: Do I need to know anything about audio engineering?**
A: No audio-engineering expertise is required. Review the saved defaults, upload, click **Create Episode**, and listen before publishing.

**Q: Which noise reduction method should I use?**
A: Start with "AI Denoiser" (recommended). It's the most advanced.

**Q: What's the difference between noise reduction and voice enhancement?**
A: Noise reduction removes unwanted sounds. Voice enhancement makes your voice clearer and more pleasant to listen to. Use both for best results!

**Q: My podcast sounds too quiet/loud. What do I do?**
A: In **Settings**, enable **Normalize audio to professional LUFS level**, choose the target, and click **Save settings**. Rerender and listen; normalization cannot repair clipping already in the source.

**Q: Can I use my own intro/outro music?**
A: Yes! Open **Settings → Audio library — actions apply immediately**, add an asset, then select **Default intro** or **Default outro** and **Save settings**. For a one-time intro, use **Create Episode → Episode options**.

**Q: Do I need a powerful computer?**
A: Not really. AI Denoiser works faster with a GPU but runs fine on CPU. Processing a 20-minute podcast takes about 5-15 minutes on most computers.

