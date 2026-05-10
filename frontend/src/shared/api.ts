export type ApiStatus = 'checking' | 'ok' | 'offline'

export type CurrentUser = {
  id: string
  username: string
  display_name?: string | null
  role?: { name: string } | null
}

export type DashboardResponse = {
  current_user: { username: string; display_name?: string | null; role: string }
  messages_today: number
  open_tasks_today: number
  open_task_list: Array<{ id: string; title: string; priority: string }>
  cash: { missing_morning_cash: boolean; missing_evening_cash: boolean; yesterday_cash_end?: number | null }
  invoices: { due_or_overdue: number }
  housekeeping: { waiting: number; cleaning: number; done: number; laundry_active: number; open_revisions: number }
}

export type NotificationItem = {
  id: string
  title: string
  body?: string | null
  severity: string
  created_at: string
  read_at?: string | null
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: 'include' })
  if (!response.ok) throw new ApiError(response.status, await response.text())
  return response.json() as Promise<T>
}

export async function login(username: string, password: string): Promise<{ csrf_token: string; user: CurrentUser }> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) throw new ApiError(response.status, 'Přihlášení se nepodařilo')
  return response.json()
}

export async function logout(csrfToken: string): Promise<void> {
  await fetch('/api/auth/logout', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
    credentials: 'include',
  })
}
