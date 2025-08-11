/**
 * Claude Code Bridge Server
 * Runs on VM/regular host with Node.js runtime
 * Decides between SDK and CLI based on command type
 */

import express from 'express';
import cors from 'cors';
import { spawn, ChildProcess } from 'node:child_process';
import { query } from '@anthropic-ai/claude-code';
import { randomUUID } from 'node:crypto';

const app = express();
app.use(cors());
app.use(express.json());

interface ExecRequest {
  text: string;
  opts?: {
    cwd?: string;
    allowedTools?: string[];
    maxTurns?: number;
    sessionId?: string;
    continueSession?: boolean;
    forceCLI?: boolean;
    permissionMode?: 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan';
    systemPrompt?: string;
  };
}

/**
 * Persistent CLI session management
 */
interface CLISession {
  id: string;
  process: ChildProcess;
  lastActivity: number;
  buffer: string;
  messageCount: number;
  created: number;
  metadata?: {
    model?: string;
    tools?: string[];
    cwd?: string;
  };
}

// Store for active CLI sessions
const cliSessions = new Map<string, CLISession>();

// Session timeout (5 minutes)
const SESSION_TIMEOUT_MS = 5 * 60 * 1000;

// Cleanup interval (1 minute)
const CLEANUP_INTERVAL_MS = 60 * 1000;

// Maximum sessions per process
const MAX_SESSIONS = parseInt(process.env.MAX_SESSIONS || '50');

/**
 * Cleanup idle sessions periodically
 */
setInterval(() => {
  const now = Date.now();
  const toDelete: string[] = [];
  
  for (const [id, session] of cliSessions) {
    if (now - session.lastActivity > SESSION_TIMEOUT_MS) {
      console.log(`Cleaning up idle session: ${id}`);
      session.process.kill('SIGTERM');
      toDelete.push(id);
    }
  }
  
  toDelete.forEach(id => cliSessions.delete(id));
  
  if (cliSessions.size > 0) {
    console.log(`Active sessions: ${cliSessions.size}/${MAX_SESSIONS}`);
  }
}, CLEANUP_INTERVAL_MS);

/**
 * Determine if we should use CLI vs SDK
 * - Slash commands → CLI for special behaviors
 * - Regular prompts → SDK for typed streaming
 */
function shouldUseCLI(text: string, forceCLI?: boolean): boolean {
  const trimmed = text.trim();
  
  // Force CLI if requested
  if (forceCLI) return true;
  
  // Slash commands that need CLI
  const cliCommands = [
    '/help', '/status', '/compact', '/clear', 
    '/agents', '/model', '/continue', '/resume',
    '/settings', '/history', '/export'
  ];
  
  return cliCommands.some(cmd => trimmed.startsWith(cmd));
}

/**
 * Main execution endpoint
 * Streams responses as Server-Sent Events
 */
