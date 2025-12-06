# Use build argument to choose base image (CPU vs GPU)
ARG BASE_IMAGE=nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
FROM ${BASE_IMAGE} AS base

# Re-declare build arg for use in subsequent layers
ARG REQUIREMENTS_FILE=requirements.txt

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
# OPTIMIZATION: Install common dependencies first (shared cache layer)
# ============================================================================
# Copy only requirements-cpu.txt first to install common dependencies
COPY requirements-cpu.txt ./
RUN pip3 install --no-cache-dir -r requirements-cpu.txt

# ============================================================================
# OPTIMIZATION: Install PyTorch separately based on variant
# ============================================================================
# For CPU builds, install CPU-optimized PyTorch
# For GPU builds, install CUDA-enabled PyTorch
RUN if [ "${REQUIREMENTS_FILE}" = "requirements-cpu.txt" ]; then \
    echo "Installing PyTorch CPU version..."; \
    pip3 install --no-cache-dir torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu; \
    else \
    echo "Installing PyTorch GPU version..."; \
    pip3 install --no-cache-dir torch==2.1.2 torchaudio==2.1.2; \
    fi

# Copy application code (separate layer for better caching)
COPY app.py .

# Expose port
EXPOSE 5002

# Run the application
CMD ["python3", "app.py"]
