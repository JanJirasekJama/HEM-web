import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'

import { modules } from '@/features/modules'
import { apiGet, login, logout, type ApiStatus, type CurrentUser, type DashboardResponse, type NotificationItem } from '@/shared/api'
import { AppStateContext } from '@/shared/auth/AppStateContext'
import type { AppState, LoginFormState } from '@/shared/auth/appStateTypes'
import { canAccessPermission, getPermissionsForRole, getRoleName, type ModuleCode, type PermissionState } from '@/shared/auth/permissions'

const CSRF_STORAGE_KEY = 'hem-csrf'

export function AppStateProvider({ children }: { children: ReactNode }) {
  const state = useAppStateController()

  return <AppStateContext.Provider value={state}>{children}</AppStateContext.Provider>
}

function useAppStateController(): AppState {
  const [activeModule, setActiveModule] = useState<ModuleCode>('dashboard')
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [csrfToken, setCsrfToken] = useState(() => sessionStorage.getItem(CSRF_STORAGE_KEY) || '')
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [loginForm, setLoginForm] = useState<LoginFormState>({ username: 'admin', password: '', error: '', isSubmitting: false })
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const refreshControllerRef = useRef<AbortController | null>(null)
  const loginControllerRef = useRef<AbortController | null>(null)
  const logoutControllerRef = useRef<AbortController | null>(null)

  const roleName = getRoleName(user?.role?.name ?? dashboard?.current_user.role)
  const rolePermissions = useMemo(() => getPermissionsForRole(roleName), [roleName])
  const permissions = useMemo<PermissionState>(
    () => ({
      roleName,
      permissions: rolePermissions,
      can: (permission: string) => canAccessPermission(rolePermissions, permission),
    }),
    [roleName, rolePermissions],
  )

  const availableModules = useMemo(() => modules.filter((module) => permissions.can(module.permission)), [permissions])
  const effectiveActiveModule = useMemo(
    () => (availableModules.some((module) => module.code === activeModule) ? activeModule : availableModules[0]?.code ?? 'dashboard'),
    [activeModule, availableModules],
  )

  const refresh = useCallback(() => {
    refreshControllerRef.current?.abort()
    const controller = new AbortController()
    refreshControllerRef.current = controller
    setIsRefreshing(true)

    void Promise.all([
      apiGet<{ status: string }>('/api/health', { signal: controller.signal })
        .then(() => setApiStatus('ok'))
        .catch((error: unknown) => {
          if (!controller.signal.aborted && !isAbortError(error)) setApiStatus('offline')
        }),
      apiGet<CurrentUser>('/api/auth/me', { signal: controller.signal })
        .then(async (currentUser) => {
          setUser(currentUser)
          const nextDashboard = await apiGet<DashboardResponse>('/api/dashboard', { signal: controller.signal })
          setDashboard(nextDashboard)
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || isAbortError(error)) return
          setUser(null)
          setDashboard(null)
          setNotifications([])
          setActiveModule('dashboard')
        }),
    ]).finally(() => {
      if (!controller.signal.aborted) setIsRefreshing(false)
    })
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(refresh, 0)

    return () => {
      window.clearTimeout(timeout)
      refreshControllerRef.current?.abort()
      loginControllerRef.current?.abort()
      logoutControllerRef.current?.abort()
    }
  }, [refresh])

  useEffect(() => {
    if (!user) return

    const controller = new AbortController()
    const refreshNotifications = () => {
      apiGet<NotificationItem[]>('/api/notifications', { signal: controller.signal })
        .then(setNotifications)
        .catch((error: unknown) => {
          if (!controller.signal.aborted && !isAbortError(error)) setNotifications([])
        })
    }

    refreshNotifications()
    const interval = window.setInterval(refreshNotifications, 30000)
    const events = new EventSource('/api/events', { withCredentials: true })
    events.addEventListener('ready', refreshNotifications)
    events.addEventListener('ping', refreshNotifications)
    events.onerror = () => undefined

    return () => {
      controller.abort()
      window.clearInterval(interval)
      events.close()
    }
  }, [user])

  const setLoginUsername = useCallback((value: string) => {
    setLoginForm((current) => ({ ...current, username: value }))
  }, [])

  const setLoginPassword = useCallback((value: string) => {
    setLoginForm((current) => ({ ...current, password: value }))
  }, [])

  const submitLogin = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    loginControllerRef.current?.abort()
    const controller = new AbortController()
    loginControllerRef.current = controller

    setLoginForm((current) => ({ ...current, error: '', isSubmitting: true }))

    void login(loginForm.username, loginForm.password, { signal: controller.signal })
      .then(async (result) => {
        sessionStorage.setItem(CSRF_STORAGE_KEY, result.csrf_token)
        setCsrfToken(result.csrf_token)
        setUser(result.user)
        setActiveModule('dashboard')
        setLoginForm((current) => ({ ...current, password: '', error: '' }))
        setDashboard(await apiGet<DashboardResponse>('/api/dashboard', { signal: controller.signal }))
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted && !isAbortError(error)) {
          setLoginForm((current) => ({ ...current, error: 'Zkontrolujte jméno a heslo.' }))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoginForm((current) => ({ ...current, isSubmitting: false }))
        }
      })
  }, [loginForm.password, loginForm.username])

  const submitLogout = useCallback(() => {
    logoutControllerRef.current?.abort()
    const controller = new AbortController()
    logoutControllerRef.current = controller

    const nextCsrfToken = csrfToken
    void Promise.resolve(nextCsrfToken ? logout(nextCsrfToken, { signal: controller.signal }) : undefined).finally(() => {
      if (controller.signal.aborted) return
      sessionStorage.removeItem(CSRF_STORAGE_KEY)
      setCsrfToken('')
      setUser(null)
      setDashboard(null)
      setNotifications([])
      setActiveModule('dashboard')
    })
  }, [csrfToken])

  return {
    activeModule: effectiveActiveModule,
    apiStatus,
    csrfToken,
    dashboard,
    loginForm,
    modules: availableModules,
    notifications,
    permissions,
    user,
    isAuthenticated: Boolean(user),
    isRefreshing,
    setActiveModule,
    setLoginUsername,
    setLoginPassword,
    submitLogin,
    submitLogout,
    refresh,
  }
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === 'AbortError'
}
