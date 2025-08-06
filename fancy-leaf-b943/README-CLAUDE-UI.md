# Claude Code Web UI

A modern web interface for Claude Code, providing a terminal-like experience with advanced features for AI-assisted development.

## Features

### ✨ Core Capabilities
- **Real-time Streaming**: Live streaming responses with support for text, JSON, and stream-JSON formats
- **Session Management**: Create new sessions, continue existing ones, or resume by ID
- **Tool Call Visualization**: Elegant animations with running ribbons, shimmer progress, and toast notifications
- **Command History**: Per-session history with keyboard navigation
- **MCP Integration**: Full support for Model Context Protocol servers and tools
- **Export Functionality**: Export transcripts as JSONL for analysis or archival

### 🎨 User Interface

#### Header / Status Line
- Model and session information display
- Execution controls (max turns, permission mode, verbose mode)
- Real-time telemetry (turns, duration, API time, cost)
- Recent sessions dropdown for quick switching

#### Transcript / Main Pane
- Schema-aware message rendering
- Syntax-highlighted tool calls and results
- Error subtype handling with actionable suggestions
- Collapsible diagnostic information

#### Prompt Bar / Composer
- Multi-line input with auto-resize
- Mode badges (output format, permission mode)
- Visual indicators for active settings
- Keyboard shortcut hints

#### Tool-Call UX
- Running ribbon animation during tool execution
- Shimmer effect on active tool calls
- Progress bars with percentage display
- Success/error toast notifications

### ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Submit prompt |
| `Shift+Enter` | New line in prompt |
| `↑/↓` | Navigate command history |
| `Ctrl+L` | Clear transcript |
| `Ctrl+C` | Interrupt running operation |

## Architecture

### Frontend Stack
- **React 19** with TypeScript
- **Zustand** for state management with persistence
- **Lucide React** for icons
- **Tailwind CSS** for styling (via custom CSS)
- **Vite** for fast development and builds

### State Management
- `session.state.ts`: Session controls and telemetry
- `messages.state.ts`: Transcript and streaming state
- `toolCalls.state.ts`: Tool execution tracking
- `history.state.ts`: Command history per session

### Backend Integration
The Worker (`worker/index.ts`) provides:
- `/api/query`: Main streaming endpoint for Claude interactions
- `/api/interrupt`: Interrupt running operations
- `/api/sessions`: Session management
- `/api/health`: Health check endpoint

## Getting Started

### Development
```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Open browser
open http://localhost:5173
```

### Production Build
```bash
# Build for production
npm run build

# Preview production build
npm run preview

# Deploy to Cloudflare Workers
npm run deploy
```

## Integration with Claude Code SDK

### Option 1: Direct SDK Integration
Replace the mock Worker implementation with actual Claude Code SDK calls:

```typescript
import { query, type SDKMessage } from "@anthropic-ai/claude-code"

// In worker/index.ts
const messages: SDKMessage[] = []
for await (const message of query({
  prompt: body.prompt,
  options: {
    maxTurns: body.maxTurns,
    outputFormat: body.outputFormat,
    sessionId: body.sessionId,
  },
})) {
  // Stream to client via SSE
  controller.enqueue(encoder.encode(`data: ${JSON.stringify(message)}\n\n`))
}
```

### Option 2: CLI Process Spawning
For environments with CLI access:

```typescript
import { spawn } from 'child_process'

const child = spawn('claude', [
  '-p',
  '--output-format', 'stream-json',
  '--max-turns', String(body.maxTurns),
  body.sessionId && '--resume', body.sessionId,
].filter(Boolean))

child.stdout.on('data', (chunk) => {
  // Parse and stream JSONL to client
})
```

## Configuration

### Environment Variables
```bash
# API configuration
ANTHROPIC_API_KEY=your-api-key

# Optional: MCP server configuration
MCP_CONFIG_PATH=/path/to/mcp-servers.json
```

### MCP Server Configuration
Create `mcp-servers.json`:
```json
{
  "servers": {
    "filesystem": {
      "type": "stdio",
      "command": "mcp-server-filesystem",
      "args": ["--readonly"]
    },
    "github": {
      "type": "stdio", 
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

## Customization

### Theme
Edit `src/styles/animations.css` and `src/App.css` to customize colors and animations.

### Tool Display
Modify `src/components/ToolCallLine.tsx` to customize how tools are displayed.

### Message Rendering
Update `src/components/Transcript.tsx` to change message formatting.

## Roadmap

### Planned Features
- [ ] File browser and code editor integration
- [ ] Authentication and API key management UI
- [ ] Settings panel with MCP server management
- [ ] Command palette (Cmd+K) for quick actions
- [ ] Diagnostics panel with verbose logs
- [ ] Long-lived session processes for better performance

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT