// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef MODWERK_USB_AUDIO_PROFILES_H
#define MODWERK_USB_AUDIO_PROFILES_H
#include <stdint.h>
/* Internal staging seam only. No host command, authorization, intentional
   reconnect lease, inventory, Keep/Undo or persistence contract exists yet. */
struct host_state {uint8_t *first,*end,*bank,*step,*alt,*running,*closed;};
extern const struct host_state mu_audio_profile_states[6];
extern const uint16_t mu_audio_profile_lengths[7];
extern volatile uint32_t mu_audio_profile, mu_audio_config_length;
uint32_t mu_audio_stage_detached(uint32_t next);
/* 0 committed; 1 invalid; 2 controller/EP3 busy; 3 audio request/running;
   4 EP0 transfer, stock awaited state or old clock SET still pending.
   A refusal changes neither the profile nor retained host/musical state. */
uint32_t mu_audio_stage_locked(uint32_t next);
#endif
