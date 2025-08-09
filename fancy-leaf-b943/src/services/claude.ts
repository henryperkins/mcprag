import { useMessages } from '../store/messages.state';
import { useToolCalls } from '../store/toolCalls.state';

export interface ClaudeMessage {
  type: 'system' | 'assistant' | 'user' | 'result' | 'tool-call' | 'tool-output';
  subtype?: string;
  content?: string;
  error?: string;
  session_id?: string;
  model?: string;
  cwd?: string;
  tools?: string[];
  mcp_servers?: string[];
  permissionMode?: string;
  num_turns?: number;
  duration_ms?: number;
  duration_api_ms?: number;
  total_cost_usd?: number;
  toolName?: string;
  toolArguments?: unknown;
  toolId?: string;
  toolResult?: unknown;
  [key: string]: unknown;
}

export interface ClaudeOptions {
  sessionId?: string;
  maxTurns?: number;
  permissionMode?: 'auto' | 'acceptAll' | 'acceptEdits' | 'confirmAll';
  verbose?: boolean;
  systemPrompt?: string;
  appendSystemPrompt?: string;
  allowedTools?: string[];
  disallowedTools?: string[];
  cwd?: string;
  continueSession?: boolean;
  onMessage?: (message: ClaudeMessage) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

class ClaudeService {
  private abortController: AbortController | null = null;
  private readonly baseUrl: string;
  private sessionId: string | null = null;
  private wsConnection: WebSocket | null = null;

  constructor() {
    // Use Worker gateway endpoint
    this.baseUrl = import.meta.env.VITE_CLAUDE_GATEWAY_URL || '';
    this.initSession();
  }

  private async initSession() {
    try {
      const response = await fetch(`${this.baseUrl}/api/session/create`, {
        method: 'POST',
      });
      const { sessionId } = await response.json();
      this.sessionId = sessionId;
      this.connectWebSocket();
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  }

  private connectWebSocket() {
    if (!this.sessionId) return;
    
    const wsUrl = this.baseUrl.replace(/^http/, 'ws');
    this.wsConnection = new WebSocket(`${wsUrl}/api/session/connect?sessionId=${this.sessionId}`);
    
    this.wsConnection.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'message') {
        // Handle real-time updates from other clients/tabs
        console.log('Real-time update:', data);
      }
    };
    
    this.wsConnection.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  async sendPrompt(prompt: string, options: ClaudeOptions = {}): Promise<void> {
    // Cancel any existing request
    if (this.abortController) {
      this.abortController.abort();
    }

    this.abortController = new AbortController();

    // Determine if this is a slash command
    const isSlashCommand = prompt.trim().startsWith('/');

    try {
      // Use the new exec endpoint that goes through Worker → Bridge
      const response = await fetch(`${this.baseUrl}/api/claude/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          text: prompt,
          opts: {
            sessionId: this.sessionId || options.sessionId,
            maxTurns: options.maxTurns ?? 3,
            permissionMode: options.permissionMode ?? 'acceptEdits',
            systemPrompt: options.systemPrompt,
            allowedTools: options.allowedTools ?? ['Read', 'Write', 'Edit', 'WebSearch'],
            cwd: options.cwd || '/home/azureuser/mcprag',
            continueSession: options.continueSession ?? true,
            forceCLI: isSlashCommand,
          },
        }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          // Handle SSE events
          if (line.startsWith('event: ')) {
            const event = line.slice(7).trim();
            
            if (event === 'done') {
              options.onComplete?.();
              break;
            } else if (event === 'error') {
              // Next line should have the error data
              continue;
            }
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            try {
              const message = JSON.parse(data) as ClaudeMessage;
              this.handleMessage(message, options);
            } catch (e) {
              console.error('Failed to parse message:', e, data);
            }
          } else if (line.startsWith(':')) {
            // Keep-alive comment, ignore
            continue;
          }
        }
      }

      // Handle any remaining data in buffer
      if (buffer.trim() && buffer.startsWith('data: ')) {
        const data = buffer.slice(6).trim();
        if (data !== '[DONE]') {
          try {
            const message = JSON.parse(data) as ClaudeMessage;
            this.handleMessage(message, options);
          } catch (e) {
            console.error('Failed to parse final message:', e, data);
          }
        }
      }

      options.onComplete?.();
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          console.log('Request aborted');
        } else {
          options.onError?.(error);
        }
      }
    } finally {
      this.abortController = null;
    }
  }

  private handleMessage(message: ClaudeMessage, options: ClaudeOptions) {
    // Call the custom handler if provided
    options.onMessage?.(message);

    // Update stores based on message type
    const messagesStore = useMessages.getState();
    const toolCallsStore = useToolCalls.getState();

    switch (message.type) {
      case 'system':
        if (message.subtype === 'init') {
          // Store session info in messages
          messagesStore.addMessage({
            type: 'system',
            subtype: 'init',
            model: message.model || '',
            cwd: message.cwd || '',
            tools: message.tools || [],
            mcp_servers: message.mcp_servers as { name: string; status: string; }[] | undefined,
            permissionMode: message.permissionMode || '',
            session_id: message.session_id,
          });
        }
        break;

      case 'assistant':
        // Add assistant message
        if (message.content) {
          messagesStore.addMessage({
            type: 'assistant',
            content: message.content,
          });
        }
        break;

      case 'tool-call':
        // Track tool call in messages
        if (message.toolName && message.toolId) {
          messagesStore.addMessage({
            type: 'tool_call',
            call_id: message.toolId,
            name: message.toolName,
            arguments: message.toolArguments,
          });
          
          // Also update tool calls store if it has the right methods
          if ('addCall' in toolCallsStore) {
            (toolCallsStore as Record<string, CallableFunction>).addCall({
              id: message.toolId,
              name: message.toolName,
              arguments: message.toolArguments,
            });
          }
        }
        break;

      case 'tool-output':
        // Update tool call result
        if (message.toolId) {
          messagesStore.addMessage({
            type: 'tool_result',
            call_id: message.toolId,
            content: message.toolResult,
            is_error: false,
          });
          
          // Also update tool calls store if it has the right methods
          if ('updateCall' in toolCallsStore) {
            (toolCallsStore as Record<string, CallableFunction>).updateCall(message.toolId, {
              result: message.toolResult,
            });
          }
        }
        break;

      case 'result':
        // Final result message
        messagesStore.addMessage({
          type: 'result',
          subtype: message.error ? 'error_during_execution' : 'success',
          session_id: message.session_id,
          duration_ms: message.duration_ms,
          duration_api_ms: message.duration_api_ms,
          num_turns: message.num_turns,
          total_cost_usd: message.total_cost_usd,
          error: message.error,
        });
        break;
    }
  }

  abort() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  isActive(): boolean {
    return this.abortController !== null;
  }
}

// Export singleton instance
export const claudeService = new ClaudeService();