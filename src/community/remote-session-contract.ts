// SPDX-License-Identifier: GPL-3.0-or-later OR Elastic-2.0
// Copyright (c) 2026 Jannik Aßfalg (repeat98)
// Remote debug sessions: an administrator asks a member by username, the member accepts in a dialog, and the member's
// browser carries the administrator's USB requests to their Octatrack. The server relays, the member's browser decides:
// both apply the same allowlist below, and the browser is the one that holds the device. See docs/FRONTEND_MCP.md.

/** The text the member agrees to; a new purpose or scope needs a new version and a new text. */
export const REMOTE_SESSION_CONSENT_VERSION = '2026-10-20.1'
export const REMOTE_SESSION_MINUTES = { least: 5, most: 60, default: 30 } as const
/** An unanswered request lapses after this long. */
export const REMOTE_REQUEST_MINUTES = 10
export const REMOTE_REASON_MAX = 300
export const REMOTE_SAY_MAX = 300
/** Largest data stage either way: one 4 KiB control transfer, as WebUSB on Windows allows. */
export const REMOTE_TRANSFER_MAX = 4096
/** Stage 1 is read-only; writes (trial, undo, keep) are a later, separately consented scope. */
export type RemoteScope = 'read'
export const REMOTE_SCOPES: readonly RemoteScope[] = ['read']

/** The vendor requests a read-only session may make, each answered without changing the unit (upload-usb.ts). */
export const REMOTE_READ_REQUESTS: Readonly<Record<number, string>> = {
  2: 'result', 3: 'identify', 14: 'missing modules', 21: 'self-test record', 27: 'inventory', 29: 'capabilities', 30: 'live load', 37: 'device log',
}
const SUBMIT = 1, SELFTEST = 21
/** HELLO is the one read-only frame (upload-wire.ts encodeUploadRequest): the 48-byte header with "MWUP", version 1 and
 * command 0, and no transaction, session or body, so every other byte is zero. Written out here so the Worker stays free
 * of the GPL-only USB code; remote-session-contract.test.ts checks it against the encoder. */
export const REMOTE_HELLO = Uint8Array.from({ length: 48 }, (_, i) => [0x4d, 0x57, 0x55, 0x50, 0, 1][i] ?? 0)
const HELLO = REMOTE_HELLO

export interface RemoteTransfer { direction: 'in' | 'out'; request: number; value: number; index: number; length?: number; data?: Uint8Array }

/** Why a transfer is refused, or null when the scope allows it. `vendorInterface` is the Modwerk interface the member's
 * browser found; nothing else on the unit (audio, storage) is ever addressed. */
export function remoteTransferRefusal(scope: RemoteScope, transfer: RemoteTransfer, vendorInterface: number | null): string | null {
  if (vendorInterface === null) return 'No Octatrack with the Modwerk base is connected.'
  if (transfer.index !== vendorInterface) return 'Only the Modwerk interface can be addressed.'
  if (!Number.isInteger(transfer.value) || transfer.value < 0 || transfer.value > 0xffff) return 'Invalid request value.'
  if (scope !== 'read') return 'Unknown session scope.'
  if (transfer.direction === 'in') {
    if (!Object.hasOwn(REMOTE_READ_REQUESTS, transfer.request)) return 'This request is not part of a read-only session.'
    // Value 1 starts a self-test, which runs the installed modules; reading the record is value 0.
    if (transfer.request === SELFTEST && transfer.value !== 0) return 'Starting a self-test is not part of a read-only session.'
    if (!Number.isInteger(transfer.length) || transfer.length! < 1 || transfer.length! > REMOTE_TRANSFER_MAX) return 'Invalid read length.'
    return null
  }
  const data = transfer.data
  if (transfer.request !== SUBMIT || !data || data.length !== HELLO.length || data.some((byte, i) => byte !== HELLO[i])) return 'Only reads and HELLO are part of a read-only session.'
  return null
}

// The relay's messages, as JSON text frames. Bytes travel as base64.
export type OperatorMessage =
  | { type: 'transfer'; id: number; direction: 'in'; request: number; value: number; index: number; length: number }
  | { type: 'transfer'; id: number; direction: 'out'; request: number; value: number; index: number; data: string }
  | { type: 'say'; text: string }
  | { type: 'end' }
export type ReplyStatus = 'ok' | 'stall' | 'refused' | 'failed'
export type MemberMessage =
  | { type: 'reply'; id: number; status: ReplyStatus; data?: string; bytesWritten?: number; reason?: string }
  | { type: 'device'; vendorInterface: number | null; model?: string }
  | { type: 'end' }
