#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact-build offline profile board/stream checks against separate native builds.

This invokes the internal board seam through an emulator C-call fixture. It
is not a host settings protocol, hardware qualification or a Keep/Undo test.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

from runtime_private_paths import private_directory, save

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sdk/octabam/tools/harness'))
from usb_host import Bench, descriptors, enumerate_device, msc_test  # noqa: E402

PROFILES = ('midi-only', 'tracks-main-cue', 'tracks', 'master', 'main-cue', 'main', 'tracks-post')
FRAME_BYTES = (0, 80, 64, 8, 16, 8, 64)
CONFIGS = ('modwerk_cfg_fs', 'modwerk_cfg_hs', 'modwerk_cfg_os_fs', 'modwerk_cfg_os_hs')
CODE, SNAP = 0x40f10000, 0x40f30000
LAYOUTS = (None, 'USB AUDIO OUT TRACKS MAIN CUE', 'USB AUDIO OUT TRACKS',
           'USB AUDIO OUT MASTER', 'USB AUDIO OUT MAIN CUE', 'USB AUDIO OUT MAIN',
           'USB AUDIO OUT TRACKS POST')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def references(root):
    result, identities = [], []
    for name, layout in zip(PROFILES, LAYOUTS):
        folder = root / name
        proof = json.loads((folder / 'proofs.json').read_text())
        if (digest(folder / 'MAIN.raw') != proof['manifest']['main_sha256'] or
                proof['configuration']['usb'].get('audio') != layout):
            raise ValueError('Separate native reference identity mismatch: ' + name)
        text = (folder / 'source/usb_base.s').read_text()
        row = []
        for label in CONFIGS:
            found = re.search(r'^' + label + r':\n\s*\.byte ([^\n]+)', text, re.M)
            if not found:
                raise ValueError('Expected the separate native configuration source: ' + name)
            blob = bytes(int(word.strip(), 16) for word in found[1].split(','))
            if struct.unpack_from('<H', blob, 2)[0] != len(blob):
                raise ValueError('Invalid separate native descriptor length.')
            row.append(blob)
        result.append(row)
        identities.append(dict(profile=name, base=proof['configurationHash'],
                               imageSha256=digest(folder / 'MAIN.raw'),
                               descriptorSourceSha256=digest(folder / 'source/usb_base.s')))
    return result, identities


def wrapper(symbols):
    return f'''.text
.global call_frame
call_frame:
 lea %sp@(-44),%sp
 moveml %d2-%d7/%a2-%a6,%sp@
 jsr {symbols['audio_frame_shim']:#x}
 moveml %sp@,%d2-%d7/%a2-%a6
 lea %sp@(44),%sp
 moveq #0,%d0
 rts
.org 0x100
read_word:
 movel %sp@(4),%a0
 movel %a0@,%d0
 rts
.org 0x120
read_sr:
 moveq #0,%d0
 movew %sr,%d0
 rts
.org 0x140
call_routine:
 lea %sp@(-44),%sp
 moveml %d2-%d7/%a2-%a6,%sp@
 movel %sp@(48),%a1
 jsr %a1@
 moveml %sp@,%d2-%d7/%a2-%a6
 lea %sp@(44),%sp
 rts
'''


