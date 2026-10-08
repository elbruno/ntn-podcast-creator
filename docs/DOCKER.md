# Docker Deployment Guide

This guide explains how to run the NTN Podcast Creator using Docker.

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
existing episode names, shows processing logs, and downloads the MP3 to the
current directory. The container also retains its output in `/app/outputs`
(the host `outputs` directory with Compose).

```powershell
# Choose a name, e.g. when RSS is unavailable
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -Name ntn568

# Disable background music for this episode
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -NoBackground

# Explicitly enable transcription and wait for it
.\scripts\ntn-create.ps1 "C:\Recordings\S recording 3.m4a" -Transcribe

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
  the MP3. Quality findings do not block an exported MP3.
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
