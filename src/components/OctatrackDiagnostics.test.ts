// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DiagnosticPreference } from '../community/octatrack-diagnostics'

const preference: DiagnosticPreference = { accountId: 'member', available: true, enabled: true, ready: true, busy: false, error: '', notice: '', hasChoice: true, saved: true, lastSent: null }
vi.mock('../community/octatrack-diagnostics', () => ({ diagnosticPreference: () => preference, subscribeDiagnosticPreference: () => () => {}, changeDiagnosticSharing: vi.fn(), collectOctatrackDiagnostics: vi.fn() }))
vi.mock('./DiagnosticsInvitation', () => ({ DiagnosticDetails: () => null, DiagnosticsInvitation: () => null }))
const { OctatrackDiagnosticsSettings } = await import('./OctatrackDiagnostics')

const containers: HTMLElement[] = []
afterEach(() => { containers.splice(0).forEach(container => container.remove()); vi.unstubAllGlobals() })
async function render(username?: string | null) {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  const container = document.createElement('div'); document.body.append(container); containers.push(container)
  await act(() => createRoot(container).render(createElement(OctatrackDiagnosticsSettings, { username })))
  return container
}

describe('diagnostics settings', () => {
  it('says which name the shared records reach the owner under', async () => {
    expect((await render('npawelczyk')).textContent).toContain('They reach me as @npawelczyk. Use the same name on Discord')
  })
  it('asks a member with a generated name to choose one', async () => {
    const link = (await render('member_6f268c45efa4')).querySelector('a[href="#account"]')
    expect(link?.textContent).toBe('choose your own')
    expect(link?.parentElement?.textContent).toContain('@member_6f268c45efa4. That name was made up by the site')
  })
  it('names nobody while sharing is off', async () => {
    preference.enabled = false
    expect((await render('npawelczyk')).textContent).not.toContain('reach me as')
    preference.enabled = true
  })
})
