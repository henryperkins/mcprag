import React from 'react'
import { renderAnsiToSpans } from '../utils/ansi'

export type AnsiToken = { text: string; classes: string[] }

type Props = {
  text: string
  useWorker?: boolean
  workerThreshold?: number // min length to offload to worker
}

export default function AnsiText({ text, useWorker = true, workerThreshold = 2000 }: Props) {
  const [tokens, setTokens] = React.useState<AnsiToken[] | null>(null)
  const workerRef = React.useRef<Worker | null>(null)

  React.useEffect(() => {
    if (!useWorker || text.length < workerThreshold) {
      setTokens(null)
      return
    }
    if (!workerRef.current) {
      workerRef.current = new Worker(new URL('../workers/ansiWorker.ts', import.meta.url), { type: 'module' })
      workerRef.current.onmessage = (e: MessageEvent<AnsiToken[]>) => {
        setTokens(e.data)
      }
    }
    workerRef.current.postMessage(text)
    return () => {
      // keep worker for component lifetime; do not terminate on every update
    }
  }, [text, useWorker, workerThreshold])

  React.useEffect(() => () => { workerRef.current?.terminate(); workerRef.current = null }, [])

  if (tokens) {
    return (
      <>
        {tokens.map((t, i) => (
          <span key={i} className={t.classes.length ? t.classes.join(' ') : undefined}>{t.text}</span>
        ))}
      </>
    )
  }
  // Fallback to synchronous renderer for small strings or when worker disabled
  return <>{renderAnsiToSpans(text)}</>
}

