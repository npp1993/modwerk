/* SPDX-License-Identifier: GPL-3.0-or-later
 * MWLD v1: public read-only cached load, never starts a meter or self-test. */
#ifndef MODWERK_LOAD_WIRE_H
#define MODWERK_LOAD_WIRE_H
#include <stdint.h>
#define MODWERK_LOAD_BYTES 48u
struct modwerk_load_cache { uint32_t flags, frames, at[3], values[5]; };
static inline void modwerk_load_encode(uint8_t *out, uint32_t ticks, const volatile struct modwerk_load_cache *cache)
{
    out[0] = 'M'; out[1] = 'W'; out[2] = 'L'; out[3] = 'D';
    out[4] = 1; out[5] = (uint8_t)cache->flags; out[6] = 0; out[7] = MODWERK_LOAD_BYTES;
    uint32_t words[10] = {ticks, cache->frames, cache->at[0], cache->at[1], cache->at[2],
                         cache->values[0], cache->values[1], cache->values[2], cache->values[3], cache->values[4]};
    for (unsigned i = 0; i < 10u; ++i)
        for (unsigned b = 0; b < 4u; ++b) out[8u + 4u * i + b] = (uint8_t)(words[i] >> (24u - 8u * b));
}
#endif
