| SPDX-License-Identifier: GPL-3.0-or-later
| Input Pre-Fader Sends for the Digitakt mk1, OS 1.54.
|
| The render's mixer (0x40071c20) loops over ten channels: tracks 1-8, then
| IN L and IN R (d2 = 8, 9). For each one it builds two pan gains in d0/d1,
| multiplies them by the channel's LEV gain to get the dry gains, and then
| derives the delay and reverb sends from those dry gains, so the sends are
| post-fader. With SETTINGS > INPUT SENDS PRE ticked, the external inputs'
| sends are taken from the pan gains before LEV instead. Tracks are never
| changed, and with the row unticked both handlers run exactly the
| instructions they replace.
|
| Both sites are jsr patches that return with rts, so they also work from
| digihealth's FAST AUDIO copy of the render in SRAM.
|
| SETTINGS > KEEP FX AWAKE. Loading a project and pressing STOP twice put
| the delay and reverb on hold: the audio interrupt fades them out and keeps
| their inputs cleared until an audio track trigs, so the external inputs get
| no effect until then. Ticked, the hold is released as soon as its fade-out
| has finished (under a second), so a double STOP still empties the effects
| but the inputs come back without a trig.

        .equ STR_CTOR,   0x4017af20     | std::string(this, const char*, alloc&)
        .equ INVALIDATE, 0x400c9a3a     | View::invalidate(view)
        .equ BLIT,       0x400c2b88     | blit(dst, src, x, y, centre)
        .equ CHECKBOXES, 0x421f8a3c     | -> Bitmap[2], 0x1c each: empty, ticked
        .equ FX_HOLD,    0x4199f124     | 0 off; 2 asked (STOP STOP, load); 1 holding
        .equ FX_FADE,    0x4199f464     | the hold's fade-out level, 16 bits

        .section .run, "ax"

| ---- 0x40071e36: the dry gains (8 bytes: the two msac.l below) ------------
| d0/d1 hold this channel's pan gains, d6 its LEV gain. Keep the pan gains
| for the sends, then make the dry gains as stock does. Only acc0/acc1 change.
        .balign 2
        .globl  ipf_dry
ipf_dry:
        move.l  %d0, ipf_pan_l
        move.l  %d1, ipf_pan_r
        msac.l  %d0, %d6, %acc0         | the instructions this replaced
        msac.l  %d1, %d6, %acc1
        addq.l  #2, (%sp)               | past the site's nop padding
        rts

| ---- 0x40071eb4: the sends (24 bytes) ---------------------------------------
| In: d0/d1 the dry gains, a0 the delay level, d6 the reverb level, d2 the
| channel. Out, as stock: a1/a0 the delay sends, d6/d1 the reverb sends.
| For IN L and IN R in PRE, the pan gains stand in for the dry gains; d0 is
| overwritten right after this block, so changing it here is safe.
        .balign 2
        .globl  ipf_sends
ipf_sends:
        tst.b   ipf_pre
        beq.s   1f
        cmpi.l  #8, %d2
        blt.s   1f                      | a track: stock
        move.l  ipf_pan_l, %d0
        move.l  ipf_pan_r, %d1
1:      msac.l  %d0, %a0, %acc0         | the instructions this replaced
        msac.l  %d1, %a0, %acc1
        movclr.l %acc0, %a1
        movclr.l %acc1, %a0
        msac.l  %d0, %d6, %acc0
        msac.l  %d1, %d6, %acc1
        movclr.l %acc0, %d6
        movclr.l %acc1, %d1
        addq.l  #8, (%sp)               | resume after the site's 24 bytes:
        addq.l  #8, (%sp)               | 18 bytes of nop padding, skipped
        addq.l  #2, (%sp)               | without touching a register
        rts

| ---- 0x40077ef8: the effects hold (6 bytes: move.l FX_HOLD, %d0) ----------
| In the audio interrupt, right before the beq that skips the hold's work
| when FX_HOLD is 0. Ticked, a hold whose fade has reached 0 is released
| here, as an audio track's trig would. The move.l replayed last sets the
| flags the beq tests; rts leaves them alone.
        .balign 2
        .globl  ipf_hold
