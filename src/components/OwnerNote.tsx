import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'
import { DiagnosticsInvitation } from './DiagnosticsInvitation'
import { assetUrl } from '../hosting'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import { api, post } from '../community/api'
import { useCommunity } from '../community/context'
import { diagnosticPreference, type DiagnosticPreference } from '../community/octatrack-diagnostics'
import { pageBusy } from '../community/public-announcement'
import { browserRequestsPrivacy } from '../community/usage'

// A new note needs a new id here and in server/auth.ts (OWNER_NOTE).
const KEY = 'modwerk.owner-note:2026-10-15-beta-2'
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
/** The required diagnostics step follows the note, even if the invitation was dismissed before, unless sharing is already on or impossible here. */
export const askForDiagnostics = (preference: DiagnosticPreference, privacy: boolean) => preference.available && !preference.enabled && !privacy

export function OwnerNote({ username, onJoin, onLeave }: { username: string; onJoin: () => void; onLeave: () => void }) {
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
  // The note stays up for a few seconds so it gets read, and then only closes through one of its two choices.
  return <dialog ref={dialog} className="app-dialog owner-note" aria-labelledby="owner-note-title" aria-describedby="owner-note-message" onCancel={event => event.preventDefault()}>
    <header className="owner-note-head"><img src={assetUrl('modwerk-mark.svg')} width={28} height={28} alt="" /><span>Modwerk beta</span></header>
    <div className="owner-note-body">
      <h2 id="owner-note-title" tabIndex={-1}>Hey guys,</h2>
      <div id="owner-note-message">
        <p>thanks a lot for testing the beta! To keep up with all the bugs coming in, I need every beta tester to do a few things from now on:</p>
        <ul className="owner-note-asks">
          <li><strong>Report bugs on Discord as they happen</strong> – in the <strong>#beta-tester</strong> channel, right when you run into them.</li>
          <li><strong>Use the same name on Discord as here</strong> (<strong>@{username}</strong>) – so I know who's who.</li>
          <li><strong>Share diagnostics</strong> – I'll ask you right after this note. It helps me see where a build or sync went wrong.</li>
        </ul>
        <p>The beta is limited to 50 people, so if you're not active on Discord, I'll pass your place on to someone else.</p>
        <p className="owner-note-warning"><Icon name="warn" size={18} /><span>This firmware is still <strong>highly experimental</strong> – but you can always roll back to the stock firmware.</span></p>
        <p>If this doesn't work for you, you can leave the beta below.</p>
        <p className="owner-note-sign">Thank you,<br /><strong>Jannik</strong></p>
      </div>
    </div>
    <footer className="owner-note-actions">
      <button type="button" className="owner-note-close" disabled={!!wait} onClick={onLeave}>Leave beta</button>
      <a className="button button-primary" href={DEVELOPMENT_DISCORD_URL} target="_blank" rel="noopener noreferrer" aria-disabled={!!wait} onClick={event => { if (wait) event.preventDefault(); else onJoin() }} aria-label="Join Discord (opens in a new tab)"><img src={assetUrl('auth/discord.svg')} width={20} height={15} alt="" />{wait ? `Join Discord (${wait})` : 'Join Discord'}</a>
    </footer>
  </dialog>
}

/** Beta testers only (App.tsx), on every device until they join Discord and share diagnostics; opens when no other dialog, menu or text field is in use. */
export function OwnerNoteGate({ enabled }: { enabled: boolean }) {
  const { session, refresh } = useCommunity(), memberId = session.user!.id
  const [step, setStep] = useState<'note' | 'diagnostics'>(), [serverDue, setServerDue] = useState<boolean>()
  useEffect(() => {
    if (ownerNoteSeen()) return
    const controller = new AbortController()
    // A Worker without this note yet falls back to this browser's marker.
    void api<{ show: boolean }>('/auth/owner-note', { signal: controller.signal }).then(result => { if (!controller.signal.aborted) setServerDue(result.show) }).catch(() => { if (!controller.signal.aborted) setServerDue(true) })
    return () => controller.abort()
  }, [memberId])
  const due = serverDue === true && !ownerNoteSeen()
  useEffect(() => {
    if (!enabled || step || !due) return
    const timer = window.setInterval(() => { if (!pageBusy()) setStep('note') }, 3000)
    return () => window.clearInterval(timer)
  }, [enabled, step, due])
  // The note counts as done once the tester joined Discord and diagnostics are on (or can't be turned on here).
  const done = () => { closeOwnerNote(); void post('/auth/owner-note', {}).catch(() => {}); setStep(undefined) }
  async function leave() {
    if (!window.confirm('Leave the beta? The beta modules and the Octatrack USB page go away for your account. If you want back in later, just ask me on Discord.')) return
    try { await post('/auth/beta-leave', {}) } catch (failure) { window.alert(failure instanceof Error ? failure.message : 'Couldn’t leave the beta. Please try again.'); return }
    setStep(undefined); await refresh()
  }
  if (step === 'diagnostics') return <DiagnosticsInvitation onClose={done} onLeave={() => void leave()} />
  return step === 'note' ? <OwnerNote username={session.user!.username!} onLeave={() => void leave()} onJoin={() => {
    void post('/auth/beta-discord-invite', {}).catch(() => {})
    if (askForDiagnostics(diagnosticPreference(), browserRequestsPrivacy())) setStep('diagnostics'); else done()
  }} /> : null
}

/** Dev preview (?preview=beta-note): the note, then the required diagnostics step. Nothing is sent. */
export function OwnerNotePreview() {
  const [step, setStep] = useState<'note' | 'diagnostics'>('note'), [closed, setClosed] = useState(false)
  if (closed) return null
  return step === 'note' ? <OwnerNote username="yourname" onJoin={() => setStep('diagnostics')} onLeave={() => setClosed(true)} /> : <DiagnosticsInvitation preview onClose={() => setClosed(true)} onLeave={() => setClosed(true)} />
}
