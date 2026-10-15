# SPDX-License-Identifier: GPL-3.0-or-later
"""Private manager journal: one runtime journal generation's owned P jobs.

Transforms the generated manager.c (after resident_placement.manager, before
zero_state.unit); the preserved upstream stays exact. Implements
dsp_journal_manager.h on resident_driver's owned transport and its
whole-transport lease. Catalogue/page/map publication stays dsp.c's. No
hardware ACK, timing or readiness is claimed: owned completion is the private
receiver's HF2/HF3 toggle, bound to internal sequences only.
"""

DECLARATIONS = r'''
/* Modwerk journal (resident_journal.py): the generation holding the whole-transport lease, 0 none. Every legacy
 * selection, observer, publication and compaction path below refuses while it is held. */
static uint32_t journal_generation;
/* The owner generation of the code each id's dispatch was last bound to on each core (legacy binds included);
 * 0: the stub, an original, stock code or unknown. A handle alone never names a generation. */
static uint32_t bound_generation[2][DL_PACKAGES],binding_generation;
static uint32_t __attribute__((noinline)) journal_source(const uint32_t *words) {
    uint32_t g=0,lock=modwerk_machine_lock(); struct runtime_owner o;
    for(unsigned i=0;words && i<RUNTIME_MODULES && !g;++i) {
        const struct runtime_module *m=modwerk_runtime_module(i);
        if(m && m->dsp.words==words && modwerk_runtime_owner_snapshot(m->dsp.image,&o)==1 && o.module==m->id) g=o.generation;
    }
    modwerk_machine_unlock(lock); return g;
}
'''

