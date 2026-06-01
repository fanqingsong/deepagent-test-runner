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
