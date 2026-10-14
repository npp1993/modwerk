#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Write Analog BD's declared DSP price from private emulator chain results.

Inputs are the private `chains.json` files of octabam's benchmark_analog_bd.py
for an AB image and for the original image (same project, FX and window). The
output holds figures and hashes only. Executed instructions stay executed
instructions: the loader converts them like any other emulator-kind claim.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ('ab_glue.asm', 'bd909.asm', 'bd808.asm', 'dsp909.py', 'dsp808.py', 'fit909.json')
BUILD = ('tools/build/ab_image.py', 'tools/build/ab_records.py')
# Engine-only per-voice peak, 0.1.4 DSP (0.1.5 is byte-identical): 6563 executed
# instructions per 16-sample block, evidence/909-reference-costs.json.
ENGINE_PEAK = ('sdk/octabam/modules/analog-bassdrum/evidence/909-reference-costs.json', 6563)
VOICE = 411       # ceil(6563 / 16): the dearer model; MODEL is a knob, so one price
FEATURE = 3       # per core while the engine is on: measured seam path + resident stub
PAIRS = (('dark-909pair', 'dark-stock', 2), ('dark-909eight-core1', 'dark-stock', 4),
         ('eq-909pair-core0', 'eq-stock-core0', 2), ('eq-909pair-flex', 'eq-stock-flex', 2), ('dark-808pair', 'dark-stock', 2),
         ('dark-808eight-core1', 'dark-stock', 4))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def declaration(ab_chains, stock_chains):
    ab = {r['case']: r for path in ab_chains for r in json.loads(Path(path).read_text())['rows']}
    stock = {r['case']: r for r in json.loads(Path(stock_chains).read_text())['rows']}
    increments = []
    for case, base, voices in PAIRS:
        a, b = ab[case], ab[base]
        increments.append(dict(case=case, baseline=base, voices=voices, core=a['core'],
                               meanPerVoice=round((a['mean'] - b['mean']) / voices, 4),
                               peakPerVoice=round((a['peak'] - b['peak']) / voices, 4)))
    seam = [dict(case=case, core=ab[case]['core'], mean=round(ab[case]['mean'] - stock[case]['mean'], 4),
                 peak=round(ab[case]['peak'] - stock[case]['peak'], 4)) for case in ('dark-stock', 'eq-stock-core0')]
    worst = max(max(row['meanPerVoice'], row['peakPerVoice']) for row in increments)
    if worst > VOICE or max(max(row['mean'], row['peak']) for row in seam) + 0.25 > FEATURE:
        raise ValueError('A measured increment exceeds the declared AB price; review the price.')
    return dict(
        schema='modwerk-ab-dsp-price-v1', moduleId='analog-bassdrum', version='0.1.5-experimental',
        kind='executed-instructions', units='DSP instructions per sample',
        perVoice=VOICE, perVoiceBasis='engine-only peak per 909 voice, ceil(%d/16), from %s' % (ENGINE_PEAK[1], ENGINE_PEAK[0]),
        perCoreWhileEnabled=FEATURE,
        perCoreBasis='seam path on non-AB tracks measured +%.2f (AB image vs original, same chain), plus the resident '
                     'dormant-branch jmp, 4 tracks x 1 instruction per 16-sample block = 0.25 (static count)'
                     % max(max(row['mean'], row['peak']) for row in seam),
        replaces='the stock source stage of its own track (measured above THRU and above FLEX); FX1/FX2 of that track stay ordinary slots',
        voicesPerCore=4,
        measuredIncrements=increments, measuredSeam=seam,
        sourcePins={**{'sdk/octabam/modules/analog-bassdrum/' + n: sha(ROOT / 'sdk/octabam/modules/analog-bassdrum' / n) for n in SOURCES},
                    **{'sdk/octabam/' + n: sha(ROOT / 'sdk/octabam' / n) for n in BUILD},
                    ENGINE_PEAK[0]: sha(ROOT / ENGINE_PEAK[0])},
        chains={'analogBd': [dict(sha256=sha(path), imageSha256=json.loads(Path(path).read_text())['rows'][0]['image_sha256']) for path in ab_chains],
                'original': dict(sha256=sha(stock_chains), imageSha256=next(iter(stock.values()))['image_sha256'])},
        limits=['ot_emu executed instructions over the four-track window, 850 frames after 50 warm-up, 300 BPM retriggers; '
                'not modeled chip cycles, physical timing or hardware headroom.',
                'Increments are differences of window peaks/means between runs, not per-block paired differences.',
                'Image: loader-free card composition of the same 0.1.5 DSP sources; the USB base runs that engine resident.',
                'Private harness patch: the current registry has no stock FX parameters, so the project keeps its own FX bytes.'],
        hardware=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ab-chains', type=Path, required=True, action='append')
    parser.add_argument('--original-chains', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('analog_bd_dsp_price.json'))
    args = parser.parse_args()
    args.out.write_text(json.dumps(declaration(args.ab_chains, args.original_chains), indent=1) + '\n')


if __name__ == '__main__':
    main()
