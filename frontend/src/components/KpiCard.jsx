export default function KpiCard({ label, value, hint, tone }) {
  const toneClass = tone === 'positive' ? 'text-brand' : tone === 'negative' ? 'text-bad' : 'text-ink'
  return (
    <div className="rounded-lg border border-line bg-panel px-4 py-3" role="group" aria-label={label}>
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className={`tabular mt-1 text-xl font-semibold ${toneClass}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  )
}
