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
