# Voice Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add voice interaction to ChatModal — users speak instead of typing, AI responses are read aloud via SiliconFlow STT/TTS.

**Architecture:** REST-based sandwich approach. Backend proxies to SiliconFlow OpenAI-compatible API for STT (TeleSpeechASR) and TTS (CosyVoice2). Frontend uses browser MediaRecorder for capture, Audio API for playback. Existing chat streaming flow unchanged.

**Tech Stack:** FastAPI, `openai` Python package (OpenAI-compatible), React, browser MediaRecorder + Audio APIs

---

## Task 1: Backend — Voice Service

**Files:**
- Create: `platform/backend/app/services/voice_service.py`

- [ ] **Step 1: Create voice_service.py with SiliconFlow API wrapper**

```python
"""Voice Service — SiliconFlow STT/TTS via OpenAI-compatible API."""

import os
import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
STT_MODEL = "TeleAI/TeleSpeechASR"
TTS_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
MAX_TTS_CHARS = 2000

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
```

- [ ] **Step 2: Commit**

```bash
git add platform/backend/app/services/voice_service.py
git commit -m "feat(voice): add voice_service with SiliconFlow STT/TTS wrapper"
```

---

## Task 2: Backend — Voice API Endpoints

**Files:**
- Create: `platform/backend/app/api/v1/endpoints/voice.py`
- Modify: `platform/backend/app/api/v1/api.py`

- [ ] **Step 1: Create voice.py endpoints**

```python
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
```

- [ ] **Step 2: Register voice router in api.py**

In `platform/backend/app/api/v1/api.py`, add the import and router registration:

Add `voice` to the existing imports:
```python
from app.api.v1.endpoints import (
    ...,
    voice,
)
```

Add router registration after the last `include_router`:
```python
api_router.include_router(
    voice.router,
    prefix="/voice",
    tags=["voice"],
)
```

- [ ] **Step 3: Add `openai` to requirements.txt**

In `platform/backend/requirements.txt`, add:
```
openai>=1.0.0
```

- [ ] **Step 4: Commit**

```bash
git add platform/backend/app/api/v1/endpoints/voice.py platform/backend/app/api/v1/api.py platform/backend/requirements.txt
git commit -m "feat(voice): add STT/TTS REST endpoints and register voice router"
```

---

## Task 3: Frontend — Voice Service API Layer

**Files:**
- Create: `platform/frontend/src/services/voiceService.js`

- [ ] **Step 1: Create voiceService.js**

```javascript
/**
 * Voice Service — API calls for STT transcription and TTS synthesis.
 */

const API_BASE = `${window.location.origin}/api/v1/voice`;

let voiceConfig = null;

export async function getVoiceConfig() {
  if (voiceConfig) return voiceConfig;
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error('Failed to fetch voice config');
  voiceConfig = await res.json();
  return voiceConfig;
}

export async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');

  const res = await fetch(`${API_BASE}/transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Speech recognition failed');
  }

  return await res.json();
}

