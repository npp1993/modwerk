// SPDX-License-Identifier: GPL-3.0-or-later
import assert from 'node:assert/strict'

/** A stock-copy source may be a site that Keep patches. Read before Keep, in
 * order: the emulator peek routine borrows one shared instruction buffer. */
export async function captureStockCopies(copies, peek) {
  const originals = []
  for (const copy of copies) originals.push(Buffer.from(await peek(copy.address, copy.length)))
  return originals
}

/** Check every relocation, including words past the first 64 image bytes. */
export async function verifyRuntimeRelocations(code, relocations, base, peek) {
  for (const offset of relocations) {
    assert.deepEqual(await peek(base + offset, 4), code.subarray(offset, offset + 4),
      `relocation word ${offset} at 0x${base.toString(16)}`)
  }
}
