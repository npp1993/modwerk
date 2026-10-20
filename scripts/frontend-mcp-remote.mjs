// SPDX-License-Identifier: GPL-3.0-or-later
// The MCP's side of a remote debug session: a WebUSB-shaped device whose control transfers travel through the
// session's relay to the member's browser, which carries them out on their Octatrack (src/community/remote-session.ts).
// The site's own OctatrackLink drives it, exactly as it drives the local USB bridge.

const VENDOR = { interfaceClass: 0xff, interfaceSubclass: 0x4d, interfaceProtocol: 1, endpoints: [] }
const toBase64 = bytes => Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength).toString('base64')

/** Opens the relay for `url` (with its one-time ticket) and resolves once the member's browser reports a unit.
 * `socket` makes the WebSocket (tests pass a fake). */
export function openRemoteUnit(url, { socket = target => new WebSocket(target), timeoutMs = 10000, waitMs = 60000 } = {}) {
  const ws = socket(url), waiting = new Map(), listeners = new Set()
  let next = 1, vendorInterface = null, model, member = false, endsAt = null, ended = null, ready
  const unitReady = new Promise((resolve, reject) => { ready = { resolve, reject } })
  const timer = setTimeout(() => ready.reject(new Error('The member’s browser has not connected an Octatrack yet; try remote_session_connect again.')), waitMs)
  const fail = reason => {
    ended ??= reason
    for (const [, pending] of waiting) pending.reject(new Error('The remote session ended: ' + reason + '.'))
    waiting.clear(); clearTimeout(timer); ready.reject(new Error('The remote session ended: ' + reason + '.'))
    for (const listener of listeners) listener({ device: unit })
  }
  ws.addEventListener('message', event => {
    let message
    try { message = JSON.parse(String(event.data)) } catch { return }
    if (message.type === 'presence') {
      member = !!message.member; endsAt = message.endsAt; model = message.model
      const had = vendorInterface
      vendorInterface = Number.isInteger(message.vendorInterface) ? message.vendorInterface : null
      if (vendorInterface !== null) { clearTimeout(timer); ready.resolve() }
      else if (had !== null) for (const listener of listeners) listener({ device: unit })
    } else if (message.type === 'ended') { ws.close(); fail(message.reason) }
    else if (message.type === 'reply') {
      const pending = waiting.get(message.id)
      if (!pending) return
      waiting.delete(message.id); clearTimeout(pending.timer)
      if (message.status === 'ok' || message.status === 'stall') pending.resolve(message)
      else pending.reject(new Error((message.status === 'refused' ? 'Refused by the session: ' : 'Remote transfer failed: ') + (message.reason ?? message.status)))
    }
  })
  ws.addEventListener('close', () => fail(ended ?? 'connection closed'))
  ws.addEventListener('error', () => fail(ended ?? 'connection error'))
  const transfer = body => new Promise((resolve, reject) => {
    if (ended) return reject(new Error('The remote session ended: ' + ended + '.'))
    const id = next++
    const timer = setTimeout(() => { waiting.delete(id); reject(new Error('The member’s browser did not answer in time.')) }, timeoutMs)
    waiting.set(id, { resolve, reject, timer })
    ws.send(JSON.stringify({ type: 'transfer', id, ...body }))
  })
  const unit = {
    get configuration() { return vendorInterface === null ? { interfaces: [] } : { interfaces: [{ interfaceNumber: vendorInterface, alternates: [VENDOR] }] } },
    opened: false,
    async open() { this.opened = true }, async close() { this.opened = false }, async selectConfiguration() {}, async claimInterface() {}, async releaseInterface() {},
    async controlTransferIn(setup, length) {
      const reply = await transfer({ direction: 'in', request: setup.request, value: setup.value, index: setup.index, length })
      if (reply.status !== 'ok' || typeof reply.data !== 'string') return { status: 'stall' }
      const bytes = new Uint8Array(Buffer.from(reply.data, 'base64'))
      return { status: 'ok', data: new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength) }
    },
    async controlTransferOut(setup, data) {
      const reply = await transfer({ direction: 'out', request: setup.request, value: setup.value, index: setup.index, data: toBase64(new Uint8Array(data)) })
      return reply.status === 'ok' ? { status: 'ok', bytesWritten: reply.bytesWritten ?? data.length } : { status: 'stall', bytesWritten: 0 }
    },
  }
  const usb = { async getDevices() { return [] }, async requestDevice() { return unit }, addEventListener(type, listener) { if (type === 'disconnect') listeners.add(listener) }, removeEventListener(type, listener) { if (type === 'disconnect') listeners.delete(listener) } }
  return {
    usb, unit, ready: unitReady,
    state: () => ({ member, endsAt, model: model ?? null, unit: vendorInterface !== null, ended }),
    say(text) { if (ended) throw new Error('The remote session ended.'); ws.send(JSON.stringify({ type: 'say', text })) },
    end() { if (!ended) { try { ws.send(JSON.stringify({ type: 'end' })) } catch { /* closing anyway */ } } ws.close(); fail('operator') },
  }
}