ipf_hold:
        tst.b   ipf_awake
        beq.s   1f
        moveq   #1, %d0
        cmp.l   FX_HOLD, %d0
        bne.s   1f                      | off, or not yet holding
        tst.w   FX_FADE
        bne.s   1f                      | still fading out
        clr.l   FX_HOLD
1:      move.l  FX_HOLD, %d0            | the instruction this replaced
        rts

| ---- ev_settings: the INPUT SENDS PRE and KEEP FX AWAKE rows ---------------
| Checkbox rows like the stock ones: YES or RIGHT ticks one, YES or LEFT
| unticks it. Unticked (stock) at every power-on; not saved. Each row's
| entries load its flag into a1 (and its name) and share the code below.
        .balign 2
        .globl  ipf_settings
ipf_settings:
        pea     ipf_row
        move.l  8(%sp), -(%sp)          | the menu
        jsr     core_additem
        addq.l  #8, %sp
        pea     ipf_row2
        move.l  8(%sp), -(%sp)
        jsr     core_additem
        addq.l  #8, %sp
        rts

ipf_label:
        lea     ipf_name, %a1
        bra.s   ipf_label_any
ipf_label2:
        lea     ipf_name2, %a1
ipf_label_any:
        link    %a6, #-4
        move.l  %d2, -(%sp)
        pea     -1(%a6)
        move.l  %a1, -(%sp)
        move.l  %a0, %d2
        move.l  %a0, -(%sp)             | the string to build
        jsr     STR_CTOR
        lea     12(%sp), %sp
        move.l  %d2, %d0
        move.l  -8(%a6), %d2
        unlk    %a6
        rts

ipf_select:
        lea     ipf_pre, %a1
        bra.s   ipf_select_any
ipf_select2:
        lea     ipf_awake, %a1
ipf_select_any:
        move.l  %d2, -(%sp)
        movea.l 8(%sp), %a0
        move.l  (%a0), %d2              | the menu
        tst.b   (%a1)
        bne.s   2f
1:      moveq   #1, %d0
        move.b  %d0, (%a1)
        bra.s   3f
2:      clr.b   (%a1)
3:      movea.l %d2, %a0
        lea     0x38(%a0), %a0
        move.l  (%sp)+, %d2
        move.l  %a0, 4(%sp)
        jmp     INVALIDATE              | redraw the menu

ipf_change:
        lea     ipf_pre, %a1
        bra.s   ipf_change_any
ipf_change2:
        lea     ipf_awake, %a1
ipf_change_any:
        move.l  12(%sp), %d0            | delta
        beq.s   9f
        move.l  %d2, -(%sp)
        movea.l 8(%sp), %a0
        move.l  (%a0), %d2
        tst.l   %d0
        bpl.s   1b                      | RIGHT: tick
        bra.s   2b                      | LEFT: untick
9:      rts

ipf_draw:
        lea     ipf_pre, %a1
        bra.s   ipf_draw_any
ipf_draw2:
        lea     ipf_awake, %a1
ipf_draw_any:
        moveq   #0, %d0
        tst.b   (%a1)
        beq.s   1f
        moveq   #0x1c, %d0              | the ticked box
1:      add.l   CHECKBOXES, %d0
        move.l  12(%sp), %d1
        move.l  %d1, 4(%sp)
        move.l  %d0, 8(%sp)
        move.l  16(%sp), %d1
        move.l  %d1, 12(%sp)
        move.l  20(%sp), %d1
        move.l  %d1, 16(%sp)
        clr.l   20(%sp)
        jmp     BLIT

        .balign 4
ipf_row:    .long   ipf_label, ipf_select, ipf_draw, ipf_change
ipf_row2:   .long   ipf_label2, ipf_select2, ipf_draw2, ipf_change2
ipf_name:   .asciz  "INPUT SENDS PRE"
ipf_name2:  .asciz  "KEEP FX AWAKE"
        .balign 2

        .section .bss
        .balign 4
ipf_pan_l:  .skip 4             | this channel's pan gains, before LEV
ipf_pan_r:  .skip 4
ipf_pre:    .skip 2             | byte 0: INPUT SENDS PRE is ticked
ipf_awake:  .skip 2             | byte 0: KEEP FX AWAKE is ticked
