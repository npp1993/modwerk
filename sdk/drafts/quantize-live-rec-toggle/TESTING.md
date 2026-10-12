# Quantize Live Rec Toggle: tests and measurements

Recorded 12 October 2026. Version `0.1.0-experimental`.

- Upstream: sambanks/octabam `6e4aeb76695cbb612e4b424c55fd2207facf73ef`, which takes the module from Zac-Kyoti/octatrack-kyoti-fw `77f132f9a60c6afa98ea4486540f6107398bdad3`.
- Native source SHA-256 of this folder (`moduleNativeSourceSha256`): `d9b8743bdc54a2a45b66ef09e938ce0173d79fb87fa015f472ff03bab96e0936`.
- Tested image (this module alone, card route, from the original OS 1.40C): MAIN OS SHA-256 `dc90fdcebd69a38a675d29750daa64bbc2e497c0259fc2e309c9b3c14828b106`.

## Not tested

- **Nothing has been tested on an MKII, and this Modwerk build has not run on any unit.** No flash, no audio, no real power cycle.
- An MKI panel in the emulator; a project loaded from a real card; grid recording; MIDI tracks; the gesture with no project loaded.
- Chip timing, frame-interrupt load and any stress run (see Performance).
- Loading over USB onto the Modwerk base: the base's loader cannot yet carry a ColdFire module with stock-code hooks.

## Source identity

`patch_qlrec.s` is byte-identical to the author's file (SHA-256 `aef5e34cf48b99c059a800bc8ccd5834b9a08e578b4e7ce6965bfb210832b33f`). Native octabam, in the pinned toolchain container without network, links it where the unit floats and again at the author's own address `0x400d7400` and compares: 176 bytes, SHA-256 `52c26af67443e470147844a52009d09fa308be5045a1f891c01344dbbaa8670d`, a match. Its build report shows the unit and the two `jmp` detours at `0x40061778` and `0x4004883a`.

The three stock guards in `manifest.py` (both hook sites and the retired site `0x400522ca`) were computed from the author's declared expectations and matched against a local original OS 1.40C MAIN image (SHA-256 `164f31224bf61181e3f50e7dec40df9afcae5b16dbf6e4c0d0cc5e986af0a84e`). `patch_qlrec.s` holds no firmware bytes: its comments describe stock routines by address and mnemonic.

## The gate

`verify.py`, run from an octabam root that holds the built image, the original MAIN OS and the ColdFire port:

```sh
OT_EMU=<path to ot_emu> python3 modules/quantize-live-rec-toggle/verify.py
```

Result on the tested image: **29 of 29 checks passed.**

1. The image, byte for byte: `0x400522ca` is as the original OS has it; both hook sites hold a `jmp`, 0x74 apart, into one unit; that unit is the author's 176 bytes.
2. The gesture by the keys (MKII panel, empty card, DSP cores running), on the module image and on the original OS:
   - the first [REC] + [PLAY] starts live recording on both, and leaves the setting alone; the module also opens the toast;
   - a second [PLAY] while the toast is up inverts the setting and its battery copy, and a third puts it back;
   - after the toast has run out, [PLAY] shows it again and does not invert;
   - releasing [REC] clears stock's held flag and closes the toast; [STOP] ends live recording;
   - [PLAY] without [REC] opens no toast and changes nothing;
   - the original OS under the same keys never changes the setting and never opens a toast.
3. A power cycle of the port: the battery RAM of a run that left the setting inverted, booted again, comes up inverted. This is the emulator's battery RAM, not a unit's.

Separately, PERSONALIZE was opened in the emulator before and after one inversion: the QUANTIZE LIVE REC box was ticked while the toast said ON and empty after it said OFF, so the toast and the menu agree there. The fresh emulator state has the setting ON.

The emulator used is the user's local build of octabam's `ot_emu` (SHA-256 `23ba6f6cdc6ec4b89b8cf206915e66d3160aec8499b1abfc9b475ac849152b28`). It does not run a real unit's timing, and the author's note that scratch RAM did not survive on hardware while it did in the emulator is the reason this module keeps no state of its own.

## Stock flows compared

