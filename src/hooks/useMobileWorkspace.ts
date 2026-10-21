import { useSyncExternalStore } from 'react'

// Phones and touch-only tablets edit sets; firmware preparation and USB belong on a computer.
export const MOBILE_WORKSPACE = '(max-width: 600px), (hover: none) and (pointer: coarse)'
function subscribe(callback: () => void) {
  if (typeof window.matchMedia !== 'function') return () => {}
  const media = window.matchMedia(MOBILE_WORKSPACE)
  media.addEventListener('change', callback)
  return () => media.removeEventListener('change', callback)
}
const snapshot = () => typeof window.matchMedia === 'function' && window.matchMedia(MOBILE_WORKSPACE).matches
export function useMobileWorkspace() { return useSyncExternalStore(subscribe, snapshot, () => false) }
