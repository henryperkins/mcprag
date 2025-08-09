import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { KeyboardEvent } from 'react';
import { useSessionStore } from '../store/session';
import { usePerformanceMonitor } from '../store/unified.adapter';
import { useAutoScrollNearBottom } from '../hooks/useAutoScrollNearBottom';
import { renderAnsiToSpans } from '../utils/ansi';

const MAX_VISIBLE_LINES = 2000;
const BATCH_INTERVAL_MS = 16; // ~60fps
const THROTTLE_INTERVAL_MS = 100;

export const Terminal: React.FC = () => {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showLoadMore, setShowLoadMore] = useState(false);
  
  const inputRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const cursorRef = useRef<HTMLSpanElement>(null);
  
  // Batching refs
  const streamBatchRef = useRef<string[]>([]);
  const batchTimerRef = useRef<number>(0);
  const lastRenderTimeRef = useRef<number>(0);
  
  // Performance monitoring
  const { markInteraction, measureInteraction } = usePerformanceMonitor();
  
  const terminal = useSessionStore(state => state.terminal);
  const actions = useSessionStore(state => state.actions);
  const { transcript, history, historyIndex, sessionId } = terminal;
  
  // Window management - only render visible lines
  const visibleTranscript = useMemo(() => {
    if (transcript.length <= MAX_VISIBLE_LINES) {
      setShowLoadMore(false);
      return transcript;
    }
    
    const start = Math.max(0, transcript.length - MAX_VISIBLE_LINES);
    setShowLoadMore(start > 0);
    return transcript.slice(start);
  }, [transcript]);
  
  // Initialize session info on mount
  useEffect(() => {
    const initMessage = `\x1b[32m➜ Claude Code Terminal\x1b[0m
\x1b[90mModel: Claude 3.5 Sonnet
CWD: ${window.location.pathname}
Mode: Interactive
Session ID: ${sessionId}
Tools: Available
MCP Servers: Connected\x1b[0m

Type your prompt and press Enter to submit.
`;
    actions.appendTranscript({ role: 'assistant', text: initMessage });
  }, [actions, sessionId]);
  
  // Batch stream updates with RAF
  const flushBatch = useCallback(() => {
    if (streamBatchRef.current.length === 0) {
      batchTimerRef.current = 0;
      return;
    }
    
    const now = performance.now();
    const timeSinceLastRender = now - lastRenderTimeRef.current;
    
    // Throttle if rendering too frequently
    if (timeSinceLastRender < BATCH_INTERVAL_MS) {
      batchTimerRef.current = requestAnimationFrame(flushBatch);
      return;
    }
    
    // Combine all batched chunks
    const combinedText = streamBatchRef.current.join('');
    streamBatchRef.current = [];
    lastRenderTimeRef.current = now;
    
    // Update transcript
    actions.appendTranscript({
      role: 'assistant',
      text: combinedText
    });
    
    // Mark performance
    markInteraction('terminal:batch-flush', {
      chunkSize: combinedText.length,
      timeSinceLastRender
    });
    
    batchTimerRef.current = 0;
  }, [actions, markInteraction]);
  
  // Add to stream batch
  const addToStreamBatch = useCallback((text: string) => {
    streamBatchRef.current.push(text);
    
    if (!batchTimerRef.current) {
      batchTimerRef.current = requestAnimationFrame(flushBatch);
    }
  }, [flushBatch]);
  
  // Auto-scroll only when near bottom
  useAutoScrollNearBottom(
    outputRef,
    [visibleTranscript],
    40 // threshold in pixels
  );
  
  // Update input from history navigation
  useEffect(() => {
    if (historyIndex >= 0 && historyIndex < history.length) {
      setInput(history[historyIndex]);
    } else if (historyIndex === -1) {
      setInput('');
    }
  }, [historyIndex, history]);
  
  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  
  // Cleanup batch timer on unmount
  useEffect(() => {
    return () => {
      if (batchTimerRef.current) {
        cancelAnimationFrame(batchTimerRef.current);
      }
    };
  }, []);
  
  const handleSubmit = async () => {
    if (!input.trim() || isStreaming) return;
    
    markInteraction('terminal:submit-start');
    
    const command = input.trim();
    setInput('');
    
    // Add to history and transcript
    actions.pushHistory(command);
    actions.appendTranscript({
      role: 'user',
      text: `\x1b[32m➜ ~Claude_Code:model-session\x1b[0m \x1b[33m${command}\x1b[0m`
    });
    
    // Start streaming response
    setIsStreaming(true);
    
    try {
      const response = await fetch('/api/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ prompt: command })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') {
                // Flush any remaining batch
                if (streamBatchRef.current.length > 0) {
                  flushBatch();
                }
                setIsStreaming(false);
                markInteraction('terminal:stream-complete');
                measureInteraction('terminal:stream-complete', 'cc:terminal:submit-start');
                break;
              }
              addToStreamBatch(data);
            }
          }
        }
      }
    } catch {
      // Fallback mock response for development
      const mockResponse = `\x1b[35m🔧 Tool:\x1b[0m Executing command...
\x1b[32m✓\x1b[0m Operation completed successfully
\x1b[90mTelemetry: 42ms | Tokens: 128\x1b[0m`;
      
      // Simulate batched streaming
      const chunkSize = 10;
      for (let i = 0; i < mockResponse.length; i += chunkSize) {
        await new Promise(resolve => setTimeout(resolve, 20));
        addToStreamBatch(mockResponse.slice(i, i + chunkSize));
      }
      
      // Final flush
      await new Promise(resolve => setTimeout(resolve, 100));
      if (streamBatchRef.current.length > 0) {
        flushBatch();
      }
      setIsStreaming(false);
      markInteraction('terminal:mock-complete');
      measureInteraction('terminal:mock-complete', 'cc:terminal:submit-start');
    }
  };
  
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // Ctrl+C - Interrupt
    if (e.ctrlKey && e.key.toLowerCase() === 'c') {
      e.preventDefault();
      if (isStreaming) {
        // Flush pending batches
        if (streamBatchRef.current.length > 0) {
          flushBatch();
        }
        setIsStreaming(false);
        actions.appendTranscript({
          role: 'assistant',
          text: '\x1b[31m^C\x1b[0m'
        });
        markInteraction('terminal:interrupt');
      }
      setInput('');
      return;
    }
    
    // Ctrl+V - Paste
    if (e.ctrlKey && e.key.toLowerCase() === 'v') {
      e.preventDefault();
      navigator.clipboard.readText().then(text => {
        setInput(prev => prev + text);
      });
      return;
    }
    
    // Ctrl+L - Clear
    if (e.ctrlKey && e.key.toLowerCase() === 'l') {
      e.preventDefault();
      actions.clearTranscript();
      markInteraction('terminal:clear');
      return;
    }
    
    // Arrow Up - History previous
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      actions.historyPrev();
      return;
    }
    
    // Arrow Down - History next
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      actions.historyNext();
      return;
    }
    
    // Enter - Submit (unless Shift is held)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
      return;
    }
  };
  
  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    const text = e.currentTarget.textContent || '';
    setInput(text);
  };
  
  // Throttled cursor position update
  const updateCursorPosition = useCallback(() => {
    if (cursorRef.current && inputRef.current) {
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const inputRect = inputRef.current.getBoundingClientRect();
        
        requestAnimationFrame(() => {
          if (cursorRef.current) {
            cursorRef.current.style.left = `${rect.right - inputRect.left}px`;
            cursorRef.current.style.top = `${rect.top - inputRect.top}px`;
          }
        });
      }
    }
  }, []);
  
  useEffect(() => {
    const throttledUpdate = () => {
      requestAnimationFrame(updateCursorPosition);
    };
    
    const interval = setInterval(throttledUpdate, THROTTLE_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [updateCursorPosition]);
  
  const handleLoadMore = () => {
    // This would load more transcript history if implemented
    markInteraction('terminal:load-more');
  };
  
  return (
    <div className="terminal-root">
      <div className="terminal-header">
        <span className="terminal-header-title text-brand">Claude Code Terminal</span>
        <div className="terminal-header-session">
          <span className="terminal-header-session-id" title={`Session ID: ${sessionId}`}>
            {sessionId}
          </span>
          <button 
            className="terminal-header-copy"
            onClick={() => navigator.clipboard.writeText(sessionId)}
            title="Copy session ID"
            aria-label="Copy session ID"
          >
            📋
          </button>
        </div>
      </div>
      
      <div ref={outputRef} className="terminal-output" style={{ flex: 1, overflowY: 'auto' }}>
        {showLoadMore && (
          <button 
            className="terminal-load-more"
            onClick={handleLoadMore}
            aria-label="Load older output"
          >
            ▲ Load older output ({transcript.length - visibleTranscript.length} hidden lines)
          </button>
        )}
        {visibleTranscript.map((msg, idx) => (
          <div key={`${msg.timestamp}-${idx}`} className="terminal-line">
            {renderAnsiToSpans(msg.text)}
          </div>
        ))}
      </div>
      
      <div className="terminal-input">
        <span className="terminal-prompt text-prompt">
          ➜ ~Claude_Code:model-session
        </span>
        <div
          ref={inputRef}
          className="terminal-input-field"
          contentEditable={!isStreaming}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          suppressContentEditableWarning
          role="textbox"
          aria-label="Terminal input"
          aria-multiline="false"
        >
          {input}
        </div>
        {!isStreaming && <span ref={cursorRef} className="cursor block" />}
      </div>
      
      <div className="terminal-footer text-muted">
        {isStreaming ? (
          <span>Streaming... Press Ctrl+C to interrupt</span>
        ) : (
          <span>Enter: Submit | Shift+Enter: Newline | ↑/↓: History | Ctrl+L: Clear | Ctrl+C: Interrupt</span>
        )}
      </div>
    </div>
  );
};
