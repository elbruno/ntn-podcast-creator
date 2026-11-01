# Background Music Folder

This folder includes the six approved NTN tracks selected by the
[portable first-run settings](../../core/config.initial.json).
Existing saved background selections always win, including an empty pool.
Only configurations missing the background selection discover all tracks.

## Supported Formats
- MP3
- WAV
- M4A
- OGG
- FLAC

## Usage
1. Add your background music files to this folder (e.g., `music1.mp3`, `music2.mp3`)
2. Restart the application
3. Add/select tracks through the audio library UI and save the desired settings

## How It Works
- The saved background pool determines which tracks are used
- When creating a podcast, one track is randomly selected from the pool
- The selected track is looped to match your podcast duration
- You can add more tracks through the UI, which will also be saved to this folder
- Additional local audio stays ignored by Git. Publish new audio only with
  redistribution permission. See the [machine handoff guide](../../docs/MACHINE_HANDOFF.md).
