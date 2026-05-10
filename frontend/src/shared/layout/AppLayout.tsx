import type { AppState } from '@/shared/auth/appStateTypes'
import { DashboardOverview } from '@/shared/layout/DashboardOverview'
import { LoginPanel } from '@/shared/layout/LoginPanel'
import { ModuleOutlet } from '@/shared/layout/ModuleOutlet'
import { NotificationsPanel } from '@/shared/layout/NotificationsPanel'
import { SidebarNav } from '@/shared/layout/SidebarNav'
import { TopBar } from '@/shared/layout/TopBar'

export function AppLayout(state: AppState) {
  if (!state.isAuthenticated || !state.user) {
    return (
      <main className="min-h-svh bg-background">
        <LoginPanel
          username={state.loginForm.username}
          password={state.loginForm.password}
          error={state.loginForm.error}
          isSubmitting={state.loginForm.isSubmitting}
          onUsernameChange={state.setLoginUsername}
          onPasswordChange={state.setLoginPassword}
          onSubmit={state.submitLogin}
        />
      </main>
    )
  }

  const activeModule = state.modules.find((module) => module.code === state.activeModule) ?? state.modules[0]

  return (
    <main className="min-h-svh bg-background">
      <div className="flex min-h-svh">
        <SidebarNav activeModule={state.activeModule} modules={state.modules} roleName={state.permissions.roleName} onModuleChange={state.setActiveModule} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            activeModule={state.activeModule}
            apiStatus={state.apiStatus}
            isRefreshing={state.isRefreshing}
            modules={state.modules}
            notificationCount={state.notifications.length}
            user={state.user}
            onModuleChange={state.setActiveModule}
            onRefresh={state.refresh}
            onLogout={state.submitLogout}
          />
          <div className="grid gap-4 px-4 py-4 lg:px-6">
            {state.activeModule === 'dashboard' ? (
              <>
                <DashboardOverview dashboard={state.dashboard} />
                <NotificationsPanel notifications={state.notifications} />
              </>
            ) : activeModule ? (
              <ModuleOutlet module={activeModule} currentUser={state.user} permissions={state.permissions} />
            ) : null}
          </div>
        </div>
      </div>
    </main>
  )
}
