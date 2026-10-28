import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtDateTimeUK, fmtFullUK, fmtMW, fmtNum, fmtSignedMW, fmtTimeUK } from '../utils/format'

const C = {
  forecast: 'var(--color-forecast)',
  actual: 'var(--color-actual)',
  grid: 'var(--color-grid)',
  axis: 'var(--color-muted)',
}
const axisProps = { tick: { fontSize: 11, fill: C.axis }, tickLine: false, axisLine: { stroke: 'var(--color-line)' } }
const yAxisProps = { ...axisProps, axisLine: false, width: 64, tickFormatter: (v) => fmtNum(v) }
// Zero-based MW axis rounded up to a whole step, so ticks land on round numbers (0, 5,000, 10,000, ...).
const roundedMW = { domain: [0, (max) => Math.max(1000, Math.ceil(max / 5000) * 5000)], tickCount: 5 }
const roundedSmall = { domain: [0, (max) => Math.max(500, Math.ceil(max / 2000) * 2000)], tickCount: 5 }

export const LEGEND_FORECAST_ACTUAL = [
  { label: 'Forecast (as of cutoff)', color: C.forecast },
  { label: 'Actual outturn', color: C.actual },
]

function TooltipBox({ title, rows }) {
  return (
    <div className="rounded-md border border-line bg-panel px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-semibold text-ink">{title}</div>
      <dl className="grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        {rows.map(([k, v, color]) => (
          <div key={k} className="contents">
            <dt className="flex items-center gap-1.5 text-muted">
              {color && <span aria-hidden="true" className="h-0.5 w-3 rounded" style={{ background: color }} />}
              {k}
            </dt>
            <dd className="tabular text-right text-ink">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function IntervalTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <TooltipBox
      title={`${fmtFullUK(p.delivery_time)}`}
      rows={[
        ['Forecast', fmtMW(p.forecast_mw), C.forecast],
        ['Actual', fmtMW(p.actual_mw), C.actual],
        ['Error (F − A)', fmtSignedMW(p.error_mw)],
        ['Published', fmtDateTimeUK(p.publish_time)],
        ['Quality', p.quality],
      ]}
    />
  )
}

/** Forecast vs actual over time (one shared MW axis). */
export function ForecastActualChart({ series, multiDay = false, height = 300 }) {
  const tickFmt = multiDay ? (v) => fmtDateTimeUK(v).split(',')[0] : fmtTimeUK
  return (
    <div style={{ height }} role="img" aria-label="Line chart of forecast and actual wind generation in MW">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="delivery_time" tickFormatter={tickFmt} minTickGap={multiDay ? 40 : 24} {...axisProps} />
          <YAxis {...yAxisProps} {...roundedMW} />
          <Tooltip content={<IntervalTooltip />} cursor={{ stroke: 'var(--color-muted)', strokeDasharray: '3 3' }} />
          <Line type="monotone" dataKey="forecast_mw" name="Forecast" stroke={C.forecast} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="actual_mw" name="Actual" stroke={C.actual} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Absolute error per hour. */
export function AbsErrorChart({ series, height = 240 }) {
  return (
    <div style={{ height }} role="img" aria-label="Line chart of absolute forecast error in MW">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="delivery_time" tickFormatter={(v) => fmtDateTimeUK(v).split(',')[0]} minTickGap={40} {...axisProps} />
          <YAxis {...yAxisProps} {...roundedSmall} />
          <Tooltip content={<IntervalTooltip />} cursor={{ stroke: 'var(--color-muted)', strokeDasharray: '3 3' }} />
          <Line type="monotone" dataKey="abs_error_mw" name="|Error|" stroke={C.forecast} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function HistTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return <TooltipBox title={`${fmtSignedMW(p.bin_start)} to ${fmtSignedMW(p.bin_end)}`} rows={[['Hours', fmtNum(p.count)]]} />
}

/** Distribution of hourly errors. */
export function ErrorHistogram({ bins, height = 240 }) {
  const data = bins.map((b) => ({ ...b, mid: (b.bin_start + b.bin_end) / 2 }))
  return (
    <div style={{ height }} role="img" aria-label="Histogram of hourly forecast errors in MW">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barCategoryGap={2}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="mid" tickFormatter={(v) => fmtNum(v)} {...axisProps} />
          <YAxis {...yAxisProps} width={40} allowDecimals={false} />
          <Tooltip content={<HistTooltip />} cursor={{ fill: 'var(--color-canvas)' }} />
          <Bar dataKey="count" fill={C.forecast} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function DailyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <TooltipBox
      title={p.date}
      rows={[
        ['MAE', fmtMW(p.mae_mw), C.forecast],
        ['Bias', fmtSignedMW(p.bias_mw), C.actual],
        ['Matched', `${p.matched_intervals}/${p.expected_intervals} h`],
      ]}
    />
  )
}

export const LEGEND_DAILY = [
  { label: 'Daily MAE', color: C.forecast, shape: 'bar' },
  { label: 'Daily bias', color: C.actual },
]

/** Daily MAE (bars) and bias (line), both in MW on one axis. */
export function DailyTrendChart({ daily, height = 260 }) {
  return (
    <div style={{ height }} role="img" aria-label="Daily MAE and bias in MW">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={daily} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="date" tickFormatter={(d) => String(Number(d.slice(8)))} {...axisProps} />
          <YAxis {...yAxisProps} />
          <ReferenceLine y={0} stroke="var(--color-muted)" />
          <Tooltip content={<DailyTooltip />} cursor={{ fill: 'var(--color-canvas)' }} />
          <Bar dataKey="mae_mw" fill={C.forecast} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Line type="monotone" dataKey="bias_mw" stroke={C.actual} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
