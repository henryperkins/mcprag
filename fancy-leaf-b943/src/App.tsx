import { useEffect } from 'react';
import { Terminal } from './components/Terminal';
import { OfflineIndicator } from './components/OfflineIndicator';
import './App.css';

function App() {
  // Apply dark theme by default
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);
  
  return (
    <div className="app-container">
      <OfflineIndicator />
      <Terminal />
    </div>
  );
}

export default App;
