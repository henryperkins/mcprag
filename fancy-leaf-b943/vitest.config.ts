import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const rootDir = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  // Make root explicit so the VS Code extension resolves paths correctly
  root: rootDir,
  esbuild: { jsx: "automatic", jsxImportSource: "react" },
  test: {
    globals: true,
    environment: 'jsdom',
    // Normalize to an array and absolute path to avoid index/resolve issues
    setupFiles: [resolve(rootDir, 'src/test/setup.ts')],
    // Help the explorer find tests without guessing
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.config.ts',
        'src/vite-env.d.ts',
      ],
    },
  },
})

