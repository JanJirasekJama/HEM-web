import { useEffect, useState } from 'react'
import { Bell, ClipboardList, Hotel, ReceiptText, ShieldCheck } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

const modules = [
  { name: 'Recepce', description: 'Vzkazy, úkoly, směny a hotovost', icon: ClipboardList },
  { name: 'Fakturace', description: 'Zálohové faktury, platby a exporty', icon: ReceiptText },
  { name: 'Housekeeping', description: 'Úklidy, fotky, revize a prádelna', icon: Hotel },
  { name: 'Notifikace', description: 'Redis fronta, SSE a centrum oznámení', icon: Bell },
]

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'offline'>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        setApiStatus(response.ok ? 'ok' : 'offline')
      })
      .catch(() => setApiStatus('offline'))
  }, [])

  const statusLabel =
    apiStatus === 'ok' ? 'Backend online' : apiStatus === 'offline' ? 'Offline režim' : 'Ověřuji API'

  return (
    <main className="min-h-svh bg-background">
      <section className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border bg-card">
              <ShieldCheck className="size-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">HEM</h1>
              <p className="text-sm text-muted-foreground">Konsolidovaná provozní aplikace</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={apiStatus === 'ok' ? 'default' : 'secondary'}>{statusLabel}</Badge>
            <Button variant="outline" size="sm">Přihlášení</Button>
          </div>
        </header>

        <Separator />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {modules.map((module) => {
            const Icon = module.icon
            return (
              <Card key={module.name} className="rounded-md">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-base">{module.name}</CardTitle>
                  <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{module.description}</p>
                </CardContent>
              </Card>
            )
          })}
        </section>
      </section>
    </main>
  )
}

export default App
