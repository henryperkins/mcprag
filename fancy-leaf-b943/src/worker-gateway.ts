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

/**
 * User context for permissions
 */
interface UserContext {
  role: 'admin' | 'developer' | 'viewer' | 'default';
  organization?: string;
  allowedRepositories?: string[];
  userId?: string;
  email?: string;
}

/**
 * Command cache structure
 */
interface CommandCache {
  commands: any[];
  tools: string[];
  timestamp: number;
  ttl: number;
}

// Session Durable Object for coordination
export class SessionDO {
  private connections: Set<WebSocket> = new Set();
  private history: unknown[] = [];
  private activeToolCalls: Map<string, unknown> = new Map();
  private state: DurableObjectState;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    // env param is available but not used directly
    void env;
    
    // Restore state from storage on initialization
    // Using waitUntil pattern for async initialization
    state.waitUntil((async () => {
      const storedHistory = await state.storage.get<unknown[]>('history');
      if (storedHistory) {
        this.history = storedHistory;
      }
      
      const storedToolCalls = await state.storage.get<Map<string, unknown>>('toolCalls');
      if (storedToolCalls) {
        this.activeToolCalls = storedToolCalls;
      }
    })());
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    switch (url.pathname) {
      case '/ws':
        return this.handleWebSocket(request);
        
      case '/append':
        return this.appendMessage(request);
        
      case '/history':
        return this.getHistory();
        
      case '/tools':
        return this.getToolCalls();
        
      case '/clear':
        return this.clearSession();
        
      default:
        return new Response('Not found', { status: 404 });
    }
  }
  
  private async handleWebSocket(request: Request): Promise<Response> {
    // Check if this is a WebSocket upgrade request
    const upgradeHeader = request.headers.get('Upgrade');
    if (!upgradeHeader || upgradeHeader !== 'websocket') {
      return new Response('Expected WebSocket', { status: 426 });
    }

    // Create WebSocket pair
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    // Accept the WebSocket connection
    server.accept();

    // Add to connections set
    this.connections.add(server);

    // Send initial state to new connection
    server.send(JSON.stringify({
      type: 'init',
      history: this.history,
      toolCalls: Array.from(this.activeToolCalls.entries()),
      connectionCount: this.connections.size
    }));

    // Set up ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (server.readyState === 1) { // WebSocket.OPEN = 1
        server.send(JSON.stringify({ type: 'ping' }));
      } else {
        clearInterval(pingInterval);
      }
    }, 30000);

    // Handle incoming messages from client
    server.addEventListener('message', async (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string);
        
        switch (data.type) {
          case 'pong':
            // Client responded to ping
            break;
            
          case 'message':
            // Broadcast message to all connections
            await this.broadcastMessage(data);
            break;
            
          case 'tool_update':
            // Update tool call status
            this.activeToolCalls.set(data.id, data);
            await this.state.storage.put('toolCalls', this.activeToolCalls);
            await this.broadcastToolUpdate(data);
            break;
            
          case 'request_history':
            // Send full history to requesting client
            server.send(JSON.stringify({
              type: 'history',
              data: this.history
            }));
            break;
            
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error handling WebSocket message:', error);
        server.send(JSON.stringify({
          type: 'error',
          message: 'Failed to process message'
        }));
      }
    });

    // Handle connection close
    server.addEventListener('close', () => {
      clearInterval(pingInterval);
      this.connections.delete(server);
      
      // Notify other connections about disconnection
      this.broadcast(JSON.stringify({
        type: 'connection_closed',
        connectionCount: this.connections.size
      }), server);
    });

    // Handle errors
    server.addEventListener('error', (error: Event) => {
      console.error('WebSocket error:', error);
      clearInterval(pingInterval);
      this.connections.delete(server);
    });

    // Return the client WebSocket
    return new Response(null, {
      status: 101,
      webSocket: client,
    } as any);
  }
  
  private async broadcastMessage(message: unknown): Promise<void> {
    const payload = JSON.stringify({
      type: 'message',
      data: message,
      timestamp: Date.now()
    });
    
    this.broadcast(payload);
  }
  
  private async broadcastToolUpdate(toolData: unknown): Promise<void> {
    const payload = JSON.stringify({
      type: 'tool_update',
      data: toolData,
      timestamp: Date.now()
    });
    
    this.broadcast(payload);
  }
  
  private broadcast(message: string, exclude?: WebSocket): void {
    for (const ws of this.connections) {
      if (ws !== exclude && ws.readyState === 1) { // WebSocket.OPEN = 1
        try {
          ws.send(message);
        } catch (error) {
          console.error('Failed to send to WebSocket:', error);
          this.connections.delete(ws);
        }
      }
    }
  }
  
  private async clearSession(): Promise<Response> {
    // Clear all stored data
    this.history = [];
    this.activeToolCalls.clear();
    
    // Clear specific keys from storage
    await this.state.storage.delete('history');
    await this.state.storage.delete('toolCalls');
    
    // Clear all message keys - we'll track them separately if needed
    // For now, just clear the main collections
    // In production, you'd want to track message keys or use a different storage pattern
    
    // Notify all connections
    this.broadcast(JSON.stringify({
      type: 'session_cleared',
      timestamp: Date.now()
    }));
    
    return new Response('Session cleared', { status: 200 });
  }
  
  private async appendMessage(request: Request): Promise<Response> {
    const message = await request.json();
    const timestamp = Date.now();
    
    // Add to history with timestamp
    const messageWithTimestamp = { ...message, timestamp };
    this.history.push(messageWithTimestamp);
    
    // Persist to Durable Object storage
    await this.state.storage.put('history', this.history);
    
    // Store individual message for efficient retrieval
    await this.state.storage.put(`msg:${timestamp}`, messageWithTimestamp);
    
    // Broadcast to all connected clients
    const broadcast = JSON.stringify({
      type: 'message',
      data: message,
      timestamp
    });
    
    this.broadcast(broadcast);
    
    return new Response('OK');
  }
  
  private async getHistory(): Promise<Response> {
    // Return persisted history
    return Response.json(this.history);
  }
  
  private async getToolCalls(): Promise<Response> {
    return Response.json(Array.from(this.activeToolCalls.values()));
  }
}

