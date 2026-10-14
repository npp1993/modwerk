# SPDX-License-Identifier: GPL-3.0-or-later
"""Runtime catalogue capability metadata follows bounded authored package headers."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('runtime_packages', ROOT / 'sdk/machines/octatrack/elekloader/module_packages.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageMetadataTests(unittest.TestCase):
    def header(self, abi=8, flags=0, sites=0, copies=0, fills=0, hooks=0):
        data = bytearray(76)
        struct.pack_into('>4sHH', data, 0, b'MWRM', abi, flags)
        struct.pack_into('>II', data, 20, hooks, sites)
        struct.pack_into('>II', data, 68, copies, fills)
        return data

    def test_record_types_require_their_base_features(self):
        self.assertEqual(builder.capabilities(self.header(abi=6)), dict(abi=6, features=0, sites=0, copies=0, fills=0))
        self.assertEqual(builder.capabilities(self.header(abi=7, sites=15, copies=1)), dict(abi=7, features=3, sites=15, copies=1, fills=0))
        self.assertEqual(builder.capabilities(self.header(flags=4, sites=85, copies=20, fills=2)), dict(abi=8, features=31, sites=85, copies=20, fills=2))

    def test_site_event_subscribers_require_the_events_feature(self):
        data = self.header(hooks=5, sites=13) + struct.pack('>5I', *[0xffffffff] * 4, 50 << 24 | 0x40)
        self.assertEqual(builder.capabilities(data), dict(abi=8, features=129, sites=13, copies=0, fills=0))
        for data in (self.header(abi=7, hooks=5) + struct.pack('>5I', *[0xffffffff] * 4, 0x40),  # ABI 8 only
                     self.header(hooks=5)):  # truncated hook words
            with self.subTest(data=bytes(data[:8])), self.assertRaises(ValueError):
                builder.capabilities(data)

    def test_unsupported_or_truncated_headers_fail_closed(self):
        for data in (self.header(abi=4), self.header()[:71], self.header(abi=6, sites=1),
                     self.header(hooks=1), self.header(flags=8), self.header(abi=7, flags=4),
                     self.header(sites=129), self.header(copies=129), self.header(fills=65), bytes(76)):
            with self.subTest(data=data[:8]), self.assertRaises(ValueError):
                builder.capabilities(data)

    def test_dsp_scan_accepts_abi8_but_refuses_impossible_lengths(self):
        self.assertEqual(builder.dsp_words(self.header()), [b'', b''])
        data = self.header()
        struct.pack_into('>IH', data, 32, 4097, 0)
        with self.assertRaises(ValueError):
            builder.dsp_words(data)


if __name__ == '__main__':
    unittest.main()
