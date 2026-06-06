import { useState, useRef, useCallback } from 'react';
import { generateScriptStream } from '../api';

const STEP_ORDER = [
  'Initializing',
  'Fetching page context',
  'Generating script',
  'Validating script',
  'Executing in sandbox',
  'Saving result',
  'Retrying (fixing script)',
];

export default function useScriptGenerationStream(testCaseId) {
  const [active, setActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(null);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [toolCalls, setToolCalls] = useState([]);
  const [generatedScript, setGeneratedScript] = useState(null);
  const [error, setError] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [finalResult, setFinalResult] = useState(null);

  const abortRef = useRef(null);
  const readerRef = useRef(null);

  const reset = useCallback(() => {
    setActive(false);
    setCurrentStep(null);
    setCompletedSteps([]);
    setStreamingContent('');
    setToolCalls([]);
    setGeneratedScript(null);
    setError(null);
    setIsComplete(false);
    setFinalResult(null);
  }, []);

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    if (readerRef.current) {
      readerRef.current.cancel().catch(() => {});
      readerRef.current = null;
    }
    setActive(false);
    setCurrentStep(prev => prev ? `${prev} (cancelled)` : 'Cancelled');
  }, []);

  const generate = useCallback(async (opts = {}) => {
    reset();
    setActive(true);
    setCurrentStep('Initializing');

    const response = await generateScriptStream(testCaseId, opts);
    const reader = response.body.getReader();
    readerRef.current = reader;
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = null;
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            try {
              const payload = JSON.parse(line.slice(6));
              handleEvent(currentEvent, payload);
            } catch {
              // skip malformed data
            }
            currentEvent = null;
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message);
      }
    } finally {
      setActive(false);
    }
  }, [testCaseId, reset]);

  function handleEvent(event, payload) {
    switch (event) {
      case 'step_started':
        setCurrentStep(payload.step);
        break;

      case 'step_completed':
        setCompletedSteps(prev => [...prev, { step: payload.step, status: payload.status }]);
        break;

      case 'tool_call':
        setToolCalls(prev => [...prev, {
          tool: payload.tool,
          args: payload.args,
          status: 'running',
        }]);
        // Extract generated script from tool args
        if (['validate_script', 'execute_script_tool', 'save_generated_script'].includes(payload.tool)) {
          const script = payload.args?.script;
          if (script && !generatedScript) {
            setGeneratedScript(script);
          }
        }
        break;

      case 'tool_result': {
        setToolCalls(prev => {
          const updated = [...prev];
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].tool === payload.tool && updated[i].status === 'running') {
              updated[i] = { ...updated[i], status: payload.is_error ? 'error' : 'done', result: payload.result_preview };
              break;
            }
          }
          return updated;
        });
        break;
      }

      case 'llm_token':
        setStreamingContent(prev => prev + payload.text);
        break;

      case 'error':
        setError(payload.message);
        setActive(false);
        break;

      case 'done':
        setFinalResult(payload);
        setIsComplete(true);
        setActive(false);
        break;
    }
  }

  const progress = (() => {
    const idx = STEP_ORDER.findIndex(s => currentStep?.startsWith(s));
    const total = STEP_ORDER.length;
    const completed = completedSteps.length;
    return { current: idx >= 0 ? idx + 1 : completed + 1, total, percent: Math.round(((completed) / total) * 100) };
  })();

  return {
    active,
    currentStep,
    completedSteps,
    streamingContent,
    toolCalls,
    generatedScript,
    error,
    isComplete,
    finalResult,
    progress,
    generate,
    cancel,
    reset,
  };
}
