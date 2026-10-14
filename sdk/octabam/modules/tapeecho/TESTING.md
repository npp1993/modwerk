# Tape Echo testing

Version: 0.1.2-experimental · author: [Jannik Aßfalg](https://github.com/repeat98)

This revision updates author credits only. The historical evidence below is retained; no new hardware or DSP qualification is claimed.


## Source evidence

Evidence source: repeat98/octamad commit `b8deefc88b2c3e5f3c6158e364eb741df1924e1d`. Read [the original record](README.md).

The pinned hardware record reports six instances running and a seventh freezing the unit; that limit remains open. Recorded gates cover native arithmetic parity, dirty state, eight-instance stress, moving controls and repeat/feedback behavior. Hardware timing and worst-case CPU headroom remain unqualified.

## Commands and results

Declared native gates:

`tools/verify/verify_tapeecho_cpu.py`

This SDK import did not rerun these gates. CPU-heavy checks remain paused. Historical results are source records, not new qualification of the SDK or a combined configuration. Record exact commands, tested source commit, workload, modes, track count, duration and results here whenever the module changes.

## Hardware and limitations

Hardware status: historical. Eight instances with all controls reversing in BEAT mode. FREE peaked at 18,063. These emulator instruction counts are not hardware cycles or CPU percentages.

Do not claim a passed hardware test without a model, image version, conditions and actual result. Packaging parity is separate from audio quality and hardware safety.

## OT UI captures — 1 October 2026

Module version: 0.1.2-experimental. Actual firmware-rendered LCD pixels captured
through the headless `ot_emu` interactive panel and `lcd_view.py`;
128×64 LCD, integer scale 6, MKII panel, transport stopped. Empty
scratch FAT16 card; no samples, personal projects or hardware connection.

The image was compiled from a temporary copy of the original seven module
sources and their required internal loader; pending imports were excluded.
Build environment: `REMIX=ui-capture XBUS=1 SPEC=1 DEV=0 BUILD=79
OCTABAM_STATIC_STOCK=0 OCTABAM_NO_CACHE=1`; native `build_bus.main()`
uses the catalog's seven-module profile (`MINIVERB`, `TAPE ECHO`, `EUCLID`
on FX2; the three station modules and Euclid added to FX1). No native
qualification, stress, audio-render or firmware parity gates were run.

Local MAIN OS build SHA-256: `5162680d8bc342deb623cef00307f2a343f539a90f0bfcef59b59ceb4c60bb83`.
Emulator binary SHA-256: `93484e4b71c70f48f795825103146a36ef95ef9ac06ee627e28608ae3e3bb3eb`.

Panel sequence and PNG hashes are recorded in [media/capture.json](media/capture.json).
Capture command: `ot_emu --image <local-image> --card <empty-scratch-card>
--dsp --frame --ms 3000 --interactive --lcd <temporary-plane> --main-level off
--rtc host --mkii`; input uses panel key rows and encoder detents. Export:
`lcd_view.png(lcd_view.screen(lcd_view.read_plane(<temporary-plane>)), <png>, 6)`.
The maintained equivalent is `scripts/capture-module-ui.py`; see
[the capture workflow](../../../../docs/MODULE_UI_CAPTURES.md).

Only screenshots, hashes and documentation are retained. This evidence
does not alter the existing hardware status or qualify a firmware release.

Publication metadata was synchronized with current main without changing native code.
The capture record preserves the original draft version and records the source-file
comparison binding these exact pixels to this documentation/media-only update.

## 0.1.4 MIX dry law (14 October 2026)

Issue [#607](https://github.com/repeat98/modwerk/issues/607): Tape Echo turned the track down. The dry signal now stays at full level through MIX 95 and fades out above it (`dry = min(1, 4*(1-mix))`); the echo path, tables and feedback law are unchanged. The change is the output stage of `tape_block` in `cpu.c` (the native oracle) and its ColdFire counterpart `te_tape_block` in `cpu_kernels.s` (`TE_TAPE_DRY`). `cpu.s` was updated by replacing only its kernel section: the machine code of every function compiled from `cpu.c` is identical to 0.1.3, checked by disassembling both (only `te_tape_block` and the addresses after it differ). A raise of the echo level to match the input was built and measured too, then dropped (below).

**Run.** `tools/verify/verify_tapeecho_cpu.py` in the `modwerk-source-tools` image (m68k-elf-gcc 16.2.0), on a private copy of the SDK with the author's own MAIN OS, against a disposable image holding Tape Echo beside the stock FX2 effects it keeps (the site's keep-stock menu for Tape Echo alone). The vendored SDK carries no `tapeecho` remix, so the image was composed the way `scripts/export-composition-proofs.py` composes its selections, and `vendor/mc68k` came from the upstream checkout. The same run on the unmodified 0.1.3 sources reproduces the figures recorded in the README exactly, so the two columns below compare like for like.

