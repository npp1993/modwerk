# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in source preparation for one base with six USB outputs and off.

No firmware or stock table is stored here. This supplies an internal detached
board seam, not a host settings/recovery protocol or catalogue admission.
"""
import hashlib
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO_SHA256 = ('ac92cdca02ab3c66a3f931b30cf3ac8b8429bfe7463182398fe9beaac080e4e0',
                'c1f39d2a21870cb5596c487388c61a1be1b9e35ec6860a9eb305268eca2287a8')
CONFIG_NAMES = ('modwerk_cfg_fs', 'modwerk_cfg_hs', 'modwerk_cfg_os_fs', 'modwerk_cfg_os_hs')
HOST_FIELDS = ('usbaudio_consumed', 'usbaudio_lastbank', 'aud_step', 'usbaudio_alt',
               'aud_running', 'aud_closed', 'aud_force')
INITIAL_ALIASES = ('usbaudio_consumed', 'usbaudio_acc', 'usbaudio_overruns', 'usbaudio_underruns',
                   'usbaudio_lastn', 'usbaudio_lastfill', 'usbaudio_lastbank', 'usbaudio_bankdup',
                   'usbaudio_srcjump', 'usbaudio_reprimes', 'usbaudio_minfill', 'usbaudio_maxfill',
                   'usbaudio_anchor', 'aud_produced', 'aud_ring', 'aud_sum', 'usbaudio_alt',
                   'aud_force', 'aud_running', 'aud_closed')
POST_ALIASES = ('post_frame', 'post_emac_leave', 'post_hidx', 'post_hist', 'post_state', 'post_gtab', 'post_emac')


def checked_source(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('USB profile producer changed; review the namespacing and ring seam.')
    return raw.decode()


def namespaced(text, include, index):
    """Rename assembler symbols/macros after the caller guarded the full source."""
    if text.count('.include "remix.inc"') != 1:
        raise ValueError('USB profile include seam changed.')
    text = text.replace('.include "remix.inc"', include)
    before, after = '.if SLOT8_LAYOUT\naud_ring:', '    .data\nusbaudio_alt:'
    if text.count(before) != 1 or text.count(after) != 1:
        raise ValueError('USB profile ring seam changed.')
    start, end = text.index(before), text.index(after)
    if end <= start:
        raise ValueError('USB profile ring span changed.')
    text = text[:start] + ('.if SLOT8_LAYOUT\n.set aud_ring, shared_ring\n.set aud_sum, shared_ring\n'
                          '.else\n.set aud_ring, shared_ring\n.set aud_sum, shared_sum\n.endif\n') + text[end:]
    names = (set(re.findall(r'^\s*([A-Za-z_.$][\w.$]*):', text, re.M)) |
             set(re.findall(r'^\s*\.(?:set|equ|macro)\s+([A-Za-z_.$][\w.$]*)', text, re.M)) |
             {'usbmidi_rx_isr_shim'})
    token = re.compile(r'(?<![\w.$])(' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r')(?![\w.$])')
    text = token.sub(lambda match: 'p%d_' % index + match[0], text)
    if '.include ' in text:
        raise ValueError('USB profiles must not retain an unbound source include.')
    return text + '\n.set p%d_usbmidi_rx_isr_shim, usbmidi_rx_isr_shim\n' % index


def prepare(base, functions, descriptors, post_descriptors, post, curve, initial):
    """Return generated sources and input pins; the curve is local verified data."""
    keys = tuple(functions.AUDIO_LAYOUTS)
    if initial not in keys or tuple(functions.AUDIO_LAYOUTS.values()) != tuple(range(6)) or keys[-1] != post.LAYOUT:
        raise ValueError('Choose an explicit initial profile from the six reviewed outputs.')
    initial_index = keys.index(initial)
    raw = [checked_source(path, digest) for path, digest in zip((base.AUDIO_SOURCE, base.POST_AUDIO_SOURCE), AUDIO_SHA256)]
    bodies = []
    for index, key in enumerate(keys):
        include = functions.audio_include(key) + (post.include(curve) if index == 5 else '')
        text = functions.audio_storage_source(functions.audio_source(raw[1 if index == 5 else 0]))
        if index != 5:
            text = functions.packet_readiness(text)
        bodies.append(namespaced(text, include, index))
    dispatch = (HERE / 'dispatch.s').read_text()
    aliases = ''.join(' .global %s\n .set %s, p%d_%s\n' % (name, name, initial_index, name) for name in INITIAL_ALIASES)
    aliases += ''.join(' .global %s\n .set %s, p5_%s\n' % (name, name, name) for name in POST_ALIASES)
    for marker, value in (('@INITIAL_PROFILE@', str(initial_index + 1)), ('@INITIAL_ALIASES@', aliases)):
        if dispatch.count(marker) != 1:
            raise ValueError('USB profile dispatcher template changed.')
        dispatch = dispatch.replace(marker, value)
    sources = {'usbaudio.s': '\n'.join(bodies) + '\n' + dispatch,
               'usb_audio_profile_stage.c': (HERE / 'stage.c').read_text(),
               'usb_audio_profiles.h': (HERE / 'usb_audio_profiles.h').read_text()}
    data = '#include "usb_audio_profiles.h"\nvolatile uint32_t mu_audio_config_length=259;\n'
    for index in range(6):
        for field in HOST_FIELDS:
            data += 'extern uint8_t p%d_%s[];\n' % (index, field)
    data += 'const struct host_state mu_audio_profile_states[6]={\n'
    for index in range(6):
        data += ' {p%d_usbaudio_consumed,p%d_aud_force+1,p%d_usbaudio_lastbank,p%d_aud_step,p%d_usbaudio_alt,p%d_aud_running,p%d_aud_closed},\n' % ((index,) * 7)
    data += '};\n'
    templates = []
    for key in (None, *keys):
        descriptor = post_descriptors if key == post.LAYOUT else descriptors
        row = [functions.configuration(base, descriptor, high, other, key)
               for high, other in ((False, False), (True, False), (False, True), (True, True))]
        if len({len(blob) for blob in row}) != 1 or any(not blob or len(blob) > 512 for blob in row):
            raise ValueError('USB profile configurations must fit their immutable 512-byte slots.')
        templates.append(row)
    data += 'const uint16_t mu_audio_profile_lengths[7]={' + ','.join(str(len(row[0])) for row in templates) + '};\n'
    data += 'const uint8_t mu_cfg_templates[7][4][512] __attribute__((aligned(512)))={\n'
    data += ',\n'.join('{' + ','.join('{' + ','.join(map(str, blob)) + '}' for blob in row) + '}' for row in templates) + '};\n'
    sources['usb_audio_profile_data.c'] = data
    read = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (base.AUDIO_SOURCE, base.POST_AUDIO_SOURCE, base.AUDIO_DESCRIPTORS, base.POST_AUDIO_DESCRIPTORS,
             *sorted(path for path in HERE.iterdir() if path.is_file() and path.suffix in ('.py', '.c', '.h', '.s')))}
    return sources, read


def assembly(base, functions, descriptors, initial):
    text = functions.assembly(base, descriptors, initial)
    for old, new in (('cmpil   #modwerk_cfg_len,%d1', 'cmpl    mu_audio_config_length,%d1'),
                     ('movel   #modwerk_cfg_len,%d1', 'movel   mu_audio_config_length,%d1')):
        if text.count(old) != 2:
            raise ValueError('USB profile descriptor clamp seam changed.')
        text = text.replace(old, new)
    text += '\n.text\n'
    for at, _, name in base.POINTERS[:4]:
        slot = CONFIG_NAMES.index(name)
        text += f'''
.global mu_push_{name}
mu_push_{name}:
 lea %sp@(-16),%sp
 moveml %d0-%d1/%a0,%sp@
 movew %sr,%d1
 movel mu_audio_profile,%d0
 lsll #8,%d0
 lsll #3,%d0
 lea mu_cfg_templates+{slot * 512},%a0
 addal %d0,%a0
 movel %a0,%sp@(12)
 movew %d1,%sr
 moveml %sp@,%d0-%d1/%a0
 lea %sp@(12),%sp
 jmp {at + 4:#x}
'''
    return text


def sites(base, functions, image_at, initial):
    result = functions.sites(base, image_at, initial)
    for item in result:
        name = item.get('target')
        if name in CONFIG_NAMES:
            at = int(item['addr'], 16) - 2
            stock = image_at(at, 6)
            if stock[:2] != bytes.fromhex('4879') or stock[2:].hex() != item['stock']:
                raise ValueError('USB profile descriptor PEA guard changed.')
            item.update(addr=hex(at), stock=stock.hex(), op='jmp', target='mu_push_' + name)
    spans = sorted((int(item['addr'], 16), len(bytes.fromhex(item['stock']))) for item in result)
    if any(at + size > following for (at, size), (following, _) in zip(spans, spans[1:])):
        raise ValueError('USB profile hooks overlap.')
    return result
