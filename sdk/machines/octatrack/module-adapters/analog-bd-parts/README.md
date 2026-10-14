# Unwired Analog BD Part retirement fence

`mw_ab_part_fence` is a conservative, read-only additional removal predicate.
It uses the exact imported Analog BD semantics: FLEX type1 at Part+0x22+track
and the three-byte AB/1 marker at Part+60+30*track. It never interprets that
version1 marker as an encoded-package identity, generation or ownership handoff.
Imported source hashes are pinned in the SDK test.

The fixed model reads every sixteen-bank working/saved Part, all four current
CS1 working/saved mirrors and bounded actual current/paused extra Parts. It
validates the actual current-bank pointer before deriving addresses and preserves
its canonical/uncached RAM alias. Each memory read is at most four bytes and
must return exactly1. Missing callbacks, unreadable bytes, invalid addresses,
unsupported AB revisions/types, unknown machine types or an incomplete/oversized
extra-Part enumeration refuse clearance. FLEX1+AB/1 retains the owner.

The extra-Part callback is a trusted board collector interface. Zero means an
independently complete end of actual current/paused Parts, not an uploaded flag.
No board collector is implemented or qualified here. Fixtures provide synthetic
read/enumeration events only. A missing actual collector stays closed.

A qualified stable snapshot must cover the entire read-only observation and
subsequent retirement decision. It must also respect the instrument's frame
interrupt deadlines; this scan is not permission to mask level5+ through all
banks. Native C regressions and ColdFire compilation do not qualify physical
read timing or scheduler behavior. Keep unknown state retained.

CLEAR means only that this additional observed Part-marker set had no retained
AB owner. The independent whole-controller-image, retained UI handler/label,
current/paused execution, actual DSP disable/job acknowledgments and foreign-root
fences must also pass against the same immutable generation before retirement.
Removing or replacing a marker requires the separate exact twelve-byte FLEX
restoration and publication proof; this helper writes no Part or control data.
No caller readiness, unsigned generation or host mode-off value can bypass it.

The helper has no loader wiring, production source registry, enable path or
public admission. It does not qualify descriptor ownership, group composition,
DSP audio/headroom, complete-base fit, physical timing, persistence or reboot.
All CI fixture data is authored synthetic state; no firmware is required.

## Retirement conversion (owner decision, 14 October 2026)

On Undo or removal of Analog BD, `mw_ab_restore_parts` converts every FLEX +
AB/1 track in the source-known Part copies back to FLEX, exactly as AB 0.1.5
does when one track leaves the machine: the six PLAYBACK and six SETUP bytes
from the stock FLEX defaults (0x400d320c), then the three marker bytes cleared.
The copies are all sixteen banks' working and saved Parts, the four working and
four saved CS1 mirrors, and the stock Part clipboard (0x460c8122) and undo
buffer (0x460bf218) while their kind word (0x460d0ffa, 0x460c80f0) is 17, the
only kind stock pastes back as a Part. Other kinds hold other copy data and
are never written.

It plans read-only first and refuses (UNKNOWN, no write) on any failed read,
an invalid bank pointer, an AB marker with another revision or machine type,
or a machine type above 4. Every write is read back; the marker is cleared
last, so an interrupted conversion still reads as AB-owned and returns
PARTIAL. Only a CLEAR re-scan permits the next retirement gate. Callers must
hold one qualified stable snapshot across plan and apply; each access moves at
most four bytes, and this does not qualify physical timing.

**Residual risk (accepted by the owner):** copies outside these known ones are
not converted. That covers task-stack temporaries and any other stock copy path
that is not source-proven here, including clipboard kinds other than a whole
Part that may carry per-track machine bytes. If such a copy later puts an AB
marker back into a Part after removal, the stock validator can reject that bank
at power-up. Projects saved to the card while AB was installed keep their AB
tracks; the module README's advice to keep a separate project copy for firmware
without the module still applies.
