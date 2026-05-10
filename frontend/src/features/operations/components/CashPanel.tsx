import { useMemo, useState } from 'react'
import { Download, History, Plus, RefreshCw, Save, Trash2 } from 'lucide-react'

import { exportUrl, queryString } from '@/features/operations/api'
import { useAbortableQuery, useApiMutation } from '@/features/operations/hooks/useOperationsApi'
import type { CashDiaryEntry, CashDiaryHistory, CashShiftLog, CashStatus } from '@/features/operations/types'
import { EmptyState, Field, FilterBar, InlineStatus, NativeSelect, NumberInput, OperationPanel, ToolbarButton } from '@/features/operations/components/primitives'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

const today = () => new Date().toISOString().slice(0, 10)

export function CashPanel(props: { userId?: string }) {
  const [userId, setUserId] = useState(props.userId ?? '')
  const [entryDate, setEntryDate] = useState(today())
  const [dateFrom, setDateFrom] = useState(today().slice(0, 8) + '01')
  const [dateTo, setDateTo] = useState(today())
  const [shiftType, setShiftType] = useState('')
  const [cashStart, setCashStart] = useState<number | null>(null)
  const [cashEnd, setCashEnd] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [historyEntry, setHistoryEntry] = useState<CashDiaryEntry | null>(null)
  const diaryPath = useMemo(() => `/api/cash/diary${queryString({ date_from: dateFrom, date_to: dateTo, user_id: userId })}`, [dateFrom, dateTo, userId])
  const shiftsPath = useMemo(() => `/api/cash/shift-log${queryString({ date_from: dateFrom, date_to: dateTo, user_id: userId })}`, [dateFrom, dateTo, userId])
  const statusPath = useMemo(() => userId ? `/api/cash/status${queryString({ date: entryDate, user_id: userId })}` : null, [entryDate, userId])
  const diary = useAbortableQuery<CashDiaryEntry[]>(diaryPath)
  const shifts = useAbortableQuery<CashShiftLog[]>(shiftsPath)
  const status = useAbortableQuery<CashStatus>(statusPath)
  const mutation = useApiMutation()

  const submitDiary = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await mutation.mutate<CashDiaryEntry>('/api/cash/diary', {
      method: 'POST',
      body: { entry_date: entryDate, user_id: userId, shift_type: shiftType || null, cash_start: cashStart, cash_end: cashEnd, notes: notes || null },
    })
    diary.reload()
    status.reload()
  }

  const createShift = async () => {
    await mutation.mutate<CashShiftLog>('/api/cash/shift-log', {
      method: 'POST',
      body: { user_id: userId, shift_type: shiftType || 'Ranní', start_time: new Date().toISOString(), cash_start: cashStart },
    })
    shifts.reload()
  }

  const deleteEntry = async (entry: CashDiaryEntry) => {
    await mutation.mutate<{ ok: boolean }>(`/api/cash/diary/${entry.id}`, { method: 'DELETE' })
    diary.reload()
    status.reload()
  }

  return (
    <OperationPanel
      title="Peněžní deník"
      description="Zápis hotovosti po směnách, kontrola ranní/večerní uzávěrky a CSV export."
      actions={
        <>
          <ToolbarButton variant="outline" onClick={() => { diary.reload(); shifts.reload(); status.reload() }} aria-label="Obnovit deník"><RefreshCw /></ToolbarButton>
          <ToolbarButton variant="outline" onClick={() => window.open(exportUrl('/api/cash/diary/export.csv', { date_from: dateFrom, date_to: dateTo, user_id: userId }), '_blank', 'noreferrer')}><Download /> CSV</ToolbarButton>
        </>
      }
    >
      <FilterBar>
        <Field label="Uživatel ID"><Input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="user_xxx" required /></Field>
        <Field label="Od"><Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></Field>
        <Field label="Do"><Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></Field>
        <div className="flex items-end gap-2">
          {status.data?.missing_morning_cash && <Badge variant="destructive">Chybí ranní</Badge>}
          {status.data?.missing_evening_cash && <Badge variant="destructive">Chybí večerní</Badge>}
        </div>
      </FilterBar>

      <form className="grid gap-3 rounded-md border p-3 md:grid-cols-6" onSubmit={submitDiary}>
        <Field label="Datum"><Input type="date" value={entryDate} onChange={(event) => setEntryDate(event.target.value)} required /></Field>
        <Field label="Směna"><NativeSelect value={shiftType} onChange={(event) => setShiftType(event.target.value)}><option value="">Auto</option><option>Ranní</option><option>Večerní</option></NativeSelect></Field>
        <Field label="Začátek"><NumberInput value={cashStart ?? ''} onValue={setCashStart} /></Field>
        <Field label="Konec"><NumberInput value={cashEnd ?? ''} onValue={setCashEnd} /></Field>
        <Field label="Poznámka" className="md:col-span-2"><Textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></Field>
        <div className="flex flex-wrap gap-2 md:col-span-6">
          <Button type="submit" disabled={!userId || mutation.loading}><Save /> Uložit deník</Button>
          <Button type="button" variant="outline" onClick={createShift} disabled={!userId || mutation.loading}><Plus /> Start směny</Button>
        </div>
      </form>
      <InlineStatus loading={mutation.loading || diary.loading || shifts.loading || status.loading} error={mutation.error || diary.error || shifts.error || status.error} />

      <Table>
        <TableHeader><TableRow><TableHead>Datum</TableHead><TableHead>Směna</TableHead><TableHead>Start</TableHead><TableHead>Konec</TableHead><TableHead>Rozdíl</TableHead><TableHead>Poznámka</TableHead><TableHead /></TableRow></TableHeader>
        <TableBody>
          {diary.data?.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell>{entry.entry_date}</TableCell>
              <TableCell>{entry.shift_type}</TableCell>
              <TableCell>{formatMoney(entry.cash_start)}</TableCell>
              <TableCell>{formatMoney(entry.cash_end)}</TableCell>
              <TableCell>{formatMoney(entry.difference)}</TableCell>
              <TableCell className="max-w-48 whitespace-normal">{entry.notes}</TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <ToolbarButton variant="outline" onClick={() => setHistoryEntry(entry)} aria-label="Historie"><History /></ToolbarButton>
                  <ToolbarButton variant="destructive" onClick={() => deleteEntry(entry)} aria-label="Smazat"><Trash2 /></ToolbarButton>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!diary.loading && !diary.data?.length && <EmptyState>Deník je pro filtr prázdný.</EmptyState>}

      <div className="rounded-md border p-3">
        <h3 className="mb-2 font-medium">Směny</h3>
        <div className="grid gap-2">
          {shifts.data?.map((shift) => <div key={shift.id} className="text-sm text-muted-foreground">{shift.shift_type} · {new Date(shift.start_time).toLocaleString()} · {formatMoney(shift.cash_start)}</div>)}
          {!shifts.data?.length && <p className="text-sm text-muted-foreground">Žádné záznamy směn.</p>}
        </div>
      </div>

      <CashHistoryDialog entry={historyEntry} open={Boolean(historyEntry)} onOpenChange={(open) => { if (!open) setHistoryEntry(null) }} />
    </OperationPanel>
  )
}

function CashHistoryDialog(props: { entry: CashDiaryEntry | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  const history = useAbortableQuery<CashDiaryHistory[]>(props.entry ? `/api/cash/diary/${props.entry.id}/history` : null)
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader><DialogTitle>Historie deníku</DialogTitle></DialogHeader>
        <div className="grid gap-2">
          {history.data?.map((item) => <div key={item.id} className="rounded-md border p-2 text-sm">{item.action} · {new Date(item.created_at).toLocaleString()}</div>)}
          {!history.loading && !history.data?.length && <EmptyState>Historie není dostupná.</EmptyState>}
          <InlineStatus loading={history.loading} error={history.error} />
        </div>
      </DialogContent>
    </Dialog>
  )
}

function formatMoney(value?: number | null) {
  if (value === undefined || value === null) return '-'
  return new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', maximumFractionDigits: 2 }).format(value)
}
