# Voice Agent Design

Date: 2026-06-01
Status: Approved

## Overview

Add voice interaction to the existing ChatModal: users speak instead of typing, AI responses are read aloud. Uses the sandwich architecture (STT > Agent > TTS) with press-to-talk recording.

## Architecture

```
User presses mic → Records audio (WebM/Opus) → POST /api/v1/voice/transcribe
→ SiliconFlow TeleSpeechASR → Returns text → Sent to existing chat stream
→ AI replies with text → POST /api/v1/voice/synthesize
→ SiliconFlow CosyVoice2 → Streaming audio (mp3) → Browser plays audio
```

All services use SiliconFlow via OpenAI-compatible API (`openai` Python package, `base_url=https://api.siliconflow.cn/v1`).

## Backend

### New Files

- `platform/backend/app/api/v1/endpoints/voice.py` — REST endpoints
- `platform/backend/app/services/voice_service.py` — SiliconFlow API wrapper

### Endpoints

**POST /api/v1/voice/transcribe**
- Input: multipart/form-data with `file` (audio: wav/mp3/webm) and optional `language`
- Process: Forward to `POST https://api.siliconflow.cn/v1/audio/transcriptions` with `model=TeleAI/TeleSpeechASR`
- Response: `{"text": "transcribed text"}`

**POST /api/v1/voice/synthesize**
- Input: JSON `{"text": "...", "voice": "alex"}`
- Process: Forward to `POST https://api.siliconflow.cn/v1/audio/speech` with `model=FunAudioLLM/CosyVoice2-0.5B`, `stream=true`, `response_format=mp3`
- Response: StreamingResponse with audio binary (mp3)

**GET /api/v1/voice/config**
- Response: `{"voice_enabled": true, "voices": ["alex","anna","bella","benjamin","charles","claire","david","diana"], "default_voice": "alex"}`
- Returns `voice_enabled: false` if `SILICONFLOW_API_KEY` is not set.

### API Configuration

Uses `openai` Python package with:
- `api_key = SILICONFLOW_API_KEY`
- `base_url = "https://api.siliconflow.cn/v1"`

For TTS, voice format is `FunAudioLLM/CosyVoice2-0.5B:{voice_name}`.

### Router Registration

Add to `platform/backend/app/api/v1/api.py`:
```python
from app.api.v1.endpoints import voice
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
```

## Frontend

### New Files

- `frontend/src/hooks/useVoiceRecorder.js` — MediaRecorder wrapper, permission management
- `frontend/src/hooks/useVoicePlayback.js` — Audio playback control, auto-play logic
- `frontend/src/components/VoiceButton.jsx` — Mic button with recording animation
- `frontend/src/components/AudioPlayer.jsx` — Play button per AI message
- `frontend/src/services/voiceService.js` — STT/TTS API calls

### UI Changes to ChatModal

Input area layout becomes:
```
[Web Search] [Deep Think] [mic button] [textarea] [Send]
```

Each assistant message gets an optional play button (visible when voice is enabled and audio is available).

### Recording

- Browser `MediaRecorder` API, mimeType `audio/webm;codecs=opus`
- Press-to-talk: click to start, click again to stop
- Minimum recording duration: 0.5s
- Visual feedback: recording animation on the mic button

### Playback

- Settings stored in localStorage: `voice-auto-play` (true/false), `voice-enabled` (true/false)
- Auto-play mode: TTS audio plays automatically when AI response completes
- Manual mode: play button on each message
- Only one audio playback at a time; new playback stops previous

### Voice Flow

1. User clicks mic → recording starts
2. User clicks mic again → recording stops
3. Frontend POSTs audio blob to `/voice/transcribe`
4. Returns text → auto-filled into input and sent via `sendMessage()`
5. AI streams text response (existing flow unchanged)
6. When response completes, if auto-play enabled: POST text to `/voice/synthesize`
7. Streaming audio response plays via `AudioContext`

## Configuration

### Environment Variables (`platform/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SILICONFLOW_API_KEY` | — | SiliconFlow API key (required for voice) |
| `VOICE_DEFAULT_VOICE` | `alex` | Default TTS voice preset |
| `VOICE_AUTO_PLAY` | `true` | Auto-play AI responses |
| `VOICE_RESPONSE_FORMAT` | `mp3` | Audio output format |

### Graceful Degradation

When `SILICONFLOW_API_KEY` is not set:
- `/voice/config` returns `voice_enabled: false`
- Frontend hides mic button and audio players
- Text chat works normally

### Infrastructure

- No new Docker services needed
- No new ports needed
- No Nginx config changes (endpoints under existing `/api/v1/` prefix)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Recording < 0.5s | Frontend toast: "Recording too short" |
| STT failure | Frontend toast: "Speech recognition failed", no message sent |
| No mic permission | Prompt user to grant, hide mic button if denied |
| TTS failure | Show text reply only, toast: "Voice synthesis failed" |
| Text too long for TTS | Truncate to 2000 characters |
| Browser unsupported | Detect and show fallback message |
| Playback during new message | Stop current playback |
| Concurrent play clicks | Cancel previous, play new |

## Dependencies

- Backend: `openai` Python package (for OpenAI-compatible SiliconFlow API)
- Frontend: No new packages (uses browser MediaRecorder + Audio APIs)

## Files Modified

- `platform/backend/app/api/v1/api.py` — Register voice router
- `platform/frontend/src/components/ChatModal.jsx` — Add VoiceButton, AudioPlayer, voice settings
- `platform/frontend/src/components/ChatModal.css` — Voice button and player styles
- `platform/.env` — Add SILICONFLOW_API_KEY and voice config

## Files Created

- `platform/backend/app/api/v1/endpoints/voice.py`
- `platform/backend/app/services/voice_service.py`
- `platform/frontend/src/hooks/useVoiceRecorder.js`
- `platform/frontend/src/hooks/useVoicePlayback.js`
- `platform/frontend/src/components/VoiceButton.jsx`
- `platform/frontend/src/components/AudioPlayer.jsx`
- `platform/frontend/src/services/voiceService.js`
