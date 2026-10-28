import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const hours = Array.from({ length: 24 }, (_, i) => {
  const t = new Date(Date.UTC(2026, 0, 15, i)).toISOString()
  return {
    delivery_time: t, forecast_mw: 1100, actual_mw: 1000, error_mw: 100, abs_error_mw: 100,
    publish_time: '2026-01-14T09:30:00Z', cutoff_time: '2026-01-14T10:00:00Z', horizon_hours: 14.5 + i, quality: 'matched',
  }
})
const kpis = {
  matched_intervals: 24, expected_intervals: 24, completeness_pct: 100, mae_mw: 100, rmse_mw: 100, bias_mw: 100,
  wape_pct: 10, mape_pct: 10, mape_min_actual_mw: 1000, mape_intervals: 24, mape_excluded_intervals: 0,
  mean_forecast_mw: 1100, mean_actual_mw: 1000, forecast_energy_mwh: 26400, actual_energy_mwh: 24000, quality_counts: { matched: 24 },
}
const metadata = {
  data_mode: 'live', cutoff: { time_local: '10:00', days_before: 1 }, last_successful_ingestion: '2026-10-28T16:22:30Z',
  row_counts: { wind_actuals: 1584, wind_forecasts: 18980, forecast_vintages: 260 }, last_ingestion: {},
  evaluation_window: { start_date: '2026-01-01', end_date: '2026-01-31' }, mape_min_actual_mw: 1000,
}

function mockFetch(routes) {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    const path = new URL(url, 'http://x').pathname
    const [status, body] = routes[path] || [404, { error: { code: 'not_found', message: 'nope' } }]
    return { ok: status < 400, status, json: async () => body }
  }))
}

const renderAt = (path) => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)

afterEach(() => vi.unstubAllGlobals())

describe('pages with mocked API', () => {
  it('Overview renders KPIs and cutoff details', async () => {
    mockFetch({
      '/api/metadata': [200, metadata],
      '/api/forecasts': [200, { status: 'ok', data_mode: 'live', date: '2026-01-15', cutoff_time: '2026-01-14T10:00:00Z', latest_publish_time_used: '2026-01-14T09:30:00Z', kpis, series: hours }],
    })
    renderAt('/?date=2026-01-15')
    expect(await screen.findByRole('group', { name: 'MAE' })).toHaveTextContent('100 MW')
    expect(screen.getByRole('group', { name: 'Bias' })).toHaveTextContent('+100 MW')
    expect(screen.getByText(/Retrospective comparison: forecast as of cutoff vs actual outturn/)).toBeInTheDocument()
    expect(screen.getByText('How to read errors')).toBeInTheDocument()
    expect(screen.getByText('Latest forecast publish time used')).toBeInTheDocument()
  })

  it('Overview shows the empty state when there is no data', async () => {
    mockFetch({
      '/api/metadata': [200, metadata],
      '/api/forecasts': [200, { status: 'no_data', data_mode: 'live', date: '2026-01-15', cutoff_time: '2026-01-14T10:00:00Z', latest_publish_time_used: null, kpis: { ...kpis, matched_intervals: 0 }, series: [] }],
    })
    renderAt('/')
    expect(await screen.findByText('No data yet: run ingestion')).toBeInTheDocument()
  })

  it('Accuracy page shows API errors', async () => {
    mockFetch({
      '/api/metadata': [200, metadata],
      '/api/accuracy': [503, { error: { code: 'database_unavailable', message: 'Database is unavailable. Try again later.' } }],
    })
    renderAt('/accuracy')
    expect(await screen.findByText('Database is unavailable. Try again later.')).toBeInTheDocument()
  })

  it('Delivery analysis renders the table and export link', async () => {
    mockFetch({
      '/api/metadata': [200, metadata],
      '/api/delivery-analysis': [200, { status: 'ok', data_mode: 'live', date: '2026-01-15', cutoff_time: '2026-01-14T10:00:00Z', rows: hours }],
    })
    renderAt('/delivery?date=2026-01-15')
    expect(await screen.findByText('1–12 of 24')).toBeInTheDocument()
    expect(screen.getAllByText('Matched').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Export CSV' })).toHaveAttribute('href', '/api/export?start_date=2026-01-15&end_date=2026-01-15')
  })

  it('demo mode shows the synthetic data banner', async () => {
    mockFetch({
      '/api/metadata': [200, { ...metadata, data_mode: 'demo' }],
      '/api/forecasts': [200, { status: 'no_data', data_mode: 'demo', date: '2026-01-15', cutoff_time: '2026-01-14T10:00:00Z', latest_publish_time_used: null, kpis, series: [] }],
    })
    renderAt('/')
    expect(await screen.findByText(/SYNTHETIC DEMO DATA, not Elexon/)).toBeInTheDocument()
  })
})