export type RelayMessage =
  | { type: 'presence'; member: boolean; operator: boolean; endsAt: string; vendorInterface: number | null; model?: string }
  | { type: 'say'; text: string }
  | { type: 'reply'; id: number; status: ReplyStatus; data?: string; bytesWritten?: number; reason?: string }
  | { type: 'ended'; reason: 'member' | 'operator' | 'time' | 'replaced' }

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const u16 = (value: unknown) => Number.isInteger(value) && (value as number) >= 0 && (value as number) <= 0xffff
const keys = (value: Record<string, unknown>, names: string) => Object.keys(value).sort().join(',') === names
const BASE64 = /^[A-Za-z0-9+/]*={0,2}$/
const base64Bytes = (text: string) => Math.floor(text.length / 4) * 3 - (text.endsWith('==') ? 2 : text.endsWith('=') ? 1 : 0)
/** Control characters other than tab and newline, which a member's dialog or banner must never show. */
export const hasControl = (text: string) => [...text].some(char => { const code = char.charCodeAt(0); return code < 32 && code !== 9 && code !== 10 || code === 127 })
const shortText = (value: unknown, most: number) => typeof value === 'string' && value.trim().length > 0 && value.length <= most && !hasControl(value)

function parse(raw: unknown): Record<string, unknown> | null {
  if (typeof raw !== 'string' || raw.length > 8192) return null
  try { const value = JSON.parse(raw) as unknown; return object(value) ? value : null } catch { return null }
}
/** A message from the administrator's side, or null when it is not one of the documented shapes. */
export function parseOperatorMessage(raw: unknown): OperatorMessage | null {
  const value = parse(raw)
  if (!value) return null
  if (value.type === 'end') return keys(value, 'type') ? { type: 'end' } : null
  if (value.type === 'say') return keys(value, 'text,type') && shortText(value.text, REMOTE_SAY_MAX) ? { type: 'say', text: value.text as string } : null
  if (value.type !== 'transfer' || !Number.isSafeInteger(value.id) || (value.id as number) < 0 || !u16(value.request) || !u16(value.value) || !u16(value.index)) return null
  if (value.direction === 'in') return keys(value, 'direction,id,index,length,request,type,value') && Number.isInteger(value.length) && (value.length as number) >= 1 && (value.length as number) <= REMOTE_TRANSFER_MAX ? value as OperatorMessage : null
  if (value.direction === 'out') return keys(value, 'data,direction,id,index,request,type,value') && typeof value.data === 'string' && value.data.length % 4 === 0 && BASE64.test(value.data) && base64Bytes(value.data) <= REMOTE_TRANSFER_MAX ? value as OperatorMessage : null
  return null
}
/** A message from the member's browser, or null when it is not one of the documented shapes. */
export function parseMemberMessage(raw: unknown): MemberMessage | null {
  const value = parse(raw)
  if (!value) return null
  if (value.type === 'end') return keys(value, 'type') ? { type: 'end' } : null
  if (value.type === 'device') {
    const allowed = Object.keys(value).every(key => ['type', 'vendorInterface', 'model'].includes(key))
    return allowed && (value.vendorInterface === null || Number.isInteger(value.vendorInterface) && (value.vendorInterface as number) >= 0 && (value.vendorInterface as number) <= 255)
      && (value.model === undefined || shortText(value.model, 32)) ? value as MemberMessage : null
  }
  if (value.type !== 'reply' || !Number.isSafeInteger(value.id) || !['ok', 'stall', 'refused', 'failed'].includes(value.status as string)) return null
  if (!Object.keys(value).every(key => ['type', 'id', 'status', 'data', 'bytesWritten', 'reason'].includes(key))) return null
  if (value.data !== undefined && (typeof value.data !== 'string' || value.data.length % 4 !== 0 || !BASE64.test(value.data) || base64Bytes(value.data) > REMOTE_TRANSFER_MAX)) return null
  if (value.bytesWritten !== undefined && !(Number.isInteger(value.bytesWritten) && (value.bytesWritten as number) >= 0 && (value.bytesWritten as number) <= REMOTE_TRANSFER_MAX)) return null
  if (value.reason !== undefined && !shortText(value.reason, 200)) return null
  return value as MemberMessage
}

export function toBase64(bytes: Uint8Array) { let text = ''; for (const byte of bytes) text += String.fromCharCode(byte); return btoa(text) }
export function fromBase64(text: string) { return Uint8Array.from(atob(text), char => char.charCodeAt(0)) }

/** What the member and the administrator see of a session. */
export interface RemoteSessionView {
  id: string; status: 'pending' | 'declined' | 'active' | 'ended' | 'expired'; scope: RemoteScope
  requester: string; member?: string; reason: string; minutes: number
  createdAt: string; expiresAt: string | null; answeredAt: string | null; endsAt: string | null; endedAt: string | null; endedBy: string | null
  summary?: Record<string, number> | null
}
