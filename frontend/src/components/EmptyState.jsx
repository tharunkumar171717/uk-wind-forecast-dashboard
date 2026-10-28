export default function EmptyState({ title = 'No data yet: run ingestion', children }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-panel p-6 text-sm">
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-1 text-ink-2">
        {children || (
          <>
            Load January 2026 from Elexon with{' '}
            <code className="rounded bg-canvas px-1 py-0.5 text-xs">python -m app.ingest --start 2026-01-01 --end 2026-01-31</code>.
          </>
        )}
      </p>
    </div>
  )
}
