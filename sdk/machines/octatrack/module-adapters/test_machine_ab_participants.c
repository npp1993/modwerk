/* SPDX-License-Identifier: MIT */
/* Synthetic exact record identities only; no encoded/source/hardware proof. */
#include "machine_admission.h"
#include <assert.h>
#include <string.h>
static unsigned reads;
static int read_memory(void *context,uint32_t address,void *out,uint32_t bytes)
{ (void)context;(void)address;reads++;memset(out,0,bytes);return 1; }
static void put16(uint8_t *p,unsigned v) { p[0]=v>>8;p[1]=v; }
static void put32(uint8_t *p,uint32_t v) { put16(p,v>>16);put16(p+2,v); }
int main(void)
{
    uint8_t images[20][16],table[MACHINE_DECLARATION_BYTES];
    struct runtime_dsp groups[20],none={0};
    memcpy(table,modwerk_machine_declarations,sizeof table);memset(groups,0,sizeof groups);
    assert(sizeof table==1072u && table[4]==2 && table[5]==0 && table[6]==24);
    for(unsigned n=0;n<20;n++) {
        unsigned choice=n%10,mask=choice<7?choice+1:choice-6;
        unsigned flags=(choice>=7?MACHINE_OPTIONAL_QUANTIZER:0u)|(n>=10?MACHINE_ANALOG_BD:0u);
        memset(images[n],0,16);memcpy(images[n],"MWMG\1",5);images[n][5]=mask;
        groups[n].present=1;groups[n].flags=RUNTIME_GROUP_METADATA;groups[n].module=0xdb769930u;
        groups[n].layout=1;groups[n].image=images[n];groups[n].image_bytes=16;groups[n].package_sha256[0]=n+1;
        uint8_t *r=table+MACHINE_DECLARATION_HEADER+n*MACHINE_DECLARATION_RECORD;
        memcpy(r,groups[n].package_sha256,32);put32(r+32,groups[n].module);r[36]=mask;r[37]=flags;put16(r+38,1);put16(r+40,1);
    }
    table[5]=20;
    for(unsigned n=0;n<20;n++) {
        assert(machine_metadata_optional_quantizer(table,&groups[n])==(int)((n%10>=7)?1:0));
        assert(machine_metadata_analog_bd(table,&groups[n])==(int)(n>=10?2:0));
        assert(machine_metadata_admission(table,&none,&groups[n],read_memory,0,0x400e21e0u)==(n>=10?RUNTIME_CONFLICT:RUNTIME_OK));
        for(unsigned to=0;to<20;to++) if(n>=10 || to>=10) {
            reads=0;
            assert(machine_metadata_admission(table,&groups[n],&groups[to],read_memory,0,0x400e21e0u)==RUNTIME_CONFLICT);
            assert(reads==0); /* No partial Part/UI/DSP authority from declarations. */
        }
        if(n>=10) assert(machine_metadata_admission(table,&groups[n],&none,read_memory,0,0x400e21e0u)==RUNTIME_CONFLICT);
        groups[n].package_sha256[31]=1;assert(machine_metadata_analog_bd(table,&groups[n])==-1);groups[n].package_sha256[31]=0;
        groups[n].layout=2;assert(machine_metadata_optional_quantizer(table,&groups[n])==-1);groups[n].layout=1;
        groups[n].module^=1;assert(machine_metadata_analog_bd(table,&groups[n])==-1);groups[n].module^=1;
    }
    table[4]=1;assert(machine_metadata_analog_bd(table,&groups[10])==-1);
    assert(machine_metadata_admission(table,&none,&groups[10],read_memory,0,0)==RUNTIME_MALFORMED);table[4]=2;
    unsigned flag_at=16+44*13+37;table[flag_at]|=1; /* FM's implicit QZ is not optional. */
    assert(machine_metadata_analog_bd(table,&groups[0])==-1);table[flag_at]&=~1u;
    table[flag_at]|=4;assert(machine_metadata_analog_bd(table,&groups[0])==-1);table[flag_at]&=~4u;
    memcpy(table+16+44*20,table+16,44);table[5]=21;
    assert(machine_metadata_analog_bd(table,&groups[10])==-1); /* Duplicates cannot differ by flags. */
    table[5]=20;memset(table+16+44*20,0,44);table[16+44*23]=1;
    assert(machine_metadata_optional_quantizer(table,&groups[0])==-1);
    return 0;
}
