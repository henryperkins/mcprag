/**
 * Claude Code Bridge Server
 * Runs on VM/regular host with Node.js runtime
 * Decides between SDK and CLI based on command type
 */

import express from 'express';
import cors from 'cors';
import { spawn } from 'node:child_process';
import { query } from '@anthropic-ai/claude-code';

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
 * Handle CLI execution with JSON streaming
 */
async function handleCLI(
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
  if (opts?.sessionId) {
    if (opts?.continueSession) {
      args.push('--continue');
    } else {
      args.push('--resume', opts.sessionId);
    }
  }
  
  // Add permission mode
  if (opts?.permissionMode) {
    args.push('--permission-mode', opts.permissionMode);
  }
  
  // Add max turns
  if (opts?.maxTurns) {
    args.push('--max-turns', String(opts.maxTurns));
  }
  
  console.log('Executing CLI:', 'claude', args.join(' '));
  
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
  // List available sessions (from ~/.claude or configured directory)
  res.json({ 
    sessions: [],
    message: 'Session listing not implemented yet' 
  });
});

app.delete('/sessions/:id', async (_req, res) => {
  // Clean up a session
  res.json({ 
    success: false,
    message: 'Session cleanup not implemented yet' 
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