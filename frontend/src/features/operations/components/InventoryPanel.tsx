import { useMemo, useState } from 'react'
import { FileBarChart, Plus, RefreshCw, Save, Trash2 } from 'lucide-react'

import { queryString } from '@/features/operations/api'
import { useAbortableQuery, useApiMutation, useDebouncedValue } from '@/features/operations/hooks/useOperationsApi'
import type { CatalogBootstrap, InventoryCatalogItem, InventoryEntry, InventoryEntryItem, InventoryModule, InventoryMonthlyReport } from '@/features/operations/types'
import { EmptyState, Field, FilterBar, InlineStatus, NativeSelect, NumberInput, OperationPanel, ToolbarButton } from '@/features/operations/components/primitives'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

type DraftLine = {
  key: string
  item_id: string
  custom_description: string
  quantity: number | null
  unit_price: number | null
  is_custom: boolean
}

const today = () => new Date().toISOString().slice(0, 10)
const month = () => today().slice(0, 7)
const modules: Array<{ value: InventoryModule; label: string }> = [
  { value: 'wellness', label: 'Wellness' },
  { value: 'minibar', label: 'Minibar' },
  { value: 'lobby', label: 'Lobby' },
]

export function InventoryPanel() {
  const [module, setModule] = useState<InventoryModule>('wellness')
  const [entryDate, setEntryDate] = useState(today())
  const [note, setNote] = useState('')
  const [text, setText] = useState('')
  const [dateFrom, setDateFrom] = useState(today().slice(0, 8) + '01')
  const [dateTo, setDateTo] = useState(today())
  const [reportMonth, setReportMonth] = useState(month())
  const [lines, setLines] = useState<DraftLine[]>(() => [newLine()])
  const debouncedText = useDebouncedValue(text)
  const catalog = useAbortableQuery<CatalogBootstrap>('/api/catalog/bootstrap')
  const currentEntry = useAbortableQuery<InventoryEntry>(`/api/inventory/entries/by-date${queryString({ entry_date: entryDate, module })}`)
  const archive = useAbortableQuery<InventoryEntry[]>(`/api/inventory/archive${queryString({ module, text: debouncedText, date_from: dateFrom, date_to: dateTo })}`)
  const report = useAbortableQuery<InventoryMonthlyReport>(`/api/inventory/reports/monthly${queryString({ module, month: reportMonth })}`)
  const mutation = useApiMutation()
  const catalogItems = useMemo(() => (catalog.data?.inventory_items ?? []).filter((item) => item.module === module), [catalog.data, module])

  const loadEntry = (entry: InventoryEntry) => {
    setEntryDate(entry.entry_date)
    setModule(entry.module)
    setNote(entry.note ?? '')
    setLines(entry.items.length ? entry.items.map(lineFromEntry) : [newLine()])
  }

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const body = { entry_date: entryDate, module, note: note || null, items: lines.map(lineToPayload).filter(Boolean) }
    if (currentEntry.data?.id) {
      await mutation.mutate<InventoryEntry>(`/api/inventory/entries/${currentEntry.data.id}`, { method: 'PUT', body })
    } else {
      await mutation.mutate<InventoryEntry>('/api/inventory/entries', { method: 'POST', body })
    }
    currentEntry.reload()
    archive.reload()
    report.reload()
  }

  const deleteArchive = async (entry: InventoryEntry) => {
    await mutation.mutate<{ ok: boolean }>(`/api/inventory/archive/${entry.id}`, { method: 'DELETE' })
    archive.reload()
    report.reload()
  }

  return (
    <OperationPanel
      title="Inventory"
      description="Denní spotřeby wellness, minibaru a lobby s měsíčním součtem."
      actions={
        <>
          <ToolbarButton variant="outline" onClick={() => { currentEntry.reload(); archive.reload(); report.reload() }} aria-label="Obnovit inventory"><RefreshCw /></ToolbarButton>
          <Badge variant="secondary">{report.data ? `${Object.keys(report.data.totals).length} položek v reportu` : 'Report'}</Badge>
        </>
      }
    >
      <FilterBar>
        <Field label="Modul"><NativeSelect value={module} onChange={(event) => setModule(event.target.value as InventoryModule)}>{modules.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</NativeSelect></Field>
        <Field label="Datum"><Input type="date" value={entryDate} onChange={(event) => setEntryDate(event.target.value)} /></Field>
        <Field label="Měsíc reportu"><Input type="month" value={reportMonth} onChange={(event) => setReportMonth(event.target.value)} /></Field>
        <div className="flex items-end"><ToolbarButton variant="outline" onClick={() => currentEntry.data && loadEntry(currentEntry.data)}>Načíst den</ToolbarButton></div>
      </FilterBar>

      <form className="space-y-3 rounded-md border p-3" onSubmit={submit}>
        <Field label="Poznámka"><Textarea value={note} onChange={(event) => setNote(event.target.value)} /></Field>
        <div className="grid gap-2">
          {lines.map((line) => (
            <InventoryLineEditor key={line.key} module={module} line={line} catalogItems={catalogItems} onChange={(next) => setLines((items) => items.map((item) => item.key === line.key ? next : item))} onRemove={() => setLines((items) => items.filter((item) => item.key !== line.key))} />
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => setLines((items) => [...items, newLine()])}><Plus /> Položka</Button>
          <Button type="submit" disabled={mutation.loading}><Save /> {currentEntry.data ? 'Aktualizovat den' : 'Uložit den'}</Button>
        </div>
      </form>
      <InlineStatus loading={catalog.loading || currentEntry.loading || mutation.loading} error={catalog.error || mutation.error} />

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-3">
          <FilterBar>
            <Field label="Archiv od"><Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></Field>
            <Field label="Archiv do"><Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></Field>
            <Field label="Hledat"><Input value={text} onChange={(event) => setText(event.target.value)} placeholder="Položka nebo poznámka" /></Field>
          </FilterBar>
          <Table>
            <TableHeader><TableRow><TableHead>Datum</TableHead><TableHead>Položky</TableHead><TableHead>Celkem</TableHead><TableHead /></TableRow></TableHeader>
            <TableBody>
              {archive.data?.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>{entry.entry_date}</TableCell>
                  <TableCell>{entry.items.length}</TableCell>
                  <TableCell>{formatMoney(entry.items.reduce((sum, item) => sum + item.total_price, 0))}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <ToolbarButton variant="outline" onClick={() => loadEntry(entry)}>Upravit</ToolbarButton>
                      <ToolbarButton variant="destructive" onClick={() => deleteArchive(entry)} aria-label="Smazat"><Trash2 /></ToolbarButton>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {!archive.loading && !archive.data?.length && <EmptyState>Archiv je prázdný.</EmptyState>}
          <InlineStatus loading={archive.loading} error={archive.error} />
        </div>

        <div className="rounded-md border p-3">
          <div className="mb-3 flex items-center gap-2 font-medium"><FileBarChart className="size-4" /> Měsíční report</div>
          <Table>
            <TableHeader><TableRow><TableHead>Položka</TableHead><TableHead>Množství</TableHead><TableHead>Hodnota</TableHead></TableRow></TableHeader>
            <TableBody>
              {Object.entries(report.data?.totals ?? {}).map(([name, total]) => (
                <TableRow key={name}><TableCell>{name}</TableCell><TableCell>{total.quantity}</TableCell><TableCell>{formatMoney(total.total_price)}</TableCell></TableRow>
              ))}
              {report.data?.custom_total_price ? <TableRow><TableCell>Vlastní lobby položky</TableCell><TableCell>-</TableCell><TableCell>{formatMoney(report.data.custom_total_price)}</TableCell></TableRow> : null}
            </TableBody>
          </Table>
          {!report.loading && !Object.keys(report.data?.totals ?? {}).length && !report.data?.custom_total_price && <EmptyState>Report zatím nemá data.</EmptyState>}
          <InlineStatus loading={report.loading} error={report.error} />
        </div>
      </div>
    </OperationPanel>
  )
}

function InventoryLineEditor(props: { module: InventoryModule; line: DraftLine; catalogItems: InventoryCatalogItem[]; onChange: (line: DraftLine) => void; onRemove: () => void }) {
  const selected = props.catalogItems.find((item) => item.id === props.line.item_id)
  const canCustom = props.module === 'lobby'
  const update = (patch: Partial<DraftLine>) => props.onChange({ ...props.line, ...patch })

  return (
    <div className="grid gap-2 rounded-md border p-2 md:grid-cols-[1fr_120px_120px_auto_auto] md:items-end">
      <Field label={props.line.is_custom ? 'Popis' : 'Položka'}>
        {props.line.is_custom ? (
          <Input value={props.line.custom_description} onChange={(event) => update({ custom_description: event.target.value })} />
        ) : (
          <NativeSelect value={props.line.item_id} onChange={(event) => {
            const item = props.catalogItems.find((candidate) => candidate.id === event.target.value)
            update({ item_id: event.target.value, unit_price: item?.price ?? 0 })
          }}>
            <option value="">Vyberte položku</option>
            {props.catalogItems.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.unit}</option>)}
          </NativeSelect>
        )}
      </Field>
      <Field label="Množství"><NumberInput min={0} value={props.line.quantity ?? ''} onValue={(value) => update({ quantity: value })} /></Field>
      <Field label="Cena"><NumberInput min={0} value={props.line.unit_price ?? selected?.price ?? ''} onValue={(value) => update({ unit_price: value })} /></Field>
      <label className="flex h-8 items-center gap-2 text-sm">
        <input type="checkbox" checked={props.line.is_custom} disabled={!canCustom} onChange={(event) => update({ is_custom: event.target.checked, item_id: '', custom_description: '' })} />
        Vlastní
      </label>
      <ToolbarButton type="button" variant="destructive" onClick={props.onRemove} aria-label="Odebrat položku"><Trash2 /></ToolbarButton>
    </div>
  )
}

function newLine(): DraftLine {
  return { key: crypto.randomUUID(), item_id: '', custom_description: '', quantity: 1, unit_price: null, is_custom: false }
}

function lineFromEntry(item: InventoryEntryItem): DraftLine {
  return { key: item.id, item_id: item.item_id ?? '', custom_description: item.custom_description ?? '', quantity: item.quantity, unit_price: item.unit_price, is_custom: item.is_custom }
}

function lineToPayload(line: DraftLine) {
  if (line.is_custom) {
    if (!line.custom_description.trim()) return null
    return { custom_description: line.custom_description, quantity: line.quantity ?? 0, unit_price: line.unit_price ?? 0, is_custom: true }
  }
  if (!line.item_id) return null
  return { item_id: line.item_id, quantity: line.quantity ?? 0, unit_price: line.unit_price, is_custom: false }
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', maximumFractionDigits: 2 }).format(value)
}
