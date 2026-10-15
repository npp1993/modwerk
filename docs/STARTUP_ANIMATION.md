# Modwerk Octatrack startup — 8 October 2026

## Docking for every member — 14 October 2026

New Octatrack card builds for every member play the docking startup, not only
beta testers'. It ends on the mark and MODWERK. The NEW / BETA labels are gone,
and so are the shockwave's solid outline and dotted echo (the `3.0.0-beta.2`
refinement below). The mark's flight plays the base's schedule 10/7 as fast and
has landed by 0.89 s instead of 1.27 s. The socket blink and the module's run keep
their lengths, so the module docks at 1.86 s instead of 2.26 s. The wave expands
more slowly, (dt / 55 ms)² px instead of (dt / 40 ms)². It bends the screen for
0.58 s instead of 0.42 s, and the complete MODWERK stands for about 1.2 s instead
of 0.9 s. The startup still lasts 3.5 seconds. The bending frames are the costly
ones (about 520k–565k executed instructions each, measured on the base): their
cost per frame is unchanged, but they now last 0.16 s longer.

![Host render of the docking startup's screen from the authored source](media/startup/docking-preview.gif)

The preview is a host build of `boot_anim.c` on the simulated clock
(`sdk/runtime/startup/preview.py`). It shows the LCD only, without the panel
lamps, and holds the last frame for 1.5 s. It is not a firmware capture.

A configuration can choose **Classic startup** on the configuration page to keep
the 2.8-second graphic-table startup. If a selection composes only without the
docking hooks, its build keeps the classic startup and the build panel says so.
Nothing that builds with the classic startup is refused for the docking one.
Beta membership still gates beta modules; it no longer selects the startup.
`/api/auth/build-access` ignores the former `betaStartup` flag from cached pages.

The art comes from `sdk/runtime/startup/public_art.py`. It reads the base's
`base.json` through `base_art.py` and leaves out the labels. The Elekloader base
builds its own startup, still marked NEW / BETA, from those two unchanged files.

### Release gate

The source, app and server changes are prepared; the release is not. Before this
startup reaches members, the owner completes these steps for the exact package.
Steps 1 to 4 and 6 were done on 14 October 2026 and step 5 in part; the owner released it with the hardware limits in step 5.

1. Done: `src/engine/assets/beta-startup.json` is rebuilt as `3.0.0`
   (10,948 bytes, SHA-256 `62dbceb8…`) in the pinned `modwerk-source-tools` container
   (GCC 16.2.0, binutils 2.47), with no firmware mounted. The same container reproduces
   the committed `3.0.0-beta.2` byte for byte, and the SDK provenance test passes.
2. Done: the native matrix (`scripts/verify-startup-beta-native.mjs`) passed for all
   ten selections, with GNU/browser link parity at both runtime bases, ROM-gate
   parity, rejection of changed hooks and of a repeated patch, and a firmware round
   trip for every image. [`beta-docking-native.json`](media/startup/beta-docking-native.json)
   is replaced.
3. Done: the emulator booted the core-only and standalone MIDI Scenes images on MKI
   and MKII (`scripts/verify-startup-beta.py`). Every run ended on the 792 authored
   pixels with none missing or extra, lit 44 (MKI) and 67 (MKII) lamps on one channel with
   levels 0 to 15, had them dark before the handover, and restored the stock screen,
   LED rows and colours. The two capture records and
   [the GIF](media/startup/beta-docking.gif), which now ends on the actual final frame,
   are replaced.
4. Done: retained evidence no longer compares shared code or unrelated assets
   (#592), so Tape Echo's evidence no longer pins the startup package.
5. Partly done on 14 October 2026: the exact core-only docking image (the one the
   emulator verified, MAIN SHA-256 `6f309847…`) was RAM-booted on the owner's MKII
   development unit, which plays it from RAM without flashing; the owner watched it
   and reported that it worked. Not run: the **Classic startup** build, an MKI, a
   flashed (not RAM-booted) install, and a power-cycle with a project loaded. The
   owner did not itemise the lamp colours or the handover to the normal screen.
6. Done: `npm run check -- --base origin/main` passes.

Checked in the preparing session: the host choreography test on MKI and MKII (one
LED channel, bounded levels, lamps dark at the end, colour restore, exact final
frame of 792 pixels), the session fallback and startup choice, configuration
persistence, the server's build access, and the TypeScript check. Not checked
there: the compiled package, native/browser parity, emulator boots and any
hardware. The first three have since been run (steps 1 to 3); one RAM boot on an MKII is the only hardware result.

## Beta docking edition — 12 October 2026

This beta edition stays in place until the docking edition above is released.
The capture records, native record and GIF linked below were replaced on 14 October
2026 by the docking edition's (`3.0.0`, 792 pixels, no labels); the results described
in this section are those of `3.0.0-beta.2`.

New Octatrack builds for beta testers and verified administrators include the
Elekloader migration's docking startup, ported independently of its new base.
The mark flies in, a module crosses the lamps and docks, and its wave reveals
MODWERK with **NEW / BETA**. It lasts 3.5 seconds. Ordinary members keep the existing
2.8-second startup. Existing firmware files need to be rebuilt to receive it.

Startup package `3.0.0-beta.2` removes the shockwave's solid circular outline and
dotted echo. The expanding distortion, text reveal and panel-lamp sweep retain
their original timing. A host-renderer comparison across 350 frames on both
models found only removed pixels during the outline phase; all other frames,
including the final artwork, remain byte-identical.

Beta eligibility is carried through validation, composition, alternative placement
checks and standalone MIDI Scenes. The server rechecks beta access immediately
before a beta build; revocation also changes the frontend build key. The build
panel labels the beta startup, and its source/configuration fingerprints distinguish
it in the device logger.

The port changes the startup loop and compositor frame-load sites and adds its
authored runtime object and persistent ROM cave gate. Both sites have SHA-256
guards; original frame-load code
comes from the verified local firmware. The drawing adapter preserves registers
and flags and stops drawing after startup. Both models restore the stock panel
colours. The same sample-memory reservation is used; the extra initialized runtime
state remains inside the existing runtime/staging bounds. The gate and its
initially zero active word occupy 80 bytes reserved before beta descriptor clones;
utility overflow sites stay intact.
Standalone MIDI Scenes uses the unused fill after its scene-mute helper. Early
compositor calls replay the stock instruction before the runtime is unpacked;
the appended loader area is reused by stock RAM and cannot hold this gate.

The original migration's MKII RAM-boot observation on 11 October applies to that
base, not to this port. Physical flashing, reboot and timing of this beta port
remain untested. The emulator exercised core-only and standalone MIDI Scenes on
both MKI and MKII. All four runs matched all 912 authored final pixels, lit the
expected 44/67 lamps on the correct channel with bounded levels, ended dark,
and handed over to the stock screen with identical LED levels, rows and colours.

The native matrix passed for core only, Repitch, Mini Verb, Tape Echo + Euclid,
Analog BD, Sidechain Compressor, USB Audio + Quantizer, standalone MIDI Scenes,
Airwindows Chorus and Poly8; the developer dynamic-loader Repitch path passed
as well. The authored startup package reproduced exactly with the macOS and
isolated Linux toolchains. GNU/browser startup links matched at both runtime bases, and the ROM
gate matched GNU placement. Every final image round-tripped through the original
firmware container without changing its tail or seed. Changed hooks and repeated
patching were rejected. The standalone live CC-cache table remained intact.

The current full repository check rejects the changed startup package while
Tape Echo retains evidence bound to the previous shared runtime. It reports a
stale `vector.json` builder-preservation record. The qualification gate and
existing owner exceptions have not been changed; release remains pending that
evidence review. SDK tests, lint and TypeScript checks passed independently.

![Outline-free beta docking animation, captured from MKII firmware](media/startup/beta-docking.gif)

[Native composition evidence](media/startup/beta-docking-native.json),
[core boot captures](media/startup/beta-docking-core.json) and
[standalone boot captures](media/startup/beta-docking-midi-scenes.json) contain
hashes and results only. Firmware and raw memory remain private.

Source, package regeneration and private-check commands are in the
[startup SDK](../sdk/runtime/startup/README.md#docking-edition).

## Public graphic-table edition

The boot animation now traces the Modwerk frame clockwise, locks eight tiles
in from the center around the ring, and brings the ninth tile in with a short
comet tail. It reveals original geometric MODWERK lettering alongside the
assembly. The stock monochrome treatment, 2.8-second duration and both models'
LED choreography remain in place. The extra choreography uses the same 843
records; it adds no firmware bytes.

![Actual MKII firmware LCD capture of the Modwerk startup animation](media/startup/modwerk-startup.gif)

The preview uses complete frames read from the real firmware LCD plane. Its
final 600 ms hold is for reviewing the image; firmware timing is unchanged.
[Capture provenance](media/startup/capture.json) records the exact local image,
emulator and asset hashes. [Verification records](media/startup/verification.json)
bind the current sources and graphic bytes to the checks below. No firmware or
raw memory is published.

## Scope

Two original graphic tables are replaced: 5,058 bytes of particle records and
440 bytes of title ink. Boot, LCD renderer, LED and module instructions remain
byte-identical. Table extents and particle count are unchanged, with no added
flash/RAM allocation or sample-memory reservation. The startup artwork is
installed in static compositions, standalone MIDI Scenes, and the developer
dynamic-loader composition path. Both writes are guarded and checked before
any mutation.

See [the source and native encoder](../sdk/runtime/startup/README.md) and
`scripts/verify-startup-animation-native.mjs` for reproduction instructions.

## Passed checks

- Ten complete images matched the independent Python encoder byte for byte:
  core only, Repitch, Mini Verb, Tape Echo + Euclid, Analog BD, Sidechain
  Compressor, USB Audio + Quantizer, standalone MIDI Scenes, dynamic-loader
  Mini Verb, and direct static core composition with stock FX2.
- Against private complete-image baselines captured before the change, all ten
  final images had exactly the same length and identical bytes outside the
  two graphic tables, including every appended runtime byte.
- Both encoders rejected changed graphic tables; the browser rejected a
  repeated patch. Native guard failures created no partial output. Original
  inputs remained unchanged. Static graphics spans were disjoint from all
  other module/platform/logger writes in the tested profiles.
- All ten final images round-tripped through full firmware packaging with
  the owner's original local 1.40C container.
  Decoded MAIN bytes matched exactly; opaque tail and seed were preserved and
  the original firmware input remained unchanged.
- The standard emulator ran the full boot on MKI (core-only composition) and
  MKII (standalone MIDI Scenes) and reached normal playback after the animation.
  Complete-frame capture then recorded 70 MKI and 69 MKII frames. Both final
  LCD frames exactly matched all authored pixels, with identical PNG hashes.
- Twenty focused engine tests passed, including artwork extent/orientation,
  final silhouette, bounded delays, clockwise tile order and the late ninth
  tile/echo timing.
  On the focused PR checkout based on current `main`, all 1,191 repository
  tests in 180 files passed. ESLint, the full TypeScript check, SDK checks,
  generated-record checks and the production Vite bundle passed using
  Node 24.21.0 (`npm run check -- --base origin/main`).

## Limits

Physical startup/reboot and chip wall-clock timing remain untested. No loaded
project, Part save/reload, project save/load or restart retaining only card and
battery-backed RAM was exercised here. A boot to playback without a loaded
project does not establish any of those paths. The byte comparisons show that
this patch leaves module/runtime bytes intact; they do not upgrade earlier
stateful-module qualification or physical reports.

No hardware flashing or module qualification-status change was performed.

## Base edition: docking (11 October 2026)

The Elekloader base starts with its own animation, so beta testers see at once that
the new base is running. The mark's ninth dot is a module arriving, which is what
this base does. First the mark flies in: every pixel of the frame and the tiles comes
from far beyond the screen and lands, as in the stock logo's flight, while the lamps stay
dark. The empty corner, the socket, blinks, and a light far off at trig 1 answers. The module
runs along the trig row, turns up through the keys under the screen and docks with a
shudder of the screen's rows. Its wave bends the screen as it passes (a lens: up to
3 px outwards within 7 px of the ring, without an outline since 15 October 2026, as on
card builds), reveals MODWERK, **NEW** and **BETA** (beta testers only: card builds leave
them out) and rolls on across the panel. It takes 3.5 s, 0.7 s longer than
stock. The base draws its own compact art from `base.json`, with room between the
elements: the mark at 29 px (5 px tiles), MODWERK at 11 px tall, and NEW and BETA
in the panel's small 7 px type.

![MKII LCD capture of the base startup, from the real base image in the emulator](media/startup/base-startup.gif)

Screen and lamps are one plane, so the module and the wave cross the screen's edge
without a break; the lamps show nothing else, so the module's run and the wave stand
out. The lamps are white on an MKII, at the panel's LED intensity, and
red on an MKI, which has fixed colours. Afterwards the MKII gets its stock colours
back: the startup repeats the firmware's own pre-logo colour call (`0x4003f430` with
the lamp lists only), and the firmware's own post-logo call follows as usual.

How it is built: `build_core.py` puts a jump on the first instruction of the stock
logo loop (0x400559c6) to `boot_anim.s`, which calls the C startup and continues with
the stock code after the loop (0x40055b7e). That code resets every LED itself.
`boot_anim.c` keeps the stock loop's own means: the free-running DTIM3 count for
time, the stock compositor and LED routines, and the frame through the core's
`ev_draw` hook. The art comes from `artwork.json` and `base.json` through
`sdk/runtime/startup/base_art.py`. Lamp positions come from the stock lamp table at
run time. The LCD's place on the MKII panel was measured against the panel drawing;
on the MKI it is an estimate.

[Verification record](media/startup/base-verification.json).
`scripts/verify-startup-base.py` boots the real base image (built with
`build_core.py`, checked with `check_flash_safety.py`) and the stock image in the
emulator with the boot logo on:

| Check | MKI | MKII |
| --- | --- | --- |
| Last startup frame vs. authored pixels (mark, wordmark, NEW, version) | 887 of 887, 0 missing, 0 extra | 887 of 887, 0 missing, 0 extra |
| LEDs: one channel, levels 0-15, dark before the stock code takes over | yes; all 44 lamps take part | yes; all 67 lamps take part, white |
| Hand-over; LED rows, levels and colours afterwards as stock | yes, identical | yes, identical |

The checker rejects the public image. A host test (`test_boot_anim.c`, run by
`test_recipe.py` in CI) plays the startup on a simulated clock as an MKII and an MKI.
It checks the exact final frame, writes only inside the frame, one LED channel, each
beat on the lamps, all dark at the end, and the white and restore calls on an MKII
only.

Cost per frame, as executed instructions in the emulator (MKII, counted between
hits of the frame's draw entry, against the stock loop's head): the startup runs a
median of 56k instructions per frame (90th percentile 93k), the stock logo loop 95k
(90th percentile 299k, max 331k). The frames in which the wave bends the screen, about
400 ms, run 520k-565k (a square root and two divisions per pixel in the band), and the
setup frame 664k: roughly twice the stock loop's worst, a few milliseconds of CPU.
These are instruction counts, not cycles or hardware timing; divisions cost more
cycles than most instructions.

On hardware, 11 October 2026: the owner's MKII RAM-booted a base with this startup
(`de124ebd8a069763…`, built from `b4e0584f` with `--dev --dsp-loader`, 1,305,168 bytes of
MAIN, under the gate's 1,310,720), came back to the normal screen with its project
loaded, and the owner watched the startup and reports that everything worked. That is
the owner's observation of one boot; no frame rate or brightness was measured. An MKI
has not run it, and its LCD position is still an estimate. The browser builder does not compose the base, so only `build_core.py`
has this startup.

## Firmware name before the animation

Updates now use **ELEKLOADER** in the fixed ten-byte ELEK name field, including
standalone MIDI Scenes. The original panel boot font uses uppercase letter
codes; lowercase codes select symbols, patterns and filled blocks. The first
follow-up used `Elekloader`: its header was correct, but its glyphs were wrong.
The owner reported the malformed text on their device. This correction keeps
the same ten cells, with no extra firmware space or runtime changes.

The headless emulator ran the **original MKII panel character-drawing routine**
for the previous `OCTAMOD79 `, the broken `Elekloader`, and corrected
`ELEKLOADER`. Each of the 30 original calls returned. The captures below decode
the routine's actual LCD controller command/data writes, with all 80 columns
per name matched against the original local panel font. They are crops of the
ten observed name cells, enlarged at integer scale 8; no text is reconstructed.

Broken lowercase name:

![Actual original MKII panel routine output for Elekloader](media/startup/boot-name-lowercase.png)

Corrected uppercase name:

![Actual original MKII panel routine output for ELEKLOADER](media/startup/boot-name-fixed.png)

[Renderer and packaging verification](media/startup/boot-name-renderer-verification.json)
records the exact MAIN, emulator, panel and capture hashes. Reproduce on a host
where the reviewed local emulator runs:

```sh
python3 scripts/verify-boot-name-renderer.py \
  --image /private/path/decoded-MAIN.os \
  --emulator /private/path/ot_emu \
  --output /private/path/new-capture-directory
```

The checker uses a new empty disposable FAT16 card. It runs the unchanged
embedded panel instructions through the headless emulator's function-call
path, maps the original local font at the panel's own absolute address, seeds
the resident loader's page/cell cursor, and records the GPIO/LCD writes.
Firmware, font tables, card and raw logs remain private. The new checker needs
no Unicorn installation and does not change emulator or firmware instructions.

This is a **panel-renderer function capture**, not a complete resident-loader
boot. Standard Octemu/headless MAIN boot skips the resident loader, and Octemu
currently ignores its character protocol. MKI panel firmware/font is absent
from MAIN and was not emulated; the new physical rendering is still untested.
These limits do not negate the reproduced MKII lowercase glyph failure.

Native Python ELUP output matches browser packaging byte for byte for FM Synth,
standalone MIDI Scenes and dynamic-loader Mini Verb. Every MAIN hash still
matches its previously tested startup image; original inputs, opaque tail and
seed remain intact. Against the saved visitor baseline, the complete ELEK
container differs only in the ten name bytes. OS/runtime/DSP instructions,
artwork, extents and memory reservations remain unchanged.

Session regression tests cover validation/build reports and all ten header
bytes for Repitch, MIDI Scenes and USB Audio + Quantizer with both stock-FX2
choices. A separate letter-range assertion rejects accidental lowercase
branding. Individual module versions remain separate. The earlier
[header-only proof](media/startup/boot-name-verification.json) retains its
original names and hashes as historical packaging evidence, not glyph evidence.
