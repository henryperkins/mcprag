import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SDKMessage } from './messages.state'

type InitMeta = {
  model: string
  cwd: string
  permissionMode: 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan'
  tools: string[]
  mcpServers: { name: string; status: string }[]
  apiKeySource?: string
}

type RunStats = {
  numTurns: number
  durationMs: number
  durationApiMs: number
  totalCostUsd: number
}

type SessionControls = {
  maxTurns: number
  permissionMode: 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan'
  verbose: boolean
  outputFormat: 'text' | 'json' | 'stream-json'
  systemPrompt?: string
  appendSystemPrompt?: string
  model?: string
  allowedTools?: string[]
  disallowedTools?: string[]
  mcpConfig?: string
  permissionPromptTool?: string
}

type SessionStore = {
  currentSessionId: string | null
  initMeta: InitMeta | null
  runStats: RunStats | null
  controls: SessionControls
  recentSessions: string[]
  isRunning: boolean
  
  setInit: (msg: SDKMessage) => void
  setResult: (msg: SDKMessage) => void
  setControls: (patch: Partial<SessionControls>) => void
  setSession: (id: string | null) => void
  rememberSession: (id: string) => void
  setRunning: (running: boolean) => void
  clearSession: () => void
}

export const useSession = create<SessionStore>()(
  persist(
    (set, get) => ({
      currentSessionId: null,
      initMeta: null,
      runStats: null,
      controls: {
        maxTurns: 6,
        permissionMode: 'default',
        verbose: false,
        outputFormat: 'stream-json',
        model: undefined,
        allowedTools: undefined,
        disallowedTools: undefined,
        mcpConfig: undefined,
        permissionPromptTool: undefined,
      },
      recentSessions: [],
      isRunning: false,

      setInit: (msg) => {
        if (msg?.type === 'system' && msg?.subtype === 'init') {
          const meta: InitMeta = {
            model: msg.model || 'unknown',
            cwd: msg.cwd || '/',
            permissionMode: (msg.permissionMode as 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan') || 'default',
            tools: msg.tools || [],
            mcpServers: msg.mcp_servers || [],
            apiKeySource: msg.apiKeySource,
          }
          set({ initMeta: meta })
          if (msg.session_id) {
            set({ currentSessionId: msg.session_id })
            get().rememberSession(msg.session_id)
          }
        }
      },

      setResult: (msg) => {
        if (msg?.type === 'result') {
          const stats: RunStats = {
            numTurns: msg.num_turns ?? 0,
            durationMs: msg.duration_ms ?? 0,
            durationApiMs: msg.duration_api_ms ?? 0,
            totalCostUsd: msg.total_cost_usd ?? 0,
          }
          set({ runStats: stats, isRunning: false })
          if (msg.session_id) {
            get().rememberSession(msg.session_id)
          }
        }
      },

      setControls: (patch) =>
        set((state) => ({ controls: { ...state.controls, ...patch } })),

      setSession: (id) => set({ currentSessionId: id }),

      rememberSession: (id) => {
        const list = get().recentSessions.filter((x) => x !== id)
        list.unshift(id)
        set({ recentSessions: list.slice(0, 20) })
        localStorage.setItem('recentSessions', JSON.stringify(list.slice(0, 20)))
      },

      setRunning: (running) => set({ isRunning: running }),

      clearSession: () => set({ 
        currentSessionId: null, 
        initMeta: null, 
        runStats: null,
        isRunning: false 
      }),
    }),
    {
      name: 'claude-session-storage',
      partialize: (state) => ({
        controls: state.controls,
        recentSessions: state.recentSessions,
      }),
    }
  )
)
