/* SPDX-License-Identifier: MIT */
#include "machine_admission.h"
#include <assert.h>
#include <string.h>
/* Pure synthetic target memory: no firmware, no table-owner admission. */
static unsigned reads,retained,unknown,part_retained;
static int read_memory(void *ctx,uint32_t at,void *out,uint32_t n)
{
    (void)ctx;reads++;memset(out,0,n);
    if(unknown) return 0;
    if(at==0x46c7d8deu && retained) {
        uint8_t *p=out;p[0]=0x47;p[1]=8;p[2]=0;p[3]=20;
    }
    if(part_retained && at==0x40170f60u+0x22u) *(uint8_t *)out=1;
    if(part_retained && at==0x40170f60u+0x3cu) memcpy(out,"FM\1",3);
    return 1;
}
static void put16(uint8_t *p,unsigned v) { p[0]=v>>8;p[1]=v; }
static void put32(uint8_t *p,uint32_t v) { put16(p,v>>16);put16(p+2,v); }
static void record(uint8_t *table,unsigned index,const struct runtime_dsp *d,unsigned mask,unsigned state,unsigned parameters)
{
    uint8_t *p=table+16+44*index;memcpy(p,d->package_sha256,32);put32(p+32,d->module);
    p[36]=mask;put16(p+38,state);put16(p+40,parameters);table[5]=index+1;
}
int main(void)
{
    uint8_t image[16]={'M','W','M','G',1,4,0,0},table[MACHINE_DECLARATION_BYTES];
    memcpy(table,modwerk_machine_declarations,sizeof table);
    struct runtime_dsp none={0},a={0},b={0};
    a.image=image;a.image_bytes=16;a.flags=4;a.present=1;a.module=123;a.layout=1;
    for(unsigned i=0;i<32;i++) a.package_sha256[i]=i+1;
    assert(machine_metadata_admission(table,&none,&none,0,0,0)==RUNTIME_OK);
    assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_MALFORMED);
    record(table,0,&a,4,1,1);
    assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_OK && reads==0);
    for(unsigned i=0;i<32;i++) { a.package_sha256[i]^=1;assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_MALFORMED);a.package_sha256[i]^=1; }
    for(unsigned i=0;i<sizeof table;i++) {
        uint8_t old=table[i];table[i]^=128;
        if(i<16 || i>=60 || i==53 || i==58 || i==59) assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_MALFORMED);
        table[i]=old;
    }
    b=a;b.package_sha256[0]=99;record(table,1,&b,4,2,1);
    assert(machine_metadata_admission(table,&a,&b,0,0,0)==RUNTIME_CONFLICT);
    record(table,1,&b,4,1,2);b.layout=2;
    assert(machine_metadata_admission(table,&a,&b,0,0,0)==RUNTIME_CONFLICT);
    record(table,1,&b,4,1,1);b.layout=1;
    /* Old relocated image must be a bounded target address. Use a separate
     * readable synthetic metadata mapping for lookup in the native fixture;
     * the host's ordinary 64-bit allocation must safely refuse retirement. */
    assert(machine_metadata_admission(table,&a,&b,read_memory,0,0x400e21e0u)==RUNTIME_IN_USE);
    memcpy(table+60,table+16,44);table[5]=2;
    assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_MALFORMED);
    memcpy(table,modwerk_machine_declarations,sizeof table);record(table,0,&a,4,1,1);
    for(unsigned at=0;at<16;at++) {
        uint8_t old=image[at];image[at]^=128;
        assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_MALFORMED);image[at]=old;
    }
    a.layout=0;assert(machine_metadata_admission(table,&none,&a,0,0,0)==RUNTIME_MALFORMED);
    return 0;
}
