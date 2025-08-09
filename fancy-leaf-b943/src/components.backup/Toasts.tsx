import { useEffect, useRef, useCallback } from 'react'
import { useToolCalls } from '../store/toolCalls.state'
import { X, Info, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

const MAX_CONCURRENT_TOASTS = 3;
const DEDUPE_WINDOW_MS = 500;

export function Toasts() {
  const { toasts, removeToast } = useToolCalls()
  const lastAnnouncedRef = useRef<Map<string, number>>(new Map())
  const announcementQueueRef = useRef<string[]>([])
  const processingRef = useRef(false)
  
  const getIcon = (kind: string) => {
    switch (kind) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-emerald-400" aria-hidden="true" />
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" aria-hidden="true" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" aria-hidden="true" />
      default:
        return <Info className="w-4 h-4 text-blue-400" aria-hidden="true" />
    }
  }

  const getStyles = (kind: string) => {
    switch (kind) {
      case 'success':
        return 'border-emerald-500/30 bg-emerald-500/10'
      case 'error':
        return 'border-red-500/30 bg-red-500/10'
      case 'warning':
        return 'border-yellow-500/30 bg-yellow-500/10'
      default:
        return 'border-blue-500/30 bg-blue-500/10'
    }
  }
  
  const getAriaLive = (kind: string): 'polite' | 'assertive' => {
    return kind === 'error' ? 'assertive' : 'polite'
  }
  
  // Deduplicate and throttle announcements
  const shouldAnnounce = (message: string): boolean => {
    const now = Date.now()
    const lastAnnounced = lastAnnouncedRef.current.get(message)
    
    if (lastAnnounced && now - lastAnnounced < DEDUPE_WINDOW_MS) {
      return false
    }
    
    lastAnnouncedRef.current.set(message, now)
    
    // Clean up old entries
    for (const [key, time] of lastAnnouncedRef.current.entries()) {
      if (now - time > DEDUPE_WINDOW_MS * 10) {
        lastAnnouncedRef.current.delete(key)
      }
    }
    
    return true
  }
  
  // Process announcement queue
  const processAnnouncements = useCallback(() => {
    if (processingRef.current || announcementQueueRef.current.length === 0) {
      return
    }
    
    processingRef.current = true
    const announcement = announcementQueueRef.current.shift()
    
    if (announcement) {
      // Create temporary live region
      const liveRegion = document.createElement('div')
      liveRegion.setAttribute('role', 'status')
      liveRegion.setAttribute('aria-live', 'polite')
      liveRegion.setAttribute('aria-atomic', 'true')
      liveRegion.className = 'sr-only'
      liveRegion.textContent = announcement
      document.body.appendChild(liveRegion)
      
      setTimeout(() => {
        document.body.removeChild(liveRegion)
        processingRef.current = false
        processAnnouncements() // Process next in queue
      }, 100)
    } else {
      processingRef.current = false
    }
  }, [])
  
  // Queue announcements for new toasts
  useEffect(() => {
    toasts.forEach(toast => {
      const message = `${toast.kind}: ${toast.title}. ${toast.body || ''}`
      if (shouldAnnounce(message)) {
        announcementQueueRef.current.push(message)
      }
    })
    
    processAnnouncements()
  }, [toasts, processAnnouncements])
  
  // Limit visible toasts
  const visibleToasts = toasts.slice(0, MAX_CONCURRENT_TOASTS)
  const hiddenCount = toasts.length - visibleToasts.length

  return (
    <>
      <div 
        className="fixed top-16 right-4 z-50 space-y-2 pointer-events-none"
        role="region"
        aria-label="Notifications"
      >
        {visibleToasts.map((toast) => (
          <div
            key={toast.id}
            className={`
              toast-enter pointer-events-auto
              bg-[#0f1520]/95 backdrop-blur-sm border rounded-lg
              px-4 py-3 shadow-lg max-w-sm
              flex items-start gap-3
              ${getStyles(toast.kind)}
            `}
            role="alert"
            aria-live={getAriaLive(toast.kind)}
            aria-atomic="true"
          >
            {getIcon(toast.kind)}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-white text-sm">
                {toast.title}
              </div>
              {toast.body && (
                <div className="text-xs text-white/60 mt-1 break-words">
                  {toast.body}
                </div>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-white/40 hover:text-white/60 transition-colors focus:outline-none focus:ring-2 focus:ring-white/20"
              aria-label={`Dismiss ${toast.kind} notification: ${toast.title}`}
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        ))}
        
        {hiddenCount > 0 && (
          <div 
            className="text-xs text-white/40 text-center"
            role="status"
            aria-live="polite"
          >
            +{hiddenCount} more notification{hiddenCount > 1 ? 's' : ''}
          </div>
        )}
      </div>
    </>
  )
}