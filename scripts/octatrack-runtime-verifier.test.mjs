// SPDX-License-Identifier: GPL-3.0-or-later
import { describe, expect, it } from 'vitest'
import { captureStockCopies, verifyRuntimeRelocations } from './octatrack-runtime-verifier.mjs'

describe('runtime install envelope verification', () => {
  it('keeps the original replay source when its stock site changes during Keep', async () => {
    const memory = Buffer.from('authored-original-replay')
    const originals = await captureStockCopies([{ address: 0, length: 8 }], async (at, n) => memory.subarray(at, at + n))
    memory.fill(0xff, 0, 8) // Keep patches the same source site.
    expect(originals[0]).toEqual(Buffer.from('authored'))
    expect(originals[0]).not.toEqual(memory.subarray(0, 8))
  })

  it('reads copy sources sequentially because peeks share one routine', async () => {
    const addresses = [], order = []
    let completeFirst
    const originals = captureStockCopies([{ address: 10, length: 4 }, { address: 20, length: 4 }], async (at, n) => {
      addresses.push(at)
      if (at === 10) await new Promise(resolve => { completeFirst = resolve })
      order.push(at)
      return Buffer.alloc(n, at)
    })
    await Promise.resolve()
    expect(addresses).toEqual([10])
    completeFirst()
    expect(await originals).toEqual([Buffer.alloc(4, 10), Buffer.alloc(4, 20)])
    expect(order).toEqual([10, 20])
  })

  it('refuses a corrupt relocation beyond the short image-prefix check', async () => {
    const code = Buffer.alloc(256)
    code.writeUInt32BE(0x48000100, 188)
    code.writeUInt32BE(0x48000110, 196)
    const memory = Buffer.from(code), read = async (at, n) => memory.subarray(at - 0x48000000, at - 0x48000000 + n)
    await expect(verifyRuntimeRelocations(code, [188, 196], 0x48000000, read)).resolves.toBeUndefined()
    memory[199] ^= 1
    await expect(verifyRuntimeRelocations(code, [188, 196], 0x48000000, read)).rejects.toThrow('relocation word 196')
  })
})
