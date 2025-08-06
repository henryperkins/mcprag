import { useRef, useEffect } from 'react'
import { useMessages } from '../store/messages.state'
import type { SDKMessage, ContentBlock } from '../store/messages.state'
import { ToolCallLine } from './ToolCallLine'
import { 
  Terminal, User, Bot, CheckCircle, XCircle, AlertTriangle, 
  Info, Download, Clock, DollarSign
} from 'lucide-react'

export function Transcript() {
  const { messages } = useMessages()
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const exportTranscript = () => {
    const jsonl = messages.map(m => JSON.stringify(m)).join('\n')
    const blob = new Blob([jsonl], { type: 'application/x-jsonlines' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `claude-transcript-${Date.now()}.jsonl`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex-1 flex flex-col bg-[#0b0f14] overflow-hidden">
      {/* Export button */}
      <div className="flex justify-end p-2 border-b border-white/10">
        <button
          onClick={exportTranscript}
          className="flex items-center gap-2 px-3 py-1 text-xs text-white/60 
                   hover:text-white/80 hover:bg-white/5 rounded transition-colors"
        >
          <Download className="w-3 h-3" />
          Export Transcript
        </button>
      </div>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
      >
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-white/40">
            <div className="text-center">
              <Terminal className="w-12 h-12 mx-auto mb-4 text-white/20" />
              <p className="text-sm">Ready to start a conversation</p>
              <p className="text-xs mt-2">Type a prompt below to begin</p>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <MessageComponent key={index} message={message} />
        ))}
      </div>
    </div>
  )
}

function MessageComponent({ message }: { message: SDKMessage }) {
  switch (message.type) {
    case 'system':
      return <SystemMessage message={message} />
    case 'user':
      return <UserMessage message={message} />
    case 'assistant':
      return <AssistantMessage message={message} />
    case 'result':
      return <ResultMessage message={message} />
    case 'tool_call':
      return <ToolCallLine callId={message.call_id} />
    case 'tool_result':
      return <ToolResultMessage message={message} />
    case 'chunk':
      return <ChunkMessage message={message} />
    default:
      return null
  }
}

