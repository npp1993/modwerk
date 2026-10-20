// @vitest-environment jsdom
import { act, createElement } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, expect, it, vi } from 'vitest'
import { OwnerNote } from './OwnerNote'

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); document.body.replaceChildren() })

it('opens Discord only once the countdown ran out and the tester accepted the note', async () => {
  vi.useFakeTimers(); vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  const onJoin = vi.fn(), container = document.createElement('div'); document.body.append(container)
  const root = createRoot(container)
  await act(() => root.render(createElement(OwnerNote, { username: 'tester_1', onJoin, onLeave() {} })))
  const join = () => container.querySelector<HTMLAnchorElement>('a.button-primary')!
  const click = () => join().dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  for (let second = 0; second < 15; second++) await act(() => { vi.advanceTimersByTime(1000) })
  expect(join().textContent).toBe('Accept & join Discord')
  expect(join().getAttribute('aria-disabled')).toBe('true')
  expect(click()).toBe(false); expect(onJoin).not.toHaveBeenCalled()
  await act(() => container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click())
  expect(join().getAttribute('aria-disabled')).toBe('false')
  join().addEventListener('click', event => event.preventDefault())
  await act(() => { click() })
  expect(onJoin).toHaveBeenCalledOnce()
  await act(() => root.unmount())
})

it('opens again when the browser closes it without a choice, as Chrome does on a second Escape', async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  const container = document.createElement('div'); document.body.append(container)
  const root = createRoot(container)
  await act(() => root.render(createElement(OwnerNote, { username: 'tester_1', onJoin() {}, onLeave() {} })))
  const dialog = container.querySelector('dialog')!
  const cancel = new Event('cancel', { cancelable: true })
  dialog.dispatchEvent(cancel)
  expect(cancel.defaultPrevented).toBe(true)
  await act(() => { dialog.close(); dialog.dispatchEvent(new Event('close')) })
  expect(dialog.open).toBe(true)
  await act(() => root.unmount())
  dialog.dispatchEvent(new Event('close'))
  expect(dialog.open).toBe(false)
})
