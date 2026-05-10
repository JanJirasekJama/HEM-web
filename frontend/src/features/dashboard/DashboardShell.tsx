import { useAppState } from '@/shared/auth/useAppState'
import { AppLayout } from '@/shared/layout/AppLayout'

export function DashboardShell() {
  return <AppLayout {...useAppState()} />
}
