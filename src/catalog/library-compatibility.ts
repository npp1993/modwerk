import { selectionConflicts, type SelectionConflict } from './selection-conflicts'
import { addBlocks, type AddBlock } from './add-blocks'
import { moduleUsbOnly, type PackageList } from './usb-only'
import { MODULES } from './modules'

/** Baked/card placement belongs to the card checkout. USB sets use published
 * package checks and the unit's resource/ownership admission when they sync.
 * This changes library feedback only; it never authorizes a package or load.
 * Without the beta interface (no USB sync) a USB-only module cannot be added at all. */
export function libraryCompatibility(beta: boolean, ids: readonly string[], keepStockFx2: boolean, candidates: readonly string[], published?: PackageList): { conflicts: SelectionConflict[]; blocks: Record<string, AddBlock> } {
  if (beta) return { conflicts: [], blocks: {} }
  const blocks = addBlocks(ids, keepStockFx2, candidates)
  for (const id of candidates) if (!ids.includes(id) && moduleUsbOnly(id, published)) blocks[id] = usbOnlyBlock(id)
  return { conflicts: selectionConflicts(ids, keepStockFx2), blocks }
}

export function usbOnlyBlock(id: string): AddBlock {
  const name = MODULES.find(module => module.id === id)?.name ?? id
  return { kind: 'usb-only', withIds: [], reason: 'USB only, in the beta', key: 'usb-only:' + id,
    detail: name + ' needs the Modwerk base, loaded over USB, which is in the beta for now. Card firmware has no base, so it cannot include ' + name + '.' }
}
