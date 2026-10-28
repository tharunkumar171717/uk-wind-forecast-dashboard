import { useMemo, useState } from 'react'

/**
 * Generic sortable, paginated table.
 * columns: [{ key, label, render?(row), sortValue?(row), align? }]
 */
export default function DataTable({ columns, rows, pageSize = 12, initialSort, caption }) {
  const [sort, setSort] = useState(initialSort || { key: columns[0].key, dir: 'asc' })
  const [page, setPage] = useState(0)

  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort.key)
    const val = col?.sortValue || ((r) => r[sort.key])
    const out = [...rows].sort((a, b) => {
      const x = val(a)
      const y = val(b)
      if (x == null && y == null) return 0
      if (x == null) return 1 // missing values always last
      if (y == null) return -1
      return (x < y ? -1 : x > y ? 1 : 0) * (sort.dir === 'asc' ? 1 : -1)
    })
    return out
  }, [rows, sort, columns])

  const pages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const current = Math.min(page, pages - 1)
  const visible = sorted.slice(current * pageSize, current * pageSize + pageSize)

  const toggle = (key) => {
    setSort((s) => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }))
    setPage(0)
  }

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-line bg-panel">
        <table className="w-full min-w-[720px] text-sm">
          {caption && <caption className="sr-only">{caption}</caption>}
          <thead className="bg-canvas text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              {columns.map((c) => {
                const active = sort.key === c.key
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    className={`px-3 py-2 font-medium ${c.align === 'right' ? 'text-right' : ''}`}
                  >
                    <button type="button" onClick={() => toggle(c.key)} className="inline-flex items-center gap-1 hover:text-ink">
                      {c.label}
                      <span aria-hidden="true" className={active ? 'text-ink' : 'text-line'}>
                        {active && sort.dir === 'desc' ? '▼' : '▲'}
                      </span>
                    </button>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={r.id ?? i} className="border-t border-line hover:bg-canvas/60">
                {columns.map((c) => (
                  <td key={c.key} className={`tabular px-3 py-2 ${c.align === 'right' ? 'text-right' : ''}`}>
                    {c.render ? c.render(r) : r[c.key]}
                  </td>
                ))}
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-6 text-center text-muted">
                  No rows match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <nav className="mt-3 flex items-center justify-between text-sm text-ink-2" aria-label="Pagination">
        <span>
          {sorted.length === 0 ? 0 : current * pageSize + 1}–{Math.min(sorted.length, (current + 1) * pageSize)} of {sorted.length}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-md border border-line bg-panel px-3 py-1 disabled:opacity-40"
            onClick={() => setPage(current - 1)}
            disabled={current === 0}
          >
            Previous
          </button>
          <span className="px-1 py-1">
            Page {current + 1} / {pages}
          </span>
          <button
            type="button"
            className="rounded-md border border-line bg-panel px-3 py-1 disabled:opacity-40"
            onClick={() => setPage(current + 1)}
            disabled={current >= pages - 1}
          >
            Next
          </button>
        </div>
      </nav>
    </div>
  )
}
