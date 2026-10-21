// A remote session end to end, without a network: the site's own OctatrackLink drives the MCP's remote device,
// whose transfers pass the relay (server/remote-relay.ts) and the member's browser relay (src/community/remote-session.ts)
// to a pretend Octatrack. Every refusal is checked at both the relay and the member's browser.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { openRemoteUnit } from './frontend-mcp-remote.mjs'
import { RemoteRelayCore } from '../server/remote-relay.ts'
import { MemberRelay, holdUnit } from '../src/community/remote-session.ts'
import { fakeUnit, FAKE_BASE } from '../src/dev/octatrack-link-fake.ts'
import { OctatrackLink, tabLocks, USB_LOCK } from '../src/engine/elekloader/octatrack-link.ts'
import { encodeUploadRequest } from '../src/engine/elekloader/upload-wire.ts'

/** Two ends of a WebSocket: what one sends, the other receives on a later tick. */
function socketPair(delay = 0) {
  const end = () => {
    const listeners = { message: new Set(), close: new Set(), error: new Set(), open: new Set() }
    return { listeners, sent: [], closed: false, addEventListener(type, listener) { listeners[type].add(listener) }, emit(type, event) { for (const listener of listeners[type]) listener(event) } }
  }
  const a = end(), b = end()
  const wire = (from, to) => {
    from.send = data => { if (from.closed) throw new Error('closed'); from.sent.push(data); setTimeout(() => to.emit('message', { data }), delay) }
    from.close = () => { if (from.closed) return; from.closed = to.closed = true; setTimeout(() => { from.emit('close'); to.emit('close') }, 0) }
  }
  wire(a, b); wire(b, a)
  return [a, b]
}
const settle = () => new Promise(resolve => setTimeout(resolve, 5))

async function session({ scope = 'read', endsAt = new Date(Date.now() + 600000).toISOString(), hopDelay = 0 } = {}) {
  const unit = fakeUnit('base'), [device] = await unit.usb.getDevices(), finished = []
  const core = new RemoteRelayCore({ scope, endsAt }, (reason, summary) => finished.push({ reason, summary }))
  const held = await holdUnit(device, tabLocks())
  const member = new MemberRelay({ id: '00000000-0000-4000-8000-000000000000', scope, device, vendorInterface: held.vendorInterface, model: 'OCTATRACK MKII',
    ticket: async () => 'f'.repeat(64), open: () => { const [browser, server] = socketPair(hopDelay); core.attach('member', server); setTimeout(() => browser.emit('open'), 0); return browser } })
  member.start('f'.repeat(64))
  let operatorEnd
  const remote = openRemoteUnit('wss://relay.test/socket', { socket: () => { const [mcp, server] = socketPair(hopDelay); operatorEnd = server; core.attach('operator', server); return mcp }, timeoutMs: 2000 })
  await remote.ready
  return { unit, device, core, member, remote, held, finished, operatorEnd }
}

beforeEach(() => { vi.stubGlobal('navigator', {}) })
afterEach(() => { vi.unstubAllGlobals() })

