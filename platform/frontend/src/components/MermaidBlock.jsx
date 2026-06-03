import { useEffect, useRef, useState, useId } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'strict',
});

export function MermaidBlock({ content }) {
  const containerRef = useRef(null);
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(null);
  const id = useId().replace(/:/g, '_');

  useEffect(() => {
    let cancelled = false;

    const render = async () => {
      try {
        const { svg: rendered } = await mermaid.render(`mermaid-${id}`, content);
        if (!cancelled) {
          setSvg(rendered);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Mermaid render failed');
          setSvg('');
        }
      }
    };

    render();
    return () => { cancelled = true; };
  }, [content, id]);

  if (error) {
    return (
      <div className="mermaid-error">
        <pre><code>{content}</code></pre>
        <p className="mermaid-error-msg">Mermaid: {error}</p>
      </div>
    );
  }

  if (!svg) return null;

  return (
    <div
      className="mermaid-container"
      ref={containerRef}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
