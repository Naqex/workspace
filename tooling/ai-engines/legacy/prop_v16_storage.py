"""Cold-pack closed console logs only; preserve source, seals, prices and ledgers."""
from collections import Counter
from pathlib import Path
import os
import subprocess
import zipfile
from prop_v16_common import *

WORKSPACE=Path("D:/ANNAM/TradingWorkspace")
CLOSED=("h1-survivor-tick","q1-native-batch")


def run():
    files=[];errors=[]
    # Metadata census, including paths we explicitly retain rather than delete.
    for label,root in (("D",WORKSPACE),("E",ROOT)):
        for folder,dirs,names in os.walk(root,onerror=lambda e:errors.append(str(e))):
            for name in names:
                p=Path(folder)/name
                if p.suffix not in (".log",".stdout"):continue
                try:files.append(dict(root=label,path=str(p),bytes=p.stat().st_size))
                except OSError as exc:errors.append(str(exc))
    save("cold-log-inventory.json",dict(files=files,errors=errors,
        source_data_and_all_other_suffixes_protected=True))
    candidates=[r for r in files if r["root"]=="E" and
        Path(r["path"]).relative_to(ROOT).parts[0] in CLOSED and
        Path(r["path"]).name=="stdout.log" and r["bytes"]>=1000000]
    processes=json.loads(subprocess.check_output(["powershell","-NoProfile","-Command",
        "Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],text=True))
    tracked=subprocess.check_output(["git","ls-files"],text=True).splitlines()
    texts=[]
    for name in tracked:
        p=WORKSPACE/name
        if p.is_file() and p.suffix in (".py",".yml",".yaml",".ps1",".json",".toml",".md"):
            try:texts.append((name,p.read_text(encoding="utf-8-sig").replace("\\","/").lower()))
            except (OSError,UnicodeError):pass
    admitted=[];held=[]
    for r in candidates:
        p=Path(r["path"]);normalized=p.as_posix().lower()
        relative=p.relative_to(ROOT).as_posix().lower()
        pids=[v["ProcessId"] for v in processes if p.parent.as_posix().lower() in
            str(v.get("CommandLine","")).replace("\\","/").lower()]
        references=[name for name,text in texts if normalized in text or relative in text]
        code=[n for n in references if not n.startswith("planning/research/")]
        proof=dict(**r,sha256=sha(p),references=references,active_pids=pids)
        if pids or code:held.append(dict(proof,reason="ACTIVE_OR_CODE_REFERENCE"));continue
        admitted.append(proof)
    archive=JOB/"closed-console-logs.zip"
    if archive.exists():raise ValueError("preserve_compaction_attempt")
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for r in admitted:
            p=Path(r["path"]);z.write(p,p.relative_to(ROOT).as_posix())
    # Restore every member to a dedicated proof directory before removing originals.
    restored=JOB/"cold-log-restore-proof";restored.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for r in admitted:
            member=Path(r["path"]).relative_to(ROOT).as_posix()
            target=(restored/member).resolve()
            if not target.is_relative_to(restored.resolve()):raise ValueError("cold_restore_scope")
            z.extract(member,restored)
            if sha(target)!=r["sha256"]:raise ValueError("cold_restore_SHA")
    archive_sha=sha(archive);removed=[]
    for r in admitted:
        target=Path(r["path"]).resolve(strict=True)
        if not target.is_relative_to(ROOT.resolve()) or target.name!="stdout.log" or \
                target.relative_to(ROOT.resolve()).parts[0] not in CLOSED:
            raise ValueError("cold_delete_scope")
        if sha(target)!=r["sha256"]:raise ValueError("cold_input_drift")
        member=target.relative_to(ROOT.resolve()).as_posix()
        locator=target.with_name("stdout.log.v16-cold.json")
        if locator.exists():raise ValueError("preserve_hydration_locator")
        receipt=dict(original=str(target),sha256=r["sha256"],archive=str(archive),
            archive_sha256=archive_sha,member=member,restored_and_hashed=True,
            restore_instruction="Extract this one member to original path; verify SHA256 before use.")
        locator.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
        target.unlink()
        # The roundtrip copy is disposable only after its SHA proof and archive locator exist.
        proof=(restored/member).resolve(strict=True)
        if not proof.is_relative_to(restored.resolve()):raise ValueError("proof_delete_scope")
        proof.unlink()
        removed.append(dict(**r,locator=str(locator),member=member))
    logical=sum(r["bytes"] for r in removed);archive_bytes=archive.stat().st_size
    save("cold-compaction.json",dict(inventoried_log_files=len(files),
        inventoried_log_bytes=sum(r["bytes"] for r in files),
        per_root={k:dict(files=sum(r["root"]==k for r in files),
            bytes=sum(r["bytes"] for r in files if r["root"]==k)) for k in ("D","E")},
        candidates=len(candidates),removed=removed,held=held,archive=str(archive),
        archive_sha256=archive_sha,archive_bytes=archive_bytes,logical_removed_bytes=logical,
        logical_net_before_receipts=logical-archive_bytes,physical_bytes_freed=None,
        restoration_proven_for_every_member=True,source_or_ledger_removed=0,
        old_V14_V15_duplicate_purge_repeated=False))
    event("V16_cold_compaction_complete",files=len(removed),logical_bytes=logical,
        archive_bytes=archive_bytes,held=len(held))


if __name__=="__main__":run()
