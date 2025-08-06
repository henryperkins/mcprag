import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { useUnifiedSession } from '../store/unified.adapter'
import { useSession } from '../store/session.state'
import { useHistory } from '../store/history.state'
import { useMessages } from '../store/messages.state'
import { Send, Square, FileText } from 'lucide-react'

interface PromptBarProps {
  onSubmit: (prompt: string) => void
  onInterrupt: () => void
}

export function PromptBar({ onSubmit, onInterrupt }: PromptBarProps) {
  const [prompt, setPrompt] = useState('')
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

  const handleInput = () => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }

  return (
    <div className="border-t border-white/10 bg-[#0b0f14] p-4">
      <div className="flex flex-col gap-2">
        {/* Mode badges */}
        <div className="flex items-center gap-2 text-xs">
          <span className="px-2 py-0.5 bg-white/5 rounded text-white/60">
            Format: {controls.outputFormat}
          </span>
          <span className="px-2 py-0.5 bg-white/5 rounded text-white/60">
            Mode: {controls.permissionMode}
          </span>
          {controls.verbose && (
            <span className="px-2 py-0.5 bg-emerald-500/20 rounded text-emerald-400">
              Verbose
            </span>
          )}
          {controls.systemPrompt && (
            <span className="px-2 py-0.5 bg-blue-500/20 rounded text-blue-400 flex items-center gap-1">
              <FileText className="w-3 h-3" />
              System Prompt
            </span>
          )}
        </div>

        {/* Input area */}
        <div className="relative flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={
              isRunning
                ? 'Claude is working... (Ctrl+C to interrupt)'
                : 'Type your prompt... (Enter to send, Shift+Enter for newline, Ctrl+L to clear)'
            }
            disabled={isRunning}
            rows={1}
            className="flex-1 bg-[#0f1520] border border-white/10 rounded-lg px-4 py-3 
                     text-white placeholder-white/40 outline-none focus:border-emerald-500/50
                     font-mono text-sm resize-none disabled:opacity-50 disabled:cursor-not-allowed
                     min-h-[48px] max-h-[200px]"
            style={{ height: 'auto' }}
          />
          
          <button
            onClick={isRunning ? onInterrupt : handleSubmit}
            disabled={!isRunning && !prompt.trim()}
            className={`p-3 rounded-lg transition-colors ${
              isRunning
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-emerald-500 hover:bg-emerald-600 text-white disabled:bg-white/10 disabled:text-white/30'
            }`}
          >
            {isRunning ? (
              <Square className="w-5 h-5" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Keyboard shortcuts hint */}
        <div className="flex items-center gap-4 text-xs text-white/40">
          <span>↑/↓ History</span>
          <span>Enter Send</span>
          <span>Shift+Enter Newline</span>
          <span>Ctrl+L Clear</span>
          {isRunning && <span className="text-red-400">Ctrl+C Interrupt</span>}
        </div>
      </div>
    </div>
  )
}