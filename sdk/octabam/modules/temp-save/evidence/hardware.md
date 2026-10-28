# TEMP SAVE hardware report

## 0.1.0 (28 October 2026)

- **Tester:** npp1993 (the contributor), by hand; the coding agent installed and removed the package over USB and read the module inventory.
- **Unit:** Octatrack MKII, OS 1.40C, flashed personal base `ccc5369236699164…` with 13 kept modules (Air Chorus, Analog BD, Apply Scene, BS WAVESHAPER, E-Verb, LIFT, LOFI2, Mini Verb, OUTPUT MATRIX, Quant Live Rec, Recorder Loop, Tape Echo, TapeHead).
- **Install:** `npm run device -- try <package> --seconds 1200` (a timed trial in RAM, never kept); stopped early with Ctrl-C, after which the inventory listed no TEMP SAVE.

### Run 1: package `335e59da46e0ad66b5fb98031d30e84d35fad49fc67c89768cb8b352a4cfa07c` (commit 88b14625)

| Check | Result |
| --- | --- |
| FUNC + YES, then trigs changed, FUNC + NO | TEMP SAVED, RELOADED, trigs back: pass |
| Parameters on several tracks | restored: pass |
| Machine change, then FUNC + NO | the machine back: pass |
| While playing | save and reload work: pass ("seems to work"; clicks or a stall were not specifically reported on) |
| Another pattern, FUNC + NO | NO TEMP SAVE: pass |
| MIXER, PROJECT, trig edit, PATTERN SETTINGS | no Temp Save message; stock ARM ALL / DISARM ALL: pass |
| SRC SETUP: FUNC + YES / FUNC + NO | no message / DISARM ALL (stock): pass |
| YES alone, NO alone | ARM ALL, DISARM ALL: pass |
| FUNC + CUE | PART 1 RELOADED; once DSP STOPPED appeared (see below) |
| Apply Scene's SCENE + YES | works: pass |
| **FUNC + YES twice quickly, FUNC + NO twice quickly** | **fail:** the second press showed ARM TRACK / DISARM TRACK. Cause: the module's own message is a popup, and the module left keys to stock while any popup was open. Fixed in 001fc493. |

DSP STOPPED is the base's DSP code loader abandoning a transfer (dsp.c); a Part reload that changes module effects can start one. It is being looked at with Analog BD's update in another session. Analog BD was taken off the tracks for run 2.

### Run 2: package `f9f45010275476bd93960b402e4ea7c0d8248c553ba12819846af0327675a687` (commit 001fc493)

| Check | Result |
| --- | --- |
| FUNC + YES twice quickly | TEMP SAVED twice, no ARM TRACK: pass |
| FUNC + NO twice quickly | RELOADED twice, no DISARM TRACK: pass |
| SRC SETUP sample slot list: FUNC + YES, CUE + YES | the sample preview plays (stock): pass |
| SRC SETUP sample slot list: FUNC + NO | DISARM TRACK (stock): pass |
| FUNC + YES on Part 1, pattern moved to Part 2 with PART, FUNC + NO | back on Part 1, pattern restored: pass |
| FUNC + CUE after a reload | on a Part never saved: stock's SAVE PART FIRST message; after a Part save: FUNC + YES, edit, FUNC + NO, more edits, FUNC + CUE: PART 1 RELOADED, back to the saved Part, no DSP STOPPED: pass |
| Save, edit and reload while playing | pass |

### Run 3: the published package  (commit eadd58a4, the release source)

On the flashed base  (flashed by another development session; 14 kept modules, the 13 above plus Ringmod SC), after a power cycle, as a timed trial. eadd58a4 changes only how the code reaches its copy buffer (an absolute, load-relocated address).

| Check | Result |
| --- | --- |
| FUNC + YES, trig and knob edits, FUNC + NO | TEMP SAVED, RELOADED, restored: pass |
| The same while playing | pass |
| FUNC + YES twice quickly, FUNC + NO twice quickly | TEMP SAVED twice, RELOADED twice: pass |
| Machine change, FUNC + NO | the machine back: pass |
| MIXER: FUNC + YES / FUNC + NO | stock ARM TRACK / DISARM TRACK, no Temp Save message: pass |

Limits: one unit and one tester; MKI not tested; nothing timed; the card build not flashed; the site's review/Keep/Undo flow not used (timed trials only); a power cycle with the module kept, project save after a reload, MIDI mode and other banks were not run on the unit (they ran under the emulator, TESTING.md).
