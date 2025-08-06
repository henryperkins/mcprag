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
        return <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
      case 'success':
        return <CheckCircle className="w-4 h-4 text-emerald-400" />
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />
    }
  }
  
  const getStatusColor = () => {
    switch (call.status) {
      case 'running':
        return 'text-white/70 border-emerald-500/30'
      case 'success':
        return 'text-emerald-400 border-emerald-500/30'
      case 'error':
        return 'text-red-400 border-red-500/30'
    }
  }

  return (
    <div
      className={`
        font-mono text-xs border rounded-md px-3 py-2 my-1
        bg-white/5 transition-all duration-300
        ${getStatusColor()}
        ${call.status === 'running' ? 'shimmer' : ''}
      `}
      aria-busy={call.status === 'running'}
    >
      <div className="flex items-center gap-2">
        {getStatusIcon()}
        <Terminal className="w-3 h-3 text-white/40" />
        <span className="font-semibold">
          {call.name.replace('mcp__', '').replace(/__/g, '.')}
        </span>
        {call.args ? (
          <span className="text-white/40 text-xs truncate max-w-[200px]">
            ({typeof call.args === 'object' ? JSON.stringify(call.args).slice(0, 50) : String(call.args).slice(0, 50)}...)
          </span>
        ) : null}
      </div>
      
      {percentage !== null && (
        <div className="mt-2 flex items-center gap-2">
          <div className="h-1 flex-1 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-1 bg-emerald-500 transition-all duration-300"
              style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }}
            />
          </div>
          <span className="text-white/60">{percentage}%</span>
        </div>
      )}
      
      {call.message && (
        <div className="mt-1 text-white/50 text-xs">
          {call.message}
        </div>
      )}
    </div>
  )
}