export async function synthesizeSpeech(text, voice = 'alex') {
  const params = new URLSearchParams({ text, voice });
  const res = await fetch(`${API_BASE}/synthesize?${params}`, {
    method: 'POST',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Voice synthesis failed');
  }

  return res.body;
}
```

- [ ] **Step 2: Commit**

```bash
git add platform/frontend/src/services/voiceService.js
git commit -m "feat(voice): add frontend voice service API layer"
```

---

## Task 4: Frontend — Voice Recorder Hook

**Files:**
- Create: `platform/frontend/src/hooks/useVoiceRecorder.js`

- [ ] **Step 1: Create useVoiceRecorder.js**

```javascript
/**
 * useVoiceRecorder — browser microphone recording hook.
 *
 * Handles MediaRecorder lifecycle, permission management,
 * and minimum recording duration.
 */
import { useState, useRef, useCallback } from 'react';

const MIN_DURATION_MS = 500;
const MIME_TYPE = 'audio/webm;codecs=opus';

export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const startTimeRef = useRef(0);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: MIME_TYPE });
      chunksRef.current = [];
      startTimeRef.current = Date.now();

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Microphone permission denied');
      } else {
        setError('Failed to start recording');
      }
    }
  }, []);

  const stop = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state !== 'recording') {
        setIsRecording(false);
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const duration = Date.now() - startTimeRef.current;
        setIsRecording(false);

        // Stop all tracks to release microphone
        recorder.stream.getTracks().forEach((t) => t.stop());

        if (duration < MIN_DURATION_MS) {
          setError('Recording too short');
          resolve(null);
          return;
        }

        const blob = new Blob(chunksRef.current, { type: MIME_TYPE });
        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  return { isRecording, error, start, stop };
}
```

- [ ] **Step 2: Commit**

```bash
git add platform/frontend/src/hooks/useVoiceRecorder.js
git commit -m "feat(voice): add useVoiceRecorder hook"
```

---

## Task 5: Frontend — Voice Playback Hook

**Files:**
- Create: `platform/frontend/src/hooks/useVoicePlayback.js`

- [ ] **Step 1: Create useVoicePlayback.js**

```javascript
/**
 * useVoicePlayback — audio playback management for TTS.
 *
 * Handles streaming audio from TTS endpoint, auto-play settings,
 * and single-playback enforcement.
 */
import { useState, useRef, useCallback } from 'react';

export function useVoicePlayback() {
  const [playingMessageId, setPlayingMessageId] = useState(null);
  const audioRef = useRef(null);
  const audioUrlRef = useRef(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setPlayingMessageId(null);
  }, []);

  const play = useCallback(async (text, voice, messageId) => {
    stop();

    try {
      const params = new URLSearchParams({ text, voice });
      const res = await fetch(
        `${window.location.origin}/api/v1/voice/synthesize?${params}`,
        { method: 'POST' }
      );

      if (!res.ok) throw new Error('TTS failed');

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      setPlayingMessageId(messageId);

      audio.onended = () => stop();
      audio.onerror = () => stop();

      await audio.play();
    } catch {
      stop();
    }
  }, [stop]);

  const isPlaying = useCallback(
    (messageId) => playingMessageId === messageId,
    [playingMessageId]
  );

  return { play, stop, isPlaying };
}
```

- [ ] **Step 2: Commit**

```bash
git add platform/frontend/src/hooks/useVoicePlayback.js
git commit -m "feat(voice): add useVoicePlayback hook"
```

---

## Task 6: Frontend — VoiceButton Component + Mic Icon

**Files:**
- Create: `platform/frontend/src/components/VoiceButton.jsx`
- Modify: `platform/frontend/src/components/Icons.jsx`

- [ ] **Step 1: Add MicIcon and SpeakerIcon to Icons.jsx**

Append to end of `platform/frontend/src/components/Icons.jsx`:

```jsx
export const MicIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M10 2a3 3 0 00-3 3v4a3 3 0 006 0V5a3 3 0 00-3-3zM5 9a1 1 0 10-2 0 7 7 0 006 6.93V18H7a1 1 0 100 2h6a1 1 0 100-2h-2v-2.07A7 7 0 0017 9a1 1 0 10-2 0 5 5 0 01-10 0z"/>
  </svg>
);

export const SpeakerIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 5h2l4-3v12l-4-3H3a1 1 0 01-1-1V6a1 1 0 011-1zm10.15 1.15a1.5 1.5 0 010 2.12M14.57 4.57a3.5 3.5 0 010 6.86"/>
  </svg>
);
```

- [ ] **Step 2: Create VoiceButton.jsx**

```jsx
import React from 'react';
import { MicIcon } from './Icons';
import './ChatModal.css';

