import React from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import MessageList, { type Message } from './MessageList'
import Composer from './Composer'
import { streamQuery } from './stream'
import SessionsPane from './SessionsPane'
import StatusBar from './StatusBar'

export default function ChatPage() {
  // Apply dark theme on mount
  React.useEffect(() => {
    const stored = (localStorage.getItem('theme') as 'light' | 'dark' | 'system' | null) ?? 'system'
    const resolve = (mode: 'light' | 'dark' | 'system') =>
      mode === 'system'
        ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : mode
    const apply = (mode: 'light' | 'dark' | 'system') => {
      document.documentElement.setAttribute('data-theme', resolve(mode))
      document.documentElement.classList.remove('dark')
    }
    apply(stored as any)

    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      const current = (localStorage.getItem('theme') as 'light' | 'dark' | 'system' | null) ?? 'system'
      if (current === 'system') apply('system')
    }
    if (mq.addEventListener) mq.addEventListener('change', onChange)
    else mq.addListener(onChange)
    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', onChange)
      else mq.removeListener(onChange)
    }
  }, [])

  const [showSessions, setShowSessions] = React.useState(false)

  const [messages, setMessages] = React.useState<Message[]>([
    {
      role: 'assistant',
      content: "Here’s a concise re-org with extracted middleware and a new health router.",
      cards: [
        {
          title: 'utils/middleware.py · Extract all middleware',
          language: 'python',
          code: `from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

async def security_middleware(request: Request, call_next):
    """Block malicious requests early"""
    return await call_next(request)

async def rate_limit_middleware(request: Request, call_next):
    return await call_next(request)
`,
        },
      ],
    },
  ])

  const [, setStreaming] = React.useState(false)

  async function handleSend(text: string) {
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setStreaming(true)

    let assembled = ''
    await streamQuery(text, {
      onMessage: (chunk) => {
        assembled += chunk + '\n'
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant' && last.content.startsWith('[streaming]')) {
            return [...prev.slice(0, -1), { ...last, content: '[streaming]\n' + assembled }]
          }
          return [...prev, { role: 'assistant', content: '[streaming]\n' + assembled }]
        })
      },
      onDone: () => setStreaming(false),
      onError: () => setStreaming(false),
    })
  }

  return (
    <div
      className="app-container scroll-smooth"
      style={{
        background: 'radial-gradient(1200px 600px at 50% -200px, rgba(var(--primary-rgb), 0.12), transparent)',
      }}
    >
      <div className="ribbon" aria-hidden="true" />
      <Sidebar onToggleSessions={() => setShowSessions((v) => !v)} showSessions={showSessions} />
      <div className="pl-14 flex">
        {showSessions && (
          <aside
            className="hidden md:block w-80 shrink-0 border-r border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-tertiary) 90%, transparent)]/90 backdrop-blur-sm"
            aria-label="Sessions library"
          >
            <SessionsPane />
          </aside>
        )}

        <div className="flex-1 min-w-0 grid grid-rows-[auto,1fr,auto,auto] h-screen">
          <TopBar />
          <main className="overflow-y-auto">
            <MessageList messages={messages} />
          </main>
          <StatusBar messages={messages} />
          <Composer onSend={handleSend} />
        </div>
      </div>
    </div>
  )
}
