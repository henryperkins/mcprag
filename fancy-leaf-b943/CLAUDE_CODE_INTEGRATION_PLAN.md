# Claude Code CLI Integration Plan for React/Vite Terminal UI

## Executive Summary

This document outlines the comprehensive implementation plan for integrating a React/Vite web-based terminal UI with the Claude Code CLI running in headless mode. The architecture leverages Server-Sent Events (SSE) for real-time streaming, Cloudflare Workers for edge computing, and a Node.js bridge server for Claude Code CLI/SDK integration.

## Architecture Overview

### 3-Tier Architecture

```
┌─────────────────┐     SSE/WebSocket      ┌──────────────────┐     child_process     ┌──────────────────┐
│   React UI      │ ◄──────────────────► │ Cloudflare Worker│ ◄────────────────► │  Bridge Server   │
│   (Vite)        │                       │   (Edge Proxy)   │                    │  (Node.js)       │
└─────────────────┘                       └──────────────────┘                    └──────────────────┘
                                                    │                                        │
                                                    ▼                                        ▼
                                          ┌──────────────────┐                    ┌──────────────────┐
                                          │   D1/KV/R2      │                    │  Claude Code     │
                                          │   Storage        │                    │  CLI/SDK         │
                                          └──────────────────┘                    └──────────────────┘
```

### Component Responsibilities

1. **React UI** (`src/components/`)
   - Terminal interface with ANSI rendering
   - SSE consumption for real-time updates
   - Session management UI
   - Tool status visualization

2. **Cloudflare Worker** (`worker/index.ts`, `src/worker-gateway.ts`)
   - CORS handling for browser access
   - Request proxying to bridge server
   - Session state via Durable Objects
   - Security enforcement layer
   - Command caching

3. **Bridge Server** (`src/bridge-server.ts`)
   - Claude Code CLI process management
   - SDK integration for typed responses
   - SSE streaming to clients
   - Multi-turn conversation handling
   - MCP server coordination

## Current State Analysis

### Existing Infrastructure

#### ✅ Already Implemented
- Basic SSE streaming setup
- Worker-to-bridge proxying
- Session creation endpoints
- React service with SSE parsing
- Tool call state management
- ANSI text rendering

#### 🔧 Needs Enhancement
- Streaming JSON input for persistent CLI sessions
- SDK message type parsing
- Command discovery and caching
- Permission enforcement layer
- Session persistence and recovery
- MCP server integration

## Implementation Phases

## Phase 1: Bridge Server Streaming JSON Support

### Objective
Enable persistent CLI processes that can handle multiple conversation turns without restarting.

### Implementation Details

```typescript
// src/bridge-server.ts additions

interface CLISession {
  process: ChildProcess;
  lastActivity: number;
  buffer: string;
}

const cliSessions = new Map<string, CLISession>();

// Cleanup idle sessions after 5 minutes
setInterval(() => {
  const now = Date.now();
  for (const [id, session] of cliSessions) {
    if (now - session.lastActivity > 300000) {
      session.process.kill();
      cliSessions.delete(id);
    }
  }
}, 60000);

async function handleStreamingCLI(
  sessionId: string,
  text: string,
  opts: ExecRequest['opts'],
  res: express.Response
) {
  let session = cliSessions.get(sessionId);
  
  if (!session) {
    const proc = spawn('claude', [
      '-p',
      '--output-format', 'stream-json',
      '--input-format', 'stream-json',
      '--allowedTools', opts.allowedTools.join(','),
      '--verbose'
    ]);
    
    session = { 
      process: proc, 
      lastActivity: Date.now(),
      buffer: ''
    };
    
    cliSessions.set(sessionId, session);
    
    // Set up output streaming
    proc.stdout.on('data', (chunk) => {
      session.buffer += chunk.toString();
      const lines = session.buffer.split('\n');
      session.buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.trim()) {
          res.write(`event: message\n`);
          res.write(`data: ${line}\n\n`);
        }
      }
    });
    
    proc.stderr.on('data', (chunk) => {
      console.error('CLI error:', chunk.toString());
      res.write(`event: error\n`);
      res.write(`data: ${JSON.stringify({ error: chunk.toString() })}\n\n`);
    });
    
    proc.on('exit', (code) => {
      cliSessions.delete(sessionId);
      res.write(`event: done\n`);
      res.write(`data: ${JSON.stringify({ code })}\n\n`);
      res.end();
    });
  }
  
  // Send user message as JSONL
  const userMessage = {
    type: 'user',
    message: {
      role: 'user',
      content: [{ type: 'text', text }]
    }
  };
  
  session.process.stdin.write(JSON.stringify(userMessage) + '\n');
  session.lastActivity = Date.now();
}
```

