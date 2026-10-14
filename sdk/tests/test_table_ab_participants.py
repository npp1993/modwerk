# SPDX-License-Identifier: MIT
"""Synthetic AB table associations; never actual controller/import qualification."""
from pathlib import Path
import hashlib
import json
import struct
import unittest
import sys
ADAPTER = Path(__file__).resolve().parents[1] / 'machines/octatrack/module-adapters'
sys.path.append(str(ADAPTER))
import machine_layout as layout
import table_declarations as declarations
import test_table_declarations as base

# Preserve unittest discovery's SDK wrapper precedence over adapter fixtures.
sys.path.insert(0,str(Path(__file__).resolve().parent))


class AbTableParticipantTests(base.TableDeclarationTests):
    def changed(self,entry,index,mask=None,optional=False,ab=False,schema=None):
        package=bytearray(entry['package']);size=struct.unpack_from('>I',package,8)[0]
        package[76+24]=index+1
        if mask is not None:
            package[7]=4;package[76:76+16]=b'MWMG\1'+bytes((mask,))+bytes(10)
            struct.pack_into('>I',package,28,0xdb769930)
        image=package[76:76+size];captured=json.loads(entry['recipe']);captured['imageSha256']=base.sha(image)
        recipe=json.dumps(captured).encode();doc=json.loads(entry['declaration'])
        doc.update(packageSha256=base.sha(package),imageSha256=base.sha(image),
                   compiledImageSha256=base.sha(image),recipeSha256=base.sha(recipe))
        if mask is not None:
            doc.update(schema=schema or declarations.ANALOG_BD_SCHEMA,
                       participants=list(layout.canonical_participants(mask,optional,ab)))
        encoded=json.dumps(doc).encode()
        return dict(entry,package=bytes(package),recipe=recipe,declaration=encoded,reviewed_sha256=base.sha(encoded))

    def test_seventeen_qz_group_and_distinct_mutes_records_fit_exactly(self):
        variants=[(m,False) for m in range(4,8)]+[(m,True) for m in range(1,4)]
        entries=[self.changed(self.entry(),i,mask,qz,ab) for i,(mask,qz,ab) in
                 enumerate((m,qz,ab) for ab in (False,True) for m,qz in variants)]
        entries+=[self.changed(self.entry(),14),self.changed(self.entry('mute-modes'),15),
                  self.changed(self.entry('mute-modes'),16)]
        output=declarations.generate(entries)
        self.assertEqual((len(output),output[:7]),(1456,b'MWTD\1\21\30'))
        self.assertEqual(len({output[16+60*i:48+60*i] for i in range(17)}),17)
        self.assertEqual(sum(output[16+60*i+40]==1 for i in range(17)),15)
        self.assertEqual(sum(output[16+60*i+40]==2 for i in range(17)),2)
        self.assertEqual(set(output[16+60*17:]),{0})
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            declarations.generate(entries+[entries[0]])

    def test_ab_participants_cannot_enter_old_schema_or_false_table_family(self):
        for schema in (declarations.SCHEMA,declarations.PARTICIPANT_SCHEMA):
            with self.assertRaises(ValueError):
                declarations.validate(**self.changed(self.entry(),0,4,False,True,schema=schema))
        with self.assertRaises(ValueError):
            declarations.validate(**self.changed(self.entry(),0,1,False,True))
        entry=self.changed(self.entry(),0,1,True,True)
        self.assertEqual(declarations.validate(**entry).family,1)
        with self.assertRaises(ValueError):
            declarations.validate(**dict(entry,reviewed_sha256='0'*64))
        (self.root/'table.s').write_bytes(b'source drift\n')
        with self.assertRaisesRegex(ValueError,'source changed'):
            declarations.validate(**entry)


if __name__=='__main__':unittest.main()
