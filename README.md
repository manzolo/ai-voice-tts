# AI Voice TTS - Text-to-Speech Service

![CI Status](https://github.com/manzolo/ai-voice-tts/actions/workflows/ci.yml/badge.svg)

Local GPU-accelerated Text-to-Speech service with web interface. Runs completely offline using Docker containers.

<a href="https://www.buymeacoffee.com/manzolo">
  <img src=".github/blue-button.png" alt="Buy Me A Coffee" width="200">
</a>

## Features

- **Multilingual Support**: 16+ languages (English, Italian, Spanish, French, German, Portuguese, etc.)
- **Voice Options**: Male and female voices for each language
- **GPU Acceleration**: Optional CUDA support for faster synthesis
- **Offline Operation**: No cloud dependencies, runs entirely locally
- **Web Interface**: User-friendly browser-based UI
- **REST API**: Simple HTTP API for programmatic access

## Technology Stack

- **TTS Engine**: Coqui TTS with XTTS v2 model
- **Backend**: FastAPI (Python)
- **Web UI**: Single-page HTML/JavaScript application
- **Infrastructure**: Docker Compose

## Quick Start

### CPU Mode (Default)

```bash
make setup
```

This will:
1. Create `.env` file from template
2. Build Docker images
3. Download TTS models (~2GB on first use)
4. Start services

Access the web interface at: http://localhost:8080

### GPU Mode (Faster)

Requirements: NVIDIA GPU with Docker GPU support

```bash
make setup-gpu
```

## Usage

### Web Interface

1. Open http://localhost:8080 in your browser
2. Enter text to synthesize
3. Select language and voice (male/female)
4. Click "Generate Speech" to create audio
5. Download or play the generated audio

### API Usage

```bash
curl -X POST http://localhost:9876/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "language": "en", "speaker": "male"}' \
  --output speech.wav
```

**Parameters:**
- `text` (required): Text to synthesize
- `language` (optional): Two-letter language code (default: `en`)
- `speaker` (optional): `"male"` or `"female"` (default: `male`)

**Supported Languages:**
`en`, `es`, `fr`, `de`, `it`, `pt`, `pl`, `tr`, `ru`, `nl`, `cs`, `ar`, `zh-cn`, `hu`, `ko`, `ja`, `hi`

## Common Commands

```bash
make up         # Start services (CPU mode)
make up-gpu     # Start services (GPU mode)
make down       # Stop services
make restart    # Restart services
make logs       # View service logs
make status     # Check container status
make test       # Test TTS API
make clean      # Remove containers
make clean-all  # Remove containers + downloaded models
```

## Configuration

Edit `.env` to change settings:

```bash
# TTS defaults
DEFAULT_LANGUAGE=en
DEFAULT_SPEAKER=male

# TTS Model Configuration
# Default: XTTS v2 (~2GB, multilingual)
TTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2

# For faster CI/testing with smaller models (~100-200MB, English only):
# TTS_MODEL=tts_models/en/ljspeech/glow-tts
# TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC

# Optional vocoder (only for non-end-to-end models)
TTS_VOCODER=

# Ports
TTS_PORT=9876
WEB_PORT=8080

# GPU (for GPU mode only)
CUDA_VISIBLE_DEVICES=0
```

### Using Smaller Models

For development, CI, or resource-constrained environments, you can use smaller models:

**glow-tts** (~100MB, fast, English only):
```bash
TTS_MODEL=tts_models/en/ljspeech/glow-tts
```

**tacotron2-DDC** (~200MB, high quality, English only):
```bash
TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
TTS_VOCODER=vocoder_models/en/ljspeech/hifigan_v2
```

## CI/CD and Testing

The project includes automated testing via GitHub Actions that:

1. **Builds Docker images** without errors
2. **Starts the service** with a small model (glow-tts ~100MB)
3. **Verifies health endpoint** returns healthy status
4. **Tests TTS API** by generating a test audio file
5. **Validates output** ensures generated WAV file is valid

The CI workflow uses a smaller model to stay within GitHub Actions resource limits while still testing the full functionality. See `.github/workflows/ci.yml` for details.

**Running tests locally:**
```bash
make test  # Test the API with current configuration
```

## Architecture

The project consists of two Docker containers:

1. **tts**: FastAPI service running Coqui TTS
   - Port: 9876 (configurable)
   - Models cached in `./models` directory
   - Endpoint: `POST /api/tts`

2. **web**: Static file server
   - Port: 8080 (configurable)
   - Serves the web interface

## Disk Requirements

- **Docker images**: ~5GB
- **TTS models**: ~2GB (downloaded on first use)
- **Total**: ~7GB

## GPU Requirements (GPU mode only)

- **VRAM**: ~2GB for XTTS v2 model
- **CUDA**: Compatible NVIDIA GPU with CUDA 12.1+
- **Driver**: Recent NVIDIA drivers with Docker GPU support

## Troubleshooting

### Container won't start
```bash
make logs  # Check logs for errors
```

### GPU not detected (GPU mode)
```bash
# Test GPU access:
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### Models not downloading
- Check internet connectivity
- Ensure ~2GB disk space available
- Models download on first API call (can take 5-10 minutes)
- Check logs: `make logs`

### Web interface can't connect to API
- Verify containers are running: `make status`
- Check browser console for errors
- Ensure TTS_PORT matches in `.env` and web interface

## API Reference

### POST /api/tts

Generate speech from text.

**Request:**
```json
{
  "text": "Text to synthesize",
  "language": "en",
  "speaker": "male"
}
```

**Response:** WAV audio file (24kHz)

### GET /

Get service status and configuration.

**Response:**
```json
{
  "status": "ready",
  "gpu_available": true,
  "supported_languages": [...],
  "speaker_map": {...}
}
```

## License

This project uses Coqui TTS, which requires agreeing to their Terms of Service. By running this service, you agree to the Coqui TTS ToS.

## Links

- [Coqui TTS](https://github.com/coqui-ai/TTS)
- [XTTS v2 Model](https://huggingface.co/coqui/XTTS-v2)
