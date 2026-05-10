import { describe, expect, it } from 'vitest'

import { modules } from '@/features/modules'
import { canAccessModule, canAccessPermission, getPermissionsForRole } from '@/shared/auth/permissions'
import type { CurrentUser } from '@/shared/api'

const role = (name: string, permissions: string[]): CurrentUser['role'] => ({ id: `role-${name}`, name, permissions })

const moduleAccessFor = (permissions: string[]) => {
  return modules.filter((module) => canAccessModule(permissions, module.permission)).map((module) => module.code)
}

describe('role permissions and module gating', () => {
  it('grants admins wildcard access to every registered module', () => {
    expect(moduleAccessFor(getPermissionsForRole(role('admin', ['*'])))).toEqual(modules.map((module) => module.code))
  })

  it('uses server-issued reception permissions for operational modules without settings access', () => {
    const permissions = getPermissionsForRole(
      role('recepcni', ['messages:*', 'tasks:*', 'cash:*', 'inventory:*', 'invoices:*', 'housekeeping:reception']),
    )

    expect(moduleAccessFor(permissions)).toEqual([
      'dashboard',
      'communication',
      'tasks',
      'cash',
      'invoicing',
      'inventory',
      'housekeeping',
    ])
  })

  it('supports wildcard permission families and empty server permissions', () => {
    const permissions = getPermissionsForRole(role('pokojska', ['housekeeping:work', 'notifications:read']))

    expect(canAccessPermission(permissions, 'housekeeping:work')).toBe(true)
    expect(canAccessPermission(permissions, 'housekeeping:reception')).toBe(false)
    expect(getPermissionsForRole(role('externista', []))).toEqual([])
    expect(moduleAccessFor(getPermissionsForRole(role('externista', [])))).toEqual([])
  })
})