### Deliverables
- [ ] Persistent CLI process management
- [ ] JSONL input/output handling
- [ ] Session cleanup mechanism
- [ ] Error recovery logic

## Phase 2: Worker Gateway Enhancements

### Objective
Add intelligent caching, permission enforcement, and command discovery at the edge.

### Implementation Details

```typescript
// src/worker-gateway.ts additions

interface CommandCache {
  commands: any[];
  timestamp: number;
}

// Command discovery with TTL caching
async function getAvailableCommands(env: Env): Promise<any[]> {
  const cacheKey = 'commands_cache';
  const cached = await env.sessions_kv.get<CommandCache>(cacheKey, 'json');
  
  if (cached && Date.now() - cached.timestamp < 3600000) {
    return cached.commands;
  }
  
  const response = await fetch(`${env.BRIDGE_URL}/api/commands`, {
    headers: { 'Accept': 'application/json' }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch commands: ${response.status}`);
  }
  
  const commands = await response.json();
  
  await env.sessions_kv.put(cacheKey, JSON.stringify({
    commands,
    timestamp: Date.now()
  }), { 
    expirationTtl: 3600 
  });
  
  return commands;
}

// Role-based permission system
interface UserContext {
  role: 'admin' | 'developer' | 'viewer' | 'default';
  organization?: string;
  allowedRepositories?: string[];
}

function getToolPermissions(context: UserContext): string[] {
  const baseTools = ['Read', 'WebSearch', 'Grep', 'LS', 'Glob'];
  
  const rolePermissions = {
    admin: [
      ...baseTools, 
      'Write', 'Edit', 'MultiEdit', 
      'Bash', 'Git', 
      'NotebookEdit', 'TodoWrite'
    ],
    developer: [
      ...baseTools, 
      'Write', 'Edit', 'MultiEdit', 
      'Git', 'TodoWrite'
    ],
    viewer: baseTools,
    default: [...baseTools, 'Edit'] // Safe default
  };
  
  return rolePermissions[context.role] || rolePermissions.default;
}

// Apply permissions to request
async function enforcePermissions(
  request: Request, 
  env: Env
): Promise<any> {
  const body = await request.json();
  
  // Extract user context from JWT or session
  const context = await getUserContext(request, env);
  
  // Override tools based on permissions
  const allowedTools = getToolPermissions(context);
  
  body.opts = {
    ...body.opts,
    allowedTools: body.opts.allowedTools?.filter(
      tool => allowedTools.includes(tool)
    ) || allowedTools,
    disallowedTools: [
      'Bash(rm *)',
      'Bash(sudo *)',
      'Edit(.env)',
      'Write(.env)'
    ]
  };
  
  return body;
}
```

### Deliverables
- [ ] Command discovery endpoint with caching
- [ ] Role-based permission system
- [ ] Tool allowlist/denylist enforcement
- [ ] Request sanitization layer

## Phase 3: React Service SDK Message Parsing

### Objective
Properly parse and handle all SDK message types for a rich UI experience.

### Implementation Details

```typescript
// src/services/claude.ts enhancements

// Comprehensive SDK message types
interface SDKMessage {
  type: 'system' | 'assistant' | 'user' | 'result';
  subtype?: string;
  session_id: string;
}

interface SDKSystemInit extends SDKMessage {
  type: 'system';
  subtype: 'init';
  apiKeySource: string;
  cwd: string;
  tools: string[];
  mcp_servers: Array<{
    name: string;
    status: string;
  }>;
  model: string;
  permissionMode: string;
}

interface SDKAssistantMessage extends SDKMessage {
  type: 'assistant';
  message: {
    id: string;
    role: 'assistant';
    content: Array<
      | { type: 'text'; text: string }
      | { 
          type: 'tool_use'; 
          id: string; 
          name: string; 
          input: any 
        }
    >;
    model: string;
    usage?: {
      input_tokens: number;
      output_tokens: number;
    };
  };
}

interface SDKUserMessage extends SDKMessage {
  type: 'user';
  message: {
    role: 'user';
    content: Array<{ type: 'text'; text: string }>;
  };
}

