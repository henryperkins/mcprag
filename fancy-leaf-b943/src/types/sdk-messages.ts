/**
 * Claude Code SDK Message Types
 * Based on Claude Code SDK documentation
 */

// Base message structure
export interface SDKMessage {
  type: 'system' | 'assistant' | 'user' | 'result';
  subtype?: string;
  session_id?: string;
  message_index?: number;
  timestamp?: number;
}

// System messages
export interface SDKSystemInit extends SDKMessage {
  type: 'system';
  subtype: 'init';
  apiKeySource: string;
  cwd: string;
  tools: string[];
  mcp_servers?: Array<{
    name: string;
    status: 'connected' | 'disconnected' | 'error';
    tools?: string[];
  }>;
  model: string;
  permissionMode: 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan';
  version?: string;
}

export interface SDKSystemStatus extends SDKMessage {
  type: 'system';
  subtype: 'status';
  status: string;
  details?: any;
}

// Content blocks
export interface TextContent {
  type: 'text';
  text: string;
}

export interface ToolUseContent {
  type: 'tool_use';
  id: string;
  name: string;
  input: any;
}

export interface ToolResultContent {
  type: 'tool_result';
  tool_use_id: string;
  content: string | Array<{ type: 'text' | 'image'; text?: string; source?: any }>;
  is_error?: boolean;
}

// Assistant messages
export interface SDKAssistantMessage extends SDKMessage {
  type: 'assistant';
  message: {
    id: string;
    role: 'assistant';
    content: Array<TextContent | ToolUseContent>;
    model: string;
    stop_reason?: 'end_turn' | 'max_tokens' | 'stop_sequence' | 'tool_use';
    stop_sequence?: string;
    usage?: {
      input_tokens: number;
      output_tokens: number;
      cache_creation_input_tokens?: number;
      cache_read_input_tokens?: number;
    };
  };
}

// User messages
export interface SDKUserMessage extends SDKMessage {
  type: 'user';
  message: {
    role: 'user';
    content: Array<TextContent>;
  };
}

// Result messages
export interface SDKResultMessage extends SDKMessage {
  type: 'result';
  subtype: 'success' | 'error_max_turns' | 'error_during_execution' | 'error_invalid_request';
  result?: string;
  total_cost_usd?: number;
  duration_ms?: number;
  duration_api_ms?: number;
  num_turns?: number;
  is_error: boolean;
  error_message?: string;
  session_id: string;
}

// Tool execution tracking
export interface ToolCall {
  id: string;
  name: string;
  arguments: any;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  timestamp: number;
  duration?: number;
  result?: any;
  error?: string;
}

// Session metadata
export interface SessionMetadata {
  id: string;
  created: number;
  lastActivity: number;
  title?: string;
  model?: string;
  tools?: string[];
  messageCount: number;
  totalCost?: number;
  totalDuration?: number;
}

// Stream event types
export type StreamEventType = 
  | 'message'
  | 'text'
  | 'log'
  | 'error'
  | 'done'
  | 'session_ended'
  | 'keepalive';

export interface StreamEvent {
  event: StreamEventType;
  data: any;
}

// Helper type guards
export function isSystemInit(msg: SDKMessage): msg is SDKSystemInit {
  return msg.type === 'system' && msg.subtype === 'init';
}

export function isAssistantMessage(msg: SDKMessage): msg is SDKAssistantMessage {
  return msg.type === 'assistant';
}

export function isUserMessage(msg: SDKMessage): msg is SDKUserMessage {
  return msg.type === 'user';
}

export function isResultMessage(msg: SDKMessage): msg is SDKResultMessage {
  return msg.type === 'result';
}

export function isToolUse(content: any): content is ToolUseContent {
  return content?.type === 'tool_use';
}

export function isToolResult(content: any): content is ToolResultContent {
  return content?.type === 'tool_result';
}

export function isTextContent(content: any): content is TextContent {
  return content?.type === 'text';
}