| SPDX-License-Identifier: GPL-3.0-or-later
| The base's .run is stored packed (run_pack.py): Elekloader's own section format, its codec/aplib.py
| pack_section, read as its codec/elz.py reads it. core-ot.s's boot calls this in place of its word copy
| (build_core.py), so the RAM boot image stays under its bound.
|
| Writes exactly 4 * __run_words bytes from __run_start through the uncached alias, as the copy did, so no
| cache line holds the reserve's old contents when its code first runs. It reads only inside the stream the
| section header bounds and writes only inside the run; a stream that is not exactly the run, from exactly
| that many bytes, hangs at mw_run_fatal (the unit stays at its logo) without writing outside the run. The
| stream's integrity is the bootloader's section checksum (flash) or the gate's image hash (RAM boot).
| run_pack.decode is this routine instruction by instruction, and the build refuses a stream it does not
| turn back into .run. Returns every register as it found it. ColdFire V4e; assemble with -mcpu=54455.

        .section .boot, "ax"
        .globl  mw_run_unpack
mw_run_unpack:
        lea     -40(%sp), %sp
        movem.l %d0-%d3/%a0-%a5, (%sp)
        lea     __run_load, %a0         | [u32 stream length][u32 sum], then the stream
        move.l  (%a0), %d0
        addq.l  #8, %a0
        lea     (%a0,%d0.l), %a3        | the stream's end
        movea.l #__run_start + UNCACHED, %a1
        movea.l %a1, %a2                | the run's start
        move.l  #__run_words, %d0
        lea     (%a1,%d0.l*4), %a4      | and its end
        moveq   #0, %d2                 | no tag bits yet
mw_run_next:
        bsr.s   mw_run_bit
        bcc.s   mw_run_match            | 0: a match
        cmpa.l  %a4, %a1                | 1: one literal byte
        bcc.s   mw_run_fatal
        cmpa.l  %a3, %a0
        bcc.s   mw_run_fatal
        move.b  (%a0)+, (%a1)+
        bra.s   mw_run_next
mw_run_match:
        bsr.w   mw_run_gamma
        moveq   #2, %d1
        cmp.l   %d1, %d0
        beq.s   mw_run_fatal            | 2 reuses the last offset, which the kit's packer never writes
        cmpa.l  %a3, %a0
        bcc.s   mw_run_fatal
        lsl.l   #8, %d0
        moveq   #0, %d1
        move.b  (%a0)+, %d1
        add.l   %d1, %d0
        subi.l  #767, %d0               | the offset; 0 ends the stream
        beq.s   mw_run_done
        move.l  %d0, %d3
        moveq   #0, %d1                 | two bits: a length of 1-3, or 00 and a gamma + 2
        bsr.s   mw_run_bit
        addx.l  %d1, %d1
        bsr.s   mw_run_bit
        addx.l  %d1, %d1
        tst.l   %d1                     | addx only ever clears Z
        bne.s   mw_run_far
        bsr.s   mw_run_gamma
        move.l  %d0, %d1
        addq.l  #2, %d1
mw_run_far:
        cmpi.l  #3328, %d3              | past offset 3328 the length gains 1
        bls.s   mw_run_copy
        addq.l  #1, %d1
mw_run_copy:
        movea.l %a1, %a5                | length + 1 bytes from offset back: from what is written
        suba.l  %d3, %a5
        cmpa.l  %a2, %a5
        bcs.s   mw_run_fatal
        cmpa.l  %a1, %a5
        bcc.s   mw_run_fatal
        move.l  %a4, %d0                | into the rest of the run
        sub.l   %a1, %d0
        cmp.l   %d0, %d1
        bcc.s   mw_run_fatal
mw_run_byte:
        move.b  (%a5)+, (%a1)+          | forward, so an overlapping copy repeats its pattern
        subq.l  #1, %d1
        bcc.s   mw_run_byte
        bra.s   mw_run_next
mw_run_done:
        cmpa.l  %a4, %a1                | the whole run, from the whole stream
        bne.s   mw_run_fatal
        cmpa.l  %a3, %a0
        bne.s   mw_run_fatal
        movem.l (%sp), %d0-%d3/%a0-%a5
        lea     40(%sp), %sp
        rts
mw_run_fatal:
        bra.s   mw_run_fatal
| The next tag bit into C and X. d2 holds the tag byte's bits not yet read, MSB first, above a stop bit.
mw_run_bit:
        add.l   %d2, %d2
        bne.s   mw_run_bit_done
        cmpa.l  %a3, %a0                | only the stop bit was left: the next tag byte
        bcc.s   mw_run_fatal
        move.b  (%a0)+, %d2
        lsl.l   #8, %d2
        ori.l   #0x80, %d2
        swap    %d2
        add.l   %d2, %d2
mw_run_bit_done:
        rts
| An interlaced Elias gamma into d0: from 1, each data bit shifted in, until a stop bit of 1.
mw_run_gamma:
        moveq   #1, %d0
mw_run_gamma_bit:
        bsr.s   mw_run_bit
        addx.l  %d0, %d0
        bsr.s   mw_run_bit
        bcc.s   mw_run_gamma_bit
        rts
