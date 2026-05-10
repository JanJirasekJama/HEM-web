import { useMemo, useState } from 'react'
import { RefreshCw, Shield, Trash2, UserPlus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

import { createUser, deleteUser, loadRoles, loadUsers, useAdminResource } from './api'
import type { RoleRead, UserCreatePayload, UserRead } from './types'

type UserFormState = {
  username: string
  password: string
  display_name: string
  role_name: string
  comment_color: string
}

const initialForm: UserFormState = {
  username: '',
  password: '',
  display_name: '',
  role_name: '',
  comment_color: '#2563eb',
}

export function UserRolesPanel({ onMessage }: { onMessage: (message: string) => void }) {
  const users = useAdminResource(loadUsers, [])
  const roles = useAdminResource(loadRoles, [])

  const reload = () => {
    users.reload()
    roles.reload()
  }

  const save = async (payload: UserCreatePayload) => {
    try {
      await createUser(payload)
      onMessage('Uživatel byl vytvořen.')
      users.reload()
    } catch (error) {
      onMessage(error instanceof Error ? error.message : 'Uživatele se nepodařilo vytvořit')
    }
  }

  const remove = async (userId: string) => {
    try {
      await deleteUser(userId)
      onMessage('Uživatel byl smazán.')
      users.reload()
    } catch (error) {
      onMessage(error instanceof Error ? error.message : 'Uživatele se nepodařilo smazat')
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
      <div className="grid gap-4">
        <Card className="rounded-md">
          <CardHeader><CardTitle className="text-lg">Nový uživatel</CardTitle></CardHeader>
          <CardContent>
            <UserCreateForm roles={roles.data ?? []} onSave={save} />
          </CardContent>
        </Card>
        <RolesCard roles={roles.data ?? []} loading={roles.loading} error={roles.error} />
      </div>
      <Card className="rounded-md">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">Uživatelé</CardTitle>
            <Badge variant="secondary">{users.loading ? 'Načítám' : `${users.data?.length ?? 0} účtů`}</Badge>
          </div>
          <Button variant="outline" size="icon" onClick={reload} aria-label="Obnovit"><RefreshCw className="size-4" /></Button>
        </CardHeader>
        <CardContent className="grid gap-3">
          {users.error && <StatusLine text={users.error} tone="error" />}
          <UsersTable users={users.data ?? []} loading={users.loading} onDelete={remove} />
        </CardContent>
      </Card>
    </div>
  )
}

function UserCreateForm({ roles, onSave }: { roles: RoleRead[]; onSave: (payload: UserCreatePayload) => void }) {
  const defaultRole = roles[0]?.name ?? ''
  const [form, setForm] = useState<UserFormState>(initialForm)
  const selectedRole = form.role_name || defaultRole

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload: UserCreatePayload = {
      username: form.username.trim(),
      password: form.password,
      role_name: selectedRole,
      display_name: form.display_name.trim() || null,
      comment_color: form.comment_color || null,
    }
    onSave(payload)
    setForm({ ...initialForm, role_name: selectedRole })
  }

  return (
    <form className="grid gap-3" onSubmit={submit}>
      <Field label="Uživatelské jméno">
        <Input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} minLength={2} required />
      </Field>
      <Field label="Heslo">
        <Input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength={6} required />
      </Field>
      <Field label="Zobrazované jméno">
        <Input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} />
      </Field>
      <div className="grid grid-cols-[1fr_64px] gap-3">
        <Field label="Role">
          <select className="h-9 rounded-md border bg-background px-3 text-sm" value={selectedRole} onChange={(event) => setForm({ ...form, role_name: event.target.value })} required>
            {roles.map((role) => <option key={role.id} value={role.name}>{role.name}</option>)}
          </select>
        </Field>
        <Field label="Barva">
          <Input type="color" className="px-1 py-1" value={form.comment_color} onChange={(event) => setForm({ ...form, comment_color: event.target.value })} />
        </Field>
      </div>
      <Button type="submit" disabled={!roles.length}><UserPlus className="size-4" /> Přidat uživatele</Button>
    </form>
  )
}

function RolesCard({ roles, loading, error }: { roles: RoleRead[]; loading: boolean; error: string }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle className="text-lg">Role</CardTitle></CardHeader>
      <CardContent className="grid gap-3">
        {error && <StatusLine text={error} tone="error" />}
        <div className="flex flex-wrap gap-2">
          {roles.map((role) => (
            <Badge key={role.id} variant="outline" className="gap-1.5"><Shield className="size-3.5" /> {role.name} · {role.permissions.length}</Badge>
          ))}
          {!roles.length && <p className="text-sm text-muted-foreground">{loading ? 'Načítám role...' : 'Žádné role'}</p>}
        </div>
      </CardContent>
    </Card>
  )
}

function UsersTable({ users, loading, onDelete }: { users: UserRead[]; loading: boolean; onDelete: (id: string) => void }) {
  const sortedUsers = useMemo(() => [...users].sort((a, b) => a.username.localeCompare(b.username, 'cs-CZ')), [users])

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Účet</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Stav</TableHead>
          <TableHead>Poslední přihlášení</TableHead>
          <TableHead>Akce</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedUsers.map((user) => (
          <TableRow key={user.id}>
            <TableCell>
              <div className="flex items-center gap-2">
                <ColorSwatch color={user.comment_color} />
                <div>
                  <div className="font-medium">{user.display_name || user.username}</div>
                  <div className="text-xs text-muted-foreground">{user.username}</div>
                </div>
              </div>
            </TableCell>
            <TableCell>{user.role?.name ?? user.role_id}</TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                <Badge variant={user.active ? 'default' : 'secondary'}>{user.active ? 'Aktivní' : 'Vypnuto'}</Badge>
                {user.cannot_delete && <Badge variant="outline">Chráněný</Badge>}
              </div>
            </TableCell>
            <TableCell>{user.last_login_at ? formatDate(user.last_login_at) : '-'}</TableCell>
            <TableCell>
              <Button variant="destructive" size="icon-sm" disabled={user.cannot_delete} onClick={() => onDelete(user.id)} aria-label={`Smazat ${user.username}`}>
                <Trash2 className="size-3.5" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
        {!sortedUsers.length && <TableRow><TableCell colSpan={5} className="h-20 text-center text-muted-foreground">{loading ? 'Načítám uživatele...' : 'Žádní uživatelé'}</TableCell></TableRow>}
      </TableBody>
    </Table>
  )
}

function ColorSwatch({ color }: { color?: string | null }) {
  return <span className="size-3 rounded-full border" style={{ backgroundColor: color || 'transparent' }} aria-hidden="true" />
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
