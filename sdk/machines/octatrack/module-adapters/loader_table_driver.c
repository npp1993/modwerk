/* SPDX-License-Identifier: MIT */
/* Native-test-only trust builder. Never compile this into a board base. */
#define MODWERK_RUNTIME_METADATA_EXTERNAL
#include "loader.c"
#include "sha256.c"
#include "table_admission.h"
#include "machine_admission.h"
void *memcpy(void *to,const void *from,unsigned long length)
{ volatile uint8_t *out=to;const volatile uint8_t *in=from;for(unsigned long i=0;i<length;i++)out[i]=in[i];return to; }
/* Synthetic fixtures link without libc, like the board runtime. */
void *memset(void *to, int value, unsigned long length)
{
    volatile uint8_t *out = to;
    for (unsigned long i = 0; i < length; ++i) out[i] = (uint8_t)value;
    return to;
}
static uint8_t fixture_table[TABLE_DECLARATION_BYTES];
static uint8_t fixture_machines[MACHINE_DECLARATION_BYTES];
static int read_board(void *context,uint32_t at,void *out,uint32_t n)
{
    (void)context;uint32_t physical=at>=0x48000400u && at<0x4ff00000u?at-0x08000000u:at;
    if(!((physical>=0x40000400u && physical<0x47f00000u && n<=0x47f00000u-physical) ||
         (at>=0x10000000u && at<0x10100000u && n<=0x10100000u-at))) return 0;
    const volatile uint8_t *from=(const volatile uint8_t *)(uintptr_t)at;uint8_t *to=out;
    for(uint32_t i=0;i<n;i++)to[i]=from[i];
    return 1;
}
void fixture_hash(const uint8_t *data,uint32_t length,uint8_t *out) {mu_sha256(data,length,out);}
void fixture_clear_table(void)
{
    for(unsigned i=0;i<TABLE_DECLARATION_BYTES;i++)fixture_table[i]=modwerk_table_declarations[i];
    for(unsigned i=0;i<MACHINE_DECLARATION_BYTES;i++)fixture_machines[i]=modwerk_machine_declarations[i];
}
void fixture_review_table_offsets(const uint8_t *data,uint32_t length,uint32_t family,uint32_t state,uint32_t parameters,
    uint32_t a,uint32_t b,uint32_t c)
{
    uint8_t digest[32];mu_sha256(data,length,digest);unsigned i=0;
    for(;i<fixture_table[5];i++) {unsigned k=0;while(k<32 && fixture_table[16+60*i+k]==digest[k])k++;if(k==32)break;}
    if(i>=TABLE_DECLARATION_CAPACITY)return;
    uint8_t *r=fixture_table+16+60*i;
    for(unsigned k=0;k<32;k++)r[k]=digest[k];
    for(unsigned k=0;k<4;k++)r[32+k]=data[28+k];
    r[36]=state>>8;r[37]=state;r[38]=parameters>>8;r[39]=parameters;r[40]=family;
    r[41]=family==TABLE_QUANTIZER?3:16;r[42]=family==TABLE_QUANTIZER?3:2;r[43]=family==TABLE_QUANTIZER?3:1;
    put32(r+44,a);put32(r+48,b);put32(r+52,c);
    for(unsigned k=56;k<60;k++)r[k]=0;
    if(i==fixture_table[5])fixture_table[5]++;
}
void fixture_review_table(const uint8_t *data,uint32_t length,uint32_t family,uint32_t state,uint32_t parameters)
{fixture_review_table_offsets(data,length,family,state,parameters,80,160,240);}
void fixture_review_machine(const uint8_t *data,uint32_t length,uint32_t state,uint32_t parameters)
{
    uint8_t digest[32];mu_sha256(data,length,digest);unsigned i=0;
    for(;i<fixture_machines[5];i++) {unsigned k=0;while(k<32 && fixture_machines[16+44*i+k]==digest[k])k++;if(k==32)break;}
    if(i>=MACHINE_DECLARATION_CAPACITY)return;
    uint8_t *r=fixture_machines+16+44*i;
    for(unsigned k=0;k<32;k++)r[k]=digest[k];
    for(unsigned k=0;k<4;k++)r[32+k]=data[28+k];
    r[36]=data[81];r[37]=0;r[38]=state>>8;r[39]=state;r[40]=parameters>>8;r[41]=parameters;r[42]=r[43]=0;
    if(i==fixture_machines[5])fixture_machines[5]++;
}
int modwerk_machine_metadata_admit(const struct runtime_dsp *from,struct runtime_dsp *to,
    const struct runtime_context *context,enum runtime_metadata_operation operation)
{
    int why=machine_metadata_admission(fixture_machines,from,to,read_board,0,
        *(volatile uint32_t *)(uintptr_t)0x46c82456u);
    if(why)return why;
    why=table_machine_association(fixture_machines,fixture_table,from);
    if(why)return why;
    why=table_machine_association(fixture_machines,fixture_table,to);
    if(why)return why;
    struct runtime_span span[RUNTIME_PAUSED];unsigned count=modwerk_machine_paused(span,RUNTIME_PAUSED,context);
    why=table_metadata_admission(fixture_table,from,to,operation,read_board,0,span,count);
    if(!why)to->foreign_roots=to->present && ((to->flags&RUNTIME_GROUP_METADATA)||table_metadata_family(fixture_table,to));
    return why;
}
void fixture_review_optional_quantizer(const uint8_t *data,uint32_t length,uint32_t optional)
{
    uint8_t digest[32];mu_sha256(data,length,digest);
    for(unsigned i=0;i<fixture_machines[5];i++) {
        uint8_t *r=fixture_machines+16+44*i;unsigned k=0;
        while(k<32 && r[k]==digest[k])k++;
        if(k==32) {r[37]=(uint8_t)optional;return;}
    }
}
uint32_t fixture_table_image(void)
{const struct runtime_module *m=modwerk_runtime_module(0);return m?(uint32_t)(uintptr_t)m->dsp.image:0;}
