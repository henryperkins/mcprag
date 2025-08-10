import React from 'react'
import { Plus, Paperclip, Send } from 'lucide-react'
import { SlashMenu, type SlashCommand } from '../components/SlashMenu'
import { useSessionStore } from '../store/session'

type Props = {
  onSend: (text: string) => void
  onCancel?: () => void
  onClear?: () => void
  isStreaming?: boolean
  commands?: SlashCommand[]
}

export default function Composer({ onSend, onCancel, onClear, isStreaming = false, commands = [] }: Props) {
  const [value, setValue] = React.useState('')
  const ref = React.useRef<HTMLTextAreaElement | null>(null)
  const MAX_COMPOSER_HEIGHT_PX = 192 // 12rem
  React.useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    const h = Math.min(MAX_COMPOSER_HEIGHT_PX, el.scrollHeight)
    el.style.height = `${h}px`
    el.style.overflowY = el.scrollHeight > MAX_COMPOSER_HEIGHT_PX ? 'auto' : 'hidden'
  }, [value])
  // Slash menu state
  const [isSlashOpen, setIsSlashOpen] = React.useState(false)
  const [slashFilter, setSlashFilter] = React.useState('')
  const [slashIndex, setSlashIndex] = React.useState(0)
  // History
  const history = useSessionStore((s) => s.terminal.history)
  const historyIndex = useSessionStore((s) => s.terminal.historyIndex)
  const actions = useSessionStore((s) => s.actions)

  React.useEffect(() => {
    if (historyIndex >= 0 && historyIndex < history.length) {
      setValue(history[historyIndex])
    } else if (historyIndex === -1) {
      // Reset to empty when not navigating history
      // no-op if user is typing
    }
  }, [historyIndex, history])

  return (
    <footer className="sticky bottom-0 z-20 border-t border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-primary) 85%, transparent)] backdrop-blur">
      <div className="mx-auto max-w-4xl px-5 py-3">
        <form
          className="flex items-end gap-2 rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)] p-2 focus-within:ring-2 focus-within:ring-[color:var(--color-primary)]"
          onSubmit={(e) => {
            e.preventDefault()
            const text = value.trim()
            // If slash menu is open, don't submit yet
            if (!text || isSlashOpen) return
            actions.pushHistory(text)
            onSend(text)
            setValue('')
            ref.current?.focus()
          }}
          aria-label="Reply composer"
        >
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-lg text-[color:var(--text-secondary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            aria-label="Insert"
            title="Insert"
          >
            <Plus className="h-5 w-5" />
          </button>

          <textarea
            ref={ref}
            rows={1}
            placeholder="Message Claude…"
            value={value}
            onChange={(e) => {
              const next = e.target.value
              setValue(next)
              const trimmed = next.trimStart()
              if (trimmed.startsWith('/')) {
                setIsSlashOpen(true)
                const idx = trimmed.indexOf(' ')
                const filter = (idx === -1 ? trimmed : trimmed.slice(0, idx)).replace(/^\//, '')
                setSlashFilter(filter)
                setSlashIndex(0)
              } else {
                setIsSlashOpen(false)
                setSlashFilter('')
              }
            }}
             onInput={(e) => {
               const el = e.currentTarget
               el.style.height = 'auto'
               const h = Math.min(MAX_COMPOSER_HEIGHT_PX, el.scrollHeight)
               el.style.height = `${h}px`
               el.style.overflowY = el.scrollHeight > MAX_COMPOSER_HEIGHT_PX ? 'auto' : 'hidden'
             }}
             onKeyDown={(e) => {
              // Let SlashMenu handle its own navigation keys
              if (isSlashOpen && (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'Enter' || e.key === 'Escape' || e.key === 'Home' || e.key === 'End')) {
                return
              }
              // Ctrl+C: cancel streaming
              if (e.ctrlKey && e.key.toLowerCase() === 'c') {
                e.preventDefault()
                if (isStreaming) onCancel?.()
                setValue('')
                return
              }
              // Ctrl+L: clear chat
              if (e.ctrlKey && e.key.toLowerCase() === 'l') {
                e.preventDefault()
                onClear?.()
                return
              }
              // History navigation
              if (e.key === 'ArrowUp') {
                e.preventDefault()
                actions.historyPrev()
                return
              }
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                actions.historyNext()
                return
              }
            }}
            className="min-h-[32px] max-h-48 w-full min-w-0 flex-1 resize-none bg-transparent px-1 py-0.5 outline-none placeholder:text-[color:var(--text-muted)]"
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="grid h-9 w-9 place-items-center rounded-lg text-[color:var(--text-secondary)] hover:bg-[color:color-mix(in srgb, var(--color-primary) 12%, transparent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
              aria-label="Attach"
              title="Attach"
            >
              <Paperclip className="h-5 w-5" />
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-primary)] px-3 py-2 text-sm font-medium text-white hover:bg-[color:var(--color-primary-hover)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
              aria-label="Send"
              title="Send"
            >
              <Send className="h-4 w-4" />
              Send
            </button>
          </div>
          {/* Inline slash menu under the composer */}
          <div className="w-full">
            <SlashMenu
              isOpen={isSlashOpen}
              filter={slashFilter}
              onSelect={(cmd) => {
                const next = `${cmd} `
                setValue(next)
                setIsSlashOpen(false)
                // focus textarea and move cursor to end
                requestAnimationFrame(() => {
                  const el = ref.current
                  if (!el) return
                  el.focus()
                  el.selectionStart = el.selectionEnd = next.length
                })
              }}
              onClose={() => setIsSlashOpen(false)}
              selectedIndex={slashIndex}
              onSelectedIndexChange={setSlashIndex}
              commands={commands}
            />
          </div>
        </form>

        <p className="mt-2 text-xs text-muted">
          Press <kbd>Enter</kbd> to send • <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
        </p>
      </div>
    </footer>
  )
}