interface SDKResultMessage extends SDKMessage {
  type: 'result';
  subtype: 'success' | 'error_max_turns' | 'error_during_execution';
  result?: string;
  total_cost_usd: number;
  duration_ms: number;
  duration_api_ms: number;
  num_turns: number;
  is_error: boolean;
}

class EnhancedClaudeService extends ClaudeService {
  private availableTools: string[] = [];
  private mcpServers: Array<{ name: string; status: string }> = [];
  private currentModel: string = '';
  
  private handleSDKMessage(data: SDKMessage) {
    const { addMessage, updateMessage } = useMessages.getState();
    const { addToolCall, updateToolCall } = useToolCalls.getState();
    
    switch (data.type) {
      case 'system':
        this.handleSystemMessage(data as SDKSystemInit);
        break;
        
      case 'assistant':
        this.handleAssistantMessage(data as SDKAssistantMessage);
        break;
        
      case 'user':
        this.handleUserMessage(data as SDKUserMessage);
        break;
        
      case 'result':
        this.handleResultMessage(data as SDKResultMessage);
        break;
    }
  }
  
  private handleSystemMessage(data: SDKSystemInit) {
    if (data.subtype === 'init') {
      this.sessionId = data.session_id;
      this.availableTools = data.tools;
      this.mcpServers = data.mcp_servers;
      this.currentModel = data.model;
      
      // Notify UI components
      this.emit('tools-update', {
        tools: data.tools,
        mcpServers: data.mcp_servers,
        model: data.model
      });
      
      // Add system message to transcript
      useMessages.getState().addMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `Session initialized\nModel: ${data.model}\nTools: ${data.tools.length} available`,
        metadata: {
          sessionId: data.session_id,
          cwd: data.cwd,
          permissionMode: data.permissionMode
        }
      });
    }
  }
  
  private handleAssistantMessage(data: SDKAssistantMessage) {
    const messageId = crypto.randomUUID();
    let textContent = '';
    const toolCalls: any[] = [];
    
    // Parse content blocks
    for (const block of data.message.content || []) {
      if (block.type === 'text') {
        textContent += block.text;
      } else if (block.type === 'tool_use') {
        const toolCall = {
          id: block.id,
          name: block.name,
          arguments: block.input,
          status: 'pending' as const,
          timestamp: Date.now()
        };
        
        toolCalls.push(toolCall);
        
        // Add to tool calls store
        useToolCalls.getState().addToolCall(toolCall);
      }
    }
    
    // Add assistant message
    if (textContent || toolCalls.length > 0) {
      useMessages.getState().addMessage({
        id: messageId,
        role: 'assistant',
        content: textContent,
        toolCalls: toolCalls.map(tc => tc.id),
        metadata: {
          model: data.message.model,
          usage: data.message.usage
        }
      });
    }
  }
  
  private handleResultMessage(data: SDKResultMessage) {
    this.lastSessionId = data.session_id;
    
    // Store session for continuation
    useSession.getState().addSession({
      id: data.session_id,
      timestamp: Date.now(),
      title: this.generateSessionTitle(),
      metadata: {
        cost: data.total_cost_usd,
        duration: data.duration_ms,
        turns: data.num_turns,
        error: data.is_error
      }
    });
    
    // Add completion message if there's a result
    if (data.result) {
      useMessages.getState().addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.result,
        metadata: {
          isFinal: true,
          cost: data.total_cost_usd,
          duration: data.duration_ms,
          turns: data.num_turns
        }
      });
    }
    
    // Notify completion
    this.emit('session-complete', {
      sessionId: data.session_id,
      success: data.subtype === 'success',
      error: data.is_error ? data.subtype : null
    });
  }
}
```

### Deliverables
- [ ] Complete SDK message type definitions
- [ ] Message parsing and state updates
- [ ] Tool call tracking
- [ ] Session metadata storage

## Phase 4: UI Components for Tools and MCP

### Objective
Create React components to visualize available tools, MCP servers, and execution status.

### New Components

#### ToolsPanel.tsx
```tsx
import { useEffect, useState } from 'react';
import { Shield, Tool, Server, CheckCircle, XCircle } from 'lucide-react';
import { claudeService } from '../services/claude';

interface Tool {
  name: string;
  category: 'file' | 'search' | 'edit' | 'system' | 'mcp';
  enabled: boolean;
}

