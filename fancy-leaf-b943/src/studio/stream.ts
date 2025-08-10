export type StreamHandlers = {
  onMessage: (text: string) => void
  onDone?: () => void
  onError?: (e: unknown) => void
  onStart?: (sessionId: string) => void
  onInit?: (payload: any) => void
  onResult?: (payload: any) => void
  onToolCall?: (payload: any) => void
  onToolOutput?: (payload: any) => void
}

export type StreamOptions = {
  signal?: AbortSignal
}

/**
 * Stream line-delimited text from /api/query.
 * The backend is expected to stream newline-terminated chunks.
 */
export function streamQuery(
  prompt: string,
  handlers: StreamHandlers,
  options?: StreamOptions & { sessionId?: string; model?: string }
) {
  const controller = new AbortController()
  const signal = options?.signal ?? controller.signal

  const promise = (async () => {
    try {
      const resp = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Forward body expected by Bridge so Worker can proxy directly
        body: JSON.stringify({
          prompt,
          sessionId: options?.sessionId,
          options: {
            continueSession: Boolean(options?.sessionId),
            resumeSessionId: options?.sessionId,
            model: options?.model,
          },
        }),
        signal,
      })

      if (!resp.body) throw new Error('No response body')

      // Parse SSE stream: expect lines like `event: message` and `data: {...}`
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()

      let buffer = ''
      let currentEvent: string | null = null

      const emitText = (text: string) => {
        if (text) handlers.onMessage(text)
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let idx
        while ((idx = buffer.indexOf('\n')) !== -1) {
          const raw = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 1)
          const line = raw.trimEnd()
          if (!line) continue

          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
            continue
          }
          if (line.startsWith(':')) {
            // comment / heartbeat
            continue
          }
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue
            try {
              const payload = JSON.parse(data)
              const type = payload.type as string | undefined

              if (currentEvent === 'error') {
                throw new Error(payload?.error || 'Stream error')
              }
              if (currentEvent === 'done') {
                continue
              }
              if (currentEvent === 'start') {
                if (payload?.sessionId) handlers.onStart?.(String(payload.sessionId))
              } else if (currentEvent === 'message') {
                switch (type) {
                  case 'system': {
                    if (payload.subtype === 'init') {
                      handlers.onInit?.(payload)
                      const stats = [payload.model, payload.cwd].filter(Boolean).join(' • ')
                      if (stats) emitText(`(${stats})`)
                    }
                    break
                  }
                  case 'assistant': {
                    if (payload.content) emitText(String(payload.content))
                    break
                  }
                  case 'tool-call': {
                    const name = payload.toolName || 'tool'
                    emitText(`\u{1F527} Tool: ${name}`)
                    if (payload.toolArguments) emitText(JSON.stringify(payload.toolArguments, null, 2))
                    handlers.onToolCall?.(payload)
                    break
                  }
                  case 'tool-output': {
                    const out = typeof payload.toolResult === 'string' ? payload.toolResult : JSON.stringify(payload.toolResult, null, 2)
                    emitText(`\u2713 ${out}`)
                    handlers.onToolOutput?.(payload)
                    break
                  }
                  case 'result': {
                    handlers.onResult?.(payload)
                    if (payload.content) emitText(String(payload.content))
                    const meta: string[] = []
                    if (payload.duration_ms) meta.push(`${payload.duration_ms}ms`)
                    if (payload.total_cost_usd) meta.push(`$${Number(payload.total_cost_usd).toFixed(4)}`)
                    if (payload.num_turns) meta.push(`${payload.num_turns} turns`)
                    if (meta.length) emitText(`Telemetry: ${meta.join(' | ')}`)
                    break
                  }
                  default: {
                    // Unknown message type; emit raw JSON to help debug
                    emitText(typeof payload === 'string' ? payload : JSON.stringify(payload))
                  }
                }
              }
            } catch (e) {
              // If parsing fails, surface raw line for visibility
              emitText(line)
            }
            continue
          }
        }
      }

      handlers.onDone?.()
    } catch (e: any) {
      if (e?.name === 'AbortError' || signal.aborted) return
      handlers.onError?.(e)
    }
  })()

  return {
    abort: () => controller.abort(),
    promise,
  }
}
