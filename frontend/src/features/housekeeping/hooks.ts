import { useCallback, useEffect, useMemo, useState } from 'react'

import type {
  AssignmentCreateDraft,
  AssignmentPhoto,
  HousekeepingAssignment,
  HousekeepingMutationName,
  HousekeepingWorkspaceData,
  LaundryTask,
  MinibarEntry,
  MonthlyWorkReport,
  RevisionCreateDraft,
  RevisionTask,
} from './types'

type CatalogResponse = {
  hotel_rooms?: Array<{ id: string; label: string; name?: string }>
  housekeeping_minibar_items?: Array<{ id: string; name: string; label?: string }>
  photo_task_types?: Array<{ id: string; name: string; label?: string }>
}

type HousekeepingStateResponse = Pick<HousekeepingWorkspaceData, 'assignments' | 'revisions' | 'laundry'>

type HousekeepingLoadOptions = {
  loadHistory?: boolean
  loadReport?: boolean
}

const monthKey = new Date().toISOString().slice(0, 7)

const emptyWorkspaceData: HousekeepingWorkspaceData = {
  rooms: [],
  minibarItems: [],
  photoTaskTypes: [],
  assignments: [],
  revisions: [],
  laundry: [],
  history: [],
  report: { month: monthKey, housekeepers: {} },
}

