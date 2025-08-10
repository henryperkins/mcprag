/**
 * Cloudflare Workers Gateway for Claude Code
 * Handles SSE streaming, session coordination, and persistence
 */

import type {} from './worker-types.d.ts'

// Environment bindings
export interface Env {
  // Configuration
  BRIDGE_URL: string; // Your Claude Code bridge endpoint (via Tunnel)
  ANTHROPIC_API_KEY?: string; // Optional if using bridge
  R2_PUBLIC_BASE?: string; // Public domain base for R2 (e.g. https://claude-r2.lakefrontdigital.io/user-assets)

  // Durable Objects
  SESSION: DurableObjectNamespace;

  // Storage bindings
  DB: D1Database;
  sessions_kv: KVNamespace;
  FILES: R2Bucket;
  JOBS: Queue;

  // Security
  TURNSTILE_SECRET?: string;
  ACCESS_JWT_SECRET?: string;
}

// Session Durable Object for coordination
export class SessionDO {
  private connections: Set<WebSocket> = new Set();
  private history: unknown[] = [];
  private activeToolCalls: Map<string, unknown> = new Map();

  constructor(state: DurableObjectState, env: Env) {
    // Store state and env as needed
    void state;
    void env;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    switch (url.pathname) {
      case '/ws':
        return this.handleWebSocket();
        
      case '/append':
        return this.appendMessage(request);
        
      case '/history':
        return this.getHistory();
        
      case '/tools':
        return this.getToolCalls();
        
      default:
        return new Response('Not found', { status: 404 });
    }
  }
  
  private async handleWebSocket(): Promise<Response> {
    // WebSocket upgrade would be handled here in production
    // For now, return a placeholder response
    return new Response(JSON.stringify({
      type: 'history',
      data: this.history
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  private async appendMessage(request: Request): Promise<Response> {
    const message = await request.json();
    const timestamp = Date.now();
    
    // Store in DO state
    // Store in memory for now - would use DO storage in production
    // await this.env.storage.put(`msg:${timestamp}`, message);
    this.history.push({ ...message, timestamp });
    
    // Broadcast to all connected clients
    const broadcast = JSON.stringify({
      type: 'message',
      data: message,
      timestamp
    });
    
    for (const ws of this.connections) {
      try {
        ws.send(broadcast);
      } catch {
        this.connections.delete(ws);
      }
    }
    
    return new Response('OK');
  }
  
  private async getHistory(): Promise<Response> {
    // Return from memory - would use DO storage in production
    const messages = this.history;
    return Response.json(messages);
  }
  
  private async getToolCalls(): Promise<Response> {
    return Response.json(Array.from(this.activeToolCalls.values()));
  }
}

// Main Worker
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    
    // CORS headers for development
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': 'true',
    };
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    try {
      // Route handlers
      switch (url.pathname) {
        case '/api/claude/stream':
          return await this.handleClaudeStream(request, env, ctx, corsHeaders);
          
        case '/api/session/create':
          return await this.createSession(request, env, corsHeaders);
          
        case '/api/session/connect':
          return await this.connectSession(request, env, corsHeaders);
          
        case '/api/transcript/save':
          return await this.saveTranscript(request, env, corsHeaders);
          
        case '/api/transcript/load':
          return await this.loadTranscript(request, env, corsHeaders);
          
        case '/api/files/upload':
          return await this.uploadFile(request, env, corsHeaders);
          
        case '/api/health':
          return new Response(JSON.stringify({ 
            status: 'healthy',
            timestamp: Date.now(),
            bridge: env.BRIDGE_URL ? 'configured' : 'missing'
          }), { 
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
          
        default:
          return new Response('Not found', { status: 404, headers: corsHeaders });
      }
    } catch (error) {
      console.error('Worker error:', error);
      return new Response(JSON.stringify({ 
        error: error instanceof Error ? error.message : 'Internal error' 
      }), { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  },
  
  async handleClaudeStream(
    request: Request, 
    env: Env, 
    ctx: ExecutionContext,
    corsHeaders: Record<string, string>
  ): Promise<Response> {
    const body = await request.json();
    const sessionId = body.sessionId || crypto.randomUUID();
    
    // Get or create session DO
    const sessionDO = env.SESSION.get(env.SESSION.idFromName(sessionId));
    
    // Forward to bridge with auth
    const bridgeRequest = new Request(env.BRIDGE_URL || 'http://localhost:8787/api/claude/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('Authorization') || '',
        'X-Session-ID': sessionId,
      },
      body: JSON.stringify(body),
    });
    
    const upstream = await fetch(bridgeRequest);
    
    if (!upstream.ok) {
      return new Response(`Bridge error: ${upstream.status}`, { 
        status: upstream.status,
        headers: corsHeaders 
      });
    }
    
    // Create transform stream for SSE
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const reader = upstream.body!.getReader();
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    
    // Keep-alive interval
    const keepAlive = setInterval(() => {
      writer.write(encoder.encode(':keepalive\n\n')).catch(() => {
        clearInterval(keepAlive);
      });
    }, 20000);
    
    // Process stream and save to DO/D1
    ctx.waitUntil((async () => {
      const chunks: string[] = [];
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          chunks.push(chunk);
          
          // Forward to client
          await writer.write(value);
          
          // Parse SSE messages and save to session
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data && data !== '[DONE]') {
                try {
                  const message = JSON.parse(data);
                  // Append to session DO
                  await sessionDO.fetch(new Request('http://do/append', {
                    method: 'POST',
                    body: JSON.stringify(message),
                  }));
                } catch (e) {
                  console.error('Failed to parse SSE message:', e);
                }
              }
            }
          }
        }
      } finally {
        clearInterval(keepAlive);
        writer.close();
        
        // Save complete transcript to D1
        if (chunks.length > 0) {
          ctx.waitUntil(this.saveToD1(env, sessionId, chunks.join(''), body));
        }
      }
    })());
    
