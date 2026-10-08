# POLY draft validation

Status: experimental source draft, **not hardware-qualified or in the catalog**.
Historical 0.2.0 tests on 7 October 2026 used a locally verified Octatrack 1.40C, the native
ColdFire/DSP port and the separate octemu/QEMU front-panel emulator. Firmware,
project/card images, raw memory dumps and compiled executables remain private.

## 0.2.2 one-machine/headroom candidate (8 October 2026)

The user reports POLY8T02 chromatic REC+PLAY makes sound with a flashing REC
light and moving playhead, but records no trigs, reboots as FLEX and clips
when summing voices. These are actual MKII failure observations, not a hardware
pass. The reboot marker-copy defect is reproduced; the recording failure is
not reproduced in either image's fresh-assignment native gate.

Current evidence: `evidence/recording.json` (0.2.2); previous image evidence
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
