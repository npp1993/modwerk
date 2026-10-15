# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual generated transport and registry boundary; synthetic board facts.

No fixture declaration admits production source or qualifies HF2/HF3 hardware.
Only timer MMIO/SR and actual board proof callbacks are native substitutions.
"""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / 'sdk/machines/octatrack/module-adapters'
POLICY = ADAPTER / 'controller-policy'
ELEK = ROOT / 'sdk/machines/octatrack/elekloader'
sys.path.append(str(ADAPTER))
import resident_driver
from host_flags import SANITIZE  # noqa: E402

FIXTURE = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "controller_transport.h"
volatile uint32_t test_clock;
static unsigned sr,masked,interleave,flags[2],masks[2],writes,source_ok=1,resource_ok=1,owner_ok=1;
static unsigned policy_calls;
unsigned modwerk_dsp_flags(unsigned c) { return flags[c]; }
void modwerk_diag_frame(void) {} /* diag.c: the frame interrupt's freeze watch */
unsigned mw_controller_transport_test_sr(void) { return sr; }
uint32_t modwerk_machine_lock(void) { unsigned old=sr;if(sr<0x400u) sr=0x400u;return old; }
void modwerk_machine_unlock(uint32_t old) { assert(sr==0x400u);sr=old; }
void dl_selection_tick(void) {}
void dl_residency_tick(void) {}
void dl_show_message(const char *s,unsigned n) { (void)s;(void)n; }
#define DL_OWNED_ADVERSARIAL
#include "transfer.c"
void dl_owned_test_boundary(unsigned n) {
    if(n==1) { assert(sr==0x400u && !masked);sr=0x700u;masked=1; }
    if(n==2) { assert(sr==0x700u && masked);if(interleave==2) dl_request_probe++; }
    if(n==3) { assert(masked);masked=0;sr=0x400u; }
    if(interleave && !masked) {
        if(interleave==1 && n==0) dl_request_probe++;
        dl_frame();
    }
}
static int own(void *ctx,const struct mw_controller_binding *b) {
    (void)ctx;assert(sr>=0x400u);policy_calls++;return owner_ok && b->generation && b->identity.module;
}
static int resources(void *ctx,const struct mw_controller_binding *b) { (void)ctx;(void)b;assert(sr>=0x400u);return resource_ok; }
static int blocked(void *ctx) { (void)ctx;assert(sr>=0x400u);return writes; }
static int publication_fixture(void *ctx,const struct mw_controller_binding *b) { (void)ctx;(void)b;assert(sr>=0x400u);return 1; }
static int roots(void *ctx,const struct mw_controller_binding *b) { (void)ctx;(void)b;assert(sr>=0x400u);return 1; }
static uint32_t reset_words[24];
static int source(void *ctx,const struct mw_controller_binding *b,unsigned c,uint32_t offset,const uint32_t **words,unsigned *count) {
    (void)ctx;(void)c;assert(sr>=0x400u && b->identity.feature==2u && offset<193u);
    *words=reset_words;*count=193u-offset>24u ? 24u:193u-offset;return source_ok;
}
static int mask(void *ctx,const struct mw_controller_binding *b,unsigned c,uint32_t *out) { (void)ctx;(void)b;assert(sr>=0x400u);*out=masks[c];return 1; }
static const struct mw_controller_transport_policy proof={own,resources,blocked,publication_fixture,roots,source,mask};
static struct mw_controller_declaration declaration(void) {
    struct mw_controller_declaration d={0};
    d.identity.package_sha256[0]=1;d.identity.source_policy_sha256[0]=2;
    d.identity.module=77;d.identity.feature=2;d.identity.required_cores=1;
    d.identity.policy_revision=d.identity.state_revision=d.identity.parameter_revision=1;
    d.reset_words[0]=193;return d;
}
static struct mw_controller_binding bind(struct mw_controller_registry *r,unsigned generation,const struct mw_controller_binding *previous,unsigned *slot) {
    struct mw_controller_declaration d=declaration();
    struct mw_controller_binding b={d.identity,generation,0x40010000u+0x1000u*generation,512,16,128};
    unsigned old=modwerk_machine_lock();
    assert(mw_controller_reserve(r,&d,&d.identity,previous,slot)==MW_CTL_OK);
    assert(mw_controller_bind(r,*slot,&b)==MW_CTL_OK);
    modwerk_machine_unlock(old);return b;
}
static void answer(unsigned c,unsigned reject) {
    flags[c]=(flags[c]^1u)&1u;if(reject) flags[c]|=2u;
    if(!reject && dl_tx[c][2]==10u) masks[c]=dl_tx[c][5];
    dl_frame();
}
static void finish(struct mw_controller_transport *t,const struct mw_controller_binding *b,unsigned operation) {
    assert(mw_controller_transport_begin(t,b,0,operation)==MW_CTL_PENDING);dl_frame();
    assert(dl_tx[0][1]==t->jobs[0].wire_sequence && t->jobs[0].ticket==t->receipts[0].ticket);
    answer(0,0);assert(mw_controller_transport_poll(t,b,0)==MW_CTL_OK);
    assert(!t->held[0] && t->released[0]);
}
int main(int argc,char **argv) {
    assert(argc==2);unsigned mode=argv[1][0]-'0';
    struct mw_controller_transport t={0};struct mw_controller_registry r={0};unsigned at;
    struct mw_controller_transport_policy missing=proof;missing.reset_source=0;
    assert(!mw_controller_transport_init(&t,&r,&missing,0));
    assert(mw_controller_transport_init(&t,&r,&proof,0) && !mw_controller_transport_init(&t,&r,&proof,0));
    struct mw_controller_binding b=bind(&r,1,0,&at),bad=b;
    assert(sr==0 && !r.backend->owns_image(r.context,&b)); /* no raw unlocked callback authority */
    if(mode==0) {
        bad.generation++;assert(mw_controller_transport_begin(&t,&bad,0,MW_CTL_RESET)==MW_CTL_CLOSED);
        bad=b;bad.identity.source_policy_sha256[0]++;assert(mw_controller_transport_begin(&t,&bad,0,MW_CTL_RESET)==MW_CTL_CLOSED);
        bad=b;bad.canonical_extent+=0x08000000u;assert(mw_controller_transport_begin(&t,&bad,0,MW_CTL_RESET)==MW_CTL_CLOSED);
        owner_ok=0;assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_CLOSED);owner_ok=1;
        source_ok=0;assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_CLOSED);source_ok=1;
        resource_ok=0;assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_CLOSED);resource_ok=1;
        writes=1;assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_CLOSED);writes=0;
        assert(!owned_ticket && !dl_tx[0][0]);
        /* ENABLE before declared reset completion refuses, consumes the
         * actual reservation, and cancels it without transmitting. */
        assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_ENABLE)==MW_CTL_CLOSED);
        assert(owned_ticket==1 && sequence[0]==1 && !jobs[0].state && !t.held[0]);
        while(r.slots[at].state!=MW_CTL_READY) finish(&t,&b,MW_CTL_RESET);
        assert(r.slots[at].acknowledged_words[0]==193 && !r.slots[at].job_state[0]);
        finish(&t,&b,MW_CTL_ENABLE);assert(masks[0]==2);
        unsigned old=modwerk_machine_lock();assert(mw_controller_publish(&r,&b)==MW_CTL_OK);modwerk_machine_unlock(old);
        assert(r.slots[at].state==MW_CTL_ACTIVE && policy_calls);
        /* Same-feature incoming may be reserved, but real predecessor
         * ownership remains held; no manufactured readiness transfer. */
        unsigned next;struct mw_controller_binding incoming=bind(&r,2,&b,&next);
        assert(mw_controller_transport_begin(&t,&incoming,0,MW_CTL_RESET)==MW_CTL_CLOSED);
        assert(!jobs[0].state && r.slots[at].state==MW_CTL_ACTIVE && r.slots[next].state==MW_CTL_BOUND);
    } else if(mode==1 || mode==2) {
        assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_PENDING);dl_frame();
        struct dl_owned_job actual=t.receipts[0];
        if(mode==1) { for(unsigned i=0;i<64;i++) dl_frame(); }
        else { answer(0,0);t.receipts[0].ticket++; }
        assert(mw_controller_transport_poll(&t,&b,0)==MW_CTL_PENDING);
        assert(t.closed[0] && r.slots[at].state==MW_CTL_QUARANTINED && mw_controller_holds(&r,&b));
        if(mode==2) {
            assert(!t.released[0] && t.held[0] && r.slots[at].job_state[0]);
            t.receipts[0]=actual;assert(mw_controller_transport_poll(&t,&b,0)==MW_CTL_PENDING);
        }
        answer(0,0);assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_CLOSED);
        assert(r.slots[at].state==MW_CTL_QUARANTINED);
    } else if(mode==3) {
        interleave=1;assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_CLOSED);
        assert(!t.held[0] && !owned_ticket && pending[0] && pending[1]);
        interleave=0;answer(0,0);answer(1,0);
        interleave=2;assert(mw_controller_transport_begin(&t,&b,0,MW_CTL_RESET)==MW_CTL_PENDING);
        assert(!pending[0] && !dl_tx[0][0]); /* restore ISR sees only state5 */
        interleave=0;dl_frame();answer(0,0);assert(mw_controller_transport_poll(&t,&b,0)==MW_CTL_OK);
        assert(r.slots[at].acknowledged_words[0]==24);
    } else if(mode==4) {
        while(r.slots[at].state!=MW_CTL_READY) finish(&t,&b,MW_CTL_RESET);
        finish(&t,&b,MW_CTL_ENABLE);
        unsigned old=modwerk_machine_lock();assert(mw_controller_publish(&r,&b)==MW_CTL_OK);modwerk_machine_unlock(old);
        unsigned next;struct mw_controller_binding incoming=bind(&r,2,&b,&next);
        finish(&t,&b,MW_CTL_DISABLE);assert(r.slots[at].state==MW_CTL_RETIRING);
        /* Synthetic resource proof permits the helper path only. Real stock
         * hook predecessor ownership is unchanged and remains a board gate. */
        assert(mw_controller_transport_begin(&t,&incoming,0,MW_CTL_RESET)==MW_CTL_PENDING);
        dl_frame();dl_abort();assert(mw_controller_transport_poll(&t,&incoming,0)==MW_CTL_PENDING);
        assert(r.slots[at].state==MW_CTL_QUARANTINED && r.slots[next].state==MW_CTL_QUARANTINED);
        assert(mw_controller_holds(&r,&b) && mw_controller_holds(&r,&incoming) && owned_closed[0]);
    } else assert(0);
    assert(sr==0);return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'host C compiler unavailable')
class ControllerTransport(unittest.TestCase):
    def generated(self):
        spec = importlib.util.spec_from_file_location('controller_transport_core', ELEK / 'build_core.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        texts = {}
        for name in ('transfer.c', 'transfer.h', 'selection.h'):
            text = (core.DYNLOAD / name).read_text()
            for old, new in core.DSP_EDITS.get(name, ()) + core.WIDTH_EDITS.get(name, ()):
                self.assertEqual(text.count(old), 1)
                text = text.replace(old, new)
            if name == 'transfer.c':
                text = resident_driver.transport(text).replace('*(volatile uint32_t *)0xfc07c00cu', 'test_clock')
            elif name == 'transfer.h':
                text = resident_driver.transport_header(text)
            texts[name] = text
        return texts

    def test_actual_owned_frame_registry_boundary_and_retained_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for name, text in self.generated().items():
                (work / name).write_text(text)
            shutil.copyfile(ELEK / 'fxids.h', work / 'fxids.h')
            (work / 'fixture.c').write_text(FIXTURE)
            executable = work / 'controller'
            compile_result = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                *SANITIZE, '-fno-omit-frame-pointer', '-DDL_NATIVE_TEST', '-DMW_CONTROLLER_TRANSPORT_TEST',
                '-DMODWERK_FX_IDS=64', '-DMODWERK_DSP_TABLE0=4096', '-DMODWERK_DSP_TABLE1=4096',
                '-DMODWERK_DSP_WORDS0=2000', '-DMODWERK_DSP_WORDS1=2000', '-I' + str(work), '-I' + str(POLICY),
                '-I' + str(ROOT / 'sdk/runtime/loader'), '-I' + str(ROOT / 'sdk/runtime/upload'),
                str(work / 'fixture.c'), str(POLICY / 'controller_transport.c'), str(POLICY / 'controller_association.c'),
                '-o', str(executable)], capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            for mode in range(5):
                with self.subTest(mode=mode):
                    result = subprocess.run([str(executable), str(mode)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_boundary_has_no_host_receipt_or_readiness_arguments(self):
        source = (POLICY / 'controller_transport.c').read_text()
        self.assertIn('uint32_t irq=modwerk_machine_lock();', source)
        self.assertIn('"move.w %%sr,%0"', source)
        self.assertIn('receipt.first_sequence', source)
        self.assertIn('dl_owned_cancel(&t->receipts[c])==1', source)
        self.assertIn('dl_owned_job_release(&t->receipts[c])!=1', source)
        self.assertNotIn('modwerk_machine_journal_enabled', source)
