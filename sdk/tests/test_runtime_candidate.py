# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic exact-base/guard/declaration regressions; no firmware or USB."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / 'sdk/machines/octatrack/module-adapters'))
import runtime_candidate as candidate
import standalone_runtime as standalone
import candidate_packages as packages


def stored(data):
    """The kit's section format, every byte a literal (run_pack.py's stream, without the kit's match finder)."""
    tail = bin((1 << 24) + 2)[3:]
    bits = [(1, bytes((b,))) for b in data] + [(0, b'')] + [e for i, b in enumerate(tail) for e in (
        (int(b), b''), (int(i == len(tail) - 1), b'\xff' if i == len(tail) - 1 else b''))]
    body = b''.join(bytes((sum(bit << 7 - k for k, (bit, _) in enumerate(bits[i:i + 8])),)) +
                    b''.join(p for _, p in bits[i:i + 8]) for i in range(0, len(bits), 8))
    return len(body).to_bytes(4, 'big') + (sum(body) & 0xffffffff).to_bytes(4, 'big') + body


def fixture():
    main = bytearray(0x300)
    symbols = dict(arena_base=0x40d00000, pool=0x48001000, __bss_start=0x48001000,
                   __bss_end=0x48100000, modwerk_base_digest=0x48000010,
                   __run_load=candidate.LOAD + 0x200, __run_start=0x48000000, __run_words=0x40)
    for address in (0x4000045e, 0x4000046c, 0x400004c8):
        struct.pack_into('>I', main, address - candidate.LOAD, symbols['arena_base'])
    main[0x210:0x230] = bytes(range(1, 33))
    layout = dict(ddr=[0x48000000, 0x48000100], run_load=candidate.LOAD + 0x200)
    main, _ = candidate.run_pack.pack(main, layout, symbols, candidate.LOAD, stored)
    proof = dict(configurationHash=bytes(range(1, 33)).hex(), manifest=dict(
        main_sha256=hashlib.sha256(main).hexdigest(), main_len=len(main), link=dict(layout=layout)))
    return bytes(main), symbols, proof


