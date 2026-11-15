"""Read-only V12 census, archive member inventory and bounded code duplicate proof."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
import zipfile
import tarfile
import re
from workspace_maintenance import inventory
from prop_campaign_source import ROOT

JOB = ROOT / "sl-active-ensemble-v12-20261115"
ROOTS = [Path("D:/ANNAM/TradingWorkspace"), Path("E:/BACKUP-TRADINGWORKSPACE")]
SKIP = {".git", "node_modules", ".venv", "venv", "target", "rust-target",
        "cargo-target", "api-target", "__pycache__"}
MARKET = re.compile("GBPUSD|AUDUSD|USDJPY|US500|USAIDX|SPX500", re.I)


def write(name, value):
    with (JOB / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def run():
    JOB.mkdir(exist_ok=True)
    for root, label in zip(ROOTS, ("D", "E")):
        print(dict(stage="storage_census", root=str(root)), flush=True)
        p = JOB / f"storage-{label}.json"
        if not p.exists():
            write(p.name, dict(inventory(root), observed_utc=datetime.now(timezone.utc).isoformat()))
    archives, errors, code = [], [], []
    for root in ROOTS:
        stack = [root]
        while stack:
            folder = stack.pop()
            try:
                scan = "\\\\?\\" + str(folder) if os.name == "nt" else folder
                with os.scandir(scan) as entries:
                    for e in entries:
                        p = folder / e.name
                        s = e.stat(follow_symlinks=False)
                        if e.is_symlink() or getattr(s, "st_file_attributes", 0) & 1024:
                            continue
                        if e.is_dir(follow_symlinks=False):
                            if e.name.lower() not in SKIP:
                                stack.append(p)
                            continue
                        if p.suffix.lower() in {".zip", ".7z", ".tar", ".tgz", ".gz", ".zst"}:
                            archives.append(dict(path=str(p), bytes=s.st_size))
                        if root == ROOTS[0] and p.suffix.lower() in {
                                ".py", ".rs", ".md", ".toml", ".ts", ".js"} and s.st_size <= 2_000_000:
                            code.append(p)
            except OSError as exc:
                errors.append(dict(path=str(folder), error=type(exc).__name__))
    print(dict(stage="archive_metadata", archives=len(archives)), flush=True)
    matches, inspected = [], []
    for a in archives:
        p = Path(a["path"])
        row = dict(a, status="UNSUPPORTED_METADATA_CONTAINER", members=None)
        try:
            if p.suffix.lower() == ".zip":
                with zipfile.ZipFile(p) as z:
                    info = z.infolist()
                    row.update(status="LISTED_NO_EXTRACTION", members=len(info))
                    matches.extend(dict(archive=str(p), member=r.filename,
                                        uncompressed_bytes=r.file_size, encrypted=bool(r.flag_bits & 1))
                                   for r in info if MARKET.search(str(p) + "/" + r.filename))
            elif p.suffix.lower() in {".tar", ".tgz", ".gz"} and tarfile.is_tarfile(p):
                with tarfile.open(p) as z:
                    count = 0
                    for r in z:
                        count += 1
                        if MARKET.search(str(p) + "/" + r.name):
                            matches.append(dict(archive=str(p), member=r.name, uncompressed_bytes=r.size))
                    row.update(status="LISTED_NO_EXTRACTION", members=count)
        except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
            row.update(status="METADATA_ERROR", error=type(exc).__name__)
        inspected.append(row)
    write("archive-members.json", dict(archives=inspected, matches=matches, errors=errors,
                                      price_values_decoded=False, extracted=False))
    duplicates, checked, hashed = [], 0, 0
    for source in sorted(code):
        if checked >= 2000:
            break
        rel = source.relative_to(ROOTS[0])
        for target in (ROOTS[1] / "workspace" / rel, ROOTS[1] / rel):
            try:
                if target.is_file() and target.stat().st_size == source.stat().st_size:
                    checked += 1
                    digests = []
                    for p in (source, target):
                        with p.open("rb") as stream:
                            digests.append(hashlib.file_digest(stream, "sha256").hexdigest())
                        hashed += p.stat().st_size
                    if digests[0] == digests[1]:
                        duplicates.append(dict(D=str(source), E=str(target),
                                               bytes=source.stat().st_size, sha256=digests[0]))
            except OSError as exc:
                errors.append(dict(path=str(target), error=type(exc).__name__))
    write("duplicate-files.json", dict(verified_identical_files=duplicates, checked_pairs=checked,
        bytes_hashed=hashed, pair_budget=2000, scope="code/docs <=2MB; not raw data",
        whole_directory_redundancy_proven=False, deleted=False, errors=errors))
    print(dict(stage="storage_complete", archives=len(archives), market_members=len(matches),
               identical_file_pairs=len(duplicates), deleted=False), flush=True)


if __name__ == "__main__":
    run()
