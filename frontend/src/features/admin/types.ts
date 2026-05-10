export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue }

export type SettingRead = {
  key: string
  value: JsonValue
}

export type CatalogBase = {
  id: string
  sort_order: number
  active: boolean
}

export type NamedCatalog = CatalogBase & {
  name: string
}

export type ServiceCategory = NamedCatalog

export type Service = NamedCatalog & {
  category_id: string
  type: string
  price: number
}

export type DueTerm = NamedCatalog & {
  value: number
  unit: string
}

export type InventoryItem = NamedCatalog & {
  module: string
  unit: string
  category?: string | null
  price?: number | null
  has_price: boolean
}

export type HotelRoom = CatalogBase & {
  label: string
}

export type EmailRecipient = NamedCatalog & {
  email: string
}

export type CatalogBootstrap = {
  service_categories: ServiceCategory[]
  services: Service[]
  due_terms: DueTerm[]
  inventory_items: InventoryItem[]
  hotel_rooms: HotelRoom[]
  housekeeping_minibar_items: NamedCatalog[]
  photo_task_types: NamedCatalog[]
  email_recipients: EmailRecipient[]
}

export type CatalogKind =
  | 'service-categories'
  | 'services'
  | 'due-terms'
  | 'inventory-items'
  | 'hotel-rooms'
  | 'housekeeping-minibar-items'
  | 'photo-task-types'
  | 'email-recipients'

export type CatalogRecord = ServiceCategory | Service | DueTerm | InventoryItem | HotelRoom | NamedCatalog | EmailRecipient

export type BackupRecord = {
  id: string
  backup_type: string
  file_path: string
  note?: string | null
  size_bytes?: number | null
  status: string
  created_by?: string | null
  created_at: string
  retained_until?: string | null
  metadata_json?: Record<string, JsonValue> | null
}

export type RecoveryPoint = {
  id: string
  description?: string | null
  data_snapshot_path: string
  created_by?: string | null
  created_at: string
  restored_at?: string | null
  restore_metadata_json?: Record<string, JsonValue> | null
}

export type RestoreResult = {
  restored: boolean
  recovery_point_id: string
  restored_at: string
  metadata: Record<string, JsonValue>
}
