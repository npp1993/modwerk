/* SPDX-License-Identifier: GPL-3.0-or-later
 * Authored synthetic Part memory only: no firmware bytes, board callbacks or
 * generation proof. The 12 "stock defaults" below are invented test values. */
#include "analog_bd_part_restore.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define STRIDE 6322u
#define BANK0 0x400e21e0u
#define BANK_STRIDE 0x9b340u
#define ROWS 138u
struct fixture {
    uint8_t rows[ROWS][STRIDE];
    uint8_t defaults[12];
    uint32_t current,kind[2];
    unsigned reads,writes,fail_read,fail_write,corrupt_write;
};
static uint32_t address(unsigned row)
{
    if(row<128u)return BANK0+(row/8u)*BANK_STRIDE+(row%8u<4u?0x8ed80u:0x9504au)+(row%4u)*STRIDE;
    if(row<136u)return(row<132u?0x100a4eceu:0x100ab196u)+(row%4u)*STRIDE;
    return row==136u?0x460c8122u:0x460bf218u;
}
static uint8_t *locate(struct fixture *f,uint32_t at,unsigned n)
{
    if(at>=0x48000000u && at<0x50000000u)at-=0x08000000u;
    for(unsigned row=0;row<ROWS;++row){uint32_t base=address(row);
        if(at>=base && at-base<=STRIDE-n)return f->rows[row]+at-base;}
    return 0;
}
static void put32(uint8_t *out,uint32_t v){for(unsigned i=0;i<4u;++i)out[i]=(uint8_t)(v>>(24u-8u*i));}
static int read_mem(void *context,uint32_t at,uint8_t *out,unsigned n)
{
    struct fixture *f=context;assert(n>=1u && n<=4u);
    if(++f->reads==f->fail_read)return 0;
    if(at==0x46c82456u){assert(n==4u);put32(out,f->current);return 1;}
    if(at==0x460d0ffau||at==0x460c80f0u){assert(n==4u);put32(out,f->kind[at==0x460c80f0u]);return 1;}
    if(at>=0x400d320cu && at+n<=0x400d3218u){memcpy(out,f->defaults+(at-0x400d320cu),n);return 1;}
    uint8_t *p=locate(f,at,n);if(!p)return 0;memcpy(out,p,n);return 1;
}
static int write_mem(void *context,uint32_t at,const uint8_t *in,unsigned n)
{
    struct fixture *f=context;assert(n>=1u && n<=4u);
    ++f->writes;if(f->writes==f->fail_write)return -1;
    uint8_t *p=locate(f,at,n);assert(p);memcpy(p,in,n);
    if(f->writes==f->corrupt_write)p[0]^=0x55u;
    return 1;
}
static void fresh(struct fixture *f)
{
    memset(f,0,sizeof *f);f->current=BANK0;f->fail_read=f->fail_write=f->corrupt_write=0xffffffffu;
    for(unsigned i=0;i<12u;++i)f->defaults[i]=(uint8_t)(0x30u+i);
    for(unsigned row=0;row<ROWS;++row)for(unsigned i=0;i<STRIDE;++i)f->rows[row][i]=(uint8_t)((i*7u+row*13u)%97u);
    for(unsigned row=0;row<ROWS;++row)for(unsigned t=0;t<8u;++t){f->rows[row][0x22u+t]=1;memset(f->rows[row]+60u+30u*t,0,3);}
}
static void sign(struct fixture *f,unsigned row,unsigned track,unsigned type,unsigned revision)
{
    f->rows[row][0x22u+track]=(uint8_t)type;uint8_t *p=f->rows[row]+60u+30u*track;p[0]='A';p[1]='B';p[2]=(uint8_t)revision;
}
static int converted(const struct fixture *f,const uint8_t before[STRIDE],unsigned row,unsigned track)
{
    for(unsigned i=0;i<STRIDE;++i){
        uint8_t want=before[i];unsigned at=i;
        if(at>=0x2au+30u*track+6u && at<0x2au+30u*track+12u)want=f->defaults[at-(0x2au+30u*track+6u)];
        else if(at>=0x1dau+30u*track+6u && at<0x1dau+30u*track+12u)want=f->defaults[6u+at-(0x1dau+30u*track+6u)];
        else if(at>=60u+30u*track && at<63u+30u*track)want=0;
        if(f->rows[row][i]!=want)return 0;
    }
    return 1;
}
int main(void)
{
    struct fixture *f=calloc(1,sizeof *f);uint8_t *before=malloc(STRIDE);assert(f&&before);
    struct mw_ab_part_io io={f,read_mem,write_mem};struct mw_ab_restore_plan plan;unsigned cases=0;
    assert(mw_ab_restore_parts(NULL,&plan)==MW_AB_RESTORE_UNKNOWN);
    struct mw_ab_part_io missing={f,read_mem,NULL};fresh(f);assert(mw_ab_restore_parts(&missing,&plan)==MW_AB_RESTORE_UNKNOWN);
    for(unsigned alias=0;alias<2u;++alias)for(unsigned bank=0;bank<16u;++bank){
        fresh(f);f->current=BANK0+bank*BANK_STRIDE+(alias?0x08000000u:0);f->kind[0]=f->kind[1]=17;
        assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_CLEAR && !f->writes);++cases;
    }
    /* Every known copy, every track: exactly 15 bytes change, both buffers only as kind-17 Parts. */
    for(unsigned row=0;row<ROWS;++row)for(unsigned track=0;track<8u;++track){
        fresh(f);f->kind[0]=f->kind[1]=17;f->current=BANK0+(row%16u)*BANK_STRIDE+(track&1u?0x08000000u:0);
        sign(f,row,track,1,1);memcpy(before,f->rows[row],STRIDE);
        assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_CLEAR);
        assert(converted(f,before,row,track) && f->rows[row][0x22u+track]==1u);++cases;
    }
    for(unsigned b=0;b<2u;++b)for(uint32_t kind=0;kind<20u;++kind){
        fresh(f);f->kind[b]=kind;f->kind[!b]=0;sign(f,136u+b,3,1,1);memcpy(before,f->rows[136u+b],STRIDE);
        int r=mw_ab_restore_parts(&io,&plan);
        if(kind==17u)assert(r==MW_AB_RESTORE_CLEAR && converted(f,before,136u+b,3));
        else assert(r==MW_AB_RESTORE_CLEAR && !f->writes && !memcmp(before,f->rows[136u+b],STRIDE));
        ++cases;
    }
    /* Many tracks across many copies in one pass. */
    fresh(f);f->kind[0]=f->kind[1]=17;
    for(unsigned row=0;row<ROWS;row+=3u)for(unsigned track=row%3u;track<8u;track+=2u)sign(f,row,track,1,1);
    assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_CLEAR);
    assert(mw_ab_restore_plan(&io,&plan)==MW_AB_RESTORE_CLEAR);++cases;
    /* Unsupported markers and machine types refuse before any write. */
    for(unsigned type=0;type<7u;++type)for(unsigned revision=0;revision<3u;++revision){
        fresh(f);sign(f,40,5,type,revision);sign(f,7,0,1,1);
        int r=mw_ab_restore_parts(&io,&plan);
        if(type==1u && revision==1u)assert(r==MW_AB_RESTORE_CLEAR);else assert(r==MW_AB_RESTORE_UNKNOWN && !f->writes);
        ++cases;
    }
    fresh(f);f->rows[135][0x22u+7u]=5;sign(f,0,0,1,1);assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_UNKNOWN && !f->writes);++cases;
    for(uint32_t bad=0;bad<4u;++bad){fresh(f);sign(f,0,0,1,1);f->current=bad==0?0:bad==1?BANK0+1u:bad==2?BANK0+16u*BANK_STRIDE:0x4c0e21e0u;
        assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_UNKNOWN && !f->writes);++cases;}
    /* Every failed plan read refuses with no write. */
    fresh(f);f->kind[0]=17;sign(f,9,2,1,1);assert(mw_ab_restore_plan(&io,&plan)==MW_AB_RESTORE_PLANNED);
    unsigned plan_reads=f->reads;
    for(unsigned failure=1;failure<=plan_reads;++failure){fresh(f);f->kind[0]=17;sign(f,9,2,1,1);f->fail_read=failure;
        assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_UNKNOWN && !f->writes);++cases;}
    /* Every failed or corrupted write is PARTIAL; the marker goes last, so a
     * track whose conversion did not complete still reads as AB-owned. */
    fresh(f);sign(f,9,2,1,1);sign(f,130,6,1,1);assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_CLEAR);
    unsigned total_writes=f->writes;assert(total_writes==2u*(2u+2u+1u));
    for(unsigned failure=1;failure<=total_writes;++failure)for(unsigned corrupt=0;corrupt<2u;++corrupt){
        fresh(f);sign(f,9,2,1,1);sign(f,130,6,1,1);
        if(corrupt)f->corrupt_write=failure;else f->fail_write=failure;
        assert(mw_ab_restore_parts(&io,&plan)==MW_AB_RESTORE_PARTIAL);
        unsigned done=(failure-1u)/5u,marker=(failure-1u)%5u==4u;
        const uint8_t *second=f->rows[130]+60u+30u*6u,*first=f->rows[9]+60u+30u*2u;
        int ab_first=first[0]=='A' && first[1]=='B' && first[2]==1u,ab_second=second[0]=='A' && second[1]=='B' && second[2]==1u;
        if(done==0u){assert(ab_second);if(!(marker && corrupt))assert(ab_first);}
        else{assert(!first[0] && !first[1] && !first[2]);if(!(marker && corrupt))assert(ab_second);}
        ++cases;
    }
    free(before);free(f);
    printf("PASS AB Part conversion: %u synthetic copy/alias/kind/marker/read/write cases; marker cleared last, no board proof\n",cases);
    return 0;
}
