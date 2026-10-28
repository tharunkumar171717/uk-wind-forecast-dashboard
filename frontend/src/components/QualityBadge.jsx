import { QUALITY_LABELS } from '../utils/format'

const STYLES = {
  matched: 'bg-brand-soft text-brand border-green-200',
  partial_actual: 'bg-amber-50 text-warn border-amber-200',
  missing_forecast: 'bg-red-50 text-bad border-red-200',
  missing_actual: 'bg-red-50 text-bad border-red-200',
  missing_both: 'bg-red-50 text-bad border-red-200',
}
const ICON = { matched: '✓', partial_actual: '◐' }

export default function QualityBadge({ quality }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[quality] || ''}`}>
      <span aria-hidden="true">{ICON[quality] || '✕'}</span>
      {QUALITY_LABELS[quality] || quality}
    </span>
  )
}
