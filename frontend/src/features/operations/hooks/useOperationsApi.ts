import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { operationsApi } from '@/features/operations/api'
import type { ApiMutationState, QueryState } from '@/features/operations/types'

export function useDebouncedValue<T>(value: T, delayMs = 350): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(id)
  }, [delayMs, value])

  return debounced
}

export function useAbortableQuery<T>(path: string | null): QueryState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [version, setVersion] = useState(0)

  const reload = useCallback(() => setVersion((value) => value + 1), [])

  useEffect(() => {
    if (!path) {
      queueMicrotask(() => {
        setData(null)
        setLoading(false)
        setError('')
      })
      return undefined
    }

    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        setData(await operationsApi<T>(path, { signal: controller.signal }))
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Načtení se nepodařilo')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()

    return () => controller.abort()
  }, [path, version])

  return useMemo(() => ({ data, error, loading, reload }), [data, error, loading, reload])
}

export function useApiMutation() {
  const [state, setState] = useState<ApiMutationState>({ error: '', loading: false })
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const mutate = useCallback(async <T,>(path: string, options: Parameters<typeof operationsApi<T>>[1] = {}) => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setState({ error: '', loading: true })
    try {
      const result = await operationsApi<T>(path, { ...options, signal: controller.signal })
      setState({ error: '', loading: false })
      return result
    } catch (reason) {
      if (controller.signal.aborted) throw reason
      const message = reason instanceof Error ? reason.message : 'Operace se nepodařila'
      setState({ error: message, loading: false })
      throw reason
    }
  }, [])

  return { ...state, mutate }
}
