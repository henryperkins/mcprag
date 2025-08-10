import React from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import MessageList, { type Message } from './MessageList'
import type { CodeCardProps } from './CodeCard'
import Composer from './Composer'
import { streamQuery } from './stream'
import SessionsPane from './SessionsPane'
import StatusBar from './StatusBar'
import { useAutoScrollNearBottom } from '../hooks/useAutoScrollNearBottom'
import { useSession } from '../store/session.state'
import type { SlashCommand } from '../components/SlashMenu'

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

  const [isStreaming, setStreaming] = React.useState(false)
  const abortRef = React.useRef<() => void>(() => {})
  const sessionIdRef = React.useRef<string | null>(null)
  const sess = useSession()
  const bufferRef = React.useRef<string[]>([])
  const rAFRef = React.useRef<number | null>(null)
  const mainRef = React.useRef<HTMLDivElement | null>(null)
  useAutoScrollNearBottom(mainRef, [messages], 80)

  // Load dynamic slash commands from Worker → Bridge
  const [slashCommands, setSlashCommands] = React.useState<SlashCommand[]>([])
  React.useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const r = await fetch('/api/commands?includeContent=1')
        if (!r.ok) throw new Error('failed to load commands')
        const data = await r.json() as { commands?: Array<{ command: string; description: string; content?: string }> }
        if (!mounted) return
        const cmds: SlashCommand[] = (data.commands || []).map(c => ({ command: c.command, description: c.description || '', content: c.content }))
        setSlashCommands(cmds)
      } catch {
        // ignore
      }
    })()
    return () => { mounted = false }
  }, [])

  async function expandSlashIfNeeded(input: string): Promise<string> {
    const raw = input.trim()
    if (!raw.startsWith('/')) return input
    const firstSpace = raw.indexOf(' ')
    const cmdName = (firstSpace === -1 ? raw : raw.slice(0, firstSpace)).trim()
    const args = firstSpace === -1 ? '' : raw.slice(firstSpace + 1)
    // Prefer server-side expansion to support !`bash` and @file
    try {
      const r = await fetch('/api/commands/expand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: cmdName,
          args,
          allowedTools: sess.controls.allowedTools,
        }),
      })
      if (r.ok) {
        const data = await r.json() as { expanded?: string }
        if (data?.expanded) return data.expanded
      }
    } catch {}
    // Fallback: local expand if server not available
    const match = slashCommands.find(c => c.command === cmdName)
    if (!match || !match.content) return input
    const body = match.content
    const expanded = body.includes('$ARGUMENTS') ? body.replaceAll('$ARGUMENTS', args) : [body, args].filter(Boolean).join('\n')
    return expanded
  }

  async function handleSend(text: string) {
    const expanded = await expandSlashIfNeeded(text)
    setMessages((prev) => [...prev, { role: 'user', content: expanded }])
    setStreaming(true)
    try { sess.setRunning(true) } catch {}

    const flush = () => {
      rAFRef.current = null
      const chunks = bufferRef.current
      if (!chunks.length) return
      const appended = chunks.join('\n') + '\n'
      bufferRef.current = []
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        const content = last?.role === 'assistant' && last.content.startsWith('[streaming]')
          ? last.content + appended
          : '[streaming]\n' + appended
        if (last?.role === 'assistant' && last.content.startsWith('[streaming]')) {
          return [...prev.slice(0, -1), { ...last, content }]
        }
        return [...prev, { role: 'assistant', content }]
      })
    }

    const scheduleFlush = () => {
      if (rAFRef.current != null) return
      rAFRef.current = requestAnimationFrame(flush)
    }

    const { abort, promise } = streamQuery(expanded, {
      onStart: (sid) => { sessionIdRef.current = sid },
      onInit: (payload) => { try { sess.setInit(payload) } catch {} },
      onResult: (payload) => { try { sess.setResult(payload) } catch {} },
      onToolCall: (payload) => {
        const title = payload?.toolName ? `Tool: ${payload.toolName}` : 'Tool Call'
        const code = payload?.toolArguments ? JSON.stringify(payload.toolArguments, null, 2) : ''
        const card: CodeCardProps = {
          title,
          subtitle: payload?.toolId ? `id: ${payload.toolId}` : undefined,
          language: 'json',
          code,
        }
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant') {
            const cards = [...(last.cards || []), card]
            return [...prev.slice(0, -1), { ...last, cards }]
          }
          return [...prev, { role: 'assistant', content: '', cards: [card] }]
        })
      },
      onToolOutput: (payload) => {
        const title = payload?.toolName ? `Result: ${payload.toolName}` : 'Tool Result'
        const raw = payload?.toolResult
        const code = typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2)
        const card: CodeCardProps = {
          title,
          subtitle: payload?.toolId ? `id: ${payload.toolId}` : undefined,
          language: 'json',
          code,
        }
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant') {
            const cards = [...(last.cards || []), card]
            return [...prev.slice(0, -1), { ...last, cards }]
          }
          return [...prev, { role: 'assistant', content: '', cards: [card] }]
        })
      },
      onMessage: (chunk) => {
        bufferRef.current.push(chunk)
        scheduleFlush()
      },
      onDone: () => {
        // ensure last chunks render
        flush()
        setStreaming(false)
        sess.setRunning(false)
      },
      onError: () => {
        bufferRef.current = []
        if (rAFRef.current) cancelAnimationFrame(rAFRef.current)
        rAFRef.current = null
        setStreaming(false)
        sess.setRunning(false)
      },
    }, { 
      sessionId: sessionIdRef.current ?? sess.currentSessionId ?? undefined,
      model: sess.controls.model,
      maxTurns: sess.controls.maxTurns,
      permissionMode: sess.controls.permissionMode,
      verbose: sess.controls.verbose,
      systemPrompt: sess.controls.systemPrompt,
      appendSystemPrompt: sess.controls.appendSystemPrompt,
      allowedTools: sess.controls.allowedTools,
      disallowedTools: sess.controls.disallowedTools,
      mcpConfig: sess.controls.mcpConfig,
      permissionPromptTool: sess.controls.permissionPromptTool,
      continueSession: Boolean(sessionIdRef.current ?? sess.currentSessionId),
    })
    abortRef.current = abort
    await promise
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
          <main id="main" tabIndex={-1} ref={mainRef} className="overflow-y-auto">
            <MessageList messages={messages} />
          </main>
          <StatusBar messages={messages} />
          <Composer 
            onSend={handleSend}
            isStreaming={isStreaming}
            onCancel={() => {
              try { 
                // Try server-side interrupt first if we have a session id
                const sid = sessionIdRef.current
                if (sid) {
                  fetch('/api/interrupt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sessionId: sid })
                  }).catch(() => { /* ignore */ })
                }
                abortRef.current?.()
              } catch {}
              setStreaming(false)
              sess.setRunning(false)
            }}
            onClear={() => { setMessages([]); sessionIdRef.current = null; sess.clearSession() }}
            commands={slashCommands}
          />
        </div>
      </div>
    </div>
  )
}
