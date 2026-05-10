import { useMemo, useState } from 'react'
import { Check, Plus, RefreshCw, Trash2 } from 'lucide-react'

import { queryString } from '@/features/operations/api'
import { useAbortableQuery, useApiMutation } from '@/features/operations/hooks/useOperationsApi'
import type { TaskCalendar, TaskItem } from '@/features/operations/types'
import { EmptyState, Field, FilterBar, InlineStatus, NativeSelect, OperationPanel, ToolbarButton } from '@/features/operations/components/primitives'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const today = () => new Date().toISOString().slice(0, 10)
const weekdays = [
  ['monday', 'Po'],
  ['tuesday', 'Út'],
  ['wednesday', 'St'],
  ['thursday', 'Čt'],
  ['friday', 'Pá'],
  ['saturday', 'So'],
  ['sunday', 'Ne'],
] as const

export function TasksPanel() {
  const [date, setDate] = useState(today())
  const [dialogOpen, setDialogOpen] = useState(false)
  const calendarPath = useMemo(() => `/api/tasks/calendar${queryString({ date })}`, [date])
  const calendar = useAbortableQuery<TaskCalendar>(calendarPath)
  const mutation = useApiMutation()

  const toggleTask = async (task: TaskItem) => {
    await mutation.mutate<TaskItem>(`/api/tasks/${task.id}/completion`, { method: 'PATCH', body: { completed: !task.completed, occurrence_date: task.occurrence_date } })
    calendar.reload()
  }

  const deleteTask = async (task: TaskItem) => {
    await mutation.mutate<{ ok: boolean }>(`/api/tasks/${task.id}`, { method: 'DELETE' })
    calendar.reload()
  }

  return (
    <OperationPanel
      title="Úkoly"
      description="Denní kalendář úkolů s jednorázovým i opakovaným zadáním."
      actions={
        <>
          <ToolbarButton variant="outline" onClick={calendar.reload} aria-label="Obnovit úkoly"><RefreshCw /></ToolbarButton>
          <ToolbarButton onClick={() => setDialogOpen(true)}><Plus /> Nový úkol</ToolbarButton>
        </>
      }
    >
      <FilterBar>
        <Field label="Datum"><Input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></Field>
        <div className="flex items-end gap-2 md:col-span-3">
          <Badge variant="secondary">Celkem {calendar.data?.stats.total ?? 0}</Badge>
          <Badge variant="secondary">Otevřené {calendar.data?.stats.open ?? 0}</Badge>
          <Badge variant="secondary">Hotové {calendar.data?.stats.completed ?? 0}</Badge>
        </div>
      </FilterBar>

      <div className="grid gap-2">
        {calendar.data?.tasks.map((task) => (
          <div key={`${task.id}:${task.occurrence_date}`} className="grid gap-3 rounded-md border p-3 md:grid-cols-[auto_1fr_auto] md:items-start">
            <Checkbox checked={task.completed} onCheckedChange={() => toggleTask(task)} aria-label="Splnit úkol" />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-medium">{task.title}</h3>
                <Badge variant={task.completed ? 'default' : 'secondary'}>{task.completed ? 'Hotovo' : task.priority}</Badge>
              </div>
              {task.description && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{task.description}</p>}
              <p className="mt-1 text-xs text-muted-foreground">{task.recurrence_type ? `Opakování: ${task.recurrence_type}` : `Termín: ${task.due_date}`}</p>
            </div>
            <div className="flex gap-2">
              <ToolbarButton variant="outline" onClick={() => toggleTask(task)}><Check /> {task.completed ? 'Otevřít' : 'Splnit'}</ToolbarButton>
              <ToolbarButton variant="destructive" onClick={() => deleteTask(task)} aria-label="Smazat úkol"><Trash2 /></ToolbarButton>
            </div>
          </div>
        ))}
        {!calendar.loading && !calendar.data?.tasks.length && <EmptyState>Na vybrané datum nejsou žádné úkoly.</EmptyState>}
        <InlineStatus loading={calendar.loading || mutation.loading} error={calendar.error || mutation.error} />
      </div>

      <TaskFormDialog open={dialogOpen} defaultDate={date} onOpenChange={setDialogOpen} onSaved={calendar.reload} />
    </OperationPanel>
  )
}

function TaskFormDialog(props: { open: boolean; defaultDate: string; onOpenChange: (open: boolean) => void; onSaved: () => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dueDate, setDueDate] = useState(props.defaultDate)
  const [priority, setPriority] = useState('Normalni')
  const [recurrenceType, setRecurrenceType] = useState('')
  const [recurrenceDays, setRecurrenceDays] = useState<string[]>([])
  const [intervalDays, setIntervalDays] = useState('7')
  const [endDate, setEndDate] = useState('')
  const mutation = useApiMutation()

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await mutation.mutate<TaskItem>('/api/tasks', {
      method: 'POST',
      body: {
        title,
        description: description || null,
        due_date: dueDate,
        priority,
        assigned_to_all: true,
        recurrence_type: recurrenceType || null,
        recurrence_days: recurrenceType === 'weekly' ? recurrenceDays : [],
        recurrence_interval_days: recurrenceType === 'interval' ? Number(intervalDays) : null,
        recurrence_end_date: endDate || null,
      },
    })
    setTitle('')
    setDescription('')
    props.onSaved()
    props.onOpenChange(false)
  }

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader><DialogTitle>Nový úkol</DialogTitle></DialogHeader>
        <form className="space-y-3" onSubmit={submit}>
          <Field label="Název"><Input value={title} onChange={(event) => setTitle(event.target.value)} required /></Field>
          <Field label="Popis"><Textarea value={description} onChange={(event) => setDescription(event.target.value)} /></Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Termín"><Input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} required /></Field>
            <Field label="Priorita"><NativeSelect value={priority} onChange={(event) => setPriority(event.target.value)}><option>Normalni</option><option>Vysoka</option><option>Nizka</option></NativeSelect></Field>
            <Field label="Opakování"><NativeSelect value={recurrenceType} onChange={(event) => setRecurrenceType(event.target.value)}><option value="">Bez opakování</option><option value="weekly">Týdně</option><option value="interval">Interval</option></NativeSelect></Field>
          </div>
          {recurrenceType === 'weekly' && (
            <div className="flex flex-wrap gap-3">
              {weekdays.map(([value, label]) => (
                <label key={value} className="flex items-center gap-2 text-sm">
                  <Checkbox checked={recurrenceDays.includes(value)} onCheckedChange={() => setRecurrenceDays((days) => days.includes(value) ? days.filter((day) => day !== value) : [...days, value])} />
                  {label}
                </label>
              ))}
            </div>
          )}
          {recurrenceType === 'interval' && <Field label="Každých dnů"><Input type="number" min={1} value={intervalDays} onChange={(event) => setIntervalDays(event.target.value)} /></Field>}
          {recurrenceType && <Field label="Konec opakování"><Input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></Field>}
          <InlineStatus loading={mutation.loading} error={mutation.error} />
          <DialogFooter><Button type="submit" disabled={mutation.loading || !title.trim()}><Plus /> Vytvořit</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
