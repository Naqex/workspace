"""Sequential Live TCA & Slippage-Drift Monitor (strictly read-only, OrderSend=0, Holdout=0).

Audits live/demo execution fills (`ftmo_calibration_fills_*.csv`, optional `naqex_exec_audit*.csv`)
and continuous 5-second live Bid/Ask spread telemetry (`mt5_live_spread_log.jsonl`) against
strictly pre-2025 Development M1 (`2018-2024`, `< 2025-01-01`, `holdout_rows_analysed = 0`)
baselines.

Core diagnostics:
  1. 10,000-resample non-parametric Bootstrap 95% CI for Realized Friction Multiplier
     (`[ci_lo, median, mean, ci_hi]`) overall (equal-weight stratified + pooled) and per-symbol
     (`USDJPY`, `GBPUSD`, `EURJPY`, `US100.cash`), reusing `quant_factory/tca_reconcile.py`
     symbol alias normalization (`normalize_symbol_alias`, `point_size_for_symbol`,
     `benchmark_spread_for_symbol`).
  2. Page's One-Sided CUSUM Slippage-Regime Drift Detector (`S_t = max(0, S_{t-1} + (z_t - k))`)
     anchored strictly to pre-2025 Dev baseline slippage scale (immune to live std masking).
  3. Per-Symbol Tail-Slip Outlier Detector flagging single-fill adverse slippage spikes against
     `V101-06 SetDeviationInPoints()` limits (`30` pts FX / `150` pts indices / `80` pts XAU).
  4. Concurrent-append safe partial-line CSV/JSONL readers + strict OPSEC redaction (ZERO real
     logins, ticket/order/deal IDs, IPv4/IPv6 addresses, URLs, secrets, or bare dollar signs).

SAFETY INVARIANTS:
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0` (NEVER imports `MetaTrader5`).
  - Strictly read-only: NEVER modifies or locks `.runtime/live-overnight/*`.
  - Holdout 2025+ SEALED: `holdout_rows_analysed == 0` verified programmatically on every parquet read.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import numpy as np

QUANT_FACTORY_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = QUANT_FACTORY_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]

for _p in (AI_ENGINES_DIR, QUANT_FACTORY_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.tca_reconcile import (  # noqa: E402
    BENCHMARK_SPREAD_PTS,
    POINT_SIZES,
    benchmark_spread_for_symbol,
    normalize_symbol_alias,
    point_size_for_symbol,
)

# ---------------------------------------------------------------------------
# Fail-Closed Safety Constants
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "naqex-prop-live-tca-monitor-v1"
ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_START_UTC_TS: int = 1735689600  # 2025-01-01T00:00:00Z
EXPECTED_HOLDOUT_LOCK_SHA = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"

DEFAULT_LIVE_DIR = REPO_ROOT / ".runtime/live-overnight"
DEFAULT_SPREAD_LOG = DEFAULT_LIVE_DIR / "mt5_live_spread_log.jsonl"
DEFAULT_HOT_M1_CACHE = REPO_ROOT / ".runtime/hot-m1-cache"
DEFAULT_HOLDOUT_LOCK_JSON = REPO_ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"

CORE_SYMBOLS: tuple[str, ...] = ("USDJPY", "GBPUSD", "EURJPY", "US100.cash")
SESSION_ORDER: tuple[str, ...] = ("ASIA", "LONDON", "NY_OVERLAP", "NY_AFTERNOON")

# Map `tca_reconcile.normalize_symbol_alias` output to FTMO canonical display symbol
_CORE_DISPLAY_MAP: dict[str, str] = {
    "US100": "US100.cash",
    "US500": "US500.cash",
}

# V101-06 SetDeviationInPoints() reference limits (broker points)
DEFAULT_DEVIATION_PTS: dict[str, float] = {
    "USDJPY": 30.0,
    "GBPUSD": 30.0,
    "EURUSD": 30.0,
    "EURJPY": 30.0,
    "GBPJPY": 30.0,
    "AUDUSD": 30.0,
    "USDCAD": 30.0,
    "USDCHF": 30.0,
    "NZDUSD": 30.0,
    "XAUUSD": 80.0,
    "US100.cash": 150.0,
    "US100": 150.0,
    "US500.cash": 150.0,
    "US500": 150.0,
    "US30": 150.0,
    "GER40": 150.0,
    "UK100": 150.0,
}

# Verified pre-2025 Dev M1 (2018-2024, max_utc=2024-12-31T21:59:00Z, holdout_rows_analysed=0)
# baseline cost budgets synced 1:1 with `ftmo_demo_calibration_probe.py` & `.runtime/hot-m1-cache`.
STATIC_DEV_M1_BASELINES_PRE2025: dict[str, Any] = {
    "source": "static_verified_pre2025_dev_m1_2018_2024",
    "holdout_lock_sha256": EXPECTED_HOLDOUT_LOCK_SHA,
    "holdout_rows_analysed": 0,
    "dev_m1_max_utc": "2024-12-31T21:59:00+00:00",
    "by_symbol": {
        "USDJPY": {
            "cache_asset": "USDJPY",
            "point": 0.001,
            "dev_rows": 2607454,
            "dev_median_mid": 112.3,
            "median_spread_pts": 4.0,
            "p90_spread_pts": 9.0,
            "median_spread_bps": 0.3390,
            "p90_spread_bps": 0.6693,
            "dev_comm_rt_bps": 0.5000,
            "dev_base_slip_rt_px": 0.004,
            "dev_base_slip_rt_pts": 4.0,
            "dev_base_slip_rt_bps": 0.3562,
            "total_1x_rt_bps": 1.1952,
            "total_stress_rt_bps": 1.6404,
        },
        "GBPUSD": {
            "cache_asset": "GBPUSD",
            "point": 0.00001,
            "dev_rows": 2608982,
            "dev_median_mid": 1.28645,
            "median_spread_pts": 9.0,
            "p90_spread_pts": 15.0,
            "median_spread_bps": 0.7100,
            "p90_spread_bps": 1.1981,
            "dev_comm_rt_bps": 0.3887,
            "dev_base_slip_rt_px": 0.00004,
            "dev_base_slip_rt_pts": 4.0,
            "dev_base_slip_rt_bps": 0.3109,
            "total_1x_rt_bps": 1.4096,
            "total_stress_rt_bps": 1.7983,
        },
        "EURJPY": {
            "cache_asset": "EURJPY",
            "point": 0.001,
            "dev_rows": 2610264,
            "dev_median_mid": 130.8835,
            "median_spread_pts": 7.0,
            "p90_spread_pts": 16.0,
            "median_spread_bps": 0.5610,
            "p90_spread_bps": 1.0745,
            "dev_comm_rt_bps": 0.4290,
            "dev_base_slip_rt_px": 0.004,
            "dev_base_slip_rt_pts": 4.0,
            "dev_base_slip_rt_bps": 0.3056,
            "total_1x_rt_bps": 1.2956,
            "total_stress_rt_bps": 1.6776,
        },
        "US100.cash": {
            "cache_asset": "US100",
            "point": 0.01,
            "dev_rows": 2358750,
            "dev_median_mid": 12339.667,
            "median_spread_pts": 307.2,
            "p90_spread_pts": 347.2,
            "median_spread_bps": 2.2075,
            "p90_spread_bps": 4.0843,
            "dev_comm_rt_bps": 0.0,
            "dev_base_slip_rt_px": 2.00,
            "dev_base_slip_rt_pts": 200.0,
            "dev_base_slip_rt_bps": 1.6208,
            "total_1x_rt_bps": 3.8283,
            "total_stress_rt_bps": 5.4491,
        },
    },
}

_SYMBOL_DEV_COST_SPEC: dict[str, dict[str, float]] = {
    "USDJPY": {"comm_rt_usd_per_lot": 5.0, "base_slip_rt_px": 0.004, "stress_slip_rt_px": 0.009},
    "GBPUSD": {"comm_rt_usd_per_lot": 5.0, "base_slip_rt_px": 0.00004, "stress_slip_rt_px": 0.00009},
    "EURJPY": {"comm_rt_usd_per_lot": 5.0, "base_slip_rt_px": 0.004, "stress_slip_rt_px": 0.009},
    "US100.cash": {"comm_rt_usd_per_lot": 0.0, "base_slip_rt_px": 2.00, "stress_slip_rt_px": 4.00},
}


# ---------------------------------------------------------------------------
# Strict OPSEC Redaction (ZERO real logins, tickets, IPs, URLs, bare `$`)
# ---------------------------------------------------------------------------
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Safe IPv6 regex: requires >=3 colons or "::" so `HH:MM:SS` ISO timestamps stay intact
_IPV6_RE = re.compile(
    r"(?:\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F:]{1,20}"
    r"|::[0-9a-fA-F:]{1,20})"
)
_URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
_SECRET_KV_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|bearer)\b\s*[:=]\s*[^\s,;\"']+"
)
_ID_KV_RE = re.compile(
    r"(?i)\b(account_login|login|account|ticket|position_id|order_id|deal_id|tk|pos)\b\s*[:=]\s*#?\d{4,}"
)
# Redact 8-12 digit standalone numeric identifiers (broker logins/tickets) while avoiding ISO dates
_LONG_DIGIT_ID_RE = re.compile(r"(?<![A-Za-z0-9\-\.])\d{8,12}(?![A-Za-z0-9\-\.])")
# Also redact login embedded in filenames like `ftmo_calibration_fills_1515343318.csv`
_FILENAME_LOGIN_RE = re.compile(r"([_\-])(\d{7,12})(?=\.(?:csv|jsonl|json|log|txt)\b)", re.IGNORECASE)
_BARE_DOLLAR_RE = re.compile(r"\$")


def sanitize_text(text: str) -> str:
    """Strip any IPv4/IPv6, URL, secret, broker login/ticket ID, and bare dollar sign."""
    out = str(text)
    out = _URL_RE.sub("[REDACTED_URL]", out)
    out = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}=[REDACTED_SECRET]", out)
    out = _ID_KV_RE.sub(lambda m: f"{m.group(1)}=[REDACTED_ID]", out)
    out = _FILENAME_LOGIN_RE.sub(r"\1[REDACTED_ID]", out)
    out = _IPV4_RE.sub("[REDACTED_IPV4]", out)
    out = _IPV6_RE.sub("[REDACTED_IPV6]", out)
    out = _LONG_DIGIT_ID_RE.sub("[REDACTED_ID]", out)
    out = _BARE_DOLLAR_RE.sub("USD", out)
    return out


def sanitize_path_label(path: Path | str | None) -> str | None:
    """Return only sanitized basename (never full local path or embedded account login)."""
    if path is None:
        return None
    return sanitize_text(Path(path).name)


def sanitize_payload(obj: Any) -> Any:
    """Recursively sanitize every string inside a JSON-serializable structure."""
    if isinstance(obj, str):
        return sanitize_text(obj)
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("account_login", "login", "password", "position_id", "order_id", "deal_id", "ticket"):
                continue
            cleaned[sanitize_text(str(k))] = sanitize_payload(v)
        return cleaned
    if isinstance(obj, (list, tuple)):
        return [sanitize_payload(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Symbol Normalization & Thresholds (reusing `tca_reconcile.py`)
# ---------------------------------------------------------------------------
def normalize_tca_symbol(raw_symbol: str) -> str:
    """Normalize broker symbol aliases via `tca_reconcile.normalize_symbol_alias` to FTMO Core keys."""
    canon = normalize_symbol_alias(raw_symbol)
    if not canon:
        return ""
    return _CORE_DISPLAY_MAP.get(canon, canon)


def deviation_limit_pts_for_symbol(symbol: str) -> float:
    """Return V101-06 `SetDeviationInPoints()` threshold (broker points) for a symbol."""
    norm = normalize_tca_symbol(symbol)
    if norm in DEFAULT_DEVIATION_PTS:
        return DEFAULT_DEVIATION_PTS[norm]
    canon = normalize_symbol_alias(symbol)
    if canon in DEFAULT_DEVIATION_PTS:
        return DEFAULT_DEVIATION_PTS[canon]
    if canon.startswith("XAU"):
        return 80.0
    if canon.startswith(("US100", "US500", "US30", "GER40", "UK100")):
        return 150.0
    return 30.0


def tag_session_utc(utc_ts: int) -> str:
    """Classify UTC Unix timestamp into ASIA / LONDON / NY_OVERLAP / NY_AFTERNOON."""
    if utc_ts <= 0:
        return "UNKNOWN"
    hour = datetime.fromtimestamp(int(utc_ts), timezone.utc).hour
    if 7 <= hour < 12:
        return "LONDON"
    if 12 <= hour < 16:
        return "NY_OVERLAP"
    if 16 <= hour < 21:
        return "NY_AFTERNOON"
    return "ASIA"


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        x = float(s)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _safe_int(val: Any) -> int | None:
    x = _safe_float(val)
    if x is None:
        return None
    return int(round(x))


def _estimate_notional_usd_1lot(symbol: str, ref_mid: float, usdjpy_mid: float) -> float:
    norm = normalize_tca_symbol(symbol)
    if norm == "US100.cash":
        return max(1.0, ref_mid * 1.0)
    if norm == "USDJPY":
        return 100_000.0
    if norm == "GBPUSD":
        return 100_000.0 * ref_mid
    if norm == "EURJPY":
        # 100,000 EUR quoted in JPY -> convert to USD via USDJPY
        return (100_000.0 * ref_mid) / max(1.0, usdjpy_mid)
    return 100_000.0


# ---------------------------------------------------------------------------
# Strictly Pre-2025 Dev M1 Baseline Loader (`holdout_rows_analysed == 0`)
# ---------------------------------------------------------------------------
def load_pre2025_dev_baselines(
    *,
    hot_cache_dir: Path | None = DEFAULT_HOT_M1_CACHE,
    holdout_lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON,
    use_hot_cache: bool = True,
) -> dict[str, Any]:
    """Load strictly pre-2025 (`< 2025-01-01`, `holdout_rows_analysed=0`) Dev M1 baselines.

    When `use_hot_cache=True` and `.runtime/hot-m1-cache/manifest.json` + Holdout lock are
    present, computes exact Dev M1 spread medians from pre-2025 parquet rows and asserts
    `holdout_rows_analysed == 0` on every row. Falls back gracefully to verified static
    pre-2025 baselines for fast offline/fixture runs.
    """
    if not use_hot_cache or hot_cache_dir is None:
        return json.loads(json.dumps(STATIC_DEV_M1_BASELINES_PRE2025))

    cache_path = Path(hot_cache_dir)
    manifest_path = cache_path / "manifest.json"
    if not manifest_path.is_file() or not Path(holdout_lock_path).is_file():
        return json.loads(json.dumps(STATIC_DEV_M1_BASELINES_PRE2025))

    lock_sha = hashlib.sha256(Path(holdout_lock_path).read_bytes()).hexdigest()
    if lock_sha != EXPECTED_HOLDOUT_LOCK_SHA:
        raise RuntimeError(f"HOLDOUT_LOCK_SHA_MISMATCH: {lock_sha[:16]}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("holdout_rows", -1)) != 0 or manifest.get("holdout_lock_sha256") != lock_sha:
        raise RuntimeError("HOT_M1_CACHE_HOLDOUT_GUARD_MISMATCH")

    try:
        import pyarrow.parquet as pq
    except ImportError:
        return json.loads(json.dumps(STATIC_DEV_M1_BASELINES_PRE2025))

    holdout_rows_analysed = 0
    max_ts_seen = 0
    raw_sym_data: dict[str, dict[str, Any]] = {}

    for sym in CORE_SYMBOLS:
        static_sym = STATIC_DEV_M1_BASELINES_PRE2025["by_symbol"][sym]
        cache_asset = str(static_sym["cache_asset"])
        am = manifest.get("assets", {}).get(cache_asset)
        if not isinstance(am, dict):
            raw_sym_data[sym] = dict(static_sym)
            continue
        folder = cache_path / am["dir"]
        scale = float(am["scale"])
        pt = point_size_for_symbol(sym)

        ts_parts: list[np.ndarray] = []
        bo_parts: list[np.ndarray] = []
        ao_parts: list[np.ndarray] = []
        for year_str, ym in sorted(am.get("years", {}).items()):
            if int(year_str) >= 2025:
                raise RuntimeError(f"HOLDOUT_YEAR_DETECTED_IN_HOT_CACHE: {year_str}")
            pq_path = folder / ym["parquet"]
            if not pq_path.is_file():
                continue
            tbl = pq.read_table(pq_path, columns=["minute", "bo", "ao"])
            ts = tbl["minute"].to_numpy().astype(np.int64) * 60
            n_hold = int(np.sum(ts >= HOLDOUT_START_UTC_TS))
            if n_hold > 0:
                raise RuntimeError(f"HOLDOUT_ROWS_DETECTED: {cache_asset} {year_str} count={n_hold}")
            holdout_rows_analysed += n_hold
            if len(ts) > 0:
                max_ts_seen = max(max_ts_seen, int(ts[-1]))
            ts_parts.append(ts)
            bo_parts.append(tbl["bo"].to_numpy().astype(np.float64) / scale)
            ao_parts.append(tbl["ao"].to_numpy().astype(np.float64) / scale)

        if not ts_parts:
            raw_sym_data[sym] = dict(static_sym)
            continue

        ts_all = np.concatenate(ts_parts)
        bid_all = np.concatenate(bo_parts)
        ask_all = np.concatenate(ao_parts)
        valid = (bid_all > 0.0) & (ask_all >= bid_all)
        bid_all = bid_all[valid]
        ask_all = ask_all[valid]

        sp_px = ask_all - bid_all
        mid_px = 0.5 * (ask_all + bid_all)
        sp_pts = sp_px / pt
        sp_bps = (sp_px / mid_px) * 10_000.0
        med_mid = float(np.median(mid_px))

        raw_sym_data[sym] = {
            "cache_asset": cache_asset,
            "point": pt,
            "dev_rows": int(len(bid_all)),
            "dev_median_mid": round(med_mid, 5),
            "median_spread_pts": round(float(np.median(sp_pts)), 3),
            "p90_spread_pts": round(float(np.percentile(sp_pts, 90)), 3),
            "median_spread_bps": round(float(np.median(sp_bps)), 4),
            "p90_spread_bps": round(float(np.percentile(sp_bps, 90)), 4),
        }

    usdjpy_mid = float(raw_sym_data.get("USDJPY", {}).get("dev_median_mid", 112.3))
    by_symbol: dict[str, dict[str, Any]] = {}
    for sym, d in raw_sym_data.items():
        spec = _SYMBOL_DEV_COST_SPEC[sym]
        pt = float(d["point"])
        ref_mid = float(d["dev_median_mid"])
        notional = _estimate_notional_usd_1lot(sym, ref_mid, usdjpy_mid)
        comm_rt_bps = (spec["comm_rt_usd_per_lot"] / notional) * 10_000.0
        base_slip_rt_bps = (spec["base_slip_rt_px"] / ref_mid) * 10_000.0
        stress_slip_rt_bps = (spec["stress_slip_rt_px"] / ref_mid) * 10_000.0
        med_sp_bps = float(d["median_spread_bps"])
        total_1x = med_sp_bps + comm_rt_bps + base_slip_rt_bps
        total_stress = med_sp_bps + comm_rt_bps + stress_slip_rt_bps
        by_symbol[sym] = {
            **d,
            "dev_comm_rt_bps": round(comm_rt_bps, 4),
            "dev_base_slip_rt_px": spec["base_slip_rt_px"],
            "dev_base_slip_rt_pts": round(spec["base_slip_rt_px"] / pt, 2),
            "dev_base_slip_rt_bps": round(base_slip_rt_bps, 4),
            "total_1x_rt_bps": round(total_1x, 4),
            "total_stress_rt_bps": round(total_stress, 4),
        }

    return {
        "source": "hot_m1_cache_pre2025_verified",
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": holdout_rows_analysed,
        "dev_m1_max_utc": (
            datetime.fromtimestamp(max_ts_seen, timezone.utc).isoformat()
            if max_ts_seen > 0
            else STATIC_DEV_M1_BASELINES_PRE2025["dev_m1_max_utc"]
        ),
        "by_symbol": by_symbol,
    }


def _baseline_for_symbol(symbol: str, dev_baselines: dict[str, Any]) -> dict[str, Any]:
    """Return Dev 1.00x baseline budget for `symbol` (fallback uses `tca_reconcile` benchmarks)."""
    norm = normalize_tca_symbol(symbol)
    by_sym = dev_baselines.get("by_symbol", {})
    if norm in by_sym:
        return by_sym[norm]
    # Generic fallback for non-Core4 symbols reusing `tca_reconcile.py`
    pt = point_size_for_symbol(norm)
    bench_pts = benchmark_spread_for_symbol(norm) or 10.0
    is_idx = norm.startswith(("US100", "US500", "US30", "GER40", "UK100"))
    ref_mid = 10000.0 if is_idx else (150.0 if norm.endswith("JPY") else 1.15)
    sp_bps = ((bench_pts * pt) / ref_mid) * 10_000.0
    comm_bps = 0.0 if is_idx else 0.45
    slip_bps = 1.50 if is_idx else 0.35
    return {
        "cache_asset": normalize_symbol_alias(norm),
        "point": pt,
        "dev_rows": 0,
        "dev_median_mid": ref_mid,
        "median_spread_pts": bench_pts,
        "p90_spread_pts": round(bench_pts * 1.8, 3),
        "median_spread_bps": round(sp_bps, 4),
        "p90_spread_bps": round(sp_bps * 1.8, 4),
        "dev_comm_rt_bps": comm_bps,
        "dev_base_slip_rt_px": round((slip_bps / 10_000.0) * ref_mid, 6),
        "dev_base_slip_rt_pts": round(((slip_bps / 10_000.0) * ref_mid) / pt, 2),
        "dev_base_slip_rt_bps": slip_bps,
        "total_1x_rt_bps": round(sp_bps + comm_bps + slip_bps, 4),
        "total_stress_rt_bps": round(sp_bps + comm_bps + 2.0 * slip_bps, 4),
    }


# ---------------------------------------------------------------------------
# Concurrent-Append Safe Read-Only Loaders
# ---------------------------------------------------------------------------
def _ephemeral_pair_hash(raw_pos_id: str, trade_seq: str, symbol: str) -> str:
    """Hash raw position/trade identifiers for internal pairing ONLY (never exposes raw ticket)."""
    key = f"{symbol}|{raw_pos_id.strip()}|{trade_seq.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def load_calibration_fills_readonly(paths: Iterable[Path]) -> dict[str, Any]:
    """Read `ftmo_calibration_fills_*.csv` strictly read-only with partial-line safety."""
    fills: list[dict[str, Any]] = []
    files_read: list[str] = []
    missing_files: list[str] = []
    dryrun_ignored = 0
    rejected_orders = 0
    malformed_skipped = 0
    swap_violations = 0

    for raw_p in paths:
        p = Path(raw_p)
        if not p.is_file():
            missing_files.append(sanitize_path_label(p) or "missing.csv")
            continue
        files_read.append(sanitize_path_label(p) or "fills.csv")
        try:
            raw_text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing_files.append(sanitize_path_label(p) or "unreadable.csv")
            continue

        lines = [ln for ln in raw_text.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        reader = csv.reader(lines)
        header = [h.strip() for h in next(reader)]
        expected_cols = len(header)
        if expected_cols < 10 or "symbol" not in header:
            malformed_skipped += max(0, len(lines) - 1)
            continue

        for row_idx, raw_row in enumerate(reader, start=1):
            # Guard against mid-write truncated trailing row during live append
            if len(raw_row) != expected_cols:
                malformed_skipped += 1
                continue
            r = dict(zip(header, raw_row))
            if str(r.get("dry_run", "")).strip().lower() in ("true", "1", "yes"):
                dryrun_ignored += 1
                continue

            leg = str(r.get("leg", "")).strip().upper()
            retcode = _safe_int(r.get("retcode"))
            if leg == "ENTRY_REJECT" or (retcode is not None and retcode != 10009):
                rejected_orders += 1
                continue
            if leg not in ("ENTRY", "EXIT"):
                malformed_skipped += 1
                continue

            utc_ts = _safe_int(r.get("utc_ts"))
            pre_spread_pts = _safe_float(r.get("pre_spread_pts"))
            pre_spread_bps = _safe_float(r.get("pre_spread_bps"))
            adv_slip_pts = _safe_float(r.get("adverse_slip_pts"))
            adv_slip_bps = _safe_float(r.get("adverse_slip_bps"))
            exp_px = _safe_float(r.get("expected_price"))
            fill_px = _safe_float(r.get("fill_price"))
            if None in (utc_ts, pre_spread_bps, adv_slip_pts, adv_slip_bps, exp_px, fill_px):
                malformed_skipped += 1
                continue

            raw_sym = str(r.get("symbol", "")).strip()
            sym = normalize_tca_symbol(raw_sym)
            if not sym:
                malformed_skipped += 1
                continue

            pt = point_size_for_symbol(sym)
            if pre_spread_pts is None and exp_px and exp_px > 0:
                pre_spread_pts = ((pre_spread_bps / 10_000.0) * exp_px) / pt

            comm_bps = _safe_float(r.get("commission_bps")) or 0.0
            lat_ms = _safe_float(r.get("latency_ms")) or 0.0
            swap_usd = _safe_float(r.get("swap_usd")) or 0.0
            if abs(swap_usd) > 1e-6:
                swap_violations += 1

            sess = str(r.get("session", "")).strip().upper()
            if sess not in SESSION_ORDER:
                sess = tag_session_utc(int(utc_ts))

            raw_pos_id = str(r.get("position_id", "")).strip()
            raw_seq = str(r.get("trade_seq", "")).strip()
            pair_key = _ephemeral_pair_hash(raw_pos_id or f"seq_{raw_seq}_{row_idx}", raw_seq, sym)

            fills.append({
                "source": "calibration_fills_csv",
                "utc_ts": int(utc_ts),
                "utc_iso": datetime.fromtimestamp(int(utc_ts), timezone.utc).isoformat(),
                "session": sess,
                "symbol": sym,
                "leg": leg,
                "side": str(r.get("side", "")).strip().upper(),
                "exit_reason": str(r.get("exit_reason", "")).strip().upper(),
                "pair_key": pair_key,
                "pre_spread_pts": float(pre_spread_pts or 0.0),
                "pre_spread_bps": float(pre_spread_bps),
                "adverse_slip_pts": float(adv_slip_pts),
                "adverse_slip_bps": float(adv_slip_bps),
                "commission_bps": float(comm_bps),
                "latency_ms": float(lat_ms),
                "swap_usd": float(swap_usd),
                "has_explicit_commission": True,
            })

    return {
        "fills": fills,
        "files_read": files_read,
        "missing_files": missing_files,
        "dryrun_rows_ignored": dryrun_ignored,
        "rejected_orders": rejected_orders,
        "malformed_or_partial_rows_skipped": malformed_skipped,
        "swap_violations": swap_violations,
    }


def load_exec_audit_readonly(paths: Iterable[Path], dev_baselines: dict[str, Any]) -> dict[str, Any]:
    """Read optional `naqex_exec_audit*.csv` strictly read-only with partial-line safety."""
    fills: list[dict[str, Any]] = []
    files_read: list[str] = []
    missing_files: list[str] = []
    dryrun_ignored = 0
    rejected_orders = 0
    malformed_skipped = 0
    swap_violations = 0

    for raw_p in paths:
        p = Path(raw_p)
        if not p.is_file():
            missing_files.append(sanitize_path_label(p) or "missing_audit.csv")
            continue
        files_read.append(sanitize_path_label(p) or "naqex_exec_audit.csv")
        try:
            raw_text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing_files.append(sanitize_path_label(p) or "unreadable_audit.csv")
            continue

        lines = [ln for ln in raw_text.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        reader = csv.reader(lines)
        header = [h.strip() for h in next(reader)]
        expected_cols = len(header)
        if expected_cols < 8 or "symbol" not in header or "event_type" not in header:
            malformed_skipped += max(0, len(lines) - 1)
            continue

        for row_idx, raw_row in enumerate(reader, start=1):
            if len(raw_row) != expected_cols:
                malformed_skipped += 1
                continue
            r = dict(zip(header, raw_row))
            ev = str(r.get("event_type", "")).strip().upper()
            if ev == "DRYRUN_SIGNAL":
                dryrun_ignored += 1
                continue
            if ev == "ORDER_REJECT":
                rejected_orders += 1
                continue
            if ev not in ("ORDER_FILL", "ORDER_FILL_RECONCILED", "POSITION_CLOSE"):
                continue

            utc_ts = _safe_int(r.get("utc_ts"))
            sig_px = _safe_float(r.get("signal_price"))
            fill_px = _safe_float(r.get("fill_price"))
            spread_pts = _safe_float(r.get("spread_pts"))
            if None in (utc_ts, sig_px, fill_px, spread_pts) or sig_px <= 0.0:
                malformed_skipped += 1
                continue

            sym = normalize_tca_symbol(str(r.get("symbol", "")))
            if not sym:
                malformed_skipped += 1
                continue

            pt = point_size_for_symbol(sym)
            side = str(r.get("side", "")).strip().upper()
            side_sign = 1.0 if side == "BUY" else -1.0
            adv_px = side_sign * (fill_px - sig_px)
            adv_pts = adv_px / pt
            adv_bps = (adv_px / sig_px) * 10_000.0
            sp_bps = ((spread_pts * pt) / sig_px) * 10_000.0
            lat_ms = _safe_float(r.get("latency_ms")) or 0.0
            swap_usd = _safe_float(r.get("swap_usd")) or 0.0
            if abs(swap_usd) > 1e-6:
                swap_violations += 1

            base_sym = _baseline_for_symbol(sym, dev_baselines)
            oneway_comm_bps = 0.5 * float(base_sym["dev_comm_rt_bps"])
            leg = "EXIT" if ev == "POSITION_CLOSE" else "ENTRY"

            # Pair via hashed pos= tag inside comment when available (V101-01)
            comment = str(r.get("comment", ""))
            pos_match = re.search(r"pos=(\d+)", comment)
            pair_raw = pos_match.group(1) if pos_match else f"audit_{row_idx}_{utc_ts}"
            pair_key = _ephemeral_pair_hash(pair_raw, str(row_idx), sym)

            fills.append({
                "source": "naqex_exec_audit_csv",
                "utc_ts": int(utc_ts),
                "utc_iso": datetime.fromtimestamp(int(utc_ts), timezone.utc).isoformat(),
                "session": tag_session_utc(int(utc_ts)),
                "symbol": sym,
                "leg": leg,
                "side": side,
                "exit_reason": "AUDIT_CLOSE" if leg == "EXIT" else "",
                "pair_key": pair_key,
                "pre_spread_pts": float(spread_pts),
                "pre_spread_bps": float(sp_bps),
                "adverse_slip_pts": float(adv_pts),
                "adverse_slip_bps": float(adv_bps),
                "commission_bps": float(oneway_comm_bps),
                "latency_ms": float(lat_ms),
                "swap_usd": float(swap_usd),
                "has_explicit_commission": False,
            })

    return {
        "fills": fills,
        "files_read": files_read,
        "missing_files": missing_files,
        "dryrun_rows_ignored": dryrun_ignored,
        "rejected_orders": rejected_orders,
        "malformed_or_partial_rows_skipped": malformed_skipped,
        "swap_violations": swap_violations,
    }


def load_live_spread_log_readonly(spread_jsonl_path: Path | None) -> dict[str, Any]:
    """Read `mt5_live_spread_log.jsonl` strictly read-only, skipping truncated trailing lines."""
    by_symbol: dict[str, dict[str, dict[str, list[float]]]] = {}
    rows_parsed = 0
    partial_lines_skipped = 0
    file_present = False
    file_label = sanitize_path_label(spread_jsonl_path)

    if spread_jsonl_path is None or not Path(spread_jsonl_path).is_file():
        return {
            "file_present": False,
            "file_label": file_label,
            "rows_parsed": 0,
            "partial_lines_skipped": 0,
            "by_symbol": by_symbol,
        }

    file_present = True
    try:
        raw_text = Path(spread_jsonl_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {
            "file_present": False,
            "file_label": file_label,
            "rows_parsed": 0,
            "partial_lines_skipped": 0,
            "by_symbol": by_symbol,
        }

    for line in raw_text.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            # Concurrent append mid-write partial line: safely skip
            partial_lines_skipped += 1
            continue
        if not isinstance(row, dict):
            partial_lines_skipped += 1
            continue

        quotes = row.get("quotes")
        if not isinstance(quotes, dict):
            continue
        rows_parsed += 1
        ts_val = _safe_int(row.get("captured_utc_ts")) or 0
        sess = str(row.get("session") or "").strip().upper()
        if sess not in SESSION_ORDER:
            sess = tag_session_utc(ts_val) if ts_val > 0 else "UNKNOWN"

        for raw_sym, q in quotes.items():
            if not isinstance(q, dict) or not q.get("available"):
                continue
            bid = _safe_float(q.get("bid"))
            ask = _safe_float(q.get("ask"))
            if bid is None or ask is None or bid <= 0.0 or ask < bid:
                continue
            sym = normalize_tca_symbol(str(raw_sym))
            if not sym:
                continue
            pt = _safe_float(q.get("point")) or point_size_for_symbol(sym)
            sp_px = ask - bid
            mid = 0.5 * (ask + bid)
            sp_pts = _safe_float(q.get("spread_pts"))
            if sp_pts is None:
                sp_pts = sp_px / pt
            sp_bps = _safe_float(q.get("spread_bps"))
            if sp_bps is None:
                sp_bps = (sp_px / mid) * 10_000.0

            sym_map = by_symbol.setdefault(sym, {})
            for bucket in (sess, "OVERALL"):
                b = sym_map.setdefault(bucket, {"pts": [], "bps": []})
                b["pts"].append(float(sp_pts))
                b["bps"].append(float(sp_bps))

    return {
        "file_present": file_present,
        "file_label": file_label,
        "rows_parsed": rows_parsed,
        "partial_lines_skipped": partial_lines_skipped,
        "by_symbol": by_symbol,
    }


# ---------------------------------------------------------------------------
# Statistical Engines: 10,000-Resample Bootstrap CI, Page's CUSUM, Tail Outliers
# ---------------------------------------------------------------------------
def bootstrap_mean_ci(
    values: np.ndarray | list[float],
    *,
    n_draws: int = 10_000,
    seed: int = 20261125,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Compute deterministic non-parametric Bootstrap 95% CI `[ci_lo, median, mean, ci_hi]`."""
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = int(len(arr))
    if n == 0:
        return {
            "n": 0,
            "n_draws": int(n_draws),
            "ci_lo": None,
            "median": None,
            "mean": None,
            "ci_hi": None,
            "sample_median": None,
            "median_ci_lo": None,
            "median_ci_hi": None,
        }
    point_mean = float(np.mean(arr))
    point_median = float(np.median(arr))
    if n == 1:
        return {
            "n": 1,
            "n_draws": int(n_draws),
            "ci_lo": round(point_mean, 4),
            "median": round(point_mean, 4),
            "mean": round(point_mean, 4),
            "ci_hi": round(point_mean, 4),
            "sample_median": round(point_median, 4),
            "median_ci_lo": round(point_median, 4),
            "median_ci_hi": round(point_median, 4),
        }

    rng = np.random.default_rng(int(seed))
    draws = max(100, int(n_draws))
    idx = rng.integers(0, n, size=(draws, n))
    sampled = arr[idx]
    boot_means = sampled.mean(axis=1)
    boot_medians = np.median(sampled, axis=1)

    lo_pct = 100.0 * (alpha / 2.0)
    hi_pct = 100.0 * (1.0 - alpha / 2.0)
    ci_lo, boot_med, ci_hi = np.percentile(boot_means, [lo_pct, 50.0, hi_pct])
    m_lo, m_hi = np.percentile(boot_medians, [lo_pct, hi_pct])
    return {
        "n": n,
        "n_draws": draws,
        "ci_lo": round(float(ci_lo), 4),
        "median": round(float(boot_med), 4),
        "mean": round(point_mean, 4),
        "ci_hi": round(float(ci_hi), 4),
        "sample_median": round(point_median, 4),
        "median_ci_lo": round(float(m_lo), 4),
        "median_ci_hi": round(float(m_hi), 4),
    }


