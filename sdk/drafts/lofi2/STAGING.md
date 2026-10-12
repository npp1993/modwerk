# LOFI2 staging status

This is an unlisted `0.1.0-experimental` import of Bryan T's LOFI2, not a
downloadable release. It is kept in `sdk/drafts/` rather than
`sdk/octabam/modules/` because the module rules refuse a module folder there
without a qualification record (worst-case cycles, exact memory and hardware
evidence), and this build has no hardware evidence. The same convention holds
LO-FI AMF Fix.

The files are laid out exactly as the module folder will be. `manifest.py`,
`verify_lofi2.py`, README.md and TESTING.md name `modules/lofi2/...`: to build
or verify it, copy or link this folder to `sdk/octabam/modules/lofi2` in a
scratch copy of the SDK, as TESTING.md describes. Nothing in it has to change
when it is promoted.

The source remains attributed to Bryan T (bryantysinger), under octabam's MIT
licence (Sam Banks); the full text is in `LICENSE` and `upstream/LICENSE`. The
licence component is not in the active SDK inventory
(`sdk/octabam/licenses/manifest.json`) while the module is outside the release
SDK.

Before promotion, follow `docs/ADD_A_MODULE.md`:

1. The owner's review of the source pin and the cost. The pin is the head
   of octabam pull request 704 (`e8665fae`), unmerged on 12 October 2026:
   re-pin to the merge commit once it lands, and re-check the files if the
   author pushed again. SHIFT executes 428 instructions/sample at worst,
   dearer than every stock effect (DJ EQ 331). On the Modwerk base it is
   admitted as 414 modeled and refused as 429 executed: the owner picks the
   figure, or a hardware-timed one replaces it.
2. Hardware evidence for this build on effect ID `0x09`: several instances on
   both cores, both MODE families, parameter locks, Part/project reload and a
   reboot.
3. `evidence/performance.json` (the stress run is missing) and `fx:audit`.
4. Move the folder to `sdk/octabam/modules/lofi2`, update `root` in
   `sdk/imports/lofi2-e8665fa.json`, add the `lofi2` licence component
   (source `upstream/LICENSE`) and run `npm run licenses:generate`.
5. For USB loading: `lofi2` in `dsp_packages.py`'s `FX` list and
   `src/engine/assets/dsp-packages.json`, an entry in
   `src/engine/assets/octatrack-module-packages.json` (fx2, state 132, the
   cycle figure and its kind), `npm run octatrack:module-packages`, and an
   install, pick and soak on a base.
6. Catalog pin, compiled packages, `npm run module:verify` (native/browser
   comparison; the browser builder must learn LOFI2's placement and its
   Analog BD refusal), version-matched release notes in
   `src/community/module-changelogs.json`, and a `docs/VERIFICATION.md` entry.

First publication requires the owner's review and his build-approval record.
The results in TESTING.md are evidence, not an exception to those gates.
