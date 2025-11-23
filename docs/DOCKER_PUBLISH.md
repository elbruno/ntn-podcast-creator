# Publishing to Docker Hub

This guide explains how to build and publish the NTN Podcast Creator Docker image to Docker Hub.

## Prerequisites

- Docker installed and running
- Docker Hub account ([Sign up here](https://hub.docker.com/signup))
- Logged in to Docker Hub via CLI: `docker login`

## Building the Image

### Build for Your Architecture

```bash
# Navigate to the project root
cd /path/to/ntn-podcast-creator

# Build the image
docker build -t your-dockerhub-username/ntn-podcast-creator:latest .

# Tag with version number (optional but recommended)
docker build -t your-dockerhub-username/ntn-podcast-creator:v1.0.0 .
```

### Build Multi-Architecture Image (Recommended)

To support both ARM64 (Apple Silicon, ARM servers) and AMD64 (Intel/AMD):

```bash
# Create a new builder instance
docker buildx create --name multiarch --use

# Build and push multi-architecture image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-dockerhub-username/ntn-podcast-creator:latest \
  -t your-dockerhub-username/ntn-podcast-creator:v1.0.0 \
  --push .
```

## Publishing to Docker Hub

### Method 1: Direct Push

```bash
# Tag the image with your Docker Hub username
docker tag ntn-podcast-creator:latest your-dockerhub-username/ntn-podcast-creator:latest
docker tag ntn-podcast-creator:latest your-dockerhub-username/ntn-podcast-creator:v1.0.0

# Push to Docker Hub
docker push your-dockerhub-username/ntn-podcast-creator:latest
docker push your-dockerhub-username/ntn-podcast-creator:v1.0.0
```

### Method 2: Using Buildx (for multi-arch)

```bash
# Build and push in one command
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-dockerhub-username/ntn-podcast-creator:latest \
  -t your-dockerhub-username/ntn-podcast-creator:v1.0.0 \
  --push .
```

## For Repository Owner (elbruno)

To publish the official image:

```bash
# Build multi-architecture image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t elbruno/ntn-podcast-creator:latest \
  -t elbruno/ntn-podcast-creator:v1.0.0 \
  --push .
```

## Versioning Strategy

Use semantic versioning for tags:
- `latest` - Always points to the most recent stable release (use for quick starts and examples)
- `v1.0.0` - Specific version number (use for production deployments requiring exact versions)
- `v1.0` - Minor version (receives patch updates automatically, good for production)
- `v1` - Major version (receives all updates within major version, good for development/testing)

**Recommended Usage:**
- **Production**: Use specific versions like `v1.0.0` or minor versions like `v1.0` for stability
- **Development/Testing**: Use `latest` or major versions like `v1` for latest features
- **Documentation/Examples**: Use `latest` for simplicity

Example:
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t elbruno/ntn-podcast-creator:latest \
  -t elbruno/ntn-podcast-creator:v1.0.0 \
  -t elbruno/ntn-podcast-creator:v1.0 \
  -t elbruno/ntn-podcast-creator:v1 \
  --push .
```

## Automated Builds with GitHub Actions

For automated builds on every release, create `.github/workflows/docker-publish.yml`:

```yaml
name: Publish Docker Image

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: elbruno/ntn-podcast-creator
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=raw,value=latest

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

## Verify the Published Image

After publishing, verify the image works:

```bash
# Pull the image
docker pull your-dockerhub-username/ntn-podcast-creator:latest

# Run it
docker run -d \
  --name ntn-podcast-test \
  -p 7860:7860 \
  your-dockerhub-username/ntn-podcast-creator:latest

# Check logs
docker logs -f ntn-podcast-test

# Access at http://localhost:7860

# Clean up
docker stop ntn-podcast-test
docker rm ntn-podcast-test
```

## Update Documentation

After publishing to Docker Hub, update the documentation to reference the public image:

In `README.md` and `docs/DOCKER.md`, add:

```bash
# Quick start with published image (no build needed)
docker run -d \
  --name ntn-podcast-creator \
  -p 7860:7860 \
  -v $(pwd)/audios:/app/audios \
  -v $(pwd)/outputs:/app/outputs \
  elbruno/ntn-podcast-creator:latest
```

Or update `docker-compose.yml`:

```yaml
services:
  ntn-podcast-creator:
    image: elbruno/ntn-podcast-creator:latest
    # ... rest of the configuration
```

## Troubleshooting

### Build Fails with Certificate Error
If you encounter SSL certificate errors during build, you may need to configure Docker to use a different DNS or disable SSL verification temporarily (not recommended for production).

### Multi-arch Build Not Working
Ensure you have buildx installed and configured:
```bash
docker buildx version
docker buildx ls
```

### Push Permission Denied
Make sure you're logged in:
```bash
docker login
```

### Image Too Large
The current image is optimized with:
- Python slim base image
- Minimal dependencies
- Multi-stage builds (if needed)

Current image size should be ~500-800 MB compressed.

## Security Scanning

Before publishing, scan for vulnerabilities:

```bash
# Using Docker Scout
docker scout cves ntn-podcast-creator:latest

# Using Trivy
trivy image ntn-podcast-creator:latest
```

## Best Practices

1. **Always scan images** for security vulnerabilities before publishing
2. **Use semantic versioning** for predictable updates
3. **Tag both latest and version-specific** tags
4. **Support multiple architectures** (amd64, arm64)
5. **Keep the image updated** with security patches
6. **Document breaking changes** in release notes
7. **Test thoroughly** before pushing to `latest` tag

## Resources

- [Docker Hub](https://hub.docker.com/)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Semantic Versioning](https://semver.org/)
