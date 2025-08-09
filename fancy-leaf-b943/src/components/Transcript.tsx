import { useRef, useEffect } from 'react'
import { useMessages } from '../store/messages.state'
import type { SDKMessage, ContentBlock } from '../store/messages.state'
import { ToolCallLine } from './ToolCallLine'
import { 
  Terminal, User, Bot, CheckCircle, XCircle, AlertTriangle, 
  Info, Download, Clock, DollarSign
} from 'lucide-react'
import '../styles/transcript.css'

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
    <div className="transcript">
      {/* Export button */}
      <div className="transcript-header">
        <button
          onClick={exportTranscript}
          className="transcript-export-button"
        >
          <Download className="transcript-export-icon" />
          Export Transcript
        </button>
      </div>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="transcript-messages"
      >
        {messages.length === 0 && (
          <div className="transcript-empty">
            <div className="transcript-empty-content">
              <Terminal className="transcript-empty-icon" />
              <p className="transcript-empty-title">Ready to start a conversation</p>
              <p className="transcript-empty-subtitle">Type a prompt below to begin</p>
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
    <div className="message-system">
      <div className="message-system-header">
        <Info className="message-system-icon" />
        <span className="message-system-title">Session Initialized</span>
      </div>
      <div className="message-system-grid">
        <div className="message-system-item">
          Model: <span className="message-system-value">{message.model}</span>
        </div>
        <div className="message-system-item">
          CWD: <span className="message-system-value message-system-mono">{message.cwd}</span>
        </div>
        <div className="message-system-item">
          Mode: <span className="message-system-value">{message.permissionMode}</span>
        </div>
        {message.session_id && (
          <div className="message-system-item">
            Session: <span className="message-system-value message-system-mono">{message.session_id.slice(0, 8)}</span>
          </div>
        )}
        {message.tools && message.tools.length > 0 && (
          <div className="message-system-item message-system-full">
            Tools: <span className="message-system-value">{message.tools.length} available</span>
          </div>
        )}
        {message.mcp_servers && message.mcp_servers.length > 0 && (
          <div className="message-system-item message-system-full">
            MCP Servers: {message.mcp_servers.map(s => (
              <span key={s.name} className="message-system-badge">
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
    <div className="message">
      <div className="message-avatar message-avatar-user">
        <User className="message-avatar-icon message-avatar-icon-user" />
      </div>
      <div className="message-content">
        <div className="message-label">You</div>
        <div className="message-text">
          {content}
        </div>
      </div>
    </div>
  )
}

function AssistantMessage({ message }: { message: Extract<SDKMessage, { type: 'assistant' }> }) {
  const renderContent = () => {
    if (typeof message.content === 'string') {
      return <div className="message-text">{message.content}</div>
    }

    return (
      <div className="space-y-2">
        {message.content.map((block: ContentBlock, idx: number) => {
          if (block.type === 'text') {
            return (
              <div key={idx} className="message-text">
                {block.text}
              </div>
            )
          }
          if (block.type === 'tool_use') {
            return (
              <div key={idx} className="message-tool-use">
                <div className="message-tool-use-header">
                  <Terminal className="message-tool-use-icon" />
                  <span>Using tool: {block.name}</span>
                </div>
                {block.input !== undefined && block.input !== null && (
                  <pre className="message-tool-use-input">
                    {String(JSON.stringify(block.input, null, 2))}
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
    <div className="message">
      <div className="message-avatar message-avatar-assistant">
        <Bot className="message-avatar-icon message-avatar-icon-assistant" />
      </div>
      <div className="message-content">
        <div className="message-label">Claude</div>
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
    if (isSuccess) return <CheckCircle className="message-result-icon message-result-icon-success" />
    if (isInterrupted) return <AlertTriangle className="message-result-icon message-result-icon-warning" />
    return <XCircle className="message-result-icon message-result-icon-error" />
  }

  const getTitle = () => {
    if (isSuccess) return 'Completed Successfully'
    if (isMaxTurns) return 'Max Turns Reached'
    if (isInterrupted) return 'Interrupted'
    if (isError) return 'Error During Execution'
    return 'Completed'
  }

  const getResultClass = () => {
    if (isSuccess) return 'message-result message-result-success'
    if (isInterrupted) return 'message-result message-result-warning'
    return 'message-result message-result-error'
  }

  return (
    <div className={getResultClass()}>
      <div className="message-result-header">
        {getIcon()}
        <span className="message-result-title">{getTitle()}</span>
      </div>

      <div className="message-result-stats">
        {message.num_turns !== undefined && (
          <div className="message-result-stat">
            <Terminal className="message-result-stat-icon" />
            Turns: <span className="message-result-stat-value">{message.num_turns}</span>
          </div>
        )}
        {message.duration_ms !== undefined && (
          <div className="message-result-stat">
            <Clock className="message-result-stat-icon" />
            Time: <span className="message-result-stat-value">{message.duration_ms}ms</span>
          </div>
        )}
        {message.duration_api_ms !== undefined && (
          <div className="message-result-stat">
            <Clock className="message-result-stat-icon" />
            API: <span className="message-result-stat-value">{message.duration_api_ms}ms</span>
          </div>
        )}
        {message.total_cost_usd !== undefined && (
          <div className="message-result-stat">
            <DollarSign className="message-result-stat-icon" />
            Cost: <span className="message-result-stat-cost">${message.total_cost_usd.toFixed(4)}</span>
          </div>
        )}
      </div>

      {isMaxTurns && (
        <div className="message-result-alert message-result-alert-warning">
          <p>
            Reached the maximum number of turns. Consider increasing max turns in settings.
          </p>
        </div>
      )}

      {message.error && (
        <div className="message-result-alert message-result-alert-error">
          <p>{message.error}</p>
        </div>
      )}

      {message.stderr && (
        <details className="message-result-details">
          <summary className="message-result-details-summary">
            View stderr output
          </summary>
          <pre className="message-result-details-content">
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
    <div className={isError ? 'message-tool-result message-tool-result-error' : 'message-tool-result message-tool-result-success'}>
      <div className="message-tool-result-header">
        {isError ? (
          <XCircle className="message-tool-result-icon message-tool-result-icon-error" />
        ) : (
          <CheckCircle className="message-tool-result-icon message-tool-result-icon-success" />
        )}
        <span className="message-tool-result-label">Tool Result</span>
      </div>
      {message.content !== undefined && message.content !== null && (
        <pre className="message-tool-result-content">
          {typeof message.content === 'string' 
            ? message.content 
            : String(JSON.stringify(message.content, null, 2))}
        </pre>
      )}
    </div>
  )
}

function ChunkMessage({ message }: { message: Extract<SDKMessage, { type: 'chunk' }> }) {
  return (
    <div className="message-chunk">
      {message.data}
    </div>
  )
}