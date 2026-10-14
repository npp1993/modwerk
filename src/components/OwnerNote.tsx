import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'
import { assetUrl } from '../hosting'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import { SUPPORT_URL } from '../config/support'
import { api, post } from '../community/api'
import { useCommunity } from '../community/context'
import { pageBusy } from '../community/public-announcement'
import { trackUsage } from '../community/usage'

// A new note needs a new id here and in server/auth.ts (OWNER_NOTE).
const KEY = 'modwerk.owner-note:2026-10-14'
const WAIT = 10
let closedThisVisit = false
export function ownerNoteSeen() {
  if (closedThisVisit) return true
  try { return localStorage.getItem(KEY) === 'seen' } catch { return false }
}
export function closeOwnerNote() {
  closedThisVisit = true
  try { localStorage.setItem(KEY, 'seen') } catch { /* Stays closed for this visit when storage is blocked. */ }
}

export function OwnerNote({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null), [wait, setWait] = useState(WAIT)
  useEffect(() => {
    const element = dialog.current, previousFocus = document.activeElement
    element?.showModal(); element?.querySelector('h2')?.focus()
    return () => { element?.close(); if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus() }
  }, [])
  useEffect(() => {
    if (!wait) return
    const timer = window.setTimeout(() => setWait(wait - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [wait])
  // The note stays up for a few seconds so it gets read; the links still open meanwhile.
  const close = () => { if (!wait) onClose() }
  return <dialog ref={dialog} className="app-dialog owner-note" aria-labelledby="owner-note-title" aria-describedby="owner-note-message" onCancel={event => { event.preventDefault(); close() }}>
    <header className="owner-note-head"><img src={assetUrl('modwerk-mark.svg')} width={28} height={28} alt="" /><span>Modwerk</span></header>
    <div className="owner-note-body">
      <h2 id="owner-note-title" tabIndex={-1}>Hey guys,</h2>
      <div id="owner-note-message">
        <p>the response I've been getting for this project is immense – and I'm super grateful for everything that has been happening the past week(s). However, I really need to slow down. I'm honestly feeling burnt out, since I just can't keep up with the demand and all the new issue reports coming in.</p>
        <p>I've been mostly fixing stuff myself – also in modules whose maintainers haven't gotten to their bugs yet – and working on a big Octatrack update that brings a new way to flash over USB and changes how FX get loaded onto the DSP chip.</p>
        <p>A big thank you to the developers who have been helping so far! But it's not enough to keep up with the demand, and at this rate I can't continue without more active helpers in the Discord server. I've laid the groundwork for a platform that is available for free, but now it's up to the developers and the community to make it work. This is a community project and I'd like it to stay that way – it won't work without you guys.</p>
        <p className="owner-note-warning"><Icon name="warn" size={18} /><span>One important thing: the modules are <strong>not safe to use in a live setting (yet)</strong>. Flashing the firmware is known to be quite safe with the provided bootloader, but the modules themselves can still crash.</span></p>
        <p>Also, I'm not integrating any mods that clone products that are still on sale or that would affect Elektron's sales negatively – the mods are mostly meant to be additive and integrate well into the existing UI.</p>
        <p>If you like and support my work over the last weeks, I'd be grateful for a small donation – I've been covering all the hosting costs myself.</p>
        <p className="owner-note-sign">Thank you,<br /><strong>Jannik</strong></p>
      </div>
    </div>
    <footer className="owner-note-actions">
      <button type="button" className="owner-note-close" disabled={!!wait} onClick={close}>{wait ? `Close in ${wait}` : 'Close'}</button>
      <a className="button button-quiet" href={DEVELOPMENT_DISCORD_URL} target="_blank" rel="noopener noreferrer" onClick={close} aria-label="Join Discord (opens in a new tab)"><img src={assetUrl('auth/discord.svg')} width={20} height={15} alt="" />Join Discord</a>
      <a className="button button-primary" href={SUPPORT_URL} target="_blank" rel="noopener noreferrer" onClick={() => { trackUsage('support_link_opened'); close() }} aria-label="Support on Ko-fi (opens in a new tab)"><Icon name="heart" size={15} />Support on Ko-fi</a>
    </footer>
  </dialog>
}

/** Once per verified account on every device, once per browser for visitors; opens when no other dialog, menu or text field is in use. */
export function OwnerNoteGate({ enabled }: { enabled: boolean }) {
  const { session, loading } = useCommunity(), memberId = session.user?.verified ? session.user.id : null
  const [open, setOpen] = useState(false), [serverDue, setServerDue] = useState<boolean>()
  const ask = !loading && !!memberId && !ownerNoteSeen()
  useEffect(() => {
    if (!ask) return
    const controller = new AbortController()
    // A Worker without this route yet falls back to this browser's marker.
    void api<{ show: boolean }>('/auth/owner-note', { signal: controller.signal }).then(result => { if (!controller.signal.aborted) setServerDue(result.show) }).catch(() => { if (!controller.signal.aborted) setServerDue(true) })
    return () => controller.abort()
  }, [ask, memberId])
  const due = !loading && !ownerNoteSeen() && (!memberId || serverDue === true)
  useEffect(() => {
    if (!enabled || open || !due) return
    const timer = window.setInterval(() => { if (!pageBusy()) setOpen(true) }, 3000)
    return () => window.clearInterval(timer)
  }, [enabled, open, due])
  return open ? <OwnerNote onClose={() => { closeOwnerNote(); setOpen(false); if (memberId) void post('/auth/owner-note', {}).catch(() => {}) }} /> : null
}
