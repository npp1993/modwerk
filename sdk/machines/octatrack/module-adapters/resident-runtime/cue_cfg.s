| SPDX-License-Identifier: GPL-3.0-or-later
| CUE CFG 2 (Output Matrix's MATRIX) across a project load and a power cycle, resident bases only
| (build_core.py --resident-stock-hooks). Stock boot parses the project and checks the CS1 settings before any
| module package is installed, so the base owns both widenings and the Output Matrix package leaves them out.
| Stock never writes 2: for every other project and setting both behave as stock.
|
| The project load (0x4008732a, a jmp over tst.l d0; bge.s; clr.l d0): stock clamps CUE_STUDIO_MODE in d0 to
| 0 below zero and to 1 above it, then stores it at 0x40087338. Here 0..2 is kept and anything above 2 reads
| as STUDIO (1), as stock reads any positive value. Only d0 and the condition codes change, as stock.
        .text
        .globl  modwerk_cue_cfg_clamp
modwerk_cue_cfg_clamp:
        tst.l   %d0
        bge.s   1f
        moveq   #0,%d0
        jmp     0x40087338
1:      cmpi.l  #2,%d0
        ble.s   2f
        moveq   #1,%d0
2:      jmp     0x40087338
