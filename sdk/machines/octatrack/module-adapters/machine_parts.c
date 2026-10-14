/* SPDX-License-Identifier: GPL-3.0-or-later
 * Stock-free layout facts: 1.40C copy routine 0x4004a908 copies 6322B
 * bank+0x8ed80+i*6322 -> bank+0x9504a+i*6322, then saved SRAM
 * 0x100ab196+i*6322. Shared authored machine owner uses machine byte
 * Part[0x22+track] < 2 and signature Part[60+30*track]. */
#include "machine_parts.h"
#define STRIDE 6322u
#define UNCACHED 0x08000000u
#define STOCK_RAM_END 0x47f00000u
#define FM_LEG 0x2fdu
#define FLEX_SLOT 0x2cbu
#define SETTINGS_BASE 0x100b14f0u
#define SETTINGS_STRIDE 0x448u
/* FM's reviewed po_is_synth/po_slot_marker read FLEX only, slots0..127.
 * Its basename prefix is case-sensitive SYNTH or FMSYNTH; suffixes allowed.
 * A nonterminated/unreadable path is unknown, never evidence of absence. */
static int marker(machine_part_read read, void *context, uint8_t slot)
{
    if (slot >= 128u) return MACHINE_PART_CLEAR; /* none or recorder */
    uint8_t path[256];
    if (!read(context, SETTINGS_BASE + slot * SETTINGS_STRIDE, path, sizeof path))
        return MACHINE_PART_UNKNOWN;
    unsigned end=0,base=0;
    while (end<sizeof path && path[end]) { if (path[end]=='/') base=end+1u; ++end; }
    if (end==sizeof path) return MACHINE_PART_UNKNOWN;
    if (end-base>=2u && path[base]=='F' && path[base+1u]=='M') base+=2u;
    return end-base>=5u && path[base]=='S' && path[base+1u]=='Y' && path[base+2u]=='N' &&
           path[base+3u]=='T' && path[base+4u]=='H' ? MACHINE_PART_FM_MARKER : MACHINE_PART_CLEAR;
}
static unsigned member(const uint8_t *signature)
{
    if (signature[0] == 'P' && signature[1] == 'L' && signature[2] == 1) return 1;
    if (signature[0] == 'S' && signature[1] == '2' && (signature[2] == 1 || signature[2] == 2)) return 2;
    if (signature[0] == 'F' && signature[1] == 'M' && signature[2] == 1) return 4;
    return 0;
}
int machine_part_lifetime(machine_part_read read, void *context, uint32_t bank, unsigned dropped)
{
    if (!dropped) return 0;
    uint32_t physical = bank >= 0x48000000u && bank < STOCK_RAM_END + UNCACHED ? bank - UNCACHED : bank;
    if (!read || (dropped & ~7u) || (bank & 1u) || physical < 0x40000000u ||
        physical > STOCK_RAM_END - (0x9504au + 4u * STRIDE)) return 2;
    /* Validate the physical extent, but read RAM through the caller's alias.
     * The fixed battery SRAM mirrors retain their reviewed addresses. */
    for (unsigned region = 0; region < 4; ++region) {
        uint32_t base = region == 0 ? bank + 0x8ed80u : region == 1 ? bank + 0x9504au :
                        region == 2 ? 0x100a4eceu : 0x100ab196u;
        for (unsigned part = 0; part < 4; ++part)
            for (unsigned track = 0; track < 8; ++track) {
                uint8_t type, signature[3];
                uint32_t at = base + part * STRIDE;
                if (!read(context, at + 0x22u + track, &type, 1)) return 2;
                if (dropped & 4u) {
                    uint8_t leg,slot;
                    if (!read(context, at + FM_LEG + 30u * track, &leg, 1)) return MACHINE_PART_UNKNOWN;
                    if (leg) return MACHINE_PART_FM_LEG; /* all ordinary audio machines, not only signed FM */
                    if (type > 4u) return MACHINE_PART_UNKNOWN;
                    if (type == 1u) {
                        if (!read(context, at + FLEX_SLOT + 5u * track, &slot, 1)) return MACHINE_PART_UNKNOWN;
                        int result=marker(read,context,slot);
                        if (result) return result;
                    }
                }
                if (type >= 2u) continue; /* only FLEX/STATIC carry signed owners */
                if (!read(context, at + 60u + 30u * track, signature, 3)) return MACHINE_PART_UNKNOWN;
                if (member(signature) & dropped) return MACHINE_PART_RETAINED;
            }
    }
    return 0;
}
int machine_part_signature(machine_part_read read, void *context, uint32_t bank, const uint8_t sig[2], uint8_t lo, uint8_t hi)
{
    uint32_t physical = bank >= 0x48000000u && bank < STOCK_RAM_END + UNCACHED ? bank - UNCACHED : bank;
    if (!read || !sig || (bank & 1u) || physical < 0x40000000u || physical > STOCK_RAM_END - (0x9504au + 4u * STRIDE)) return MACHINE_PART_UNKNOWN;
    for (unsigned region = 0; region < 4; ++region) {
        uint32_t base = region == 0 ? bank + 0x8ed80u : region == 1 ? bank + 0x9504au : region == 2 ? 0x100a4eceu : 0x100ab196u;
        for (unsigned part = 0; part < 4; ++part)
            for (unsigned track = 0; track < 8; ++track) {
                uint8_t type, s[3];
                uint32_t at = base + part * STRIDE;
                if (!read(context, at + 0x22u + track, &type, 1)) return MACHINE_PART_UNKNOWN;
                if (type >= 2u) continue;
                if (!read(context, at + 60u + 30u * track, s, 3)) return MACHINE_PART_UNKNOWN;
                if (s[0] == sig[0] && s[1] == sig[1] && s[2] >= lo && s[2] <= hi) return MACHINE_PART_RETAINED;
            }
    }
    return MACHINE_PART_CLEAR;
}
