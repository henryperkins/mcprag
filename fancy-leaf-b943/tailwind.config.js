// Tailwind config (ESM)
import forms from '@tailwindcss/forms'
import typography from '@tailwindcss/typography'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: 'var(--color-primary)',
        success: 'var(--color-success)',
        info: 'var(--color-info)',
        muted: 'var(--text-muted)',
        // Flatten color keys to ensure utilities are generated predictably
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'bg-elevated': 'var(--bg-elevated)',
      },
      borderColor: {
        subtle: 'var(--border-subtle)',
        faint: 'var(--border-faint)',
      },
      fontFamily: {
        mono: 'var(--font-mono)',
      },
    },
  },
  plugins: [forms(), typography()],
}
