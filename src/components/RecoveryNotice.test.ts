// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { FaqPage } from './FaqPage'
import { FirmwareBuildPanel } from './FirmwareBuildPanel'
import { RecoveryNotice } from './RecoveryNotice'
import { RECOVERY_FAQ, type RecoveryMachine } from './recovery-faq'
import type { useFirmwareBuild } from '../hooks/useFirmwareBuild'

vi.mock('../community/usage', () => ({trackFirmwareDownload: vi.fn()}))
let root: Root, container: HTMLDivElement
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(() => root.unmount()); container.remove(); vi.unstubAllGlobals() })
const notice = (machine: RecoveryMachine) => act(() => root.render(createElement(RecoveryNotice, {machine, steps: 'Hold FUNC while powering on.', checked: false, onChange: vi.fn()})))
const link = () => container.querySelector('.recovery-notice a')

it('links every machine to a FAQ answer that exists', async () => {
  await act(() => root.render(createElement(FaqPage)))
  for (const id of new Set(Object.values(RECOVERY_FAQ))) expect(container.querySelector('#faq-' + id), id).not.toBeNull()
})

it('sends each machine to its own recovery answer, in a new tab', async () => {
  for (const [machine, href] of [['octatrack', '#faq/recover'], ['digitakt', '#faq/digi-recovery'], ['digitone', '#faq/digi-recovery']] as const) {
    await notice(machine)
    expect(link()?.getAttribute('href'), machine).toBe(href)
    expect(link()?.getAttribute('target')).toBe('_blank')
  }
})

it('says the card for the Octatrack and keeps the bootloader promise to elekloader builds', async () => {
  await notice('octatrack')
  expect(container.textContent).toContain('Flash it from the CompactFlash card')
  expect(container.textContent).not.toContain('bootloader')
  await notice('digitakt')
  expect(container.textContent).toContain('the bootloader is never touched')
  expect(container.textContent).toContain('Elektron Transfer')
})

const built = (sha256: string) => ({key: 'octatrack-build', state: 'built', phase: undefined, report: undefined, result: {buffer: new ArrayBuffer(4), sha256},
  build: vi.fn(), cancel: vi.fn(), retry: vi.fn(), canRetry: false}) as unknown as ReturnType<typeof useFirmwareBuild>
const panel = (sha256: string) => act(() => root.render(createElement(FirmwareBuildPanel, {build: built(sha256), available: true, downloadsEnabled: true, firmwareReady: true,
  moduleCount: 1, riskAccepted: true, configurationName: 'Live', onExport: vi.fn(), exported: false, results: null})))
const download = () => [...container.querySelectorAll('button')].find(button => button.textContent?.includes('Download .bin'))!

it('holds the Octatrack .bin until the box is ticked, and asks again for another file', async () => {
  await panel('a'.repeat(64))
  expect(link()?.getAttribute('href')).toBe('#faq/recover')
  expect(container.querySelector('.recovery-notice')?.textContent).toContain('If the custom OS does not start: Hold FUNC while powering on, choose MIDI UPGRADE and send the stock .syx over DIN MIDI.')
  expect(download().disabled).toBe(true)
  await act(() => container.querySelector<HTMLInputElement>('.recovery-notice input')!.click())
  expect(download().disabled).toBe(false)
  await panel('b'.repeat(64))
  expect(download().disabled).toBe(true)
})
