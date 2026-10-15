import { afterEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import type { DiagnosticPreference } from '../community/octatrack-diagnostics'

afterEach(() => { vi.unstubAllGlobals(); vi.resetModules() })

describe('beta tester note', () => {
  it('names the channel and the tester, warns, and offers only Leave beta or Join Discord, both locked at first', async () => {
    const { OwnerNote } = await import('./OwnerNote')
    const html = renderToStaticMarkup(createElement(OwnerNote, { username: 'tester_1', onJoin() {}, onLeave() {} }))
    expect(html).toContain('#beta-tester')
    expect(html).toContain('@tester_1')
    expect(html).toContain('pass your place on to someone else')
    expect(html).toContain('as they happen')
    expect(html).toContain('roll back to the stock firmware')
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Leave beta<\/button>/)
    expect(html).toMatch(new RegExp(`<a[^>]*href="${DEVELOPMENT_DISCORD_URL}"[^>]*aria-disabled="true"[^>]*>.*Join Discord \\(10\\)</a>`))
    expect(html.match(/<button|<a /g)).toHaveLength(2)
  })

  it('asks for diagnostics afterwards unless sharing is already on or unavailable', async () => {
    const { askForDiagnostics } = await import('./OwnerNote')
    const preference = { available: true, enabled: false } as DiagnosticPreference
    expect(askForDiagnostics(preference, false)).toBe(true)
    expect(askForDiagnostics({ ...preference, enabled: true }, false)).toBe(false)
    expect(askForDiagnostics({ ...preference, available: false }, false)).toBe(false)
    expect(askForDiagnostics(preference, true)).toBe(false)
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
