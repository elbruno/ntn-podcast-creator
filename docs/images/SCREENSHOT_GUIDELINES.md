# Screenshot Guidelines for NTN Podcast Creator

This document describes the screenshots that should be captured for the application documentation.

## Screenshot List

### Main Application Screenshots

1. **01-initial-view.png** - Initial application view
   - Shows the main podcast creator interface when first loaded
   - Displays the voice file upload area at the top
   - Shows the output name field with auto-suggestion
   - Viewport: 1920x1080

2. **02-voice-upload.png** - Voice file upload section
   - Focus on the voice recording upload component
   - Shows the file selector and any uploaded file
   - Displays file information if a file is selected

3. **03-intro-outro.png** - Intro/Outro selection
   - Shows the intro audio file selector
   - Shows the outro audio file selector  
   - Displays current selections or default state

4. **04-background-music.png** - Background music section
   - Shows background music file selector (multiple files supported)
   - Displays volume control slider
   - Shows individual track volume controls
   - Preview section for background tracks

5. **05-audio-processing.png** - Audio processing options
   - Shows denoising checkbox and method dropdown
   - Displays Adobe enhancement option
   - Shows trim silence option

6. **06-lufs-normalization.png** - LUFS normalization
   - Shows LUFS normalization checkbox
   - Displays target LUFS value selector (-23 to -13)
   - Explains what LUFS normalization does

7. **07-transcription.png** - Transcription options
   - Shows transcript generation checkbox
   - Displays Whisper model selector (tiny, base, small, medium)
   - Explains the transcription feature

8. **08-create-button.png** - Create button and output
   - Shows the "Create Podcast" button
   - Displays the output section where results appear
   - Shows download buttons for created podcast and transcript

9. **09-full-overview.png** - Full page overview
   - Full-page screenshot showing entire workflow
   - Demonstrates the complete interface layout

10. **10-standalone-denoiser.png** - Standalone AI Denoiser tab
    - Shows the standalone denoiser interface
    - Displays the separate denoising tool
    - Shows denoising options and methods

11. **11-settings-tab.png** - Settings management
    - Shows configuration export/import
    - Displays saved settings
    - Configuration management options

## Animated GIF Requirements

The animated GIF (app-demo.gif) should show:

1. **Frame 1** (3s): Initial view with empty form
2. **Frame 2** (3s): Voice file being selected/uploaded
3. **Frame 3** (3s): Scrolling to intro/outro selection
4. **Frame 4** (3s): Selecting background music files
5. **Frame 5** (3s): Adjusting volume controls
6. **Frame 6** (3s): Enabling audio processing options
7. **Frame 7** (3s): Enabling transcription
8. **Frame 8** (3s): Creating the podcast (showing progress)
9. **Frame 9** (5s): Final result with download buttons

### GIF Specifications
- Resolution: 1200px width (scaled from 1920px)
- Duration: 3 seconds per frame, 5 seconds for last frame
- Format: GIF with loop enabled
- Optimization: Balance between quality and file size (aim for <10MB)
- Slow transitions to show each step clearly

## How to Capture

Run the provided script:
```bash
# Start the application
python app.py

# In another terminal, run the capture script
python scripts/capture_screenshots.py
```

The script will:
1. Connect to the running application at http://localhost:7860
2. Navigate through different sections
3. Capture screenshots at each step
4. Generate an animated GIF from the screenshots
5. Save all files to `docs/images/screenshots/`

## Image Organization

All screenshots are stored in a single directory:
```
docs/images/screenshots/
├── 01-initial-view.png
├── 02-voice-upload.png
├── 03-intro-outro.png
├── 04-background-music.png
├── 05-audio-processing.png
├── 06-lufs-normalization.png
├── 07-transcription.png
├── 08-create-button.png
├── 09-full-overview.png
├── 10-standalone-denoiser.png
└── 11-settings-tab.png
```

The animated GIF is stored at:
```
docs/images/app-demo.gif
```

## Usage in Documentation

### In README.md
- Use the animated GIF prominently near the top
- Reference: `![Application Demo](docs/images/app-demo.gif)`

### In USER_MANUAL.md  
- Use specific screenshots to illustrate each feature
- Reference: `![Voice Upload](docs/images/screenshots/02-voice-upload.png)`

### In Other Documentation
- All documentation should reference images from the centralized location
- Use relative paths from the document location
- Example from docs/: `![Screenshot](images/screenshots/01-initial-view.png)`
