# Retrig Rec testing

## 0.1.0-experimental (rytm-emu, 31 October 2026)

Not tested on a unit. These are emulator results only: pad pressure is a scripted stream, not a real pad.

### Builds

Owner-supplied OS 1.74 (stock sha256 cb0f99d6…e123), core-ar2 0.7 (`vendor/elekloader/catalog/core-ar2-0.7.elemod`), linked with `scripts/link-image.mjs`, `m68k-elf-` toolchain.

- RR03: this module alone, sha256 08292d31567a7288…
- RR04: this module and Retrig Grid 0.2.0-experimental, sha256 770546b71198c36e…

Emulator: rytm-emu c5732f0.

### Diagnosis

- **Certain** (disassembly and rytm-emu): the RETRIG menu's pressure handler writes a trigless lock with retrig and velocity on each step. The LIVE RECORDING tick treats the hold as a held note and removes the lock trig under it, unless the lock came after that step's last tick.
- **Certain** (rytm-emu): disabling that one call in stock left a velocity lock on all 15 steps of a roll, against 5 of 15.
- **Certain** (disassembly): stock's retrig series fires in the audio block and queues no note event to the recorder, so a roll's hits never reach it.
- **Certain** (rytm-emu): live retrigs are not quantized. A press 0.23 of a step early or 0.15 late keeps the whole roll that far off the grid.

### Method

Factory project (RYTMLINJE, 127 BPM, ADVANCED scale), BD at 1x, swing set to 50 %, quantize live rec on unless noted. The pad is pressed, held about 15 steps and sent a pressure message every 20 ms, a triangle wave across the pad's range. Trig words and locks are read from the pattern in memory. Hit times come from `DTEMU_FRAME_TRACE=160,162`, during recording and on the next loop with no keys held.

### Results

| Case | Recorded | Playback against live |
| --- | --- | --- |
| 1/16, press 0.15 step late | a trig on all 15 steps | same spacing, within 0.02 step |
| 1/8 | a trig every 2 steps | same spacing, within 0.02 step |
| 1/12 | a trig for each hit, micro timing kept | same spacing, within 0.05 step |
| 1/32 | a trig a step, step retrig 1/32 | 2 hits a step, within 0.02 step |
| 1/24, 1/20 | a trig every 2 and 4 steps, step retrig | 0.67 and 0.80 step apart |
| ALWAYS ON, 1/16 | as RTRG + pad | as RTRG + pad |
| Track at 2x and 1/2x | rates follow the track's step | spacing as played |
| Retrig Rate changed during the roll | trigs follow, no locks | not measured |
| Retrig Grid beside it (RR04) | a trig on all 15 steps | first hit at the press, rest on the grid |

1/24, 1/20, 2x, 1/2x, the rate change and ALWAYS ON ran on RR01/RR02 or the prototype with the same recording code, not on RR03.

Velocity: the 1/16 velocity word at each playback hit equalled the recorded locks in order, on the prototype (PR12). Recorded velocities follow the scripted pressure at half its raw value.

VEL.CUR -8 at 1/32 (RR01): each trig stored -8. OFF stored 0.

Plain pad hits still quantize with quantize on (RR01). Against stock, on RR03: a held pad without a retrig over plain trigs, identical. NO + pad removes the roll's trigs. NO + SCNE reloads the pattern and removes the recording, as stock.

### Not tested

A unit. External MIDI clock. Where hits land when the pattern changes during a roll (the live hits matched stock). Load was not measured.
