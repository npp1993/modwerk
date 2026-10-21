#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check a private POST base's executed gain/ramp and EMAC save/restore.

This deliberately disables fake audio frames and supplies synthetic snapshots.
The producer probe replaces the dormant ISR epilogue with an authored C return.
It does not test DSP pairing, project controls, audible output or chip timing.
No instrument access. Stock-bearing artifacts stay outside Git.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

from runtime_private_paths import private_directory, save

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sdk/octabam/tools/harness'))
from usb_host import Bench, enumerate_device  # noqa: E402

CODE, SNAP, INPUT, BEFORE, AFTER, OUTER = (
    0x40f10000, 0x40f11000, 0x40f12000, 0x40f12100, 0x40f12200, 0x40f12300)
LIMITATION = ('Synthetic ColdFire execution without audio frames: not DSP-main '
              'pairing, project mute/solo/scene behaviour, physical EMAC '
              'preservation, audio quality or chip timing.')


def assembly(symbols):
    """C-callable wrappers; Bench.call passes arguments on the stack, not d0."""
    return f'''.text
.global probe
probe:
 lea %sp@(-44),%sp
 moveml %d2-%d7/%a2-%a6,%sp@
 movel %sp@(48),%d0
 jsr {symbols['post_frame']:#x}
 jsr {symbols['post_emac_leave']:#x}
 moveml %sp@,%d2-%d7/%a2-%a6
 lea %sp@(44),%sp
 moveq #0,%d0
 rts
.org 0x100
read_word:
 movel %sp@(4),%a0
 movel %a0@,%d0
 rts
.macro EMAC_SAVE ptr
 movel %macsr,%d0
 movel %d0,\\ptr
 moveq #0,%d0
 movel %d0,%macsr
 movel %acc0,%d0
 movel %d0,\\ptr+4
 movel %acc1,%d0
 movel %d0,\\ptr+8
 movel %acc2,%d0
 movel %d0,\\ptr+12
 movel %acc3,%d0
 movel %d0,\\ptr+16
 movel %accext01,%d0
 movel %d0,\\ptr+20
 movel %accext23,%d0
 movel %d0,\\ptr+24
.endm
.macro EMAC_LOAD ptr
 moveq #0,%d0
 movel %d0,%macsr
 movel \\ptr+4,%d0
 movel %d0,%acc0
 movel \\ptr+8,%d0
 movel %d0,%acc1
 movel \\ptr+12,%d0
 movel %d0,%acc2
 movel \\ptr+16,%d0
 movel %d0,%acc3
 movel \\ptr+20,%d0
 movel %d0,%accext01
 movel \\ptr+24,%d0
 movel %d0,%accext23
 movel \\ptr,%d0
 movel %d0,%macsr
.endm
.org 0x200
emac_probe:
 lea %sp@(-44),%sp
 moveml %d2-%d7/%a2-%a6,%sp@
 EMAC_SAVE {OUTER:#x}
 EMAC_LOAD {INPUT:#x}
 EMAC_SAVE {BEFORE:#x}
 EMAC_LOAD {BEFORE:#x}
 movel %sp@(56),%d1
 tstl %d1
 beq 2f
 jsr {symbols['audio_frame_shim']:#x}
 bra 1f
2:
 movel %sp@(48),%d0
 jsr {symbols['post_frame']:#x}
 movel %sp@(52),%d0
 tstl %d0
 beq 1f
 jsr {symbols['post_emac_leave']:#x}
1:
 EMAC_SAVE {AFTER:#x}
 EMAC_LOAD {OUTER:#x}
 moveml %sp@,%d2-%d7/%a2-%a6
 lea %sp@(44),%sp
 moveq #0,%d0
 rts
.org 0x600
producer_probe:
 lea %sp@(-44),%sp
 moveml %d2-%d7/%a2-%a6,%sp@
 jsr {symbols['audio_frame_shim']:#x}
 moveml %sp@,%d2-%d7/%a2-%a6
 lea %sp@(44),%sp
 moveq #0,%d0
 rts
'''


def target(main, xlv, curve):
    # Independent integer definition of the documented DSP-main gain.
    signed = main if main < 0x8000 else main - 0x10000
    squared = min(signed * signed >> 7, 0x7fffff)
    return squared * (curve[xlv >> 7 & 255] >> 2) >> 23


def ramp(state, gain, split):
    current, increment, previous = state
    split &= 15
    continuing = min(split, previous)
    values = [current + increment * i for i in range(continuing)]
    current += increment * continuing
    values.extend([current] * (split - continuing))
    increment = (gain - current) >> 4
    values.extend(current + increment * i for i in range(16 - split))
    return values, [current + increment * (16 - split), increment, split]


