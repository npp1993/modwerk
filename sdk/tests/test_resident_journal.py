# SPDX-License-Identifier: GPL-3.0-or-later
"""Stock-free tests of the actual generated manager journal on the actual owned transport.

Only the frame clock read is substituted. Fixture flags, owners, journal
progress and catalogue handles are synthetic stand-ins for board facts: they
exercise source behaviour, never physical DSP timing, ACKs or qualification.
"""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / 'sdk/machines/octatrack/module-adapters'
ELEK = ROOT / 'sdk/machines/octatrack/elekloader'
RUNTIME = ADAPTER / 'resident-runtime'
sys.path.insert(0, str(ADAPTER))
sys.path.insert(0, str(ELEK))
import resident_driver
import resident_journal
import resident_placement
import zero_state
from host_flags import SANITIZE  # noqa: E402


FIXTURE = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
/* DL_NATIVE_TEST omits observer storage the base still names; storage only. */
static uint32_t auto_serial=0x80000000u;
static unsigned observed_valid;
static uint8_t last[16];
#include "manager.c"
int dl_sum_start(unsigned,unsigned,unsigned,uint32_t);
int dl_hook_reset_start(unsigned,unsigned,unsigned,unsigned,const uint32_t *);
struct dl_package dl_catalog[MODWERK_FX_IDS];
struct code dl_codes[2][MODWERK_FX_IDS];
const uint32_t dl_pmap16=0;
const fx_set dl_stub_at_boot={{0}},modwerk_fx_modules={{0,0xffffffffu}};
uint8_t dl_journal_test_live[16];
volatile uint32_t test_clock;
/* Synthetic board state. */
static unsigned flags[2],refuse[2],silent[2];
static struct runtime_journal_progress progress;
struct module { struct runtime_module m; uint8_t image[16]; uint32_t words[64],generation; int handle; };
static struct module modules[4]; /* 0 old A, 1 new A, 2 old B, 3 new B */
static const struct runtime_dsp empty;
int modwerk_stock_hook_export_idle(void) { return 1; }
int modwerk_saved_set_busy(void) { return 0; }
uint32_t modwerk_dsp_source_charge(unsigned c) { (void)c;return 0; }
int modwerk_dsp_buffer_permitted(unsigned c,unsigned k,unsigned b,unsigned id) { (void)c;(void)k;(void)b;(void)id;return 1; }
int modwerk_stock_hook_buffer_policy(unsigned c,unsigned id,struct mw_hook_buffer_claim *out) { (void)c;(void)id;(void)out;return 0; }
unsigned modwerk_dsp_flags(unsigned c) { return flags[c]; }
void dl_selection_tick(void) {}
void dl_show_message(const char *s,unsigned n) { (void)s;(void)n; }
uint32_t modwerk_machine_lock(void) { return 0; }
void modwerk_machine_unlock(uint32_t s) { (void)s; }
const struct runtime_module *modwerk_runtime_module(unsigned i) { return i<4 ? &modules[i].m : 0; }
int modwerk_runtime_owner_snapshot(const uint8_t *image,struct runtime_owner *o) {
    for(unsigned i=0;i<4;++i) if(image==modules[i].image && modules[i].generation) {
        memset(o,0,sizeof *o);o->generation=modules[i].generation;o->module=modules[i].m.id;return 1;
    }
    return 0;
}
void modwerk_runtime_journal_snapshot(struct runtime_journal_progress *p) { *p=progress; }
int modwerk_dsp_catalogue_handle(uint32_t module) {
    return module==modules[0].m.id ? modules[0].handle : module==modules[2].m.id ? modules[2].handle : -1;
}
struct packet { unsigned core,op,seq,id,init,proc; };
static struct packet sent[96];
static unsigned nsent;
static uint16_t seen[2];
static void observe(void) {
    for(unsigned c=0;c<2;++c) if(dl_tx[c][0]==DL_MAGIC && dl_tx[c][1]!=seen[c]) {
        seen[c]=dl_tx[c][1];assert(nsent<96);
        sent[nsent++]=(struct packet){c,dl_tx[c][2],dl_tx[c][1],dl_tx[c][4],dl_tx[c][5],dl_tx[c][7]};
    }
}
static void answer(void) {
    for(unsigned c=0;c<2;++c) if(dl_tx[c][0] && !silent[c]) flags[c]=((flags[c]^1u)&1u)|(refuse[c] ? 2u:0u);
    dl_frame();observe();
}
static void pump(void) { dl_frame();observe();answer(); }
static int drive(uint32_t g,unsigned limit) {
    int s=0;
    for(unsigned n=0;n<limit && !(s=mw_manager_journal_step(g));++n) pump();
    return s;
}
static void module(unsigned i,uint32_t id,uint32_t generation,unsigned count,unsigned init,unsigned proc,unsigned handle) {
    struct module *x=&modules[i];
    for(unsigned w=0;w<64;++w) x->words[w]=0x1000u*(i+1u)+w;
    x->m.id=id;x->generation=generation;x->handle=(int)handle;
    struct runtime_dsp *d=&x->m.dsp;
    d->words=x->words;d->count=count;d->init=(uint16_t)init;d->proc=(uint16_t)proc;d->id=(uint8_t)handle;
    d->slots=3;d->present=1;d->module=id;d->image=x->image;d->kind=RUNTIME_HARDWARE;d->cycles=100;
}
static struct runtime_journal_view row(unsigned i) {
    struct runtime_journal_view r;memset(&r,0,sizeof r);
    r.before.generation=modules[i].generation;r.before.module=modules[i].m.id;
    r.after.generation=modules[i+1].generation;r.after.module=modules[i+1].m.id;
    r.from=&modules[i].m.dsp;r.to=&modules[i+1].m.dsp;r.module=modules[i].m.id;return r;
}
static void place(unsigned c,unsigned p,unsigned offset,unsigned words,uint32_t generation) {
    allocator.live[c][p]=(struct dl_placement){(uint16_t)offset,(uint16_t)words,1};bound_generation[c][p]=generation;
}
static void setup(void) {
    module(0,0x1234,5,30,1,2,40);module(1,0x1234,9,49,3,4,40);
    module(2,0x9999,21,10,0,1,42);module(3,0x9999,22,20,2,5,42);
    initialized=1;dl_allocator_init(&allocator,dl_catalog,1936,1936,3120,3565);dl_buffers_init(&buffers,0);
    dl_catalog[40]=(struct dl_package){30,1,400,3,0,1,0};
    dl_codes[0][40]=dl_codes[1][40]=(struct code){modules[0].words,0,30,1,2,0};
    for(unsigned c=0;c<2;++c) place(c,40,0,30,5);
    place(0,41,30,50,0);
    progress.generation=7;progress.phase=RJ_PUBLISHING;
}
static const struct packet *find(unsigned c,unsigned op,unsigned nth) {
    for(unsigned i=0;i<nsent;++i) if(sent[i].core==c && sent[i].op==op && !nth--) return &sent[i];
    return 0;
}
static unsigned count(unsigned c,unsigned op) { unsigned n=0;for(unsigned i=0;i<nsent;++i) n+=sent[i].core==c && sent[i].op==op;return n; }
static void legacy_blocked(void) {
    struct dl_selection selection;memset(&selection,0,sizeof selection);
    uint8_t ids[16],sources[8]={0};memset(ids,40,sizeof ids);
    uint32_t word=1;struct dl_upload u={&word,0,1,0,64};struct dl_owned_job x;
    assert(!dl_command_start(0,DL_PROBE,0,0,0) && !dl_upload_start(1,&u) && !dl_sum_start(0,64,1,1) &&
           !dl_hook_reset_start(0,1,0,1,&word));
    assert(dl_selection_prepare(&selection,77)==DL_SELECT_UNAVAILABLE);
    assert(dl_publication_prepare(ids,sources,78)==DL_SELECT_UNAVAILABLE);
    assert(!dl_move(0,40,500) && !dl_publication_ready(ids) && !dl_publication_idle() && !dl_hook_buffer_ranges_idle(1));
    assert(!dl_owned_command_reserve(0,99,DL_PROBE,0,0,0,&x)); /* another generation cannot use the lease */
    dl_residency_tick();assert(!phase && !waiting && !queued_token);
}
static void zero_receipt(const struct mw_manager_core_receipt *r) {
    static const struct mw_manager_core_receipt none;assert(!memcmp(r,&none,sizeof none));
}
static void check(const struct mw_manager_core_receipt *r,unsigned c,unsigned code,unsigned words,const struct packet *first,const struct packet *last) {
    assert(r->job_ticket && r->job_generation==progress.generation && r->released==1);
    assert(r->pool_base==4096 && r->pool_words==2000 && r->code_offset==code && r->code_words==words);
    assert(first && last && first->core==c && last->core==c);
    assert(r->first_sequence==first->seq && r->last_sequence==last->seq && r->acknowledged_sequence==last->seq);
}
int main(int argc,char **argv) {
    assert(argc==2);
    unsigned mode=(unsigned)strtoul(argv[1],0,10);
    struct runtime_journal_view r;struct mw_manager_core_receipt out[2];uint8_t required=0xff;
    setup();r=row(0);
    if(mode==0) { /* replace on both cores, forward then exact reverse */
        assert(mw_manager_journal_stage(7,&r,0)==0);
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_freeze(7)==1 && mw_manager_journal_freeze(8)==0);
        dl_request_probe++;legacy_blocked();pump();assert(!nsent); /* a queued probe waits under the lease */
        assert(mw_manager_journal_stage(7,&r,1)==0);
        assert(mw_manager_journal_stage(7,&r,0)==1 && mw_manager_journal_stage(7,&r,0)==1);
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==0);
        assert(drive(7,40)==1);
        /* New code goes to the lowest hole clear of live code: 80 on core 0 (0..30, 30..80 live), 30 on core 1. */
        for(unsigned c=0;c<2;++c) {
            unsigned at=64u+(c ? 30u:80u);
            const struct packet *w=find(c,DL_WRITE,0),*b=find(c,DL_BIND,0);
            assert(count(c,DL_WRITE)==3 && count(c,DL_BIND)==1 && w->init==at && b->id==40 && b->init==at+3 && b->proc==at+4);
            assert(b->seq==w->seq+3u && b->seq>find(c,DL_WRITE,2)->seq);
        }
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==1 && required==3);
        for(unsigned c=0;c<2;++c) check(&out[c],c,4096u+64u+(c ? 30u:80u),49,find(c,DL_WRITE,0),find(c,DL_BIND,0));
        for(unsigned c=0;c<2;++c) assert(allocator.live[c][40].present && !allocator.live[c][40].offset && bound_generation[c][40]==5);
        struct runtime_journal_view stale=r;stale.after.generation=10;
        assert(mw_manager_journal_receipt(7,&stale,0,&required,out)==0);
        assert(mw_manager_journal_release(7)==0);
        progress.phase=RJ_TRIAL;assert(mw_manager_journal_release(7)==0); /* rebound: only an exact reverse releases */
        progress.phase=RJ_ROLLBACK;nsent=0;
        assert(mw_manager_journal_stage(7,&r,1)==1 && drive(7,20)==1);
        for(unsigned c=0;c<2;++c) {
            const struct packet *b=find(c,DL_BIND,0);
            assert(nsent==2 && b->id==40 && b->init==64+1 && b->proc==64+2);
        }
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==0);
        assert(mw_manager_journal_receipt(7,&r,1,&required,out)==1 && required==3);
        for(unsigned c=0;c<2;++c) check(&out[c],c,4096u+64u,30,find(c,DL_BIND,0),find(c,DL_BIND,0));
        assert(mw_manager_journal_release(7)==0);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==1 && mw_manager_journal_release(7)==0);
        nsent=0;dl_frame();observe();assert(find(0,DL_PROBE,0) && find(1,DL_PROBE,0));answer();
        assert(dl_command_start(0,DL_PROBE,0,0,0));pump();assert(dl_job_status(0)==1);dl_job_release(0);
        progress.generation=8;progress.phase=RJ_PUBLISHING;assert(mw_manager_journal_freeze(8)==1);
    } else if(mode==1) { /* removal placed on core 1 only: BYPASS, then BIND back */
        allocator.live[0][40].present=0;r.to=&empty;r.after.generation=0;r.after.module=0;
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==1 && drive(7,20)==1);
        const struct packet *b=find(1,DL_BYPASS,0);
        assert(nsent==1 && b && b->id==40);
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==1 && required==2);
        zero_receipt(&out[0]);check(&out[1],1,0,0,b,b);
        progress.phase=RJ_ROLLBACK;nsent=0;
        assert(mw_manager_journal_stage(7,&r,1)==1 && drive(7,20)==1);
        b=find(1,DL_BIND,0);assert(nsent==1 && b->id==40 && b->init==65 && b->proc==66);
        assert(mw_manager_journal_receipt(7,&r,1,&required,out)==1 && required==2);
        zero_receipt(&out[0]);check(&out[1],1,4096u+64u,30,b,b);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==1);
    } else if(mode==2) { /* every refusal leaves lease, rows, reservations and wire unchanged */
        progress.generation=8;assert(mw_manager_journal_freeze(7)==0);
        progress.generation=7;progress.phase=RJ_VERIFIED;assert(mw_manager_journal_freeze(7)==0);
        progress.phase=RJ_PUBLISHING;
        assert(dl_command_start(0,DL_PROBE,0,0,0) && mw_manager_journal_freeze(7)==0);pump();
        assert(dl_job_status(0)==1);dl_job_release(0);
        dl_request_stage++;assert(mw_manager_journal_freeze(7)==0);pump();
        phase=1;assert(mw_manager_journal_freeze(7)==0);phase=0;
        dl_residency_enabled=0;assert(mw_manager_journal_freeze(7)==0);dl_residency_enabled=1;
        nsent=0;assert(mw_manager_journal_freeze(7)==1);
        struct module *a=&modules[0],*b=&modules[1];
        b->m.dsp.buffer=100;assert(mw_manager_journal_stage(7,&r,0)==0);b->m.dsp.buffer=0;
        b->m.dsp.flags=RUNTIME_GROUP_METADATA;assert(mw_manager_journal_stage(7,&r,0)==0);b->m.dsp.flags=0;
        a->m.dsp.foreign_roots=1;assert(mw_manager_journal_stage(7,&r,0)==0);a->m.dsp.foreign_roots=0;
        r.before.generation=4;assert(mw_manager_journal_stage(7,&r,0)==0);r=row(0); /* not the bound predecessor */
        r.after.generation=5;assert(mw_manager_journal_stage(7,&r,0)==0);r=row(0);
        bound_generation[1][40]=0;assert(mw_manager_journal_stage(7,&r,0)==0);bound_generation[1][40]=5;
        stubbed[0]=fx_with(stubbed[0],40);assert(mw_manager_journal_stage(7,&r,0)==0);stubbed[0]=fx_without(stubbed[0],40);
        allocator.live[0][40].words=31;assert(mw_manager_journal_stage(7,&r,0)==0);allocator.live[0][40].words=30;
        a->handle=41;assert(mw_manager_journal_stage(7,&r,0)==0);a->handle=-2;assert(mw_manager_journal_stage(7,&r,0)==0);a->handle=40;
        b->m.dsp.count=1900;assert(mw_manager_journal_stage(7,&r,0)==0);b->m.dsp.count=49; /* no contiguous hole */
        r.from=&empty;r.before.generation=0;assert(mw_manager_journal_stage(7,&r,0)==0);r=row(0); /* install over placed code */
        b->m.dsp.id=5;r.from=&empty;r.before.generation=0;assert(mw_manager_journal_stage(7,&r,0)==0);r=row(0);b->m.dsp.id=40;
        assert(!mw_manager_journal_stage(8,&r,0) && !mw_manager_journal_stage(7,&r,1) && !mw_manager_journal_stage(7,0,0) && !mw_manager_journal_stage(7,&r,2));
        assert(!journal_count && !nsent && !journal_lane[0].job.ticket && !journal_lane[1].job.ticket && !journal_quarantined);
        assert(mw_manager_journal_step(7)==-1 && !journal_quarantined); /* nothing staged */
        assert(mw_manager_journal_stage(7,&r,0)==1);  /* the refusals left a usable journal */
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==1 && !nsent); /* staged, never rebound */
    } else if(mode==3 || mode==4) { /* timeout or HF3 refusal: unknown, quarantined, never retried */
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==1);
        if(mode==3) { assert(!mw_manager_journal_step(7));silent[0]=1;for(unsigned i=0;i<70;++i) pump(); }
        else for(unsigned i=0;i<40 && !find(0,DL_BIND,0);++i) { assert(!mw_manager_journal_step(7));dl_frame();observe(); if(find(0,DL_BIND,0)) refuse[0]=1;answer(); }
        assert(mw_manager_journal_step(7)==-1 && journal_quarantined);
        assert(mw_manager_journal_stage(7,&r,0)==-1 && mw_manager_journal_step(7)==-1 && mw_manager_journal_freeze(7)==-1);
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==-1 && mw_manager_journal_release(7)==-1);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==-1);
        uint8_t ids[16]={0};struct dl_selection selection;memset(&selection,0,sizeof selection);
        assert(!dl_command_start(1,DL_PROBE,0,0,0) && dl_selection_prepare(&selection,5)==DL_SELECT_UNAVAILABLE && !dl_publication_ready(ids));
    } else if(mode==5) { /* a slot running the id defers its rebind; one found running it after is unknown */
        dl_journal_test_live[0]=40; /* track 1 FX1: core 1 */
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==1 && drive(7,40)==0);
        assert(count(0,DL_BIND)==1 && count(1,DL_WRITE)==3 && !count(1,DL_BIND) && journal_lane[1].job.ticket);
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==0);
        dl_journal_test_live[0]=0;assert(drive(7,20)==1 && count(1,DL_BIND)==1);
        progress.phase=RJ_ROLLBACK;assert(mw_manager_journal_stage(7,&r,1)==1 && !mw_manager_journal_step(7));
        dl_journal_test_live[8]=40;pump();
        assert(mw_manager_journal_step(7)==-1 && journal_quarantined);
    } else if(mode==6) { /* reverse of a partly rebound row: only the rebound core goes back */
        dl_journal_test_live[12]=40; /* track 5 FX2: core 0 */
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==1 && drive(7,40)==0);
        assert(count(1,DL_BIND)==1 && !count(0,DL_BIND) && journal_lane[0].job.ticket);
        progress.phase=RJ_ROLLBACK;nsent=0;
        assert(mw_manager_journal_stage(7,&r,1)==1 && !journal_lane[0].job.ticket && drive(7,20)==1);
        assert(nsent==1 && find(1,DL_BIND,0)->init==65);
        assert(mw_manager_journal_receipt(7,&r,1,&required,out)==1 && required==2);
        zero_receipt(&out[0]);check(&out[1],1,4096u+64u,30,find(1,DL_BIND,0),find(1,DL_BIND,0));
        dl_journal_test_live[12]=0;progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==1 && nsent==1);
    } else if(mode==7) { /* positively checked no-job transitions */
        struct module *cf=&modules[2],*fresh=&modules[3];
        struct runtime_journal_view a,b,c;memset(&a,0,sizeof a);
        a.module=0x55;a.before.generation=11;a.after.generation=12;a.from=&empty;a.to=&empty;
        cf->m.id=0x66;cf->handle=-1;b=row(2);b.module=0x66;b.from=&empty;b.before.generation=0;
        fresh->m.dsp.id=43;fresh->m.id=0x66;fresh->m.dsp.module=0x66;
        c=a;c.module=0x77;
        assert(mw_manager_journal_freeze(7)==1);
        assert(mw_manager_journal_stage(7,&a,0)==1 && mw_manager_journal_step(7)==1);
        assert(mw_manager_journal_receipt(7,&a,0,&required,out)==1 && !required);zero_receipt(&out[0]);zero_receipt(&out[1]);
        assert(mw_manager_journal_stage(7,&b,0)==1 && mw_manager_journal_step(7)==1);
        assert(mw_manager_journal_receipt(7,&b,0,&required,out)==1 && !required);
        progress.phase=RJ_ROLLBACK;
        assert(mw_manager_journal_stage(7,&b,1)==1 && mw_manager_journal_step(7)==1);
        assert(mw_manager_journal_receipt(7,&b,1,&required,out)==1 && !required);
        assert(mw_manager_journal_stage(7,&c,1)==1 && mw_manager_journal_receipt(7,&c,1,&required,out)==1 && !required);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==1 && !nsent);
    } else if(mode==8) { /* a legacy bind records the generation it binds; an unknown one refuses */
        allocator.live[1][40].present=0;bound_generation[0][40]=0;modules[0].generation=0;
        assert(dl_move(0,40,200)==1);
        for(unsigned n=0;n<400 && phase;++n) { dl_residency_tick();pump(); }
        assert(!phase && allocator.live[0][40].offset==200 && !bound_generation[0][40]);
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==0);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(7)==1);
        modules[0].generation=5;nsent=0;assert(dl_move(0,40,300)==1);
        for(unsigned n=0;n<400 && phase;++n) { dl_residency_tick();pump(); }
        const struct packet *b=find(0,DL_BIND,0);
        assert(!phase && allocator.live[0][40].offset==300 && bound_generation[0][40]==5 && b && b->init==64+300+1);
        progress.generation=8;progress.phase=RJ_PUBLISHING;nsent=0;
        assert(mw_manager_journal_freeze(8)==1 && mw_manager_journal_stage(8,&r,0)==1 && drive(8,40)==1);
        assert(count(0,DL_BIND)==1 && !count(1,DL_WRITE) && find(0,DL_WRITE,0)->init==64+80);
    } else if(mode==9) { /* rows one at a time; a later row's hole avoids earlier rows' new code */
        place(0,42,200,10,21);
        struct runtime_journal_view b=row(2);
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==1);
        assert(mw_manager_journal_stage(7,&b,0)==0 && drive(7,40)==1);
        nsent=0;assert(mw_manager_journal_stage(7,&b,0)==1 && drive(7,40)==1);
        const struct packet *bind=find(0,DL_BIND,0);
        assert(nsent==2 && find(0,DL_WRITE,0)->init==64+129 && bind->id==42 && bind->init==64+129+2 && bind->proc==64+129+5);
        assert(mw_manager_journal_receipt(7,&b,0,&required,out)==1 && required==1);
        assert(mw_manager_journal_receipt(7,&r,0,&required,out)==0); /* only the active row has a receipt */
    } else if(mode==10) { /* Keep: an unplaced fresh install finalizes with nothing moved or freed, then releases */
        struct runtime_journal_view f=row(2),stale;f.from=&empty;f.before.generation=0;f.before.module=0;
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&f,0)==1 && mw_manager_journal_step(7)==1);
        assert(mw_manager_journal_receipt(7,&f,0,&required,out)==1 && !required && !nsent);
        zero_receipt(&out[0]);zero_receipt(&out[1]);
        assert(!mw_manager_journal_accept(7,&f,1)); /* still publishing */
        progress.phase=RJ_TRIAL;stale=f;stale.after.generation=23;
        assert(!mw_manager_journal_accept(8,&f,1) && !mw_manager_journal_accept(7,&f,2) && !mw_manager_journal_accept(7,&f,0) &&
               !mw_manager_journal_accept(7,0,1) && !mw_manager_journal_accept(7,&stale,1) && !journal_accepted);
        legacy_blocked();
        assert(mw_manager_journal_accept(7,&f,1)==1 && journal_accepted==7);
        assert(mw_manager_journal_release(7)==0); /* not idle yet: the lease stays */
        observed_valid=1;memset(last,0,sizeof last);progress.phase=RJ_IDLE;
        assert(mw_manager_journal_release(7)==1 && !journal_generation && !journal_accepted && !nsent);
        assert(!observed_valid && last[0]==255 && last[15]==255); /* nudged: tracks naming the kept install load it */
        for(unsigned c=0;c<2;++c) assert(!allocator.live[c][42].present && !bound_generation[c][42] &&
                                         allocator.live[c][40].present && bound_generation[c][40]==5);
        assert(dl_command_start(0,DL_PROBE,0,0,0));pump();assert(dl_job_status(0)==1);dl_job_release(0); /* legacy open */
        /* A replacement retires its predecessor, even with no job: refused with nothing changed. */
        struct runtime_journal_view a;memset(&a,0,sizeof a);a.module=0x55;a.before.generation=11;a.after.generation=12;a.from=a.to=&empty;
        progress.generation=8;progress.phase=RJ_PUBLISHING;
        assert(mw_manager_journal_freeze(8)==1 && mw_manager_journal_stage(8,&a,0)==1 && mw_manager_journal_step(8)==1);
        progress.phase=RJ_TRIAL;assert(!mw_manager_journal_accept(8,&a,1) && !journal_accepted);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(8)==1);
        progress.generation=9;progress.phase=RJ_PUBLISHING;nsent=0;
        assert(mw_manager_journal_freeze(9)==1 && mw_manager_journal_stage(9,&r,0)==1 && drive(9,40)==1);
        progress.phase=RJ_TRIAL;assert(!mw_manager_journal_accept(9,&r,1) && !journal_accepted && journal_count==1);
        progress.phase=RJ_IDLE;assert(mw_manager_journal_release(9)==0 && journal_generation==9); /* rebound: only its reverse releases */
        journal_quarantined=1;progress.phase=RJ_TRIAL;assert(mw_manager_journal_accept(9,&r,1)==-1); /* unknown */
    } else if(mode==11 || mode==12) { /* a move's BIND (11) or upload (12) refused: the rollback rebinds the old copy, which
                                       * keeps its generation */
        allocator.live[1][40].present=0;binding_generation=99; /* whatever a bind before left there */
        assert(dl_move(0,40,300)==1);
        for(unsigned n=0;n<400 && phase;++n) {
            dl_residency_tick();dl_frame();observe();
            refuse[0]=mode==11 ? find(0,DL_BIND,0) && !find(0,DL_BIND,1) : !find(0,DL_BIND,0); /* the way back is not */
            answer();
        }
        const struct packet *to=mode==11 ? find(0,DL_BIND,0) : 0,*back=find(0,DL_BIND,mode==11);
        assert(!phase && back && back->init==64+1 && back->proc==64+2 && !count(0,DL_BYPASS) && count(0,DL_BIND)==2u-(mode==12));
        assert(mode==12 ? count(0,DL_WRITE)==1 : to->init==64+300+1);
        assert(allocator.live[0][40].offset==0 && bound_generation[0][40]==5 && !fx_in(stubbed[0],40));
        assert(mw_manager_journal_freeze(7)==1 && mw_manager_journal_stage(7,&r,0)==1); /* still its bound predecessor */
    } else assert(0);
    return 0;
}
'''


def generated():
    """The build's exact manager/transport pipeline for --resident-stock-hooks, without saved-set wiring."""
    spec = importlib.util.spec_from_file_location('resident_journal_core_fixture', ELEK / 'build_core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    texts = {}
    for name in core.DYNLOAD_SOURCES:
        text = reference = (core.DYNLOAD / name).read_text()
        for old, new in core.DSP_EDITS.get(name, ()) + core.WIDTH_EDITS.get(name, ()):
            if text.count(old) != 1:
                raise AssertionError('Changed base input seam: ' + name)
            text = text.replace(old, new)
        if name == 'buffers.c':
            text = resident_placement.buffers(text)
        elif name == 'manager.c':
            text = resident_journal.manager(resident_placement.manager(text))
        elif name == 'transfer.c':
            text = resident_driver.transport(text)
        elif name == 'transfer.h':
            text = resident_driver.transport_header(text)
        if name in zero_state.UNITS:
            text = zero_state.unit(name, text, reference)
        texts[name] = text
    return texts


class ResidentJournal(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'host C compiler unavailable')
    def test_actual_manager_journal_on_actual_owned_transport(self):
        texts = generated()
        clock = '*(volatile uint32_t *)0xfc07c00cu'
        self.assertEqual(texts['transfer.c'].count(clock), 1)
        texts['transfer.c'] = '#include <stdint.h>\nextern volatile uint32_t test_clock;\n' + texts['transfer.c'].replace(clock, 'test_clock')
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for name, text in texts.items():
                (work / name).write_text(text)
            (work / 'fixture.c').write_text(FIXTURE)
            executable = work / 'journal'
            flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', *SANITIZE, '-fno-omit-frame-pointer',
                     '-DDL_NATIVE_TEST', '-DMODWERK_FX_IDS=64', '-DMODWERK_DSP_ALLOWANCE0=3120', '-DMODWERK_DSP_ALLOWANCE1=3565',
                     '-DMODWERK_DSP_TABLE0=4096', '-DMODWERK_DSP_TABLE1=4096', '-DMODWERK_DSP_WORDS0=2000', '-DMODWERK_DSP_WORDS1=2000']
            includes = ['-I' + str(p) for p in (work, ELEK, RUNTIME, ROOT / 'sdk/runtime/loader', ROOT / 'sdk/runtime/upload')]
            sources = [work / 'fixture.c', work / 'transfer.c', work / 'allocator.c', work / 'buffers.c',
                       RUNTIME / 'stock_hooks.c', RUNTIME / 'stock_hook_resources.c']
            result = subprocess.run(['cc', *flags, *includes, *map(str, sources), '-o', str(executable)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for mode in range(13):
                with self.subTest(mode=mode):
                    result = subprocess.run([str(executable), str(mode)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('m68k-elf-gcc'), 'ColdFire compiler unavailable')
    def test_actual_journal_manager_and_transport_compile_for_mcf54455_at_o2(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for name, text in generated().items():
                (work / name).write_text(text)
            flags = ['-mcpu=54455', '-O2', '-std=c99', '-ffreestanding', '-fno-builtin', '-fno-common', '-Wall', '-Wextra',
                     '-Werror', '-DMODWERK_FX_IDS=128u', '-DRUNTIME_MODULES=128u', '-DMODWERK_RESIDENT_STOCK_HOOKS',
                     '-DMODWERK_DSP_ALLOWANCE0=3120', '-DMODWERK_DSP_ALLOWANCE1=3565']
            flags += ['-DMODWERK_DSP_%s%d=4096' % (name, c) for name in ('TABLE', 'WORDS') for c in (0, 1)]
            includes = ['-I' + str(p) for p in (work, ELEK, RUNTIME, ROOT / 'sdk/runtime/loader', ROOT / 'sdk/runtime/upload')]
            for name in ('manager.c', 'transfer.c'):
                result = subprocess.run(['m68k-elf-gcc', *flags, *includes, '-c', str(work / name), '-o', str(work / (name + '.o'))],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_seams_refuse_drift_and_keep_upstream_exact(self):
        texts = generated()
        manager = texts['manager.c']
        self.assertIn('int mw_manager_journal_freeze(uint32_t g)', manager)
        self.assertIn('if(journal_generation || !modwerk_stock_hook_export_idle()', manager)
        self.assertEqual(manager.count('if(journal_generation || !modwerk_stock_hook_export_idle()'), 3)
        self.assertIn('static struct dl_allocator allocator;', manager)  # zero_state still applies afterwards
        self.assertNotIn('__attribute__((optimize', manager)        # no -Os on manager code
        spec = importlib.util.spec_from_file_location('resident_journal_core_fixture2', ELEK / 'build_core.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        original = (core.DYNLOAD / 'manager.c').read_text()
        with self.assertRaisesRegex(ValueError, 'manager journal seam changed'):
            resident_journal.manager(original)
        text = original
        for old, new in core.DSP_EDITS['manager.c'] + core.WIDTH_EDITS['manager.c']:
            text = text.replace(old, new)
        once = resident_journal.manager(resident_placement.manager(text))
        with self.assertRaisesRegex(ValueError, 'manager journal seam changed'):
            resident_journal.manager(once)
        self.assertEqual((core.DYNLOAD / 'manager.c').read_text(), original)


if __name__ == '__main__':
    unittest.main()
