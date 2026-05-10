import { Banknote, Boxes, ClipboardList, MessageSquareText } from 'lucide-react'

import type { CurrentUser } from '@/shared/api'
import { CashPanel } from '@/features/operations/components/CashPanel'
import { InventoryPanel } from '@/features/operations/components/InventoryPanel'
import { MessagesPanel } from '@/features/operations/components/MessagesPanel'
import { TasksPanel } from '@/features/operations/components/TasksPanel'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function OperationsWorkspace(props: { currentUser?: CurrentUser | null }) {
  return (
    <section className="space-y-4">
      <Tabs defaultValue="messages">
        <TabsList className="flex w-full flex-wrap justify-start">
          <TabsTrigger value="messages"><MessageSquareText /> Vzkazy</TabsTrigger>
          <TabsTrigger value="tasks"><ClipboardList /> Úkoly</TabsTrigger>
          <TabsTrigger value="cash"><Banknote /> Peněžní deník</TabsTrigger>
          <TabsTrigger value="inventory"><Boxes /> Inventory</TabsTrigger>
        </TabsList>
        <TabsContent value="messages"><MessagesPanel /></TabsContent>
        <TabsContent value="tasks"><TasksPanel /></TabsContent>
        <TabsContent value="cash"><CashPanel userId={props.currentUser?.id} /></TabsContent>
        <TabsContent value="inventory"><InventoryPanel /></TabsContent>
      </Tabs>
    </section>
  )
}

export { CashPanel, InventoryPanel, MessagesPanel, TasksPanel }
