// SPDX-License-Identifier: GPL-3.0-or-later
// A module whose published USB package needs a base DSP feature (ABI 9 `requires`, sdk/machines/octatrack/dsp-sites.json,
// such as the key bus) exists only on the Modwerk base loaded over USB. Card firmware has no base, so the configurator's
// card build refuses it; USB sync still takes it. Derived from the published package, never listed per module.
import packages from '../engine/assets/octatrack-module-packages.json' with { type: 'json' }
import { resolveSelection } from './modules.ts'

type PackageList = { packages: readonly { id: string; requires?: number }[] }
export function moduleUsbOnly(id: string, published: PackageList = packages) {
  return published.packages.some(entry => entry.id === id && (entry.requires ?? 0) !== 0)
}

export function cardBuildError(ids: readonly string[], published: PackageList = packages): string {
  const usbOnly = resolveSelection(ids).filter(module => moduleUsbOnly(module.id, published)), one = usbOnly.length === 1
  return usbOnly.length ? usbOnly.map(module => module.name).join(', ') + (one ? ' needs' : ' need') + ' the Modwerk base, so card firmware cannot include ' + (one ? 'it' : 'them') + '. Sync this set over USB, or take ' + (one ? 'it' : 'them') + ' out to build card firmware.' : ''
}
