#!/usr/bin/env python3
"""TEMP SAVE's gate: the built image under the ColdFire port (ot_emu --mkii).

    python3 modules/temp-save/verify.py        (from the octabam root)

Reads, and SKIPs without any of them:
  - the image: out/mainos_bus.bin built with TEMP SAVE (TEMP_IMAGE overrides);
  - the port: out/emu/ot_emu (`make emu-cf`; OT_EMU overrides);
  - a project to stage: out/_stage_tmpl/OCTABAM/TMPL (TEMP_PROJECT overrides).

What it checks, on one interactive boot and then a power cycle:
  1. FUNC + YES on the pattern screen: the toast is TEMP SAVED, stock's
     ARM ALL routine does not run, and the pattern, the Part, the saved
     Part and the CS1 copies are unchanged.
  2. Edits made through the panel after it: trigs placed in grid recording,
     a knob turned on two pages, a scene lock written, the scene selection
     changed. FUNC + NO: the toast is RELOADED, stock's DISARM ALL routine
     does not run; the pattern (bank RAM and its battery copy) is the one
     saved byte for byte; the working Part is the one saved byte for byte
     but for the scene selection, which is the one live before the reload;
     the CS1 working copy equals RAM; the saved Part is unchanged; the
     unsaved bit is set; the machines are the saved ones.
  3. FUNC + NO again after more edits puts the same copy back (the copy
     survives its reload); FUNC + YES again replaces it.
  3a. Bigger edits in between: the whole pattern cleared (FUNC + PLAY) and
     the current track's machine changed (FUNC + SRC, DOWN, DOWN, YES):
     the reload brings back the pattern and the machine, and stock's machine
     transition 0x400972fc runs for each of the eight tracks.
  3b. In a window (AMP SETUP, MIXER, PROJECT, PART) FUNC + YES and FUNC + NO
     stay stock: no module toast, no pattern or Part byte moved.
  4. On another pattern FUNC + NO shows NO TEMP SAVE and changes nothing;
     back on the saved pattern it reloads.
  4a. While the sequencer plays: FUNC + YES, edits, FUNC + NO: the pattern
     and the Part come back and the transport keeps running.
  4b. The pattern moved to another Part (PART, DOWN, YES) after FUNC + YES:
     FUNC + NO brings back the pattern's Part as well, the saved copy into
     it with that Part's own scene selection; the other Part is untouched.
  4c. Another bank (BANK, trig, trig): NO TEMP SAVE; there, on Parts with no
     saved copy, FUNC + YES / FUNC + NO work and the Part still has no saved
     copy afterwards (stock RELOAD PART still finds none).
  4d. MIDI mode: the same save and reload with MIDI-track edits.
  4e. Key order: FUNC released before YES or NO: the next stock FUNC + YES
     and FUNC + NO in a window reach stock on press and on release.
  5. Stock flows: YES alone reaches ARM ALL and NO alone DISARM ALL; RELOAD
     PART (FUNC + CUE) still restores the saved Part, not the temp save.
  6. A power cycle (CS1 and card kept, the firmware's own power-up load):
     the copy is gone, FUNC + NO shows NO TEMP SAVE.
What it cannot see: hardware timing, audible output, the panel's own LCD,
the sample lists' FUNC + YES preview (stock's own list test is the
handler's first branch, which the detour leaves untouched).
"""
import hashlib
import io
import os
import pathlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).absolute().parent
ROOT = pathlib.Path.cwd() if (pathlib.Path.cwd() / "tools/emu").is_dir() else HERE.parents[1]
EMU = pathlib.Path(os.environ.get("OT_EMU", ROOT / "out/emu/ot_emu"))
IMAGE = pathlib.Path(os.environ.get("TEMP_IMAGE", ROOT / "out/mainos_bus.bin"))
PROJECT = pathlib.Path(os.environ.get("TEMP_PROJECT", ROOT / "out/_stage_tmpl/OCTABAM/TMPL"))
PY = pathlib.Path(os.environ.get("OT_PY", ROOT / ".venv/bin/python3"))
PY = PY if PY.exists() else pathlib.Path(sys.executable)
BASE = 0x40000400
YES_SITE, NO_SITE = 0x4005E3D8, 0x4005E1FC

