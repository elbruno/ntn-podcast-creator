# Docker Deployment Guide

This guide explains how to run the NTN Podcast Creator using Docker.

## Pending episode folders (Python)

Select a folder rather than manually supplying each voice recording:

```powershell
python .\scripts\ntn-create-pending.py
python .\scripts\ntn-create-pending.py --list-only
python .\scripts\ntn-create-pending.py --no-play
python .\scripts\ntn-create-pending.py --root "D:\Podcast"
python .\scripts\ntn-create-pending.py --server-url http://localhost:7860 --no-auto-start
```

The client uses only Python's standard library (Python 3.8+); no PowerShell,
FFmpeg, Gradio, or audio/AI packages are required on Windows. Audio processing
and joining happen inside Docker. It can be launched from any working directory.

### Folder selection

- Default library: `C:\od\OneDrive\Podcast`.
- Only immediate dated folders such as `26 10 11 NTN 580 Title` are scanned.
  The date is interpreted as year/month/day in the 2000s. Archive and undated
  idea folders are not traversed.
- Pending folders appear newest first by the date in their name, not OneDrive's
  modification timestamp. All matching folders are examined.
- A final such as `ntn580.mp3`, `nt580.mp3`, `ntn580-03.mp3`, or
  `ntn580_final.mp3` means already processed. A final with a different episode
  number also excludes the folder, with a warning; nothing is renamed.
- Voice inputs can be `Recording` or `Recoding` in M4A, MP3, or WAV, ignoring
  case. The base file comes first, followed by `(2)`, `(3)`, etc. Multiple inputs
  are joined without additional pauses or crossfades, using the existing MP3
  intermediate concatenation helper.
- Duplicate indices (including two extensions at the same index), missing base
  files, and index gaps block processing until the files are corrected.
- Folders without recognized recordings and access errors are reported.

Choose an index, review the ordered inputs, final destination and server settings,
then enter `s` to confirm. Enter at selection, or anything other than `s`/`si` at
confirmation, cancels without uploading audio. The script processes one episode
per invocation and opens the downloaded MP3 in your default audio player after
all downloads finish. Use `--no-play` to disable this. A player launch failure
produces a warning without affecting the saved episode. Playback depends on the
default MP3 application configured on your computer.

### Server and saved settings

The server must include the new `folder_episode_settings` and
`create_folder_episode` API endpoints. To update an existing container after
updating this repository, explicitly rebuild when no episode is running:

```powershell
docker compose -f .\deployment\docker-compose.yml up -d --build
```

The script never recreates or rebuilds an existing container automatically.
For the default local URL only, it starts the existing `ntn-podcast-creator`
container if the connection is refused. If no container exists it uses Docker
Compose to create one; Docker Desktop's engine must already be running.
Custom server URLs and `--no-auto-start` require an already-running server.
`--list-only` never contacts Docker or the API.

The new flow uses the **server's saved processing configuration**, including
intro/outro, background tracks and volumes, optional voice processing,
normalization, quality gate and **saved transcription toggle/model**. If settings
change after review, the server rejects the render and asks for a new confirmation.
The old single-recording PowerShell command and `create_episode` API retain their
original defaults: transcription off unless explicitly requested.

### Outputs, OneDrive and recovery

The final is named exactly `ntn<folder_number>.mp3`, downloaded beside the
recordings; a copy remains in a unique server directory such as
`outputs/folder-episode-<unique-id>/ntn581.mp3`. Each folder render gets its own
directory, so an older `outputs/ntn581.mp3` or another folder with the same
episode number cannot block the new render. Older outputs are neither reused
nor overwritten: the selected recordings are always processed.
The single-recording API/PowerShell workflow keeps its existing flat output
directory and collision checks. Optional
transcript, cleaned voice and quality report are downloaded alongside it when
available. The client's downloads do not rebind server-side quality identities
to the local copy. The usual last-output-name bookkeeping remains on the server;
processing toggles are not changed.

Original recordings are never modified or deleted, even if the app's
`delete_voice` setting is enabled. Existing outputs and local downloads are never
overwritten, and collisions never increment the folder's episode number.
Downloads use unique `.part` files and are published only when complete; partial
downloads are removed. Final filename recognition is not an audio quality check.

