"""Tests for voice API endpoints."""
import pytest
import pytest_asyncio
import httpx
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestVoiceConfig:
    @pytest.mark.asyncio
    async def test_config_returns_voices(self, client):
        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=True):
            res = await client.get("/api/v1/voice/config")
        assert res.status_code == 200
        data = res.json()
        assert data["voice_enabled"] is True
        assert len(data["voices"]) == 8
        assert data["default_voice"] == "alex"

    @pytest.mark.asyncio
    async def test_config_disabled_without_key(self, client):
        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=False):
            res = await client.get("/api/v1/voice/config")
        data = res.json()
        assert data["voice_enabled"] is False


class TestVoiceTranscribe:
    @pytest.mark.asyncio
    async def test_transcribe_empty_file_returns_400(self, client):
        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=True):
            res = await client.post(
                "/api/v1/voice/transcribe",
                files={"file": ("a.webm", b"", "audio/webm")},
            )
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, client):
        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=True), \
             patch("app.api.v1.endpoints.voice.transcribe", new_callable=AsyncMock, return_value="hello"):
            res = await client.post(
                "/api/v1/voice/transcribe",
                files={"file": ("a.webm", b"fake-audio", "audio/webm")},
            )
        assert res.status_code == 200
        assert res.json()["text"] == "hello"

    @pytest.mark.asyncio
    async def test_transcribe_no_speech_returns_422(self, client):
        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=True), \
             patch("app.api.v1.endpoints.voice.transcribe", new_callable=AsyncMock, return_value=""):
            res = await client.post(
                "/api/v1/voice/transcribe",
                files={"file": ("a.webm", b"fake", "audio/webm")},
            )
        assert res.status_code == 422


class TestVoiceSynthesize:
    @pytest.mark.asyncio
    async def test_synthesize_empty_text_returns_400(self, client):
        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=True):
            res = await client.post("/api/v1/voice/synthesize?text=&voice=alex")
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_synthesize_streams_audio(self, client):
        async def fake_gen(*a, **kw):
            yield b"audio-chunk-1"
            yield b"audio-chunk-2"

        with patch("app.api.v1.endpoints.voice.is_voice_enabled", return_value=True), \
             patch("app.api.v1.endpoints.voice.synthesize", return_value=fake_gen()):
            res = await client.post("/api/v1/voice/synthesize?text=hello&voice=alex")
        assert res.status_code == 200
        assert res.content == b"audio-chunk-1audio-chunk-2"
