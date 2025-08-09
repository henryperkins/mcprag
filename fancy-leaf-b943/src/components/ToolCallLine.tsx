import { useToolCalls } from '../store/toolCalls.state'
import { Loader2, CheckCircle, XCircle, Terminal } from 'lucide-react'

interface ToolCallLineProps {
  callId: string
}

export function ToolCallLine({ callId }: ToolCallLineProps) {
  const call = useToolCalls((state) => state.active[callId])
  
  if (!call) return null
  
  const percentage = call.total && call.progress != null 
    ? Math.round((call.progress / call.total) * 100) 
    : null
  
  const getStatusIcon = () => {
    switch (call.status) {
      case 'running':
        return <Loader2 className="tool-call-icon tool-call-icon-status tool-call-icon-status-running" />
      case 'success':
        return <CheckCircle className="tool-call-icon tool-call-icon-status tool-call-icon-status-success" />
      case 'error':
        return <XCircle className="tool-call-icon tool-call-icon-status tool-call-icon-status-error" />
    }
  }
  
  const getStatusClass = () => {
    switch (call.status) {
      case 'running':
        return 'tool-call tool-call-running'
      case 'success':
        return 'tool-call tool-call-success'
      case 'error':
        return 'tool-call tool-call-error'
    }
  }

  return (
    <div
      className={getStatusClass()}
      aria-busy={call.status === 'running'}
    >
      <div className="tool-call-header">
        {getStatusIcon()}
        <Terminal className="tool-call-icon-terminal" />
        <span className="tool-call-name">
          {call.name.replace('mcp__', '').replace(/__/g, '.')}
        </span>
        {call.args ? (
          <span className="tool-call-args">
            ({typeof call.args === 'object' ? JSON.stringify(call.args).slice(0, 50) : String(call.args).slice(0, 50)}...)
          </span>
        ) : null}
      </div>
      
      {percentage !== null && (
        <div className="tool-call-progress">
          <div className="tool-call-progress-bar">
            <div
              className="tool-call-progress-fill"
              style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }}
            />
          </div>
          <span className="tool-call-progress-text">{percentage}%</span>
        </div>
      )}
      
      {call.message && (
        <div className="tool-call-message">
          {call.message}
        </div>
      )}
    </div>
  )
}
