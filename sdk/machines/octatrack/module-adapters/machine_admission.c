/* SPDX-License-Identifier: MIT */
#include "machine_admission.h"
#include "machine_parts.h"
#include <stddef.h>
static uint32_t be16(const uint8_t *p) { return (uint32_t)p[0]<<8 | p[1]; }
static uint32_t be32(const uint8_t *p) { return be16(p)<<16 | be16(p+2); }
static int equal(const uint8_t *a,const uint8_t *b,unsigned n)
{ for(unsigned i=0;i<n;i++) if(a[i]!=b[i]) return 0;return 1; }
static int nonzero(const uint8_t *p,unsigned n)
{ for(unsigned i=0;i<n;i++) if(p[i]) return 1;return 0; }
/* Validate the entire trusted table, including unused storage, before lookup.
 * Duplicate package identities could otherwise hide incompatible revisions. */
static int table_valid(const uint8_t *table)
{
    if(!table || !equal(table,(const uint8_t *)"MWMD",4) || table[4]!=MACHINE_DECLARATION_REVISION ||
       table[5]>MACHINE_DECLARATION_CAPACITY || table[6]!=MACHINE_DECLARATION_CAPACITY || nonzero(table+7,9)) return 0;
    for(unsigned i=0;i<MACHINE_DECLARATION_CAPACITY;i++) {
        const uint8_t *r=table+MACHINE_DECLARATION_HEADER+i*MACHINE_DECLARATION_RECORD;
        if(i>=table[5]) { if(nonzero(r,MACHINE_DECLARATION_RECORD)) return 0;continue; }
        if(!nonzero(r,32) || !be32(r+32) || !r[36] || (r[36]&~7u) || (r[37]&~(MACHINE_OPTIONAL_QUANTIZER|MACHINE_ANALOG_BD)) || ((r[36]&4u)&&(r[37]&MACHINE_OPTIONAL_QUANTIZER)) ||
           (r[37] && be32(r+32)!=0xdb769930u) || !be16(r+38) || !be16(r+40) || be16(r+42)) return 0;
        for(unsigned j=0;j<i;j++) if(equal(r,table+MACHINE_DECLARATION_HEADER+j*MACHINE_DECLARATION_RECORD,32)) return 0;
    }
    return 1;
}
static const uint8_t *declared(const uint8_t *table,const struct runtime_dsp *d)
{
    if(!d->present || d->flags!=RUNTIME_GROUP_METADATA || d->count || !d->image ||
       d->image_bytes<16u || d->image_bytes>RUNTIME_IMAGE_BYTES || !d->layout ||
       !equal(d->image,(const uint8_t *)"MWMG",4) || d->image[4]!=1 ||
       !d->image[5] || (d->image[5]&~7u) || nonzero(d->image+6,10)) return 0;
    for(unsigned i=0;i<table[5];i++) {
        const uint8_t *r=table+MACHINE_DECLARATION_HEADER+i*MACHINE_DECLARATION_RECORD;
        if(equal(r,d->package_sha256,32) && be32(r+32)==d->module && r[36]==d->image[5] && be16(r+40)==d->layout) return r;
    }
    return 0;
}
int machine_metadata_optional_quantizer(const uint8_t table[MACHINE_DECLARATION_BYTES],const struct runtime_dsp *d)
{
    if(!d) return -1;
    if(!d->present || !(d->flags&RUNTIME_GROUP_METADATA)) return 0;
    if(!table_valid(table)) return -1;
    const uint8_t *r=declared(table,d);
    return r?(int)(r[37]&MACHINE_OPTIONAL_QUANTIZER):-1;
}
int machine_metadata_analog_bd(const uint8_t table[MACHINE_DECLARATION_BYTES],const struct runtime_dsp *d)
{
    if(!d) return -1;
    if(!d->present || !(d->flags&RUNTIME_GROUP_METADATA)) return 0;
    if(!table_valid(table)) return -1;
    const uint8_t *r=declared(table,d);
    return r?(int)(r[37]&MACHINE_ANALOG_BD):-1;
}
struct part_reader { machine_memory_read read;void *context; };
static int part_read(void *opaque,uint32_t at,uint8_t *out,unsigned n)
{ struct part_reader *r=opaque;return r->read(r->context,at,out,n); }
int machine_metadata_admission(const uint8_t table[MACHINE_DECLARATION_BYTES],const struct runtime_dsp *from,const struct runtime_dsp *to,
    machine_memory_read read,void *context,uint32_t bank)
{
    if(!from || !to) return RUNTIME_MALFORMED;
    unsigned old_group=from->flags&RUNTIME_GROUP_METADATA,new_group=to->flags&RUNTIME_GROUP_METADATA;
    if(!old_group && !new_group) return RUNTIME_OK;
    if(!table_valid(table)) return RUNTIME_MALFORMED;
    const uint8_t *old=old_group?declared(table,from):0,*next=new_group?declared(table,to):0;
    if((old_group&&!old) || (new_group&&!next) || (old_group&&to->present&&!new_group) ||
       (new_group&&from->present&&!old_group)) return RUNTIME_MALFORMED;
    /* Schema/trusted participation is not production controller authority.
     * Both directions remain closed until actual source/encoded association,
     * owned DSP generation ACKs and distinct AB Part/UI retirement are bound. */
    if((old && (old[37]&MACHINE_ANALOG_BD)) || (next && (next[37]&MACHINE_ANALOG_BD))) return RUNTIME_CONFLICT;
    if(old && next) {
        if(from->module!=to->module) return RUNTIME_CONFLICT;
        /* Even a different mask may preserve a participant's stored values.
         * Equality of membership is never a state-layout declaration. */
        if((old[36]&next[36]) && (be16(old+38)!=be16(next+38) || be16(old+40)!=be16(next+40))) return RUNTIME_CONFLICT;
    }
    if(old) {
        uintptr_t lo=(uintptr_t)from->image;
        if(!read || lo>UINT32_MAX || from->image_bytes>UINT32_MAX-(uint32_t)lo ||
           machine_ui_lifetime(read,context,(uint32_t)lo,(uint32_t)lo+from->image_bytes)!=MACHINE_CLEAR) return RUNTIME_IN_USE;
        struct part_reader reader={read,context};
        unsigned dropped=old[36]&~(next?next[36]:0u);
        if(machine_part_lifetime(part_read,&reader,bank,dropped)!=MACHINE_PART_CLEAR) return RUNTIME_IN_USE;
    }
    return RUNTIME_OK;
}
