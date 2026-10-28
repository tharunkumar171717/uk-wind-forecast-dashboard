const TZ = 'Europe/London'

const nf0 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const nf1 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1, minimumFractionDigits: 1 })

const isNum = (v) => typeof v === 'number' && Number.isFinite(v)

export const fmtNum = (v) => (isNum(v) ? nf0.format(v) : '–')
export const fmtMW = (v) => (isNum(v) ? `${nf0.format(v)} MW` : '–')
export const fmtSignedMW = (v) => (isNum(v) ? `${v > 0 ? '+' : ''}${nf0.format(v)} MW` : '–')
export const fmtMWh = (v) => (isNum(v) ? `${nf0.format(v)} MWh` : '–')
export const fmtPct = (v) => (isNum(v) ? `${nf1.format(v)}%` : '–')
export const fmtHours = (v) => (isNum(v) ? `${nf1.format(v)} h` : '–')

const dtFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: TZ,
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})
const timeFmt = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false })
const fullFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: TZ,
  year: 'numeric',
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZoneName: 'short',
})

/** "15 Jan, 13:00" in UK local time. */
export const fmtDateTimeUK = (iso) => (iso ? dtFmt.format(new Date(iso)) : '–')
/** "13:00" in UK local time. */
export const fmtTimeUK = (iso) => (iso ? timeFmt.format(new Date(iso)) : '–')
/** "15 Jan 2026, 13:00 GMT" in UK local time, with zone. */
export const fmtFullUK = (iso) => (iso ? fullFmt.format(new Date(iso)) : '–')

/** "Thu 15 Jan 2026" from a YYYY-MM-DD date. */
export const fmtDay = (ymd) =>
  ymd
    ? new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(
        new Date(`${ymd}T00:00:00Z`),
      )
    : '–'

export const QUALITY_LABELS = {
  matched: 'Matched',
  missing_forecast: 'Missing forecast',
  missing_actual: 'Missing actual',
  partial_actual: 'Partial actual',
  missing_both: 'Missing both',
}
