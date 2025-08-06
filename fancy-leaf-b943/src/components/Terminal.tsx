import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { KeyboardEvent } from 'react';
import { useSessionStore } from '../store/session';
import { renderAnsiToSpans } from '../utils/ansi';

export const Terminal: React.FC = () => {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState('');
  const inputRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const cursorRef = useRef<HTMLSpanElement>(null);
  const rafRef = useRef<number>(0);
  
  const terminal = useSessionStore(state => state.terminal);
  const actions = useSessionStore(state => state.actions);
  const { transcript, history, historyIndex, sessionId } = terminal;
  
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
  }, []);
  
  // Auto-scroll to bottom when transcript updates
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [transcript]);
  
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
  
  // Streaming renderer (60fps)
  const streamRenderer = useCallback(() => {
    if (streamBuffer.length > 0) {
      // Take chunk of buffer (simulate token streaming)
      const chunkSize = Math.min(10, streamBuffer.length);
      const chunk = streamBuffer.slice(0, chunkSize);
      setStreamBuffer(prev => prev.slice(chunkSize));
      
      // Append to last assistant message
      actions.appendTranscript({
        role: 'assistant',
        text: chunk
      });
      
      rafRef.current = requestAnimationFrame(streamRenderer);
    } else {
      setIsStreaming(false);
    }
  }, [streamBuffer, actions]);
  
  useEffect(() => {
    if (isStreaming && streamBuffer.length > 0) {
      rafRef.current = requestAnimationFrame(streamRenderer);
    }
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [isStreaming, streamBuffer, streamRenderer]);
  
  const handleSubmit = async () => {
    if (!input.trim() || isStreaming) return;
    
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
                setIsStreaming(false);
                break;
              }
              setStreamBuffer(prev => prev + data);
            }
          }
        }
      }
    } catch (error) {
      // Fallback mock response for development
      const mockResponse = `\x1b[35m🔧 Tool:\x1b[0m Executing command...
\x1b[32m✓\x1b[0m Operation completed successfully
\x1b[90mTelemetry: 42ms | Tokens: 128\x1b[0m`;
      
      // Simulate streaming
      for (let i = 0; i < mockResponse.length; i += 5) {
        await new Promise(resolve => setTimeout(resolve, 20));
        setStreamBuffer(prev => prev + mockResponse.slice(i, i + 5));
      }
    }
  };
  
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // Ctrl+C - Interrupt
    if (e.ctrlKey && e.key.toLowerCase() === 'c') {
      e.preventDefault();
      if (isStreaming) {
        setIsStreaming(false);
        setStreamBuffer('');
        actions.appendTranscript({
          role: 'assistant',
          text: '\x1b[31m^C\x1b[0m'
        });
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
  
  // Update cursor position
  useEffect(() => {
    if (cursorRef.current && inputRef.current) {
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const inputRect = inputRef.current.getBoundingClientRect();
        
        cursorRef.current.style.left = `${rect.right - inputRect.left}px`;
        cursorRef.current.style.top = `${rect.top - inputRect.top}px`;
      }
    }
  });
  
  return (
    <div className="terminal-root">
      <div className="terminal-header">
        <span className="fg-ansi-10">Claude Code Terminal</span>
        <span className="fg-ansi-8"> - {sessionId}</span>
      </div>
      
      <div ref={outputRef} className="terminal-output" style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {transcript.map((msg, idx) => (
          <div key={idx} className="terminal-line">
            {renderAnsiToSpans(msg.text)}
          </div>
        ))}
      </div>
      
      <div className="terminal-input" style={{ padding: '0 12px 12px 12px' }}>
        <span className="terminal-prompt fg-ansi-2">
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
      
      <div className="terminal-footer fg-ansi-8">
        {isStreaming ? (
          <span>Streaming... Press Ctrl+C to interrupt</span>
        ) : (
          <span>Enter: Submit | Shift+Enter: Newline | ↑/↓: History | Ctrl+L: Clear | Ctrl+C: Interrupt</span>
        )}
      </div>
    </div>
  );
};