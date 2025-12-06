# Use build argument to choose base image (CPU vs GPU)
# Default to lightweight Python slim for CPU builds
ARG BASE_IMAGE=python:3.10-slim-bullseye
FROM ${BASE_IMAGE} AS base

# Re-declare build arg for use in subsequent layers
ARG REQUIREMENTS_FILE=requirements-cpu.txt

# Install system dependencies (shared layer for CPU and GPU)
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

# ============================================================================
# OPTIMIZATION: Install dependencies based on variant to avoid duplication
# ============================================================================
# Copy appropriate requirements file
COPY requirements*.txt ./

# Install dependencies conditionally
# CPU builds: Install common packages, then PyTorch CPU separately
# GPU builds: Install all packages from requirements.txt (includes PyTorch GPU)
RUN if [ "${REQUIREMENTS_FILE}" = "requirements-cpu.txt" ]; then \
    echo "Building CPU variant..."; \
    echo "Installing common dependencies..."; \
    pip3 install --no-cache-dir -r requirements-cpu.txt && \
    echo "Installing PyTorch CPU version..."; \
    pip3 install --no-cache-dir torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu; \
    else \
    echo "Building GPU variant..."; \
    echo "Installing all dependencies (including PyTorch GPU)..."; \
    pip3 install --no-cache-dir -r requirements.txt; \
    fi

# Copy application code (separate layer for better caching)
COPY app.py .

# Expose port
EXPOSE 5002

# Run the application
CMD ["python3", "app.py"]