/**
 * Get tool permissions based on user role
 */
function getToolPermissions(context: UserContext): string[] {
  const baseTools = ['Read', 'WebSearch', 'Grep', 'LS', 'Glob'];
  
  const rolePermissions: Record<UserContext['role'], string[]> = {
    admin: [
      ...baseTools,
      'Write', 'Edit', 'MultiEdit',
      'Bash', 'Git',
      'NotebookEdit', 'TodoWrite',
      'Task', 'ExitPlanMode'
    ],
    developer: [
      ...baseTools,
      'Write', 'Edit', 'MultiEdit',
      'Git', 'TodoWrite',
      'Task'
    ],
    viewer: baseTools,
    default: [...baseTools, 'Edit']
  };
  
  return rolePermissions[context.role] || rolePermissions.default;
}

/**
 * Get allowed commands based on user role
 */
function getCommandPermissions(context: UserContext): string[] {
  const baseCommands = ['/help', '/clear', '/model', '/resume'];
  
  const rolePermissions: Record<UserContext['role'], string[]> = {
    admin: [
      ...baseCommands,
      '/init',
      '/permissions',
      '/ultra-think',
      '/project:*',
      '/mcp:*',
      '/hooks:*',
      '/settings:*'
    ],
    developer: [
      ...baseCommands,
      '/init',
      '/permissions',
      '/project:*',
      '/mcp:*'
    ],
    viewer: baseCommands,
    default: [...baseCommands, '/init']
  };
  
  return rolePermissions[context.role] || rolePermissions.default;
}

/**
 * Filter commands based on user permissions
 */
function filterCommands(commands: any[], context: UserContext): any[] {
  const allowedCommands = getCommandPermissions(context);
  
  return commands.filter(cmd => {
    const cmdName = cmd.name || cmd;
    
    // Check exact match
    if (allowedCommands.includes(cmdName)) {
      return true;
    }
    
    // Check wildcard patterns
    for (const pattern of allowedCommands) {
      if (pattern.endsWith('*')) {
        const prefix = pattern.slice(0, -1);
        if (typeof cmdName === 'string' && cmdName.startsWith(prefix)) {
          return true;
        }
      }
    }
    
    return false;
  });
}

/**
 * Extract user context from request
 */
async function getUserContext(request: Request, env: Env): Promise<UserContext> {
  // Check for JWT token
  const auth = request.headers.get('Authorization');
  if (auth?.startsWith('Bearer ') && env.ACCESS_JWT_SECRET) {
    try {
      // In production, verify JWT and extract claims
      // For now, return default context
      return { role: 'default' };
    } catch {
      // Invalid token
    }
  }
  
  // Check for session cookie
  const cookie = request.headers.get('Cookie');
  if (cookie) {
    const sid = cookie.match(/sid=([^;]+)/)?.[1];
    if (sid) {
      // Look up session in KV
      const sessionData = await env.sessions_kv.get(`session:${sid}`, { type: 'json' }) as any;
      if (sessionData?.role) {
        return {
          role: sessionData.role,
          userId: sessionData.userId,
          email: sessionData.email
        };
      }
    }
  }
  
  // Default context
  return { role: 'default' };
}

