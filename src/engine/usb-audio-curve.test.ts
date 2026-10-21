import { describe, expect, it } from 'vitest'
import { parseDspMemory } from './dsp-memory.ts'
import type { StockDspCore } from './stock-dsp.ts'
import { usbAudioPostCurve } from './usb-audio-curve.ts'
import { fillBase, type BaseFill } from './elekloader/octatrack-base.ts'

const words = Array.from({ length: 256 }, (_, i) => Math.round(Math.sin(2 * Math.PI * i / 1024) * 0x7fffff))
function core(values = words, space = 1, address = 0x6c00): StockDspCore {
  const le = (value: number) => [value & 255, value >>> 8 & 255, value >>> 16 & 255]
  return { tag: 'A', memory: parseDspMemory(Uint8Array.from([...[space, address, values.length].flatMap(le), ...values.flatMap(le), ...[3, 0].flatMap(le)])),
    packages: [{ fxId: 4, words: Uint32Array.of(0x123456) }], shared: [] } as unknown as StockDspCore
}

describe('the shared USB post-fader stock-data recipe', () => {
  it('reads core 0 X data regardless of core order and refuses changed or unloaded data', () => {
    expect([...usbAudioPostCurve([{ ...core(), tag: 'B' }, core()])]).toEqual(words)
    for (const cores of [[], [core(words.slice(1))], [core(words, 2)], [core(words, 1, 0x6c01)], [core(words.map((word, i) => i === 12 ? word + 65 : word))], [core(words.map(() => 0))]])
      expect(() => usbAudioPostCurve(cores)).toThrow()
  })

  it('restores 32-bit data beside existing 24-bit code fills without changing offsets or padding', () => {
    const stripped = JSON.stringify({ sections: { '.run': { len: 1031, parts: [['hex', 'aa00'], ['hex', 'bbcc']] } }, sites: [] })
    const fills: BaseFill[] = [{ tag: 'A', curve: 'usb-post-xlv', first: 0, count: 256, section: '.run', offset: 2 },
      { tag: 'A', fx: 4, first: 0, count: 1, section: '.run', offset: 1026 }]
    const doc = JSON.parse(fillBase(stripped, fills, [core()]))
    const data = doc.sections['.run'].parts.map((part: string[]) => part[1]).join('')
    expect(data).toBe('aa00' + words.map(word => word.toString(16).padStart(8, '0')).join('') + '123456bbcc')
    expect(data.length / 2).toBe(1031)
  })

  it('refuses malformed, ambiguous and out-of-place 32-bit recipes before reconstruction', () => {
    const fill = { tag: 'A', curve: 'usb-post-xlv', first: 0, count: 256, section: '.run', offset: 0 }
    const text = JSON.stringify({ sections: { '.run': { len: 1024, parts: [] } }, sites: [] })
    for (const bad of [{ curve: 'unknown' }, { tag: 'B' }, { first: 1 }, { count: 255 }, { offset: -2 }, { offset: 1 }, { offset: 0.5 }, { section: '.absent' }, { section: '__proto__' }, { section: null }, { fx: 4 }, { site: '0x40000000' }])
      expect(() => fillBase(text, [{ ...fill, ...bad } as BaseFill], [core()])).toThrow('Unsupported USB POST')
  })
})
