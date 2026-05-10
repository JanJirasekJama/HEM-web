import { useEffect, useState } from 'react'

import { apiGet, type NotificationItem } from '@/shared/api'

export function useNotifications(enabled: boolean) {
  const [items, setItems] = useState<NotificationItem[]>([])

  useEffect(() => {
    if (!enabled) return
    let cancelled = false

    const refresh = () => {
      apiGet<NotificationItem[]>('/api/notifications')
        .then((notifications) => {
          if (!cancelled) setItems(notifications)
        })
        .catch(() => undefined)
    }

    refresh()
    const interval = window.setInterval(refresh, 30000)
    const events = new EventSource('/api/events', { withCredentials: true })
    events.addEventListener('ready', refresh)
    events.addEventListener('ping', refresh)
    events.onerror = () => undefined

    return () => {
      cancelled = true
      window.clearInterval(interval)
      events.close()
    }
  }, [enabled])

  return items
}

