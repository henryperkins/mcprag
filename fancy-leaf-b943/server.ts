import express from 'express'
import cors from 'cors'
import crypto from 'node:crypto'
import { query, type QueryMessage } from '@anthropic-ai/claude-code'
import 'dotenv/config'

const app = express()
app.use(cors())
app.use(express.json())

type PermissionMode = 'acceptEdits' | 'plan' | 'ask'
interface ClaudeRequestBody {
  prompt: string
  sessionId?: string
  options?: {
    systemPrompt?: string
    maxTurns?: number
    allowedTools?: string[]
    continueSession?: boolean
    cwd?: string
    permissionMode?: PermissionMode
    verbose?: boolean
  }
}

if (!process.env.ANTHROPIC_API_KEY) {
  // Fail fast so you notice during dev
  console.warn('⚠️  ANTHROPIC_API_KEY not set. Set it in .dev.vars (dev) or via wrangler secret.')
}

// Track live streams so we can interrupt
const sessions = new Map<
  string,
  { ended: boolean; end: () => void; abort?: AbortController }
>()

// Unified health
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', service: 'claude-code-bridge' })
})

// Minimal active sessions list
app.get('/api/sessions', (_req, res) => {
  res.json({ active: Array.from(sessions.keys()) })
})

// Interrupt by sessionId
app.post('/api/interrupt', (req, res) => {
  const { sessionId } = (req.body ?? {}) as { sessionId?: string }
  if (!sessionId) return res.status(400).json({ error: 'sessionId required' })
  const sess = sessions.get(sessionId)
  if (!sess) return res.status(404).json({ error: 'no such session' })
  try {
    sess.abort?.abort()
    sess.end()
    sessions.delete(sessionId)
    return res.json({ ok: true, interrupted: sessionId })
  } catch (e) {
    return res.status(500).json({ error: (e as Error).message })
  }
})

// Main SSE endpoint used by the Worker
app.post('/api/claude/stream', async (req, res) => {
  const { prompt, sessionId: rawId, options } = req.body as ClaudeRequestBody
  if (typeof prompt !== 'string' || !prompt.length) {
    return res.status(400).json({ error: 'prompt required' })
  }

  const sessionId = rawId ?? crypto.randomUUID()

  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.setHeader('X-Accel-Buffering', 'no')

  const send = (event: string, data: unknown) => {
    res.write(`event: ${event}\n`)
    res.write(`data: ${JSON.stringify(data)}\n\n`)
  }

  // Heartbeat to keep proxies from killing the stream
  const hb = setInterval(() => res.write(': hb\n\n'), 15000)

  const abort = new AbortController()
  sessions.set(sessionId, {
    ended: false,
    end: () => {
      if (!res.writableEnded) res.end()
      clearInterval(hb)
    },
    abort,
  })

  try {
    send('start', { sessionId })

    const iterable = query({
      prompt,
      options: {
        systemPrompt: options?.systemPrompt,
        maxTurns: options?.maxTurns ?? 3,
        allowedTools: options?.allowedTools ?? ['Bash', 'Read', 'WebSearch', 'Edit', 'Write'],
        continueSession: options?.continueSession ?? false,
        cwd: options?.cwd ?? process.cwd(),
        permissionMode: options?.permissionMode ?? 'acceptEdits',
        verbose: options?.verbose ?? false,
      },
      // Some builds of the SDK may ignore AbortController; this is best-effort.
      // @ts-expect-error: signal may not be typed in older versions
      signal: abort.signal,
    })

    let count = 0
    for await (const m of iterable as AsyncIterable<QueryMessage>) {
      count++
      send('message', { sessionId, ...m })
    }

    send('done', { sessionId, complete: true, messageCount: count })
  } catch (error) {
    send('error', {
      sessionId,
      error: error instanceof Error ? error.message : 'Unknown error',
    })
  } finally {
    const s = sessions.get(sessionId)
    s?.end()
    sessions.delete(sessionId)
  }
})

// Legacy simple health (kept for docs/scripts that call /health)
app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'claude-code-bridge' }))

const PORT = process.env.CLAUDE_BRIDGE_PORT || 8787
app.listen(PORT, () => {
  console.log(`🤖 Bridge on http://localhost:${PORT}`)
  console.log(`   Health:  GET /api/health`)
  console.log(`   Stream:  POST /api/claude/stream`)
  console.log(`   Sessions GET /api/sessions`)
  console.log(`   Interrupt POST /api/interrupt`)
})