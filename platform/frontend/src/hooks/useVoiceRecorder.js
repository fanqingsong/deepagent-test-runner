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