OneDrive may download cloud-only recordings when they are uploaded. Keep OneDrive
connected and ensure the selected files are available; read/upload failures are
reported and no render is submitted until all uploads succeed.

If the render connection fails, the server may still be working. The client shows
the job identifier when available: inspect Docker logs and server `outputs`
before resubmitting. A local download failure does not delete the server output;
the error gives its path and MP3 download URL. Recover the output from the server
or the repository's mounted `outputs` folder instead of generating it again.
Optional processing failures continue with warnings as in the app; critical
input, rendering or write failures stop and are not reported as success.

## Quick Start with Docker

### Prerequisites
- Docker installed on your system ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose (included with Docker Desktop)

### Option 1: Using Pre-built Image (Fastest)

Once the image is published to Docker Hub, you can run it directly without cloning the repository:

```bash
# Create directories for your audio files
mkdir -p audios/intro_audio audios/outro_audio audios/background_music outputs uploads core

# Run the container
docker run -d \
  --name ntn-podcast-creator \
  -p 127.0.0.1:7860:7860 \
  -v $(pwd)/audios/intro_audio:/app/audios/intro_audio \
  -v $(pwd)/audios/outro_audio:/app/audios/outro_audio \
  -v $(pwd)/audios/background_music:/app/audios/background_music \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/core:/app/core \
  elbruno/ntn-podcast-creator:latest

# View logs
docker logs -f ntn-podcast-creator

# Stop and remove
docker stop ntn-podcast-creator && docker rm ntn-podcast-creator
```

The application will be available at http://localhost:7860

### Option 2: Using Docker Compose (Recommended for Development)

If you want to build from source or modify the application:

```bash
# Clone the repository
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The application will be available at http://localhost:7860

### Option 3: Build from Source

If you want to build from source and customize the Docker image:

```bash
# Clone the repository
git clone https://github.com/elbruno/ntn-podcast-creator.git
cd ntn-podcast-creator

# Build the image
docker build -t ntn-podcast-creator .

# Run the container
docker run -d \
  --name ntn-podcast-creator \
  -p 127.0.0.1:7860:7860 \
  -v $(pwd)/audios/intro_audio:/app/audios/intro_audio \
  -v $(pwd)/audios/outro_audio:/app/audios/outro_audio \
  -v $(pwd)/audios/background_music:/app/audios/background_music \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/core:/app/core \
  ntn-podcast-creator

# View logs
docker logs -f ntn-podcast-creator

# Stop the container
docker stop ntn-podcast-creator

# Remove the container
docker rm ntn-podcast-creator
```

## Volume Mounts Explained

The Docker setup uses volume mounts to persist your data:

| Volume Mount | Purpose |
|--------------|---------|
| `./audios/intro_audio` | Your intro audio files |
| `./audios/outro_audio` | Your outro audio files |
| `./audios/background_music` | Your background music tracks |
| `./outputs` | Generated podcast files |
| `./uploads` | Uploaded voice recordings |

**Settings**: Compose now mounts `./core` at `/app/core` to persist settings and
templates across container recreation. Mount the directory, not just `config.json`:
settings saves use atomic file replacement. For standalone `docker run`, add
`-v <absolute-host-core-directory>:/app/core`.

**Existing containers**: Before enabling the new mount or rebuilding, back up the
running container's settings. A bind mount hides the image/container's old files.
From the repository root, copy to a new backup directory:

```powershell
docker cp ntn-podcast-creator:/app/core ./core-backup
```

Compare the backup with your host `core` directory, then copy the desired
`config.json` and `templates` into host `core` before recreating the container.
Do not replace saved settings with the repository's sample configuration.
Use paths under `/app/audios/...` or relative `audios/...` for saved audio; Windows
host paths are not readable inside a Linux container.

All these files and directories remain on your host machine, so your data persists even if you stop or remove the container.

## Pre-loading Audio Files

To have audio files automatically available when starting the container:

1. Before running Docker, place your audio files in the appropriate folders:
   ```
   audios/intro_audio/     - Place intro audio files here
   audios/outro_audio/     - Place outro audio files here
   audios/background_music/ - Place background music here
   ```

2. Start the container, and the files will be automatically loaded

## Accessing Your Podcasts

Generated podcasts are saved in the `./outputs` directory on your host machine. You can access them directly even while the container is running.

## Command-line Episode Creation

Once you have saved the desired settings in the portal, a recording can be
processed without opening a browser. The script starts the local Docker container
if no server is listening at the default URL, then waits for the API. Docker
Desktop's engine must already be running; the container must include the
`create_episode` API. Requires **PowerShell 7+** (`pwsh`),
not Windows PowerShell 5.1. No host Python installation or recording-folder mount
is needed; the client uploads the file over HTTP.

For an existing, up-to-date container, just run the script from the repository root:

```powershell
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a"
```

If the container predates the episode API, back up/migrate settings as described
above and rebuild explicitly:

```powershell
docker compose -f deployment/docker-compose.yml up -d --build
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a"
```

The command uses the next episode number from the configured RSS feed, skips
existing episode names, shows processing logs, downloads the MP3 to the
recording's folder, and opens it in your default audio player. The container also
retains its output in `/app/outputs`
(the host `outputs` directory with Compose).

```powershell
# Choose a name, e.g. when RSS is unavailable
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -Name ntn568

