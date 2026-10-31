# Retrig Rec testing

## 0.1.0-experimental (rytm-emu, 31 October 2026)

Not tested on a unit. These are emulator results only: pad pressure is a scripted stream, not a real pad.

### Builds

Owner-supplied OS 1.74 (stock sha256 cb0f99d6…e123), core-ar2 0.7 (`vendor/elekloader/catalog/core-ar2-0.7.elemod`), linked with `scripts/link-image.mjs`, `m68k-elf-` toolchain.

- RR05: this module alone, sha256 90a9f2e9d0b48134…
- RR06: this module and Retrig Grid 0.2.0-experimental, sha256 90a996197948a5cd…
- RR07: RR05 with the early-hit fix, sha256 bdc962d64cc82566…
- RR08: RR06 with the early-hit fix, sha256 c97bd28f65c01ab8…
- RR09: RR07 with the guard on the recorder track's step, kept past the release, sha256 56094153e36ac7e8…
- RR10: RR08 with the same, sha256 c36b3f55527005d6…

Emulator: rytm-emu c5732f0.

### Diagnosis

- **Certain** (disassembly and rytm-emu): the RETRIG menu's pressure handler writes a trigless lock with retrig and velocity on each step. The LIVE RECORDING tick treats the hold as a held note and removes the lock trig under it, unless the lock came after that step's last tick.
- **Certain** (rytm-emu): disabling that one call in stock left a velocity lock on all 15 steps of a roll, against 5 of 15.
- **Certain** (disassembly): stock's retrig series fires in the audio block and queues no note event to the recorder, so a roll's hits never reach it.
- **Certain** (rytm-emu): live retrigs are not quantized. A press 0.23 of a step early or 0.15 late keeps the whole roll that far off the grid.
- **Certain** (disassembly and rytm-emu, RR05): a hit placed on the next step becomes the recorder's held note before the playhead gets there. A sequencer notification in that gap runs the held-note wipe on the playhead's step and removes the hit before it. Runs at micro -10 lost steps 5 and 11 (roll from before LIVE RECORDING) and step 0 (roll from inside it); with the wipe call disabled none were lost. Micro -6 and later lost none here, and the emulator's notifications came about 0.4 step before a step, one every 6 steps. What sends them was not identified, so a unit may lose hits at other timings without the fix.
- **Certain** (disassembly): the wipe's "current step" is the step of the track the recorder follows (recorder + 64, its index at + 8), the same for every track it loops over, and the tick clears the skip byte of every track each pass. A pad press sets that track to the pad's (rytm-emu: index 0, then 1 after an SD press). RR09 reads that step, and keeps the guard after a release until the step arrives or the track's held notes are gone.

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
| Roll started before LIVE RECORDING (RR07), micro -10, +3, +10 | trigs from the first hit on, no step lost | 1.00 step apart, within 0.02 step |
| Roll inside LIVE RECORDING, hits early (RR07), micro -10 and -6, also ALWAYS ON | no step lost | within 0.02 step |
| Early hits at 1/8, 1/12, 1/32 (RR07) | every hit recorded, steps without one stay empty | spacing as played |
| Press again during a roll, hits early (RR07) | no step lost | as played |
| 1/16 pass, then a 1/8 pass over it (RR07) | the wipe still clears the steps between hits, same trig words as RR05 | not compared |
| Retrig Grid, early press and roll from before LIVE RECORDING (RR08) | no step lost | first hit at the press, rest on the grid |
| Retrig Grid beside it (RR06) | plain trigs on all 15 steps | first hit at the press, rest on the grid |
| RR09 rerun: roll from before LIVE RECORDING at micro -10, +3, +10; inside it at -10, -6, +7; ALWAYS ON early; re-press early; 1/10 early; 2x; 1/16 pass then a slower pass over it | trig words identical to RR07 in every case | identical to RR07 |
| RR10 rerun: Retrig Grid, roll from before LIVE RECORDING and early press inside it | identical to RR08 | identical to RR08 |

Velocity: the 1/16 velocity word at each playback hit equalled the recorded locks in order, on the prototype (PR12, 2026-10-31). Recorded velocities follow the scripted pressure at half its raw value.

VEL.CUR -8 at 1/32: each trig stored -8 and velocities followed the fade, not the pressure (stock's pressure path is off with VEL.CUR set). OFF stored 0.

A held pad without a retrig gave the same trig word on RR07 as on RR05. Other cases in the table ran on RR05 or RR06, not again on RR07 or RR09. A roll on a track other than the one the recorder follows was not produced: a pad press selects its track, and no other path to a retrig series was tried.

Plain pad hits still quantize with quantize on. Against stock: a held pad without a retrig over plain trigs, identical trig words. NO + pad removes the roll's trigs. NO + SCNE reloads the pattern and removes the recording, as stock.

The release race, the note-off flags and the queue guard were changed from reading the code. No test reaches them.

### Not tested

A unit. External MIDI clock. Where hits land when the pattern changes during a roll (the live hits matched stock). Load was not measured.
