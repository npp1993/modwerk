import { useEffect } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { onCommunityReconnect } from './api'

/** While a community load has failed, bumps its revision once reads work again, so it heals without a page reload. */
export function useReconnectRetry(failed: boolean, setRevision: Dispatch<SetStateAction<number>>) {
  useEffect(() => failed ? onCommunityReconnect(() => setRevision(value => value + 1)) : undefined, [failed, setRevision])
}
