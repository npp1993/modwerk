# POLY draft validation

Status: experimental source draft, **not hardware-qualified or in the catalog**.
Historical 0.2.0 tests on 7 October 2026 used a locally verified Octatrack 1.40C, the native
ColdFire/DSP port and the separate octemu/QEMU front-panel emulator. Firmware,
project/card images, raw memory dumps and compiled executables remain private.


## 0.2.5 POLY8T06 consistency and performance (8 October 2026)

The user described T05 as “works in theory.” This is not a per-test hardware
qualification. T06 remains private, pending physical recording, reboot and
worst-case CPU deadlines. `module:doctor -- poly-machine` cannot discover a
module kept under `sdk/drafts`; the public catalog and downloads are unchanged.
Private version-matched release notes remain in `release-notes.json` until a
first catalog release; that release must migrate them into the community changelog.

T05's actual panel flow reproduced two defects: SRC SETUP re-selection reset
LOOP PIPO to OFF, and LEFT from the FLEX sample pool left the chooser cursor/title
on FLEX while highlighting the assigned POLY. T06 retains AUTO and PIPO across
re-selection (the entire 6,322-byte Part stays unchanged), restores the POLY
cursor/title on LEFT, and returns to FLEX slots on RIGHT. Sample confirmation,
browse/cancel, changing to ordinary FLEX, and assigning POLY again all pass;
a fresh assignment still defaults to LOOP OFF. See the actual native LCD
captures and their provenance under `media/t06`.

The ColdFire changes use signed high-half word loads for interpolation, process
held stereo pairs with one loop branch, and skip a redundant peak scan at unity
limiter gain. Eight voices with fixed 1/8 gain and envelopes at or below unity
fit the Q25 sum; defensive output saturation and limiter recovery remain.
Both original stock DSP uploads are byte-identical. There is no DSP loader,
per-note DSP chain, new timing source or allocator change.

Twelve native A/B cases each measure 1,000 blocks of 16 samples after warm-up.
Counts include the whole ColdFire system and are averages, not chip cycles,
CPU utilization or a maximum interrupt-latency measurement. All twelve compare
16,000 frames of all eight captured output channels identically; the native
host needs at most a one-sample stream alignment (listed in the evidence).
The previous SDK base differs only in the unselected PLAY MODES module.

| Workload | T05 instructions/block | T06 | Reduction |
|---|---:|---:|---:|
| Idle | 23,629.985 | 23,629.985 | 0% |
| One held root | 25,682.827 | 25,682.827 | 0% |
| Eight held notes | 39,851.352 | 38,218.173 | 4.10% |
| Eight notes plus seven FLEX tracks | 51,803.551 | 50,176.347 | 3.14% |
| Eight notes at admission cost 40 plus seven FLEX tracks | 60,608.979 | 58,606.766 | 3.30% |
| Eight POLY + seven FLEX, 24 LFOs including POLY PTCH | 53,925.871 | 51,873.998 | 3.81% |

The highest measured case average is 58,606.766 instructions/block, a 3.30%
reduction. Pitch pressure at CC16=127 retires to two voices as intended; it
uses 45,804.979 instructions/block, 1.31% less. This is a bounded stress matrix,
not an exhaustive timing bound. Stock FILTER/DELAY are selected on all tracks;
all stock-FX combinations and hardware deadlines still need qualification.
Startup-dominated DSP stopwatch summaries are deliberately excluded.

Eight coherent +32767 and -32768 PCM inputs stay within the signed Q25 mix
range, with identical T05/T06 sums. The stock fetch path places the positive
sum a fraction of one 16-bit LSB below the ideal bound; the gate allows at most
one LSB and checks both limits. This does not certify downstream physical clipping.

Fresh assignment records a four-note chord. At HOLD/REL MAX, 128 physical-panel
UART presses (10 ms down/up in emulated time) keep at most eight active voices
and complete 7,077 further DSP-driven frames. Both refusal-modal paths
leave the Part unchanged; NO and the native timeout dismiss the modal.
Battery-RAM-only restart preserves both markers and LOOP OFF, plays POLY and
ordinary FLEX, records three advancing steps, and renders sparse selector 31
without changing adjacent cache bytes. These are native-port results only.
The completed SAVE checkpoint writes both 32 KiB logs, with CRCs, source/version
identity, recording and engine-stage counters accepted by the production parser.
Its directed backoff test advances the UI tick counter by 2,100; it does not
claim a measured real-time 30-second checkpoint deadline.