def stratified_portfolio_bootstrap_ci(
    per_symbol_values: dict[str, list[float]],
    *,
    n_draws: int = 10_000,
    seed: int = 20261125,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Equal-weight stratified 10k-resample Bootstrap 95% CI across active symbols."""
    active = {
        sym: np.asarray(vals, dtype=np.float64)
        for sym, vals in sorted(per_symbol_values.items())
        if len(vals) > 0
    }
    if not active:
        return {
            "active_symbols": 0,
            "total_observations": 0,
            "n_draws": int(n_draws),
            "ci_lo": None,
            "median": None,
            "mean": None,
            "ci_hi": None,
        }

    draws = max(100, int(n_draws))
    rng = np.random.default_rng(int(seed))
    sym_boot_means: list[np.ndarray] = []
    sym_point_means: list[float] = []
    total_obs = 0

    for sym, arr in active.items():
        n = int(len(arr))
        total_obs += n
        sym_point_means.append(float(np.mean(arr)))
        if n == 1:
            sym_boot_means.append(np.full(draws, float(arr[0]), dtype=np.float64))
        else:
            idx = rng.integers(0, n, size=(draws, n))
            sym_boot_means.append(arr[idx].mean(axis=1))

    port_boot = np.mean(np.vstack(sym_boot_means), axis=0)
    lo_pct = 100.0 * (alpha / 2.0)
    hi_pct = 100.0 * (1.0 - alpha / 2.0)
    ci_lo, boot_med, ci_hi = np.percentile(port_boot, [lo_pct, 50.0, hi_pct])
    return {
        "active_symbols": len(active),
        "total_observations": total_obs,
        "n_draws": draws,
        "ci_lo": round(float(ci_lo), 4),
        "median": round(float(boot_med), 4),
        "mean": round(float(np.mean(sym_point_means)), 4),
        "ci_hi": round(float(ci_hi), 4),
    }


def run_pages_cusum_slippage(
    standardized_z: Iterable[float],
    *,
    k_allowance: float = 0.5,
    h_threshold: float = 4.0,
) -> dict[str, Any]:
    """Page's one-sided upper CUSUM detector (`S_t = max(0, S_{t-1} + (z_t - k))`).

    Detects upward slippage regime shifts (`z_t` positive when realized adverse slippage exceeds
    pre-2025 Dev baseline). Returns peak statistic, current statistic, breach indices, and
    estimated change-point index (last zero state preceding the first breach).
    """
    z_list = [float(z) for z in standardized_z if math.isfinite(float(z))]
    n = len(z_list)
    if n == 0:
        return {
            "n_obs": 0,
            "k_allowance": float(k_allowance),
            "h_threshold": float(h_threshold),
            "current_stat": 0.0,
            "max_stat": 0.0,
            "alert": False,
            "active_breach": False,
            "first_breach_index": None,
            "estimated_changepoint_index": None,
            "breach_count": 0,
        }

    s = 0.0
    max_s = 0.0
    last_zero_idx = -1
    first_breach_idx: int | None = None
    changepoint_idx: int | None = None
    breach_count = 0

    for i, z in enumerate(z_list):
        if s == 0.0:
            last_zero_idx = i
        s = max(0.0, s + (z - float(k_allowance)))
        if s > max_s:
            max_s = s
        if s >= float(h_threshold):
            breach_count += 1
            if first_breach_idx is None:
                first_breach_idx = i
                changepoint_idx = max(0, last_zero_idx)

    return {
        "n_obs": n,
        "k_allowance": float(k_allowance),
        "h_threshold": float(h_threshold),
        "current_stat": round(s, 4),
        "max_stat": round(max_s, 4),
        "alert": first_breach_idx is not None,
        "active_breach": s >= float(h_threshold),
        "first_breach_index": first_breach_idx,
        "estimated_changepoint_index": changepoint_idx,
        "breach_count": breach_count,
    }


def _pair_roundtrips(sym_fills: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Pair ENTRY + EXIT fills by ephemeral `pair_key`; fall back to 2x scaling for unpaired legs."""
    entries_by_key: dict[str, dict[str, Any]] = {}
    paired: list[dict[str, Any]] = []
    used_entry_keys: set[str] = set()

    for f in sym_fills:
        if f["leg"] == "ENTRY" and f["pair_key"] not in entries_by_key:
            entries_by_key[f["pair_key"]] = f

    unpaired_exits: list[dict[str, Any]] = []
    for f in sym_fills:
        if f["leg"] == "EXIT":
            en = entries_by_key.get(f["pair_key"])
            if en is not None and f["pair_key"] not in used_entry_keys:
                used_entry_keys.add(f["pair_key"])
                paired.append({
                    "utc_ts": f["utc_ts"],
                    "paired": True,
                    "spread_rt_bps": 0.5 * (en["pre_spread_bps"] + f["pre_spread_bps"]),
                    "comm_rt_bps": en["commission_bps"] + f["commission_bps"],
                    "slip_rt_pos_bps": max(0.0, en["adverse_slip_bps"]) + max(0.0, f["adverse_slip_bps"]),
                    "slip_rt_signed_bps": en["adverse_slip_bps"] + f["adverse_slip_bps"],
                })
            else:
                unpaired_exits.append(f)

    unpaired_entries = [
        en for k, en in entries_by_key.items() if k not in used_entry_keys
    ]
    unpaired_legs = unpaired_entries + unpaired_exits
    # Include unpaired legs ONLY if no paired round-trips exist yet for that symbol
    # (avoids double-counting open in-flight position alongside completed round-trips)
    if not paired and unpaired_legs:
        for leg in unpaired_legs:
            paired.append({
                "utc_ts": leg["utc_ts"],
                "paired": False,
                "spread_rt_bps": leg["pre_spread_bps"],
                "comm_rt_bps": 2.0 * leg["commission_bps"],
                "slip_rt_pos_bps": 2.0 * max(0.0, leg["adverse_slip_bps"]),
                "slip_rt_signed_bps": 2.0 * leg["adverse_slip_bps"],
            })
    return paired, len(unpaired_legs)


# ---------------------------------------------------------------------------
# Main Diagnostic Orchestrator
# ---------------------------------------------------------------------------
def evaluate_live_tca(
    *,
    fills_csv_paths: Iterable[Path] = (),
    spread_jsonl_path: Path | None = None,
    audit_csv_paths: Iterable[Path] = (),
    hot_cache_dir: Path | None = DEFAULT_HOT_M1_CACHE,
    holdout_lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON,
    use_hot_cache: bool = True,
    dev_baselines: dict[str, Any] | None = None,
    n_bootstrap_draws: int = 10_000,
    seed: int = 20261125,
    cusum_k: float = 0.5,
    cusum_h: float = 4.0,
    friction_amber_threshold: float = 1.5,
    friction_red_threshold: float = 2.0,
) -> dict[str, Any]:
    """Run full strictly read-only Sequential Live TCA & Slippage-Drift evaluation."""
    assert ORDER_SEND_CAPABLE is False and ORDER_SEND_COUNT == 0

    baselines = (
        dev_baselines
        if dev_baselines is not None
        else load_pre2025_dev_baselines(
            hot_cache_dir=hot_cache_dir,
            holdout_lock_path=holdout_lock_path,
            use_hot_cache=use_hot_cache,
        )
    )
    if int(baselines.get("holdout_rows_analysed", -1)) != 0:
        raise RuntimeError("HOLDOUT_CONTAMINATION_DETECTED")

    cal_res = load_calibration_fills_readonly(fills_csv_paths)
    aud_res = load_exec_audit_readonly(audit_csv_paths, baselines)
    sp_res = load_live_spread_log_readonly(spread_jsonl_path)

    all_fills = sorted(
        [*cal_res["fills"], *aud_res["fills"]],
        key=lambda x: (x["utc_ts"], 0 if x["leg"] == "ENTRY" else 1),
    )

    total_dryrun_ignored = cal_res["dryrun_rows_ignored"] + aud_res["dryrun_rows_ignored"]
    total_rejects = cal_res["rejected_orders"] + aud_res["rejected_orders"]
    total_malformed = cal_res["malformed_or_partial_rows_skipped"] + aud_res["malformed_or_partial_rows_skipped"]
    total_swap_violations = cal_res["swap_violations"] + aud_res["swap_violations"]

    # Determine full set of symbols to report (always include Core-4 + any extra observed symbols)
    observed_syms = sorted(
        set(CORE_SYMBOLS)
        | {f["symbol"] for f in all_fills}
        | {s for s in sp_res["by_symbol"].keys() if s in CORE_SYMBOLS}
    )
    ordered_syms = list(CORE_SYMBOLS) + [s for s in observed_syms if s not in CORE_SYMBOLS]

    per_symbol_report: dict[str, dict[str, Any]] = {}
    per_sym_mult_pos: dict[str, list[float]] = {}
    per_sym_mult_signed: dict[str, list[float]] = {}
    pooled_mult_pos: list[float] = []
    pooled_mult_signed: list[float] = []
    overall_cusum_z: list[float] = []
    all_tail_outliers: list[dict[str, Any]] = []
    all_latencies: list[float] = []

    # Build chronological standardized z-scores across ALL fills for portfolio CUSUM
    for f in all_fills:
        base_s = _baseline_for_symbol(f["symbol"], baselines)
        oneway_base_bps = 0.5 * float(base_s["dev_base_slip_rt_bps"])
        sigma0_bps = max(0.15, oneway_base_bps)
        z_t = (max(0.0, float(f["adverse_slip_bps"])) - oneway_base_bps) / sigma0_bps
        overall_cusum_z.append(z_t)

    for sym_idx, sym in enumerate(ordered_syms):
        base_s = _baseline_for_symbol(sym, baselines)
        dev_1x_rt_bps = max(1e-6, float(base_s["total_1x_rt_bps"]))
        dev_med_sp_pts = float(base_s["median_spread_pts"])
        dev_med_sp_bps = float(base_s["median_spread_bps"])
        oneway_base_bps = 0.5 * float(base_s["dev_base_slip_rt_bps"])
        sigma0_bps = max(0.15, oneway_base_bps)
        dev_limit_pts = deviation_limit_pts_for_symbol(sym)

        sym_fills = [f for f in all_fills if f["symbol"] == sym]
        rt_rows, unpaired_cnt = _pair_roundtrips(sym_fills)

        # Spread-log comparison
        sp_buckets = sp_res["by_symbol"].get(sym, {})
        ov_sp = sp_buckets.get("OVERALL", {"pts": [], "bps": []})
        live_sp_samples = len(ov_sp["pts"])
        live_sp_med_pts = round(float(np.median(ov_sp["pts"])), 3) if live_sp_samples else None
        live_sp_p90_pts = round(float(np.percentile(ov_sp["pts"], 90)), 3) if live_sp_samples else None
        live_sp_med_bps = round(float(np.median(ov_sp["bps"])), 4) if live_sp_samples else None
        live_sp_p90_bps = round(float(np.percentile(ov_sp["bps"], 90)), 4) if live_sp_samples else None
        live_vs_dev_sp_ratio = (
            round(live_sp_med_bps / dev_med_sp_bps, 3)
            if (live_sp_med_bps is not None and dev_med_sp_bps > 0)
            else None
        )

        # Round-trip realized friction multipliers
        mult_pos_list: list[float] = []
        mult_signed_list: list[float] = []
        for rt in rt_rows:
            fric_pos = rt["spread_rt_bps"] + rt["comm_rt_bps"] + rt["slip_rt_pos_bps"]
            fric_signed = rt["spread_rt_bps"] + rt["comm_rt_bps"] + rt["slip_rt_signed_bps"]
            mult_pos_list.append(fric_pos / dev_1x_rt_bps)
            mult_signed_list.append(fric_signed / dev_1x_rt_bps)

        if mult_pos_list:
            per_sym_mult_pos[sym] = mult_pos_list
            per_sym_mult_signed[sym] = mult_signed_list
            pooled_mult_pos.extend(mult_pos_list)
            pooled_mult_signed.extend(mult_signed_list)

        boot_pos = bootstrap_mean_ci(mult_pos_list, n_draws=n_bootstrap_draws, seed=seed + 101 + sym_idx)
        boot_signed = bootstrap_mean_ci(mult_signed_list, n_draws=n_bootstrap_draws, seed=seed + 202 + sym_idx)

        # Continuous spread-log anchored multiplier (uses 5s median spread + realized comm + realized slip)
        spread_anchored_mult = None
        if rt_rows and live_sp_med_bps is not None:
            mean_comm = float(np.mean([r["comm_rt_bps"] for r in rt_rows]))
            mean_slip_pos = float(np.mean([r["slip_rt_pos_bps"] for r in rt_rows]))
            spread_anchored_mult = round((live_sp_med_bps + mean_comm + mean_slip_pos) / dev_1x_rt_bps, 4)

        # Per-symbol Page's CUSUM
        sym_z = [
            (max(0.0, float(f["adverse_slip_bps"])) - oneway_base_bps) / sigma0_bps
            for f in sym_fills
        ]
        sym_cusum = run_pages_cusum_slippage(sym_z, k_allowance=cusum_k, h_threshold=cusum_h)

        # Per-symbol Tail-Slip Outlier Detection vs V101-06 SetDeviationInPoints()
        sym_outliers: list[dict[str, Any]] = []
        adv_pts_arr = [float(f["adverse_slip_pts"]) for f in sym_fills]
        adv_bps_arr = [float(f["adverse_slip_bps"]) for f in sym_fills]
        lat_arr = [float(f["latency_ms"]) for f in sym_fills if f["latency_ms"] > 0.0]
        all_latencies.extend(lat_arr)

        for idx_f, f in enumerate(sym_fills):
            adv_pts = float(f["adverse_slip_pts"])
            if adv_pts > dev_limit_pts:
                ratio = adv_pts / max(1e-6, dev_limit_pts)
                sev = "CRITICAL_DEVIATION_BREACH" if ratio >= 2.0 else "WARN_DEVIATION_SPIKE"
                rec = {
                    "symbol": sym,
                    "fill_index": idx_f,
                    "utc_iso": f["utc_iso"],
                    "session": f["session"],
                    "leg": f["leg"],
                    "side": f["side"],
                    "adverse_slip_pts": round(adv_pts, 2),
                    "adverse_slip_bps": round(float(f["adverse_slip_bps"]), 4),
                    "deviation_limit_pts": dev_limit_pts,
                    "ratio_to_deviation_limit": round(ratio, 3),
                    "severity": sev,
                }
                sym_outliers.append(rec)
                all_tail_outliers.append(rec)

        max_adv_pts = round(max(adv_pts_arr), 2) if adv_pts_arr else None
        p90_adv_pts = round(float(np.percentile(adv_pts_arr, 90)), 2) if adv_pts_arr else None
        med_adv_pts = round(float(np.median(adv_pts_arr)), 2) if adv_pts_arr else None
        recommended_dev_pts = None
        if sym_outliers and max_adv_pts is not None:
            # Round recommended SetDeviationInPoints buffer up to nearest 10 pts with 1.15x headroom
            recommended_dev_pts = float(math.ceil((max_adv_pts * 1.15) / 10.0) * 10)

        sym_status = "NO_FILLS"
        if sym_fills:
            if sym_cusum["alert"]:
                sym_status = "RED_CUSUM_DRIFT"
            elif boot_pos["mean"] is not None and boot_pos["mean"] > friction_red_threshold:
                sym_status = "RED_FRICTION_BREACH"
            elif sym_outliers or (boot_pos["ci_hi"] is not None and boot_pos["ci_hi"] > friction_amber_threshold):
                sym_status = "AMBER_WATCH"
            else:
                sym_status = "GREEN"

        per_symbol_report[sym] = {
            "symbol": sym,
            "canonical_alias": normalize_symbol_alias(sym),
            "point_size": point_size_for_symbol(sym),
            "tca_benchmark_spread_pts": benchmark_spread_for_symbol(sym),
            "dev_1x_budget_rt_bps": round(dev_1x_rt_bps, 4),
            "dev_m1_median_spread_pts": dev_med_sp_pts,
            "dev_m1_median_spread_bps": dev_med_sp_bps,
            "deviation_limit_pts": dev_limit_pts,
            "fill_legs": len(sym_fills),
            "paired_roundtrips": sum(1 for r in rt_rows if r["paired"]),
            "unpaired_legs": unpaired_cnt,
            "live_spread_samples": live_sp_samples,
            "live_spread_median_pts": live_sp_med_pts,
            "live_spread_p90_pts": live_sp_p90_pts,
            "live_spread_median_bps": live_sp_med_bps,
            "live_spread_p90_bps": live_sp_p90_bps,
            "live_vs_dev_spread_ratio_bps": live_vs_dev_sp_ratio,
            "adverse_slip_pts_median": med_adv_pts,
            "adverse_slip_pts_p90": p90_adv_pts,
            "adverse_slip_pts_max": max_adv_pts,
            "adverse_slip_bps_mean": round(float(np.mean(adv_bps_arr)), 4) if adv_bps_arr else None,
            "latency_p50_ms": round(float(np.median(lat_arr)), 2) if lat_arr else None,
            "latency_p90_ms": round(float(np.percentile(lat_arr, 90)), 2) if lat_arr else None,
            "friction_multiplier_bootstrap_95ci": boot_pos,
            "friction_multiplier_signed_bootstrap_95ci": boot_signed,
            "spread_log_anchored_multiplier": spread_anchored_mult,
            "cusum": sym_cusum,
            "tail_slip_outliers": sym_outliers,
            "recommended_deviation_pts_if_breached": recommended_dev_pts,
            "status": sym_status,
        }

    # Portfolio-level Bootstrap 95% CI (Equal-Weight Stratified + Pooled) & Portfolio CUSUM
    port_boot_pos = stratified_portfolio_bootstrap_ci(
        per_sym_mult_pos, n_draws=n_bootstrap_draws, seed=seed
    )
    port_boot_signed = stratified_portfolio_bootstrap_ci(
        per_sym_mult_signed, n_draws=n_bootstrap_draws, seed=seed + 17
    )
    pooled_boot_pos = bootstrap_mean_ci(pooled_mult_pos, n_draws=n_bootstrap_draws, seed=seed + 31)
    overall_cusum = run_pages_cusum_slippage(overall_cusum_z, k_allowance=cusum_k, h_threshold=cusum_h)

    any_sym_cusum_alert = any(d["cusum"]["alert"] for d in per_symbol_report.values())
    cusum_alert_triggered = bool(overall_cusum["alert"] or any_sym_cusum_alert)

    # Verdict synthesis
    alerts: list[str] = []
    if not all_fills:
        verdict = "SPREAD_ONLY_NO_FILLS" if sp_res["rows_parsed"] > 0 else "NO_DATA"
    else:
        if cusum_alert_triggered:
            alerts.append(
                f"CUSUM_DRIFT_ALERT: Page CUSUM peak={overall_cusum['max_stat']} "
                f"(threshold={cusum_h})"
            )
        if total_swap_violations > 0:
            alerts.append(f"SWAP_VIOLATION: {total_swap_violations} fills carried non-zero swap")
        if port_boot_pos["mean"] is not None and port_boot_pos["mean"] > friction_red_threshold:
            alerts.append(
                f"FRICTION_BREACH: portfolio multiplier mean={port_boot_pos['mean']}x > {friction_red_threshold}x"
            )
        elif port_boot_pos["ci_hi"] is not None and port_boot_pos["ci_hi"] > friction_amber_threshold:
            alerts.append(
                f"FRICTION_CI_UPPER_ELEVATED: 95% CI upper={port_boot_pos['ci_hi']}x > {friction_amber_threshold}x"
            )
        if all_tail_outliers:
            worst = max(all_tail_outliers, key=lambda x: x["ratio_to_deviation_limit"])
            alerts.append(
                f"TAIL_SLIP_OUTLIER: {len(all_tail_outliers)} fill(s) exceeded SetDeviationInPoints() "
                f"(worst={worst['symbol']} +{worst['adverse_slip_pts']} pts vs limit {worst['deviation_limit_pts']} pts, "
                f"{worst['ratio_to_deviation_limit']}x)"
            )

        if cusum_alert_triggered:
            verdict = "RED_CUSUM_DRIFT_ALERT"
        elif total_swap_violations > 0 or (
            port_boot_pos["mean"] is not None and port_boot_pos["mean"] > friction_red_threshold
        ):
            verdict = "RED_FRICTION_BREACH"
        elif all_tail_outliers or (
            port_boot_pos["ci_hi"] is not None and port_boot_pos["ci_hi"] > friction_amber_threshold
        ):
            verdict = "AMBER_TAIL_SLIP_OUTLIER" if all_tail_outliers else "AMBER_FRICTION_WATCH"
        else:
            verdict = "GREEN_HEALTHY"

    payload: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "readonly": True,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": int(baselines["holdout_rows_analysed"]),
        "holdout_lock_sha256": str(baselines.get("holdout_lock_sha256", EXPECTED_HOLDOUT_LOCK_SHA)),
        "dev_m1_baseline_source": str(baselines.get("source", "unknown")),
        "dev_m1_max_utc": baselines.get("dev_m1_max_utc"),
        "verdict": verdict,
        "alerts": alerts,
        "inputs": {
            "calibration_files_read": cal_res["files_read"],
            "audit_files_read": aud_res["files_read"],
            "missing_files": [*cal_res["missing_files"], *aud_res["missing_files"]],
            "spread_log_present": sp_res["file_present"],
            "spread_log_file": sp_res["file_label"],
            "spread_log_rows_parsed": sp_res["rows_parsed"],
            "spread_log_partial_lines_skipped": sp_res["partial_lines_skipped"],
            "live_fill_legs_analysed": len(all_fills),
            "dryrun_rows_ignored": total_dryrun_ignored,
            "rejected_orders": total_rejects,
            "malformed_or_partial_rows_skipped": total_malformed,
            "swap_violations": total_swap_violations,
        },
        "portfolio": {
            "bootstrap_draws": int(n_bootstrap_draws),
            "bootstrap_seed": int(seed),
            "stratified_friction_multiplier_95ci": port_boot_pos,
            "stratified_friction_multiplier_signed_95ci": port_boot_signed,
            "pooled_friction_multiplier_95ci": pooled_boot_pos,
            "latency_p50_ms": round(float(np.median(all_latencies)), 2) if all_latencies else None,
            "latency_p90_ms": round(float(np.percentile(all_latencies, 90)), 2) if all_latencies else None,
        },
        "cusum_overall": overall_cusum,
        "tail_slip_outliers": all_tail_outliers,
        "per_symbol": per_symbol_report,
    }
    return sanitize_payload(payload)


