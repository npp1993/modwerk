/* SPDX-License-Identifier: MIT */
/* FM-only actual-controller fixture: no VECTOR/POLY engine or saved-state rewriting. */
#define _GNU_SOURCE
#include <assert.h>
#include <sys/mman.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "controller.c"
const char *mr_src_names[9]={"STATIC","FLEX","THRU","NEIGHBOR","PICKUP"};
uint32_t mr_pb_table[9];
static unsigned fm_ticks,stock_validates;
const uint8_t fm_defaults[12]={41,42,43,44,45,46,47,48,49,50,51,52};
unsigned fm_type(unsigned type,const Part *ptr) { (void)ptr;return type; }
unsigned fm_admit_track(const Part *part,unsigned track) { (void)part;(void)track;return 1; }
void fm_ui_tick(void) { fm_ticks++; }
uint32_t fm_track_page(const Part *ptr) { (void)ptr;return 0x400fed00u; }
void bridge_stock_pool_open(void) {}
void bridge_stock_list_draw(void) {}
int mr_stock_validate(uint8_t *part) {
 stock_validates++;
 for(unsigned t=0;t<8;t++)for(unsigned k=0;k<12;k++)part[(k<6?0x2a:0x1da)+30*t+6+k%6]=0;
 return 7;
}
static void map_at(uintptr_t address,size_t bytes) { assert(mmap((void *)address,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON|MAP_FIXED,-1,0)!=(void *)-1); }
static unsigned param(unsigned track,unsigned k) { return (k<6?0x2a:0x1da)+30*track+6+k%6; }
int main(void) {
 map_at(0x40000000u,0x100000u);map_at(0x46c80000u,0x4000u);map_at(0x100a0000u,0x20000u);map_at(0x80000000u,0x1000u);
 U32(BANK)=0x40000000u;U8(0x100b14cfu)=0;U8(0x100b14ccu)=0;
 Part *part=current_part();Part *mirror=(Part *)(uintptr_t)SRAM_PART;
 for(unsigned row=0;row<5;row++)U32(0x400d5f38u+4*row)=0x1000u+row;
 assert(mr_row(POLY)==0&&mr_row(AB)==0&&mr_row(VECTOR)==0&&mr_row(FM)==5);
 assert(strcmp(mr_name(5),"FM SYNTH")==0&&strcmp(mr_name(6),"FLEX")==0);
 part[0x22]=1;part[SIG]='S';part[SIG+1]='2';part[SIG+2]=2;
 assert(mr_type(1,part+0x22)==1&&mr_current_owner()==STOCK&&mr_page(part+0x22)==0);
 assert(part[SIG]=='S'&&part[SIG+1]=='2'&&part[SIG+2]==2);
 part[SIG]='P';part[SIG+1]='L';part[SIG+2]=1;assert(mr_current_owner()==STOCK);
 assert(part[SIG]=='P'&&part[SIG+1]=='L');
 memset((void *)part,0,PART_STRIDE);memset((void *)mirror,0,PART_STRIDE);
 assert(mr_assign(part,0,5)==1&&mr_assign(part,2,5)==1);
 for(unsigned k=0;k<12;k++)assert(part[param(0,k)]==fm_defaults[k]&&mirror[param(2,k)]==fm_defaults[k]);
 for(unsigned k=0;k<12;k++)part[param(0,k)]=(uint8_t)(70+k),part[param(2,k)]=(uint8_t)(90+k);
 assert(mr_validate(part)==7&&stock_validates==1);
 for(unsigned k=0;k<12;k++)assert(part[param(0,k)]==70+k&&part[param(2,k)]==90+k);
 uint32_t before=U32(0x400d5f4cu);
 mr_ui_tick();assert(fm_ticks==1&&mr_pb_table[0]==0x1000u&&mr_pb_table[5]==0x400fed00u);
 assert(U32(0x400d5f4cu)==before&&mr_page(part+0x22)==0x400fed00u);
 assert(mr_assign(part,2,0)==0&&part[SIG+60]==0&&mirror[SIG+60]==0&&part[SIG]=='F');
 puts("FM-only controller: independent tracks, private page, absent VECTOR/POLY and stock fallback passed");
 return 0;
}