class CandidateTests(unittest.TestCase):
    def test_recorder_literals_reconstruct_exact_alias_with_device_resource_guard(self):
        for arena in (0x40d00000, 0x48d00000):
            if arena >= 0x47f00000:
                with self.assertRaises(ValueError):
                    candidate.guarded_arena_literals(struct.pack('>I', arena), [], arena, 1)
                continue
            word = struct.pack('>I', arena)
            image = b'\x12\x34' + word + b'\x4e\x75' + word
            guarded, copies = candidate.guarded_arena_literals(image, [], arena, 2)
            self.assertEqual(guarded, b'\x12\x34' + bytes(4) + b'\x4e\x75' + bytes(4))
            restored = bytearray(guarded)
            for offset, address, length, digest in copies:
                self.assertEqual((address, length), (candidate.ARENA_WORDS[0], 4))
                self.assertEqual(digest, hashlib.sha256(word).digest())
                restored[offset:offset + length] = word
            self.assertEqual(restored, image)
            for expected, relocs in ((1, []), (3, []), (True, []), (2, [0]), (2, [10])):
                with self.assertRaises(ValueError):
                    candidate.guarded_arena_literals(image, relocs, arena, expected)

    def test_private_hybrid_refuses_alternate_dsp_payload_or_resource_figures(self):
        spec = importlib.util.spec_from_file_location('candidate_test_private_builder', ROOT / 'sdk/runtime/loader/build.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        fields = dict(octabam='tapeecho', stock=Path('/nonexistent-stock'), upstream=Path('/nonexistent-upstream'),
                      no_page=False, page_from=None, name=None, layout=1, stock_recipe=None, capture_stock_recipe=None,
                      slots='fx2', dsp=str(ROOT / 'src/engine/assets/dsp-packages.json') + ':tapeecho',
                      cycles=4, cycles_kind='modeled', state=1, buffer=0, pinned=True)
        for changed in ({'dsp': str(ROOT / 'src/engine/assets/dsp-packages.json') + ':euclid'},
                        {'dsp': '/tmp/alternate.json:tapeecho'}, {'cycles': 3}, {'state': 0}, {'pinned': False}, {'name': 'Other'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                builder.private_standalone(SimpleNamespace(**dict(fields, **changed)))

    def test_identity_comes_from_appended_flash_run_blob_not_ddr_offset(self):
        main, symbols, proof = fixture()
        binding = candidate.bind_base(main, symbols, proof)
        self.assertEqual(binding['identity'], bytes(range(1, 33)).hex())
        self.assertEqual(binding['arena'], symbols['arena_base'])
        self.assertEqual(binding['poolOrigins'], (0x50002000, 0x50005000))
        # A plausible map with the same arena/pool cannot substitute its digest.
        for key, value in (('modwerk_base_digest', 0x48000020), ('arena_base', 0x40d00004),
                           ('pool', symbols['__bss_end'] - 32), ('arena_base', True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate.bind_base(main, {**symbols, key: value}, proof)

    def test_stale_image_native_proof_layout_and_identity_refuse(self):
        main, symbols, proof = fixture()
        broken = bytearray(main); broken[-1] = 1
        with self.assertRaises(ValueError):
            candidate.bind_base(bytes(broken), symbols, proof)
        for mutate in (lambda p: p.update(configurationHash='ff' * 32),
                       lambda p: p['manifest'].update(main_len=len(main) + 1),
                       lambda p: p['manifest']['link']['layout'].update(run_load=0x50000000),
                       lambda p: p['manifest']['link']['layout'].update(ddr=[0x48000020, 0x48000100]),
                       lambda p: p['manifest']['link']['layout'].update(ddr=[0x48000000, 0x48000020])):
            damaged = copy.deepcopy(proof); mutate(damaged)
            with self.subTest(proof=damaged['manifest']['link']['layout']), self.assertRaises(ValueError):
                candidate.bind_base(main, symbols, damaged)

    def test_original_guard_must_also_match_actual_base(self):
        main = b'authored fixture code'
        guard = hashlib.sha256(main[:8]).digest()
        sites = [(candidate.LOAD, guard, b'\0' * 8, [2], 0, 8)]
        copies = [(0, candidate.LOAD, 8, guard)]
        candidate.check_sites_and_copies(main, sites, copies)
        for changed in (b'X' + main[1:], main[:4]):
            with self.assertRaises(ValueError):
                candidate.check_sites_and_copies(changed, sites, copies)

    def test_output_is_new_private_and_outside_git(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            created = candidate.private_output(root / 'proof')
            if os.name == 'nt':
                candidate.private_paths.check_windows_acl(candidate.private_paths.windows_acl(created), directory=True)
            else:
                self.assertEqual(created.stat().st_mode & 0o777, 0o700)
            artifact = created / 'owned.bin'
            candidate.private_paths.save(artifact, b'owned synthetic bytes')
            self.assertEqual(artifact.read_bytes(), b'owned synthetic bytes')
            with self.assertRaises(FileExistsError):
                candidate.private_paths.save(artifact, b'changed')
            self.assertEqual(artifact.read_bytes(), b'owned synthetic bytes')
            if os.name == 'nt':
                candidate.private_paths.check_windows_acl(candidate.private_paths.windows_acl(artifact), directory=False)
            else:
                self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                candidate.private_output(created)
            repo = root / 'repo'; repo.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
            with self.assertRaises(ValueError):
                candidate.private_output(repo / 'nested' / 'private')

    def test_authored_provenance_exact_guard_and_nonoverlap_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'unit.s'; path.write_text('entry:\n rts\n')
            image = b'\x12\x34\x56\x78' * 4
            inputs = {'unit.s': standalone.digest(path.read_bytes())}
            row = dict(offset=4, length=4, address=0x40001000, sha256=standalone.digest(image[4:8]),
                       purpose='Reviewed authored return sequence',
                       authored=dict(source='unit.s', lines=[1, 2], symbol='entry', method='native-unit'))
            recipe = dict(schema=1, sources=inputs, imageSha256=standalone.digest(image), copies=[row], fills=[])
            read = lambda address, n: image[4:4 + n]
            emitted, copies = standalone.apply(image, [], recipe, inputs, root, read)
            self.assertEqual(emitted, image[:4] + bytes(4) + image[8:])
            self.assertEqual(len(copies), 1)
            for change in (lambda r: r.update(fills=[{}]), lambda r: r.update(imageSha256='ff' * 32),
                           lambda r: r['copies'][0]['authored'].update(lines=[1, 3]),
                           lambda r: r['copies'][0]['authored'].update(source='../foreign.s'),
                           lambda r: r['copies'].append(copy.deepcopy(row))):
                damaged = copy.deepcopy(recipe); change(damaged)
                with self.assertRaises(ValueError):
                    standalone.apply(image, [], damaged, inputs, root, read)
            with self.assertRaises(ValueError):
                standalone.apply(image, [4], recipe, inputs, root, read)
            with self.assertRaises(ValueError):
                standalone.apply(image, [], recipe, inputs, root, lambda address, n: bytes(n))

    def test_guards_are_decoded_from_actual_records_and_truncation_refuses(self):
        spec = importlib.util.spec_from_file_location('candidate_test_builder', ROOT / 'sdk/runtime/loader/build.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        guard = hashlib.sha256(b'authored return').digest()
        sites = [(candidate.LOAD, guard, b'\x4e\x71' * 3, [2], 0, 6)]
        copies = [(8, candidate.LOAD + 8, 4, guard)]
        data = builder.package(bytes(16), 0, [], [], sites, name='fixture', hashed=True,
                               title='Fixture', copies=copies, abi=8)
        actual_sites, actual_copies = packages.records(data)
        self.assertEqual(actual_sites[0][:3], sites[0][:3])
        self.assertEqual(actual_sites[0][-2:], sites[0][-2:])
        self.assertEqual(actual_copies, copies)
        for damaged in (data[:6], data[:76], data[:-1], b'bad!'):
            with self.assertRaises(ValueError):
                packages.records(damaged)


if __name__ == '__main__':
    unittest.main()
