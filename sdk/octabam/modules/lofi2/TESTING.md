# LOFI2: testing record

Module version `0.1.0-experimental`. Source: octabam `modules/lofi2` at commit `e8665fae3975c68a8b52ba8047c45aef5753a3f7`, the head of Bryan T's pull request 704 ("LOFI2: 654 -> 414 cycles/sample in SHIFT; eight instances fit", branch `bryantysinger:lofi2-opt`), which was open and unmerged when imported on 12 October 2026. It sits two commits on top of the merged LOFI2 (`a6f41a1dff922be622e2e8a7d93bc5a5958c90ab`, pull request 657) and changes `lofi2.asm`, one line of `manifest.py` and the README. The Modwerk adaptations are listed in README.md. An earlier local revision of this import pinned `a6f41a1d`; every result below was rerun on `e8665fae`. Recorded 12 October 2026. The import is based on `main` at `addca5cf`, which contains the Elekloader migration (pull request 464).

Everything below marked **here** was run for this import, in the emulator and `dsp_host` on a computer. **Nothing was run on hardware for this import.** Everything marked **upstream** is the author's own report, quoted with attribution, and applies to his octabam images, not to this build.

## Identity

| Item | SHA-256 |
| --- | --- |
| `lofi2.asm` (unchanged from upstream) | `cecdd20bfca0f7561fa8c34c8066780e50406cf2396d8ee2ed42aad5bdf5d5ab` |
| `manifest.py` (adapted) | `96b362e87ad633568f8004847bdd31d2f63fb74f788bc07c5f0175e9413aea32` |
| `verify_lofi2.py` (adapted) | `d8feb6850d283a0a605bf206f81cd52b38cda81890298b3baed8b217ee467537` |
| Stock MAIN OS 1.40C used (the tester's own, never committed) | `164f31224bf61181e3f50e7dec40df9afcae5b16dbf6e4c0d0cc5e986af0a84e` |
| Private native image of the `lofi2` test remix (static stock, never committed) | `43e110ff87d66c0b3aa47fc1eaf8d2effedb331a121f32fcbbc51ff15f21b24e` |
| `dsp_host` | `bde6cf5f348e215d7adca2080044533ee7853407469cee7f887fce8ef3865fd9` |
| `ot_emu` | `23ba6f6cdc6ec4b89b8cf206915e66d3160aec8499b1abfc9b475ac849152b28` |

## How it was built (here)

A scratch copy of `sdk/octabam` with this folder copied to `modules/lofi2`, the patched DSP56300 tools under `vendor/`, the tester's own 1.40C MAIN OS at `out/raw/section_3_MAIN_OS.bin`, and the author's test remix (`upstream/remixes/test/lofi2/remix.py`, LOFI2 beside twelve stock effects with PLATE REV and SPRING REV given up) at `remixes/test/lofi2/`.

```sh
export OCTABAM_STATIC_STOCK=1          # what the Makefile exports; no DSP loader
make bus REMIX=lofi2
python3 modules/lofi2/verify_lofi2.py
python3 tools/verify/verify_dirtystate.py lofi2
python3 tools/verify/verify_initregs.py lofi2
REMIX=lofi2 python3 tools/verify/verify_menu.py
python3 tools/verify/verify_replaces.py --image lofi2
.venv/bin/python3 tools/verify/verify_labels.py lofi2
.venv/bin/python3 tools/verify/verify_modenames.py lofi2
make cycles REMIX=lofi2
```

Build report, both payloads identical in size:

| Payload | Table | Code | Region | Free |
| --- | --- | --- | --- | --- |
| A (core 0, tracks 5-8) | P:0x01000..0x01204, 516 words | P:0x01204..0x01548, 836 words | PLATE REV + SPRING REV, 1,657 words | 305 |
| B (core 1, tracks 1-4) | P:0x00dc0..0x00fc4, 516 words | P:0x00fc4..0x01308, 836 words | 1,657 words | 305 |

ColdFire: descriptor clone at 0x400d6b20 (416 bytes), two label formatters (RANGE 54 bytes, MODE 188 bytes), no code of its own. The table stays in P memory in this remix because DJ EQ is kept.

## Render gate: `verify_lofi2.py` (here)

All 48 checks pass. `dsp_host`, payload A, a scratch image holding LOFI2 alone. Stock LO-FI is rendered from the tester's own stock image for the SRR and BRR comparisons.

| Result | Check | Measured |
| --- | --- | --- |
| PASS | ring level, GAIN 0: -2.80 dB re MIX 0 | -2.79 dB |
| PASS | GAIN 64: +6.02 dB re GAIN 0 | +6.02 dB |
| PASS | GAIN 127: +11.95 dB re GAIN 0 | +11.95 dB |
| PASS | SHIFT UP level: about -0.07 dB re MIX 0 | -0.07 dB |
| PASS | AMPH 0 deg (64): L == R bit for bit |  |
| PASS | AMPH +45 / -45 deg: L untouched |  |
| PASS | AMPH +45 / -45 deg: R moved, differently |  |
| PASS | fade-in: the first 32 samples carry < 20% of the steady wet | 0.026 of steady |
| PASS | fade-in: the wet is back within 0.5 dB by 9 ms | -0.02 dB |
| PASS | MODE RING -> UP: no step larger than the steady states' | switch 13529 vs steady 11685 (d2, LSB) |
| PASS | MODE RING -> UP: passes through the dry | closest 16-sample window 2176 LSB (limit 83886) |
| PASS | SRR 16: the hold's droop at 2 kHz matches stock's | stock -0.07 dB, LOFI2 -0.08 dB |
| PASS | SRR 32: the hold's droop at 2 kHz matches stock's | stock -0.23 dB, LOFI2 -0.24 dB |
| PASS | SRR 64: the hold's droop at 2 kHz matches stock's | stock -0.90 dB, LOFI2 -0.98 dB |
| PASS | SRR 96: the hold's droop at 2 kHz matches stock's | stock -2.38 dB, LOFI2 -2.38 dB |
| PASS | SRR 127: the hold's droop at 2 kHz matches stock's | stock -5.09 dB, LOFI2 -5.08 dB |
| PASS | SRR turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | BRR 16: the step matches stock's | stock 3.32 bits (375 plateaus), LOFI2 3.322 bits (377) |
| PASS | BRR 32: the step matches stock's | stock 7.107 bits (375 plateaus), LOFI2 7.098 bits (376) |
| PASS | BRR 48: the step matches stock's | stock 10.502 bits (375 plateaus), LOFI2 10.5 bits (375) |
| PASS | BRR 64: the step matches stock's | stock 13.458 bits (375 plateaus), LOFI2 13.453 bits (376) |
| PASS | BRR 80: the step matches stock's | stock 15.977 bits (109 plateaus), LOFI2 15.977 bits (110) |
| PASS | BRR 96: the step matches stock's | stock 18.055 bits (26 plateaus), LOFI2 18.054 bits (26) |
| PASS | BRR 112: the step matches stock's | stock 19.699 bits (8 plateaus), LOFI2 19.698 bits (8) |
| PASS | BRR 127: the step matches stock's | stock 20.8 bits (4 plateaus), LOFI2 20.801 bits (4) |
| PASS | BRR 64: unity gain against BRR 0 | -0.001 dB |
| PASS | BRR turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | LPF 0: the shelf matches its design | c 0.98586 (table 0.98585), DC 0.99995, Nyquist -12.04 dB |
| PASS | LPF 0: no gain above unity anywhere (feedback-safe) | peak -0.0004 dB |
| PASS | LPF 32: the shelf matches its design | c 0.94959 (table 0.94959), DC 0.99999, Nyquist -12.04 dB |
| PASS | LPF 32: no gain above unity anywhere (feedback-safe) | peak -0.0001 dB |
| PASS | LPF 64: the shelf matches its design | c 0.82800 (table 0.82800), DC 1.00000, Nyquist -12.04 dB |
| PASS | LPF 64: no gain above unity anywhere (feedback-safe) | peak -0.0000 dB |
| PASS | LPF 96: the shelf matches its design | c 0.47685 (table 0.47685), DC 1.00000, Nyquist -12.04 dB |
| PASS | LPF 96: no gain above unity anywhere (feedback-safe) | peak -0.0000 dB |
| PASS | LPF 120: the shelf matches its design | c -0.11015 (table -0.11015), DC 1.00000, Nyquist -12.04 dB |
| PASS | LPF 120: no gain above unity anywhere (feedback-safe) | peak +0.0000 dB |
| PASS | LPF 126: the shelf matches its design | c -0.37003 (table -0.37003), DC 1.00000, Nyquist -12.04 dB |
| PASS | LPF 126: no gain above unity anywhere (feedback-safe) | peak -0.0000 dB |
| PASS | LPF 127: the shelf out of circuit, output == input bit for bit | delay 0 samples |
| PASS | LPF turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | FREQ: an LFO's fraction between two knob steps is heard (64 + 1/2 lands between 64 and 65) | 480.40 / 487.86 / 495.54 Hz, 0.50 of the step |
| PASS | FREQ turn 20 -> 110, RING: block-locked step under -70 dBFS | turn -140.0 dBFS, held -106.6 |
| PASS | FREQ turn 20 -> 110, SHIFT UP: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | MIX, RING turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | GAIN, RING turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | FDBK, SHIFT UP turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
| PASS | AMPH, RING (R) turn 20 -> 110: block-locked step under -70 dBFS | turn -140.0 dBFS, held -140.0 |
Not covered by this gate, as its author notes: payload B (tracks 1-4). `verify_dirtystate` below renders both payloads.

## Other gates (here)

| Gate | Result |
| --- | --- |
| `verify_dirtystate.py lofi2` | PASS: 8 renders, 0 failed; defaults and every knob nudged from a garbage-filled instance block, both payloads, tail -138.5 dBFS |
| `verify_initregs.py lofi2` | PASS: init preserves r1 |
| `verify_menu.py` | PASS: the panel prints `LOFI2`, abbreviation `LOF2`, nine drawn slot names match the manifest; FX1 chooser byte-identical to stock in this remix |
| `verify_replaces.py --image lofi2` | PASS: every stock id is stock's, or declared |
| `verify_labels.py lofi2` | PASS: RANGE prints LOW / HIGH, MODE prints RING / DOWN / UP |
| `verify_modenames.py lofi2` | PASS, 7 checks: RING names slot 2 GAIN, DOWN and UP name it FDBK, out-of-range values clamp |
| `verify_dram_boot.py`, `verify_hidden.py` | not applicable (no DRAM payload, nothing hidden) |
| `verify_set.py`, `verify_usb.py`, the `verify_knob_clicks.py` census, `make check` as a whole | not run |

Without `OCTABAM_STATIC_STOCK=1` (a direct script run, which adds octabam's experimental DSP loader) `verify_dirtystate` and `verify_replaces` report failures; that loader is not what Modwerk ships and those runs are not counted.

## Size and fit (here)

Native builds with stock DSP code built in; each row is a real `make bus` run of a scratch remix, core 0 shown (core 1 agrees).

| Selection | Stock effects given up | Result |
| --- | --- | --- |
| LOFI2 | none | refused |
| LOFI2 | PLATE REV | refused: 1,352 > 594 words |
| LOFI2 | SPRING REV | refused: 1,352 > 1,063 words |
| LOFI2 | DARK REV | refused: 1,352 > 1,067 words |
| LOFI2 | PLATE REV + SPRING REV | fits: 1,657-word region, 305 free |
| LOFI2 | SPRING REV + DARK REV | fits: 2,130-word region, 778 free |
| Output Matrix + TapeHead + Sidechain Compressor + LOFI2 | three reverbs | refused: 2,931 > 2,724 words |
| the same | three reverbs + CHORUS | fits: 3,053-word region, 122 free |
| the same | three reverbs + LO-FI | fits: two runs, 3,261 words, 330 free |
| Analog BD + LOFI2, with or without the others | three reverbs (+ LO-FI) | refused: "ANALOG BD cannot share DSP memory with LOFI2" (not on `DSP_COMPANIONS` in `tools/build/ab_image.py`) |

Scratch-only probe, **not part of this change and not reviewed**: with `DSP_COMPANIONS` widened locally to admit LOFI2 and Output Matrix, Analog BD + Output Matrix + TapeHead + Sidechain Compressor + LOFI2 is refused with three reverbs + LO-FI given up (LOFI2 needs 1,352 contiguous words, largest opening 1,067), refused with DJ EQ also given up (the build then parks LOFI2's table in the stock curve bank in X memory, and Sidechain Compressor no longer finds an opening: largest 298), and builds with CHORUS given up as well (four runs, 2,903 words, 488 free). That image was only built, never run. A table read from X memory by a dispatched effect is reported hardware-proven in octabam for another module, not for LOFI2.

Module words in those builds: TapeHead 422, Output Matrix 727 + 42 table, Sidechain Compressor 340 + 48 table, LOFI2 836 + 516 table.

## Cost (here)

Static, `tools/build/cycle_count.py`: **414 cycles/sample** on the dearest path (SHIFT); the merged revision counted 654. Four instances on one core: 1,656 of the 3,120 the counter calls usable.

`python3 modules/lofi2/perf.py bench <out>` (Modwerk's own script, after E-Verb's): `benchmark_stock_dsp.py`'s method (one instance per core at positions 0 and 4, audio at X:0, 4,096 blocks of 16 frames, the null stub's peak subtracted), executed instructions per sample, not chip cycles. LOFI2 on the private image, stock effects on the stock image, through the same fixed, moving and trig-split (positions 1-15) cases:

| Effect | Worst, no split | Worst with splits |
| --- | --- | --- |
| LOFI2, SHIFT DOWN at the manifest's dearest settings | 405.44 | 429.06 |
| LOFI2, SHIFT UP at the dearest settings | 405.06 | 428.31 |
| LOFI2, RING at the dearest settings | 251.06 | 274.31 |
| LOFI2, defaults (passthrough) | 249.88 | not run |
| stock LO-FI | 275.44 | 290.06 |
| stock SPRING REV | 257.50 | 314.19 |
| stock DARK REV | 193.25 | 242.38 |
| stock DJ EQ | 293.38 | 330.94 |

The stock figures without splits reproduce E-Verb's record (SPRING REV 257.5, DARK REV 193.25, DJ EQ 293.38), a positive control on the method. LOFI2 in SHIFT is 1.37x SPRING REV's worst case and 1.48x stock LO-FI's (the closest stock effect); in RING 0.87x and 0.95x. The merged revision (`a6f41a1d`) measured 596.4 and 347.4 with an earlier scratch script. SHIFT is dearer than every stock effect (DJ EQ 330.94), which the performance audit accepts only with a justification and the owner's acceptance; the justification is in `evidence/performance.json`.

`python3 modules/lofi2/perf.py stress <out> --seconds 32`: LOFI2 on FX2 of all eight tracks (four per core) behind DJ EQ on every FX1; three LFOs per track on FREQ, SRR and LPF; a new random value on all 14 named slots of both effects every sixteenth at 120 BPM, MODE and RANGE included, so the modes switch under load; trig splits of 1, 3, 7, 8, 12 and 15 frames on six tracks; eight different stems, 32 s plus a 2 s tail; `dsp_host -guard 0x4000 -guard-shared -dirty 0x5a`. Result: host exit 0, no hang, 16 guarded instances, LOFI2's eight instances 0 stray write regions and 0 clobbers, 0 clobbers overall; per-core peak 3,009.9 and 3,010.1 executed instructions/sample with all sixteen effects (824 s of wall time). It exercises the DSP side only.

`npm run perf:audit -- check sdk/octabam/modules/lofi2/evidence/performance.json`:

```
✓ record          dsp record for lofi2@0.1.0-experimental
· cycles          4 x 414 = 1656 of 3120 per sample per core (53%), measured 429.06 per instance; over half a core: say what stays free for stock effects and other modules
· stock benchmark 429.06 vs LO-FI 290.06 (1.48x); the dearest stock effect is 330.94; justified in the record
✓ stress          4 per core, eight tracks, 3 LFOs and 14 locked slots, 32 s, no clobber, no hang
```

No check failed. What stays free: with four SHIFT instances on a core, 1,464 static cycles remain of the 3,120, about four stock effects at SPRING REV's cost on the same core's FX1 slots. Four RING instances leave more.

The author's own weighting of the SHIFT loop by measured chip move costs (his README, "Cost, and how many fit") gives about 990 against about 1,530 for the September source; he calls those ratios, not cycles. Not reproduced here.

## Sound quality: `npm run fx:audit` (here)

`npm run fx:audit -- plan`, each signal rendered through LOFI2 with `dsp_host` on payload A of the private image (mono in, both channels; one instance; a scratch script, not committed), then `npm run fx:audit -- check`. Audit defaults: aliasing -60 dBc, DC -60 dBFS, idle -90 dBFS.

Defaults (MIX 0, SRR 0, BRR 0, LPF 127), the passthrough: no check failed, idle is digital silence.

| signal | out dBFS | harmonics | aliasing | residual | DC dBFS | rails | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tone-1100hz-12db | -12.0 | <-140 | <-140 | -134.5 | <-140 | 0 | ok |
| tone-1100hz-1db | -1.0 | <-140 | <-140 | <-140 | <-140 | 0 | ok |
| tone-2701hz-12db | -12.0 | <-140 | <-140 | -134.5 | <-140 | 0 | ok |
| tone-2701hz-1db | -1.0 | <-140 | <-140 | <-140 | <-140 | 0 | ok |
| tone-5301hz-12db | -12.0 | <-140 | <-140 | -134.6 | <-140 | 0 | ok |
| tone-5301hz-1db | -1.0 | <-140 | <-140 | <-140 | <-140 | 0 | ok |
| tone-9102hz-12db | -12.0 | <-140 | <-140 | -134.5 | <-140 | 0 | ok |
| tone-9102hz-1db | -1.0 | <-140 | <-140 | <-140 | <-140 | 0 | ok |

LPF 0 (the shelf fully in, everything else at its default): no check failed, idle is digital silence. The level drop is the shelf's -12 dB.

| signal | out dBFS | harmonics | aliasing | residual | DC dBFS | rails | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tone-1100hz-12db | -23.5 | <-140 | <-140 | -121.1 | <-140 | 0 | ok |
| tone-1100hz-1db | -12.5 | <-140 | <-140 | -132.1 | <-140 | 0 | ok |
| tone-2701hz-12db | -24.0 | <-140 | <-140 | -120.6 | <-140 | 0 | ok |
| tone-2701hz-1db | -13.0 | <-140 | <-140 | -131.7 | <-140 | 0 | ok |
| tone-5301hz-12db | -24.0 | <-140 | <-140 | -120.5 | <-140 | 0 | ok |
| tone-5301hz-1db | -13.0 | <-140 | <-140 | -131.6 | <-140 | 0 | ok |
| tone-9102hz-12db | -24.0 | <-140 | <-140 | -120.6 | <-140 | 0 | ok |
| tone-9102hz-1db | -13.0 | <-140 | <-140 | -131.6 | <-140 | 0 | ok |

The three settings that modulate cannot pass this audit by construction, and their figures are recorded, not treated as defects:

- **RING, MIX 127, FREQ 64 HIGH.** The audit looks for the input tone and its harmonics; a ring modulator at full depth removes the tone and leaves the two sidebands, which the audit files under residual (+39 dBc) and, where a sideband lands on a fold frequency, aliasing (-27.5 dBc at 1.1 kHz, -43.2 dBc at 9.1 kHz; 4 checks flagged). DC is under -100 dBFS, no sample on the rails, idle is digital silence.
- **SHIFT UP, MIX 127, FREQ 64 HIGH, FDBK 127.** Every partial is moved, so the same applies (8 tone checks flagged). No sample on the rails. Idle fails: see below.
- **The manifest's dearest settings (SRR 127, BRR 127).** Sample-rate and bit reduction alias by design (up to +36 dBc read as aliasing; DC up to -40.8 dBFS from the coarse quantiser at 20.8 bits removed; 8 checks flagged). Idle is digital silence.

### After the input stops, in SHIFT

Found by the audit's idle row and measured separately: a 0.5 s, 440 Hz burst at 0.5 FS, then 12 s of silence, RMS of the left channel in 0.5 s windows starting 0.5, 2.5, 5.5 and 11.5 s after the burst (`dsp_host`, payload A, MIX 127, FREQ 64, RANGE HIGH unless noted).

| Setting | 0.5 s | 2.5 s | 5.5 s | 11.5 s |
| --- | --- | --- | --- | --- |
| RING | silence | silence | silence | silence |
| SHIFT UP, FDBK 0 | -77.0 dBFS | -77.0 | -77.0 | -77.0 |
| SHIFT UP, FDBK 64 | -83.5 | -83.5 | -83.5 | -83.5 |
| SHIFT UP, FDBK 127 | -76.9 | -77.0 | -76.9 | -77.0 |
| SHIFT UP, FDBK 127, FREQ 0 LOW | -74.1 | -77.6 | -78.6 | -79.5 |
| SHIFT UP, FDBK 127, FREQ 127 | -76.7 | -76.7 | -76.7 | -76.7 |
| SHIFT DOWN, FDBK 127 | -82.3 | -82.2 | -82.2 | -82.2 |
| SHIFT UP, FDBK 127, MIX 64 | -82.9 | -82.9 | -82.9 | -82.9 |
| dearest settings (BRR 127) | silence | silence | silence | silence |

In SHIFT, once signal has passed through, the output does not return to silence: a steady residue of about 1,100 to 2,200 LSB peak (24-bit) stays for as long as measured, with FDBK at 0 too, so it is not the feedback tail. A fresh instance on silence stays silent (`verify_dirtystate`). The merged upstream revision (`a6f41a1d`) rendered the same figures, so this is a property of the author's shifter and not of the port or of the optimisation. The cause was not investigated and the DSP was not changed; it is listed as a limitation and should go to the author. Not checked on hardware.

## A silent master track at BRR 127 (here)

Reported from a combined-image trial: with a fixture project that stores effect id 0x09 on all sixteen FX slots (a free id on stock, LOFI2 here), turning MASTER TRACK on made the main output silent. Reproduced on the LOFI2-only image under `ot_emu`, without Output Matrix; the stock image passes audio in the same run.

- The knob words the T8 FX2 instance receives (`--dsp-peek` at its r6 block; T7's are identical) are FREQ 47, MIX 0, FDBK 127, SRR 0, BRR 127, LPF 0, MODE UP: the fixture's stored bytes, not defaults.
- Clearing T8's FX2 id brings the audio back; clearing only its FX1 does not. Tracks 1-7 with the same knob words pass audio.
- Offline (`dsp_host`, payload A, a 220 Hz sine, those knob words): LOFI2's output is exactly zero for inputs up to 0.10 FS and returns at 0.115 FS. Stock LO-FI at BRR 127 does the same at the same inputs, with the same step once it passes (1,874,262 LSB against LOFI2's 1,871,726 with the shelf out).
- With T8's FX2 cleared, the master bus peaks at about 0.9 million LSB in that fixture, under the rounding threshold of 938,502 LSB (half a step of 2^20.84).

So the mix reaching the master track is quieter than half a quantiser step and rounds to silence, as it would through stock LO-FI. Not a defect; it is listed under limitations. Changing BRR by poking the live record under the emulator did not take effect, so the conclusion rests on the offline threshold, the match with stock and the measured level, not on a direct A/B in the emulator. Not checked on hardware.

## Elekloader path: the Modwerk base and USB loading (here)

Since the migration merged, a DSP effect reaches the unit as a runtime package loaded over USB into the Modwerk base. Run in a scratch copy of `main` with this folder at `sdk/octabam/modules/lofi2`, `lofi2` added to `dsp_packages.py`'s `FX` list and a scratch catalog pin; none of that is committed.

```sh
ELEKLOADER_DSP_ASM=.../dsp_asm python3 -B sdk/machines/octatrack/elekloader/dsp_packages.py --check src/engine/assets/dsp-packages.json
ELEKLOADER_DSP_ASM=.../dsp_asm python3 -B sdk/machines/octatrack/elekloader/dsp_packages.py --out dsp-packages.lofi2.json
python3 -B sdk/runtime/loader/build.py --dsp dsp-packages.lofi2.json:lofi2 --slots fx2 \
    --cycles 414 --cycles-kind modeled --state 132 --no-page --name LOFI2 -o lofi2.mwrm
```

| Step | Result |
| --- | --- |
| `dsp_packages.py --check` with LOFI2 added | the eight published packages stay identical |
| LOFI2's relocatable DSP package | builds: 1,352 words (the 516-word table first, then 836 of code), 4 relocations, init at 516, proc at 534, proofs at four bases; SHA-256 of the words `4090dfd37463d5e75baf17b8b8ccce19d3db59abc9a3d02a4d25a01cc80f29ee` |
| `build.py --dsp ... --no-page` | builds a 5,484-byte ABI 6 package: no ColdFire code, hooks or stock-code sites, DSP effect 9 (private, not committed) |
| The effect page recipe (chooser row and knob pages on the base) | not built: it reads the generated catalogue, which needs the catalog pin |
| Install on a base, emulator or unit | not run |

What the base's admission rule (`modwerk_machine_dsp_admit` in `sdk/machines/octatrack/elekloader/dsp.c`, constants in `build_core.py`) says about it, read from the source, not run:

- **Memory: fits.** 1,352 words against a per-core arena of about 5,194 words with every stock effect on demand, so on the base LOFI2 costs no stock reverb. State is 132 words (`$00-$83`), exactly the base's limit of 132. No buffer.
- **Cycles: on the line.** One instance must fit beside seven stock slots: 3,120 - 7 x 342 = 726 chip cycles, and an emulator figure (modeled or executed) is charged at 7/4, so the largest one the base admits is 414. Which figure a package declares decides it:

  | Figure declared | Charged | Result |
  | --- | --- | --- |
  | 414, modeled (the static count; TapeHead and Mini Verb declare theirs this way) | 725 | admitted, 1 cycle under the limit |
  | 406, executed, no trig split | 711 | admitted |
  | 429, executed, worst trig split (E-Verb declares its worst split) | 751 | refused, `RUNTIME_CYCLES` |

  The merged revision (654 static, 596 executed) was refused on every figure. A figure timed on hardware is charged as it stands; none exists. Which figure to declare is the owner's call.

## Screenshots (here)

`scripts/capture-module-ui.py` with the image above, `ot_emu`, MKII panel, empty scratch card, transport stopped. Five PNGs and `media/capture.json` (plan, image, emulator and PNG hashes). Each image was opened and checked: LOFI2 selected in FX2 SETUP with RANGE, MODE and AMPH; the main page at defaults; FREQ 64 / MIX 127; MODE turned to UP (the knob names itself UP); the main page in UP with slot 2 renamed FDBK and set to 60. They show the pages and labels, not audio or hardware.

## Upstream evidence (Bryan T, octabam; not this build)

Taken from the author's README and manifest at the pinned commit (kept under `upstream/`). Effect ID 0x1f, octabam's tree and placement, his own remix.

- Manifest `proof_note` (`Proof.HARDWARE`): "Bryan T's MKII, images 96-99 (Oct 2026, this tree): tracks 1 and 5, five instances at once; `_bt_oct` build 11 (12 Oct 2026, the 414-cycle loop): eight in SHIFT at once, four per core, UP/DOWN switched while playing".
- `_bt_oct` build 11, 12 Oct 2026, this revision's loop: all eight tracks ran SHIFT at once, four on each core, switching between UP and DOWN while playing, cleanly. RING on all eight is unrun. What FX1 held was not recorded.
- At 506 counted cycles (an intermediate build 10) four in SHIFT cut out on either core.
- Image 96, 10 Oct 2026 (his remix with RECORDER LOOP FIX and USB AUDIO): LPF right on track 1 (payload B), SHIFT on two tracks at once, MODE through RING / DOWN / UP without a fault.
- Image 97: AMPH bipolar, GAIN and the MODE duck ran on the unit.
- Image 98, 10 Oct 2026: his own SRR, BRR and LPF on track 1 and track 5: "sounding and working great", and the MODE change no longer clicks.
- Image 99, 10-11 Oct 2026 (the earlier 654-cycle source): the FREQ, MIX, GAIN/FDBK and AMPH glides with five instances at once; T1-T7 in RING played; three SHIFT UP instances on core 0 (T5-T7) played and a fourth (T8) cut the audio out with bursts of digital noise. The author withdrew his earlier note that four in SHIFT on core 1 had been run.
- Stock LO-FI's SRR rates measured on his unit, 10 Oct 2026: 8,018 Hz at 64 and 3,564 Hz at 127.
- A ten-character MODE label ("SHIFT DOWN") faulted his unit; the labels are five characters or fewer since.
- He states every optimisation step but the per-block glides and the carrier direction is bit-identical to the one before it; not checked here.
- His bit-identity render of the October port against his September source (`rig_render`, T1 on payload B and T5 on payload A) was not repeated here.

## Not tested

- Any hardware run of this build: MKI or MKII, audio, instance counts, chip timing.
- Parameter locks, LFO modulation on the unit, scenes and the crossfader.
- Part save/reload, project save/load, reboot persistence, several instances with different settings.
- FX1 placement, and LOFI2 beside any Modwerk module on hardware.
- `rig_render` on both cores, `verify_set` under the ColdFire port, `make check` as a whole.
- `stress_project.py` on a real Octatrack project and `pressure.py render`: the stress run above drives the same load straight into `dsp_host`.
- `npm run modules:generate`, `npm run module:verify` (native/browser comparison) and the published USB package: all three need the qualification record, which needs the hardware report first.
- On the Modwerk base: the effect page recipe, the published package manifest entry, and any install, pick, self-test or soak on a Modwerk base (emulator or unit).

## Packages (here)

- `scripts/build-module-packages.py`: `lofi2` added to the effect order after `everb`, with a descriptor guard for FX2 id 0x09 (DARK REV's descriptor as donor, the one E-Verb uses; the id's stock FX2 slot is NONE). Both guard hashes were recomputed from the tester's own OS 1.40C and equal E-Verb's recorded ones; only hashes are kept.
- `bash scripts/build-modules-isolated.sh . <new folder> <modwerk-source-tools image id>` (Docker, no network, no firmware): passed, "Compiled loadable DSP modules with four-origin relocation proofs".
- `npm run modules:import -- <folder>/packages --development`: imported. LOFI2's package in `src/engine/assets/dsp-packages.json`: 1,352 words, init 516, proc 534, words SHA-256 `4090dfd37463d5e75baf17b8b8ccce19d3db59abc9a3d02a4d25a01cc80f29ee`, the same words as the Elekloader-path build above.

## Repository checks (here)

- `npm run sdk:imports:check`: passes with `sdk/imports/lofi2-e8665fa.json`.
- `npm run licenses:generate`: passes with the `lofi2` licence component.
- `npm run perf:audit -- check`: no check failed (above).
- `npm run modules:generate`, `npm run modules:check` and `npm run check`: **fail** until `tests.qualification` exists: "lofi2.tests.qualification: publication requires worst-case cycles, exact memory and hardware test evidence". The cycle and memory parts are measured (above); the hardware report is missing, and it is not replaced by a placeholder.
- `npm run module:verify -- lofi2`: **not run**. It refuses a module the generated catalogue does not offer.
- `npm run module:doctor -- lofi2`: red on the lines that follow from the two above.
