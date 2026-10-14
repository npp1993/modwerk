#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a private ot_emu with accurate Modwerk idle-loop bounds; upstream files stay exact.

python3 -B scripts/octatrack-emulator/build.py --native ~/.cache/modwerk-upstream/octabam --out /private/tmp/abi7-emu
Needs the native checkout's already-built out/emu archives (make setup && make emu-cf there).
No firmware is read or written. Run under the machine-wide build/check lock.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent

def build(native, out):
    out.mkdir(parents=True, exist_ok=False)
    source = native / 'tools/emu/ot_emu'
    rtos = (source / 'rtos.cpp').read_text()
    old = 'm_spinLo = m_machine.peek32(g_mainSpin - 4);\n\t\t\tm_spinHi = m_spinLo + 0x80;'
    new = 'const auto entry = m_machine.peek32(g_mainSpin - 4);\n            const auto range = modwerkIdleRange(entry, [this](uint32_t at) { return m_machine.read16(at); });\n            // Unknown detours are stepped normally, never assumed to be idle.\n            m_spinLo = range.first;\n            m_spinHi = range.second;'
    if rtos.count(old) != 1:
        raise ValueError('Native idle detector changed; review this adapter before rebuilding.')
    (out / 'rtos.cpp').write_text('#include "idle-range.h"\n' + rtos.replace(old, new))
    libraries = [native / 'out/emu/libot_machine.a', native / 'out/emu/mc68k/lib68kEmu.a',
                 native / 'out/emu/dsp56300/dsp56kEmu/libdsp56kEmu.a', native / 'out/emu/dsp56300/dsp56kBase/libdsp56kBase.a', native / 'out/emu/dsp56300/asmjit/libasmjit.a']
    # Newer native checkouts build the DSP JIT with VTune's profiling hooks in their own archive.
    libraries += [p for p in (native / 'out/emu/dsp56300/vtuneSdk/libvtuneSdk.a',) if p.is_file()]
    # Record exact inputs, including the archives whose source built the remaining machine.
    inputs = [source / 'rtos.cpp', source / 'rtos.h', source / 'main.cpp', *libraries, HERE / 'idle-range.h', Path(__file__)]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    flags = ['/usr/bin/c++', '-O3', '-DNDEBUG', '-flto', '-std=c++17', '-I' + str(HERE),
             '-I' + str(source), '-I' + str(native / 'vendor'), '-I' + str(native / 'vendor/dsp56300/source')]
    subprocess.run(flags + [str(source / 'main.cpp'), str(out / 'rtos.cpp'), *map(str, libraries), '-lpthread', '-o', str(out / 'ot_emu')], check=True)
    hashes['output'] = hashlib.sha256((out / 'ot_emu').read_bytes()).hexdigest()
    (out / 'inputs.json').write_text(json.dumps(hashes, indent=2) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.native.expanduser().resolve(), args.out.resolve())
