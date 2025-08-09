# Cloudflare Workers React Terminal - Setup Guide

## Overview

This is a **Cloudflare Workers React Terminal UI** application that provides an interactive Claude assistant experience running on Cloudflare's edge network. Built with React 19, TypeScript, Vite 7, and deployed via Cloudflare Workers.

## Prerequisites

- Node.js 16+ and npm 8+
- Cloudflare account (free tier works)
- Wrangler CLI (installed as dev dependency)

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Local Development

Start the Vite development server with Cloudflare Workers runtime emulation:

```bash
npm run dev
```

The app will be available at `http://localhost:5173` with hot module replacement (HMR) enabled.

### 3. Build for Production

```bash
npm run build
```

This runs TypeScript compilation (`tsc -b`) followed by Vite production build.

### 4. Preview Production Build

```bash
npm run preview
```

Builds and serves the production bundle locally for testing.

### 5. Deploy to Cloudflare Workers

```bash
npm run deploy
```

Deploys to your `*.workers.dev` subdomain or custom domain configured in `wrangler.jsonc`.

## Project Structure

```
.
├── src/                    # React application source
│   ├── components/        # UI components (Terminal, Header, etc.)
│   ├── hooks/            # Custom React hooks
│   ├── store/            # Zustand state management
│   ├── styles/           # CSS modules
│   ├── utils/            # Utility functions
│   └── main.tsx          # Application entry point
├── worker/               # Cloudflare Worker backend
│   └── index.ts         # Worker API endpoints
├── public/              # Static assets
├── .claude/             # Claude Code configuration
│   ├── settings.json    # Tool permissions and hooks
│   └── commands/        # Custom command definitions
├── vite.config.ts       # Vite + Cloudflare plugin config
├── wrangler.jsonc       # Cloudflare Workers configuration
└── CLAUDE.md           # Project conventions and guidelines
```

## Available Scripts

### Core Commands
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run deploy` - Deploy to Cloudflare Workers

### Code Quality
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Auto-fix linting issues
- `npm run typecheck` - TypeScript type checking
- `npm run format` - Format with Prettier
- `npm run format:check` - Check formatting

### Testing
- `npm run test` - Run Vitest tests
- `npm run test:watch` - Watch mode
- `npm run test:coverage` - Coverage report

### Utilities
- `npm run cf-typegen` - Generate Cloudflare types
- `npm run clean` - Clean build artifacts

## Configuration Files

### `wrangler.jsonc`
Cloudflare Workers configuration:
- **main**: Points to `worker/index.ts` (backend API)
- **assets.not_found_handling**: Set to `single-page-application` for React SPA routing
- **bindings**: Configure KV, R2, D1, and other Cloudflare services

### `vite.config.ts`
Vite configuration with:
- `@vitejs/plugin-react-swc` - React with SWC for fast refresh
- `@cloudflare/vite-plugin` - Workers runtime emulation in development

### `.claude/settings.json`
Claude Code configuration:
- Tool permissions for file operations
- Git hooks for code quality
- Auto-formatting and linting on file changes

## Key Dependencies

### Runtime
- **React 19** - UI framework
- **Zustand 5** - State management
- **Monaco Editor** - Code editor component
- **Lucide React** - Icons
- **Sonner** - Toast notifications
- **@anthropic-ai/claude-code** - Claude SDK

### Development
- **TypeScript 5.8** - Type safety
- **Vite 7** - Build tool
- **ESLint 9** - Linting
- **Prettier 3** - Code formatting
- **Vitest 2** - Testing framework
- **Wrangler 4** - Cloudflare CLI

## Development Workflow

### 1. Feature Development
```bash
# Start dev server
npm run dev

# Make changes with HMR
# TypeScript checking runs automatically in build

# Run linter
npm run lint:fix

# Format code
npm run format

# Run tests
npm run test
```

### 2. Before Committing
```bash
# Type check
npm run typecheck

# Lint check
npm run lint

# Test build
npm run build

# Preview locally
npm run preview
```

### 3. Deployment
```bash
# Deploy to Cloudflare Workers
npm run deploy

# Or use Wrangler directly
npx wrangler deploy
```

## Using Worker Bindings

The Worker at `worker/index.ts` can access Cloudflare bindings (KV, R2, D1, etc.). Configure bindings in `wrangler.jsonc`:

```jsonc
{
  "name": "my-react-app",
  "main": "worker/index.ts",
  "kv_namespaces": [
    { "binding": "MY_KV", "id": "xxxxx" }
  ],
  "r2_buckets": [
    { "binding": "MY_BUCKET", "bucket_name": "my-bucket" }
  ]
}
```

Access bindings in your Worker:

```typescript
// worker/index.ts
export default {
  async fetch(request, env) {
    // Access KV namespace
    await env.MY_KV.put("key", "value");
    
    // Access R2 bucket
    await env.MY_BUCKET.put("file.txt", data);
    
    return new Response("OK");
  }
}
```

## Environment Variables

### Development
Create `.dev.vars` for local development:
```env
API_KEY=your-api-key
DATABASE_URL=your-database-url
```

### Production
Set secrets via Wrangler:
```bash
npx wrangler secret put API_KEY
```

## Routing

The app uses SPA routing with `not_found_handling = "single-page-application"` in `wrangler.jsonc`:

1. Static assets are served first (from `dist/` after build)
2. API routes go to the Worker (`/api/*`)
3. All other routes return `index.html` for React Router handling

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

### Clear Build Cache
```bash
npm run clean
rm -rf .wrangler
```

### TypeScript Errors
```bash
# Full type check
npm run typecheck

# Skip lib check for faster checks
npx tsc --noEmit --skipLibCheck
```

### Deployment Issues
```bash
# Check Wrangler auth
npx wrangler whoami

# Login if needed
npx wrangler login

# Verbose deploy
npx wrangler deploy --log-level debug
```

## CI/CD with Workers Builds

Configure in your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Deploy to Cloudflare Workers
  uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    command: deploy
```

## Resources

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [React + Vite on Workers](https://developers.cloudflare.com/workers/framework-guides/web-apps/react/)
- [Cloudflare Vite Plugin](https://developers.cloudflare.com/workers/vite-plugin/)
- [Workers Bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/)
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)

## License

This project is configured for Cloudflare Workers deployment. Ensure you comply with Cloudflare's terms of service and any applicable licenses for dependencies.