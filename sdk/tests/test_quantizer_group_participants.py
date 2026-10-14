# SPDX-License-Identifier: MIT
"""Optional QZ ownership requires exact independently reviewed participants."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / 'sdk/machines/octatrack/module-adapters'
sys.path.append(str(ADAPTER))
import machine_layout as layout
import machine_declarations as declarations
import quantizer_runtime as quantizer
fixtures = importlib.import_module('test_machine_layout')


class ParticipantTests(unittest.TestCase):
    setUp = fixtures.LayoutTests.setUp
    declaration = fixtures.LayoutTests.declaration

    def entry(self, mask, optional=False, **changes):
        data = bytearray(self.package)
        data[81] = mask
        doc, recipe, _ = self.declaration(bytes(data))
        value = json.loads(doc)
        value.update(schema=layout.PARTICIPANT_SCHEMA,
                     participants=list(layout.canonical_participants(mask, optional)))
        value.update(changes)
        doc = fixtures.encoded(value)
        return dict(package=bytes(data), declaration=doc, recipe=recipe,
                    reviewed_sha256=hashlib.sha256(doc).hexdigest(), source_root=self.root)

    def test_each_optional_canonical_subset_sets_only_exact_trusted_bit(self):
        for mask in range(1, 8):
            for optional in (False, True):
                entry = self.entry(mask, optional)
                checked = layout.validate(**entry)
                table = declarations.generate([entry])
                expected = int(optional and not mask & 4)
                self.assertEqual(checked.optional_quantizer, bool(expected))
                self.assertEqual(table[53], expected)
                self.assertEqual((len(table), table[52]), (1072, mask))

    def test_absent_duplicate_renamed_reordered_and_mask_drift_refused(self):
        for values in ([], ['quantizer'], ['poly8', 'poly8', 'quantizer'],
                       ['quantizer', 'poly8'], ['poly8', 'synth', 'quantizer'],
                       ['poly8', 'Quantizer']):
            with self.subTest(participants=values), self.assertRaises(ValueError):
                layout.validate(**self.entry(1, participants=values))
        entry = self.entry(1, True)
        doc = json.loads(entry['declaration'])
        del doc['participants']
        entry['declaration'] = fixtures.encoded(doc)
        entry['reviewed_sha256'] = fixtures.sha(entry['declaration'])
        with self.assertRaises(ValueError):
            layout.validate(**entry)
        with self.assertRaisesRegex(ValueError, 'Duplicate trusted package'):
            declarations.generate([self.entry(1), self.entry(1, True)])

    def test_original_quantizer_sources_are_pinned_and_only_mailboxes_move(self):
        sdk = ROOT / 'sdk/octabam/modules/quantizer/upstream/quantizer'
        for name in quantizer.PINS:
            original = (sdk / name).read_text()
            changed = quantizer.source_variant(name, original)
            with self.assertRaisesRegex(ValueError, 'source changed'):
                quantizer.source_variant(name, original + '\n')
            if name != 'quantizer.s':
                self.assertEqual(changed, original)
            else:
                self.assertIn('.set    KEYS_AT, qz_pkey', changed)
                self.assertIn('.set    SCALE_AT, qz_scale_at', changed)
                self.assertNotIn('movea.l #sy_render', changed)
                self.assertIn('KIND_FLEX', changed)


if __name__ == '__main__':
    unittest.main()
