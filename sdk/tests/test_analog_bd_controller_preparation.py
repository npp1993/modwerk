# SPDX-License-Identifier: MIT
"""Register closed private Analog BD port preparation regressions."""
import importlib.util
from pathlib import Path
import sys

adapter = Path(__file__).resolve().parents[1] / 'machines/octatrack/module-adapters'
sys.path.append(str(adapter))  # Keep SDK wrappers first during unittest discovery.
spec = importlib.util.spec_from_file_location('private_analog_bd_preparation_tests', adapter / 'analog_bd_preparation_tests.py')
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
SourceTests = tests.SourceTests
NativeTests = tests.NativeTests
ObservationTests = tests.ObservationTests
PriceTests = tests.PriceTests
