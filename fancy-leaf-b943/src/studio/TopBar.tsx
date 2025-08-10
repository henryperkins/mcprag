import { Share2, ChevronDown } from 'lucide-react'

export default function TopBar() {
  return (
    <header className="sticky top-0 z-20 border-b border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-primary) 80%, transparent)] backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-5 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
            <span className="truncate">4Hosts</span>
            <span>•</span>
            <span className="truncate">LLM Function Calling and Web Search Workflow</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-3 py-1.5 text-sm text-white/90 hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="Share"
          >
            <Share2 className="h-4 w-4" />
            Share
          </button>
          <button
            className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-3 py-1.5 text-sm text-white/85 hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="Model selector"
          >
            Claude Opus 4
            <ChevronDown className="h-4 w-4 opacity-80" />
          </button>
        </div>
      </div>
    </header>
  )
}
