import React from 'react'
import { Plus, Paperclip, Send } from 'lucide-react'

export default function Composer({ onSend }: { onSend: (text: string) => void }) {
  const [value, setValue] = React.useState('')
  const ref = React.useRef<HTMLTextAreaElement | null>(null)

  return (
    <footer className="sticky bottom-0 z-20 border-t border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-primary) 85%, transparent)] backdrop-blur">
      <div className="mx-auto max-w-4xl px-5 py-3">
        <form
          className="flex items-end gap-2 rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 70%, transparent)] p-2 focus-within:ring-2 focus-within:ring-[color:var(--color-primary)]"
          onSubmit={(e) => {
            e.preventDefault()
            const text = value.trim()
            if (!text) return
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
            onChange={(e) => setValue(e.target.value)}
            className="min-h-[44px] max-h-40 flex-1 resize-none bg-transparent px-1 py-2 outline-none placeholder:text-[color:var(--text-muted)]"
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
        </form>

        <p className="mt-2 text-xs text-muted">
          Press <kbd>Enter</kbd> to send • <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
        </p>
      </div>
    </footer>
  )
}
