import { useMemo, useRef, useState } from 'react'
import { Copy, Check, Download } from 'lucide-react'

export type CodeCardProps = {
  title: string
  subtitle?: string
  language?: string
  code: string
}

function getExtForLanguage(lang?: string) {
  const l = (lang || '').toLowerCase()
  if (l.includes('typescript') || l === 'ts') return 'ts'
  if (l.includes('tsx')) return 'tsx'
  if (l.includes('javascript') || l === 'js') return 'js'
  if (l.includes('python') || l === 'py') return 'py'
  if (l.includes('json')) return 'json'
  if (l.includes('bash') || l === 'sh' || l.includes('shell')) return 'sh'
  if (l.includes('html')) return 'html'
  if (l.includes('css')) return 'css'
  if (l.includes('yaml') || l.includes('yml')) return 'yml'
  if (l.includes('docker')) return 'Dockerfile'
  return (l && /^[a-z0-9]+$/.test(l)) ? l : 'txt'
}

export default function CodeCard({ title, subtitle, language = 'text', code }: CodeCardProps) {
  const [copied, setCopied] = useState(false)
  const timeoutRef = useRef<number | null>(null)
  const langLabel = useMemo(() => language.toLowerCase(), [language])

  const fileName = useMemo(() => {
    const base = (title || 'snippet').replace(/[^\w.-]+/g, '_').slice(0, 64) || 'snippet'
    const ext = getExtForLanguage(language)
    return base.endsWith(`.${ext}`) ? base : `${base}.${ext}`
  }, [title, language])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current)
      timeoutRef.current = window.setTimeout(() => setCopied(false), 1400)
    } catch {
      // noop
    }
  }

  const handleDownload = () => {
    try {
      const blob = new Blob([code], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      // noop
    }
  }

  return (
    <section className="rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] backdrop-blur-sm shadow-sm overflow-hidden">
      <header className="flex items-center justify-between px-5 py-3 border-b border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)]">
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-white/95 truncate" title={title}>{title}</h3>
          {subtitle ? <p className="text-xs text-[color:var(--text-muted)] truncate" title={subtitle}>{subtitle}</p> : null}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wide text-[color:var(--text-muted)] border border-[color:var(--border-faint)] rounded px-2 py-1">
            {langLabel}
          </span>
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1 rounded-md border border-[color:var(--border-faint)] px-3 py-1.5 text-xs text-white/90 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-white/20"
            aria-label={copied ? 'Code copied to clipboard' : 'Copy code to clipboard'}
            title={copied ? 'Copied' : 'Copy'}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center gap-1 rounded-md border border-[color:var(--border-faint)] px-3 py-1.5 text-xs text-white/90 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-white/20"
            aria-label={`Download ${fileName}`}
            title={`Download ${fileName}`}
          >
            <Download className="h-3.5 w-3.5" />
            Download
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
