import { useCallback, useEffect, useState } from 'react'

import type { BackupRecord, CatalogBootstrap, CatalogKind, CatalogRecord, JsonValue, RecoveryPoint, RestoreResult, SettingRead } from './types'

type ApiState<T> = {
  data: T | null
  loading: boolean
  error: string
}

const emptyState = <T,>(): ApiState<T> => ({ data: null, loading: false, error: '' })

function csrfToken() {
  return sessionStorage.getItem('hem-csrf') || ''
}

async function apiRequest<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    signal,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init.method && init.method !== 'GET' ? { 'X-CSRF-Token': csrfToken() } : {}),
      ...init.headers,
    },
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function useAdminResource<T>(loader: (signal: AbortSignal) => Promise<T>, deps: React.DependencyList = []) {
  const [state, setState] = useState<ApiState<T>>(emptyState<T>)

  const reload = useCallback(() => {
    const controller = new AbortController()
    setState((current) => ({ ...current, loading: true, error: '' }))
    loader(controller.signal)
      .then((data) => setState({ data, loading: false, error: '' }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({ data: null, loading: false, error: error instanceof Error ? error.message : 'Načtení se nepodařilo' })
      })
    return () => controller.abort()
  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/use-memo
  }, deps)

  useEffect(() => reload(), [reload])

  return { ...state, reload }
}

export function loadSetting(key: string, signal: AbortSignal) {
  return apiRequest<SettingRead>(`/api/settings/${key}`, {}, signal)
}

export function saveSetting(key: string, value: JsonValue) {
  return apiRequest<SettingRead>(`/api/settings/${key}`, { method: 'PUT', body: JSON.stringify({ value }) })
}

export function loadCatalog(signal: AbortSignal) {
  return apiRequest<CatalogBootstrap>('/api/catalog/bootstrap?active_only=false', {}, signal)
}

export function createCatalogItem(kind: CatalogKind, payload: Record<string, unknown>) {
  return apiRequest<CatalogRecord>(`/api/catalog/${kind}`, { method: 'POST', body: JSON.stringify(payload) })
}

export function updateCatalogItem(kind: CatalogKind, id: string, payload: Record<string, unknown>) {
  return apiRequest<CatalogRecord>(`/api/catalog/${kind}/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function deleteCatalogItem(kind: CatalogKind, id: string) {
  return apiRequest<{ ok: boolean }>(`/api/catalog/${kind}/${id}`, { method: 'DELETE' })
}

export function loadBackups(signal: AbortSignal) {
  return apiRequest<BackupRecord[]>('/api/backups', {}, signal)
}

export function createManualBackup(note: string) {
  return apiRequest<BackupRecord>('/api/backups/manual', { method: 'POST', body: JSON.stringify({ note: note || null }) })
}

export function deleteBackup(id: string) {
  return apiRequest<{ ok: boolean }>(`/api/backups/${id}`, { method: 'DELETE' })
}

export function createRecoveryPoint(description: string) {
  return apiRequest<RecoveryPoint>('/api/backups/recovery-points', { method: 'POST', body: JSON.stringify({ description: description || null }) })
}

export function restoreRecoveryPoint(id: string) {
  return apiRequest<RestoreResult>(`/api/backups/recovery-points/${id}/restore`, { method: 'POST' })
}
