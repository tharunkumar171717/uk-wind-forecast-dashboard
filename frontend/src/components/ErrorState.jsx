export default function ErrorState({ error, onRetry }) {
  const unavailable = error?.status === 503
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm">
      <p className="font-semibold text-bad">{unavailable ? 'Data service unavailable' : 'Something went wrong'}</p>
      <p className="mt-1 text-ink-2">{error?.message || 'Unexpected error.'}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-line bg-panel px-3 py-1.5 font-medium text-ink hover:bg-canvas focus:outline-2 focus:outline-accent"
        >
          Retry
        </button>
      )}
    </div>
  )
}
