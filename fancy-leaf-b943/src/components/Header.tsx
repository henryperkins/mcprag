import { useState } from 'react'
import { useSession } from '../store/session.state'
import { ChevronDown, Terminal, Settings, RotateCcw } from 'lucide-react'

export function Header() {
  const {
    initMeta,
    runStats,
    currentSessionId,
    controls,
    setControls,
    recentSessions,
    setSession,
    clearSession,
    isRunning,
  } = useSession()
  
  const [showSessionMenu, setShowSessionMenu] = useState(false)
  const [resumeId, setResumeId] = useState('')
  const [showResumeModal, setShowResumeModal] = useState(false)

  const handleNewSession = () => {
    clearSession()
    setShowSessionMenu(false)
  }

  const handleContinue = () => {
    // Continue will be handled by backend with --continue flag
    setShowSessionMenu(false)
  }

  const handleResume = () => {
    if (resumeId.trim()) {
      setSession(resumeId.trim())
      setShowResumeModal(false)
      setResumeId('')
    }
  }

  return (
    <>
      <header className="bg-[#0b0f14] border-b border-white/10 px-4 py-2">
        <div className="flex items-center gap-4">
          {/* Logo and Model */}
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-emerald-400">Claude Code</span>
            {initMeta && (
              <span className="text-xs text-white/60 ml-2">
                {initMeta.model}
              </span>
            )}
          </div>

          {/* Session Controls */}
          <div className="relative">
            <button
              onClick={() => setShowSessionMenu(!showSessionMenu)}
              className="flex items-center gap-2 px-3 py-1 rounded bg-white/5 hover:bg-white/10 text-sm"
            >
              <span className="text-white/80">
                Session: {currentSessionId ? currentSessionId.slice(0, 8) : 'New'}
              </span>
              <ChevronDown className="w-4 h-4 text-white/60" />
            </button>
            
            {showSessionMenu && (
              <div className="absolute top-full mt-1 left-0 bg-[#0f1520] border border-white/10 rounded-md shadow-lg z-50 min-w-[200px]">
                <button
                  onClick={handleNewSession}
                  className="w-full text-left px-3 py-2 hover:bg-white/5 text-sm"
                >
                  New Session
                </button>
                <button
                  onClick={handleContinue}
                  className="w-full text-left px-3 py-2 hover:bg-white/5 text-sm"
                  disabled={!currentSessionId}
                >
                  Continue Current
                </button>
                <button
                  onClick={() => {
                    setShowResumeModal(true)
                    setShowSessionMenu(false)
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-white/5 text-sm"
                >
                  Resume by ID...
                </button>
                {recentSessions.length > 0 && (
                  <>
                    <div className="border-t border-white/10 my-1" />
                    <div className="px-3 py-1 text-xs text-white/40">Recent</div>
                    {recentSessions.slice(0, 5).map((id) => (
                      <button
                        key={id}
                        onClick={() => {
                          setSession(id)
                          setShowSessionMenu(false)
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-white/5 text-xs font-mono"
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
          <div className="flex items-center gap-4">
            {/* Max Turns */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/60">Max turns:</span>
              <input
                type="range"
                min={1}
                max={12}
                value={controls.maxTurns}
                onChange={(e) => setControls({ maxTurns: Number(e.target.value) })}
                className="w-20 accent-emerald-500"
              />
              <span className="text-sm text-white/80 w-6 text-center">
                {controls.maxTurns}
              </span>
            </div>

            {/* Permission Mode */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/60">Mode:</span>
              <select
                value={controls.permissionMode}
                onChange={(e) => 
                  setControls({ 
                    permissionMode: e.target.value as typeof controls.permissionMode 
                  })
                }
                className="bg-[#0f1520] border border-white/10 rounded px-2 py-1 text-sm outline-none focus:border-emerald-500"
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
              />
              <span className="text-sm text-white/80">Verbose</span>
            </label>
          </div>

          {/* Telemetry */}
          <div className="ml-auto flex items-center gap-4">
            {isRunning && (
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-emerald-400 animate-spin" />
                <span className="text-xs text-emerald-400">Running...</span>
              </div>
            )}
            
            {runStats && (
              <div className="flex items-center gap-3 text-xs text-white/60">
                <span>Turns: {runStats.numTurns}</span>
                <span>Time: {runStats.durationMs}ms</span>
                <span>API: {runStats.durationApiMs}ms</span>
                <span className="text-emerald-400">
                  ${runStats.totalCostUsd.toFixed(4)}
                </span>
              </div>
            )}

            {/* Settings Button */}
            <button className="p-2 hover:bg-white/5 rounded">
              <Settings className="w-4 h-4 text-white/60" />
            </button>
          </div>
        </div>

        {/* MCP Servers Status */}
        {initMeta?.mcpServers && initMeta.mcpServers.length > 0 && (
          <div className="flex items-center gap-2 mt-2 text-xs">
            <span className="text-white/40">MCP:</span>
            {initMeta.mcpServers.map((server) => (
              <span
                key={server.name}
                className="px-2 py-0.5 bg-white/5 rounded text-white/60"
              >
                {server.name}
              </span>
            ))}
          </div>
        )}
      </header>

      {/* Resume Modal */}
      {showResumeModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#0f1520] border border-white/10 rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Resume Session</h3>
            <input
              type="text"
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
              placeholder="Enter session ID..."
              className="w-full bg-[#0b0f14] border border-white/10 rounded px-3 py-2 mb-4 outline-none focus:border-emerald-500"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowResumeModal(false)
                  setResumeId('')
                }}
                className="px-4 py-2 text-white/60 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleResume}
                className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600"
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