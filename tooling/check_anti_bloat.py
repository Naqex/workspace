"""Reject large changed raw JSON/CSV payloads; historical blobs stay grandfathered."""
import argparse
import json
from pathlib import Path
import subprocess

LIMIT = 1_048_576
TOTAL = 8 * LIMIT
COUNT = 100


def evaluate(records):
    raw = [r for r in records if Path(r["path"]).suffix.lower() in {".json", ".csv", ".jsonl"}]
    failures = [dict(path=r["path"], reason="raw_file_exceeds_1MiB", bytes=r["bytes"])
                for r in raw if r["bytes"] > LIMIT]
    if sum(r["bytes"] for r in raw) > TOTAL:
        failures.append(dict(reason="raw_change_exceeds_8MiB"))
    if len(raw) > COUNT:
        failures.append(dict(reason="raw_change_exceeds_100_files"))
    return dict(passed=not failures, raw_files=len(raw),
                raw_bytes=sum(r["bytes"] for r in raw), failures=failures)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="origin/main")
    a = p.parse_args()
    paths = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", a.base, "HEAD"])
    records = []
    for path in paths.decode().split("\0"):
        if path and Path(path).is_file():
            records.append(dict(path=path, bytes=Path(path).stat().st_size))
    result = evaluate(records)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
