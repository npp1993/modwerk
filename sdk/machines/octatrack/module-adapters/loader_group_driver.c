/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Synthetic board admission or actual private declaration helper under the
 * explicit native-test define. Production's default trust table is empty. */
#define MODWERK_RUNTIME_METADATA_EXTERNAL
#include "loader.c"
#include "sha256.c"
void *memcpy(void *to, const void *from, unsigned long length)
{
    volatile uint8_t *out=to;
    const volatile uint8_t *in=from;
    for (unsigned long i=0;i<length;i++) out[i]=in[i];
    return to;
}
/* Synthetic fixtures link without libc, like the board runtime. */
void *memset(void *to, int value, unsigned long length)
{
    volatile uint8_t *out = to;
    for (unsigned long i = 0; i < length; ++i) out[i] = (uint8_t)value;
    return to;
}
#ifdef MODWERK_MACHINE_DECLARATION_TEST
#include "machine_admission.h"
static uint8_t fixture_table[MACHINE_DECLARATION_BYTES];
static int fixture_read(void *ctx,uint32_t at,void *out,uint32_t n)
{
    (void)ctx;
    if(!((at>=0x10000000u && at<0x10100000u && n<=0x10100000u-at) ||
         (at>=0x40000400u && at<0x4ff00000u && n<=0x4ff00000u-at))) return 0;
    volatile const uint8_t *in=(volatile const uint8_t *)(uintptr_t)at;uint8_t *p=out;
    for(uint32_t i=0;i<n;i++) p[i]=in[i];
    return 1;
}
void fixture_clear_declarations(void)
{ for(unsigned i=0;i<MACHINE_DECLARATION_BYTES;i++) fixture_table[i]=modwerk_machine_declarations[i]; }
void fixture_review_package(const uint8_t *data,uint32_t length,uint32_t state,uint32_t parameters)
{
    uint8_t digest[32];mu_sha256(data,length,digest);
    unsigned i=0;
    for(;i<fixture_table[5];i++) {
        unsigned k=0;while(k<32 && fixture_table[16+44*i+k]==digest[k]) k++;
        if(k==32) break;
    }
    if(i>=MACHINE_DECLARATION_CAPACITY) return;
    uint8_t *r=fixture_table+16+44*i;
    for(unsigned k=0;k<32;k++) r[k]=digest[k];
    for(unsigned k=0;k<4;k++) r[32+k]=data[28+k];
    r[36]=data[81];r[37]=0;r[38]=state>>8;r[39]=state;r[40]=parameters>>8;r[41]=parameters;r[42]=r[43]=0;
    if(i==fixture_table[5]) fixture_table[5]++;
}
int modwerk_machine_metadata_admit(const struct runtime_dsp *from,struct runtime_dsp *to,
    const struct runtime_context *context,enum runtime_metadata_operation operation)
{
    (void)context;(void)operation;
    return machine_metadata_admission(fixture_table,from,to,fixture_read,0,
        *(volatile uint32_t *)(uintptr_t)0x46c82456u);
}
#else
int modwerk_machine_metadata_admit(const struct runtime_dsp *from, struct runtime_dsp *to,
    const struct runtime_context *context,enum runtime_metadata_operation operation)
{ (void)from; (void)to;(void)context;(void)operation;return RUNTIME_OK; }
#endif
uint32_t fixture_group_image(void)
{ const struct runtime_module *m=modwerk_runtime_module(0); return m?(uint32_t)(uintptr_t)m->dsp.image:0; }