# Disable background music for this episode
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -NoBackground

# Explicitly enable transcription and wait for it
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -Transcribe

# Skip automatic playback
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -NoPlay

# Keep the previous download-to-current-directory behavior and skip playback
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -OutputDirectory "." -NoPlay

# Download to another folder or connect to another local port
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" `
  -OutputDirectory "C:\Podcasts\Finished" -ServerUrl "http://localhost:7860"

# Optional session alias for a shorter command
Set-Alias ntn-create "$PWD/scripts/ntn-create.ps1"
ntn-create "C:\Recordings\S recording 3.m4a"
```

### CLI defaults and safety

- Automatic startup is limited to `http://localhost:7860` and
  `http://127.0.0.1:7860` without a path prefix. A reachable server is reused.
  Other URLs never trigger Docker startup. `-NoAutoStart` disables startup.
- A named existing container is started without recreating or rebuilding it, so
  its saved settings are preserved. If none exists, the repository's Compose
  configuration is used (and may build the image on first run). The Compose file
  is resolved relative to the script, not your current working directory.
- Compose startup uses plain progress, disables ANSI output, and accepts startup
  prompts with `--yes` so piped PowerShell output does not require a console
  handle. Use a current Docker Compose plugin that supports these options.
- Readiness waits up to 180 seconds after Docker startup. Override with
  `-StartupTimeoutSeconds 300` for slower startup. Docker build time is separate
  from this timeout. The container stays running after the command finishes.
- Startup failures occur before upload/submission. Check Docker Desktop, container
  logs, and port mappings before retrying; startup never retries a render.
- Uses a snapshot of **saved** intro, outro, tracks, track volumes, voice processing,
  normalization, overlap, and quality settings. Unsaved portal edits do not apply.
- **Background music is on by default**, regardless of the recording's filename.
  This differs intentionally from the portal's per-recording filename rules.
  No saved tracks means no music.
- **Transcription is always off by default**, even if it is enabled in saved settings.
  `-Transcribe` uses the saved Whisper model and waits for completion. Failure produces
  a warning while preserving the exported MP3.
- Overrides do not change saved settings. Successful export updates the last output name.
- Downloads available transcripts, quality reports, and cleaned recordings alongside
  the MP3. The default destination is the recording's folder, not the terminal's
  current directory. `-OutputDirectory` overrides it for all downloaded files.
  Files are downloaded directly there; existing local files are never overwritten.
  Quality findings do not block an exported MP3.
- After successful downloads, the MP3 opens through the OS file association.
  `-NoPlay` disables this. Playback launch failure produces a warning without
  treating the saved episode as a failed render; open it manually or configure
  a default MP3 player. No files are moved or removed from the container.
- Original host recordings are never deleted. Server-owned temporary working copies
  are cleaned after each job, including failed jobs.
  Gradio's content-addressed upload cache follows the server's cache lifecycle; it
  is not deleted by a CLI job because other queued jobs may reference the same upload.
- Both terminal and website renders share the `episode-render` queue.
- Automatic naming refreshes RSS and skips existing outputs; RSS failure requires
  `-Name`. Names are extension-free stems containing letters, digits, `-`, or `_`.
  Explicit collisions fail. Server exports and local downloads are never overwritten.
