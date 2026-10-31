"""Verify a complete downloaded DDS source without game files or native code."""
from pathlib import Path
import argparse,hashlib,json,re,sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent/'lib'))
import texture_formats as fmt
import categories

def need(ok,why):
    if not ok:raise ValueError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check_file(path,pin):
    with fmt.held(path) as (f,st):
        need(st[2]==pin['bytes'] and fmt.sha_file(f)==pin['sha256'],'File checksum: '+Path(path).name)
def verify(folder,progress=lambda _:None):
    folder=Path(folder);source=json.loads((folder/'texture-source.json').read_bytes())
    need(source['schema']=='texturequest-dds-source-v1' and source['distribution_version']==1,'Source schema')
    need(source['current_installer_uses_this_source'] is False,'Unexpected installer activation')
    index_pin=source['index'];need(index_pin['name']=='texture-index.json','Index filename')
    check_file(folder/index_pin['name'],index_pin)
    index=json.loads((folder/index_pin['name']).read_bytes())
    need(index['schema']=='texturequest-dds-index-v1' and index['texture_version']==source['texture_version'] and index['fingerprint_schema']=='TQABUP01','Index schema/version')
    objects={o['sha256']:o for o in index['objects']}
    need(len(objects)==len(index['objects'])==source['unique_dds_count'],'Object cardinality')
    rows=index['named_textures'];need(len(rows)==source['named_texture_count'] and len({r['id'] for r in rows})==len(rows),'Named cardinality')
    need(index['taxonomy']==categories.taxonomy(),'Category taxonomy')
    for row in rows:categories.validate(row['category'])
    need(index['category_summary']==source['category_summary']==categories.summary(rows),'Category accounting')
    need(source['uncompressed_dds_bytes']==sum(o['bytes'] for o in objects.values()),'DDS byte accounting')
    need(source['compressed_download_bytes']==sum(c['bytes'] for c in source['chunks']),'Download byte accounting')
    need({r['object_sha256'] for r in rows}==set(objects),'Unreferenced or missing DDS objects')
    chunks={c['name']:c for c in source['chunks']};need(len(chunks)==len(source['chunks']),'Chunk aliases')
    need({o['chunk'] for o in objects.values()}==set(chunks),'Chunk membership')
    outcomes={}
    for row in rows:
        need(row['id']==sha((row['owner'].lower()+'\0'+row['member']).encode()),'Named identity')
        key=(tuple(row['source']['layout']),row['source']['fingerprint'])
        outcomes.setdefault(key,set()).add((tuple(row['target']['layout']),row['target']['fingerprint']))
    targets={}
    for row in rows:
        key=(tuple(row['source']['layout']),row['source']['fingerprint'])
        expected='AMBIGUOUS_KEEP_ORIGINAL' if len(outcomes[key])>1 else 'UNAMBIGUOUS_CONTENT_MATCH'
        need(row['graphics_match']==expected,'Ambiguous graphics mapping must keep original')
        targets.setdefault(row['object_sha256'],[]).append(row['target'])
    need(sum(r['graphics_match']=='AMBIGUOUS_KEEP_ORIGINAL' for r in rows)==source['ambiguous_named_count'],'Ambiguous count')
    checked=0
    for number,(name,pin) in enumerate(chunks.items(),1):
        need(re.fullmatch(r'dds-\d{3}-[a-f0-9]{12}\.zip',name) is not None,'Chunk path')
        check_file(folder/name,pin)
        selected={o['entry']:o for o in objects.values() if o['chunk']==name}
        with zipfile.ZipFile(folder/name) as z:
            entries=z.infolist()
            need(len(entries)==len(selected)==pin['objects'] and {x.filename for x in entries}==set(selected),'Exact ZIP membership')
            for info in entries:
                need(re.fullmatch(r'dds/[a-f0-9]{64}\.dds',info.filename) is not None and not info.flag_bits&1 and (info.external_attr>>16)==0o100644,'ZIP path/type')
                obj=selected[info.filename]
                need(128<=info.file_size<=fmt.MAX_DDS+4096 and info.file_size==obj['bytes'],'DDS byte bound')
                raw=z.read(info)  # Also checks ZIP CRC; never writes loose files.
                need(sha(raw)==obj['sha256'] and info.filename=='dds/'+obj['sha256']+'.dds','Exact DDS bytes')
                layout,pixels,tail=fmt.decode_dds(raw)
                for target in targets[obj['sha256']]:
                    need(list(layout)==target['layout'] and fmt.fingerprint(layout,pixels)==target['fingerprint'] and len(pixels)==target['mip_bytes'] and sha(pixels)==target['mip_sha256'] and len(tail)==target['tail_bytes'] and sha(tail)==target['tail_sha256'],'DDS layout/mip/tail fingerprint')
                checked+=1
        progress(dict(chunks_done=number,chunks_total=len(chunks),objects_verified=checked))
    need(checked==len(objects),'Incomplete DDS verification')
    return dict(status='VERIFIED',named_textures=len(rows),unique_dds=checked,chunks=len(chunks),ambiguous_named=source['ambiguous_named_count'])
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);args=parser.parse_args()
    print(json.dumps(verify(args.folder,lambda p:print(json.dumps(p),flush=True))))
