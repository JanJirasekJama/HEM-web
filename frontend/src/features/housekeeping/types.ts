export type HousekeepingRole = 'reception' | 'housekeeper'

export type HousekeepingCapabilities = {
  viewHistory: boolean
  viewReport: boolean
  createAssignments: boolean
  workAssignments: boolean
  uploadAssignmentPhotos: boolean
  addMinibarEntries: boolean
  createRevisions: boolean
  completeRevisions: boolean
  createLaundry: boolean
  workLaundry: boolean
}

export type AssignmentStatus = 'Prideleno' | 'Uklizi se' | 'Pozastaveno' | 'Hotovo'

export type CatalogItem = {
  id: string
  name: string
  label?: string
}

export type HotelRoom = {
  id: string
  label: string
}

export type RequiredPhoto = {
  id: string
  photo_task_type_id: string
  task_label_snapshot: string
  uploaded: boolean
}

export type AssignmentPhoto = {
  id: string
  task_label?: string | null
  photo_task_type_id?: string | null
  public_url?: string | null
}

export type MinibarEntry = {
  id: string
  item_id: string
  item_name_snapshot: string
  quantity: number
}

export type HousekeepingAssignment = {
  id: string
  room_id: string
  room_label_snapshot: string
  work_type: string
  priority: string
  reception_note?: string | null
  status: AssignmentStatus
  paused_seconds: number
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  required_photos: RequiredPhoto[]
  photos: AssignmentPhoto[]
  minibar_entries: MinibarEntry[]
}

export type RevisionTask = {
  id: string
  location: string
  text: string
  status: 'open' | 'done'
  completion_note?: string | null
  created_at: string
  completed_at?: string | null
}

export type LaundryTask = {
  id: string
  status: 'open' | 'accepted' | 'done'
  created_at: string
  accepted_at?: string | null
  done_at?: string | null
  photo_uploaded: boolean
}

export type AssignmentHistoryRow = {
  id: string
  assignment_id: string
  room_label_snapshot: string
  work_type: string
  priority: string
  housekeeper_username_snapshot?: string | null
  finished_at: string
  duration_seconds?: number | null
}

export type MonthlyWorkReport = {
  month: string
  housekeepers: Record<string, { assignment_count: number; revision_count: number; laundry_count: number }>
}

export type HousekeepingWorkspaceData = {
  rooms: HotelRoom[]
  minibarItems: CatalogItem[]
  photoTaskTypes: CatalogItem[]
  assignments: HousekeepingAssignment[]
  revisions: RevisionTask[]
  laundry: LaundryTask[]
  history: AssignmentHistoryRow[]
  report: MonthlyWorkReport
}

export type AssignmentCreateDraft = {
  roomIds: string[]
  workType: string
  priority: string
  receptionNote: string
  requiredPhotoTypeIds: string[]
}

export type RevisionCreateDraft = {
  location: string
  text: string
}

export type HousekeepingMutationName =
  | 'createAssignments'
  | 'startAssignment'
  | 'pauseAssignment'
  | 'resumeAssignment'
  | 'finishAssignment'
  | 'uploadAssignmentPhoto'
  | 'addMinibarEntry'
  | 'createRevision'
  | 'completeRevision'
  | 'createLaundry'
  | 'acceptLaundry'
  | 'uploadLaundryPhoto'
  | 'finishLaundry'
