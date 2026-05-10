import { useMemo, useState } from 'react'
import { DatabaseBackup, Plus, RefreshCw, RotateCcw, Save, Settings, Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

import {
  createCatalogItem,
  createManualBackup,
  createRecoveryPoint,
  deleteBackup,
  deleteCatalogItem,
  loadBackups,
  loadCatalog,
  loadSetting,
  restoreRecoveryPoint,
  saveSetting,
  updateCatalogItem,
  useAdminResource,
} from './api'
import type { BackupRecord, CatalogBootstrap, CatalogKind, CatalogRecord, JsonValue, RecoveryPoint } from './types'

const settingKeys = [
  { key: 'company', label: 'Firma' },
  { key: 'app', label: 'Aplikace' },
  { key: 'email', label: 'E-mail' },
  { key: 'backup', label: 'Zálohy' },
]

const catalogKinds: Array<{ kind: CatalogKind; label: string }> = [
  { kind: 'service-categories', label: 'Kategorie služeb' },
  { kind: 'services', label: 'Služby' },
  { kind: 'due-terms', label: 'Splatnosti' },
  { kind: 'inventory-items', label: 'Inventory položky' },
  { kind: 'hotel-rooms', label: 'Pokoje' },
  { kind: 'photo-task-types', label: 'Foto typy' },
  { kind: 'housekeeping-minibar-items', label: 'Minibar HK' },
  { kind: 'email-recipients', label: 'Adresáti e-mailů' },
]

export function AdminWorkspace() {
  const catalog = useAdminResource(loadCatalog, [])
  const backups = useAdminResource(loadBackups, [])
  const [message, setMessage] = useState('')

  return (
    <section className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-normal">Admin</h1>
        <p className="text-sm text-muted-foreground">Nastavení, katalogy, zálohy a recovery body</p>
      </header>
      {message && <StatusLine text={message} />}
      <Tabs defaultValue="settings" className="gap-4">
        <TabsList className="w-full justify-start overflow-x-auto rounded-md">
          <TabsTrigger value="settings"><Settings className="size-4" /> Nastavení</TabsTrigger>
          <TabsTrigger value="catalog"><Plus className="size-4" /> Katalog</TabsTrigger>
          <TabsTrigger value="backups"><DatabaseBackup className="size-4" /> Zálohy</TabsTrigger>
        </TabsList>
        <TabsContent value="settings"><SettingsPanel onMessage={setMessage} /></TabsContent>
        <TabsContent value="catalog"><CatalogPanel catalog={catalog.data} loading={catalog.loading} error={catalog.error} onReload={catalog.reload} onMessage={setMessage} /></TabsContent>
        <TabsContent value="backups"><BackupPanel backups={backups.data ?? []} loading={backups.loading} error={backups.error} onReload={backups.reload} onMessage={setMessage} /></TabsContent>
      </Tabs>
    </section>
  )
}

function SettingsPanel({ onMessage }: { onMessage: (message: string) => void }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {settingKeys.map((setting) => (
        <JsonSettingsEditor key={setting.key} settingKey={setting.key} label={setting.label} onMessage={onMessage} />
      ))}
    </div>
  )
}

function JsonSettingsEditor({ settingKey, label, onMessage }: { settingKey: string; label: string; onMessage: (message: string) => void }) {
  const resource = useAdminResource((signal) => loadSetting(settingKey, signal), [settingKey])
  const [draft, setDraft] = useState<{ source: JsonValue | null; text: string }>({ source: null, text: '{}' })
  const loadedValue = resource.data?.value ?? null
  const text = draft.source === loadedValue ? draft.text : JSON.stringify(loadedValue, null, 2)

  const submit = async () => {
    try {
      const parsed = JSON.parse(text) as JsonValue
      const saved = await saveSetting(settingKey, parsed)
      setDraft({ source: saved.value, text: JSON.stringify(saved.value, null, 2) })
      onMessage(`${label}: uloženo.`)
      resource.reload()
    } catch (error) {
      onMessage(error instanceof Error ? error.message : `${label}: neplatný JSON.`)
    }
  }

  return (
    <Card className="rounded-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg">{label}</CardTitle>
        <Button size="sm" onClick={submit}><Save className="size-4" /> Uložit</Button>
      </CardHeader>
      <CardContent className="grid gap-3">
        <Textarea className="min-h-64 font-mono text-xs" value={text} onChange={(event) => setDraft({ source: loadedValue, text: event.target.value })} spellCheck={false} />
        {resource.error && <StatusLine text={resource.error} tone="error" />}
      </CardContent>
    </Card>
  )
}

