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
