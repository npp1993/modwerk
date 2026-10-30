# QPERF

An Analog Rytm MKII mod by Nathaniel Pavel (@npp1993). Version 0.1.0-experimental. Not tested on hardware.

Set performance locks from the QPER key, much faster than one performance at a time.

## Controls

Link performances as on stock: hold QPER and press pads or trig keys. Then, with QPER still held:

| Gesture | What it does |
| --- | --- |
| Turn a knob | The knob's travel since QPER went down becomes the parameter's offset. It replaces that parameter's lock in every linked performance, split evenly, so together they reach it at full QPER. A box shows the total. |
| PLAY | Clears every linked performance, with stock's clear. There is no undo. |
| YES | Writes what the linked performances add at the QPER knob's position into the kit. The locks stay. |

FUNC + QPER (mute) and linking are stock's.

Boxes: NO LINKS (QPER links nothing), LOCKS FULL, CLEARED, APPLIED, NOTHING (nothing to apply: the knob is at zero), MUTED (QPER is muted, so YES does nothing).

## Things to know

- **Linked performances add up.** That is why a turn is split across them.
- **48 locks a kit.** All 12 performances share them. A new parameter takes one lock in each linked performance. If they do not all fit, the turn writes nothing and shows LOCKS FULL. Turning a parameter already locked in all of them needs no new lock.
- **After YES the sound moves further.** The kit now holds the offsets and the locks still add them on top, until you turn QPER down or clear with QPER + PLAY.
- **QPER + YES skips the FX track.** Knob turns on the FX track are not tested.

## Stock flows changed

- **QPER + PLAY** starts the sequencer on stock. With this mod it clears instead, because PLAY is next to where the hand already is and QPER + PLAY has no other stock meaning. PLAY alone is unchanged. Remove the mod to get it back.
- **QPER + knob** changes the parameter on stock. With this mod it writes locks and leaves the parameter alone. On a parameter that has no lock id, such as a trig page's, stock's behaviour stays.
- **QPER + YES** did nothing visible on stock (rytm-emu, OS 1.74).

## Tutorial

1. Hold QPER, press pads 1 and 2 to link two performances, and keep holding.
2. Turn FLTR's cutoff up and the resonance a little, and let go of QPER.
3. Sweep the QPER knob. Both moves come in together.
4. When a position sounds right, hold QPER and press YES to keep it in the kit.
5. Turn the QPER knob down, and hold QPER and press PLAY to clear the locks.
