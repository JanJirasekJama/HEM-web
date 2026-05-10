import { ShieldCheck } from 'lucide-react'

import type { ModuleCode, ModuleDefinition } from '@/shared/auth/permissions'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'

type SidebarNavProps = {
  activeModule: ModuleCode
  modules: ModuleDefinition[]
  roleName: string
  onModuleChange: (module: ModuleCode) => void
}

export function SidebarNav({ activeModule, modules, roleName, onModuleChange }: SidebarNavProps) {
  return (
    <aside className="hidden min-h-svh w-64 shrink-0 border-r bg-sidebar text-sidebar-foreground lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-3 border-b px-4">
        <div className="flex size-9 items-center justify-center rounded-md border bg-background">
          <ShieldCheck className="size-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-lg font-semibold leading-tight">HEM</div>
          <div className="truncate text-xs text-muted-foreground">{roleName}</div>
        </div>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <nav className="grid gap-1 p-3" aria-label="Moduly">
          {modules.map((module) => {
            const Icon = module.icon
            const isActive = activeModule === module.code

            return (
              <Button
                key={module.code}
                type="button"
                variant={isActive ? 'secondary' : 'ghost'}
                className={cn('h-10 justify-start gap-2 rounded-md px-3', isActive && 'bg-sidebar-accent text-sidebar-accent-foreground')}
                onClick={() => onModuleChange(module.code)}
              >
                <Icon className="size-4" />
                <span className="truncate">{module.name}</span>
              </Button>
            )
          })}
        </nav>
      </ScrollArea>
    </aside>
  )
}
