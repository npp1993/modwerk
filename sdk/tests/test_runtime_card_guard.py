# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual native loader/card integration, synthetic data and no stock input."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RuntimeCardGuard(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc') or shutil.which('gcc'), 'Native C compiler unavailable')
    def test_actual_loader_and_card_restore_reject_moved_resource_word(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / ('card-guard.exe' if os.name == 'nt' else 'card-guard')
            command = [shutil.which('cc') or shutil.which('gcc'), '-std=c99', '-Wall', '-Wextra', '-Werror',
                       '-DMODWERK_HOST', '-I' + str(ROOT / 'sdk/runtime/upload'),
                       '-I' + str(ROOT / 'sdk/runtime/loader'), str(ROOT / 'sdk/tests/runtime_card_guard.c'), '-o', str(binary)]
            subprocess.run(command, check=True, capture_output=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn('no card writes or module execution', result.stdout)