function SystemMessage({ message }: { message: Extract<SDKMessage, { type: 'system' }> }) {
  if (message.subtype !== 'init') return null

  return (
    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-xs">
      <div className="flex items-center gap-2 mb-2">
        <Info className="w-4 h-4 text-blue-400" />
        <span className="font-semibold text-blue-400">Session Initialized</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-white/60">
        <div>Model: <span className="text-white/80">{message.model}</span></div>
        <div>CWD: <span className="text-white/80 font-mono">{message.cwd}</span></div>
        <div>Mode: <span className="text-white/80">{message.permissionMode}</span></div>
        {message.session_id && (
          <div>Session: <span className="text-white/80 font-mono">{message.session_id.slice(0, 8)}</span></div>
        )}
        {message.tools && message.tools.length > 0 && (
          <div className="col-span-2">
            Tools: <span className="text-white/80">{message.tools.length} available</span>
          </div>
        )}
        {message.mcp_servers && message.mcp_servers.length > 0 && (
          <div className="col-span-2">
            MCP Servers: {message.mcp_servers.map(s => (
              <span key={s.name} className="ml-2 px-2 py-0.5 bg-white/5 rounded text-white/60">
                {s.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function UserMessage({ message }: { message: Extract<SDKMessage, { type: 'user' }> }) {
  const content = typeof message.content === 'string' 
    ? message.content 
    : message.content.map((b: ContentBlock) => 
        b.type === 'text' ? b.text : `[${b.type}]`
      ).join('')

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 bg-white/10 rounded-full flex items-center justify-center">
        <User className="w-4 h-4 text-white/60" />
      </div>
      <div className="flex-1">
        <div className="text-xs text-white/40 mb-1">You</div>
        <div className="text-white/90 text-sm whitespace-pre-wrap">
          {content}
        </div>
      </div>
    </div>
  )
}

function AssistantMessage({ message }: { message: Extract<SDKMessage, { type: 'assistant' }> }) {
  const renderContent = () => {
    if (typeof message.content === 'string') {
      return <div className="text-white/90 text-sm whitespace-pre-wrap">{message.content}</div>
    }

    return (
      <div className="space-y-2">
        {message.content.map((block: ContentBlock, idx: number) => {
          if (block.type === 'text') {
            return (
              <div key={idx} className="text-white/90 text-sm whitespace-pre-wrap">
                {block.text}
              </div>
            )
          }
          if (block.type === 'tool_use') {
            return (
              <div key={idx} className="bg-white/5 border border-white/10 rounded p-2 text-xs">
                <div className="flex items-center gap-2 text-emerald-400">
                  <Terminal className="w-3 h-3" />
                  <span>Using tool: {block.name}</span>
                </div>
                {block.input && (
                  <pre className="mt-2 text-white/60 overflow-x-auto">
                    {JSON.stringify(block.input, null, 2)}
                  </pre>
                )}
              </div>
            )
          }
          return null
        })}
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 bg-emerald-500/20 rounded-full flex items-center justify-center">
        <Bot className="w-4 h-4 text-emerald-400" />
      </div>
      <div className="flex-1">
        <div className="text-xs text-white/40 mb-1">Claude</div>
        {renderContent()}
      </div>
    </div>
  )
}

function ResultMessage({ message }: { message: Extract<SDKMessage, { type: 'result' }> }) {
  const isSuccess = message.subtype === 'success'
  const isMaxTurns = message.subtype === 'error_max_turns'
  const isError = message.subtype === 'error_during_execution'
  const isInterrupted = message.subtype === 'interrupted'

  const getIcon = () => {
    if (isSuccess) return <CheckCircle className="w-4 h-4 text-emerald-400" />
    if (isInterrupted) return <AlertTriangle className="w-4 h-4 text-yellow-400" />
    return <XCircle className="w-4 h-4 text-red-400" />
  }

  const getTitle = () => {
    if (isSuccess) return 'Completed Successfully'
    if (isMaxTurns) return 'Max Turns Reached'
    if (isInterrupted) return 'Interrupted'
    if (isError) return 'Error During Execution'
    return 'Completed'
  }

  const getBorderColor = () => {
    if (isSuccess) return 'border-emerald-500/30'
    if (isInterrupted) return 'border-yellow-500/30'
    return 'border-red-500/30'
  }

  return (
    <div className={`bg-white/5 border ${getBorderColor()} rounded-lg p-4 text-xs`}>
      <div className="flex items-center gap-2 mb-3">
        {getIcon()}
        <span className="font-semibold text-white/80">{getTitle()}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-white/60">
        {message.num_turns !== undefined && (
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            Turns: <span className="text-white/80">{message.num_turns}</span>
          </div>
        )}
        {message.duration_ms !== undefined && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Time: <span className="text-white/80">{message.duration_ms}ms</span>
          </div>
        )}
        {message.duration_api_ms !== undefined && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            API: <span className="text-white/80">{message.duration_api_ms}ms</span>
          </div>
        )}
        {message.total_cost_usd !== undefined && (
          <div className="flex items-center gap-1">
            <DollarSign className="w-3 h-3" />
            Cost: <span className="text-emerald-400">${message.total_cost_usd.toFixed(4)}</span>
          </div>
        )}
      </div>

      {isMaxTurns && (
        <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded">
          <p className="text-yellow-400 text-xs">
            Reached the maximum number of turns. Consider increasing max turns in settings.
          </p>
        </div>
      )}

      {message.error && (
        <div className="mt-3 p-2 bg-red-500/10 border border-red-500/30 rounded">
          <p className="text-red-400 text-xs font-mono">{message.error}</p>
        </div>
      )}

      {message.stderr && (
        <details className="mt-3">
          <summary className="cursor-pointer text-white/60 hover:text-white/80">
            View stderr output
          </summary>
          <pre className="mt-2 p-2 bg-black/30 rounded text-xs text-white/60 overflow-x-auto">
            {message.stderr}
          </pre>
        </details>
      )}
    </div>
  )
}

function ToolResultMessage({ message }: { message: Extract<SDKMessage, { type: 'tool_result' }> }) {
  const isError = message.is_error

  return (
    <div className={`ml-8 bg-white/5 border ${isError ? 'border-red-500/30' : 'border-white/10'} rounded p-2 text-xs`}>
      <div className="flex items-center gap-2 mb-1">
        {isError ? (
          <XCircle className="w-3 h-3 text-red-400" />
        ) : (
          <CheckCircle className="w-3 h-3 text-emerald-400" />
        )}
        <span className="text-white/60">Tool Result</span>
      </div>
      {message.content && (
        <pre className="text-white/60 overflow-x-auto text-xs">
          {typeof message.content === 'string' 
            ? message.content 
            : JSON.stringify(message.content, null, 2)}
        </pre>
      )}
    </div>
  )
}

function ChunkMessage({ message }: { message: Extract<SDKMessage, { type: 'chunk' }> }) {
  return (
    <div className="text-white/80 text-sm whitespace-pre-wrap font-mono">
      {message.data}
    </div>
  )
}