#!/bin/bash

# NTN Podcast Creator - Setup Script
# This script helps set up the development environment and verify installation

set -e

echo "🎙️ NTN Podcast Creator - Setup & Verification"
echo "=" * 50

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    echo "🐍 Checking Python installation..."
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo "✓ Python $PYTHON_VERSION found"

        # Check if version is 3.8 or higher
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            echo "✓ Python version is compatible (3.8+)"
        else
            echo "❌ Python 3.8+ is required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        echo "❌ Python 3 is not installed"
        echo "Please install Python 3.8 or higher"
        exit 1
    fi
}

# Function to check FFmpeg
check_ffmpeg() {
    echo "🎵 Checking FFmpeg installation..."
    if command_exists ffmpeg; then
        echo "✓ FFmpeg found"
    else
        echo "⚠️  FFmpeg not found"
        echo "Installing FFmpeg is recommended for audio processing"
        echo ""
        echo "Install commands:"
        echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "  macOS: brew install ffmpeg"
        echo "  Windows: Download from https://ffmpeg.org/download.html"
        echo ""
    fi
}

# Function to install Python dependencies
install_dependencies() {
    echo "📦 Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        python3 -m pip install --upgrade pip
        python3 -m pip install -r requirements.txt
        echo "✓ Dependencies installed"
    else
        echo "❌ requirements.txt not found"
        exit 1
    fi
}

# Function to verify directory structure
check_directory_structure() {
    echo "📁 Verifying directory structure..."

    REQUIRED_DIRS=("features" "core" "tests" "docs" "audios" "outputs" "uploads")
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo "✓ $dir/ exists"
        else
            echo "❌ $dir/ missing"
            exit 1
        fi
    done
}

# Function to run basic tests
run_tests() {
    echo "🧪 Running basic functionality tests..."

    # Test imports
    echo "Testing imports..."
    python3 -c "from features import AudioProcessor, ConfigManager; print('✓ Core imports work')"

    # Run test suite if available
    if [ -f "tests/test_audio_denoising.py" ]; then
        echo "Running audio denoising tests..."
        python3 tests/test_audio_denoising.py
    fi

    echo "✓ Basic tests passed"
}

# Function to create sample environment file
create_env_sample() {
    echo "⚙️ Creating development environment..."

    if [ -f "deployment/.env.sample" ] && [ ! -f ".env" ]; then
        cp deployment/.env.sample .env
        echo "✓ Created .env from sample"
        echo "Edit .env file to configure your environment"
    fi
}

# Main setup process
main() {
    echo "Starting setup process..."
    echo ""

    check_python
    echo ""

    check_ffmpeg
    echo ""

    install_dependencies
    echo ""

    check_directory_structure
    echo ""

    create_env_sample
    echo ""

    run_tests
    echo ""

    echo "🎉 Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Start the application: python app.py"
    echo "2. Open http://localhost:7860 in your browser"
    echo "3. Upload audio files to audios/ folders for defaults"
    echo "4. Check docs/ for user manual and guides"
    echo ""
    echo "For Docker deployment: ./scripts/test_docker.sh"
}

# Run main function
main "$@"