BANK_PTR, CUR_PART, CUR_PAT = 0x46c82456, 0x80000003, 0x100b14d0
PAT_LEN, PART_LEN, PARTS, SAVED, UNSAVED = 0x8ed8, 0x18b2, 0x8ed80, 0x9504a, 0x95048
PAT_CS1, PART_CS1 = 0x1001614e, 0x100a4ece
SEL = 0x10                           # Part + 0x10, + 0x11: scenes A and B
MACH = 0x22                          # Part + 0x22 + track: the machines
CUR_TRACK, TRANSITION, POPUP = 0x80000000, 0x400972fc, 0x460d175c
VOICE_BIND = 0x40006820              # stock binds a track's voice: a trig played
TICK = 0x400a1e0c                    # the sequencer tick
NOTIFY, ARM_ALL, DISARM_ALL = 0x4005a2b8, 0x4005e294, 0x4005e0e8
YES_REJOIN, NO_REJOIN = 0x4005e3e0, 0x4005e204
HAS_SAVED, PAT_PART, CUR_BANK = 0x9b312, 0x8e57, 0x80000002
MKI = os.environ.get("TEMP_MODEL", "mkii").lower() == "mki"
TEXTS = {"saved": "TEMP SAVED", "reloaded": "RELOADED", "none": "NO TEMP SAVE"}
KEYS = {'scene_a': 0x19, 'scene_b': 0x1a, 'yes': 0x31, 'no': 0x32, 'func': 0x2d, 'cue': 0x2a, 'pattern': 0x2e,
        'play': 0x28, 'bank': 0x2f, 'midi': 0x35, 'down': 0x20, 'up': 0x33, 'proj': 0x1c, 'part': 0x1d, 'mixer': 0x30, 'stop': 0x27, 'rec': 0x29, 'pg_src': 0x22, 'pg_amp': 0x23, 'pg_fx1': 0x25,
        **{f'trig{i + 1}': i for i in range(16)}}
FAILS = []


def check(ok, what):
    print(("  ok    " if ok else "  FAIL  ") + what, flush=True)
    if not ok:
        FAILS.append(what)


