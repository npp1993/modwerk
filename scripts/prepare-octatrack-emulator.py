#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare an isolated, pinned Octatrack emulator with caller-stack cleanup.

The shared upstream checkout and imported SDK stay unchanged. With --build,
run six stock-free gates; neither a stock image nor a card/project is needed.
Serialize builds with the repository's machine-wide check lock.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

from runtime_private_paths import private_directory, save

ROOT = Path(__file__).resolve().parents[1]
PIN = '8250be0c23ca0a0a953cb7e5721e3bdb98dadfe5'
RTOS = 'tools/emu/ot_emu/rtos.cpp'
RTOS_SHA256 = 'b4589de516372e21211b37b6f68511f23503219a6fbeb3ef1a325dcc130bdfce'
PATHS = ['tools/emu/ot_emu', 'tools/harness', 'modules/tapeecho']
TARGETS = ['ot_emu', 'ot_emac_test', 'ot_periph_test', 'mc68kColdFireTimingTest',
           'mc68kColdFireDivideTest', 'mc68kHdi08ReceiveTest', 'modwerk_call_stack']
GATES = '^(emac|periph|mc68kColdFireTimingTest|mc68kColdFireDivideTest|mc68kHdi08ReceiveTest|modwerk_call_stack)$'


def git(source, *args):
    return subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True).stdout


def patch(text):
    before = 'const auto sp = m_machine.getA7() - 4 * static_cast<uint32_t>(1 + _args.size());'
    after = ('const auto callerSp = m_machine.getA7();\n\t\t'
             'const auto sp = callerSp - 4 * static_cast<uint32_t>(1 + _args.size());')
    old_return = '\t\t\t_d0 = m_machine.getD0();\n\t\t\treturn true;'
    new_return = ('\t\t\t_d0 = m_machine.getD0();\n'
                  '\t\t\t// The borrowed C caller discards its arguments after a confirmed return.\n'
                  '\t\t\t// Leave a failed/incomplete call intact for diagnosis.\n'
                  '\t\t\tm_machine.setA7(callerSp);\n\t\t\treturn true;')
    if text.count(before) != 1 or text.count(old_return) != 1:
        raise ValueError('The pinned borrowed-call implementation changed.')
    return text.replace(before, after).replace(old_return, new_return)


def prepare(source, output, build=False):
    source = source.resolve()
    if git(source, 'rev-parse', 'HEAD').decode().strip() != PIN:
        raise ValueError('Use the reviewed Octabam tools checkout at ' + PIN + '.')
    if hashlib.sha256((source / RTOS).read_bytes()).hexdigest() != RTOS_SHA256:
        raise ValueError('The upstream RTOS source differs from the reviewed input.')
    # The two documented hardware-tool repairs are outside these source trees.
    if git(source, 'status', '--porcelain', '--untracked-files=no', '--', *PATHS, 'vendor'):
        raise ValueError('The emulator, harness, module or vendor sources have local changes.')
    if output.exists():
        raise ValueError('Choose a new private output directory.')
    output = private_directory(output)
    prepared = output / 'source'
    archive = git(source, 'archive', '--format=tar', PIN, *PATHS)
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        for item in files:
            relative = PurePosixPath(item.name)
            if relative.is_absolute() or '..' in relative.parts or not (item.isdir() or item.isfile()):
                raise ValueError('Unsupported path in the pinned source archive.')
            target = prepared.joinpath(*relative.parts)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if item.isdir():
                target.mkdir(mode=0o700, exist_ok=True)
            else:
                data = files.extractfile(item)
                if data is None:
                    raise ValueError('The pinned source archive is incomplete.')
                save(target, data.read())
    rtos = prepared / RTOS
    updated = patch(rtos.read_text())
    rtos.write_text(updated)
    fixture = ROOT / 'scripts/fixtures/octatrack-emulator-call-stack.cpp'
    test = rtos.parent / 'test_modwerk_call_stack.cpp'
    save(test, fixture.read_bytes())
    cmake = rtos.parent / 'CMakeLists.txt'
    with cmake.open('a') as file:
        file.write('\nadd_executable(modwerk_call_stack test_modwerk_call_stack.cpp)\n'
                   'target_link_libraries(modwerk_call_stack PRIVATE ot_machine)\n'
                   'add_test(NAME modwerk_call_stack COMMAND modwerk_call_stack)\n')
    receipt = dict(kind='isolated-octatrack-emulator', upstream=PIN,
                   sourceRtosSha256=RTOS_SHA256, patchedRtosSha256=hashlib.sha256(updated.encode()).hexdigest(),
                   regressionSha256=hashlib.sha256(fixture.read_bytes()).hexdigest(), built=False,
                   limitations=['Six stock-free gates do not qualify firmware, a project, DSP pairing or hardware.',
                                'Shared checkout, cached binaries and imported SDK are unchanged.'])
    if build:
        directory = output / 'build'
        subprocess.run(['cmake', '-S', str(rtos.parent), '-B', str(directory),
                        '-DCMAKE_BUILD_TYPE=Release', '-DOT_VENDOR=' + str(source / 'vendor')], check=True)
        subprocess.run(['cmake', '--build', str(directory), '--target', *TARGETS, '-j2'], check=True)
        subprocess.run(['ctest', '--test-dir', str(directory), '--output-on-failure', '-R', GATES], check=True)
        # Do not report a binary built while shared input revisions changed.
        if git(source, 'rev-parse', 'HEAD').decode().strip() != PIN or git(
                source, 'status', '--porcelain', '--untracked-files=no', '--', 'vendor'):
            raise ValueError('The shared vendor inputs changed during the isolated build.')
        binary = directory / ('ot_emu.exe' if os.name == 'nt' else 'ot_emu')
        receipt.update(built=True, gates=6, emulatorSha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    save(output / 'receipt.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    prepare(args.source, args.output, args.build)
