import { create } from 'zustand'

export type ToolCallState = {
  callId: string
  name: string
  args?: unknown
  startedAt: number
  progress?: number
  total?: number
  message?: string
  status: 'running' | 'success' | 'error'
  endedAt?: number
}

export type Toast = {
  id: string
  kind: 'info' | 'success' | 'error' | 'warning'
  title: string
  body?: string
  duration?: number
}

type ToolCallStore = {
  active: Record<string, ToolCallState>
  toasts: Toast[]
  ribbonCount: number
  
  startTool: (call: Omit<ToolCallState, 'startedAt' | 'status'>) => void
  updateProgress: (callId: string, patch: Partial<ToolCallState>) => void
  finishTool: (callId: string, success: boolean, body?: string) => void
  pushToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
  clearTools: () => void
}

export const useToolCalls = create<ToolCallStore>((set, get) => ({
  active: {},
  toasts: [],
  ribbonCount: 0,

  startTool: (call) => {
    const toolCall: ToolCallState = {
      ...call,
      startedAt: Date.now(),
      status: 'running',
    }
    
    set((state) => ({
      active: { ...state.active, [call.callId]: toolCall },
      ribbonCount: state.ribbonCount + 1,
    }))
    
    get().pushToast({
      kind: 'info',
      title: `Running ${call.name}`,
      body: call.args ? JSON.stringify(call.args, null, 2).slice(0, 100) : undefined,
      duration: 3000,
    })
  },

  updateProgress: (callId, patch) => {
    set((state) => {
      const current = state.active[callId]
      if (!current) return state
      
      return {
        active: {
          ...state.active,
          [callId]: { ...current, ...patch },
        },
      }
    })
  },

  finishTool: (callId, success, body) => {
    const current = get().active[callId]
    if (!current) return

    const updated: ToolCallState = {
      ...current,
      status: success ? 'success' : 'error',
      endedAt: Date.now(),
    }

    set((state) => ({
      active: { ...state.active, [callId]: updated },
    }))

    // Auto-remove after a delay
    setTimeout(() => {
      set((state) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [callId]: removed, ...rest } = state.active
        return {
          active: rest,
          ribbonCount: Math.max(0, state.ribbonCount - 1),
        }
      })
    }, 800)

    // Show completion toast
    get().pushToast({
      kind: success ? 'success' : 'error',
      title: `${current.name} ${success ? 'completed' : 'failed'}`,
      body: body?.slice(0, 200),
      duration: success ? 4000 : 6000,
    })
  },

  pushToast: (toast) => {
    const id = crypto.randomUUID()
    const fullToast: Toast = { ...toast, id }
    
    set((state) => ({
      toasts: [...state.toasts, fullToast],
    }))
    
    // Auto-remove after duration
    if (toast.duration) {
      setTimeout(() => {
        get().removeToast(id)
      }, toast.duration)
    }
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },

  clearTools: () => {
    set({ active: {}, ribbonCount: 0 })
  },
}))