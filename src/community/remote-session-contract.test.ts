import { describe, expect, it } from 'vitest'
import { encodeUploadRequest } from '../engine/elekloader/upload-wire'
import { parseMemberMessage, parseOperatorMessage, REMOTE_HELLO, remoteTransferRefusal, toBase64, fromBase64 } from './remote-session-contract'

const read = (request: number, value = 0, length = 64, index = 5) => ({ direction: 'in' as const, request, value, index, length })
const hello = encodeUploadRequest({ command: 'hello' })

describe('the read-only remote session allowlist', () => {
  it('knows HELLO’s exact bytes', () => { expect(Array.from(REMOTE_HELLO)).toEqual(Array.from(hello)) })
  it('passes the link’s reads and HELLO on the Modwerk interface only', () => {
    for (const request of [2, 3, 14, 21, 27, 29, 30, 37]) expect(remoteTransferRefusal('read', read(request), 5)).toBeNull()
    expect(remoteTransferRefusal('read', { direction: 'out', request: 1, value: 7, index: 5, data: hello }, 5)).toBeNull()
    expect(remoteTransferRefusal('read', read(3, 0, 64, 0), 5)).toMatch(/Modwerk interface/)
    expect(remoteTransferRefusal('read', read(3), null)).toMatch(/No Octatrack/)
  })
  it('refuses every write, self-test start, saved-file export and unknown request', () => {
    expect(remoteTransferRefusal('read', read(21, 1), 5)).toMatch(/self-test/)
    for (const request of [1, 31, 32, 33, 34, 35, 36, 0, 255]) expect(remoteTransferRefusal('read', read(request), 5)).not.toBeNull()
    const enter = encodeUploadRequest({ command: 'enter', session: 'a'.repeat(64) })
    const begin = encodeUploadRequest({ command: 'begin', transaction: 1, session: 'a'.repeat(64), base: 'b'.repeat(64), digest: 'c'.repeat(64), generation: 1, length: 10 })
    for (const data of [enter, begin, hello.slice(0, 47), Uint8Array.from([...hello.slice(0, 47), 1])]) expect(remoteTransferRefusal('read', { direction: 'out', request: 1, value: 1, index: 5, data }, 5)).not.toBeNull()
    expect(remoteTransferRefusal('read', { direction: 'out', request: 2, value: 1, index: 5, data: hello }, 5)).not.toBeNull()
    expect(remoteTransferRefusal('read', read(3, 0, 4097), 5)).toMatch(/length/)
  })
})

describe('relay messages', () => {
  it('accept only the documented shapes', () => {
    expect(parseOperatorMessage(JSON.stringify({ type: 'transfer', id: 1, direction: 'in', request: 3, value: 0, index: 5, length: 72 }))).toMatchObject({ request: 3 })
    expect(parseOperatorMessage(JSON.stringify({ type: 'transfer', id: 1, direction: 'out', request: 1, value: 0, index: 5, data: toBase64(hello) }))).toMatchObject({ direction: 'out' })
    expect(parseOperatorMessage(JSON.stringify({ type: 'transfer', id: 1, direction: 'in', request: 3, value: 0, index: 5, length: 72, extra: 1 }))).toBeNull()
    expect(parseOperatorMessage(JSON.stringify({ type: 'transfer', id: 1, direction: 'out', request: 1, value: 0, index: 5, data: toBase64(new Uint8Array(4097)) }))).toBeNull()
    expect(parseOperatorMessage(JSON.stringify({ type: 'say', text: 'Please power-cycle it.' }))).toEqual({ type: 'say', text: 'Please power-cycle it.' })
    expect(parseOperatorMessage(JSON.stringify({ type: 'say', text: 'x'.repeat(301) }))).toBeNull()
    expect(parseOperatorMessage('not json')).toBeNull()
    expect(parseMemberMessage(JSON.stringify({ type: 'reply', id: 4, status: 'ok', data: toBase64(Uint8Array.of(1, 2)) }))).toMatchObject({ id: 4 })
    expect(parseMemberMessage(JSON.stringify({ type: 'device', vendorInterface: 5, model: 'OCTATRACK MKII' }))).toMatchObject({ vendorInterface: 5 })
    expect(parseMemberMessage(JSON.stringify({ type: 'device', vendorInterface: 300 }))).toBeNull()
    expect(parseMemberMessage(JSON.stringify({ type: 'reply', id: 4, status: 'maybe' }))).toBeNull()
    expect(Array.from(fromBase64(toBase64(Uint8Array.of(0, 255, 7))))).toEqual([0, 255, 7])
  })
})
