# Temp Save testing

Not tested on hardware. Everything below is rytm-emu, which only approximates the instrument.

## Emulator

rytm-emu c5732f0, `dtboot`, stock OS 1.74, Modwerk base 0c92aa45, Temp Save alone, build TS05 (sha256 8d39f005), factory kit K001 RYTMLINJE, pattern A01. Pattern, stored buffer and kit records read from snapshots with `dtpeek`. Screens read from `dtboot`'s output. The emulator's boot leaves a calibration warning open that takes YES and NO until it is closed; these runs close it first.

| Check | Result |
| --- | --- |
| FUNC + NO, no save yet | NO TEMP SAVE; nothing changed |
| FUNC + YES | TEMP SAVED; stored buffer equals the live pattern |
| Add a trig (RECORD, T1) and turn TUN, then FUNC + NO | RELOADED; pattern (85,760 bytes) and kit record (2,531 bytes) byte-identical to the save |
| FUNC + NO again | RELOADED |
| To A02 and back to A01, then FUNC + NO | NO TEMP SAVE; the edit stays |
| Playing: FUNC + YES, later FUNC + NO | Both run; the sequencer keeps playing (TS02 for the reload) |
| Grid record, T2 held, FUNC + NO | No message; the trig stays: stock's |
| Sample slot list open (SMPL, push D), FUNC + YES | CONFIRMED!, stock's; no TEMP SAVED |
| GLOBAL menu open, FUNC + YES | Menu stays; no message (TS02) |
| Page key + YES | RANDOMIZE PAGE, stock's (TS02) |
| FUNC + NO while TEMP SAVED shows | Ignored: stock's message takes NO |

Read from stock's code, not run: performance locks at kit record + 1950 and scene locks at + 2190, inside the bytes compared above.

## Not tested

- Anything on a unit: stock FUNC + YES and FUNC + NO without the module on every screen, audio during a reload, timing.
- Sample preview with a sample in the slot, the sound browser, the song and chain modes.
- A performance or scene lock edited by hand and reloaded.
- A pattern whose kit differs from the saved one. Project load dropping the save.
- A project save after FUNC + YES, power cycle, and this beside other modules. Memory and load were not measured.
- Mutes, the tempo and the performance knob across a reload.
