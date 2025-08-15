import React, { useRef } from 'react';
import { useSessionStore } from '../store/session';
import { useAutoScrollNearBottom } from '../hooks/useAutoScrollNearBottom';
import AnsiText from './AnsiText';

export const ChatPane: React.FC = () => {
  const { transcript } = useSessionStore(state => state.terminal);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll only when near bottom
  useAutoScrollNearBottom(
    scrollRef,
    [transcript],
    40 // threshold in pixels
  );
  
  return (
    <div className="chat-pane-container">
      <div className="chat-pane-header text-brand">
        Chat History
      </div>
      <div className="chat-pane-content" ref={scrollRef}>
        {transcript.length === 0 ? (
          <div className="chat-empty text-muted">
            No messages yet. Start typing in the terminal to begin.
          </div>
        ) : (
          transcript.map((msg, idx) => (
            <div 
              key={idx} 
              className={`chat-message chat-message-${msg.role}`}
              tabIndex={0}
              role="button"
              aria-label={`${msg.role} message from ${msg.timestamp ? new Date(msg.timestamp).toLocaleString() : 'unknown time'}`}
              onClick={() => console.log('Message clicked:', idx)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  console.log('Message selected:', idx);
                }
              }}
            >
              <div className="chat-message-role text-accent">
                <span className="chat-message-icon">
                  {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🤖' : '🔧'}
                </span>
                {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Claude' : 'Tool'}
              </div>
              <div className="chat-message-text">
                <AnsiText text={msg.text} useWorker workerThreshold={1500} />
              </div>
              <div className="chat-message-footer">
                {msg.timestamp && (
                  <div className="chat-message-time text-muted">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                )}
                <div className="chat-message-status">
                  <span className="chat-message-status-icon text-success">✓</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
