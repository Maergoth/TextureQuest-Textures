"""Annotate a metadata inventory without editing it or importing processing code."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import categories

def project(doc,source_sha256):
    rows=[];seen=set()
    for r in doc["rows"]:
        key=(r["owner"].lower(),r["member"])
        if key in seen:raise ValueError("Duplicate owner/member identity")
        seen.add(key)
        rows.append(dict(id=r.get("id"),owner=r["owner"],member=r["member"],
            category=categories.classify(r["member"],role=r.get("role"),
                role_present="role" in r,material=r.get("material"),
                scope="inventory_snapshot",route=r.get("processing_route"),
                format_name=r.get("format"))))
    return dict(schema="texturequest-inventory-category-sidecar-v1",
        input_sha256=source_sha256,rows=rows,taxonomy=categories.taxonomy(),
        summary=categories.summary(rows))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--inventory",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    raw=args.inventory.read_bytes();result=project(json.loads(raw),hashlib.sha256(raw).hexdigest())
    result["observed_utc"]=datetime.now(timezone.utc).isoformat()
    with args.output.open("x",encoding="utf-8",newline="\n") as f:json.dump(result,f,ensure_ascii=False,sort_keys=True,separators=(",",":"));f.write("\n")
    print(json.dumps(result["summary"]))
if __name__=="__main__":main()
