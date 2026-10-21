# SPDX-License-Identifier: GPL-3.0-or-later
| Private all-profile base source-link prototype; no settings ABI.
.text
.global audio_frame_shim
audio_frame_shim:
 movel mu_audio_profile,%d0
 cmpil #6,%d0
 beq 1f
 moveq #0,%d0
 jsr p5_post_frame
 jsr p5_post_emac_leave
1:
 .global dispatch_frame
dispatch_frame:
 lea %sp@(-12),%sp
 moveml %d0/%a0,%sp@
 movel mu_audio_profile,%d0
 lea dispatch_frame_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(8)
 moveml %sp@,%d0/%a0
 lea %sp@(8),%sp
 rts
.balign 4
dispatch_frame_table:
 .long off_dispatch_frame
 .long p0_audio_frame_shim
 .long p1_audio_frame_shim
 .long p2_audio_frame_shim
 .long p3_audio_frame_shim
 .long p4_audio_frame_shim
 .long p5_audio_frame_shim
 | Preserve the handler entry CCR as well as registers. In particular, the
| audio-off GET_INTERFACE path reproduces a PEA, which leaves CCR unchanged.
.global audio_setiface_shim
audio_setiface_shim:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lea audio_setiface_shim_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 rts
.balign 4
audio_setiface_shim_table:
 .long off_audio_setiface_shim
 .long p0_audio_setiface_shim
 .long p1_audio_setiface_shim
 .long p2_audio_setiface_shim
 .long p3_audio_setiface_shim
 .long p4_audio_setiface_shim
 .long p5_audio_setiface_shim
 .global audio_getiface_shim
audio_getiface_shim:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lea audio_getiface_shim_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 rts
.balign 4
audio_getiface_shim_table:
 .long off_audio_getiface_shim
 .long p0_audio_getiface_shim
 .long p1_audio_getiface_shim
 .long p2_audio_getiface_shim
 .long p3_audio_getiface_shim
 .long p4_audio_getiface_shim
 .long p5_audio_getiface_shim
 .global audio_ctrl_shim
audio_ctrl_shim:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lea audio_ctrl_shim_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 rts
.balign 4
audio_ctrl_shim_table:
 .long off_audio_ctrl_shim
 .long p0_audio_ctrl_shim
 .long p1_audio_ctrl_shim
 .long p2_audio_ctrl_shim
 .long p3_audio_ctrl_shim
 .long p4_audio_ctrl_shim
 .long p5_audio_ctrl_shim
 .global audio_reset_shim
audio_reset_shim:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lea audio_reset_shim_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 rts
.balign 4
audio_reset_shim_table:
 .long off_audio_reset_shim
 .long p0_audio_reset_shim
 .long p1_audio_reset_shim
 .long p2_audio_reset_shim
 .long p3_audio_reset_shim
 .long p4_audio_reset_shim
 .long p5_audio_reset_shim
 .global audio_sessend_shim
audio_sessend_shim:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lea audio_sessend_shim_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 rts
.balign 4
audio_sessend_shim_table:
 .long off_audio_sessend_shim
 .long p0_audio_sessend_shim
 .long p1_audio_sessend_shim
 .long p2_audio_sessend_shim
 .long p3_audio_sessend_shim
 .long p4_audio_sessend_shim
 .long p5_audio_sessend_shim
 .global audio_isr_shim
audio_isr_shim:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lea audio_isr_shim_table,%a0
 movel %a0@(0,%d0:l:4),%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 rts
.balign 4
audio_isr_shim_table:
 .long off_audio_isr_shim
 .long p0_audio_isr_shim
 .long p1_audio_isr_shim
 .long p2_audio_isr_shim
 .long p3_audio_isr_shim
 .long p4_audio_isr_shim
 .long p5_audio_isr_shim

.global audio_ep0page_shim
.set audio_ep0page_shim, p5_audio_ep0page_shim
.global post_xlv
.set post_xlv, p5_post_xlv
@INITIAL_ALIASES@

off_dispatch_frame:
 clrl 0x46104d4e
 jmp 0x4000d9a6
off_audio_setiface_shim:
 movel 0xfc0b01c4,%d0
 jmp 0x4001dd0a
off_audio_getiface_shim:
 pea 0x400e20a1
 jmp 0x4001d81e
off_audio_ctrl_shim:
 movel 0xfc0b01c0,%d0
 jmp 0x4001de6a
off_audio_reset_shim:
 jsr 0x4001d6b8
 moveq #64,%d0
 jmp 0x4001e922
off_audio_sessend_shim:
 movel 0xfc0b0140,%d0
 jmp 0x4001e958
off_audio_isr_shim:
 jmp usbmidi_rx_isr_shim
.data
.balign 4
.global mu_audio_profile
mu_audio_profile: .long @INITIAL_PROFILE@
.bss
.balign 32
.global shared_ring,shared_sum
shared_ring: .space 81920
shared_sum: .space 8192

.global p0_usbaudio_consumed,p0_usbaudio_lastbank,p0_aud_step,p0_usbaudio_alt,p0_aud_running,p0_aud_closed,p0_aud_force

.global p1_usbaudio_consumed,p1_usbaudio_lastbank,p1_aud_step,p1_usbaudio_alt,p1_aud_running,p1_aud_closed,p1_aud_force

.global p2_usbaudio_consumed,p2_usbaudio_lastbank,p2_aud_step,p2_usbaudio_alt,p2_aud_running,p2_aud_closed,p2_aud_force

.global p3_usbaudio_consumed,p3_usbaudio_lastbank,p3_aud_step,p3_usbaudio_alt,p3_aud_running,p3_aud_closed,p3_aud_force

.global p4_usbaudio_consumed,p4_usbaudio_lastbank,p4_aud_step,p4_usbaudio_alt,p4_aud_running,p4_aud_closed,p4_aud_force

.global p5_usbaudio_consumed,p5_usbaudio_lastbank,p5_aud_step,p5_usbaudio_alt,p5_aud_running,p5_aud_closed,p5_aud_force
.global p5_uac2_set_pending

.text
.global mu_audio_stage_detached
mu_audio_stage_detached:
 movew %sr,%d0
 movel %d0,%sp@-
 movew #0x2700,%sr
 movel %sp@(8),%sp@-
 jsr mu_audio_stage_locked
 addql #4,%sp
 movel %sp@+,%d1
 movew %d1,%sr
 rts
