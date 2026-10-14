/* SPDX-License-Identifier: GPL-3.0-or-later
 * Owner-approved AB retirement (14 Oct 2026): convert every FLEX + AB/1 track
 * in the source-known Part copies back to FLEX, as AB 0.1.5 does when one track
 * leaves AB (machine.s ab_sig_write): the 12 borrowed bytes from stock FLEX
 * defaults 0x400d320c, then the marker cleared. Layout facts as in
 * analog_bd_part_fence.c. The stock Part clipboard 0x460c8122 and undo buffer
 * 0x460bf218 hold a Part only while their kind word is 17, the only value with
 * which stock pastes them back (0x40029b78 reads 0x460d0ffa, 0x40029b08 reads
 * 0x460c80f0); other kinds hold other copy data and are never written here.
 */
#include "analog_bd_part_restore.h"
#define BANK0 0x400e21e0u
#define BANK_STRIDE 0x9b340u
#define PART_BYTES 6322u
#define UNCACHED 0x08000000u
#define RAM_END 0x47f00000u
#define DEFAULTS 0x400d320cu
#define PART_KIND 17u
static const uint32_t buffers[2][2]={{0x460c8122u,0x460d0ffau},{0x460bf218u,0x460c80f0u}};
static int get(const struct mw_ab_part_io *io,uint32_t at,uint8_t *out,unsigned n)
{
    while (n) { unsigned k=n>4u?4u:n; if (io->read(io->context,at,out,k)!=1) return 0; at+=k;out+=k;n-=k; }
    return 1;
}
static int put(const struct mw_ab_part_io *io,uint32_t at,const uint8_t *in,unsigned n)
{
    uint8_t back[4];
    while (n) {
        unsigned k=n>4u?4u:n;
        if (io->write(io->context,at,in,k)!=1 || io->read(io->context,at,back,k)!=1) return 0;
        for (unsigned i=0;i<k;++i) if (back[i]!=in[i]) return 0;
        at+=k;in+=k;n-=k;
    }
    return 1;
}
static uint32_t be32(const uint8_t *p) { return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3]; }
static int scan(const struct mw_ab_part_io *io,struct mw_ab_restore_plan *plan,uint32_t at)
{
    uint8_t mine=0;
    for (unsigned track=0;track<8u;++track) {
        uint8_t type,signature[3];
        if (!get(io,at+0x22u+track,&type,1) || !get(io,at+60u+30u*track,signature,3)) return 0;
        if (signature[0]=='A' && signature[1]=='B') {
            if (type!=1u || signature[2]!=1u) return 0; /* unsupported marker: never guess */
            mine|=(uint8_t)(1u<<track);
        } else if (type>4u) return 0;
    }
    if (mine) { plan->part[plan->count]=at;plan->tracks[plan->count]=mine;++plan->count; }
    return 1;
}
int mw_ab_restore_plan(const struct mw_ab_part_io *io,struct mw_ab_restore_plan *plan)
{
    uint8_t word[4];
    if (!io || !io->read || !io->write || !plan) return MW_AB_RESTORE_UNKNOWN;
    plan->count=0;
    if (!get(io,0x46c82456u,word,4) || !get(io,DEFAULTS,plan->defaults,12)) return MW_AB_RESTORE_UNKNOWN;
    uint32_t current=be32(word),alias=current>=0x48000000u && current<RAM_END+UNCACHED?UNCACHED:0;
    uint32_t physical=current-alias;
    if (physical<BANK0 || physical>BANK0+15u*BANK_STRIDE || (physical-BANK0)%BANK_STRIDE) return MW_AB_RESTORE_UNKNOWN;
    for (unsigned bank=0;bank<16u;++bank)
        for (unsigned region=0;region<2u;++region)
            for (unsigned index=0;index<4u;++index)
                if (!scan(io,plan,BANK0+alias+bank*BANK_STRIDE+(region?0x9504au:0x8ed80u)+index*PART_BYTES))
                    return MW_AB_RESTORE_UNKNOWN;
    for (unsigned region=0;region<2u;++region)
        for (unsigned index=0;index<4u;++index)
            if (!scan(io,plan,(region?0x100ab196u:0x100a4eceu)+index*PART_BYTES)) return MW_AB_RESTORE_UNKNOWN;
    for (unsigned b=0;b<2u;++b) {
        if (!get(io,buffers[b][1],word,4)) return MW_AB_RESTORE_UNKNOWN;
        if (be32(word)==PART_KIND && !scan(io,plan,buffers[b][0])) return MW_AB_RESTORE_UNKNOWN;
    }
    return plan->count?MW_AB_RESTORE_PLANNED:MW_AB_RESTORE_CLEAR;
}
int mw_ab_restore_apply(const struct mw_ab_part_io *io,const struct mw_ab_restore_plan *plan)
{
    static const uint8_t cleared[3]={0,0,0};
    if (!io || !io->read || !io->write || !plan || plan->count>MW_AB_RESTORE_PARTS) return MW_AB_RESTORE_UNKNOWN;
    for (unsigned n=0;n<plan->count;++n)
        for (unsigned track=0;track<8u;++track) {
            if (!(plan->tracks[n]>>track&1u)) continue;
            uint32_t at=plan->part[n]+30u*track;
            if (!put(io,at+0x2au+6u,plan->defaults,6) || !put(io,at+0x1dau+6u,plan->defaults+6,6) ||
                !put(io,at+60u,cleared,3)) return MW_AB_RESTORE_PARTIAL;
        }
    return MW_AB_RESTORE_CLEAR;
}
int mw_ab_restore_parts(const struct mw_ab_part_io *io,struct mw_ab_restore_plan *plan)
{
    int result=mw_ab_restore_plan(io,plan);
    if (result!=MW_AB_RESTORE_PLANNED) return result;
    if (mw_ab_restore_apply(io,plan)!=MW_AB_RESTORE_CLEAR) return MW_AB_RESTORE_PARTIAL;
    result=mw_ab_restore_plan(io,plan);
    return result==MW_AB_RESTORE_CLEAR?MW_AB_RESTORE_CLEAR:result==MW_AB_RESTORE_UNKNOWN?MW_AB_RESTORE_UNKNOWN:MW_AB_RESTORE_PARTIAL;
}
