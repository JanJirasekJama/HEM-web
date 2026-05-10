import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ModuleOutlet } from '@/shared/layout/ModuleOutlet'
import type { ModuleDefinition } from '@/shared/auth/permissions'

const TestIcon = ({ className }: { className?: string }) => <svg aria-hidden="true" className={className} />

describe('ModuleOutlet', () => {
  it('renders the fallback module title and metric when a workspace component is not supplied', () => {
    const module = {
      code: 'dashboard',
      name: 'Dashboard',
      metric: 'Provozní přehled',
      permission: 'app:authenticated',
      icon: TestIcon,
    } satisfies ModuleDefinition

    render(<ModuleOutlet module={module} currentUser={null} permissions={{ roleName: 'test', permissions: [], can: () => false }} />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Provozní přehled')).toBeInTheDocument()
  })
})
