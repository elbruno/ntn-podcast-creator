# Use Python 3.12 slim base image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY audio_processor.py .
COPY config_manager.py .

# Create necessary directories with proper permissions
RUN mkdir -p /app/audios/intro_audio \
    /app/audios/outro_audio \
    /app/audios/background_music \
    /app/audios/test \
    /app/uploads \
    /app/outputs \
    && chmod -R 777 /app/uploads \
    && chmod -R 777 /app/outputs

# Expose Gradio port
EXPOSE 7860

# Set environment variables
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"

# Run the application
CMD ["python", "app.py"]