# ---------------------------------------------------------------------------
# Plain-Vietnamese Executive Summary Renderer (ZERO bare `$`, ZERO leaks)
# ---------------------------------------------------------------------------
def _fmt_ci(ci: dict[str, Any]) -> str:
    if ci.get("mean") is None:
        return "chua co du lieu"
    return (
        f"[{ci['ci_lo']:.3f}x .. {ci['median']:.3f}x .. {ci['ci_hi']:.3f}x] "
        f"(trung binh {ci['mean']:.3f}x, n={ci.get('n', ci.get('total_observations', 0))})"
    )


def render_tca_monitor_vi(report: dict[str, Any]) -> str:
    """Render concise plain-Vietnamese diagnostic report with zero bare `$` or sensitive IDs."""
    verdict_labels = {
        "GREEN_HEALTHY": "XANH — CHI PHI KHOP LENH ON DINH",
        "AMBER_TAIL_SLIP_OUTLIER": "VANG — MA SAT TONG THAP NHUNG CO DUOI TRUOT GIA VUOT NGUONG",
        "AMBER_FRICTION_WATCH": "VANG — CAN THEO DOI BIEN TREN MA SAT",
        "RED_CUSUM_DRIFT_ALERT": "DO — CANH BAO DICH CHUYEN CHE DO TRUOT GIA (CUSUM)",
        "RED_FRICTION_BREACH": "DO — MA SAT THUC TE VUOT NGUONG AN TOAN",
        "SPREAD_ONLY_NO_FILLS": "CHO — MOI CO MAU SPREAD, CHUA CO LENH KHOP",
        "NO_DATA": "CHO — CHUA CO DU LIEU KHOP LENH HOAC SPREAD",
    }
    v_str = verdict_labels.get(report["verdict"], report["verdict"])
    inp = report["inputs"]
    port = report["portfolio"]
    cusum = report["cusum_overall"]

    lines = [
        "=== GIAM SAT CHI PHI KHOP LENH & TRUOT GIA THUC TE (READ-ONLY) ===",
        f"Trang thai tong: {v_str} ({report['verdict']})",
        (
            f"An toan: OrderSend={report['order_send_count']} | "
            f"Holdout 2025+={report['holdout_rows_analysed']} dong | "
            f"Moc Dev M1 <= {report.get('dev_m1_max_utc') or '2024-12-31'}"
        ),
        (
            f"Du lieu doc (chi doc): {inp['live_fill_legs_analysed']} chan khop lenh | "
            f"{inp['spread_log_rows_parsed']} mau spread 5s | "
            f"reject={inp['rejected_orders']} | swap!=0: {inp['swap_violations']} | "
            f"bo qua dong dang ghi do: csv={inp['malformed_or_partial_rows_skipped']}, "
            f"jsonl={inp['spread_log_partial_lines_skipped']}"
        ),
        (
            f"He so ma sat thuc te (Bootstrap {port['bootstrap_draws']} lan, KTC 95%, bao thu truot am=0): "
            f"{_fmt_ci(port['stratified_friction_multiplier_95ci'])}"
        ),
        (
            f"He so ma sat rong (co dau, tinh ca khop gia tot hon): "
            f"{_fmt_ci(port['stratified_friction_multiplier_signed_95ci'])}"
        ),
        (
            f"Page CUSUM truot gia toan danh muc: hien tai={cusum['current_stat']:.2f} / "
            f"dinh={cusum['max_stat']:.2f} (nguong canh bao={cusum['h_threshold']:.1f}) -> "
            f"{'CANH BAO DICH CHUYEN' if cusum['alert'] else 'BINH THUONG'}"
        ),
        "",
        "Chi tiet tung ma (Bootstrap 95% CI vs ngan sach Dev 1.00x):",
    ]

    for sym, d in report["per_symbol"].items():
        sp_str = (
            f"spread 5s={d['live_spread_median_pts']} pts ({d['live_vs_dev_spread_ratio_bps']}x Dev)"
            if d["live_spread_samples"] > 0
            else "chua co spread 5s"
        )
        slip_str = (
            f"truot max={d['adverse_slip_pts_max']:+.1f} pts (gioi han {d['deviation_limit_pts']:.0f} pts)"
            if d["adverse_slip_pts_max"] is not None
            else "chua co lenh"
        )
        lines.append(
            f"  - {sym}: {d['paired_roundtrips']} vong ({d['fill_legs']} chan) | "
            f"KTC 95%={_fmt_ci(d['friction_multiplier_bootstrap_95ci'])} | "
            f"{sp_str} | {slip_str} | CUSUM dinh={d['cusum']['max_stat']:.2f} [{d['status']}]"
        )

    outliers = report.get("tail_slip_outliers", [])
    if outliers:
        lines.append("")
        lines.append(f"Canh bao duoi truot gia don le vuot nguong SetDeviationInPoints ({len(outliers)} chan):")
        for o in outliers:
            rec_pts = report["per_symbol"].get(o["symbol"], {}).get("recommended_deviation_pts_if_breached")
            rec_note = f" | goi y dem deviation >= {rec_pts:.0f} pts" if rec_pts else ""
            lines.append(
                f"  ! {o['symbol']} {o['leg']} {o['side']} ({o['session']}, {o['utc_iso']}): "
                f"+{o['adverse_slip_pts']} pts ({o['adverse_slip_bps']} bps) = "
                f"{o['ratio_to_deviation_limit']}x nguong {o['deviation_limit_pts']:.0f} pts [{o['severity']}]{rec_note}"
            )

    if report.get("alerts"):
        lines.append("")
        lines.append("Tom tat co canh bao:")
        for a in report["alerts"]:
            lines.append(f"  * {a}")

    return sanitize_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Discovery Helpers & Offline Fixture Mode
