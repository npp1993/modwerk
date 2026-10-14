/**
 * The native declaration checks, one pair at a time (src/catalog/compatibility-pairs.json, written by
 * `npm run modules:pairs -- --write`). octabam's ledger compares modules two at a time, except POLY8's shared
 * composition, which changes the machine modules' claims when POLY8 (and FM Synth) are selected. So the table holds,
 * per context, each module alone and each pair the ledger refuses; everything else among its modules is clean.
 * scripts/module-pairs.py proves on every check that the pairs decide every selection.
 */
export type PairChecks = { schemaVersion: 2; revision: string; modules: string[]; contexts: string[]; clashes: Record<string, Record<string, string[]>> }

export function selectionKey(ids: readonly string[]) { return [...ids].sort().join('+') }

/** The longest context whose modules the selection holds, '' for none (scripts/module-pairs.py context_of). */
export function selectionContext(checks: PairChecks, ids: readonly string[]) {
  const held = new Set(ids), size = (context: string) => context ? context.split('+').length : 0
  return checks.contexts.filter(context => !context || context.split('+').every(id => held.has(id)))
    .reduce((best, context) => size(context) > size(best) ? context : best, '')
}

/** What the ledger refuses between two modules in this selection's context; [] when they are clean together. */
export function pairClash(checks: PairChecks, ids: readonly string[], a: string, b: string) {
  return checks.clashes[selectionContext(checks, ids)]?.[selectionKey([a, b])] ?? []
}

/** The ledger's notes for a selection: [] when it is clean, undefined when a module is outside the table. */
export function recordedCheck(checks: PairChecks, ids: readonly string[]): string[] | undefined {
  if (ids.some(id => !checks.modules.includes(id))) return undefined
  const clashes = checks.clashes[selectionContext(checks, ids)] ?? {}, sorted = [...new Set(ids)].sort()
  return sorted.flatMap((a, index) => [...(clashes[a] ?? []), ...sorted.slice(index + 1).flatMap(b => clashes[a + '+' + b] ?? [])])
}
