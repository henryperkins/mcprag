import { useState, useEffect, useRef } from 'react'
import { useUnifiedSession, usePerformanceMonitor } from '../store/unified.adapter'
import { useSession } from '../store/session.state'
import { ChevronDown, Terminal, Settings, RotateCcw } from 'lucide-react'

export function Header() {
  // Use unified state for reading
  const unifiedState = useUnifiedSession()
  
  // Still need original session for actions (until migrated)
  const {
    setControls,
    recentSessions,
    setSession,
    clearSession,
  } = useSession()
  
  // Extract values from unified state
  const initMeta = {
    model: unifiedState.session.model,
    cwd: unifiedState.session.cwd,
    tools: unifiedState.session.tools,
    mcpServers: unifiedState.session.mcpServers,
  }
  const runStats = unifiedState.session.stats
  const currentSessionId = unifiedState.session.id
  const isRunning = unifiedState.session.isRunning
  const controls = useSession().controls // Keep for now as it's not in unified yet
  
  const [showSessionMenu, setShowSessionMenu] = useState(false)
  const [resumeId, setResumeId] = useState('')
  const [showResumeModal, setShowResumeModal] = useState(false)
  
  const sessionMenuRef = useRef<HTMLDivElement>(null)
  const sessionButtonRef = useRef<HTMLButtonElement>(null)
  const { markInteraction } = usePerformanceMonitor()

  const handleNewSession = () => {
    clearSession()
    setShowSessionMenu(false)
    markInteraction('header:new-session')
  }

  const handleContinue = () => {
    setShowSessionMenu(false)
    markInteraction('header:continue-session')
  }

  const handleResume = () => {
    if (resumeId.trim()) {
      setSession(resumeId.trim())
      setShowResumeModal(false)
      setResumeId('')
      markInteraction('header:resume-session', { sessionId: resumeId })
    }
  }
  
  // Focus trap for session menu
  useEffect(() => {
    if (showSessionMenu && sessionMenuRef.current) {
      const focusableElements = sessionMenuRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]
      
      firstElement?.focus()
      
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          setShowSessionMenu(false)
          sessionButtonRef.current?.focus()
        } else if (e.key === 'Tab') {
          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault()
            lastElement?.focus()
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault()
            firstElement?.focus()
          }
        }
      }
      
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [showSessionMenu])
  
  // Click outside to close
  useEffect(() => {
    if (showSessionMenu) {
      const handleClickOutside = (e: MouseEvent) => {
        if (
          sessionMenuRef.current &&
          !sessionMenuRef.current.contains(e.target as Node) &&
          !sessionButtonRef.current?.contains(e.target as Node)
        ) {
          setShowSessionMenu(false)
        }
      }
      
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSessionMenu])

  return (
    <>
      <header className="bg-[#0b0f14] border-b border-white/10 px-4 py-2" role="banner">
        <div className="flex items-center gap-4">
          {/* Logo and Model */}
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-emerald-400" aria-hidden="true" />
            <span className="font-semibold text-emerald-400">Claude Code</span>
            {initMeta && (
              <span className="text-xs text-white/60 ml-2" aria-label={`Model: ${initMeta.model}`}>
                {initMeta.model}
              </span>
            )}
          </div>

          {/* Session Controls */}
          <div className="relative">
            <button
              ref={sessionButtonRef}
              onClick={() => setShowSessionMenu(!showSessionMenu)}
              className="flex items-center gap-2 px-3 py-1 rounded bg-white/5 hover:bg-white/10 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              aria-expanded={showSessionMenu}
              aria-controls="session-menu"
              aria-label={`Session menu. Current session: ${currentSessionId ? currentSessionId.slice(0, 8) : 'New'}`}
            >
              <span className="text-white/80" aria-hidden="true">
                Session: {currentSessionId ? currentSessionId.slice(0, 8) : 'New'}
              </span>
              <ChevronDown className="w-4 h-4 text-white/60" aria-hidden="true" />
            </button>
            
            {showSessionMenu && (
              <div 
                ref={sessionMenuRef}
                id="session-menu"
                className="absolute top-full mt-1 left-0 bg-[#0f1520] border border-white/10 rounded-md shadow-lg z-50 min-w-[200px]"
                role="menu"
                aria-labelledby="session-button"
              >
                <button
                  onClick={handleNewSession}
                  className="w-full text-left px-3 py-2 hover:bg-white/5 text-sm focus:outline-none focus:bg-white/5"
                  role="menuitem"
                >
                  New Session
                </button>
                <button
                  onClick={handleContinue}
                  className="w-full text-left px-3 py-2 hover:bg-white/5 text-sm focus:outline-none focus:bg-white/5 disabled:opacity-50"
                  disabled={!currentSessionId}
                  role="menuitem"
                  aria-disabled={!currentSessionId}
                >
                  Continue Current
                </button>
                <button
                  onClick={() => {
                    setShowResumeModal(true)
                    setShowSessionMenu(false)
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-white/5 text-sm focus:outline-none focus:bg-white/5"
                  role="menuitem"
                >
                  Resume by ID...
                </button>
                {recentSessions.length > 0 && (
                  <>
                    <div className="border-t border-white/10 my-1" role="separator" />
                    <div className="px-3 py-1 text-xs text-white/40" role="heading" aria-level={3}>Recent</div>
                    {recentSessions.slice(0, 5).map((id) => (
                      <button
                        key={id}
                        onClick={() => {
                          setSession(id)
                          setShowSessionMenu(false)
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-white/5 text-xs font-mono focus:outline-none focus:bg-white/5"
                        role="menuitem"
                        aria-label={`Resume session ${id.slice(0, 8)}`}
                      >
                        {id.slice(0, 8)}...
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Execution Controls */}
          <div className="flex items-center gap-4" role="group" aria-label="Execution controls">
            {/* Max Turns */}
            <div className="flex items-center gap-2">
              <label htmlFor="max-turns" className="text-xs text-white/60">Max turns:</label>
              <input
                id="max-turns"
                type="range"
                min={1}
                max={12}
                value={controls.maxTurns}
                onChange={(e) => setControls({ maxTurns: Number(e.target.value) })}
                className="w-20 accent-emerald-500"
                aria-valuenow={controls.maxTurns}
                aria-valuemin={1}
                aria-valuemax={12}
              />
              <span className="text-sm text-white/80 w-6 text-center" aria-live="polite">
                {controls.maxTurns}
              </span>
            </div>

            {/* Permission Mode */}
            <div className="flex items-center gap-2">
              <label htmlFor="permission-mode" className="text-xs text-white/60">Mode:</label>
              <select
                id="permission-mode"
                value={controls.permissionMode}
                onChange={(e) => 
                  setControls({ 
                    permissionMode: e.target.value as typeof controls.permissionMode 
                  })
                }
                className="bg-[#0f1520] border border-white/10 rounded px-2 py-1 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                aria-label="Permission mode"
              >
                <option value="default">Default</option>
                <option value="acceptEdits">Accept Edits</option>
                <option value="bypassPermissions">Bypass</option>
                <option value="plan">Plan</option>
              </select>
            </div>

            {/* Verbose */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={controls.verbose}
                onChange={(e) => setControls({ verbose: e.target.checked })}
                className="accent-emerald-500"
                aria-describedby="verbose-description"
              />
              <span className="text-sm text-white/80">Verbose</span>
              <span id="verbose-description" className="sr-only">Enable verbose output logging</span>
            </label>
          </div>

          {/* Telemetry */}
          <div className="ml-auto flex items-center gap-4">
            {isRunning && (
              <div className="flex items-center gap-2" role="status" aria-live="polite">
                <RotateCcw className="w-4 h-4 text-emerald-400 animate-spin" aria-hidden="true" />
                <span className="text-xs text-emerald-400">Running...</span>
              </div>
            )}
            
            {runStats && (
              <div className="flex items-center gap-3 text-xs text-white/60" role="group" aria-label="Session statistics">
                <span aria-label={`Turns: ${runStats.numTurns}`}>Turns: {runStats.numTurns}</span>
                <span aria-label={`Duration: ${runStats.durationMs} milliseconds`}>Time: {runStats.durationMs}ms</span>
                <span className="text-emerald-400" aria-label={`Cost: ${runStats.totalCostUsd.toFixed(4)} dollars`}>
                  ${runStats.totalCostUsd.toFixed(4)}
                </span>
              </div>
            )}

            {/* Settings Button */}
            <button 
              className="p-2 hover:bg-white/5 rounded focus:outline-none focus:ring-2 focus:ring-emerald-500"
              aria-label="Settings"
            >
              <Settings className="w-4 h-4 text-white/60" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* MCP Servers Status */}
        {initMeta?.mcpServers && initMeta.mcpServers.length > 0 && (
          <div className="flex items-center gap-2 mt-2 text-xs" role="group" aria-label="MCP server status">
            <span className="text-white/40">MCP:</span>
            {initMeta.mcpServers.map((server) => (
              <span
                key={server.name}
                className="px-2 py-0.5 bg-white/5 rounded text-white/60"
                role="status"
                aria-label={`MCP server ${server.name} is connected`}
              >
                {server.name}
              </span>
            ))}
          </div>
        )}
      </header>

      {/* Resume Modal */}
      {showResumeModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="resume-dialog-title"
        >
          <div className="bg-[#0f1520] border border-white/10 rounded-lg p-6 max-w-md w-full">
            <h3 id="resume-dialog-title" className="text-lg font-semibold mb-4">Resume Session</h3>
            <input
              type="text"
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
              placeholder="Enter session ID..."
              className="w-full bg-[#0b0f14] border border-white/10 rounded px-3 py-2 mb-4 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              autoFocus
              aria-label="Session ID"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowResumeModal(false)
                  setResumeId('')
                }}
                className="px-4 py-2 text-white/60 hover:text-white focus:outline-none focus:ring-2 focus:ring-white/20"
              >
                Cancel
              </button>
              <button
                onClick={handleResume}
                className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                Resume
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}