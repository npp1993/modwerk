/* SPDX-License-Identifier: GPL-3.0-or-later
 * Octatrack board accessors for the AB retirement conversion. Base-only: the
 * caller is the loader's metadata admission, under the stable machine lock with
 * no task running (RUNTIME_METADATA_SWITCH). Reads reach only the Part records,
 * the bank pointer, the stock FLEX defaults and the two clipboard kind words;
 * writes reach only the 138 Part records. Cached and uncached RAM aliases
 * resolve to the same record; the access keeps the caller's alias.
 */
#include "analog_bd_part_board.h"
#define BANK0 0x400e21e0u
#define BANK_STRIDE 0x9b340u
#define PART_BYTES 6322u
static uint32_t physical(uint32_t at) { return at>=0x48000400u && at<0x4ff00000u ? at-0x08000000u : at; }
static int inside(uint32_t at,unsigned n,uint32_t base,uint32_t bytes) { return at>=base && at-base<=bytes-n; }
static int record(uint32_t at,unsigned n)
{
    uint32_t p=physical(at);
    if (p>=BANK0 && p<BANK0+16u*BANK_STRIDE) {
        uint32_t in=(p-BANK0)%BANK_STRIDE;
        for (unsigned region=0;region<2u;++region)
            for (unsigned index=0;index<4u;++index)
                if (inside(in,n,(region?0x9504au:0x8ed80u)+index*PART_BYTES,PART_BYTES)) return 1;
        return 0;
    }
    for (unsigned index=0;index<4u;++index)
        if (inside(at,n,0x100a4eceu+index*PART_BYTES,PART_BYTES) || inside(at,n,0x100ab196u+index*PART_BYTES,PART_BYTES)) return 1;
    return inside(p,n,0x460c8122u,PART_BYTES) || inside(p,n,0x460bf218u,PART_BYTES);
}
int mw_ab_part_board_access(uint32_t at,unsigned n,int write)
{
    if (!n || n>4u || at>UINT32_MAX-n) return 0;
    if (record(at,n)) return 1;
    if (write) return 0;
    return (at==0x46c82456u || at==0x460d0ffau || at==0x460c80f0u) ? n==4u : inside(at,n,0x400d320cu,12u);
}
#ifndef MODWERK_HOST
static int board_read(void *context,uint32_t at,uint8_t *out,unsigned n)
{
    (void)context;
    if (!mw_ab_part_board_access(at,n,0)) return 0;
    const volatile uint8_t *from=(const volatile uint8_t *)(uintptr_t)at;
    for (unsigned i=0;i<n;++i) out[i]=from[i];
    return 1;
}
static int board_write(void *context,uint32_t at,const uint8_t *in,unsigned n)
{
    (void)context;
    if (!mw_ab_part_board_access(at,n,1)) return 0;
    volatile uint8_t *to=(volatile uint8_t *)(uintptr_t)at;
    for (unsigned i=0;i<n;++i) to[i]=in[i];
    return 1;
}
/* The plan is board state, not stack: retirement may run on a small task stack. */
static struct mw_ab_restore_plan plan;
static int locked(void)
{
    uint32_t sr;
    __asm__ __volatile__("move.w %%sr,%0" : "=d"(sr) :: "memory");
    return (sr&0x0700u)>=0x0400u;
}
int mw_ab_board_check(void)
{
    const struct mw_ab_part_io io={0,board_read,board_write};
    if (!locked()) return MW_AB_RESTORE_UNKNOWN;
    return mw_ab_restore_plan(&io,&plan);
}
int mw_ab_board_retire(void)
{
    const struct mw_ab_part_io io={0,board_read,board_write};
    if (!locked()) return MW_AB_RESTORE_UNKNOWN;
    return mw_ab_restore_parts(&io,&plan);
}
#endif
