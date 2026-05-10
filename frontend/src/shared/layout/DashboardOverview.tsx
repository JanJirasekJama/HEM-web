import { Banknote, BedDouble, ClipboardList, MessageSquareText } from 'lucide-react'

import type { DashboardResponse } from '@/shared/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function DashboardOverview({ dashboard }: { dashboard: DashboardResponse | null }) {
  const metrics = [
    { label: 'Vzkazy', value: dashboard?.messages_today ?? 0, icon: MessageSquareText },
    { label: 'Nesplněné úkoly', value: dashboard?.open_tasks_today ?? 0, icon: ClipboardList },
    { label: 'Pokoje čekají', value: dashboard?.housekeeping.waiting ?? 0, icon: BedDouble },
    { label: 'Splatnosti', value: dashboard?.invoices.due_or_overdue ?? 0, icon: Banknote },
  ]

  return (
    <section className="grid gap-4 xl:grid-cols-[1fr_340px]">
      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>Dnes</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => {
            const Icon = metric.icon

            return (
              <div key={metric.label} className="rounded-md border p-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="text-sm text-muted-foreground">{metric.label}</div>
                  <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                </div>
                <div className="text-2xl font-semibold tracking-normal">{metric.value}</div>
              </div>
            )
          })}
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>Prioritní úkoly</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {dashboard?.open_task_list.slice(0, 4).map((task) => (
            <div key={task.id} className="flex items-center justify-between gap-3 rounded-md border px-3 py-2">
              <span className="min-w-0 truncate text-sm">{task.title}</span>
              <span className="shrink-0 text-xs text-muted-foreground">{task.priority}</span>
            </div>
          ))}
          {!dashboard?.open_task_list.length && <p className="text-sm text-muted-foreground">Žádné prioritní úkoly</p>}
        </CardContent>
      </Card>
    </section>
  )
}
