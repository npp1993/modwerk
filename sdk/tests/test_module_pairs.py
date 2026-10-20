# SPDX-License-Identifier: GPL-3.0-or-later
"""Pair table (scripts/module-pairs.py): contexts and the largest clean selections the proof runs the ledger on."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('module_pairs', ROOT / 'scripts/module-pairs.py')
pairs = importlib.util.module_from_spec(spec); spec.loader.exec_module(pairs)


class PairTests(unittest.TestCase):
    def test_contexts(self):
        contexts = pairs.contexts_for(['synth'])
        self.assertEqual(contexts, [(), ('poly8',), ('poly8', 'synth')])
        self.assertEqual(pairs.context_of(['synth', 'vector'], contexts), ())
        self.assertEqual(pairs.context_of(['poly8', 'vector'], contexts), ('poly8',))
        self.assertEqual(pairs.context_of(['synth', 'poly8'], contexts), ('poly8', 'synth'))

    def test_largest_clean_selections(self):
        refused = {frozenset(p) for p in [('a', 'b'), ('b', 'c')]}
        found = pairs.maximal_cliques(['a', 'b', 'c', 'd'], lambda x, y: frozenset((x, y)) not in refused)
        self.assertEqual(sorted(found), [['a', 'c', 'd'], ['b', 'd']])

    def test_an_fx2_buffer_meets_a_range_declared_in_its_slot_tail(self):
        import sys
        from types import SimpleNamespace as Mod
        sys.path.insert(0, str(ROOT / 'sdk/octabam/tools'))
        from remix.schema import Claims, DspRange
        # Sidechain Compressor's key window: the last 514 words of the bank-track-3 FX2 slot on each core.
        holder = Mod(name='holder', dsp=None, claims=Claims(dsp_ranges=(DspRange('y', 0x3dfe, 0x202, 'key window', half_relative=True),)))
        effect = lambda **c: Mod(name='effect', dsp=None, claims=Claims(stock_instance_buffer=True, **c))
        self.assertEqual(len(pairs.slot_tail_meetings([holder, effect(buffer_words=16384)])), 2)  # T7 on core A, T3 on core B
        self.assertTrue(pairs.slot_tail_meetings([effect(), holder]))                            # undeclared: the whole slot
        self.assertFalse(pairs.slot_tail_meetings([holder, effect(buffer_words=15870)]))         # stops at +$3dfd
        self.assertFalse(pairs.slot_tail_meetings([holder, effect(fx1_only=True, buffer_words=2048)]))


if __name__ == '__main__':
    unittest.main()