# Size: helpers stay out of line and per-core work is one function (MAIN margin; O2 kept, no -Os here).
JOURNAL = r'''
/* Modwerk journal (dsp_journal_manager.h). Each row keeps its predecessor's placement and dispatch; new code goes
 * to a fresh contiguous hole beside it, uploaded and bound through the owned transport. The dispatcher inits only
 * on an id change, so an id is rebound only while no slot runs it, and a slot found running it after its rebind
 * makes the row unknown. Unknown work quarantines: the lease and both generations stay held until cold init.
 * A receipt's acknowledged sequence is the internal binding of the receiver's HF2 toggle, never a returned one. */
#ifndef DL_NATIVE_TEST
#define JOURNAL_LIVE ((const volatile uint8_t *)0x80000ec4u)
#else
extern uint8_t dl_journal_test_live[16];
#define JOURNAL_LIVE dl_journal_test_live
#endif
#define JOURNAL_HELPER static __attribute__((noinline))
#define JOURNAL_NEED(j) ((j)->reverse ? (j)->dispatched : (j)->placed)
int modwerk_dsp_catalogue_handle(uint32_t module);
struct journal_row {
    const struct runtime_dsp *from,*to;
    uint32_t module,before,after;                   /* owner generations: one handle can hold either */
    uint16_t offset[2];                             /* the new code's arena offset per placed core */
    uint8_t handle,placed,dispatched,reverse,done;  /* core masks; handle 255: no DSP id */
    uint8_t pad[3];                                 /* 32 bytes: indexing shifts instead of multiplying */
};
struct journal_lane { struct dl_owned_job job; struct mw_manager_core_receipt receipt; uint8_t next; };
static struct journal_row journal_rows[RUNTIME_JOURNAL_ROWS];
static struct journal_lane journal_lane[2];         /* the active row per core: reservation, receipt, chain step */
static unsigned journal_count,journal_active,journal_quarantined;
static uint32_t journal_accepted;                   /* the generation whose fresh installs Keep finalized, 0 none */
static uint8_t journal_submitted;
/* At freeze: Part desired slots, the Y buffer plan and stubs, which no path may change under the lease. */
#define JOURNAL_STATE (48u+sizeof stubbed)
static uint8_t journal_saved[JOURNAL_STATE];
JOURNAL_HELPER uint32_t journal_capture(uint8_t *s) {
    const uint8_t *k=(const uint8_t *)stubbed;
    for(unsigned i=0;i<JOURNAL_STATE;++i)
        s[i]=i<16u ? desired[i] : i<32u ? buffers.live[i-16u] : i<48u ? buffers.target[i-32u] : k[i-48u];
    return phase|waiting|queued_token|allocator.phase|buffers.open;
}
static int journal_fail(void) { journal_quarantined=1; return -1; }
JOURNAL_HELPER int journal_phase(uint32_t g) {
    struct runtime_journal_progress p; modwerk_runtime_journal_snapshot(&p);
    return g && g==journal_generation && g==p.generation ? (int)p.phase : -1;
}
JOURNAL_HELPER int journal_runs(unsigned c,unsigned h) {
    for(unsigned i=0;i<16;++i) if(((i&7)<4 ? 1u:0u)==c && JOURNAL_LIVE[i]==h) return 1;
    return 0;
}
/* Rows are one per module; its owner generations make a stale view miss. */
JOURNAL_HELPER struct journal_row *journal_find(const struct runtime_journal_view *r) {
    for(unsigned k=0;r && k<journal_count;++k) {
        struct journal_row *j=&journal_rows[k];
        if(j->module==r->module && j->before==r->before.generation && j->after==r->after.generation) return j;
    }
    return 0;
}
/* Unsubmitted reservations of the active row; 0 when the transport refuses (then unknown). */
JOURNAL_HELPER int journal_cancel(void) {
    for(unsigned c=0;c<2;++c) {
        if(journal_lane[c].job.ticket && dl_owned_cancel(&journal_lane[c].job)!=1) return 0;
        journal_lane[c].job.ticket=0;
    }
    return 1;
}
JOURNAL_HELPER struct journal_row *journal_activate(struct journal_row *j,const struct runtime_journal_view *r,unsigned reverse) {
    uint8_t *z=(uint8_t *)journal_lane;
    for(unsigned i=0;i<sizeof journal_lane;++i) z[i]=0;
    if(!j) {
        j=&journal_rows[journal_count++];
        j->from=r->from;j->to=r->to;j->module=r->module;j->before=r->before.generation;j->after=r->after.generation;
        j->offset[0]=j->offset[1]=0;j->handle=255;j->placed=j->dispatched=0;
    }
    j->reverse=(uint8_t)reverse;j->done=0;journal_active=(unsigned)(j-journal_rows);return j;
}
/* The lowest hole of n words on core c clear of live code and of every row's new code (kept until release). */
JOURNAL_HELPER int journal_hole(unsigned c,unsigned n) {
    unsigned base=0,k=0;
    while(k<DL_PACKAGES+journal_count) {
        unsigned at,end;
        if(k<DL_PACKAGES) { const struct dl_placement *l=&allocator.live[c][k]; at=l->offset; end=l->present ? at+l->words : at; }
        else { const struct journal_row *j=&journal_rows[k-DL_PACKAGES]; at=j->offset[c]; end=j->placed>>c&1u ? at+j->to->count : at; }
        if(at<end && base<end && base+n>at) base=end,k=0; else ++k;
    }
    return base+n<=allocator.capacity[c] ? (int)base : -1;
}
/* Placed code is rebound only when its bound generation is exactly this row's predecessor: 1 placed, 0 not, -1 refuse. */
JOURNAL_HELPER int journal_placed(unsigned c,unsigned h,const struct runtime_dsp *from,uint32_t before) {
    const struct dl_placement *l=&allocator.live[c][h];
    if(!l->present) return 0;
    return from->count && before && bound_generation[c][h]==before && l->words==from->count && !fx_in(stubbed[c],h) ? 1 : -1;
}
JOURNAL_HELPER int journal_reserve(const struct journal_row *j,unsigned c) {
    const struct runtime_dsp *d=j->reverse ? j->from : j->to;
    struct dl_owned_job *v=&journal_lane[c].job;
    unsigned at=DL_CODE_START+(j->reverse ? allocator.live[c][j->handle].offset : j->offset[c]);
    if(!j->reverse && d->count && !journal_lane[c].next) {
        struct dl_upload u={d->words,d->relocations,(uint16_t)d->count,d->relocation_count,(uint16_t)at};
        return dl_owned_upload_reserve(c,journal_generation,&u,v);
    }
    return dl_owned_command_reserve(c,journal_generation,d->count ? DL_BIND : DL_BYPASS,j->handle,
                                    d->count ? at+d->init : 0u,d->count ? at+d->proc : 0u,v);
}
/* One core of the active row: forward upload then BIND (BYPASS for a removal), reverse BIND to the predecessor;
 * -1 unknown, else 0. A row's jobs must be contiguous in the core's sequence: nothing else transmitted between. */
JOURNAL_HELPER int journal_core(struct journal_row *j,unsigned c) {
    struct journal_lane *l=&journal_lane[c]; struct dl_owned_job *v=&l->job;
    unsigned bit=1u<<c,dispatch=l->next==(!j->reverse && j->to->count);
    if(!(JOURNAL_NEED(j)&bit) || (j->done&bit)) return 0;
    if(!(journal_submitted&bit)) {
        if(!v->ticket && !journal_reserve(j,c)) return -1;
        if(dispatch && journal_runs(c,j->handle)) return 0;    /* rebind once no slot runs it */
        if((l->next && v->first_sequence!=(uint16_t)(l->receipt.last_sequence+1u)) || !dl_owned_submit(v)) return -1;
        journal_submitted|=bit;
        if(dispatch && !j->reverse) j->dispatched|=bit;
        if(!l->next) l->receipt.first_sequence=v->first_sequence;
    }
    struct dl_owned_progress p;
    int s=dl_owned_job_poll(v,&p);
    if(!s) return 0;
    if(s!=1 || p.acknowledged_sequence!=v->last_sequence || dl_owned_job_release(v)!=1) return -1;
    journal_submitted&=~bit;
    l->receipt.job_ticket=v->ticket; l->receipt.job_generation=v->generation;
    l->receipt.last_sequence=l->receipt.acknowledged_sequence=v->last_sequence; v->ticket=0;
    if(!dispatch) { ++l->next; return 0; }
    if(journal_runs(c,j->handle)) return -1;                    /* it may have started on the other code */
    const struct runtime_dsp *d=j->reverse ? j->from : j->to;
    unsigned at=DL_CODE_START+(j->reverse ? allocator.live[c][j->handle].offset : j->offset[c]);
    l->receipt.pool_base=dl_pool_base[c]; l->receipt.pool_words=dl_pool_words[c];
    l->receipt.code_offset=d->count ? (uint16_t)(dl_pool_base[c]+at) : 0u; /* absolute P address of the bound code */
    l->receipt.code_words=(uint16_t)d->count; l->receipt.released=1; j->done|=bit; return 0;
}
int mw_manager_journal_freeze(uint32_t g) {
    if(journal_quarantined) return -1;
    if(journal_generation) return journal_generation==g;
    struct runtime_journal_progress p; modwerk_runtime_journal_snapshot(&p);
    if(!g || p.generation!=g || p.phase!=RJ_PUBLISHING || !dl_residency_enabled || journal_capture(journal_saved) ||
       !dl_owned_lease_acquire(g)) return 0;
    journal_generation=g; journal_count=0; return 1;
}
int mw_manager_journal_stage(uint32_t g,const struct runtime_journal_view *r,int reverse) {
    if(journal_quarantined) return -1;
    if(!r || !r->from || !r->to || (reverse!=0 && reverse!=1) || journal_phase(g)!=(reverse ? RJ_ROLLBACK : RJ_PUBLISHING)) return 0;
    struct journal_row *j=journal_find(r);
    if(j && j->reverse==reverse) return 1;
    if(journal_submitted || (!j && journal_count==RUNTIME_JOURNAL_ROWS)) return 0;
    if(reverse) {
        /* Restore only what was rebound, onto the frozen predecessor placement and generation. */
        for(unsigned c=0;j && c<2;++c) if((j->dispatched>>c&1u) && journal_placed(c,j->handle,j->from,j->before)!=1) return journal_fail();
        if(!journal_cancel()) return journal_fail();
        journal_activate(j,r,1); return 1;          /* never staged: nothing of it was rebound */
    }
    /* One row at a time; a reversed row is never published again. */
    if(j || (journal_count && journal_rows[journal_active].done!=JOURNAL_NEED(&journal_rows[journal_active]))) return 0;
    /* Normal FX only. shortcut: no buffer-transition, machine-metadata or foreign-root contract exists yet. */
    const struct runtime_dsp *f=r->from,*t=r->to;
    if(!r->module || r->before.generation==r->after.generation || (f->count ? f->buffer : 0u)!=(t->count ? t->buffer : 0u) ||
       ((f->flags|t->flags)&RUNTIME_GROUP_METADATA) || f->foreign_roots || t->foreign_roots) return 0;
    int h=f->count ? modwerk_dsp_catalogue_handle(r->module) : t->count ? t->id : -1,at[2]={-1,-1};
    if(f->count && (h<0 || (t->count && h!=t->id))) return 0;
    if(h>=0) {
        if(h>=(int)DL_PACKAGES || !fx_in(modwerk_fx_modules,(unsigned)h)) return 0;
        for(unsigned k=0;k<journal_count;++k) if(journal_rows[k].handle==h) return 0;
        for(unsigned c=0;c<2;++c) {
            int placed=journal_placed(c,(unsigned)h,f,r->before.generation);
            if(placed<0 || (placed && (at[c]=t->count ? journal_hole(c,t->count) : 0)<0)) return 0;
        }
    }
    j=journal_activate(0,r,0); j->handle=(uint8_t)h;
    for(unsigned c=0;c<2;++c) if(at[c]>=0) j->placed|=(uint8_t)(1u<<c),j->offset[c]=(uint16_t)at[c];
    return 1;
}
int mw_manager_journal_step(uint32_t g) {
    if(journal_quarantined || !g || g!=journal_generation || journal_active>=journal_count) return -1;
    struct journal_row *j=&journal_rows[journal_active];
    if(journal_core(j,0)<0 || journal_core(j,1)<0) return journal_fail();
    return j->done==JOURNAL_NEED(j);
}
int mw_manager_journal_receipt(uint32_t g,const struct runtime_journal_view *r,int reverse,
                               uint8_t *required,struct mw_manager_core_receipt out[2]) {
    if(journal_quarantined) return -1;
    const struct journal_row *j=journal_find(r);
    if(!g || g!=journal_generation || !required || !out || !j || j!=&journal_rows[journal_active] ||
       j->reverse!=reverse || journal_submitted || j->done!=JOURNAL_NEED(j)) return 0;
    *required=JOURNAL_NEED(j);
    for(unsigned c=0;c<2;++c) bytes(&out[c],&journal_lane[c].receipt,sizeof *out);
    return 1;
}
/* Keep: forward finalization of a fresh-install set. Stage refuses an install over placed code, so each such row
 * placed and rebound nothing and has no predecessor to free: its new catalogue entry is already the live state,
 * and the legacy residency binds it (recording its generation) once release lets go of the lease. */
int mw_manager_journal_accept(uint32_t g,const struct runtime_journal_view *rows,unsigned n) {
    if(journal_quarantined) return -1;
    if(journal_phase(g)!=RJ_TRIAL || journal_submitted || !rows || !n || n!=journal_count) return 0;
    for(unsigned k=0;k<n;++k) {
        const struct journal_row *j=journal_find(&rows[k]);
        if(!j || j->reverse || j->before || !j->after || j->placed || j->dispatched || j->done) return 0;
    }
    journal_accepted=g; return 1;
}
int mw_manager_journal_release(uint32_t g) {
    if(journal_quarantined) return -1;
    if(journal_submitted || journal_phase(g)!=RJ_IDLE) return 0;
    for(unsigned k=0;k<journal_count;++k) {
        const struct journal_row *j=&journal_rows[k];
        /* shortcut: root has no roots proof yet, so a rebound row releases only after its exact reverse, and Keep
         * accepts unplaced fresh installs alone; finalizing a placed row (new placement live, predecessor freed)
         * waits for that proof. */
        if(j->reverse ? j->done!=j->dispatched : j->dispatched!=0) return 0;
        for(unsigned c=0;c<2;++c) if((j->placed>>c&1u) && (!allocator.live[c][j->handle].present ||
                                     bound_generation[c][j->handle]!=j->before)) return journal_fail();
    }
    uint8_t s[JOURNAL_STATE];
    if(journal_capture(s)) return journal_fail();
    for(unsigned i=0;i<JOURNAL_STATE;++i) if(s[i]!=journal_saved[i]) return journal_fail();
    if(!journal_cancel()) return journal_fail();
    if(dl_owned_lease_release(g)!=1) return 0;
    if(journal_accepted==g) dl_residency_nudge(); /* tracks may already name a kept install: load it there now */
    journal_generation=0; journal_count=0; journal_accepted=0; return 1;
}
'''