CF BIN and MIDI SYX independently round-trip to the exact tested MAIN, preserving
stock header/seed. The full repository check passes 191 files / 1,286 tests,
SDK/catalog/licences, lint, typecheck and build with one Vitest worker and all
original assertions/timeouts. The remaining documentation/provenance changes
receive the lightweight checks. Firmware, audio, card images and raw logs stay
private. Exact fingerprints are in `evidence/build.json`, `diagnostic-t06.json`
and `performance-t06.json`; the original T05 evidence is retained.

## 0.2.3 POLY8T04 diagnostic candidate (8 October 2026)

T04 includes core logger 0.2.0 without shared logger/build changes. The private
`build-diagnostic.py` composes it with the native POLY runtime, reserves sixteen
extra pages and excludes the retained 8 KiB from the initialized image/stage.
Seven logger hooks are guarded against original stock and against POLY overlap.
Audio instrumentation only increments fixed RAM counters; five snapshots at
most once per sixty stock UI ticks append to the existing bounded ring.

Scratch storage covers all 32 physical selectors, while admission remains eight
active voices. The native gate relocates a sounding extension to selector 31,
hears it and verifies adjacent tuning-cache bytes are unchanged. This corrects
a bounds mismatch defensively; it is not the confirmed physical-stall cause.
The single-machine modal automatically closes after 120 stock UI ticks; both
native assignment menus refuse before changing the target Part.

The exact final MAIN OS is `792dde58d775fc7dcb8de7bd00c9e9fdd1e47fe909ef8d21dae898bea409a549`.
Warm battery-RAM boot retains both markers, native FLEX backing and LOOP OFF.
POLY/FLEX key audio captures each contain 8,820 frames, peaks 361/3,042;
REC+PLAY records notes 72/76/79 on advancing steps 2/4/6. Sparse-selector audio
peaks 712. Fresh assignment at HOLD/REL MAX records a four-note chord and
128 rapid presses retain at most eight voices with 7,072 further DSP-driven
frames. These are native-port results, not physical-device success.

ASan/UBSan allocator/recorder tests and unchanged core logger host/controller/
file-adapter tests pass. CF/MIDI container round trips recover the exact MAIN,
with original header/seed preserved. Detailed fingerprints and checkpoint scope
are in `evidence/diagnostic-t04.json`; collection steps are in DIAGNOSTICS.md.
The SAVE checkpoint gate waits for actual completion/readback, then the strict
site parser accepts both 32 KiB files with valid CRCs and exact configuration/
source identity. The newer slot includes recent successful recording counters.
The stock UI counter is advanced by 2,100 ticks for this directed backoff probe;
no real-time thirty-second persistence deadline is claimed. The original shorter
probe stopped while SAVING PROJECT was still visible and only captured the
earlier checkpoint; it was not accepted as evidence of the recent log tail.

The complete current-main `npm run check -- --base origin/main` passes with
Vitest limited to one worker: 189 files / 1,275 tests, SDK/catalog/licences,
lint, typecheck and production build. The private Node preload only adds the
standard `--maxWorkers=1` CLI option to the Vitest child; every suite, assertion
and original timeout remains enabled. A direct one-worker test run also passes.
Earlier default parallel runs hit existing timeout failures under machine
contention; no timeout or unrelated application code was changed.

## POLY8T03 hardware regression (8 October 2026)

The owner reports transport stuck at step 1 and no audio on any channel,
including sample preview. Returning to stock 1.40C restores operation in the
same project. This blocks further hardware testing of T03. The physical cause
remains open. T04 below is a new diagnostic candidate; no fixed hardware result is claimed.

The original battery-only restart gate checks Part identity and frame progress,
not playback or sound. The additional `native-warm-audio-gate.py` exercises
POLY and ordinary FLEX chromatic sound, REC+PLAY and recording on multiple
advancing steps after restoring the same private
battery RAM. It requires every boot/run slice to finish emulated time before
sending another key. An earlier diagnostic sent keys after a wall-limited
partial boot and never entered chromatic mode; its silent result is invalid.
The new gate asserts the mode and checks signal above idle output residue.
The optional `--preview` probe opens native FLEX slots and presses FUNC+YES,
but did not confirm the expected 440 Hz signal in either stock or T03. That
preview test remains unqualified; small nonzero output alone is not a pass.

