/** Data-mode banner. Demo data is always labelled so it can never be mistaken for Elexon data. */
export default function StatusBanner({ dataMode }) {
  if (dataMode !== 'demo') return null
  return (
    <div role="alert" className="border-b border-yellow-300 bg-yellow-100 px-4 py-2 text-sm font-semibold text-yellow-900">
      ⚠ SYNTHETIC DEMO DATA, not Elexon. Figures on this page are generated for demonstration only.
    </div>
  )
}