interface MCPServer {
  name: string;
  status: 'connected' | 'disconnected' | 'error';
  tools: string[];
}

export function ToolsPanel() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [filter, setFilter] = useState<string>('all');
  
  useEffect(() => {
    const unsubscribe = claudeService.on('tools-update', (data) => {
      // Categorize tools
      const categorizedTools = data.tools.map(name => ({
        name,
        category: getCategoryForTool(name),
        enabled: true
      }));
      
      setTools(categorizedTools);
      setMcpServers(data.mcpServers);
    });
    
    return unsubscribe;
  }, []);
  
  const getCategoryForTool = (name: string): Tool['category'] => {
    if (name.startsWith('mcp__')) return 'mcp';
    if (['Read', 'Write', 'LS', 'Glob'].includes(name)) return 'file';
    if (['Edit', 'MultiEdit', 'NotebookEdit'].includes(name)) return 'edit';
    if (['Grep', 'WebSearch'].includes(name)) return 'search';
    return 'system';
  };
  
  const filteredTools = filter === 'all' 
    ? tools 
    : tools.filter(t => t.category === filter);
  
  return (
    <div className="tools-panel">
      {/* Filter tabs */}
      <div className="tool-filters">
        {['all', 'file', 'edit', 'search', 'system', 'mcp'].map(cat => (
          <button
            key={cat}
            className={`filter-tab ${filter === cat ? 'active' : ''}`}
            onClick={() => setFilter(cat)}
          >
            {cat}
          </button>
        ))}
      </div>
      
      {/* Tools grid */}
      <div className="tools-section">
        <h3><Tool size={16} /> Available Tools ({filteredTools.length})</h3>
        <div className="tools-grid">
          {filteredTools.map(tool => (
            <div 
              key={tool.name} 
              className={`tool-chip ${tool.enabled ? 'enabled' : 'disabled'}`}
              title={`Category: ${tool.category}`}
            >
              <Shield size={12} className={tool.enabled ? 'text-green' : 'text-gray'} />
              {tool.name}
            </div>
          ))}
        </div>
      </div>
      
      {/* MCP servers */}
      {mcpServers.length > 0 && (
        <div className="mcp-section">
          <h3><Server size={16} /> MCP Servers</h3>
          {mcpServers.map(server => (
            <div key={server.name} className="mcp-server">
              <span className={`status-indicator ${server.status}`}>
                {server.status === 'connected' ? (
                  <CheckCircle size={14} />
                ) : (
                  <XCircle size={14} />
                )}
              </span>
              <span className="server-name">{server.name}</span>
              <span className="tool-count">({server.tools.length} tools)</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

#### CommandPalette.tsx
```tsx
import { useState, useEffect } from 'react';
import { Command, Search } from 'lucide-react';

interface SlashCommand {
  name: string;
  description: string;
  category: 'builtin' | 'custom' | 'mcp';
  arguments?: string[];
}

export function CommandPalette({ onExecute }) {
  const [commands, setCommands] = useState<SlashCommand[]>([]);
  const [search, setSearch] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  
  useEffect(() => {
    // Fetch available commands
    fetch('/api/commands')
      .then(res => res.json())
      .then(data => setCommands(data));
  }, []);
  
  const filteredCommands = commands.filter(cmd =>
    cmd.name.toLowerCase().includes(search.toLowerCase()) ||
    cmd.description.toLowerCase().includes(search.toLowerCase())
  );
  
  return (
    <>
      <button 
        className="command-trigger"
        onClick={() => setIsOpen(true)}
      >
        <Command size={16} />
        Commands
      </button>
      
      {isOpen && (
        <div className="command-palette-overlay" onClick={() => setIsOpen(false)}>
          <div className="command-palette" onClick={e => e.stopPropagation()}>
            <div className="command-search">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search commands..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                autoFocus
              />
            </div>
            
            <div className="command-list">
              {filteredCommands.map(cmd => (
                <button
                  key={cmd.name}
                  className="command-item"
                  onClick={() => {
                    onExecute(cmd);
                    setIsOpen(false);
                  }}
                >
                  <span className="command-name">{cmd.name}</span>
                  <span className="command-desc">{cmd.description}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
```

### Deliverables
- [ ] ToolsPanel component with categorization
- [ ] CommandPalette for slash commands
- [ ] MCP server status visualization
- [ ] Tool execution status indicators

## Phase 5: Session Persistence and Recovery

### Objective
Implement robust session management with persistence across page refreshes and browser restarts.

### Implementation Details

```typescript
// src/store/session.state.ts

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface Session {
  id: string;
  timestamp: number;
  title: string;
  messages: number;
  cost?: number;
  duration?: number;
}

interface SessionState {
  currentSessionId: string | null;
  sessions: Session[];
  maxSessions: number;
  
  // Actions
  createSession: () => string;
  resumeSession: (id: string) => Promise<void>;
  continueLastSession: () => Promise<void>;
  deleteSession: (id: string) => void;
  clearOldSessions: () => void;
  exportSession: (id: string) => Promise<void>;
}

export const useSession = create<SessionState>()(
  persist(
    (set, get) => ({
      currentSessionId: null,
      sessions: [],
      maxSessions: 20,
      
      createSession: () => {
        const id = crypto.randomUUID();
        const session: Session = {
          id,
          timestamp: Date.now(),
          title: `Session ${new Date().toLocaleString()}`,
          messages: 0
        };
        
        set(state => ({
          currentSessionId: id,
          sessions: [session, ...state.sessions].slice(0, state.maxSessions)
        }));
        
        return id;
      },
      
      resumeSession: async (id: string) => {
        const session = get().sessions.find(s => s.id === id);
        if (!session) {
          throw new Error(`Session ${id} not found`);
        }
        
        set({ currentSessionId: id });
        
        // Load messages from KV/D1
        await claudeService.loadSession(id);
      },
      
      continueLastSession: async () => {
        const sessions = get().sessions;
        if (sessions.length === 0) {
          throw new Error('No sessions to continue');
        }
        
        await get().resumeSession(sessions[0].id);
      },
      
      deleteSession: (id: string) => {
        set(state => ({
          sessions: state.sessions.filter(s => s.id !== id),
          currentSessionId: state.currentSessionId === id 
            ? null 
            : state.currentSessionId
        }));
        
        // Delete from backend
        claudeService.deleteSession(id);
      },
      
      clearOldSessions: () => {
        const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7 days
        
        set(state => ({
          sessions: state.sessions.filter(s => s.timestamp > cutoff)
        }));
      },
      
      exportSession: async (id: string) => {
        const session = get().sessions.find(s => s.id === id);
        if (!session) return;
        
        const data = await claudeService.exportSession(id);
        
        // Download as JSON
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `claude-session-${id}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    }),
    {
      name: 'claude-sessions',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions.slice(0, state.maxSessions),
        maxSessions: state.maxSessions
      })
    }
  )
);
```

### Worker Session Storage
```typescript
// src/worker-gateway.ts additions

