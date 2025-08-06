import React, { useEffect, useRef } from 'react';
import { useSessionStore } from '../store/session';
import { renderAnsiToSpans } from '../utils/ansi';

export const ChatPane: React.FC = () => {
  const { transcript } = useSessionStore(state => state.terminal);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);
  
  return (
    <div className="chat-pane-container">
      <div className="chat-pane-header fg-ansi-10">
        Chat History
      </div>
      <div className="chat-pane-content" ref={scrollRef}>
        {transcript.length === 0 ? (
          <div className="chat-empty fg-ansi-8">
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
              <div className="chat-message-role fg-ansi-14">
                <span className="chat-message-icon">
                  {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🤖' : '🔧'}
                </span>
                {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Claude' : 'Tool'}
              </div>
              <div className="chat-message-text">
                {renderAnsiToSpans(msg.text)}
              </div>
              <div className="chat-message-footer">
                {msg.timestamp && (
                  <div className="chat-message-time fg-ansi-8">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                )}
                <div className="chat-message-status">
                  <span className="chat-message-status-icon fg-ansi-10">✓</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
