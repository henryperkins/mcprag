import { useEffect } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Terminal } from './components/Terminal';
import { FileTree } from './components/FileTree';
import { ChatPane } from './components/ChatPane';
import { PwaInstallPrompt } from './components/PwaInstallPrompt';
import { OfflineIndicator } from './components/OfflineIndicator';
import { useSessionStore } from './store/session';
import './styles/terminal.css';

function App() {
  const { ui, actions } = useSessionStore();
  
  // Load session on mount
  useEffect(() => {
    actions.loadSession();
  }, []);
  
  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', ui.theme);
  }, [ui.theme]);
  
  return (
    <>
      <OfflineIndicator />
      <div className="panel-container">
        <PanelGroup direction="horizontal" className="panel-group">
        {/* Left Panel - File Tree */}
        <Panel 
          defaultSize={ui.leftPane}
          minSize={10}
          maxSize={40}
          onResize={(size) => actions.setPaneSizes(size, ui.rightPane)}
        >
          <div className="panel-content">
            <FileTree />
          </div>
        </Panel>
        
        <PanelResizeHandle className="panel-resizer" />
        
        {/* Middle Panel - Terminal */}
        <Panel defaultSize={100 - ui.leftPane - ui.rightPane}>
          <div className="panel-content">
            <Terminal />
          </div>
        </Panel>
        
        <PanelResizeHandle className="panel-resizer" />
        
        {/* Right Panel - Chat */}
        <Panel 
          defaultSize={ui.rightPane}
          minSize={10}
          maxSize={40}
          onResize={(size) => actions.setPaneSizes(ui.leftPane, size)}
        >
          <div className="panel-content">
            <ChatPane />
          </div>
        </Panel>
        </PanelGroup>
      </div>
      <PwaInstallPrompt />
    </>
  );
}

export default App;