Run with and without the module (the gate's second part): starting live recording with [REC] + [PLAY], [PLAY] alone, [STOP], [REC] press and release. One change, listed in the README: the toast on [REC] + [PLAY], and that a [REC] + [PLAY] during live recording shows or inverts the setting where stock does nothing. Flows not run are under Not tested.

## Performance

Executed instructions of the unit, counted with the port's program-counter watch on every instruction of it:

| Press | Authored instructions |
|---|---:|
| [PLAY] without [REC] | 4 |
| [REC] + [PLAY]: show, live recording starts | 17 |
| [PLAY]: invert while live recording runs | 23 |
| [PLAY]: invert, live recording stopped (then stock's [PLAY] path) | 23 |
| [REC] release with a toast up | 5 |
| [REC] release without | 4 |

The longest path in the source is 24 instructions. `evidence/performance.json` prices an instruction at 16 core cycles, the conservative V4 envelope Mute Modes' TESTING.md derives from the MCF54455 manual: 384 static, 368 measured, against one 362.8 µs frame at 264 MHz (95,778) taken as a generous deadline for a key handler. These are not chip timings. The stock routines the unit calls (the project gate, the checksum, opening and closing the notification) are stock cost and are not counted.

`npm run perf:audit -- check evidence/performance.json` passes the cycle row and **fails the stock benchmark and the stress run: neither was measured.** Both are defined for code in the frame or MIDI path (a `cfmeter.py` capture from a unit, a MIDI flood). This unit runs only inside two key handlers and handles no MIDI, so by its source it adds nothing to the frame interrupt; that is an argument, not a measurement. `module:doctor` therefore reports the performance line as failing until the owner accepts or waives it.

## Memory

176 bytes of ROM for the unit (code and two strings; position independent, so the same anywhere) and two six-byte detours over stock instructions: 188 bytes. No RAM of its own, no DSP memory, no heap. It reads stock's [REC]-held and live-recording flags and the notification handle, and writes the stock setting word and its battery copy, then calls stock's checksum routine as the PERSONALIZE menu does.

## Native comparison and listing dry run

Done on 12 October 2026 on a scratch copy of the Elekloader migration branch (since merged as repeat98/modwerk#464) with the module listed (catalogue entry, packages built in the isolated toolchain container and imported, `npm run module:verify -- quantize-live-rec-toggle --os <OS 1.40C update file>`). None of it is committed; the shared-code patch, the comparison record and the logs are kept outside the repository with the session notes.

- **130 selections: 56 built and identical to native octabam (20 outright, 36 outside the platform writes), 74 matching refusals, 0 mismatches.** The module alone is identical outright.
- Getting there needed two changes to the shared browser composer (`src/engine/requested-modules.ts`): place this module's ROM unit after the utility and replacing modules, as native does for a module this late in the catalogue (14 mismatches before), and refuse a Recorder Loop Fix cave that does not fit at the cave cursor, as native does, where the browser moved it to the overflow run (one nine-module selection). Every other module's committed comparison record shows the same mismatch count with and without them; those records were already stale on this base.
- `module:verify` needed the one-line Node fix from repeat98/modwerk#482 applied locally: on this base `src/engine/protocol.ts` reads Vite's environment, which stops the tool in Node.
- `npm run check -- --base 0659ebc1` in that state, with a clearly marked temporary hardware placeholder so the tools would run: 1,889 of 1,890 tests passed. The one failure is `module:doctor --all`, on the two unmeasured performance rows below. Without the placeholder `modules:check` stops first, at the missing hardware report.
- `npm run module:doctor -- quantize-live-rec-toggle`: every line green except those two performance rows.

What listing still needs:

1. A hardware report from an MKII for the exact test image (`tests.qualification.hardware`; `qualification.example.json` is the record with that part left open).
2. The owner's decision on the two performance rows that were not measured (Performance, above).
3. Room for the declaration checks: listing records 493,056 more selections and takes `src/catalog/native-metadata.json` from 70 MB to 142 MB, over GitHub's 100 MB file limit. That needs a change to how the record is kept.
4. The `module:verify` step also adds this module to `src/engine/assets/chooser-metadata.json`, which the Octatrack base hashes as a build input, so the committed base would have to be rebuilt. The module builds to the same bytes without that entry.
5. Then: move the folder to `sdk/octabam/modules/`, add the catalogue entry, the licence component and the changelog entry, build and import the packages, and run `module:verify`.

## Captures

`media/capture.json` records the plan, the image and emulator hashes and each PNG's hash. Made with `scripts/capture-module-ui.py --key-ms 100` on the tested image. Every picture was opened and checked: the two toasts over the main screen, and PERSONALIZE with QUANTIZE LIVE REC selected and its box empty after the switch to OFF.

## Upstream hardware reports

The author reports, for his own standalone build of this source on an MKI: the show-then-invert gesture working with the tick hook removed (25 September 2026), and a changed setting surviving a power cycle (30 September 2026). He also records that an earlier version, which hooked the engine frame handler at `0x400522ca`, hard-crashed that MKI; this version does not touch that site, and the gate checks it. These are reports about his image, not tests of this build.
