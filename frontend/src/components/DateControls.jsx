export const EVAL_START = '2026-01-01'
export const EVAL_END = '2026-01-31'

const inputClass =
  'rounded-md border border-line bg-panel px-2.5 py-1.5 text-sm text-ink focus:border-accent focus:outline-2 focus:outline-accent/30'

export function DatePicker({ value, onChange, label = 'Delivery date' }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-muted">
      {label}
      <input
        type="date"
        className={inputClass}
        min={EVAL_START}
        max={EVAL_END}
        value={value}
        onChange={(e) => e.target.value && onChange(e.target.value)}
      />
    </label>
  )
}

export function DateRangePicker({ start, end, onChange }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs font-medium text-muted">
        From
        <input
          type="date"
          className={inputClass}
          min={EVAL_START}
          max={end}
          value={start}
          onChange={(e) => e.target.value && onChange(e.target.value, end)}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-muted">
        To
        <input
          type="date"
          className={inputClass}
          min={start}
          max={EVAL_END}
          value={end}
          onChange={(e) => e.target.value && onChange(start, e.target.value)}
        />
      </label>
      <button
        type="button"
        className="rounded-md border border-line bg-panel px-3 py-1.5 text-sm font-medium text-ink-2 hover:bg-canvas"
        onClick={() => onChange(EVAL_START, EVAL_END)}
      >
        All of January
      </button>
    </div>
  )
}
