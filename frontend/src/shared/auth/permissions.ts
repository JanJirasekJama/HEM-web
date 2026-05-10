import type { ComponentType } from 'react'

export const DEFAULT_ROLE_PERMISSIONS = {
  admin: ['*'],
  recepcni: ['messages:*', 'tasks:*', 'cash:*', 'inventory:*', 'invoices:*', 'housekeeping:reception'],
  ucetni: ['invoices:*', 'reports:*', 'exports:*'],
  pokojska: ['housekeeping:work', 'notifications:read'],
} as const

export type RoleName = keyof typeof DEFAULT_ROLE_PERMISSIONS
export type PermissionCode = (typeof DEFAULT_ROLE_PERMISSIONS)[RoleName][number] | string

export type ModuleCode =
  | 'dashboard'
  | 'communication'
  | 'tasks'
  | 'cash'
  | 'invoicing'
  | 'inventory'
  | 'housekeeping'
  | 'reporting'
  | 'settings'

export type ModuleDefinition = {
  code: ModuleCode
  name: string
  metric: string
  permission: PermissionCode
  icon: ComponentType<{ className?: string }>
  component?: ComponentType
}

export type PermissionState = {
  roleName: string
  permissions: string[]
  can: (permission: string) => boolean
}

const DEFAULT_ROLE_NAMES = Object.keys(DEFAULT_ROLE_PERMISSIONS)

export function getRoleName(roleName?: string | null) {
  return roleName || 'unknown'
}

export function getPermissionsForRole(roleName?: string | null) {
  if (roleName && DEFAULT_ROLE_NAMES.includes(roleName)) {
    return [...DEFAULT_ROLE_PERMISSIONS[roleName as RoleName]]
  }

  return []
}

export function canAccessPermission(permissions: string[], permission: string) {
  if (permission === 'app:authenticated') return permissions.length > 0 || permissions.includes('*')
  if (permissions.includes('*')) return true

  return permissions.some((granted) => permissionMatches(granted, permission))
}

export function permissionMatches(granted: string, requested: string) {
  if (granted === requested || granted === '*') return true
  if (!granted.endsWith(':*')) return false

  return requested.startsWith(`${granted.slice(0, -2)}:`)
}
