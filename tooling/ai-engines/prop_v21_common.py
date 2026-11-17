"""Exclusive V21 evidence; compressed outputs keep original byte identities."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
from prop_v20_common import ROOT, V19, V16, FIRST, DEV_END, END, read, sha
from prop_v18_common import V14

JOB=ROOT/"trade-forensics-behavioral-v21-20261117"
PROTOCOL=Path("planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-PROTOCOL-20261117.md")


def save(name, value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(value,f,indent=2,ensure_ascii=False,default=lambda v:v.tolist())


def compressed(name, value):
    import zstandard as zstd
    raw=json.dumps(value,ensure_ascii=False,separators=(",",":"),default=lambda v:v.tolist()).encode()
    packed=zstd.ZstdCompressor(level=9).compress(raw)
    assert zstd.ZstdDecompressor().decompress(packed)==raw
    p=JOB/(name+".json.zst")
    with p.open("xb") as f:f.write(packed)
    receipt=dict(file=p.name,original_bytes=len(raw),compressed_bytes=len(packed),
        original_sha256=hashlib.sha256(raw).hexdigest(),compressed_sha256=sha(p),roundtrip_verified=True)
    save(name+"-manifest.json",receipt)
    return receipt


def unpack(name):
    import zstandard as zstd
    p=JOB/(name+".json.zst");m=read(JOB/(name+"-manifest.json"))
    if sha(p)!=m["compressed_sha256"]:raise ValueError("V21_compressed_hash")
    raw=zstd.ZstdDecompressor().decompress(p.read_bytes())
    if hashlib.sha256(raw).hexdigest()!=m["original_sha256"]:raise ValueError("V21_original_hash")
    return json.loads(raw)


def event(stage,**values):
    row=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**values)
    with (JOB/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(row)+"\n")
    print(json.dumps(row),flush=True)
