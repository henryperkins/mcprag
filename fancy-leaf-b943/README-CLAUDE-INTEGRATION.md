# Claude Code SDK Integration

This project now includes full integration with the Claude Code SDK, allowing you to run Claude commands directly from the terminal UI.

## Architecture

The integration uses a hybrid approach:
- **Frontend**: React Terminal UI running on Cloudflare Workers or Vite dev server
- **Backend**: Node.js Express server running the Claude Code SDK
- **Communication**: Server-Sent Events (SSE) for streaming responses

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy the example environment file and add your Anthropic API key:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```env
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

### 3. Running the Application

#### Option A: Development Mode (Recommended)

Run all services together:
```bash
npm run dev:all
```

This starts:
- Vite dev server on http://localhost:5173 (Frontend)
- Cloudflare Worker on http://localhost:8788 (Worker backend)
- Express server on http://localhost:8787 (Claude Code SDK bridge)

#### Option B: Run Services Separately

Terminal 1 - Frontend:
```bash
npm run dev
```

Terminal 2 - Cloudflare Worker:
```bash
npm run dev:worker
```

Terminal 3 - Claude SDK Server:
```bash
npm run dev:server
```

### 4. Using the Terminal

Once running, open http://localhost:5173 in your browser and you can:

- Type commands and questions for Claude
- Claude will use tools like Read, Write, Edit, Bash, and WebSearch
- See real-time streaming responses
- View tool calls and their outputs
- Use Ctrl+C to interrupt streaming
- Use Ctrl+L to clear the terminal
- Use arrow keys to navigate command history

## Features

### Integrated State Management
- Messages are stored in Zustand stores
- Session management with continuation support
- Tool call tracking and progress display
- Persistent history across sessions

### Streaming Response Handling
- Real-time character-by-character streaming
- Batched updates for performance
- ANSI color code support
- Tool call visualization

### Claude Code SDK Features
- Full access to Claude Code tools (Read, Write, Edit, Bash, etc.)
- Session continuation support
- Permission mode configuration
- Custom system prompts
- Tool allowlist/blocklist

## Production Deployment

### Deploy to Cloudflare Workers

1. Build the application:
```bash
npm run build
```

2. Deploy to Cloudflare:
```bash
npm run deploy
```

### Deploy the Express Server

The Express server needs to be deployed separately to a Node.js hosting service:

Options:
- **Heroku**: Add a `Procfile` with `web: node dist-server/server.js`
- **Railway**: Push to GitHub and connect repository
- **Fly.io**: Use `fly launch` and configure Node.js app
- **AWS Lambda**: Wrap with serverless-http adapter

Remember to set the `ANTHROPIC_API_KEY` environment variable in your production environment.

## Configuration Options

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)
- `CLAUDE_BRIDGE_PORT`: Port for the Express server (default: 8787)
- `VITE_CLAUDE_SERVER_URL`: External Claude server URL for production
- `MCP_CONFIG`: JSON configuration for MCP servers
- `NODE_ENV`: Environment mode (development/production)

### Claude Options

Configure in `src/services/claude.ts`:

```typescript
{
  maxTurns: 3,                    // Maximum conversation turns
  permissionMode: 'acceptEdits',  // Permission handling
  allowedTools: [...],            // Allowed Claude tools
  continueSession: true,          // Continue previous session
  cwd: '/path/to/workspace',      // Working directory
}
```

## Troubleshooting

### No API Key Error
Make sure you've set `ANTHROPIC_API_KEY` in your `.env` file

### Connection Refused
Ensure the Express server is running (`npm run dev:server`)

### CORS Issues
The server includes CORS headers for development. For production, configure appropriate origins.

### Tool Permissions
Claude might need filesystem access. Ensure the server has appropriate permissions for the working directory.

## Development Tips

1. **Mock Mode**: The worker includes mock responses when no API key is configured
2. **Debug Logging**: Set `NODE_ENV=development` for detailed logs
3. **Performance**: The terminal uses batching and windowing for smooth performance
4. **Testing**: Use the mock mode for UI development without consuming API credits

## Security Notes

- Never commit your `.env` file with real API keys
- Use environment variables for production deployments
- Consider implementing rate limiting for production use
- Restrict CORS origins in production environments