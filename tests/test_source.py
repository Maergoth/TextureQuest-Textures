"""Tiny synthetic archive integration; never opens a game or production asset."""
from pathlib import Path
import copy,hashlib,json,struct,sys,tempfile,unittest,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_source as build
import verify_source as verify
fmt=build.fmt

def dds(value):
    w=[0]*31;w[0],w[1],w[2],w[3],w[6],w[18]=124,0x21007,8,8,1,32
    w[19:26]=[0x41,0,32,0xff0000,0xff00,0xff,0xff000000];w[26]=0x1000
    return b'DDS '+struct.pack('<31I',*w)+bytes([value,4,7,255])*64+b'kept tail'
def make_vpk(rows):
    body=bytearray();table=bytearray()
    for name,data in rows:
        name=name.encode()
        packed=zlib.compress(struct.pack('<II',len(name)+1,len(data))+name+b'\0'+data)
        table+=struct.pack('<III',len(body),len(packed),len(name))+name
        body+=struct.pack('<I',len(packed))+packed
    index=zlib.compress(struct.pack('<II',len(table)+8,len(rows))+table)
    return bytes(body)+struct.pack('<I',len(index)+12)+index+struct.pack('<III',0x33744,len(body),2)
class SourceTests(unittest.TestCase):
    def setUp(self):
        base=Path(r'D:\eq2 paks\work\tmp');base.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base,prefix='dds-source-');self.root=Path(self.tmp.name)
        self.a,self.b=dds(10),dds(20)
        self.archive=self.root/'fixture.vpk'
        self.archive.write_bytes(make_vpk([('a.dds',self.a),('b.dds',self.a),('c.dds',self.b),('unselected.txt',b'not a texture')]))
        self.rows=[]
        original=dds(1);layout,pixels,_=fmt.decode_dds(original)
        for name,raw in [('a.dds',self.a),('b.dds',self.a),('c.dds',self.b)]:
            target,tp,_=fmt.decode_dds(raw)
            self.rows.append(dict(owner='fixture.vpk',member=name,source_layout=list(layout),target_layout=list(target),
                source_fingerprint=fmt.fingerprint(layout,pixels),target_fingerprint=fmt.fingerprint(target,tp),
                source_dds_sha256=build.sha(original),target_dds_sha256=build.sha(raw),payload_sha256=build.sha(tp)))
        self.binding=dict(texture_version='1.2.3',archives=[dict(path=str(self.archive),name='fixture.vpk',bytes=self.archive.stat().st_size,sha256=build.sha(self.archive.read_bytes()),entries=4,url='https://example.invalid/inert')])
    def tearDown(self):
        assert self.root.resolve().is_relative_to(Path(r'D:\eq2 paks\work\tmp').resolve())
        self.tmp.cleanup()
    def produce(self):
        out=self.root/'out'
        result=build.build(self.binding,out,limit=450,fixture=({},self.rows))
        return out,result
    def test_exact_only_dds_dedup_tails_chunks_and_ambiguity(self):
        out,result=self.produce()
        self.assertEqual(result['named_texture_count'],3);self.assertEqual(result['unique_dds_count'],2)
        self.assertEqual(result['ambiguous_named_count'],3);self.assertEqual(len(result['chunks']),2)
        checked=verify.verify(out);self.assertEqual(checked['unique_dds'],2)
        self.assertEqual(len(list(out.glob('*.zip'))),2)
        self.assertFalse(list(out.glob('*.vpk')))
    def test_changed_pak_refuses_before_any_texture_is_published(self):
        self.archive.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'PAK hash'):self.produce()
        self.assertFalse(list((self.root/'out').glob('*.zip')))
    def test_changed_selected_dds_refuses(self):
        self.rows[0]['target_dds_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Selected DDS'):self.produce()
    def test_changed_zip_is_not_accepted(self):
        out,result=self.produce();p=out/result['chunks'][0]['name'];raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,'checksum'):verify.verify(out)
    def test_partial_output_directory_is_preserved(self):
        out,result=self.produce()
        with self.assertRaisesRegex(ValueError,'Output exists'):build.build(self.binding,out,fixture=({},self.rows))
        self.assertEqual(verify.verify(out)['unique_dds'],2)
    def test_index_parser_refuses_truncation_and_duplicate_identity(self):
        row=copy.deepcopy(self.rows[0])
        row.update(offset=0,payload_bytes=len(fmt.decode_dds(self.a)[1]))
        wire=fmt.wire_row(row);index=b'TQGX0002'+struct.pack('<IIQ',2,1,row['payload_bytes'])+wire
        self.assertEqual(build.parse_index(index)[0]['member'],'a.dds')
        with self.assertRaisesRegex(ValueError,'Truncated|labels'):build.parse_index(index[:-2])
        duplicate=b'TQGX0002'+struct.pack('<IIQ',2,2,row['payload_bytes'])+wire+wire
        with self.assertRaisesRegex(ValueError,'Duplicate'):build.parse_index(duplicate)
if __name__=='__main__':unittest.main(verbosity=2)
