export type CatalogItem = {
  id: string
  name: string
  sort_order: number
  active: boolean
}

export type ServiceCategory = CatalogItem

export type ServiceItem = CatalogItem & {
  category_id: string
  type: string
  price: number
}

export type DueTerm = CatalogItem & {
  value: number
  unit: string
}

export type CatalogBootstrap = {
  service_categories: ServiceCategory[]
  services: ServiceItem[]
  due_terms: DueTerm[]
}

export type Invoice = {
  id: string
  invoice_number: string
  variable_symbol: string
  customer_name: string
  customer_email?: string | null
  customer_phone?: string | null
  service_id?: string | null
  service_name: string
  custom_service_name?: string | null
  event_at: string
  due_at: string
  due_term_id: string
  due_term_name: string
  due_term_value: number
  due_term_unit: string
  base_price: number
  increase_percent: number
  price: number
  note?: string | null
  pdf_path: string
  payment_status: 'pending' | 'paid' | 'unpaid' | 'overdue' | string
  created_at: string
  updated_at: string
}

export type InvoiceCreatePayload = {
  customer_name: string
  customer_email?: string
  customer_phone?: string
  service_id?: string
  custom_service_name?: string
  event_at: string
  due_term_id: string
  price?: number
  increase_percent: number
  note?: string
}

export type InvoiceEmailIntent = {
  intent_id: string
  invoice_id: string
  recipient: string
  sender: string
  subject: string
  status: string
}

export type InvoiceStatistics = {
  invoice_count: number
  paid_count: number
  unpaid_count: number
  pending_count: number
  total_amount: number
  average_invoice: number
  most_common_service?: string | null
  highest_turnover_service?: string | null
  by_service: Record<string, number>
}

export type InvoiceTaxReport = {
  gross_revenue: number
  vat_rate: number
  vat: number
  net_revenue: number
  by_service: Record<string, { gross: number; net: number; vat: number }>
}

export type InventoryMonthlyReport = {
  module: string
  month: string
  totals: Record<string, { quantity: number; total_price: number }>
  custom_total_price: number
}

export type ExportRecord = {
  id: string
  export_type: string
  module: string
  period_from?: string | null
  period_to?: string | null
  file_path: string
  created_at: string
}
