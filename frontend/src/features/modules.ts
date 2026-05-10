import { Banknote, BedDouble, Boxes, ClipboardList, LayoutDashboard, MessageSquareText, ReceiptText, Settings, ShieldCheck } from 'lucide-react'

export const modules = [
  { code: 'dashboard', name: 'Dashboard', metric: 'Provozní přehled', icon: LayoutDashboard },
  { code: 'communication', name: 'Vzkazy', metric: 'Recepční komunikace', icon: MessageSquareText },
  { code: 'tasks', name: 'Úkoly', metric: 'Kalendář a opakování', icon: ClipboardList },
  { code: 'cash', name: 'Peněžní deník', metric: 'Směny a hotovost', icon: Banknote },
  { code: 'invoicing', name: 'Fakturace', metric: 'Zálohy a platby', icon: ReceiptText },
  { code: 'inventory', name: 'Inventory', metric: 'Wellness, minibar, lobby', icon: Boxes },
  { code: 'housekeeping', name: 'Housekeeping', metric: 'Úklidy, fotky, prádelna', icon: BedDouble },
  { code: 'reporting', name: 'Reporty', metric: 'Exporty a daně', icon: ShieldCheck },
  { code: 'settings', name: 'Nastavení', metric: 'Firma, role, zálohy', icon: Settings },
]

