import { useState, useEffect, useRef } from 'react'
import type { KeyboardEvent } from 'react'
import './App.css'
import { useMessages } from './store/messages.state'
import { useSession } from './store/session.state'
import { useHistory } from './store/history.state'
import { SlashMenu } from './components/SlashMenu'

function App() {
  const [input, setInput] = useState('')
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [slashFilter, setSlashFilter] = useState('')
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0)
  const [showWelcome] = useState(true)
  const terminalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLDivElement>(null)
  
  const { messages, addMessage, isStreaming, setStreaming } = useMessages()
  const { currentSessionId, setRunning, setInit, setResult, initMeta } = useSession()
  const { push, prev, next, reset } = useHistory()

  // Handle keyboard input exactly like terminal
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    // Check for slash command
    if (e.key === '/' && input === '' && !showSlashMenu) {
      setShowSlashMenu(true)
      setSlashFilter('')
      setSelectedCommandIndex(0)
      return
    }

    // Handle slash menu navigation
    if (showSlashMenu) {
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowSlashMenu(false)
        setSlashFilter('')
        setInput('')
        if (inputRef.current) {
          inputRef.current.textContent = ''
        }
        return
      } else if (e.key === 'Backspace' && input === '/') {
        e.preventDefault()
        setShowSlashMenu(false)
        setSlashFilter('')
        setInput('')
        if (inputRef.current) {
          inputRef.current.textContent = ''
        }
        return
      }
      // Let other keys be handled by SlashMenu component
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (input.trim() && !isStreaming) {
        submitPrompt()
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prevPrompt = prev(currentSessionId || 'default')
      if (prevPrompt) {
        setInput(prevPrompt)
        if (inputRef.current) {
          inputRef.current.textContent = prevPrompt
        }
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      const nextPrompt = next(currentSessionId || 'default')
      if (nextPrompt !== null) {
        setInput(nextPrompt)
        if (inputRef.current) {
          inputRef.current.textContent = nextPrompt
        }
      }
    } else if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault()
      clearTerminal()
    } else if (e.key === 'c' && e.ctrlKey) {
      e.preventDefault()
      if (isStreaming) {
        interruptStream()
      }
    }
  }

  const handleSlashCommand = (command: string) => {
    setShowSlashMenu(false)
    setSlashFilter('')
    
    // Handle slash commands
    switch (command) {
      case '/clear':
        clearTerminal()
        setInput('')
        if (inputRef.current) {
          inputRef.current.textContent = ''
        }
        break
      case '/cost':
        // Show cost info from last result if available
        const lastResult = messages.filter(m => m.type === 'result').pop()
        if (lastResult && lastResult.type === 'result') {
          addMessage({ 
            type: 'assistant', 
            content: `Session cost: $${lastResult.total_cost_usd || 0} • Duration: ${lastResult.duration_ms || 0}ms` 
          })
        } else {
          addMessage({ 
            type: 'assistant', 
            content: 'No cost information available yet' 
          })
        }
        setInput('')
        if (inputRef.current) {
          inputRef.current.textContent = ''
        }
        break
      case '/exit':
      case '/quit':
        addMessage({ type: 'assistant', content: 'Goodbye!' })
        // In real app, would close the terminal
        break
      default:
        // For other commands, just add to input
        setInput(command)
        if (inputRef.current) {
          inputRef.current.textContent = command
        }
    }
  }

  const submitPrompt = async () => {
    const prompt = input.trim()
    if (!prompt) return

    // Check if it's a slash command
    if (prompt.startsWith('/')) {
      handleSlashCommand(prompt)
      return
    }

    // Add user message immediately
    addMessage({ type: 'user', content: prompt })
    
    push(prompt, currentSessionId || 'default')
    setInput('')
    if (inputRef.current) {
      inputRef.current.textContent = ''
    }
    setStreaming(true)
    setRunning(true)

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          sessionId: currentSessionId,
          outputFormat: 'stream-json',
          maxTurns: 6,
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\\n\\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const dataLine = line
              .split('\\n')
              .find(l => l.trim().startsWith('data: '))
            
            if (!dataLine) continue
            
            const payload = dataLine.slice(6)
            try {
              const data = JSON.parse(payload)
              
              // Handle session init
              if (data.type === 'system' && data.subtype === 'init') {
                setInit(data)
              } else if (data.type === 'result') {
                setResult(data)
              }
              
              addMessage(data)
            } catch (err) {
              // Handle plain text chunks
              if (payload) {
                addMessage({ type: 'chunk', data: payload })
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Query error:', error)
      // Error will be shown in console, no need to add message
    } finally {
      setStreaming(false)
      setRunning(false)
      reset(currentSessionId || 'default')
    }
  }

  const clearTerminal = () => {
    useMessages.getState().clearMessages()
  }

  const interruptStream = async () => {
    try {
      await fetch('/api/interrupt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: currentSessionId }),
      })
      setStreaming(false)
      setRunning(false)
      addMessage({
        type: 'result',
        subtype: 'interrupted',
        session_id: currentSessionId || undefined,
      })
    } catch (error) {
      console.error('Interrupt error:', error)
    }
  }

  // Auto-scroll to bottom
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  // Format diff content with line numbers and colors
  const formatDiffContent = (content: string) => {
    const lines = content.split('\n')
    return lines.map((line, idx) => {
      const lineNum = idx + 1
      const isAddition = line.startsWith('+')
      const isDeletion = line.startsWith('-')
      const className = isAddition ? 'diff-add' : isDeletion ? 'diff-del' : ''
      
      return (
        <div key={idx} className={`diff-line ${className}`}>
          <span className="line-number">{lineNum.toString().padStart(3, ' ')}</span>
          <span className="diff-marker">{isAddition ? '+' : isDeletion ? '-' : ' '}</span>
          <span className="diff-content">{line.slice(1)}</span>
        </div>
      )
    })
  }

  return (
    <div className="terminal-container">
      {/* Terminal Header */}
      <div className="terminal-header">
        <div className="terminal-tab">
          <span className="terminal-icon">▼</span>
          <span className="terminal-title">TERMINAL</span>
        </div>
        <div className="terminal-session">
          <span className="session-model">claude - mcprag</span>
          <span className="terminal-controls">⊞ □ ✕</span>
        </div>
      </div>

      <div className="terminal-body" ref={terminalRef}>
        {/* Welcome message */}
        {showWelcome && (
          <div className="welcome-box">
            <div className="welcome-header">❈ Welcome to Claude Code!</div>
            <div className="welcome-content">
              <div className="welcome-hint">/help for help, /status for your current setup</div>
              <div className="welcome-cwd">cwd: /home/azureuser/mcprag</div>
            </div>
          </div>
        )}

        {/* Tip message */}
        <div className="terminal-tip">
          ❈ Tip: Use /memory to view and manage Claude memory
        </div>

        {/* Messages rendered in CLI style */}
        {messages.map((msg, idx) => (
          <div key={idx} className={`terminal-message ${msg.type}`}>
            {/* User message */}
            {msg.type === 'user' && (
              <>
                <div className="terminal-line user">
                  <span className="prompt-marker">●</span>
                  <span className="user-input">
                    {typeof msg.content === 'string' 
                      ? msg.content 
                      : Array.isArray(msg.content)
                        ? msg.content.map((block: any) => 
                            block.type === 'text' ? block.text : `[${block.type}]`
                          ).join('')
                        : String(msg.content)
                    }
                  </span>
                </div>
                <div className="terminal-line empty"></div>
              </>
            )}
            
            {/* Assistant message */}
            {msg.type === 'assistant' && (
              <div className="terminal-line assistant">
                <div className="assistant-content">
                  {typeof msg.content === 'string' 
                    ? msg.content 
                    : Array.isArray(msg.content) 
                      ? msg.content.map((block: any) => 
                          block.type === 'text' ? block.text : `[${block.type}]`
                        ).join('')
                      : String(msg.content)
                  }
                </div>
              </div>
            )}
            
            {/* Tool calls - Write/Read/etc */}
            {msg.type === 'tool_call' && (
              <div className="terminal-line tool">
                <span className="tool-marker">●</span>
                <span className="tool-name">
                  {msg.name === 'Write' ? 'Write' : 
                   msg.name === 'Read' ? 'Read' :
                   msg.name === 'Edit' ? 'Edit' :
                   msg.name === 'Bash' ? 'Bash' :
                   msg.name}
                </span>
                <span className="tool-args-paren">(</span>
                <span className="tool-args">
                  {msg.arguments?.file_path || msg.arguments?.path || 
                   (typeof msg.arguments === 'string' ? msg.arguments : 
                    typeof msg.arguments === 'object' ? JSON.stringify(msg.arguments).slice(0, 50) : '')}
                </span>
                <span className="tool-args-paren">)</span>
              </div>
            )}
            
            {/* Tool result */}
            {msg.type === 'tool_result' && (
              <div className="terminal-line tool-result">
                <span className="tool-result-indent">└</span>
                <span className="tool-result-content">
                  {msg.is_error ? (
                    <span className="error">Error: {msg.content}</span>
                  ) : (
                    <>
                      {typeof msg.content === 'string' && msg.content.includes('lines') ? (
                        <span>{msg.content}</span>
                      ) : (
                        <span>Done</span>
                      )}
                    </>
                  )}
                </span>
              </div>
            )}

            {/* Diff display */}
            {msg.type === 'chunk' && msg.data?.includes('@@') && (
              <div className="diff-block">
                {formatDiffContent(msg.data)}
              </div>
            )}
            
            {/* Result message */}
            {msg.type === 'result' && (
              <div className="terminal-line result">
                <span className="result-marker">
                  {msg.subtype === 'success' ? '✓' : 
                   msg.subtype === 'interrupted' ? '⚠' : '✗'}
                </span>
                <span className="result-content">
                  {msg.subtype === 'success' ? 'Completed' :
                   msg.subtype === 'interrupted' ? 'Interrupted by user' :
                   msg.subtype === 'error_max_turns' ? 'Max turns reached' :
                   'Error'}
                </span>
              </div>
            )}
          </div>
        ))}

        {/* Sussing indicator when streaming */}
        {isStreaming && (
          <div className="terminal-line sussing">
            <span className="sussing-marker">*</span>
            <span className="sussing-text">Sussing...</span>
            <span className="sussing-info">(29s · ⚡7.2k tokens · esc to interrupt)</span>
          </div>
        )}

        {/* Current prompt line */}
        <div className="terminal-line current">
          <span className="prompt-marker">{'>'}</span>
          <div className="prompt-input-container">
          <div 
            ref={inputRef}
            className="terminal-input"
            contentEditable
            suppressContentEditableWarning
            onKeyDown={handleKeyDown}
            onInput={(e) => {
              const text = e.currentTarget.textContent || ''
              setInput(text)
              
              // Handle slash menu filtering
              if (text.startsWith('/')) {
                setShowSlashMenu(true)
                setSlashFilter(text.slice(1))
                setSelectedCommandIndex(0)
              } else if (showSlashMenu) {
                setShowSlashMenu(false)
                setSlashFilter('')
              }
            }}
            data-placeholder=""
          />
          <span className="cursor">█</span>
          </div>
          {/* Slash menu */}
          <SlashMenu
            isOpen={showSlashMenu}
            filter={slashFilter}
            onSelect={handleSlashCommand}
            onClose={() => {
              setShowSlashMenu(false)
              setSlashFilter('')
            }}
            selectedIndex={selectedCommandIndex}
            onSelectedIndexChange={setSelectedCommandIndex}
          />
        </div>
      </div>

      <div className="terminal-footer">
        <span className="footer-shortcut">? for shortcuts</span>
        {initMeta && (
          <span className="footer-status">
            Approaching Opus usage limit • /model to use best available model
          </span>
        )}
      </div>
    </div>
  )
}

export default App