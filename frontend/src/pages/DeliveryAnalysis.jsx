import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, exportUrl } from '../api/client'
import DataTable from '../components/DataTable'
import { DatePicker } from '../components/DateControls'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { PageSkeleton, UpdatingBadge } from '../components/Skeleton'
import QualityBadge from '../components/QualityBadge'
import { useApi } from '../hooks/useApi'
import { fmtDay, fmtDateTimeUK, fmtFullUK, fmtNum, QUALITY_LABELS } from '../utils/format'

const COLUMNS = [
  { key: 'delivery_time', label: 'Delivery time (UK)', render: (r) => fmtDateTimeUK(r.delivery_time) },
  { key: 'forecast_mw', label: 'Forecast MW', align: 'right', render: (r) => fmtNum(r.forecast_mw) },
  { key: 'actual_mw', label: 'Actual MW', align: 'right', render: (r) => fmtNum(r.actual_mw) },
  {
    key: 'error_mw',
    label: 'Error MW',
    align: 'right',
    render: (r) => (r.error_mw == null ? '–' : `${r.error_mw > 0 ? '+' : ''}${fmtNum(r.error_mw)}`),
  },
  { key: 'abs_error_mw', label: '|Error| MW', align: 'right', render: (r) => fmtNum(r.abs_error_mw) },
  { key: 'publish_time', label: 'Publish time (UK)', render: (r) => fmtDateTimeUK(r.publish_time) },
  { key: 'quality', label: 'Quality', render: (r) => <QualityBadge quality={r.quality} /> },
]

export default function DeliveryAnalysis() {
  const [params, setParams] = useSearchParams()
  const date = params.get('date') || '2026-01-15'
  const [quality, setQuality] = useState('all')
  const { data, error, loading, refreshing, reload } = useApi(() => api.deliveryAnalysis(date), [date])

  const rows = useMemo(
    () => (data?.rows || []).filter((r) => quality === 'all' || r.quality === quality),
    [data, quality],
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">Delivery-day analysis: {fmtDay(date)}</h2>
            {refreshing && <UpdatingBadge />}
          </div>
          <p className="mt-0.5 text-sm text-muted">
            Hourly intervals for the selected UK delivery day.
            {data?.cutoff_time && <> Cutoff: {fmtFullUK(data.cutoff_time)}.</>}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <DatePicker value={date} onChange={(d) => setParams({ date: d })} />
          <label className="flex flex-col gap-1 text-xs font-medium text-muted">
            Quality
            <select
              className="rounded-md border border-line bg-panel px-2.5 py-1.5 text-sm text-ink"
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
            >
              <option value="all">All</option>
              {Object.entries(QUALITY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <a
            href={exportUrl(date, date)}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
            download
          >
            Export CSV
          </a>
        </div>
      </div>

      {loading && !data && <PageSkeleton kpis={0} charts={0} table />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && data.status === 'no_data' && <EmptyState />}
      {data && data.status === 'ok' && (
        <div className={`transition-opacity ${refreshing ? 'opacity-50' : ''}`} aria-busy={refreshing}>
          <DataTable
            caption={`Hourly forecast vs actual for ${date}`}
            columns={COLUMNS}
            rows={rows.map((r) => ({ ...r, id: r.delivery_time }))}
            pageSize={12}
          />
        </div>
      )}
    </div>
  )
}
