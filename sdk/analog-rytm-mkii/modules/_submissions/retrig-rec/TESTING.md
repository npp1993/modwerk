# Retrig Rec testing

## 0.1.0-experimental (rytm-emu, 31 October 2026)

Not tested on a unit. These are emulator results only: pad pressure is a scripted stream, not a real pad.

### Builds

Owner-supplied OS 1.74 (stock sha256 cb0f99d6…e123), core-ar2 0.7 (`vendor/elekloader/catalog/core-ar2-0.7.elemod`), linked with `scripts/link-image.mjs`, `m68k-elf-` toolchain.

- RR05: this module alone, sha256 90a9f2e9d0b48134…
- RR06: this module and Retrig Grid 0.2.0-experimental, sha256 90a996197948a5cd…

Emulator: rytm-emu c5732f0.

### Diagnosis

- **Certain** (disassembly and rytm-emu): the RETRIG menu's pressure handler writes a trigless lock with retrig and velocity on each step. The LIVE RECORDING tick treats the hold as a held note and removes the lock trig under it, unless the lock came after that step's last tick.
- **Certain** (rytm-emu): disabling that one call in stock left a velocity lock on all 15 steps of a roll, against 5 of 15.
- **Certain** (disassembly): stock's retrig series fires in the audio block and queues no note event to the recorder, so a roll's hits never reach it.
- **Certain** (rytm-emu): live retrigs are not quantized. A press 0.23 of a step early or 0.15 late keeps the whole roll that far off the grid.

### Method

Factory project (RYTMLINJE, 127 BPM, ADVANCED scale), BD at 1x, swing set to 50 %, quantize live rec on unless noted. The pad is pressed, held about 15 steps and sent a pressure message every 20 ms, a triangle wave across the pad's range. Trig words and locks are read from the pattern in memory. Hit times come from `DTEMU_FRAME_TRACE=160,162`, during recording and on the next loop with no keys held.

### Results

Hits closer than 100 samples count as one: a trigger's switch takes up to 64 samples. All on RR05 unless noted.

| Case | Recorded | Playback against live |
| --- | --- | --- |
| 1/16, press 0.15 step late | plain trigs on all 15 steps, press included | 1.00 step apart, within 0.02 step |
| 1/8 | a plain trig every 2 steps | 2.00 steps apart, within 0.02 step |
| 1/12 | a plain trig for each hit, micro timing kept | 1.29-1.38 steps apart |
| 1/32 | a trig a step, step retrig 1/32 | 0.50 step apart |
| 1/24, 1/20 | a trig every 2 and 4 steps, step retrig | 0.67 and 0.80 step apart, within 0.05 |
| ALWAYS ON, 1/16 | as RTRG + pad | as RTRG + pad |
| Track at 2x, 1/2x | rates follow the track's step | as played, within 0.02 step |
| 1/16 to 1/24 during the roll | plain trigs, then a trig with step retrig from the next hit | spacing as played |
| Press again during a roll, also with Retrig Grid | a new press trig at 0x7f, the roll goes on from it | as played, within 0.02 step |
| CHROMATIC, a second note during the roll | hits follow the new note | not measured |
| Hold of 30 steps, past the 16-step loop | second pass overwrites, no step lost | 1.00 step apart |
| Roll started before LIVE RECORDING | trigs from the first hit on; two of three runs lost 2 of about 17 hits, cause not found | not measured |
| Retrig Grid beside it (RR06) | plain trigs on all 15 steps | first hit at the press, rest on the grid |

Velocity: the 1/16 velocity word at each playback hit equalled the recorded locks in order, on the prototype (PR12, 2026-10-31). Recorded velocities follow the scripted pressure at half its raw value.

VEL.CUR -8 at 1/32: each trig stored -8 and velocities followed the fade, not the pressure (stock's pressure path is off with VEL.CUR set). OFF stored 0.

Plain pad hits still quantize with quantize on. Against stock: a held pad without a retrig over plain trigs, identical trig words. NO + pad removes the roll's trigs. NO + SCNE reloads the pattern and removes the recording, as stock.

The release race, the note-off flags and the queue guard were changed from reading the code. No test reaches them.

### Not tested

A unit. External MIDI clock. Where hits land when the pattern changes during a roll (the live hits matched stock). Load was not measured.