# ---------------------------------------------------------------------------
def discover_live_inputs(live_dir: Path = DEFAULT_LIVE_DIR) -> dict[str, Any]:
    """Discover calibration fill CSVs, live spread JSONL, and optional exec audit CSVs."""
    d = Path(live_dir)
    fills = sorted(d.glob("ftmo_calibration_fills_*.csv")) if d.is_dir() else []
    audits = sorted(d.glob("naqex_exec_audit*.csv")) if d.is_dir() else []
    spread = d / "mt5_live_spread_log.jsonl"
    return {
        "fills_csv_paths": fills,
        "audit_csv_paths": audits,
        "spread_jsonl_path": spread if spread.is_file() else None,
    }


def build_offline_fixture_report(
    fixture_path: Path | None = None,
    *,
    n_bootstrap_draws: int = 10_000,
    seed: int = 20261125,
) -> dict[str, Any]:
    """Run deterministic offline self-test from a fixture directory/JSON or built-in clean sample."""
    if fixture_path is not None:
        fp = Path(fixture_path)
        if fp.is_dir():
            fills = sorted(fp.glob("*fills*.csv"))
            audits = sorted(fp.glob("*exec_audit*.csv"))
            spread_candidates = sorted(fp.glob("*spread*.jsonl"))
            return evaluate_live_tca(
                fills_csv_paths=fills,
                audit_csv_paths=audits,
                spread_jsonl_path=spread_candidates[0] if spread_candidates else None,
                use_hot_cache=False,
                n_bootstrap_draws=n_bootstrap_draws,
                seed=seed,
            )
        if fp.is_file() and fp.suffix.lower() == ".csv":
            return evaluate_live_tca(
                fills_csv_paths=[fp],
                use_hot_cache=False,
                n_bootstrap_draws=n_bootstrap_draws,
                seed=seed,
            )
        raise FileNotFoundError(f"Offline fixture path not found or unsupported: {sanitize_path_label(fp)}")

    # Built-in clean synthetic fixture (no disk writes, purely in-memory)
    import tempfile

    with tempfile.TemporaryDirectory(prefix="naqex_tca_fixture_") as tmp:
        td = Path(tmp)
        csv_p = td / "ftmo_calibration_fills_fixture.csv"
        header = (
            "utc_ts,utc_iso,session,account_login,server,trade_seq,position_id,order_id,deal_id,"
            "symbol,leg,side,position_side,exit_reason,volume,pre_bid,pre_ask,pre_spread_pts,"
            "pre_spread_bps,expected_price,fill_price,sl_price,adverse_slip_pts,adverse_slip_bps,"
            "latency_ms,commission_usd,commission_bps,swap_usd,pnl_usd,retcode,dry_run,comment"
        )
        rows = [
            "1795603100,2026-11-25T10:38:20+00:00,LONDON,99999999,FTMO-Demo,1,10000001,10000001,20000001,USDJPY,ENTRY,BUY,BUY,,0.01,159.200,159.204,4.0,0.2512,159.204,159.204,159.054,0.0,0.0,320.0,-0.03,0.30,0.0,0.0,10009,False,FIXTURE",
            "1795603300,2026-11-25T10:41:40+00:00,LONDON,99999999,FTMO-Demo,1,10000001,10000002,20000002,USDJPY,EXIT,SELL,BUY,TIME_EXIT,0.01,159.210,159.214,4.0,0.2512,159.210,159.209,159.054,1.0,0.0628,310.0,-0.03,0.30,0.0,0.05,10009,False,FIXTURE",
            "1795603600,2026-11-25T10:46:40+00:00,LONDON,99999999,FTMO-Demo,2,10000003,10000003,20000003,GBPUSD,ENTRY,SELL,SELL,,0.01,1.30700,1.30704,4.0,0.3060,1.30700,1.30700,1.30850,0.0,0.0,340.0,-0.03,0.23,0.0,0.0,10009,False,FIXTURE",
            "1795603800,2026-11-25T10:50:00+00:00,LONDON,99999999,FTMO-Demo,2,10000003,10000004,20000004,GBPUSD,EXIT,BUY,SELL,TIME_EXIT,0.01,1.30680,1.30684,4.0,0.3061,1.30684,1.30685,1.30850,1.0,0.0765,330.0,-0.03,0.23,0.0,0.12,10009,False,FIXTURE",
            "1795604100,2026-11-25T10:55:00+00:00,LONDON,99999999,FTMO-Demo,3,10000005,10000005,20000005,EURJPY,ENTRY,BUY,BUY,,0.01,174.300,174.308,8.0,0.4590,174.308,174.309,174.158,1.0,0.0574,350.0,-0.03,0.27,0.0,0.0,10009,False,FIXTURE",
            "1795604300,2026-11-25T10:58:20+00:00,LONDON,99999999,FTMO-Demo,3,10000005,10000006,20000006,EURJPY,EXIT,SELL,BUY,TIME_EXIT,0.01,174.320,174.328,8.0,0.4589,174.320,174.320,174.158,0.0,0.0,340.0,-0.03,0.27,0.0,0.10,10009,False,FIXTURE",
            "1795604600,2026-11-25T11:03:20+00:00,LONDON,99999999,FTMO-Demo,4,10000007,10000007,20000007,US100.cash,ENTRY,BUY,BUY,,0.01,25500.00,25501.95,195.0,0.7647,25501.95,25502.35,25451.95,40.0,0.1569,410.0,0.0,0.0,0.0,0.0,10009,False,FIXTURE",
            "1795604900,2026-11-25T11:08:20+00:00,LONDON,99999999,FTMO-Demo,4,10000007,10000008,20000008,US100.cash,EXIT,SELL,BUY,TIME_EXIT,0.01,25510.00,25511.95,195.0,0.7644,25510.00,25509.60,25451.95,40.0,0.1568,420.0,0.0,0.0,0.0,0.08,10009,False,FIXTURE",
        ]
        csv_p.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
        return evaluate_live_tca(
            fills_csv_paths=[csv_p],
            use_hot_cache=False,
            n_bootstrap_draws=n_bootstrap_draws,
            seed=seed,
        )


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Strictly read-only Sequential Live TCA & Slippage-Drift Monitor "
            "(10,000-resample Bootstrap 95% CI + Page CUSUM + Tail-Slip Outliers; OrderSend=0, Holdout=0)."
        )
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--live-readonly",
        action="store_true",
        help="Read live .runtime/live-overnight calibration fills + spread log strictly read-only.",
    )
    mode.add_argument(
        "--offline-fixture",
        nargs="?",
        const="__BUILTIN__",
        default=None,
        help="Run offline self-test on built-in clean fixture or a specified fixture directory/CSV.",
    )
    ap.add_argument("--live-dir", type=Path, default=DEFAULT_LIVE_DIR)
    ap.add_argument("--fills-csv", type=Path, action="append", default=[])
    ap.add_argument("--spread-jsonl", type=Path, default=None)
    ap.add_argument("--audit-csv", type=Path, action="append", default=[])
    ap.add_argument("--hot-cache-dir", type=Path, default=DEFAULT_HOT_M1_CACHE)
    ap.add_argument("--no-hot-cache", action="store_true", help="Use verified static pre-2025 Dev M1 baselines.")
    ap.add_argument("--bootstrap-draws", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--cusum-k", type=float, default=0.5)
    ap.add_argument("--cusum-h", type=float, default=4.0)
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit sanitized JSON instead of Vietnamese summary.")
    ap.add_argument("--strict-alerts", action="store_true", help="Exit with code 2 on AMBER tail/friction alerts too.")
    return ap


def exit_code_for_report(report: dict[str, Any], *, strict_alerts: bool = False) -> int:
    v = str(report.get("verdict", ""))
    if v.startswith("RED_"):
        return 2
    if strict_alerts and v.startswith("AMBER_"):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    if args.offline_fixture is not None:
        fixture_arg = None if args.offline_fixture == "__BUILTIN__" else Path(args.offline_fixture)
        report = build_offline_fixture_report(
            fixture_arg,
            n_bootstrap_draws=args.bootstrap_draws,
            seed=args.seed,
        )
    else:
        fills = list(args.fills_csv)
        audits = list(args.audit_csv)
        spread = args.spread_jsonl
        if args.live_readonly or (not fills and not audits and spread is None):
            disc = discover_live_inputs(args.live_dir)
            if not fills:
                fills = disc["fills_csv_paths"]
            if not audits:
                audits = disc["audit_csv_paths"]
            if spread is None:
                spread = disc["spread_jsonl_path"]
        report = evaluate_live_tca(
            fills_csv_paths=fills,
            spread_jsonl_path=spread,
            audit_csv_paths=audits,
            hot_cache_dir=args.hot_cache_dir,
            use_hot_cache=not args.no_hot_cache,
            n_bootstrap_draws=args.bootstrap_draws,
            seed=args.seed,
            cusum_k=args.cusum_k,
            cusum_h=args.cusum_h,
        )

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_tca_monitor_vi(report))
    return exit_code_for_report(report, strict_alerts=bool(args.strict_alerts))


if __name__ == "__main__":
    raise SystemExit(main())