async function persistSession(
  env: Env,
  sessionId: string,
  data: any
): Promise<void> {
  // Store in D1 for long-term persistence
  await env.DB.prepare(`
    INSERT OR REPLACE INTO sessions (
      id, 
      created_at, 
      updated_at, 
      data,
      message_count,
      total_cost_usd
    ) VALUES (?, ?, ?, ?, ?, ?)
  `).bind(
    sessionId,
    data.created_at || Date.now(),
    Date.now(),
    JSON.stringify(data),
    data.message_count || 0,
    data.total_cost_usd || 0
  ).run();
  
  // Also cache in KV for fast access
  await env.sessions_kv.put(
    `session:${sessionId}`,
    JSON.stringify(data),
    { expirationTtl: 86400 * 7 } // 7 days
  );
}

async function loadSession(
  env: Env,
  sessionId: string
): Promise<any> {
  // Try KV first (faster)
  const cached = await env.sessions_kv.get(`session:${sessionId}`, 'json');
  if (cached) return cached;
  
  // Fall back to D1
  const result = await env.DB.prepare(`
    SELECT data FROM sessions WHERE id = ?
  `).bind(sessionId).first();
  
  if (result?.data) {
    const data = JSON.parse(result.data as string);
    
    // Re-cache in KV
    await env.sessions_kv.put(
      `session:${sessionId}`,
      JSON.stringify(data),
      { expirationTtl: 86400 * 7 }
    );
    
    return data;
  }
  
  return null;
}
```

### Deliverables
- [ ] Session state management with Zustand
- [ ] LocalStorage persistence
- [ ] D1/KV backend storage
- [ ] Session export/import functionality
- [ ] Automatic cleanup of old sessions

## Configuration Files

### MCP Server Configuration (.mcp.json)
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/azureuser/mcprag"
      ]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

### Hook Configuration (hooks.json)
```json
{
  "hooks": {
    "PreToolUse": {
      "Edit": {
        "script": "./hooks/protect-files.js",
        "config": {
          "protected": [".env", ".git", "node_modules"]
        }
      },
      "Write": {
        "script": "./hooks/protect-files.js",
        "config": {
          "protected": [".env", ".git", "node_modules"]
        }
      },
      "Bash": {
        "script": "./hooks/validate-command.js",
        "config": {
          "forbidden": ["rm -rf", "sudo", "chmod 777"]
        }
      }
    },
    "UserPromptSubmit": {
      "script": "./hooks/sanitize-input.js",
      "config": {
        "maxLength": 10000,
        "stripSecrets": true
      }
    },
    "PostToolUse": {
      "Edit": "./hooks/format-code.js",
      "Write": "./hooks/format-code.js"
    }
  }
}
```

### Environment Variables
```bash
# .env.example

