# SPDX-License-Identifier: GPL-3.0-or-later
"""Private exact Quantizer mailbox/accessor relocation; no runtime admission.

Original imported files remain unchanged. Shared POLY8 key ownership must be
resolved by the reviewed machine-composition policy before this source port.
"""
from dataclasses import replace
import hashlib
from pathlib import Path
import re

PINS = {
    'keys.s': 'e2ffdbfae34b0828794a4eb4cc229e3efcaed25dc953bf7c05c13f6e37f65587',
    'core.s': '2992b6c85cff440de03ae84eb22dee8b8a83a84f23e94b699404d28940b6f958',
    'scale.s': '82242c407847ac61a6f60fe15bdc5b0b4fc852bac82c39745b5c838ec9389c64',
    'quantizer.s': 'b14f214cc8236c19b8881d1113ea42359052a6d7ef0e9e0f02aaa88279da64a9',
}


def source_variant(name, source):
    if name not in PINS or hashlib.sha256(source.encode()).hexdigest() != PINS[name]:
        raise ValueError('Reviewed Quantizer source changed: ' + name)
    if name != 'quantizer.s':
        return source
    for old, new in (('.set    KEYS_AT, 0x400d2cb0', '.set    KEYS_AT, qz_pkey'),
                     ('.set    SCALE_AT, 0x400d2ca8', '.set    SCALE_AT, qz_scale_at')):
        if source.count(old) != 1: raise ValueError('Quantizer fixed-address seam changed.')
        source = source.replace(old, new)
    for symbol in ('qz_pkey', 'qz_pmask', 'qz_clock', 'qz_oct'):
        source, count = re.subn(rf'^ *\.set +{symbol}, KEYS_AT[^\n]*\n', '', source, flags=re.M)
        if count != 1: raise ValueError('Quantizer mailbox alias changed: ' + symbol)
    # Standalone QZ has no private FM renderer. Its existing clock guard and
    # stock FLEX renderer access remain exact; FM uses its separate adapter.
    return source


def port(module, sdk_root, work):
    if module.name != 'quantizer' or {u.label for u in module.linked} != {'qzk', 'qzc', 'qzs', 'qz'}:
        raise ValueError('Quantizer requires its four complete authored units.')
    sdk_root, work = Path(sdk_root).resolve(), Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    units = []
    for unit in module.linked:
        original = (sdk_root / unit.source).resolve()
        if not original.is_relative_to(sdk_root) or unit.include or unit.defsyms or unit.stock_copies:
            raise ValueError('Quantizer has an undeclared linked input.')
        target = work / (unit.label + '.s')
        target.write_text(source_variant(original.name, original.read_text()))
        units.append(replace(unit, source=str(target), cave_addr=None, dram=True))
    return replace(module, linked=tuple(units))
