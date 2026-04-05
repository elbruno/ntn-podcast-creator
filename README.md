# NTN Podcast Creator 🎙️

**Transform your voice recordings into professional podcasts in minutes!**

A simple, powerful desktop app that combines your recordings with intro/outro music and applies professional audio processing—all with just a few clicks.

---

## 🎯 What Does It Do?

**In short**: Upload your voice recording, click "Create Podcast", and get a professional-quality podcast episode with intro music, outro music, noise reduction, and perfect volume levels.

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
- **Theme Selector**: Light, dark, or system theme

---

## 🎨 How It Works

### Basic Workflow

```
1. Upload Voice Recording → 2. (Optional) Apply Audio Processing → 3. Click "Create Podcast" → 4. Download Final Episode!
```

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
1. In the "Audio Processing" tab, check **"Enable professional voice enhancement"**
2. Choose your preset (Podcast recommended)
3. Create your podcast as normal

**Pro tip**: Use noise reduction first, then voice enhancement for best results!

---

## 📚 Documentation

- **[User Manual](docs/USER_MANUAL.md)** - Complete step-by-step guide with screenshots
- **[Technical Docs](docs/TECHNICAL_IMPLEMENTATION.md)** - Architecture and API details
- **[Docker Guide](docs/DOCKER.md)** - Containerized deployment
- **[Audio Denoising Guide](docs/AUDIO_DENOISING_IMPLEMENTATION.md)** - Deep dive into AI noise reduction

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
A: Nope! The defaults work great. Just upload and click "Create Podcast".

**Q: Which noise reduction method should I use?**
A: Start with "AI Denoiser" (recommended). It's the most advanced.

**Q: What's the difference between noise reduction and voice enhancement?**
A: Noise reduction removes unwanted sounds. Voice enhancement makes your voice clearer and more pleasant to listen to. Use both for best results!

**Q: My podcast sounds too quiet/loud. What do I do?**
A: Enable "LUFS Normalization" in Audio Processing. It ensures professional loudness levels.

**Q: Can I use my own intro/outro music?**
A: Yes! Go to "Audio Files" tab and upload your own audio files.

**Q: Do I need a powerful computer?**
A: Not really. AI Denoiser works faster with a GPU but runs fine on CPU. Processing a 20-minute podcast takes about 5-15 minutes on most computers.