describe('a read-only remote session', () => {
  it('lets the site’s own link read the member’s unit through the relay', async () => {
    const { remote, member, finished, device } = await session()
    expect(remote.state()).toMatchObject({ member: true, unit: true, model: 'OCTATRACK MKII' })
    const link = new OctatrackLink(remote.usb, undefined, 300, tabLocks()), stop = link.start()
    await link.connect()
    expect(link.getState()).toMatchObject({ status: 'ready', identity: { base: FAKE_BASE, model: 'OCTATRACK MKII' } })
    const inventory = await link.inventory()
    expect(Array.isArray(inventory)).toBe(true)
    expect(member.getState().log.map(entry => entry.label)).toContain('identify')
    expect(member.getState().log.every(entry => entry.outcome !== 'refused')).toBe(true)
    // HELLO, the one frame a read-only session may submit, reaches the unit (the pretend one stalls every SUBMIT).
    const out = vi.spyOn(device, 'controlTransferOut')
    const hello = encodeUploadRequest({ command: 'hello' })
    expect(await remote.unit.controlTransferOut({ requestType: 'vendor', recipient: 'interface', request: 1, value: 1, index: 5 }, hello)).toEqual({ status: 'stall', bytesWritten: 0 })
    expect(out).toHaveBeenCalledTimes(1)
    expect(member.getState().log.at(-1)).toMatchObject({ label: 'HELLO', outcome: 'stall' })
    stop(); remote.end(); await settle()
    expect(finished).toMatchObject([{ reason: 'operator' }])
    expect(finished[0].summary['in 3 ok']).toBeGreaterThan(0)
    expect(finished[0].summary['out 1 stall']).toBe(1)
    expect(member.getState()).toMatchObject({ status: 'ended', ended: 'operator' })
    expect(device.opened).toBe(true)
  })
  it('refuses writes, self-test starts and saved-file reads at the relay', async () => {
    const { remote, member, device } = await session()
    const out = vi.spyOn(device, 'controlTransferOut'), into = vi.spyOn(device, 'controlTransferIn')
    const setup = request => ({ requestType: 'vendor', recipient: 'interface', request, value: 0, index: 5 })
    const enter = encodeUploadRequest({ command: 'enter', session: 'a'.repeat(64) })
    await expect(remote.unit.controlTransferOut(setup(1), enter)).rejects.toThrow(/Refused by the session/)
    await expect(remote.unit.controlTransferIn({ ...setup(21), value: 1 }, 96)).rejects.toThrow(/self-test/)
    await expect(remote.unit.controlTransferIn(setup(31), 80)).rejects.toThrow(/read-only/)
    await expect(remote.unit.controlTransferIn({ ...setup(3), index: 0 }, 72)).rejects.toThrow(/Modwerk interface/)
    expect(out).not.toHaveBeenCalled(); expect(into).not.toHaveBeenCalled()
    expect(member.getState().count).toBe(0)
    remote.end()
  })
  it('checks again in the member’s browser, which holds the device', async () => {
    const { device } = await session()
    const [browser, server] = socketPair(), into = vi.spyOn(device, 'controlTransferIn')
    const relay = new MemberRelay({ id: '00000000-0000-4000-8000-000000000001', scope: 'read', device, vendorInterface: 5, ticket: async () => 'f'.repeat(64), open: () => browser })
    relay.start('f'.repeat(64)); browser.emit('open'); await settle()
    // As if a relay had passed it on: the browser refuses it on its own.
    server.send(JSON.stringify({ type: 'transfer', id: 9, direction: 'in', request: 32, value: 0, index: 5, length: 480 }))
    await settle()
    expect(into).not.toHaveBeenCalled()
    expect(browser.sent.map(text => JSON.parse(text)).find(message => message.type === 'reply')).toMatchObject({ id: 9, status: 'refused' })
    expect(relay.getState().log).toMatchObject([{ outcome: 'refused' }])
    relay.stop()
  })
  it('holds the site’s USB lock for the whole session, so the site’s own reads wait', async () => {
    const unit = fakeUnit('base'), [device] = await unit.usb.getDevices(), locks = tabLocks()
    const held = await holdUnit(device, locks)
    let ran = false
    const waiting = locks.request(USB_LOCK, {}, async () => { ran = true })
    await settle(); expect(ran).toBe(false)
    await held.release(); await waiting
    expect(ran).toBe(true)
    // A sync that holds the lock keeps a session from starting.
    let finish
    void locks.request(USB_LOCK, {}, () => new Promise(resolve => { finish = resolve }))
    await expect(holdUnit(device, locks, 50)).rejects.toThrow(/busy with a sync/)
    finish()
  })
  it('ends on time, and tells both sides', async () => {
    const { core, member, remote, finished } = await session()
    core.end('time'); await settle()
    expect(finished).toMatchObject([{ reason: 'time' }])
    expect(member.getState()).toMatchObject({ status: 'ended', ended: 'time' })
    expect(remote.state().ended).toBe('time')
    await expect(remote.unit.controlTransferIn({ requestType: 'vendor', recipient: 'interface', request: 3, value: 0, index: 5 }, 72)).rejects.toThrow(/ended/)
  })
  it('passes the administrator’s message to the member’s banner', async () => {
    const { remote, member } = await session({ hopDelay: 10 })
    try {
      remote.say('Please switch the Octatrack off and on, then plug it back in.')
      await vi.waitFor(() => expect(member.getState().messages.map(message => message.text)).toEqual(['Please switch the Octatrack off and on, then plug it back in.']))
    } finally { remote.end() }
  })
  it('fails the administrator’s waiting requests when the member’s browser goes away', async () => {
    const { remote, member, device } = await session()
    vi.spyOn(device, 'controlTransferIn').mockImplementation(() => new Promise(() => {}))
    const reading = remote.unit.controlTransferIn({ requestType: 'vendor', recipient: 'interface', request: 3, value: 0, index: 5 }, 72)
    await settle()
    member.stop('lost')
    await expect(reading).rejects.toThrow(/disconnected/)
    remote.end()
  })
})