class Session:
    def __init__(self, args, output, symbols, proof, frames, check):
        self.symbols, self.check = symbols, check
        self.sock = output.parent / ('usb-profile-' + os.urandom(4).hex() + '.sock')
        if len(os.fsencode(self.sock)) > 100:
            raise ValueError('Choose a shorter private output parent for the Unix socket.')
        self.log = (output / 'emulator.log').open('w')
        self.child = subprocess.Popen([str(args.emulator), '--image', str(args.build / 'MAIN.raw'),
            '--usb-host', str(self.sock), '--usb-hold-ms', '600000', '--mkii'] + (['--frame'] if frames else []),
            stdout=self.log, stderr=subprocess.STDOUT)
        self.bench = None
        try:
            self.bench = Bench(str(self.sock), timeout=20)
            enumerate_device(self.bench, True)
            identity = self.identity()
            check('exact base before fixture writes', identity[:4] == b'MWUI' and identity[16:48].hex() == proof['configurationHash'])
            if not frames:
                source = output / 'wrapper.s'
                save(source, wrapper(symbols).encode())
                for cmd in [['m68k-elf-as', '-mcpu=54455', '-o', output / 'wrapper.o', source],
                            ['m68k-elf-ld', '-Ttext=' + hex(CODE), '-o', output / 'wrapper.elf', output / 'wrapper.o'],
                            ['m68k-elf-objcopy', '-O', 'binary', '-j', '.text', output / 'wrapper.elf', output / 'wrapper.bin']]:
                    subprocess.run(list(map(str, cmd)), check=True, capture_output=True, timeout=30)
                self.bench.poke(CODE, (output / 'wrapper.bin').read_bytes())
                # Dormant ISR epilogue only: an authored C return for explicit off-frame calls.
                self.bench.poke(0x4000d9a6, b'\x4e\x75')
                self.bench.poke(0x80003c10, struct.pack('>I', SNAP))
                self.bench.poke(SNAP, bytes(64))
        except BaseException:
            self.close()
            raise

    def identity(self):
        return self.bench.ctrl_in(0xc1, 3, 0, 1, 72)

    def peek(self, address, count):
        return bytes.fromhex(self.bench.cmd(f'peek {address:#x} {count}', 'peek').split()[1])

    def word(self, address):
        return self.bench.call(CODE + 0x100, address) & 0xffffffff

    def close(self):
        if self.bench:
            self.bench.sock.close()
        if self.child.poll() is None:
            self.child.terminate()
        try:
            self.child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.wait()
        self.log.close()
        with contextlib.suppress(FileNotFoundError):
            self.sock.unlink()


def readiness_checks(session, ordinary=False):
    """Exercise the real packet reader at its lag boundary and counter wrap."""
    b, s, check = session.bench, session.symbols, session.check
    prefix = '' if ordinary else 'p0_'
    def put(name, value, size=4):
        b.poke(s[prefix + name], value.to_bytes(size, 'big'))
    def call(name):
        return b.call(CODE + 0x140, s[prefix + name])
    if not ordinary:
        b.cmd('unplug', 'ok')
        check('readiness profile stage', b.call(s['mu_audio_stage_detached'], 1) == 0)
        b.cmd('plug', 'ok')
        enumerate_device(b, True)
    b.ctrl_nodata(1, 11, 1, 5)
    b.call(CODE)  # One authored frame sets up the real EP3 queue head.
    b.ctrl_nodata(1, 11, 0, 5)
    b.call(CODE)
    for raw, consumed, high, expected in ((128, 112, True, 0), (8, 0xfffffff8, True, 0),
                                         (144, 112, True, 1), (156, 112, False, 1)):
        call('audio_ep3_down')
        for field, value, size in (('aud_produced', raw, 4), ('usbaudio_consumed', consumed, 4),
                                  ('aud_hs', int(high), 1), ('aud_step', 11025 if high else 44100, 4),
                                  ('usbaudio_alt', 1, 1), ('aud_await', 0, 1), ('aud_tail', 0, 1),
                                  ('usbaudio_acc', 0, 4), ('usbaudio_underruns', 0, 4)):
            put(field, value, size)
        result = call('audio_pkt_build')
        check('packet readiness raw=%#x consumed=%#x HS=%s' % (raw, consumed, high), result == expected)
        if not expected:
            check('not-ready packet keeps cursor', session.word(s[prefix + 'usbaudio_consumed']) == consumed)
            check('not-ready packet records underrun', session.word(s[prefix + 'usbaudio_underruns']) == 1)
    call('audio_ep3_down')
    put('usbaudio_alt', 0, 1)
    for index, first, last, stride in (((0, 48, 159, 80),) if ordinary else ((0, 48, 159, 80), (3, 64, 159, 16))):
        selected = '' if ordinary else 'p%d_' % index
        ring = s['aud_ring' if ordinary else 'shared_ring']
        b.poke(s[selected + 'aud_produced'], struct.pack('>I', 128))
        for slot in (first - 1, first, last, last + 1):
            b.poke(ring + slot * stride, b'Z' * stride)
        b.call(CODE + 0x140, s[selected + 'audio_cushion_zero'])
        for slot in (first, last):
            check('fresh-start boundary cleared profile=%d slot=%d' % (index + 1, slot),
                  session.peek(ring + slot * stride, stride) == bytes(stride))
        for slot in (first - 1, last + 1):
            check('fresh-start clear bounded profile=%d slot=%d' % (index + 1, slot),
                  session.peek(ring + slot * stride, stride) == b'Z' * stride)


