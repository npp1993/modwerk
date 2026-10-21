import { describe, expect, it } from 'vitest'
import { MODULES } from './modules'
import { DIGI_MODS } from '../devices/digi-mods'
import { matchesModuleQuery, octatrackMatchesQuery, digiMatchesQuery } from './module-search'

describe('module discovery search', () => {
  it('combines words across fields in any order without requiring a phrase', () => {
    expect(matchesModuleQuery('delay tape', 'Tape Echo', 'A delay effect')).toBe(true)
    expect(matchesModuleQuery('tape unknown', 'Tape Echo', 'A delay effect')).toBe(false)
    expect(matchesModuleQuery('  ', 'Tape Echo')).toBe(true)
  })
  it('ignores case, accents and punctuation when finding actual catalogue text', () => {
    expect(matchesModuleQuery('RETRIG midi', 'MIDI-retrig')).toBe(true)
    expect(matchesModuleQuery('andre', 'André')).toBe(true)
    expect(matchesModuleQuery('usb/audio', 'USB Audio')).toBe(true)
  })
  it('includes the instrument and type in Octatrack results', () => {
    const reverb = MODULES.find(module => module.id === 'everb')!
    expect(octatrackMatchesQuery(reverb, 'octatrack reverb')).toBe(true)
    expect(octatrackMatchesQuery(reverb, 'digitakt reverb')).toBe(false)
    expect(octatrackMatchesQuery(reverb, reverb.authorName)).toBe(true)
  })
  it('uses the same matching rules for Digi instrument, type and author searches', () => {
    const mod = DIGI_MODS.find(mod => mod.device === 'digitakt' && mod.libraryCategory === 'midi-usb')!
    expect(mod).toBeDefined()
    expect(digiMatchesQuery(mod, 'digitakt midi')).toBe(true)
    expect(digiMatchesQuery(mod, 'digitone midi')).toBe(false)
    expect(digiMatchesQuery(mod, mod.author)).toBe(true)
  })
})
