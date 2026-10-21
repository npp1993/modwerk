import { useEffect, type RefObject } from 'react'

const backgrounds = new WeakMap<HTMLElement, { users: number; wasInert: boolean }>()
const controls = 'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]'

// Sheets render beside the app in a body portal. Their scrim must also block keyboard and
// assistive-technology access to the covered app, and dismissal must return focus after inert is removed.
export function useSheetFocus(open: boolean, panel: RefObject<HTMLElement | null>, trigger: RefObject<HTMLElement | null>, initialFocus?: string) {
  useEffect(() => {
    const currentPanel = panel.current
    if (!open || !currentPanel) return
    const sheet = currentPanel, returnTo = trigger.current
    const covered = [...document.body.children].filter((element): element is HTMLElement =>
      element instanceof HTMLElement && !element.contains(sheet) && !element.matches('.sheet-scrim, .mobile-menu-scrim, script, style, link'))
    for (const element of covered) {
      const state = backgrounds.get(element) ?? { users: 0, wasInert: element.hasAttribute('inert') }
      state.users++
      backgrounds.set(element, state)
      element.setAttribute('inert', '')
    }
    function focusable() {
      return [...sheet.querySelectorAll<HTMLElement>(controls)].filter(element => element.tabIndex >= 0
        && !element.closest('[hidden], [inert]') && getComputedStyle(element).display !== 'none' && getComputedStyle(element).visibility !== 'hidden')
    }
    const first = () => (initialFocus ? sheet.querySelector<HTMLElement>(initialFocus) : null) ?? focusable()[0] ?? sheet
    first().focus()
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Tab') return
      const items = focusable(), index = items.indexOf(document.activeElement as HTMLElement)
      if (!items.length || index < 0 || event.shiftKey && index === 0 || !event.shiftKey && index === items.length - 1) {
        event.preventDefault()
        const next = event.shiftKey ? items.at(-1) ?? sheet : items[0] ?? sheet
        next.focus()
      }
    }
    function onFocus(event: FocusEvent) {
      if (!sheet.contains(event.target as Node)) first().focus()
    }
    sheet.addEventListener('keydown', onKey)
    document.addEventListener('focusin', onFocus)
    return () => {
      sheet.removeEventListener('keydown', onKey)
      document.removeEventListener('focusin', onFocus)
      for (const element of covered) {
        const state = backgrounds.get(element)!
        if (--state.users) continue
        if (!state.wasInert) element.removeAttribute('inert')
        backgrounds.delete(element)
      }
      // A sheet may hand off to another dialog; do not take focus back from that dialog.
      if (returnTo?.isConnected && (document.activeElement === document.body || sheet.contains(document.activeElement))) returnTo.focus()
    }
  }, [open, panel, trigger, initialFocus])
}