/**
 * Get available commands with caching
 */
async function getAvailableCommands(env: Env): Promise<CommandCache> {
  const cacheKey = 'commands_cache';
  const cached = await env.sessions_kv.get<CommandCache>(cacheKey, { type: 'json' });
  
  // Check cache validity (1 hour TTL)
  if (cached && Date.now() - cached.timestamp < 3600000) {
    return cached;
  }
  
  // Fetch from bridge
  const target = (env.BRIDGE_URL || 'http://localhost:8787')
    .replace(/\/api\/claude\/stream$/, '/api/commands');
    
  try {
    const response = await fetch(target, {
      headers: { 'Accept': 'application/json' }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch commands: ${response.status}`);
    }
    
    const data = await response.json() as any;
    
    const cache: CommandCache = {
      commands: data.commands || [],
      tools: data.tools || [],
      timestamp: Date.now(),
      ttl: 3600000
    };
    
    // Store in KV with TTL
    await env.sessions_kv.put(cacheKey, JSON.stringify(cache), {
      expirationTtl: 3600
    });
    
    return cache;
  } catch (error) {
    console.error('Failed to fetch commands:', error);
    
    // Return minimal defaults on error
    return {
      commands: [],
      tools: ['Read', 'Write', 'Edit'],
      timestamp: Date.now(),
      ttl: 60000
    };
  }
}

/**
 * Sanitize and enforce permissions on request
 */
async function enforcePermissions(
  request: Request,
  env: Env
): Promise<any> {
  const body = await request.json() as any;
  
  // Get user context
  const context = await getUserContext(request, env);
  
  // Get allowed tools for this user
  const allowedTools = getToolPermissions(context);
  
  // Filter tools based on permissions
  if (body.opts?.allowedTools) {
    body.opts.allowedTools = body.opts.allowedTools.filter(
      (tool: string) => allowedTools.includes(tool)
    );
  } else if (body.opts) {
    body.opts.allowedTools = allowedTools;
  } else {
    body.opts = { allowedTools };
  }
  
  // Add disallowed patterns for safety
  const disallowedPatterns = [
    'Bash(rm -rf *)',
    'Bash(sudo *)',
    'Bash(chmod 777 *)',
    'Edit(.env)',
    'Write(.env)',
    'Edit(**/.env)',
    'Write(**/.env)',
    'Edit(**/secrets/*)',
    'Write(**/secrets/*)'
  ];
  
  if (!body.opts.disallowedTools) {
    body.opts.disallowedTools = disallowedPatterns;
  } else {
    body.opts.disallowedTools = [
      ...body.opts.disallowedTools,
      ...disallowedPatterns
    ];
  }
  
  // Sanitize input text
  if (body.text && typeof body.text === 'string') {
    body.text = sanitizeInput(body.text);
  }
  
  return body;
}

/**
 * Sanitize user input
 */
function sanitizeInput(input: string): string {
  // Remove potential command injection attempts
  const dangerous = [
    /\$\(.*?\)/g,  // Command substitution
    /`.*?`/g,      // Backticks
    /;\s*rm\s+-rf/g, // Dangerous rm commands
    /\|\|\s*rm/g,   // OR with rm
    /&&\s*rm/g      // AND with rm
  ];
  
  let sanitized = input;
  for (const pattern of dangerous) {
    sanitized = sanitized.replace(pattern, '[SANITIZED]');
  }
  
  // Truncate to reasonable length
  return sanitized.slice(0, 10000);
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
        case '/api/query':
          // Alias to the same SSE handler to match bridge compatibility
          return await this.handleClaudeStream(request, env, ctx, corsHeaders);
        case '/api/commands': {
          // Get cached commands or fetch from bridge
          const commandCache = await getAvailableCommands(env);
          
          // Get user context to filter based on permissions
          const context = await getUserContext(request, env);
          const allowedTools = getToolPermissions(context);
          
          // Filter tools based on user permissions
          const filteredTools = commandCache.tools.filter(
            tool => allowedTools.includes(tool)
          );
          
          // Filter commands based on user permissions
          const filteredCommands = filterCommands(commandCache.commands, context);
          
          return new Response(JSON.stringify({
            commands: filteredCommands,
            tools: filteredTools,
            timestamp: commandCache.timestamp,
            userRole: context.role
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          });
        }
          
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
    // Enforce permissions and sanitize input
    const body = await enforcePermissions(request.clone(), env);
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
