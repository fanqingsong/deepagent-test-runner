export default function ScreenshotLightbox({ src, onClose }) {
  if (!src) return null;
  return (
    <div className="screenshot-lightbox-overlay" onClick={onClose}>
      <div className="screenshot-lightbox-content" onClick={(e) => e.stopPropagation()}>
        <button className="screenshot-lightbox-close" onClick={onClose}>x</button>
        <img src={src} alt="Screenshot detail" className="screenshot-lightbox-image" />
      </div>
    </div>
  );
}
