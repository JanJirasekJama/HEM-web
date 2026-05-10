import { useCallback, useEffect, useState } from 'react'

import type {
  CatalogBootstrap,
  ExportRecord,
  InventoryMonthlyReport,
  Invoice,
  InvoiceCreatePayload,
  InvoiceEmailIntent,
  InvoiceStatistics,
  InvoiceTaxReport,
} from './types'

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

export function useFinanceResource<T>(loader: (signal: AbortSignal) => Promise<T>, deps: React.DependencyList = []) {
  const [state, setState] = useState<ApiState<T>>(emptyState<T>)

  const reload = useCallback(() => {
    const controller = new AbortController()
    setState((current) => ({ ...current, loading: true, error: '' }))
    loader(controller.signal)
      .then((data) => setState({ data, loading: false, error: '' }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({ data: null, loading: false, error: error instanceof Error ? error.message : 'Akce se nepodařila' })
      })
    return () => controller.abort()
  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/use-memo
  }, deps)

  useEffect(() => reload(), [reload])

  return { ...state, reload }
}

export function loadFinanceBootstrap(signal: AbortSignal) {
  return apiRequest<CatalogBootstrap>('/api/catalog/bootstrap?active_only=false', {}, signal)
}

export function loadInvoiceArchive(signal: AbortSignal) {
  return apiRequest<Invoice[]>('/api/invoices/archive', {}, signal)
}

export function createInvoice(payload: InvoiceCreatePayload) {
  return apiRequest<Invoice>('/api/invoices', { method: 'POST', body: JSON.stringify(payload) })
}

export function refreshInvoiceStatuses() {
  return apiRequest<{ updated: number }>('/api/invoices/archive/refresh-statuses', { method: 'POST', body: JSON.stringify({}) })
}

export function markInvoicePaid(invoiceId: string) {
  return apiRequest<Invoice>(`/api/invoices/${invoiceId}/mark-paid`, { method: 'PATCH' })
}

export function markInvoiceUnpaid(invoiceId: string) {
  return apiRequest<Invoice>(`/api/invoices/${invoiceId}/mark-unpaid`, { method: 'PATCH' })
}

export function queueInvoiceEmail(invoiceId: string) {
  return apiRequest<InvoiceEmailIntent>(`/api/invoices/${invoiceId}/send-email`, { method: 'POST' })
}

export function archiveCsvUrl() {
  return '/api/invoices/archive/export.csv'
}

export function invoicePdfUrl(invoiceId: string) {
  return `/api/invoices/${invoiceId}/pdf`
}

export function loadInvoiceStatistics(dateFrom: string, dateTo: string, signal: AbortSignal) {
  return apiRequest<InvoiceStatistics>(`/api/reports/invoices/statistics?date_from=${dateFrom}&date_to=${dateTo}`, {}, signal)
}

export function loadInvoiceTax(dateFrom: string, dateTo: string, signal: AbortSignal) {
  return apiRequest<InvoiceTaxReport>(`/api/reports/invoices/tax?date_from=${dateFrom}&date_to=${dateTo}`, {}, signal)
}

export function loadInventoryMonthly(module: string, month: string, signal: AbortSignal) {
  return apiRequest<InventoryMonthlyReport>(`/api/reports/inventory/monthly?module=${module}&month=${month}`, {}, signal)
}

export function createReportExport(payload: { module: string; export_type: string; period_from?: string; period_to?: string }) {
  return apiRequest<ExportRecord>('/api/reports/exports', { method: 'POST', body: JSON.stringify(payload) })
}
