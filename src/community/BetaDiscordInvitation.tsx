import { useEffect, useState } from 'react'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import { assetUrl } from '../hosting'
import { api, post } from './api'
import { useCommunity } from './context'
import { hasBetaAccess } from './beta-access'

/** Existing and newly admitted testers get a separate once-per-account invitation. Joining stays optional. */
export function BetaDiscordInvitation() {
  const { session } = useCommunity()
  const eligible = hasBetaAccess(session)
  return eligible ? <Invitation key={session.user!.id} /> : null
}
function Invitation() {
  const [show, setShow] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    void api<{ show: boolean }>('/auth/beta-discord-invite', { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setShow(value.show) }).catch(() => {})
    return () => controller.abort()
  }, [])
  function handled() { setShow(false); void post('/auth/beta-discord-invite', {}).catch(() => {}) }
  if (!show) return null
  return <aside className="beta-discord-invitation" aria-label="Beta tester Discord invitation">
    <img src={assetUrl('auth/discord.svg')} width="28" height="22" alt="" />
    <div><strong>Join the beta testers on Discord</strong><p>Ask questions, share what works and help us find bugs.</p></div>
    <div className="beta-discord-actions"><a className="button button-primary" href={DEVELOPMENT_DISCORD_URL} target="_blank" rel="noreferrer" onClick={handled}>Join Discord<span className="sr-only"> (opens in a new tab)</span></a><button type="button" className="text-button" onClick={handled}>Not now</button></div>
  </aside>
}
