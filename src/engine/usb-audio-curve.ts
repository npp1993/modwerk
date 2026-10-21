// SPDX-License-Identifier: GPL-3.0-or-later
// Shared stock-data recipe for the card composer and the base's POST producer.
import { readDspWords } from './dsp-memory.ts'
import type { StockDspCore } from './stock-dsp.ts'

export function usbAudioPostCurve(cores: readonly StockDspCore[]): Uint32Array {
  const core = cores.find(item => item.tag === 'A')
  if (!core) throw new Error('USB Audio needs the stock core 0 gain table.')
  const curve = readDspWords(core.memory, 1, 0x6c00, 256)
  for (const [i, word] of curve.entries()) {
    const expected = Math.round(Math.sin(2 * Math.PI * i / 1024) * 0x7fffff)
    if (Math.abs(word - expected) > 64 || (i > 0 && word <= curve[i - 1])) throw new Error('USB Audio post-fader curve differs from the stock quarter-sine table.')
  }
  return curve
}
