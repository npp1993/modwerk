# SPDX-License-Identifier: MIT
"""Synthetic private MWMDv2 AB declarations: no actual import/packet admission."""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
import sys
import test_machine_declarations as base
import machine_declarations as declarations
import machine_layout as layout

ROOT=Path(__file__).resolve().parents[2]
ADAPTER=ROOT/'sdk/machines/octatrack/module-adapters'

# Preserve unittest discovery's SDK wrapper precedence over adapter fixtures.
sys.path.insert(0,str(Path(__file__).resolve().parent))


class AbParticipantTests(base.DeclarationTests):
    def selections(self):
        return [(mask,qz,ab) for ab in (False,True) for mask,qz in
                [(m,False) for m in range(1,8)]+[(m,True) for m in range(1,4)]]

    def entry_for(self,index,mask,qz,ab):
        data=bytearray(self.package);data[81]=mask;data[76+24]=index+1
        return self.entry(bytes(data),schema=layout.ANALOG_BD_SCHEMA,
                          participants=list(layout.canonical_participants(mask,qz,ab)))

    def test_twenty_exact_variants_fit_without_mask_or_participant_inference(self):
        selections=self.selections();entries=[self.entry_for(i,*v) for i,v in enumerate(selections)]
        table=declarations.generate(entries)
        self.assertEqual((len(table),table[:7]),(1072,b'MWMD\2\24\30'))
        rows=[table[16+44*n:16+44*(n+1)] for n in range(20)]
        self.assertEqual(len({r[:32] for r in rows}),20)
        self.assertEqual(sum(bool(r[37]&2) for r in rows),10)
        self.assertEqual(sum(bool(r[37]&1) for r in rows),6)
        self.assertEqual({(r[36],r[37]) for r in rows},
                         {(m,(int(qz)|int(ab)<<1)) for m,qz,ab in selections})
        self.assertEqual(set(table[16+44*20:]),{0})
        for entry in entries:
            checked=layout.validate(**entry)
            self.assertEqual(checked.package_sha256,hashlib.sha256(entry['package']).hexdigest())
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            declarations.generate(entries+[entries[0]])

    def test_ab_needs_explicit_new_schema_and_exact_source_review(self):
        entry=self.entry_for(0,1,False,True)
        for changes in (dict(schema=layout.PARTICIPANT_SCHEMA,participants=['poly8','analog-bassdrum']),
                        dict(schema=layout.SCHEMA,participants=['poly8','analog-bassdrum']),
                        dict(participants=['analog-bassdrum','poly8']),dict(participants=['poly8','analog-bassdrum','analog-bassdrum']),
                        dict(participants=['poly8','unknown'])):
            with self.assertRaises(ValueError):declarations.generate([self.entry(entry['package'],**changes)])
        altered=dict(entry,reviewed_sha256='0'*64)
        with self.assertRaises(ValueError):declarations.generate([altered])
        (self.root/'engine.s').write_bytes(b'source drift\n')
        with self.assertRaisesRegex(ValueError,'source changed'):declarations.generate([entry])

    def test_actual_host_and_coldfire_default_closed_contract(self):
        cc=shutil.which('cc');gcc=shutil.which('m68k-elf-gcc');nm=shutil.which('m68k-elf-nm')
        if not cc or not gcc or not nm:self.skipTest('host and ColdFire compilers required')
        sources=['machine_admission','machine_declarations','machine_lifetime','machine_parts','test_machine_ab_participants']
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);out=folder/'host'
            subprocess.run([cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ADAPTER),
                            '-I'+str(ROOT/'sdk/runtime/loader'),'-I'+str(ROOT/'sdk/runtime/upload'),
                            *[str(ADAPTER/(name+'.c')) for name in sources],'-o',str(out)],check=True,capture_output=True)
            subprocess.run([str(out)],check=True,capture_output=True)
            for name in sources[:-1]:
                subprocess.run([gcc,'-mcpu=5475','-msoft-float','-O2','-ffreestanding','-fno-builtin',
                                '-Wall','-Wextra','-Werror','-I'+str(ADAPTER),'-I'+str(ROOT/'sdk/runtime/loader'),
                                '-I'+str(ROOT/'sdk/runtime/upload'),'-c',str(ADAPTER/(name+'.c')),
                                '-o',str(folder/(name+'.o'))],check=True,capture_output=True)
            obj=folder/'storage.o'
            subprocess.run([gcc,'-mcpu=5475','-msoft-float','-O2','-ffreestanding','-fno-builtin',
                            '-Wall','-Wextra','-Werror','-I'+str(ADAPTER),'-I'+str(ROOT/'sdk/runtime/loader'),
                            '-I'+str(ROOT/'sdk/runtime/upload'),'-c',str(ADAPTER/'machine_declarations.c'),'-o',str(obj)],check=True,capture_output=True)
            text=subprocess.check_output([nm,'-S',str(obj)],text=True)
            self.assertRegex(text,r'00000430 [Rr] modwerk_machine_declarations')


if __name__=='__main__':unittest.main()
