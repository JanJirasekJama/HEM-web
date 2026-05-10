import { createContext } from 'react'

import type { AppState } from '@/shared/auth/appStateTypes'

export const AppStateContext = createContext<AppState | null>(null)
