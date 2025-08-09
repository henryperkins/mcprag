import { useEffect } from 'react';
import { Terminal } from './components/Terminal';
import { OfflineIndicator } from './components/OfflineIndicator';

function App() {
  // Apply dark theme by default
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);
  
  return (
    <>
      <OfflineIndicator />
      <Terminal />
    </>
  );
}

export default App;
