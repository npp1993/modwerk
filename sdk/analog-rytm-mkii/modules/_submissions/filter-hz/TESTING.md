# Filter Hz — test report

- Module: `filter-hz` 1.0.0, for Analog Rytm MKII OS 1.73 on core-ar2 0.1.
- Source: https://github.com/Iced-Cream/rytm2_mods at `698b859cc48d990fc0833d3638a5fea4fa07a873` (tag `v1.0`), `filter-hz`.
  `src/filter-hz.s` (`7de4714b…7a8d`) and `include/ar2-1.73.inc` (`c0f1e25c…16ce`) are byte-identical to it.
- Original: MrScruff's rytm-mods `0008-filter-hz`, in rytm-mods-src at `cf5ac006`, marked hardware-verified there.
- Stock OS 1.73: `.syx` `8ad67108…1e52`, main OS `28d9ef40…85d6`.
- Tested build FZ01 (core-ar2 0.1 + filter-hz 1.0): `.syx` `58dec6c48bcd532e71fcb2ea46229ce9c41cb5337aa89e44efe7e3b294369830`,
  main OS `97eab77fccb4420c541175b407bfc708ffe9bb9f7d69fd7e27d1f5aac0cbb0f2`.

## Hardware

On an Analog Rytm MKII with OS 1.73, 2026-10-13, Iced-Cream flashed FZ01 with Elektron
Transfer and confirmed that the FILTER page's FRQ popup shows the cutoff frequency in Hz,
then restored stock 1.73. The port was later confirmed again in a build with all eleven
rytm2_mods ports. Duration and individual readings were not recorded. See
[the hardware report](evidence/hardware-testing.json).

## Source build comparison

The module is a submission (`modules/_submissions/`) until the browser can build it. Modwerk's own validation and compiler path, run on this folder:

```sh
node scripts/machine-modules.mjs --drafts --base origin/main
MODWERK_CROSS=m68k-linux-gnu- node scripts/build-elemod-packages.mjs --output OUT --source-commit <commit> --drafts --module analog-rytm-mkii:filter-hz
node scripts/verify-elemod-source-parity.mjs --packages OUT --oracle ORACLE --out RESULT --firmware analog-rytm-mkii:Analog-Rytm_MKII_OS1.73.syx
```

`ORACLE` held elekloader's `core-0.1.elemod` (core-ar2 0.1, built at elekloader `d17478b`) and
rytm2_mods v1.0's release `filter-hz-1.0.elemod` (`e1d63508…87bf`). The materialised Modwerk
package linked with that core gives main OS `97eab77f…b0f2`, byte-identical to the core linked
with the release object, and to the main OS of FZ01, the build tested on the unit
([source-parity.json](evidence/source-parity.json)). `.run` is 256 bytes, one site, no
relocations. Packed into the stock container by Modwerk's writer it passes `verifyEle3Build`,
flash end `0x1D85B0`, 1,210,960 bytes below the `0x300000` limit.

Compiler: Ubuntu 24.04 `m68k-linux-gnu` GCC 13.3.0 and binutils 2.42. Modwerk's pinned Docker
toolchain was not run here, and CI's `elemod-source` job compiles published folders only.

## Emulator

[rytm-emu](https://github.com/trigcondition/rytm-emu) `3c4c42c`, headless `dtboot`, the same
input on FZ01 and on stock 1.73 ([capture plan](media/capture.json)):

| Screen | Stock 1.73 | FZ01 |
| --- | --- | --- |
| FILTER page | FRQ label | identical |
| FRQ at 60 | `60` | `440Hz` |
| FRQ at 127 | `127` | `21.1kHz` |

Across all 104 screens of the run, every difference lies in the FRQ label (x 3–95,
y 144–159 of the 384×192 PNG); the rest of every screen is identical. The analog voices are
stubbed in the emulator, so this says nothing about sound, which the module does not touch.

## Load and memory

256 bytes in the shared DDR area, no `.bss`, no fast SRAM. The site is in
`param_value_text`, which formats a parameter's value for the screen; for any parameter but
FRQ the stub re-runs the two displaced instructions and returns. Nothing runs in the audio,
sequencer or tick paths. Static reading, not a measurement.

## Not tested

- Filter types other than LP2 against a measured cutoff (the scale is assumed to hold).
- Other modules beside it, except rytm2_mods' own ports.
- Long sessions, project save and reload, and a power cycle with this build were not recorded.
