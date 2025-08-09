import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { KeyboardEvent } from 'react';
import { useSessionStore } from '../store/session';
import { usePerformanceMonitor } from '../store/unified.adapter';
import { useAutoScrollNearBottom } from '../hooks/useAutoScrollNearBottom';
import { renderAnsiToSpans } from '../utils/ansi';
import { claudeService, type ClaudeMessage } from '../services/claude';
import { toast } from 'sonner';
import { SlashMenu } from './SlashMenu';

const MAX_VISIBLE_LINES = 2000;
const BATCH_INTERVAL_MS = 16; // ~60fps
const THROTTLE_INTERVAL_MS = 100;

export const Terminal: React.FC = () => {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showLoadMore, setShowLoadMore] = useState(false);
  const [showIntro, setShowIntro] = useState(true);
  // Slash menu state
  const [isSlashOpen, setIsSlashOpen] = useState(false);
  const [slashFilter, setSlashFilter] = useState('');
  const [slashIndex, setSlashIndex] = useState(0);
  
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
  
  // Leave transcript empty at start; we'll show a styled intro block in the UI
  useEffect(() => { /* intro is handled by a styled callout block */ }, []);
  
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

  // Close slash menu when streaming or input cleared
  useEffect(() => {
    if (isStreaming) {
      setIsSlashOpen(false);
    }
  }, [isStreaming]);
  
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

    // If slash menu is open and input looks like a slash command, do not submit yet
    if (isSlashOpen) return;
    
    markInteraction('terminal:submit-start');
    
    const command = input.trim();
    setInput('');
    setShowIntro(false);
    
    // Add to history and transcript
    actions.pushHistory(command);
    actions.appendTranscript({
      role: 'user',
      text: `\x1b[32m➜ ~Claude_Code:${sessionId || 'new-session'}\x1b[0m \x1b[33m${command}\x1b[0m`
    });
    
    // Start streaming response
    setIsStreaming(true);
    
    try {
      await claudeService.sendPrompt(command, {
        sessionId: sessionId || undefined,
        continueSession: !!sessionId,
        maxTurns: 3,
        permissionMode: 'acceptEdits',
        allowedTools: ['Read', 'Write', 'Edit', 'Bash', 'WebSearch', 'Grep', 'Glob'],
        onMessage: (message: ClaudeMessage) => {
          // Handle different message types
          switch (message.type) {
            case 'system':
              if (message.subtype === 'init' && message.content) {
                addToStreamBatch(`\x1b[90m${message.content}\x1b[0m\n`);
              }
              break;
              
            case 'assistant':
              if (message.content) {
                addToStreamBatch(message.content);
              }
              break;
              
            case 'tool-call':
              if (message.toolName) {
                addToStreamBatch(`\n\x1b[35m🔧 Tool:\x1b[0m ${message.toolName}\n`);
                if (message.toolArguments) {
                  const argsStr = JSON.stringify(message.toolArguments, null, 2);
                  addToStreamBatch(`\x1b[90m${argsStr}\x1b[0m\n`);
                }
              }
              break;
              
            case 'tool-output':
              if (message.toolResult) {
                const resultStr = typeof message.toolResult === 'string' 
                  ? message.toolResult 
                  : JSON.stringify(message.toolResult, null, 2);
                addToStreamBatch(`\x1b[32m✓\x1b[0m ${resultStr}\n`);
              }
              break;
              
            case 'result':
              if (message.content) {
                addToStreamBatch(`\n${message.content}\n`);
              }
              if (message.duration_ms || message.total_cost_usd) {
                const stats = [];
                if (message.duration_ms) stats.push(`${message.duration_ms}ms`);
                if (message.total_cost_usd) stats.push(`$${message.total_cost_usd.toFixed(4)}`);
                if (message.num_turns) stats.push(`${message.num_turns} turns`);
                if (stats.length > 0) {
                  addToStreamBatch(`\n\x1b[90mTelemetry: ${stats.join(' | ')}\x1b[0m\n`);
                }
              }
              break;
          }
        },
        onError: (error: Error) => {
          console.error('Claude service error:', error);
          toast.error(`Error: ${error.message}`);
          addToStreamBatch(`\n\x1b[31m✗ Error:\x1b[0m ${error.message}\n`);
        },
        onComplete: () => {
          // Flush any remaining batch
          if (streamBatchRef.current.length > 0) {
            flushBatch();
          }
          setIsStreaming(false);
          markInteraction('terminal:stream-complete');
          measureInteraction('terminal:stream-complete', 'cc:terminal:submit-start');
        },
      });
    } catch (error) {
      console.error('Failed to send prompt:', error);
      toast.error('Failed to connect to Claude service');
      addToStreamBatch(`\n\x1b[31m✗ Connection Error\x1b[0m\n`);
      
      // Flush and cleanup
      if (streamBatchRef.current.length > 0) {
        flushBatch();
      }
      setIsStreaming(false);
      markInteraction('terminal:error');
    }
  };
  
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // While slash menu is open, let it handle arrows/enter/escape
    if (isSlashOpen) {
      // Allow typing and backspace to continue filtering; prevent history navigation
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'Enter' || e.key === 'Escape' || e.key === 'Home' || e.key === 'End') {
        // Let the SlashMenu's capture-phase handler consume this
        return;
      }
    }
    // Ctrl+C - Interrupt
    if (e.ctrlKey && e.key.toLowerCase() === 'c') {
      e.preventDefault();
      if (isStreaming) {
        // Abort the Claude service request
        claudeService.abort();
        
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
    // Simple slash command detection: show menu when input starts with '/'
    const trimmed = text.trimStart();
    if (trimmed.startsWith('/')) {
      setIsSlashOpen(true);
      // Use the portion after the initial '/'
      const idx = trimmed.indexOf(' ');
      const filter = (idx === -1 ? trimmed : trimmed.slice(0, idx)).replace(/^\//, '');
      setSlashFilter(filter);
      setSlashIndex(0);
    } else {
      setIsSlashOpen(false);
      setSlashFilter('');
    }
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
        {showIntro && (
          <div className="cc-callout" role="note" aria-label="Welcome">
            <div className="cc-callout-title">* Welcome to <span className="cc-strong">Claude Code</span>!</div>
            <div className="cc-callout-body">
              {`/help for help, /status for your current setup\n\ncwd: ${window.location.pathname}`}
            </div>
          </div>
        )}
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
        <div className="terminal-input-shell" role="group" aria-label="Prompt">
          <span className="terminal-prompt-tile" aria-hidden="true">›</span>
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
        </div>
        {!isStreaming && <span ref={cursorRef} className="cursor block" />}

        {/* Inline slash menu under the prompt, matching screenshot */}
        <SlashMenu
          isOpen={isSlashOpen}
          filter={slashFilter}
          onSelect={(cmd) => {
            // Replace current input with the selected command and a space
            const newVal = `${cmd} `;
            setInput(newVal);
            setIsSlashOpen(false);
            // Put caret at end
            requestAnimationFrame(() => {
              const el = inputRef.current;
              if (!el) return;
              el.focus();
              const range = document.createRange();
              range.selectNodeContents(el);
              range.collapse(false);
              const sel = window.getSelection();
              sel?.removeAllRanges();
              sel?.addRange(range);
            });
          }}
          onClose={() => setIsSlashOpen(false)}
          selectedIndex={slashIndex}
          onSelectedIndexChange={setSlashIndex}
        />
      </div>
      
      <div className="terminal-footer text-muted">
        {isStreaming ? <span>Streaming... Press Ctrl+C to interrupt</span> : <span>? for shortcuts</span>}
      </div>
    </div>
  );
};
