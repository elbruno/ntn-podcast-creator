# Test Suite

Comprehensive test suite for the NTN Podcast Creator application.

## 🧪 Test Files

### Core Functionality Tests

#### [test_audio_denoising.py](test_audio_denoising.py)
- Tests the AI audio denoising processor
- Validates graceful handling of missing libraries
- Tests configuration management integration
- Verifies enabled/disabled flag behavior

#### [test_podcast_creation.py](test_podcast_creation.py)
- End-to-end podcast creation testing
- Tests audio mixing and processing pipeline
- Validates output file generation
- Tests with real audio files

#### [test_large_file_denoising.py](test_large_file_denoising.py)
- Tests the new chunking functionality for large files
- Validates audio splitting and merging
- Tests memory efficiency and cleanup
- Simulates large file processing scenarios

#### [test_audio_enhancement.py](test_audio_enhancement.py)
- Tests Adobe audio enhancement integration
- Validates browser automation components
- Tests configuration and error handling

### Infrastructure Tests

#### [test_docker.sh](test_docker.sh)
- Docker container build and deployment tests
- Application startup validation
- Network connectivity testing
- Automated cleanup and teardown

## 🚀 Running Tests

### Individual Tests
```bash
# From project root
python tests/test_audio_denoising.py
python tests/test_podcast_creation.py
python tests/test_large_file_denoising.py
python tests/test_audio_enhancement.py
```

### Docker Tests
```bash
# From project root
chmod +x tests/test_docker.sh
./tests/test_docker.sh
```

### All Tests (if using pytest)
```bash
# From project root
python -m pytest tests/
```

## 📊 Test Coverage

The test suite covers:
- ✅ Audio processing and mixing
- ✅ AI denoising with chunking
- ✅ Configuration management
- ✅ Error handling and graceful degradation
- ✅ File I/O operations
- ✅ Integration between components
- ✅ Docker deployment
- ✅ Large file processing

## 🛠️ Test Requirements

Tests require:
- Python 3.8+
- All application dependencies (see requirements.txt)
- FFmpeg installed
- Test audio files in `audios/test/` directory
- Optional: Docker for container tests

## 📝 Adding New Tests

When adding new tests:
1. Follow the `test_*.py` naming convention
2. Include docstrings explaining test purpose
3. Test both success and failure scenarios
4. Clean up any temporary files created
5. Update this README with new test descriptions
