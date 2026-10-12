#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""QUANTIZE_LIVE_REC_TOGGLE's gate: the built image against the original OS, then under the ColdFire port.

    python3 modules/quantize-live-rec-toggle/verify.py        (from the octabam root)

Reads, and SKIPs without them:
  - the image: out/mainos_bus.bin built with QUANTIZE_LIVE_REC_TOGGLE (QLR_IMAGE overrides);
  - the original OS 1.40C MAIN image: out/raw/section_3_MAIN_OS.bin (QLR_STOCK overrides);
  - the port: out/emu/ot_emu (`make emu-cf`; OT_EMU overrides). Without it only part 1 runs.

1. The image, byte for byte (no emulator):
   - the retired engine-frame site 0x400522ca still holds the original instruction (the manifest's guard);
   - [PLAY] 0x40061778 and [REC] release 0x4004883a hold a `jmp` into one unit, 0x74 apart;
   - that unit is the author's 176 bytes (the manifest's reference SHA-256).
2. The gesture, by the keys, MKII panel, empty card, on this image and on the original OS:
   - [REC] + [PLAY] opens the toast, leaves the setting alone and starts live recording (stock starts it too);
   - a second and third [PLAY] while the toast is up invert the setting and its battery copy and reopen the toast;
   - after the toast has run out, [PLAY] shows again without inverting;
   - releasing [REC] closes the toast; [STOP] ends live recording;
   - [PLAY] without [REC] opens no toast and changes nothing;
   - the original OS under the same keys never changes the setting and opens no toast.
3. A power cycle in the port: the battery RAM of a run that left the setting inverted, booted again
   (--cs1-in), comes up with the inverted setting.
What it cannot see: a real unit's timing, its battery, the DSP's use of shared RAM during audio, an MKI panel.
"""
import ast
import hashlib
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).absolute().parent
ROOT = pathlib.Path.cwd() if (pathlib.Path.cwd() / "tools/emu").is_dir() else HERE.parents[1]
EMU = pathlib.Path(os.environ.get("OT_EMU", ROOT / "out/emu/ot_emu"))
IMAGE = pathlib.Path(os.environ.get("QLR_IMAGE", ROOT / "out/mainos_bus.bin"))
STOCK = pathlib.Path(os.environ.get("QLR_STOCK", ROOT / "out/raw/section_3_MAIN_OS.bin"))
BASE = 0x40000400
QLR, SHADOW, TOAST, REC_HELD, LIVE_REC = 0x800000ac, 0x100fff3c, 0x460d1e70, 0x460d1726, 0x460d172a
CS1, CS1_LEN = 0x10000000, 0x100000
KEYS = {"NO": 0x32, "REC": 0x29, "PLAY": 0x28, "STOP": 0x27}
FAILS = []


def check(ok, what):
    print(("  ok    " if ok else "  FAIL  ") + what)
    if not ok:
        FAILS.append(what)


def declared():
    """The manifest's sites, guard and reference, read as literals: the declaration is never imported."""
    tree = ast.parse((HERE / "manifest.py").read_text())
    names = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "stock_guard":
                value = ast.Tuple(elts=value.args[1:], ctx=ast.Load())
            try:
                names[node.targets[0].id] = ast.literal_eval(value)
            except ValueError:
                pass
    return names


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Port:
    """ot_emu's line protocol: keys by scan row, emulated milliseconds, memory reads."""

    def __init__(self, image, work, extra=()):
        card = work / "card.img"
        if not card.exists():
            (work / "tree").mkdir()
            card.write_bytes(load("qlr_card", ROOT / "tools/emu/emu_card.py").build_image(str(work / "tree"), 32))
        command = [str(EMU), "--image", str(image), "--card", str(card), "--dsp", "--frame", "--ms", "3000",
                   "--interactive", "--main-level", "off", "--rtc", "host", "--mkii", *extra]
        env = {key: value for key, value in os.environ.items() if not key.startswith("OT_")}
        self.port = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=work, env=env)
        self.pending, self.rows = b"", [0] * 8
        self.reply(("ready ",))

    def reply(self, prefixes, timeout=180):
        deadline = time.monotonic() + timeout
        while True:
            while b"\n" in self.pending:
                line, self.pending = self.pending.split(b"\n", 1)
                if line.decode("latin-1").startswith(prefixes):
                    return line.decode("latin-1")
            if time.monotonic() > deadline or self.port.poll() is not None:
                raise RuntimeError("the port stopped answering")
            self.pending += os.read(self.port.stdout.fileno(), 65536)

    def send(self, line):
        self.port.stdin.write((line + "\n").encode())
        self.port.stdin.flush()
        answer = self.reply(("ok", "err", "peek "))
        if answer.startswith("err"):
            raise RuntimeError(answer)
        return answer

    def key(self, name, down, ms=120):
        code = KEYS[name]
        self.rows[code >> 3] = self.rows[code >> 3] | 1 << (code & 7) if down else self.rows[code >> 3] & ~(1 << (code & 7))
        self.send("key %d %d" % (0x20 | code >> 3, self.rows[code >> 3]))
        self.send("run %d" % ms)

    def tap(self, name):
        self.key(name, True)
        self.key(name, False)

    def long(self, address):
        return int.from_bytes(bytes.fromhex(self.send("peek %d 4" % address)[5:]), "big")

    def battery(self):
        return b"".join(bytes.fromhex(self.send("peek %d 4096" % (CS1 + at))[5:]) for at in range(0, CS1_LEN, 4096))

    def close(self):
        try:
            self.send("quit")
            self.port.wait(timeout=10)
        except Exception:
            self.port.kill()


