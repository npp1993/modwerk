# QPERF

An Analog Rytm MKII mod by Nathaniel Pavel (@npp1993). Version 0.1.0-experimental. Hardware testing has started: see [TESTING.md](TESTING.md).

Set performance locks from the QPER key, much faster than one performance at a time.

## Controls

Link performances as on stock: hold QPER and press pads or trig keys. Then, with QPER still held:

| Gesture | What it does |
| --- | --- |
| Turn a knob | Works as holding a performance pad does: the knob inverts and shows the offset, here the total of the linked performances. A turn carries on from that total and splits it evenly across them, so together they reach it at full QPER. |
| PLAY | Clears every linked performance, with stock's clear. PLAY again undoes it, while the links and locks are as the clear left them. |
| YES | Writes what the linked performances add at the QPER knob's position into the kit, muted or not. The locks stay. |

FUNC + QPER (mute) and linking are stock's.

Stock draws every message. YES shows PERFORMANCE 3 APPLIED, or PERFORMANCES APPLIED with several linked, or NOTHING TO APPLY. PLAY shows the same with CLEARED, then UNDO CLEAR or NOTHING TO CLEAR. A turn with nothing linked shows NOTHING LINKED, and with no room LOCK MEM FULL!.

## Things to know

- **Linked performances add up.** That is why a turn is split across them.
- **48 locks a kit.** All 12 performances share them. A new parameter takes one lock in each linked performance. If they do not all fit, the turn writes nothing and shows LOCK MEM FULL!. Turning a parameter already locked in all of them needs no new lock.
- **After YES the sound moves further.** The kit now holds the offsets and the locks still add them on top, until you turn QPER down or clear with QPER + PLAY.
- **FX track.** QPER + knob sets FX locks as a performance pad does. QPER + YES skips them.
- **Changing links while you hold QPER** changes what the knob shows: it is always the total of the performances linked now.

## Stock flows changed

- **QPER + PLAY** starts the sequencer on stock. With this mod it clears instead: PLAY alone still starts the sequencer, so stock loses only the combination. Remove the mod to get it back.
- **QPER + knob** changes the parameter on stock. With this mod it edits locks and leaves the parameter alone.
- **QPER + YES** did nothing visible on stock (rytm-emu, OS 1.74).

## Tutorial

1. Hold QPER, press pads 1 and 2 to link two performances, and keep holding.
2. Turn FLTR's cutoff up and the resonance a little, and let go of QPER.
3. Sweep the QPER knob. Both moves come in together.
4. When a position sounds right, hold QPER and press YES to keep it in the kit.
5. Turn the QPER knob down, and hold QPER and press PLAY to clear the locks.
