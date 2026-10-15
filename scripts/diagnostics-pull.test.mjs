import { describe, expect, it } from 'vitest'
import { pullAll, summary } from './diagnostics-pull.mjs'

const entry = (n, username = 'tester', data = { event: 'health', phase: 'ready' }) =>
  ({ eventId: 'e' + n, username, createdAt: new Date(Date.UTC(2026, 9, 15, 0, 0, n)).toISOString(), data })

describe('diagnostics pull', () => {
  it('pages from the last record of a full page and drops the overlap', async () => {
    const all = Array.from({ length: 700 }, (_, n) => entry(n))
    const asked = []
    const result = await pullAll(async since => {
      asked.push(since)
      return { events: all.filter(row => row.createdAt >= since).slice(0, 500), counts: [{ day: '2026-10-15', event: 'usb_sync_kept', count: 2 }] }
    }, '2026-09-15T00:00:00.000Z')
    expect(asked).toEqual(['2026-09-15T00:00:00.000Z', all[499].createdAt])
    expect(result.events).toHaveLength(700)
    expect(result.counts).toHaveLength(1)
  })
  it('stops when a full page cannot move the cursor', async () => {
    let calls = 0
    const same = Array.from({ length: 500 }, (_, n) => ({ ...entry(0), eventId: 'e' + n }))
    await pullAll(async () => { calls++; return { events: same, counts: [] } }, same[0].createdAt)
    expect(calls).toBe(1)
  })
  it('lists members and problems, newest first', () => {
    const failed = entry(5, 'other', { event: 'sync_failed', phase: 'sending', error: 'device', refusal: 3, modules: [{ id: 'poly8', catalogVersion: '0.3.0' }] })
    const text = summary({ events: [entry(1), failed, entry(9, 'tester', { event: 'selftest', phase: 'testing', result: 'ok' })], counts: [{ day: '2026-10-15', event: 'usb_sync_failed', count: 1 }] })
    expect(text).toContain('3 records from 2 members')
    expect(text).toContain('@tester  last 2026-10-15T00:00  health 1, selftest 1')
    expect(text).toContain('Problems (1, newest first')
    expect(text).toContain('@other sync_failed sending error=device refusal=3 poly8@0.3.0')
    expect(text).toContain('2026-10-15  failed 1')
  })
})
