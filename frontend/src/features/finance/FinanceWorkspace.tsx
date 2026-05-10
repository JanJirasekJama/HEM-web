import { useMemo, useState } from 'react'
import { Archive, Download, FileDown, FileText, Mail, Plus, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

import {
  archiveCsvUrl,
  createInvoice,
  createReportExport,
  invoicePdfUrl,
  loadFinanceBootstrap,
  loadInventoryMonthly,
  loadInvoiceArchive,
  loadInvoiceStatistics,
  loadInvoiceTax,
  markInvoicePaid,
  markInvoiceUnpaid,
  queueInvoiceEmail,
  refreshInvoiceStatuses,
  useFinanceResource,
} from './api'
import type { CatalogBootstrap, InventoryMonthlyReport, Invoice, InvoiceStatistics, InvoiceTaxReport } from './types'

const money = new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', maximumFractionDigits: 0 })

export function FinanceWorkspace({ defaultTab = 'invoices' }: { defaultTab?: 'invoices' | 'reports' }) {
  const catalog = useFinanceResource(loadFinanceBootstrap, [])
  const archive = useFinanceResource(loadInvoiceArchive, [])
  const [message, setMessage] = useState('')

  const mutateArchive = async (action: () => Promise<unknown>, success: string) => {
    setMessage('')
    try {
      await action()
      setMessage(success)
      archive.reload()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Akce se nepodařila')
    }
  }

  return (
    <section className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8">
      <WorkspaceHeader title="Finance" detail="Fakturace, platby, PDF, e-mailová fronta a reporty" />
      {message && <StatusLine text={message} />}
      <Tabs defaultValue={defaultTab} className="gap-4">
        <TabsList className="w-full justify-start overflow-x-auto rounded-md">
          <TabsTrigger value="invoices"><FileText className="size-4" /> Fakturace</TabsTrigger>
          <TabsTrigger value="reports"><Archive className="size-4" /> Reporty</TabsTrigger>
        </TabsList>
        <TabsContent value="invoices" className="grid gap-4 xl:grid-cols-[380px_1fr]">
          <InvoiceCreatePanel catalog={catalog.data} loading={catalog.loading} onCreated={() => archive.reload()} onMessage={setMessage} />
          <InvoiceArchivePanel
            invoices={archive.data ?? []}
            loading={archive.loading}
            error={archive.error}
            onRefresh={() => archive.reload()}
            onRefreshStatuses={() => mutateArchive(refreshInvoiceStatuses, 'Splatnosti byly přepočítány.')}
            onTogglePaid={(invoice) =>
              mutateArchive(
                () => (invoice.payment_status === 'paid' ? markInvoiceUnpaid(invoice.id) : markInvoicePaid(invoice.id)),
                invoice.payment_status === 'paid' ? 'Faktura je zpět jako neuhrazená.' : 'Faktura je označena jako uhrazená.',
              )
            }
            onQueueEmail={(invoice) => mutateArchive(() => queueInvoiceEmail(invoice.id), 'E-mail byl zařazen do fronty.')}
          />
        </TabsContent>
        <TabsContent value="reports">
          <ReportsPanel />
        </TabsContent>
      </Tabs>
    </section>
  )
}

function WorkspaceHeader({ title, detail }: { title: string; detail: string }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </div>
      <div className="flex items-center gap-2">
        <a className={cn(buttonVariants({ variant: 'outline' }))} href={archiveCsvUrl()}><FileDown className="size-4" /> CSV faktur</a>
      </div>
    </header>
  )
}

