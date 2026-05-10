import type { FormEvent } from 'react'

import type { modules } from '@/features/modules'
import type { ApiStatus, CurrentUser, DashboardResponse, NotificationItem } from '@/shared/api'
import type { ModuleCode, PermissionState } from '@/shared/auth/permissions'

export type LoginFormState = {
  username: string
  password: string
  error: string
  isSubmitting: boolean
}

export type AppState = {
  activeModule: ModuleCode
  apiStatus: ApiStatus
  csrfToken: string
  dashboard: DashboardResponse | null
  loginForm: LoginFormState
  modules: typeof modules
  notifications: NotificationItem[]
  permissions: PermissionState
  user: CurrentUser | null
  isAuthenticated: boolean
  isRefreshing: boolean
  setActiveModule: (module: ModuleCode) => void
  setLoginUsername: (value: string) => void
  setLoginPassword: (value: string) => void
  submitLogin: (event: FormEvent<HTMLFormElement>) => void
  submitLogout: () => void
  refresh: () => void
}
