import { create } from 'zustand'

export type ContentBlock = 
  | { type: 'text'; text: string }
  | { type: 'tool_use'; id: string; name: string; input: unknown }
  | { type: 'tool_result'; tool_use_id: string; content?: unknown; is_error?: boolean }

export type SDKMessage = 
  | {
      type: 'system'
      subtype: 'init'
      model: string
      cwd: string
      tools: string[]
      mcp_servers?: Array<{ name: string; status: string }>
      permissionMode: string
      session_id?: string
      apiKeySource?: string
    }
  | {
      type: 'user'
      content: string | ContentBlock[]
    }
  | {
      type: 'assistant'
      content: string | ContentBlock[]
    }
  | {
      type: 'result'
      subtype: 'success' | 'error_max_turns' | 'error_during_execution' | 'interrupted'
      session_id?: string
      duration_ms?: number
      duration_api_ms?: number
      num_turns?: number
      total_cost_usd?: number
      error?: string
      stderr?: string
      exit_code?: number
    }
  | {
      type: 'tool_call'
      call_id: string
      name: string
      arguments?: unknown
    }
  | {
      type: 'tool_result'
      call_id: string
      content?: unknown
      is_error?: boolean
    }
  | {
      type: 'chunk'
      data: string
    }

type MessagesStore = {
  messages: SDKMessage[]
  isStreaming: boolean
  
  addMessage: (message: SDKMessage) => void
  clearMessages: () => void
  setStreaming: (streaming: boolean) => void
  updateLastMessage: (update: Partial<SDKMessage>) => void
}

export const useMessages = create<MessagesStore>((set) => ({
  messages: [],
  isStreaming: false,

  addMessage: (message) => {
    set((state) => ({
      messages: [...state.messages, message],
    }))
  },

  clearMessages: () => {
    set({ messages: [] })
  },

  setStreaming: (streaming) => {
    set({ isStreaming: streaming })
  },

  updateLastMessage: (update) => {
    set((state) => {
      const messages = [...state.messages]
      if (messages.length > 0) {
        const last = messages[messages.length - 1]
        messages[messages.length - 1] = { ...last, ...update } as SDKMessage
      }
      return { messages }
    })
  },
}))