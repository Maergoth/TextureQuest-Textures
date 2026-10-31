"""Stream only declared released DDS members into immutable download chunks.
No game/source/model access, image re-encoding, PAK writes or generator control.
Input binding files are private local build inputs and must not be published.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,os,re,struct,sys,time,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent/'lib'))
import texture_formats as fmt
import vpk
import categories
MAX_CHUNK=512*1024**2
REPOSITORY='Maergoth/TextureQuest-Textures'

def need(ok,why):
    if not ok:raise ValueError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def dump(path,value):
    raw=fmt.canonical(value)+b'\n'
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return dict(name=Path(path).name,bytes=len(raw),sha256=sha(raw))
def pin_file(p):
    with fmt.held(p) as (f,st):return dict(name=Path(p).name,bytes=st[2],sha256=fmt.sha_file(f))
def verified(p,pin):
    raw=Path(p).read_bytes();need(len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],'Input binding changed: '+Path(p).name);return raw

def parse_index(raw):
    need(len(raw)>=24 and raw[:8] in (b'TQGX0001',b'TQGX0002'),'Index framing')
    version,count,payload=struct.unpack_from('<IIQ',raw,8)
    need((raw[:8],version) in [(b'TQGX0001',1),(b'TQGX0002',2)] and 0<count<=100000,'Index version/count')
    pos=24;rows=[];keys=set()
    for _ in range(count):
        need(pos+224<=len(raw),'Truncated row')
        values=struct.unpack_from('<II10IQQ',raw,pos);pos+=64
        a,b=values[:2];source=list(values[2:7]);target=list(values[7:12]);offset,size=values[12:]
        hashes=[raw[pos+i*32:pos+(i+1)*32].hex() for i in range(5)];pos+=160
        need(0<a<=256 and 0<b<=4096 and pos+a+b<=len(raw),'Index labels')
        owner=raw[pos:pos+a].decode('utf-8');pos+=a;member=raw[pos:pos+b].decode('utf-8');pos+=b
        need('\0' not in owner+member and member.lower().endswith('.dds'),'Invalid member')
        key=(owner.lower(),member);need(key not in keys,'Duplicate named texture');keys.add(key)
        need(offset<=payload and size<=payload-offset and size==sum(x[4] for x in fmt.mip_levels(target)),'Invalid payload range')
        rows.append(dict(owner=owner,member=member,source_layout=source,target_layout=target,source_fingerprint=hashes[0],target_fingerprint=hashes[1],payload_sha256=hashes[2],source_dds_sha256=hashes[3],target_dds_sha256=hashes[4]))
    need(pos==len(raw),'Trailing index bytes');return rows

def load_inputs(binding):
    inputs=binding['inputs'];need(len(inputs)==4,'Exact build-input roster')
    manifest=json.loads(verified(inputs[0]['path'],inputs[0]))
    cfg=verified(inputs[1]['path'],inputs[1]);index=verified(inputs[2]['path'],inputs[2]);handoff=json.loads(verified(inputs[3]['path'],inputs[3]))
    need(cfg[:8]==b'TQGXCFG2' and len(cfg)>=24,'Graphics config framing')
    ver,dual,npath,nidx=struct.unpack_from('<4I',cfg,8)
    need(ver==2 and dual==0 and len(cfg)==24+npath+nidx,'Graphics config shape')
    embedded=cfg[24+npath:];need(embedded[:8]==b'TQGX0002' and struct.unpack_from('<I',embedded,8)[0]==2 and embedded[12:]==index[12:],'Frozen graphics index differs')
    rows=parse_index(embedded)
    need(manifest['schema']=='texturequest-release-v3' and manifest['texture_version']==binding['texture_version'] and len(rows)==manifest['texture_count']==binding['named_replacements'],'Release/index count')
    folder=Path(inputs[3]['path']).parent;whitelist={}
    need(handoff['schema']=='tq-portable-released-member-catalog-v1' and handoff['status']=='COMPLETE_FROZEN','Frozen selection required')
    for pin in handoff['files']:
        p=folder/pin['path'];doc=json.loads(verified(p,pin))
        if p.name=='current-archives.json':
            frozen={a['name'].lower():{k:a[k] for k in ['bytes','sha256','entries']} for a in doc['archives']}
            expected={a['name'].lower():{k:a[k] for k in ['bytes','sha256','entries']} for a in manifest['archives']}
            need(frozen==expected,'Frozen archive domain differs')
        else:
            for row in doc['members']:
                key=(row['owner'].lower(),row['member']);need(key not in whitelist,'Duplicate frozen member');whitelist[key]=row
    need({(r['owner'].lower(),r['member']) for r in rows}==set(whitelist),'Whole selected-set identity differs')
    for row in rows:
        saved=whitelist[(row['owner'].lower(),row['member'])]
        need(saved['source_dds']['sha256']==row['source_dds_sha256'],'Stock fingerprint/source binding differs')
        target=saved['replacement_dds']['sha256'];need(target in (None,row['target_dds_sha256']),'Saved replacement hash differs')
    expected={a['name'].lower():{k:a[k] for k in ['bytes','sha256','entries','url']} for a in manifest['archives']}
    actual={a['name'].lower():{k:a[k] for k in ['bytes','sha256','entries','url']} for a in binding['archives']}
    need(expected==actual and len(binding['archives'])==len(expected),'Local archive inventory differs')
    return manifest,rows

class Chunks:
    def __init__(self,out,limit=MAX_CHUNK):self.out=out;self.limit=limit;self.z=None;self.files=[];self.objects={};self.used=0;self.number=0
    def close(self):
        if self.z is None:return
        self.z.close();self.z=None;pin=pin_file(self.path);name='dds-%03d-%s.zip'%(self.number,pin['sha256'][:12]);p=self.out/name
        need(not p.exists(),'Existing chunk preserved');os.replace(self.path,p);pin['name']=name;pin['objects']=self.part_objects;self.files.append(pin)
    def add(self,data):
        digest=sha(data)
        if digest in self.objects:
            need(self.objects[digest]['bytes']==len(data),'Object collision');return digest
        if self.z is None or self.used+len(data)>self.limit:
            self.close();self.number+=1;self.path=self.out/('chunk-%03d.partial'%self.number)
            self.z=zipfile.ZipFile(self.path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True);self.used=0;self.part_objects=0
        entry='dds/'+digest+'.dds';info=zipfile.ZipInfo(entry,(1980,1,1,0,0,0));info.external_attr=0o100644<<16
        self.z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=1)
        self.objects[digest]=dict(sha256=digest,bytes=len(data),entry=entry,part=self.number)
        self.used+=len(data);self.part_objects+=1;return digest
    def finish(self):
        self.close();need(all(p['bytes']<2*1024**3 for p in self.files),'GitHub asset size bound')
        names={i+1:p['name'] for i,p in enumerate(self.files)}
        return [dict(sha256=o['sha256'],bytes=o['bytes'],entry=o['entry'],chunk=names[o['part']]) for o in sorted(self.objects.values(),key=lambda x:x['sha256'])]

def build(binding,out,*,limit=MAX_CHUNK,fixture=None,progress=lambda _:None):
    out=Path(out);need(not out.exists(),'Output exists; preserve its partial history');out.mkdir(parents=True)
    manifest,rows=load_inputs(binding) if fixture is None else fixture
    if fixture is None:
        category_doc=json.loads(verified(binding['categories']['path'],binding['categories']))
        need(category_doc['schema']=='texturequest-named-categories-v1' and category_doc['taxonomy']==categories.taxonomy(),'Category schema/rules')
        annotations={(r['owner'].lower(),r['member']):r['category'] for r in category_doc['rows']}
        need(len(annotations)==len(category_doc['rows'])==len(rows) and set(annotations)=={(r['owner'].lower(),r['member']) for r in rows},'Exact category membership')
        for value in annotations.values():categories.validate(value)
    else:
        annotations={(r['owner'].lower(),r['member']):categories.classify(r['member']) for r in rows}
    byowner={}
    for row in rows:byowner.setdefault(row['owner'].lower(),[]).append(row)
    outcomes={}
    for row in rows:outcomes.setdefault((tuple(row['source_layout']),row['source_fingerprint']),set()).add((tuple(row['target_layout']),row['target_fingerprint']))
    chunks=Chunks(out,limit);named=[];source_archives=[]
    for number,archive in enumerate(sorted(binding['archives'],key=lambda a:a['name'].lower()),1):
        with fmt.held(archive['path']) as (stream,st):
            need(st[2]==archive['bytes'] and fmt.sha_file(stream)==archive['sha256'],'Released PAK hash changed: '+archive['name'])
            table=vpk.index(stream,st[2]);need(len(table.entries)==archive['entries'],'Released PAK entry count')
            members={e.member:e for e in table.entries};need(len(members)==len(table.entries),'Literal member aliases')
            for row in sorted(byowner.get(archive['name'].lower(),[]),key=lambda r:r['member']):
                need(row['member'] in members,'Released member missing')
                data=vpk.member_data(stream,members[row['member']]);need(sha(data)==row['target_dds_sha256'],'Selected DDS differs from tested release: '+row['member'])
                layout,pixels,tail=fmt.decode_dds(data)
                need(list(layout)==row['target_layout'] and sha(pixels)==row['payload_sha256'] and fmt.fingerprint(layout,pixels)==row['target_fingerprint'],'DDS graphics representation differs')
                object_id=chunks.add(data);key=(tuple(row['source_layout']),row['source_fingerprint'])
                named.append(dict(id=sha((row['owner'].lower()+'\0'+row['member']).encode()),owner=row['owner'],member=row['member'],object_sha256=object_id,
                    source=dict(dds_sha256=row['source_dds_sha256'],layout=row['source_layout'],fingerprint=row['source_fingerprint']),
                    target=dict(layout=row['target_layout'],fingerprint=row['target_fingerprint'],mip_bytes=len(pixels),mip_sha256=sha(pixels),tail_bytes=len(tail),tail_sha256=sha(tail)),
                    graphics_match='AMBIGUOUS_KEEP_ORIGINAL' if len(outcomes[key])>1 else 'UNAMBIGUOUS_CONTENT_MATCH',source_archive=archive['name'],
                    category=annotations[(row['owner'].lower(),row['member'])]))
        source_archives.append({k:archive[k] for k in ['name','bytes','sha256','url']})
        status=dict(archives_done=number,archives_total=len(binding['archives']),named_textures=len(named),expected_textures=len(rows),unique_dds=len(chunks.objects),stored_zip_parts=chunks.number)
        progress(status)
    objects=chunks.finish();need(len(named)==len(rows) and len({r['id'] for r in named})==len(rows),'Complete selected-set accounting')
    index=dict(schema='texturequest-dds-index-v1',texture_version=binding['texture_version'],fingerprint_schema='TQABUP01',layout_fields=['width','height','mip_count','format_family','representation'],
        format_families={'1':'BC1/DXT1','2':'BC2/DXT3','3':'BC3/DXT5','4':'BGRA8','5':'BGRX8','6':'R8','7':'QWVU_TAGGED_RGBA8'},
        taxonomy=categories.taxonomy(),category_summary=categories.summary(named),
        named_textures=sorted(named,key=lambda r:(r['owner'],r['member'])),objects=objects)
    ip=dump(out/'texture-index.json',index)
    base='https://github.com/'+REPOSITORY+'/releases/download/v'+binding['texture_version']+'/'
    for row in chunks.files:row['url']=base+row['name']
    ip['url']=base+ip['name']
    summary=dict(schema='texturequest-dds-source-v1',texture_version=binding['texture_version'],distribution_version=1,named_texture_count=len(named),unique_dds_count=len(objects),
        ambiguous_named_count=sum(r['graphics_match']=='AMBIGUOUS_KEEP_ORIGINAL' for r in named),uncompressed_dds_bytes=sum(o['bytes'] for o in objects),
        compressed_download_bytes=sum(c['bytes'] for c in chunks.files),index=ip,chunks=chunks.files,category_summary=categories.summary(named),
        provenance=dict(source_repository='Maergoth/TextureQuest',release_manifest_sha256=binding['inputs'][0]['sha256'] if fixture is None else 'fixture',
            graphics_index_sha256=binding['inputs'][2]['sha256'] if fixture is None else 'fixture',archives=source_archives),
        payload='Only exact released replacement DDS files. Original texture pixels are not included.',current_installer_uses_this_source=False,
        qualification='Prepared data source for a future graphics-only installer; not a current installer manifest or a universal runtime coverage claim.')
    dump(out/'texture-source.json',summary)
    with (out/'SHA256SUMS.txt').open('x',encoding='utf-8',newline='\n') as f:
        for p in [*chunks.files,ip,pin_file(out/'texture-source.json')]:f.write(p['sha256']+'  '+p['name']+'\n')
    return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    binding=json.loads(args.inputs.read_bytes());start=time.time()
    def progress(v):
        v['elapsed_seconds']=round(time.time()-start,1);print(json.dumps(v),flush=True)
        p=args.output.parent/'progress.json';tmp=p.with_suffix('.tmp');tmp.write_bytes(fmt.canonical(v)+b'\n');os.replace(tmp,p)
    summary=build(binding,args.output,progress=progress);print(json.dumps({k:summary[k] for k in ['named_texture_count','unique_dds_count','ambiguous_named_count','compressed_download_bytes']}),flush=True)
if __name__=='__main__':main()
