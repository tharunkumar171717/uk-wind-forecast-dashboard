import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import ChartCard from '../components/ChartCard'
import {
  AbsErrorChart,
  DailyTrendChart,
  ErrorHistogram,
  ForecastActualChart,
  LEGEND_DAILY,
  LEGEND_FORECAST_ACTUAL,
} from '../components/Charts'
import { DateRangePicker, EVAL_END, EVAL_START } from '../components/DateControls'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import KpiCard from '../components/KpiCard'
import { PageSkeleton, UpdatingBadge } from '../components/Skeleton'
import { useApi } from '../hooks/useApi'
import { fmtMW, fmtNum, fmtPct, fmtSignedMW } from '../utils/format'

export default function Accuracy() {
  const [params, setParams] = useSearchParams()
  const start = params.get('start') || EVAL_START
  const end = params.get('end') || EVAL_END
  const { data, error, loading, refreshing, reload } = useApi(() => api.accuracy(start, end), [start, end])
  const s = data?.summary

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">Forecast accuracy</h2>
            {refreshing && <UpdatingBadge />}
          </div>
          <p className="mt-0.5 text-sm text-muted">Matched hourly intervals only. Error = forecast − actual.</p>
        </div>
        <DateRangePicker start={start} end={end} onChange={(a, b) => setParams({ start: a, end: b })} />
      </div>

      {loading && !data && <PageSkeleton kpis={6} charts={2} />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && data.status === 'no_data' && <EmptyState />}

      {data && data.status === 'ok' && (
        <div className={`space-y-5 transition-opacity ${refreshing ? 'opacity-50' : ''}`} aria-busy={refreshing}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <KpiCard label="MAE" value={fmtMW(s.mae_mw)} hint="Typical size of error" />
            <KpiCard label="RMSE" value={fmtMW(s.rmse_mw)} hint="Penalises large misses" />
            <KpiCard label="Bias" value={fmtSignedMW(s.bias_mw)} hint={s.bias_mw > 0 ? 'Over-forecast on average' : 'Under-forecast on average'} />
            <KpiCard label="WAPE" value={fmtPct(s.wape_pct)} hint="Σ|error| / Σ actual" />
            <KpiCard
              label="MAPE"
              value={fmtPct(s.mape_pct)}
              hint={`Hours with actual ≥ ${fmtNum(s.mape_min_actual_mw)} MW; ${s.mape_excluded_intervals} excluded`}
            />
            <KpiCard label="Matched" value={`${fmtNum(s.matched_intervals)} / ${fmtNum(s.expected_intervals)}`} hint={`${fmtPct(s.completeness_pct)} complete`} />
          </div>

          <ChartCard title="Forecast vs actual over time" subtitle="Hourly MW, UK local time" legend={LEGEND_FORECAST_ACTUAL}>
            <ForecastActualChart series={data.series} multiDay />
          </ChartCard>

          <div className="grid gap-5 lg:grid-cols-2">
            <ChartCard title="Absolute error over time" subtitle="|forecast − actual|, MW per hour">
              <AbsErrorChart series={data.series} />
            </ChartCard>
            <ChartCard title="Error distribution" subtitle="Hours per 500 MW error bin. Right of 0 = over-forecast.">
              <ErrorHistogram bins={data.histogram} />
            </ChartCard>
          </div>

          <ChartCard title="Daily MAE and bias" subtitle="Per UK delivery day, MW" legend={LEGEND_DAILY}>
            <DailyTrendChart daily={data.daily} />
          </ChartCard>
        </div>
      )}
    </div>
  )
}
