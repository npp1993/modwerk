# Temp Save testing

**Hardware status: tested by hand on one MKII over USB, 28 October 2026** ([evidence/hardware.md](evidence/hardware.md)): every step passed with package `f9f45010…` (commit 001fc493). The first package failed one check, a quick second FUNC + YES / FUNC + NO, which 001fc493 fixes. The MKI and the card build have not run on a unit; nothing was timed on the unit.

The rest of this file is the ColdFire port (`ot_emu`) on native builds of OS 1.40C, which approximates the instrument: no real-time timing, no audio check.

## Commands and exact revision

Emulator, 27 and 28 Oct 2026. Final runs on the source of commit `001fc493` (`unit.s`); `verify.py` as of this commit. Earlier rows name their commit. The images are native builds in a scratch copy of `sdk/octabam` with this folder copied to `modules/temp-save` and `static_stock=True` remixes:

```sh
make bus REMIX=temp-save-stock BUILD=0     # TEMP SAVE + every stock effect
make bus REMIX=temp-save-combo BUILD=0     # the same + APPLY SCENE, PREVIEW VOL, DIRECT_JUMP_KYOTI
python3 modules/temp-save/verify.py                      # MKII panel
TEMP_MODEL=mki python3 modules/temp-save/verify.py       # MKI panel
```

The build reports `jmp 0x4005e3d8 -> temp_save:ts_yes_hook` and `jmp 0x4005e1fc -> temp_save:ts_no_hook`, the unit in the DRAM reserve, and no other site.

| image (MAIN OS SHA-256, first 12) | remix | gate | result |
|---|---|---|---|
| `32417b06af3f` | temp-save-stock, 001fc493 | verify.py, MKII | PASS, 37 checks (with the quick double press and the cost measurement) |
| `01b6df8c37bd` | temp-save-stock, 88b14625 | verify.py, MKII | PASS, 35 checks |
| `01b6df8c37bd` | temp-save-stock, 88b14625 | verify.py, MKI | PASS, 34 checks (no PROJ/PART keys: PART opened with FUNC + MIDI) |
| `cacf548ba078` | temp-save-combo, 88b14625 | verify.py, MKII | PASS |
| `cacf548ba078` | temp-save-combo, 88b14625 | Apply Scene's verify.py | PASS, 264 checks |

eadd58a4 (the release source) changes only how the code reaches its copy buffer: an absolute, load-relocated address instead of a 16-bit PC offset, which `module:verify` showed the largest card selections need. On its image `e74f49925947` verify.py passes, 37 checks, with the same save and reload costs (16,287 / 637,251 / 640,923).

001fc493 changes only `ts_screen` (a popup that is the message no longer counts as a window); the MKI and combination runs were not repeated on it.

`npm run modules:compat -- temp-save`, with the folder copied into `sdk/octabam/modules/` and a temporary `sdk/catalog.json` entry (both removed again): 30 active modules, 435 pairs and the whole set, 0 problems.

**Release checks on eadd58a4 and later:** packages rebuilt in the isolated toolchain and imported; `npm run octatrack:module-packages -- --check`: every package identical; published package `public/octatrack-modules/temp-save/0.1.0-experimental.mwrm`, 1,032 bytes, SHA-256 `1078481879f6853a874b79d8bd98959909ea5a882d6f14dedef817dc53af2880` (836 bytes of code and data, 42,892 of bss, 6 relocations, 2 sites). `npm run module:verify -- temp-save --os <1.40C>`: 166 selections, 74 native images match, 92 matching refusals, 0 mismatches (`sdk/native-comparisons/temp-save.json`). Analog BD companion proofs re-exported natively (`export-composition-proofs.py --suite analog-bd --static-stock --vendored-sdk`, toolchain image, 8 shards merged in the committed order): all 212 proofs byte-identical, only `moduleSourceTreeSha256` moves (`242f5527…`). The performance record's flood runs (`evidence/performance.json`) used 001fc493's code, whose instruction path eadd58a4 keeps.

**USB packages (private, not committed).** `build.py --octabam temp-save --name "TEMP SAVE" --stock <1.40C .syx> --upstream <elekloader 3b31ef3c>`: module `84a2f52f`, no relocations or hooks, two hashed stock-code sites; the builder's strict stock-free scans passed. 88b14625: 816 bytes of code and data, 42,892 of bss, 988 bytes, SHA-256 `335e59da…` (hardware run 1). 001fc493: 824 bytes of code and data, 42,892 of bss, SHA-256 `f9f45010275476bd93960b402e4ea7c0d8248c553ba12819846af0327675a687` (hardware run 2).

## What verify.py checked

The fixture is octabam's TMPL project, staged unchanged. Edits are made with the panel: trigs placed in grid recording, knobs turned on AMP and FX1, a scene A lock, the scene A selection.

