/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "saved_set_session.h"
static unsigned le16(const uint8_t *p) { return p[0] | (unsigned)p[1] << 8; }
int msx_session_active(const struct msx_session *s) { return s->running || s->file.status != MSX_IDLE; }
int msx_session_reading(const struct msx_session *s)
{
    return s->running && s->file.status == MSX_PENDING && s->file.token == s->running_token;
}
void msx_session_reset(struct msx_session *s) { msx_reset(&s->file); s->quiet = 0; }
void msx_session_tick(struct msx_session *s)
{
    if (s->file.status != MSX_IDLE && ++s->quiet >= MSX_TIMEOUT_TICKS) msx_session_reset(s);
}
unsigned msx_session_request(struct msx_session *s, const uint8_t setup[8],
                             uint8_t out[MSX_CHUNK_BYTES], unsigned interface, int can_begin)
{
    if (!s || !setup || !out || setup[0] != 0xc1u || le16(setup + 4) != interface) return 0;
    const unsigned request = setup[1], value = le16(setup + 2), length = le16(setup + 6);
    if (request == 31u && value <= 2u && length == MSX_METADATA_BYTES) {
        if (value && (!can_begin || msx_session_active(s) || !msx_begin(&s->file, value - 1u))) {
            /* A refused begin never owns or changes the current token/snapshot. */
            msx_metadata(&s->file, out); out[5] = MSX_BUSY;
            for (unsigned i = 12; i < MSX_METADATA_BYTES; ++i) out[i] = 0;
            return MSX_METADATA_BYTES;
        }
        msx_metadata(&s->file, out); s->quiet = 0; return MSX_METADATA_BYTES;
    }
    if (request == 32u && length == MSX_CHUNK_BYTES && msx_chunk(&s->file, value, out)) {
        s->quiet = 0; return MSX_CHUNK_BYTES;
    }
    if (request == 33u && length == MSX_METADATA_BYTES && value && msx_release(&s->file, value)) {
        msx_metadata(&s->file, out); s->quiet = 0; return MSX_METADATA_BYTES;
    }
    return 0;
}
void msx_session_service(struct msx_session *s, int (*safe)(void),
    enum msx_status (*read_slot)(uint32_t, uint8_t *, uint32_t, uint32_t *),
    void (*hash)(const uint8_t *, uint32_t, uint8_t[32]))
{
    if (s->running || s->file.status != MSX_PENDING) return;
    s->running_token = s->file.token;
    __asm__ volatile ("" ::: "memory"); s->running = 1;
    /* A release/reset can have preempted before the running latch was set. */
    if (msx_session_reading(s)) msx_service(&s->file, safe && safe(), read_slot, hash);
    __asm__ volatile ("" ::: "memory"); s->running = 0;
}
