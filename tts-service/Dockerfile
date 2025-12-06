# Use build argument to choose base image (CPU vs GPU)
ARG BASE_IMAGE=nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
FROM ${BASE_IMAGE}

# Re-declare build arg for use in subsequent layers
ARG REQUIREMENTS_FILE=requirements.txt

# Install system dependencies
# Note: python3/pip may already be installed on python:* base images
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    libsndfile1 \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install (leverage layer caching)
COPY requirements*.txt ./
RUN pip3 install --no-cache-dir -r ${REQUIREMENTS_FILE}

# Copy application (separate layer for better caching)
COPY app.py .

# Expose port
EXPOSE 5002

# Run the application
CMD ["python3", "app.py"]
