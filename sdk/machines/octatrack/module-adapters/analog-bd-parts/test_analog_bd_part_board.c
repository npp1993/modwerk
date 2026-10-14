/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host check of the board access window only (MODWERK_HOST: no target memory). */
#include "analog_bd_part_board.h"
#include <assert.h>
#include <stdio.h>
#define BANK0 0x400e21e0u
#define BANK_STRIDE 0x9b340u
#define STRIDE 6322u
int main(void)
{
    unsigned cases=0;
    for(unsigned alias=0;alias<2u;++alias)for(unsigned bank=0;bank<16u;++bank)for(unsigned region=0;region<2u;++region)for(unsigned index=0;index<4u;++index){
        uint32_t at=BANK0+(alias?0x08000000u:0)+bank*BANK_STRIDE+(region?0x9504au:0x8ed80u)+index*STRIDE;
        assert(mw_ab_part_board_access(at,4,1) && mw_ab_part_board_access(at+STRIDE-4u,4,1));
        assert(mw_ab_part_board_access(at+STRIDE-1u,1,0) && !mw_ab_part_board_access(at+STRIDE-2u,4,0) && (index||region||!mw_ab_part_board_access(at-1u,1,1)));
        cases+=4;
    }
    for(unsigned index=0;index<4u;++index){
        assert(mw_ab_part_board_access(0x100a4eceu+index*STRIDE,4,1) && mw_ab_part_board_access(0x100ab196u+index*STRIDE+STRIDE-3u,3,1));++cases;
        assert(!mw_ab_part_board_access(0x100a4eceu+index*STRIDE+0x08000000u,4,1));++cases; /* SRAM has no RAM alias */
    }
    for(unsigned b=0;b<2u;++b){uint32_t at=b?0x460bf218u:0x460c8122u;
        assert(mw_ab_part_board_access(at,4,1) && mw_ab_part_board_access(at+0x08000000u+STRIDE-4u,4,1) && !mw_ab_part_board_access(at+STRIDE,1,0));cases+=3;}
    /* Read-only facts: never written, exact widths. */
    const uint32_t words[]={0x46c82456u,0x460d0ffau,0x460c80f0u};
    for(unsigned i=0;i<3u;++i){assert(mw_ab_part_board_access(words[i],4,0) && !mw_ab_part_board_access(words[i],4,1) && !mw_ab_part_board_access(words[i],2,0));cases+=3;}
    assert(mw_ab_part_board_access(0x400d320cu,4,0) && mw_ab_part_board_access(0x400d3214u,4,0) && !mw_ab_part_board_access(0x400d3216u,4,0));
    assert(!mw_ab_part_board_access(0x400d320cu,4,1));cases+=4;
    /* Outside every record: bank gaps, stock code, other RAM, oversize and wrap. */
    const uint32_t outside[]={BANK0,BANK0+0x8ed80u-1u,BANK0+0x8ed80u+4u*STRIDE,BANK0+16u*BANK_STRIDE+0x8ed80u,0x40000400u,0x47000000u,0x100a4eceu-4u,0xfffffffeu};
    for(unsigned i=0;i<sizeof outside/sizeof outside[0];++i){assert(!mw_ab_part_board_access(outside[i],2,0) && !mw_ab_part_board_access(outside[i],2,1));++cases;}
    assert(!mw_ab_part_board_access(BANK0+0x8ed80u,0,0) && !mw_ab_part_board_access(BANK0+0x8ed80u,5,1));cases+=2;
    printf("PASS AB board access window: %u cases; writes only inside the 138 Part records\n",cases);
    return 0;
}
