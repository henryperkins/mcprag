import { useEffect } from 'react';
import { OfflineIndicator } from './components/OfflineIndicator';
import { Header } from './components/Header';
import { Transcript } from './components/Transcript';
import { PromptBar } from './components/PromptBar';
import { claudeService } from './services/claude';

function App() {
  // Apply dark theme by default
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    // Enable Tailwind dark variants without introducing a light theme
    document.documentElement.classList.add('dark');
  }, []);

  const handleSubmit = (prompt: string) => {
    return claudeService.sendPrompt(prompt, {
      // Callbacks are optional; stores update via claudeService internally
      onError: (err) => console.error('Claude error:', err),
    });
  };

  const handleInterrupt = () => {
    claudeService.abort();
  };
  
  return (
    <div className="app-container">
      <OfflineIndicator />
      <Header />
      <main className="app-main">
        <Transcript />
      </main>
      <footer className="app-footer">
        <PromptBar onSubmit={handleSubmit} onInterrupt={handleInterrupt} />
      </footer>
    </div>
  );
}

export default App;
