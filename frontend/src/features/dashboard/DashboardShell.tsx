import { useEffect, useState } from 'react'
import { Bell, LogOut, RefreshCw, ShieldCheck } from 'lucide-react'

import { modules } from '@/features/modules'
import { useNotifications } from '@/features/notifications/useNotifications'
import { apiGet, login, logout, type ApiStatus, type CurrentUser, type DashboardResponse } from '@/shared/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'

export function DashboardShell() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [csrfToken, setCsrfToken] = useState<string>(() => sessionStorage.getItem('hem-csrf') || '')
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const notifications = useNotifications(Boolean(user))

  const refresh = () => {
    apiGet<{ status: string }>('/api/health')
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('offline'))

    apiGet<CurrentUser>('/api/auth/me')
      .then((current) => {
        setUser(current)
        return apiGet<DashboardResponse>('/api/dashboard')
      })
      .then(setDashboard)
      .catch(() => {
        setUser(null)
        setDashboard(null)
      })
  }

  useEffect(refresh, [])

  const submitLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoginError('')
    try {
      const result = await login(username, password)
      sessionStorage.setItem('hem-csrf', result.csrf_token)
      setCsrfToken(result.csrf_token)
      setUser(result.user)
      setPassword('')
      setDashboard(await apiGet<DashboardResponse>('/api/dashboard'))
    } catch {
      setLoginError('Zkontrolujte jméno a heslo.')
    }
  }

  const submitLogout = async () => {
    if (csrfToken) await logout(csrfToken).catch(() => undefined)
    sessionStorage.removeItem('hem-csrf')
    setCsrfToken('')
    setUser(null)
    setDashboard(null)
  }

  return (
    <main className="min-h-svh bg-background">
      <section className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border bg-card">
              <ShieldCheck className="size-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">HEM</h1>
              <p className="text-sm text-muted-foreground">Konsolidovaná provozní aplikace</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={apiStatus === 'ok' ? 'default' : 'secondary'}>{apiStatus === 'ok' ? 'Backend online' : apiStatus === 'offline' ? 'Offline' : 'Kontrola'}</Badge>
            <Button variant="outline" size="icon" onClick={refresh} aria-label="Obnovit">
              <RefreshCw className="size-4" aria-hidden="true" />
            </Button>
            {user && (
              <Button variant="outline" size="icon" onClick={submitLogout} aria-label="Odhlásit">
                <LogOut className="size-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        </header>

        {!user ? (
          <LoginPanel username={username} password={password} loginError={loginError} onUsername={setUsername} onPassword={setPassword} onSubmit={submitLogin} />
        ) : (
          <>
            <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
              <Card className="rounded-md">
                <CardHeader>
                  <CardTitle className="text-lg">Dnes</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Vzkazy" value={dashboard?.messages_today ?? 0} />
                  <Metric label="Nesplněné úkoly" value={dashboard?.open_tasks_today ?? 0} />
                  <Metric label="Pokoje čekají" value={dashboard?.housekeeping.waiting ?? 0} />
                  <Metric label="Splatnosti" value={dashboard?.invoices.due_or_overdue ?? 0} />
                </CardContent>
              </Card>
              <Card className="rounded-md">
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-lg">Oznámení</CardTitle>
                  <Bell className="size-4 text-muted-foreground" aria-hidden="true" />
                </CardHeader>
                <CardContent className="space-y-3">
                  {notifications.slice(0, 3).map((item) => (
                    <div key={item.id} className="rounded-md border p-3">
                      <div className="text-sm font-medium">{item.title}</div>
                      {item.body && <div className="text-sm text-muted-foreground">{item.body}</div>}
                    </div>
                  ))}
                  {!notifications.length && <p className="text-sm text-muted-foreground">Žádná nová oznámení</p>}
                </CardContent>
              </Card>
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {modules.map((module) => {
                const Icon = module.icon
                return (
                  <Card key={module.code} className="rounded-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-base">{module.name}</CardTitle>
                      <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">{module.metric}</p>
                    </CardContent>
                  </Card>
                )
              })}
            </section>
          </>
        )}
      </section>
    </main>
  )
}

function LoginPanel(props: {
  username: string
  password: string
  loginError: string
  onUsername: (value: string) => void
  onPassword: (value: string) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
}) {
  return (
    <Card className="max-w-md rounded-md">
      <CardHeader>
        <CardTitle>Přihlášení</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={props.onSubmit}>
          <Input value={props.username} onChange={(event) => props.onUsername(event.target.value)} placeholder="Uživatel" autoComplete="username" />
          <Input value={props.password} onChange={(event) => props.onPassword(event.target.value)} placeholder="Heslo" type="password" autoComplete="current-password" />
          {props.loginError && <p className="text-sm text-destructive">{props.loginError}</p>}
          <Separator />
          <Button type="submit" className="w-full">Přihlásit</Button>
        </form>
      </CardContent>
    </Card>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-semibold tracking-normal">{value}</div>
    </div>
  )
}

