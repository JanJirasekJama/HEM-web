import type { FormEvent } from 'react'
import { LogIn } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'

type LoginPanelProps = {
  username: string
  password: string
  error: string
  isSubmitting: boolean
  onUsernameChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function LoginPanel({ username, password, error, isSubmitting, onUsernameChange, onPasswordChange, onSubmit }: LoginPanelProps) {
  return (
    <div className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-4 py-10">
      <Card className="w-full max-w-sm rounded-md">
        <CardHeader>
          <CardTitle>Přihlášení</CardTitle>
          <CardDescription>HEM provozní konzole</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onSubmit}>
            <Input value={username} onChange={(event) => onUsernameChange(event.target.value)} placeholder="Uživatel" autoComplete="username" />
            <Input value={password} onChange={(event) => onPasswordChange(event.target.value)} placeholder="Heslo" type="password" autoComplete="current-password" />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Separator />
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              <LogIn className="size-4" aria-hidden="true" />
              {isSubmitting ? 'Přihlašuji' : 'Přihlásit'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
