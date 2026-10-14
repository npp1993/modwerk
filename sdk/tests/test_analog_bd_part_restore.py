# SPDX-License-Identifier: GPL-3.0-or-later
"""Owner-approved AB retirement conversion: synthetic Part memory, no firmware in CI."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
SOURCE=Path(__file__).resolve().parents[1]/'machines/octatrack/module-adapters/analog-bd-parts'
class AnalogBdPartRestore(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc') or shutil.which('gcc'),'native C compiler unavailable')
    def test_known_copies_convert_marker_last_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'part-restore'
            subprocess.run([shutil.which('cc') or shutil.which('gcc'),'-std=c99','-O1','-Wall','-Wextra','-Werror','-pedantic',
                SOURCE/'analog_bd_part_restore.c',SOURCE/'test_analog_bd_part_restore.c','-o',binary],check=True,capture_output=True)
            result=subprocess.run([binary],check=True,text=True,capture_output=True)
            self.assertIn('PASS AB Part conversion',result.stdout)
    @unittest.skipUnless(shutil.which('m68k-elf-gcc'),'ColdFire compiler unavailable')
    def test_coldfire_o2_has_no_owned_state_or_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj=Path(tmp)/'restore.o'
            subprocess.run(['m68k-elf-gcc','-mcpu=54455','-msoft-float','-O2','-ffreestanding','-fno-builtin',
                '-Wall','-Wextra','-Werror','-c',SOURCE/'analog_bd_part_restore.c','-o',obj],check=True,capture_output=True)
            symbols=subprocess.check_output(['m68k-elf-nm',obj],text=True)
            for name in ('mw_ab_restore_plan','mw_ab_restore_apply','mw_ab_restore_parts'):
                self.assertIn(' T '+name,symbols)
            for kind in (' U ',' B ',' D ',' b ',' d '):
                self.assertNotIn(kind,symbols)


class AnalogBdPartBoard(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc') or shutil.which('gcc'),'native C compiler unavailable')
    def test_board_window_writes_only_part_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'part-board'
            subprocess.run([shutil.which('cc') or shutil.which('gcc'),'-std=c99','-O1','-Wall','-Wextra','-Werror','-pedantic','-DMODWERK_HOST',
                SOURCE/'analog_bd_part_board.c',SOURCE/'test_analog_bd_part_board.c','-o',binary],check=True,capture_output=True)
            self.assertIn('PASS AB board access window',subprocess.run([binary],check=True,text=True,capture_output=True).stdout)
    @unittest.skipUnless(shutil.which('m68k-elf-gcc'),'ColdFire compiler unavailable')
    def test_coldfire_glue_links_with_one_static_plan_and_no_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            objects=[]
            for name in ('analog_bd_part_board','analog_bd_part_restore'):
                obj=Path(tmp)/(name+'.o');objects.append(obj)
                subprocess.run(['m68k-elf-gcc','-mcpu=54455','-msoft-float','-O2','-ffreestanding','-fno-builtin',
                    '-Wall','-Wextra','-Werror','-c',SOURCE/(name+'.c'),'-o',obj],check=True,capture_output=True)
            both=Path(tmp)/'both.o'
            subprocess.run(['m68k-elf-ld','-r','-o',both,*objects],check=True,capture_output=True)
            symbols=subprocess.check_output(['m68k-elf-nm','-S',both],text=True)
            self.assertNotIn(' U ',symbols)
            for name in ('mw_ab_board_check','mw_ab_board_retire'):self.assertIn(' T '+name,symbols)
            bss=[line for line in symbols.splitlines() if line.split()[-2] in ('b','B')]
            self.assertEqual([line.split()[-1] for line in bss],['plan'])
            self.assertRegex(subprocess.check_output(['m68k-elf-objdump','-d',both],text=True),r'movew? %sr,')
