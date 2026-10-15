import { useEffect, useState, useSyncExternalStore } from 'react'
import { api, post } from '../community/api'
import type { LinkState, OctatrackLink } from '../engine/elekloader/octatrack-link'
import baseBinding from '../../sdk/machines/octatrack/base-binding.json' with { type: 'json' }

const noSubscription = () => () => {}
/** What the prompt needs to know of the unit: it runs the current Modwerk base, it is still being read, or neither (an
 * older base counts as neither: every beta tester updates, owner 15 October 2026). */
export function unitForPrompt(state?: LinkState): 'base' | 'connecting' | 'other' {
  if (state?.identity) return state.identity.base === baseBinding.identity ? 'base' : 'other'
  return state?.status === 'ready' ? 'base' : state?.status === 'connecting' ? 'connecting' : 'other'
}

/**
 * The base install prompt for a verified member with USB access: due until their unit runs the current base, on any
 * device, and opened once the page is visible and no other dialog is open. Only a connected unit that runs the current
 * base records it as done; closing it or Later hides it for this visit, and a connected older base opens it.
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
    /** Both are gone for this visit only, so the prompt returns on the next one until the unit runs the current base. */
    close() { setDue(false); setOpen(false) },
    later() { setDue(false); setOpen(false) },
  }
}
