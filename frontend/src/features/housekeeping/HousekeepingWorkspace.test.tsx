import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HousekeepingWorkspace } from './HousekeepingWorkspace'
import { housekeepingSampleData } from './sampleData'

describe('HousekeepingWorkspace', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => Promise.resolve(jsonResponseFor(String(input)))))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('does not offer a role the user is not allowed to use', () => {
    render(<HousekeepingWorkspace initialData={housekeepingSampleData} allowedRoles={['housekeeper']} defaultRole="reception" />)

    expect(screen.queryByRole('button', { name: /recepce/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /zadat/i })).not.toBeInTheDocument()
    expect(screen.getByText('Pokojská')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument()
  })

  it('surfaces fetch failures without falling back to sample data', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('catalog failed'))))

    render(<HousekeepingWorkspace />)

    await waitFor(() => expect(screen.getByText('Backend nedostupný')).toBeInTheDocument())
    expect(screen.queryByText('Pokoj 101')).not.toBeInTheDocument()
  })
})

function jsonResponseFor(path: string) {
  if (path.startsWith('/api/catalog')) {
    return Response.json({ hotel_rooms: [], housekeeping_minibar_items: [], photo_task_types: [] })
  }
  if (path.startsWith('/api/housekeeping/state')) return Response.json({ assignments: [], revisions: [], laundry: [] })
  if (path.startsWith('/api/housekeeping/history')) return Response.json([])
  if (path.startsWith('/api/housekeeping/reports/monthly-work')) return Response.json({ month: '2026-05', housekeepers: {} })
  return Response.json({})
}
