# SPDX-License-Identifier: GPL-3.0-or-later
"""Private base binding for staged packages; no USB, publication or raw output."""
import hashlib
from pathlib import Path
import struct
import importlib.util

LOAD = 0x40000400
POOL_BYTES = 768 * 1024
ARENA_WORDS = (0x4000045e, 0x4000046c, 0x400004c8)
# Trusted source helper, never a runtime tool-selected path.
_private_spec = importlib.util.spec_from_file_location("candidate_private_paths",
    Path(__file__).resolve().parents[4] / "scripts/runtime_private_paths.py")
private_paths = importlib.util.module_from_spec(_private_spec)
_private_spec.loader.exec_module(private_paths)
_run_pack_spec = importlib.util.spec_from_file_location("candidate_run_pack",
    Path(__file__).resolve().parents[1] / "elekloader/run_pack.py")
run_pack = importlib.util.module_from_spec(_run_pack_spec)
_run_pack_spec.loader.exec_module(run_pack)


def private_output(path):
    path = Path(path).expanduser().absolute()
    if path.exists() or path.is_symlink():
        raise ValueError('Candidate output must be new and outside Git.')
    return private_paths.private_directory(path)


def bind_base(main, symbols, proof):
    """Independently bind actual private image, IDENTIFY digest, arena and pool.

    Maps and images are explicit developer inputs, never MCP tool arguments.
    This verifies a preparation binding, not physical boot or lifetime safety.
    """
    arena, pool = symbols.get('arena_base'), symbols.get('pool')
    start, end, identity = (symbols.get(name) for name in ('__bss_start', '__bss_end', 'modwerk_base_digest'))
    if (any(type(value) is not int for value in (arena, pool, start, end, identity))
            or not (0x40a955e0 < arena < 0x47f00000 and start <= pool and pool + POOL_BYTES <= end)):
        raise ValueError('Candidate map must name the moved arena and bounded runtime pool.')
    for address in ARENA_WORDS:
        at = address - LOAD
        if at + 4 > len(main) or struct.unpack_from('>I', main, at)[0] != arena:
            raise ValueError('Candidate image and map disagree on the moved arena.')
    manifest = proof.get('manifest', {})
    layout = manifest.get('link', {}).get('layout', {})
    ddr, run_load = layout.get('ddr'), layout.get('run_load')
    if (manifest.get('main_sha256') != hashlib.sha256(main).hexdigest() or manifest.get('main_len') != len(main)
            or not isinstance(ddr, list) or len(ddr) != 2 or any(type(value) is not int for value in ddr)
            or type(run_load) is not int or not ddr[0] <= identity <= ddr[1] - 32):
        raise ValueError('Candidate native link proof does not bind the exact image and identity location.')
    # The core's .run bytes live packed in the appended FLASH blob, then boot
    # unpacks them to DDR (run_pack.py). A DDR symbol is not an offset into MAIN.raw.
    plain = run_pack.unpack(main, layout, symbols, LOAD)
    at = run_load - LOAD + identity - ddr[0]
    if at < 0 or at + 32 > len(plain) or not any(plain[at:at + 32]):
        raise ValueError('Candidate IDENTIFY digest lies outside its actual image or is empty.')
    if plain[at:at + 32].hex() != proof.get('configurationHash'):
        raise ValueError('Candidate authored IDENTIFY bytes differ from its native proof.')
    return dict(identity=plain[at:at + 32].hex(), arena=arena, pool=pool, poolOrigins=pool_origins(pool),
                imageSha256=hashlib.sha256(main).hexdigest())


def pool_origins(pool):
    """The two origins a pool unit is linked at to prove it relocates (uncached aliases inside the pool)."""
    return (pool + 0x08001000, pool + 0x08004000)


def guarded_arena_literals(image, relocations, arena, expected):
    """Reconstruct proven recorder literals from a checked running-base word.

    This is a four-byte resource guard, not a configuration-identity check.
    The existing loader reads this cached MAIN address through its uncached
    machine view; the literal itself retains the fresh source's exact alias.
    """
    if (type(arena) is not int or not 0x40a955e0 < arena < 0x47f00000 or arena & 3
            or type(expected) is not int or not 0 < expected <= 128):
        raise ValueError('Recorder literals need their exact bounded native arena census.')
    word = struct.pack('>I', arena)
    offsets = [at for at in range(0, len(image) - 3, 2) if image[at:at + 4] == word]
    if (len(offsets) != expected or any(a + 4 > b for a, b in zip(offsets, offsets[1:]))
            or any(at < r + 4 and r < at + 4 for at in offsets for r in relocations)):
        raise ValueError('Recorder arena literals differ from their independent native proof.')
    guarded = bytearray(image)
    digest = hashlib.sha256(word).digest()
    for at in offsets:
        guarded[at:at + 4] = bytes(4)
    return bytes(guarded), [(at, ARENA_WORDS[0], 4, digest) for at in offsets]


def check_sites_and_copies(main, sites, copies):
    """The installed base itself must preserve every runtime stock guard."""
    for address, length, guard in ([(address, checked, digest) for address, digest, _, _, _, checked in sites]
                                    + [(address, length, digest) for _, address, length, digest in copies]):
        at = address - LOAD
        if at < 0 or at + length > len(main) or hashlib.sha256(main[at:at + length]).digest() != guard:
            raise ValueError('A staged runtime site or copy disagrees with the exact candidate base.')
