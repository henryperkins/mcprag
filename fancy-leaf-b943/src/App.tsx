import { useEffect } from 'react';
import { OfflineIndicator } from './components/OfflineIndicator';
import { Header } from './components/Header';
import { Transcript } from './components/Transcript';
import { PromptBar } from './components/PromptBar';
import { claudeService } from './services/claude';
import { useSession } from './store/session.state';
import { useUnifiedSession } from './store/unified.adapter';

function App() {
  // Apply dark theme by default
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    // Enable Tailwind dark variants without introducing a light theme
    document.documentElement.classList.add('dark');
  }, []);

  // Wire session controls to client options
  const sess = useSession();
  const unified = useUnifiedSession();
  const controls = sess.controls;
  const currentSessionId = unified.session.id || sess.currentSessionId || undefined;

  const handleSubmit = (prompt: string) => {
    return claudeService.sendPrompt(prompt, {
      sessionId: currentSessionId,
      model: controls.model,
      maxTurns: controls.maxTurns,
      permissionMode: controls.permissionMode,
      verbose: controls.verbose,
      systemPrompt: controls.systemPrompt,
      appendSystemPrompt: controls.appendSystemPrompt,
      allowedTools: controls.allowedTools,
      disallowedTools: controls.disallowedTools,
      cwd: '/home/azureuser/mcprag',
      continueSession: Boolean(currentSessionId),
      mcpConfig: controls.mcpConfig,
      permissionPromptTool: controls.permissionPromptTool,
      outputFormat: controls.outputFormat,
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