app.post('/exec', async (req, res) => {
  const { text, opts } = req.body as ExecRequest;
  
  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering
  res.flushHeaders?.();
  
  // Default safe tools (no Bash for untrusted input)
  const allowedTools = opts?.allowedTools ?? ['Read', 'WebSearch', 'Edit', 'Write'];
  const cwd = opts?.cwd ?? process.cwd();
  
  try {
    if (shouldUseCLI(text, opts?.forceCLI)) {
      // Use CLI in print mode with structured output
      await handleCLI(text, { ...opts, allowedTools, cwd }, res);
    } else {
      // Use SDK for normal prompts
      await handleSDK(text, { ...opts, allowedTools, cwd }, res);
    }
  } catch (error) {
    console.error('Execution error:', error);
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ 
      error: error instanceof Error ? error.message : 'Unknown error' 
    })}\n\n`);
    res.end();
  }
});

/**
 * Handle CLI execution with persistent sessions
 */
async function handleCLI(
  text: string, 
  opts: ExecRequest['opts'] & { allowedTools: string[]; cwd: string },
  res: express.Response
) {
  // Use existing session or create new one
  const sessionId = opts?.sessionId || randomUUID();
  const isPersistent = opts?.continueSession === true;
  
  if (isPersistent) {
    // Use persistent streaming session
    await handleStreamingCLI(sessionId, text, opts, res);
  } else {
    // Use one-shot CLI execution (original behavior)
    await handleOneshotCLI(text, opts, res);
  }
}

/**
 * Handle persistent streaming CLI session
 */
async function handleStreamingCLI(
  sessionId: string,
  text: string,
  opts: ExecRequest['opts'] & { allowedTools: string[]; cwd: string },
  res: express.Response
) {
  // Check if we've hit session limit
  if (cliSessions.size >= MAX_SESSIONS && !cliSessions.has(sessionId)) {
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ 
      error: 'Maximum sessions reached. Please try again later.' 
    })}\n\n`);
    res.end();
    return;
  }
  
  let session = cliSessions.get(sessionId);
  
  if (!session) {
    // Create new persistent session
    console.log(`Creating new streaming session: ${sessionId}`);
    
    const proc = spawn('claude', [
      '--output-format', 'stream-json',
      '--input-format', 'stream-json',
      '--allowedTools', opts.allowedTools.join(','),
      '--cwd', opts.cwd,
      '--verbose',
      ...(opts.permissionMode ? ['--permission-mode', opts.permissionMode] : [])
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: opts.cwd,
      env: {
        ...process.env,
        CLAUDE_OUTPUT_FORMAT: 'stream-json',
        CLAUDE_INPUT_FORMAT: 'stream-json',
      }
    });
    
    session = {
      id: sessionId,
      process: proc,
      lastActivity: Date.now(),
      buffer: '',
      messageCount: 0,
      created: Date.now(),
      metadata: {
        tools: opts.allowedTools,
        cwd: opts.cwd
      }
    };
    
    cliSessions.set(sessionId, session);
    
    // Set up output streaming
    proc.stdout.on('data', (chunk: Buffer) => {
      const s = cliSessions.get(sessionId);
      if (!s) return;
      
      s.buffer += chunk.toString();
      const lines = s.buffer.split('\n');
      s.buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.trim()) {
          try {
            const message = JSON.parse(line);
            s.messageCount++;
            
            // Enrich message with session info
            const enriched = {
              ...message,
              session_id: sessionId,
              message_index: s.messageCount
            };
            
            res.write(`event: message\n`);
            res.write(`data: ${JSON.stringify(enriched)}\n\n`);
          } catch (e) {
            console.error('Failed to parse JSON:', line);
            res.write(`event: text\n`);
            res.write(`data: ${JSON.stringify({ content: line })}\n\n`);
          }
        }
      }
    });
    
    proc.stderr.on('data', (chunk: Buffer) => {
      const text = chunk.toString();
      console.error(`Session ${sessionId} stderr:`, text);
      res.write(`event: log\n`);
      res.write(`data: ${JSON.stringify({ stderr: text, session_id: sessionId })}\n\n`);
    });
    
    proc.on('exit', (code) => {
      console.log(`Session ${sessionId} process exited with code ${code}`);
      cliSessions.delete(sessionId);
      
      // Flush remaining buffer
      if (session && session.buffer.trim()) {
        try {
          const message = JSON.parse(session.buffer);
          res.write(`event: message\n`);
          res.write(`data: ${JSON.stringify({ ...message, session_id: sessionId })}\n\n`);
        } catch {
          res.write(`event: text\n`);
          res.write(`data: ${JSON.stringify({ content: session.buffer })}\n\n`);
        }
      }
      
      res.write(`event: session_ended\n`);
      res.write(`data: ${JSON.stringify({ session_id: sessionId, code })}\n\n`);
      res.end();
    });
    
    proc.on('error', (err) => {
      console.error(`Session ${sessionId} error:`, err);
      cliSessions.delete(sessionId);
      res.write(`event: error\n`);
      res.write(`data: ${JSON.stringify({ error: err.message, session_id: sessionId })}\n\n`);
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
  
  console.log(`Sending message to session ${sessionId}:`, userMessage);
  
  session.process.stdin?.write(JSON.stringify(userMessage) + '\n');
  session.lastActivity = Date.now();
  
  // Don't end response - keep connection open for streaming
  res.on('close', () => {
    console.log(`Client disconnected from session ${sessionId}`);
  });
}

/**
 * Handle one-shot CLI execution (original behavior)
 */
async function handleOneshotCLI(
  text: string,
  opts: ExecRequest['opts'] & { allowedTools: string[]; cwd: string },
  res: express.Response
) {
  const args: string[] = [
    '-p', text, // Print mode
    '--output-format', 'stream-json', // Structured output
    '--allowedTools', opts.allowedTools.join(','),
    '--cwd', opts.cwd,
    '--no-interactive' // Disable interactive prompts
  ];
  
  // Add session management
  if (opts?.sessionId && !opts?.continueSession) {
    args.push('--resume', opts.sessionId);
  }
  
  // Add permission mode
  if (opts?.permissionMode) {
    args.push('--permission-mode', opts.permissionMode);
  }
  
  // Add max turns
  if (opts?.maxTurns) {
    args.push('--max-turns', String(opts.maxTurns));
  }
  
  console.log('Executing one-shot CLI:', 'claude', args.join(' '));
  
  const child = spawn('claude', args, {
    stdio: ['ignore', 'pipe', 'pipe'],
    cwd: opts.cwd,
    env: {
      ...process.env,
      CLAUDE_OUTPUT_FORMAT: 'stream-json',
      CLAUDE_NO_INTERACTIVE: '1',
    }
  });
  
  let buffer = '';
  
  // Process stdout (JSON lines)
  child.stdout.on('data', (chunk: Buffer) => {
    buffer += chunk.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line
    
    for (const line of lines) {
      if (line.trim()) {
        try {
          const message = JSON.parse(line);
          res.write(`event: message\n`);
          res.write(`data: ${JSON.stringify(message)}\n\n`);
        } catch {
          // Not JSON, send as plain text
          res.write(`event: text\n`);
          res.write(`data: ${JSON.stringify({ content: line })}\n\n`);
        }
      }
    }
  });
  
  // Process stderr (logs/errors)
  child.stderr.on('data', (chunk: Buffer) => {
    const text = chunk.toString();
    console.error('CLI stderr:', text);
    res.write(`event: log\n`);
    res.write(`data: ${JSON.stringify({ stderr: text })}\n\n`);
  });
  
  // Handle process exit
  child.on('close', (code) => {
    // Flush any remaining buffer
    if (buffer.trim()) {
      try {
        const message = JSON.parse(buffer);
        res.write(`event: message\n`);
        res.write(`data: ${JSON.stringify(message)}\n\n`);
      } catch {
        res.write(`event: text\n`);
        res.write(`data: ${JSON.stringify({ content: buffer })}\n\n`);
      }
    }
    
    res.write(`event: done\n`);
    res.write(`data: ${JSON.stringify({ exitCode: code })}\n\n`);
    res.end();
  });
  
  // Handle errors
  child.on('error', (err) => {
    console.error('CLI spawn error:', err);
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
    res.end();
  });
}

/**
 * Handle SDK execution with typed streaming
 */
async function handleSDK(
  text: string,
  opts: ExecRequest['opts'] & { allowedTools: string[]; cwd: string },
  res: express.Response
) {
  console.log('Executing SDK query:', { text, opts });
  
  try {
    // Build query options
    const queryOptions = {
      prompt: text,
      options: {
        cwd: opts.cwd,
        maxTurns: opts.maxTurns ?? 3,
        allowedTools: opts.allowedTools,
        permissionMode: opts.permissionMode ?? 'acceptEdits',
        verbose: process.env.NODE_ENV === 'development',
        systemPrompt: undefined as string | undefined,
        continueSession: undefined as boolean | undefined,
        sessionId: undefined as string | undefined,
      }
    };
    
    // Add system prompt if provided
    if (opts.systemPrompt) {
      queryOptions.options.systemPrompt = opts.systemPrompt;
    }
    
    // Session management
    if (opts.sessionId && opts.continueSession) {
      queryOptions.options.continueSession = true;
      queryOptions.options.sessionId = opts.sessionId;
    }
    
    // Stream messages from SDK
    let messageCount = 0;
    const startTime = Date.now();
    
    for await (const message of query(queryOptions)) {
      messageCount++;
      
      // Add metadata to message
      const enrichedMessage = {
        ...message,
        _metadata: {
          index: messageCount,
          timestamp: Date.now(),
          sessionId: opts.sessionId,
        }
      };
      
      res.write(`event: message\n`);
      res.write(`data: ${JSON.stringify(enrichedMessage)}\n\n`);
    }
    
    // Send completion event
    const duration = Date.now() - startTime;
    res.write(`event: done\n`);
    res.write(`data: ${JSON.stringify({ 
      messageCount,
      duration,
      sessionId: opts.sessionId 
    })}\n\n`);
    res.end();
    
  } catch (error) {
    console.error('SDK error:', error);
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ 
      error: error instanceof Error ? error.message : 'SDK error',
      stack: process.env.NODE_ENV === 'development' ? 
        (error instanceof Error ? error.stack : undefined) : undefined
    })}\n\n`);
    res.end();
  }
}

/**
 * Health check endpoint
 */
app.get('/health', (_req, res) => {
  const hasApiKey = !!process.env.ANTHROPIC_API_KEY;
  const claudeInstalled = !!which('claude');
  
  res.json({
    status: 'healthy',
    timestamp: Date.now(),
    apiKey: hasApiKey ? 'configured' : 'missing',
    cli: claudeInstalled ? 'installed' : 'missing',
    sdk: 'ready',
    version: process.env.npm_package_version || 'unknown',
  });
});

/**
 * Session management endpoints
 */
app.get('/sessions', async (_req, res) => {
  const sessions = Array.from(cliSessions.entries()).map(([id, session]) => ({
    id,
    created: session.created,
    lastActivity: session.lastActivity,
    messageCount: session.messageCount,
    metadata: session.metadata,
    active: true,
    age: Date.now() - session.created,
    idle: Date.now() - session.lastActivity
  }));
  
  res.json({ 
    sessions,
    total: sessions.length,
    maxSessions: MAX_SESSIONS,
    sessionTimeout: SESSION_TIMEOUT_MS
  });
});

app.get('/sessions/:id', async (req, res) => {
  const session = cliSessions.get(req.params.id);
  
  if (!session) {
    res.status(404).json({ 
      error: 'Session not found',
      sessionId: req.params.id 
    });
    return;
  }
  
  res.json({
    id: session.id,
    created: session.created,
    lastActivity: session.lastActivity,
    messageCount: session.messageCount,
    metadata: session.metadata,
    active: true,
    age: Date.now() - session.created,
    idle: Date.now() - session.lastActivity
  });
});

app.delete('/sessions/:id', async (req, res) => {
  const session = cliSessions.get(req.params.id);
  
  if (!session) {
    res.status(404).json({ 
      success: false,
      message: 'Session not found' 
    });
    return;
  }
  
  try {
    session.process.kill('SIGTERM');
    cliSessions.delete(req.params.id);
    
    res.json({ 
      success: true,
      message: 'Session terminated',
      sessionId: req.params.id
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Failed to terminate session',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Command discovery endpoint
 */
app.get('/api/commands', async (_req, res) => {
  // Return available slash commands and tools
  const commands = [
    { name: '/help', description: 'Show help information', category: 'builtin' },
    { name: '/status', description: 'Show current status', category: 'builtin' },
    { name: '/compact', description: 'Toggle compact mode', category: 'builtin' },
    { name: '/clear', description: 'Clear conversation', category: 'builtin' },
    { name: '/agents', description: 'List available agents', category: 'builtin' },
    { name: '/model', description: 'Switch model', category: 'builtin' },
    { name: '/continue', description: 'Continue last session', category: 'builtin' },
    { name: '/resume', description: 'Resume specific session', category: 'builtin' },
    { name: '/settings', description: 'Show settings', category: 'builtin' },
    { name: '/history', description: 'Show command history', category: 'builtin' },
    { name: '/export', description: 'Export conversation', category: 'builtin' }
  ];
  
  const tools = [
    'Read', 'Write', 'Edit', 'MultiEdit',
    'Grep', 'LS', 'Glob', 'WebSearch',
    'Bash', 'Git', 'NotebookEdit', 'TodoWrite'
  ];
  
  res.json({
    commands,
    tools,
    timestamp: Date.now()
  });
});

// Helper to check if command exists
function which(cmd: string): boolean {
  try {
    // Use dynamic import for ESM compatibility
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { execSync } = require('child_process');
    execSync(`which ${cmd}`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

// Start server
const PORT = process.env.BRIDGE_PORT || 8787;
app.listen(PORT, () => {
  console.log(`
🌉 Claude Code Bridge Server
   Port: ${PORT}
   API Key: ${process.env.ANTHROPIC_API_KEY ? '✓ Configured' : '✗ Missing'}
   Claude CLI: ${which('claude') ? '✓ Installed' : '✗ Missing'}
   
   Endpoints:
   POST /exec - Execute Claude commands
   GET /health - Health check
   GET /sessions - List sessions
   DELETE /sessions/:id - Clean up session
  `);
});

export default app;