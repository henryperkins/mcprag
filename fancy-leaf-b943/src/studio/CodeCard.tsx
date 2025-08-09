import { useMemo, useRef, useState } from 'react'
import { Copy, Check } from 'lucide-react'

export type CodeCardProps = {
  title: string
  subtitle?: string
  language?: string
  code: string
}

export default function CodeCard({ title, subtitle, language = 'text', code }: CodeCardProps) {
  const [copied, setCopied] = useState(false)
  const timeoutRef = useRef<number | null>(null)
  const langLabel = useMemo(() => language.toLowerCase(), [language])

  return (
    <section className="rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] backdrop-blur-sm shadow-sm overflow-hidden">
      <header className="flex items-center justify-between px-5 py-3 border-b border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)]">
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-white/95 truncate">{title}</h3>
          {subtitle ? <p className="text-xs text-[color:var(--text-muted)] truncate">{subtitle}</p> : null}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wide text-[color:var(--text-muted)] border border-[color:var(--border-faint)] rounded px-2 py-1">
            {langLabel}
          </span>
          <button
            type="button"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(code)
                setCopied(true)
                if (timeoutRef.current) window.clearTimeout(timeoutRef.current)
                timeoutRef.current = window.setTimeout(() => setCopied(false), 1400)
              } catch {}
            }}
            className="inline-flex items-center gap-1 rounded-md border border-[color:var(--border-faint)] px-3 py-1.5 text-xs text-white/90 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-white/20"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </header>
      <div className="relative">
        <pre className="m-0 overflow-auto code-scroll text-[13px] leading-[1.55] p-5 font-mono text-white/95 bg-[color:var(--bg-elevated)]" aria-label="code">
          <code>{code}</code>
        </pre>
      </div>
    </section>
  )
}
