# Base image with PyTorch and CUDA 12.1 support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
# ffmpeg is required for audio processing (Whisper)
# git is often required to install whisperx directly from source
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libavfilter-dev libavdevice-dev libswresample-dev \
    pkg-config \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .

# Create a constraint file to force Cython < 3
RUN echo "Cython<3" > /tmp/constraint.txt

# Obsidian Layer: Absolute infrastructure dependencies to prevent boot crashes
RUN pip install --no-cache-dir \
    "pydantic>=2.7.0,<2.8.0" \
    "langchain>=0.3.0,<0.4.0" \
    "supabase>=2.4.0,<2.5.0" \
    "langgraph>=0.2.0,<0.3.0" \
    "gunicorn==23.0.0" \
    "sentry-sdk[fastapi]" \
    "google-cloud-texttospeech" \
    "google-auth-oauthlib" \
    "google-auth-httplib2" \
    "httpx" \
    "reportlab" \
    "pdfminer.six" \
    "scikit-learn" \
    "numpy" \
    "lxml_html_clean" \
    "stripe" \
    "google-api-python-client" \
    "python-multipart"

# Install Python dependencies
# Removed PIP_CONSTRAINT to avoid Pydantic V1 legacy lock issues
RUN pip install --no-cache-dir -r requirements.txt

# Install WhisperX (Hack Mode - Ignore checks)
RUN pip install --no-cache-dir whisperx==3.1.1 --no-deps

# Copy the rest of the application code
COPY . .

# Expose port (adjust based on your Flask/FastAPI settings)
EXPOSE 8080

# Default command (can be overridden by docker-compose)
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "api_server:app"]