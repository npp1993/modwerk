#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise a private base's real MIDI reset/replug paths in ot_emu.

Pass --expect-stale for the unchanged-source negative control. Images, symbols,
traces and receipts stay in a private output directory. This verifies firmware
execution and endpoint ownership, not a physical host driver or audio quality.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from runtime_private_paths import private_directory, save

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'sdk/octabam/tools/harness'))
from usb_host import Bench, enumerate_device  # noqa: E402

CLOCK = bytes.fromhex('0ff80000')
NOTE = bytes.fromhex('09903c64')


def run(args):
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Choose a new private output directory.')
    output = private_directory(output)
    sock = output / 'usb.sock'
    log = output / 'emulator.log'
    symbols = json.loads(args.symbols.read_text())
    if symbols['usbmidi_tx_acc_len'] != symbols['usbmidi_up'] + 4:
        raise ValueError('MIDI accumulator layout differs from the reviewed cleanup.')
    checks = []

    def check(name, actual, expected):
        checks.append(dict(check=name, passed=actual == expected))
        if actual != expected:
            raise AssertionError(name)

    def enumerate_ready(bench):
        enumerate_device(bench, True)
        # Stock primes SET_CONFIGURATION's status before the MIDI init body.
        # A completed subsequent control transfer is the ordering barrier;
        # a bench call immediately after its ACK can outrun initialization.
        identity = bench.ctrl_in(0xc1, 3, 0, 1, 72)
        check('configured base answers IDENTIFY', identity[:4], b'MWUI')

    def reopen_audio(bench):
        if args.audio_interface is None:
            return
        check('reset audio alternate setting is zero',
              bench.ctrl_in(0x81, 10, 0, args.audio_interface, 1), b'\0')
        bench.iso_hz(4000)
        bench.ctrl_nodata(0x01, 11, 1, args.audio_interface)
        check('audio alternate setting reopens',
              bench.ctrl_in(0x81, 10, 0, args.audio_interface, 1), b'\1')
        # The control ACK can precede the first producer frame. The iso
        # bench returns empty polls during that bounded startup window.
        packet = b''
        for _ in range(64):
            packet = bench.ep_in(3, 1024, timeout=5)
            if packet:
                break
        check('audio resumes whole frames', bool(packet) and
              len(packet) % args.audio_frame_bytes == 0, True)

    with log.open('w') as stream:
        process = subprocess.Popen([str(args.emulator), '--image', str(args.image),
            '--usb-host', str(sock), '--usb-hold-ms', '120000', '--frame', '--mkii'],
            stdout=stream, stderr=subprocess.STDOUT, env=dict(os.environ, OT_USB_TRACE='1'))
    try:
        bench = Bench(str(sock), timeout=15)
        try:
            enumerate_ready(bench)
            bench.call(0x400108b0, 0xf8)
            check('initial clock arrives', bench.ep_in(2, 64, timeout=5), CLOCK)
            for cycle in range(4):
                # Alternate an in-flight old packet with an empty endpoint.
                if cycle % 2:
                    bench.call(0x400108b0, 0xf8)
                # Injected sender calls need the bench's idle-call gate.
                # Open audio after those calls and leave it open across the
                # cable pull; resume sender checks after reset stopped EP3.
                reopen_audio(bench)
                bench.cmd('unplug', 'ok')
                for _ in range(2):
                    bench.call(0x400108b0, 0xf8)
                bench.cmd('plug', 'ok')
                bench.call(0x400108b0, 0xf8)
                enumerate_ready(bench)
                bench.poke(0x400d807c, NOTE[1:])
                bench.call(0x40010bc8, 3, 0x400d807c)
                packet = bench.ep_in(2, 64, timeout=5)
                if args.expect_stale:
                    check('negative control retains stale clocks', CLOCK in packet and NOTE in packet, True)
                    break
                check('replug %d sends only the fresh note' % (cycle + 1), packet, NOTE)
                bench.call(0x400108b0, 0xf8)
                check('replug %d continues transmitting' % (cycle + 1),
                      bench.ep_in(2, 64, timeout=5), CLOCK)
            if not args.expect_stale:
                # A bus reset with no cable pull must also discard old traffic.
                bench.call(0x400108b0, 0xf8)
                bench.call(0x400108b0, 0xf8)
                reopen_audio(bench)
                enumerate_ready(bench)
                bench.poke(0x400d807c, NOTE[1:])
                bench.call(0x40010bc8, 3, 0x400d807c)
                check('bus reset sends only the fresh note', bench.ep_in(2, 64, timeout=5), NOTE)
                reopen_audio(bench)
        finally:
            bench.sock.close()
        process.wait(timeout=15)
        trace = log.read_text(errors='replace')
        disconnected = False
        primes = 0
        for line in trace.splitlines():
            if 'cmd unplug' in line:
                disconnected = True
            elif 'cmd setup 0009010000000000' in line:
                disconnected = False
            elif disconnected and 'wr 0x1b0 <- ' in line:
                if int(line.rsplit(' ', 1)[1], 16) & 0x00040000:
                    primes += 1
        check('no MIDI IN prime before reconfiguration' if not args.expect_stale else
              'negative control primes MIDI IN while disconnected', primes == 0, not args.expect_stale)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        with contextlib.suppress(FileNotFoundError):
            sock.unlink()
        receipt = dict(kind='octatrack-base-usb-midi-reconnect',
            imageSha256=hashlib.sha256(args.image.read_bytes()).hexdigest(),
            negativeControl=args.expect_stale, checks=checks, hardware=False,
            limitation='Emulator controller flushes immediately; physical driver recovery and audio remain separate.')
        save(output / 'receipt.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('emulator', 'image', 'symbols', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expect-stale', action='store_true')
    parser.add_argument('--audio-interface', type=int,
                        help='also reopen EP3 after each reset (public base: 5)')
    parser.add_argument('--audio-frame-bytes', type=int, default=80,
                        help='bytes in one complete audio frame (20 int32 channels: 80)')
    args = parser.parse_args()
    if args.audio_frame_bytes < 1 or args.audio_interface is not None and not 0 <= args.audio_interface < 256:
        parser.error('Use a valid interface and positive audio frame size.')
    run(args)
