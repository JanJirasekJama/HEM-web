import { Banknote, BedDouble, Boxes, ClipboardList, LayoutDashboard, MessageSquareText, ReceiptText, Settings, ShieldCheck } from 'lucide-react'

import type { ModuleDefinition } from '@/shared/auth/permissions'

export const modules = [
  { code: 'dashboard', name: 'Dashboard', metric: 'Provozní přehled', permission: 'app:authenticated', icon: LayoutDashboard },
  { code: 'communication', name: 'Vzkazy', metric: 'Recepční komunikace', permission: 'messages:read', icon: MessageSquareText },
  { code: 'tasks', name: 'Úkoly', metric: 'Kalendář a opakování', permission: 'tasks:read', icon: ClipboardList },
  { code: 'cash', name: 'Peněžní deník', metric: 'Směny a hotovost', permission: 'cash:read', icon: Banknote },
  { code: 'invoicing', name: 'Fakturace', metric: 'Zálohy a platby', permission: 'invoices:read', icon: ReceiptText },
  { code: 'inventory', name: 'Inventory', metric: 'Wellness, minibar, lobby', permission: 'inventory:read', icon: Boxes },
  { code: 'housekeeping', name: 'Housekeeping', metric: 'Úklidy, fotky, prádelna', permission: 'housekeeping:work', icon: BedDouble },
  { code: 'reporting', name: 'Reporty', metric: 'Exporty a daně', permission: 'reports:read', icon: ShieldCheck },
  { code: 'settings', name: 'Nastavení', metric: 'Firma, role, zálohy', permission: '*', icon: Settings },
] satisfies ModuleDefinition[]
