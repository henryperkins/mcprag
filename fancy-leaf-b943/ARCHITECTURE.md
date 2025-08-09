# Architecture Documentation

## Overview

This is a **Cloudflare Workers React Terminal UI** application that provides an interactive Claude assistant experience. The architecture follows Cloudflare's recommended pattern for SPAs with API Workers using the Vite plugin.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloudflare Edge                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Worker Runtime                       │   │
│  │                                                       │   │
│  │  ┌─────────────────┐    ┌───────────────────────┐   │   │
│  │  │  Static Assets  │    │     API Worker        │   │   │
│  │  │   (React SPA)   │───►│   (worker/index.ts)   │   │   │
│  │  │                 │    │                       │   │   │
│  │  │  - index.html   │    │  Endpoints:          │   │   │
│  │  │  - JS bundles   │    │  - /api/query        │   │   │
│  │  │  - CSS files    │    │  - /api/interrupt    │   │   │
│  │  │  - Assets       │    │  - /api/sessions     │   │   │
│  │  └─────────────────┘    │  - /api/health       │   │   │
│  │                          └───────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    Browser        │
                    │  (React Client)   │
                    └──────────────────┘
```

## Request Flow

### 1. Static Asset Requests
- Browser requests `https://your-worker.workers.dev/`
- Cloudflare serves static assets from the `dist/client` directory
- SPA routing handled by `not_found_handling: "single-page-application"`
- All non-existent routes return `index.html` for React Router

### 2. API Requests
- React app makes fetch requests to `/api/*` endpoints
- Worker intercepts these requests (no network roundtrip)
- Worker processes the request and returns response
- Streaming responses supported via Server-Sent Events (SSE)

## Key Components

### Frontend (React SPA)

#### State Management (Zustand)
```
src/store/
├── messages.state.ts     # Chat messages
├── session.state.ts      # Session management
├── history.state.ts      # Chat history
├── toolCalls.state.ts    # Tool execution tracking
└── unified.adapter.ts    # State coordination
```

#### UI Components
```
src/components/
├── Terminal.tsx          # Main terminal interface
├── ChatPane.tsx          # Chat display
├── PromptBar.tsx        # User input
├── Header.tsx           # App header
├── SlashMenu.tsx        # Command menu
├── Transcript.tsx       # Message display
└── ToolCallLine.tsx     # Tool execution display
```

### Backend (Worker API)

#### Environment Variables
```typescript
interface Env {
  ANTHROPIC_API_KEY?: string     // API key for Claude
  MCP_CONFIG?: string            // MCP servers configuration
  CLAUDE_CODE_USE_BEDROCK?: string
  CLAUDE_CODE_USE_VERTEX?: string
}
```

#### API Endpoints

##### `/api/query` (POST)
Main interaction endpoint for Claude Code SDK
```typescript
interface QueryBody {
  prompt: string
  outputFormat?: 'text' | 'json' | 'stream-json'
  sessionId?: string
  maxTurns?: number
  permissionMode?: 'auto' | 'acceptAll' | 'acceptEdits' | 'confirmAll'
  verbose?: boolean
  systemPrompt?: string
  appendSystemPrompt?: string
  allowedTools?: string[]
  disallowedTools?: string[]
}
```

##### `/api/interrupt` (POST)
Cancel an active session
```typescript
interface InterruptBody {
  sessionId?: string
}
```

##### `/api/sessions` (GET)
List active sessions

##### `/api/health` (GET)
Health check and configuration status

## Development Workflow

### Local Development
```bash
npm run dev
```
- Vite dev server runs on port 5173
- Cloudflare Vite plugin emulates Workers runtime
- Hot Module Replacement (HMR) for React
- Worker code runs in miniflare (local Workers emulation)

### Build Process
```bash
npm run build
```
1. TypeScript compilation (`tsc -b`)
2. Vite builds React app to `dist/client/`
3. Worker code prepared in `dist/fancy-leaf-b943/`
4. Output `wrangler.json` generated with build artifacts

### Preview
```bash
npm run preview
```
- Runs production build locally
- Uses actual Workers runtime behavior
- Validates routing and API integration

### Deployment
```bash
npm run deploy
```
- Uses output `wrangler.json` from build
- Deploys to Cloudflare Workers
- Available at `https://fancy-leaf-b943.workers.dev`

## Configuration Files

### `wrangler.jsonc`
- **Input** configuration for development
- Defines Worker name, compatibility date, assets handling
- Configures environment variables and bindings

### `vite.config.ts`
```typescript
plugins: [
  react(),           // React Fast Refresh
  cloudflare()       // Workers runtime integration
]
```

### TypeScript Configuration
- `tsconfig.app.json` - React app configuration
- `tsconfig.node.json` - Node/build tools configuration
- `tsconfig.worker.json` - Worker code configuration

## Security Considerations

### API Keys
- Store sensitive data as Worker secrets:
  ```bash
  npx wrangler secret put ANTHROPIC_API_KEY
  ```
- Never commit secrets to version control
- Use `.dev.vars` for local development

### CORS
- Currently allows all origins (`*`) for development
- Should be restricted in production to your domain

### Session Management
- Sessions tracked in-memory (ephemeral)
- Consider KV namespace for persistent sessions

## Performance Optimizations

### Edge-First Architecture
- Static assets served from Cloudflare edge (200+ locations)
- API runs at the edge, close to users
- No origin server required

### Asset Optimization
- Vite handles:
  - Code splitting
  - Tree shaking
  - Asset hashing for cache invalidation
  - Minification

### Streaming Responses
- Server-Sent Events for real-time updates
- Reduces time to first byte (TTFB)
- Progressive UI updates

## Scaling Considerations

### Current Limitations
- In-memory session storage (lost on Worker restart)
- Single Worker instance handles all requests
- No persistent storage configured

### Production Enhancements

#### Add KV Namespace for Sessions
```jsonc
// wrangler.jsonc
{
  "kv_namespaces": [
    { "binding": "SESSIONS", "id": "your-kv-id" }
  ]
}
```

#### Add D1 Database for History
```jsonc
// wrangler.jsonc
{
  "d1_databases": [
    { "binding": "DB", "database_name": "chat-history" }
  ]
}
```

#### Add R2 for File Storage
```jsonc
// wrangler.jsonc
{
  "r2_buckets": [
    { "binding": "FILES", "bucket_name": "user-files" }
  ]
}
```

## Monitoring & Observability

### Enabled Features
- Observability enabled in `wrangler.jsonc`
- Cloudflare dashboard provides:
  - Request logs
  - Error tracking
  - Performance metrics
  - Analytics

### Custom Metrics
Consider adding:
- Session duration tracking
- API call success rates
- Token usage monitoring
- Error categorization

## Future Enhancements

### Immediate Priorities
1. Add persistent storage (KV/D1)
2. Implement proper authentication
3. Add rate limiting
4. Configure production CORS

### Long-term Goals
1. Multi-region deployment with Durable Objects
2. WebSocket support for real-time updates
3. File upload/download capabilities
4. Collaborative sessions

## Related Documentation

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [React + Vite Tutorial](https://developers.cloudflare.com/workers/vite-plugin/tutorial/)
- [Static Assets Routing](https://developers.cloudflare.com/workers/static-assets/routing/)
- [Workers Bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/)
- [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code)