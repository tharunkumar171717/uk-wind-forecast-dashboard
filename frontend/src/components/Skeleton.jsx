import LoadingState from './LoadingState'

const Block = ({ className = '' }) => <div className={`animate-pulse rounded-md bg-line/70 ${className}`} />

/** Placeholder layout shown on first load, so the page keeps its shape while data arrives. */
export function PageSkeleton({ kpis = 6, charts = 1, table = false }) {
  return (
    <div className="space-y-5" aria-busy="true">
      <LoadingState />
      {kpis > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6" aria-hidden="true">
          {Array.from({ length: kpis }, (_, i) => (
            <div key={i} className="rounded-lg border border-line bg-panel px-4 py-3">
              <Block className="h-3 w-20" />
              <Block className="mt-2 h-6 w-24" />
              <Block className="mt-2 h-3 w-16" />
            </div>
          ))}
        </div>
      )}
      {Array.from({ length: charts }, (_, i) => (
        <div key={i} className="rounded-lg border border-line bg-panel p-4" aria-hidden="true">
          <Block className="h-4 w-48" />
          <Block className="mt-2 h-3 w-64" />
          <Block className="mt-4 h-56 w-full" />
        </div>
      ))}
      {table && (
        <div className="space-y-2 rounded-lg border border-line bg-panel p-4" aria-hidden="true">
          {Array.from({ length: 8 }, (_, i) => (
            <Block key={i} className="h-6 w-full" />
          ))}
        </div>
      )}
    </div>
  )
}

/** Small inline indicator while newer data replaces what is on screen. */
export function UpdatingBadge() {
  return (
    <span role="status" className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
      <span aria-hidden="true" className="h-3 w-3 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      Updating…
    </span>
  )
}
