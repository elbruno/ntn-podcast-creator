#!/bin/bash

# Docker Test Script for NTN Podcast Creator
# This script helps verify your Docker setup is working correctly
# Usage: ./test_docker.sh [--cleanup]

set -e

# Parse arguments
AUTO_CLEANUP=false
if [[ "$1" == "--cleanup" ]]; then
    AUTO_CLEANUP=true
fi

echo "=================================="
echo "NTN Podcast Creator - Docker Test"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker is installed"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "   Please start Docker Desktop or the Docker service"
    exit 1
fi

echo "✓ Docker is running"

# Check Docker Compose
if docker compose version &> /dev/null; then
    echo "✓ Docker Compose is available (plugin)"
elif command -v docker-compose &> /dev/null; then
    echo "✓ Docker Compose is available (standalone)"
else
    echo "⚠️  Docker Compose not found (optional)"
fi

echo ""
echo "=================================="
echo "Building Docker Image"
echo "=================================="
echo ""

# Build the image
echo "Building ntn-podcast-creator image..."
docker build -t ntn-podcast-creator:test .

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo ""
echo "=================================="
echo "Testing Docker Run"
echo "=================================="
echo ""

# Create test directories
echo "Creating test directories..."
mkdir -p test_docker/{audios/{intro_audio,outro_audio,background_music},outputs,uploads}

# Run container in test mode
echo "Starting test container..."
docker run -d \
  --name ntn-podcast-test \
  -p 7860:7860 \
  -v $(pwd)/test_docker/audios/intro_audio:/app/audios/intro_audio \
  -v $(pwd)/test_docker/audios/outro_audio:/app/audios/outro_audio \
  -v $(pwd)/test_docker/audios/background_music:/app/audios/background_music \
  -v $(pwd)/test_docker/outputs:/app/outputs \
  -v $(pwd)/test_docker/uploads:/app/uploads \
  ntn-podcast-creator:test

if [ $? -ne 0 ]; then
    echo "❌ Failed to start container"
    exit 1
fi

echo "✓ Container started"
echo ""
echo "Waiting for application to start (10 seconds)..."
sleep 10

# Check if container is still running
if docker ps | grep -q ntn-podcast-test; then
    echo "✓ Container is running"
else
    echo "❌ Container stopped unexpectedly"
    echo ""
    echo "Container logs:"
    docker logs ntn-podcast-test
    docker rm ntn-podcast-test
    exit 1
fi

# Check if application is responding
echo ""
echo "Testing application endpoint..."

# Try curl first, fall back to wget or python if not available
if command -v curl &> /dev/null; then
    if curl -s -f http://localhost:7860 > /dev/null 2>&1; then
        echo "✓ Application is responding"
    else
        echo "⚠️  Application may not be fully ready yet"
        echo "   Try accessing http://localhost:7860 in your browser"
    fi
elif command -v wget &> /dev/null; then
    if wget -q --spider http://localhost:7860 2>&1; then
        echo "✓ Application is responding"
    else
        echo "⚠️  Application may not be fully ready yet"
        echo "   Try accessing http://localhost:7860 in your browser"
    fi
elif command -v python3 &> /dev/null; then
    if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:7860', timeout=5)" 2>&1; then
        echo "✓ Application is responding"
    else
        echo "⚠️  Application may not be fully ready yet"
        echo "   Try accessing http://localhost:7860 in your browser"
    fi
else
    echo "⚠️  Cannot test endpoint (curl, wget, or python not available)"
    echo "   Please manually check http://localhost:7860 in your browser"
fi

echo ""
echo "=================================="
echo "Container Information"
echo "=================================="
echo ""

echo "Container ID:"
docker ps --filter name=ntn-podcast-test --format "{{.ID}}"

echo ""
echo "Container Status:"
docker ps --filter name=ntn-podcast-test --format "{{.Status}}"

echo ""
echo "Container Logs (last 20 lines):"
docker logs --tail 20 ntn-podcast-test

echo ""
echo "=================================="
echo "✓ Docker Test Complete"
echo "=================================="
echo ""
echo "The application is running at: http://localhost:7860"
echo ""
echo "To view logs:"
echo "  docker logs -f ntn-podcast-test"
echo ""
echo "To stop and clean up:"
echo "  docker stop ntn-podcast-test"
echo "  docker rm ntn-podcast-test"
echo "  rm -rf test_docker"
echo ""

# Cleanup based on mode
if [ "$AUTO_CLEANUP" = true ]; then
    echo "Auto-cleanup enabled, removing test container and directories..."
    docker stop ntn-podcast-test
    docker rm ntn-podcast-test
    rm -rf test_docker
    echo "✓ Cleanup complete"
elif [ -t 0 ]; then
    # Interactive mode - prompt user
    echo "To clean up now, run:"
    read -p "Stop and remove test container? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stop ntn-podcast-test
        docker rm ntn-podcast-test
        echo "✓ Test container removed"
        echo ""
        read -p "Remove test directories? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf test_docker
            echo "✓ Test directories removed"
        fi
    fi
else
    # Non-interactive mode - skip cleanup prompts
    echo "Note: Running in non-interactive mode. Use --cleanup flag for automatic cleanup."
fi
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf test_docker
        echo "✓ Test directories removed"
    fi
fi

echo ""
echo "Happy podcasting! 🎙️"
