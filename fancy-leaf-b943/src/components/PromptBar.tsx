import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent, ChangeEvent } from 'react'
import { useUnifiedSession } from '../store/unified.adapter'
import { useSession } from '../store/session.state'
import { useHistory } from '../store/history.state'
import { useMessages } from '../store/messages.state'
import { Send, Square, FileText } from 'lucide-react'
import { SlashMenu } from './SlashMenu'
import type { SlashCommand } from './SlashMenu'

interface PromptBarProps {
  onSubmit: (prompt: string) => void
  onInterrupt: () => void
}

export function PromptBar({ onSubmit, onInterrupt }: PromptBarProps) {
  const [prompt, setPrompt] = useState('')
  const [isSlashOpen, setIsSlashOpen] = useState(false)
  const [slashFilter, setSlashFilter] = useState('')
  const [slashIndex, setSlashIndex] = useState(0)
  const [slashCommands, setSlashCommands] = useState<SlashCommand[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Use unified state for reading
  const unifiedState = useUnifiedSession()
  
  // Extract values from unified state
  const currentSessionId = unifiedState.session.id
  const isRunning = unifiedState.session.isRunning
  const controls = useSession().controls // Keep for now as it's not in unified yet
  
  const { push, prev, next, reset } = useHistory()
  const { clearMessages } = useMessages()
  
  const sessionId = currentSessionId || 'default'

  useEffect(() => {
    // Auto-focus on mount
    textareaRef.current?.focus()
  }, [])

  useEffect(() => {
    // Fetch available slash commands once (try same-origin, configured gateway, and local bridge)
    let cancelled = false
    async function loadCommands() {
      const envBase = (import.meta.env.VITE_CLAUDE_GATEWAY_URL || '').replace(/\/$/, '')
      const candidates = Array.from(new Set<string>([
        '', // same-origin
        envBase,
        'http://localhost:8787',
        'http://127.0.0.1:8787',
      ])).filter(Boolean).concat('') // ensure '' is included at least once

      for (const base of candidates) {
        try {
          const url = `${base}/api/commands`
          const res = await fetch(url)
          if (!res.ok) continue
          const data = await res.json().catch(() => ({}))
          const list = Array.isArray(data) ? data : (data.commands ?? [])
          if (list && list.length) {
            const mapped: SlashCommand[] = (list || []).map((c: any) => ({
              command: c.name || c.command,
              description: c.description || '',
              args: Array.isArray(c.arguments) ? c.arguments.join(' ') : c.args
            }))
            if (!cancelled) setSlashCommands(mapped)
            return
          }
        } catch {
          // try next candidate
        }
      }

      if (!cancelled) {
        // Fallback defaults if discovery fails
        setSlashCommands([
          { command: '/help', description: 'Show available commands' },
          { command: '/clear', description: 'Clear conversation' },
          { command: '/model', description: 'Switch model' },
        ])
      }
    }
    loadCommands()
    return () => { cancelled = true }
  }, [])

  const handleSubmit = () => {
    if (!prompt.trim() || isRunning) return
    
    push(prompt, sessionId)
    onSubmit(prompt)
    setPrompt('')
    reset(sessionId)
    
    // Auto-resize textarea back to default
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // If slash menu is open, let it handle navigation/selection keys
    if (isSlashOpen && (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'Enter' || e.key === 'Escape' || e.key === 'Home' || e.key === 'End')) {
      return
    }

    // Enter to submit (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
      return
    }

    // Ctrl+L to clear
    if (e.key === 'l' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      clearMessages()
      return
    }

    // Ctrl+C to interrupt
    if (e.key === 'c' && (e.ctrlKey || e.metaKey) && isRunning) {
      e.preventDefault()
      onInterrupt()
      return
    }

    // Up arrow for history (only when at start of input)
    if (e.key === 'ArrowUp' && textareaRef.current?.selectionStart === 0) {
      e.preventDefault()
      const previous = prev(sessionId)
      if (previous !== null) {
        setPrompt(previous)
        // Move cursor to end
        setTimeout(() => {
          if (textareaRef.current) {
            const len = textareaRef.current.value.length
            textareaRef.current.setSelectionRange(len, len)
          }
        }, 0)
      }
      return
    }

    // Down arrow for history
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const nextItem = next(sessionId)
      if (nextItem !== null) {
        setPrompt(nextItem)
      }
      return
    }
  }

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const next = e.target.value
    setPrompt(next)
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
  }

  const handleInput = () => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }

  return (
    <div className="prompt-bar">
      <div className="prompt-bar-inner">
        {/* Mode badges */}
        <div className="prompt-bar-badges">
          <span className="prompt-bar-badge">
            Format: {controls.outputFormat}
          </span>
          <span className="prompt-bar-badge">
            Mode: {controls.permissionMode}
          </span>
          {controls.verbose && (
            <span className="prompt-bar-badge prompt-bar-badge-verbose">
              Verbose
            </span>
          )}
          {controls.systemPrompt && (
            <span className="prompt-bar-badge prompt-bar-badge-system">
              <FileText className="prompt-bar-badge-icon" />
              System Prompt
            </span>
          )}
          {controls.appendSystemPrompt && (
            <span className="prompt-bar-badge prompt-bar-badge-system">
              <FileText className="prompt-bar-badge-icon" />
              Append Prompt
            </span>
          )}
        </div>

        {/* Input area */}
        <div className="prompt-bar-input-area">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={
              isRunning
                ? 'Claude is working... (Ctrl+C to interrupt)'
                : 'Type your prompt... (Enter to send, Shift+Enter for newline, / for commands, Ctrl+L to clear)'
            }
            disabled={isRunning}
            rows={1}
            className="prompt-bar-textarea"
            style={{ height: 'auto' }}
          />
          <SlashMenu
            isOpen={isSlashOpen}
            filter={slashFilter}
            onSelect={(cmd) => {
              const nextVal = `${cmd} `
              setPrompt(nextVal)
              setIsSlashOpen(false)
              // focus textarea and move cursor to end
              requestAnimationFrame(() => {
                const el = textareaRef.current
                if (!el) return
                el.focus()
                el.selectionStart = el.selectionEnd = nextVal.length
              })
            }}
            onClose={() => setIsSlashOpen(false)}
            selectedIndex={slashIndex}
            onSelectedIndexChange={setSlashIndex}
            commands={slashCommands}
          />
          
          <button
            onClick={isRunning ? onInterrupt : handleSubmit}
            disabled={!isRunning && !prompt.trim()}
            className={`prompt-bar-button ${
              isRunning
                ? 'prompt-bar-button-interrupt'
                : 'prompt-bar-button-submit'
            }`}
          >
            {isRunning ? (
              <Square className="prompt-bar-button-icon" />
            ) : (
              <Send className="prompt-bar-button-icon" />
            )}
          </button>
        </div>

        {/* Keyboard shortcuts hint */}
        <div className="prompt-bar-shortcuts">
          <span>↑/↓ History</span>
          <span>Enter Send</span>
          <span>Shift+Enter Newline</span>
          <span>Ctrl+L Clear</span>
          {isRunning && <span className="prompt-bar-shortcut-interrupt">Ctrl+C Interrupt</span>}
        </div>
      </div>
    </div>
  )
}
