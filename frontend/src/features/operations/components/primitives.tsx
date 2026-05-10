import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export function OperationPanel(props: { title: string; description: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <Card className="rounded-md">
      <CardHeader className="gap-3 md:flex md:flex-row md:items-center md:justify-between">
        <div>
          <CardTitle className="text-lg">{props.title}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">{props.description}</p>
        </div>
        {props.actions && <div className="flex flex-wrap items-center gap-2">{props.actions}</div>}
      </CardHeader>
      <CardContent className="space-y-4">{props.children}</CardContent>
    </Card>
  )
}

export function Field(props: { label: string; children: ReactNode; className?: string }) {
  return (
    <label className={cn('grid gap-1.5 text-sm font-medium', props.className)}>
      <span>{props.label}</span>
      {props.children}
    </label>
  )
}

export function NativeSelect(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        'h-8 w-full rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50',
        props.className,
      )}
    />
  )
}

export function FilterBar(props: { children: ReactNode }) {
  return <div className="grid gap-3 rounded-md border bg-muted/20 p-3 md:grid-cols-4">{props.children}</div>
}

export function EmptyState(props: { children: ReactNode }) {
  return <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">{props.children}</div>
}

export function InlineStatus(props: { error?: string; loading?: boolean; saved?: string }) {
  if (props.loading) return <Badge variant="secondary">Pracuji...</Badge>
  if (props.error) return <p className="text-sm text-destructive">{props.error}</p>
  if (props.saved) return <p className="text-sm text-muted-foreground">{props.saved}</p>
  return null
}

export function NumberInput({ onValue, ...props }: Omit<React.ComponentProps<typeof Input>, 'type' | 'onChange'> & { onValue: (value: number | null) => void }) {
  return (
    <Input
      {...props}
      type="number"
      step="0.01"
      onChange={(event) => onValue(event.target.value === '' ? null : Number(event.target.value))}
    />
  )
}

export function ToolbarButton(props: React.ComponentProps<typeof Button>) {
  return <Button size="sm" {...props} />
}
