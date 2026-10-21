# SPDX-License-Identifier: GPL-3.0-or-later
"""Source staging guards and actual GNU assembly; no stock file or device."""
import hashlib
import importlib.util
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


base = load('profiles_usb_base', ROOT / 'sdk/machines/octatrack/elekloader/usb_base.py')
functions = load('profiles_usb_functions', ROOT / 'sdk/machines/octatrack/module-adapters/base_usb_functions.py')
profiles = load('profiles_source', ROOT / 'sdk/machines/octatrack/module-adapters/usb-audio-profiles/profiles.py')
post = load('profiles_post_curve', ROOT / 'sdk/machines/octatrack/elekloader/usb_post.py')
normal = load('profiles_normal_descriptors', base.AUDIO_DESCRIPTORS)
post_desc = load('profiles_post_descriptors', base.POST_AUDIO_DESCRIPTORS)
# Mathematical fixture, never an extracted stock table.
CURVE = [round(math.sin(2 * math.pi * i / 1024) * 0x7fffff) for i in range(256)]


def prepare(initial):
    return profiles.prepare(base, functions, normal, post_desc, post, CURVE, initial)


class UsbAudioProfiles(unittest.TestCase):
    def test_readiness_transform_refuses_changed_reader_or_cushion(self):
        raw = base.AUDIO_SOURCE.read_text()
        for changed in (raw.replace('audio_cushion_zero:\n', 'changed_cushion:\n'),
                        raw.replace('    movel   aud_produced,%d0', '    nop', 1),
                        raw.replace('    moveq   #AUD_TARGET-1,%d1', '    moveq #1,%d1'),
                        raw.replace('.set MAIN_CUE_LAG_BLOCKS, 1', '.set MAIN_CUE_LAG_BLOCKS, 2'),
                        raw.replace('.set CUE_MASTER_LAG_BLOCKS,  2', '.set CUE_MASTER_LAG_BLOCKS,  3')):
            with self.subTest(changed=hashlib.sha256(changed.encode()).hexdigest()), self.assertRaises(ValueError):
                functions.packet_readiness(changed)

    def test_changed_producer_and_invalid_initial_profile_fail_closed(self):
        for invalid in (None, '', True, 'USB AUDIO IN AB'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                prepare(invalid)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changed.s'
            path.write_text(base.AUDIO_SOURCE.read_text() + '\n| changed\n')
            with self.assertRaisesRegex(ValueError, 'producer changed'):
                profiles.checked_source(path, profiles.AUDIO_SHA256[0])

    def test_all_inputs_are_bound_and_templates_have_no_unresolved_seams(self):
        for initial in functions.AUDIO_LAYOUTS:
            with self.subTest(initial=initial):
                sources, inputs = prepare(initial)
                self.assertEqual(set(sources), {'usbaudio.s', 'usb_audio_profile_data.c',
                                               'usb_audio_profile_stage.c', 'usb_audio_profiles.h'})
                self.assertNotIn('@INITIAL_', sources['usbaudio.s'])
                self.assertNotIn('.include ', sources['usbaudio.s'])
                for path, digest in inputs.items():
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                self.assertIn(base.AUDIO_SOURCE, inputs)
                self.assertIn(base.POST_AUDIO_SOURCE, inputs)
                self.assertEqual({p.name for p in profiles.HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.s', '.c', '.h')},
                                 {p.name for p in inputs if p.parent == profiles.HERE})

    @unittest.skipUnless(shutil.which('m68k-elf-as') and shutil.which('m68k-elf-nm'), 'GNU ColdFire toolchain not installed')
    def test_actual_assembler_resolves_six_producers_and_initial_counter_alias(self):
        for initial in ('USB AUDIO OUT TRACKS MAIN CUE', post.LAYOUT):
            with self.subTest(initial=initial), tempfile.TemporaryDirectory() as directory:
                directory = Path(directory)
                sources, _ = prepare(initial)
                (directory / 'usbaudio.s').write_text(sources['usbaudio.s'])
                subprocess.run(['m68k-elf-as', '-mcpu=54455', '-o', str(directory / 'audio.o'),
                                str(directory / 'usbaudio.s')], check=True, capture_output=True)
                undefined = subprocess.check_output(['m68k-elf-nm', '-u', str(directory / 'audio.o')], text=True)
                self.assertEqual({line.split()[-1] for line in undefined.splitlines()},
                                 {'usbmidi_rx_isr_shim', 'mu_audio_stage_locked'})
                symbols = {}
                for line in subprocess.check_output(['m68k-elf-nm', str(directory / 'audio.o')], text=True).splitlines():
                    fields = line.split()
                    if len(fields) == 3:
                        symbols[fields[2]] = (int(fields[0], 16), fields[1].upper())
                selected = functions.AUDIO_LAYOUTS[initial]
                self.assertEqual(symbols['usbaudio_alt'], symbols['p%d_usbaudio_alt' % selected])
                self.assertEqual(symbols['post_frame'], symbols['p5_post_frame'])
                for index in range(6):
                    self.assertIn('p%d_audio_frame_shim' % index, symbols)
                    self.assertEqual(symbols['p%d_aud_ring' % index], symbols['shared_ring'])

    def test_cli_requires_explicit_staging_setup_before_reading_stock(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'never-created'
            command = [sys.executable, '-B', str(ROOT / 'sdk/machines/octatrack/elekloader/build_core.py'),
                       '--stock', str(Path(directory) / 'absent.bin'), '--upstream', directory,
                       '--output', str(output), '--usb-audio-profiles']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('--usb-audio-profiles needs', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