function CatalogPanel(props: {
  catalog: CatalogBootstrap | null
  loading: boolean
  error: string
  onReload: () => void
  onMessage: (message: string) => void
}) {
  const [kind, setKind] = useState<CatalogKind>('services')
  const rows = useMemo(() => catalogRows(props.catalog, kind), [props.catalog, kind])
  const selectedLabel = catalogKinds.find((item) => item.kind === kind)?.label ?? kind

  const save = async (payload: Record<string, unknown>, id?: string) => {
    try {
      if (id) await updateCatalogItem(kind, id, payload)
      else await createCatalogItem(kind, payload)
      props.onMessage(`${selectedLabel}: uloženo.`)
      props.onReload()
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Katalog se nepodařilo uložit')
    }
  }

  const remove = async (id: string) => {
    try {
      await deleteCatalogItem(kind, id)
      props.onMessage(`${selectedLabel}: položka deaktivována.`)
      props.onReload()
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Položku se nepodařilo deaktivovat')
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <Card className="rounded-md">
        <CardHeader><CardTitle className="text-lg">Katalogy</CardTitle></CardHeader>
        <CardContent className="grid gap-2">
          {catalogKinds.map((item) => (
            <Button key={item.kind} variant={kind === item.kind ? 'default' : 'outline'} className="justify-start" onClick={() => setKind(item.kind)}>{item.label}</Button>
          ))}
          <Separator />
          <Button variant="outline" onClick={props.onReload}><RefreshCw className="size-4" /> Obnovit</Button>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-lg">{selectedLabel}</CardTitle>
            <Badge variant="secondary">{props.loading ? 'Načítám' : `${rows.length} položek`}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4">
          {props.error && <StatusLine text={props.error} tone="error" />}
          <CatalogForm kind={kind} catalog={props.catalog} onSave={save} />
          <CatalogTable kind={kind} rows={rows} onSave={save} onDelete={remove} />
        </CardContent>
      </Card>
    </div>
  )
}

function CatalogForm({ kind, catalog, onSave }: { kind: CatalogKind; catalog: CatalogBootstrap | null; onSave: (payload: Record<string, unknown>) => void }) {
  const [form, setForm] = useState<Record<string, string>>({})

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSave(payloadForKind(kind, form, catalog))
    setForm({})
  }

  return (
    <form className="grid gap-3 rounded-md border p-3" onSubmit={submit}>
      <div className="grid gap-3 md:grid-cols-4">
        {fieldsForKind(kind, catalog).map((field) => (
          <Field key={field.name} label={field.label}>
            {field.options ? (
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={form[field.name] ?? ''} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })} required={field.required}>
                <option value="">Vyberte</option>
                {field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            ) : (
              <Input type={field.type ?? 'text'} value={form[field.name] ?? ''} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })} required={field.required} />
            )}
          </Field>
        ))}
      </div>
      <div className="flex justify-end"><Button type="submit"><Plus className="size-4" /> Přidat</Button></div>
    </form>
  )
}

function CatalogTable({ rows, onSave, onDelete }: { kind: CatalogKind; rows: CatalogRecord[]; onSave: (payload: Record<string, unknown>, id?: string) => void; onDelete: (id: string) => void }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Název</TableHead>
          <TableHead>Detail</TableHead>
          <TableHead>Pořadí</TableHead>
          <TableHead>Stav</TableHead>
          <TableHead>Akce</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-medium">{displayName(row)}</TableCell>
            <TableCell>{displayDetail(row)}</TableCell>
            <TableCell>{row.sort_order}</TableCell>
            <TableCell><Badge variant={row.active ? 'default' : 'secondary'}>{row.active ? 'Aktivní' : 'Vypnuto'}</Badge></TableCell>
            <TableCell>
              <div className="flex gap-1">
                <Button variant="outline" size="icon-sm" aria-label="Aktivovat" onClick={() => onSave({ active: !row.active }, row.id)}><RefreshCw className="size-3.5" /></Button>
                <Button variant="destructive" size="icon-sm" aria-label="Soft-delete" onClick={() => onDelete(row.id)}><Trash2 className="size-3.5" /></Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
        {!rows.length && <TableRow><TableCell colSpan={5} className="h-20 text-center text-muted-foreground">Katalog je prázdný</TableCell></TableRow>}
      </TableBody>
    </Table>
  )
}

