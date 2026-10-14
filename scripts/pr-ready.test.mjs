import { describe, expect, it } from 'vitest'
import { readiness } from './pr-ready.mjs'

describe('pr:ready verdict', () => {
  it('is ready only with a committed, current, regenerated branch whose checks pass', () => {
    expect(readiness({}).ok).toBe(true)
    for (const state of [{ dirty: ['a.ts'] }, { behind: true }, { regenerated: ['src/catalog/module-documents.json'] }, { checkPassed: false }]) expect(readiness(state).ok).toBe(false)
  })
  it('says how to bring a stale branch up to date from the remote that holds main', () => {
    expect(readiness({ behind: true, remote: 'upstream' }).problems[0]).toContain('git merge upstream/main')
  })
  it('names the generated files to commit', () => {
    expect(readiness({ regenerated: ['src/catalog/module-documents.json'] }).problems[0]).toContain('src/catalog/module-documents.json')
  })
  it('tells an author whether the bot can merge the update, and why not', () => {
    expect(readiness({ author: 'octo', scope: { modules: ['digieq'] } }).notes[0]).toContain('Automatic merge')
    const refused = readiness({ author: 'octo', scope: { error: 'Licence text changes require owner review.' } })
    expect(refused.ok).toBe(false)
    expect(refused.problems[0]).toContain('Licence text changes require owner review.')
  })
  it('tells everyone else that the owner merges once CI is green, and to rerun when main moves', () => {
    const { notes } = readiness({})
    expect(notes[0]).toContain('owner reviews it and merges it with one click')
    expect(notes.at(-1)).toContain('If main moves before the merge, run this again')
  })
})
