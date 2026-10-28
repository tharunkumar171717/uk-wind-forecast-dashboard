import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import { fmtFullUK, fmtNum } from '../utils/format'

function Section({ title, children }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-5">
      <h3 className="mb-2 text-sm font-semibold text-ink">{title}</h3>
      <div className="space-y-2 text-sm leading-relaxed text-ink-2">{children}</div>
    </section>
  )
}

const Code = ({ children }) => <code className="rounded bg-canvas px-1 py-0.5 text-xs text-ink">{children}</code>

export default function Methodology({ meta }) {
  const m = meta?.data
  const cutoff = m?.cutoff ? `${m.cutoff.time_local} Europe/London on D-${m.cutoff.days_before}` : '10:00 Europe/London on D-1'

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold">Methodology & data quality</h2>

      <Section title="Data freshness & ingestion status">
        {meta?.loading && <LoadingState label="Loading metadata…" />}
        {meta?.error && <ErrorState error={meta.error} onRetry={meta.reload} />}
        {m && (
          <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
            <div><dt className="text-xs text-muted">Data mode</dt><dd className="font-medium">{m.data_mode === 'demo' ? 'Synthetic demo data' : 'Live (Elexon via Supabase)'}</dd></div>
            <div><dt className="text-xs text-muted">Last successful ingestion</dt><dd className="font-medium">{fmtFullUK(m.last_successful_ingestion)}</dd></div>
            <div><dt className="text-xs text-muted">Actual rows (half-hourly)</dt><dd className="tabular font-medium">{fmtNum(m.row_counts?.wind_actuals)}</dd></div>
            <div><dt className="text-xs text-muted">Forecast rows / vintages</dt><dd className="tabular font-medium">{fmtNum(m.row_counts?.wind_forecasts)} / {fmtNum(m.row_counts?.forecast_vintages)}</dd></div>
            <div><dt className="text-xs text-muted">FUELHH last ingested</dt><dd className="font-medium">{fmtFullUK(m.last_ingestion?.FUELHH)}</dd></div>
            <div><dt className="text-xs text-muted">WINDFOR last ingested</dt><dd className="font-medium">{fmtFullUK(m.last_ingestion?.WINDFOR)}</dd></div>
            <div><dt className="text-xs text-muted">Evaluation window</dt><dd className="font-medium">{m.evaluation_window.start_date} to {m.evaluation_window.end_date} (UK delivery days)</dd></div>
          </dl>
        )}
      </Section>

      <Section title="Datasets (Elexon Insights API, no key required)">
        <p><strong>FUELHH</strong> gives actual generation by fuel type for each half-hour settlement period, in MW. Only <Code>fuelType = WIND</Code> is used. There are 48 periods a day (46 or 50 on clock-change days). If a period is revised, the latest <Code>publishTime</Code> wins.</p>
        <p><strong>WINDFOR</strong> is the national wind generation forecast. It is published several times a day, and each <em>vintage</em> covers roughly the next 2–3 days with <strong>hourly</strong> values. Every vintage is stored, so any cutoff can be replayed.</p>
      </Section>

      <Section title="Decision cutoff (assumption)">
        <p>For each delivery day D we use the forecast that was <strong>available at decision time</strong>: for every hourly interval, the vintage with the latest <Code>publish_time ≤ cutoff(D)</Code>, where cutoff(D) = <strong>{cutoff}</strong>.</p>
        <p>This cutoff is an <strong>assumption</strong> modelled on GB day-ahead auction timing. It is not an official Elexon rule. Forecasts published after the cutoff are never used, and actuals never influence which forecast is chosen.</p>
        <p>The cutoff changes the results. A later cutoff means a shorter horizon between publication and delivery, and usually lower error. An earlier cutoff measures a longer-range forecast and usually shows higher error. Each interval reports its <Code>publish_time</Code>, <Code>cutoff_time</Code> and <Code>horizon_hours</Code>.</p>
      </Section>

      <Section title="Metrics (matched intervals only; error = forecast − actual)">
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>MAE</strong> = mean(|error|): the typical size of a miss, in MW.</li>
          <li><strong>RMSE</strong> = √mean(error²): like MAE, but large misses weigh more.</li>
          <li><strong>Bias</strong> = mean(error). Positive means over-forecasting on average.</li>
          <li><strong>WAPE</strong> = Σ|error| / Σ|actual| × 100. Shown as null when Σ|actual| = 0.</li>
          <li><strong>MAPE</strong> = mean(|error| / actual) × 100, only where actual ≥ {fmtNum(m?.mape_min_actual_mw ?? 1000)} MW, so near-zero actuals don't inflate it. The number of excluded hours is reported.</li>
          <li><strong>Energy (MWh)</strong> = Σ hourly average MW × 1 h.</li>
          <li><strong>Completeness</strong> = matched hours / expected hours in the period.</li>
        </ul>
      </Section>

      <Section title="Alignment & missing-data rules">
        <p>Forecasts are hourly and actuals are half-hourly. The hourly actual is the <strong>mean</strong> of the two settlement periods starting at HH:00 and HH:30, because both are average MW. Rows are joined on timestamp, never on row position.</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>matched</strong>: forecast and both half-hours present. Only these hours count in the metrics.</li>
          <li><strong>partial_actual</strong>: only one half-hour present. Excluded from metrics.</li>
          <li><strong>missing_forecast</strong>, <strong>missing_actual</strong>, <strong>missing_both</strong>: excluded from metrics and shown in the table.</li>
          <li>Rows with NaN, negative, or absurd (&gt; 60,000 MW) values are rejected at ingestion. They are never treated as zero.</li>
        </ul>
      </Section>

      <Section title="Timezone handling">
        <p>All timestamps are stored in UTC (<Code>timestamptz</Code>). Delivery days are <strong>Europe/London</strong> calendar days, so 29 Mar 2026 has 23 hours and 25 Oct 2026 has 25. The UI shows UK local time.</p>
      </Section>

      <Section title="Known limitations">
        <ul className="list-disc space-y-1 pl-5">
          <li>FUELHH wind is metered transmission-connected output. It reflects curtailment and excludes most embedded (distribution-connected) wind, so it may not measure exactly the same quantity as WINDFOR. A persistent bias can partly reflect this rather than pure forecast skill.</li>
          <li>The cutoff is an assumed decision time, not a market rule.</li>
          <li>Only January 2026 is ingested. Results for one winter month may not generalise.</li>
          <li>This is a retrospective accuracy view. It does not model demand, prices, purchase volumes or financial impact.</li>
        </ul>
      </Section>
    </div>
  )
}
