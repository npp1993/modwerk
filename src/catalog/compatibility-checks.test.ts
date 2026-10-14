import { describe, expect, it } from 'vitest'
import committed from './compatibility-pairs.json'
import { pairClash, recordedCheck, selectionContext, selectionKey, type PairChecks } from './compatibility-checks'

const table: PairChecks = { schemaVersion: 2, revision: 'r', modules: ['a', 'b', 'c', 'poly8', 'synth'], contexts: ['', 'poly8', 'poly8+synth'],
  clashes: { '': { 'a+b': ['hook site: a and b both claim 0x1'] }, poly8: {}, 'poly8+synth': { c: ['c alone'] } } }
describe('pair compatibility checks', () => {
  it('picks the longest context the selection holds', () => {
    expect(selectionContext(table, ['a', 'synth'])).toBe('')
    expect(selectionContext(table, ['poly8', 'a'])).toBe('poly8')
    expect(selectionContext(table, ['synth', 'poly8', 'a'])).toBe('poly8+synth')
  })
  it('answers a selection from its modules and pairs in either order', () => {
    expect(recordedCheck(table, ['b', 'a'])).toEqual(['hook site: a and b both claim 0x1'])
    expect(recordedCheck(table, ['a', 'b', 'poly8'])).toEqual([])
    expect(recordedCheck(table, ['c', 'poly8', 'synth'])).toEqual(['c alone'])
    expect(recordedCheck(table, ['a', 'c'])).toEqual([])
    expect(pairClash(table, ['a', 'b', 'c'], 'b', 'a')).toHaveLength(1)
    expect(recordedCheck(table, ['unknown'])).toBeUndefined()
  })
  it('commits a table over the catalogue in the shape the site reads', () => {
    const checks = committed as PairChecks
    expect(checks.schemaVersion).toBe(2)
    expect(checks.contexts[0]).toBe('')
    expect(checks.modules).toEqual([...checks.modules].sort())
    for (const found of Object.values(checks.clashes)) for (const key of Object.keys(found)) {
      expect(key).toBe(selectionKey(key.split('+')))
      expect(key.split('+').every(id => checks.modules.includes(id))).toBe(true)
    }
  })
})
