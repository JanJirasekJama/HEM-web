import { DashboardShell } from '@/features/dashboard/DashboardShell'
import { AppStateProvider } from '@/shared/auth/AppState'

function App() {
  return (
    <AppStateProvider>
      <DashboardShell />
    </AppStateProvider>
  )
}

export default App
