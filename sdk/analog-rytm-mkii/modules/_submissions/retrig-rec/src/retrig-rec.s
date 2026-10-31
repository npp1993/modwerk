        | Stock sites for Retrig Rec, OS 1.74. See retrig-rec.c.

        .equ    MENU_NO_STEP,   0x400e29ee        | RETRIG menu: no step to write
        .equ    TIMING_DONE,    0x400b469a        | recorder, past the quantize

        .text

        | The RETRIG menu notes the step of its opening only in LIVE RECORDING; with
        | none noted, its pressure and rate writes to the steps never run.
        .globl  retrig_rec_menu
retrig_rec_menu:
        jmp     MENU_NO_STEP

        | The recorder drops a note's micro timing with quantize on. Over `tstb d0;
        | seq d0; mvsb d0,d0; andl d0,d5`: d0 the quantize, d5 the micro timing, d7 the
        | step retrig rate or -1. A queued hit (micro + 256, see KEEP_TIMING) and a
        | retrig press keep it, and the press may lose its rate here.
        .globl  retrig_rec_timing
retrig_rec_timing:
        cmpi.l  #128,%d5
        blt.s   1f
        subi.l  #256,%d5
        bra.s   3f
1:      tst.l   %d7
        bge.s   2f
        tst.b   %d0
        seq     %d0
        extb.l  %d0
        and.l   %d0,%d5
        bra.s   3f
2:      move.l  %d4,-(%sp)
        move.l  %d7,-(%sp)
        jsr     retrig_rec_press_rate
        addq.l  #8,%sp
        move.l  %d0,%d7
3:      jmp     TIMING_DONE

        | Over the recorder's call to set the step's retrig rate (track, step, rate):
        | d4 is the pad's track.
        .globl  retrig_rec_rate
retrig_rec_rate:
        move.l  %d4,-(%sp)
        move.l  16(%sp),-(%sp)
        move.l  16(%sp),-(%sp)
        move.l  16(%sp),-(%sp)
        jsr     retrig_rec_step_rate
        lea     16(%sp),%sp
        rts

        | Over the recorder's note-off call that sets a retrig's LEN (track, step, len):
        | d6 is the note's track.
        .globl  retrig_rec_length
retrig_rec_length:
        move.l  %d6,-(%sp)
        move.l  16(%sp),-(%sp)
        move.l  16(%sp),-(%sp)
        move.l  16(%sp),-(%sp)
        jsr     retrig_rec_step_length
        lea     16(%sp),%sp
        rts
