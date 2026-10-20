// SPDX-License-Identifier: Elastic-2.0
// Copyright (c) 2026 Jannik Aßfalg (repeat98)
// Remote debug sessions: the requests, consent and tickets. The relay itself is server/remote-relay.ts.
import type { Database, Env, User } from './platform'
import { ADMIN_ACTOR, needMember, throttle } from './auth'
import { digest, HttpError, jsonBody, response, token } from './security'
import { hasControl, REMOTE_REASON_MAX, REMOTE_REQUEST_MINUTES, REMOTE_SESSION_CONSENT_VERSION, REMOTE_SESSION_MINUTES, type RemoteSessionView } from '../src/community/remote-session-contract'

const TICKET_SECONDS = 60, RETENTION_DAYS = 90
type Row = { id: string; member_id: string; member?: string | null; requester_name: string; reason: string; scope: 'read'; minutes: number; status: RemoteSessionView['status']; created_at: string; expires_at: string; answered_at: string | null; ends_at: string | null; ended_at: string | null; ended_by: string | null; summary_json: string | null }
const COLUMNS = 's.id,s.member_id,u.username AS member,s.requester_name,s.reason,s.scope,s.minutes,s.status,s.created_at,s.expires_at,s.answered_at,s.ends_at,s.ended_at,s.ended_by,s.summary_json'
const later = (now: Date, minutes: number) => new Date(now.getTime() + minutes * 60000).toISOString()
function view(row: Row, admin = false): RemoteSessionView {
  return { id: row.id, status: row.status, scope: row.scope, requester: row.requester_name, ...(admin ? { member: row.member ?? undefined } : {}), reason: row.reason, minutes: row.minutes,
    createdAt: row.created_at, expiresAt: row.status === 'pending' ? row.expires_at : null, answeredAt: row.answered_at, endsAt: row.ends_at, endedAt: row.ended_at, endedBy: row.ended_by,
    summary: row.summary_json ? JSON.parse(row.summary_json) as Record<string, number> : null }
}
const relay = (env: Env, id: string) => {
  if (!env.REMOTE_SESSIONS) throw new HttpError(503, 'Remote sessions are not available on this backend.')
  return env.REMOTE_SESSIONS.get(env.REMOTE_SESSIONS.idFromName(id))
}
async function ticket(db: Database, id: string, side: 'member' | 'operator') {
  const value = token(), now = Math.floor(Date.now() / 1000)
  await db.batch([
    db.prepare('DELETE FROM remote_session_tickets WHERE expires<=?').bind(now),
    db.prepare('INSERT INTO remote_session_tickets(token_hash,session_id,side,expires) VALUES(?,?,?,?)').bind(await digest(value), id, side, now + TICKET_SECONDS),
  ])
  return value
}
/** The relay was told to stop; a relay that has gone (redeploy) has nothing to stop. */
async function stopRelay(env: Env, id: string, by: 'member' | 'operator') {
  if (!env.REMOTE_SESSIONS) return
  try { await relay(env, id).fetch(new Request('https://relay/end', { method: 'POST', headers: { 'X-Remote-By': by } })) } catch { /* The hourly cleanup closes the record. */ }
}
/** Whether a member has a request waiting or a session running; the bell's poll carries it to the site. */
export async function remoteSessionDue(db: Database, memberId: string, now = new Date()) {
  try {
    return !!await db.prepare("SELECT 1 FROM remote_sessions WHERE member_id=? AND ((status='pending' AND expires_at>?) OR (status='active' AND ends_at>?))").bind(memberId, now.toISOString(), now.toISOString()).first()
  } catch { return false } // A Worker that is ahead of its migration.
}
export async function cleanupRemoteSessions(db: Database, now = new Date()) {
  const at = now.toISOString()
  await db.batch([
    db.prepare("UPDATE remote_sessions SET status='expired' WHERE status='pending' AND expires_at<=?").bind(at),
    db.prepare("UPDATE remote_sessions SET status='ended',ended_at=ends_at,ended_by='time' WHERE status='active' AND ends_at<=?").bind(at),
    db.prepare('DELETE FROM remote_session_tickets WHERE expires<=?').bind(Math.floor(now.getTime() / 1000)),
    db.prepare('DELETE FROM remote_sessions WHERE created_at<?').bind(new Date(now.getTime() - RETENTION_DAYS * 86400000).toISOString()),
  ])
}

