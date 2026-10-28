"""TEMP SAVE -- [FUNC] + [YES] keeps a temporary copy of the active pattern
and its whole Part (scenes included); [FUNC] + [NO] puts both back, as
Temp Save and Reload do on the Digitakt and Digitone.

One slot, in the module's memory, empty at every power-on: the active
pattern's 0x8ed8 bytes and the working Part's 0x18b2 bytes, with the bank,
pattern, Part and a hash of the project's name and set. A reload on another
bank, pattern or project changes nothing (NO TEMP SAVE). The pattern goes
back through stock's pattern writer 0x4002b9b0 (pattern paste and its
undo), the Part through stock's Part Reload 0x4004aab4 with the copy
swapped into the saved slot for the call and back out after it, then FUNC
+ CUE's screen refresh. The saved Part, the clipboard, the crossfader, the
scene selection and the mutes stay as they were.

Stock routines changed: two. The FUNCTION layer's YES handler 0x4005e3d8
and NO handler 0x4005e1fc take a press while no sample list is open (and
outside YES's divert and NO's special mode); there stock's FUNC + YES runs
the plain-YES routine (ARM ALL) and FUNC + NO the plain-NO routine (DISARM
ALL), which YES and NO alone still do. Everything else replays the two
displaced instructions. Measured under ot_emu: see verify.py and
TESTING.md.
"""

from remix.schema import Category, Proof, Gate, Detour, Kind, Linked, Module
from remix.stock_guard import stock_guard

MODULE = Module(
    name="temp-save",
    key="TEMP SAVE",
    kind=Kind.CF_PATCH,
    doc="FUNC + YES temp-saves the active pattern and its Part; FUNC + NO reloads them.",
    category=Category.PARTS, author="npp1993", author_url="https://github.com/npp1993",
    proof=Proof.UNTESTED, proof_note="draft; verify.py under ot_emu not yet run",
    # 773 bytes of code and 42,892 bytes of buffers (one pattern, one Part),
    # position-independent, in the DRAM reserve as Apply Scene's unit.
    linked=(Linked("temp_save", "modules/temp-save/unit.s", cpu="5475", dram=True),),
    detours=(
        Detour(0x4005E3D8, stock_guard(0x4005e3d8, 8, "74c5c24f09bf544b8fad303723b3935f248a9f48eefdbd230049cf63bd8fee5e"),
               "temp_save", "ts_yes_hook",
               "FUNCTION-layer YES handler entry: with no list open, FUNC + YES temp-saves the pattern and its Part",
               kind="jmp", pad_to=8),
        Detour(0x4005E1FC, stock_guard(0x4005e1fc, 8, "91fea154aed7ca7f7aed1e03380f8eba791542d2f01b3f4a9b173e2dec9df118"),
               "temp_save", "ts_no_hook",
               "FUNCTION-layer NO handler entry: with no list open, FUNC + NO reloads the temp save",
               kind="jmp", pad_to=8),
    ),
    gates=(Gate("modules/temp-save/verify.py", remix_arg=False),),
)
