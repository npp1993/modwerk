#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Require byte-identical stock RTOS gate reports with and without the private idle adapter.

Run under the shared build lock after build.py. The caller supplies a private unpacked MAIN OS.
"""
import argparse, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent

def verify(native, adapter, stock):
    if not stock.is_file():
        raise FileNotFoundError('Supply an existing private stock MAIN image: ' + str(stock))
    source = native / 'tools/emu/ot_emu'
    archives = [native / 'out/emu/libot_machine.a', native / 'out/emu/mc68k/lib68kEmu.a',
        native / 'out/emu/dsp56300/dsp56kEmu/libdsp56kEmu.a', native / 'out/emu/dsp56300/dsp56kBase/libdsp56kBase.a',
        native / 'out/emu/dsp56300/asmjit/libasmjit.a']
    flags = ['/usr/bin/c++', '-O3', '-DNDEBUG', '-flto', '-std=c++17', '-I' + str(HERE),
        '-I' + str(source), '-I' + str(native / 'vendor'), '-I' + str(native / 'vendor/dsp56300/source')]
    reports = []
    for label, units in [('reference', []), ('adapted', [adapter / 'rtos.cpp'])]:
        binary = adapter / ('stock-gate-' + label)
        subprocess.run(flags + [str(source / 'test_rtos.cpp'), *map(str, units), *map(str, archives), '-lpthread', '-o', str(binary)], check=True)
        report = subprocess.run([str(binary), str(stock)], check=True, capture_output=True).stdout
        if b'rtos gate passed.' not in report:
            raise ValueError('The stock gate did not execute successfully: ' + label)
        (adapter / ('stock-gate-' + label + '.txt')).write_bytes(report)
        reports.append(report)
    if reports[0] != reports[1]:
        raise ValueError('Stock RTOS gate reports differ; inspect the two private reports.')
    print('Stock RTOS gates passed and reports are byte-identical, including the serial negative control.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--stock', type=Path, required=True)
    args = parser.parse_args()
    verify(args.native.expanduser().resolve(), args.adapter.resolve(), args.stock.resolve())