def stage(work):
    proj = work / "TSFIX"
    proj.mkdir()
    for f in PROJECT.iterdir():
        if f.is_file() and f.suffix.lower() in (".work", ".strd"):
            shutil.copy2(f, proj / f.name)
    card = work / "card.img"
    r = subprocess.run([str(PY), str(ROOT / "tools/emu/ot_emu/stage_card.py"), str(proj), "TEMPSAV", "TSFIX",
                        "--tree", str(work / "tree"), "--out", str(card)], capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        sys.exit(f"verify temp-save: stage_card failed:\n{r.stdout[-800:]}{r.stderr[-800:]}")
    return card


class Emu:
    """`ot_emu --interactive`: one command line out, one reply line back."""

    def __init__(self, card, log, extra=()):
        argv = [str(EMU), "--image", str(IMAGE), "--card", str(card), "--interactive", "--mount", "--set", "TEMPSAV",
                "--project", "TSFIX", "--internal-clock", *(() if MKI else ("--mkii",)), "--card-rw", *extra]
        self.err = open(log, "wb")
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, bufsize=0)
        self.q = queue.Queue()
        self.rows = {}
        threading.Thread(target=self._rd, daemon=True).start()
        while True:
            line = self.q.get(timeout=900)
            if line is None:
                raise RuntimeError(f"ot_emu died before ready ({log})")
            if line.startswith("ready"):
                break

    def _rd(self):
        f = io.BufferedReader(self.p.stdout, buffer_size=1 << 16)
        for raw in iter(f.readline, b""):
            self.q.put(raw.decode("ascii", "replace").rstrip())
        self.q.put(None)

    def cmd(self, line, expect="ok"):
        self.p.stdin.write(line.encode() + b"\n")
        self.p.stdin.flush()
        while True:
            r = self.q.get(timeout=900)
            if r is None:
                raise RuntimeError("ot_emu died on " + line)
            head = r.split(" ", 1)[0]
            if head == expect:
                return r
            if head == "err":
                raise RuntimeError(r)

    def run(self, ms):
        self.cmd(f"run {ms}")

    def peek(self, a, n):
        out = b""
        while n > 0:
            k = min(n, 4096)
            out += bytes.fromhex(self.cmd(f"peek {a:#x} {k}", "peek")[5:])
            a += k
            n -= k
        return out

    def u32(self, a):
        return int.from_bytes(self.peek(a, 4), "big")

    def key(self, name, down):
        code = KEYS[name]
        row = 0x20 | (code >> 3)
        cur = self.rows.get(row, 0)
        cur = cur | (1 << (code & 7)) if down else cur & ~(1 << (code & 7))
        self.rows[row] = cur
        self.cmd(f"key {row:#x} {cur:#x}")

    def tap(self, name, hold=80, after=300):
        self.key(name, True)
        self.run(hold)
        self.key(name, False)
        self.run(after)

    def chord(self, held, name, after=400):
        held = (held,) if isinstance(held, str) else held
        for k in held:
            self.key(k, True)
            self.run(150)
        self.tap(name)
        for k in reversed(held):
            self.key(k, False)
            self.run(150)
        self.run(after)

    def knob(self, enc, delta):
        self.cmd(f"knob {0x30 + enc:#x} {delta & 0xff}")
        self.run(200)

    def watch(self, addrs):
        self.cmd("watch " + ",".join(hex(a) for a in addrs))
        self.hits()

    def hits(self):
        return [tuple(int(x, 16) for x in h.split(":")) for h in self.cmd("hits", "hits").split()[2:]]

    def quit(self):
        try:
            self.cmd("quit")
        except Exception:
            pass
        self.p.wait(timeout=60)
        self.err.close()

    def state(self):
        b = self.u32(BANK_PTR)
        p = self.peek(CUR_PART, 1)[0]
        n = self.peek(CUR_PAT, 1)[0]
        return {"bank": b, "p": p, "n": n,
                "P": self.peek(b + n * PAT_LEN, PAT_LEN), "Pcs1": self.peek(PAT_CS1 + n * PAT_LEN, PAT_LEN),
                "W": self.peek(b + PARTS + p * PART_LEN, PART_LEN), "Wcs1": self.peek(PART_CS1 + p * PART_LEN, PART_LEN),
                "S": self.peek(b + SAVED + p * PART_LEN, PART_LEN),
                "unsaved": self.peek(b + UNSAVED, 1)[0] >> p & 1}


def is_open(e):
    rec = e.u32(POPUP)
    return bool(rec and e.u32(rec + 0x20) & 0x20)


def diff(a, b):
    return sum(x != y for x, y in zip(a, b))


def toasts(hits, texts):
    return [k for k, a in texts.items() for h in hits if h[1] == NOTIFY and a in h]


def gesture(e, held, name, texts):
    e.watch([NOTIFY, ARM_ALL, DISARM_ALL])
    e.chord(held, name, after=800)
    h = e.hits()
    return toasts(h, texts), any(x[1] == ARM_ALL for x in h), any(x[1] == DISARM_ALL for x in h)


def edit(e):
    """Panel edits to the pattern and the Part: trigs, knobs, a scene lock, the scene selection."""
    e.tap("rec", after=400)                       # grid recording
    for t in ("trig2", "trig7", "trig12"):
        e.tap(t)
    e.tap("rec", after=400)
    e.tap("pg_amp")
    e.knob(0, 9)
    e.tap("pg_fx1")
    e.knob(1, -7)
    e.key("scene_a", True)
    e.run(150)
    e.knob(2, 11)                                 # a scene A lock
    e.tap("trig5")                                # scene A := 5
    e.key("scene_a", False)
    e.run(400)


