/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_ANALOG_BD_PART_RESTORE_H
#define MODWERK_ANALOG_BD_PART_RESTORE_H
#include <stdint.h>
/* 16 banks x (4 working + 4 saved), the 8 CS1 mirrors, then the stock Part
 * clipboard and undo buffers while their kind word says they hold a Part. */
#define MW_AB_RESTORE_PARTS 138u
/* Trusted board accessors under one qualified stable snapshot. Each call moves
 * 1..4 bytes and returns exactly1 when complete; anything else is unknown. */
struct mw_ab_part_io {
    void *context;
    int (*read)(void *, uint32_t, uint8_t *, unsigned);
    int (*write)(void *, uint32_t, const uint8_t *, unsigned);
};
struct mw_ab_restore_plan {
    uint32_t part[MW_AB_RESTORE_PARTS];
    uint8_t tracks[MW_AB_RESTORE_PARTS]; /* bit t: FLEX + AB/1 on track t */
    unsigned count;
    uint8_t defaults[12];                /* stock FLEX defaults, 6 PLAYBACK + 6 SETUP */
};
enum mw_ab_restore_result {
    MW_AB_RESTORE_CLEAR=0,    /* no AB/1 track left in any known copy */
    MW_AB_RESTORE_PLANNED=1,  /* plan holds tracks to convert */
    MW_AB_RESTORE_UNKNOWN=2,  /* unreadable copy, bad bank pointer or unsupported AB marker */
    MW_AB_RESTORE_PARTIAL=3   /* a write or read-back failed: markers may remain, retain both owners */
};
/* Read-only. Refuses (UNKNOWN) on any failed read, an invalid current bank,
 * an AB prefix with another revision or machine type, or a type above 4. */
int mw_ab_restore_plan(const struct mw_ab_part_io *, struct mw_ab_restore_plan *);
/* Per planned track: the 12 borrowed FLEX bytes from the plan's stock
 * defaults, read back, then the 3-byte marker cleared and read back. The
 * marker goes last, so an interrupted conversion still reads as AB-owned. */
int mw_ab_restore_apply(const struct mw_ab_part_io *, const struct mw_ab_restore_plan *);
/* Plan, apply, then plan again: CLEAR only when the re-read finds no AB/1. */
int mw_ab_restore_parts(const struct mw_ab_part_io *, struct mw_ab_restore_plan *);
#endif
