import type { ApiStatus } from '@/shared/api'
import { Badge } from '@/components/ui/badge'

export function StatusBadge({ status }: { status: ApiStatus }) {
  const label = status === 'ok' ? 'Backend online' : status === 'offline' ? 'Offline' : 'Kontrola'

  return <Badge variant={status === 'ok' ? 'default' : 'secondary'}>{label}</Badge>
}
