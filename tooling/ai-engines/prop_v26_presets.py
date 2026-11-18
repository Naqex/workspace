"""Metadata-first D/E companion inventory; presets/reports remain private data."""
from collections import Counter,defaultdict
from pathlib import Path
import argparse
import hashlib
import os
import re
import subprocess
import time
import prop_v26_common as common
from prop_v26_common import *
from quant_core.job_workspace import JobWorkspace
from quant_core.native_paths import PathGuard,read_bounded,read_handle,io_path,logical_path
from quant_core.mt_report_parser import PRESETS,REPORTS,preset_bytes,report_bytes

LAB=JobWorkspace(ROOT/"batch-exact-iso-v26-20261118"/"companions",Path(__file__).resolve().parents[2])
PRUNE={".git","node_modules",".venv","venv","target","dist","build","__pycache__",
       ".next","$Recycle.Bin","System Volume Information","Windows","Recovery","$WINDOWS.~BT",
       "Microsoft SQL Server"}
CONTEXT=re.compile(r"(?:MQL[45]|MetaTrader|[\\/](?:Experts|Tester|Presets)[\\/])",re.I)
REPORT_NAME=re.compile(r"report|tester|backtest|strategytest",re.I)


def normalized_stem(path):
    return re.sub(r"[^a-z0-9]","",Path(path).stem.casefold())


def associations(paths):
    stems,folders=defaultdict(set),defaultdict(set)
    for row in paths:
        stems[normalized_stem(row["path"])].add(row["profile"])
        if row["format"] in {".mq4",".mq5",".ex4",".ex5",".pine"}:
            folders[str(Path(row["path"]).parent).casefold()].add(row["profile"])
    return stems,folders


def scan(version=1):
    inventory=unpack("inventory-and-profiles",V25)
    # A Python utility named status/config is not evidence that a distant app's
    # status.xml/config.ini belongs to a trading bot.
    candidates=[r for r in inventory["rows"] if r["format"] in {".mq4",".mq5",".ex4",".ex5",".pine"}]
    stems,folders=associations(candidates)
    version_suffix="" if version==1 else f"-v{version}"
    guard=PathGuard();records=[];metadata=[];errors=[];seen=set()
    started=time.perf_counter()
    save("inventory-registration"+version_suffix+".json",dict(source_sha256=sha(__file__),
        parser_sha256=sha("tooling/ai-engines/quant_core/mt_report_parser.py"),
        roots=["D:/","E:/"],maxdepth=24,pruned=sorted(PRUNE),no_links=True,
        protected_VI_exclusions=["projects/vi-dubber/work/pytest-p20","projects/vi-dubber/work/pytest-p20-final"],
        content_admission="associated stem/folder or MQL/MT/tester context; report-name signature probe",
        association_profile_scope="MQL/EX/Pine; generic Python/C# name matches do not admit unrelated configs",
        case_insensitive_extensions_and_pruning=True,original_profiles_not_modified=True))
    for rank,root in enumerate((Path("D:/"),Path("E:/"))):
        args=["rg","--files","--hidden","--no-ignore","--no-follow","--glob-case-insensitive",
              "--maxdepth","24",str(io_path(root))]
        for suffix in sorted(PRESETS|REPORTS):args+=["-g","*"+suffix]
        for name in sorted(PRUNE):args+=["-g","!**/"+name,"-g","!**/"+name+"/**"]
        for fixture in ("pytest-p20","pytest-p20-final"):
            args+=["-g","!**/projects/vi-dubber/work/"+fixture,
                   "-g","!**/projects/vi-dubber/work/"+fixture+"/**"]
        stderr=LAB.root/f"rg{version_suffix}-{rank}-stderr.txt"
        with stderr.open("x",encoding="utf-8") as out:
            proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=out,text=True,encoding="utf-8")
            for line in proc.stdout:
                path=logical_path(line.rstrip("\r\n"))
                if str(path).casefold() in seen:continue
                seen.add(str(path).casefold())
                suffix=path.suffix.casefold()
                named=stems.get(normalized_stem(path),set())
                folder=folders.get(str(path.parent).casefold(),set())
                identity=named or folder
                base=dict(path=str(path),format=suffix,profiles=sorted(identity),
                          association="EXACT_STEM_NAME_ONLY" if named else "COLOCATED_AMBIGUOUS" if folder else "NONE")
                try:
                    _,info=guard.admit(path)
                    if info.st_size>16*1024*1024:
                        metadata.append(dict(base,status="SIZE_LIMIT_EXCLUSION"));continue
                    admitted=bool(identity or CONTEXT.search(str(path)))
                    if not admitted and suffix in REPORTS and REPORT_NAME.search(path.name):
                        with read_handle(io_path(path)) as stream:
                            prefix=stream.read(8192)
                        text=prefix.decode("utf-16" if prefix.startswith((b"\xff\xfe",b"\xfe\xff")) else "utf-8",errors="ignore")
                        admitted=bool(re.search(r"Strategy Tester|Modelling quality|Ticks modelled|Open.?Time|<Deals",text,re.I))
                    if not admitted:
                        metadata.append(dict(base,status="NO_BOT_CONTEXT_METADATA_ONLY"));continue
                    raw=read_bounded(path,16*1024*1024,guard=guard)
                    parsed=preset_bytes(raw,suffix) if suffix in PRESETS else report_bytes(raw,suffix)
                    records.append(dict(base,parsed=parsed,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
                    metadata.append(dict(base,status="PARSED",sha256=records[-1]["sha256"]))
                except (OSError,ValueError,UnicodeError,SyntaxError) as exc:
                    errors.append(dict(base,status=type(exc).__name__))
                if len(seen)%2000==0:event("companion_inventory_progress",files=len(seen),parsed=len(records),errors=len(errors))
            code=proc.wait()
        if code not in (0,1):
            errors.append(dict(path=str(root),status="RG_TRAVERSAL_ERROR",stderr_sha256=sha(stderr)))
    compressed("companion-profiles"+version_suffix,records)
    compressed("companion-metadata"+version_suffix,dict(rows=metadata,errors=errors))
    extensions=defaultdict(list)
    for row in records:
        for profile in row["profiles"]:
            extensions[profile].append(dict(path=row["path"],sha256=row["sha256"],
                format=row["format"],association=row["association"],
                parameters=len(row["parsed"].get("parameters",[])),trades=len(row["parsed"].get("trades",[])),
                clone_ready=row["parsed"].get("clone_ready",False)))
    compressed("profile-companion-overlay"+version_suffix,dict(extensions))
    summary=dict(metadata_files=len(seen),formats=dict(Counter(Path(p).suffix.casefold() for p in seen)),
        parsed=len(records),parsed_presets=sum(r["format"] in PRESETS for r in records),
        parsed_reports=sum(r["format"] in REPORTS for r in records),
        clone_ready_reports=sum(r["parsed"].get("clone_ready",False) for r in records),
        canonical_trades=sum(len(r["parsed"].get("trades",[])) for r in records),
        linked_profiles=len(extensions),associations=dict(Counter(r["association"] for r in records)),
        metadata_statuses=dict(Counter(r["status"] for r in metadata)),
        errors=dict(Counter(r["status"] for r in errors)),seconds=time.perf_counter()-started,
        full_disk_coverage_claimed=False,credential_values_exported=False,execution_performed=False)
    save("companion-summary"+version_suffix+".json",summary)
    print(summary,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--version",type=int,choices=(1,2,3),default=1)
    args=parser.parse_args()
    with bindings(common,JOB=LAB.root,RUNTIME=LAB):
        activate_runtime()
        scan(args.version)
