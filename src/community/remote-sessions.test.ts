import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DatabaseSync } from 'node:sqlite'
import { testServer } from './test-server'
import { digest } from '../../server/security'
import { cleanupRemoteSessions } from '../../server/remote-sessions'
import { handleCommunity } from '../../server/transport'
import { REMOTE_SESSION_CONSENT_VERSION as version } from './remote-session-contract'

const databases: DatabaseSync[] = []
afterEach(() => { vi.useRealTimers(); databases.splice(0).forEach(db => db.close()) })
const member = 'a'.repeat(64), other = 'b'.repeat(64)
async function fixture({ relay = true } = {}) {
  const server = await testServer(); databases.push(server.db)
  for (const [id, token] of [['member', member], ['other', other]] as const) {
    server.db.prepare('INSERT INTO users(id,display_name,username,email_verified) VALUES(?,?,?,1)').run(id, id, id)
    server.db.prepare('INSERT INTO sessions(token_hash,user_id,expires) VALUES(?,?,?)').run(await digest(token), id, Math.floor(Date.now() / 1000) + 3600)
  }
  const relayed: Request[] = []
  if (relay) server.env.REMOTE_SESSIONS = { idFromName: name => name, get: () => ({ async fetch(request: Request) { relayed.push(request); return new Response(null, { status: 204 }) } }) }
  const admin = (await (await server.call('/auth/admin', 'POST', { key: 'e'.repeat(64) })).json()).token as string
  const ask = (body: unknown = { username: 'member', reason: 'Your unit froze after a sync; I want to read its log.', minutes: 15 }) => server.call('/admin/remote-sessions', 'POST', body, '', admin)
  const socket = (id: string, ticket: string) => handleCommunity(new Request(`https://api.example.test/api/remote-sessions/${id}/socket?ticket=${ticket}`, { headers: { Upgrade: 'websocket', Origin: 'https://octamod.test' } }), server.env)
  return { ...server, admin, ask, relayed, socket }
}

