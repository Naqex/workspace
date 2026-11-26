"""Reject large changed raw JSON/CSV payloads; historical blobs stay grandfathered."""

import argparse
import json
import subprocess
from pathlib import Path

LIMIT = 1_048_576
TOTAL = 8 * LIMIT
COUNT = 100


def parse_raw_diff_paths(raw_output: bytes) -> list[str]:
    """Return paths from `git diff --raw -M100% -z --diff-filter=ACMR`, skipping exact R100 renames."""
    tokens = raw_output.decode("utf-8", errors="replace").split("\0")
    paths: list[str] = []
    i = 0
    while i < len(tokens):
        meta = tokens[i]
        i += 1
        if not meta:
            continue
        if not meta.startswith(":"):
            continue
        parts = meta[1:].split()
        if len(parts) < 5:
            continue
        old_sha, new_sha, status = parts[2], parts[3], parts[4]
        if status.startswith(("R", "C")):
            if i + 1 >= len(tokens):
                break
            _old_path, new_path = tokens[i], tokens[i + 1]
            i += 2
            # Grandfather exact byte-identical blob renames (zero new payload bytes).
            if status == "R100" and old_sha == new_sha:
                continue
            paths.append(new_path)
        else:
            if i >= len(tokens):
                break
            paths.append(tokens[i])
            i += 1
    return paths


def collect_changed_records(base: str, root: Path | None = None) -> tuple[int, list[dict]]:
    """Collect changed raw-file candidates vs `base`, grandfathering exact R100 renames."""
    repo_root = Path(root) if root is not None else Path.cwd()
    proc = subprocess.run(
        [
            "git",
            "-c",
            "diff.renameLimit=5000",
            "diff",
            "--raw",
            "-M100%",
            "-z",
            "--diff-filter=ACMR",
            base,
            "HEAD",
        ],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode, []
    records: list[dict] = []
    for rel in parse_raw_diff_paths(proc.stdout):
        if rel:
            candidate = repo_root / rel
            if candidate.is_file():
                records.append({"path": rel, "bytes": candidate.stat().st_size})
    return 0, records


def evaluate(records):
    raw = [r for r in records if Path(r["path"]).suffix.lower() in {".json", ".csv", ".jsonl"}]
    failures = [
        dict(path=r["path"], reason="raw_file_exceeds_1MiB", bytes=r["bytes"]) for r in raw if r["bytes"] > LIMIT
    ]
    if sum(r["bytes"] for r in raw) > TOTAL:
        failures.append(dict(reason="raw_change_exceeds_8MiB"))
    if len(raw) > COUNT:
        failures.append(dict(reason="raw_change_exceeds_100_files"))
    return dict(passed=not failures, raw_files=len(raw), raw_bytes=sum(r["bytes"] for r in raw), failures=failures)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="origin/main")
    a = p.parse_args()
    rc, records = collect_changed_records(a.base)
    if rc != 0:
        print(json.dumps({"passed": False, "error": f"git diff failed (rc={rc})"}, indent=2))
        return 1
    result = evaluate(records)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