# Bridge Server
ANTHROPIC_API_KEY=sk-ant-...
BRIDGE_PORT=8787
BRIDGE_HOST=localhost

# Cloudflare Worker
BRIDGE_URL=http://localhost:8787/exec
R2_PUBLIC_BASE=https://claude-r2.example.com/user-assets

# MCP Servers
GITHUB_TOKEN=ghp_...
DATABASE_URL=postgresql://...

# Security
ACCESS_JWT_SECRET=...
TURNSTILE_SECRET=...

# Feature Flags
ENABLE_MCP_SERVERS=true
ENABLE_STREAMING_SESSIONS=true
MAX_SESSIONS_PER_USER=10
SESSION_TIMEOUT_MINUTES=30
```

## Security Considerations

### 1. Tool Access Control
- **Never expose raw Bash access** in web context
- Use **allowedTools allowlist** per user role
- Implement **disallowedTools** for dangerous patterns
- Log all tool executions to audit trail

### 2. Input Sanitization
```typescript
function sanitizeUserInput(input: string): string {
  // Remove potential command injection attempts
  const dangerous = [
    /\$\(.*\)/g,  // Command substitution
    /`.*`/g,      // Backticks
    /;.*$/g,      // Command chaining
    /\|\|/g,      // OR operator
    /&&/g         // AND operator
  ];
  
  let sanitized = input;
  for (const pattern of dangerous) {
    sanitized = sanitized.replace(pattern, '');
  }
  
  // Truncate to reasonable length
  return sanitized.slice(0, 10000);
}
```

### 3. Rate Limiting
```typescript
// Worker rate limiting
const rateLimiter = {
  windowMs: 60000, // 1 minute
  maxRequests: 30,
  
  async checkLimit(clientId: string, env: Env): Promise<boolean> {
    const key = `rate:${clientId}`;
    const count = await env.sessions_kv.get(key);
    
    if (!count) {
      await env.sessions_kv.put(key, '1', { expirationTtl: 60 });
      return true;
    }
    
    const current = parseInt(count);
    if (current >= this.maxRequests) {
      return false;
    }
    
    await env.sessions_kv.put(key, String(current + 1), { expirationTtl: 60 });
    return true;
  }
};
```

### 4. Session Security
- Use secure session IDs (UUIDs)
- Implement session expiration
- Validate session ownership
- Encrypt sensitive session data

## Performance Optimizations

### 1. Connection Pooling
```typescript
// Reuse CLI processes for same session
const processPool = new Map<string, ChildProcess>();

function getOrCreateProcess(sessionId: string): ChildProcess {
  if (!processPool.has(sessionId)) {
    const proc = spawn('claude', ['--streaming']);
    processPool.set(sessionId, proc);
    
    // Cleanup on exit
    proc.on('exit', () => {
      processPool.delete(sessionId);
    });
  }
  
  return processPool.get(sessionId)!;
}
```

### 2. Response Caching
```typescript
// Cache command discovery and common responses
const responseCache = new LRU<string, any>({
  max: 100,
  ttl: 1000 * 60 * 5 // 5 minutes
});

