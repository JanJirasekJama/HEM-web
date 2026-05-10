import { Banknote, BedDouble, Boxes, ClipboardList, LayoutDashboard, MessageSquareText, ReceiptText, Settings, ShieldCheck } from 'lucide-react'
import { createElement } from 'react'

import { AdminWorkspace } from '@/features/admin/AdminWorkspace'
import { FinanceWorkspace } from '@/features/finance/FinanceWorkspace'
import { HousekeepingWorkspace } from '@/features/housekeeping/HousekeepingWorkspace'
import type { HousekeepingCapabilities, HousekeepingRole } from '@/features/housekeeping/types'
import { CashPanel } from '@/features/operations/components/CashPanel'
import { InventoryPanel } from '@/features/operations/components/InventoryPanel'
import { MessagesPanel } from '@/features/operations/components/MessagesPanel'
import { TasksPanel } from '@/features/operations/components/TasksPanel'
import type { ModuleComponentProps, ModuleDefinition } from '@/shared/auth/permissions'

export const modules = [
  { code: 'dashboard', name: 'Dashboard', metric: 'Provozní přehled', permission: 'app:authenticated', icon: LayoutDashboard },
  { code: 'communication', name: 'Vzkazy', metric: 'Recepční komunikace', permission: 'messages:read', icon: MessageSquareText, component: MessagesPanel },
  { code: 'tasks', name: 'Úkoly', metric: 'Kalendář a opakování', permission: 'tasks:read', icon: ClipboardList, component: TasksPanel },
  { code: 'cash', name: 'Peněžní deník', metric: 'Směny a hotovost', permission: 'cash:read', icon: Banknote, component: CashWorkspace },
  { code: 'invoicing', name: 'Fakturace', metric: 'Zálohy a platby', permission: 'invoices:read', icon: ReceiptText, component: InvoicingWorkspace },
  { code: 'inventory', name: 'Inventory', metric: 'Wellness, minibar, lobby', permission: 'inventory:read', icon: Boxes, component: InventoryPanel },
  { code: 'housekeeping', name: 'Housekeeping', metric: 'Úklidy, fotky, prádelna', permission: ['housekeeping:work', 'housekeeping:reception'], icon: BedDouble, component: HousekeepingModuleWorkspace },
  { code: 'reporting', name: 'Reporty', metric: 'Exporty a daně', permission: 'reports:read', icon: ShieldCheck, component: ReportingWorkspace },
  { code: 'settings', name: 'Nastavení', metric: 'Firma, role, zálohy', permission: '*', icon: Settings, component: AdminWorkspace },
] satisfies ModuleDefinition[]

function CashWorkspace({ currentUser }: ModuleComponentProps) {
  return createElement(CashPanel, { userId: currentUser?.id })
}

function InvoicingWorkspace() {
  return createElement(FinanceWorkspace, { defaultTab: 'invoices' })
}

function HousekeepingModuleWorkspace({ permissions }: ModuleComponentProps) {
  const canReception = permissions.can('housekeeping:reception')
  const canWork = permissions.can('housekeeping:work')
  const allowedRoles = [
    canReception ? 'reception' : null,
    canWork ? 'housekeeper' : null,
  ].filter((role): role is HousekeepingRole => role !== null)
  const capabilities: Partial<HousekeepingCapabilities> = {
    viewHistory: canReception,
    viewReport: permissions.can('reports:read'),
    createAssignments: canReception,
    createRevisions: canReception,
    createLaundry: canReception,
    workAssignments: canWork,
    uploadAssignmentPhotos: canWork,
    addMinibarEntries: canWork,
    completeRevisions: canWork,
    workLaundry: canWork,
  }

  return createElement(HousekeepingWorkspace, {
    allowedRoles,
    defaultRole: canReception ? 'reception' : 'housekeeper',
    capabilities,
  })
}

function ReportingWorkspace() {
  return createElement(FinanceWorkspace, { defaultTab: 'reports' })
}
