import React from 'react'
import { Search, Clock, Star, FolderGit2, MessageSquare } from 'lucide-react'

type SessionItem = {
  id: string
  title: string
  subtitle?: string
  updated: string
  pinned?: boolean
}

const demo: SessionItem[] = [
  { id: 's-1', title: 'LLM Function Calling and Web Search Workflow', subtitle: '4Hosts · Workspace', updated: '2h ago', pinned: true },
  { id: 's-2', title: 'MCP VSCode Extension parity tasks', subtitle: 'Personal · Notes', updated: 'Yesterday' },
  { id: 's-3', title: 'Claude Code SDK explorations', subtitle: 'Playground', updated: '2 days ago' },
  { id: 's-4', title: 'Terminal renderer refactor plan', subtitle: 'Draft', updated: 'Aug 3' },
]

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-3 py-2 text-[11px] tracking-wide uppercase text-[color:var(--text-muted)]/70">
      {children}
    </div>
  )
}

function Item({ item }: { item: SessionItem }) {
  return (
    <button
      className="group w-full text-left px-3 py-2.5 hover:bg-white/5 focus:bg-white/5 rounded-[10px] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
      aria-label={`Open session ${item.title}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 grid h-6 w-6 flex-shrink-0 place-items-center rounded-md border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)] text-white/80">
          <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-[13px] text-white/95">{item.title}</p>
            {item.pinned && (
              <Star className="h-3.5 w-3.5 text-[color:var(--color-primary)]" aria-label="Pinned" />
            )}
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-[11px] text-[color:var(--text-muted)]">
            {item.subtitle ? (
              <>
                <FolderGit2 className="h-3 w-3 opacity-80" aria-hidden="true" />
                <span className="truncate">{item.subtitle}</span>
              </>
            ) : null}
            <span className="mx-1 opacity-50">•</span>
            <Clock className="h-3 w-3 opacity-80" aria-hidden="true" />
            <span>{item.updated}</span>
          </div>
        </div>
      </div>
    </button>
  )
}

export default function SessionsPane() {
  const [query, setQuery] = React.useState('')

  const list = React.useMemo(() => {
    if (!query.trim()) return demo
    const q = query.toLowerCase()
    return demo.filter(
      (d) => d.title.toLowerCase().includes(q) || d.subtitle?.toLowerCase().includes(q)
    )
  }, [query])

  const pinned = list.filter((i) => i.pinned)
  const recent = list.filter((i) => !i.pinned)

  return (
    <div className="flex h-full flex-col">
      <div className="sticky top-0 z-10 border-b border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-tertiary) 92%, transparent)]/95 backdrop-blur-sm">
        <div className="flex items-center justify-between px-3 py-2">
          <div className="flex items-center gap-2 text-[13px] text-[color:var(--color-primary)]">
            <span className="font-semibold">Library</span>
          </div>
        </div>
        <div className="px-3 pb-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-white/50" aria-hidden="true" />
            <input
              aria-label="Search sessions"
              className="w-full rounded-lg border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)] py-2 pl-8 pr-3 text-[13px] text-white/90 outline-none placeholder:text-white/40 focus:ring-2 focus:ring-[color:var(--color-primary)]"
              placeholder="Search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-2">
        {pinned.length > 0 && (
          <div className="mb-2">
            <SectionHeader>Pinned</SectionHeader>
            <div className="space-y-1 px-2">
              {pinned.map((p) => (
                <Item key={p.id} item={p} />
              ))}
            </div>
          </div>
        )}

        <div className="mb-2">
          <SectionHeader>Recent</SectionHeader>
          <div className="space-y-1 px-2">
            {recent.map((r) => (
              <Item key={r.id} item={r} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}