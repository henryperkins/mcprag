import React, { useState, useEffect, useRef } from 'react';

export const OfflineIndicator: React.FC = () => {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const announcedRef = useRef(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      announcedRef.current = false;
    };
    
    const handleOffline = () => {
      setIsOffline(true);
      announcedRef.current = false;
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Announce status change to screen readers
  useEffect(() => {
    if (!announcedRef.current) {
      const message = isOffline 
        ? 'You are now offline. Some features may be limited.'
        : 'You are back online.';
      
      // Create temporary live region for important announcement
      const liveRegion = document.createElement('div');
      liveRegion.setAttribute('role', 'alert');
      liveRegion.setAttribute('aria-live', 'assertive');
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.className = 'sr-only';
      liveRegion.textContent = message;
      document.body.appendChild(liveRegion);
      
      announcedRef.current = true;
      
      setTimeout(() => {
        document.body.removeChild(liveRegion);
      }, 1000);
    }
  }, [isOffline]);

  if (!isOffline) return null;

  return (
    <div 
      className="offline-indicator bg-warning"
      role="status"
      aria-live="polite"
      aria-label="Network status"
    >
      <span aria-hidden="true">⚠</span>
      <span>Offline - Some features may be limited</span>
    </div>
  );
};