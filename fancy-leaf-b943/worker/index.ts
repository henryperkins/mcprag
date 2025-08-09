export interface Env {
  BRIDGE_URL: string
}

// Build CORS headers dynamically to support local dev origins
const makeCorsHeaders = (req: Request): Record<string, string> => {
  const origin = req.headers.get('origin') || ''
  let allowOrigin = '*'
  try {
    if (
      origin && (
        origin.startsWith('http://localhost') ||
        origin.startsWith('http://127.0.0.1') ||
        origin.endsWith('.workers.dev') ||
        origin === 'https://claude-worker.lakefrontdigital.io'
      )
    ) {
      allowOrigin = origin
    }
  } catch {
    // ignore parsing errors; fall back to '*'
  }
  return {
    'access-control-allow-origin': allowOrigin,
    'access-control-allow-headers': 'content-type',
    'access-control-allow-methods': 'POST, GET, OPTIONS',
  }
}

const json = (req: Request, data: unknown, init: ResponseInit = {}) => {
  const headers = {
    'content-type': 'application/json',
    ...makeCorsHeaders(req),
    ...(init.headers || {})
  }
  return new Response(JSON.stringify(data), { status: 200, ...init, headers })
}

const sseProxy = async (req: Request, env: Env) => {
  // forward POST body to the bridge and pipe SSE back
  const bridge = new URL(env.BRIDGE_URL) // e.g. http://localhost:8787/api/claude/stream
  const init: RequestInit = {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: await req.text(),
  }
  const upstream = await fetch(bridge.toString(), init)

  if (!upstream.ok || !upstream.body) {
    return json(req, { error: `Bridge error: ${upstream.status}` }, { status: 502 })
  }

  // stream back to client
  const { readable, writable } = new TransformStream()
  upstream.body.pipeTo(writable) // zero-copy in Workers

  // Preserve SSE headers with CORS
  return new Response(readable, {
    status: 200,
    headers: {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache',
      'x-accel-buffering': 'no',
      'connection': 'keep-alive',
      ...makeCorsHeaders(req)
    },
  })
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url)

    // Handle OPTIONS preflight requests for CORS
    if (url.pathname.startsWith('/api/') && req.method === 'OPTIONS') {
      return new Response(null, { headers: makeCorsHeaders(req) })
    }

    // Health -> map to bridge /api/health
    if (url.pathname === '/api/health' && req.method === 'GET') {
      try {
        const r = await fetch(new URL('/api/health', new URL(env.BRIDGE_URL).origin).toString())
        return json(req, await r.json(), { status: r.status })
      } catch {
        return json(req, { status: 'down' }, { status: 502 })
      }
    }

    // Streamed query -> proxy to bridge SSE
    if (url.pathname === '/api/query' && req.method === 'POST') {
      return sseProxy(req, env)
    }

    // Interrupt -> forward to bridge
    if (url.pathname === '/api/interrupt' && req.method === 'POST') {
      const r = await fetch(new URL('/api/interrupt', new URL(env.BRIDGE_URL).origin).toString(), {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: await req.text(),
      })
      return json(req, await r.json(), { status: r.status })
    }

    // Sessions -> forward to bridge
    if (url.pathname === '/api/sessions' && req.method === 'GET') {
      const r = await fetch(new URL('/api/sessions', new URL(env.BRIDGE_URL).origin).toString())
      return json(req, await r.json(), { status: r.status })
    }

    // Fallback to static asset handling (SPA mode configured in wrangler.jsonc)
    return new Response(null, { status: 404 })
  },
}
