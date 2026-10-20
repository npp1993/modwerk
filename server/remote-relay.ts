// SPDX-License-Identifier: Elastic-2.0
// Copyright (c) 2026 Jannik Aßfalg (repeat98)
// The relay of one remote debug session: a Durable Object holding the member's and the administrator's WebSockets.
// It forwards the administrator's USB requests to the member's browser and the replies back, refuses what the session's
// scope does not allow (the browser checks again; it holds the device), and ends the session on time. It keeps request
// counts for the member's record, never the bytes.
import type { Database } from './platform'
import { fromBase64, parseMemberMessage, parseOperatorMessage, remoteTransferRefusal, type RelayMessage, type RemoteScope } from '../src/community/remote-session-contract'

export interface RelaySocket {
  send(data: string): void
  close(code?: number, reason?: string): void
  addEventListener(type: 'message', listener: (event: { data: unknown }) => void): void
  addEventListener(type: 'close' | 'error', listener: () => void): void
}
type Side = 'member' | 'operator'
export type EndReason = 'member' | 'operator' | 'time'
const IN_FLIGHT = 16, PER_SECOND = 100

export class RemoteRelayCore {
  private readonly sockets: Partial<Record<Side, RelaySocket>> = {}
  private vendorInterface: number | null = null
  private model?: string
  /** Requests passed to the member's browser and not yet answered, with their kind for the counts. */
  private readonly pending = new Map<number, string>()
  private readonly counts: Record<string, number> = {}
  private window = { second: 0, count: 0 }
  private ended = false
  private readonly config: { scope: RemoteScope; endsAt: string }
  private readonly finish: (reason: EndReason, summary: Record<string, number>) => unknown
  private readonly clock: () => number
  constructor(config: { scope: RemoteScope; endsAt: string }, finish: (reason: EndReason, summary: Record<string, number>) => unknown, clock = Date.now) {
    this.config = config; this.finish = finish; this.clock = clock
  }
  get done() { return this.ended }
  attach(side: Side, socket: RelaySocket) {
    if (this.ended) { send(socket, { type: 'ended', reason: 'time' }); socket.close(1000, 'Session ended'); return }
    const previous = this.sockets[side]
    this.sockets[side] = socket
    if (previous) { send(previous, { type: 'ended', reason: 'replaced' }); previous.close(1000, 'Replaced') }
    if (side === 'member') this.lose()
    socket.addEventListener('message', event => side === 'member' ? this.fromMember(event.data) : this.fromOperator(event.data))
    const gone = () => this.detach(side, socket)
    socket.addEventListener('close', gone); socket.addEventListener('error', gone)
    this.presence()
  }
  end(reason: EndReason) {
    if (this.ended) return
    this.ended = true
    for (const socket of Object.values(this.sockets)) { send(socket!, { type: 'ended', reason }); try { socket!.close(1000, 'Session ended') } catch { /* already closed */ } }
    void this.finish(reason, { ...this.counts })
  }
  private count(key: string) { this.counts[key] = (this.counts[key] ?? 0) + 1 }
  private presence() {
    const message: RelayMessage = { type: 'presence', member: !!this.sockets.member, operator: !!this.sockets.operator, endsAt: this.config.endsAt, vendorInterface: this.vendorInterface, ...(this.model ? { model: this.model } : {}) }
    for (const socket of Object.values(this.sockets)) send(socket!, message)
  }
  /** The member's browser went away: whatever it had not answered fails, and no device is known until it says again. */
  private lose() {
    for (const id of this.pending.keys()) if (this.sockets.operator) send(this.sockets.operator, { type: 'reply', id, status: 'failed', reason: 'The member’s browser disconnected.' })
    this.pending.clear(); this.vendorInterface = null; this.model = undefined
  }
  private detach(side: Side, socket: RelaySocket) {
    if (this.sockets[side] !== socket) return
    delete this.sockets[side]
    if (side === 'member') this.lose()
    if (!this.ended) this.presence()
  }
  private fromOperator(raw: unknown) {
    if (this.ended) return
    const message = parseOperatorMessage(raw), operator = this.sockets.operator!
    if (!message) { this.count('invalid'); return }
    if (message.type === 'end') return this.end('operator')
    if (message.type === 'say') { if (this.sockets.member) send(this.sockets.member, message); return }
    const fail = (status: 'refused' | 'failed', reason: string) => { this.count(`${message.direction} ${message.request} ${status}`); send(operator, { type: 'reply', id: message.id, status, reason }) }
    const second = Math.floor(this.clock() / 1000)
    if (second !== this.window.second) this.window = { second, count: 0 }
    if (++this.window.count > PER_SECOND || this.pending.size >= IN_FLIGHT) return fail('failed', 'Too many requests at once.')
    if (this.pending.has(message.id)) return fail('failed', 'This request id is already waiting.')
    if (!this.sockets.member) return fail('failed', 'The member’s browser is not connected.')
    const refusal = remoteTransferRefusal(this.config.scope, message.direction === 'in'
      ? { direction: 'in', request: message.request, value: message.value, index: message.index, length: message.length }
      : { direction: 'out', request: message.request, value: message.value, index: message.index, data: fromBase64(message.data) }, this.vendorInterface)
    if (refusal) return fail('refused', refusal)
    this.pending.set(message.id, `${message.direction} ${message.request}`)
    send(this.sockets.member, message)
  }
  private fromMember(raw: unknown) {
    if (this.ended) return
    const message = parseMemberMessage(raw)
    if (!message) { this.count('invalid'); return }
    if (message.type === 'end') return this.end('member')
    if (message.type === 'device') { this.vendorInterface = message.vendorInterface; this.model = message.model; this.presence(); return }
    // Only answers to requests the relay passed on reach the administrator.
    const kind = this.pending.get(message.id)
    if (!kind) return
    this.pending.delete(message.id)
    this.count(`${kind} ${message.status}`)
    if (this.sockets.operator) send(this.sockets.operator, message)
  }
}
function send(socket: RelaySocket, message: unknown) { try { socket.send(JSON.stringify(message)) } catch { /* A closed socket's close event follows. */ } }

