import { useEffect } from 'react';
import { ChatPane } from './components/ChatPane';
import { OfflineIndicator } from './components/OfflineIndicator';

function App() {
  // Apply dark theme by default
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);
  
  return (
    <>
      <OfflineIndicator />
      <ChatPane />
    </>
  );
}

export default App;
