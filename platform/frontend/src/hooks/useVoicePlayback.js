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
