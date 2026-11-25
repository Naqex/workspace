"""Naqex Home-VPS MT5 & MQL5 UTF-16LE log filter (`OrderSend = 0`)."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import pathlib
import re

DEFAULT_MT5_ROOT = pathlib.Path(r"C:\Naqex\mt5")
ERR_RE = re.compile(r"WARN|ERR|CRITICAL|FAIL|REJECT|ORPHAN|DISCONNECT|KILL", re.IGNORECASE)


def decode_log(path: pathlib.Path) -> list[str]:
    raw = path.read_bytes()
    txt = raw.decode("utf-16-le", errors="ignore") if b"\x00" in raw[:200] else raw.decode("utf-8", errors="ignore")
    return txt.splitlines()


def query_logs(
    mt5_root: pathlib.Path = DEFAULT_MT5_ROOT,
    *,
    scope: str = "mql5",
    days: int = 1,
    grep: str = "",
    errors_only: bool = False,
    tail: int = 40,
) -> dict:
    log_dir = mt5_root / ("MQL5/Logs" if scope == "mql5" else "Logs")
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y%m%d") for i in range(max(1, days))]
    pat = re.compile(grep, re.IGNORECASE) if grep else None
    matched: list[dict] = []
    files_read: list[str] = []

    for d in reversed(dates):
        p = log_dir / f"{d}.log"
        if not p.exists():
            continue
        files_read.append(p.name)
        for ln in decode_log(p):
            if errors_only and not ERR_RE.search(ln):
                continue
            if pat and not pat.search(ln):
                continue
            parts = ln.split("\t")
            if len(parts) >= 5:
                matched.append({"date": d, "time": parts[2], "source": parts[3], "msg": parts[4][:240]})
            elif ln.strip():
                matched.append({"date": d, "time": "", "source": "", "msg": ln.strip()[:240]})

    return {
        "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": 0,
        "scope": scope,
        "files_read": files_read,
        "total_matches": len(matched),
        "lines": matched[-max(1, tail) :],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only MT5/MQL5 log query returning compact JSON.")
    ap.add_argument("--mt5-root", type=pathlib.Path, default=DEFAULT_MT5_ROOT)
    ap.add_argument("--scope", choices=("mql5", "terminal"), default="mql5")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--grep", default="")
    ap.add_argument("--errors-only", action="store_true")
    ap.add_argument("--tail", type=int, default=40)
    args = ap.parse_args()
    print(json.dumps(query_logs(args.mt5_root, scope=args.scope, days=args.days, grep=args.grep, errors_only=args.errors_only, tail=args.tail), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
