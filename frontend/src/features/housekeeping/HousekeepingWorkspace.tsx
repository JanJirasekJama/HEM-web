import { useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import {
  BedDouble,
  Camera,
  Check,
  ClipboardCheck,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Shirt,
  SquarePen,
  Timer,
  Upload,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

import { useHousekeepingWorkspace } from './hooks'
import type { AssignmentCreateDraft, HousekeepingAssignment, HousekeepingRole, HousekeepingWorkspaceData, RevisionTask } from './types'

type DialogState =
  | { type: 'assignment' }
  | { type: 'assignment-photo'; assignmentId: string; photoTaskTypeId?: string; taskLabel?: string }
  | { type: 'revision-create' }
  | { type: 'revision-complete'; revisionId: string }
  | { type: 'laundry-photo'; laundryId: string }
  | null

export function HousekeepingWorkspace({ initialData }: { initialData?: HousekeepingWorkspaceData }) {
  const { data, loading, error, pending, actions } = useHousekeepingWorkspace(initialData)
  const [role, setRole] = useState<HousekeepingRole>('reception')
  const [tab, setTab] = useState('rooms')
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string | null>(data.assignments[0]?.id ?? null)
  const [dialog, setDialog] = useState<DialogState>(null)
  const selectedAssignment = data.assignments.find((assignment) => assignment.id === selectedAssignmentId) ?? data.assignments[0]
  const openAssignments = data.assignments.filter((assignment) => assignment.status !== 'Hotovo')
  const doneAssignments = data.assignments.filter((assignment) => assignment.status === 'Hotovo')
  const openRevisions = data.revisions.filter((revision) => revision.status === 'open')

  const stats = useMemo(
    () => [
      { label: 'Čeká', value: data.assignments.filter((item) => item.status === 'Prideleno').length },
      { label: 'Běží', value: data.assignments.filter((item) => item.status === 'Uklizi se').length },
      { label: 'Revize', value: openRevisions.length },
      { label: 'Prádelna', value: data.laundry.filter((item) => item.status !== 'done').length },
    ],
    [data.assignments, data.laundry, openRevisions.length],
  )

  return (
    <section className="min-h-svh bg-background">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-3 py-3 sm:px-5 lg:px-8">
        <header className="flex flex-col gap-3 rounded-md border bg-card px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border bg-background">
              <BedDouble className="size-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-normal sm:text-2xl">Housekeeping</h1>
              <p className="text-sm text-muted-foreground">{loading ? 'Načítám provozní data' : error ? 'Lokální náhled, backend nedostupný' : 'Recepce a pokojské v jednom workflow'}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex">
            <Button variant={role === 'reception' ? 'default' : 'outline'} onClick={() => setRole('reception')}>
              <ClipboardCheck className="size-4" aria-hidden="true" />
              Recepce
            </Button>
            <Button variant={role === 'housekeeper' ? 'default' : 'outline'} onClick={() => setRole('housekeeper')}>
              <Shirt className="size-4" aria-hidden="true" />
              Pokojská
            </Button>
          </div>
        </header>

        <section className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {stats.map((item) => (
            <div key={item.label} className="rounded-md border bg-card p-3">
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className="text-2xl font-semibold tracking-normal">{item.value}</div>
            </div>
          ))}
        </section>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid h-auto w-full grid-cols-3 sm:inline-flex sm:w-fit">
            <TabsTrigger value="rooms">Pokoje</TabsTrigger>
            <TabsTrigger value="revision">Revize</TabsTrigger>
            <TabsTrigger value="reports">Reporty</TabsTrigger>
          </TabsList>

          <TabsContent value="rooms" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-semibold tracking-normal">Úklidy</h2>
                {role === 'reception' && (
                  <Button onClick={() => setDialog({ type: 'assignment' })}>
                    <Plus className="size-4" aria-hidden="true" />
                    Zadat
                  </Button>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {[...openAssignments, ...doneAssignments].map((assignment) => (
                  <AssignmentCard key={assignment.id} assignment={assignment} active={assignment.id === selectedAssignment?.id} onSelect={() => setSelectedAssignmentId(assignment.id)} />
                ))}
              </div>
            </div>

            <AssignmentDetail
              assignment={selectedAssignment}
              role={role}
              minibarItems={data.minibarItems}
              pending={pending}
              onStart={actions.startAssignment}
              onPause={actions.pauseAssignment}
              onResume={actions.resumeAssignment}
              onFinish={actions.finishAssignment}
              onUploadPhoto={(assignment, required) =>
                setDialog({ type: 'assignment-photo', assignmentId: assignment.id, photoTaskTypeId: required?.photo_task_type_id, taskLabel: required?.task_label_snapshot })
              }
              onAddMinibar={actions.addMinibarEntry}
            />
          </TabsContent>

          <TabsContent value="revision" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
            <section className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold tracking-normal">Revize</h2>
                {role === 'reception' && (
                  <Button onClick={() => setDialog({ type: 'revision-create' })}>
                    <SquarePen className="size-4" aria-hidden="true" />
                    Nová
                  </Button>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {data.revisions.map((revision) => (
                  <RevisionCard key={revision.id} revision={revision} role={role} onComplete={() => setDialog({ type: 'revision-complete', revisionId: revision.id })} />
                ))}
              </div>
            </section>
            <LaundryPanel data={data} role={role} pending={pending} onCreate={actions.createLaundry} onAccept={actions.acceptLaundry} onPhoto={(laundryId) => setDialog({ type: 'laundry-photo', laundryId })} onDone={actions.finishLaundry} />
          </TabsContent>

          <TabsContent value="reports" className="grid gap-4 lg:grid-cols-2">
            <HistoryPanel data={data} />
            <MonthlyReport data={data} />
          </TabsContent>
        </Tabs>
      </div>

      <AssignmentDialog open={dialog?.type === 'assignment'} data={data} onOpenChange={(open) => setDialog(open ? { type: 'assignment' } : null)} onSubmit={actions.createAssignments} />
      <PhotoDialog
        open={dialog?.type === 'assignment-photo'}
        title="Nahrát fotku pokoje"
        capture
        onOpenChange={(open) => setDialog(open && dialog?.type === 'assignment-photo' ? dialog : null)}
        onSubmit={(file) => {
          if (dialog?.type !== 'assignment-photo') return Promise.resolve()
          return actions.uploadAssignmentPhoto(dialog.assignmentId, file, dialog.taskLabel, dialog.photoTaskTypeId)
        }}
      />
      <RevisionDialog open={dialog?.type === 'revision-create'} onOpenChange={(open) => setDialog(open ? { type: 'revision-create' } : null)} onSubmit={actions.createRevision} />
      <RevisionCompleteDialog
        open={dialog?.type === 'revision-complete'}
        onOpenChange={(open) => setDialog(open && dialog?.type === 'revision-complete' ? dialog : null)}
        onSubmit={(note, files) => {
          if (dialog?.type !== 'revision-complete') return Promise.resolve()
          return actions.completeRevision(dialog.revisionId, note, files)
        }}
      />
      <PhotoDialog
        open={dialog?.type === 'laundry-photo'}
        title="Fotka skříně s prádlem"
        capture
        onOpenChange={(open) => setDialog(open && dialog?.type === 'laundry-photo' ? dialog : null)}
        onSubmit={(file) => {
          if (dialog?.type !== 'laundry-photo') return Promise.resolve()
          return actions.uploadLaundryPhoto(dialog.laundryId, file)
        }}
      />
    </section>
  )
}

function AssignmentCard({ assignment, active, onSelect }: { assignment: HousekeepingAssignment; active: boolean; onSelect: () => void }) {
  return (
    <button type="button" onClick={onSelect} className={'rounded-md border bg-card p-3 text-left transition-colors hover:bg-muted/60 ' + (active ? 'border-primary ring-2 ring-primary/20' : '')}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-lg font-semibold tracking-normal">Pokoj {assignment.room_label_snapshot}</div>
          <div className="text-sm text-muted-foreground">{assignment.work_type}</div>
        </div>
        <StatusBadge status={assignment.status} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span>{assignment.priority}</span>
        <span>{assignment.required_photos.filter((photo) => !photo.uploaded).length} fotek chybí</span>
        <span>{assignment.minibar_entries.length} minibar</span>
      </div>
    </button>
  )
}

function AssignmentDetail(props: {
  assignment?: HousekeepingAssignment
  role: HousekeepingRole
  minibarItems: Array<{ id: string; name: string }>
  pending: Partial<Record<string, boolean>>
  onStart: (id: string) => Promise<void>
  onPause: (id: string) => Promise<void>
  onResume: (id: string) => Promise<void>
  onFinish: (id: string) => Promise<void>
  onUploadPhoto: (assignment: HousekeepingAssignment, required?: HousekeepingAssignment['required_photos'][number]) => void
  onAddMinibar: (assignmentId: string, itemId: string, quantity: number) => Promise<void>
}) {
  const [minibarItemId, setMinibarItemId] = useState(props.minibarItems[0]?.id ?? '')
  const [quantity, setQuantity] = useState(1)
  const assignment = props.assignment
  if (!assignment) return <Card className="rounded-md"><CardContent>Žádný pokoj není vybraný.</CardContent></Card>
  const missingRequired = assignment.required_photos.filter((photo) => !photo.uploaded)
  const canFinish = missingRequired.length === 0

  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>Pokoj {assignment.room_label_snapshot}</CardTitle>
        <CardDescription>{assignment.reception_note || 'Bez poznámky recepce'}</CardDescription>
        <CardAction><StatusBadge status={assignment.status} /></CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {props.role === 'housekeeper' && (
          <div className="grid grid-cols-2 gap-2">
            {assignment.status === 'Prideleno' && <Button onClick={() => props.onStart(assignment.id)}><Play className="size-4" aria-hidden="true" />Start</Button>}
            {assignment.status === 'Uklizi se' && <Button variant="outline" onClick={() => props.onPause(assignment.id)}><Pause className="size-4" aria-hidden="true" />Pauza</Button>}
            {assignment.status === 'Pozastaveno' && <Button onClick={() => props.onResume(assignment.id)}><RefreshCw className="size-4" aria-hidden="true" />Pokračovat</Button>}
            <Button disabled={!canFinish || assignment.status === 'Hotovo'} onClick={() => props.onFinish(assignment.id)}><Check className="size-4" aria-hidden="true" />Hotovo</Button>
          </div>
        )}

        <section className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium"><Camera className="size-4" aria-hidden="true" />Povinné fotky</div>
          <div className="grid gap-2">
            {assignment.required_photos.map((required) => (
              <div key={required.id} className="flex items-center justify-between gap-2 rounded-md border p-2">
                <div>
                  <div className="font-medium">{required.task_label_snapshot}</div>
                  <div className="text-xs text-muted-foreground">{required.uploaded ? 'Nahráno' : 'Vyžadováno před dokončením'}</div>
                </div>
                <Button size="icon" variant={required.uploaded ? 'outline' : 'default'} onClick={() => props.onUploadPhoto(assignment, required)} aria-label={'Nahrát fotku ' + required.task_label_snapshot}>
                  <Upload className="size-4" aria-hidden="true" />
                </Button>
              </div>
            ))}
            <Button variant="outline" onClick={() => props.onUploadPhoto(assignment)}>
              <Camera className="size-4" aria-hidden="true" />
              Dobrovolná fotka
            </Button>
          </div>
        </section>

        <Separator />
        <section className="space-y-2">
          <div className="text-sm font-medium">Minibar checklist</div>
          <div className="grid grid-cols-[1fr_80px_auto] gap-2">
            <select className="h-8 rounded-lg border bg-background px-2 text-sm" value={minibarItemId} onChange={(event) => setMinibarItemId(event.target.value)} aria-label="Položka minibaru">
              {props.minibarItems.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <Input type="number" min={1} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} aria-label="Počet" />
            <Button size="icon" disabled={!minibarItemId || Boolean(props.pending.addMinibarEntry)} onClick={() => props.onAddMinibar(assignment.id, minibarItemId, quantity)} aria-label="Přidat minibar">
              <Plus className="size-4" aria-hidden="true" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {assignment.minibar_entries.map((entry) => <Badge key={entry.id} variant="secondary">{entry.item_name_snapshot} × {entry.quantity}</Badge>)}
            {!assignment.minibar_entries.length && <span className="text-sm text-muted-foreground">Zatím nic zapsáno</span>}
          </div>
        </section>
      </CardContent>
    </Card>
  )
}

function RevisionCard({ revision, role, onComplete }: { revision: RevisionTask; role: HousekeepingRole; onComplete: () => void }) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>{revision.location}</CardTitle>
        <CardDescription>{revision.text}</CardDescription>
        <CardAction><Badge variant={revision.status === 'open' ? 'outline' : 'secondary'}>{revision.status === 'open' ? 'Ke splnění' : 'Hotovo'}</Badge></CardAction>
      </CardHeader>
      {role === 'housekeeper' && revision.status === 'open' && (
        <CardContent>
          <Button className="w-full" onClick={onComplete}><Check className="size-4" aria-hidden="true" />Splnit revizi</Button>
        </CardContent>
      )}
    </Card>
  )
}

function LaundryPanel(props: {
  data: HousekeepingWorkspaceData
  role: HousekeepingRole
  pending: Partial<Record<string, boolean>>
  onCreate: () => Promise<void>
  onAccept: (id: string) => Promise<void>
  onPhoto: (id: string) => void
  onDone: (id: string) => Promise<void>
}) {
  const active = props.data.laundry.filter((task) => task.status !== 'done')
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>Prádelna</CardTitle>
        <CardDescription>Echo, převzetí, fotka skříně a dokončení</CardDescription>
        {props.role === 'reception' && <CardAction><Button size="icon" onClick={props.onCreate} aria-label="Vyvolat prádelnu"><Plus className="size-4" aria-hidden="true" /></Button></CardAction>}
      </CardHeader>
      <CardContent className="grid gap-2">
        {active.map((task) => (
          <div key={task.id} className="rounded-md border p-3">
            <div className="flex items-center justify-between">
              <span className="font-medium">{task.status === 'open' ? 'Dorazila prádelna' : 'Převzato'}</span>
              <Badge variant="outline">{task.photo_uploaded ? 'Fotka OK' : 'Chybí fotka'}</Badge>
            </div>
            {props.role === 'housekeeper' && (
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Button variant="outline" disabled={task.status !== 'open'} onClick={() => props.onAccept(task.id)}>Převzít</Button>
                <Button variant="outline" onClick={() => props.onPhoto(task.id)}><Camera className="size-4" aria-hidden="true" />Foto</Button>
                <Button disabled={!task.photo_uploaded || Boolean(props.pending.finishLaundry)} onClick={() => props.onDone(task.id)}>Hotovo</Button>
              </div>
            )}
          </div>
        ))}
        {!active.length && <p className="text-sm text-muted-foreground">Žádné aktivní echo prádelny.</p>}
      </CardContent>
    </Card>
  )
}

function HistoryPanel({ data }: { data: HousekeepingWorkspaceData }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle>Historie úklidů</CardTitle><CardDescription>{data.report.month}</CardDescription></CardHeader>
      <CardContent className="grid gap-2">
        {data.history.map((row) => (
          <div key={row.id} className="grid grid-cols-[1fr_auto] gap-2 rounded-md border p-3">
            <div>
              <div className="font-medium">Pokoj {row.room_label_snapshot}</div>
              <div className="text-sm text-muted-foreground">{row.work_type} · {row.housekeeper_username_snapshot || 'bez jména'}</div>
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground"><Timer className="size-4" aria-hidden="true" />{formatSeconds(row.duration_seconds)}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function MonthlyReport({ data }: { data: HousekeepingWorkspaceData }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle>Měsíční report</CardTitle><CardDescription>Výkon pokojských</CardDescription></CardHeader>
      <CardContent className="grid gap-2">
        {Object.entries(data.report.housekeepers).map(([name, row]) => (
          <div key={name} className="grid grid-cols-[1fr_repeat(3,52px)] items-center gap-2 rounded-md border p-3 text-sm">
            <div className="font-medium">{name}</div>
            <div className="text-center">{row.assignment_count}</div>
            <div className="text-center">{row.revision_count}</div>
            <div className="text-center">{row.laundry_count}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function AssignmentDialog(props: { open: boolean; data: HousekeepingWorkspaceData; onOpenChange: (open: boolean) => void; onSubmit: (draft: AssignmentCreateDraft) => Promise<void> }) {
  const [draft, setDraft] = useState<AssignmentCreateDraft>({ roomIds: [], workType: 'Prijezd', priority: 'Normalni', receptionNote: '', requiredPhotoTypeIds: [] })
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await props.onSubmit(draft)
    props.onOpenChange(false)
  }
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
        <DialogHeader><DialogTitle>Zadat úklid</DialogTitle></DialogHeader>
        <form className="grid gap-4" onSubmit={submit}>
          <div className="grid grid-cols-3 gap-2">
            {props.data.rooms.map((room) => (
              <label key={room.id} className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <Checkbox checked={draft.roomIds.includes(room.id)} onCheckedChange={(checked) => setDraft((current) => ({ ...current, roomIds: toggle(current.roomIds, room.id, Boolean(checked)) }))} />
                {room.label}
              </label>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input value={draft.workType} onChange={(event) => setDraft((current) => ({ ...current, workType: event.target.value }))} placeholder="Typ úklidu" />
            <Input value={draft.priority} onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value }))} placeholder="Priorita" />
          </div>
          <Textarea value={draft.receptionNote} onChange={(event) => setDraft((current) => ({ ...current, receptionNote: event.target.value }))} placeholder="Poznámka pro pokojskou" />
          <div className="grid gap-2">
            {props.data.photoTaskTypes.map((task) => (
              <label key={task.id} className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <Checkbox checked={draft.requiredPhotoTypeIds.includes(task.id)} onCheckedChange={(checked) => setDraft((current) => ({ ...current, requiredPhotoTypeIds: toggle(current.requiredPhotoTypeIds, task.id, Boolean(checked)) }))} />
                {task.name}
              </label>
            ))}
          </div>
          <DialogFooter><Button type="submit" disabled={!draft.roomIds.length}>Vytvořit zadání</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RevisionDialog(props: { open: boolean; onOpenChange: (open: boolean) => void; onSubmit: (draft: { location: string; text: string }) => Promise<void> }) {
  const [location, setLocation] = useState('')
  const [text, setText] = useState('')
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await props.onSubmit({ location, text })
    props.onOpenChange(false)
  }
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Nová revize</DialogTitle></DialogHeader>
        <form className="grid gap-3" onSubmit={submit}>
          <Input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Místo" required />
          <Textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Úkol" required />
          <DialogFooter><Button type="submit">Uložit</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RevisionCompleteDialog(props: { open: boolean; onOpenChange: (open: boolean) => void; onSubmit: (note: string, files: File[]) => Promise<void> }) {
  const [note, setNote] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await props.onSubmit(note, files)
    props.onOpenChange(false)
  }
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Splnit revizi</DialogTitle></DialogHeader>
        <form className="grid gap-3" onSubmit={submit}>
          <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Poznámka" />
          <Input type="file" accept="image/*" capture="environment" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} />
          <DialogFooter><Button type="submit">Dokončit</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function PhotoDialog(props: { open: boolean; title: string; capture?: boolean; onOpenChange: (open: boolean) => void; onSubmit: (file: File) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null)
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) return
    await props.onSubmit(file)
    props.onOpenChange(false)
  }
  const changeFile = (event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null)
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>{props.title}</DialogTitle></DialogHeader>
        <form className="grid gap-3" onSubmit={submit}>
          <Input type="file" accept="image/*" capture={props.capture ? 'environment' : undefined} onChange={changeFile} required />
          <DialogFooter><Button type="submit" disabled={!file}><Upload className="size-4" aria-hidden="true" />Nahrát</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function StatusBadge({ status }: { status: HousekeepingAssignment['status'] }) {
  const variant = status === 'Hotovo' ? 'secondary' : status === 'Uklizi se' ? 'default' : 'outline'
  return <Badge variant={variant}>{status}</Badge>
}

function toggle(values: string[], value: string, checked: boolean) {
  if (checked) return values.includes(value) ? values : [...values, value]
  return values.filter((item) => item !== value)
}

function formatSeconds(value?: number | null) {
  if (!value) return '0 min'
  return Math.round(value / 60) + ' min'
}
