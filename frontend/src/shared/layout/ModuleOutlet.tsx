import type { ModuleDefinition } from '@/shared/auth/permissions'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function ModuleOutlet({ module }: { module: ModuleDefinition }) {
  if (module.component) {
    const ModuleComponent = module.component
    return <ModuleComponent />
  }

  const Icon = module.icon

  return (
    <Card className="rounded-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>{module.name}</CardTitle>
        <Icon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{module.metric}</p>
      </CardContent>
    </Card>
  )
}