export function VoiceButton({ isRecording, onStart, onStop, disabled }) {
  return (
    <button
      className={`chat-voice-btn ${isRecording ? 'recording' : ''}`}
      onClick={isRecording ? onStop : onStart}
      disabled={disabled}
      title={isRecording ? 'Stop recording' : 'Start voice input'}
    >
      <MicIcon size={16} />
    </button>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add platform/frontend/src/components/VoiceButton.jsx platform/frontend/src/components/Icons.jsx
git commit -m "feat(voice): add VoiceButton component and MicIcon/SpeakerIcon"
```

---

## Task 7: Frontend — AudioPlayer Component

**Files:**
- Create: `platform/frontend/src/components/AudioPlayer.jsx`

- [ ] **Step 1: Create AudioPlayer.jsx**

```jsx
import React from 'react';
import { SpeakerIcon } from './Icons';
import './ChatModal.css';

export function AudioPlayer({ messageId, text, voice, isPlaying, onPlay }) {
  if (!text) return null;

  return (
    <button
      className={`chat-audio-player ${isPlaying ? 'playing' : ''}`}
      onClick={() => onPlay(text, voice, messageId)}
      title={isPlaying ? 'Playing...' : 'Play audio'}
    >
      <SpeakerIcon size={14} />
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add platform/frontend/src/components/AudioPlayer.jsx
git commit -m "feat(voice): add AudioPlayer component"
```

---

## Task 8: Frontend — Integrate Voice into ChatModal

**Files:**
- Modify: `platform/frontend/src/components/ChatModal.jsx`
- Modify: `platform/frontend/src/components/ChatModal.css`

- [ ] **Step 1: Add voice CSS styles to ChatModal.css**

Append to end of `platform/frontend/src/components/ChatModal.css`:

```css
/* Voice Button */
.chat-voice-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: none;
  border: 1px solid #e0e0e0;
  color: #525252;
  cursor: pointer;
  border-radius: 0;
  flex-shrink: 0;
  padding: 0;
}

.chat-voice-btn:hover:not(:disabled) {
  background-color: #e0e0e0;
}

.chat-voice-btn.recording {
  border-color: #da1e28;
  color: #da1e28;
  background-color: #fff1f1;
  animation: voice-pulse 1.2s ease-in-out infinite;
}

.chat-voice-btn:disabled {
  color: #a8a8a8;
  cursor: not-allowed;
}

@keyframes voice-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Audio Player */
.chat-audio-player {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: none;
  border: none;
  color: #525252;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
  vertical-align: middle;
}

.chat-audio-player:hover {
  color: #0f62fe;
}

.chat-audio-player.playing {
  color: #0f62fe;
  animation: voice-pulse 1.2s ease-in-out infinite;
}

/* Voice Settings Toggle */
.chat-voice-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 48px;
  padding: 0 12px;
  background: none;
  border: 1px solid #e0e0e0;
  color: #525252;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 12px;
  cursor: pointer;
  border-radius: 0;
  white-space: nowrap;
  flex-shrink: 0;
}

.chat-voice-toggle:hover {
  background-color: #e0e0e0;
}

.chat-voice-toggle.active {
  border-color: #0f62fe;
  color: #0f62fe;
  background-color: #edf5ff;
}
```

- [ ] **Step 2: Modify ChatModal.jsx — add imports**

Add after the existing imports at top of file:

```jsx
import { VoiceButton } from './VoiceButton';
import { AudioPlayer } from './AudioPlayer';
import { SpeakerIcon } from './Icons';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { useVoicePlayback } from '../hooks/useVoicePlayback';
import { getVoiceConfig, transcribeAudio } from '../services/voiceService';
```

- [ ] **Step 3: Modify ChatModal.jsx — add voice state and hooks**

Inside the `ChatModal` function, after the existing state declarations (around line 105), add:

```jsx
  // Voice state
  const { isRecording, error: voiceError, start: startRecording, stop: stopRecording } = useVoiceRecorder();
  const { play: playAudio, isPlaying: isAudioPlaying } = useVoicePlayback();
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [autoPlay, setAutoPlay] = useState(() => localStorage.getItem('voice-auto-play') !== 'false');
  const [selectedVoice, setSelectedVoice] = useState('alex');
  const [voiceLoading, setVoiceLoading] = useState(false);
  const lastAssistantMsgRef = useRef(null);

  // Check voice config on mount
  useEffect(() => {
    getVoiceConfig().then((config) => {
      setVoiceEnabled(config.voice_enabled);
      if (config.default_voice) setSelectedVoice(config.default_voice);
    }).catch(() => setVoiceEnabled(false));
  }, []);

  useEffect(() => { localStorage.setItem('voice-auto-play', autoPlay.toString()); }, [autoPlay]);
```

- [ ] **Step 4: Modify ChatModal.jsx — add voice recording handler**

After `handleClearConversation` (around line 172), add:

```jsx
  const handleVoiceRecord = async () => {
    if (isRecording) {
      const blob = await stopRecording();
      if (!blob) return;
      setVoiceLoading(true);
      try {
        const { text } = await transcribeAudio(blob);
        if (text?.trim()) {
          setInputValue('');
          sendMessage(text.trim(), { enableSearch, enableDeepThinking: deepThinking });
        }
      } catch (err) {
        console.error('Voice transcription failed:', err);
      } finally {
        setVoiceLoading(false);
      }
    } else {
      await startRecording();
    }
  };
```

- [ ] **Step 5: Modify ChatModal.jsx — add auto-play effect**

After the voice recording handler, add:

```jsx
  // Auto-play TTS when AI response completes
  useEffect(() => {
    if (!autoPlay || !voiceEnabled || isStreaming) return;
    const lastMsg = messages.filter((m) => m.role === 'assistant').pop();
    if (lastMsg && lastMsg.content && lastMsg !== lastAssistantMsgRef.current) {
      lastAssistantMsgRef.current = lastMsg;
      playAudio(lastMsg.content, selectedVoice, `msg-${messages.indexOf(lastMsg)}`);
    }
  }, [messages, isStreaming, autoPlay, voiceEnabled, selectedVoice, playAudio]);
```

- [ ] **Step 6: Modify ChatModal.jsx — add VoiceButton to input area**

In the input area JSX, after the deep thinking toggle button block, add:

```jsx
            {voiceEnabled && (
              <VoiceButton
                isRecording={isRecording}
                onStart={startRecording}
                onStop={handleVoiceRecord}
                disabled={isStreaming || voiceLoading}
              />
            )}
```

- [ ] **Step 7: Modify ChatModal.jsx — add AudioPlayer to assistant messages**

Inside each assistant message `chat-message assistant-message` div, after the `message-content` div, add:

```jsx
              {voiceEnabled && msg.role === 'assistant' && msg.content && (
                <AudioPlayer
                  messageId={`msg-${idx}`}
                  text={msg.content}
                  voice={selectedVoice}
                  isPlaying={isAudioPlaying(`msg-${idx}`)}
                  onPlay={playAudio}
                />
              )}
```

- [ ] **Step 8: Modify ChatModal.jsx — add auto-play toggle**

After the deep thinking toggle in the input area, add:

```jsx
            {voiceEnabled && (
              <button
                className={`chat-voice-toggle ${autoPlay ? 'active' : ''}`}
                onClick={() => setAutoPlay(prev => !prev)}
                title={autoPlay ? 'Disable auto-play' : 'Enable auto-play'}
              >
                <SpeakerIcon size={16} />
                <span className="chat-voice-toggle-label">Auto</span>
              </button>
            )}
```

- [ ] **Step 9: Commit**

```bash
git add platform/frontend/src/components/ChatModal.jsx platform/frontend/src/components/ChatModal.css
git commit -m "feat(voice): integrate voice recording and playback into ChatModal"
```

---

## Task 9: Configuration — Environment Variables

**Files:**
- Modify: `platform/.env`

- [ ] **Step 1: Add voice environment variables to .env**

Append to `platform/.env`:

```
# Voice (SiliconFlow)
SILICONFLOW_API_KEY=
VOICE_DEFAULT_VOICE=alex
VOICE_AUTO_PLAY=true
VOICE_RESPONSE_FORMAT=mp3
```

- [ ] **Step 2: Commit**

```bash
git add platform/.env
git commit -m "feat(voice): add voice environment variables"
```

---

## Task 10: Test — Backend Voice Endpoints

**Files:**
- Create: `platform/backend/tests/test_voice.py`

- [ ] **Step 1: Create test_voice.py**

```python
"""Tests for voice API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestVoiceConfig:
    def test_config_returns_voices(self, client):
        with patch("app.services.voice_service.is_voice_enabled", return_value=True):
            res = client.get("/api/v1/voice/config")
        assert res.status_code == 200
        data = res.json()
        assert data["voice_enabled"] is True
        assert len(data["voices"]) == 8
        assert data["default_voice"] == "alex"

    def test_config_disabled_without_key(self, client):
        with patch("app.services.voice_service.is_voice_enabled", return_value=False):
            res = client.get("/api/v1/voice/config")
        data = res.json()
        assert data["voice_enabled"] is False


class TestVoiceTranscribe:
    def test_transcribe_empty_file_returns_400(self, client):
        with patch("app.services.voice_service.is_voice_enabled", return_value=True):
            res = client.post("/api/v1/voice/transcribe", files={"file": ("a.webm", b"", "audio/webm")})
        assert res.status_code == 400

    def test_transcribe_returns_text(self, client):
        with patch("app.services.voice_service.is_voice_enabled", return_value=True), \
             patch("app.services.voice_service.transcribe", new_callable=AsyncMock, return_value="hello"):
            res = client.post("/api/v1/voice/transcribe", files={"file": ("a.webm", b"fake-audio", "audio/webm")})
        assert res.status_code == 200
        assert res.json()["text"] == "hello"

    def test_transcribe_no_speech_returns_422(self, client):
        with patch("app.services.voice_service.is_voice_enabled", return_value=True), \
             patch("app.services.voice_service.transcribe", new_callable=AsyncMock, return_value=""):
            res = client.post("/api/v1/voice/transcribe", files={"file": ("a.webm", b"fake", "audio/webm")})
        assert res.status_code == 422


class TestVoiceSynthesize:
    def test_synthesize_empty_text_returns_400(self, client):
        with patch("app.services.voice_service.is_voice_enabled", return_value=True):
            res = client.post("/api/v1/voice/synthesize?text=&voice=alex")
        assert res.status_code == 400

    def test_synthesize_streams_audio(self, client):
        async def fake_gen(*a, **kw):
            yield b"audio-chunk-1"
            yield b"audio-chunk-2"

        with patch("app.services.voice_service.is_voice_enabled", return_value=True), \
             patch("app.services.voice_service.synthesize", return_value=fake_gen()):
            res = client.post("/api/v1/voice/synthesize?text=hello&voice=alex")
        assert res.status_code == 200
        assert res.content == b"audio-chunk-1audio-chunk-2"
```

- [ ] **Step 2: Run tests**

```bash
cd platform/backend && python -m pytest tests/test_voice.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add platform/backend/tests/test_voice.py
git commit -m "test(voice): add backend voice endpoint tests"
```

---

## Task 11: Manual Integration Test

- [ ] **Step 1: Start dev environment**

```bash
cd platform && ./start-dev.sh
```

- [ ] **Step 2: Verify backend endpoints**

```bash
curl http://localhost:8011/api/v1/voice/config
curl -X POST http://localhost:8011/api/v1/voice/transcribe -F "file=@test-audio.webm"
curl -X POST "http://localhost:8011/api/v1/voice/synthesize?text=hello&voice=alex" --output test.mp3
```

- [ ] **Step 3: Verify frontend**

Open http://localhost:8085 in browser:
- Open chat modal
- Verify mic button appears when SILICONFLOW_API_KEY is set
- Click mic → grant permission → speak → click stop
- Verify text appears in chat and sends
- Verify AI response has play button
- Verify auto-play toggle works
