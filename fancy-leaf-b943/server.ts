import express from 'express';
import cors from 'cors';
import { query, type QueryMessage } from '@anthropic-ai/claude-code';

const app = express();
app.use(cors());
app.use(express.json());

interface ClaudeRequestBody {
  prompt: string;
  options?: {
    systemPrompt?: string;
    maxTurns?: number;
    allowedTools?: string[];
    continueSession?: boolean;
    cwd?: string;
    permissionMode?: 'acceptEdits' | 'plan' | 'ask';
  };
}

app.post('/api/claude/stream', async (req, res) => {
  const { prompt, options } = req.body as ClaudeRequestBody;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');

  try {
    const messages: QueryMessage[] = [];
    
    for await (const message of query({
      prompt,
      options: {
        systemPrompt: options?.systemPrompt,
        maxTurns: options?.maxTurns ?? 3,
        allowedTools: options?.allowedTools ?? ['Bash', 'Read', 'WebSearch', 'Edit', 'Write'],
        continueSession: options?.continueSession ?? false,
        cwd: options?.cwd ?? process.cwd(),
        permissionMode: options?.permissionMode ?? 'acceptEdits',
      },
    })) {
      messages.push(message);
      
      // Stream each message as SSE
      res.write(`event: message\n`);
      res.write(`data: ${JSON.stringify(message)}\n\n`);
    }
    
    // Send completion event
    res.write(`event: done\n`);
    res.write(`data: ${JSON.stringify({ complete: true, messageCount: messages.length })}\n\n`);
    res.end();
  } catch (error) {
    console.error('Claude query error:', error);
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ 
      error: error instanceof Error ? error.message : 'Unknown error occurred',
      stack: process.env.NODE_ENV === 'development' && error instanceof Error ? error.stack : undefined
    })}\n\n`);
    res.end();
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'claude-code-bridge' });
});

const PORT = process.env.CLAUDE_BRIDGE_PORT || 8787;

app.listen(PORT, () => {
  console.log(`🤖 Claude Code bridge server running on http://localhost:${PORT}`);
  console.log(`   Health check: http://localhost:${PORT}/health`);
  console.log(`   Stream endpoint: POST http://localhost:${PORT}/api/claude/stream`);
});