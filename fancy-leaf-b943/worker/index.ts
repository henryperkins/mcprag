// Note: The @anthropic-ai/claude-code package integration
// This implementation handles both SDK availability and mock responses

interface QueryBody {
  prompt: string
  outputFormat?: 'text' | 'json' | 'stream-json'
  sessionId?: string
  maxTurns?: number
  permissionMode?: 'auto' | 'acceptAll' | 'acceptEdits' | 'confirmAll'
  verbose?: boolean
  systemPrompt?: string
  appendSystemPrompt?: string
  allowedTools?: string[]
  disallowedTools?: string[]
}

// Define environment bindings
export interface Env {
  ANTHROPIC_API_KEY?: string
  MCP_CONFIG?: string // JSON string of MCP servers configuration
  // Optional third-party provider flags
  CLAUDE_CODE_USE_BEDROCK?: string
  CLAUDE_CODE_USE_VERTEX?: string
}

// Track active sessions for interrupt support
const sessionAborters = new Map<string, AbortController>()

// SDK-compatible message types
interface SDKMessage {
  type: 'system' | 'assistant' | 'user' | 'result'
  subtype?: string
  content?: string
  error?: string
  session_id?: string
  model?: string
  cwd?: string
  tools?: string[]
  mcp_servers?: string[]
  permissionMode?: string
  num_turns?: number
  duration_ms?: number
  duration_api_ms?: number
  total_cost_usd?: number
  [key: string]: any // Allow additional properties
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
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

    // Query endpoint - main Claude Code interaction
    if (url.pathname === '/api/query' && request.method === 'POST') {
      try {
        const body: QueryBody = await request.json()
        
        // Check if API key is configured (for production)
        const hasApiKey = !!env.ANTHROPIC_API_KEY
        
        // Parse MCP configuration if provided
        let mcpConfig = undefined
        if (env.MCP_CONFIG) {
          try {
            mcpConfig = JSON.parse(env.MCP_CONFIG)
          } catch (e) {
            console.error('Failed to parse MCP_CONFIG:', e)
          }
        }

        // Create abort controller for this session
        const sessionId = body.sessionId || crypto.randomUUID()
        const abortController = new AbortController()
        sessionAborters.set(sessionId, abortController)

        // Create streaming response
        const encoder = new TextEncoder()
        const stream = new ReadableStream({
          async start(controller) {
            try {
              // Try to use the actual SDK if available
              if (hasApiKey) {
                try {
                  // Dynamic import to handle cases where SDK might not be available
                  const claudeCode = await import('@anthropic-ai/claude-code')
                  
                  // Build options object based on what the SDK accepts
                  const queryOptions: any = {
                    prompt: body.prompt,
                    abortController,
                  }
                  
                  // Add optional parameters that might be supported
                  const options: any = {}
                  if (body.maxTurns !== undefined) options.maxTurns = body.maxTurns
                  if (body.systemPrompt) options.systemPrompt = body.systemPrompt
                  if (body.appendSystemPrompt) options.appendSystemPrompt = body.appendSystemPrompt
                  if (body.allowedTools) options.allowedTools = body.allowedTools
                  if (body.disallowedTools) options.disallowedTools = body.disallowedTools
                  if (body.permissionMode) options.permissionMode = body.permissionMode
                  if (body.verbose !== undefined) options.verbose = body.verbose
                  if (mcpConfig) options.mcpConfig = mcpConfig
                  
                  // Only add options if there are any
                  if (Object.keys(options).length > 0) {
                    queryOptions.options = options
                  }
                  
                  // Use the SDK's query function - it returns an async iterator
                  const queryResult = claudeCode.query(queryOptions)
                  
                  // Stream messages from the async iterator
                  for await (const message of queryResult) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify(message)}\n\n`))
                  }
                } catch (sdkError) {
                  console.error('SDK error:', sdkError)
                  throw new Error('Claude Code SDK error: ' + (sdkError instanceof Error ? sdkError.message : 'Unknown error'))
                }
              } else {
                // Mock response when no API key is configured
                const initMessage: SDKMessage = {
                  type: 'system',
                  subtype: 'init',
                  model: 'claude-3-opus-20240229',
                  cwd: '/workspace',
                  tools: ['file_read', 'file_write', 'bash'],
                  mcp_servers: [],
                  permissionMode: body.permissionMode || 'auto',
                  session_id: sessionId,
                }
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(initMessage)}\n\n`))
                
                await new Promise(resolve => setTimeout(resolve, 500))
                
                const assistantMessage: SDKMessage = {
                  type: 'assistant',
                  content: `[Mock Response] I received your prompt: "${body.prompt}". In production with a valid API key, this would connect to the Claude Code SDK.`,
                  session_id: sessionId,
                }
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(assistantMessage)}\n\n`))
                
                await new Promise(resolve => setTimeout(resolve, 200))
                
                const resultMessage: SDKMessage = {
                  type: 'result',
                  subtype: 'success',
                  session_id: sessionId,
                  num_turns: 1,
                  duration_ms: 700,
                  duration_api_ms: 500,
                  total_cost_usd: 0.0001,
                }
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(resultMessage)}\n\n`))
              }
            } catch (error) {
              // Send error as result message
              const errorMessage: SDKMessage = {
                type: 'result',
                subtype: 'error_during_execution',
                error: error instanceof Error ? error.message : 'Unknown error occurred',
                session_id: sessionId,
              }
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(errorMessage)}\n\n`))
            } finally {
              // Clean up session aborter
              sessionAborters.delete(sessionId)
              controller.close()
            }
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
        console.error('Request error:', error)
        return Response.json(
          { error: 'Invalid request body' },
          { status: 400, headers: corsHeaders }
        )
      }
    }

    // Interrupt endpoint
    if (url.pathname === '/api/interrupt' && request.method === 'POST') {
      try {
        const body = await request.json() as { sessionId?: string }
        
        if (body.sessionId && sessionAborters.has(body.sessionId)) {
          const aborter = sessionAborters.get(body.sessionId)
          aborter?.abort()
          sessionAborters.delete(body.sessionId)
          
          return Response.json(
            { ok: true, message: 'Session interrupted' },
            { status: 202, headers: corsHeaders }
          )
        }
        
        return Response.json(
          { ok: false, message: 'Session not found' },
          { status: 404, headers: corsHeaders }
        )
      } catch (error) {
        return Response.json(
          { error: 'Invalid request' },
          { status: 400, headers: corsHeaders }
        )
      }
    }

    // Sessions endpoint
    if (url.pathname === '/api/sessions' && request.method === 'GET') {
      // Return active sessions (in production, this might query a database)
      const activeSessions = Array.from(sessionAborters.keys()).map(id => ({
        id,
        active: true,
        timestamp: new Date().toISOString(),
      }))
      
      return Response.json(
        { sessions: activeSessions },
        { headers: corsHeaders }
      )
    }

    // Health check
    if (url.pathname === '/api/health') {
      return Response.json(
        { 
          status: 'ok', 
          timestamp: new Date().toISOString(),
          hasApiKey: !!env.ANTHROPIC_API_KEY,
          hasMcpConfig: !!env.MCP_CONFIG,
        },
        { headers: corsHeaders }
      )
    }

    // Legacy stream endpoint (for backward compatibility)
    if (url.pathname === '/api/stream' && request.method === 'POST') {
      // Redirect to /api/query
      const body = await request.json() as any
      return fetch(new URL('/api/query', url.origin), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: body.prompt || '',
          outputFormat: 'stream-json'
        }),
      })
    }

    return new Response('Not Found', { status: 404, headers: corsHeaders })
  },
} satisfies ExportedHandler<Env>