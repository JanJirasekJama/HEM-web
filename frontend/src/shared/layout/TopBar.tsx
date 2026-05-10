import { Bell, LogOut, Menu, RefreshCw } from 'lucide-react'

import type { ModuleCode, ModuleDefinition } from '@/shared/auth/permissions'
import type { ApiStatus, CurrentUser } from '@/shared/api'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

type TopBarProps = {
  activeModule: ModuleCode
  apiStatus: ApiStatus
  isRefreshing: boolean
  modules: ModuleDefinition[]
  notificationCount: number
  user: CurrentUser
  onModuleChange: (module: ModuleCode) => void
  onRefresh: () => void
  onLogout: () => void
}

export function TopBar({ activeModule, apiStatus, isRefreshing, modules, notificationCount, user, onModuleChange, onRefresh, onLogout }: TopBarProps) {
  const activeModuleDefinition = modules.find((module) => module.code === activeModule)
  const displayName = user.display_name || user.username

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 lg:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button type="button" variant="outline" size="icon" className="lg:hidden" aria-label="Otevřít moduly">
                <Menu className="size-4" aria-hidden="true" />
              </Button>
            }
          />
          <DropdownMenuContent className="w-56">
            <DropdownMenuLabel>Moduly</DropdownMenuLabel>
            {modules.map((module) => (
              <DropdownMenuItem key={module.code} onClick={() => onModuleChange(module.code)}>
                <module.icon className="size-4" />
                {module.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-normal">{activeModuleDefinition?.name ?? 'Dashboard'}</h1>
          <p className="truncate text-xs text-muted-foreground">{activeModuleDefinition?.metric ?? 'Provozní přehled'}</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <StatusBadge status={apiStatus} />
        <Badge variant={notificationCount > 0 ? 'default' : 'secondary'} className="hidden sm:inline-flex">
          <Bell className="size-3" aria-hidden="true" />
          {notificationCount}
        </Badge>
        <span className="hidden max-w-40 truncate text-sm text-muted-foreground md:inline">{displayName}</span>
        <Button type="button" variant="outline" size="icon" onClick={onRefresh} disabled={isRefreshing} aria-label="Obnovit">
          <RefreshCw className={isRefreshing ? 'size-4 animate-spin' : 'size-4'} aria-hidden="true" />
        </Button>
        <Button type="button" variant="outline" size="icon" onClick={onLogout} aria-label="Odhlásit">
          <LogOut className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </header>
  )
}
