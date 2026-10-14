#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private native AB fixtures over the actual composed images; no admission.

Queue under the machine lock. Original MAIN, linked images, logs and the
receipt stay in a new private directory outside Git; firmware never enters CI.
Analog BD alone (its own units; the base machine registry owns the shared
chooser seams in the events model) is linked fresh at two origins and must
relocate exactly.
The loader's stock copies are filled from the original MAIN, as it would on the
device. Fixture lease functions and helper identities are synthetic: this proves
authored ColdFire behaviour only, never board ACKs, generations, DSP audio,
retirement closure, physical timing or hardware.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
ADAPTER = Path(__file__).resolve().parent
SDK = ROOT / 'sdk/octabam'
sys.path.insert(0, str(ADAPTER))
import machine_composition  # noqa: E402

_spec = importlib.util.spec_from_file_location('analog_bd_private_paths', ROOT / 'scripts/runtime_private_paths.py')
_private = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_private)
MAIN_SHA256 = '164f31224bf61181e3f50e7dec40df9afcae5b16dbf6e4c0d0cc5e986af0a84e'
MAIN_LOAD = 0x40000400
ARCHIVES = ('libot_machine.a', 'mc68k/lib68kEmu.a', 'dsp56300/dsp56kEmu/libdsp56kEmu.a',
            'dsp56300/dsp56kBase/libdsp56kBase.a', 'dsp56300/asmjit/libasmjit.a')
