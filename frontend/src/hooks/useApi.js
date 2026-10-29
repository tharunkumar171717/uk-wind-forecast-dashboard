import { useCallback, useEffect, useState } from 'react'

/**
 * Run `fetcher` whenever `deps` change. Returns { data, error, loading, refreshing, reload }.
 * Previous data stays available while a new request loads (`refreshing`).
 * Stale responses from superseded requests are ignored.
 */
export function useApi(fetcher, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let active = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fetcher()
      .then((data) => active && setState({ data, error: null, loading: false }))
      .catch((error) => active && setState({ data: null, error, loading: false }))
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { ...state, refreshing: state.loading && state.data != null, reload }
}
