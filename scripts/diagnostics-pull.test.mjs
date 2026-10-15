import { describe, expect, it } from 'vitest'
import { members, pullAll, reportsByMember, summary, when } from './diagnostics-pull.mjs'

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
    expect(text).toContain(`@tester  last ${when(entry(9).createdAt)}\n  health 1, selftest 1`)
    expect(text).toContain('self-test peaks, not the live load')
    expect(text).toContain('Problems (1, newest first')
    expect(text).toContain(`${when(failed.createdAt)} @other sync_failed sending error=device refusal=3 poly8@0.3.0`)
    expect(text).toContain('2026-10-15  failed 1')
  })
  it('counts a reconnect back on the bare base as a restart, but not a plain reconnect', () => {
    const base = 'a'.repeat(64), set = 'b'.repeat(64), next = 'c'.repeat(64)
    const at = (n, event, active) => entry(n, 'tester', { event, phase: 'ready', base, ...active && { active } })
    const found = members([at(1, 'connected', base), at(2, 'kept', set), at(3, 'disconnected', set), at(4, 'connected', set),
      at(5, 'disconnected', set), at(6, 'connected', base), at(7, 'sync_failed', next), at(8, 'connected'), at(9, 'connected', base)]).get('tester')
    expect(found.restarts).toEqual([entry(6).createdAt, entry(9).createdAt])
    expect(found.bases).toEqual([base])
  })
  it('names each base against the site’s, the last self-test’s peaks and the member’s reports', () => {
    const old = 'a'.repeat(64), current = 'd'.repeat(64)
    const reading = { state: 3, failed: 64, ran: 3, cpu: 879, tracks1to4: 418, tracks5to8: 573 }
    const events = [entry(1, 'tester', { event: 'connected', phase: 'ready', base: old, active: old }),
      entry(2, 'tester', { event: 'selftest', phase: 'testing', base: current, reading }),
      entry(3, 'tester', { event: 'selftest', phase: 'testing', base: current, reading: { state: 2, failed: 0, ran: 0, cpu: 0, tracks1to4: 0, tracks5to8: 0 } })]
    const reports = reportsByMember([{ number: 646, title: '[poly8] freezes', state: 'OPEN', body: 'Reported on [Modwerk](https://modwerk.app/) by [tester](https://modwerk.app/forum/profile/tester/) · @repeat98' },
      { number: 1, title: 'no profile', state: 'OPEN', body: 'GitHub only' }])
    expect([...reports.keys()]).toEqual(['tester'])
    const text = summary({ events, counts: [] }, { base: current, reports })
    expect(text).toContain('base aaaaaaaa (older than the site’s dddddddd) → dddddddd (the site’s current base)')
    expect(text).toContain('  report #646 open: [poly8] freezes')
    expect(text).toContain('  last self-test passed, no DSP module ran')
    expect(text).toContain(`  highest self-test peaks ${when(entry(2).createdAt)}: CPU 87.9%, DSP T1-4 41.8%, T5-8 57.3%`)
  })
})
