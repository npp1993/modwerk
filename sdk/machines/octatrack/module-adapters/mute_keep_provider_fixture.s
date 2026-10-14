| SPDX-License-Identifier: GPL-3.0-or-later
| An ev_mute_keep provider for the emulator test (loader_mute_keep_fixture.cpp): the handler
| proposed for SIDECHAIN_COMPRESSOR's own runtime package, which owns the KEY. It is Mute Modes'
| native SC_KEY scan (patch_softmute.s p1_key, Session 116) in the C convention: the tracks that
| a COMPRESSOR (FX id 0x18) on any track names as its KEY (page-2 slot 8: 0 OFF, 1..8 T1..T8),
| read from this frame's per-track DSP record (half 0, 0x80000110 + t*64; FX1 id +55 and KEY
| +38, FX2 id +57 and KEY +50). Synthetic stand-in: no Sidechain package carries it yet.
        .text
        .globl  sc_mute_keep
sc_mute_keep:
        lea     0x80000110,%a0          | track 0's record, ping-pong half 0
        moveq   #0,%d0
sk_loop:
        move.b  (55,%a0),%d1            | FX1 id
        cmpi.b  #0x18,%d1
        bne.s   sk_fx2
        mvz.b   (38,%a0),%d1            | its KEY 0..8
        subq.l  #1,%d1                  | -> track 0..7; OFF lands on bit 31
        bset    %d1,%d0
sk_fx2:
        move.b  (57,%a0),%d1            | FX2 id
        cmpi.b  #0x18,%d1
        bne.s   sk_next
        mvz.b   (50,%a0),%d1
        subq.l  #1,%d1
        bset    %d1,%d0
sk_next:
        lea     (64,%a0),%a0
        cmpa.l  #0x80000310,%a0
        bne.s   sk_loop
        andi.l  #0xff,%d0               | the contract's bits 0..7
        rts
