import { useStore } from './useStore';
import { useSession } from './session.state';
import { useSessionStore } from './session';

/**
 * Unified store adapter that provides a single interface for all stores
 * This is a non-breaking adapter pattern that preserves existing functionality
 * while providing unified hooks for new components
 */

export interface UnifiedState {
  // Session management
  session: {
    id: string | null;
    isRunning: boolean;
    model: string;
    cwd: string;
    tools: string[];
    mcpServers: { name: string; status: string }[];
    stats?: {
      numTurns: number;
      durationMs: number;
      totalCostUsd: number;
    };
  };
  
  // UI state
  ui: {
    theme: 'dark' | 'light' | 'system';
    leftPaneSize: number;
    rightPaneSize: number;
    sidebarCollapsed: boolean;
  };
  
  // Terminal state
  terminal: {
    transcript: Array<{
      role: 'user' | 'assistant' | 'tool';
      text: string;
      timestamp?: number;
    }>;
    history: string[];
    historyIndex: number;
    isStreaming: boolean;
  };
  
  // Files state
  files: {
    tree: any[]; // FileNode type from useStore
    selected: any | null;
  };
}

/**
 * Unified session hook - merges session data from multiple stores
 */
export function useUnifiedSession() {
  const sessionState = useSession();
  const sessionStore = useSessionStore();
  const appStore = useStore();
  
  return {
    session: {
      id: sessionState.currentSessionId || sessionStore.terminal.sessionId,
      isRunning: sessionState.isRunning,
      model: sessionState.initMeta?.model || 'unknown',
      cwd: sessionState.initMeta?.cwd || '/',
      tools: sessionState.initMeta?.tools || [],
      mcpServers: sessionState.initMeta?.mcpServers || [],
      stats: sessionState.runStats ? {
        numTurns: sessionState.runStats.numTurns,
        durationMs: sessionState.runStats.durationMs,
        totalCostUsd: sessionState.runStats.totalCostUsd,
      } : undefined,
    },
    ui: {
      theme: sessionStore.ui.theme,
      leftPaneSize: sessionStore.ui.leftPane,
      rightPaneSize: sessionStore.ui.rightPane,
      sidebarCollapsed: appStore.sidebarCollapsed,
    },
    terminal: {
      transcript: sessionStore.terminal.transcript,
      history: sessionStore.terminal.history,
      historyIndex: sessionStore.terminal.historyIndex,
      isStreaming: appStore.isStreaming,
    },
    files: {
      tree: appStore.files,
      selected: appStore.selectedFile,
    },
  } as UnifiedState;
}

/**
 * Unified UI hook - provides UI-specific state and actions
 */
export function useUnifiedUI() {
  const sessionStore = useSessionStore();
  const appStore = useStore();
  
  return {
    theme: sessionStore.ui.theme,
    setTheme: sessionStore.actions.setTheme,
    leftPane: sessionStore.ui.leftPane,
    rightPane: sessionStore.ui.rightPane,
    setPaneSizes: sessionStore.actions.setPaneSizes,
    sidebarCollapsed: appStore.sidebarCollapsed,
    toggleSidebar: appStore.toggleSidebar,
  };
}

/**
 * Unified terminal hook - provides terminal-specific state and actions
 */
export function useUnifiedTerminal() {
  const sessionStore = useSessionStore();
  const appStore = useStore();
  
  return {
    transcript: sessionStore.terminal.transcript,
    history: sessionStore.terminal.history,
    historyIndex: sessionStore.terminal.historyIndex,
    sessionId: sessionStore.terminal.sessionId,
    isStreaming: appStore.isStreaming,
    
    // Actions
    appendTranscript: sessionStore.actions.appendTranscript,
    pushHistory: sessionStore.actions.pushHistory,
    historyPrev: sessionStore.actions.historyPrev,
    historyNext: sessionStore.actions.historyNext,
    clearTranscript: sessionStore.actions.clearTranscript,
    setIsStreaming: appStore.setIsStreaming,
  };
}

/**
 * Unified files hook - provides file system state and actions
 */
export function useUnifiedFiles() {
  const appStore = useStore();
  
  return {
    files: appStore.files,
    selectedFile: appStore.selectedFile,
    setSelectedFile: appStore.setSelectedFile,
    updateFileContent: appStore.updateFileContent,
    refreshFiles: appStore.refreshFiles,
  };
}

/**
 * Performance monitoring hook - adds UserTiming marks
 */
export function usePerformanceMonitor() {
  const markInteraction = (name: string, metadata?: Record<string, any>) => {
    if (typeof window !== 'undefined' && window.performance) {
      const mark = `cc:${name}`;
      performance.mark(mark, {
        detail: metadata,
      });
    }
  };
  
  const measureInteraction = (name: string, startMark: string, endMark?: string) => {
    if (typeof window !== 'undefined' && window.performance) {
      try {
        performance.measure(
          `cc:measure:${name}`,
          startMark,
          endMark || `cc:${name}`
        );
      } catch (e) {
        console.debug('Performance measurement failed:', e);
      }
    }
  };
  
  return {
    markInteraction,
    measureInteraction,
  };
}