"""Voice Service — SiliconFlow STT/TTS via OpenAI-compatible API."""

import os
import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
STT_MODEL = os.getenv("STT_MODEL", "TeleAI/TeleSpeechASR")
TTS_MODEL = os.getenv("TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B")
MAX_TTS_CHARS = int(os.getenv("MAX_TTS_CHARS", "2000"))

PRESET_VOICES = [
    "alex", "anna", "bella", "benjamin",
    "charles", "claire", "david", "diana",
]


def get_voice_client() -> AsyncOpenAI | None:
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key, base_url=SILICONFLOW_BASE_URL)


def is_voice_enabled() -> bool:
    return bool(os.getenv("SILICONFLOW_API_KEY"))


async def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Send audio to SiliconFlow STT, return transcript text."""
    client = get_voice_client()
    if not client:
        raise ValueError("SILICONFLOW_API_KEY not configured")

    response = await client.audio.transcriptions.create(
        model=STT_MODEL,
        file=(filename, audio_bytes),
    )
    return response.text


async def synthesize(
    text: str,
    voice: str = "alex",
    response_format: str = "mp3",
) -> AsyncIterator[bytes]:
    """Stream TTS audio chunks from SiliconFlow CosyVoice2."""
    client = get_voice_client()
    if not client:
        raise ValueError("SILICONFLOW_API_KEY not configured")

    text = text[:MAX_TTS_CHARS]
    voice_id = f"{TTS_MODEL}:{voice}"

    response = await client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice_id,
        input=text,
        response_format=response_format,
    )

    # Stream chunks
    async for chunk in response.response.aiter_bytes(chunk_size=4096):
        yield chunk