def main():
    for what, path in (("image", IMAGE), ("port", EMU), ("project", PROJECT)):
        if not path.exists():
            print(f"verify temp-save: SKIP (no {what}: {path})")
            return 0
    img = IMAGE.read_bytes()
    if any(img[s - BASE:s - BASE + 2] != b"\x4e\xf9" for s in (YES_SITE, NO_SITE)):
        print(f"verify temp-save: SKIP ({IMAGE} has no TEMP SAVE detours)")
        return 0
    hook = int.from_bytes(img[YES_SITE - BASE + 2:YES_SITE - BASE + 6], "big")
    print(f"verify temp-save: image {hashlib.sha256(img).hexdigest()[:12]}, hook {hook:#x}")
    work = pathlib.Path(tempfile.mkdtemp(prefix="temp_save_verify_"))
    card = stage(work)

    e = Emu(card, work / "main.log")
    try:
        e.run(3000)
        e.tap("yes", after=1500)                  # the clock dialog
        unit = e.peek(hook, 0x400)
        texts = {}
        for k, words in TEXTS.items():
            at = unit.find(words.encode() + b"\0")
            if at < 0:
                sys.exit(f"verify temp-save: the unit's text {words!r} is not where the detour points")
            texts[k] = hook + at

        print("verify temp-save: FUNC + YES")
        edit(e)                                   # something worth saving
        s0 = e.state()
        t, arm, disarm = gesture(e, "func", "yes", texts)
        s1 = e.state()
        check(t == ["saved"] and not arm, f"FUNC + YES: toast {t}, ARM ALL {'ran' if arm else 'did not run'}")
        check(all(s1[k] == s0[k] for k in ("P", "Pcs1", "W", "Wcs1", "S", "unsaved")),
              "FUNC + YES changes no pattern or Part byte")

        print("verify temp-save: edits, then FUNC + NO")
        edit(e)
        s2 = e.state()
        check(diff(s2["P"], s0["P"]) > 0 and diff(s2["W"], s0["W"]) > 0 and s2["W"][SEL] == 4,
              f"the edits moved {diff(s2['P'], s0['P'])} pattern and {diff(s2['W'], s0['W'])} Part bytes, scene A 5")
        t, arm, disarm = gesture(e, "func", "no", texts)
        s3 = e.state()
        want = bytearray(s0["W"])
        want[SEL:SEL + 2] = s2["W"][SEL:SEL + 2]
        check(t == ["reloaded"] and not disarm, f"FUNC + NO: toast {t}, DISARM ALL {'ran' if disarm else 'did not run'}")
        check(s3["P"] == s0["P"] and s3["Pcs1"] == s0["P"], f"the pattern is the saved one, RAM and battery copy "
              f"({diff(s3['P'], s0['P'])} / {diff(s3['Pcs1'], s0['P'])} bytes differ)")
        check(s3["W"] == bytes(want), f"the working Part is the saved one but for the live scene selection "
              f"({diff(s3['W'], want)} bytes differ)")
        check(s3["Wcs1"] == s3["W"], "the CS1 working copy equals RAM")
        check(s3["S"] == s0["S"], "the saved Part is unchanged")
        check(s3["unsaved"] == 1, "the Part is marked unsaved")
        check(s3["W"][MACH:MACH + 8] == s0["W"][MACH:MACH + 8], f"machines {list(s3['W'][MACH:MACH + 8])}")

        print("verify temp-save: the copy survives its reload")
        edit(e)
        e.key("scene_a", True)
        e.run(150)
        e.tap("trig9")                            # scene A := 9
        e.key("scene_a", False)
        e.run(400)
        s4 = e.state()
        t, _, _ = gesture(e, "func", "no", texts)
        s5 = e.state()
        want[SEL:SEL + 2] = s4["W"][SEL:SEL + 2]
        check(t == ["reloaded"] and s5["P"] == s0["P"] and s5["W"] == bytes(want),
              f"FUNC + NO again: toast {t}, pattern {diff(s5['P'], s0['P'])} and Part {diff(s5['W'], want)} bytes off")
        edit(e)
        s6 = e.state()
        t, _, _ = gesture(e, "func", "yes", texts)
        edit(e)
        t2, _, _ = gesture(e, "func", "no", texts)
        s7 = e.state()
        want6 = bytearray(s6["W"])
        want6[SEL:SEL + 2] = s7["W"][SEL:SEL + 2]
        check(t == ["saved"] and t2 == ["reloaded"] and s7["P"] == s6["P"] and s7["W"] == bytes(want6),
              "a second FUNC + YES replaces the copy")

        print("verify temp-save: a cleared pattern and a new machine")
        t, _, _ = gesture(e, "func", "yes", texts)
        sa = e.state()
        trk = e.peek(CUR_TRACK, 1)[0]
        e.chord("func", "play", after=800)       # clear the pattern
        e.chord("func", "pg_src", after=800)     # the machine
        e.tap("down")
        e.tap("down")
        e.tap("yes", after=800)
        e.tap("no", after=600)
        sb = e.state()
        check(diff(sb["P"], sa["P"]) > 0 and sb["W"][MACH + trk] != sa["W"][MACH + trk],
              f"cleared: {diff(sb['P'], sa['P'])} pattern bytes moved; T{trk + 1} machine {sa['W'][MACH + trk]} -> "
              f"{sb['W'][MACH + trk]}")
        e.watch([NOTIFY, TRANSITION])
        e.chord("func", "no", after=800)
        h = e.hits()
        t = toasts(h, texts)
        sc = e.state()
        moves = sum(x[1] == TRANSITION for x in h)
        check(t == ["reloaded"] and sc["P"] == sa["P"] and sc["Pcs1"] == sa["P"] and sc["W"][MACH:MACH + 8] == sa["W"][MACH:MACH + 8]
              and sc["Wcs1"] == sc["W"] and moves == 8,
              f"FUNC + NO: toast {t}, pattern {diff(sc['P'], sa['P'])} bytes off, T{trk + 1} machine "
              f"{sc['W'][MACH + trk]}, machine transitions {moves}")
        s7 = e.state()
        s6 = sa

        print("verify temp-save: in a window FUNC + YES and FUNC + NO stay stock")
        for name, opening, closing in ((("AMP SETUP", ("func", "pg_amp"), ("no",)), ("MIXER", ("mixer",), ("mixer",)),
                                        ("PROJECT", ("proj",), ("no",)), ("PART", ("part",), ("part",)))):
            e.chord(*opening, after=800) if len(opening) == 2 else e.tap(opening[0], after=800)
            sw = e.state()
            ty, _, _ = gesture(e, "func", "yes", texts)
            tn, _, _ = gesture(e, "func", "no", texts)
            sx = e.state()
            open_ = is_open(e)
            for k in closing:
                e.tap(k, after=600)
            check(not ty and not tn and sx["P"] == sw["P"] and sx["W"] == sw["W"] and open_ != 0,
                  f"{name}: no module toast ({ty + tn}), nothing changed")
        check(not is_open(e), "back on the pattern screen")

        print("verify temp-save: another pattern")
        e.chord("pattern", "trig2", after=1200)
        s8 = e.state()
        t, _, _ = gesture(e, "func", "no", texts)
        s9 = e.state()
        check(s8["n"] != s7["n"] and t == ["none"] and s9["P"] == s8["P"] and s9["W"] == s8["W"],
              f"pattern {s8['n'] + 1}: toast {t}, nothing changed")
        e.chord("pattern", f"trig{s7['n'] + 1}", after=1200)
        t, _, _ = gesture(e, "func", "no", texts)
        check(t == ["reloaded"] and e.state()["P"] == s6["P"], f"back on pattern {s7['n'] + 1}: toast {t}")

        print("verify temp-save: while playing")
        e.cmd("frame on")                         # the frame engine: the sequencer runs
        e.tap("play", after=1500)
        e.watch([VOICE_BIND, TICK])
        e.run(2500)
        h = e.hits()
        before = (sum(x[1] == VOICE_BIND for x in h), sum(x[1] == TICK for x in h))
        t, _, _ = gesture(e, "func", "yes", texts)
        sp = e.state()
        edit(e)
        t2, _, _ = gesture(e, "func", "no", texts)
        sq = e.state()
        e.watch([VOICE_BIND, TICK])
        e.run(2500)
        h = e.hits()
        binds = (sum(x[1] == VOICE_BIND for x in h), sum(x[1] == TICK for x in h))
        print(f"        voice binds / sequencer ticks in 2.5 s: before {before}, after the reload {binds}")
        want = bytearray(sp["W"])
        want[SEL:SEL + 2] = sq["W"][SEL:SEL + 2]
        check(t == ["saved"] and t2 == ["reloaded"] and sq["P"] == sp["P"] and sq["W"] == bytes(want)
              and binds[0] > 0 and binds[1] > 0 and before[1] > 0, f"playing: toasts {t + t2}, pattern {diff(sq['P'], sp['P'])} and Part "
              f"{diff(sq['W'], want)} bytes off, the sequencer runs on")
        e.tap("stop", after=800)

        print("verify temp-save: the pattern moved to another Part")
        t, _, _ = gesture(e, "func", "yes", texts)
        sa = e.state()
        p0 = sa["p"]
        if MKI:
            e.chord("func", "midi", after=600)
        else:
            e.tap("part", after=600)
        e.tap("down" if p0 < 3 else "up", after=300)
        e.tap("yes", after=800)
        sb = e.state()
        other = lambda: e.peek(sb["bank"] + PARTS + sb["p"] * PART_LEN, PART_LEN)
        edit(e)
        e.key("scene_a", True)
        e.run(150)
        e.tap("trig11")                           # this Part's scene A := 11, unlike the saved Part's
        e.key("scene_a", False)
        e.run(400)
        before_other = other()
        own_sel = e.peek(sa["bank"] + PARTS + p0 * PART_LEN + SEL, 2)
        t2, _, _ = gesture(e, "func", "no", texts)
        sc = e.state()
        want = bytearray(sa["W"])
        want[SEL:SEL + 2] = own_sel
        check(own_sel != before_other[SEL:SEL + 2], f"the two Parts' scene selections differ "
              f"({list(own_sel)} / {list(before_other[SEL:SEL + 2])})")
        check(sb["p"] != p0 and t2 == ["reloaded"] and sc["p"] == p0 and sc["P"] == sa["P"]
              and sc["P"][PAT_PART] == p0 and sc["W"] == bytes(want),
              f"Part {p0 + 1} -> {sb['p'] + 1}, FUNC + NO: toast {t2}, Part {sc['p'] + 1} again, pattern "
              f"{diff(sc['P'], sa['P'])} and Part {diff(sc['W'], want)} bytes off")
        after_other = other()
        check(after_other == before_other,
              f"Part {sb['p'] + 1}, where the edits went, is as the edits left it")
        print("verify temp-save: another bank")
        e.tap("bank", after=600)
        e.tap("trig3", after=600)
        e.tap("trig1", after=1500)
        if is_open(e):
            e.tap("no", after=600)
        sd = e.state()
        t, _, _ = gesture(e, "func", "no", texts)
        check(e.peek(CUR_BANK, 1)[0] == 2 and t == ["none"] and e.state()["P"] == sd["P"], f"bank C: toast {t}, nothing changed")
        hs = lambda: e.peek(e.u32(BANK_PTR) + HAS_SAVED + e.peek(CUR_PART, 1)[0], 1)[0]
        hs0 = hs()
        t, _, _ = gesture(e, "func", "yes", texts)
        se = e.state()
        edit(e)
        t2, _, _ = gesture(e, "func", "no", texts)
        sf = e.state()
        want = bytearray(se["W"])
        want[SEL:SEL + 2] = sf["W"][SEL:SEL + 2]
        check(hs0 == 0 and t == ["saved"] and t2 == ["reloaded"] and sf["P"] == se["P"] and sf["W"] == bytes(want)
              and hs() == 0 and sf["S"] == se["S"],
              f"no saved Part (has-saved {hs0}): toasts {t + t2}, restored, has-saved {hs()} after, saved slot unchanged")
        edit(e)
        sg = e.state()
        e.chord("func", "cue", after=800)
        check(e.state()["W"] == sg["W"], "stock RELOAD PART still finds no saved copy there and changes nothing")

        print("verify temp-save: MIDI mode")
        e.tap("midi", after=600)
        t, _, _ = gesture(e, "func", "yes", texts)
        sh = e.state()
        e.tap("rec", after=400)
        e.tap("trig4")
        e.tap("rec", after=400)
        e.tap("pg_amp")
        e.knob(0, 13)
        si = e.state()
        t2, _, _ = gesture(e, "func", "no", texts)
        sj = e.state()
        check(e.peek(0x80000012, 4) != b"\0\0\0\0" and t == ["saved"] and t2 == ["reloaded"]
              and (diff(si["P"], sh["P"]) + diff(si["W"], sh["W"])) > 0 and sj["P"] == sh["P"]
              and sj["W"][:SEL] + sj["W"][SEL + 2:] == sh["W"][:SEL] + sh["W"][SEL + 2:],
              f"MIDI mode: toasts {t + t2}, edits moved {diff(si['P'], sh['P'])} pattern and {diff(si['W'], sh['W'])} "
              f"Part bytes, restored")
        e.tap("midi", after=600)

        print("verify temp-save: key order")
        for k in ("yes", "no"):
            e.key("func", True); e.run(150)
            e.key(k, True); e.run(150)
            e.key("func", False); e.run(150)
            e.key(k, False); e.run(600)
        e.tap("mixer", after=800)
        e.watch([YES_REJOIN, NO_REJOIN])
        e.chord("func", "yes", after=400)
        e.chord("func", "no", after=400)
        h = e.hits()
        ry, rn = sum(x[1] == YES_REJOIN for x in h), sum(x[1] == NO_REJOIN for x in h)
        e.tap("mixer", after=800)
        check(ry == 2 and rn == 2, f"after FUNC released first: in MIXER stock gets FUNC + YES {ry}/2 and FUNC + NO {rn}/2 "
              "(press and release)")

        e.tap("bank", after=600)                  # back to bank A, pattern 1
        e.tap("trig1", after=600)
        e.tap("trig1", after=1500)
        if is_open(e):
            e.tap("no", after=600)
        check(e.peek(CUR_BANK, 1)[0] == 0, "back on bank A")

        print("verify temp-save: stock flows")
        e.watch([ARM_ALL, DISARM_ALL, NOTIFY])
        e.tap("yes", after=600)
        e.tap("no", after=600)
        h = e.hits()
        check(any(x[1] == ARM_ALL for x in h) and any(x[1] == DISARM_ALL for x in h) and not toasts(h, texts),
              "YES alone reaches ARM ALL, NO alone DISARM ALL, no module toast")
        e.chord("func", "cue", after=800)
        s10 = e.state()
        check(s10["W"][:MACH] + s10["W"][MACH + 8:] == s10["S"][:MACH] + s10["S"][MACH + 8:],
              "RELOAD PART (FUNC + CUE) restores the saved Part")
        t, _, _ = gesture(e, "func", "yes", texts)    # a copy for the power cycle to lose
        e.run(1000)
        cs1 = e.peek(0x10000000, 0x100000)
        e.cmd("card flush", "card")
    finally:
        e.quit()

    print("verify temp-save: power cycle")
    (work / "cs1.bin").write_bytes(cs1)
    e = Emu(card, work / "pc.log", extra=("--cs1-in", str(work / "cs1.bin"), "--no-post"))
    try:
        e.run(4000)
        e.tap("yes", after=1500)
        s0 = e.state()
        t, _, disarm = gesture(e, "func", "no", texts)
        s1 = e.state()
        check(t == ["none"] and s1["P"] == s0["P"] and s1["W"] == s0["W"],
              f"after the power cycle: toast {t}, nothing changed")
    finally:
        e.quit()

    print(f"verify temp-save: {'FAIL' if FAILS else 'PASS'} ({len(FAILS)} failed)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
