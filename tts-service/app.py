from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from TTS.api import TTS
import io
import torch
import os
import soundfile as sf
import nltk
import numpy as np
from typing import List, Optional
import re
import glob

app = FastAPI()

# Get CORS configuration from environment
CORS_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")
CORS_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
CORS_METHODS = os.getenv("CORS_ALLOW_METHODS", "*")
CORS_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "*")

# Convert comma-separated origins to list, or use ["*"] for wildcard
if CORS_ORIGINS == "*":
    origins_list = ["*"]
else:
    origins_list = [origin.strip() for origin in CORS_ORIGINS.split(",")]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=[CORS_METHODS] if CORS_METHODS == "*" else [method.strip() for method in CORS_METHODS.split(",")],
    allow_headers=[CORS_HEADERS] if CORS_HEADERS == "*" else [header.strip() for header in CORS_HEADERS.split(",")],
)

print(f"CORS Configuration:")
print(f"  - Origins: {origins_list}")
print(f"  - Credentials: {CORS_CREDENTIALS}")
print(f"  - Methods: {CORS_METHODS}")
print(f"  - Headers: {CORS_HEADERS}")

# Get defaults from environment
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "it")
DEFAULT_SPEAKER = os.getenv("DEFAULT_SPEAKER", "male")

# Model configuration - allows using smaller models for CI/testing
TTS_MODEL = os.getenv("TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
TTS_VOCODER = os.getenv("TTS_VOCODER", None)  # Optional vocoder for non-end-to-end models

# Global state tracking
tts = None
model_name = TTS_MODEL.split('/')[-1] if TTS_MODEL else "unknown"
loading_state = {
    "status": "initializing",  # initializing, downloading, loading, ready, error
    "message": "Service starting up...",
    "progress": 0
}

def initialize_models():
    """Initialize NLTK and TTS models. Called during startup."""
    global tts, loading_state

    try:
        # Download NLTK data for sentence tokenization
        loading_state["status"] = "downloading"
        loading_state["message"] = "Downloading NLTK data..."
        loading_state["progress"] = 10

        try:
            nltk.data.find('tokenizers/punkt')
            print("NLTK punkt tokenizer already available")
        except LookupError:
            print("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
            print("NLTK punkt tokenizer downloaded!")

        loading_state["progress"] = 20

        # Initialize TTS model (configurable via environment)
        loading_state["status"] = "downloading"
        is_xtts = "xtts" in TTS_MODEL.lower()
        model_size = "~2GB" if is_xtts else "~100-500MB"
        loading_state["message"] = f"Downloading/loading {model_name} model ({model_size}, may take several minutes on first run)..."
        loading_state["progress"] = 30
        print(f"Loading TTS model: {TTS_MODEL}")
        if TTS_VOCODER:
            print(f"Using vocoder: {TTS_VOCODER}")

        # Initialize TTS with or without vocoder
        if TTS_VOCODER:
            tts = TTS(TTS_MODEL, vocoder_path=TTS_VOCODER, gpu=torch.cuda.is_available())
        else:
            tts = TTS(TTS_MODEL, gpu=torch.cuda.is_available())

        loading_state["status"] = "ready"
        loading_state["message"] = "TTS service ready"
        loading_state["progress"] = 100
        print(f"TTS model loaded: {model_name}")

    except Exception as e:
        loading_state["status"] = "error"
        loading_state["message"] = f"Failed to initialize: {str(e)}"
        loading_state["progress"] = 0
        print(f"Error loading models: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    """Run model initialization in background on startup."""
    import threading
    print("Starting model initialization in background...")
    thread = threading.Thread(target=initialize_models, daemon=True)
    thread.start()


# Map speaker selection to built-in XTTS v2 speakers
# XTTS v2 has different speakers that work better with different languages
SPEAKER_MAP = {
    "male": "Andrew Chipper",      # English male
    "female": "Claribel Dervla",   # English female
    "male_deep": "Damien Black",   # Deep male voice
    "female_soft": "Sofia Hellen",  # Soft female voice
    "male_italian": "Abrahan Mack", # Works well for Italian male
    "female_italian": "Ana Florence" # Works well for Italian female
}

# Language-specific speaker preferences
LANGUAGE_SPEAKER_MAP = {
    "it": {  # Italian
        "male": "Abrahan Mack",
        "female": "Ana Florence"
    },
    "es": {  # Spanish
        "male": "Damien Black",
        "female": "Sofia Hellen"
    },
    "fr": {  # French
        "male": "Damien Black",
        "female": "Claribel Dervla"
    },
    "de": {  # German
        "male": "Andrew Chipper",
        "female": "Sofia Hellen"
    },
    "pt": {  # Portuguese
        "male": "Abrahan Mack",
        "female": "Ana Florence"
    }
    # Default to SPEAKER_MAP for other languages
}

print(f"Configuration:")
print(f"  - TTS Model: {TTS_MODEL}")
if TTS_VOCODER:
    print(f"  - Vocoder: {TTS_VOCODER}")
print(f"  - GPU available: {torch.cuda.is_available()}")
print(f"  - Default language: {DEFAULT_LANGUAGE}, Default speaker: {DEFAULT_SPEAKER}")
print(f"  - Available speakers: {list(SPEAKER_MAP.keys())}")
print(f"  - Language-specific mappings: {list(LANGUAGE_SPEAKER_MAP.keys())}")


# Threshold for using sentence-based chunking (characters)
CHUNK_THRESHOLD = 200

def clean_text_for_tts(text: str) -> str:
    """Clean text to prevent TTS from vocalizing punctuation."""
    # Replace ellipsis (...) with a single dot
    text = re.sub(r'\.{3,}', '.', text)
    # Replace multiple dots with single dot
    text = re.sub(r'\.{2,}', '.', text)
    # Remove standalone dots (spaces before and after)
    text = re.sub(r'\s+\.\s+', '. ', text)
    # Fix dots without space after (e.g., "word.word" -> "word. word")
    text = re.sub(r'\.([a-zA-Z])', r'. \1', text)
    # Ensure single space after sentence-ending punctuation
    text = re.sub(r'([.!?])\s+', r'\1 ', text)
    # Remove trailing dots that might be read
    text = re.sub(r'\.\s*$', '', text)
    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def split_into_sentences(text: str, language: str) -> List[str]:
    """Split text into sentences using NLTK's sentence tokenizer."""
    try:
        # Use language-specific tokenizer if available
        sentences = nltk.sent_tokenize(text, language=language if language in ['english', 'german', 'french', 'italian', 'spanish', 'portuguese'] else 'english')
    except:
        # Fallback to basic splitting if language not supported
        sentences = nltk.sent_tokenize(text)

    # Filter out empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def merge_audio_chunks(audio_chunks: List[np.ndarray], sample_rate: int = 24000, pause_duration: float = 0.2) -> np.ndarray:
    """
    Merge multiple audio chunks into a single array with small pauses between sentences.

    Args:
        audio_chunks: List of numpy arrays containing audio data
        sample_rate: Sample rate of the audio (default 24000 Hz for XTTS v2)
        pause_duration: Duration of pause between sentences in seconds (default 0.2s)

    Returns:
        Merged numpy array
    """
    if not audio_chunks:
        return np.array([])

    if len(audio_chunks) == 1:
        return audio_chunks[0]

    # Create silence array for pauses
    pause_samples = int(sample_rate * pause_duration)
    silence = np.zeros(pause_samples, dtype=audio_chunks[0].dtype)

    # Merge chunks with pauses
    merged = []
    for i, chunk in enumerate(audio_chunks):
        merged.append(chunk)
        # Add pause between sentences (but not after the last one)
        if i < len(audio_chunks) - 1:
            merged.append(silence)

    return np.concatenate(merged)

class TTSRequest(BaseModel):
    text: str
    language: str = DEFAULT_LANGUAGE
    speaker: str = DEFAULT_SPEAKER
    voice_profile: Optional[str] = None  # "default", "user2", etc. for voice cloning

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    # Check if model is ready
    if loading_state["status"] != "ready" or tts is None:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {loading_state['message']} ({loading_state['progress']}%)"
        )

    try:
        # Check if using voice cloning
        speaker_wavs = None
        if request.voice_profile:
            profile_path = f"/app/voice-profiles/{request.voice_profile}"
            if os.path.exists(profile_path):
                speaker_wavs = sorted(glob.glob(f"{profile_path}/*.wav"))
                if speaker_wavs:
                    print(f"Using voice cloning with profile: {request.voice_profile}")
                    print(f"Found {len(speaker_wavs)} voice samples")
                else:
                    print(f"Warning: No voice samples found in profile '{request.voice_profile}', using default speaker")
            else:
                print(f"Warning: Voice profile '{request.voice_profile}' not found, using default speaker")

        # Get speaker name - use language-specific mapping if available (only if not using voice cloning)
        speaker_name = None
        if not speaker_wavs:
            if request.language in LANGUAGE_SPEAKER_MAP and request.speaker in LANGUAGE_SPEAKER_MAP[request.language]:
                speaker_name = LANGUAGE_SPEAKER_MAP[request.language][request.speaker]
            else:
                speaker_name = SPEAKER_MAP.get(request.speaker, SPEAKER_MAP["male"])

        print(f"Generating speech for: {request.text[:50]}...")
        if speaker_wavs:
            print(f"Language: {request.language}, Voice Profile: {request.voice_profile}")
        else:
            print(f"Language: {request.language}, Speaker: {request.speaker} -> {speaker_name}")
        print(f"Text length: {len(request.text)} characters")

        # Check if text is long enough to warrant sentence-based chunking
        if len(request.text) > CHUNK_THRESHOLD:
            print(f"Using sentence-based chunking (text length: {len(request.text)} > {CHUNK_THRESHOLD})")

            # Split text into sentences
            sentences = split_into_sentences(request.text, request.language)
            print(f"Split into {len(sentences)} sentences")

            # Generate audio for each sentence
            audio_chunks = []
            for i, sentence in enumerate(sentences, 1):
                progress_pct = int((i / len(sentences)) * 100)
                print(f"  [{progress_pct:3d}%] Processing sentence {i}/{len(sentences)}: {sentence[:50]}...")
                # Clean text to prevent punctuation vocalization
                cleaned_sentence = clean_text_for_tts(sentence)

                # Use voice cloning or default speaker
                if speaker_wavs:
                    wav = tts.tts(
                        text=cleaned_sentence,
                        speaker_wav=speaker_wavs,
                        language=request.language,
                        split_sentences=False  # Disable internal sentence splitting
                    )
                else:
                    wav = tts.tts(
                        text=cleaned_sentence,
                        speaker=speaker_name,
                        language=request.language,
                        split_sentences=False  # Disable internal sentence splitting
                    )
                audio_chunks.append(np.array(wav))

            # Merge all audio chunks
            print("Merging audio chunks...")
            merged_audio = merge_audio_chunks(audio_chunks, sample_rate=24000)

            # Convert to WAV bytes
            buffer = io.BytesIO()
            sf.write(buffer, merged_audio, 24000, format='WAV')
            buffer.seek(0)

            print(f"Generated {len(merged_audio)/24000:.2f} seconds of audio")
            return Response(
                content=buffer.read(), 
                media_type="audio/wav",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )

        else:
            print("Using single-pass generation (text is short)")

            # Clean text to prevent punctuation vocalization
            cleaned_text = clean_text_for_tts(request.text)

            # Generate speech with XTTS v2 in one go (with voice cloning or default speaker)
            if speaker_wavs:
                wav = tts.tts(
                    text=cleaned_text,
                    speaker_wav=speaker_wavs,
                    language=request.language,
                    split_sentences=False  # Disable internal sentence splitting
                )
            else:
                wav = tts.tts(
                    text=cleaned_text,
                    speaker=speaker_name,
                    language=request.language,
                    split_sentences=False  # Disable internal sentence splitting
                )

            # Convert to WAV bytes
            buffer = io.BytesIO()
            sf.write(buffer, wav, 24000, format='WAV')  # XTTS v2 uses 24kHz
            buffer.seek(0)

            return Response(
                content=buffer.read(), 
                media_type="audio/wav",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    # Determine supported languages based on model
    is_xtts = "xtts" in TTS_MODEL.lower()
    supported_langs = ["it", "en", "es", "fr", "de", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko"] if is_xtts else ["en"]

    response = {
        "status": "running",
        "model": model_name,
        "model_path": TTS_MODEL,
        "gpu": torch.cuda.is_available(),
        "supported_languages": supported_langs,
        "speakers": list(SPEAKER_MAP.keys()),
        "speaker_map": SPEAKER_MAP
    }

    if TTS_VOCODER:
        response["vocoder"] = TTS_VOCODER

    return response

@app.get("/health")
async def health():
    """Health check endpoint that verifies TTS model is loaded and ready."""
    try:
        # Return loading state information
        if loading_state["status"] == "ready":
            return {
                "status": "healthy",
                "model": model_name,
                "model_path": TTS_MODEL,
                "model_loaded": True,
                "gpu_available": torch.cuda.is_available(),
                "loading_state": loading_state["status"],
                "message": loading_state["message"],
                "progress": loading_state["progress"]
            }
        elif loading_state["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "model_loaded": False,
                    "loading_state": loading_state["status"],
                    "message": loading_state["message"],
                    "progress": loading_state["progress"]
                }
            )
        else:
            # Still loading (initializing, downloading, loading)
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "loading",
                    "model_loaded": False,
                    "loading_state": loading_state["status"],
                    "message": loading_state["message"],
                    "progress": loading_state["progress"]
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
