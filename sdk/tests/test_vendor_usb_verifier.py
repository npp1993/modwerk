# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact private verifier expectations; authored descriptors, no firmware."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('private_vendor_usb_verifier', ROOT / 'sdk/machines/octatrack/elekloader/verify_vendor_usb.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class VendorDescriptorExpectations(unittest.TestCase):
    def test_legacy_and_development_expectations_remain_exact(self):
        for hs in (False, True):
            for audio in (False, True):
                self.assertEqual(verifier.descriptor_expectations(hs, audio),
                    (verifier.usb.configuration(hs, False, audio),
                     verifier.usb.configuration(not hs, True, audio), verifier.usb.device(audio)))
            self.assertEqual(verifier.audio_shape(hs), (*verifier.usb.AUDIO_INTERFACES, 16 if hs else 8))

    def test_composite_midi_and_each_output_layout_have_complete_descriptors(self):
        for hs in (False, True):
            for audio in (None, *verifier.functions.AUDIO_LAYOUTS):
                with self.subTest(high_speed=hs, audio=audio):
                    chosen = dict(midi='bounded-rx-1', audio=audio)
                    cfg, other, device = verifier.descriptor_expectations(hs, composite=chosen)
                    self.assertEqual(cfg, verifier.functions.configuration(verifier.usb, verifier.descriptor_source(audio), hs, False, audio))
                    self.assertEqual(other, verifier.functions.configuration(verifier.usb, verifier.descriptor_source(audio), not hs, True, audio))
                    self.assertEqual(device, verifier.usb.device(True))
                    self.assertEqual(other[1], 7)
                    self.assertEqual(int.from_bytes(other[2:4], 'little'), len(other))
                    if audio:
                        self.assertGreater(len(other), 255)
                        channels = verifier.descriptor_source(audio).HS_LAYOUT[audio][0] if hs else verifier.descriptor_source(audio).FS_CHANNELS
                        self.assertEqual(verifier.audio_shape(hs, audio), (4, 5, channels * 4))

    def test_unreviewed_midi_and_input_layouts_are_refused(self):
        for chosen in (dict(midi='unknown', audio=None), dict(midi='bounded-rx-1', audio='USB AUDIO IN AB')):
            with self.assertRaises(ValueError):
                verifier.descriptor_expectations(True, composite=chosen)


if __name__ == '__main__':
    unittest.main()