**Result: all gates passed.** Native signal gates, the voice gate (three new dry-level checks: unity through MIX 95, about -6 dB at MIX 111, none at full wet), the fused filter and tape kernels against the native oracle bit for bit (1,024 blocks of the tape kernel: 258 dry, 256 full wet, 254 mixed, 256 ramping, 26 curve-limit records, 5,873 clipped outputs), eight instances bit for bit over 2,300 blocks, and the complete stock delay routine with modelled DMA. The tape kernel's per-block ceiling rose from 1,000 to 1,020 instructions (946 before, 1,010 now, only in the knob-ramp path).

| Executed instructions, 8 instances, full 16-sample routine | 0.1.3 | 0.1.4 |
| --- | ---: | ---: |
| Settled MIX=90, full history, peak | 16,248 | 16,280 |
| Moving FREE TIME, MIX=90, mean | 16,459 | 16,491 |
| MIX / FDBK / AGE endpoint reversals, peak | 17,624 / 17,600 / 17,776 | 18,136 / 18,112 / 18,288 |
| All controls reversing, FREE, peak | 18,063 | 18,575 |
| All controls reversing, BEAT, peak | 21,547 | 22,059 |

Settled blocks pay 4 instructions per instance once; a block whose MIX, FDBK or AGE is ramping pays them per sample, so those peaks are 512 instructions (2.4 to 2.9%) higher while the knob moves. These are executed instructions, not hardware cycles, and the freeze at seven instances is not shown to be related or unrelated.

**Level.** Host oracle, FREE, TIME 64, AGE 64, broadband noise at -20 dBFS RMS, steady output relative to its input (dB), before / after:

| MIX | FDBK 0 | FDBK 64 |
| ---: | ---: | ---: |
| 0 | 0.0 / 0.0 | 0.0 / 0.0 |
| 32 | -2.4 / +0.1 | -2.4 / +0.1 |
| 64 | -5.4 / +0.2 | -5.3 / +0.2 |
| 90 | -7.8 / +0.3 | -7.4 / +0.4 |
| 111 | -8.7 / -4.3 | -7.8 / -3.9 |
| 127 | -8.0 / -8.0 | -7.1 / -7.1 |

A decaying 180 Hz hit keeps its level (0.0 dB) at MIX 64 and 90, against -6.1 and -10.7 dB before. Above MIX 95 the level falls toward the echo-only level, as it always did at 127.

**Rejected: raising the echo level.** Making the first repeat return at its input level (+5.6 dB wet makeup with the feedback table divided by the same factor, so repeat decay was unchanged) matched a 1 kHz tone to within 0.15 dB, but 20-second self-oscillation runs at full wet clipped the output: 25.3% of samples at FDBK 102, 49.1% at FDBK 110 and 68.0% at FDBK 127, against none and peaks of 0.66, 0.78 and 0.96 of full scale for the shipped level. The shipped level has the same figures as before, with no clipped samples.

**Native and browser comparison (14 October 2026).** `npm run module:verify -- tapeecho` on the author's own 1.40C: 126 selections, 54 native module-owned images that Modwerk's browser builder reproduces, 72 matching refusals, 0 mismatches. The 76 Analog BD profiles that contain Tape Echo were re-exported natively (52 images changed, 24 refusals identical) and `scripts/verify-analog-bd-native.mjs` passes against them: 162 native OS comparisons and bootloader comparisons, 50 matching refusals, 6 firmware round trips. The ColdFire link oracles of the three Tape Echo cases (`coldfire-runtime-oracles.json`) were relinked with GNU `m68k-elf-ld`; the same procedure reproduces the two cases without Tape Echo exactly. The published USB package (`public/octatrack-modules/tapeecho/0.1.4-experimental.mwrm`) was rebuilt from its reviewed standalone recipe, which now lists seven spans that coincide with stock (the end of `te_tape_block` and the start of `te_read_linear` shifted and split in two); both strict stock-free scans pass (longest shared run 11 bytes, limit 12). `octatrack-module-packages.py --check` is identical for every other package.

**Not tested for this version:** any hardware (the unit, a seventh instance, UI responsiveness while editing, the USB package on a real base), chip cycles, `npm run fx:audit` (aliasing, DC, idle), listening, Part/project save and reload, reboot persistence, multiple-instance isolation beyond the eight-instance emulator gate. Emulator figures, the host oracle and the software comparisons above do not establish any of them. The UI captures above show the same panel for 0.1.4 and are retained from 0.1.2 by the owner's exact-version approval (`sdk/tapeecho-build-approval.json`).
