import { useEffect, useState } from 'react'
import { onApiError } from '../api/errors'

type Toast = {
  id: number
  message: string
}

const TOAST_MS = 6500
const MAX_TOASTS = 3
let nextId = 1

/** Fixed-position stack of toasts for API failures; auto-dismisses. */
export function ToastHost() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(
    () => onApiError((message) => {
      const id = nextId++
      setToasts((current) => {
        if (current.length > 0 && current[current.length - 1].message === message) {
          return current
        }
        return [...current.slice(-(MAX_TOASTS - 1)), { id, message }]
      })
      window.setTimeout(
        () => setToasts((current) => current.filter((toast) => toast.id !== id)),
        TOAST_MS,
      )
    }),
    [],
  )

  if (toasts.length === 0) return null
  return (
    <div className="toast-stack" role="alert">
      {toasts.map((toast) => (
        <div className="toast" key={toast.id}>
          <span className="toast-text">{toast.message}</span>
          <button
            aria-label="Dismiss"
            className="toast-close"
            onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
            type="button"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
