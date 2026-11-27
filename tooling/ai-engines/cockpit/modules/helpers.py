"""Shared read-only file parsers, numeric coercions, sanitizers, and time helpers."""

from __future__ import annotations

import csv
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cockpit.modules.state import _IPV4_OR_URL_RE, _NTP_OFFSET_RE, VN_TZ


def as_dict(val: Any) -> dict[str, Any]:
    """Return `val` when it is a dict, otherwise an empty dict."""
    return val if isinstance(val, dict) else {}


def as_list(val: Any) -> list[Any]:
    """Return `val` when it is a list, otherwise an empty list."""
    return val if isinstance(val, list) else []


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl_tail(path: Path, limit: int = 25) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for ln in lines[-limit:]:
            s = ln.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    rows.append(obj)
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _parse_pod_snapshot_md(path: Path) -> dict[str, Any]:
    """Parse structured KPIs & sleeve table from `.runtime/pod_dashboard_snapshot.md`."""
    if not path.is_file():
        return {"available": False, "path": str(path)}
    txt = path.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, str] = {}
    for key, pat in (
        ("generated_utc", r"\*\*Generated UTC:\*\*\s*`([^`]+)`"),
        ("active_policy", r"\*\*Active Allocation Policy:\*\*\s*`([^`]+)`"),
        ("mt5_heartbeat", r"\*\*MT5 Heartbeat:\*\*\s*`([^`]+)`"),
        ("next_red_news", r"\*\*Next Red-News:\*\*\s*`([^`]+)`"),
    ):
        m = re.search(pat, txt)
        if m:
            meta[key] = m.group(1)

    sleeves: list[dict[str, str]] = []
    in_sec1 = False
    for ln in txt.splitlines():
        if ln.startswith("## 1."):
            in_sec1 = True
            continue
        if in_sec1 and ln.startswith("## "):
            break
        if in_sec1 and ln.startswith("| S"):
            parts = [p.strip() for p in ln.strip("|").split("|")]
            if len(parts) >= 12:
                sleeves.append({
                    "sleeve": parts[0],
                    "strategy": parts[1],
                    "cagr": parts[2],
                    "vol": parts[3],
                    "sharpe": parts[4],
                    "max_dd": parts[5],
                    "cap_wt": parts[6],
                    "risk_wt": parts[7],
                    "traffic_light": parts[8],
                    "cusum_sigma": parts[9],
                    "sprt_state": parts[10],
                    "cone_pct": parts[11],
                })
    return {
        "available": True,
        "meta": meta,
        "sleeves": sleeves,
        "raw_chars": len(txt),
    }


