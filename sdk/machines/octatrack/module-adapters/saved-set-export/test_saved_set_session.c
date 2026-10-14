/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "saved_set_session.h"
#include "upload.h"
static struct msx_session session;
static uint8_t out[MSX_CHUNK_BYTES], setup[8];
static unsigned reads, hashes, interrupt_at;
static int gate = 1;
static uint32_t be32(const uint8_t *p) { return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3]; }
static void shape(unsigned request, unsigned value, unsigned bytes)
{
    uint8_t s[8] = {0xc1,(uint8_t)request,(uint8_t)value,(uint8_t)(value>>8),1,0,(uint8_t)bytes,(uint8_t)(bytes>>8)};
    memcpy(setup,s,8);
}
static unsigned request(unsigned req,unsigned value,unsigned n,int allowed)
{
    shape(req,value,n); return msx_session_request(&session,setup,out,1,allowed);
}
static void empty_payload(void) { for(unsigned i=12;i<MSX_METADATA_BYTES;++i) assert(!out[i]); }
static void interrupt(void)
{
    unsigned token=session.file.token;
    assert(msx_session_reading(&session));
    if(interrupt_at==3) {
        for(unsigned i=0;i<MSX_TIMEOUT_TICKS;++i) msx_session_tick(&session);
    } else if(interrupt_at==4) msx_session_reset(&session);
    else assert(request(33,token,80,1)==80);
    assert(session.file.status==MSX_IDLE && msx_session_active(&session));
    assert(!msx_session_reading(&session));
    assert(request(31,2,80,1)==80 && out[5]==MSX_BUSY && be32(out+8)==token);
    empty_payload(); assert(session.file.token==token && session.file.status==MSX_IDLE);
}
static int safe(void) { return gate && msx_session_reading(&session); }
static enum msx_status reader(uint32_t slot,uint8_t *bytes,uint32_t capacity,uint32_t *length)
{
    assert(msx_session_active(&session) && msx_session_reading(&session));
    assert(slot<2 && capacity==MSX_CAPACITY); ++reads;
    for(unsigned i=0;i<500;++i) bytes[i]=(uint8_t)i;
    memcpy(bytes,"MWST",4); *length=500;
    if(interrupt_at && interrupt_at!=2) interrupt();
    return MSX_READY;
}
static void hash(const uint8_t *bytes,uint32_t n,uint8_t digest[32])
{
    ++hashes; mu_sha256(bytes,n,digest);
    if(interrupt_at==2) interrupt();
}
static void service(void) { msx_session_service(&session,safe,reader,hash); }
int main(void)
{
    assert(request(31,0,80,1)==80 && out[5]==MSX_IDLE && be32(out+8)==0); empty_payload();
    for(unsigned byte=0;byte<8;++byte) {
        shape(31,1,80); setup[byte]^=0x80;
        assert(!msx_session_request(&session,setup,out,1,1));
        assert(!msx_session_active(&session) && !session.file.token);
    }
    assert(!request(31,3,80,1)); assert(!request(32,0,480,1)); assert(!request(33,0,80,1));
    assert(request(31,1,80,0)==80 && out[5]==MSX_BUSY && !be32(out+8)); empty_payload();
    assert(request(31,1,80,1)==80 && out[5]==MSX_PENDING && be32(out+8)==1 && out[6]==0);
    assert(msx_session_active(&session) && !reads && !hashes);
    assert(request(31,2,80,1)==80 && out[5]==MSX_BUSY && be32(out+8)==1 && out[6]==0); empty_payload();
    gate=0; service(); assert(!reads && !hashes && session.file.status==MSX_UNSAFE);
    assert(request(31,0,80,1)==80 && out[5]==MSX_UNSAFE); empty_payload();
    assert(!request(33,2,80,1) && msx_session_active(&session));
    assert(request(33,1,80,1)==80 && out[5]==MSX_IDLE && be32(out+8)==1); empty_payload();
    assert(!msx_session_active(&session));
    gate=1;
    assert(request(31,2,80,1)==80 && out[5]==MSX_PENDING && be32(out+8)==2 && out[6]==1);
    service(); assert(reads==1 && hashes==1 && session.file.status==MSX_READY);
    uint8_t digest[32]; mu_sha256(session.file.snapshot,500,digest);
    assert(request(31,0,80,1)==80 && be32(out+12)==500 && !memcmp(out+16,digest,32));
    assert(request(32,0,480,1)==480 && !memcmp(out,"MWSC",4) && be32(out+8)==2 && be32(out+12)==0 && be32(out+20)==448);
    assert(!memcmp(out+32,session.file.snapshot,448));
    assert(request(32,1,480,1)==480 && be32(out+12)==448 && be32(out+16)==500 && be32(out+20)==52);
    assert(!memcmp(out+32,session.file.snapshot+448,52));
    for(unsigned i=84;i<480;++i) assert(!out[i]);
    session.quiet=599; assert(!request(32,2,480,1) && session.quiet==599);
    assert(request(31,0,80,1)==80 && session.quiet==0);
    for(unsigned i=0;i<599;++i) msx_session_tick(&session);
    assert(msx_session_active(&session)); msx_session_tick(&session);
    assert(!msx_session_active(&session) && session.file.token==2);
    for(interrupt_at=1;interrupt_at<=4;++interrupt_at) {
        assert(request(31,1,80,1)==80 && out[5]==MSX_PENDING);
        service(); assert(!session.running && session.file.status==MSX_IDLE && !session.file.length);
        assert(!msx_session_active(&session));
    }
    session.file.token=65535; assert(request(31,1,80,1)==80 && out[5]==MSX_BUSY && be32(out+8)==65535);
    empty_payload(); assert(!msx_session_active(&session));
    puts("fixed request shapes, no ISR I/O, interrupted freeze and expiry passed"); return 0;
}
