import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import KpiCard from '../components/KpiCard'
import LoadingState from '../components/LoadingState'
import StatusBanner from '../components/StatusBanner'

describe('components', () => {
  it('KpiCard renders label, value and hint', () => {
    render(<KpiCard label="MAE" value="1,234 MW" hint="Mean absolute error" />)
    const card = screen.getByRole('group', { name: 'MAE' })
    expect(card).toHaveTextContent('1,234 MW')
    expect(card).toHaveTextContent('Mean absolute error')
  })

  it('LoadingState announces loading', () => {
    render(<LoadingState />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading data')
  })

  it('ErrorState shows the message and retries', async () => {
    const onRetry = vi.fn()
    render(<ErrorState error={{ status: 503, message: 'Database is unavailable.' }} onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Data service unavailable')
    expect(screen.getByRole('alert')).toHaveTextContent('Database is unavailable.')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('EmptyState tells the user to run ingestion', () => {
    render(<EmptyState />)
    expect(screen.getByText('No data yet: run ingestion')).toBeInTheDocument()
  })

  it('StatusBanner only shows for demo data', () => {
    const { rerender } = render(<StatusBanner dataMode="live" />)
    expect(screen.queryByRole('alert')).toBeNull()
    rerender(<StatusBanner dataMode="demo" />)
    expect(screen.getByRole('alert')).toHaveTextContent('SYNTHETIC DEMO DATA, not Elexon')
  })
})
