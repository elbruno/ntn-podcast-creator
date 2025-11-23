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
mkdir -p audios/intro_audio audios/outro_audio audios/background_music outputs uploads

# Run the container
docker run -d \
  --name ntn-podcast-creator \
  -p 7860:7860 \
  -v $(pwd)/audios/intro_audio:/app/audios/intro_audio \
  -v $(pwd)/audios/outro_audio:/app/audios/outro_audio \
  -v $(pwd)/audios/background_music:/app/audios/background_music \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
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
  -p 7860:7860 \
  -v $(pwd)/audios/intro_audio:/app/audios/intro_audio \
  -v $(pwd)/audios/outro_audio:/app/audios/outro_audio \
  -v $(pwd)/audios/background_music:/app/audios/background_music \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
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

**Note**: Settings (config.json) are stored inside the container and will persist as long as the container exists. To preserve settings across container deletions, you can optionally mount config.json, but ensure the file exists first: `touch config.json` before starting the container.

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
