import { afterEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import type { DiagnosticPreference } from '../community/octatrack-diagnostics'

afterEach(() => { vi.unstubAllGlobals(); vi.resetModules() })

describe('beta tester note', () => {
  it('names the channel and the tester, requires a recovery path, keeps reports off the site, and offers only Leave beta or an accepted Join Discord, both locked at first', async () => {
    const { OwnerNote } = await import('./OwnerNote')
    const html = renderToStaticMarkup(createElement(OwnerNote, { username: 'tester_1', onJoin() {}, onLeave() {} }))
    expect(html).toContain('#beta-testers')
    expect(html).toContain('@tester_1')
    expect(html).toContain('pass your place on to someone else')
    expect(html).toContain('right when you run into them')
    expect(html).toContain('recover without USB')
    expect(html).toContain('CompactFlash card reader')
    expect(html).toContain('MIDI interface')
    expect(html).toContain('don&#x27;t use the report forms on this site')
    expect(html).not.toContain('you can always roll back')
    expect(html).toMatch(/<input type="checkbox"\/><span>I&#x27;ve read this\./)
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Leave beta<\/button>/)
    expect(html).toMatch(new RegExp(`<a[^>]*href="${DEVELOPMENT_DISCORD_URL}"[^>]*aria-disabled="true"[^>]*>.*Accept &amp; join Discord \\(15\\)</a>`))
    expect(html.match(/<button|<a /g)).toHaveLength(3)
    expect(html).toContain('<a href="#faq"')
  })

  it('asks for diagnostics afterwards unless sharing is already on or unavailable', async () => {
    const { askForDiagnostics } = await import('./OwnerNote')
    const preference = { available: true, enabled: false } as DiagnosticPreference
    expect(askForDiagnostics(preference, false)).toBe(true)
    expect(askForDiagnostics({ ...preference, enabled: true }, false)).toBe(false)
    expect(askForDiagnostics({ ...preference, available: false }, false)).toBe(false)
    expect(askForDiagnostics(preference, true)).toBe(false)
  })

  it('asks again after a new consent version, but not a tester who turned sharing off under the current one', async () => {
    const { diagnosticsLapsed } = await import('./OwnerNote')
    const preference = { accountId: 'm1', ready: true, available: true, enabled: false, hasChoice: false } as DiagnosticPreference
    expect(diagnosticsLapsed(preference, 'm1', false)).toBe(true)
    expect(diagnosticsLapsed({ ...preference, hasChoice: true }, 'm1', false)).toBe(false)
    expect(diagnosticsLapsed({ ...preference, enabled: true }, 'm1', false)).toBe(false)
    expect(diagnosticsLapsed({ ...preference, ready: false }, 'm1', false)).toBe(false)
    expect(diagnosticsLapsed(preference, 'm2', false)).toBe(false)
    expect(diagnosticsLapsed(preference, 'm1', true)).toBe(false)
  })

  it('shows once per browser, and once per visit when storage is blocked', async () => {
    const storage = new Map<string, string>()
    vi.stubGlobal('localStorage', { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value) })
    let note = await import('./OwnerNote')
    expect(note.ownerNoteSeen()).toBe(false)
    note.closeOwnerNote()
    vi.resetModules(); note = await import('./OwnerNote')
    expect(note.ownerNoteSeen()).toBe(true)

    vi.stubGlobal('localStorage', { getItem() { throw new Error('blocked') }, setItem() { throw new Error('blocked') } })
    vi.resetModules(); note = await import('./OwnerNote')
    expect(note.ownerNoteSeen()).toBe(false)
    note.closeOwnerNote()
    expect(note.ownerNoteSeen()).toBe(true)
  })
})
