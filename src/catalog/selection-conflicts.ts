import { DSP_EFFECT_IDS, resolveSelection } from './modules.ts'
import { MODULE_DOCUMENTS_BY_ID } from './documents.ts'
import pairs from './compatibility-pairs.json' with { type: 'json' }
import { pairClash, selectionKey, type PairChecks } from './compatibility-checks.ts'
const CHECKS = pairs as PairChecks

export type ConflictFix = { label: string; removeIds?: string[]; keepStockFx2?: boolean }
export type SelectionConflict = { id: string; title: string; description: string; moduleIds: string[]; fixes: ConflictFix[] }
// Only these custom effects have reviewed placements beside Analog BD. Output Matrix is not one yet.
const analogBdCompanions = ['miniverb', 'tapeecho', 'euclid', 'tapehead', 'sidechain-compressor', 'airwindows-chorus']
// These build beside the stock FX2 effects: TapeHead fits in the space they leave, and Sidechain
// Compressor hooks stock COMPRESSOR instead of taking a slot. Every other DSP effect needs their space.
const FITS_BESIDE_STOCK_FX2 = ['tapehead', 'sidechain-compressor']
const crowdedMenuIds = ['miniverb', 'tapeecho', 'euclid', 'repitch', 'quantizer']
// shortcut: flags these versions still carry although each module is a reviewed Analog BD companion; their package
// recipes pin the manifest, so each leaves at its module's next version (selection-conflicts.test.ts fails until it does).
export const STALE_CONFLICT_FLAGS = ['analog-bassdrum+sidechain-compressor', 'analog-bassdrum+tapehead']
const flagged = (a: string, b: string) => !STALE_CONFLICT_FLAGS.includes(selectionKey([a, b])) &&
  (MODULE_DOCUMENTS_BY_ID[a]?.compatibility.conflicts.includes(b) || MODULE_DOCUMENTS_BY_ID[b]?.compatibility.conflicts.includes(a))
// A flag that names a collision the ledger finds stands down where the selection's context resolves it (POLY8's shared machine list).
const collides = (a: string, b: string) => Object.values(CHECKS.clashes).some(found => found[selectionKey([a, b])])

export function selectionConflicts(ids: readonly string[], keepStockFx2 = false): SelectionConflict[] {
  const modules = resolveSelection(ids), selected = new Set(modules.map(module => module.id))
  const dsp = modules.filter(module => DSP_EFFECT_IDS.includes(module.id))
  const analogBdBlockers = dsp.filter(module => !analogBdCompanions.includes(module.id))
  const conflicts: SelectionConflict[] = []
  if (selected.has('midi-scenes') && modules.length > 1) {
    const companions = modules.filter(module => module.id !== 'midi-scenes')
    conflicts.push({ id: 'midi-scenes-standalone', title: 'Build MIDI Scenes on its own',
      description: 'MIDI Scenes currently supports standalone firmware. Remove the other modules to build this configuration.',
      moduleIds: modules.map(module => module.id),
      fixes: [{ label: 'Keep MIDI Scenes', removeIds: companions.map(module => module.id) }, { label: 'Remove MIDI Scenes', removeIds: ['midi-scenes'] }] })
  }
  if (selected.has('analog-bassdrum') && analogBdBlockers.length) conflicts.push({
    id: 'analog-bd-custom-dsp', title: 'Choose effects that fit with Analog BD',
    description: 'Analog BD can share effect memory with Mini Verb, Tape Echo, Euclid, TapeHead, Sidechain Compressor and Air Chorus, subject to space. It cannot run alongside ' + analogBdBlockers.map(module => module.name).join(', ') + '.',
    moduleIds: ['analog-bassdrum', ...analogBdBlockers.map(module => module.id)],
    fixes: [{ label: 'Remove Analog BD', removeIds: ['analog-bassdrum'] }, { label: 'Keep Analog BD · remove incompatible effects', removeIds: analogBdBlockers.map(module => module.id) }],
  })
  const stockFx2Dsp = dsp.filter(module => !FITS_BESIDE_STOCK_FX2.includes(module.id))
  if (keepStockFx2 && (stockFx2Dsp.length || selected.has('analog-bassdrum'))) conflicts.push({
    id: 'stock-fx2-space', title: 'Make room for your modules',
    description: 'These modules need space used by the original FX2 effects. Turn off “Keep stock FX2 effects” to continue. Original FX1 effects stay available.',
    moduleIds: [...stockFx2Dsp.map(module => module.id), ...(selected.has('analog-bassdrum') ? ['analog-bassdrum'] : [])],
    fixes: [{ label: 'Turn off stock FX2', keepStockFx2: false }],
  })
  // Native matrix: this five-module subset exhausts menu space, regardless
  // of additional MIDI Scenes or USB Audio units in DRAM.
  if (!keepStockFx2 && crowdedMenuIds.every(id => selected.has(id))) conflicts.push({
    id: 'module-menu-space', title: 'This selection needs more menu space',
    description: 'Mini Verb, Tape Echo, Euclid, Repitch and Scale Quantizer need more menu space than the Octatrack has available together. Removing Euclid keeps every other selected module.',
    moduleIds: crowdedMenuIds,
    fixes: [{ label: 'Remove Euclid', removeIds: ['euclid'] }],
  })
  // Every pair the native ledger refuses in this selection's context, and every pair an author flagged as incompatible.
  for (const [index, left] of modules.entries()) for (const right of modules.slice(index + 1)) {
    if (conflicts.some(conflict => conflict.moduleIds.includes(left.id) && conflict.moduleIds.includes(right.id))) continue
    const clash = pairClash(CHECKS, [...selected], left.id, right.id)
    if (!clash.length && !(flagged(left.id, right.id) && !collides(left.id, right.id))) continue
    conflicts.push({ id: 'pair-' + selectionKey([left.id, right.id]), title: 'Choose ' + left.name + ' or ' + right.name,
      description: left.name + ' and ' + right.name + (clash.length ? ' change the same part of the firmware.' : ' are marked as incompatible by their authors.') + ' Build them separately.',
      moduleIds: [left.id, right.id],
      fixes: [{ label: 'Keep ' + left.name, removeIds: [right.id] }, { label: 'Keep ' + right.name, removeIds: [left.id] }],
    })
  }
  return conflicts
}
export function selectionConflictError(ids: readonly string[], keepStockFx2 = false) {
  return selectionConflicts(ids, keepStockFx2).map(conflict => conflict.title + '. ' + conflict.description).join(' ')
}
