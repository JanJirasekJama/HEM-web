import { ApiError } from '@/shared/api'

type ApiOptions = {
  body?: unknown
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  signal?: AbortSignal
}

const mutatingMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export async function operationsApi<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers = new Headers()
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  if (mutatingMethods.has(method)) {
    const csrf = sessionStorage.getItem('hem-csrf')
    if (csrf) headers.set('X-CSRF-Token', csrf)
  }

  const response = await fetch(path, {
    method,
    headers,
    credentials: 'include',
    signal: options.signal,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  if (!response.ok) throw new ApiError(response.status, await response.text())
  if (response.status === 204) return undefined as T
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return (await response.text()) as T
  return response.json() as Promise<T>
}

export function queryString(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function exportUrl(path: string, params: Record<string, string | number | boolean | null | undefined> = {}) {
  return `${path}${queryString(params)}`
}
