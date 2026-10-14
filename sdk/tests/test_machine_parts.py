# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure active/saved Part ownership checks; no firmware."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'machines/octatrack/module-adapters'

class MachineParts(unittest.TestCase):
    def test_every_ram_sram_part_and_track_is_checked(self):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('no host C compiler')
        with tempfile.TemporaryDirectory() as work:
            subprocess.run([cc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-I', ROOT,
                            ROOT / 'machine_parts.c', ROOT / 'test_machine_parts.c', '-o', work + '/parts'],
                           check=True, capture_output=True)
            result = subprocess.run([work + '/parts'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
