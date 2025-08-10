import React from 'react'
import { Share2, ChevronDown, Sun, Moon, Monitor } from 'lucide-react'

export default function TopBar() {
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
  const themeLabel = theme.charAt(0).toUpperCase() + theme.slice(1);

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
          >
            Claude Opus 4
            <ChevronDown className="h-4 w-4 opacity-80" />
          </button>
        </div>
      </div>
    </header>
  )
}
