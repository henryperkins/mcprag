import { Plus, Grid2x2, Settings } from 'lucide-react'

export default function Sidebar() {
  return (
    <nav
      aria-label="Primary"
      className="fixed left-0 top-0 h-full w-14 border-r border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-tertiary) 90%, transparent)] backdrop-blur-sm"
    >
      <div className="flex h-full flex-col items-center justify-between py-4">
        <div className="flex flex-col items-center gap-3">
          <button
            className="grid h-9 w-9 place-items-center rounded-lg text-white/80 hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="New chat"
            title="New"
          >
            <Plus className="h-5 w-5" />
          </button>
          <button
            className="grid h-9 w-9 place-items-center rounded-lg text-white/60 hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="Library"
            title="Library"
          >
            <Grid2x2 className="h-5 w-5" />
          </button>
        </div>
        <button
          className="mb-1 grid h-9 w-9 place-items-center rounded-lg text-white/60 hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
          aria-label="Settings"
          title="Settings"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>
    </nav>
  )
}