/** Workers' runtime pieces the relay uses; lib.dom has none of them. */
interface ServerSocket extends RelaySocket { accept(): void }
declare const WebSocketPair: { new (): { 0: ServerSocket; 1: ServerSocket } }
interface RelayState { storage: { setAlarm(time: number): Promise<void> } }

export class RemoteSessionRelay {
  private core?: RemoteRelayCore
  private readonly state: RelayState
  private readonly env: { DB?: Database }
  private id = ''
  constructor(state: RelayState, env: { DB?: Database }) { this.state = state; this.env = env }
  async fetch(request: Request): Promise<Response> {
    const path = new URL(request.url).pathname
    if (path === '/end') {
      const by = request.headers.get('X-Remote-By')
      this.core?.end(by === 'member' ? 'member' : 'operator')
      return new Response(null, { status: 204 })
    }
    if (path !== '/socket' || request.headers.get('Upgrade') !== 'websocket') return new Response('Not found', { status: 404 })
    const side = request.headers.get('X-Remote-Side'), endsAt = request.headers.get('X-Remote-Ends') ?? '', scope = request.headers.get('X-Remote-Scope')
    if ((side !== 'member' && side !== 'operator') || scope !== 'read' || !(Date.parse(endsAt) > Date.now())) return new Response('Invalid session', { status: 400 })
    if (!this.core || this.core.done) {
      this.id = request.headers.get('X-Remote-Session') ?? ''
      this.core = new RemoteRelayCore({ scope, endsAt }, (reason, summary) => this.record(reason, summary))
      await this.state.storage.setAlarm(Date.parse(endsAt))
    }
    const pair = new WebSocketPair(), [client, server] = [pair[0], pair[1]]
    server.accept()
    this.core.attach(side, server)
    return new Response(null, { status: 101, webSocket: client } as ResponseInit)
  }
  async alarm() { this.core?.end('time') }
  /** The member's record: how it ended and how many requests of each kind passed. */
  private async record(reason: EndReason, summary: Record<string, number>) {
    if (!this.env.DB || !this.id) return
    const at = new Date().toISOString()
    await this.env.DB.prepare("UPDATE remote_sessions SET summary_json=?,status=CASE WHEN status='active' THEN 'ended' ELSE status END,ended_at=COALESCE(ended_at,?),ended_by=COALESCE(ended_by,?) WHERE id=?")
      .bind(JSON.stringify(summary), at, reason, this.id).run().catch(() => {})
  }
}