def gesture(image, module):
    """The key sequence on one image. Returns the battery RAM of a run left with the setting inverted (module only)."""
    with tempfile.TemporaryDirectory(prefix="qlr-gate.") as directory:
        port = Port(image, pathlib.Path(directory))
        try:
            for _ in range(3):
                port.tap("NO")                                   # the empty card's prompts
            port.send("run 1500")
            first, who = port.long(QLR), "module" if module else "original OS"
            print("        (%s: setting %d, toast handle %#x, recording %d)" % (who, first, port.long(TOAST), port.long(LIVE_REC)))
            check(first in (0, 1) and port.long(TOAST) == 0 and port.long(LIVE_REC) == 0, who + ": idle after boot, no toast, not recording")
            port.key("REC", True)
            port.key("PLAY", True)
            check(port.long(LIVE_REC) == 1, who + ": the first [REC] + [PLAY] starts live recording")
            check(port.long(QLR) == first, who + ": the first [REC] + [PLAY] leaves the setting alone")
            check((port.long(TOAST) != 0) == module, who + (": it opens the toast" if module else ": no toast"))
            port.key("PLAY", False)
            port.key("PLAY", True)
            check(port.long(QLR) == (first ^ 1 if module else first), who + (": a second [PLAY] while the toast is up inverts the setting" if module else ": a second [PLAY] changes nothing"))
            if module:
                check(port.long(SHADOW) == first ^ 1 and port.long(TOAST) != 0, "module: the battery copy follows and the toast is reopened")
            port.key("PLAY", False)
            port.key("PLAY", True)
            check(port.long(QLR) == first and port.long(SHADOW) == first, who + ": a third [PLAY] leaves the setting as it began")
            port.key("PLAY", False)
            port.send("run 1500")
            if module:
                check(port.long(TOAST) == 0, "module: the toast closes by itself")
            port.key("PLAY", True)
            check(port.long(QLR) == first and (port.long(TOAST) != 0) == module, who + (": [PLAY] after the toast has gone shows it again and does not invert" if module else ": still unchanged"))
            port.key("PLAY", False)
            port.key("REC", False)
            check(port.long(REC_HELD) == 0 and port.long(TOAST) == 0, who + ": releasing [REC] clears the held flag" + (" and closes the toast" if module else ""))
            port.tap("STOP")
            port.send("run 300")
            check(port.long(LIVE_REC) == 0, who + ": [STOP] ends live recording")
            port.tap("PLAY")
            check(port.long(QLR) == first and port.long(TOAST) == 0, who + ": [PLAY] without [REC] opens no toast and changes nothing")
            port.tap("STOP")
            if not module:
                return None
            port.key("REC", True)
            port.tap("PLAY")
            port.tap("PLAY")
            port.key("REC", False)
            port.tap("STOP")
            port.send("run 300")
            check(port.long(QLR) == first ^ 1, "module: left inverted for the power cycle")
            return first ^ 1, port.battery()
        finally:
            port.close()


def power_cycle(image, value, battery):
    with tempfile.TemporaryDirectory(prefix="qlr-gate.") as directory:
        work = pathlib.Path(directory)
        (work / "cs1.bin").write_bytes(battery)
        port = Port(image, work, ("--cs1-in", str(work / "cs1.bin")))
        try:
            for _ in range(3):
                port.tap("NO")
            port.send("run 500")
            check(port.long(QLR) == value, "module: after a power cycle of the port (battery RAM kept) the inverted setting is still there")
        finally:
            port.close()


def main():
    if not IMAGE.is_file() or not STOCK.is_file():
        print("[SKIP] quantize-live-rec-toggle: needs the built image and the original MAIN OS")
        return 0
    facts, image, stock = declared(), IMAGE.read_bytes(), STOCK.read_bytes()
    at = lambda address: address - BASE
    retired, play, rec = facts["RETIRED_TICK_HOOK"], facts["PLAY_HOOK"], facts["RECREL_HOOK"]
    length, digest = facts["RETIRED_TICK_GUARD"]
    print("1. the image")
    check(hashlib.sha256(stock[at(retired):at(retired) + length]).hexdigest() == digest, "the original OS matches the guard at 0x%x" % retired)
    check(image[at(retired):at(retired) + length] == stock[at(retired):at(retired) + length], "0x%x is left as the original OS has it" % retired)
    jumps = [int.from_bytes(image[at(site) + 2:at(site) + 6], "big") for site in (play, rec)]
    check(all(image[at(site):at(site) + 2] == b"\x4e\xf9" for site in (play, rec)), "[PLAY] and [REC] release hold a jmp")
    check(jumps[1] - jumps[0] == 0x74, "both reach one unit, 0x74 apart")
    check(hashlib.sha256(image[at(jumps[0]):at(jumps[0]) + 176]).hexdigest() == facts["REFERENCE"][1], "the unit is the author's 176 bytes")
    if not EMU.is_file():
        print("[SKIP] the gesture: no port at %s" % EMU)
        return 1 if FAILS else 0
    print("2. the gesture")
    value, battery = gesture(IMAGE, True)
    gesture(STOCK, False)
    print("3. a power cycle in the port")
    power_cycle(IMAGE, value, battery)
    print("%d failed" % len(FAILS) if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
