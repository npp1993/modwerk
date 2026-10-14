import { describe, expect, it } from 'vitest'
import { checkSelection } from './compatibility'
import { MODULES } from './modules'
import { availableModules } from './availability'
describe('declarative compatibility',()=>{
 it('checks every nonempty selection in the verified native profile against its pinned ledger',()=>{const supported=MODULES.filter(module=>['spectrum','modulation','character','miniverb','tapeecho','euclid','repitch'].includes(module.id));expect(supported).toHaveLength(7);for(let mask=1;mask<1<<supported.length;mask++){const ids=supported.filter((_,index)=>mask&(1<<index)).map(m=>m.id);expect(checkSelection(ids).checked).toBe(true);expect(checkSelection(ids).issues).toEqual([])}})
 // A pair the ledger refuses becomes a conflict, never a note, so a note means a module the pair table lacks.
 it('has a declaration check for every public or beta pair and the whole offer', () => {
  const visible = availableModules(true).map(m => m.id).filter(id => id !== 'midi-scenes'), unchecked: string[] = []
  for (const [index, a] of visible.entries()) for (const b of visible.slice(index + 1)) if (checkSelection([a, b]).notes.length) unchecked.push(a + '+' + b)
  expect(unchecked).toEqual([])
  expect(checkSelection(visible).notes).toEqual([])
 })
 it('checks MIDI Scenes only on its own', () => {
  const others = availableModules(true).map(m => m.id).filter(id => id !== 'midi-scenes')
  expect(checkSelection(['midi-scenes']).checked).toBe(true)
  for (const ids of [...others.map(id => ['midi-scenes', id]), ['midi-scenes', ...others]]) {
   const result = checkSelection(ids)
   expect(result.checked).toBe(false)
   expect(result.issues.join(' ')).toContain('standalone')
  }
 })
 it('refuses unknown modules and does not call an empty configuration checked',()=>{expect(()=>checkSelection(['unknown'])).toThrow();expect(checkSelection([]).checked).toBe(false)})
})
