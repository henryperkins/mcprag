import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type HistoryStore = {
  itemsBySession: Record<string, string[]>
  indexBySession: Record<string, number>
  
  push: (prompt: string, sessionId: string) => void
  prev: (sessionId: string) => string | null
  next: (sessionId: string) => string | null
  reset: (sessionId: string) => void
}

export const useHistory = create<HistoryStore>()(
  persist(
    (set, get) => ({
      itemsBySession: {},
      indexBySession: {},

      push: (prompt, sessionId) => {
        const items = get().itemsBySession[sessionId] || []
        const filtered = items.filter((i) => i !== prompt)
        const next = [prompt, ...filtered].slice(0, 100)
        set((state) => ({
          itemsBySession: { ...state.itemsBySession, [sessionId]: next },
          indexBySession: { ...state.indexBySession, [sessionId]: -1 },
        }))
      },

      prev: (sessionId) => {
        const items = get().itemsBySession[sessionId] || []
        const currentIdx = get().indexBySession[sessionId] ?? -1
        const nextIdx = currentIdx + 1
        
        if (nextIdx >= items.length) return null
        
        set((state) => ({
          indexBySession: { ...state.indexBySession, [sessionId]: nextIdx },
        }))
        
        return items[nextIdx] || null
      },

      next: (sessionId) => {
        const items = get().itemsBySession[sessionId] || []
        const currentIdx = get().indexBySession[sessionId] ?? -1
        const nextIdx = currentIdx - 1
        
        if (nextIdx < -1) return null
        
        set((state) => ({
          indexBySession: { ...state.indexBySession, [sessionId]: nextIdx },
        }))
        
        return nextIdx === -1 ? '' : items[nextIdx] || null
      },

      reset: (sessionId) => {
        set((state) => ({
          indexBySession: { ...state.indexBySession, [sessionId]: -1 },
        }))
      },
    }),
    {
      name: 'claude-history-storage',
      partialize: (state) => ({
        itemsBySession: Object.fromEntries(
          Object.entries(state.itemsBySession).slice(-10)
        ),
      }),
    }
  )
)