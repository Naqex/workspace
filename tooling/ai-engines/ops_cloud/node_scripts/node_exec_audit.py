"""Naqex Home-VPS execution audit & shadow CSV summarizer (`OrderSend = 0`)."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import pathlib
import statistics

DEFAULT_FILES_DIR = pathlib.Path(r"C:\Naqex\mt5\MQL5\Files")


def _safe_float(val: str | None) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def summarize_exec_audit(files_dir: pathlib.Path = DEFAULT_FILES_DIR) -> dict:
    audit_files = sorted(files_dir.glob("naqex_exec_audit*.csv")) if files_dir.exists() else []
    shadow_files = sorted(files_dir.glob("naqex_*shadow*.csv")) if files_dir.exists() else []

    events_by_type: dict[str, int] = {}
    fills_by_symbol: dict[str, int] = {}
    latencies_ms: list[float] = []
    slip_pts: list[float] = []
    rejects: list[dict] = []
    total_rows = 0

    for fp in audit_files:
        try:
            with fp.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_rows += 1
                    ev = (row.get("event_type") or row.get("event") or "UNKNOWN").strip()
                    events_by_type[ev] = events_by_type.get(ev, 0) + 1
                    sym = (row.get("symbol") or "").strip()
                    lat = _safe_float(row.get("latency_ms") or row.get("lat_ms"))
                    if lat is not None and lat >= 0:
                        latencies_ms.append(lat)
                    if ev == "ORDER_FILL":
                        if sym:
                            fills_by_symbol[sym] = fills_by_symbol.get(sym, 0) + 1
                        req_px = _safe_float(row.get("req_price") or row.get("signal_price"))
                        fill_px = _safe_float(row.get("fill_price") or row.get("exec_price"))
                        if req_px and fill_px and req_px > 0 and fill_px > 0:
                            slip_pts.append(abs(fill_px - req_px) / req_px * 10000.0)
                    elif "REJECT" in ev or "UNRESOLVED" in ev or "FAIL" in ev:
                        rejects.append({"file": fp.name, "symbol": sym, "event": ev, "note": (row.get("note") or row.get("reason") or "")[:120]})
        except Exception as exc:
            rejects.append({"file": fp.name, "event": "PARSE_ERR", "note": str(exc)[:120]})

    shadow_rows = 0
    for sf in shadow_files:
        try:
            lines = [ln for ln in sf.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
            shadow_rows += max(0, len(lines) - 1)
        except Exception:
            pass

    def _pct(vals: list[float], q: float) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        idx = min(len(s) - 1, max(0, int(round((len(s) - 1) * q))))
        return round(s[idx], 3)

    return {
        "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": 0,
        "audit_files": [p.name for p in audit_files],
        "shadow_files": [p.name for p in shadow_files],
        "total_audit_rows": total_rows,
        "shadow_rows": shadow_rows,
        "events_by_type": events_by_type,
        "fills_by_symbol": fills_by_symbol,
        "latency_ms": {
            "count": len(latencies_ms),
            "median": round(statistics.median(latencies_ms), 2) if latencies_ms else None,
            "p90": _pct(latencies_ms, 0.90),
            "max": round(max(latencies_ms), 2) if latencies_ms else None,
        },
        "abs_slip_bps": {
            "count": len(slip_pts),
            "median": round(statistics.median(slip_pts), 3) if slip_pts else None,
            "p90": _pct(slip_pts, 0.90),
        },
        "rejects_tail": rejects[-10:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize MT5 execution audit and shadow CSVs on node.")
    ap.add_argument("--files-dir", type=pathlib.Path, default=DEFAULT_FILES_DIR)
    args = ap.parse_args()
    print(json.dumps(summarize_exec_audit(args.files_dir), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
