export type StreamHandlers = {
  onMessage: (text: string) => void
  onDone?: () => void
  onError?: (e: unknown) => void
}

/**
 * Stream line-delimited text from /api/query.
 * The backend is expected to stream newline-terminated chunks.
 */
export async function streamQuery(prompt: string, handlers: StreamHandlers) {
  try {
    const resp = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, outputFormat: 'stream-json' }),
    })

    if (!resp.body) throw new Error('No response body')

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()

    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // Split on newlines and emit complete lines
      let idx
      while ((idx = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, idx).trim()
        buffer = buffer.slice(idx + 1)
        if (!line) continue
        handlers.onMessage(line)
      }
    }

    // Flush any remaining buffer content as a final message
    const last = buffer.trim()
    if (last) handlers.onMessage(last)

    handlers.onDone?.()
  } catch (e) {
    handlers.onError?.(e)
  }
}