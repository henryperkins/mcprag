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
            <div key={idx} className={`chat-message chat-message-${msg.role}`}>
              <div className="chat-message-role fg-ansi-14">
                {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Claude' : 'Tool'}
              </div>
              <div className="chat-message-text">
                {renderAnsiToSpans(msg.text)}
              </div>
              {msg.timestamp && (
                <div className="chat-message-time fg-ansi-8">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