export async function remoteSessionRoutes(request: Request, env: Env, db: Database, user: User | null, adminId: string | null): Promise<Response | null> {
  const url = new URL(request.url), path = url.pathname, now = new Date(), at = now.toISOString()
  let match: RegExpMatchArray | null
  // The WebSocket: a one-time ticket stands in for the session, since browsers cannot send a bearer token here.
  if ((match = path.match(/^\/api\/remote-sessions\/([0-9a-f-]{36})\/socket$/))) {
    if (request.method !== 'GET' || request.headers.get('Upgrade')?.toLowerCase() !== 'websocket') throw new HttpError(426, 'Open this route as a WebSocket.')
    const value = url.searchParams.get('ticket') ?? ''
    if (!/^[a-f0-9]{64}$/.test(value)) throw new HttpError(401, 'A session ticket is required.')
    const used = await db.prepare('DELETE FROM remote_session_tickets WHERE token_hash=? AND session_id=? RETURNING side,expires').bind(await digest(value), match[1]).first<{ side: 'member' | 'operator'; expires: number }>()
    if (!used || used.expires <= Math.floor(now.getTime() / 1000)) throw new HttpError(401, 'This session ticket has expired.')
    const session = await db.prepare("SELECT scope,ends_at FROM remote_sessions WHERE id=? AND status='active' AND ends_at>?").bind(match[1], at).first<{ scope: string; ends_at: string }>()
    if (!session) throw new HttpError(410, 'This remote session is not running.')
    return relay(env, match[1]).fetch(new Request('https://relay/socket', { headers: { Upgrade: 'websocket', 'X-Remote-Session': match[1], 'X-Remote-Side': used.side, 'X-Remote-Scope': session.scope, 'X-Remote-Ends': session.ends_at } }))
  }

  if (path === '/api/admin/remote-sessions' || path.startsWith('/api/admin/remote-sessions/')) {
    if (!adminId) throw new HttpError(403, 'Administrator access required.')
    if (path === '/api/admin/remote-sessions') {
      if (request.method === 'GET') return response({ sessions: (await db.prepare(`SELECT ${COLUMNS} FROM remote_sessions s JOIN users u ON u.id=s.member_id ORDER BY s.created_at DESC LIMIT 50`).all<Row>()).results.map(row => view(row, true)) })
      if (request.method !== 'POST') throw new HttpError(405, 'Use GET or POST.')
      if (!env.REMOTE_SESSIONS) throw new HttpError(503, 'Remote sessions are not available on this backend.')
      const body = await jsonBody(request, 4096)
      if (typeof body.username !== 'string' || !/^[A-Za-z0-9_.-]{1,40}$/.test(body.username.trim())) throw new HttpError(400, 'Give the member’s username.')
      if (typeof body.reason !== 'string' || !body.reason.trim() || body.reason.trim().length > REMOTE_REASON_MAX || hasControl(body.reason)) throw new HttpError(400, `Say in up to ${REMOTE_REASON_MAX} characters why you ask; the member reads it.`)
      const minutes = body.minutes ?? REMOTE_SESSION_MINUTES.default
      if (!Number.isInteger(minutes) || (minutes as number) < REMOTE_SESSION_MINUTES.least || (minutes as number) > REMOTE_SESSION_MINUTES.most) throw new HttpError(400, `Ask for ${REMOTE_SESSION_MINUTES.least} to ${REMOTE_SESSION_MINUTES.most} minutes.`)
      const member = await db.prepare('SELECT id,username FROM users WHERE lower(username)=lower(?) AND email_verified=1 AND suspended=0').bind(body.username.trim()).first<{ id: string; username: string }>()
      if (!member) throw new HttpError(404, 'No verified member has this username.')
      await throttle(db, 'remote-session-request:' + adminId, 20, 3600)
      await throttle(db, 'remote-session-member:' + member.id, 5, 86400)
      const requester = adminId === ADMIN_ACTOR ? 'Modwerk administrator' : (await db.prepare('SELECT username FROM users WHERE id=?').bind(adminId).first<{ username: string | null }>())?.username ?? 'Modwerk administrator'
      const id = crypto.randomUUID()
      // One open request or session per member; the insert itself checks, so two requests cannot both land.
      const inserted = await db.prepare(`INSERT INTO remote_sessions(id,member_id,requested_by,requester_name,reason,scope,minutes,status,created_at,expires_at)
        SELECT ?,?,?,?,?,'read',?,'pending',?,? WHERE NOT EXISTS(SELECT 1 FROM remote_sessions WHERE member_id=? AND ((status='pending' AND expires_at>?) OR (status='active' AND ends_at>?)))`)
        .bind(id, member.id, adminId, requester, body.reason.trim(), minutes, at, later(now, REMOTE_REQUEST_MINUTES), member.id, at, at).run()
      if (!inserted.meta.changes) throw new HttpError(409, 'This member already has a remote session request or a running session.')
      const row = await db.prepare(`SELECT ${COLUMNS} FROM remote_sessions s JOIN users u ON u.id=s.member_id WHERE s.id=?`).bind(id).first<Row>()
      return response({ session: view(row!, true) }, 201)
    }
    if (!(match = path.match(/^\/api\/admin\/remote-sessions\/([0-9a-f-]{36})(\/ticket)?$/))) throw new HttpError(404, 'Remote session route not found.')
    const row = await db.prepare(`SELECT ${COLUMNS} FROM remote_sessions s JOIN users u ON u.id=s.member_id WHERE s.id=?`).bind(match[1]).first<Row>()
    if (!row) throw new HttpError(404, 'Remote session not found.')
    if (match[2]) {
      if (request.method !== 'POST') throw new HttpError(405, 'Use POST.')
      if (row.status !== 'active' || !row.ends_at || row.ends_at <= at) throw new HttpError(409, row.status === 'pending' ? 'The member has not accepted yet.' : 'This remote session is not running.')
      return response({ ticket: await ticket(db, row.id, 'operator'), endsAt: row.ends_at })
    }
    if (request.method === 'GET') return response({ session: view(row, true) })
    if (request.method !== 'DELETE') throw new HttpError(405, 'Use GET or DELETE.')
    await db.prepare("UPDATE remote_sessions SET status=CASE WHEN status='pending' THEN 'expired' ELSE 'ended' END,ended_at=?,ended_by='operator' WHERE id=? AND status IN ('pending','active')").bind(at, row.id).run()
    if (row.status === 'active') await stopRelay(env, row.id, 'operator')
    return response({ ok: true })
  }

  if (path !== '/api/remote-sessions' && !path.startsWith('/api/remote-sessions/')) return null
  const member = needMember(user)
  if (path === '/api/remote-sessions') {
    if (request.method !== 'GET') throw new HttpError(405, 'Use GET.')
    // The current request or session first, then the member's history.
    const rows = (await db.prepare(`SELECT ${COLUMNS} FROM remote_sessions s JOIN users u ON u.id=s.member_id WHERE s.member_id=? ORDER BY s.created_at DESC LIMIT 20`).bind(member.id).all<Row>()).results
    const open = rows.find(row => row.status === 'pending' && row.expires_at > at || row.status === 'active' && !!row.ends_at && row.ends_at > at)
    return response({ current: open ? view(open) : null, consentVersion: REMOTE_SESSION_CONSENT_VERSION, sessions: rows.map(row => view(row)) })
  }
  if (!(match = path.match(/^\/api\/remote-sessions\/([0-9a-f-]{36})\/(accept|decline|ticket|end)$/)) || request.method !== 'POST') throw new HttpError(404, 'Remote session route not found.')
  const [, id, action] = match
  const row = await db.prepare(`SELECT ${COLUMNS} FROM remote_sessions s JOIN users u ON u.id=s.member_id WHERE s.id=? AND s.member_id=?`).bind(id, member.id).first<Row>()
  if (!row) throw new HttpError(404, 'Remote session not found.')
  if (action === 'accept') {
    const body = await jsonBody(request, 1024)
    if (body.version !== REMOTE_SESSION_CONSENT_VERSION) throw new HttpError(400, 'Reload the page and read the current consent text.')
    if (!env.REMOTE_SESSIONS) throw new HttpError(503, 'Remote sessions are not available on this backend.')
    const accepted = await db.prepare("UPDATE remote_sessions SET status='active',answered_at=?,consent_version=?,ends_at=? WHERE id=? AND member_id=? AND status='pending' AND expires_at>?")
      .bind(at, REMOTE_SESSION_CONSENT_VERSION, later(now, row.minutes), id, member.id, at).run()
    if (!accepted.meta.changes) throw new HttpError(409, 'This request has expired or was withdrawn.')
    const current = await db.prepare(`SELECT ${COLUMNS} FROM remote_sessions s JOIN users u ON u.id=s.member_id WHERE s.id=?`).bind(id).first<Row>()
    return response({ session: view(current!), ticket: await ticket(db, id, 'member') })
  }
  if (action === 'decline') {
    await db.prepare("UPDATE remote_sessions SET status='declined',answered_at=? WHERE id=? AND member_id=? AND status='pending'").bind(at, id, member.id).run()
    return response({ ok: true })
  }
  if (action === 'ticket') {
    if (row.status !== 'active' || !row.ends_at || row.ends_at <= at) throw new HttpError(409, 'This remote session is not running.')
    return response({ ticket: await ticket(db, id, 'member'), endsAt: row.ends_at })
  }
  await db.prepare("UPDATE remote_sessions SET status=CASE WHEN status='pending' THEN 'declined' ELSE 'ended' END,ended_at=?,ended_by='member' WHERE id=? AND member_id=? AND status IN ('pending','active')").bind(at, id, member.id).run()
  if (row.status === 'active') await stopRelay(env, id, 'member')
  return response({ ok: true })
}