def ep0_fence_checks(session):
    """Pending real control transfers and RAM-state faults must not commit."""
    b, s, check = session.bench, session.symbols, session.check
    def snapshot():
        fields = [(s['mu_audio_profile'], 4), (s['mu_audio_config_length'], 4),
                  (s['p5_post_hist'], 256), (s['p5_post_state'], 96), (s['p5_post_gtab'], 512)]
        fields += [(s['p%d_usbaudio_consumed' % index],
                    s['p%d_aud_force' % index] + 1 - s['p%d_usbaudio_consumed' % index]) for index in range(6)]
        return [session.peek(address, count) for address, count in fields]
    def refused(label):
        before = snapshot()
        check(label, b.call(s['mu_audio_stage_detached'], 1) == 4)
        check(label + ' preserves profile and retained state', snapshot() == before)
    b.cmd('unplug', 'ok')
    for label, address, value in (('EP0 stock IN state', 0x460bb3ec, struct.pack('>I', 10)),
                                  ('stock awaited OUT', 0x460bb3f4, struct.pack('>I', CODE + 0x300)),
                                  ('old POST clock latch', s['p5_uac2_set_pending'], b'\1')):
        saved = session.peek(address, len(value))
        b.poke(address, value)
        refused(label + ' refuses profile commit')
        check(label + ' is not silently cleared', session.peek(address, len(value)) == value)
        b.poke(address, saved)
    b.cmd('plug', 'ok')
    enumerate_device(b, True)
    b.setup(0x21, 1, 0x0100, 0x1004, 4)  # Actual POST clock SET_CUR, deliberately no data.
    b.cmd('unplug', 'ok')
    check('interrupted clock retains its pending latch', session.peek(s['p5_uac2_set_pending'], 1) == b'\1')
    check('interrupted clock still owns EP0 OUT', session.word(0xfc0b01b8) & 1 == 1)
    refused('interrupted clock data stage refuses profile commit')
    b.cmd('plug', 'ok')
    enumerate_device(b, True)  # A real new SETUP cancels the old clock stage.
    check('new SETUP retires the old clock latch', session.peek(s['p5_uac2_set_pending'], 1) == b'\0')
    b.cmd('unplug', 'ok')
    check('retired clock permits bounded stage', b.call(s['mu_audio_stage_detached'], 6) == 0)
    b.cmd('plug', 'ok')
    enumerate_device(b, True)
    b.setup(0x80, 6, 0x0200, 0, 259)  # Descriptor IN is not consumed by the host.
    b.cmd('unplug', 'ok')
    check('unconsumed descriptor still owns EP0 IN', session.word(0xfc0b01b8) & 0x10000 == 0x10000)
    refused('unconsumed descriptor refuses profile commit')
    b.cmd('plug', 'ok')
    enumerate_device(b, True)
    b.cmd('unplug', 'ok')
    check('retired descriptor permits bounded stage', b.call(s['mu_audio_stage_detached'], 6) == 0)
    b.cmd('plug', 'ok')
    enumerate_device(b, True)
    b.setup(0x41, 1, 1, 1, 52)  # A real SUBMIT OUT stage, without its frame data.
    check('vendor SUBMIT owns EP0 OUT', session.word(0xfc0b01b8) & 1 == 1)
    b.poke(0xfc0b0140, bytes(4))  # Stop RS without a reset; deliberately skip retirement.
    refused('stopped controller with vendor OUT refuses profile commit')
    b.cmd('unplug', 'ok')
    b.cmd('plug', 'ok')
    enumerate_device(b, True)
    b.cmd('unplug', 'ok')
    check('normal reset retires vendor OUT before stage', b.call(s['mu_audio_stage_detached'], 6) == 0)


