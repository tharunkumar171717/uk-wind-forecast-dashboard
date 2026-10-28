export default function ChartCard({ title, subtitle, legend, actions, children }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4" aria-label={title}>
      <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-4">
          {legend && (
            <ul className="flex flex-wrap gap-4 text-xs text-ink-2" aria-label="Legend">
              {legend.map((l) => (
                <li key={l.label} className="flex items-center gap-1.5">
                  <span
                    aria-hidden="true"
                    className={l.shape === 'bar' ? 'h-2.5 w-2.5 rounded-sm' : 'h-0.5 w-4 rounded'}
                    style={{ background: l.color }}
                  />
                  {l.label}
                </li>
              ))}
            </ul>
          )}
          {actions}
        </div>
      </header>
      {children}
    </section>
  )
}
