// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DigiBuildPanel } from './DigiBuildPanel'
import type { DigiMachine } from '../devices/digi-mods'
import type { useDigiFirmware } from '../hooks/useDigiFirmware'

const mocks = vi.hoisted(() => ({phase: 'built', sha256: 'a'.repeat(64), recovery: 'hold FUNC while powering on for the startup menu, then send the stock .syx'}))
vi.mock('../community/usage', () => ({trackFirmwareDownload: vi.fn()}))
vi.mock('../hooks/useDigiBuild', () => ({useDigiBuild: () => ({
  state: {phase: mocks.phase, key: 'build', moduleIds: ['digihealth'],
    device: {default_version: '2.0a', version_len: 4},
    result: {version: '2.0a', files: [{name: 'preview.syx', data: new ArrayBuffer(4)}], bytes: 4, seconds: 1, mods: [], sha256: mocks.sha256, recovery: mocks.recovery}},
  check: vi.fn(), build: vi.fn(), cancel: vi.fn(),
})}))
let root: Root, container: HTMLDivElement
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => {
  await act(() => root.unmount()); container.remove(); vi.unstubAllGlobals()
  mocks.phase = 'built'; mocks.sha256 = 'a'.repeat(64); mocks.recovery = 'hold FUNC while powering on for the startup menu, then send the stock .syx'
})
const render = (machine: DigiMachine = 'digitakt', recovery?: string) => act(() => root.render(createElement(DigiBuildPanel, {
  device: {id: machine, name: machine, firmware: recovery ? {recovery} : undefined}, firmware: {state: 'empty'} as ReturnType<typeof useDigiFirmware>,
  moduleIds: ['digihealth'], onExport: vi.fn(), exported: false, canExport: false, results: null})))
const notice = () => container.querySelector('.recovery-notice')
const download = () => [...container.querySelectorAll('button')].find(button => button.textContent?.includes('Download .syx'))!
const box = (label: string) => [...container.querySelectorAll('label')].find(item => item.textContent?.includes(label))!.querySelector('input')!

it('says how to get back to stock after a build and holds the download until it is ticked', async () => {
  await render()
  expect(notice()?.textContent).toContain('Before you flash: how to get back to stock')
  expect(notice()?.textContent).toContain('If the custom OS does not start: hold FUNC while powering on for the startup menu, then send the stock .syx.')
  expect(notice()?.querySelector('a')?.getAttribute('href')).toBe('#faq/digi-recovery')
  expect(notice()?.querySelector('a')?.target).toBe('_blank')
  expect(download().disabled).toBe(true)
  await act(() => box('I understand the risks').click())
  expect(download().disabled).toBe(true)
  await act(() => box('I know how to get my unit back to stock').click())
  expect(download().disabled).toBe(false)
  await act(() => box('I know how to get my unit back to stock').click())
  expect(download().disabled).toBe(true)
})

it('keeps the tick for a rebuild of the same file and asks again for a different one', async () => {
  await render()
  await act(() => box('I understand the risks').click())
  await act(() => box('I know how to get my unit back to stock').click())
  expect(download().disabled).toBe(false)
  await render()
  expect(download().disabled).toBe(false)
  mocks.sha256 = 'b'.repeat(64)
  await render()
  expect(box('I know how to get my unit back to stock').checked).toBe(false)
  expect(download().disabled).toBe(true)
})

it('falls back to the machine registry steps, ending in one full stop', async () => {
  mocks.recovery = ''
  await render('digitone', 'Hold FUNC while powering on, choose OS UPGRADE and send the stock .syx.')
  expect(notice()?.querySelector('p')?.textContent).toMatch(/If the custom OS does not start: Hold FUNC while powering on, choose OS UPGRADE and send the stock \.syx\.$/)
})

it('is not shown before a build or where downloads are closed', async () => {
  mocks.phase = 'ready'
  await render()
  expect(notice()).toBeNull()
  mocks.phase = 'built'
  await render('digitakt-ii')
  expect(notice()).toBeNull()
})