def _format_countdown_vi(delta_sec: float) -> str:
    if abs(delta_sec) <= 300.0:
        return "CẤM ±5m"
    if delta_sec < 0:
        return f"Đã qua {int(abs(delta_sec) // 60)}m"
    mins = int(delta_sec // 60)
    if mins < 60:
        return f"+{mins}m"
    hrs, rem_m = divmod(mins, 60)
    if hrs < 24:
        return f"+{hrs}h {rem_m:02d}m" if rem_m else f"+{hrs}h"
    days, rem_h = divmod(hrs, 24)
    return f"+{days}d {rem_h}h"


def _load_upcoming_red_news(root: Path, limit: int = 10) -> list[dict[str, Any]]:
    csv_path = root / "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv"
    if not csv_path.is_file():
        return []
    now_ts = datetime.now(UTC).timestamp()
    upcoming: list[dict[str, Any]] = []
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                ts = float(r.get("utc_ts") or 0.0)
                if ts >= now_ts - 3600.0:
                    dt_utc = datetime.fromtimestamp(ts, UTC)
                    dt_vn = dt_utc.astimezone(VN_TZ)
                    delta_s = ts - now_ts
                    upcoming.append({
                        "utc_ts": int(ts),
                        "utc_iso": dt_utc.strftime("%Y-%m-%d %H:%M UTC"),
                        "vn_iso": dt_vn.strftime("%d/%m %H:%M ICT"),
                        "hours_away": round(delta_s / 3600.0, 1),
                        "countdown_vi": _format_countdown_vi(delta_s),
                        "in_blackout_window": abs(delta_s) <= 300.0,
                        "ccy": str(r.get("ccy", "")).strip(),
                        "event": str(r.get("event", "")).strip(),
                    })
    except Exception:
        return []
    upcoming.sort(key=lambda x: x["utc_ts"])
    return upcoming[:limit]


def _pip_size_for_symbol(symbol: str) -> float:
    s = str(symbol or "").upper()
    if "JPY" in s:
        return 0.01
    index_tokens = (
        "US100",
        "NAS100",
        "NDX",
        "USTEC",
        "US500",
        "SPX",
        "US30",
        "GER40",
        "DE40",
        "DAX",
        "UK100",
        "FTSE",
        "XAU",
        "GOLD",
        "BTC",
    )
    if any(tok in s for tok in index_tokens):
        return 1.0
    return 0.0001


def _downsample_series(
    dates: list[str],
    values_map: dict[str, list[float]],
    max_points: int = 260,
) -> tuple[list[str], dict[str, list[float]]]:
    n = len(dates)
    if n <= max_points:
        return dates, {k: [round(v, 4) for v in arr] for k, arr in values_map.items()}
    step = max(1, n // max_points)
    idxs = list(range(0, n, step))
    if idxs[-1] != n - 1:
        idxs.append(n - 1)
    ds_dates = [dates[i] for i in idxs]
    ds_vals = {k: [round(arr[i], 4) for i in idxs] for k, arr in values_map.items()}
    return ds_dates, ds_vals


def _parse_float_token(tok: str) -> float | None:
    m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", tok or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _coerce_opt_float(val: Any, ndigits: int = 2) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        f = float(val)
        if not math.isfinite(f):
            return None
        return round(f, ndigits)
    except (TypeError, ValueError):
        return None


def _coerce_opt_int(val: Any) -> int | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _coerce_opt_bool(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(int(val))
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on", "enabled"):
        return True
    if s in ("0", "false", "no", "off", "disabled"):
        return False
    return None


def _sanitize_short_token(val: Any, default: str = "UNKNOWN", max_len: int = 48) -> str:
    if val is None:
        return default
    s = _IPV4_OR_URL_RE.sub("[REDACTED]", str(val)).strip()
    s = re.sub(r"[\r\n\t]+", " ", s)[:max_len].strip()
    return s or default


def _sanitize_ntp_offset(val: Any) -> str | None:
    if val is None:
        return None
    m = _NTP_OFFSET_RE.search(str(val))
    if m:
        return m.group(0)
    return "unknown"


def _sanitize_heroku_status(raw_last: Any, raw_text: Any = None) -> str:
    if isinstance(raw_last, dict):
        if raw_last.get("ok") is True:
            return "OK"
        resp = raw_last.get("response")
        if isinstance(resp, dict) and resp.get("ok") is True:
            return "OK"
        st = str(raw_last.get("status") or "").strip().upper()
        if st in ("OK", "HEALTHY", "WARN", "ALERT", "STALE", "ERROR", "DEGRADED"):
            return "OK" if st == "HEALTHY" else st
        if raw_last.get("ok") is False or raw_last.get("error"):
            return "ERROR"
        return "UNKNOWN"
    if isinstance(raw_text, str) and raw_text.strip():
        low = raw_text.lower()
        if any(tok in low for tok in ("error", "fail", "exception", "timeout")):
            return "ERROR"
        if '"ok": true' in low or '"ok":true' in low or "status_code=200" in low or "200 ok" in low:
            return "OK"
        return "UNKNOWN"
    return "UNKNOWN"


def _extract_first_float(d: dict[str, Any], keys: tuple[str, ...], ndigits: int = 2) -> float | None:
    for k in keys:
        if k in d:
            v = _coerce_opt_float(d.get(k), ndigits)
            if v is not None:
                return v
    return None


def _extract_first_int(d: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for k in keys:
        if k in d:
            v = _coerce_opt_int(d.get(k))
            if v is not None:
                return v
    return None
