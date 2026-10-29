import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import StatusBanner from './StatusBanner'
import { fmtFullUK } from '../utils/format'

const NAV = [
  { to: '/', label: 'Overview', end: true },
  { to: '/accuracy', label: 'Forecast Accuracy' },
  { to: '/delivery', label: 'Delivery-Day Analysis' },
  { to: '/methodology', label: 'Methodology & Data Quality' },
]

export default function Layout({ metadata }) {
  const [open, setOpen] = useState(false)
  const dataMode = metadata?.data_mode

  return (
    <div className="flex min-h-full">
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-60 shrink-0 bg-nav text-white transition-transform md:static md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Main navigation"
      >
        <div className="flex h-14 items-center gap-2 border-b border-white/10 px-4">
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          <div className="leading-tight">
            <div className="text-sm font-semibold">UK Wind Forecast</div>
            <div className="text-[11px] text-white/60">Accuracy dashboard</div>
          </div>
        </div>
        <nav className="flex flex-col gap-0.5 p-3">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${isActive ? 'bg-white/12 font-semibold text-white' : 'text-white/75 hover:bg-white/8 hover:text-white'}`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 w-full border-t border-white/10 p-4 text-[11px] leading-relaxed text-white/55">
          Source: Elexon BMRS (FUELHH, WINDFOR). Delivery window Jan 2026.
        </div>
      </aside>
      {open && <button aria-label="Close menu" className="fixed inset-0 z-20 bg-black/30 md:hidden" onClick={() => setOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col">
        <StatusBanner dataMode={dataMode} />
        <header className="flex h-14 items-center justify-between gap-3 border-b border-line bg-panel px-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md border border-line px-2 py-1 text-sm md:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open menu"
            >
              ☰
            </button>
            <h1 className="text-sm font-semibold text-ink sm:text-base">National wind forecast vs actual</h1>
          </div>
          <div className="text-right text-xs text-muted">
            <div>
              Cutoff: <span className="font-medium text-ink-2">{metadata?.cutoff ? `${metadata.cutoff.time_local} UK, D-${metadata.cutoff.days_before}` : 'Loading…'}</span>
            </div>
            <div className="hidden sm:block">
              Last data refresh: <span className="font-medium text-ink-2">{metadata ? fmtFullUK(metadata.last_successful_ingestion) : 'Loading…'}</span>
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
