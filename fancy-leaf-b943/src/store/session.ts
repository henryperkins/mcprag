import { create } from 'zustand';
import { loadEncrypted, saveEncrypted } from '../utils/persist';

export interface TranscriptMessage {
  role: 'user' | 'assistant' | 'tool';
  text: string;
  timestamp?: number;
}

interface SessionState {
  ui: {
    leftPane: number;
    rightPane: number;
    theme: 'system' | 'light' | 'dark';
  };
  terminal: {
    history: string[];
    historyIndex: number;
    transcript: TranscriptMessage[];
    sessionId: string;
  };
  actions: {
    pushHistory: (cmd: string) => void;
    historyPrev: () => void;
    historyNext: () => void;
    appendTranscript: (msg: TranscriptMessage) => void;
    setPaneSizes: (left: number, right: number) => void;
    setTheme: (theme: 'system' | 'light' | 'dark') => void;
    clearTranscript: () => void;
    loadSession: () => Promise<void>;
    saveSession: () => Promise<void>;
  };
}

const STORAGE_KEY = 'cc.session';
let saveTimer: ReturnType<typeof setTimeout> | null = null;

const defaultState = {
  ui: {
    leftPane: 20,
    rightPane: 30,
    theme: 'system' as const,
  },
  terminal: {
    history: [],
    historyIndex: -1,
    transcript: [],
    sessionId: `session-${Date.now()}`,
  },
};

export const useSessionStore = create<SessionState>((set, get) => ({
  ...defaultState,
  actions: {
    pushHistory: (cmd: string) => {
      set((state) => ({
        terminal: {
          ...state.terminal,
          history: [...state.terminal.history, cmd].slice(-100), // Keep last 100
          historyIndex: -1,
        },
      }));
      scheduleSave();
    },
    
    historyPrev: () => {
      set((state) => {
        const { history, historyIndex } = state.terminal;
        const newIndex = historyIndex === -1 
          ? history.length - 1 
          : Math.max(0, historyIndex - 1);
        
        return {
          terminal: {
            ...state.terminal,
            historyIndex: newIndex,
          },
        };
      });
    },
    
    historyNext: () => {
      set((state) => {
        const { history, historyIndex } = state.terminal;
        const newIndex = historyIndex === -1 
          ? -1 
          : Math.min(history.length - 1, historyIndex + 1);
        
        return {
          terminal: {
            ...state.terminal,
            historyIndex: newIndex === history.length - 1 ? -1 : newIndex,
          },
        };
      });
    },
    
    appendTranscript: (msg: TranscriptMessage) => {
      set((state) => ({
        terminal: {
          ...state.terminal,
          transcript: [...state.terminal.transcript, {
            ...msg,
            timestamp: msg.timestamp || Date.now(),
          }].slice(-500), // Keep last 500 messages
        },
      }));
      scheduleSave();
    },
    
    setPaneSizes: (left: number, right: number) => {
      set((state) => ({
        ui: {
          ...state.ui,
          leftPane: left,
          rightPane: right,
        },
      }));
      scheduleSave();
    },
    
    setTheme: (theme: 'system' | 'light' | 'dark') => {
      set((state) => ({
        ui: {
          ...state.ui,
          theme,
        },
      }));
      
      // Apply theme to document
      document.documentElement.setAttribute('data-theme', theme);
      scheduleSave();
    },
    
    clearTranscript: () => {
      set((state) => ({
        terminal: {
          ...state.terminal,
          transcript: [],
        },
      }));
      scheduleSave();
    },
    
    loadSession: async () => {
      try {
        const saved = await loadEncrypted<typeof defaultState>(
          STORAGE_KEY,
          defaultState
        );
        
        set({
          ui: saved.ui,
          terminal: {
            ...saved.terminal,
            sessionId: `session-${Date.now()}`, // New session ID on load
          },
        });
        
        // Apply saved theme
        document.documentElement.setAttribute('data-theme', saved.ui.theme);
      } catch (error) {
        console.error('Failed to load session:', error);
      }
    },
    
    saveSession: async () => {
      const state = get();
      try {
        await saveEncrypted(STORAGE_KEY, {
          ui: state.ui,
          terminal: state.terminal,
        });
      } catch (error) {
        console.error('Failed to save session:', error);
      }
    },
  },
}));

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    useSessionStore.getState().actions.saveSession();
  }, 300);
}

// Load session on init
if (typeof window !== 'undefined') {
  useSessionStore.getState().actions.loadSession();
}