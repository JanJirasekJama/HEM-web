import type { ComponentType } from 'react'
import type { CurrentUser } from '@/shared/api'

export type PermissionCode = string

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
  permission: PermissionCode | PermissionCode[]
  icon: ComponentType<{ className?: string }>
  component?: ComponentType<ModuleComponentProps>
}

export type ModuleComponentProps = {
  currentUser: CurrentUser | null
  permissions: PermissionState
}

export type PermissionState = {
  roleName: string
  permissions: string[]
  can: (permission: string) => boolean
}

export function getRoleName(roleName?: string | null) {
  return roleName || 'unknown'
}

export function getPermissionsForRole(role?: CurrentUser['role']) {
  return role?.permissions ? [...role.permissions] : []
}

export function canAccessPermission(permissions: string[], permission: string) {
  if (permission === 'app:authenticated') return permissions.length > 0 || permissions.includes('*')
  if (permissions.includes('*')) return true

  return permissions.some((granted) => permissionMatches(granted, permission))
}

export function canAccessModule(permissions: string[], permission: ModuleDefinition['permission']) {
  const requiredPermissions = Array.isArray(permission) ? permission : [permission]
  return requiredPermissions.some((item) => canAccessPermission(permissions, item))
}

export function permissionMatches(granted: string, requested: string) {
  if (granted === requested || granted === '*') return true
  if (!granted.endsWith(':*')) return false

  return requested.startsWith(`${granted.slice(0, -2)}:`)
}
