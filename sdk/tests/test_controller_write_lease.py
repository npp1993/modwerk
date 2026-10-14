# SPDX-License-Identifier: GPL-3.0-or-later
"""The scoped controller write lease against the actual loader ledger (host).

Real prepared owner, geometry-derived canonical extent, exact package SHA
binding, reviewed entry/continuation offsets and the running task's stack.
Synthetic ACKs only: no DSP transport, physical timing or alias split.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'sdk/machines/octatrack/module-adapters/controller-policy'


@unittest.skipUnless(shutil.which('cc'), 'host C compiler unavailable')
class ControllerWriteLease(unittest.TestCase):
    def test_resolver_binds_owned_image_policy_continuations_and_stack(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / 'lease'
            ledger = Path(temp) / 'ledger.c'  # the loader with its private owner ledger reachable
            ledger.write_text('#include "loader.c"\n'
                              'struct runtime_owner *test_owner_identity(unsigned i) { return &owner_identity[i]; }\n'
                              'struct runtime_module *test_owned(unsigned i) { return owned[i]; }\n')
            compiled = subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                                       '-I', ROOT / 'sdk/runtime/loader', '-I', ROOT / 'sdk/runtime/upload', '-I', POLICY,
                                       POLICY / 'test_controller_write_lease.c', ledger,
                                       ROOT / 'sdk/runtime/upload/sha256.c', '-o', binary], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            ran = subprocess.run([binary], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)


if __name__ == '__main__':
    unittest.main()