- **FUNC + YES** shows TEMP SAVED, does not reach stock's ARM ALL routine and changes no pattern, Part, saved-Part or CS1 byte.
- **FUNC + NO** after edits shows RELOADED and does not reach DISARM ALL. The pattern equals the saved copy byte for byte in bank RAM and in its battery copy. The working Part equals the saved copy byte for byte except the scene selection, which keeps the value live before the reload. The CS1 working copy equals RAM, the saved Part is unchanged, the unsaved bit is set in RAM and CS1, and the has-saved byte is as before.
- **Again:** a second FUNC + NO after more edits restores the same copy; a second FUNC + YES replaces it.
- **Bigger edits:** the pattern cleared (FUNC + PLAY) and T3's machine changed FLEX → NEIGHBOR (FUNC + SRC, DOWN, DOWN, YES). FUNC + NO restores both; stock's machine transition `0x400972fc` runs for all eight tracks.
- **The pattern moved to another Part** (PART, DOWN, YES) after FUNC + YES, with the two Parts' scene selections different: FUNC + NO brings back the pattern's Part. Engine and UI Part are the saved one again, and Part Reload's current-Part branch ran (its eight transitions). The restored Part keeps its own live selection, and the other Part is as the edits left it.
- **Another bank** (BANK, trig 3, trig 1): FUNC + NO shows NO TEMP SAVE. On that bank's Parts, which have no saved copy, FUNC + YES / FUNC + NO work, the Part still has no saved copy afterwards and stock RELOAD PART still finds none.
- **MIDI mode:** save, a trig and a knob on a MIDI track, reload restores both.
- **While playing** (`frame on`, PLAY): FUNC + YES, edits, FUNC + NO restore the pattern and the Part, and the sequencer keeps ticking. The two hit counts before and after were identical (41,366 voice binds, 532 ticks), which looks like the watch's cap, so this shows only that it runs.
- **Another pattern** (PTN + trig 2): NO TEMP SAVE, nothing changes; back on the saved pattern FUNC + NO reloads.
- **Windows:** in AMP SETUP, MIXER, PROJECT and PART (MKII; AMP SETUP, MIXER and PART on the MKI) the hooks are reached on press and release, leave the keys to stock, show no module toast and change nothing.
- **Key order:** FUNC let go before YES or NO. Under the port both releases still reached the hooks. Afterwards stock gets FUNC + YES and FUNC + NO in MIXER on press and on release.
- **Stock flows:** YES alone reaches ARM ALL and NO alone DISARM ALL with no module toast; RELOAD PART (FUNC + CUE) restores the saved Part, not the temp save.
- **Quick second presses** (001fc493): FUNC + YES twice and FUNC + NO twice inside the message's lifetime: TEMP SAVED, TEMP SAVED, RELOADED, RELOADED, and neither ARM ALL nor DISARM ALL runs.
- **Cost:** executed ColdFire instructions, interrupts included (frame engine on), from the hook's entry: a save to its toast 16,287; a reload to the end of its screen refresh 637,251 stopped and 640,923 playing. Executed instructions, not chip cycles; not timed on the unit.
- **Power cycle** (CS1 and card kept, `--cs1-in --no-post`): the copy is gone, FUNC + NO shows NO TEMP SAVE.

## Screens

`scripts/capture-module-ui.py` on image `32417b06…`, MKII panel, a card staged from octabam's TMPL project; FUNC is held through each capture because stock clears the message when FUNC is released. The plan and hashes are in `media/capture.json`.

## Code review

An independent review of `unit.s` against the stock disassembly (27 Oct 2026) found:

- **A taken flag could stay set** if a release went to another handler, swallowing a later stock release such as the sample-list preview's. **Fixed:** one flag per key, cleared on every press that goes to stock.
- **No gate for the mode in which YES and NO alone do nothing** (`0x800000b8`), where FUNC + YES / NO are stock's only route to ARM ALL / DISARM ALL. **Fixed:** the module leaves both gestures to stock there.
- **The unit's state sat in `.data`.** **Fixed:** it moved into `.text`, as in Apply Scene.
- **The reload might not apply the Part when the pattern was moved to another Part.** Not reproduced: the Part-switch case above shows the current-Part branch running.
- **Open:** `ts_pat(%pc)` is a 16-bit PC-relative reference into the shared DRAM link's bss. A very large card remix could fail to link ("relocation truncated"); it cannot misbehave at run time. Not seen in the builds above.

## Not tested

- The MKI and the card build on a unit; timing on the unit; the site's review/Keep/Undo flow (the hardware runs used timed trials).
- Audible output in detail: a reload while playing worked by ear, but clicks were not specifically listened for.
- A project save and reload after FUNC + NO; arranger mode and pattern chains; a pattern change queued at the moment of FUNC + NO; the 0x800000b8 mode itself (its stock meaning is not identified).
