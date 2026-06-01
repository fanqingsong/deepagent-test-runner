"""Voice API Endpoints — STT transcription and TTS synthesis."""

import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.services.voice_service import (
    transcribe,
    synthesize,
    is_voice_enabled,
    PRESET_VOICES,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config")
async def get_voice_config():
    """Return voice feature config. Frontend uses this to show/hide voice UI."""
    return {
        "voice_enabled": is_voice_enabled(),
        "voices": PRESET_VOICES,
        "default_voice": "alex",
    }


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (webm/wav/mp3)"),
):
    """Transcribe audio to text using SiliconFlow TeleSpeechASR."""
    if not is_voice_enabled():
        raise HTTPException(status_code=503, detail="Voice service not configured")

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        text = await transcribe(audio_bytes, filename=file.filename or "audio.webm")
    except Exception as e:
        logger.error(f"STT failed: {e}")
        raise HTTPException(status_code=502, detail="Speech recognition failed")

    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="No speech detected")

    return {"text": text}


@router.post("/synthesize")
async def synthesize_speech(
    text: str,
    voice: str = "alex",
):
    """Synthesize text to audio using SiliconFlow CosyVoice2. Returns streaming mp3."""
    if not is_voice_enabled():
        raise HTTPException(status_code=503, detail="Voice service not configured")

    if voice not in PRESET_VOICES:
        voice = "alex"

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        audio_stream = synthesize(text, voice=voice)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=502, detail="Voice synthesis failed")

    return StreamingResponse(
        audio_stream,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )
