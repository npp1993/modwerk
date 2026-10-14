# SPDX-License-Identifier: MIT
"""Execute freshly compiled authored paused-task glue; no firmware or device.

The native Octabam port is optional on CI. Set OCTABAM_NATIVE to its verified
checkout with built emulator archives to run the register/context fixture.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
NATIVE = Path(os.environ.get('OCTABAM_NATIVE', Path.home() / '.cache/modwerk-upstream/octabam'))


class PausedTests(unittest.TestCase):
    def test_current_registers_and_all_known_task_contexts(self):
        gcc, ld, objcopy, nm = [shutil.which('m68k-elf-' + tool) for tool in ('gcc', 'ld', 'objcopy', 'nm')]
        cxx = shutil.which('c++')
        archives = [NATIVE / 'out/emu' / p for p in (
            'libot_machine.a', 'mc68k/lib68kEmu.a', 'dsp56300/dsp56kEmu/libdsp56kEmu.a',
            'dsp56300/dsp56kBase/libdsp56kBase.a', 'dsp56300/asmjit/libasmjit.a')]
        if not all((gcc, ld, objcopy, nm, cxx)) or not all(p.is_file() for p in archives):
            self.skipTest('ColdFire compiler and built native Octabam emulator archives required')
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            glue = ROOT / 'sdk/machines/octatrack/elekloader'
            common = [gcc, '-mcpu=5475', '-msoft-float', '-O2', '-ffreestanding', '-fno-builtin',
                      '-fno-jump-tables', '-fno-asynchronous-unwind-tables', '-fomit-frame-pointer',
                      '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror',
                      '-I' + str(glue), '-I' + str(ROOT / 'sdk/runtime/loader'),
                      '-I' + str(ROOT / 'sdk/runtime/upload')]
            subprocess.run(common + ['-c', glue / 'runtime.c', '-o', work / 'runtime.o'], check=True, capture_output=True)
            subprocess.run(common + ['-c', ROOT / 'sdk/machines/octatrack/module-adapters/paused_register_driver.c',
                                    '-o', work / 'entry.o'], check=True, capture_output=True)
            (work / 'link.ld').write_text('SECTIONS { . = 0x40000400; .text : { *(.text) *(.text.*) } '
                                         '.rodata : { *(.rodata*) } /DISCARD/ : { *(.comment) *(.eh_frame*) } }')
            subprocess.run([ld, '--gc-sections', '-e', 'one', '-T', work / 'link.ld',
                            work / 'entry.o', work / 'runtime.o', '-o', work / 'runtime.elf'], check=True, capture_output=True)
            symbols = subprocess.check_output([nm, work / 'runtime.elf'], text=True)
            self.assertIn('40000400 T one\n', symbols)
            self.assertNotIn(' U ', symbols)
            entries = {line.split()[-1]: line.split()[0] for line in symbols.splitlines()}
            subprocess.run([objcopy, '-O', 'binary', work / 'runtime.elf', work / 'runtime.bin'], check=True)
            source = NATIVE / 'tools/emu/ot_emu'
            subprocess.run([cxx, '-O2', '-std=c++17', '-I' + str(source), '-I' + str(NATIVE / 'vendor'),
                            '-I' + str(NATIVE / 'vendor/dsp56300/source'),
                            ROOT / 'sdk/machines/octatrack/module-adapters/paused_register_fixture.cpp',
                            *archives, '-lpthread', '-o', work / 'probe'], check=True, capture_output=True)
            result = subprocess.run([work / 'probe', work / 'runtime.bin', entries['one'], entries['three']],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # The actual loader must also clear an unheld group. Scanning its
            # own working registers/frames would falsely keep the old image.
            subprocess.run(common + ['-c', ROOT / 'sdk/machines/octatrack/module-adapters/loader_group_driver.c',
                                    '-o', work / 'group.o'], check=True, capture_output=True)
            exports = ['fixture_group_image', 'modwerk_runtime_free', 'modwerk_runtime_active',
                       'modwerk_runtime_refusal', 'modwerk_runtime_backend']
            subprocess.run([ld, '--gc-sections', '-e', 'modwerk_backend_prepare', *['--undefined=' + name for name in exports],
                            '-T', work / 'link.ld', work / 'group.o', work / 'runtime.o', '-o', work / 'group.elf'],
                           check=True, capture_output=True)
            group_symbols = subprocess.check_output([nm, work / 'group.elf'], text=True)
            self.assertNotIn(' U ', group_symbols)
            (work / 'group.symbols').write_text(group_symbols)
            subprocess.run([objcopy, '-O', 'binary', work / 'group.elf', work / 'group.bin'], check=True)
            subprocess.run([cxx, '-O2', '-std=c++17', '-I' + str(source), '-I' + str(NATIVE / 'vendor'),
                            '-I' + str(NATIVE / 'vendor/dsp56300/source'),
                            ROOT / 'sdk/machines/octatrack/module-adapters/loader_group_fixture.cpp',
                            *archives, '-lpthread', '-o', work / 'group-probe'], check=True, capture_output=True)
            result = subprocess.run([work / 'group-probe', work / 'group.bin', work / 'group.symbols'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Repeat real loader lifecycle with the actual private admission
            # helper: empty trust, exact SHA/layout drift, foreign UI roots,
            # saved FM LEG refusal, then replacement/Undo/reclamation.
            adapter = ROOT / 'sdk/machines/octatrack/module-adapters'
            defines = ['-DMODWERK_MACHINE_DECLARATION_TEST', '-I' + str(adapter)]
            objects = []
            for name in ('loader_group_driver','machine_admission','machine_declarations','machine_lifetime','machine_parts'):
                obj = work / (name + '.o')
                subprocess.run(common + defines + ['-c', adapter / (name + '.c'), '-o', obj], check=True, capture_output=True)
                objects.append(obj)
            exports += ['fixture_clear_declarations','fixture_review_package']
            subprocess.run([ld,'--gc-sections','-e','modwerk_backend_prepare',*['--undefined='+name for name in exports],
                            '-T',work/'link.ld',*objects,work/'runtime.o','-o',work/'declared.elf'],check=True,capture_output=True)
            symbols = subprocess.check_output([nm,work/'declared.elf'],text=True)
            self.assertNotIn(' U ', symbols)
            (work/'declared.symbols').write_text(symbols)
            subprocess.run([objcopy,'-O','binary',work/'declared.elf',work/'declared.bin'],check=True)
            subprocess.run([cxx,'-O2','-std=c++17',*defines,'-I'+str(source),'-I'+str(NATIVE/'vendor'),
                            '-I'+str(NATIVE/'vendor/dsp56300/source'),adapter/'loader_group_fixture.cpp',
                            *archives,'-lpthread','-o',work/'declared-probe'],check=True,capture_output=True)
            result = subprocess.run([work/'declared-probe',work/'declared.bin',work/'declared.symbols'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
