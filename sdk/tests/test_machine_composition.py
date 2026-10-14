# SPDX-License-Identifier: MIT
"""Register guarded runtime machine composition regressions with the SDK suite."""
import importlib.util
from pathlib import Path
import sys

adapter = Path(__file__).resolve().parents[1] / 'machines/octatrack/module-adapters'
sys.path.append(str(adapter))  # Keep SDK wrappers first during unittest discovery.
spec = importlib.util.spec_from_file_location('runtime_machine_composition_tests', adapter / 'machine_composition_tests.py')
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
SourceTests = tests.SourceTests
ManifestTests = tests.ManifestTests
LinkTests = tests.LinkTests
HostTests = tests.HostTests
LifetimeTests = tests.LifetimeTests
