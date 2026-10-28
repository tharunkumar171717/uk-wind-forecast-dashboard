// All network calls live here. Base URL comes from VITE_API_BASE_URL; empty means same-origin /api.
const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function get(path, params) {
  const qs = params ? `?${new URLSearchParams(params)}` : ''
  let res
  try {
    res = await fetch(`${BASE}${path}${qs}`, { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach the API. Check that the backend is running.')
  }
  let body = null
  try {
    body = await res.json()
  } catch {
    // Non-JSON error page (e.g. proxy 502).
  }
  if (!res.ok) {
    const err = body?.error
    throw new ApiError(res.status, err?.code || 'http_error', err?.message || `Request failed (${res.status}).`)
  }
  return body
}

export const api = {
  health: () => get('/api/health'),
  metadata: () => get('/api/metadata'),
  forecasts: (date) => get('/api/forecasts', { date }),
  accuracy: (startDate, endDate) => get('/api/accuracy', { start_date: startDate, end_date: endDate }),
  deliveryAnalysis: (date) => get('/api/delivery-analysis', { date }),
}

export function exportUrl(startDate, endDate) {
  return `${BASE}/api/export?${new URLSearchParams({ start_date: startDate, end_date: endDate })}`
}
