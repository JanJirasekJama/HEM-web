import { Bell } from 'lucide-react'

import type { NotificationItem } from '@/shared/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function NotificationsPanel({ notifications }: { notifications: NotificationItem[] }) {
  return (
    <Card className="rounded-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Oznámení</CardTitle>
        <Bell className="size-4 text-muted-foreground" aria-hidden="true" />
      </CardHeader>
      <CardContent className="space-y-3">
        {notifications.slice(0, 5).map((item) => (
          <div key={item.id} className="rounded-md border p-3">
            <div className="text-sm font-medium">{item.title}</div>
            {item.body && <div className="mt-1 text-sm text-muted-foreground">{item.body}</div>}
          </div>
        ))}
        {!notifications.length && <p className="text-sm text-muted-foreground">Žádná nová oznámení</p>}
      </CardContent>
    </Card>
  )
}
