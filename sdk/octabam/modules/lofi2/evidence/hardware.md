# LOFI2 0.1.0-experimental: hardware report

A functional report, as the tester gave it. It is reported evidence, not a measured stress qualification.

- **Unit:** Octatrack MKII.
- **Date:** 13 October 2026.
- **Tester:** npp1993 (the contributor of this port; LOFI2's author is Bryan T).
- **Image:** `OCTATRACK_LOFI2T03.bin`, a private native build of the submitted source (octabam `21f6de905df71c2d7e4faba6cc7b5c7f7fb53de7` with the Modwerk adaptations): LOFI2 on the FX2 chooser beside twelve stock effects, PLATE REV and SPRING REV given up, stock DSP code built in. MAIN OS SHA-256 `3d63406d3254e161b1fc52c9acfbfc14af6130b2c9314a554030e0ac060678e2`; card file SHA-256 `0446107ddea33ca5b6cb45af749dd0fd0a058d2e0ad1cc41c60dd8881bf80e99`. The image stays on the tester's computer.
- **Duration:** about 5 to 10 minutes.

## What was asked and what came back

| Check | Result |
| --- | --- |
| Select LOFI2 in FX2 SETUP; sound unchanged at the defaults; SETUP shows RNGE, MODE and AMPH, MODE's value under the knob | pass |
| RING, then DOWN and UP; no click or freeze when MODE changes | pass |
| SRR, BRR and LPF each act | pass |
| Several instances with different settings, a track in 1-4 and one in 5-8 | pass; five instances in SHIFT at once |
| A parameter lock on FREQ | works; the tester noticed the locked value stays after the locked step (see below) |
| Part reload restores the settings | pass |
| Power cycle restores the settings | pass |
| The faint residue in SHIFT after the input stops (about -77 dBFS in `dsp_host`) | "can't really hear a faint tone" |

Remarks from the same session and from an earlier combined private image (12 October source): the range label was too wide and MODE printed its value twice, both fixed before this image; "the low pass filter doesn't seem to do a ton" (LPF is a 12 dB shelf by design); "ring mode sounds like amp mod" (it is amplitude modulation by a bipolar carrier, a tremolo on RNGE LOW).

## The lock that stays after its step

The tester locked FREQ on a trigless (green) trig and heard the value hold past that step, then saw the same with stock FILTER. Checked under `ot_emu` on the tester's unmodified OS 1.40C and on this image, with one project: track 1 with trigs on steps 1 and 9 and a trigless lock on step 5, track 2 with a lock on a trig at step 5 and its next trig on step 9; locks on AMP VOL, an FX1 slot and an FX2 slot; the live track record dumped at every step for 19 steps.

On both images each locked value appears at step 5, holds through steps 6, 7 and 8, and returns to the stored value at step 9, the track's next trig. The lock timing is identical on the stock image and on the LOFI2 image (the records differ only in one page-2 byte that the firmware clamps to MODE's three values). So a lock holding until the next trig is the instrument's own sequencer behaviour, and LOFI2 follows it.

## The USB package on the beta base (15 October 2026)

The published runtime package, not a card image: `public/octatrack-modules/lofi2/0.1.0-experimental.mwrm`, SHA-256 `7ee9277f3510988366912a0b7ed4e7ca0b5523503b48844e94af7b7ff33fe976`, built from source at `c20b7756`. Same MKII, OS 1.40C, the flashed beta base `acf91e0a…`. Driven over USB by a coordinating session with `npm run device`; the panel and listening checks are the tester's. The only other module installed was APPLY SCENE.

| Check | Result |
| --- | --- |
| Trial without Keep (`try --seconds 3`) | the slot ran, then rolled back (Undo) |
| Install with Keep (`try --accept`) | accepted; the inventory lists LOFI2 at handle 9, module `d7bf66ce` |
| FX2 on T1 (core 1) and T5 (core 0), then FX1 on T1 and T5 | pass: in both choosers, defaults sound unchanged, SETUP shows RNGE, MODE and AMPH with MODE's value under the knob |
| RING, DOWN and UP, SRR, BRR, LPF | pass: RING FREQ and MIX audible, RNGE LOW a tremolo; DOWN and UP shift with FDBK, no click or freeze on MODE changes; SRR and BRR audible, LPF 0 darkens |
| Two instances on different cores (T1 and T5 FX2, different settings) | pass: independent |
| Two on one core (T1 and T2 FX2) | admitted, the other core-1 slots at NONE; clean audio, no crackle or freeze |
| A third on core 1 (T1 FX1) | refused, DSP FULL |
| Removal while a track runs it | refused twice, loader refusal 7 (in use) |
| Removal with every slot at NONE | accepted; LOFI2 left the inventory |
| Missing module | `npm run device -- missing` listed LOFI2; the reloaded project showed MODULE MISSING; after reinstalling, nothing missing and the project put LOFI2 back on T1 and T5 with their settings |
| Persistence | Part save, knob change, RELOAD: settings back. Project save, power cycle: module still installed, T1 and T5 ran LOFI2 with their settings |

Not run on this base: a worst-case timing pass (the flashed base has no development meters). The package's 637 cycles come from the timing on a development twin (TESTING.md, USB loading).

## Limits

- One unit, one short session, by ear. No measurement of chip load, no memory check, no recording.
- Five instances at once, not the eight the cycle and memory records price.
- Scenes and the crossfader were not confirmed. Project save and reload was not reported separately from the Part reload and the power cycle.
- FX2 only on the card image (LOFI2T03). FX1 was run with the USB package, above.
- LOFI2 beside other Modwerk modules: only APPLY SCENE, in the USB run.
