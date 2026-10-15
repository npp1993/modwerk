import { describe, expect, it } from 'vitest'
import { DEVICE_LOG_BYTES, DEVICE_LOG_PAGE, DEVICE_LOG_PAGES, parseDeviceLog } from './device-log'

/** A log as diag.h lays it out, big-endian: header, freeze slot, 96 loads, 32 incidents. */
function log(edit: (view: DataView) => void) {
  const data = new Uint8Array(DEVICE_LOG_PAGES * DEVICE_LOG_PAGE), view = new DataView(data.buffer)
  view.setUint32(0, 0x4d574447); view.setUint32(4, 1); view.setUint32(8, 0x1234); view.setUint32(12, 3); view.setUint32(16, 9)
  edit(view)
  return data
}
const LOADS = 40 + 92, INCIDENTS = LOADS + 28 * 96

describe('the unit’s diagnostics log', () => {
  it('reads diag.h’s layout and keeps written records, oldest first', () => {
    const parsed = parseDeviceLog(log(view => {
      const at = LOADS + 28 * 5 // ring slot 5 holds seq 7, slot 0 seq 2
      view.setUint32(at, 7); view.setUint32(at + 4, 3); view.setUint32(at + 8, 25)
      ;[400, 600, 300, 350, 200, 250, 600, 300].forEach((v, i) => view.setUint16(at + 12 + 2 * i, v))
      view.setUint32(LOADS, 2); view.setUint32(LOADS + 4, 2)
      const i = INCIDENTS + 92 * 3
      view.setUint32(i, 8); view.setUint32(i + 4, 3); view.setUint32(i + 8, 61); view.setUint32(i + 12, 16536)
      view.setUint16(i + 16, 3); view.setUint16(i + 18, 950); view.setUint16(i + 20, 500); view.setUint16(i + 22, 400)
      view.setUint8(i + 24, 1); view.setUint8(i + 48, 33); view.setUint8(i + 79, 19)
      view.setUint32(i + 80, 0x400cbf2c); view.setUint32(i + 84, 2880); view.setUint32(i + 88, 1)
      view.setUint32(INCIDENTS + 92 * 4 + 16, 0x00020000) // kind set, seq 0: being written, left out
    }))!
    expect(parsed).toMatchObject({ nonce: 0x1234, boot: 3, seq: 9 })
    expect(parsed.loads.map(load => load.seq)).toEqual([2, 7])
    expect(parsed.loads[1]).toEqual({ seq: 7, boot: 3, minute: 25, cpu: [400, 600], dsp5to8: [300, 350], dsp1to4: [200, 250], samples: 600, playing: 300 })
    expect(parsed.incidents).toHaveLength(1)
    expect(parsed.incidents[0]).toMatchObject({ seq: 8, boot: 3, second: 61, a: 16536, kind: 'freeze', cpu: 950, dsp5to8: 500, dsp1to4: 400, screen: 0x400cbf2c, tempo24: 2880, playing: true })
    expect(parsed.incidents[0].machines[0]).toBe(1); expect(parsed.incidents[0].fx[0]).toBe(33); expect(parsed.incidents[0].keys[15]).toBe(19)
  })
  it('refuses another magic or version and a short read', () => {
    expect(parseDeviceLog(log(view => view.setUint32(4, 2)))).toBeUndefined()
    expect(parseDeviceLog(log(view => view.setUint32(0, 0)))).toBeUndefined()
    expect(parseDeviceLog(new Uint8Array(DEVICE_LOG_BYTES - 1))).toBeUndefined()
    expect(DEVICE_LOG_PAGE % 64).not.toBe(0)
  })
})