function BackupPanel(props: { backups: BackupRecord[]; loading: boolean; error: string; onReload: () => void; onMessage: (message: string) => void }) {
  const [note, setNote] = useState('')
  const [description, setDescription] = useState('')
  const [recoveryPoints, setRecoveryPoints] = useState<RecoveryPoint[]>([])

  const manual = async () => {
    try {
      await createManualBackup(note)
      setNote('')
      props.onMessage('Ruční záloha byla vytvořena.')
      props.onReload()
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Zálohu se nepodařilo vytvořit')
    }
  }

  const recovery = async () => {
    try {
      const point = await createRecoveryPoint(description)
      setRecoveryPoints((current) => [point, ...current])
      setDescription('')
      props.onMessage('Recovery bod byl vytvořen.')
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Recovery bod se nepodařilo vytvořit')
    }
  }

  const restore = async (id: string) => {
    try {
      const result = await restoreRecoveryPoint(id)
      props.onMessage(`Obnova dokončena: ${result.restored_at}`)
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Obnova se nepodařila')
    }
  }

  const remove = async (id: string) => {
    try {
      await deleteBackup(id)
      props.onMessage('Záloha byla smazána.')
      props.onReload()
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Zálohu se nepodařilo smazat')
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
      <Card className="rounded-md">
        <CardHeader><CardTitle className="text-lg">Akce</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <Field label="Poznámka k záloze"><Input value={note} onChange={(event) => setNote(event.target.value)} /></Field>
          <Button onClick={manual}><DatabaseBackup className="size-4" /> Vytvořit zálohu</Button>
          <Separator />
          <Field label="Popis recovery bodu"><Input value={description} onChange={(event) => setDescription(event.target.value)} /></Field>
          <Button variant="outline" onClick={recovery}><RotateCcw className="size-4" /> Vytvořit recovery</Button>
        </CardContent>
      </Card>
      <div className="grid gap-4">
        <Card className="rounded-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-lg">Zálohy</CardTitle>
            <Button variant="outline" size="icon" onClick={props.onReload} aria-label="Obnovit"><RefreshCw className="size-4" /></Button>
          </CardHeader>
          <CardContent>
            {props.error && <StatusLine text={props.error} tone="error" />}
            <Table>
              <TableHeader><TableRow><TableHead>Soubor</TableHead><TableHead>Stav</TableHead><TableHead>Velikost</TableHead><TableHead>Vytvořeno</TableHead><TableHead>Akce</TableHead></TableRow></TableHeader>
              <TableBody>
                {props.backups.map((backup) => (
                  <TableRow key={backup.id}>
                    <TableCell className="font-medium">{backup.file_path}</TableCell>
                    <TableCell>{backup.status}</TableCell>
                    <TableCell>{formatBytes(backup.size_bytes)}</TableCell>
                    <TableCell>{formatDate(backup.created_at)}</TableCell>
                    <TableCell><Button variant="destructive" size="icon-sm" onClick={() => remove(backup.id)} aria-label="Smazat"><Trash2 className="size-3.5" /></Button></TableCell>
                  </TableRow>
                ))}
                {!props.backups.length && <TableRow><TableCell colSpan={5} className="h-20 text-center text-muted-foreground">{props.loading ? 'Načítám zálohy...' : 'Žádné zálohy'}</TableCell></TableRow>}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardHeader><CardTitle className="text-lg">Recovery body vytvořené v této relaci</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Popis</TableHead><TableHead>Snapshot</TableHead><TableHead>Vytvořeno</TableHead><TableHead>Obnova</TableHead></TableRow></TableHeader>
              <TableBody>
                {recoveryPoints.map((point) => (
                  <TableRow key={point.id}>
                    <TableCell>{point.description || '-'}</TableCell>
                    <TableCell>{point.data_snapshot_path}</TableCell>
                    <TableCell>{formatDate(point.created_at)}</TableCell>
                    <TableCell><Button variant="outline" size="sm" onClick={() => restore(point.id)}><RotateCcw className="size-4" /> Restore</Button></TableCell>
                  </TableRow>
                ))}
                {!recoveryPoints.length && <TableRow><TableCell colSpan={4} className="h-20 text-center text-muted-foreground">Nový recovery bod se zobrazí po vytvoření</TableCell></TableRow>}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function catalogRows(catalog: CatalogBootstrap | null, kind: CatalogKind): CatalogRecord[] {
  if (!catalog) return []
  if (kind === 'service-categories') return catalog.service_categories
  if (kind === 'services') return catalog.services
  if (kind === 'due-terms') return catalog.due_terms
  if (kind === 'inventory-items') return catalog.inventory_items
  if (kind === 'hotel-rooms') return catalog.hotel_rooms
  if (kind === 'housekeeping-minibar-items') return catalog.housekeeping_minibar_items
  if (kind === 'photo-task-types') return catalog.photo_task_types
  return catalog.email_recipients
}

type FieldConfig = { name: string; label: string; type?: string; required?: boolean; options?: Array<{ value: string; label: string }> }

function fieldsForKind(kind: CatalogKind, catalog: CatalogBootstrap | null): FieldConfig[] {
  const base: FieldConfig[] = [{ name: 'name', label: 'Název', required: true }, { name: 'sort_order', label: 'Pořadí', type: 'number' }]
  if (kind === 'services') return [{ name: 'category_id', label: 'Kategorie', required: true, options: (catalog?.service_categories ?? []).map((item) => ({ value: item.id, label: item.name })) }, ...base, { name: 'type', label: 'Typ' }, { name: 'price', label: 'Cena', type: 'number' }]
  if (kind === 'due-terms') return [...base, { name: 'value', label: 'Hodnota', type: 'number', required: true }, { name: 'unit', label: 'Jednotka', required: true, options: [{ value: 'hodiny', label: 'hodiny' }, { value: 'dny', label: 'dny' }] }]
  if (kind === 'inventory-items') return [...base, { name: 'module', label: 'Modul', required: true, options: [{ value: 'wellness', label: 'wellness' }, { value: 'minibar', label: 'minibar' }, { value: 'lobby', label: 'lobby' }] }, { name: 'unit', label: 'Jednotka', required: true }, { name: 'category', label: 'Kategorie' }, { name: 'price', label: 'Cena', type: 'number' }]
  if (kind === 'hotel-rooms') return [{ name: 'label', label: 'Pokoj', required: true }, { name: 'sort_order', label: 'Pořadí', type: 'number' }]
  if (kind === 'email-recipients') return [...base, { name: 'email', label: 'E-mail', type: 'email', required: true }]
  return base
}

function payloadForKind(kind: CatalogKind, form: Record<string, string>, catalog: CatalogBootstrap | null): Record<string, unknown> {
  const payload: Record<string, unknown> = { active: true, sort_order: Number(form.sort_order || 0) }
  for (const field of fieldsForKind(kind, catalog)) {
    const value = form[field.name]
    if (value === undefined || value === '') continue
    payload[field.name] = field.type === 'number' ? Number(value) : value
  }
  if (kind === 'inventory-items') payload.has_price = form.price !== undefined && form.price !== ''
  if (kind === 'services' && !payload.type) payload.type = 'ostatni'
  return payload
}

function displayName(row: CatalogRecord) {
  return 'name' in row ? row.name : row.label
}

function displayDetail(row: CatalogRecord) {
  if ('email' in row) return row.email
  if ('price' in row && row.price !== null && row.price !== undefined) return `${row.price} Kč`
  if ('value' in row) return `${row.value} ${row.unit}`
  if ('module' in row) return `${row.module} / ${row.unit}`
  return '-'
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="grid gap-1 text-sm font-medium">{label}{children}</label>
}

function StatusLine({ text, tone = 'default' }: { text: string; tone?: 'default' | 'error' }) {
  return <div className={`rounded-md border px-3 py-2 text-sm ${tone === 'error' ? 'border-destructive text-destructive' : 'bg-muted/40'}`}>{text}</div>
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('cs-CZ')
}

function formatBytes(value?: number | null) {
  if (!value) return '-'
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} kB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
