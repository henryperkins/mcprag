import React from 'react'
import { Timer, Gauge, Coins } from 'lucide-react'
import type { Message } from './MessageList'

export default function StatusBar({ messages }: { messages: Message[] }) {
  const tokens = React.useMemo(() => {
    const chars = messages.reduce((acc, m) => acc + (m.content?.length || 0), 0)
    return Math.max(0, Math.ceil(chars / 4))
  }, [messages])

  const turns = React.useMemo(() => {
    return messages.filter(m => m.role === 'user' || m.role === 'assistant').length
  }, [messages])

  return (
    <div className="mx-auto max-w-4xl px-5 py-2 text-xs text-[color:var(--text-muted)] border-t border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-primary) 85%, transparent)]">
      <div className="flex items-center gap-5">
        <span className="inline-flex items-center gap-1.5"><Gauge className="h-3.5 w-3.5 opacity-80" /> {turns} turns</span>
        <span className="inline-flex items-center gap-1.5"><Coins className="h-3.5 w-3.5 opacity-80" /> ~{tokens.toLocaleString()} tok</span>
        <span className="inline-flex items-center gap-1.5"><Timer className="h-3.5 w-3.5 opacity-80" /> live</span>
      </div>
    </div>
  )
}