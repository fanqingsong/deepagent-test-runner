import { useEffect, useState } from 'react';
import './Toast.css';

export default function Toast({ message, type, onDone }) {
  const [visible, setVisible] = useState(false);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    if (!message) return;
    setVisible(true);
    setFading(false);

    const fadeTimer = setTimeout(() => setFading(true), 2000);
    const removeTimer = setTimeout(() => {
      setVisible(false);
      onDone?.();
    }, 2500);

    return () => { clearTimeout(fadeTimer); clearTimeout(removeTimer); };
  }, [message, type]);

  if (!visible) return null;

  return (
    <div className={`toast toast--${type || 'success'} ${fading ? 'toast--fading' : ''}`}>
      <span className="toast-icon">{type === 'error' ? '✕' : '✓'}</span>
      <span className="toast-text">{message}</span>
    </div>
  );
}
