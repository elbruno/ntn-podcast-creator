# Screenshots and GIF Creation Guide

## Required Screenshots/GIFs

This file documents the screenshots and animated GIFs that need to be created for the documentation.

### 1. Theme Selector Demo GIF
**File:** `theme-selector-demo.gif`
**Description:** Animated GIF showing the theme selector in action
**Steps to create:**
1. Start the application: `python app.py`
2. Open in browser at http://localhost:7860
3. Use a screen recording tool (e.g., LICEcap, ScreenToGif, or ffmpeg)
4. Record the following actions:
   - Show the theme dropdown in the top right
   - Select "Light" theme - show the interface updating
   - Select "Dark" theme - show the interface updating
   - Select "System" theme
5. Save as `theme-selector-demo.gif`
6. Optimize the GIF (keep it under 5MB if possible)

**Recommended recording settings:**
- Duration: 10-15 seconds
- Frame rate: 10-15 fps
- Resolution: 1200x800 or similar
- Focus on the theme selector area and a section of the UI that shows the theme change

### 2. Progress and Console Demo GIF
**File:** `progress-console-demo.gif`
**Description:** Animated GIF showing the progress bar and console during podcast creation
**Steps to create:**
1. Start the application: `python app.py`
2. Open in browser at http://localhost:7860
3. Use a screen recording tool
4. Record the following actions:
   - Upload a voice file
   - Click "Create Podcast" button
   - Show the **top progress bar appearing** with percentage and status
   - Show the **bottom console appearing** with live log updates
   - Let it run for a few seconds to show progress updates
   - Show the completion state with 100% progress
5. Save as `progress-console-demo.gif`

**Recommended recording settings:**
- Duration: 15-20 seconds
- Frame rate: 10-15 fps
- Resolution: 1600x900 or full screen
- Focus on both the top progress bar and bottom console

### 3. Main Interface Screenshot (Updated)
**File:** `main-interface.png`
**Description:** High-quality screenshot of the main podcast creation interface
**Steps to create:**
1. Start the application: `python app.py`
2. Open in browser at http://localhost:7860
3. Set the theme to "Light" for consistency
4. Upload a sample voice file to show the timeline preview
5. Take a full-page screenshot showing:
   - Header with title and theme selector
   - Upload section
   - Timeline preview
   - Processing options (denoise, enhance, etc.)
   - Output section
6. Save as `main-interface.png`

**Recommended settings:**
- Format: PNG
- Resolution: High resolution (1920x1080 or higher)
- Include the full interface from header to footer

### 4. Dark Theme Screenshot
**File:** `dark-theme.png`
**Description:** Screenshot showing the dark theme
**Steps to create:**
1. Start the application: `python app.py`
2. Open in browser at http://localhost:7860
3. Select "Dark" theme from the dropdown
4. Take a full-page screenshot
5. Save as `dark-theme.png`

### 5. Settings Tab Screenshot
**File:** `settings-tab.png`
**Description:** Screenshot of the settings configuration interface
**Steps to create:**
1. Navigate to the "Settings" tab
2. Show intro/outro/background music configuration
3. Show volume controls
4. Take a full-page screenshot
5. Save as `settings-tab.png`

## Tools for Creating GIFs

### LICEcap (Windows/macOS)
- Free and simple
- https://www.cockos.com/licecap/

### ScreenToGif (Windows)
- Free with built-in editor
- https://www.screentogif.com/

### Kap (macOS)
- Open source and lightweight
- https://getkap.co/

### Using FFmpeg (All platforms)
```bash
# Record screen on Linux/macOS
ffmpeg -f x11grab -s 1920x1080 -i :0.0 output.mp4
# Or on macOS using AVFoundation
ffmpeg -f avfoundation -i "1" -t 20 output.mp4

# Convert to GIF
ffmpeg -i output.mp4 -vf "fps=10,scale=1200:-1:flags=lanczos" -c:v gif output.gif

# Optimize GIF
ffmpeg -i output.gif -filter_complex "[0:v] fps=10,scale=1200:-1:flags=lanczos,split [a][b];[a] palettegen [p];[b][p] paletteuse" optimized.gif
```

## Placement

Once created, place the files in this `docs/images/` directory and update the references in:
- `README.md` (root)
- `docs/USER_MANUAL.md`
- `docs/TECHNICAL_IMPLEMENTATION.md` (if applicable)

## Note

These screenshots/GIFs need to be created by actually running the application. The AI agent cannot run a GUI application to capture screenshots, so this needs to be done manually by the repository owner or a contributor with access to a running instance.