def dispatcher_context_checks(session, output):
    """End-of-session fixture: no USB request follows these dormant patches."""
    b, s, check = session.bench, session.symbols, session.check
    code, capture, pea_capture, buf = CODE + 0x400, CODE + 0xc00, CODE + 0xd00, CODE + 0xe00
    handlers = ('audio_setiface_shim', 'audio_getiface_shim', 'audio_ctrl_shim',
                'audio_reset_shim', 'audio_sessend_shim', 'audio_isr_shim')
    seeds = tuple(0x12345600 + index * 0x10101 for index in range(15))
    registers = tuple('d%d' % i for i in range(8)) + tuple('a%d' % i for i in range(7))
    text = '.text\n'
    for index, name in enumerate(handlers):
        text += f'''.org {index * 0x100:#x}
probe_{index}:
 lea %sp@(-48),%sp
 moveml %d2-%d7/%a2-%a6,%sp@
 movel %sp@(52),%d0
 movel %d0,{s['mu_audio_profile']:#x}
 movel %sp,{buf + 68:#x}
'''
        text += ''.join(' %s #%#x,%%%s\n' % ('moveal' if reg[0] == 'a' else 'movel', value, reg)
                        for reg, value in zip(registers, seeds))
        text += f''' movel %d0,%sp@(44)
 movel %sp@(56),%d0
 movew %d0,%sr
 moveml %sp@(44),%d0
 jsr {s[name]:#x}
 moveml %sp@,%d2-%d7/%a2-%a6
 lea %sp@(48),%sp
 moveq #0,%d0
 rts
'''
    for address, extra in ((capture, 0), (pea_capture, 4)):
        text += f'''.org {address - code:#x}
 lea %sp@(-64),%sp
 moveml %d0-%d7/%a0-%a6,%sp@
 movew %sr,%d0
 andil #0xffff,%d0
 movel %d0,{buf + 60:#x}
 movel %sp,{buf + 64:#x}
'''
        if extra:
            text += f' movel %sp@(64),%d0\n movel %d0,{buf + 72:#x}\n'
        text += f''' lea {buf:#x},%a0
 moveal %sp,%a1
 moveq #14,%d1
1: movel %a1@+,%a0@+
 subql #1,%d1
 bpl 1b
 lea %sp@({64 + extra}),%sp
 rts
'''
    source = output / 'dispatcher-context.s'
    save(source, text.encode())
    for cmd in [['m68k-elf-as', '-mcpu=54455', '-o', output / 'dispatcher-context.o', source],
                ['m68k-elf-ld', '-Ttext=' + hex(code), '-o', output / 'dispatcher-context.elf', output / 'dispatcher-context.o'],
                ['m68k-elf-objcopy', '-O', 'binary', '-j', '.text', output / 'dispatcher-context.elf', output / 'dispatcher-context.bin']]:
        subprocess.run(list(map(str, cmd)), check=True, capture_output=True, timeout=30)
    b.cmd('unplug', 'ok')
    b.poke(code, (output / 'dispatcher-context.bin').read_bytes())
    def jump(address):
        return b'\x4e\xf9' + struct.pack('>I', address)
    def context(index, profile, flags, extra=0):
        check('dispatcher context fixture returns', b.call(code + index * 0x100, profile, 0x2000 | flags) == 0)
        got = struct.unpack('>19I', session.peek(buf, 76))
        check('selected handler receives original registers', got[:15] == seeds)
        check('selected handler receives original CCR', got[15] == 0x2000 | flags)
        check('dispatcher preserves caller stack', got[17] - got[16] == 68 + extra)
        if extra:
            check('audio-off GET_INTERFACE pushes original pointer', got[18] == 0x400e20a1)
    rejoin = 0x4001d81e
    original = session.peek(rejoin, 6)
    b.poke(rejoin, jump(pea_capture))
    for flags in range(32):
        context(1, 0, flags, 4)
    # Prove the check notices a missing SR restore in the authored dispatcher.
    fn, end = s['audio_getiface_shim'], s['audio_getiface_shim_table']
    body = session.peek(fn, end - fn)
    matches = [at for at in range(0, len(body) - 1, 2) if body[at:at + 2] == b'\x46\xc1']
    check('dispatcher has one SR restoration', len(matches) == 1)
    at = fn + matches[0]
    b.poke(at, b'\x4e\x71')
    b.call(code + 0x100, 0, 0x201f)
    check('skipped dispatcher SR restore is detected', struct.unpack('>I', session.peek(buf + 60, 4))[0] != 0x201f)
    b.poke(at, b'\x46\xc1')
    b.poke(rejoin, original)
    patches = []
    for profile in range(7):
        for name in handlers:
            label = ('off_' + name) if profile == 0 else ('p%d_' % (profile - 1) + name)
            address = s[label]
            b.poke(address, jump(capture))
            patches.append(dict(address=hex(address), bytes=6, purpose='dormant handler entry capture'))
    for index in range(len(handlers)):
        for profile in range(7):
            for flags in range(32):
                context(index, profile, flags)
    return dict(handlerContexts=6 * 7 * 32, actualOffPeaContexts=32,
                skippedSrRestoreDetected=True, fixtureSha256=digest(output / 'dispatcher-context.bin'),
                patches=patches + [dict(address=hex(rejoin), bytes=6, purpose='temporary PEA capture rejoin; restored')])