function InvoiceCreatePanel(props: { catalog: CatalogBootstrap | null; loading: boolean; onCreated: () => void; onMessage: (message: string) => void }) {
  const services = props.catalog?.services.filter((item) => item.active) ?? []
  const dueTerms = props.catalog?.due_terms.filter((item) => item.active) ?? []
  const [serviceMode, setServiceMode] = useState<'catalog' | 'custom'>('catalog')
  const [form, setForm] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    service_id: '',
    custom_service_name: '',
    event_at: '',
    due_term_id: '',
    price: '',
    increase_percent: '0',
    note: '',
  })

  const selectedService = services.find((service) => service.id === form.service_id)
  const effectivePrice = serviceMode === 'catalog' ? selectedService?.price : Number(form.price || 0)

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    props.onMessage('')
    try {
      await createInvoice({
        customer_name: form.customer_name,
        customer_email: form.customer_email || undefined,
        customer_phone: form.customer_phone || undefined,
        service_id: serviceMode === 'catalog' ? form.service_id : undefined,
        custom_service_name: serviceMode === 'custom' ? form.custom_service_name : undefined,
        event_at: form.event_at,
        due_term_id: form.due_term_id,
        price: serviceMode === 'custom' || form.price ? Number(form.price) : undefined,
        increase_percent: Number(form.increase_percent || 0),
        note: form.note || undefined,
      })
      setForm((current) => ({ ...current, customer_name: '', customer_email: '', customer_phone: '', note: '' }))
      props.onCreated()
      props.onMessage('Faktura byla vytvořena a PDF připraveno.')
    } catch (error) {
      props.onMessage(error instanceof Error ? error.message : 'Fakturu se nepodařilo vytvořit')
    }
  }

  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle className="text-lg">Nová faktura</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="grid gap-3" onSubmit={submit}>
          <Field label="Zákazník"><Input value={form.customer_name} onChange={(event) => setForm({ ...form, customer_name: event.target.value })} required /></Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="E-mail"><Input type="email" value={form.customer_email} onChange={(event) => setForm({ ...form, customer_email: event.target.value })} /></Field>
            <Field label="Telefon"><Input value={form.customer_phone} onChange={(event) => setForm({ ...form, customer_phone: event.target.value })} /></Field>
          </div>
          <div className="flex rounded-md border p-1">
            <Button type="button" variant={serviceMode === 'catalog' ? 'default' : 'ghost'} className="flex-1" onClick={() => setServiceMode('catalog')}>Katalog</Button>
            <Button type="button" variant={serviceMode === 'custom' ? 'default' : 'ghost'} className="flex-1" onClick={() => setServiceMode('custom')}>Vlastní</Button>
          </div>
          {serviceMode === 'catalog' ? (
            <Field label="Služba">
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={form.service_id} onChange={(event) => setForm({ ...form, service_id: event.target.value, price: '' })} required>
                <option value="">{props.loading ? 'Načítám...' : 'Vyberte službu'}</option>
                {services.map((service) => <option key={service.id} value={service.id}>{service.name} - {money.format(service.price)}</option>)}
              </select>
            </Field>
          ) : (
            <div className="grid gap-3 sm:grid-cols-[1fr_120px]">
              <Field label="Vlastní služba"><Input value={form.custom_service_name} onChange={(event) => setForm({ ...form, custom_service_name: event.target.value })} required /></Field>
              <Field label="Cena"><Input type="number" min="0" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required /></Field>
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Termín"><Input placeholder="DD.MM.RRRR HH:MM" value={form.event_at} onChange={(event) => setForm({ ...form, event_at: event.target.value })} required /></Field>
            <Field label="Splatnost">
              <select className="h-9 rounded-md border bg-background px-3 text-sm" value={form.due_term_id} onChange={(event) => setForm({ ...form, due_term_id: event.target.value })} required>
                <option value="">Vyberte</option>
                {dueTerms.map((term) => <option key={term.id} value={term.id}>{term.name}</option>)}
              </select>
            </Field>
            <Field label="Navýšení %"><Input type="number" value={form.increase_percent} onChange={(event) => setForm({ ...form, increase_percent: event.target.value })} /></Field>
          </div>
          <Field label="Poznámka"><Textarea value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} /></Field>
          <Separator />
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm text-muted-foreground">Základ: {effectivePrice === undefined ? 'nezvolen' : money.format(effectivePrice)}</div>
            <Button type="submit"><Plus className="size-4" /> Vytvořit</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function InvoiceArchivePanel(props: {
  invoices: Invoice[]
  loading: boolean
  error: string
  onRefresh: () => void
  onRefreshStatuses: () => void
  onTogglePaid: (invoice: Invoice) => void
  onQueueEmail: (invoice: Invoice) => void
}) {
  const totals = useMemo(() => props.invoices.reduce((sum, invoice) => sum + Number(invoice.price || 0), 0), [props.invoices])

  return (
    <Card className="rounded-md">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-lg">Archiv faktur</CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="icon" onClick={props.onRefresh} aria-label="Obnovit"><RefreshCw className="size-4" /></Button>
            <Button variant="outline" onClick={props.onRefreshStatuses}>Přepočítat splatnosti</Button>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Faktury" value={String(props.invoices.length)} />
          <Metric label="Celkem" value={money.format(totals)} />
          <Metric label="Po splatnosti" value={String(props.invoices.filter((invoice) => invoice.payment_status === 'overdue').length)} />
        </div>
      </CardHeader>
      <CardContent>
        {props.error && <StatusLine text={props.error} tone="error" />}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Číslo</TableHead>
              <TableHead>Zákazník</TableHead>
              <TableHead>Služba</TableHead>
              <TableHead>Částka</TableHead>
              <TableHead>Stav</TableHead>
              <TableHead>Akce</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {props.invoices.map((invoice) => (
              <TableRow key={invoice.id}>
                <TableCell className="font-medium">{invoice.invoice_number}</TableCell>
                <TableCell>{invoice.customer_name}</TableCell>
                <TableCell>{invoice.service_name}</TableCell>
                <TableCell>{money.format(invoice.price)}</TableCell>
                <TableCell><PaymentBadge status={invoice.payment_status} /></TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="outline" size="icon-sm" onClick={() => props.onTogglePaid(invoice)} aria-label="Přepnout platbu"><RefreshCw className="size-3.5" /></Button>
                    <Button variant="outline" size="icon-sm" onClick={() => props.onQueueEmail(invoice)} aria-label="Zařadit e-mail"><Mail className="size-3.5" /></Button>
                    <a className={cn(buttonVariants({ variant: 'outline', size: 'icon-sm' }))} href={invoicePdfUrl(invoice.id)} aria-label="Stáhnout PDF"><Download className="size-3.5" /></a>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {!props.invoices.length && (
              <TableRow><TableCell colSpan={6} className="h-20 text-center text-muted-foreground">{props.loading ? 'Načítám archiv...' : 'Archiv je prázdný'}</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function ReportsPanel() {
  const today = new Date().toISOString().slice(0, 10)
  const month = today.slice(0, 7)
  const [filters, setFilters] = useState({ from: `${today.slice(0, 8)}01`, to: today, module: 'minibar', month })
  const stats = useFinanceResource((signal) => loadInvoiceStatistics(filters.from, filters.to, signal), [filters.from, filters.to])
  const tax = useFinanceResource((signal) => loadInvoiceTax(filters.from, filters.to, signal), [filters.from, filters.to])
  const inventory = useFinanceResource((signal) => loadInventoryMonthly(filters.module, filters.month, signal), [filters.module, filters.month])
  const [exportMessage, setExportMessage] = useState('')

  const createExport = async (module: string, exportType: string) => {
    setExportMessage('')
    try {
      const result = await createReportExport({ module, export_type: exportType, period_from: filters.from, period_to: filters.to })
      setExportMessage(`Export připraven: ${result.file_path}`)
    } catch (error) {
      setExportMessage(error instanceof Error ? error.message : 'Export se nepodařil')
    }
  }

  return (
    <div className="grid gap-4">
      <Card className="rounded-md">
        <CardContent className="grid gap-3 pt-6 sm:grid-cols-5">
          <Field label="Od"><Input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} /></Field>
          <Field label="Do"><Input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} /></Field>
          <Field label="Inventory"><select className="h-9 rounded-md border bg-background px-3 text-sm" value={filters.module} onChange={(event) => setFilters({ ...filters, module: event.target.value })}><option value="wellness">Wellness</option><option value="minibar">Minibar</option><option value="lobby">Lobby</option></select></Field>
          <Field label="Měsíc"><Input type="month" value={filters.month} onChange={(event) => setFilters({ ...filters, month: event.target.value })} /></Field>
          <div className="flex items-end gap-2">
            <Button variant="outline" onClick={() => createExport('invoices', 'csv')}><FileDown className="size-4" /> Faktury</Button>
            <Button variant="outline" onClick={() => createExport(filters.module, 'csv')}><FileDown className="size-4" /> Inventory</Button>
          </div>
        </CardContent>
      </Card>
      {exportMessage && <StatusLine text={exportMessage} />}
      <div className="grid gap-4 xl:grid-cols-3">
        <InvoiceStatsCard stats={stats.data} />
        <TaxCard tax={tax.data} />
        <InventoryCard report={inventory.data} />
      </div>
    </div>
  )
}

function InvoiceStatsCard({ stats }: { stats: InvoiceStatistics | null }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle className="text-lg">Statistiky faktur</CardTitle></CardHeader>
      <CardContent className="grid gap-3">
        <Metric label="Počet" value={String(stats?.invoice_count ?? 0)} />
        <Metric label="Uhrazené / neuhrazené" value={`${stats?.paid_count ?? 0} / ${stats?.unpaid_count ?? 0}`} />
        <Metric label="Obrat" value={money.format(stats?.total_amount ?? 0)} />
        <Metric label="Průměr" value={money.format(stats?.average_invoice ?? 0)} />
        <SmallTable rows={Object.entries(stats?.by_service ?? {}).map(([name, value]) => [name, money.format(value)])} />
      </CardContent>
    </Card>
  )
}

function TaxCard({ tax }: { tax: InvoiceTaxReport | null }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle className="text-lg">Daňový přehled</CardTitle></CardHeader>
      <CardContent className="grid gap-3">
        <Metric label="Hrubé" value={money.format(tax?.gross_revenue ?? 0)} />
        <Metric label={`DPH ${tax?.vat_rate ?? 21} %`} value={money.format(tax?.vat ?? 0)} />
        <Metric label="Čisté" value={money.format(tax?.net_revenue ?? 0)} />
        <SmallTable rows={Object.entries(tax?.by_service ?? {}).map(([name, value]) => [name, money.format(value.gross)])} />
      </CardContent>
    </Card>
  )
}

function InventoryCard({ report }: { report: InventoryMonthlyReport | null }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle className="text-lg">Měsíční inventory</CardTitle></CardHeader>
      <CardContent className="grid gap-3">
        <Metric label="Modul" value={report?.module ?? '-'} />
        <Metric label="Vlastní položky" value={money.format(report?.custom_total_price ?? 0)} />
        <SmallTable rows={Object.entries(report?.totals ?? {}).map(([name, value]) => [name, `${value.quantity} ks / ${money.format(value.total_price)}`])} />
      </CardContent>
    </Card>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="grid gap-1 text-sm font-medium">{label}{children}</label>
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border p-3"><div className="text-xs text-muted-foreground">{label}</div><div className="text-lg font-semibold tracking-normal">{value}</div></div>
}

function PaymentBadge({ status }: { status: string }) {
  const variant = status === 'paid' ? 'default' : status === 'overdue' ? 'destructive' : 'secondary'
  const text = status === 'paid' ? 'Uhrazeno' : status === 'overdue' ? 'Po splatnosti' : 'Čeká'
  return <Badge variant={variant}>{text}</Badge>
}

function StatusLine({ text, tone = 'default' }: { text: string; tone?: 'default' | 'error' }) {
  return <div className={`rounded-md border px-3 py-2 text-sm ${tone === 'error' ? 'border-destructive text-destructive' : 'bg-muted/40'}`}>{text}</div>
}

function SmallTable({ rows }: { rows: string[][] }) {
  return (
    <div className="rounded-md border">
      {rows.length ? rows.slice(0, 8).map((row) => (
        <div key={row.join(':')} className="flex items-center justify-between gap-3 border-b px-3 py-2 last:border-b-0">
          <span className="truncate text-muted-foreground">{row[0]}</span>
          <span className="font-medium">{row[1]}</span>
        </div>
      )) : <div className="px-3 py-6 text-center text-muted-foreground">Bez dat</div>}
    </div>
  )
}