Native frame interrupts come from the DSP bank-word handshake by default,
not the optional frame timer. Emulator timing, IRQ scheduling and generated
fixtures still cannot certify the physical device or the owner's project.
The completed strict gate on the exact shipped T03 image produces 8,820
PCM frames per key-audio capture (POLY peak 361, ordinary FLEX peak 3,042)
and records notes 72/76/79 on steps 2/4/6. Its metadata and private log hashes
are in `evidence/hardware-regression-t03.json`. Native build/runtime inputs are
unchanged from the shipped image; no replacement firmware was compiled.
The exact shipped T03 MAIN OS hash is used; these are test-only changes with
no module behavior/version change. The original build remains private. The rebased test/documentation update
passes `npm run check -- --base origin/main`: 188 test files / 1,266 tests,
SDK/catalog/licences/lint/typecheck/build. The initial run under emulator load
hit the existing five-second module-doctor timeout; the isolated full rerun
passes without changing the timeout. `verify-source.py` also passes, and all
shipped module runtime/build input hashes are unchanged.

## 0.2.2 one-machine/headroom candidate (8 October 2026)

The user reports POLY8T02 chromatic REC+PLAY makes sound with a flashing REC
light and moving playhead, but records no trigs, reboots as FLEX and clips
when summing voices. These are actual MKII failure observations, not a hardware
pass. The reboot marker-copy defect is reproduced; the recording failure is
not reproduced in either image's fresh-assignment native gate.

Historical evidence: `evidence/recording.json` (0.2.2); previous image evidence
is retained as `evidence/recording-0.2.1.json`. The native gate now starts from
unsigned FLEX and uses actual panel SRC SETUP assignment, checks both marker
copies and LOOP OFF, then records with REC+PLAY. The modal uses the native
NO acknowledgement. `native-limit-gate.py` checks both SRC SETUP and the machine
chooser without altering the target Part. `native-warm-gate.py` restores battery
RAM before boot, runs the DSP with 1 GiB shared memory, and never requests an
explicit project load. It requires the private persistence-audit emulator's
full SRAM mapping and `OT_PERSIST_SRAM_IN`; this is still emulator evidence.

The full-scale DC gate measures both signs, one and eight active heads, and
uses the exact built image. `verify-gain.py` checks eight heads and the raw
Q25 sum before downstream DSP: +33,546,240 and -33,554,432 fit the
[-33,554,432, 33,554,431] range. The single-voice output falls by a factor of
eight versus 0.2.1. No physical clipping/deadline result is claimed.

## Historical 0.2.1 recording/stability candidate (8 October 2026)

The user reported MKII unresponsiveness while rapidly pressing panel trigs, with
HOLD/REL INF. This candidate reduces the shared limit to eight active heads
and enforces a conservative pitch-weighted fetch budget. Release tails yield
before held notes. Emulator results do not certify hardware deadlines.

- Current-main SDK native build after rebase: passes 51 guarded non-overlapping
  edits. Four stock replay holes stay private.
- ASan/UBSan allocator: eight-head limit, 10,000 cross-track steals, released
  tail preference, retuning work limit, independent release and machine cleanup.
- ASan/UBSan recorder: all 232 supported chord shapes round-trip; native context
  and step routing, bounds, trigless behavior, recording off and SAMPLE retention.
- Native sequencer: two four-note captures play independently at offsets
  0/9/10/11, with eight heads active and the track tuning at unity.
  11,130,303 ColdFire instructions in 250 measured blocks = 44,521/block;
  instruction counts are not physical cycles. Full project loading completes.
- Native new assignment: LOOP OFF in both Part copies. Setting LOOP ON then
  confirming the sample browser retains ON in both copies.
- Native MKII panel UART input (pre-signed fixture, not fresh assignment): REC+PLAY captures notes 72/73/74/75 in step 3
  (root 72, shape 67). All held owners clear after release/STOP.
- 128 real panel presses at 10 ms down / 10 ms up, HOLD/REL 127 and LOOP OFF:
  7,075 additional frame interrupts complete; at most eight active heads.
  No illegal/fault/stalled run reply. This is emulated time, not physical timing.
- Native PROJECT > SAVE > YES writes 6,932 sectors to the disposable card with
  zero write errors. A fresh emulator process explicitly loads that saved card,
  runs 1,300 blocks and reproduces all four pitches at offsets -12/-11/-10/-9.
  This is a project-load test, not a battery-only reboot test. Stored Part PTCH stays 64 and track tuning stays at unity. No sidecar used.
- Fresh native MIDI regression completes 2,400 blocks: notes 0/127/71/72/84/96/
  97/126, velocity-zero off, finite envelope reclamation, three-note tuning
  and PTCH-lock preservation all pass.
