import { describe, expect, it } from 'vitest'
import { requireFlaggedOverlaps, requireKnownConflicts } from './conflict-ids.mjs'

const doc = (id, version, conflicts) => ({ id, version, compatibility: { conflicts } })

describe('compatibility.conflicts ids', () => {
  it('accepts module ids of the same machine and refuses any other id by name', () => {
    const known = new Set(['a', 'b'])
    expect(() => requireKnownConflicts('digitakt', doc('a', '1.0.0', ['b']), known)).not.toThrow()
    expect(() => requireKnownConflicts('digitakt', doc('a', '1.0.0', ['b', 'bb']), known)).toThrow(/names bb,/)
    expect(() => requireKnownConflicts('digitakt', doc('a', '1.0.0', ['bb']), known)).toThrow(/names bb, which is not a digitakt module/)
  })

  it('keeps an earlier unknown id only at the exact version that carried it', () => {
    const known = new Set(['analog-bassdrum', 'synth'])
    expect(() => requireKnownConflicts('octatrack', doc('analog-bassdrum', '0.1.5-experimental', ['synth', 'machinedrum', 'poly']), known)).not.toThrow()
    expect(() => requireKnownConflicts('octatrack', doc('analog-bassdrum', '0.1.6-experimental', ['synth', 'machinedrum']), known)).toThrow(/machinedrum/)
    expect(() => requireKnownConflicts('digitakt', doc('analog-bassdrum', '0.1.5-experimental', ['machinedrum']), known)).toThrow()
  })
})

describe('overlapping Digitakt and Digitone mods', () => {
  const mod = (id, sites, conflicts = [], machine = 'digitakt') => ({ machine, id, compatibility: { conflicts }, patchSites: sites })
  it('refuses an overlap on a release both support unless one mod flags the other', () => {
    const a = mod('a', { '1.53': [{ addr: '0x40001000', len: 8 }] }), b = mod('b', { '1.53': [{ addr: '0x40001006', len: 8 }] })
    expect(() => requireFlaggedOverlaps([a, b])).toThrow(/digitakt\/a and b both patch 0x40001000 on OS 1\.53/)
    expect(() => requireFlaggedOverlaps([a, { ...b, compatibility: { conflicts: ['a'] } }])).not.toThrow()
  })
  it('allows touching ranges, other releases and other machines', () => {
    const a = mod('a', { '1.53': [{ addr: '0x40001000', len: 8 }], '1.54': [] })
    expect(() => requireFlaggedOverlaps([a, mod('b', { '1.53': [{ addr: '0x40001008', len: 8 }] })])).not.toThrow()
    expect(() => requireFlaggedOverlaps([a, mod('b', { '1.54': [{ addr: '0x40001000', len: 8 }] })])).not.toThrow()
    expect(() => requireFlaggedOverlaps([a, mod('b', { '1.53': [{ addr: '0x40001000', len: 8 }] }, [], 'digitone')])).not.toThrow()
  })
})
