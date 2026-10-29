import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import ChartCard from '../components/ChartCard'
import { ForecastActualChart, LEGEND_FORECAST_ACTUAL } from '../components/Charts'
import { DatePicker } from '../components/DateControls'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import KpiCard from '../components/KpiCard'
import { PageSkeleton, UpdatingBadge } from '../components/Skeleton'
import { useApi } from '../hooks/useApi'
import { fmtDay, fmtFullUK, fmtHours, fmtMW, fmtMWh, fmtPct, fmtSignedMW } from '../utils/format'

export default function Overview({ metadata }) {
  const [params, setParams] = useSearchParams()
  const date = params.get('date') || '2026-01-15'
  const { data, error, loading, refreshing, reload } = useApi(() => api.forecasts(date), [date])

  const k = data?.kpis
  const horizons = data?.series?.map((s) => s.horizon_hours).filter((h) => h != null) || []

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">Overview: {fmtDay(date)}</h2>
            {refreshing && <UpdatingBadge />}
          </div>
          <p className="mt-0.5 text-sm text-muted">Retrospective comparison: forecast as of cutoff vs actual outturn</p>
        </div>
        <DatePicker value={date} onChange={(d) => setParams({ date: d })} />
      </div>

      {loading && !data && <PageSkeleton kpis={6} charts={1} />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && data.status === 'no_data' && <EmptyState />}

      {data && data.status === 'ok' && (
        <div className={`space-y-5 transition-opacity ${refreshing ? 'opacity-50' : ''}`} aria-busy={refreshing}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <KpiCard label="Forecast energy" value={fmtMWh(k.forecast_energy_mwh)} hint={`Actual ${fmtMWh(k.actual_energy_mwh)}`} />
            <KpiCard label="Avg forecast" value={fmtMW(k.mean_forecast_mw)} />
            <KpiCard label="Avg actual" value={fmtMW(k.mean_actual_mw)} />
            <KpiCard label="MAE" value={fmtMW(k.mae_mw)} hint="Mean absolute error" />
            <KpiCard label="Bias" value={fmtSignedMW(k.bias_mw)} hint={k.bias_mw > 0 ? 'Forecast above actual' : k.bias_mw < 0 ? 'Forecast below actual' : ''} />
            <KpiCard label="Matched hours" value={`${k.matched_intervals} / ${k.expected_intervals}`} hint={`${fmtPct(k.completeness_pct)} complete`} />
          </div>

          <div className="grid gap-3 rounded-lg border border-line bg-panel p-4 text-sm sm:grid-cols-3">
            <div>
              <div className="text-xs text-muted">Decision cutoff used</div>
              <div className="font-medium">{fmtFullUK(data.cutoff_time)}</div>
            </div>
            <div>
              <div className="text-xs text-muted">Latest forecast publish time used</div>
              <div className="font-medium">{fmtFullUK(data.latest_publish_time_used)}</div>
            </div>
            <div>
              <div className="text-xs text-muted">Forecast horizon range</div>
              <div className="font-medium">
                {horizons.length ? `${fmtHours(Math.min(...horizons))} to ${fmtHours(Math.max(...horizons))}` : '–'}
              </div>
            </div>
          </div>

          <ChartCard
            title="Forecast vs actual wind generation"
            subtitle="Hourly average MW, UK local time. Hover for error and publish time."
            legend={LEGEND_FORECAST_ACTUAL}
          >
            <ForecastActualChart series={data.series} />
          </ChartCard>

          <aside className="rounded-lg border border-line bg-accent-soft p-4 text-sm text-ink-2" aria-label="How to read errors">
            <h3 className="mb-1 font-semibold text-ink">How to read errors</h3>
            <ul className="list-disc space-y-1 pl-5">
              <li><strong>Error = forecast − actual.</strong></li>
              <li><strong>Positive error</strong>: the forecast exceeded actual, so there was less wind than expected.</li>
              <li><strong>Negative error</strong>: there was more wind than forecast.</li>
              <li>A larger |error| means more uncertainty at decision time.</li>
            </ul>
          </aside>
          {metadata?.last_successful_ingestion && (
            <p className="text-xs text-muted">Last data refresh: {fmtFullUK(metadata.last_successful_ingestion)}</p>
          )}
        </div>
      )}
    </div>
  )
}
