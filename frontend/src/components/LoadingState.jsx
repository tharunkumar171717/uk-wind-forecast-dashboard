export default function LoadingState({ label = 'Loading data…' }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 rounded-lg border border-line bg-panel p-6 text-sm text-muted">
      <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      {label}
    </div>
  )
}
