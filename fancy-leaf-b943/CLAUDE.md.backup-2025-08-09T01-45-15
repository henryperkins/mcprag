# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a React + TypeScript application built with Vite and deployed to Cloudflare Workers. It combines a React frontend with a Cloudflare Worker backend API, enabling edge-deployed full-stack applications.

## Essential Commands

```bash
# Development
npm run dev          # Start Vite dev server with HMR

# Build & Preview
npm run build        # TypeScript check + Vite build
npm run preview      # Build and preview production build locally

# Code Quality
npm run lint         # Run ESLint

# Deployment
npm run deploy       # Build and deploy to Cloudflare Workers
npm run cf-typegen   # Generate TypeScript types from Cloudflare configuration
```

## Architecture

### Frontend (React SPA)
- **Entry Point**: `src/main.tsx` - React app bootstrap with StrictMode
- **Main Component**: `src/App.tsx` - Root component with example API integration
- **Build System**: Vite with React SWC plugin for fast builds and HMR
- **Assets**: Static assets in `public/` and `src/assets/`

### Backend (Cloudflare Worker)
- **Entry Point**: `worker/index.ts` - Cloudflare Worker handling API routes
- **API Pattern**: Routes starting with `/api/` are handled by the Worker
- **Configuration**: `wrangler.jsonc` defines Worker settings and bindings
- **TypeScript**: Separate `tsconfig.worker.json` for Worker-specific types

### Build Configuration
- **TypeScript**: Project references split between app, node, and worker contexts
- **Vite Config**: Uses `@cloudflare/vite-plugin` for Worker integration
- **ESLint**: Configured with TypeScript and React hooks plugins

## Key Patterns

### API Communication
The frontend communicates with the Worker backend through `/api/` endpoints. Example from `src/App.tsx`:
```typescript
fetch('/api/')
  .then((res) => res.json())
  .then((data) => setName(data.name))
```

### Worker Request Handling
The Worker checks URL pathname to route API vs static asset requests:
```typescript
if (url.pathname.startsWith("/api/")) {
  return Response.json({ name: "Cloudflare" });
}
```

### TypeScript Configuration
The project uses TypeScript project references to separate:
- `tsconfig.app.json` - React application code
- `tsconfig.node.json` - Node.js tooling (Vite config)
- `tsconfig.worker.json` - Cloudflare Worker code

## Claude Code Web UI

This project includes a **terminal-style web interface** that closely replicates the Claude Code CLI experience in the browser. The design prioritizes authenticity over modern web UI patterns.

### Terminal Interface Features

- **Authentic CLI Look**: Deep blue/black gradient background with monospace font throughout
- **Terminal Prompt**: Green prompt prefix showing `➜ ~Claude_Code:model-session` just like the CLI
- **Session Initialization Display**: Shows Model, CWD, Mode, Session ID, Tools, and MCP servers on startup
- **CLI-style Message Rendering**: 
  - User input in yellow with full prompt prefix
  - Assistant responses in white without prefixes
  - Tool calls with purple tool names and emoji markers (🔧)
  - Results with checkmarks/warning symbols and telemetry data
- **Contenteditable Input**: Single-line terminal input with blinking cursor
- **Keyboard-First Navigation**: All interactions via keyboard shortcuts
- **Footer Status**: Shows available shortcuts and streaming status

### Keyboard Shortcuts
- `Enter`: Submit prompt
- `Shift+Enter`: New line in prompt  
- `↑/↓`: Navigate command history per session
- `Ctrl+L`: Clear terminal (like real terminal)
- `Ctrl+C`: Interrupt running operation

### Terminal Layout
- **Header Bar**: "Claude Code" title with session ID
- **Terminal Body**: Scrollable area with session info and message history
- **Current Prompt**: Active input line with blinking cursor
- **Footer**: Available keyboard shortcuts and status

## Development Workflow

1. Run `npm run dev` to start the Vite dev server with Cloudflare runtime emulation
2. Frontend changes in `src/` trigger HMR
3. Worker changes in `worker/` require restart
4. Test production build with `npm run preview`
5. Deploy to Cloudflare with `npm run deploy`

### Testing the Terminal UI
1. Open http://localhost:5173 in your browser
2. You'll see a terminal interface that looks like the Claude Code CLI
3. Type prompts and press Enter to see mock responses
4. Use keyboard shortcuts to navigate like a real terminal
5. In production, replace mock Worker with actual Claude Code SDK integration

## Cloudflare Workers Best Practices

### Code Standards
- Use TypeScript for type safety
- Use ES modules exclusively (no CommonJS)
- Minimize external dependencies to reduce bundle size
- Never hardcode secrets - use environment variables or Wrangler secrets
- Implement comprehensive error handling with meaningful error messages

### Available Platform Services
When developing features, leverage these Cloudflare services through bindings:
- **KV**: Key-value storage for simple data
- **D1**: SQLite database for relational data
- **R2**: Object storage for files and media
- **Durable Objects**: Stateful, consistent computing for real-time features
- **Queues**: Async task processing
- **Workers AI**: AI model inference
- **Vectorize**: Vector embeddings for semantic search

### Performance Considerations
- Minimize cold starts by keeping Worker code lightweight
- Implement strategic caching for frequently accessed data
- Use streaming for large responses or AI-generated content
- Be aware of Workers platform limits (CPU time, memory, subrequest limits)

### Security Guidelines
- Validate all incoming requests
- Implement proper CORS headers for API endpoints
- Use appropriate security headers (CSP, X-Frame-Options, etc.)
- Sanitize user inputs before processing
- Implement rate limiting for API endpoints

### React + Workers Integration Patterns
- The Worker serves as both static asset server and API backend
- SPA routing handled by `not_found_handling: "single-page-application"` in wrangler.jsonc
- API routes should be prefixed with `/api/` for clear separation
- Use `fetch()` from React to interact with Worker API endpoints
- Consider implementing WebSocket support for real-time features using Durable Objects

### Deployment Considerations
- Set appropriate `compatibility_date` in wrangler.jsonc
- Configure observability for production monitoring
- Use environment-specific configurations for staging/production
- Consider implementing preview deployments for pull requests