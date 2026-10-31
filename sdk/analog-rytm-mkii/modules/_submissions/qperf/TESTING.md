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

Build QP06 (sha256 3305266d), same setup:

| Check | Result |
| --- | --- |
| Hold QPER on a kit linked to 2 | Mask drops to the lowest one |
| QPER + SD, knob poked to full | Link moves; new performance's amount 0x7f80, old 0 |
| QPER + SD twice | Unlinked, amount 0 |
| QPER + trig 3 | Link moves to performance 3 |
| QPER + YES, knob full | Locks read 0, 31 slots kept, PERFORMANCE 1 APPLIED |
| QPER + YES, knob about half | Locks halved (22272 to 11180) |
| QPER + PLAY twice | Stock's clear, then undo: 31 locks back |
| RECORD, link SD, STOP, STOP | COPY PERFORMANCE 1; pasted (35 locks); undone (31 locks) |

FX apply was not reached: the emulator did not select the FX track.

Reported by the author on build QP06:

- Single link works. Holding several pads in performance mode still works as on stock.
- Overdrive +12, QPER + YES at full: overdrive 12, lock +0, second YES NOTHING TO APPLY, knob down changed nothing.
- Pan +40 at about half: kit +21, lock +18. Repeated YES crept closer until NOTHING TO APPLY.
- Clear and undo, copy, paste and undo paste all worked.
- FX track volume +53, QPER + YES at full: APPLIED, but the lock stayed and the sound still followed the knob. Cause: wrong stock id table. Fixed in QP07.
- Pad 1 stays dim green, brighter when linked.

Reported by the author on build QP07:

- Pad 1's dim green went out after CLEAR PERFORMANCE: stock's marker for a performance with locks.
- Clear in kit 1, load kit 2, QPER + PLAY: CLEAR PERFORMANCE, no undo, and kit 1's locks did not appear.
- +127 at half knob, saved, power cycled, kit reloaded: applied value and reduced lock both back.
- After power on, QPER + YES before moving the knob: APPLIED, no crash, value unchanged. After moving the knob it followed the position.

Build QP07 (sha256 95ef219d): a +40 lock poked into the FX track at index 22, QPER + YES at full: lock 0, kit byte 78 to 118. Index 34 also went to 0 and its kit value moved. The FX track was not selected on screen.

Build QP08 (sha256 951dade2): QPER + YES at full removed all 13 of performance 1's locks (31 slots to 18); at about half all 13 stayed.

Reported by the author on build QP08: FX track threshold +127, QPER + YES at full: PERFORMANCE 4 APPLIED, the lock went away, the sound held. Locks set on BD, snare and RS show as red pads on the performance page, as stock.

Combined build QC01 (sha256 493d5fa2): core 0.7 base 0c92aa45, Filter Hz 1.2.0, Pipo Loop 0.1.0-experimental, QPERF, Silent Pad+Trig 0.5.1-experimental. Linked with no overlap and booted in rytm-emu:

| Check | Result |
| --- | --- |
| Any key on a kit linked to 2 | Mask drops to the lowest one on the next tick |
| Mask poked to 2 links | Drops to the lowest one |
| QPER + SD, turn SWD | Lock in performance 2, knob inverted, reads +28 |
| FLTR page, turn FRQ | Reads 21.1kHz |
| Trigs placed, PLAY | Sequencer ran, output peak 11229 |

Pipo Loop and Silent Pad+Trig were not exercised, only booted beside it.

Reported by the author on QC01: Filter Hz, Silent Pad+Trig, Pipo Loop and QPERF's knob and YES looked good. LFO depth +30, QPER + YES at half knob: the sound moved up. Half knob leaves half the lock, which adds a quarter more at that position, so this is the expected step, not shown to be LFO-specific.

QC02 (sha256 562c8c76): the link check now starts from `ev_project`. Booted with no key pressed, the factory kit's two links dropped to one. QPER + SD and a knob turn wrote a lock.

## Not tested

- A kit loaded with another link or several, on a unit.
- QPER gestures inside a menu or dialog: they still fire there.
- Knob turns on the LFO page, and parameters with wide ranges.
- Performance load.
