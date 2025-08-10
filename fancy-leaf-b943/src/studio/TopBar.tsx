import React from 'react'
import { Share2, ChevronDown, Sun, Moon, Monitor, Wrench } from 'lucide-react'
import { useSession } from '../store/session.state'

export default function TopBar() {
  const sess = useSession()
  type ThemeMode = 'light' | 'dark' | 'system';
  const [theme, setTheme] = React.useState<ThemeMode>(() => {
    const stored = (localStorage.getItem('theme') as ThemeMode) || 'system';
    return stored;
  });

  React.useEffect(() => {
    const resolved = theme === 'system'
      ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : theme;
    document.documentElement.setAttribute('data-theme', resolved);
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  React.useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      const stored = (localStorage.getItem('theme') as ThemeMode) || 'system';
      if (stored === 'system') {
        document.documentElement.setAttribute('data-theme', mq.matches ? 'dark' : 'light');
      }
    };
    if (mq.addEventListener) mq.addEventListener('change', handler);
    else mq.addListener(handler);
    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', handler);
      else mq.removeListener(handler);
    };
  }, []);

  const cycleTheme = () =>
    setTheme((prev) => (prev === 'light' ? 'dark' : prev === 'dark' ? 'system' : 'light'));

  const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor;
  const models = ['auto', 'claude-3-7-sonnet', 'claude-3-5-sonnet', 'claude-3-opus'] as const
  const [modelIdx, setModelIdx] = React.useState(() => {
    const cur = sess.controls.model || 'auto'
    const idx = models.indexOf(cur as any)
    return idx >= 0 ? idx : 0
  })
  const currentModel = models[modelIdx]
  const cycleModel = () => {
    const next = (modelIdx + 1) % models.length
    setModelIdx(next)
    const value = models[next] === 'auto' ? undefined : models[next]
    sess.setControls({ model: value as any })
  }
  const themeLabel = theme.charAt(0).toUpperCase() + theme.slice(1);

  // Simple tools panel
  const [showTools, setShowTools] = React.useState(false)
  const [allowedInput, setAllowedInput] = React.useState<string>(() => (sess.controls.allowedTools || []).join(', '))
  const [disallowedInput, setDisallowedInput] = React.useState<string>(() => (sess.controls.disallowedTools || []).join(', '))
  const [mcpConfigInput, setMcpConfigInput] = React.useState<string>(() => sess.controls.mcpConfig || '')
  const [permPromptInput, setPermPromptInput] = React.useState<string>(() => sess.controls.permissionPromptTool || '')
  const applyTools = () => {
    const parse = (v: string) => v.split(/[,\n]/).map(s => s.trim()).filter(Boolean)
    sess.setControls({
      allowedTools: parse(allowedInput),
      disallowedTools: parse(disallowedInput),
      mcpConfig: mcpConfigInput || undefined,
      permissionPromptTool: permPromptInput || undefined,
    } as any)
    setShowTools(false)
  }

  return (
    <header className="sticky top-0 z-20 border-b border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-primary) 80%, transparent)] backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-5 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm text-[color:var(--text-muted)]">
            <span className="truncate">Studio</span>
            <span>•</span>
            <span className="truncate">Claude Code SDK</span>
            {sess.currentSessionId && (
              <span
                className="ml-2 inline-flex items-center gap-1 rounded-full border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-2 py-0.5 text-xs"
                title={`Session: ${sess.currentSessionId}`}
              >
                <span className="inline-block h-2 w-2 rounded-full bg-[color:var(--color-success)]" aria-hidden="true" />
                {sess.currentSessionId.slice(0, 8)}…
                <button
                  className="ml-1 opacity-80 hover:opacity-100"
                  aria-label="Copy session id"
                  onClick={() => navigator.clipboard.writeText(sess.currentSessionId!)}
                >
                  📋
                </button>
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              onClick={() => setShowTools(v => !v)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-3 py-1.5 text-sm text-[color:var(--text-primary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
              aria-label="Tools settings"
              title="Allowed/Disallowed tools"
            >
              <Wrench className="h-4 w-4" />
              Tools
            </button>
            {showTools && (
              <div className="absolute right-0 mt-2 w-[420px] rounded-xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)] p-3 shadow-xl z-10">
                <p className="text-sm text-[color:var(--text-secondary)] mb-1">Allowed tools (comma or newline separated)</p>
                <textarea
                  className="w-full h-16 resize-y rounded-md border border-[color:var(--border-faint)] bg-transparent p-2 text-sm"
                  value={allowedInput}
                  onChange={(e) => setAllowedInput(e.target.value)}
                  placeholder="e.g. Read, Write, Edit, Bash, WebSearch, mcp__puppeteer"
                />
                <p className="mt-2 text-sm text-[color:var(--text-secondary)] mb-1">Disallowed tools</p>
                <textarea
                  className="w-full h-12 resize-y rounded-md border border-[color:var(--border-faint)] bg-transparent p-2 text-sm"
                  value={disallowedInput}
                  onChange={(e) => setDisallowedInput(e.target.value)}
                  placeholder="e.g. Bash(rm *), Bash(git reset --hard)"
                />
                <p className="mt-2 text-sm text-[color:var(--text-secondary)] mb-1">MCP config (path or JSON)</p>
                <input
                  className="w-full rounded-md border border-[color:var(--border-faint)] bg-transparent p-2 text-sm"
                  value={mcpConfigInput}
                  onChange={(e) => setMcpConfigInput(e.target.value)}
                  placeholder="e.g. .claude/mcp.json or JSON string"
                />
                <p className="mt-2 text-sm text-[color:var(--text-secondary)] mb-1">Permission prompt tool (MCP)</p>
                <input
                  className="w-full rounded-md border border-[color:var(--border-faint)] bg-transparent p-2 text-sm"
                  value={permPromptInput}
                  onChange={(e) => setPermPromptInput(e.target.value)}
                  placeholder="e.g. mcp__test-server__approval_prompt"
                />
                <div className="mt-3 flex justify-end gap-2">
                  <button
                    onClick={() => setShowTools(false)}
                    className="rounded-md border border-[color:var(--border-faint)] px-3 py-1.5 text-sm text-[color:var(--text-secondary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)]"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={applyTools}
                    className="rounded-md bg-[color:var(--color-primary)] px-3 py-1.5 text-sm text-white hover:bg-[color:var(--color-primary-hover)]"
                  >
                    Apply
                  </button>
                </div>
              </div>
            )}
          </div>
          <button
            onClick={cycleTheme}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-3 py-1.5 text-sm text-[color:var(--text-primary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label={`Toggle theme (current: ${themeLabel})`}
            title={`Theme: ${themeLabel}`}
          >
            <ThemeIcon className="h-4 w-4" />
            {themeLabel}
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-3 py-1.5 text-sm text-[color:var(--text-primary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="Share"
          >
            <Share2 className="h-4 w-4" />
            Share
          </button>
          <button
            className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--border-faint)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] px-3 py-1.5 text-sm text-[color:var(--text-secondary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="Model selector"
            onClick={cycleModel}
          >
            {currentModel}
            <ChevronDown className="h-4 w-4 opacity-80" />
          </button>
        </div>
      </div>
    </header>
  )
}
