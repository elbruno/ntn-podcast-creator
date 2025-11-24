# NTN Podcast Creator - Images Directory

This directory contains all screenshots, GIFs, and visual assets for the NTN Podcast Creator documentation.

## Directory Structure

```
docs/images/
├── screenshots/          # Application screenshots (organized centrally)
│   ├── 01-initial-view.png
│   ├── 02-voice-upload.png
│   ├── 03-intro-outro.png
│   ├── 04-background-music.png
│   ├── 05-audio-processing.png
│   ├── 06-lufs-normalization.png
│   ├── 07-transcription.png
│   ├── 08-create-button.png
│   ├── 09-full-overview.png
│   ├── 10-standalone-denoiser.png
│   └── 11-settings-tab.png
├── app-demo.gif          # Main animated demonstration (workflow)
├── SCREENSHOT_GUIDELINES.md  # Detailed guidelines
└── README.md             # This file
```

## Automated Screenshot Capture

To capture fresh screenshots automatically using Playwright:

### Prerequisites
```bash
pip install playwright Pillow requests
playwright install chromium
```

### Capture Process
1. Start the application:
   ```bash
   python app.py
   ```

2. In another terminal, run the capture script:
   ```bash
   python scripts/capture_screenshots.py
   ```

The script will:
- ✅ Connect to http://localhost:7860
- ✅ Navigate through all sections
- ✅ Capture 11+ high-quality screenshots
- ✅ Generate animated GIF from screenshots
- ✅ Save everything to `docs/images/screenshots/`

## Screenshot List

| # | Filename | Description |
|---|----------|-------------|
| 1 | `01-initial-view.png` | Initial application view with empty form |
| 2 | `02-voice-upload.png` | Voice file upload section focused |
| 3 | `03-intro-outro.png` | Intro and outro file selectors |
| 4 | `04-background-music.png` | Background music selection and controls |
| 5 | `05-audio-processing.png` | Denoising and enhancement options |
| 6 | `06-lufs-normalization.png` | LUFS normalization settings |
| 7 | `07-transcription.png` | Transcription options with Whisper |
| 8 | `08-create-button.png` | Create button and output section |
| 9 | `09-full-overview.png` | Full-page overview of entire interface |
| 10 | `10-standalone-denoiser.png` | Standalone AI Denoiser tab |
| 11 | `11-settings-tab.png` | Settings and configuration management |

## Animated GIF Specifications

**File:** `app-demo.gif`

**Content:**
- Shows complete podcast creation workflow
- Displays all major features in sequence
- Smooth transitions between steps
- Slow enough to see all options clearly

**Technical Specs:**
- Resolution: 1200px width (scaled from 1920px)
- Duration: ~30 seconds total
- Frame rate: 3 seconds per frame, 5 seconds for last frame
- Format: GIF with infinite loop
- Size target: < 10MB (optimized)

**Workflow Shown:**
1. Initial view → 2. File upload → 3. Intro/outro → 4. Background music →
5. Volume adjustment → 6. Audio processing → 7. Transcription → 
8. Create podcast → 9. Results with downloads

## Usage in Documentation

### Root README.md
```markdown
![Application Demo](docs/images/app-demo.gif)
*Complete podcast creation workflow demonstration*
```

### User Manual (docs/USER_MANUAL.md)
```markdown
![Voice Upload](images/screenshots/02-voice-upload.png)
*Voice recording upload section*
```

### Technical Docs (from docs/ directory)
```markdown
![Feature Screenshot](images/screenshots/05-audio-processing.png)
```

## Centralized Image Organization

**Why One Directory?**
- ✅ No duplicate images across documentation
- ✅ Single source of truth for all visuals
- ✅ Easier maintenance and updates
- ✅ Consistent file naming and organization
- ✅ Simpler relative path references

**Migration Note:**
All documentation now references images from `docs/images/screenshots/` only. No images are duplicated in other directories.

## Maintenance Checklist

When updating screenshots:
- [ ] Run the automated capture script
- [ ] Review all generated screenshots for quality
- [ ] Check that animated GIF shows complete workflow
- [ ] Update documentation if UI changes significantly
- [ ] Verify all image references in docs still work
- [ ] Commit all new images to git
- [ ] Optimize large files if needed (use imageOptim, tinypng, etc.)

## Image Optimization

For better performance:

### PNG Optimization
```bash
# Using optipng
optipng -o7 *.png

# Using pngquant
pngquant --quality=80-95 *.png
```

### GIF Optimization
```bash
# Using gifsicle
gifsicle -O3 --colors 256 app-demo.gif -o app-demo-optimized.gif
```

## Manual Screenshot Capture (Alternative)

If the automated script doesn't work:

1. Start application: `python app.py`
2. Open browser to http://localhost:7860
3. Use browser dev tools (F12):
   - Set viewport to 1920x1080
   - Take screenshots with Cmd/Ctrl + Shift + P → "Capture screenshot"
4. Use screen recording tool for GIF:
   - LICEcap (Windows/Mac)
   - ScreenToGif (Windows)
   - Kap (macOS)
   - Peek (Linux)
5. Name files according to the list above
6. Save to `docs/images/screenshots/`

## Notes

- Always use test/sample data in screenshots
- Avoid showing sensitive or personal information
- Keep screenshots current with latest UI
- Prefer dark theme for animated GIFs (better contrast)
- Test all image links after updating
