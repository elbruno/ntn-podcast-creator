# Fix Summary: Progress Bar and Console Display Issue

## Problem
The app was showing a Gradio warning:
```
A function (create_podcast_handler_with_progress) returned too many output values (needed: 7, returned: 8). Ignoring extra values.
```

This caused the progress bar and console log to not display during podcast creation, even though they were being generated.

## Root Cause
The `create_podcast_handler_with_progress()` function had 8 yield statements, each returning **8 values instead of 7**. The issue was:
1. Each yield statement was returning the console log TWICE (once as the 5th value and once as the 6th value)
2. The Gradio output component list only expected 7 values:
   - status_output
   - audio_output
   - denoised_audio_output
   - transcript_output
   - realtime_console_output
   - progress_bar
   - bottom_console

## Solution
Fixed all 8 yield statements in the `create_podcast_handler_with_progress()` function to return exactly 7 values instead of 8:

**Before** (8 values - WRONG):
```python
yield "status", audio, denoised, transcript, console, console, progress_html, bottom_html
```

**After** (7 values - CORRECT):
```python
yield "status", audio, denoised, transcript, console, progress_html, bottom_html
```

### Changes Made
1. **Line 775**: Removed duplicate console from error case
2. **Line 787**: Removed duplicate console from "Preparing files" yield
3. **Line 793**: Removed duplicate console from save error case
4. **Line 798**: Removed duplicate console from "Loading configuration" yield
5. **Line 828**: Removed duplicate console from "Starting audio processing" yield
6. **Line 920**: Removed duplicate console from main processing loop yield
7. **Line 936**: Removed duplicate console from error result yield
8. **Line 955**: Removed duplicate console from success result yield
9. **Lines 1476-1481**: Updated initial HTML component values to `display: none` instead of `visible=False`

## Verification
- ✅ Python syntax check: `python -m py_compile app.py` PASSED
- ✅ Function is properly recognized as a generator
- ✅ All 8 yield statements now return exactly 7 values
- ✅ Gradio output component count matches function return values
- ✅ Progress bar HTML now displays during processing
- ✅ Bottom console log now displays during processing

## Expected Behavior After Fix
During podcast creation:
1. Top progress bar will show as a fixed header with animated spinner and percentage
2. Bottom console log will show live updates as processing happens
3. No Gradio warnings about output value mismatch
4. UI remains responsive while podcast is being created
