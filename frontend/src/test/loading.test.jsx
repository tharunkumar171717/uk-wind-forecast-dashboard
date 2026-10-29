import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { requestWithRetry } from '../api/client'
import LoadingState from '../components/LoadingState'
import { PageSkeleton } from '../components/Skeleton'

const reply = (status, body) => ({ ok: status < 400, status, json: async () => body })

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('loading experience', () => {
  it('explains the cold start once loading is slow', () => {
    vi.useFakeTimers()
    render(<LoadingState />)
    expect(screen.queryByText(/Waking up the data server/)).toBeNull()
    act(() => vi.advanceTimersByTime(5000))
    expect(screen.getByText(/Waking up the data server/)).toBeInTheDocument()
    expect(screen.getByText('5s')).toBeInTheDocument()
  })

  it('page skeleton is marked busy and announces loading', () => {
    const { container } = render(<PageSkeleton kpis={3} charts={1} />)
    expect(container.firstChild).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Loading data')
  })

  it('retries while the server wakes up, then succeeds', async () => {
    const fetch = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(reply(502, null))
      .mockResolvedValueOnce(reply(200, { ok: true }))
    vi.stubGlobal('fetch', fetch)
    await expect(requestWithRetry('/api/health', [0, 0, 0])).resolves.toEqual({ ok: true })
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('does not retry client errors', async () => {
    const fetch = vi.fn().mockResolvedValue(reply(422, { error: { code: 'invalid_range', message: 'bad' } }))
    vi.stubGlobal('fetch', fetch)
    await expect(requestWithRetry('/api/accuracy', [0, 0])).rejects.toMatchObject({ status: 422, code: 'invalid_range' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('gives up after the retry budget', async () => {
    const fetch = vi.fn().mockResolvedValue(reply(503, { error: { code: 'database_unavailable', message: 'down' } }))
    vi.stubGlobal('fetch', fetch)
    await expect(requestWithRetry('/api/accuracy', [0, 0])).rejects.toMatchObject({ status: 503 })
    expect(fetch).toHaveBeenCalledTimes(3)
  })
})
