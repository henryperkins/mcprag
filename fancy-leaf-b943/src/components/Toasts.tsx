import { useToolCalls } from '../store/toolCalls.state'
import { X, Info, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

export function Toasts() {
  const { toasts, removeToast } = useToolCalls()

  const getIcon = (kind: string) => {
    switch (kind) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-emerald-400" />
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />
      default:
        return <Info className="w-4 h-4 text-blue-400" />
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

  return (
    <div className="fixed top-16 right-4 z-50 space-y-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            toast-enter pointer-events-auto
            bg-[#0f1520]/95 backdrop-blur-sm border rounded-lg
            px-4 py-3 shadow-lg max-w-sm
            flex items-start gap-3
            ${getStyles(toast.kind)}
          `}
          role="status"
          aria-live="polite"
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
            className="text-white/40 hover:text-white/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}