/**
 * useVoiceRecorder — browser microphone recording hook.
 *
 * Handles MediaRecorder lifecycle, permission management,
 * minimum recording duration, and silence-based auto-stop (VAD).
 */
import { useState, useRef, useCallback } from 'react';

const MIN_DURATION_MS = 500;
const MIME_TYPE = 'audio/webm;codecs=opus';

// VAD (Voice Activity Detection) settings
const SILENCE_THRESHOLD = 0.01;   // RMS level below this = silence
const SILENCE_DURATION_MS = 1500; // Stop after this much continuous silence
const VAD_POLL_MS = 100;          // How often to check audio level

export function useVoiceRecorder({ onAutoStop } = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const startTimeRef = useRef(0);
  const vadTimerRef = useRef(null);
  const silenceStartRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const vadStoppedRef = useRef(false);

  const stop = useCallback(() => {
    return new Promise((resolve) => {
      // Clear VAD timer
      if (vadTimerRef.current) {
        clearInterval(vadTimerRef.current);
        vadTimerRef.current = null;
      }
      silenceStartRef.current = null;

      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state !== 'recording') {
        setIsRecording(false);
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const duration = Date.now() - startTimeRef.current;
        setIsRecording(false);

        // Close audio context
        if (audioContextRef.current) {
          audioContextRef.current.close().catch(() => {});
          audioContextRef.current = null;
        }

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

  const start = useCallback(async () => {
    setError(null);
    vadStoppedRef.current = false;
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

      // Set up VAD using Web Audio API
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      silenceStartRef.current = null;

      // Poll audio level for silence detection
      vadTimerRef.current = setInterval(() => {
        if (vadStoppedRef.current) return;

        const data = new Float32Array(analyser.fftSize);
        analyser.getFloatTimeDomainData(data);

        // Calculate RMS volume
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
        const rms = Math.sqrt(sum / data.length);

        const now = Date.now();
        const elapsed = now - startTimeRef.current;

        if (rms < SILENCE_THRESHOLD) {
          // Only start counting silence after minimum recording duration
          if (elapsed > MIN_DURATION_MS) {
            if (!silenceStartRef.current) {
              silenceStartRef.current = now;
            } else if (now - silenceStartRef.current > SILENCE_DURATION_MS) {
              // Silence detected for long enough — auto-stop
              vadStoppedRef.current = true;
              clearInterval(vadTimerRef.current);
              vadTimerRef.current = null;
              if (onAutoStop) onAutoStop();
            }
          }
        } else {
          // Sound detected — reset silence timer
          silenceStartRef.current = null;
        }
      }, VAD_POLL_MS);
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Microphone permission denied');
      } else {
        setError('Failed to start recording');
      }
    }
  }, [onAutoStop]);

  return { isRecording, error, start, stop };
}
