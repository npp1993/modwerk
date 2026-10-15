# BBD Delay 0.1.0-experimental release resource bounds

Native source: the released folder (`bbd.asm`, `manifest.py`, `bbd_ref.py`).
MAIN OS SHA-256: `bc53d1b3e96a4c22d5efb426c880d08e26d4f0288dccbe8ffaf43e25a18fb3ba`
(BBDMW2), the native build of BBD beside the stock effects, as the site places
it; `sdk/native-comparisons/bbd.json` records the browser's match.

## Software cycle upper bound

Basis: 44.1 kHz, 16 frames/block, eight FX2 instances, four per core.

**Sample work.** `tools/build/cycle_count.py` prices the per-sample loop at
378 modeled cycles with the bucket tick taken and HPF on (its `bsr bbhsec`
charged as inlined, plus the call pair). A block holds at most 16 samples,
split or not: `16 * 378 = 6,048`.

**Per-call work**, a union bound over the assembled program (1,075 words):

| part | modeled cycles |
| --- | ---: |
| every word outside the sample loop and the helpers, once: init (51), the per-call prologue with both the clear path and the run path (545), the tail (8) | 604 |
| extra iterations of the fixed loops: init zeroing (90), the clear's three loops (255 + 56 + 10), the three per-call 24-step divides (3 x 23) | 480 |
| the coefficient rotation, up to nine passes after a reset: 8 extra x 45 words | 360 |
| helper bodies: ten `bbsect` calls, nine for the rotation and one for HPF's section (46 words + 23 extra divide steps each; `bbpole` is smaller), and two `bbexp2` (23 each: LIM and HPF) | 736 |
| control overheads beyond the word count: 19 `do` x 4, 13 `bsr`/`rts` pairs x 6, 34 branches x 4 (each rotation pass's two counted) | 290 |
| **total** | **2,470** |

Rounded up to **2,600 modeled cycles/call**. Charging the clear path and the
run path together, and the reset's nine-section rotation on every call, keeps
it a ceiling for any call.

Two calls per block cover a trigger split. The per-instance block bound is
`6,048 + 2 * 2,600 = 11,248`; four instances cost **44,992/core/block**. The SDK
module allowance is `3,120 * 16 = 49,920`, leaving 4,928 modeled cycles. The
original stock/scheduling reserve is kept outside this allowance. This is a
conservative code-word model, not a whole-instrument contention or wall-clock
guarantee; companion custom effects must fit the remaining budget separately.

For comparison, the matched emulator benchmark (TESTING.md) measures at most
439.44 executed instructions per sample with a trig split at every position.

Commands: `python3 modules/bbd/verify.py` (including the no-op loop marker
proof), `dsp_asm -sym` for the label addresses and `dsp56kDisassemble` for the
control-flow census: no `rep`, no recursion, no helper calls a helper, and no
backward loop outside the priced sample loop other than those counted above.

## Exact reserved memory

Per instance: the stock FX2 allocation, `256 * 3 + 16,384 * 3 = 49,920` bytes.
BBD uses X state `r7+$00..$5a` (91 words) of the 256-word X block, and of the
16,384-word Y buffer the ring (at most 4,095 words) and 58 coefficient words at
`base+$2000..$2039` (nine clock-filter sections, HPF's section, FREQ's
bandpass); the rest is reserved, unused padding.

Shared: two 1,075-word P programs (6,450 bytes; `P:0x01000..0x01433` and
`P:0x00dc0..0x011f3`, in the space of SPRING REV and PLATE REV), the system
stack on both cores (72 bytes, below), the cloned 416-byte FX2 descriptor at
`0x400D6B20` and the 54-byte STGS label formatter at `0x400D6CC0`:
**6,992 bytes**. Eight instances total **406,352 bytes**.

Stack: the deepest nesting is the dispatcher's call, the rotation's `do`, a
`bsr bbsect` and its divide's `do`: six system-stack entries (two 24-bit words
each) per core. The sample loop nests less (call, `do`, `bsr bbhsec`).

DSP numbers are logical 24-bit words; descriptor and formatter counts use byte
accounting. BBD reuses the stock instance buffers and dispatcher stack. There
is no authored heap, SDRAM allocation, ColdFire executable or callback. Its
constants are inline program immediates. `init` leaves r1/n1/m1 unchanged. The
eight-instance guard and dirty-start gates cover software isolation; they do
not claim hardware canaries.
