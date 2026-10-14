/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_SAVED_SET_SESSION_H
#define MODWERK_SAVED_SET_SESSION_H
#include "saved_set_export.h"
#define MSX_TIMEOUT_TICKS 600u
struct msx_session {
    struct msx_export file;
    volatile uint32_t running;
    uint32_t running_token;
    volatile uint32_t quiet;
};
/* ISR: strict fixed-interface request shape, queue/cache only. No reader call.
 * 31: value 0 poll, 1 begin slot0, 2 begin slot1; 32: chunk ordinal;
 * 33: nonzero current 16-bit release token. All are vendor-interface IN. */
unsigned msx_session_request(struct msx_session *, const uint8_t setup[8],
                             uint8_t out[MSX_CHUNK_BYTES], unsigned interface, int can_begin);
int msx_session_active(const struct msx_session *);
int msx_session_reading(const struct msx_session *);
void msx_session_reset(struct msx_session *);
void msx_session_tick(struct msx_session *);
/* Engine-only. running survives ISR release/reset until read/hash returns. */
void msx_session_service(struct msx_session *, int (*safe)(void),
    enum msx_status (*read_slot)(uint32_t, uint8_t *, uint32_t, uint32_t *),
    void (*hash)(const uint8_t *, uint32_t, uint8_t[32]));
#endif
