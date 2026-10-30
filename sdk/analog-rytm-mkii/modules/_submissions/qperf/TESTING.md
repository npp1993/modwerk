# QPERF testing

Nothing here proves reboot persistence or the QPER knob itself. The only hardware run so far is reported below, on a build since fixed.

## Hardware

Reported by the author on build QP01, Analog Rytm MKII, OS 1.74:

- PLAY alone counted as a clear, with no QPER held.
- No sound.
- The message boxes did not match stock's popups.

Reported by the author on build QP02:

- QPER + clear worked. A +30 turn with 3 linked split to +10 each. QPER + YES at full applied a lock, and +10 split across 2 then applied to one gave +5.
- QPER + YES showed NOTHING with the knob at full after relinking, until the knob was moved: stock only writes the amount to performances linked when it moves.
- The offset toast was not what a held performance shows.

Build QP03 changes all of this. 

Reported by the author on build QP05:

- Link 3, overdrive +30, relink to one, QPER + YES with the knob untouched: PERFORMANCE 5 APPLIED, overdrive +10. The knob position reached the apply.
- Half knob added about half the offset. Fine tune stopped at its maximum of 63 on repeated applies, still showing APPLIED.
- Locked knobs inverted while QPER held. Hold again and turn from +30 to +40 with 3 linked.
- QPER + PLAY cleared; PLAY again showed UNDO CLEAR. Whether undone locks follow the knob: unsure.
- After a restart, QPER + YES showed PERFORMANCE 12 APPLIED. The value was not reported.
- LOCK MEM FULL! appeared. Linking on FX track and LFO pages seemed fine. FUNC + QPER muted. Linking by pads worked. Kit reload seemed right.
- At full knob, QPER + YES stacks the offset on what the performance still adds, so the sound jumps.
- Unsure or not run: release back to stock, unequal locks, undo across kits, the NO PERFORMANCE LINKED turn, QPER + YES with FX locks, power cycle.

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

Build QP03 (sha256 093064d6), base 0c92aa45, factory kit K001:

| Check | Result |
| --- | --- |
| QPER held, 2 linked, turn SWD | Knob inverted, reads +34; 17.0 in each linked performance |
| Turn back | +28, 14.0 in each |
| QPER released, turn the knob | No lock written (31 locks) |
| QPER + YES, knob poked to 127 | APPLIED TO KIT |
| QPER + YES, knob poked to 0 | QPER KNOB AT ZERO |
| QPER + YES, knob not moved since boot | MOVE THE QPER KNOB FIRST |
| QPER + PLAY twice | CLEARED (31 locks to 18), then NO LOCKS TO CLEAR |
| Links removed, QPER + YES | NO PERFORMANCES LINKED |
| FUNC + QPER, then QPER + YES | QPER IS MUTED |

The emulator has no QPER knob, so the position was poked: the site that reads it (0x400a4994) is patched but has not run.

Build QP04 (sha256 ad915f44), same setup:

| Check | Result |
| --- | --- |
| QPER + YES, 2 linked, knob poked to 0 | PERFORMANCES APPLIED |
| FUNC + QPER to mute, then QPER + YES | PERFORMANCES APPLIED |
| QPER + pad, QPER + YES | PERFORMANCE 1 APPLIED |
| Links removed, QPER + YES | NOTHING TO APPLY |
| QPER + PLAY twice | 31 locks to 18, then UNDO CLEAR and the same 31 locks |
| QPER + PLAY three times | 18 locks: the third clears again |
| QPER + PLAY, relink to another pad, PLAY | That pad's locks cleared, no undo of the first |

Build QP05 is QP04 with one message changed. Links removed, QPER held, turn a knob: NO PERFORMANCE LINKED, no lock written.

## Not tested

- The real QPER knob: the emulator has none, so amounts were poked. Full amount is taken as 0x7f80 from the code, not measured.
- Knob turns on the FX track and the LFO page.
- LOCK MEM FULL! on screen.
- The site that reads the QPER knob.
- A build beside other modules.
- The kit's power-on knob position: until the knob moves, QPER + YES falls back on stock's per-performance amounts.
- Save and reload of the kit after a turn, clear or apply.
- Hardware, audio, performance load.
