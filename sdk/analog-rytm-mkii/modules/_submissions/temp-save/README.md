# Temp Save

An Analog Rytm MKII mod by Nathaniel Pavel (@npp1993). Version 0.1.0-experimental. See [TESTING.md](TESTING.md) for what ran on a unit.

Save the pattern and its kit with one gesture, try something, and get back.

## Controls

| Gesture | What it does | Message |
| --- | --- | --- |
| FUNC + YES | Saves the active pattern and its kit. | TEMP SAVED |
| FUNC + NO | Reloads both. | RELOADED |
| FUNC + NO with no save for this pattern | Nothing changes. | NO TEMP SAVE |

Both work on the main screen and the sound pages, stopped or playing. There are no settings, no effect slot and no knob.

## What it saves

It runs stock's pattern save and kit save, then stock's pattern reload and kit reload. The kit's record holds its performance and scene locks, so they come back too.

- **The pattern's copy is one buffer in RAM.** Stock refills it on every pattern change, so a save belongs to its pattern. Change pattern and come back, or load a project, and FUNC + NO shows NO TEMP SAVE. The module uses no memory for the copy: a pattern is 85,760 bytes, more than the room modules share.
- **The kit's copy is the kit's saved copy.** FUNC + YES replaces what stock's kit reload returns to, and a project save keeps it. This is the difference from the Octatrack module of the same name.
- **While a message shows,** the message takes FUNC + NO, so wait for it to go and press again.

## Changes to stock flows

| Change | For whom | Why | Neighbouring flows |
| --- | --- | --- | --- |
| FUNC + NO on a sound page no longer does stock's FUNC + NO, unless a trig is held. | Anyone with the module installed. | The gesture matches Digitakt and Digitone and the Octatrack module. With no trig held stock's case changes nothing that was seen, and a held trig leaves the keys to stock. | RANDOMIZE PAGE (page key + YES) and the sample slot list were run with the module in; see TESTING.md. |
| FUNC + YES saves where stock does nothing visible. | Anyone with the module installed. | The gesture itself. | Menus and lists take YES first and keep it. |

## Compatibility

It patches three stock calls, in the main view's YES and NO cases and in the sound page's NO case, and subscribes to `ev_tick` and `ev_project`. A screen above those views that takes YES or NO keeps it. Claims `ui:FUNC + YES` and `ui:FUNC + NO`. It needs no other module.

## Credits

Original work by Nathaniel Pavel. The design follows Digitakt's and Digitone's temp save and the Octatrack's Temp Save, with no code shared.