- Final C regeneration and native rebuild are byte-identical to the tested
  image. Final rebase to main 8304186 changes only SDK credit prose, leaving
  native build inputs unchanged. Repository check passes 179 files/1,188 tests,
  lint (existing warnings), typecheck, production build and SDK/catalog/licences.
- Independent CF ELUP/ELEK decoding/checksums and MIDI extraction recover the
  exact same tested MAIN OS. Private wrapper POLY8T02 retains internal code
  0178 and the original ELUP seed. No firmware is committed or uploaded.
  Current metadata is in `evidence/recording.json`; older pool/panel/pitch
  reports explicitly identify their historical 0.2.0 version.

## Historical 0.2.0 results

- Native guarded build: passes, with 50 non-overlapping stock edits. Authored
  C is compiled for MCF5475 and linked with the assembly; four replay holes are
  populated only from the locally guarded original OS.
- Pitch helper: 768 combinations, all MIDI notes at six track-tuning values.
  Monotonic including saturation, zero-rate preserved, maximum error 0.024667
  cents, maximum 61 ColdFire instructions and 12 bytes of helper stack.
- Bounded allocator: AddressSanitizer/UndefinedBehaviorSanitizer host test
  passes 32 voices on one track, cross-track allocation, 10,000 repeated steals,
  stealing the oldest primary, independent release ownership and stale-machine
  extension cleanup. Fixed storage only; no allocation calls.
- Native 32-voice pool: one track has one active primary plus 31 extensions;
  eight tracks have eight primaries plus 24 extensions. Both produce audio.
  On the 33rd note, then a note on another track, the pool remains at 32.
  A later release of a stolen note does not stop its replacement.
- Full-range MIDI: notes 0, 127, 71, 72, 84, 96, 97 and 126; velocity-zero note
  off; C–E–G chord; CC16 tuning of all three voices. Held owners clear,
  independent finite releases finish, and note input never writes the PTCH lock.
- Native UI: selecting POLY opens FLEX slots directly; loading SINE440.WAV,
  confirming the slot and leaving the browser reaches SRC/POLY; chromatic
  presses create three distinct pitches without moving PTCH; turning PTCH
  transposes them together. Current real LCD captures are in `media/`.
- Earlier UI pass verified printed octave endpoints -6/+3 and TSTR OFF in
  SRC SETUP. Their control logic is unchanged by the allocator work. This is
  distinct from the current flow capture; do not treat old pool-choice screenshots
  as current UI. Double-tap TRACK reopening is not qualified by the current walk.

## Quick paraphony comparison

Same source-fetch/resampling and per-track FX path, 32 held voices across eight
tracks, four notes per track (72, 76, 79, 84), generated 440 Hz FLEX loop.
Warm up for 1,200 audio blocks and measure the following 1,200 blocks; each
block is 16 samples. ATK 0, HOLD INF, REL 20, AMP VOL 64. Both runs verify
8 primary plus 24 extension heads active and render audio.

| Envelope arrangement | ColdFire instructions / 16 samples |
| --- | ---: |
| Separate envelope per voice | 79,800 |
| One shared AMP per track | 76,787 |

Shared AMP saves **3.78%** of the measured total in this held-note case.
The user selected polyphony; the shipped draft retains independent envelopes.
These variants used the earlier fixed allocation only to isolate AMP cost.
The current shared-pool implementation is tested separately. This quick test
is not a comparison of moving attacks/releases or physical CPU percentages.

The native CLI resets its instruction counter after the last timed action but
prints a denominator covering the whole run. `benchmark-result.py --window 1200`
uses the actual steady window, not that misleading printed per-frame figure.
Host wall time and emulator “real time” ratios are not hardware evidence.

## Reproduction

The native SDK must be available separately, with the developer's own verified
stock image and reviewed local toolchain. Copy this draft into a private
`modules/poly-machine` staging directory and select it from a native remix.
Regenerate the authored C assembly into a fresh output file:

```sh
python3 modules/poly-machine/prepare-registration.py --output /private/tmp/registration.s
```

Copy that generated file into the private module directory, then use the
repository's native build procedure (`REMIX=poly-machine`, `XBUS=1`, `SPEC=1`).
Use a one- or two-digit BUILD tag. No stock bytes are needed to regenerate the
C/assembly; the guarded image is required only for the actual native build.

Firmware-free checks from this draft directory:

