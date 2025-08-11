import { useMessages } from '../store/messages.state';
import { useToolCalls } from '../store/toolCalls.state';
import { useSession } from '../store/session.state';
import {
  type SDKMessage,
  type SDKAssistantMessage,
  type SDKUserMessage,
  type SDKResultMessage,
  type ToolCall,
  isSystemInit,
  isAssistantMessage,
  isUserMessage,
  isResultMessage,
  isToolUse,
  isTextContent
} from '../types/sdk-messages';

// Re-export the message types for backward compatibility
export type ClaudeMessage = SDKMessage;

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
  private eventListeners: Map<string, Set<Function>> = new Map();
  private availableTools: string[] = [];
  private mcpServers: any[] = [];

  constructor() {
    // Use Worker gateway endpoint
    this.baseUrl = import.meta.env.VITE_CLAUDE_GATEWAY_URL || '';
    this.initSession();
    
    // Set up event listener for tools info requests
    this.on('request-tools-info', () => {
      // Emit current tools state if available
      if (this.availableTools.length > 0 || this.mcpServers.length > 0) {
        this.emit('tools-update', {
          tools: this.availableTools,
          mcpServers: this.mcpServers
        });
      }
    });
  }

  // Event emitter methods
  on(event: string, callback: Function): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      const listeners = this.eventListeners.get(event);
      if (listeners) {
        listeners.delete(callback);
      }
    };
  }

  emit(event: string, data?: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
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

  private handleMessage(message: SDKMessage, options: ClaudeOptions) {
    // Call the custom handler if provided
    options.onMessage?.(message);

    // Update stores based on message type
    const messagesStore = useMessages.getState();
    const toolCallsStore = useToolCalls.getState();
    const sessionStore = useSession.getState();

    if (isSystemInit(message)) {
      // System initialization
      this.sessionId = message.session_id || this.sessionId;
      this.availableTools = message.tools || [];
      this.mcpServers = message.mcp_servers || [];
      
      messagesStore.addMessage({
        type: 'system',
        subtype: 'init',
        model: message.model,
        cwd: message.cwd,
        tools: message.tools,
        mcp_servers: message.mcp_servers,
        permissionMode: message.permissionMode,
        session_id: message.session_id,
      });
      
      // Update session store with available tools
      if ('setAvailableTools' in sessionStore) {
        (sessionStore as any).setAvailableTools(message.tools);
      }
      
      // Store MCP servers if available
      if (message.mcp_servers && 'setMcpServers' in sessionStore) {
        (sessionStore as any).setMcpServers(message.mcp_servers);
      }
      
      // Emit tools update event for UI components
      this.emit('tools-update', {
        tools: this.availableTools,
        mcpServers: this.mcpServers,
        model: message.model
      });
    } else if (isAssistantMessage(message)) {
      // Assistant message with content blocks
      const assistantMsg = message as SDKAssistantMessage;
      let textContent = '';
      const toolCalls: ToolCall[] = [];
      
      for (const block of assistantMsg.message.content || []) {
        if (isTextContent(block)) {
          textContent += block.text;
        } else if (isToolUse(block)) {
          const toolCall: ToolCall = {
            id: block.id,
            name: block.name,
            arguments: block.input,
            status: 'pending',
            timestamp: Date.now()
          };
          
          toolCalls.push(toolCall);
          
          // Add to tool calls store - use startTool instead of addToolCall
          if ('startTool' in toolCallsStore) {
            (toolCallsStore as any).startTool(block.name, block.id);
          }
        }
      }
      
      // Add message to store
      if (textContent || toolCalls.length > 0) {
        messagesStore.addMessage({
          id: assistantMsg.message.id,
          type: 'assistant',
          content: textContent,
          toolCalls: toolCalls.map(tc => tc.id),
          model: assistantMsg.message.model,
          usage: assistantMsg.message.usage,
          stop_reason: assistantMsg.message.stop_reason,
        });
      }
    } else if (isUserMessage(message)) {
      // User message
      const userMsg = message as SDKUserMessage;
      let textContent = '';
      
      for (const block of userMsg.message.content || []) {
        if (isTextContent(block)) {
          textContent += block.text;
        }
      }
      
      if (textContent) {
        messagesStore.addMessage({
          type: 'user',
          content: textContent,
        });
      }
    } else if (isResultMessage(message)) {
      // Result message - session complete
      const resultMsg = message as SDKResultMessage;
      
      messagesStore.addMessage({
        type: 'result',
        subtype: resultMsg.subtype,
        session_id: resultMsg.session_id,
        duration_ms: resultMsg.duration_ms,
        duration_api_ms: resultMsg.duration_api_ms,
        num_turns: resultMsg.num_turns,
        total_cost_usd: resultMsg.total_cost_usd,
        is_error: resultMsg.is_error,
        error: resultMsg.error_message,
        result: resultMsg.result,
      });
      
      // Update session metadata
      if ('updateSessionMetadata' in sessionStore) {
        (sessionStore as any).updateSessionMetadata({
          id: resultMsg.session_id,
          totalCost: resultMsg.total_cost_usd,
          totalDuration: resultMsg.duration_ms,
          lastActivity: Date.now()
        });
      }
      
      // Mark session as complete
      if (resultMsg.subtype === 'success') {
        this.sessionId = null; // Reset for next session
      }
    } else {
      // Handle legacy message formats for backward compatibility
      this.handleLegacyMessage(message);
    }
  }
  
  private handleLegacyMessage(message: any) {
    const messagesStore = useMessages.getState();
    const toolCallsStore = useToolCalls.getState();
    
    // Legacy tool-call and tool-output handling
    if (message.type === 'tool-call' && message.toolName && message.toolId) {
      messagesStore.addMessage({
        type: 'tool_call',
        call_id: message.toolId,
        name: message.toolName,
        arguments: message.toolArguments,
      });
      
      if ('addCall' in toolCallsStore) {
        (toolCallsStore as any).addCall({
          id: message.toolId,
          name: message.toolName,
          arguments: message.toolArguments,
        });
      }
    } else if (message.type === 'tool-output' && message.toolId) {
      messagesStore.addMessage({
        type: 'tool_result',
        call_id: message.toolId,
        content: message.toolResult,
        is_error: false,
      });
      
      if ('updateCall' in toolCallsStore) {
        (toolCallsStore as any).updateCall(message.toolId, {
          result: message.toolResult,
        });
      }
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