def manager(text):
    """Apply after resident_placement.manager and before zero_state.unit; refuse any seam drift."""
    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('Generated manager journal seam changed: ' + old[:70])
        text = text.replace(old, new)
    change('#include "stock_hook_resources.h"\n', '#include "stock_hook_resources.h"\n#include "dsp_journal_manager.h"\n')
    change('static int result=0;\n', 'static int result=0;\n' + DECLARATIONS.lstrip('\n'))
    # A legacy bind records the generation it binds, read where it starts; an acknowledged unbind/bypass clears it.
    # A rollback's BIND back to a moved id's old copy (build_core's dl_move edit, `back`) binds that same code.
    change('        } else waiting=dl_command_start(c,mode==3 || back ? DL_BIND : mode==4 || dl_bypass_unbound ? DL_BYPASS:DL_UNBIND,\n'
           '                                         p,offset+code->init,offset+code->proc);\n',
           '        } else {\n'
           '            if(mode==3 || back) binding_generation=journal_source(code->words);\n'
           '            waiting=dl_command_start(c,mode==3 || back ? DL_BIND : mode==4 || dl_bypass_unbound ? DL_BYPASS:DL_UNBIND,\n'
           '                                     p,offset+code->init,offset+code->proc);\n'
           '        }\n')
    change('            if(phase==3) stubbed[c]=fx_without(stubbed[c],id);\n',
           '            if(phase!=2) bound_generation[c][id]=phase==3 || sent_back ? binding_generation : 0;\n'
           '            if(phase==3) stubbed[c]=fx_without(stubbed[c],id);\n')
    # An owned job (the board's RESET or CAS, an engine's WRITE or PLACE) holds its core: a legacy start refuses and
    # dl_job_status answers -2 for that core, as for a start refused outright. That is a wait, as for a legacy job of
    # someone else: the next tick starts again, so a Part switch needing an upload completes after the owned job. At
    # most 600 refused starts per owned job (the evacuation's patience); then it refuses as before.
    change('static void tables(void) {\n',
           'static uint32_t owned_seen;\nstatic unsigned owned_patience;\n'
           'static unsigned owned_wait(unsigned c) {\n'
           '    uint32_t ticket=dl_owned_holder(c);\n'
           '    if(!ticket) return 0;\n'
           '    if(ticket!=owned_seen) { owned_seen=ticket; owned_patience=0; }\n'
           '    return ++owned_patience<=600u;\n'
           '}\n'
           'static void tables(void) {\n')
    change('        if(!waiting && dl_job_status((unsigned)i/8)==-2) {',
           '        if(!waiting && dl_job_status((unsigned)i/8)==-2 && !owned_wait((unsigned)i/8)) {')
    change('        if(!waiting && dl_job_status(c)==-2) {',
           '        if(!waiting && dl_job_status(c)==-2 && !owned_wait(c)) {')
    for entry in ('int dl_selection_prepare(const struct dl_selection *s,uint32_t token) {',
                  'int dl_move(unsigned c,unsigned p,unsigned offset) {',
                  'int dl_publication_prepare(const uint8_t ids[16],const uint8_t sources[8],uint32_t token) {'):
        change(entry + '\n    if(!modwerk_stock_hook_export_idle()',
               entry + '\n    if(journal_generation || !modwerk_stock_hook_export_idle()')
    change('void dl_residency_tick(void) {\n    if(!dl_residency_enabled) return;',
           'void dl_residency_tick(void) {\n    if(!dl_residency_enabled || journal_generation) return;')
    change('int dl_publication_ready(const uint8_t ids[16]) {\n',
           'int dl_publication_ready(const uint8_t ids[16]) {\n    if(journal_generation) return 0;\n')
    change('    if(phase || waiting || queued_token || buffers.open) return 0;',
           '    if(journal_generation || phase || waiting || queued_token || buffers.open) return 0;')
    change('int dl_publication_idle(void) { return phase==0; }',
           'int dl_publication_idle(void) { return phase==0 && !journal_generation; }')
    return text + JOURNAL
