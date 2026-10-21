# SPDX-License-Identifier: GPL-3.0-or-later
"""POST stock-data packing, with computed synthetic words, never firmware."""
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'sdk/machines/octatrack/elekloader'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


post = load('tested_usb_post_recipe', 'usb_post.py')
core = load('tested_post_base_builder', 'build_core.py')


class PostStockData(unittest.TestCase):
    def setUp(self):
        self.words = [round(math.sin(2 * math.pi * i / 1024) * 0x7fffff) for i in range(256)]

    def test_table_is_read_from_core_zero_x_and_generated_only_from_guarded_words(self):
        image = b''.join(w.to_bytes(3, 'little') for w in self.words)
        device = SimpleNamespace(main_load=0x40000000)
        dsp = SimpleNamespace(records=lambda image, device, tag: [(1, 0x6c00, 256, device.main_load)],
                              w24=lambda image, at: int.from_bytes(image[at:at + 3], 'little'))
        self.assertEqual(post.image_words(image, device, dsp), self.words)
        self.assertEqual(post.include(self.words).count('.long '), 256)
        dsp.records = lambda image, device, tag: [(2, 0x6c00, 256, device.main_load)]
        with self.assertRaisesRegex(ValueError, 'does not contain'):
            post.image_words(image, device, dsp)
        for bad in (self.words[:-1], [0] * 256, [True] + self.words[1:], [-1] + self.words[1:],
                    self.words[:10] + [self.words[10] + 65] + self.words[11:]):
            with self.subTest(length=len(bad)):
                with self.assertRaises(ValueError):
                    post.include(bad)

    def test_only_the_named_bounded_data_recipe_can_use_four_byte_words(self):
        fill = post.fill('.run', 2)
        self.assertEqual(post.width(fill), 4)
        self.assertEqual(post.width(dict(fx=4)), 3)
        for key, value in [('curve', 'unknown'), ('tag', 'B'), ('first', 1), ('count', 255),
                           ('offset', 1), ('offset', -2), ('offset', True), ('section', '')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                post.width(dict(fill, **{key: value}))
        with self.assertRaises(ValueError):
            post.width(dict(fill, fx=4))
        with self.assertRaises(ValueError):
            post.width({k: v for k, v in fill.items() if k != 'section'})

    def test_strip_removes_exact_32_bit_table_alongside_old_24_bit_fills(self):
        packed = b''.join(w.to_bytes(4, 'big') for w in self.words)
        original = bytes.fromhex('aabb') + packed + bytes.fromhex('112233ccdd')
        document = dict(sections={'.run': dict(len=len(original), parts=[['hex', original.hex()]])}, sites=[])
        fills = [post.fill('.run', 2), dict(tag='A', fx=4, first=0, count=1, section='.run', offset=1026)]
        recovered = lambda fill: self.words if 'curve' in fill else [0x112233]
        stripped = core.strip(document, fills, recovered, b'', 0)
        self.assertEqual(stripped['sections']['.run']['parts'], [['hex', 'aabb'], ['hex', 'ccdd']])
        self.assertEqual(document['sections']['.run']['parts'], [['hex', original.hex()]])
        with self.assertRaisesRegex(ValueError, 'does not name'):
            core.strip(document, fills, lambda fill: [0] * fill['count'], b'', 0)
        with self.assertRaises(ValueError):
            core.strip(document, [dict(fills[0], curve='unknown')], recovered, b'', 0)


if __name__ == '__main__':
    unittest.main()
