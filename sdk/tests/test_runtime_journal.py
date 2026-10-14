# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual saved-set code holds still while a volatile journal owns RAM and takes
only an exactly matching Keep; absent backend is closed.

The loader's normal host suite exercises real allocation, site publication,
partial/unknown synthetic ACKs and reverse rollback under both pool sizes.
These fixtures establish native source behavior, not physical DSP readiness.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from host_flags import SANITIZE  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LOADER = ROOT / 'sdk/runtime/loader'
ELEK = ROOT / 'sdk/machines/octatrack/elekloader'


@unittest.skipUnless(shutil.which('cc'), 'host C compiler unavailable')
class RuntimeJournal(unittest.TestCase):
    def compile_run(self, source, defines=()):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / 'fixture.c'
            fixture.write_text(source)
            args = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                    *defines, '-I', LOADER, '-I', ROOT / 'sdk/runtime/upload',
                    '-I', ELEK, fixture, '-o', Path(temp) / 'fixture']
            compiled = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = subprocess.run([Path(temp) / 'fixture'], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)

    def test_actual_board_begin_gate_refuses_every_outstanding_work_factor(self):
        # Execute these exact board functions, substituting only the two
        # fixed status registers and uncached host address alias. No fixture
        # result can establish board readiness or a real DSP census.
        text = (ELEK / 'ep0.c').read_text()
        def function(signature):
            start = text.index(signature)
            at = text.index('{', start)
            depth = 1
            end = at + 1
            while depth:
                depth += (text[end] == '{') - (text[end] == '}')
                end += 1
            return text[start:end]
        source = '''#include <assert.h>
#include "vendor.h"
#define MODWERK_SAVED_SET_EXPORT
#define MODWERK_RESIDENT_STOCK_HOOKS
#define MODWERK_RUNTIME_VOLATILE_JOURNAL
#include "volatile_service.h"
#define UNCACHED(p) (p)
static struct mv_transport transport;
static struct mu_context controller;
static struct mvs_service volatile_service;
#define VOLATILE_SERVICE (&volatile_service)
static int started=1,wake_posted,receiving,held,controller_started;
static int journal_busy,service_busy;
int modwerk_runtime_volatile_busy(void) { return journal_busy; }
int modwerk_volatile_busy(const struct mvs_service *s) { assert(s==VOLATILE_SERVICE);return service_busy; }
static int exporting,modset_idle=1,dsp_idle=1,stopped=1,hooks_idle=1;
/* 0x460d1cb8: card mounted (1); 0x460e76a0: USB disk mode active. */
static uint32_t card_ready=1,usb_disk;
static uint32_t reg(uint32_t a) { assert(a==0x460d1cb8u || a==0x460e76a0u); return a==0x460d1cb8u?card_ready:usb_disk; }
#define REG(a) reg(a)
int modwerk_saved_set_busy(void) { return exporting; }
int modwerk_modset_export_idle(void) { return modset_idle; }
int modwerk_dsp_export_idle(void) { return dsp_idle; }
int modwerk_machine_stopped(void) { return stopped; }
int modwerk_stock_hook_export_idle(void) { return hooks_idle; }
''' + function('static int saved_set_structural_safe(void)') + '\n' + function('int modwerk_machine_journal_begin_safe(void)') + '''
int main(void) {
    assert(modwerk_machine_journal_begin_safe());
    int *bad_one[]={&wake_posted,&receiving,&held,&exporting,&journal_busy,&service_busy};
    for(unsigned i=0;i<sizeof bad_one/sizeof bad_one[0];i++) {
        *bad_one[i]=1;assert(!modwerk_machine_journal_begin_safe());*bad_one[i]=0;
        assert(modwerk_machine_journal_begin_safe());
    }
    int *bad_zero[]={&started,&modset_idle,&dsp_idle,&stopped,&hooks_idle};
    for(unsigned i=0;i<sizeof bad_zero/sizeof bad_zero[0];i++) {
        *bad_zero[i]=0;assert(!modwerk_machine_journal_begin_safe());*bad_zero[i]=1;
        assert(modwerk_machine_journal_begin_safe());
    }
    transport.resets=1;assert(!modwerk_machine_journal_begin_safe());transport.handled=1;
    transport.lapses=1;assert(!modwerk_machine_journal_begin_safe());transport.lapses_handled=1;
    assert(modwerk_machine_journal_begin_safe());
    controller_started=1;controller.phase=MU_TRIAL;assert(!modwerk_machine_journal_begin_safe());controller.phase=MU_NORMAL;
    card_ready=0;assert(!modwerk_machine_journal_begin_safe());card_ready=1;
    usb_disk=1;assert(!modwerk_machine_journal_begin_safe());usb_disk=0;
    assert(modwerk_machine_journal_begin_safe());return 0;
}
'''
        self.compile_run(source)

    def test_all_real_saved_set_paths_preserve_both_files_and_ram_baseline(self):
        source = (ELEK / 'test_modset.c').read_text()
        sanitizers = ('-g', *SANITIZE, '-fno-sanitize-recover=all')
        for defines in (('-DMODWERK_HOST',), ('-DMODWERK_HOST', '-DRUNTIME_MODULES=128u', '-DRUNTIME_POOL_BYTES=786432u')):
            with self.subTest(defines=defines):
                self.compile_run(source, defines + sanitizers)

    def test_missing_production_journal_backend_does_not_open_a_service(self):
        # Keep the real legacy loader suite and remove only the synthetic
        # journal adapter and its enabled-path fixture. Its weak production
        # functions then execute rather than being asserted from source text.
        source = (LOADER / 'tests/host_test.c').read_text()
        source = source.replace('#define MODWERK_RUNTIME_JOURNAL_EXTERNAL\n', '')
        source = source.replace('#include "../loader.c"', '#include "loader.c"')
        source = source.replace('#include "../../upload/sha256.c"', '#include "sha256.c"')
        start = source.index('/* Trusted synthetic adapter:')
        end = source.index('static const struct mu_backend *b', start)
        source = source[:start] + source[end:]
        start = source.index('    /* The real pool keeps')
        end = source.index('    if (failures)', start)
        source = source[:start] + '''
    CHECK(modwerk_runtime_journal_begin()==RJ_REFUSED);
    CHECK(!modwerk_runtime_volatile_busy());
    struct runtime_journal_progress snapshot;
    modwerk_runtime_journal_snapshot(&snapshot);
    CHECK(snapshot.phase==RJ_IDLE && !snapshot.generation && !snapshot.records);
    CHECK(modwerk_runtime_journal_verify()==RJ_REFUSED);
    CHECK(modwerk_runtime_journal_activate()==RJ_REFUSED);
    CHECK(modwerk_runtime_journal_abort()==RJ_STALE);
    CHECK(modwerk_runtime_journal_accept()==RJ_REFUSED && !modwerk_runtime_volatile_busy());
    CHECK(!modwerk_machine_journal_accept(0,0));
''' + source[end:]
        self.compile_run(source)

    def test_actual_board_ledger_drives_the_real_checked_dsp_commit(self):
        # journal_board.c's stored receipts against dsp.c/fxpage.c/fxmap.c's
        # actual checked publication. Owners, progress, the association row
        # and manager receipts are synthetic; no DSP ACK is established.
        for defines in ((), ('-DMODWERK_FX_IDS=128u',)):
            with self.subTest(defines=defines), tempfile.TemporaryDirectory() as temp:
                args = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-g',
                        *SANITIZE, '-fno-sanitize-recover=all', '-DMODWERK_HOST',
                        '-DMODWERK_DSP_ALLOWANCE0=3120', '-DMODWERK_DSP_ALLOWANCE1=3565', '-DMODWERK_DSP_RESERVE=342',
                        *defines, '-I', ELEK, '-I', ROOT / 'sdk/octabam/platform/dsp-dynload-transport',
                        '-I', ROOT / 'sdk/runtime/upload', '-I', LOADER, ELEK / 'test_journal_board.c',
                        '-o', Path(temp) / 'board']
                compiled = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                ran = subprocess.run([Path(temp) / 'board'], capture_output=True, text=True)
                self.assertEqual(ran.returncode, 0, ran.stderr)

    def test_public_board_adapter_is_closed_and_declares_nothing(self):
        source = (ELEK / 'journal_board.c').read_text()
        self.assertIn('#define MODWERK_JOURNAL_BOARD_ENABLED 0', source)
        self.assertIn('#define MW_REVIEWED_JOURNAL_ASSOCIATIONS /* none */', source)
        build = (ELEK / 'build_core.py').read_text()
        self.assertNotIn('MODWERK_JOURNAL_BOARD_ENABLED', build)
        self.assertNotIn('MW_REVIEWED_JOURNAL_ASSOCIATIONS', build)


if __name__ == '__main__':
    unittest.main()
