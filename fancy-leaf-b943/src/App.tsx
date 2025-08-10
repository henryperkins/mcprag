import { useEffect } from 'react';
import { ChatPane } from './components/ChatPane';
import { OfflineIndicator } from './components/OfflineIndicator';

function App() {
  // Apply dark theme by default
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    // Enable Tailwind dark variants without introducing a light theme
    document.documentElement.classList.add('dark');
  }, []);
  
  return (
    <div className="app-container">
      <OfflineIndicator />
      <ChatPane />
    </div>
  );
}

export default App;
