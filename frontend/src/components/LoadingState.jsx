import { useEffect, useState } from 'react'

const SLOW_AFTER_S = 4

/** Spinner with elapsed time; explains the free-tier cold start when loading is slow. */
export default function LoadingState({ label = 'Loading data…' }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [])
  const slow = seconds >= SLOW_AFTER_S

  return (
    <div role="status" aria-live="polite" className="rounded-lg border border-line bg-panel p-4 text-sm">
      <div className="flex items-center gap-3 text-ink-2">
        <span aria-hidden="true" className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-line border-t-accent" />
        <span>{label}</span>
        {slow && <span className="tabular ml-auto text-xs text-muted">{seconds}s</span>}
      </div>
      {slow && (
        <div className="mt-3">
          <p className="text-xs text-muted">
            Waking up the data server. It runs on a free plan that sleeps when idle, so the first request can take up to a
            minute. It's fast after that.
          </p>
          <div className="mt-2 h-1 overflow-hidden rounded bg-canvas" aria-hidden="true">
            <div
              className="h-full rounded bg-accent transition-[width] duration-1000 ease-linear"
              style={{ width: `${Math.min(95, (seconds / 60) * 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