def run(args):
    if args.output.exists():
        raise ValueError('Choose a new private output directory.')
    output = private_directory(args.output)
    symbols = json.loads((args.build / 'symbols.json').read_text())
    proof = json.loads((args.build / 'proofs.json').read_text())
    image = args.build / 'MAIN.raw'
    for name in ['post_frame', 'post_emac_leave', 'post_hist', 'post_state',
                 'post_hidx', 'post_gtab', 'post_xlv', 'audio_frame_shim',
                 'aud_force', 'usbaudio_alt', 'aud_running', 'aud_produced',
                 'aud_closed', 'aud_sum', 'aud_ring']:
        if type(symbols.get(name)) is not int or not 0x40000000 <= symbols[name] < CODE:
            raise ValueError('Expected the reviewed POST symbols below the scratch region.')
    if any(CODE <= value < OUTER + 28 for value in symbols.values() if type(value) is int):
        raise ValueError('Scratch region overlaps a linked symbol.')
    save(output / 'probe.s', assembly(symbols).encode())
    for command in [
        ['m68k-elf-as', '-mcpu=5475', '-o', output / 'probe.o', output / 'probe.s'],
        ['m68k-elf-ld', '-Ttext=' + hex(CODE), '-o', output / 'probe.elf', output / 'probe.o'],
        ['m68k-elf-objcopy', '-O', 'binary', '-j', '.text', output / 'probe.elf', output / 'probe.bin'],
    ]:
        subprocess.run(list(map(str, command)), check=True, capture_output=True, timeout=30)

    receipt = dict(kind='usb-post-synthetic-coldfire-probe', hardware=False,
                   base=proof['configurationHash'], imageSha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                   emulatorSha256=hashlib.sha256(args.emulator.read_bytes()).hexdigest(),
                   symbolsSha256=hashlib.sha256((args.build / 'symbols.json').read_bytes()).hexdigest(),
                   limitation=LIMITATION, checks=[])

    def check(name, actual, expected):
        receipt['checks'].append(dict(check=name, passed=actual == expected))
        if actual != expected:
            raise AssertionError(name)

    socket = output / 'emu.sock'
    bench = process = None
    try:
        with (output / 'emulator.log').open('w') as log:
            process = subprocess.Popen([str(args.emulator), '--image', str(image),
                '--usb-host', str(socket), '--usb-hold-ms', '600000', '--mkii'],
                stdout=log, stderr=subprocess.STDOUT)
        bench = Bench(str(socket), timeout=15)
        enumerate_device(bench, True)
        identity = bench.ctrl_in(0xc1, 3, 0, 1, 72)
        check('IDENTIFY magic', identity[:4], b'MWUI')
        check('exact base identity', identity[16:48].hex(), proof['configurationHash'])
        bench.poke(CODE, (output / 'probe.bin').read_bytes())

        def peek(address, count):
            # Older emulator binaries support call but not peek. Read through
            # an authored C-callable wrapper, without changing the emulator.
            if count % 4:
                raise ValueError('Only complete words can be read.')
            return b''.join(struct.pack('>I', bench.call(CODE + 0x100, address + i) & 0xffffffff)
                            for i in range(0, count, 4))

        bench.poke(0x80003c10, struct.pack('>I', SNAP))
        for name, count in [('post_hist', 256), ('post_state', 96), ('post_hidx', 4)]:
            bench.poke(symbols[name], bytes(count))
        for attempt in range(2):
            check(f'no asynchronous gain state advance {attempt}', peek(symbols['post_hidx'], 4), bytes(4))
        curve = struct.unpack('>256I', peek(symbols['post_xlv'], 1024))
        states, history = [[0, 0, 0] for _ in range(8)], [[(0, 0, 0)] * 8 for _ in range(4)]
        random_source = random.Random(0x20261021)
        for frame in range(96):
            current = [([0, 0x100, 0x3400, 0x7f00, 0x8000, 0x4800, 0x1200, 0x6c00][(frame + t) % 8],
                        [0, 0x80, 0x3fff, 0x7fff][(frame + 2 * t) % 4], (frame * 3 + t * 5) & 15)
                       if frame < 32 else tuple(random_source.randrange(65536) for _ in range(3))
                       for t in range(8)]
            bench.poke(SNAP, b''.join(struct.pack('>4H', 0, *words) for words in current))
            sentinel = b'\x5a' * 512
            bench.poke(symbols['post_gtab'], sentinel)
            expected = []
            for track, (main, xlv, split) in enumerate(history[frame % 4]):
                values, states[track] = ramp(states[track], target(main, xlv, curve), split)
                expected.append(values)
            open_stream = frame % 3 != 0
            bench.call(CODE, int(open_stream))
            history[frame % 4] = current
            check(f'frame {frame} four-block history index',
                  struct.unpack('>I', peek(symbols['post_hidx'], 4))[0], (frame + 1) % 4)
            check(f'frame {frame} exact ramp state', list(struct.unpack('>24i', peek(symbols['post_state'], 96))),
                  [word for state in states for word in state])
            table = peek(symbols['post_gtab'], 512)
            if open_stream:
                check(f'frame {frame} per-sample gains', list(struct.unpack('>128I', table)),
                      [expected[track][sample] << 10 & 0xffffffff for sample in range(16) for track in range(8)])
            else:
                check(f'frame {frame} closed path leaves table alone', table, sentinel)
        # Private producer probe: fake frames stay off. The original ISR
        # epilogue is replaced only in emulator RAM, giving its shim a C return.
        receipt['emulatorOnlyReturnPatch'] = dict(address='0x4000d9a6', bytes=2, purpose='C return in dormant ISR epilogue; producer unchanged')
        bench.poke(0x4000d9a6, b'\x4e\x75')
        bench.poke(symbols['aud_force'], b'\1')
        bench.poke(symbols['usbaudio_alt'], b'\0')
        bench.poke(symbols['aud_running'], b'\0')
        for case in range(8):
            hs = case < 4
            bench.speed(hs)
            words = [(0x8000 if case % 4 < 2 else 0 if case % 4 == 3 and t % 2 else 0x1000 + t * 0x900,
                      0x7fff if case % 4 < 2 else 0x1000 + t * 0x700, 0) for t in range(8)]
            gains = [target(main, xlv, curve) for main, xlv, _split in words]
            source = [[[(0x7fffff if case % 4 == 0 else -0x800000) if case % 4 < 2
                        else ((sample * 132539 + t * 896783 + channel * 379717) % 16777216) - 8388608
                        for channel in range(2)] for sample in range(16)] for t in range(8)]
            snapshot = b''.join(struct.pack('>4H', 0, *x) for x in words)
            hist = b''.join(struct.pack('>4H', *x, 0) for x in words) * 4
            bench.poke(SNAP, snapshot)
            bench.poke(symbols['post_hist'], hist)
            bench.poke(symbols['post_hidx'], bytes(4))
            bench.poke(symbols['post_state'], b''.join(struct.pack('>3i', g, 0, 0) for g in gains))
            bench.poke(0x800000e4, struct.pack('>I', 0))
            bench.poke(0x80003190, b''.join(struct.pack('>I', ((x << 8) & 0xffffffff) | 0xa5)
                                          for track in source for pair in track for x in pair))
            bench.poke(symbols['aud_produced'], bytes(4))
            bench.poke(symbols['aud_closed'], b'\0')
            bench.poke(symbols['aud_sum'], b'\x5a' * 128)
            bench.call(CODE + 0x600)
            expected = [[[(gains[t] * source[t][sample][channel]) >> 21 for channel in range(2)]
                         for t in range(8)] for sample in range(16)]
            encoded = b''.join(struct.pack('<I', (x << 8) & 0xffffffff)
                               for frame_words in expected for pair in frame_words for x in pair)
            check(f'producer {case} exact frame-major stereo stems', peek(symbols['aud_ring'], 1024), encoded)
            check(f'producer {case} sixteen frames advanced', peek(symbols['aud_produced'], 4), struct.pack('>I', 16))
            if hs:
                check(f'producer {case} high-speed sum untouched', peek(symbols['aud_sum'], 128), b'\x5a' * 128)
            else:
                summed = b''.join(struct.pack('<I', (max(-8388608, min(8388607,
                    sum(frame_words[t][channel] for t in range(8)))) << 8) & 0xffffffff)
                    for frame_words in expected for channel in range(2))
                check(f'producer {case} saturated full-speed stereo sum', peek(symbols['aud_sum'], 128), summed)
        for case, mode in enumerate([0, 0x20, 0x40, 0x60, 0x80, 0xa0, 0xc0, 0xe0, 0x21, 0x2e, 0x100, 0xf00]):
            bench.poke(INPUT, struct.pack('>7I', mode, 0x12345678, 0x9abcdef0, 0x76543210,
                                         0xfedcba98, 0x12345678, 0x9abcdef0))
            bench.call(CODE + 0x200, case % 2, 1, 0)
            check(f'EMAC gain helper context {case} restored', peek(AFTER, 28), peek(BEFORE, 28))
            bench.poke(symbols['aud_force'], bytes([case % 2]))
            bench.call(CODE + 0x200, case % 2, 1, 1)
            check(f'EMAC actual producer context {case} restored', peek(AFTER, 28), peek(BEFORE, 28))
        bench.poke(INPUT, struct.pack('>7I', 0x80, 0x12345678, 0x9abcdef0, 0x76543210,
                                     0xfedcba98, 0x12345678, 0x9abcdef0))
        bench.call(CODE + 0x200, 1, 0, 0)
        check('skipped EMAC restore negative control differs', peek(AFTER, 28) != peek(BEFORE, 28), True)
        receipt.update(passed=True, frames=96, tracks=8, producerCases=8, emacContexts=24)
    except Exception as error:
        receipt.update(passed=False, error=str(error))
        raise
    finally:
        if bench:
            bench.sock.close()
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        socket.unlink(missing_ok=True)
        save(output / 'receipt.json', receipt)
    print(json.dumps(dict(passed=receipt['passed'], checks=len(receipt['checks']), hardware=False)))


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument('--emulator', type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument('--output', type=lambda value: Path(value).resolve(), required=True)
    run(parser.parse_args())
