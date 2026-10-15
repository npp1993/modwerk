import { useEffect, useState, useSyncExternalStore } from 'react'
import { api, post } from '../community/api'
import type { LinkState, OctatrackLink } from '../engine/elekloader/octatrack-link'

const noSubscription = () => () => {}
/** What the prompt needs to know of the unit: it runs a Modwerk base already, it is still being read, or neither. */
export function unitForPrompt(state?: LinkState): 'base' | 'connecting' | 'other' {
  return state?.identity || state?.status === 'ready' ? 'base' : state?.status === 'connecting' ? 'connecting' : 'other'
}

/**
 * The one-time base install prompt for a verified member: due until they close it,
 * on any device, and opened once the page is visible and no other dialog is open.
 * A connected unit that already runs a Modwerk base keeps it from opening and records it as done: installing one is all it asks.
 * A failed read keeps it quiet; a failed record lets it show again next visit.
 */
export function useBaseInstallPrompt(memberId: string | null, enabled: boolean, link: OctatrackLink | null = null) {
  const [due, setDue] = useState(false), [open, setOpen] = useState(false)
  const unit = useSyncExternalStore(link?.subscribe ?? noSubscription, () => unitForPrompt(link?.getState()), () => 'other')
  useEffect(() => {
    if (!memberId || !enabled) return
    const controller = new AbortController()
    void api<{ show: boolean }>('/auth/base-install-prompt', { signal: controller.signal }).then(result => { if (!controller.signal.aborted) setDue(result.show) }).catch(() => {})
    return () => controller.abort()
  }, [memberId, enabled])
  // The marker is idempotent, so a reconnect that records it again is harmless.
  useEffect(() => { if (due && unit === 'base') void post('/auth/base-install-prompt', {}).catch(() => {}) }, [due, unit])
  useEffect(() => {
    if (!due || open || !enabled || unit !== 'other') return
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible' && !document.querySelector('dialog[open]')) setOpen(true) }, 1500)
    return () => window.clearInterval(timer)
  }, [due, open, enabled, unit])
  return {
    open: open && !!memberId,
    close() { setDue(false); setOpen(false); void post('/auth/base-install-prompt', {}).catch(() => {}) },
    /** Gone for this visit only, so it returns on the next one. */
    later() { setDue(false); setOpen(false) },
  }
}