    return new Response(readable, {
      headers: {
        ...corsHeaders,
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  },
  
  async createSession(request: Request, env: Env, corsHeaders: Record<string, string>): Promise<Response> {
    const sessionId = crypto.randomUUID();
    const sessionDO = env.SESSION.get(env.SESSION.idFromName(sessionId));

    // Initialize session in DO
    await sessionDO.fetch(new Request('http://do/append', {
      method: 'POST',
      body: JSON.stringify({
        type: 'session_created',
        sessionId,
        timestamp: Date.now(),
      }),
    }));

    // Persist session metadata in KV for quick lookups (30 days TTL)
    const kvKey = `session:${sessionId}`;
    await env.sessions_kv.put(
      kvKey, 
      JSON.stringify({
        createdAt: Date.now(),
        userAgent: request.headers.get('User-Agent'),
        ip: request.headers.get('CF-Connecting-IP'),
      }),
      { expirationTtl: 60 * 60 * 24 * 30 }
    );

    // Store session metadata in D1 using Sessions API for strong consistency
    const s = env.DB.session();
    try {
      await s.exec('BEGIN');
      await s.prepare(`
        INSERT INTO sessions (id, created_at, metadata)
        VALUES (?, datetime('now'), ?)
      `).bind(sessionId, JSON.stringify({
        userAgent: request.headers.get('User-Agent'),
        ip: request.headers.get('CF-Connecting-IP'),
      })).run();
      await s.exec('COMMIT');
    } catch (e) {
      try { await s.exec('ROLLBACK'); } catch {}
      throw e;
    } finally {
      await s.close();
    }

    // Set cookie for client session
    const cookie = `sid=${sessionId}; Path=/; HttpOnly; SameSite=Lax`;
    return new Response(JSON.stringify({ sessionId }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json', 'Set-Cookie': cookie },
    });
  },
  
  async connectSession(request: Request, env: Env, corsHeaders: Record<string, string>): Promise<Response> {
    const url = new URL(request.url);
    const sessionId = url.searchParams.get('sessionId');
    
    if (!sessionId) {
      return new Response('Missing sessionId', { status: 400, headers: corsHeaders });
    }
    
    // Upgrade to WebSocket for real-time updates
    const upgradeHeader = request.headers.get('Upgrade');
    if (!upgradeHeader || upgradeHeader !== 'websocket') {
      return new Response('Expected WebSocket', { status: 426, headers: corsHeaders });
    }
    
    const sessionDO = env.SESSION.get(env.SESSION.idFromName(sessionId));
    return sessionDO.fetch(new Request('http://do/ws', {
      headers: request.headers,
    }));
  },
  
  async saveTranscript(request: Request, env: Env, corsHeaders: Record<string, string>): Promise<Response> {
    const { sessionId, messages } = await request.json();

    const s = env.DB.session();
    try {
      await s.exec('BEGIN');
      await s.prepare(`
        INSERT INTO transcripts (session_id, messages, created_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(session_id) DO UPDATE SET
          messages = ?,
          updated_at = datetime('now')
      `).bind(sessionId, JSON.stringify(messages), JSON.stringify(messages)).run();
      await s.exec('COMMIT');
    } catch (e) {
      try { await s.exec('ROLLBACK'); } catch {}
      throw e;
    } finally {
      await s.close();
    }

    // Enqueue async job for further processing
    await env.JOBS.send({
      type: 'index_transcript',
      sessionId,
      length: Array.isArray(messages) ? messages.length : undefined,
      ts: Date.now(),
    });

    return new Response('OK', { headers: corsHeaders });
  },
  
  async loadTranscript(request: Request, env: Env, corsHeaders: Record<string, string>): Promise<Response> {
    const url = new URL(request.url);
    const sessionId = url.searchParams.get('sessionId');

    const s = env.DB.session();
    try {
      if (!sessionId) {
        // List recent sessions (consistent snapshot)
        const result = await s.prepare(`
          SELECT id, created_at,
                 json_extract(metadata, '$.prompt') as first_prompt
          FROM sessions
          ORDER BY created_at DESC
          LIMIT 20
        `).all<{ id: string; created_at: string; first_prompt: string | null }>();

        return new Response(JSON.stringify(result.results), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      // Load specific transcript
      const result = await s.prepare(`
        SELECT messages FROM transcripts
        WHERE session_id = ?
      `).bind(sessionId).first<{ messages?: string }>();

      if (!result || !result.messages) {
        return new Response('Not found', { status: 404, headers: corsHeaders });
      }

      return new Response(result.messages, {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    } finally {
      await s.close();
    }
  },
  
  async uploadFile(request: Request, env: Env, corsHeaders: Record<string, string>): Promise<Response> {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const sessionId = formData.get('sessionId') as string;
    
    if (!file) {
      return new Response('No file provided', { status: 400, headers: corsHeaders });
    }
    
    const key = `${sessionId}/${Date.now()}-${file.name}`;
    await env.FILES.put(key, file.stream(), {
      httpMetadata: {
        contentType: file.type,
      },
      customMetadata: {
        sessionId,
        originalName: file.name,
        uploadedAt: new Date().toISOString(),
      },
    });
    
    // Generate signed URL for access (1 hour expiry)
    const signedUrl = await env.FILES.createSignedUrl(key, { expiresIn: 3600 });
    // Public custom-domain URL (if configured): https://claude-r2.lakefrontdigital.io/user-assets/<key>
    const publicUrl = env.R2_PUBLIC_BASE
      ? `${env.R2_PUBLIC_BASE.replace(/\/$/, '')}/${encodeURIComponent(key)}`
      : undefined;

    // Enqueue async job for file post-processing
    await env.JOBS.send({
      type: 'file_uploaded',
      sessionId,
      key,
      size: file.size,
      contentType: file.type,
      ts: Date.now(),
    });
    
    return new Response(JSON.stringify({
      key,
      url: publicUrl ?? signedUrl,
      signedUrl,
      size: file.size,
      type: file.type,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  },
  
  async saveToD1(env: Env, sessionId: string, transcript: string, metadata: unknown): Promise<void> {
    const s = env.DB.session();
    try {
      await s.exec('BEGIN');
      await s.prepare(`
        INSERT INTO messages (session_id, content, metadata, created_at)
        VALUES (?, ?, ?, datetime('now'))
      `).bind(
        sessionId,
        transcript,
        JSON.stringify(metadata)
      ).run();
      await s.exec('COMMIT');
    } catch (error) {
      try { await s.exec('ROLLBACK'); } catch {}
      console.error('Failed to save to D1:', error);
    } finally {
      await s.close();
    }
  },

  // Cloudflare Queues consumer: process async jobs (indexing, post-processing)
  async queue(batch: MessageBatch<any>): Promise<void> {
    for (const msg of batch.messages) {
      try {
        const data = msg.body as any;
        switch (data?.type) {
          case 'index_transcript':
            // TODO: implement indexing/analytics; placeholder no-op
            break;
          case 'file_uploaded':
            // TODO: generate thumbnails/scan/etc.; placeholder no-op
            break;
          default:
            // Unknown job type; ignore
            break;
        }
        await msg.ack?.();
      } catch (e) {
        // Let platform retry this message
        await msg.retry?.();
      }
    }
  },
};