async function getCachedOrFetch(key: string, fetcher: () => Promise<any>) {
  const cached = responseCache.get(key);
  if (cached) return cached;
  
  const fresh = await fetcher();
  responseCache.set(key, fresh);
  return fresh;
}
```

### 3. Streaming Optimizations
- Use chunked transfer encoding
- Implement backpressure handling
- Buffer management for large responses
- Compression for non-SSE responses

## Testing Strategy

### Unit Tests
```typescript
// Example test for permission system
describe('Permission System', () => {
  it('should filter tools based on role', () => {
    const context = { role: 'viewer' };
    const tools = getToolPermissions(context);
    
    expect(tools).toContain('Read');
    expect(tools).not.toContain('Write');
    expect(tools).not.toContain('Bash');
  });
});
```

### Integration Tests
```typescript
// Test end-to-end flow
describe('Claude Integration', () => {
  it('should handle streaming session', async () => {
    const service = new ClaudeService();
    const messages = [];
    
    await service.sendPrompt('Hello', {
      onMessage: (msg) => messages.push(msg)
    });
    
    expect(messages).toContainEqual(
      expect.objectContaining({ type: 'system', subtype: 'init' })
    );
  });
});
```

### E2E Tests
```typescript
// Playwright test for UI flow
test('complete conversation flow', async ({ page }) => {
  await page.goto('/');
  
  // Type prompt
  await page.fill('[data-testid="prompt-input"]', 'Explain React hooks');
  await page.press('[data-testid="prompt-input"]', 'Enter');
  
  // Wait for response
  await page.waitForSelector('[data-testid="assistant-message"]');
  
  // Verify tools panel
  await expect(page.locator('[data-testid="tools-panel"]')).toBeVisible();
});
```

## Deployment Checklist

### Pre-deployment
- [ ] All tests passing
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Environment variables configured

### Deployment Steps
1. Deploy Bridge Server to VM/Container
2. Deploy Worker to Cloudflare
3. Configure D1 database schema
4. Set up KV namespaces
5. Configure R2 buckets
6. Update DNS records
7. Enable monitoring

### Post-deployment
- [ ] Smoke tests passing
- [ ] Monitoring dashboards active
- [ ] Error tracking enabled
- [ ] Performance metrics baseline established
- [ ] Security scanning completed

## Monitoring and Observability

### Key Metrics
- Session creation rate
- Message throughput
- Tool execution count
- Error rate by type
- P95 response latency
- Active session count
- Cost per session

### Logging Strategy
```typescript
// Structured logging
const logger = {
  info: (msg: string, meta?: any) => {
    console.log(JSON.stringify({
      level: 'info',
      message: msg,
      timestamp: new Date().toISOString(),
      ...meta
    }));
  },
  
  error: (msg: string, error?: Error, meta?: any) => {
    console.error(JSON.stringify({
      level: 'error',
      message: msg,
      error: error?.stack,
      timestamp: new Date().toISOString(),
      ...meta
    }));
  }
};
```

### Alerting Rules
- High error rate (> 1% of requests)
- Slow response time (P95 > 5s)
- Session creation failures
- MCP server disconnections
- Memory/CPU usage spikes

## Rollback Plan

### Rollback Triggers
- Error rate > 5%
- P95 latency > 10s
- Critical security vulnerability
- Data corruption detected

### Rollback Steps
1. Switch Worker to previous version
2. Revert Bridge Server deployment
3. Clear corrupted cache entries
4. Restore database from backup
5. Notify affected users

## Success Criteria

### Technical Metrics
- ✅ < 200ms time to first byte
- ✅ < 50ms streaming latency
- ✅ 99.9% uptime
- ✅ Zero security incidents
- ✅ < 100MB memory per session

### User Experience Metrics
- ✅ Seamless session continuation
- ✅ Real-time streaming updates
- ✅ Tool execution visibility
- ✅ Command discovery working
- ✅ Error recovery graceful

## Appendix

### Related Documentation
- [Claude Code SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)

### Example Implementations
- [Claude Code SDK TypeScript Examples](https://github.com/anthropics/claude-code-sdk-typescript/examples)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)
- [SSE Client Implementation](https://github.com/EventSource/eventsource)

### Troubleshooting Guide
1. **Session not persisting**: Check KV/D1 write permissions
2. **Tools not available**: Verify MCP server configuration
3. **Streaming stops**: Check for proxy timeouts
4. **High latency**: Review Worker placement and caching
5. **Memory issues**: Implement process pooling limits

---

*Last Updated: 2025-08-11*
*Version: 1.0.0*
*Status: Implementation Ready*