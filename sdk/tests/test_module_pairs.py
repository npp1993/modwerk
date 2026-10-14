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


if __name__ == '__main__':
    unittest.main()