export function useHousekeepingWorkspace(initialData?: HousekeepingWorkspaceData, options: HousekeepingLoadOptions = {}) {
  const [data, setData] = useState<HousekeepingWorkspaceData>(initialData ?? emptyWorkspaceData)
  const [loading, setLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Partial<Record<HousekeepingMutationName, boolean>>>({})
  const loadHistory = options.loadHistory ?? false
  const loadReport = options.loadReport ?? false

  const csrfToken = useMemo(() => sessionStorage.getItem('hem-csrf') || '', [])

  const withPending = useCallback(async <T,>(name: HousekeepingMutationName, action: () => Promise<T>) => {
    setPending((current) => ({ ...current, [name]: true }))
    try {
      return await action()
    } finally {
      setPending((current) => ({ ...current, [name]: false }))
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      apiJson<CatalogResponse>('/api/catalog/housekeeping?active_only=true', { signal: controller.signal }),
      apiJson<HousekeepingStateResponse>('/api/housekeeping/state', { signal: controller.signal }),
      loadHistory ? apiJson<AssignmentHistoryRowResponse[]>('/api/housekeeping/history?month=' + monthKey, { signal: controller.signal }) : Promise.resolve([]),
      loadReport ? apiJson<MonthlyWorkReport>('/api/housekeeping/reports/monthly-work?month=' + monthKey, { signal: controller.signal }) : Promise.resolve(emptyWorkspaceData.report),
    ])
      .then(([catalog, state, history, report]) => {
        if (controller.signal.aborted) return
        setData((current) => ({
          ...current,
          rooms: catalog.hotel_rooms ? catalog.hotel_rooms.map((room) => ({ id: room.id, label: room.label || room.name || room.id })) : current.rooms,
          minibarItems: catalog.housekeeping_minibar_items ?? current.minibarItems,
          photoTaskTypes: catalog.photo_task_types ?? current.photoTaskTypes,
          assignments: state.assignments,
          revisions: state.revisions,
          laundry: state.laundry,
          history,
          report,
        }))
        setError(null)
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(normalizeError(caught))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [loadHistory, loadReport])

  const createAssignments = useCallback(
    (draft: AssignmentCreateDraft) =>
      withPending('createAssignments', async () => {
        const created = await apiJson<HousekeepingAssignment[]>('/api/housekeeping/assignments', {
          method: 'POST',
          csrfToken,
          body: JSON.stringify({
            room_ids: draft.roomIds,
            work_type: draft.workType,
            priority: draft.priority,
            reception_note: draft.receptionNote || null,
            required_photo_type_ids: draft.requiredPhotoTypeIds,
          }),
        })
        const enriched = created.map((assignment) => enrichAssignment(assignment, draft.requiredPhotoTypeIds, data.photoTaskTypes))
        setData((current) => ({ ...current, assignments: [...enriched, ...current.assignments] }))
      }),
    [csrfToken, data.photoTaskTypes, withPending],
  )

  const patchAssignment = useCallback(
    (name: Extract<HousekeepingMutationName, 'startAssignment' | 'pauseAssignment' | 'resumeAssignment' | 'finishAssignment'>, assignmentId: string, action: 'start' | 'pause' | 'resume' | 'finish') =>
      withPending(name, async () => {
        const updated = await apiJson<HousekeepingAssignment>('/api/housekeeping/assignments/' + assignmentId + '/' + action, { method: 'PATCH', csrfToken })
        setData((current) => ({
          ...current,
          assignments: current.assignments.map((assignment) => (assignment.id === assignmentId ? { ...assignment, ...updated } : assignment)),
        }))
      }),
    [csrfToken, withPending],
  )

  const uploadAssignmentPhoto = useCallback(
    (assignmentId: string, file: File, taskLabel?: string, photoTaskTypeId?: string) =>
      withPending('uploadAssignmentPhoto', async () => {
        const form = new FormData()
        form.append('file', file)
        if (taskLabel) form.append('task_label', taskLabel)
        if (photoTaskTypeId) form.append('photo_task_type_id', photoTaskTypeId)
        const photo = await apiJson<AssignmentPhoto>('/api/housekeeping/assignments/' + assignmentId + '/photos', { method: 'POST', csrfToken, body: form })
        setData((current) => ({
          ...current,
          assignments: current.assignments.map((assignment) =>
            assignment.id === assignmentId
              ? {
                  ...assignment,
                  photos: [...assignment.photos, photo],
                  required_photos: assignment.required_photos.map((required) => (required.photo_task_type_id === photoTaskTypeId ? { ...required, uploaded: true } : required)),
                }
              : assignment,
          ),
        }))
      }),
    [csrfToken, withPending],
  )

  const addMinibarEntry = useCallback(
    (assignmentId: string, itemId: string, quantity: number) =>
      withPending('addMinibarEntry', async () => {
        const entry = await apiJson<MinibarEntry>('/api/housekeeping/assignments/' + assignmentId + '/minibar', {
          method: 'POST',
          csrfToken,
          body: JSON.stringify({ item_id: itemId, quantity }),
        })
        setData((current) => ({
          ...current,
          assignments: current.assignments.map((assignment) => (assignment.id === assignmentId ? { ...assignment, minibar_entries: [...assignment.minibar_entries, entry] } : assignment)),
        }))
      }),
    [csrfToken, withPending],
  )

  const createRevision = useCallback(
    (draft: RevisionCreateDraft) =>
      withPending('createRevision', async () => {
        const revision = await apiJson<RevisionTask>('/api/housekeeping/revisions', { method: 'POST', csrfToken, body: JSON.stringify({ location: draft.location, text: draft.text }) })
        setData((current) => ({ ...current, revisions: [revision, ...current.revisions] }))
      }),
    [csrfToken, withPending],
  )

  const completeRevision = useCallback(
    (revisionId: string, note: string, files: File[]) =>
      withPending('completeRevision', async () => {
        const form = new FormData()
        if (note) form.append('note', note)
        files.forEach((file) => form.append('files', file))
        const revision = await apiJson<RevisionTask>('/api/housekeeping/revisions/' + revisionId + '/complete', { method: 'PATCH', csrfToken, body: form })
        setData((current) => ({ ...current, revisions: current.revisions.map((item) => (item.id === revisionId ? revision : item)) }))
      }),
    [csrfToken, withPending],
  )

  const createLaundry = useCallback(
    () =>
      withPending('createLaundry', async () => {
        const laundry = await apiJson<LaundryTask>('/api/housekeeping/laundry', { method: 'POST', csrfToken })
        setData((current) => ({ ...current, laundry: [{ ...laundry, photo_uploaded: false }, ...current.laundry] }))
      }),
    [csrfToken, withPending],
  )

  const acceptLaundry = useCallback(
    (laundryId: string) =>
      withPending('acceptLaundry', async () => {
        const laundry = await apiJson<LaundryTask>('/api/housekeeping/laundry/' + laundryId + '/accept', { method: 'PATCH', csrfToken })
        setData((current) => ({ ...current, laundry: current.laundry.map((item) => (item.id === laundryId ? { ...item, ...laundry } : item)) }))
      }),
    [csrfToken, withPending],
  )

  const uploadLaundryPhoto = useCallback(
    (laundryId: string, file: File) =>
      withPending('uploadLaundryPhoto', async () => {
        const form = new FormData()
        form.append('file', file)
        await apiJson('/api/housekeeping/laundry/' + laundryId + '/photos', { method: 'POST', csrfToken, body: form })
        setData((current) => ({ ...current, laundry: current.laundry.map((item) => (item.id === laundryId ? { ...item, photo_uploaded: true } : item)) }))
      }),
    [csrfToken, withPending],
  )

  const finishLaundry = useCallback(
    (laundryId: string) =>
      withPending('finishLaundry', async () => {
        const laundry = await apiJson<LaundryTask>('/api/housekeeping/laundry/' + laundryId + '/done', { method: 'PATCH', csrfToken })
        setData((current) => ({ ...current, laundry: current.laundry.map((item) => (item.id === laundryId ? { ...item, ...laundry, photo_uploaded: item.photo_uploaded } : item)) }))
      }),
    [csrfToken, withPending],
  )

  return {
    data,
    loading,
    error,
    pending,
    actions: {
      createAssignments,
      startAssignment: (assignmentId: string) => patchAssignment('startAssignment', assignmentId, 'start'),
      pauseAssignment: (assignmentId: string) => patchAssignment('pauseAssignment', assignmentId, 'pause'),
      resumeAssignment: (assignmentId: string) => patchAssignment('resumeAssignment', assignmentId, 'resume'),
      finishAssignment: (assignmentId: string) => patchAssignment('finishAssignment', assignmentId, 'finish'),
      uploadAssignmentPhoto,
      addMinibarEntry,
      createRevision,
      completeRevision,
      createLaundry,
      acceptLaundry,
      uploadLaundryPhoto,
      finishLaundry,
    },
  }
}

type AssignmentHistoryRowResponse = HousekeepingWorkspaceData['history'][number]

async function apiJson<T = unknown>(path: string, init: (RequestInit & { csrfToken?: string }) = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (init.csrfToken) headers.set('X-CSRF-Token', init.csrfToken)
  const response = await fetch(path, { ...init, headers, credentials: 'include' })
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}

function normalizeError(caught: unknown) {
  return caught instanceof Error && caught.name !== 'AbortError' && caught.message ? caught.message : 'Housekeeping data se nepodařilo načíst.'
}

function enrichAssignment(assignment: HousekeepingAssignment, requiredPhotoTypeIds: string[], photoTypes: Array<{ id: string; name: string }>): HousekeepingAssignment {
  return {
    ...assignment,
    required_photos:
      assignment.required_photos ||
      requiredPhotoTypeIds.map((photoTypeId) => {
        const photoType = photoTypes.find((item) => item.id === photoTypeId)
        return { id: assignment.id + '-' + photoTypeId, photo_task_type_id: photoTypeId, task_label_snapshot: photoType?.name || photoTypeId, uploaded: false }
      }),
    photos: assignment.photos || [],
    minibar_entries: assignment.minibar_entries || [],
  }
}
