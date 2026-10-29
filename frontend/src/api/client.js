// All network calls live here. Base URL comes from VITE_API_BASE_URL; empty means same-origin /api.
const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

// Free Render instances sleep when idle; while waking, requests fail or return 502/503/504.
// Retry those for about a minute instead of showing an error straight away.
const RETRY_STATUS = new Set([502, 503, 504])
export const RETRY_DELAYS_MS = import.meta.env.MODE === 'test' ? [] : [2000, 3000, 5000, 8000, 10000, 10000, 10000, 10000]

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function once(url) {
  let res
  try {
    res = await fetch(url, { headers: { Accept: 'application/json' } })
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

export async function requestWithRetry(url, delays = RETRY_DELAYS_MS) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await once(url)
    } catch (err) {
      const retryable = err.status === 0 || RETRY_STATUS.has(err.status)
      if (!retryable || attempt >= delays.length) throw err
      await sleep(delays[attempt])
    }
  }
}

function get(path, params) {
  const qs = params ? `?${new URLSearchParams(params)}` : ''
  return requestWithRetry(`${BASE}${path}${qs}`)
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