describe('remote debug sessions', () => {
  it('lets only administrators ask, and only verified members by username', async () => {
    const { call, ask, db } = await fixture()
    expect((await call('/admin/remote-sessions', 'POST', { username: 'member', reason: 'x' }, other)).status).toBe(403)
    expect((await ask({ username: 'nobody', reason: 'Look at the log.' })).status).toBe(404)
    expect((await ask({ username: 'member', reason: '' })).status).toBe(400)
    expect((await ask({ username: 'member', reason: 'Look at the log.', minutes: 120 })).status).toBe(400)
    db.prepare("UPDATE users SET suspended=1 WHERE id='other'").run()
    expect((await ask({ username: 'other', reason: 'Look at the log.' })).status).toBe(404)
    const created = await ask()
    expect(created.status).toBe(201)
    expect((await created.json()).session).toMatchObject({ status: 'pending', member: 'member', requester: 'Modwerk administrator', minutes: 15, scope: 'read' })
    // One open request per member.
    expect((await ask()).status).toBe(409)
  })
  it('brings the request to the member through the bell, and only to them', async () => {
    const { call, ask } = await fixture()
    expect((await (await call('/notifications/unread', 'GET', undefined, member)).json()).remoteSession).toBeUndefined()
    const { session } = await (await ask()).json()
    expect((await (await call('/notifications/unread', 'GET', undefined, member)).json()).remoteSession).toBe(true)
    expect((await (await call('/notifications/unread', 'GET', undefined, other)).json()).remoteSession).toBeUndefined()
    const mine = await (await call('/remote-sessions', 'GET', undefined, member)).json()
    expect(mine).toMatchObject({ consentVersion: version, current: { id: session.id, reason: 'Your unit froze after a sync; I want to read its log.', requester: 'Modwerk administrator' } })
    expect(mine.current.member).toBeUndefined()
    expect((await (await call('/remote-sessions', 'GET', undefined, other)).json()).current).toBeNull()
    expect((await call(`/remote-sessions/${session.id}/accept`, 'POST', { version }, other)).status).toBe(404)
  })
  it('opens the relay only after consent, with one-time tickets for each side', async () => {
    const { call, ask, admin, relayed, socket, db } = await fixture()
    const { session } = await (await ask()).json()
    expect((await call(`/admin/remote-sessions/${session.id}/ticket`, 'POST', {}, '', admin)).status).toBe(409)
    expect((await call(`/remote-sessions/${session.id}/accept`, 'POST', { version: 'old' }, member)).status).toBe(400)
    const accepted = await (await call(`/remote-sessions/${session.id}/accept`, 'POST', { version }, member)).json()
    expect(accepted.session).toMatchObject({ status: 'active' })
    expect(Date.parse(accepted.session.endsAt) - Date.now()).toBeGreaterThan(14 * 60000)
    expect(db.prepare('SELECT consent_version FROM remote_sessions').get()).toEqual({ consent_version: version })
    expect((await socket(session.id, accepted.ticket)).status).toBe(204)
    expect(relayed.at(-1)!.headers.get('X-Remote-Side')).toBe('member')
    expect(relayed.at(-1)!.headers.get('X-Remote-Scope')).toBe('read')
    // A ticket opens one socket.
    expect((await socket(session.id, accepted.ticket)).status).toBe(401)
    expect((await socket(session.id, 'f'.repeat(64))).status).toBe(401)
    const { ticket } = await (await call(`/admin/remote-sessions/${session.id}/ticket`, 'POST', {}, '', admin)).json()
    expect((await socket(session.id, ticket)).status).toBe(204)
    expect(relayed.at(-1)!.headers.get('X-Remote-Side')).toBe('operator')
    expect((await handleCommunity(new Request(`https://api.example.test/api/remote-sessions/${session.id}/socket?ticket=${ticket}`), (await fixture()).env)).status).toBe(426)
  })
  it('lets the member decline, and end a running session at once', async () => {
    const { call, ask, admin, relayed, socket } = await fixture()
    const first = (await (await ask()).json()).session
    expect((await call(`/remote-sessions/${first.id}/decline`, 'POST', {}, member)).status).toBe(200)
    expect((await call(`/remote-sessions/${first.id}/accept`, 'POST', { version }, member)).status).toBe(409)
    const second = (await (await ask()).json()).session
    const { ticket } = await (await call(`/remote-sessions/${second.id}/accept`, 'POST', { version }, member)).json()
    expect((await call(`/remote-sessions/${second.id}/end`, 'POST', {}, member)).status).toBe(200)
    expect(new URL(relayed.at(-1)!.url).pathname).toBe('/end')
    expect(relayed.at(-1)!.headers.get('X-Remote-By')).toBe('member')
    expect((await socket(second.id, ticket)).status).toBe(410)
    expect((await call(`/admin/remote-sessions/${second.id}/ticket`, 'POST', {}, '', admin)).status).toBe(409)
    const history = await (await call('/remote-sessions', 'GET', undefined, member)).json()
    expect(history.current).toBeNull()
    expect(history.sessions.map((item: { status: string; endedBy: string | null }) => [item.status, item.endedBy])).toEqual([['ended', 'member'], ['declined', null]])
  })
  it('lets the administrator end or withdraw, and expires what nobody answered', async () => {
    const { call, ask, admin, env } = await fixture()
    const pending = (await (await ask()).json()).session
    expect((await call(`/admin/remote-sessions/${pending.id}`, 'DELETE', undefined, '', admin)).status).toBe(200)
    expect((await (await call(`/admin/remote-sessions/${pending.id}`, 'GET', undefined, '', admin)).json()).session).toMatchObject({ status: 'expired', endedBy: 'operator' })
    const lapsed = (await (await ask()).json()).session
    await cleanupRemoteSessions(env.DB!, new Date(Date.now() + 11 * 60000))
    expect((await call(`/remote-sessions/${lapsed.id}/accept`, 'POST', { version }, member)).status).toBe(409)
  })
  it('closes a session whose time ran out, and keeps records for 90 days', async () => {
    const { call, ask, env } = await fixture()
    const session = (await (await ask()).json()).session
    await call(`/remote-sessions/${session.id}/accept`, 'POST', { version }, member)
    await cleanupRemoteSessions(env.DB!, new Date(Date.now() + 16 * 60000))
    expect((await (await call('/remote-sessions', 'GET', undefined, member)).json()).sessions[0]).toMatchObject({ status: 'ended', endedBy: 'time' })
    await cleanupRemoteSessions(env.DB!, new Date(Date.now() + 91 * 86400000))
    expect((await (await call('/remote-sessions', 'GET', undefined, member)).json()).sessions).toEqual([])
  })
  it('says so when the backend has no relay', async () => {
    const { ask } = await fixture({ relay: false })
    expect((await ask()).status).toBe(503)
  })
})
