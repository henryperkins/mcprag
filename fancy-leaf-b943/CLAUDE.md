# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloudflare Workers-based React Terminal UI application built with Vite, TypeScript, and React 19. This is a Claude Code terminal interface that runs on Cloudflare's edge network and provides an interactive Claude assistant experience.

## Development Commands

### Package Management
- `npm install` or `yarn install` - Install dependencies
- `npm ci` or `yarn install --frozen-lockfile` - Install dependencies for CI/CD
- `npm update` or `yarn upgrade` - Update dependencies

### Build Commands
- `npm run build` - Build TypeScript and Vite production bundle
- `npm run dev` - Start Vite development server
- `npm run preview` - Build and preview production bundle
- `npm run deploy` - Build and deploy to Cloudflare Workers
- `npm run cf-typegen` - Generate Cloudflare types

### Testing Commands
- No test scripts configured yet (consider adding Vitest or Jest)
- Integration test script available: `./test-integration.sh`

### Code Quality Commands
- `npm run lint` - Run ESLint for code linting
- No lint:fix script configured (add `eslint . --fix`)
- No format script configured (consider adding Prettier)
- No explicit typecheck script (runs via `tsc -b` in build)

### Development Tools
- No Storybook configured
- No bundle analyzer configured (consider vite-bundle-visualizer)
- No clean script (add `rm -rf dist node_modules/.vite`)

## Technology Stack

### Core Technologies
- **JavaScript/TypeScript** - Primary programming languages
- **Node.js** - Runtime environment
- **npm/yarn** - Package management

### Frameworks & Libraries
- **React 19** - Latest React with hooks and functional components
- **Zustand** - State management (v5.0.7)
- **Monaco Editor** - Code editor component
- **Lucide React** - Icon library
- **Sonner** - Toast notifications
- **React Resizable Panels** - Layout management
- **@anthropic-ai/claude-code** - Claude Code SDK (v1.0.70)

### Build Tools
- **Vite 7** - Primary build tool and dev server
- **@vitejs/plugin-react-swc** - React Fast Refresh with SWC
- **@cloudflare/vite-plugin** - Cloudflare Workers integration
- **Wrangler** - Cloudflare Workers CLI and deployment tool
- **TypeScript 5.8** - Type checking and compilation

### Testing Framework
- No testing framework configured
- Recommended: Add Vitest for unit tests (integrates well with Vite)
- Consider @testing-library/react for component testing

### Code Quality Tools
- **ESLint 9** - JavaScript/TypeScript linter with:
  - typescript-eslint v8.35
  - eslint-plugin-react-hooks
  - eslint-plugin-react-refresh
- **TypeScript 5.8** - Static type checking
- No Prettier configured (recommend adding)
- No Husky configured (consider for pre-commit hooks)

## Project Structure Guidelines

### Current File Organization
```
src/
├── components/     # React UI components (Terminal, Header, etc.)
├── hooks/         # Custom React hooks (useAutoScrollNearBottom)
├── utils/         # Utility functions (ansi, crypto, persist)
├── store/         # Zustand state management
│   ├── history.state.ts
│   ├── messages.state.ts
│   ├── session.state.ts
│   └── toolCalls.state.ts
├── styles/        # CSS modules (terminal.css, animations.css)
├── assets/        # Static assets (SVGs)
└── worker/        # Cloudflare Worker code
```

### Naming Conventions (Current Project)
- **Files**: PascalCase for components (`Terminal.tsx`), camelCase for utilities (`ansi.ts`)
- **Components**: PascalCase (`Terminal`, `ChatPane`, `Header`)
- **Functions**: camelCase (`useAutoScrollNearBottom`, `parseAnsi`)
- **State files**: `.state.ts` suffix for Zustand stores
- **Types**: Defined in component files or `vite-env.d.ts`

## TypeScript Guidelines

### Type Safety
- Enable strict mode in `tsconfig.json`
- Use explicit types for function parameters and return values
- Prefer interfaces over types for object shapes
- Use union types for multiple possible values
- Avoid `any` type - use `unknown` when type is truly unknown

### Best Practices
- Use type guards for runtime type checking
- Leverage utility types (`Partial`, `Pick`, `Omit`, etc.)
- Create custom types for domain-specific data
- Use enums for finite sets of values
- Document complex types with JSDoc comments

## Code Quality Standards

### ESLint Configuration
- Use recommended ESLint rules for JavaScript/TypeScript
- Enable React-specific rules if using React
- Configure import/export rules for consistent module usage
- Set up accessibility rules for inclusive development

### Prettier Configuration
- Use consistent indentation (2 spaces recommended)
- Set maximum line length (80-100 characters)
- Use single quotes for strings
- Add trailing commas for better git diffs

### Testing Standards
- Aim for 80%+ test coverage
- Write unit tests for utilities and business logic
- Use integration tests for component interactions
- Implement e2e tests for critical user flows
- Follow AAA pattern (Arrange, Act, Assert)

## Performance Optimization

### Bundle Optimization
- Use code splitting for large applications
- Implement lazy loading for routes and components
- Optimize images and assets
- Use tree shaking to eliminate dead code
- Analyze bundle size regularly

### Runtime Performance
- Implement proper memoization (React.memo, useMemo, useCallback)
- Use virtualization for large lists
- Optimize re-renders in React applications
- Implement proper error boundaries
- Use web workers for heavy computations

## Security Guidelines

### Dependencies
- Regularly audit dependencies with `npm audit`
- Keep dependencies updated
- Use lock files (`package-lock.json`, `yarn.lock`)
- Avoid dependencies with known vulnerabilities

### Code Security
- Sanitize user inputs
- Use HTTPS for API calls
- Implement proper authentication and authorization
- Store sensitive data securely (environment variables)
- Use Content Security Policy (CSP) headers

## Development Workflow

### Before Starting
1. Check Node.js version (16+ required)
2. Install dependencies with `npm install`
3. Configure Cloudflare settings in `wrangler.jsonc`
4. Build project with `npm run build` to verify TypeScript

### During Development
1. Use TypeScript for type safety
2. Run linter frequently to catch issues early
3. Write tests for new features
4. Use meaningful commit messages
5. Review code changes before committing

### Before Committing
1. Check linting: `npm run lint`
2. Test production build: `npm run build`
3. Preview locally: `npm run preview`
4. Consider adding:
   - `npm run typecheck` script
   - Prettier formatting
   - Test suite