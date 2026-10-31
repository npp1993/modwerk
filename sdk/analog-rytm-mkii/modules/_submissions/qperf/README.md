# QPERF

An Analog Rytm MKII mod by Nathaniel Pavel (@npp1993). Version 0.1.0-experimental. See [TESTING.md](TESTING.md) for what ran on a unit.

Set performance locks from the QPER key, much faster than one performance at a time.

## Controls

QPER links one performance at a time. Hold QPER and press a pad or trig key: the link moves there. Press the linked one to unlink it. With QPER still held:

| Gesture | What it does |
| --- | --- |
| Turn a knob | Edits the linked performance's lock, as holding a performance pad does: the knob inverts and shows the offset. |
| PLAY | CLEAR PERFORMANCE, with stock's clear. PLAY again: UNDO CLEAR. |
| YES | What the lock adds at the QPER knob's position goes into the kit and comes off the lock, so full QPER still lands where it did. At full, the sound holds and the lock goes away, freeing its slot. |
| RECORD | COPY PERFORMANCE n. |
| STOP | PASTE PERFORMANCE onto the linked one. STOP again: UNDO PASTE. |

FUNC + QPER (mute) is stock's.

Stock draws every message. YES shows PERFORMANCE n APPLIED, or NOTHING TO APPLY when no lock has a value. A key or turn with nothing linked shows NO PERFORMANCE LINKED, and with no room LOCK MEM FULL!.

## Things to know

- **One link only.** A kit saved with several, or loaded with another, drops to the lowest one. An unlinked performance stops adding, and the newly linked one takes the knob's position, so the sound follows the link.
- **48 locks a kit.** All 12 performances share them. A new parameter with none left shows LOCK MEM FULL! and writes nothing.
- **Power on.** Stock does not know the QPER knob until it moves, so the amount is 0 and YES adds nothing until then.
- **YES and later edits.** The target holds through YES. Turn the parameter by hand afterwards and the target moves with it, because locks are offsets.

## Stock flows changed

- **QPER + pads and trigs** link several performances on stock. With this mod a press moves the one link, and the linked one unlinks it. Why: linked offsets add up, so several made the knob's total and QPER + YES hard to follow.
- **QPER + PLAY** starts the sequencer on stock. With this mod it clears instead. PLAY alone still starts it.
- **QPER + STOP and QPER + RECORD** act as STOP and RECORD on stock. With this mod they paste and copy.
- **QPER + knob** changes the parameter on stock. With this mod it edits locks and leaves the parameter alone.
- **QPER + YES** did nothing visible on stock (rytm-emu, OS 1.74).

Remove the mod to get these back.

## Tutorial

1. Hold QPER, press pad 1 to link its performance, and keep holding.
2. Turn FLTR's cutoff up and the resonance a little, and let go of QPER.
3. Sweep the QPER knob. Both moves come in together.
4. When a position sounds right, hold QPER and press YES to keep it in the kit.
5. Hold QPER and press RECORD, press pad 2, then STOP to start another performance from this one.
