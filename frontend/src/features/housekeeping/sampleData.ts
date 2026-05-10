import type { HousekeepingWorkspaceData } from './types'

const now = new Date('2026-05-10T08:30:00.000Z').toISOString()

export const housekeepingSampleData: HousekeepingWorkspaceData = {
  rooms: [
    { id: 'room-101', label: '101' },
    { id: 'room-102', label: '102' },
    { id: 'room-205', label: '205' },
    { id: 'room-208', label: '208' },
  ],
  minibarItems: [
    { id: 'hk-minibar-water', name: 'Voda' },
    { id: 'hk-minibar-beer', name: 'Pivo' },
    { id: 'hk-minibar-cola', name: 'Cola' },
  ],
  photoTaskTypes: [
    { id: 'photo-bed', name: 'Postel' },
    { id: 'photo-bath', name: 'Koupelna' },
    { id: 'photo-minibar', name: 'Minibar' },
  ],
  assignments: [
    {
      id: 'hk-asg-101',
      room_id: 'room-101',
      room_label_snapshot: '101',
      work_type: 'Prijezd',
      priority: 'Vysoka',
      reception_note: 'VIP host, zkontrolovat květiny.',
      status: 'Prideleno',
      paused_seconds: 0,
      created_at: now,
      required_photos: [
        { id: 'req-101-bed', photo_task_type_id: 'photo-bed', task_label_snapshot: 'Postel', uploaded: false },
        { id: 'req-101-bath', photo_task_type_id: 'photo-bath', task_label_snapshot: 'Koupelna', uploaded: false },
      ],
      photos: [],
      minibar_entries: [],
    },
    {
      id: 'hk-asg-205',
      room_id: 'room-205',
      room_label_snapshot: '205',
      work_type: 'Odjezd',
      priority: 'Normalni',
      reception_note: 'Doplnit ručníky.',
      status: 'Uklizi se',
      paused_seconds: 120,
      created_at: now,
      started_at: now,
      required_photos: [{ id: 'req-205-minibar', photo_task_type_id: 'photo-minibar', task_label_snapshot: 'Minibar', uploaded: true }],
      photos: [{ id: 'photo-205-minibar', task_label: 'Minibar', photo_task_type_id: 'photo-minibar' }],
      minibar_entries: [{ id: 'minibar-205-water', item_id: 'hk-minibar-water', item_name_snapshot: 'Voda', quantity: 1 }],
    },
  ],
  revisions: [
    { id: 'hk-rev-1', location: '2. patro', text: 'Vyleštit okna u výtahu.', status: 'open', created_at: now },
    { id: 'hk-rev-2', location: 'Sklad', text: 'Srovnat náhradní peřiny.', status: 'done', completion_note: 'Hotovo', created_at: now, completed_at: now },
  ],
  laundry: [{ id: 'hk-laundry-1', status: 'open', created_at: now, photo_uploaded: false }],
  history: [
    {
      id: 'hist-208',
      assignment_id: 'hk-asg-208',
      room_label_snapshot: '208',
      work_type: 'Pobyt',
      priority: 'Normalni',
      housekeeper_username_snapshot: 'pokojska',
      finished_at: now,
      duration_seconds: 1680,
    },
  ],
  report: {
    month: '2026-05',
    housekeepers: {
      pokojska: { assignment_count: 14, revision_count: 2, laundry_count: 1 },
      lenka: { assignment_count: 9, revision_count: 1, laundry_count: 0 },
    },
  },
}
