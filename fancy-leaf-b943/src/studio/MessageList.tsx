import { memo } from 'react'
import CodeCard, { type CodeCardProps } from './CodeCard'
import AnsiText from '../components/AnsiText'

export type Message =
  | { role: 'user'; content: string }
  | { role: 'assistant'; content: string; cards?: CodeCardProps[] }

function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div className="mx-auto max-w-4xl px-5 py-6 space-y-6">
      {messages.map((m, i) => (
        <div key={i} className="space-y-4">
          {m.role === 'user' ? (
            <article className="rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] p-5">
              <h4 className="text-sm font-medium text-[color:var(--text-muted)] mb-2">You</h4>
              <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
            </article>
          ) : (
            <article className="rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] p-5">
              <h4 className="text-sm font-medium text-[color:var(--text-muted)] mb-2">Claude</h4>
              <p className="whitespace-pre-wrap leading-relaxed">
                <AnsiText text={m.content} useWorker workerThreshold={1500} />
              </p>
            </article>
          )}
          {m.role === 'assistant' && m.cards?.map((c, idx) => <CodeCard key={idx} {...c} />)}
        </div>
      ))}
    </div>
  )
}

export default memo(MessageList)
