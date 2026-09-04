import io
import os
import glob
import logging
from typing import Optional, List
from pathlib import Path

import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("f5_tts_server")

from contextlib import asynccontextmanager

# Paths & Settings
VOICES_DIR = Path(os.getenv("VOICES_DIR", "/app/voices"))
VOICES_DIR.mkdir(parents=True, exist_ok=True)
PORT = int(os.getenv("PORT", "5000"))

# Global model holder
tts_model = None

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_model
    device = get_device()
    logger.info(f"Initializing F5-TTS on device: {device}...")
    try:
        from f5_tts.api import F5TTS
        tts_model = F5TTS(device=device)
        logger.info("F5-TTS model successfully loaded into memory!")
        if device == "cuda":
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            logger.info(f"VRAM Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB")
    except Exception as e:
        logger.error(f"Failed to load F5-TTS model: {e}", exc_info=True)
        raise e
    yield

# Initialize FastAPI
app = FastAPI(
    title="F5-TTS Inference Server",
    description="High-performance, OpenAI-compatible Text-To-Speech API powered by F5-TTS",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def resolve_voice(voice_name: Optional[str] = None):
    """
    Finds reference audio file and matching transcription (.txt) from the voices directory.
    """
    valid_exts = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]
    
    # 1. If voice_name given, look for exact or stem match
    if voice_name:
        candidate_path = VOICES_DIR / voice_name
        if candidate_path.is_file():
            ref_file = candidate_path
        else:
            # Match by stem (e.g. "jarvis" -> "jarvis.wav")
            matches = [f for f in VOICES_DIR.iterdir() if f.stem.lower() == voice_name.lower() and f.suffix.lower() in valid_exts]
            if matches:
                ref_file = matches[0]
            else:
                ref_file = None
    else:
        ref_file = None

    # 2. Fallback to first available audio file in voices dir
    if not ref_file or not ref_file.exists():
        all_audio = [f for f in VOICES_DIR.iterdir() if f.suffix.lower() in valid_exts]
        if all_audio:
            ref_file = all_audio[0]
            logger.info(f"No specific voice matched; defaulting to: {ref_file.name}")
        else:
            ref_file = None

    ref_text = ""
    if ref_file:
        txt_sidecar = ref_file.with_suffix(".txt")
        if txt_sidecar.exists():
            ref_text = txt_sidecar.read_text(encoding="utf-8").strip()

    return ref_file, ref_text

# Schemas
class OpenAISpeechRequest(BaseModel):
    model: str = "f5-tts"
    input: str
    voice: Optional[str] = "jarvis"
    response_format: Optional[str] = "wav"
    speed: Optional[float] = 1.0

class F5TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "jarvis"
    ref_audio_path: Optional[str] = None
    ref_text: Optional[str] = None
    speed: Optional[float] = 1.0
    nfe_step: Optional[int] = 32
    cfg_strength: Optional[float] = 2.0
    remove_silence: Optional[bool] = False

@app.get("/health")
async def health_check():
    device = get_device()
    info = {
        "status": "healthy" if tts_model is not None else "loading",
        "device": device,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
    }
    if torch.cuda.is_available():
        info["vram_allocated_gb"] = round(torch.cuda.memory_allocated() / (1024 ** 3), 2)
        info["vram_reserved_gb"] = round(torch.cuda.memory_reserved() / (1024 ** 3), 2)
    return info

@app.get("/v1/voices")
async def list_voices():
    valid_exts = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]
    voices = []
    for f in VOICES_DIR.iterdir():
        if f.suffix.lower() in valid_exts:
            txt_sidecar = f.with_suffix(".txt")
            has_txt = txt_sidecar.exists()
            transcript = txt_sidecar.read_text(encoding="utf-8").strip() if has_txt else ""
            voices.append({
                "name": f.stem,
                "filename": f.name,
                "has_transcript": has_txt,
                "transcript": transcript
            })
    return {"voices": voices}

@app.post("/v1/audio/speech")
async def openai_speech_endpoint(req: OpenAISpeechRequest):
    """
    OpenAI-compatible text-to-speech endpoint.
    Compatible with OpenAI Python SDK, LangChain, Home Assistant, etc.
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="Model is still initializing")

    ref_file, ref_text = resolve_voice(req.voice)
    if not ref_file:
        raise HTTPException(
            status_code=400,
            detail=f"No reference audio found in {VOICES_DIR}. Please place a reference .wav/.mp3 file (e.g. jarvis.wav) in the voices folder."
        )

    try:
        wav, sample_rate, _ = tts_model.infer(
            ref_file=str(ref_file),
            ref_text=ref_text,
            gen_text=req.input,
            speed=req.speed or 1.0,
        )

        buf = io.BytesIO()
        sf.write(buf, wav, sample_rate, format="WAV")
        buf.seek(0)

        return Response(content=buf.read(), media_type="audio/wav")
    except Exception as e:
        logger.error(f"TTS inference failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/tts")
async def custom_tts_endpoint(req: F5TTSRequest):
    """
    Native F5-TTS endpoint supporting advanced parameters (nfe_step, cfg_strength, silence removal).
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="Model is still initializing")

    if req.ref_audio_path and os.path.isfile(req.ref_audio_path):
        ref_file = Path(req.ref_audio_path)
        ref_text = req.ref_text or ""
    else:
        ref_file, auto_text = resolve_voice(req.voice)
        ref_text = req.ref_text if req.ref_text is not None else auto_text

    if not ref_file:
        raise HTTPException(
            status_code=400,
            detail=f"No reference voice available. Please put a .wav and .txt in {VOICES_DIR}"
        )

    try:
        wav, sample_rate, _ = tts_model.infer(
            ref_file=str(ref_file),
            ref_text=ref_text,
            gen_text=req.text,
            speed=req.speed or 1.0,
            nfe_step=req.nfe_step or 32,
            cfg_strength=req.cfg_strength or 2.0,
            remove_silence=req.remove_silence or False
        )

        buf = io.BytesIO()
        sf.write(buf, wav, sample_rate, format="WAV")
        buf.seek(0)

        return Response(content=buf.read(), media_type="audio/wav")
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
