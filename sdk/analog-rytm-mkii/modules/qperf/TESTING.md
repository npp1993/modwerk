# QPERF testing

Not tested on hardware. Nothing here proves audible results, reboot persistence or the QPER knob itself.

## Emulator

rytm-emu c5732f0, `dtboot`, stock OS 1.74, Modwerk base 0c92aa45 with QPERF source on branch `claude/rytm-qperf`, factory kit K001 RYTMLINJE (31 performance locks, QPER linked to performances 1 and 10). Lock table and effective parameters read from snapshots with `dtpeek`.

| Check | Result |
| --- | --- |
| QPER held, turn SWD 6 times | Performances 1 and 10 each got a lock of 2816 (total 5632, 8.8); SWD unchanged; box shows the total |
| QPER + PLAY | Both linked performances cleared (31 locks to 18); sequencer did not start |
| QPER + YES, performance 1's amount poked to half | Effective parameters rose by half each lock (track 2 param 41: 11305 to 22396 for a lock of 22272); locks kept (31); box APPLIED |
| QPER + YES, amount 0 | Lock table unchanged |
| Turn without QPER | Table unchanged |
| FUNC + QPER | Stock's mute flag set |
| QPER + pads | Stock's link mask changed (0x201 to 0x3) |
| 47 locks used, a new parameter with 2 linked | Nothing written, parameters unchanged |

## Not tested

- The real QPER knob: the emulator has none, so amounts were poked. Full amount is taken as 0x7f80 from the code, not measured.
- Knob turns on the FX track and on LFO or TRIG pages.
- The LOCKS FULL and NO LINKS boxes on screen (the writes were checked, not the frames).
- A build beside other modules. QPERF answers every parameter id in `core_params` while QPER is held.
- Save and reload of the kit after a turn, clear or apply.
- Hardware, audio, performance load.
