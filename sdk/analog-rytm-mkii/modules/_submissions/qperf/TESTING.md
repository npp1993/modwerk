# QPERF testing

Nothing here proves reboot persistence or the QPER knob itself. The only hardware run so far is reported below, on a build since fixed.

## Hardware

Reported by the author on build QP01, Analog Rytm MKII, OS 1.74:

- PLAY alone counted as a clear, with no QPER held.
- No sound.
- The message boxes did not match stock's popups.

Build QP02 fixes the first and the third. It has not run on hardware yet.

## Emulator

rytm-emu c5732f0, `dtboot`, stock OS 1.74, Modwerk base 0c92aa45 with QPERF source on branch `claude/rytm-qperf`, factory kit K001 RYTMLINJE (31 performance locks, QPER linked to performances 1 and 10). Lock table and effective parameters read from snapshots with `dtpeek`.

| Check | Result |
| --- | --- |
| QPER held, turn SWD 6 times | Performances 1 and 10 each got a lock of 2816 (total 5632, 8.8); SWD unchanged; total shown |
| QPER + PLAY | Both linked performances cleared (31 locks to 18); sequencer did not start |
| QPER + YES, performance 1's amount poked to half | Effective parameters rose by half each lock (track 2 param 41: 11305 to 22396 for a lock of 22272); locks kept (31); APPLIED shown |
| QPER + YES, amount 0 | Lock table unchanged |
| Turn without QPER | Table unchanged |
| FUNC + QPER | Stock's mute flag set |
| QPER + pads | Stock's link mask changed (0x201 to 0x3) |
| 47 locks used, a new parameter with 2 linked | Nothing written, parameters unchanged |
| PLAY held, then QPER (key repeats) | Table unchanged |
| QPER, then FUNC + PLAY | Table unchanged |
| TRIG page, QPER + turn | No lock written |

Build QP02 (sha256 008f2f89), key release read from bit 0 as stock does, messages through stock's popup:

| Check | Result |
| --- | --- |
| QP01: QPER + pad, release, then PLAY | Reproduced: QPER stayed held, PLAY was taken, output peak 0 |
| QP02: same steps, four trigs placed | QPER released, sequencer started, output peak 11229 |
| PLAY alone | Sequencer started, output peak 11229 |
| QPER + pad + PLAY | CLEARED popup; sequencer did not start, output peak 0 |
| QPER + YES, then PLAY while the popup is open | Sequencer started |
| QPER held, turn 30 steps | Total popup, closes after release; no fault |

## Not tested

- The real QPER knob: the emulator has none, so amounts were poked. Full amount is taken as 0x7f80 from the code, not measured.
- Knob turns on the FX track and the LFO page.
- The LOCKS FULL and NO LINKS popups on screen (the writes were checked, not the frames).
- A build beside other modules. QPERF answers every parameter id in `core_params` while QPER is held.
- Save and reload of the kit after a turn, clear or apply.
- Hardware, audio, performance load.
