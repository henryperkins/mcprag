import express from 'express'
import cors from 'cors'
import crypto from 'node:crypto'
import fs from 'node:fs/promises'
import path from 'node:path'
import os from 'node:os'
import { exec as execCb } from 'node:child_process'
import { promisify } from 'node:util'
import { query, type QueryMessage } from '@anthropic-ai/claude-code'
import 'dotenv/config'

const app = express()
app.use(cors())
app.use(express.json())

// Broaden to align with various SDK builds
type PermissionMode =
  | 'acceptEdits'
  | 'plan'
  | 'ask'
  | 'auto'
  | 'acceptAll'
  | 'confirmAll'
  | 'bypassPermissions'
  | (string & {})
interface ClaudeRequestBody {
  prompt: string
  sessionId?: string
  options?: {
    systemPrompt?: string
    appendSystemPrompt?: string
    maxTurns?: number
    allowedTools?: string[]
    disallowedTools?: string[]
    continueSession?: boolean
    resumeSessionId?: string
    cwd?: string
    permissionMode?: PermissionMode
    verbose?: boolean
    model?: string
    mcpConfig?: string
    permissionPromptTool?: string
  }
}

const exec = promisify(execCb)

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

// Discover slash commands from project and user scope
app.get('/api/commands', async (req, res) => {
  const includeContent = String(req.query.includeContent || req.query.include || '') === '1'
  const cwd = (typeof req.query.cwd === 'string' && req.query.cwd.length > 0)
    ? req.query.cwd
    : process.cwd()

  const roots = [
    { root: path.resolve(cwd, '.claude/commands'), scope: 'project' as const },
    { root: path.join(os.homedir(), '.claude/commands'), scope: 'user' as const },
  ]

  type Cmd = { command: string; description: string; args?: string; scope: string; content?: string }
  const results: Cmd[] = []

  // Recursively walk a directory and accumulate command files
  async function walk(dir: string, relBase = ''): Promise<string[]> {
    const out: string[] = []
    let entries: import('node:fs').Dirent[] = []
    try { entries = await fs.readdir(dir, { withFileTypes: true }) } catch { return out }
    for (const ent of entries) {
      const full = path.join(dir, ent.name)
      const rel = path.join(relBase, ent.name)
      if (ent.isDirectory()) {
        const nested = await walk(full, rel)
        out.push(...nested)
        continue
      }
      if (ent.isFile() && ent.name.toLowerCase().endsWith('.md')) {
        out.push(rel)
      }
    }
    return out
  }

  // Parse very simple YAML-ish frontmatter: key: value until the closing ---
  function parseFrontmatter(src: string): { front: Record<string, string>; body: string } {
    const lines = src.split(/\r?\n/)
    if (lines[0]?.trim() !== '---') return { front: {}, body: src }
    const front: Record<string, string> = {}
    let i = 1
    for (; i < lines.length; i++) {
      const line = lines[i]
      if (line.trim() === '---') { i++; break }
      const m = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/)
      if (m) front[m[1].trim()] = m[2].trim()
    }
    const body = lines.slice(i).join('\n')
    return { front, body }
  }

  for (const { root, scope } of roots) {
    try {
      const stat = await fs.stat(root).catch(() => null)
      if (!stat || !stat.isDirectory()) continue

      const files = await walk(root)
      for (const rel of files) {
        const filePath = path.join(root, rel)
        let content = ''
        try { content = await fs.readFile(filePath, 'utf8') } catch {}

        const { front, body } = parseFrontmatter(content)
        const ns = path.dirname(rel).replaceAll('\\', '/').split('/').filter(Boolean).join(':')
        const base = path.basename(rel, path.extname(rel))
        const command = `/${ns ? ns + ':' : ''}${base}`

        let description = ''
        const scan = (front.description || body).split(/\r?\n/)
        for (const line of scan) {
          const trimmed = line.trim()
          if (!trimmed) continue
          description = trimmed.replace(/^#+\s*/, '').slice(0, 200)
          break
        }

        const args = front['argument-hint'] || undefined
        const entry: Cmd = {
          command,
          description: description || `Command ${base}`,
          scope,
          ...(args ? { args } : {}),
          ...(includeContent ? { content: body } : {}),
        }
        results.push(entry)
      }
    } catch {
      // ignore per root
    }
  }

  // Sort: project-scope first, then by command name
  results.sort((a, b) => (a.scope === b.scope ? a.command.localeCompare(b.command) : a.scope === 'project' ? -1 : 1))
  res.json({ commands: results })
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
  // Accept both current shape { prompt, options } and legacy { text, opts }
  const body = req.body as any
  const prompt: string | undefined = body?.prompt ?? body?.text
  const rawId: string | undefined = body?.sessionId
  const options: ClaudeRequestBody['options'] | undefined = body?.options ?? body?.opts
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
        appendSystemPrompt: options?.appendSystemPrompt,
        maxTurns: options?.maxTurns ?? 3,
        allowedTools: options?.allowedTools ?? ['Bash', 'Read', 'WebSearch', 'Edit', 'Write'],
        disallowedTools: options?.disallowedTools,
        continueSession: options?.continueSession ?? false,
        // If provided, resume explicit session
        // @ts-expect-error: option may not be in older SDK typings
        resumeSessionId: options?.resumeSessionId,
        // @ts-expect-error: model option may be supported in newer SDKs
        model: options?.model,
        cwd: options?.cwd ?? process.cwd(),
        permissionMode: options?.permissionMode ?? 'acceptEdits',
        verbose: options?.verbose ?? false,
        // @ts-expect-error: newer SDKs support MCP config
        mcpConfig: options?.mcpConfig,
        // @ts-expect-error: newer SDKs support permission prompt tool
        permissionPromptTool: options?.permissionPromptTool,
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

// Provide a simple alias for clients posting to /api/query
app.post('/api/query', (req, res) => {
  // Delegate to /api/claude/stream to keep a single implementation
  // Express doesn't easily re-route to a handler, so call it directly
  // by modifying url and delegating through a fetch-like call is overkill; reuse logic
  // Here we simply forward to the same handler by reusing req/res
  // Note: this relies on the shared implementation above
  ;(app._router as any).handle({ ...req, url: '/api/claude/stream', method: 'POST' }, res, () => {})
})

// Expand a slash command: resolve $ARGUMENTS, execute allowed pre-exec bash (!`cmd`), and inline @file references
app.post('/api/commands/expand', async (req, res) => {
  type ExpandReq = {
    command: string // e.g. "/frontend:component" or "/security-review"
    args?: string
    cwd?: string
    allowedTools?: string[]
  }
  const body = (req.body || {}) as ExpandReq
  const name = String(body.command || '').trim().replace(/^\//, '')
  if (!name) return res.status(400).json({ error: 'command required' })
  const args = body.args ?? ''
  const cwd = body.cwd && body.cwd.length ? body.cwd : process.cwd()
  const sessionAllowed = Array.isArray(body.allowedTools) ? body.allowedTools : []

  // Locate the command file under project or user scope
  const relPath = name.replaceAll(':', path.sep) + '.md'
  const candidates = [
    path.resolve(cwd, '.claude/commands', relPath),
    path.join(os.homedir(), '.claude/commands', relPath),
  ]
  let content = ''
  let front: Record<string, string> = {}
  try {
    let found = ''
    for (const p of candidates) {
      try {
        const st = await fs.stat(p)
        if (st.isFile()) { found = p; break }
      } catch {}
    }
    if (!found) return res.status(404).json({ error: 'command_not_found' })
    const raw = await fs.readFile(found, 'utf8')
    ;({ front, body: content } = (function parseFrontmatterLocal(src: string) {
      const lines = src.split(/\r?\n/)
      if (lines[0]?.trim() !== '---') return { front: {}, body: src }
      const f: Record<string, string> = {}
      let i = 1
      for (; i < lines.length; i++) {
        const line = lines[i]
        if (line.trim() === '---') { i++; break }
        const m = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/)
        if (m) f[m[1].trim()] = m[2].trim()
      }
      const body = lines.slice(i).join('\n')
      return { front: f, body }
    })(raw))
  } catch (e) {
    return res.status(500).json({ error: (e as Error).message })
  }

  // Replace $ARGUMENTS
  let expanded = content.includes('$ARGUMENTS') ? content.replaceAll('$ARGUMENTS', args) : (args ? content + '\n' + args : content)

  // Prepare allowed Bash specs: prefer command frontmatter allowed-tools, fall back to session allowed
  const fromFront = (front['allowed-tools'] || front['allowed_tools'] || '').split(/[\n,]/).map(s => s.trim()).filter(Boolean)
  const combinedAllowed = [...fromFront, ...sessionAllowed]
  const bashAny = combinedAllowed.some(s => /^Bash\s*$/i.test(s))
  const bashSpecs = combinedAllowed
    .map(s => {
      const m = s.match(/^Bash\((.+)\)$/i)
      return m ? m[1].trim() : null
    })
    .filter(Boolean) as string[]

  const globToRegex = (glob: string) => {
    const esc = glob.replace(/[.+^${}()|\[\]\\]/g, '\\$&').replace(/\*/g, '.*')
    return new RegExp(`^${esc}$`)
  }
  const isCmdAllowed = (cmd: string) => {
    if (bashAny) return true
    for (const spec of bashSpecs) {
      try {
        if (globToRegex(spec).test(cmd)) return true
      } catch {}
    }
    return false
  }

  // Execute !`cmd` snippets
  const execMatches: Array<{ match: string; cmd: string; out: string }> = []
  const execRe = /!`([^`]+)`/g
  let m: RegExpExecArray | null
  const seen = new Set<string>()
  while ((m = execRe.exec(expanded))) {
    const cmd = m[1].trim()
    const match = m[0]
    if (seen.has(match)) continue
    seen.add(match)
    if (!isCmdAllowed(cmd)) {
      execMatches.push({ match, cmd, out: `[[permission denied: ${cmd}]]` })
      continue
    }
    try {
      const { stdout } = await exec(cmd, { cwd, timeout: 15000, maxBuffer: 2 * 1024 * 1024 })
      execMatches.push({ match, cmd, out: stdout.trimEnd() })
    } catch (e) {
      const err = e as any
      const msg = err?.stderr?.toString?.() || err?.message || String(e)
      execMatches.push({ match, cmd, out: `[[error running ${cmd}: ${msg.replace(/\n+/g, ' ').slice(0, 500)}]]` })
    }
  }
  for (const it of execMatches) {
    // Inline output – if multiline, keep as-is; consumer will render markdown
    expanded = expanded.replaceAll(it.match, it.out)
  }

  // Inline @file references
  const fileRe = /(^|\s)@([A-Za-z0-9_./\-]+)(?=\s|$)/g
  const fileMatches: Array<{ match: string; full: string; path: string; block: string }> = []
  let fm: RegExpExecArray | null
  while ((fm = fileRe.exec(expanded))) {
    const full = fm[0]
    const rel = fm[2]
    const abs = path.resolve(cwd, rel)
    try {
      const stat = await fs.stat(abs)
      if (!stat.isFile()) continue
      const data = await fs.readFile(abs, 'utf8')
      const ext = path.extname(rel).replace(/^\./, '')
      const codeFenceLang = ext.length <= 12 ? ext : ''
      const block = `\n\n\`\`\`${codeFenceLang}\n// file: ${rel}\n${data}\n\`\`\`\n\n`
      fileMatches.push({ match: full, full, path: rel, block })
    } catch {
      // silently skip missing files
    }
  }
  for (const it of fileMatches) {
    // Replace the whole token with block; preserve leading whitespace from match
    const lead = it.match.startsWith(' ') ? ' ' : ''
    expanded = expanded.replace(it.match, lead + it.block)
  }

  return res.json({ expanded })
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
