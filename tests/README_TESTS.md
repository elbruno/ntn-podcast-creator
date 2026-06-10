# UI Tests for NTN Podcast Creator

This directory contains UI tests for the NTN Podcast Creator application.

## Running the Tests

### Core Functionality Tests (Quick - ~60 seconds)
```bash
python tests/test_ui_core.py
```

This runs 7 core tests covering:
- UI creation
- Configuration management
- Intro/outro information
- Background tracks display
- Console logging
- Audio denoising handler

All tests use actual audio files from `audios/test/` directory.

### Playwright UI Tests (Browser-based - requires running app)
```bash
pip install pytest playwright
playwright install chromium
python -m pytest tests/test_ui_playwright.py -v -s
```

This runs 13 comprehensive browser-based UI tests:
- UI loading and page structure
- File upload inputs and buttons
- Volume sliders and checkboxes
- Intro/outro and background music sections
- Audio processing options
- Responsive layout (desktop/tablet/mobile)
- Console error detection
- Basic accessibility checks

**Note**: These tests start the Gradio app automatically and use Playwright to interact with the actual UI in a browser.

### Playwright Test Structure Verification (Quick)
```bash
python -m pytest tests/test_playwright_structure.py -v
```

This verifies the Playwright test module structure without starting the app:
- Module imports correctly
- All expected test functions exist
- Fixtures are properly defined
- GradioApp helper class exists

### Full Integration Tests (Optional - requires pytest)
```bash
pip install pytest
python -m pytest tests/test_ui_podcast_creation.py -v -s
```

This runs comprehensive tests including:
- Podcast creation workflows
- Error handling
- Input validation
- Progress tracking
- All feature combinations

### All Unit Tests
```bash
pip install pytest
python -m pytest tests/test_units.py -v
```

This runs 20 unit tests covering:
- ConfigManager functionality
- AudioProcessor core functions
- App helper functions

## Test Results

### Core Tests: 7/7 ✓
✓ UI Creation
✓ ConfigManager
✓ Intro Info
✓ Outro Info
✓ Background Tracks Display
✓ Console Logging
✓ Denoise Handler

## Test Audio Files

Location: `audios/test/`

- `251121-ntn443-Recording.m4a` (18.1MB)
  - Used for denoise handler testing
  - Used for podcast creation tests
  - Demonstrates large file processing with chunking

- `test_brunos_project.mp3`
  - Available for additional testing

- `test_brunos_project_denoised.wav`
  - Reference denoised output for comparison

## Test Coverage

### UI Components
- ✓ Gradio Blocks creation
- ✓ Tab components
- ✓ Text input fields
- ✓ Audio upload components
- ✓ File output display
- ✓ Progress bars
- ✓ Console log display

### Backend Handlers
- ✓ Podcast creation with progress tracking
- ✓ Audio denoising handler
- ✓ Configuration management
- ✓ Console logging
- ✓ Error handling

### Features Tested
- ✓ Trim silence
- ✓ Noise reduction (multiple methods)
- ✓ LUFS normalization (different levels)
- ✓ Large file handling with chunking
- ✓ Audio file upload and saving
- ✓ Configuration persistence

## What's Fixed

### Issue 1: Output Value Mismatch
- **Before**: Function returned 7 values but needed 8
- **After**: All yield statements return correct 8 values

### Issue 2: Function Definition Structure
- **Before**: `get_progress_html()` was nested inside main function
- **After**: Moved to module level for proper generator flow

### Issue 3: Progress Display
- **Before**: Progress bar and console not showing during processing
- **After**: Both display properly with real-time updates

## Notes

- Tests use actual audio files from the `audios/test/` directory
- Denoise handler test requires audio processing (takes ~1 minute)
- Core tests run without full podcast processing for speed
- All tests are independent and can be run individually
- Test results are displayed in the terminal with colored output

## Troubleshooting

**Test hangs or times out**:
- Core tests should complete in ~60 seconds
- Full tests may take 5-10 minutes depending on CPU
- Check that test audio files exist in `audios/test/`

**Import errors**:
- Ensure you're running from project root: `cd /workspaces/ntn-podcast-creator`
- Python path is automatically set up in test files

**Missing dependencies**:
- Core tests require only Python 3.x and installed project dependencies
- Full tests require: `pip install pytest`
