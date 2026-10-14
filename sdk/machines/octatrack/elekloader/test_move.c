/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host check of the allocator's move (build_core.py's edit to Octabam's allocator.c, applied by test_recipe.py):
 * a live package gets a new copy only clear of all live code, its own old copy included; one move at a time; after
 * the commit and the retirement only that package sits elsewhere. */
#include "allocator.h"
#include <stdio.h>
static uint32_t source[2]; /* dsp.c: the machines' source-stage charge per core */
uint32_t modwerk_dsp_source_charge(unsigned c) { return source[c]; }

static unsigned failures;
#define CHECK(x) do { if (!(x)) { failures++; fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #x); } } while (0)
static struct dl_package catalog[DL_PACKAGES];

int main(void)
{
    static struct dl_allocator a;
    catalog[1] = (struct dl_package){100, 1, 10, 3, 0, 1, 0};
    catalog[2] = (struct dl_package){50, 4, 10, 3, 0, 1, 0};
    dl_allocator_init(&a, catalog, 1000, 1000, 100000, 100000);
    /* Core 1 by hand: package 1 at 0+100, package 2 at 152+50, a hole at 100-152. */
    a.live[1][1] = (struct dl_placement){0, 100, 1};
    a.live[1][2] = (struct dl_placement){152, 50, 1};
    CHECK(dl_allocator_move(&a, 1, 2, 120, 7) == DL_ALLOC_TRANSITION); /* over its own old copy */
    CHECK(dl_allocator_move(&a, 1, 2, 60, 7) == DL_ALLOC_TRANSITION);  /* over package 1 */
    CHECK(dl_allocator_move(&a, 1, 2, 101, 7) == DL_ALLOC_MEMORY);     /* off its alignment */
    CHECK(dl_allocator_move(&a, 1, 2, 952, 7) == DL_ALLOC_MEMORY);     /* past the arena */
    CHECK(dl_allocator_move(&a, 1, 3, 300, 7) == DL_ALLOC_STALE);      /* not live */
    CHECK(dl_allocator_move(&a, 1, 2, 100, 0) == DL_ALLOC_STALE);      /* no token */
    CHECK(dl_allocator_move(&a, 1, 2, 300, 7) == DL_ALLOC_OK);         /* to the top first: clear of everything */
    CHECK(a.phase == 1 && a.required == 2 && a.target[1][2].offset == 300 && a.target[1][1].offset == 0 && a.target[1][1].present);
    CHECK(dl_allocator_move(&a, 1, 1, 400, 8) == DL_ALLOC_STALE);      /* one move at a time */
    CHECK(a.live[1][2].offset == 152);                                 /* the old copy stays live until the commit */
    CHECK(dl_allocator_ack(&a, 7, 1) == DL_ALLOC_OK && dl_allocator_commit(&a, 7) == DL_ALLOC_OK);
    CHECK(dl_allocator_retire(&a, 7) == DL_ALLOC_OK && a.phase == 0);
    CHECK(a.live[1][2].present && a.live[1][2].offset == 300 && a.live[1][1].present && a.live[1][1].offset == 0);
    CHECK(dl_allocator_move(&a, 1, 2, 100, 9) == DL_ALLOC_OK);         /* then down into the hole, now clear */

    /* Placement: a package of a quarter of the arena or more as high as it fits, the rest as low. */
    static struct dl_allocator b;
    uint8_t ids[16];
    catalog[3] = (struct dl_package){300, 1, 10, 3, 0, 1, 0};
    catalog[4] = (struct dl_package){260, 4, 10, 3, 0, 1, 0};
    catalog[5] = (struct dl_package){330, 1, 10, 3, 0, 1, 0};
    dl_allocator_init(&b, catalog, 1000, 1000, 100000, 100000);
    for (unsigned i = 0; i < 16u; ++i) ids[i] = DL_NONE;
    ids[0] = 3, ids[1] = 1, ids[2] = 4; /* core 1 */
    CHECK(dl_allocator_prepare(&b, ids, 5) == DL_ALLOC_OK);
    CHECK(b.target[1][3].offset == 700 && b.target[1][1].offset == 0 && b.target[1][4].offset == 440); /* 4: aligned down */
    CHECK(dl_allocator_ack(&b, 5, 1) == DL_ALLOC_OK && dl_allocator_commit(&b, 5) == DL_ALLOC_OK && dl_allocator_retire(&b, 5) == DL_ALLOC_OK);
    ids[3] = 5; /* the highest run that holds it, between 1 and 4 */
    CHECK(dl_allocator_prepare(&b, ids, 6) == DL_ALLOC_OK && b.target[1][5].offset == 110 && b.target[1][3].offset == 700);
    CHECK(dl_allocator_cancel(&b, 6) == DL_ALLOC_OK);
    catalog[5].words = 341; /* no run holds it, nor the whole arena */
    CHECK(dl_allocator_prepare(&b, ids, 7) == DL_ALLOC_MEMORY);

    /* Source stage: each core's FX slots are admitted beside its machines' charge; past the allowance, nothing. */
    static struct dl_allocator s;
    dl_allocator_init(&s, catalog, 1000, 1000, 100, 100);
    for (unsigned i = 0; i < 16; ++i) ids[i] = DL_NONE;
    ids[0] = 1; /* track 1, core 1: 10 cycles */
    source[1] = 90; CHECK(dl_allocator_prepare(&s, ids, 11) == DL_ALLOC_OK); dl_allocator_cancel(&s, 11);
    source[1] = 91; CHECK(dl_allocator_prepare(&s, ids, 12) == DL_ALLOC_CYCLES);
    source[1] = 101; ids[0] = DL_NONE; CHECK(dl_allocator_prepare(&s, ids, 13) == DL_ALLOC_CYCLES); /* no underflow */
    source[1] = 0; source[0] = 95; ids[4] = 1; CHECK(dl_allocator_prepare(&s, ids, 14) == DL_ALLOC_CYCLES); /* track 5: core 0 */
    source[0] = 0;
    if (failures) { fprintf(stderr, "%u move checks failed\n", failures); return 1; }
    puts("allocator move: clear of live code, one at a time, only that package moves; big packages placed from the top.");
    return 0;
}