def run(args):
    symbols = json.loads((args.build / 'symbols.json').read_text())
    proof = json.loads((args.build / 'proofs.json').read_text())
    if digest(args.build / 'MAIN.raw') != proof['manifest']['main_sha256']:
        raise ValueError('The base image does not match its native proof.')
    mode = proof.get('configuration', {}).get('usb', {}).get('profiles')
    if args.ordinary and (mode is not None or proof['configuration']['usb'].get('audio') != LAYOUTS[1]):
        raise ValueError('Use an ordinary twenty-channel source build for --ordinary.')
    if not args.ordinary and mode != dict(schema=1, initial=6, stagingOnly=True, hostSettings=False):
        raise ValueError('Use an opt-in all-profile source build with explicit initial TRACKS POST.')
    if any(CODE <= value < SNAP + 64 for value in symbols.values() if type(value) is int):
        raise ValueError('The authored fixture scratch overlaps a linked symbol.')
    layout = proof['manifest']['link']['layout']
    for low, high in (layout['boot'], layout['fast'], (layout['ddr'][0], layout['reserve']['end'])):
        if not (type(low) is int and type(high) is int and low <= high):
            raise ValueError('Invalid linked reservation bounds.')
        if low < SNAP + 64 and CODE < high:
            raise ValueError('The authored fixture scratch overlaps a linked reservation.')
    if not args.ordinary and args.reference_builds is None:
        raise ValueError('The all-profile gate needs seven separate native --reference-builds.')
    expected, refs = (None, []) if args.ordinary else references(args.reference_builds)
    if args.output.exists():
        raise ValueError('Choose a new private output directory.')
    output = private_directory(args.output)
    checks, cases = [], []
    receipt = dict(kind='octatrack-usb-profile-source-probe', hardware=False, ordinaryReadinessOnly=args.ordinary,
        base=proof['configurationHash'], imageSha256=digest(args.build / 'MAIN.raw'),
        symbolsSha256=digest(args.build / 'symbols.json'), emulatorSha256=digest(args.emulator),
        referenceBuilds=refs, checks=checks, streamCases=cases,
        limitations=['Internal detached board seam, not host settings/authorization/reconnect recovery or lifecycle.',
            'No real DSP/project, cache/DMA, host class drivers, audio quality or hardware timing.',
            'Frame-free fixture uses dormant ISR/USB continuations and handler-entry captures; no USB traffic follows the final context patches. Streaming phase has no code patches.'])
    def check(name, condition):
        checks.append(dict(check=name, passed=bool(condition)))
        if not condition:
            raise AssertionError(name)
    session = None
    try:
        for frames in ((False,) if args.ordinary else (False, True)):
            folder = private_directory(output / ('stream' if frames else 'board'))
            session = Session(args, folder, symbols, proof, frames, check)
            b = session.bench
            if args.ordinary:
                readiness_checks(session, ordinary=True)
                session.close()
                session = None
                continue
            if not frames:
                check('running controller refuses mutation', b.call(symbols['mu_audio_stage_detached'], 0) == 2)
                check('connected refusal preserves initial profile', session.word(symbols['mu_audio_profile']) == 6)
                for invalid in (7, 0xffffffff):
                    check('invalid profile refused', b.call(symbols['mu_audio_stage_detached'], invalid) == 1)
            for high in (True, False):
                for profile, name in enumerate(PROFILES):
                    b.cmd('unplug', 'ok')
                    saved = {}
                    if not frames:
                        check('controller stopped', session.word(0xfc0b0140) & 1 == 0)
                        b.poke(symbols['p3_usbaudio_alt'], b'\1')
                        check('pending stream request refuses stage', b.call(symbols['mu_audio_stage_detached'], profile) == 3)
                        b.poke(symbols['p3_usbaudio_alt'], b'\0')
                        saved = {field: session.peek(symbols['p5_' + field], count) for field, count in
                                 [('post_hidx', 4), ('post_hist', 256), ('post_state', 96), ('post_gtab', 512), ('post_emac', 12)]}
                        for address in (symbols['shared_ring'], symbols['shared_ring'] + 81920 - 64, symbols['shared_sum']):
                            b.poke(address, b'Z' * 64)
                        sr = b.call(CODE + 0x120)
                    else:
                        for address, size in ((symbols['shared_ring'], 81920), (symbols['shared_sum'], 8192)):
                            for offset in range(0, size, 1024):
                                b.poke(address + offset, b'Z' * min(1024, size - offset))
                    attempts = []
                    for _ in range(30):
                        result = b.call(symbols['mu_audio_stage_detached'], profile)
                        attempts.append(result)
                        if result != 3 or not frames:
                            break
                        time.sleep(.01)
                    check('detached profile stage accepted', result == 0)
                    if not frames:
                        check('IRQ mask restored', b.call(CODE + 0x120) & 0x2700 == sr & 0x2700)
                        check('profile committed', session.word(symbols['mu_audio_profile']) == profile)
                        check('clamp committed', session.word(symbols['mu_audio_config_length']) == len(expected[profile][0]))
                        for field, value in saved.items():
                            check('POST ' + field + ' preserved', session.peek(symbols['p5_' + field], len(value)) == value)
                        check('no bulk ring clearing', all(session.peek(address, 64) == b'Z' * 64 for address in
                              (symbols['shared_ring'], symbols['shared_ring'] + 81920 - 64, symbols['shared_sum'])))
                        for index, label in enumerate(CONFIGS):
                            address = symbols['mu_cfg_templates'] + profile * 2048 + index * 512
                            table = session.peek(address, 512)
                            check('immutable ' + label + ' matches native', table[:len(expected[profile][index])] == expected[profile][index])
                            check('unused template tail zero', not any(table[len(expected[profile][index]):]))
                            check('template stays in one page', address // 4096 == (address + 511) // 4096)
                    b.cmd('plug', 'ok')
                    _, config = enumerate_device(b, high)
                    check('enumerated descriptor matches native', config == expected[profile][int(high)])
                    check('base identity unchanged', session.identity()[16:48].hex() == proof['configurationHash'])
                    b.call(0x400108b0, 0xf8)
                    check('fresh MIDI clock', b.ep_in(2, 64) == bytes([15, 248, 0, 0]))
                    if not frames:
                        check('active descriptor length clamp', len(b.ctrl_in(0x80, 6, 0x0200, 0, 1024)) == len(config))
                        check('opposite-speed descriptor', b.ctrl_in(0x80, 6, 0x0700, 0, 1024) == expected[profile][2 + int(not high)])
                        check('storage INQUIRY', msc_test(b))
                        check('connected mutation still refused', b.call(symbols['mu_audio_stage_detached'], (profile + 1) % 7) == 2)
                        if profile:
                            check('closed alt0', b.ctrl_in(0x81, 10, 0, 5, 1) == b'\0')
                        else:
                            before = session.word(symbols['p5_post_hidx'])
                            check('off frame keeps POST history', b.call(CODE) == 0 and session.word(symbols['p5_post_hidx']) == (before + 1) % 4)
                    elif profile:
                        row = dict(profile=name, highSpeed=high, stageAttempts=attempts, packetLengths=[])
                        cases.append(row)
                        b.iso_hz(4000 if high else 1000)
                        b.ctrl_nodata(1, 11, 1, 5)
                        check('stream alt1', b.ctrl_in(0x81, 10, 0, 5, 1) == b'\1')
                        nonempty = 0
                        for _ in range(64):
                            packet = b.ep_in(3, 1024)
                            row['packetLengths'].append(len(packet))
                            if not packet:
                                continue
                            geometry = FRAME_BYTES[profile] if high else 8
                            check('prior ring sentinel excluded', b'Z' * 16 not in packet)
                            check('selected packet geometry', len(packet) % geometry == 0 and len(packet) // geometry in ((10, 11, 12) if high else (43, 44, 45)))
                            nonempty += 1
                            if nonempty == 16:
                                break
                        check('sixteen nonempty packets', nonempty == 16)
                        b.ctrl_nodata(1, 11, 0, 5)
                        check('stream alt0', b.ctrl_in(0x81, 10, 0, 5, 1) == b'\0')
                    if not profile:
                        check('off has no AudioStreaming or EP3', config[4] == 4 and not any(
                            (kind == 4 and data[5:8] == bytes([1, 2, 32])) or (kind == 5 and data[2] == 0x83)
                            for kind, data in descriptors(config)))
            if not frames:
                ep0_fence_checks(session)
                readiness_checks(session)
                receipt['dispatcherContext'] = dispatcher_context_checks(session, folder)
            session.close()
            session = None
        receipt['passed'] = True
    except Exception as error:
        receipt['error'] = str(error)
        raise
    finally:
        if session:
            session.close()
        save(output / 'receipt.json', receipt)
    print(json.dumps(dict(passed=True, checks=len(checks), audioStreamCases=len(cases), hardware=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'emulator', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-builds', type=Path)
    parser.add_argument('--ordinary', action='store_true', help='Only the ordinary twenty-channel compiled packet-reader/startup gate.')
    run(parser.parse_args())
