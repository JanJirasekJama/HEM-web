import { useContext } from 'react'

import { AppStateContext } from '@/shared/auth/AppStateContext'

export function useAppState() {
  const state = useContext(AppStateContext)
  if (!state) throw new Error('useAppState must be used inside AppStateProvider')

  return state
}
