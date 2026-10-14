# SPDX-License-Identifier: MIT
"""Exact private trust storage and actual compiled admission refusal tests."""
import importlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / 'sdk/machines/octatrack/module-adapters'
sys.path.append(str(ADAPTER))
import machine_declarations as declarations
fixtures = importlib.import_module('test_machine_layout')


class DeclarationTests(unittest.TestCase):
    setUp = fixtures.LayoutTests.setUp
    declaration = fixtures.LayoutTests.declaration
    validate = fixtures.LayoutTests.validate
    def entry(self, data=None, **changes):
        data = self.package if data is None else data
        doc, recipe, digest = self.declaration(data, **changes)
        return dict(package=data, declaration=doc, recipe=recipe, reviewed_sha256=digest, source_root=self.root)

    def test_fixed_empty_and_reviewed_storage(self):
        empty = declarations.empty()
        self.assertEqual((len(empty), empty[:7], set(empty[7:])), (1072, b'MWMD\2\0\30', {0}))
        table = declarations.generate([self.entry()])
        self.assertEqual((len(table), table[5], table[52]), (1072, 1, 4))
        self.assertEqual(table[16:48].hex(), self.validate().package_sha256)
        for bad in ([self.entry(), self.entry()], [self.entry()] * 25, [dict(self.entry(), reviewed_sha256='0'*64)],
                    [dict(self.entry(), extra=True)], [self.entry(stateLayoutRevision=0)]):
            with self.assertRaises(ValueError): declarations.generate(bad)

    def test_filling_preserves_all_other_bytes_symbols_and_bounds(self):
        empty, table = declarations.empty(), declarations.generate([self.entry()])
        before = b'prefix'*4 + empty + b'identity'+b'guard'*4
        offset, symbols = 24, dict(table=24, arena=0x47080000, guard=1096)
        after = declarations.fill_reserved(before, offset, table)
        self.assertTrue(declarations.assert_stable_layout(before, after, symbols, dict(symbols), offset)['stable'])
        for bad in (offset-1, -1, True, len(before)):
            with self.assertRaises(ValueError): declarations.fill_reserved(before, bad, table)
        with self.assertRaises(ValueError): declarations.fill_reserved(after, offset, table)
        for image, changed in ((after+b'x', symbols), (after, dict(symbols, arena=0x47080010)),
                               (b'changed!'+after[8:], symbols)):
            with self.assertRaises(ValueError): declarations.assert_stable_layout(before, image, symbols, changed, offset)
        changed = after[:1096]+b'Identity'+after[1104:]
        self.assertTrue(declarations.assert_stable_layout(before, changed, symbols, symbols, offset, [(1096,1104)])['stable'])
        with self.assertRaises(ValueError): declarations.assert_stable_layout(before, changed, symbols, symbols, offset, [(20,1102)])

    def test_actual_c_admission_defaults_closed_and_rejects_exact_drift(self):
        cc = shutil.which('cc')
        if not cc: self.skipTest('no C compiler')
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'test'
            sources = [ADAPTER/(name+'.c') for name in ('machine_admission','machine_declarations','machine_lifetime','machine_parts','test_machine_admission')]
            subprocess.run([cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I',str(ADAPTER),
                            '-I',str(ROOT/'sdk/runtime/loader'),'-I',str(ROOT/'sdk/runtime/upload'),*map(str,sources),'-o',str(out)],check=True,capture_output=True)
            subprocess.run([str(out)],check=True,capture_output=True)


if __name__ == '__main__': unittest.main()