- A failed connection after submission may leave a job running. The client never
  retries automatically. Check container logs/outputs before submitting again.
- Returns a nonzero exit code for critical render, upload, connection, or download
  failures. Optional-feature warnings leave a successfully downloaded episode usable.

### API contract

The client uses Gradio 6.10's existing HTTP server:

1. `POST /gradio_api/upload`, multipart field `files`, returns an uploaded path.
2. `POST /gradio_api/call/create_episode`, JSON `data`:
   `[FileData, name, background, transcribe]`. FileData contains `path` and
   `meta: {"_type": "gradio.FileData"}`; use the path returned by upload.
3. `GET /gradio_api/call/create_episode/{event_id}` streams SSE
   `generating`, `complete`, `heartbeat`, or `error` events.

Each result is a single JSON object in Gradio's output array, with
`schema: "ntn-episode-v1"`, `state`, `success`, and cumulative `logs`.
A successful terminal result includes `episode_name`, `output_path`, `warnings`,
`qc_status`, and FileData download references `mp3`, `transcript`, `quality_report`,
and `denoised` (optional references are null). Processing failures return
`state: "error"`, `success: false`, and `error`. Invalid upload paths can be rejected
by Gradio before the handler runs, producing an SSE error.

### Troubleshooting and exposure

- **API missing**: rebuild/update the container; older images cannot run this command.
- **Connection refused**: the CLI starts the default local container automatically
  if Docker Desktop's engine is ready. For custom URLs or `-NoAutoStart`, start the
  server yourself and verify its port mapping. If automatic startup times out,
  check container logs and increase `-StartupTimeoutSeconds` if needed.
- **`failed to get console: The handle is invalid`**: update the CLI script;
  automatic Compose startup now runs non-interactively with plain-text output.
- **Saved asset missing**: repair the saved intro/outro/music paths in Settings.
- **Download exists**: use another output directory; the server episode remains available.
- **RSS unavailable**: specify `-Name` rather than accepting an unsafe fallback.
- This workflow is for a **trusted local instance**. Compose publishes port 7860 on
  `127.0.0.1` only. For standalone Docker use `-p 127.0.0.1:7860:7860`.
  This API does not add authentication; do not expose it directly to the internet.

## Updating the Application

To update to the latest version:

```bash
# Stop and remove the current container
docker-compose down

# Pull the latest changes
git pull

# Rebuild and start
docker-compose up -d --build
```

## Environment Variables

You can customize the application using environment variables:

```yaml
environment:
  - GRADIO_SERVER_NAME=0.0.0.0  # Server host
  - GRADIO_SERVER_PORT=7860     # Server port
```

## Troubleshooting

### Port Already in Use

If port 7860 is already in use, change it in `docker-compose.yml`:

```yaml
ports:
  - "8080:7860"  # Use port 8080 instead
```

Then access the application at http://localhost:8080

### Permission Issues

If you encounter permission issues with volume mounts:

```bash
# Ensure directories have proper permissions
chmod -R 755 audios outputs uploads
```

### Container Won't Start

Check the logs for error messages:

```bash
docker-compose logs
```

### FFmpeg Not Found

The Docker image includes FFmpeg automatically. If you see FFmpeg errors, rebuild the image:

```bash
docker-compose build --no-cache
docker-compose up -d
```

## Advanced Configuration

### Custom Network

To run on a custom Docker network:

```yaml
networks:
  podcast-network:
    driver: bridge

services:
  ntn-podcast-creator:
    networks:
      - podcast-network
```

### Resource Limits

To limit CPU and memory usage:

```yaml
services:
  ntn-podcast-creator:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## Building for Production

For production deployment, consider:

1. **Using a reverse proxy** (nginx, Traefik) for HTTPS
2. **Setting up automatic restarts** (already configured with `restart: unless-stopped`)
3. **Regular backups** of the `audios`, `outputs`, and `config.json` files
4. **Monitoring** container health and logs

## Security Considerations

- The application runs on `0.0.0.0` to be accessible from any network interface
- For production, consider adding authentication (e.g., using nginx basic auth)
- Keep your Docker image updated with the latest security patches
- Don't expose the container directly to the internet without proper security measures

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review the [User Manual](USER_MANUAL.md)
- Open an issue on GitHub
