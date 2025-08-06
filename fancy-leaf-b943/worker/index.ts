interface QueryBody {
  prompt: string
  outputFormat?: 'text' | 'json' | 'stream-json'
  sessionId?: string
  maxTurns?: number
  permissionMode?: string
  verbose?: boolean
  systemPrompt?: string
  appendSystemPrompt?: string
  allowedTools?: string[]
  disallowedTools?: string[]
}

export default {
  async fetch(request) {
    const url = new URL(request.url)

    // CORS headers for development
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    }

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders })
    }

    // Stream endpoint for terminal
    if (url.pathname === '/api/stream' && request.method === 'POST') {
      try {
        const body: any = await request.json()
        const prompt = body.prompt || ''
        
        // Mock streaming response with ANSI colors
        const encoder = new TextEncoder()
        const stream = new ReadableStream({
          async start(controller) {
            // Simulate different types of responses based on prompt
            const responses = prompt.toLowerCase().includes('help') 
              ? [`Available commands:\n• help - Show this help\n• test - Run tests\n• clear - Clear terminal\n`]
              : [
                  `\x1b[35m🔧 Tool:\x1b[0m Analyzing request for: ${prompt}\n`,
                  `\x1b[32m✓\x1b[0m Operation completed successfully\n`,
                  `\x1b[90mTelemetry: ${Math.floor(Math.random() * 100)}ms | Tokens: ${Math.floor(Math.random() * 500)}\x1b[0m\n`
                ]
            
            // Stream each character with small delay for effect
            for (const response of responses) {
              for (let i = 0; i < response.length; i += 3) {
                const chunk = response.slice(i, i + 3)
                controller.enqueue(encoder.encode(`data: ${chunk}\n\n`))
                await new Promise(resolve => setTimeout(resolve, 10))
              }
            }
            
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
          },
        })

        return new Response(stream, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        })
      } catch (error) {
        return Response.json(
          { error: 'Invalid request' },
          { status: 400, headers: corsHeaders }
        )
      }
    }

    // Query endpoint - main Claude Code interaction
    if (url.pathname === '/api/query' && request.method === 'POST') {
      try {
        const body: QueryBody = await request.json()
        
        // For now, return a mock streaming response
        // In production, this would call the Claude Code SDK or spawn a process
        const encoder = new TextEncoder()
        const stream = new ReadableStream({
          async start(controller) {
            // Send init message
            const init = {
              type: 'system',
              subtype: 'init',
              model: 'claude-3-opus-20240229',
              cwd: '/workspace',
              tools: ['file_read', 'file_write', 'bash'],
              mcp_servers: [],
              permissionMode: body.permissionMode || 'default',
              session_id: body.sessionId || crypto.randomUUID(),
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(init)}\n\n`))

            // Simulate assistant response
            await new Promise(resolve => setTimeout(resolve, 500))
            const assistant = {
              type: 'assistant',
              content: `I received your prompt: "${body.prompt}". This is a mock response from the Cloudflare Worker. In production, this would connect to the Claude Code SDK.`,
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(assistant)}\n\n`))

            // Send result
            await new Promise(resolve => setTimeout(resolve, 200))
            const result = {
              type: 'result',
              subtype: 'success',
              session_id: body.sessionId || init.session_id,
              num_turns: 1,
              duration_ms: 700,
              duration_api_ms: 500,
              total_cost_usd: 0.0001,
            }
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(result)}\n\n`))
            controller.close()
          },
        })

        return new Response(stream, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        })
      } catch (error) {
        return Response.json(
          { error: 'Invalid request body' },
          { status: 400, headers: corsHeaders }
        )
      }
    }

    // Interrupt endpoint
    if (url.pathname === '/api/interrupt' && request.method === 'POST') {
      // In production, this would signal the running Claude process
      return Response.json(
        { ok: true },
        { status: 202, headers: corsHeaders }
      )
    }

    // Sessions endpoint
    if (url.pathname === '/api/sessions' && request.method === 'GET') {
      // In production, this would return actual session history
      return Response.json(
        { sessions: [] },
        { headers: corsHeaders }
      )
    }

    // Health check
    if (url.pathname === '/api/health') {
      return Response.json(
        { status: 'ok', timestamp: new Date().toISOString() },
        { headers: corsHeaders }
      )
    }

    return new Response('Not Found', { status: 404, headers: corsHeaders })
  },
} satisfies ExportedHandler<Env>
