# Documentation Index

This directory contains comprehensive documentation for the NTN Podcast Creator.

## 📖 User Documentation

### [User Manual](USER_MANUAL.md)
Current upload-first **Create Episode** / **Settings** workflow: saved-setting
snapshots, explicit **Save settings** / **Discard changes**, per-episode overrides,
conditional downloads, and **Tools** / **Help & appearance** accordions.

Settings has five implemented groups: **Podcast sound** (intro/outro, background
volume, transitions), **Voice processing** (auto-balance, auto-ducking, trim,
denoise/enhance toggles), **Output & quality** (normalization, target LUFS, gate,
transcript toggle, deletion), **Naming & RSS** (recording-order preference, RSS),
and **Advanced** (denoise method, enhancement preset, Whisper model, minimum
separation, audio quality thresholds, music seed). Thresholds are directly in
**Advanced**; **Per-track volume drafts** is a separate accordion.
Library add/remove actions apply immediately; template loading and JSON import
explicitly load and apply saved settings immediately, replacing drafts.
Startup audio discovery fills only missing configuration keys; saved file choices,
explicit intro/outro **None**, and an empty background pool (`[]`) survive restart.

### [Docker Deployment Guide](DOCKER.md)
Instructions for running with Docker, including setup and troubleshooting.

### [Docker Publishing](DOCKER_PUBLISH.md)
Instructions for building and publishing Docker images.

## 🛠️ Technical Documentation

### [Audio Quality Gate](AUDIO_QUALITY_GATE.md)
Final-file QC, conditional reports/previews, deliberate warning acknowledgement,
and next-render suggestions. Existing exports remain downloadable even if QC
fails, is disabled, or is unavailable. Includes shared thresholds and the
original-recording regression setup: NTN567/NTN568 originals are still unavailable
in this container, so production verification is not claimed.

### [Technical Implementation](TECHNICAL_IMPLEMENTATION.md)
Detailed architecture, API reference, and technical specifications.

## 📝 Implementation Details

Historical implementation reports and screenshots may describe the unused legacy
UI retained in `app.py`. Use the User Manual and Audio Quality Gate guide above
for current navigation and save/apply behavior; historical reports are not proof
of production validation.

For detailed implementation documentation and technical references, see the [implementation](implementation/) folder:
- [Audio Denoising Implementation](implementation/AUDIO_DENOISING_IMPLEMENTATION.md)
- [Chunking Implementation](implementation/CHUNKING_IMPLEMENTATION_COMPLETE.md)
- [Release Notes - Chunking](implementation/RELEASE_NOTES_CHUNKING.md)
- [Structure Improvements](implementation/STRUCTURE_IMPROVEMENTS.md)

---

## Quick Start

For new users, start with the [User Manual](USER_MANUAL.md).
For developers, begin with [Technical Implementation](TECHNICAL_IMPLEMENTATION.md).
For deployment, see the [Docker Deployment Guide](DOCKER.md).
