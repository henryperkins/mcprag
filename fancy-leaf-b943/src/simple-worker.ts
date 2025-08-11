/**
 * Simple Cloudflare Worker for Claude Code Gateway
 * Proxies requests to bridge server via SSE
 */

export interface Env {
  BRIDGE_URL: string;
  DB: D1Database;
  KV: KVNamespace;
  FILES: R2Bucket;
  JOBS: Queue;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    // Command discovery proxy
    if (url.pathname === '/api/commands' && request.method === 'GET') {
      const target = (env.BRIDGE_URL || 'http://localhost:8787/api/claude/stream')
        .replace(/\/api\/claude\/stream$/, '/api/commands');
      const upstream = await fetch(target + url.search, { headers: { 'Accept': 'application/json' } });
      return new Response(upstream.body, {
        status: upstream.status,
        headers: { ...corsHeaders, 'Content-Type': upstream.headers.get('Content-Type') || 'application/json' },
      });
    }

    // Health check
    if (url.pathname === '/api/health') {
      return new Response(JSON.stringify({
        status: 'healthy',
        timestamp: Date.now(),
        bridge: env.BRIDGE_URL || 'not configured',
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    
    // Main proxy endpoint
    if ((url.pathname === '/api/claude/stream' || url.pathname === '/api/query') && request.method === 'POST') {
      try {
        const body = await request.json();
        
        // Forward to bridge
        const bridgeUrl = env.BRIDGE_URL || 'http://localhost:8787/exec';
        const bridgeResponse = await fetch(bridgeUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': request.headers.get('Authorization') || '',
          },
          body: JSON.stringify(body),
        });
        
        if (!bridgeResponse.ok) {
          return new Response(`Bridge error: ${bridgeResponse.status}`, {
            status: bridgeResponse.status,
            headers: corsHeaders,
          });
        }
        
        // Stream the response
        return new Response(bridgeResponse.body, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        });
      } catch (error) {
        console.error('Proxy error:', error);
        return new Response(JSON.stringify({
          error: error instanceof Error ? error.message : 'Proxy error',
        }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }
    
    // Session management
    if (url.pathname === '/api/session/create' && request.method === 'POST') {
      const sessionId = crypto.randomUUID();
      
      // Store in D1
      try {
        await env.DB.prepare(`
          INSERT OR IGNORE INTO sessions (id, created_at, metadata)
          VALUES (?, datetime('now'), ?)
        `).bind(sessionId, JSON.stringify({
          userAgent: request.headers.get('User-Agent'),
          ip: request.headers.get('CF-Connecting-IP'),
        })).run();
      } catch (e) {
        console.error('D1 error:', e);
      }
      
      return new Response(JSON.stringify({ sessionId }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    
    // Load transcript
    if (url.pathname === '/api/transcript/load' && request.method === 'GET') {
      const sessionId = url.searchParams.get('sessionId');
      
      if (!sessionId) {
        return new Response('Missing sessionId', {
          status: 400,
          headers: corsHeaders,
        });
      }
      
      try {
        const result = await env.DB.prepare(`
          SELECT content FROM messages WHERE session_id = ? ORDER BY created_at
        `).bind(sessionId).all();
        
        return new Response(JSON.stringify(result.results), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      } catch (e) {
        console.error('D1 error:', e);
        return new Response('Database error', {
          status: 500,
          headers: corsHeaders,
        });
      }
    }
    
    // Save transcript
    if (url.pathname === '/api/transcript/save' && request.method === 'POST') {
      try {
        const { sessionId, content, type } = await request.json();
        
        await env.DB.prepare(`
          INSERT INTO messages (session_id, content, type, created_at)
          VALUES (?, ?, ?, datetime('now'))
        `).bind(sessionId, content, type || 'message').run();
        
        return new Response('OK', { headers: corsHeaders });
      } catch (e) {
        console.error('D1 error:', e);
        return new Response('Save error', {
          status: 500,
          headers: corsHeaders,
        });
      }
    }
    
    return new Response('Not found', {
      status: 404,
      headers: corsHeaders,
    });
  },
};
