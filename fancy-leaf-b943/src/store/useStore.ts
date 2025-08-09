import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
}

export interface ToolCall {
  id: string
  name: string
  arguments: unknown
  result?: unknown
}

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  content?: string
}

export interface Terminal {
  id: string
  output: string[]
  isRunning: boolean
  currentCommand?: string
}

interface AppState {
  // Authentication
  apiKey: string | null
  setApiKey: (key: string) => void
  
  // Chat
  messages: Message[]
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  clearMessages: () => void
  isStreaming: boolean
  setIsStreaming: (streaming: boolean) => void
  
  // File System
  files: FileNode[]
  selectedFile: FileNode | null
  setSelectedFile: (file: FileNode | null) => void
  updateFileContent: (path: string, content: string) => void
  refreshFiles: () => Promise<void>
  
  // Terminal
  terminals: Terminal[]
  activeTerminalId: string | null
  createTerminal: () => string
  closeTerminal: (id: string) => void
  appendToTerminal: (id: string, output: string) => void
  clearTerminal: (id: string) => void
  
  // UI State
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  theme: 'dark' | 'light'
  toggleTheme: () => void
}

export const useStore = create<AppState>((set) => ({
  // Authentication
  apiKey: localStorage.getItem('anthropic_api_key'),
  setApiKey: (key: string) => {
    localStorage.setItem('anthropic_api_key', key)
    set({ apiKey: key })
  },
  
  // Chat
  messages: [],
  addMessage: (message) => {
    const newMessage: Message = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    }
    set((state) => ({ messages: [...state.messages, newMessage] }))
  },
  clearMessages: () => set({ messages: [] }),
  isStreaming: false,
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
  
  // File System
  files: [],
  selectedFile: null,
  setSelectedFile: (file) => set({ selectedFile: file }),
  updateFileContent: (path, content) => {
    set((state) => {
      const updateNode = (nodes: FileNode[]): FileNode[] => {
        return nodes.map((node) => {
          if (node.path === path) {
            return { ...node, content }
          }
          if (node.children) {
            return { ...node, children: updateNode(node.children) }
          }
          return node
        })
      }
      return { files: updateNode(state.files) }
    })
  },
  refreshFiles: async () => {
    try {
      const response = await fetch('/api/files')
      const files = await response.json()
      set({ files })
    } catch (error) {
      console.error('Failed to refresh files:', error)
    }
  },
  
  // Terminal
  terminals: [],
  activeTerminalId: null,
  createTerminal: () => {
    const id = crypto.randomUUID()
    const terminal: Terminal = {
      id,
      output: [],
      isRunning: false,
    }
    set((state) => ({
      terminals: [...state.terminals, terminal],
      activeTerminalId: id,
    }))
    return id
  },
  closeTerminal: (id) => {
    set((state) => ({
      terminals: state.terminals.filter((t) => t.id !== id),
      activeTerminalId:
        state.activeTerminalId === id
          ? state.terminals.find((t) => t.id !== id)?.id || null
          : state.activeTerminalId,
    }))
  },
  appendToTerminal: (id, output) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, output: [...t.output, output] } : t
      ),
    }))
  },
  clearTerminal: (id) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, output: [] } : t
      ),
    }))
  },
  
  // UI State
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  theme: 'dark',
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
}))