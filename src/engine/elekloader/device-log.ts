import { DEVICE_INCIDENTS, type DeviceIncident, type DeviceLoad } from '../../community/octatrack-diagnostics-contract.ts'

/** The unit's diagnostics log (sdk/machines/octatrack/elekloader/diag.h), as the ColdFire stores it: big-endian. */
export const DEVICE_LOG_REQUEST = 37
export const DEVICE_LOG_PAGE = 244
const MAGIC = 0x4d574447, VERSION = 1, LOADS = 96, INCIDENTS = 32, HEADER = 40, LOAD = 28, INCIDENT = 92
export const DEVICE_LOG_BYTES = HEADER + INCIDENT + LOAD * LOADS + INCIDENT * INCIDENTS
export const DEVICE_LOG_PAGES = Math.ceil(DEVICE_LOG_BYTES / DEVICE_LOG_PAGE)

export interface DeviceLog { nonce: number; boot: number; seq: number; loads: DeviceLoad[]; incidents: DeviceIncident[] }

function load(view: DataView, at: number): DeviceLoad {
  const u16 = (i: number) => view.getUint16(at + 12 + 2 * i)
  // diag.h: core 0 runs T5-8, core 1 T1-4.
  return { seq: view.getUint32(at), boot: view.getUint32(at + 4), minute: view.getUint32(at + 8), cpu: [u16(0), u16(1)],
    dsp5to8: [u16(2), u16(3)], dsp1to4: [u16(4), u16(5)], samples: u16(6), playing: u16(7) }
}
function incident(view: DataView, at: number): DeviceIncident | undefined {
  const kind = DEVICE_INCIDENTS[view.getUint16(at + 16) - 1]
  if (!kind) return undefined
  const bytes = (from: number, n: number) => Array.from({ length: n }, (_, i) => view.getUint8(at + from + i))
  return { seq: view.getUint32(at), boot: view.getUint32(at + 4), second: view.getUint32(at + 8), a: view.getUint32(at + 12), kind,
    cpu: view.getUint16(at + 18), dsp5to8: view.getUint16(at + 20), dsp1to4: view.getUint16(at + 22),
    machines: bytes(24, 24), fx: bytes(48, 16), keys: bytes(64, 16),
    screen: view.getUint32(at + 80), tempo24: view.getUint32(at + 84), playing: view.getUint32(at + 88) === 1 }
}
/** The written records, oldest first; undefined for anything but a version 1 log. A record still being written has
 * seq 0 and is left out. */
export function parseDeviceLog(data: Uint8Array): DeviceLog | undefined {
  if (data.byteLength < DEVICE_LOG_BYTES) return undefined
  const view = new DataView(data.buffer, data.byteOffset, DEVICE_LOG_BYTES)
  if (view.getUint32(0) !== MAGIC || view.getUint32(4) !== VERSION) return undefined
  const loads = Array.from({ length: LOADS }, (_, i) => load(view, HEADER + INCIDENT + LOAD * i)).filter(record => record.seq)
  const incidents = Array.from({ length: INCIDENTS }, (_, i) => incident(view, HEADER + INCIDENT + LOAD * LOADS + INCIDENT * i))
    .filter((record): record is DeviceIncident => !!record?.seq)
  const bySeq = <T extends { seq: number }>(a: T, b: T) => a.seq - b.seq
  return { nonce: view.getUint32(8), boot: view.getUint32(12), seq: view.getUint32(16), loads: loads.sort(bySeq), incidents: incidents.sort(bySeq) }
}
