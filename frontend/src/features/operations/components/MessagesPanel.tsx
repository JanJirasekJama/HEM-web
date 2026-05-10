import { useMemo, useState } from 'react'
import { Copy, Download, Mail, MessageCircle, Plus, RefreshCw, Save } from 'lucide-react'

import { exportUrl, queryString } from '@/features/operations/api'
import { useAbortableQuery, useApiMutation, useDebouncedValue } from '@/features/operations/hooks/useOperationsApi'
import type { Message, MessageComment, SendMessageEmailResponse } from '@/features/operations/types'
import { EmptyState, Field, FilterBar, InlineStatus, OperationPanel, ToolbarButton } from '@/features/operations/components/primitives'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const today = () => new Date().toISOString().slice(0, 10)

export function MessagesPanel() {
  const [dateFrom, setDateFrom] = useState(today())
  const [dateTo, setDateTo] = useState(today())
  const [text, setText] = useState('')
  const [messageDate, setMessageDate] = useState(today())
  const [content, setContent] = useState('')
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null)
  const [emailInfo, setEmailInfo] = useState('')
  const debouncedText = useDebouncedValue(text)
  const historyPath = useMemo(() => `/api/messages/history${queryString({ date_from: dateFrom, date_to: dateTo, text: debouncedText })}`, [dateFrom, dateTo, debouncedText])
  const history = useAbortableQuery<Message[]>(historyPath)
  const mutation = useApiMutation()

  const submitMessage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const saved = await mutation.mutate<Message>('/api/messages/daily', {
      method: 'POST',
      body: { message_date: messageDate, content_text: content, content_html: null },
    })
    setContent(saved.content_text)
    history.reload()
  }

  const copyToToday = async (message: Message) => {
    const copied = await mutation.mutate<Message>(`/api/messages/${message.id}/copy-to-today`, { method: 'POST', body: { today: today() } })
    setMessageDate(copied.message_date)
    setContent(copied.content_text)
    history.reload()
  }

  const sendEmail = async () => {
    const response = await mutation.mutate<SendMessageEmailResponse>('/api/messages/send-email', { method: 'POST', body: { message_date: messageDate, counts: {} } })
    setEmailInfo(`${response.status}: ${response.subject} (${response.queued_recipients.length})`)
  }

  return (
    <OperationPanel
      title="Vzkazy"
      description="Denní recepční zprávy, komentáře, kopírování na dnešek a export."
      actions={
        <>
          <ToolbarButton variant="outline" onClick={history.reload} aria-label="Obnovit vzkazy"><RefreshCw /></ToolbarButton>
          <ToolbarButton variant="outline" onClick={sendEmail}><Mail /> Odeslat</ToolbarButton>
        </>
      }
    >
      <form className="grid gap-3 md:grid-cols-[160px_1fr_auto]" onSubmit={submitMessage}>
        <Field label="Datum"><Input type="date" value={messageDate} onChange={(event) => setMessageDate(event.target.value)} /></Field>
        <Field label="Text vzkazu"><Textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="Důležité informace pro směnu" /></Field>
        <div className="flex items-end"><Button type="submit" disabled={mutation.loading}><Save /> Uložit</Button></div>
      </form>
      <InlineStatus loading={mutation.loading} error={mutation.error} saved={emailInfo} />

      <FilterBar>
        <Field label="Od"><Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></Field>
        <Field label="Do"><Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></Field>
        <Field label="Hledat"><Input value={text} onChange={(event) => setText(event.target.value)} placeholder="Text vzkazu" /></Field>
      </FilterBar>

      <div className="grid gap-3">
        {history.data?.map((message) => (
          <article key={message.id} className="rounded-md border p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="font-medium">{message.message_date}</h3>
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{message.content_text || 'Bez textu'}</p>
              </div>
              <div className="flex gap-2">
                <ToolbarButton variant="outline" onClick={() => setSelectedMessage(message)}><MessageCircle /> Komentář</ToolbarButton>
                <ToolbarButton variant="outline" onClick={() => copyToToday(message)}><Copy /> Dnes</ToolbarButton>
                <ToolbarButton variant="outline" onClick={() => window.open(exportUrl(`/api/messages/${message.id}/export.txt`), '_blank', 'noreferrer')}><Download /> Export</ToolbarButton>
              </div>
            </div>
          </article>
        ))}
        {!history.loading && !history.data?.length && <EmptyState>Žádné vzkazy pro zadané filtry.</EmptyState>}
        <InlineStatus loading={history.loading} error={history.error} />
      </div>

      <MessageCommentDialog
        message={selectedMessage}
        open={Boolean(selectedMessage)}
        onOpenChange={(open) => {
          if (!open) setSelectedMessage(null)
        }}
        onSaved={history.reload}
      />
    </OperationPanel>
  )
}

function MessageCommentDialog(props: { message: Message | null; open: boolean; onOpenChange: (open: boolean) => void; onSaved: () => void }) {
  const [comment, setComment] = useState('')
  const [color, setColor] = useState('#2563eb')
  const mutation = useApiMutation()

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!props.message) return
    await mutation.mutate<MessageComment>(`/api/messages/${props.message.id}/comments`, { method: 'POST', body: { content_text: comment, color } })
    setComment('')
    props.onSaved()
    props.onOpenChange(false)
  }

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Přidat komentář</DialogTitle></DialogHeader>
        <form className="space-y-3" onSubmit={submit}>
          <Field label="Komentář"><Textarea value={comment} onChange={(event) => setComment(event.target.value)} required /></Field>
          <Field label="Barva"><Input type="color" value={color} onChange={(event) => setColor(event.target.value)} /></Field>
          <InlineStatus loading={mutation.loading} error={mutation.error} />
          <DialogFooter><Button type="submit" disabled={mutation.loading || !comment.trim()}><Plus /> Přidat</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
