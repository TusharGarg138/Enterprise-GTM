import { useState, useCallback } from 'react'

/**
 * Generic async data fetching hook with loading/error states.
 */
export function useAsync(asyncFn) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const result = await asyncFn(...args)
      setData(result)
      return result
    } catch (err) {
      setError(err.message || 'Unknown error')
      throw err
    } finally {
      setLoading(false)
    }
  }, [asyncFn])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setLoading(false)
  }, [])

  return { data, loading, error, execute, reset }
}

/**
 * Polling hook — repeatedly calls asyncFn until stopCondition returns true.
 */
export function usePolling(asyncFn, stopCondition, intervalMs = 3000) {
  const [data, setData] = useState(null)
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState(null)

  const startPolling = useCallback(async (...args) => {
    setPolling(true)
    setError(null)

    const poll = async () => {
      try {
        const result = await asyncFn(...args)
        setData(result)
        if (stopCondition(result)) {
          setPolling(false)
          return
        }
        setTimeout(poll, intervalMs)
      } catch (err) {
        setError(err.message)
        setPolling(false)
      }
    }

    poll()
  }, [asyncFn, stopCondition, intervalMs])

  return { data, polling, error, startPolling }
}
