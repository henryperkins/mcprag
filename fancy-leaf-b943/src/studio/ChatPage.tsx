import React from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import MessageList, { type Message } from './MessageList'
import Composer from './Composer'
import { streamQuery } from './stream'

export default function ChatPage() {
  // Apply dark theme on mount
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark')
    document.documentElement.classList.add('dark')
  }, [])
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
        background: 'radial-gradient(1200px 600px at 50% -200px, rgba(124,58,237,0.12), transparent)',
      }}
    >
      <div className="ribbon" aria-hidden="true" />
      <Sidebar />
      <div className="pl-14">
        <TopBar />
        <main>
          <MessageList messages={messages} />
        </main>
        <Composer onSend={handleSend} />
      </div>
    </div>
  )
}
