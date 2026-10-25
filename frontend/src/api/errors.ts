// Tiny pub/sub for API failures. client.ts notifies on every rejected request;
// components/Toast.tsx subscribes and shows the toast.

export type ApiErrorListener = (message: string) => void

const listeners = new Set<ApiErrorListener>()

/** Subscribe to API failure notifications. Returns an unsubscribe function. */
export function onApiError(listener: ApiErrorListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Broadcast one API failure message to every subscriber. */
export function notifyApiError(message: string): void {
  for (const listener of listeners) listener(message)
}
