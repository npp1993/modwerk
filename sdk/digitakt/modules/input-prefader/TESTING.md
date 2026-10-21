# Input Pre-Fader Sends testing

Module version 0.2.0-experimental, Digitakt I OS 1.54 (stock file SHA-256 `f78ba80f…3cf6`), Core 2.1. Firmware, linked images and emulator state stay on the developer's computer; none of it is committed.

## Evidence tier

Emulator and author hardware. The author (draadpiraat) flashed both exact builds of section 3 on their own Digitakt I, OS 1.54, on 2026-10-20, and reported the results in section 5. Pattern changes and sampling from the inputs are not tested.

## How it works (OS 1.54)

**INPUT SENDS PRE.** The render's mixer (0x40071c20) loops over ten channels: tracks 1-8, then IN L and IN R. For each one it builds two pan gains, multiplies them by the LEV gain (0x40071e36) and derives the delay and reverb sends from those post-LEV gains (0x40071eb4). The module saves the pan gains at the first site and, for channels 8 and 9 with the row ticked, uses them at the second. Both handlers replay the instructions they replace; their assembled encodings are identical to the stock ones. Unchanged since 0.1.0.

**KEEP FX AWAKE.** A double STOP (and a project load) sets an effects-hold state word in the audio interrupt's data. While it holds, every audio block fades one effect level towards 0 and keeps the effects' inputs cleared; the stock firmware clears the state only where an audio track's voice starts. The audio interrupt reads that word once a block (0x40077ef8) before branching past the hold's work. The module's handler replays that read; with the row ticked, a hold whose fade has reached 0 is cleared first, as a trig would. Unticked, the handler only replays the read.

## 1. Site equivalence (patched Unicorn from pinned digiemu)

0.1.0's 20,000-case comparison of the two mixer sites against stock (all 16 registers, both accumulators, the stack; MACSR 0xA0) found 0 differences in every mode. Their handlers' instructions are unchanged in 0.2.0; only the flag the ticked test reads moved within the module's BSS. The row handlers now serve two rows through a flag pointer.

## 2. Running firmware (pinned digiemu c1b5735, firmware-native drawing)

A 440 Hz tone was fed into IN L/R through digiemu's SSI receive hook; IN L/R LEV, DEL and REV 127 were set by memory write in the External Mixer block; RMS of the output was measured in 400 ms windows after the tone stopped (the effects' tail only).

| Build and phase | Tail RMS |
| --- | --- |
| Stock 1.54, before STOP STOP | 5535, 2700, 1661 |
| Stock 1.54, after STOP STOP | 0, 0, 0 |
| Stock 1.54, after STOP STOP and clearing the hold word by memory write | 5085, 2907, 1632 |
| This module, KEEP FX AWAKE unticked, after STOP STOP | 0, 0, 0 (hold still set 1.5 s later) |
| This module, KEEP FX AWAKE ticked, before STOP STOP | 5039, 2691, 1633 |
| This module, ticked, the 1.5 s right after STOP STOP | 2, 32, 29, 17, 15, 10 (250 ms windows; hold released) |
| This module, ticked, after STOP STOP | 5441, 2769, 1532 |
| Core 2.1 + Digi Health + Digi EQ + this module, ticked, after STOP STOP | 5041, 2699, 1635 |

Build `.syx` SHA-256: module alone `ddf836a3…40fa64`; with Digi Health 1.0 and Digi EQ 1.0.2-experimental `a60b869f…ea6aa6`. Rows ticked with real panel keys (SETTINGS, 10 × DOWN, RIGHT; 12 × DOWN with Digi Health). No halt. The emulator boots without the hold, so the power-on case is hardware-only.

Notes: in the emulator, real External Mixer knob turns reach the render before any trig, and a trig writes nothing the effects code reads; the hold is the only gate found.

## 3. Build and rules

- `npm run modules:check`: passes (no overlap with any Modwerk Digitakt module's bytes).
- The local build and the main-based branch produce the identical images `ddf836a3…` and `a60b869f…`.
- Memory: 422 bytes of code, 12 bytes of BSS in DDR; no fast SRAM.
- Load (emulator, [cpu-load.json](evidence/cpu-load.json)): CycleClock at 250 MHz, zero-wait memory, the audio interrupt from entry to `rte` over 3,000 blocks of 166,666 cycles. Stock 100,448 mean / 101,241 worst; both rows ticked 100,858 / 101,726 (+410 / +485); unticked 100,779 / 101,571 (+331 / +330). About 0.2% average, 0.3% worst case of a block. Not a hardware measurement.

## 4. Screens

[capture.json](media/capture.json): the three SETTINGS screenshots from the module-alone build, in the pinned emulator.

## 5. Hardware (author's Digitakt I, OS 1.54, 2026-10-20)

Builds sent with Elektron Transfer. Source into IN L and IN R, the inputs' DEL and REV up. Results as reported by the author.

**Build A**, Core 2.1 + this module, `.syx` SHA-256 `ddf836a3…40fa64`: "everything checks out, all 7 points".

| Step | Check | Result |
| --- | --- | --- |
| 1 | KEEP FX AWAKE appears in SETTINGS below INPUT SENDS PRE, unticked | Yes |
| 2 | Unticked, after power-on: input effects silent until a trig (stock) | Yes |
| 3 | Ticked: effects come back after a double STOP, without a trig | Yes |
| 4 | Ticked: a double STOP still cuts the tail | Yes: "cut out the tail completely right away" |
| 5 | Ticked: effects come back after loading a project | Yes |
| 6 | Unticked again: a double STOP holds until a trig (stock) | Yes |
| 7 | INPUT SENDS PRE ticked, LEV 0: fully wet | Yes |

**Build B**, Core 2.1 + Digi Health 1.0 + Digi EQ 1.0.2-experimental + this module, `.syx` SHA-256 `a60b869f…ea6aa6`: steps 1 and 3-7 as build A. Step 2: "the fx are still awake after power on and the keep FX awake is ticked off (stock) though double pressing stop follows normal stock behaviour".

**Control**, Core 2.1 + Digi Health 1.0 + Digi EQ 1.0.2-experimental without this module, `.syx` SHA-256 `e4c11db6…49b02`: "fx become awake at power on, but only after about 5-10 seconds". The power-on difference in build B therefore comes from those modules, not from this one.

**Use.** After these steps the author played with the module for "about an hour or 2 without any issues whatsoever".

0.1.0's hardware results for INPUT SENDS PRE (2026-10-19, `e0f55015…4b89` and `3e8e6422…07d3`) are in the module's history; step 7 rechecked it on this build.

## Stock flows compared

| Flow | Result |
| --- | --- |
| SETTINGS menu: stock rows and order | Unchanged in the emulator; the two rows are added at the end |
| Mixer with INPUT SENDS PRE unticked | Bit-identical to stock (section 1) |
| Effects hold with KEEP FX AWAKE unticked | Stock: held until a trig (sections 2 and 5) |
| Tracks 1-8 sends and dry gains | Unchanged in both modes (section 1) |
| Power cycle | Both rows unticked again |
| Project load | With KEEP FX AWAKE ticked, effects come back without a trig (section 5) |
| Pattern change, sampling from the inputs | Not tested |

## Still to test

- Pattern changes with both rows ticked.
- Sampling from the inputs with the rows ticked.