```sh
python3 verify-source.py
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined recording-test.c -o /private/tmp/poly-recording-test
/private/tmp/poly-recording-test
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined pool-test.c -o /private/tmp/poly-pool-test
/private/tmp/poly-pool-test
```

`native-panel-gate.py WORK` checks panel recording and rapid presses against a
private `keys.img` fixture with HOLD/REL 127, LOOP OFF and no existing trigs.
It requires the Linux native emulator and symbol map in WORK and runs from the
native SDK directory. It explicitly mounts the card, dismisses the date prompt
and asserts the signed POLY Part and chromatic mode before issuing notes.

`verify-recording.py WORK` checks the private cold-reload dumps used above;
those are taken at block 1,000 of a 1,300-block native run after the stock
PROJECT SAVE flow. `native-fixture.py` stages generated sample/project fixtures and command lists
for the native emulator. `verify-midi.py PRIVATE_OUTPUT_DIRECTORY` verifies
its `final-*` dumps. `pitch-probe.cpp` executes the linked helper using the SDK
native port; pass image, runtime blob, runtime base and helper symbol address.
The source-only checks do not substitute for native execution.

## Remaining qualification

- Physical MKI/MKII, audio deadlines and long stress sessions: **not tested**.
  Emulator instruction counts cannot certify crash-free operation. An earlier
  extreme-pitch workload only delivered 12 active voices; it did not establish
  a 32-high-note limit. High-ratio raw fetching remains the major CPU risk.
- A STATIC prototype lost quieter chord components as streaming positions
  diverged. STATIC is therefore excluded; FLEX is the only current source.
- Reverse/slices, parameter locks/LFOs/scenes, mixed machines, sample replacement
  during notes, transport/Part/project changes, recorders and broader save/reload combinations:
  require broader end-to-end stress coverage. Do not infer these from allocator
  unit tests.
- Panel recording is bounded to four notes spanning eleven semitones. Recorded
  key-up duration and extended-range MIDI recording remain incomplete.
- Browser/website composition, public downloadable firmware and public catalog
  qualification are intentionally pending. `module:doctor poly-machine` does
  not discover modules under `sdk/drafts`; it cannot certify this unpublished
  draft. Repository checks and exact outcomes are recorded in the PR.

## Evidence integrity

JSON reports include source/image fingerprints where relevant. Images are
actual monochrome 128×64 emulator LCD captures enlarged by nearest-neighbour
scaling. No invented screen or physical recording is used. Historical POLY95
claims in `upstream/` are not claims about this implementation.

## T04 physical log capture and T05 isolation candidate

The MKII owner reports that loading POLY and pressing PLAY still sticks the sequencer on T04. Both supplied log checkpoints parse with valid v2 completion CRCs and exact T04 source/configuration headers. The saved PLAY-state snapshot has no modal, no REC and zero render/fetch counters; UI ticks and later jobs continue. No error/fault or dropped record is stored. The second logger boot recovers earlier records, but its saved tail ends at startup; no claim is made about power-cycle retention or the unsaved failure tail. See [T04 hardware evidence](evidence/hardware-regression-t04.json).

T04 and earlier native test builds inherited the SDK's automatic DSP DYNLOAD STOCK pair. The automatic selection originated in upstream commit [`d677b6d`](https://github.com/repeat98/octamad/commit/d677b6d6a6f7228f77564f06a57e850213025e70), authored and committed as Claude on 30 September 2026, and was imported into Modwerk's initial commit. This path was not called out in the private test metadata. T05's pinned private `remix.py` sets `static_stock=True`, the diagnostic recipe also sets `OCTABAM_STATIC_STOCK=1`, and the build asserts both stock DSP upload spans remain identical and no dynamic-stock module is selected. Shared SDK/platform source is unchanged. Removing this dependency is a hardware isolation candidate, not a demonstrated physical fix. Modwerk main explicitly defaults `DSP_LOADER=false` since [`e43a0f8`](https://github.com/repeat98/modwerk/commit/e43a0f8ced716abcfd46421279d6c8a99fbab38e); the deployed Octatrack worker was also inspected and defaults its loader option to false. The private recipe failed to carry this setting forward.

The current diagnostic gates use `t05-symbols.txt` and `t05-sram.bin` in the private work directory. `build-diagnostic.py` writes version/source-specific proof of original DSP payloads beside its report. T05 physical transport, sample audition, chromatic recording, rapid HOLD/REL MAX presses and reboot results are pending. The old native sample-preview probe remains unqualified because it failed to confirm its generated tone under stock as well.