ORIGINS = (0x47080000, 0x47100000)
HELPER = 0x47400000
FIXTURES = {'lease': 'analog_bd_write_lease_probe.cpp', 'ui': 'analog_bd_ui_fixture.cpp'}
PREPARATION = ('analog_bd_runtime.py', 'analog_bd_write_lease.py', 'machine_composition.py',
               'stock_hook_write_lease.h', 'analog_bd_write_lease_fixture.c', 'analog_bd_ui.c', 'analog_bd_ui.h',
               'analog_bd_ui_driver.c', 'machine_lifetime.c', 'machine_lifetime.h', 'probe_analog_bd.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(command, **kwargs):
    return subprocess.run([str(c) for c in command], check=True, capture_output=True, text=True, **kwargs)


def selected():
    sys.path.insert(0, str(SDK / 'tools'))
    from remix import registry
    old = Path.cwd()
    try:
        os.chdir(SDK)
        return registry._load_one(SDK / 'modules/analog-bassdrum/manifest.py')
    finally:
        os.chdir(old)


def link(objects, origin, work, bss=False):
    script, elf, binary = work / 'link.ld', work / 'linked.elf', work / 'linked.private.raw'
    script.write_text('SECTIONS { . = ' + hex(origin) + '; .text : { *(.text*) *(.rodata*) *(.data*) } .bss : { *(.bss*) *(COMMON) } '
                      '/DISCARD/ : { *(.comment) *(.note*) *(.eh_frame) } }')
    run(['m68k-elf-ld', '--no-warn-rwx-segments', '-T', script, '-o', elf, *objects])
    table = run(['m68k-elf-nm', '-S', elf]).stdout
    kinds = {line.split()[-2] for line in table.splitlines() if len(line.split()) >= 2}
    if 'U' in kinds or not bss and kinds & {'B', 'b'}:
        raise ValueError('A private AB image has unresolved imports or BSS.')
    symbols, sizes = {}, {}
    for line in table.splitlines():
        parts = line.split()
        if len(parts) in (3, 4):
            symbols[parts[-1]] = int(parts[0], 16) - origin
            if len(parts) == 4:
                sizes[parts[-1]] = int(parts[1], 16)
    run(['m68k-elf-objcopy', '-O', 'binary', elf, binary])
    return binary.read_bytes(), symbols, sizes


def compose(lease, work, main):
    """Fresh AB units, two native origins, exact relocation, then stock copies."""
    import analog_bd_runtime, analog_bd_write_lease
    port = analog_bd_write_lease.port if lease else analog_bd_runtime.port
    result = [port(selected(), SDK, work / 'source')]
    objects, copies = [], []
    for index, unit in enumerate(u for m in result for u in m.linked):
        obj = work / ('%d.o' % index)
        source = Path(unit.source)
        run(['m68k-elf-as', '-mcpu=54455', source if source.is_absolute() else SDK / source, '-o', obj], cwd=SDK)
        if unit.exports:
            run(['m68k-elf-objcopy', *['--globalize-symbol=' + n for n in unit.exports], obj])
        objects.append(obj)
        copies += [(c.symbol, c.span.address, c.span.length, c.span.sha256) for c in unit.stock_copies]
    if lease:
        obj, asm = work / 'lease-fixture.o', work / 'lease-fixture.s'  # same -S then ISA-C assembly as the units
        run(['m68k-elf-gcc', *machine_composition.FLAGS, '-S', ADAPTER / 'analog_bd_write_lease_fixture.c', '-o', asm])
        run(['m68k-elf-as', '-mcpu=54455', asm, '-o', obj])
        objects.append(obj)
    images = [link(objects, origin, work) for origin in ORIGINS]
    (low, symbols, sizes), (high, other, _) = images
    inside = lambda table: {k: v for k, v in table.items() if 0 <= v <= len(low)}  # absolute .set values excluded
    symbols = inside(symbols)
    if symbols != inside(other) or len(low) != len(high):
        raise ValueError('The AB image changes layout between native origins.')
    delta, expected, at = ORIGINS[1] - ORIGINS[0], bytearray(low), 0
    while at + 4 <= len(low):
        a, b = int.from_bytes(low[at:at + 4], 'big'), int.from_bytes(high[at:at + 4], 'big')
        if b - a == delta and ORIGINS[0] <= a < ORIGINS[0] + len(low):
            expected[at:at + 4] = b.to_bytes(4, 'big');at += 4
        else:
            at += 2
    if bytes(expected) != high:
        raise ValueError('The AB image has a non-relocatable difference between origins.')
    offsets = [at for at in range(0, len(low) - 3, 2) if int.from_bytes(high[at:at + 4], 'big') - int.from_bytes(low[at:at + 4], 'big') == delta]
    filled = bytearray(low)
    for symbol, address, length, digest in copies:
        stock = main[address - MAIN_LOAD:address - MAIN_LOAD + length]
        start = symbols[symbol]
        if sha(stock) != digest or any(filled[start:start + length]):
            raise ValueError('A loader stock copy differs from original stock or overlaps authored bytes: ' + symbol)
        filled[start:start + length] = stock
    return bytes(filled), offsets, symbols, sizes, len(copies)


def placed(image, offsets, origin):
    out = bytearray(image)
    for at in offsets:
        out[at:at + 4] = (int.from_bytes(out[at:at + 4], 'big') - ORIGINS[0] + origin).to_bytes(4, 'big')
    return bytes(out)


def helper_image(work):
    objects = []
    for name in ('analog_bd_ui', 'machine_lifetime', 'analog_bd_ui_driver'):
        obj = work / (name + '.o')
        run(['m68k-elf-gcc', '-mcpu=5475', '-msoft-float', '-O2', '-ffreestanding', '-fno-builtin', '-fno-jump-tables',
             '-fno-asynchronous-unwind-tables', '-fomit-frame-pointer', '-Wall', '-Wextra', '-Werror', '-I' + str(ADAPTER),
             '-I' + str(ROOT / 'sdk/runtime/loader'), '-I' + str(ROOT / 'sdk/runtime/upload'), '-c', ADAPTER / (name + '.c'), '-o', obj])
        objects.append(obj)
    image, symbols, _ = link(objects, HELPER, work, bss=True)  # synthetic helper state only
    return image, symbols


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--summary', type=Path, help='hash-only repository observations (analog_bd_native_observations.json)')
    args = parser.parse_args()
    main_image = args.main.read_bytes()
    if sha(main_image) != MAIN_SHA256:
        raise ValueError('The AB fixtures require the exact original reviewed 1.40C MAIN.')
    os.umask(0o077)
    out = _private.private_directory(args.out)
    if any(out.iterdir()):
        raise ValueError('Use a new empty private fixture output directory.')
    native = args.native.expanduser().resolve()
    archives = [native / 'out/emu' / path for path in ARCHIVES]
    if not all(path.is_file() for path in archives):
        raise ValueError('Built native Octabam emulator archives are required.')
    inputs = {name: sha((ADAPTER / name).read_bytes()) for name in (*PREPARATION, *FIXTURES.values())}
    executables = {}
    for key, name in FIXTURES.items():
        executables[key] = out / ('probe-' + key)
        run(['c++', '-O2', '-std=c++17', '-I' + str(native / 'tools/emu/ot_emu'), '-I' + str(native / 'vendor'),
             '-I' + str(native / 'vendor/dsp56300/source'), ADAPTER / name, *archives, '-lpthread', '-o', executables[key]])
    helper_dir = out / 'ui-helper';helper_dir.mkdir()
    helper, helper_symbols = helper_image(helper_dir)
    _private.save(helper_dir / 'helper.private.raw', helper)
    _private.save(helper_dir / 'symbols.txt', ''.join('%s %d\n' % item for item in helper_symbols.items()).encode())
    results = []
    def execute(kind, argv, row):
        execution = subprocess.run([str(a) for a in argv], text=True, capture_output=True)
        _private.save(row['work'] / (kind + '-%x.log' % row['origin']), (execution.stdout + execution.stderr).encode())
        if execution.returncode:
            raise ValueError('%s fixture failed for %s at %#x: %s' % (kind, row['variant'], row['origin'], execution.stderr[-400:]))
        observed = json.loads(execution.stdout.strip().splitlines()[-1])
        results.append(dict(fixture=kind, variant=row['variant'], origin=row['origin'], imageBytes=row['bytes'],
                            imageSha256=row['sha256'], stockCopies=row['copies'], observed=observed))
        print(kind, row['variant'], hex(row['origin']), json.dumps(observed), flush=True)
    for lease in (False, True):
        variant = 'ab-lease' if lease else 'ab'
        work = out / variant;work.mkdir()
        image, offsets, symbols, sizes, copies = compose(lease, work, main_image)
        symbol_file = work / 'symbols.txt'
        _private.save(symbol_file, ''.join('%s %d\n' % item for item in symbols.items()).encode())
        for origin in ORIGINS:
            raw = work / ('%x.private.raw' % origin)
            data = placed(image, offsets, origin)
            _private.save(raw, data)
            row = dict(work=work, variant=variant, origin=origin, bytes=len(data), sha256=sha(data), copies=copies)
            if lease:
                execute('lease', [executables['lease'], args.main, raw, symbol_file, hex(origin), sizes['ab_render']], row)
            execute('ui', [executables['ui'], args.main, raw, symbol_file, hex(origin), helper_dir / 'helper.private.raw',
                           helper_dir / 'symbols.txt', variant], row)
    receipt = dict(schema='modwerk-private-ab-native-fixtures-v1', mainSha256=MAIN_SHA256, inputs=inputs,
                   sources={name: sha((SDK / 'modules/analog-bassdrum' / name).read_bytes()) for name in
                            ('manifest.py', 'control.c', 'control.s', 'engine.h', 'engine.s', 'machine.s')},
                   archives={str(path.relative_to(native)): sha(path.read_bytes()) for path in archives},
                   results=results, hardware=False, admission=False, productionLease=False, encodedPackage=False,
                   limits=['Synthetic fixture lease functions and helper identity; no board ACK, generation or retirement proof.',
                           'Executed instructions are not modeled cycles or physical timing. No DSP audio or headroom.',
                           'Part/whole-image/UI foreign-root closure remains open; nothing here clears an AB owner.'])
    _private.save(out / 'receipt.json', receipt)
    if args.summary:
        # Hashes and counts only: no stock bytes, images or private paths.
        pins = {'sdk/machines/octatrack/module-adapters/' + name: digest for name, digest in inputs.items()}
        pins.update({'sdk/octabam/modules/analog-bassdrum/' + name: digest for name, digest in receipt['sources'].items()})
        summary = dict(schema='modwerk-private-ab-native-observations-v1', mainSha256=MAIN_SHA256,
                       receiptSha256=sha((out / 'receipt.json').read_bytes()), sourcePins=pins,
                       hardware=False, admission=False, productionLease=False, encodedPackage=False,
                       runs=[{key: row[key] for key in ('fixture', 'variant', 'origin', 'imageSha256', 'observed')} for row in results],
                       limits=receipt['limits'])
        args.summary.write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(dict(runs=len(results), receipt=str(out / 'receipt.json'))))


if __name__ == '__main__':
    main()
