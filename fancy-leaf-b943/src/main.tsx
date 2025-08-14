import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// Load project CSS after Tailwind so layers override as intended
import './styles/components.css'
import './styles/animations.css'
import './styles/claude-theme.css'
import App from './App'

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
