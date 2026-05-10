export type QueryState<T> = {
  data: T | null
  error: string
  loading: boolean
  reload: () => void
}

export type ApiMutationState = {
  error: string
  loading: boolean
}

export type Message = {
  id: string
  message_date: string
  user_id: string
  content_text: string
  content_html?: string | null
  created_at: string
  updated_at: string
}

export type MessageComment = {
  id: string
  message_id: string
  user_id: string
  content_text: string
  color?: string | null
  created_at: string
}

export type SendMessageEmailResponse = {
  intent_id: string
  queued_recipients: string[]
  subject: string
  status: string
}

export type TaskItem = {
  id: string
  title: string
  description?: string | null
  due_date: string
  occurrence_date: string
  priority: string
  assigned_to_all: boolean
  assigned_user_id?: string | null
  recurrence_type?: 'weekly' | 'interval' | null
  recurrence_days: string[]
  recurrence_interval_days?: number | null
  recurrence_end_date?: string | null
  completed: boolean
}

export type TaskCalendar = {
  date: string
  tasks: TaskItem[]
  stats: {
    total: number
    open: number
    completed: number
    priority: Record<string, number>
  }
}

export type CashDiaryEntry = {
  id: string
  entry_date: string
  user_id: string
  shift_type: string
  cash_start?: number | null
  cash_end?: number | null
  difference?: number | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export type CashShiftLog = {
  id: string
  user_id: string
  shift_type: string
  start_time: string
  end_time?: string | null
  cash_start?: number | null
  created_at: string
}

export type CashDiaryHistory = {
  id: string
  diary_entry_id: string
  action: string
  changed_by_id?: string | null
  snapshot_json: Record<string, unknown>
  created_at: string
}

export type CashStatus = {
  date: string
  user_id: string
  missing_morning_cash: boolean
  missing_evening_cash: boolean
}

export type InventoryModule = 'wellness' | 'minibar' | 'lobby'

export type InventoryCatalogItem = {
  id: string
  name: string
  sort_order: number
  active: boolean
  module: InventoryModule
  unit: string
  category?: string | null
  price?: number | null
  has_price: boolean
}

export type CatalogBootstrap = {
  inventory_items: InventoryCatalogItem[]
}

export type InventoryEntryItem = {
  id: string
  item_id?: string | null
  item_name: string
  unit?: string | null
  custom_description?: string | null
  quantity: number
  unit_price: number
  total_price: number
  is_custom: boolean
  position: number
}

export type InventoryEntry = {
  id: string
  entry_date: string
  module: InventoryModule
  note?: string | null
  items: InventoryEntryItem[]
}

export type InventoryMonthlyReport = {
  module: InventoryModule
  month: string
  totals: Record<string, { quantity: number; total_price: number }>
  custom_total_price: number
}
