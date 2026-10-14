# SPDX-License-Identifier: MIT
"""Private source-bound AB descriptor preparation; DSP admission remains closed.

This helper does not establish controller generation readiness, owned DSP jobs,
Part-root retirement, audio or hardware qualification. Call only from the
explicit private shared-controller preparation, never public package admission.
"""
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess

PINS = {
    'manifest.py': '20fa1f744630354b3986a3ad82ac6a41744345796dc783891a4c9f0bd81c787e',
    'control.c': '29f392c7e007aaa695076eff0c897729a941676ff582e4bb17957074d56ceac5',
    'control.s': '644f10fbc534d8351424e55ee96c2d0ff2f39a1b691ad8a695422d1c05e37a3f',
    'engine.h': '61bc45ef955db23b8f25eb5b0c6bd3dd01d9f71df7933d466845bb30e7c67a2b',
    'engine.s': 'c86a6ac24326fb52f71dd766b1ccc25e5dfd8511028b162459447c279da48425',
    'machine.s': '90f9ddb5c2a4cee47e0334c3cd35a7e92d42b0ee37eb3bbc8062cc7821e6aeb4',
}


def control_source(original):
    if hashlib.sha256(original.encode()).hexdigest() != PINS['control.c']:
        raise ValueError('Reviewed Analog BD controller source changed.')
    seams = (
        ('U32(0x400d5f38u+5*4)=page_for(0); return;', '(void)page_for(0); return;'),
        ('U32(0x400d5f38u+5*4)=ab_track_page(part+0x22+(U8(0x100b14ccu)&7));',
         '(void)ab_track_page(part+0x22+(U8(0x100b14ccu)&7));'),
    )
    for before, after in seams:
        if original.count(before) != 1:
            raise ValueError('Analog BD private descriptor seam changed.')
        original = original.replace(before, after)
    # page_for uses the address one past its two 458-byte descriptors as a
    # comparison sentinel. Keep that address inside the owned runtime image,
    # including AB+FM object order where desc would otherwise end the image.
    # This is authored initialized storage, never a stock copy or bounds waiver.
    return original + '''
__attribute__((used,section(".data.ab_runtime_bound")))
static uint32_t ab_runtime_bound=0;
'''


def port(module, sdk_root, work, cross='m68k-elf-'):
    if module.name != 'analog-bassdrum':
        raise ValueError('Analog BD preparation received another module.')
    sdk = Path(sdk_root).resolve()
    upstream = sdk / 'modules/analog-bassdrum'
    for name, digest in PINS.items():
        if hashlib.sha256((upstream / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Reviewed Analog BD source changed: ' + name)
    # Require every original CF unit. Do not silently drop unknown DSP or CF
    # claims; the enclosing composition and ordinary builder still reject them.
    from remix.schema import Linked
    for label, name in [('abmachine', 'machine.s'), ('abcontrol', 'control.s'), ('abengine', 'engine.s')]:
        units = [u for u in module.linked if u.label == label]
        if len(units) != 1:
            raise ValueError('Analog BD preparation needs each original controller unit once.')
        unit = units[0]
        path = Path(unit.source)
        path = path if path.is_absolute() else sdk / path
        expected = Linked(label, 'modules/analog-bassdrum/' + name, dram=True)
        if path.resolve() != (upstream / name).resolve() or replace(unit, source=expected.source) != expected:
            raise ValueError('Analog BD controller declaration drift: ' + label)
    folder = Path(work).resolve(); folder.mkdir(parents=True, exist_ok=True)
    source, assembly = folder / 'analog-bd-runtime-control.c', folder / 'analog-bd-runtime-control.s'
    source.write_text(control_source((upstream / 'control.c').read_text()))
    from machine_composition import FLAGS
    subprocess.run([cross + 'gcc', *FLAGS, '-I', str(upstream), '-S', str(source), '-o', str(assembly)],
                   check=True, capture_output=True)
    return replace(module, linked=tuple(replace(u, source=str(assembly), dram=True, cave_addr=None)
                                        if u.label == 'abcontrol' else u for u in module.linked))
