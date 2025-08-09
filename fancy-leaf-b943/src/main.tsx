import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// Load project CSS after Tailwind so layers override as intended
import './styles/components.misc.css'
import './styles/terminal.css'
import './styles/panels.css'
import './styles/animations.css'
import './styles/utilities.css'
// Component-specific styles
import './styles/header.css'
import './styles/transcript.css'
import './styles/toasts.css'
import './styles/prompt-bar.css'
import './styles/tool-call.css'
import './styles/copy-chip.css'
import './styles/file-tree.css'
import './styles/ribbon.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Register service worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(registration => {
        console.log('Service Worker registered:', registration)
      })
      .catch(error => {
        console.error('Service Worker registration failed:', error)
      })
  })
}
