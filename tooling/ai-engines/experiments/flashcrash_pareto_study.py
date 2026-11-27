"""Flash-Crash Defense Pareto Study (Shield A / B / C) on Sealed Dev 2018-2024 Tapes.

STRICT SAFETY & X13 COMPATIBILITY INVARIANTS:
  - Pure stdlib + NumPy + optional Numba + optional PyArrow (Python 3.12 & 3.14 compatible).
  - ZERO imports of `prop_engine`, `data_store`, `assert_holdout_locked`, `duckdb`, or `scipy`.
  - Loads directly from `.runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.{json,npz}`,
    verifying `npz_sha256` AND enforcing `max_day < "2025-01-01"` and `stamps[-1] < 1735689600`.
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `holdout_rows_analysed = 0`.
  - Supports deterministic MC sharding via `--shard-index`, `--shard-total`, `--out-json`
    so Wave 2A can dispatch heavy Monte Carlo shards to `<X13_WORKER>` with clean job IDs.

Evaluates Baseline `C10_NEWS_ON` (unclamped SYMCAP flash-crash shock 7.19%-16.88%) against:
  - Shield A: Total simultaneous open-account risk cap swept across 2.00% / 2.50% / 3.00%.
  - Shield B: Directional cluster caps (USD / JPY / US100 matching `Naqex_PropGuard.mqh`) +
              real M1 Bid/Ask SpreadGuard calibrated causally from `.runtime/hot-m1-cache/` +
              official 6-CCY 523-event red-news calendar (`±5m` vs `±10m`, BoJ `±60m`).
  - Shield C: Combined A + B targeting honest simultaneous 1.25x gap shock <= 4.50% across
              ALL 4 profiles (`Funded`, `P2`, `P1 Bal`, `P1 Spr`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeGuard

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback for stripped runtimes

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
HOLDOUT_STOP_TS: int = 1735689600  # 2025-01-01T00:00:00Z
TRADING_DAYS_PER_YEAR: int = 252
TRADING_DAYS_PER_MONTH: int = 21
CALENDAR_DAYS_PER_TRADING_DAY: float = 365.2425 / 252.0
BLOCK_LEN: int = 5
DEFAULT_SEED: int = 20261126

ROOT: Path = Path(__file__).resolve().parents[3]
DEFAULT_DERIVED_DIR: Path = ROOT / ".runtime/hot-m1-cache/_derived"
DEFAULT_M1_CACHE_DIR: Path = ROOT / ".runtime/hot-m1-cache"
DEFAULT_RISK_PROFILES_PATH: Path = ROOT / "tooling/ai-engines/configs/ssot/risk_profiles.json"
DEFAULT_FX_RATES_PATH: Path = ROOT / "tooling/ai-engines/configs/ssot/fx_rates.json"
DEFAULT_FIRMS_CATALOG_PATH: Path = ROOT / "tooling/ai-engines/configs/ssot/firms_catalog.json"
DEFAULT_CAL_224_PATH: Path = ROOT / "tooling/ai-engines/configs/calendars/red_news_official_2018_2024.json"
DEFAULT_CAL_523_PATH: Path = ROOT / "tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json"

CORE7_IDS: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)

CORE7_BASE_RISK_FRAC: dict[str, float] = {
    "E1_USDJPY_TOKYO": 0.001606,
    "E2_USDJPY_EXP80": 0.005894,
    "E3_GBPUSD_VH": 0.0075,
    "E4_US100_SESS40": 0.0050,
    "E5_US100_RS1130": 0.0050,
    "E6_EURJPY_VOLCOMP": 0.0050,
    "E7_USDJPY_NY10ET": 0.0050,
}

TURBO9_EXTRA_RISK_FRAC: dict[str, float] = {
    "S6_FX_USD_BSK": 0.0050,
    "S7_XAU_EXP120": 0.0050,
}

ENGINE_ASSET_MAP: dict[str, str] = {
    "E1_USDJPY_TOKYO": "USDJPY",
    "E2_USDJPY_EXP80": "USDJPY",
    "E3_GBPUSD_VH": "GBPUSD",
    "E4_US100_SESS40": "US100",
    "E5_US100_RS1130": "US100",
    "E6_EURJPY_VOLCOMP": "EURJPY",
    "E7_USDJPY_NY10ET": "USDJPY",
    "S6_FX_USD_BSK": "EURUSD",
    "S7_XAU_EXP120": "XAUUSD",
}

# M1 parquet scale -> FTMO broker point divisor:
# USDJPY (scale=1000, pt=0.001 -> 1.0), GBPUSD (scale=100000, pt=1e-5 -> 1.0),
# EURJPY (scale=1000, pt=0.001 -> 1.0), US100 (scale=1000, pt=0.01 -> 0.1).
M1_SPREAD_SPECS: dict[str, tuple[str, float]] = {
    "USDJPY": ("usdjpy", 1.0),
    "GBPUSD": ("gbpusd", 1.0),
    "EURJPY": ("eurjpy", 1.0),
    "US100": ("us100", 0.1),
}

# Strict Cluster-A causal calibration cutoff (2018-2020 ONLY; zero 2021-2024 leakage)
CLUSTER_A_CUTOFF_DAY = "2021-01-01"
CLUSTER_A_MAX_YEAR = 2020
SPREAD_GUARD_CALIBRATION_RULE = "ceil_to_5(max(session_A_p99_9, 1.10 * entry_A_p99_9))"
FORBIDDEN_X13_TOKENS: tuple[str, ...] = ("2025", "2026", "holdout")

# Static non-calibrated presets only; `"CALIB_M1_A"` is NEVER hardcoded and is always derived
# programmatically from Cluster-A (2018-2020) M1 Bid/Ask spreads via `calibrate_m1_spread_guard()`.
SPREAD_GUARD_PRESETS_DEV_PTS: dict[str, dict[str, float]] = {
    "OFF": {"USDJPY": 1e9, "GBPUSD": 1e9, "EURJPY": 1e9, "US100": 1e9},
    "V101_DEFAULT": {"USDJPY": 35.0, "GBPUSD": 35.0, "EURJPY": 45.0, "US100": 450.0},
}


def derive_causal_cluster_a_spread_cap(
    sess_a_spreads: np.ndarray | list[float],
    entry_a_spreads: np.ndarray | list[float],
    *,
    min_floor_pts: float = 5.0,
) -> float:
    """Derive a single symbol's M1 SpreadGuard cap strictly from Cluster-A (2018-2020) data.

    Uniform causal rule across ALL symbols (zero Cluster-B / full-sample inputs):
        `ceil_to_5(max(session_A_p99_9, 1.10 * entry_A_p99_9))`
    """
    sa = np.asarray(sess_a_spreads, dtype=np.float64)
    ea = np.asarray(entry_a_spreads, dtype=np.float64)
    sess_p999 = float(np.percentile(sa, 99.9)) if len(sa) > 0 else 0.0
    ent_p999 = float(np.percentile(ea, 99.9)) if len(ea) > 0 else 0.0
    raw = max(sess_p999, 1.10 * ent_p999)
    return float(max(min_floor_pts, math.ceil(raw / 5.0) * 5.0))


def _assert_no_forbidden_x13_tokens(label: str, text: str) -> None:
    low = text.lower()
    for tok in FORBIDDEN_X13_TOKENS:
        if tok in low:
            raise ValueError(f"FORBIDDEN_HOLDOUT_TOKEN in {label}: found '{tok}' in '{text}'")


# Named historical crisis windows in sealed Dev 2018-2024
CRISIS_WINDOWS: tuple[tuple[str, str, str], ...] = (
    ("2018_Q4_Fed_QT", "2018-10-01", "2018-12-31"),
    ("2020_COVID_Crash", "2020-02-20", "2020-04-30"),
    ("2022_RateHike_Shock", "2022-01-01", "2022-10-31"),
    ("2023_SVB_Bank_Stress", "2023-03-08", "2023-03-31"),
    ("2024_Aug_Yen_Unwind", "2024-07-15", "2024-08-31"),
)

# Baseline C10_NEWS_ON phase profile (aligned with configs/ssot/risk_profiles.json)
C10_PHASE_BASE: dict[str, Any] = {
    "p1_mult": 4.00,
    "p1_lock_trigger": 0.70,
    "p1_lock_mult": 2.50,
    "p2_mult": 3.50,
    "p2_lock_trigger": 0.70,
    "p2_lock_mult": 1.75,
    "funded_mult": 1.25,
    "amber_dd": 0.035,
    "amber_mult": 0.65,
    "red_dd": 0.060,
    "red_mult": 0.40,
    "p1_symcap_pct": 1.75,
    "p2_symcap_pct": 1.75,
    "funded_symcap_pct": 1.25,
    "p1_ea_daily_stop": 0.035,
    "p2_ea_daily_stop": 0.030,
    "funded_ea_daily_stop": 0.025,
}


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def assert_pre_holdout_days(days: list[str] | tuple[str, ...]) -> int:
    """Fail-closed if ANY date string is `>= 2025-01-01`; returns `holdout_rows_analysed = 0`."""
    for d in days:
        ds = str(d)
        if ds >= HOLDOUT_CUTOFF_DAY or int(ds[:4]) > 2024:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: forbidden date >= {HOLDOUT_CUTOFF_DAY}: {ds}")
    return 0


def load_frozen_tapes_direct(
    derived_dir: Path = DEFAULT_DERIVED_DIR,
    *,
    stem: str = "frozen_9e_tapes_v2",
) -> dict[str, Any]:
    """X13-safe direct loader for `frozen_9e_tapes_v2.{json,npz}` verifying `npz_sha256` & Dev cutoff."""
    meta_path = derived_dir / f"{stem}.json"
    npz_path = derived_dir / f"{stem}.npz"
    if not meta_path.is_file() or not npz_path.is_file():
        raise FileNotFoundError(f"Missing frozen tape cache files: {meta_path} / {npz_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected_sha = str(meta.get("npz_sha256") or "")
    actual_sha = _sha256_file(npz_path)
    if not expected_sha or actual_sha != expected_sha:
        raise ValueError(f"FROZEN_TAPES_SHA_MISMATCH: expected={expected_sha[:16]} actual={actual_sha[:16]}")

    ext_days = [str(d) for d in meta["ext_days"]]
    if not ext_days:
        raise ValueError("Empty ext_days in frozen_9e_tapes_v2.json")
    assert_pre_holdout_days(ext_days)
    max_day = max(ext_days)
    if max_day >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: max_day={max_day} >= {HOLDOUT_CUTOFF_DAY}")

    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    tape_days: set[str] = set()
    with np.load(npz_path, allow_pickle=False) as z:
        for eng, eng_meta in meta["tapes"].items():
            days_list = [str(d) for d in eng_meta["days"]]
            assert_pre_holdout_days(days_list)
            tape_days.update(days_list)
            rows_map = eng_meta["rows"]
            stamps_all = np.asarray(z[f"{eng}__stamps"], dtype=np.int64)
            marks_all = np.asarray(z[f"{eng}__marks"], dtype=np.float64)
            offsets = np.asarray(z[f"{eng}__offsets"], dtype=np.int64)
            if len(stamps_all) > 0 and int(stamps_all.max()) >= HOLDOUT_STOP_TS:
                raise ValueError(
                    f"HOLDOUT_LOCK_VIOLATION: tape {eng} max timestamp {int(stamps_all.max())} >= {HOLDOUT_STOP_TS}"
                )
            day_map: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
            for idx, dk in enumerate(days_list):
                s0 = int(offsets[idx])
                s1 = int(offsets[idx + 1])
                day_map[dk] = (rows_map[dk], stamps_all[s0:s1], marks_all[s0:s1])
            tapes[eng] = day_map

    ext_days = sorted(set(ext_days) | tape_days)
    assert_pre_holdout_days(ext_days)
    max_day = max(ext_days)
    if max_day >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: max_day={max_day} >= {HOLDOUT_CUTOFF_DAY}")

    return {
        "schema": str(meta.get("schema", "")),
        "profile_mode": str(meta.get("profile_mode", "Swing")),
        "binding_sha256": str(meta.get("binding_sha256", "")),
        "npz_sha256": actual_sha,
        "ext_days": ext_days,
        "max_day": max_day,
        "holdout_rows_analysed": 0,
        "tapes": tapes,
    }


def load_red_news_calendar_rich(cal_path: Path) -> dict[str, list[tuple[int, str, int]]]:
    """Load red-news JSON (both 224-event `events_by_day` & 523-event 6-CCY `events` schemas).

    Returns `{day_iso: [(utc_ts, ccy_upper, event_blackout_sec), ...]}` enforcing `< 2025-01-01`.
    """
    raw = json.loads(cal_path.read_text(encoding="utf-8"))
    by_day: dict[str, list[tuple[int, str, int]]] = {}
    if "events_by_day" in raw:
        for dk, evs in raw["events_by_day"].items():
            dks = str(dk)
            if dks >= HOLDOUT_CUTOFF_DAY or int(dks[:4]) > 2024:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: day={dks}")
            day_list: list[tuple[int, str, int]] = []
            for ev in evs:
                ts = int(ev["utc_ts"])
                if ts >= HOLDOUT_STOP_TS:
                    raise ValueError(
                        f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: day={dks} ts={ts} >= {HOLDOUT_STOP_TS}"
                    )
                day_list.append((ts, str(ev["ccy"]).upper(), int(ev.get("blackout_sec", 300))))
            by_day[dks] = day_list
        return by_day
    if "events" in raw:
        for ev in raw["events"]:
            ts = int(ev["utc_ts"])
            if ts >= HOLDOUT_STOP_TS:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: ts={ts}")
            dk = datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
            if dk >= HOLDOUT_CUTOFF_DAY or int(dk[:4]) > 2024:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: day={dk}")
            ccy = str(ev["ccy"]).upper()
            ev_name = str(ev.get("event", "")).upper()
            bsec = int(ev.get("blackout_sec", 3600 if "EST03UTC" in ev_name else 300))
            by_day.setdefault(dk, []).append((ts, ccy, bsec))
        return by_day
    raise ValueError(f"Unsupported calendar schema in {cal_path}")


def asset_currencies(asset: str) -> tuple[str, ...]:
    """Map instrument symbol to affected currencies (matches `Naqex_PropGuard.mqh`)."""
    u = str(asset).upper()
    if any(tok in u for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "XAU", "BTC")):
        return ("USD",)
    if any(tok in u for tok in ("GER40", "DE40", "DAX")):
        return ("EUR",)
    if any(tok in u for tok in ("UK100", "FTSE")):
        return ("GBP",)
    if len(u) >= 6:
        return (u[:3], u[3:6])
    return ("USD",)


def directional_factor_deltas(asset: str, side: int) -> tuple[float, float, float, float, float, float]:
    """Return unit-risk directional factor weights `(uL, uS, jL, jS, iL, iS)` matching `Naqex_PropGuard.mqh`."""
    u = str(asset).upper()
    is_buy = int(side) > 0
    u_l = u_s = j_l = j_s = i_l = i_s = 0.0
    if any(tok in u for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX")):
        if is_buy:
            i_l = 1.0
        else:
            i_s = 1.0
        return u_l, u_s, j_l, j_s, i_l, i_s
    pos_usd = u.find("USD")
    if pos_usd == 0:
        if is_buy:
            u_l = 1.0
        else:
            u_s = 1.0
    elif pos_usd >= 3:
        if is_buy:
            u_s = 1.0
        else:
            u_l = 1.0
    pos_jpy = u.find("JPY")
    if pos_jpy == 0:
        if is_buy:
            j_l = 1.0
        else:
            j_s = 1.0
    elif pos_jpy >= 3:
        if is_buy:
            j_s = 1.0
        else:
            j_l = 1.0
    return u_l, u_s, j_l, j_s, i_l, i_s


def calibrate_m1_spread_guard(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    m1_cache_dir: Path = DEFAULT_M1_CACHE_DIR,
    engines: tuple[str, ...] = CORE7_IDS,
) -> dict[str, Any]:
    """Calibrate real M1 Bid/Ask spreads on Dev 2018-2024 parquets (strict Cluster-A causal rule).

    Every symbol's Dev SpreadGuard cap is computed programmatically strictly from Cluster-A
    (`2018-2020`, `dk < "2021-01-01"`) M1 bars and Cluster-A entry minutes via
    `derive_causal_cluster_a_spread_cap()` (`ceil_to_5(max(session_A_p99_9, 1.10 * entry_A_p99_9))`),
    with ZERO Cluster-B (`2021-2024`) input.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {
            "available": False,
            "reason": "pyarrow_not_installed",
            "calibration_rule": SPREAD_GUARD_CALIBRATION_RULE,
            "calibrated_dev_caps_a": {},
            "symbols": {},
            "entry_spread_pts": {},
        }

    # Verify ALL required Dev year files (2018..2024) for all 4 symbols exist before reading
    missing_files = [
        str(m1_cache_dir / sub / f"{sym}-M1-BIDASK-{yr}.parquet")
        for sym, (sub, _) in M1_SPREAD_SPECS.items()
        for yr in range(2018, 2025)
        if not (m1_cache_dir / sub / f"{sym}-M1-BIDASK-{yr}.parquet").is_file()
    ]
    if missing_files:
        return {
            "available": False,
            "reason": "m1_parquet_cache_incomplete",
            "missing_count": len(missing_files),
            "calibration_rule": SPREAD_GUARD_CALIBRATION_RULE,
            "calibrated_dev_caps_a": {},
            "symbols": {},
            "entry_spread_pts": {},
        }

    entries_by_sym: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for eng in engines:
        for dk, (row, stamps, _marks) in tapes.get(eng, {}).items():
            sym = str(row.get("asset") or ENGINE_ASSET_MAP[eng])
            ent_min = int(stamps[0]) // 60 if len(stamps) > 0 else int(row["entry"]) // 60
            entries_by_sym[sym].append((ent_min, dk, eng))

    symbols_summary: dict[str, Any] = {}
    calibrated_dev_caps_a: dict[str, float] = {}
    entry_spread_pts: dict[tuple[str, str], float] = {}

    def _qdict(arr: np.ndarray | list[float]) -> dict[str, float]:
        a = np.asarray(arr, dtype=np.float64)
        if len(a) == 0:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "p99_5": 0.0, "p99_9": 0.0, "max": 0.0}
        qs = np.percentile(a, [50, 95, 99, 99.5, 99.9, 100])
        return {
            "p50": round(float(qs[0]), 2),
            "p95": round(float(qs[1]), 2),
            "p99": round(float(qs[2]), 2),
            "p99_5": round(float(qs[3]), 2),
            "p99_9": round(float(qs[4]), 2),
            "max": round(float(qs[5]), 2),
        }

    for sym, (sub, div_pts) in M1_SPREAD_SPECS.items():
        sym_entries = entries_by_sym.get(sym, [])
        # Entry UTC hours strictly from Cluster A (dk < 2021-01-01) — zero Cluster-B leakage!
        entry_hours_a = sorted({(em // 60) % 24 for em, dk, _ in sym_entries if dk < CLUSTER_A_CUTOFF_DAY})

        mins_a_parts: list[np.ndarray] = []
        spr_a_parts: list[np.ndarray] = []
        mins_b_parts: list[np.ndarray] = []
        spr_b_parts: list[np.ndarray] = []
        act_a_parts: list[np.ndarray] = []
        act_b_parts: list[np.ndarray] = []
        sess_a_parts: list[np.ndarray] = []

        for yr in range(2018, 2025):
            pq_path = m1_cache_dir / sub / f"{sym}-M1-BIDASK-{yr}.parquet"
            tbl = pq.read_table(pq_path, columns=["minute", "bo", "ao"])
            mn = tbl["minute"].to_numpy()
            if len(mn) > 0 and int(mn.max()) * 60 >= HOLDOUT_STOP_TS:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in {pq_path.name}: max_min={int(mn.max())}")
            sp = (tbl["ao"].to_numpy() - tbl["bo"].to_numpy()).astype(np.float64) * div_pts
            hr = (mn // 60) % 24
            act = hr < 21  # Exclude 21:00..00:00 UTC rollover blackout
            if yr <= CLUSTER_A_MAX_YEAR:
                mins_a_parts.append(mn)
                spr_a_parts.append(sp)
                act_a_parts.append(sp[act])
                sess_mask = np.isin(hr, entry_hours_a) if entry_hours_a else act
                sess_a_parts.append(sp[sess_mask])
            else:
                mins_b_parts.append(mn)
                spr_b_parts.append(sp)
                act_b_parts.append(sp[act])

        mn_a = np.concatenate(mins_a_parts) if mins_a_parts else np.empty(0, dtype=np.int64)
        sp_a_raw = np.concatenate(spr_a_parts) if spr_a_parts else np.empty(0, dtype=np.float64)
        mn_all = np.concatenate(mins_a_parts + mins_b_parts)
        sp_all = np.concatenate(spr_a_parts + spr_b_parts)
        sp_a = np.concatenate(act_a_parts) if act_a_parts else np.empty(0, dtype=np.float64)
        sp_b = np.concatenate(act_b_parts) if act_b_parts else np.empty(0, dtype=np.float64)
        sess_a = np.concatenate(sess_a_parts) if sess_a_parts else np.empty(0, dtype=np.float64)

        ent_vals_all: list[float] = []
        ent_vals_a: list[float] = []
        ent_vals_b: list[float] = []
        matched = 0
        missing_prior = 0
        for ent_m, dk, eng in sym_entries:
            # Cluster-A entries resolve strictly against Cluster-A (2018-2020) arrays only
            if dk < CLUSTER_A_CUTOFF_DAY:
                arr_m, arr_s = mn_a, sp_a_raw
            else:
                arr_m, arr_s = mn_all, sp_all
            idx = int(np.searchsorted(arr_m, ent_m))
            if idx < len(arr_m) and int(arr_m[idx]) == ent_m:
                val = float(arr_s[idx])
                matched += 1
            elif idx > 0:
                # Strictly causal fallback: nearest PRIOR bar < ent_m (never looks forward!)
                val = float(arr_s[idx - 1])
            else:
                # ent_m < arr_m[0]: no prior causal bar exists -> do NOT peek forward to bar 0
                missing_prior += 1
                continue
            entry_spread_pts[(eng, dk)] = val
            ent_vals_all.append(val)
            if dk < CLUSTER_A_CUTOFF_DAY:
                ent_vals_a.append(val)
            else:
                ent_vals_b.append(val)

        # Programmatically derive Dev SpreadGuard cap strictly from Cluster-A (2018-2020) data
        dev_cap = derive_causal_cluster_a_spread_cap(sess_a, ent_vals_a)
        calibrated_dev_caps_a[sym] = dev_cap
        # FTMO Demo live broker feed US100 normal spread is ~195 pts (~1.8x -> 350.0 pts); FX pairs stay 1:1
        live_cap = 350.0 if sym == "US100" else dev_cap

        symbols_summary[sym] = {
            "bars_total": int(len(mn_all)),
            "entry_trades_total": len(sym_entries),
            "entry_exact_minute_matches": matched,
            "missing_prior_bar_count": missing_prior,
            "entry_hours_cluster_a_utc": entry_hours_a,
            "session_cluster_a_pts": _qdict(sess_a),
            "active_cluster_a_pts": _qdict(sp_a),
            "active_cluster_b_pts": _qdict(sp_b),
            "entry_all_pts": _qdict(ent_vals_all),
            "entry_cluster_a_pts": _qdict(ent_vals_a),
            "entry_cluster_b_pts": _qdict(ent_vals_b),
            "recommended_dev_cap_pts": dev_cap,
            "recommended_ftmo_live_cap_pts": live_cap,
        }

    return {
        "available": True,
        "holdout_rows_analysed": 0,
        "cluster_a_window": "2018-01-01..2020-12-31",
        "calibration_rule": SPREAD_GUARD_CALIBRATION_RULE,
        "calibrated_dev_caps_a": calibrated_dev_caps_a,
        "symbols": symbols_summary,
        "entry_spread_pts": entry_spread_pts,
    }


def estimate_base_friction_usd_per_lot(row: dict[str, Any]) -> float:
    """Estimate round-trip friction USD/lot matching `capital_optimizer` / `portfolio_v1_vs_v2_study`."""
    stop_cost = float(row.get("stop_risk_with_cost_usd") or 0.0)
    if stop_cost <= 0.0:
        return 0.0
    init_r = row.get("initial_risk_usd")
    if init_r is not None and float(init_r) > 0.0:
        diff = max(0.0, stop_cost - float(init_r))
        if diff > 0.0:
            return diff
    ep = row.get("entry_price")
    slp = row.get("sl_price") or row.get("stop")
    asset = str(row.get("asset") or "")
    if ep is not None and slp is not None and float(ep) > 0.0 and float(slp) > 0.0:
        dist = abs(float(ep) - float(slp))
        if asset in ("EURUSD", "GBPUSD", "AUDUSD"):
            raw_sl = dist * 100_000.0
        elif asset in ("USDJPY", "EURJPY", "GBPJPY"):
            usd_jpy = float(ep) if asset == "USDJPY" else 135.0
            raw_sl = dist * 100_000.0 / max(80.0, usd_jpy)
        elif asset in ("US100", "US500", "GER40"):
            raw_sl = dist * 1.0
        elif asset == "XAUUSD":
            raw_sl = dist * 100.0
        else:
            raw_sl = stop_cost * 0.96
        if 0.50 * stop_cost <= raw_sl < stop_cost:
            return max(stop_cost - raw_sl, 0.03 * stop_cost)
    return 0.035 * stop_cost


def apply_cost_stress_to_tapes(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    cost_mult: float,
    *,
    engines: tuple[str, ...] = CORE7_IDS,
) -> dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]]:
    """Shift M1 trade tapes dollar-for-dollar by `(cost_mult - 1.0) * base_friction_usd_per_lot`."""
    if abs(cost_mult - 1.0) < 1e-9:
        return {eng: tapes[eng] for eng in engines if eng in tapes}
    delta = float(cost_mult) - 1.0
    out: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    for eng in engines:
        if eng not in tapes:
            continue
        new_dm: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
        for dk, (row, stamps, marks) in tapes[eng].items():
            extra = delta * estimate_base_friction_usd_per_lot(row)
            new_row = {
                **row,
                "net_usd_per_lot": float(row["net_usd_per_lot"]) - extra,
                "stop_risk_with_cost_usd": float(row["stop_risk_with_cost_usd"]) + extra,
            }
            new_marks = np.asarray(marks, dtype=np.float64) - extra
            new_dm[dk] = (new_row, stamps, new_marks)
        out[eng] = new_dm
    return out


def apply_red_news_and_spread_guard(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    red_news_cal: dict[str, list[tuple[int, str, int]]] | None,
    news_pad_sec: int = 300,
    spread_caps_pts: dict[str, float] | None = None,
    entry_spread_pts: dict[tuple[str, str], float] | None = None,
    engines: tuple[str, ...] = CORE7_IDS,
) -> tuple[dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]], dict[str, Any]]:
    """Causally apply SpreadGuard at entry minute + ±pad_sec (and BoJ ±3600s) red-news flatten guard."""
    out: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    stats = {
        "total_in": 0,
        "kept_untouched": 0,
        "blocked_spread": 0,
        "blocked_news_entry": 0,
        "flattened_pre_news": 0,
        "blocked_spread_examples": [],
    }
    for eng in engines:
        dm = tapes.get(eng, {})
        eng_out: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
        for dk, (row, stamps, marks) in dm.items():
            stats["total_in"] += 1
            asset = str(row.get("asset") or ENGINE_ASSET_MAP.get(eng, "USDJPY"))

            # 1. Causal entry-minute M1 SpreadGuard check
            if spread_caps_pts is not None and entry_spread_pts is not None:
                cap_pts = float(spread_caps_pts.get(asset, 1e9))
                obs_pts = entry_spread_pts.get((eng, dk))
                if obs_pts is not None and obs_pts > cap_pts:
                    stats["blocked_spread"] += 1
                    if len(stats["blocked_spread_examples"]) < 25:
                        stats["blocked_spread_examples"].append(
                            {
                                "day": dk,
                                "engine": eng,
                                "asset": asset,
                                "spread_pts": round(obs_pts, 1),
                                "cap_pts": round(cap_pts, 1),
                                "net_R": round(float(row.get("net_R", 0.0)), 3),
                            }
                        )
                    continue

            # 2. Causal red-news window block & pre-flatten (respects per-event blackout_sec >= pad_sec, e.g. BoJ 3600s)
            if red_news_cal is None:
                eng_out[dk] = (row, stamps, marks)
                stats["kept_untouched"] += 1
                continue

            ccys = set(asset_currencies(asset))
            day_ev = [
                (ts, max(int(news_pad_sec), int(ev_bsec))) for ts, c, ev_bsec in red_news_cal.get(dk, []) if c in ccys
            ]
            if not day_ev:
                eng_out[dk] = (row, stamps, marks)
                stats["kept_untouched"] += 1
                continue

            t_ent = int(stamps[0])
            t_ext = int(row["exit"])
            if any(abs(t_ent - tn) <= eff_pad for tn, eff_pad in day_ev):
                stats["blocked_news_entry"] += 1
                continue

            cut_events = [tn - eff_pad for tn, eff_pad in day_ev if t_ent < (tn - eff_pad) < t_ext]
            if not cut_events:
                eng_out[dk] = (row, stamps, marks)
                stats["kept_untouched"] += 1
                continue

            t_cut = min(cut_events)
            k = int(stamps.searchsorted(t_cut, side="right")) - 1
            if k < 0:
                stats["blocked_news_entry"] += 1
                continue

            new_stamps = stamps[: k + 1].copy()
            new_marks = marks[: k + 1].copy()
            term_pnl = float(new_marks[-1, 3])
            new_marks[-1, 3] = term_pnl
            new_net_r = float(term_pnl / max(1e-6, float(row["stop_risk_with_cost_usd"])))
            new_row = {
                **row,
                "exit": int(new_stamps[-1]) + 60,
                "at_open": False,
                "reason": "NEWS_PRE_FLATTEN",
                "net_usd_per_lot": term_pnl,
                "net_R": new_net_r,
                "gross_R": new_net_r,
            }
            eng_out[dk] = (new_row, new_stamps, new_marks)
            stats["flattened_pre_news"] += 1
        out[eng] = eng_out
    return out, stats


def margin_per_lot_usd(
    asset: str, entry_price: float, profile_mode: str = "Standard"
) -> tuple[float, float, float, float, float]:
    """Return `(margin_per_lot_usd, vol_min, vol_step, vol_max, comm_usd_per_lot)` matching FTMO Demo specs."""
    is_std = str(profile_mode) == "Standard"
    if asset in ("US100", "US100.cash", "US500", "US500.cash"):
        mgn = float(entry_price) * (0.02 if is_std else (1.0 / 15.0))
        return mgn, 0.01, 0.01, 1000.0, 0.0
    if asset == "XAUUSD":
        mgn = float(entry_price) * 100.0 * (0.02 if is_std else 0.10)
        return mgn, 0.01, 0.01, 100.0, 5.20
    lev = 100.0 if is_std else 30.0
    if asset in ("USDJPY", "USDCAD", "USDCHF"):
        notional = 100_000.0
    elif asset.startswith("EUR") and not asset.endswith("USD"):
        notional = 100_000.0 * 1.15
    elif asset.startswith("GBP") and not asset.endswith("USD"):
        notional = 100_000.0 * 1.35
    else:
        notional = 100_000.0 * float(entry_price)
    return notional / lev, 0.01, 0.01, 50.0, 5.0


def floor_lot_step(raw_lots: float, *, step: float = 0.01, vol_min: float = 0.01, vol_max: float = 1000.0) -> float:
    if raw_lots <= 0.0 or not math.isfinite(raw_lots):
        return 0.0
    capped = min(float(raw_lots), float(vol_max))
    steps = math.floor(capped / step + 1e-9)
    lot = round(steps * step, 8)
    return 0.0 if lot < vol_min - 1e-12 else lot


def prealign_days_for_tapes(
    ext_days: list[str],
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    engines: tuple[str, ...] = CORE7_IDS,
    base_risks: dict[str, float] = CORE7_BASE_RISK_FRAC,
) -> list[dict[str, Any]]:
    """Pre-align 1-lot M1 mark matrices ONCE per tape configuration (bit-exact with `ExactTierReplayCache`)."""
    pre_days: list[dict[str, Any]] = []
    for day_idx, dk in enumerate(ext_days):
        cands = [(eng, tapes[eng][dk]) for eng in engines if eng in tapes and dk in tapes[eng]]
        if not cands:
            continue
        cands.sort(key=lambda kv: (int(kv[1][0]["entry"]), kv[0]))
        k = len(cands)
        min_e = min(int(stamps[0]) for _, (_, stamps, _) in cands)
        max_x = max(int(stamps[-1]) for _, (_, stamps, _) in cands)
        n_tl = int((max_x - min_e) // 60) + 1
        marks_1lot = np.zeros((k, n_tl, 4), dtype=np.float64)

        meta_list: list[dict[str, Any]] = []
        for i, (eng, (row, stamps, marks)) in enumerate(cands):
            asset = str(row.get("asset") or ENGINE_ASSET_MAP.get(eng, "USDJPY"))
            side = int(row.get("side", 1))
            entry_ts = int(stamps[0])
            at_open = bool(row.get("at_open", False))
            release_ts = int(stamps[-1]) + (0 if at_open else 60)
            net_1lot = float(row["net_usd_per_lot"])
            stop_cost = float(row["stop_risk_with_cost_usd"])
            ep = float(row["entry_price"])
            mgn_std, vmin_s, vstep_s, vmax_s, comm_s = margin_per_lot_usd(asset, ep, "Standard")
            mgn_swg, _vmin_w, _vstep_w, _vmax_w, comm_w = margin_per_lot_usd(asset, ep, "Swing")

            offsets = (stamps - min_e) // 60
            start_o, end_o = int(offsets[0]), int(offsets[-1])
            marks_1lot[i, offsets, :] = marks
            if len(offsets) < (end_o - start_o + 1):
                pos = np.arange(start_o, end_o + 1)
                gaps = np.setdiff1d(pos, offsets, assume_unique=True)
                past = offsets.searchsorted(gaps) - 1
                marks_1lot[i, gaps, :] = marks[past, 3][:, None]
            if end_o + 1 < n_tl:
                marks_1lot[i, end_o + 1 :, :] = net_1lot

            meta_list.append(
                {
                    "eng": eng,
                    "asset": asset,
                    "side": side,
                    "factors": directional_factor_deltas(asset, side),
                    "base_r": float(base_risks[eng]),
                    "entry_ts": entry_ts,
                    "release_ts": release_ts,
                    "stop_cost": stop_cost,
                    "net_1lot": net_1lot,
                    "mgn_std": mgn_std,
                    "comm_std": comm_s,
                    "vmin": vmin_s,
                    "vstep": vstep_s,
                    "vmax": vmax_s,
                    "mgn_swg": mgn_swg,
                    "comm_swg": comm_w,
                    "stamps": stamps,
                    "marks": marks,
                }
            )

        open_fl = np.zeros((k, k), dtype=np.float64)
        for j in range(k):
            st_j = meta_list[j]["entry_ts"]
            for i in range(j):
                mi = meta_list[i]
                if st_j >= mi["release_ts"]:
                    open_fl[i, j] = mi["net_1lot"]
                else:
                    sc = mi["stamps"]
                    pos_i = int(sc.searchsorted(st_j))
                    if pos_i < len(sc) and int(sc[pos_i]) == st_j:
                        open_fl[i, j] = float(mi["marks"][pos_i, 0])
                    else:
                        open_fl[i, j] = float(mi["marks"][pos_i - 1, 3])

        pre_days.append(
            {
                "day_idx": day_idx,
                "day": dk,
                "year": int(dk[:4]),
                "cands": meta_list,
                "marks_flat": np.ascontiguousarray(marks_1lot.reshape(k, n_tl * 4)),
                "open_fl": open_fl,
            }
        )
    return pre_days


def replay_shielded_stage(
    ext_days: list[str],
    pre_days: list[dict[str, Any]],
    *,
    capital_usd: float,
    mult: float,
    symcap_pct: float,
    profile_mode: str = "Standard",
    total_open_cap_pct: float | None = None,
    usd_cluster_cap_pct: float | None = None,
    jpy_cluster_cap_pct: float | None = None,
    idx_cluster_cap_pct: float | None = None,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact M1 minute-by-minute portfolio replay enforcing SYMCAP + Shield A (total open) + Shield B (clusters)."""
    n_days = len(ext_days)
    nets = np.zeros(n_days, dtype=np.float64)
    dds = np.zeros(n_days, dtype=np.float64)
    ups = np.zeros(n_days, dtype=np.float64)
    flg = np.zeros(n_days, dtype=np.int8)

    initial = float(capital_usd)
    balance = initial
    peak_eq = initial
    max_peak_dd = 0.0
    max_daily_dd = 0.0
    symcap = float(symcap_pct) / 100.0
    tot_cap = None if total_open_cap_pct is None else float(total_open_cap_pct) / 100.0
    usd_cap = None if usd_cluster_cap_pct is None else float(usd_cluster_cap_pct) / 100.0
    jpy_cap = None if jpy_cluster_cap_pct is None else float(jpy_cluster_cap_pct) / 100.0
    idx_cap = None if idx_cluster_cap_pct is None else float(idx_cluster_cap_pct) / 100.0
    is_std = str(profile_mode) == "Standard"

    sized_cnt = 0
    min_lot_rej = 0
    margin_rej = 0
    symcap_skip = 0
    total_cap_hits = 0
    total_cap_skip = 0
    cluster_cap_hits = 0
    cluster_cap_skip = 0
    peak_simultaneous_open_risk_frac = 0.0
    peak_simultaneous_positions = 0
    wins_sum = 0.0
    wins_cnt = 0
    loss_sum = 0.0
    loss_cnt = 0
    r_sum = 0.0
    r_cnt = 0
    cur_loss = 0
    max_loss = 0
    net_a = 0.0
    net_b = 0.0

    for pd_row in pre_days:
        cands = pd_row["cands"]
        k = len(cands)
        open_fl = pd_row["open_fl"]
        lots = np.zeros(k, dtype=np.float64)
        eff_risks = [0.0] * k
        actual_risks = [0.0] * k
        margins = [0.0] * k
        any_sized = False

        for j in range(k):
            cj = cands[j]
            req_r = cj["base_r"] * float(mult)
            er = req_r
            st_j = cj["entry_ts"]
            asset_j = cj["asset"]
            du_l, du_s, dj_l, dj_s, di_l, di_s = cj["factors"]

            open_sym_r = 0.0
            open_tot_r = 0.0
            u_l = u_s = j_l = j_s = i_l = i_s = 0.0
            open_cnt = 0
            for i in range(j):
                if lots[i] > 0.0 and st_j < cands[i]["release_ts"]:
                    ri = eff_risks[i]
                    open_tot_r += ri
                    open_cnt += 1
                    if cands[i]["asset"] == asset_j:
                        open_sym_r += ri
                    fu_l, fu_s, fj_l, fj_s, fi_l, fi_s = cands[i]["factors"]
                    u_l += fu_l * ri
                    u_s += fu_s * ri
                    j_l += fj_l * ri
                    j_s += fj_s * ri
                    i_l += fi_l * ri
                    i_s += fi_s * ri

            # 1. Per-symbol cap
            rem_sym = max(0.0, symcap - open_sym_r)
            if rem_sym < er - 1e-12:
                er = rem_sym
            if er <= 1e-4:  # Matches MQL5 `allowedRiskPct <= 0.01%`
                symcap_skip += 1
                continue

            # 2. Shield B directional factor cluster caps (USD / JPY / US100)
            rem_cluster = 1e9
            if usd_cap is not None:
                if du_l > 0.0:
                    rem_cluster = min(rem_cluster, max(0.0, usd_cap - u_l))
                if du_s > 0.0:
                    rem_cluster = min(rem_cluster, max(0.0, usd_cap - u_s))
            if jpy_cap is not None:
                if dj_l > 0.0:
                    rem_cluster = min(rem_cluster, max(0.0, jpy_cap - j_l))
                if dj_s > 0.0:
                    rem_cluster = min(rem_cluster, max(0.0, jpy_cap - j_s))
            if idx_cap is not None:
                if di_l > 0.0:
                    rem_cluster = min(rem_cluster, max(0.0, idx_cap - i_l))
                if di_s > 0.0:
                    rem_cluster = min(rem_cluster, max(0.0, idx_cap - i_s))
            if rem_cluster < er - 1e-12:
                cluster_cap_hits += 1
                er = rem_cluster
            if er <= 1e-4:
                cluster_cap_skip += 1
                continue

            # 3. Shield A total simultaneous open-account risk cap
            if tot_cap is not None:
                rem_tot = max(0.0, tot_cap - open_tot_r)
                if rem_tot < er - 1e-12:
                    total_cap_hits += 1
                    er = rem_tot
                if er <= 1e-4:
                    total_cap_skip += 1
                    continue

            budget = initial * er
            lot = floor_lot_step(budget / cj["stop_cost"], step=cj["vstep"], vol_min=cj["vmin"], vol_max=cj["vmax"])
            if lot < cj["vmin"]:
                min_lot_rej += 1
                continue

            mgn_1 = cj["mgn_std"] if is_std else cj["mgn_swg"]
            comm_1 = cj["comm_std"] if is_std else cj["comm_swg"]
            used_m = 0.0
            fl_sum = 0.0
            for i in range(j):
                if lots[i] > 0.0:
                    if st_j < cands[i]["release_ts"]:
                        used_m += margins[i]
                    fl_sum += lots[i] * open_fl[i, j]
            avail = balance + fl_sum - used_m
            if lot * (mgn_1 + comm_1) > avail:
                margin_rej += 1
                continue

            lots[j] = lot
            act_r = (lot * cj["stop_cost"]) / initial
            eff_risks[j] = er
            actual_risks[j] = act_r
            margins[j] = lot * mgn_1
            any_sized = True
            sized_cnt += 1

            cur_open_r = open_tot_r + er
            if cur_open_r > peak_simultaneous_open_risk_frac:
                peak_simultaneous_open_risk_frac = cur_open_r
            if open_cnt + 1 > peak_simultaneous_positions:
                peak_simultaneous_positions = open_cnt + 1

            pnl_j = lot * cj["net_1lot"]
            if budget > 1e-9:
                r_sum += pnl_j / budget
                r_cnt += 1
            if pnl_j > 0.0:
                wins_sum += pnl_j
                wins_cnt += 1
                cur_loss = 0
            elif pnl_j < 0.0:
                loss_sum += -pnl_j
                loss_cnt += 1
                cur_loss += 1
                if cur_loss > max_loss:
                    max_loss = cur_loss

        if not any_sized:
            continue

        comb = lots @ pd_row["marks_flat"]
        day_min_rel = float(comb.min())
        day_max_rel = float(comb.max())
        day_net = float(comb[-1])
        day_dd = max(0.0, -day_min_rel)
        day_up = max(0.0, day_max_rel)

        eq_pts = balance + comb
        if eq_pts.max() > peak_eq:
            run_peaks = np.maximum(peak_eq, np.maximum.accumulate(eq_pts))
            day_peak_dd = float(np.max(run_peaks - eq_pts))
            peak_eq = float(run_peaks[-1])
        else:
            day_peak_dd = float(peak_eq - eq_pts.min())
        if day_peak_dd > max_peak_dd:
            max_peak_dd = day_peak_dd
        if day_dd > max_daily_dd:
            max_daily_dd = day_dd

        d_i = pd_row["day_idx"]
        nets[d_i] = day_net
        dds[d_i] = day_dd
        ups[d_i] = day_up
        flg[d_i] = 1
        balance += day_net
        if pd_row["year"] <= 2020:
            net_a += day_net
        else:
            net_b += day_net

    yrs_span = max(1.0, float(len({d[:4] for d in ext_days})))
    ann_pct = 100.0 * ((balance - initial) / yrs_span) / initial
    peak_dd_pct = 100.0 * max_peak_dd / initial
    calmar = (ann_pct / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0
    daily_ret = nets / initial
    std_d = float(np.std(daily_ret, ddof=1)) if n_days > 1 else 0.0
    sharpe = (float(np.mean(daily_ret)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
    pf = (wins_sum / loss_sum) if loss_sum > 1e-9 else 0.0
    wr = 100.0 * wins_cnt / max(1, wins_cnt + loss_cnt)
    rr = ((wins_sum / wins_cnt) / (loss_sum / loss_cnt)) if (wins_cnt > 0 and loss_cnt > 0) else 0.0
    ev_r = (r_sum / r_cnt) if r_cnt > 0 else 0.0
    ev_usd = (balance - initial) / max(1, sized_cnt)

    # Crisis window DD breakdown
    crisis_dd: dict[str, dict[str, float]] = {}
    for cname, d0, d1 in CRISIS_WINDOWS:
        mask = np.array([d0 <= d <= d1 for d in ext_days])
        if np.any(mask):
            c_nets = nets[mask]
            c_dds = dds[mask]
            c_eq = initial
            c_pk = initial
            c_mdd = 0.0
            for cn, cd in zip(c_nets, c_dds, strict=True):
                c_mdd = max(c_mdd, c_pk - (c_eq - float(cd)))
                c_eq += float(cn)
                if c_eq > c_pk:
                    c_pk = c_eq
            crisis_dd[cname] = {
                "ret_pct": round(100.0 * float(np.sum(c_nets)) / initial, 2),
                "max_dd_pct": round(100.0 * c_mdd / initial, 2),
                "max_daily_dd_pct": round(100.0 * float(np.max(c_dds)) / initial, 2),
            }

    metrics = {
        "capital_usd": initial,
        "mult": round(float(mult), 4),
        "sized_trades": sized_cnt,
        "min_lot_rejected": min_lot_rej,
        "margin_rejected": margin_rej,
        "symcap_skipped": symcap_skip,
        "total_cap_hits": total_cap_hits,
        "total_cap_skipped": total_cap_skip,
        "cluster_cap_hits": cluster_cap_hits,
        "cluster_cap_skipped": cluster_cap_skip,
        "peak_open_risk_pct": round(100.0 * peak_simultaneous_open_risk_frac, 3),
        "peak_simultaneous_positions": peak_simultaneous_positions,
        "net_usd": round(balance - initial, 2),
        "ev_usd_per_trade": round(ev_usd, 2),
        "ann_pct": round(ann_pct, 3),
        "ann_cluster_a_pct": round(100.0 * (net_a / 3.0) / initial, 3),
        "ann_cluster_b_pct": round(100.0 * (net_b / 4.0) / initial, 3),
        "peak_dd_pct": round(peak_dd_pct, 3),
        "max_daily_dd_pct": round(100.0 * max_daily_dd / initial, 3),
        "calmar": round(calmar, 3),
        "sharpe": round(sharpe, 3),
        "winrate_pct": round(wr, 2),
        "avg_rr": round(rr, 3),
        "ev_per_trade_r": round(ev_r, 4),
        "profit_factor": round(pf, 3),
        "max_loss_streak_trades": max_loss,
        "crisis_windows": crisis_dd,
    }
    return metrics, nets, dds, ups, flg


def compute_honest_shock_matrix(
    *,
    total_open_cap_p1p2_pct: float | None,
    total_open_cap_funded_pct: float | None,
    usd_cluster_cap_p1p2_pct: float | None = None,
    jpy_cluster_cap_p1p2_pct: float | None = None,
    idx_cluster_cap_p1p2_pct: float | None = None,
    usd_cluster_cap_funded_pct: float | None = None,
    jpy_cluster_cap_funded_pct: float | None = None,
    idx_cluster_cap_funded_pct: float | None = None,
    gap_slippage_frac: float = 0.25,
) -> list[dict[str, Any]]:
    """Honest worst-case simultaneous flash-crash gap-through shock matrix across Funded / P2 / P1 Bal / P1 Spr.

    Never clamps under 5%. Enforces exact analytical upper bound of simultaneously open SL risk:
      `max_open_risk = min(sum_per_symbol_symcap, directional_cluster_bound, total_open_account_cap)`
    then multiplies by `(1.0 + gap_slippage_frac)` (1.25x standard flash gap and 1.50x extreme gap).
    """
    usdjpy_base = (
        CORE7_BASE_RISK_FRAC["E1_USDJPY_TOKYO"]
        + CORE7_BASE_RISK_FRAC["E2_USDJPY_EXP80"]
        + CORE7_BASE_RISK_FRAC["E7_USDJPY_NY10ET"]
    )
    us100_base = CORE7_BASE_RISK_FRAC["E4_US100_SESS40"] + CORE7_BASE_RISK_FRAC["E5_US100_RS1130"]
    sym_7e = {
        "USDJPY": usdjpy_base * 100.0,
        "GBPUSD": CORE7_BASE_RISK_FRAC["E3_GBPUSD_VH"] * 100.0,
        "US100": us100_base * 100.0,
        "EURJPY": CORE7_BASE_RISK_FRAC["E6_EURJPY_VOLCOMP"] * 100.0,
    }
    sym_9e = {
        **sym_7e,
        "EURUSD": TURBO9_EXTRA_RISK_FRAC["S6_FX_USD_BSK"] * 100.0,
        "XAUUSD": TURBO9_EXTRA_RISK_FRAC["S7_XAU_EXP120"] * 100.0,
    }

    fn_caps = (
        total_open_cap_funded_pct,
        usd_cluster_cap_funded_pct,
        jpy_cluster_cap_funded_pct,
        idx_cluster_cap_funded_pct,
    )
    p12_caps = (
        total_open_cap_p1p2_pct,
        usd_cluster_cap_p1p2_pct,
        jpy_cluster_cap_p1p2_pct,
        idx_cluster_cap_p1p2_pct,
    )
    profiles = (
        ("Funded (1.00x RedTeam / PORT_7E)", sym_7e, 1.00, 1.00, *fn_caps),
        ("Funded_C10 (1.25x / PORT_7E)", sym_7e, 1.25, 1.25, *fn_caps),
        ("P2 (2.50x RedTeam / PORT_7E)", sym_7e, 2.50, 1.50, *p12_caps),
        ("P2_C10 (3.50x / PORT_7E)", sym_7e, 3.50, 1.75, *p12_caps),
        ("P1 Bal (4.00x / PORT_9E)", sym_9e, 4.00, 2.00, *p12_caps),
        ("P1 Bal_C10 (4.00x / PORT_7E)", sym_7e, 4.00, 1.75, *p12_caps),
        ("P1 Spr (4.75x / PORT_9E)", sym_9e, 4.75, 2.25, *p12_caps),
    )

    rows: list[dict[str, Any]] = []
    for name, smap, mult, symcap, tot_cap, u_cap, j_cap, i_cap in profiles:
        uncapped_sum = sum(v * mult for v in smap.values())
        sym_eff = {sym: min(v * mult, symcap) for sym, v in smap.items()}
        symcap_sum = sum(sym_eff.values())

        # Worst-case same-direction correlated FX/Index cluster exposure (if cluster caps enabled)
        usd_side = sum(sym_eff.get(s, 0.0) for s in ("USDJPY", "GBPUSD", "EURUSD", "XAUUSD"))
        jpy_side = sym_eff.get("USDJPY", 0.0) + sym_eff.get("EURJPY", 0.0)
        idx_side = sym_eff.get("US100", 0.0)
        worst_single_factor = max(
            min(usd_side, u_cap) if u_cap is not None else usd_side,
            min(jpy_side, j_cap) if j_cap is not None else jpy_side,
            min(idx_side, i_cap) if i_cap is not None else idx_side,
        )

        # Total open risk bound across ALL open positions simultaneously
        bounded_open = symcap_sum
        if u_cap is not None and j_cap is not None and i_cap is not None:
            # Even without total cap, opposite-side USD/JPY positions could still sum to 2*caps;
            # worst same-direction macro shock across USD + EURJPY + US100 is bounded by cluster sum:
            same_dir_macro = min(usd_side, u_cap) + min(sym_eff.get("EURJPY", 0.0), j_cap) + min(idx_side, i_cap)
        else:
            same_dir_macro = symcap_sum

        if tot_cap is not None:
            bounded_open = min(bounded_open, float(tot_cap))
            same_dir_macro = min(same_dir_macro, float(tot_cap))
            worst_single_factor = min(worst_single_factor, float(tot_cap))

        gap_125 = bounded_open * (1.0 + gap_slippage_frac)
        gap_150 = bounded_open * 1.50
        rows.append(
            {
                "profile": name,
                "mult": mult,
                "symcap_pct": symcap,
                "uncapped_sum_pct": round(uncapped_sum, 2),
                "symcap_sum_pct": round(symcap_sum, 2),
                "bounded_open_risk_pct": round(bounded_open, 2),
                "same_dir_macro_125x_pct": round(same_dir_macro * (1.0 + gap_slippage_frac), 2),
                "worst_single_factor_150x_pct": round(worst_single_factor * 1.50, 2),
                "gap_shock_125x_pct": round(gap_125, 2),
                "gap_shock_150x_pct": round(gap_150, 2),
                "under_4_50_pct_at_125x": gap_125 <= 4.50 + 1e-9,
                "under_5_00_pct_at_125x": gap_125 < 5.00 - 1e-9,
                "under_5_00_pct_at_150x": gap_150 < 5.00 - 1e-9,
            }
        )
    return rows


def make_block_bootstrap_indices(
    n_obs: int,
    *,
    horizon: int = 756,
    n_paths: int = 2000,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_blocks = (horizon + block_len - 1) // block_len
    starts = rng.integers(0, n_obs, size=(n_paths, n_blocks))
    offs = np.arange(block_len, dtype=np.int64)[None, None, :]
    idxs = (starts[:, :, None] + offs).reshape(n_paths, n_blocks * block_len)[:, :horizon] % n_obs
    return idxs.astype(np.int32)


@njit(cache=False)
def _simulate_ftmo_std_single_ticket_numba(
    idx_matrix: np.ndarray,
    n_p1: np.ndarray,
    d_p1: np.ndarray,
    f_p1: np.ndarray,
    n_p1l: np.ndarray,
    d_p1l: np.ndarray,
    f_p1l: np.ndarray,
    n_p2: np.ndarray,
    d_p2: np.ndarray,
    f_p2: np.ndarray,
    n_p2l: np.ndarray,
    d_p2l: np.ndarray,
    f_p2l: np.ndarray,
    n_fn: np.ndarray,
    d_fn: np.ndarray,
    f_fn: np.ndarray,
    n_amb: np.ndarray,
    d_amb: np.ndarray,
    f_amb: np.ndarray,
    n_red: np.ndarray,
    d_red: np.ndarray,
    f_red: np.ndarray,
    cap: float,
    fee_day0_usd: float,
    fee_regular_usd: float,
    card_fx_fee_pct: float,
    withdrawal_fee_pct: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    max_dd_lim: float,
    min_days: int,
    profit_split: float,
    payout_cycle_days: int,
    min_payout_usd: float,
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    amber_dd: float,
    red_dd: float,
    p1_ea_stop: float,
    p2_ea_stop: float,
    fn_ea_stop: float,
    discount_rate_annual: float,
    max_retries: int,
):
    """FTMO 2-Step Standard single-ticket/retry lifecycle simulator (parity with `capital_optimizer/simulator.py`)."""
    n_paths, horizon = idx_matrix.shape
    eff_fee_day0 = fee_day0_usd * (1.0 + card_fx_fee_pct)
    eff_fee_reg = fee_regular_usd * (1.0 + card_fx_fee_pct)
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    daily_cap = cap * daily_lim
    static_floor = cap * (1.0 - max_dd_lim)
    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + discount_rate_annual) ** (-k_d / 252.0)

    eval_pass_day = np.full(n_paths, -1, dtype=np.int32)
    eval_fail_day = np.full(n_paths, -1, dtype=np.int32)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)
    funded_enter_day = np.full(n_paths, -1, dtype=np.int32)
    funded_breach_day = np.full(n_paths, -1, dtype=np.int32)
    bot_kill_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_any = np.zeros(n_paths, dtype=np.int8)
    npv_24m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    funded_months_total = np.zeros(n_paths, dtype=np.int32)
    funded_months_dry = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1
        bal = cap
        tdays = 0
        cycle_d = 0
        refunded = False
        attempts = 1
        first_ticket = True
        cur_ticket_fee = fee_day0_usd

        cum_npv = -eff_fee_day0
        cum_cf = -eff_fee_day0
        cum_fees = eff_fee_day0
        f_pass = -1
        f_fail = -1
        f_pay1 = -1
        f_fn_in = -1
        f_fn_br = -1
        b_kill = 0
        f_br = 0

        fn_m_days = 0
        fn_m_paid = 0
        tot_fm = 0
        dry_fm = 0
        rec_24 = False

        for d in range(horizon):
            if stage > 0:
                src = idx_matrix[b, d]
                eq_pct = (bal - cap) / cap
                if eq_pct <= -red_dd:
                    net, dd, flg = n_red[src], d_red[src], f_red[src]
                    ea_stop_pct = fn_ea_stop if stage == 3 else (p2_ea_stop if stage == 2 else p1_ea_stop)
                elif eq_pct <= -amber_dd:
                    net, dd, flg = n_amb[src], d_amb[src], f_amb[src]
                    ea_stop_pct = fn_ea_stop if stage == 3 else (p2_ea_stop if stage == 2 else p1_ea_stop)
                elif stage == 1:
                    prog = eq_pct / max(1e-6, p1_target)
                    if p1_lock_trigger > 0.0 and prog >= p1_lock_trigger:
                        net, dd, flg = n_p1l[src], d_p1l[src], f_p1l[src]
                    else:
                        net, dd, flg = n_p1[src], d_p1[src], f_p1[src]
                    ea_stop_pct = p1_ea_stop
                elif stage == 2:
                    prog = eq_pct / max(1e-6, p2_target)
                    if p2_lock_trigger > 0.0 and prog >= p2_lock_trigger:
                        net, dd, flg = n_p2l[src], d_p2l[src], f_p2l[src]
                    else:
                        net, dd, flg = n_p2[src], d_p2[src], f_p2[src]
                    ea_stop_pct = p2_ea_stop
                else:
                    net, dd, flg = n_fn[src], d_fn[src], f_fn[src]
                    ea_stop_pct = fn_ea_stop

                # Raw breach checked BEFORE EA stop clamp (Bug #1 fix preserved!)
                daily_floor = bal - daily_cap
                day_min = bal - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < static_floor - 1e-9

                ea_cut = cap * ea_stop_pct if ea_stop_pct > 0.0 else 1e18
                if (not d_hit) and (not m_hit) and (dd > ea_cut):
                    b_kill = 1
                    dd_eff = min(dd, ea_cut + cap * 0.0020)
                    net = min(net, -dd_eff)
                    day_min_eff = bal - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < static_floor - 1e-9

                if d_hit or m_hit:
                    f_br = 1
                    if first_ticket:
                        if stage < 3 and f_fail < 0:
                            f_fail = d + 1
                        elif stage == 3 and f_fn_br < 0:
                            f_fn_br = d + 1
                        first_ticket = False
                    if attempts <= max_retries:
                        attempts += 1
                        cur_ticket_fee = fee_regular_usd
                        cum_npv -= eff_fee_reg * inv_df[d]
                        cum_cf -= eff_fee_reg
                        cum_fees += eff_fee_reg
                        stage = 1
                        bal = cap
                        tdays = 0
                        cycle_d = 0
                        refunded = False
                    else:
                        stage = 0
                else:
                    bal += net
                    if flg != 0:
                        tdays += 1
                    if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
                        stage = 2
                        bal = cap
                        tdays = 0
                    elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
                        stage = 3
                        bal = cap
                        tdays = 0
                        cycle_d = 0
                        if f_pass < 0:
                            f_pass = d + 1
                        if first_ticket and f_fn_in < 0:
                            f_fn_in = d + 1
                    elif stage == 3:
                        cycle_d += 1
                        fn_m_days += 1
                        if cycle_d >= payout_cycle_days:
                            prof = bal - cap
                            if prof > 1e-6:
                                gross_share = prof * profit_split
                                if gross_share >= min_payout_usd - 1e-9:
                                    net_in = gross_share * (1.0 - withdrawal_fee_pct)
                                    if not refunded:
                                        net_in += cur_ticket_fee
                                        refunded = True
                                    cum_npv += net_in * inv_df[d + 1]
                                    cum_cf += net_in
                                    fn_m_paid = 1
                                    if f_pay1 < 0:
                                        f_pay1 = d + 1
                                    bal = cap
                            cycle_d = 0
                        if fn_m_days >= 21:
                            tot_fm += 1
                            if fn_m_paid == 0:
                                dry_fm += 1
                            fn_m_days = 0
                            fn_m_paid = 0

            if (not rec_24) and (d + 1 == 504):
                npv_24m[b] = cum_npv
                cf_24m[b] = cum_cf
                fees_24m[b] = cum_fees
                rec_24 = True

        if not rec_24:
            npv_24m[b] = cum_npv
            cf_24m[b] = cum_cf
            fees_24m[b] = cum_fees
        eval_pass_day[b] = f_pass
        eval_fail_day[b] = f_fail
        pay1_day[b] = f_pay1
        funded_enter_day[b] = f_fn_in
        funded_breach_day[b] = f_fn_br
        bot_kill_any[b] = b_kill
        firm_breach_any[b] = f_br
        funded_months_total[b] = tot_fm
        funded_months_dry[b] = dry_fm

    return (
        eval_pass_day,
        eval_fail_day,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        npv_24m,
        cf_24m,
        fees_24m,
        funded_months_total,
        funded_months_dry,
    )


def wilson_upper_95(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return min(1.0, (center + margin) / denom)


def summarize_mc_raw(
    raw: tuple[np.ndarray, ...],
    *,
    fee_day0_usd: float,
    card_fx_fee_pct: float,
    usd_vnd_rate: float,
    horizon_days: int = 756,
) -> dict[str, Any]:
    """Summarize Law-13/15 single-ticket MC arrays with strict `Pass + Fail + Pending == 100.00%`."""
    (
        eval_pass_day,
        eval_fail_day,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        npv_24m,
        cf_24m,
        fees_24m,
        fn_m_tot,
        fn_m_dry,
    ) = raw
    n = len(eval_pass_day)
    if n < 1:
        raise ValueError("INVALID_MC_PATHS: summarize_mc_raw requires n_paths >= 1")
    eff_fee = float(fee_day0_usd) * (1.0 + float(card_fx_fee_pct))

    monthly: dict[str, dict[str, float]] = {}
    monthly_counts: dict[str, dict[str, int]] = {}
    for m in (3, 6, 12, 24):
        cutoff = m * TRADING_DAYS_PER_MONTH
        passed = (eval_pass_day >= 0) & (eval_pass_day <= cutoff)
        failed = (~passed) & (eval_fail_day > 0) & (eval_fail_day <= cutoff)
        pending = (~passed) & (~failed)
        c_pass = int(np.sum(passed))
        c_fail = int(np.sum(failed))
        c_pend = int(np.sum(pending))
        p_pct = 100.0 * float(c_pass) / n
        f_pct = 100.0 * float(c_fail) / n
        w_pct = 100.0 * float(c_pend) / n
        if abs((p_pct + f_pct + w_pct) - 100.0) >= 1e-6:
            raise ValueError(f"Monthly Pass+Fail+Pending != 100%: {p_pct + f_pct + w_pct}")
        monthly_counts[f"{m}m"] = {"pass": c_pass, "fail": c_fail, "pending": c_pend}
        monthly[f"{m}m"] = {
            "pass_pct": round(p_pct, 2),
            "fail_pct": round(f_pct, 2),
            "pending_pct": round(w_pct, 2),
            "sum_pct": round(p_pct + f_pct + w_pct, 2),
        }

    cal_pay1 = np.where(pay1_day > 0, pay1_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    uncond_cap730 = np.minimum(cal_pay1, 730.0)
    paid_mask = pay1_day > 0

    fn_mask = funded_enter_day >= 0
    n_fn = int(np.sum(fn_mask))
    if n_fn > 0:
        fn_in = funded_enter_day[fn_mask]
        fn_br = funded_breach_day[fn_mask]
        br_12m = (fn_br > 0) & ((fn_br - fn_in) <= TRADING_DAYS_PER_YEAR)
        n_br_12m = int(np.sum(br_12m))
        fn_br_pct = 100.0 * n_br_12m / n_fn
        wilson_ub_pct = 100.0 * wilson_upper_95(n_br_12m, n_fn)
        n_cens = int(np.sum((fn_in + TRADING_DAYS_PER_YEAR) > horizon_days))
    else:
        n_br_12m = 0
        fn_br_pct = 0.0
        wilson_ub_pct = 100.0
        n_cens = 0

    tot_fm = int(np.sum(fn_m_tot))
    dry_fm = int(np.sum(fn_m_dry))
    dry_pct = (100.0 * dry_fm / tot_fm) if tot_fm > 0 else 100.0
    ev_npv24 = float(np.mean(npv_24m))
    med_npv24 = float(np.median(npv_24m))
    ev_cf24 = float(np.mean(cf_24m))

    return {
        "model_tag": "DAILY_APPROX",
        "n_paths": n,
        "effective_fee_usd": round(eff_fee, 2),
        "effective_fee_vnd_tr": round(eff_fee * usd_vnd_rate / 1_000_000.0, 2),
        "monthly_pass_fail_pending": monthly,
        "pass_24m_pct": monthly["24m"]["pass_pct"],
        "fail_24m_pct": monthly["24m"]["fail_pct"],
        "pending_24m_pct": monthly["24m"]["pending_pct"],
        "ev_npv_24m_usd": round(ev_npv24, 2),
        "ev_npv_24m_vnd_tr": round(ev_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_24m_usd": round(med_npv24, 2),
        "med_npv_24m_vnd_tr": round(med_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_24m_usd": round(ev_cf24, 2),
        "ev_per_fee_npv24": round(ev_npv24 / max(1.0, eff_fee), 2),
        "p_npv24_le_0_pct": round(100.0 * float(np.mean(npv_24m <= 0.0)), 2),
        "cond_med_pay1_cal_days": round(float(np.median(cal_pay1[paid_mask])), 1) if np.any(paid_mask) else -1.0,
        "uncond_med_pay1_cap730_days": round(float(np.median(uncond_cap730)), 1),
        "funded_12m_breach_pct": round(fn_br_pct, 2),
        "funded_12m_wilson_ub_pct": round(wilson_ub_pct, 2),
        "funded_entered_count": n_fn,
        "funded_breach_12m_count": n_br_12m,
        "funded_censored_count": n_cens,
        "funded_dry_months_pct": round(dry_pct, 2),
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_any > 0)), 2),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_any > 0)), 2),
        # Sufficient exact raw counts/sums so X13 shards can merge losslessly without re-running MC!
        "_shard_accum": {
            "n_paths": n,
            "effective_fee_usd_exact": eff_fee,
            "monthly_counts": monthly_counts,
            "sum_npv_24m": float(np.sum(npv_24m)),
            "sum_cf_24m": float(np.sum(cf_24m)),
            "sum_fees_24m": float(np.sum(fees_24m)),
            "cnt_npv24_le_0": int(np.sum(npv_24m <= 0.0)),
            "cnt_bot_kill": int(np.sum(bot_kill_any > 0)),
            "cnt_firm_breach": int(np.sum(firm_breach_any > 0)),
            "fn_entered": n_fn,
            "fn_br_12m": n_br_12m,
            "fn_censored": n_cens,
            "fn_m_tot": tot_fm,
            "fn_m_dry": dry_fm,
        },
    }


def _is_exact_int(val: Any) -> TypeGuard[int]:
    return isinstance(val, int) and not isinstance(val, bool)


def merge_shard_summaries(shards: list[dict[str, Any]], *, usd_vnd_rate: float | None = None) -> dict[str, Any]:
    """Fail-closed exact merge of independent X13/Dev MC shard JSON payloads into full Law-15 output."""
    if not shards:
        raise ValueError("SHARD_MERGE_ERROR: cannot merge empty shard list")

    base = shards[0]
    base_sha = str(base.get("frozen_tapes_npz_sha256") or "")
    if len(base_sha) != 64:
        raise ValueError(f"SHARD_MERGE_ERROR: invalid frozen_tapes_npz_sha256={base_sha!r}")
    base_dev_window = str(base.get("dev_window") or "")
    if not base_dev_window or "2025" in base_dev_window or "2026" in base_dev_window:
        raise ValueError(f"SHARD_MERGE_ERROR: invalid dev_window={base_dev_window!r}")
    base_fx = float(base.get("usd_vnd_rate") or 0.0)
    if base_fx <= 0.0:
        raise ValueError(f"SHARD_MERGE_ERROR: missing/invalid usd_vnd_rate={base_fx}")
    if usd_vnd_rate is not None and abs(float(usd_vnd_rate) - base_fx) > 1e-6:
        raise ValueError(f"SHARD_MERGE_ERROR: caller usd_vnd_rate={usd_vnd_rate} != shard usd_vnd_rate={base_fx}")
    eff_fx = base_fx

    if "spread_guard_active" not in base or not isinstance(base["spread_guard_active"], bool):
        raise ValueError("SHARD_MERGE_ERROR: missing boolean spread_guard_active in shard[0]")
    base_sg_active = bool(base["spread_guard_active"])

    base_shard_meta = base.get("shard") or {}
    expected_total = base_shard_meta.get("shard_total")
    if not _is_exact_int(expected_total) or expected_total < 1:
        raise ValueError(f"SHARD_MERGE_ERROR: invalid shard_total={expected_total!r}")

    seen_indices: set[int] = set()
    base_sids = list(base.get("scenarios", {}).keys())
    if not base_sids:
        raise ValueError("SHARD_MERGE_ERROR: empty scenarios in shard[0]")

    for pos, sh in enumerate(shards):
        hr = sh.get("holdout_rows_analysed")
        osc = sh.get("order_send_count")
        if not _is_exact_int(hr) or hr != 0:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: shard[{pos}] holdout_rows_analysed={hr!r} != 0")
        if not _is_exact_int(osc) or osc != 0:
            raise ValueError(f"ORDER_SEND_VIOLATION: shard[{pos}] order_send_count={osc!r} != 0")
        if str(sh.get("frozen_tapes_npz_sha256") or "") != base_sha:
            raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] frozen_tapes_npz_sha256 mismatch")
        if str(sh.get("dev_window") or "") != base_dev_window:
            raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] dev_window mismatch")
        sh_fx = float(sh.get("usd_vnd_rate") or 0.0)
        if abs(sh_fx - eff_fx) > 1e-6:
            raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] usd_vnd_rate={sh_fx} != {eff_fx}")
        if not isinstance(sh.get("spread_guard_active"), bool) or sh["spread_guard_active"] != base_sg_active:
            raise ValueError(
                f"SHARD_MERGE_ERROR: shard[{pos}] spread_guard_active={sh.get('spread_guard_active')!r} "
                f"!= {base_sg_active!r}"
            )
        sm = sh.get("shard") or {}
        st = sm.get("shard_total")
        si = sm.get("shard_index")
        if not _is_exact_int(st) or st != expected_total:
            raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] shard_total={st!r} != {expected_total}")
        if not _is_exact_int(si) or not (0 <= si < expected_total):
            raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] invalid shard_index={si!r}")
        if si in seen_indices:
            raise ValueError(f"SHARD_MERGE_ERROR: duplicate shard_index={si}")
        seen_indices.add(si)
        if list(sh.get("scenarios", {}).keys()) != base_sids:
            raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] scenario key set mismatch")

    out_scenarios: dict[str, Any] = {}
    total_paths_merged = 0
    for sid in base_sids:
        s0 = base["scenarios"][sid]
        mc_keys = list(s0["ftmo_std_10k_mc"].keys())
        merged_mc: dict[str, Any] = {}
        for k in mc_keys:
            tot_n = 0
            sum_npv = 0.0
            sum_cf = 0.0
            sum_fees = 0.0
            cnt_le0 = 0
            cnt_bot_kill = 0
            cnt_firm_br = 0
            fn_en = 0
            fn_br = 0
            fn_cens = 0
            fm_tot = 0
            fm_dry = 0
            m_counts: dict[str, dict[str, int]] = {
                f"{m}m": {"pass": 0, "fail": 0, "pending": 0} for m in (3, 6, 12, 24)
            }
            eff_fee_exact: float | None = None

            for pos, sh in enumerate(shards):
                sc_mc = sh["scenarios"][sid]["ftmo_std_10k_mc"]
                if k not in sc_mc:
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] missing MC key {sid}.{k}")
                acc = sc_mc[k].get("_shard_accum")
                if not isinstance(acc, dict):
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] missing _shard_accum for {sid}.{k}")
                sh_n = acc.get("n_paths")
                if not _is_exact_int(sh_n) or sh_n <= 0:
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] invalid n_paths={sh_n!r} for {sid}.{k}")
                raw_fee = acc.get("effective_fee_usd_exact", sc_mc[k]["effective_fee_usd"])
                if isinstance(raw_fee, bool):
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] invalid effective_fee_usd={raw_fee!r}")
                sh_fee = float(raw_fee)
                if not math.isfinite(sh_fee) or sh_fee < 0.0:
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] non-finite effective_fee_usd={raw_fee!r}")
                if eff_fee_exact is None:
                    eff_fee_exact = sh_fee
                elif abs(sh_fee - eff_fee_exact) > 1e-6:
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] effective_fee_usd={sh_fee} != {eff_fee_exact}")
                raw_sum_npv = acc["sum_npv_24m"]
                raw_sum_cf = acc["sum_cf_24m"]
                raw_sum_fees = acc.get("sum_fees_24m", 0.0)
                if isinstance(raw_sum_npv, bool) or not math.isfinite(float(raw_sum_npv)):
                    raise ValueError(
                        f"SHARD_MERGE_ERROR: shard[{pos}] non-finite sum_npv_24m={raw_sum_npv!r} for {sid}.{k}"
                    )
                if isinstance(raw_sum_cf, bool) or not math.isfinite(float(raw_sum_cf)):
                    raise ValueError(
                        f"SHARD_MERGE_ERROR: shard[{pos}] non-finite sum_cf_24m={raw_sum_cf!r} for {sid}.{k}"
                    )
                if isinstance(raw_sum_fees, bool) or not math.isfinite(float(raw_sum_fees)):
                    raise ValueError(
                        f"SHARD_MERGE_ERROR: shard[{pos}] non-finite sum_fees_24m={raw_sum_fees!r} for {sid}.{k}"
                    )
                tot_n += sh_n
                sum_npv += float(raw_sum_npv)
                sum_cf += float(raw_sum_cf)
                sum_fees += float(raw_sum_fees)
                cnt_le0 += int(acc["cnt_npv24_le_0"])
                cnt_bot_kill += int(acc["cnt_bot_kill"])
                cnt_firm_br += int(acc["cnt_firm_breach"])
                fn_en += int(acc["fn_entered"])
                fn_br += int(acc["fn_br_12m"])
                fn_cens += int(acc["fn_censored"])
                fm_tot += int(acc["fn_m_tot"])
                fm_dry += int(acc["fn_m_dry"])
                sh_mc = acc.get("monthly_counts")
                if not isinstance(sh_mc, dict):
                    raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] missing monthly_counts for {sid}.{k}")
                for m in (3, 6, 12, 24):
                    mk = f"{m}m"
                    mc_row = sh_mc.get(mk)
                    if not isinstance(mc_row, dict):
                        raise ValueError(f"SHARD_MERGE_ERROR: shard[{pos}] missing monthly_counts[{mk}]")
                    cp = int(mc_row["pass"])
                    cf = int(mc_row["fail"])
                    cw = int(mc_row["pending"])
                    if cp + cf + cw != sh_n:
                        raise ValueError(
                            f"SHARD_MERGE_ERROR: shard[{pos}] {sid}.{k}.{mk} counts {cp}+{cf}+{cw} != {sh_n}"
                        )
                    m_counts[mk]["pass"] += cp
                    m_counts[mk]["fail"] += cf
                    m_counts[mk]["pending"] += cw

            if tot_n <= 0 or eff_fee_exact is None:
                raise ValueError(f"SHARD_MERGE_ERROR: zero merged paths for {sid}.{k}")
            if total_paths_merged == 0:
                total_paths_merged = tot_n

            monthly: dict[str, dict[str, float]] = {}
            for m in (3, 6, 12, 24):
                mk = f"{m}m"
                p_pct = 100.0 * float(m_counts[mk]["pass"]) / tot_n
                f_pct = 100.0 * float(m_counts[mk]["fail"]) / tot_n
                w_pct = 100.0 * float(m_counts[mk]["pending"]) / tot_n
                if abs((p_pct + f_pct + w_pct) - 100.0) >= 1e-6:
                    raise ValueError(f"Merged Monthly Pass+Fail+Pending != 100%: {p_pct + f_pct + w_pct}")
                monthly[mk] = {
                    "pass_pct": round(p_pct, 2),
                    "fail_pct": round(f_pct, 2),
                    "pending_pct": round(w_pct, 2),
                    "sum_pct": round(p_pct + f_pct + w_pct, 2),
                }

            ev_npv = sum_npv / tot_n
            ev_cf = sum_cf / tot_n
            merged_mc[k] = {
                "model_tag": "DAILY_APPROX",
                "n_paths": tot_n,
                "effective_fee_usd": round(eff_fee_exact, 2),
                "effective_fee_vnd_tr": round(eff_fee_exact * eff_fx / 1_000_000.0, 2),
                "monthly_pass_fail_pending": monthly,
                "pass_24m_pct": monthly["24m"]["pass_pct"],
                "fail_24m_pct": monthly["24m"]["fail_pct"],
                "pending_24m_pct": monthly["24m"]["pending_pct"],
                "ev_npv_24m_usd": round(ev_npv, 2),
                "ev_npv_24m_vnd_tr": round(ev_npv * eff_fx / 1_000_000.0, 2),
                "ev_undisc_24m_usd": round(ev_cf, 2),
                "ev_per_fee_npv24": round(ev_npv / max(1.0, eff_fee_exact), 2),
                "p_npv24_le_0_pct": round(100.0 * cnt_le0 / tot_n, 2),
                "funded_12m_breach_pct": round(100.0 * fn_br / fn_en, 2) if fn_en > 0 else 0.0,
                "funded_12m_wilson_ub_pct": round(100.0 * wilson_upper_95(fn_br, fn_en), 2) if fn_en > 0 else 100.0,
                "funded_entered_count": fn_en,
                "funded_breach_12m_count": fn_br,
                "funded_censored_count": fn_cens,
                "funded_dry_months_pct": round(100.0 * fm_dry / fm_tot, 2) if fm_tot > 0 else 100.0,
                "bot_auto_kill_pct": round(100.0 * cnt_bot_kill / tot_n, 2),
                "firm_hard_breach_pct": round(100.0 * cnt_firm_br / tot_n, 2),
                "_shard_accum": {
                    "n_paths": tot_n,
                    "effective_fee_usd_exact": eff_fee_exact,
                    "monthly_counts": m_counts,
                    "sum_npv_24m": sum_npv,
                    "sum_cf_24m": sum_cf,
                    "sum_fees_24m": sum_fees,
                    "cnt_npv24_le_0": cnt_le0,
                    "cnt_bot_kill": cnt_bot_kill,
                    "cnt_firm_breach": cnt_firm_br,
                    "fn_entered": fn_en,
                    "fn_br_12m": fn_br,
                    "fn_censored": fn_cens,
                    "fn_m_tot": fm_tot,
                    "fn_m_dry": fm_dry,
                },
            }
        out_scenarios[sid] = {
            **{k: v for k, v in s0.items() if k != "ftmo_std_10k_mc"},
            "ftmo_std_10k_mc": merged_mc,
        }

    shield_c_ids = [
        sid
        for sid, obj in out_scenarios.items()
        if obj["config"]["group"] == "Shield_C" and obj["all_profiles_le_4_50_pct"]
    ]
    winner_id = (
        max(
            shield_c_ids,
            key=lambda sid: (
                out_scenarios[sid]["ftmo_std_10k_mc"]["bf_1_00x"]["ev_npv_24m_usd"],
                -out_scenarios[sid]["worst_gap_125x_pct"],
            ),
        )
        if shield_c_ids
        else ""
    )

    return {
        "schema": "naqex-flashcrash-pareto-merged-v1",
        "dev_window": base_dev_window,
        "frozen_tapes_npz_sha256": base_sha,
        "usd_vnd_rate": eff_fx,
        "spread_guard_active": base_sg_active,
        "shards_merged": len(shards),
        "shard_total": expected_total,
        "shard_indices_merged": sorted(seen_indices),
        "total_paths_merged": total_paths_merged,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "winner_shield_c_id": winner_id,
        "scenarios": out_scenarios,
    }


def build_defense_scenarios() -> list[dict[str, Any]]:
    """Pre-registered Shield A / B / C Pareto matrix comparing against `C10_NEWS_ON` baseline."""
    return [
        # Baseline: C10_NEWS_ON (224 USD ±5m, SYMCAP only, unclamped total open risk)
        {
            "id": "BASELINE_C10_NEWS_ON",
            "group": "Baseline",
            "label": "C10_NEWS_ON (SYMCAP only, 224 USD ±5m, SpreadGuard OFF)",
            "calendar": "224_USD",
            "news_pad_sec": 300,
            "spread_preset": "OFF",
            "total_open_p1p2_pct": None,
            "total_open_funded_pct": None,
            "use_clusters": False,
        },
        # Shield A: Total simultaneous open-account risk cap sweep (2.00% / 2.50% / 3.00%)
        {
            "id": "SHIELD_A_TOT300",
            "group": "Shield_A",
            "label": "Shield A: TotalOpenCap 3.00% P1/P2 (2.25% Funded)",
            "calendar": "224_USD",
            "news_pad_sec": 300,
            "spread_preset": "OFF",
            "total_open_p1p2_pct": 3.00,
            "total_open_funded_pct": 2.25,
            "use_clusters": False,
        },
        {
            "id": "SHIELD_A_TOT250",
            "group": "Shield_A",
            "label": "Shield A: TotalOpenCap 2.50% P1/P2 (2.00% Funded)",
            "calendar": "224_USD",
            "news_pad_sec": 300,
            "spread_preset": "OFF",
            "total_open_p1p2_pct": 2.50,
            "total_open_funded_pct": 2.00,
            "use_clusters": False,
        },
        {
            "id": "SHIELD_A_TOT200",
            "group": "Shield_A",
            "label": "Shield A: TotalOpenCap 2.00% P1/P2 (1.75% Funded)",
            "calendar": "224_USD",
            "news_pad_sec": 300,
            "spread_preset": "OFF",
            "total_open_p1p2_pct": 2.00,
            "total_open_funded_pct": 1.75,
            "use_clusters": False,
        },
        # Shield B: Directional clusters (USD/JPY/US100) + real M1 SpreadGuard + 6-CCY 523-event (±5m vs ±10m)
        {
            "id": "SHIELD_B_6CCY_5M",
            "group": "Shield_B",
            "label": "Shield B: Clusters + M1 SpreadGuard + 6-CCY 523 ±5m",
            "calendar": "523_6CCY",
            "news_pad_sec": 300,
            "spread_preset": "CALIB_M1_A",
            "total_open_p1p2_pct": None,
            "total_open_funded_pct": None,
            "use_clusters": True,
        },
        {
            "id": "SHIELD_B_6CCY_10M",
            "group": "Shield_B",
            "label": "Shield B: Clusters + M1 SpreadGuard + 6-CCY 523 ±10m",
            "calendar": "523_6CCY",
            "news_pad_sec": 600,
            "spread_preset": "CALIB_M1_A",
            "total_open_p1p2_pct": None,
            "total_open_funded_pct": None,
            "use_clusters": True,
        },
        # Shield C: Combined A + B targeting worst 1.25x gap shock <= 4.50% across ALL 4 profiles
        {
            "id": "SHIELD_C_TOT300_5M",
            "group": "Shield_C",
            "label": "Shield C: TotalCap 3.00% + Clusters + M1 SpreadGuard + 6-CCY ±5m",
            "calendar": "523_6CCY",
            "news_pad_sec": 300,
            "spread_preset": "CALIB_M1_A",
            "total_open_p1p2_pct": 3.00,
            "total_open_funded_pct": 2.25,
            "use_clusters": True,
        },
        {
            "id": "SHIELD_C_TOT300_10M",
            "group": "Shield_C",
            "label": "Shield C: TotalCap 3.00% + Clusters + M1 SpreadGuard + 6-CCY ±10m",
            "calendar": "523_6CCY",
            "news_pad_sec": 600,
            "spread_preset": "CALIB_M1_A",
            "total_open_p1p2_pct": 3.00,
            "total_open_funded_pct": 2.25,
            "use_clusters": True,
        },
        {
            "id": "SHIELD_C_TOT250_10M",
            "group": "Shield_C",
            "label": "Shield C: TotalCap 2.50% + Clusters + M1 SpreadGuard + 6-CCY ±10m",
            "calendar": "523_6CCY",
            "news_pad_sec": 600,
            "spread_preset": "CALIB_M1_A",
            "total_open_p1p2_pct": 2.50,
            "total_open_funded_pct": 2.00,
            "use_clusters": True,
        },
        {
            "id": "SHIELD_C_TOT200_10M",
            "group": "Shield_C",
            "label": "Shield C: TotalCap 2.00% + Clusters + M1 SpreadGuard + 6-CCY ±10m",
            "calendar": "523_6CCY",
            "news_pad_sec": 600,
            "spread_preset": "CALIB_M1_A",
            "total_open_p1p2_pct": 2.00,
            "total_open_funded_pct": 1.75,
            "use_clusters": True,
        },
    ]


def compute_exact_breakeven_friction(
    ext_days: list[str],
    raw_tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    red_news_cal: dict[str, list[tuple[int, str, int]]],
    news_pad_sec: int,
    spread_caps_pts: dict[str, float] | None,
    entry_spread_pts: dict[tuple[str, str], float] | None,
    total_open_cap_pct: float | None,
    usd_cap: float | None,
    jpy_cap: float | None,
    idx_cap: float | None,
) -> dict[str, Any]:
    """Compute exact portfolio break-even friction multiple via 100K 1.0x Funded replay sweep."""
    sweep_mults = (0.66, 1.00, 1.25, 1.50, 1.75, 2.00, 2.50)
    curve: list[dict[str, Any]] = []
    net_1x = 0.0
    net_2x = 0.0
    for cm in sweep_mults:
        st_tapes = apply_cost_stress_to_tapes(raw_tapes, cm)
        guarded, _ = apply_red_news_and_spread_guard(
            st_tapes,
            red_news_cal=red_news_cal,
            news_pad_sec=news_pad_sec,
            spread_caps_pts=spread_caps_pts,
            entry_spread_pts=entry_spread_pts,
        )
        pre = prealign_days_for_tapes(ext_days, guarded)
        met, _, _, _, _ = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=100_000.0,
            mult=1.00,
            symcap_pct=1.00,
            profile_mode="Standard",
            total_open_cap_pct=total_open_cap_pct,
            usd_cluster_cap_pct=usd_cap,
            jpy_cluster_cap_pct=jpy_cap,
            idx_cluster_cap_pct=idx_cap,
        )
        curve.append(
            {
                "friction_mult": cm,
                "net_usd": met["net_usd"],
                "ann_pct": met["ann_pct"],
                "winrate_pct": met["winrate_pct"],
                "avg_rr": met["avg_rr"],
                "ev_per_trade_r": met["ev_per_trade_r"],
                "profit_factor": met["profit_factor"],
                "peak_dd_pct": met["peak_dd_pct"],
                "calmar": met["calmar"],
                "sharpe": met["sharpe"],
            }
        )
        if abs(cm - 1.00) < 1e-9:
            net_1x = float(met["net_usd"])
        elif abs(cm - 2.00) < 1e-9:
            net_2x = float(met["net_usd"])

    # Bisect exact breakeven friction multiple between 1.00x and 4.00x
    slope = net_1x - net_2x
    k_est = (1.0 + net_1x / slope) if slope > 1e-6 else 0.0
    lo, hi = 1.0, max(3.5, k_est + 0.5)
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        st_m = apply_cost_stress_to_tapes(raw_tapes, mid)
        g_m, _ = apply_red_news_and_spread_guard(
            st_m,
            red_news_cal=red_news_cal,
            news_pad_sec=news_pad_sec,
            spread_caps_pts=spread_caps_pts,
            entry_spread_pts=entry_spread_pts,
        )
        p_m = prealign_days_for_tapes(ext_days, g_m)
        m_mid, _, _, _, _ = replay_shielded_stage(
            ext_days,
            p_m,
            capital_usd=100_000.0,
            mult=1.00,
            symcap_pct=1.00,
            profile_mode="Standard",
            total_open_cap_pct=total_open_cap_pct,
            usd_cluster_cap_pct=usd_cap,
            jpy_cluster_cap_pct=jpy_cap,
            idx_cluster_cap_pct=idx_cap,
        )
        if m_mid["net_usd"] > 0.0:
            lo = mid
        else:
            hi = mid
    return {
        "breakeven_friction_mult": round(0.5 * (lo + hi), 2),
        "curve": curve,
    }


def run_pareto_study(
    *,
    derived_dir: Path = DEFAULT_DERIVED_DIR,
    m1_cache_dir: Path = DEFAULT_M1_CACHE_DIR,
    cal_224_path: Path = DEFAULT_CAL_224_PATH,
    cal_523_path: Path = DEFAULT_CAL_523_PATH,
    fx_rates_path: Path = DEFAULT_FX_RATES_PATH,
    firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
    n_paths: int = 10_000,
    seed: int = DEFAULT_SEED,
    shard_index: int = 0,
    shard_total: int = 1,
    skip_m1_spread_scan: bool = False,
    include_breakeven: bool = True,
) -> dict[str, Any]:
    """Execute the full Flash-Crash Defense Pareto Study (Shield A/B/C vs C10_NEWS_ON baseline)."""
    if (
        not _is_exact_int(shard_total)
        or not _is_exact_int(shard_index)
        or shard_total < 1
        or not (0 <= shard_index < shard_total)
    ):
        raise ValueError(f"Invalid shard arguments: index={shard_index!r}, total={shard_total!r}")
    if not _is_exact_int(n_paths) or n_paths < 1 or n_paths < shard_total:
        raise ValueError(
            f"INVALID_SHARD_PATHS: n_paths={n_paths!r} must be >= shard_total={shard_total} (>= 1 path/shard)"
        )

    # Shard MC path count deterministically (guaranteed >= 1)
    base_n = n_paths // shard_total
    rem_n = n_paths % shard_total
    shard_n_paths = base_n + (1 if shard_index < rem_n else 0)
    if shard_n_paths < 1:
        raise ValueError(f"INVALID_SHARD_PATHS: shard {shard_index}/{shard_total} assigned 0 paths")

    t0 = time.perf_counter()
    data = load_frozen_tapes_direct(derived_dir=derived_dir)
    ext_days: list[str] = data["ext_days"]
    raw_tapes = data["tapes"]

    fx_doc = json.loads(fx_rates_path.read_text(encoding="utf-8"))
    usd_vnd = float(fx_doc["usd_vnd"])
    firms_doc = json.loads(firms_catalog_path.read_text(encoding="utf-8"))
    c10k = firms_doc["contracts"]["ftmo_standard_10k"]
    c100k = firms_doc["contracts"]["ftmo_standard_100k"]
    card_fx = float(c10k["card_fx_fee_frac"])
    wd_fee = float(c10k["withdrawal_fee_frac"])

    cal_224 = load_red_news_calendar_rich(cal_224_path)
    cal_523 = load_red_news_calendar_rich(cal_523_path)

    spread_calib: dict[str, Any]
    if skip_m1_spread_scan:
        spread_calib = {
            "available": False,
            "reason": "skipped_by_flag",
            "calibration_rule": SPREAD_GUARD_CALIBRATION_RULE,
            "calibrated_dev_caps_a": {},
            "symbols": {},
            "entry_spread_pts": {},
        }
    else:
        spread_calib = calibrate_m1_spread_guard(raw_tapes, m1_cache_dir=m1_cache_dir)
    raw_ep = spread_calib.get("entry_spread_pts")
    entry_spread_pts: dict[tuple[str, str], float] | None = raw_ep if isinstance(raw_ep, dict) and raw_ep else None
    raw_caps_a = spread_calib.get("calibrated_dev_caps_a")
    calibrated_dev_caps_a: dict[str, float] | None = (
        {str(k): float(v) for k, v in raw_caps_a.items()} if isinstance(raw_caps_a, dict) and raw_caps_a else None
    )
    spread_guard_active = bool(
        spread_calib.get("available") and entry_spread_pts is not None and calibrated_dev_caps_a is not None
    )

    def _resolve_spread_caps(spread_preset: str) -> dict[str, float] | None:
        if spread_preset == "OFF" or not spread_guard_active:
            return None
        if spread_preset == "CALIB_M1_A":
            return calibrated_dev_caps_a
        return SPREAD_GUARD_PRESETS_DEV_PTS[spread_preset]

    shard_seed = int(seed) + int(shard_index) * 1009
    idx_matrix = make_block_bootstrap_indices(
        len(ext_days), horizon=756, n_paths=shard_n_paths, block_len=BLOCK_LEN, seed=shard_seed
    )

    # Pre-cache prealigned days per (friction, calendar, news_pad_sec, spread_preset)
    pre_cache: dict[tuple[float, str, int, str], tuple[list[dict[str, Any]], dict[str, Any]]] = {}

    def _get_pre(friction: float, cal_key: str, pad_sec: int, spread_preset: str):
        ck = (round(friction, 4), cal_key, int(pad_sec), spread_preset)
        if ck in pre_cache:
            return pre_cache[ck]
        st = apply_cost_stress_to_tapes(raw_tapes, friction)
        cal_obj = cal_523 if cal_key == "523_6CCY" else cal_224
        scaps = _resolve_spread_caps(spread_preset)
        guarded, gstats = apply_red_news_and_spread_guard(
            st,
            red_news_cal=cal_obj,
            news_pad_sec=pad_sec,
            spread_caps_pts=scaps,
            entry_spread_pts=entry_spread_pts,
        )
        pre = prealign_days_for_tapes(ext_days, guarded)
        pre_cache[ck] = (pre, gstats)
        return pre, gstats

    def _eval_ftmo_mc(
        pre: list[dict[str, Any]],
        *,
        contract: dict[str, Any],
        fee_day0_usd: float,
        max_retries: int,
        tot_p1p2: float | None,
        tot_fn: float | None,
        use_clusters: bool,
    ) -> dict[str, Any]:
        cap = float(contract["capital_usd"])
        u_p12, j_p12, i_p12 = (2.25, 2.00, 1.75) if use_clusters else (None, None, None)
        u_fn, j_fn, i_fn = (1.75, 1.50, 1.25) if use_clusters else (None, None, None)
        _, n_p1, d_p1, _, f_p1 = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=4.00,
            symcap_pct=1.75,
            total_open_cap_pct=tot_p12,
            usd_cluster_cap_pct=u_p12,
            jpy_cluster_cap_pct=j_p12,
            idx_cluster_cap_pct=i_p12,
        )
        _, n_p1l, d_p1l, _, f_p1l = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=2.50,
            symcap_pct=1.75,
            total_open_cap_pct=tot_p12,
            usd_cluster_cap_pct=u_p12,
            jpy_cluster_cap_pct=j_p12,
            idx_cluster_cap_pct=i_p12,
        )
        _, n_p2, d_p2, _, f_p2 = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=3.50,
            symcap_pct=1.75,
            total_open_cap_pct=tot_p12,
            usd_cluster_cap_pct=u_p12,
            jpy_cluster_cap_pct=j_p12,
            idx_cluster_cap_pct=i_p12,
        )
        _, n_p2l, d_p2l, _, f_p2l = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=1.75,
            symcap_pct=1.75,
            total_open_cap_pct=tot_p12,
            usd_cluster_cap_pct=u_p12,
            jpy_cluster_cap_pct=j_p12,
            idx_cluster_cap_pct=i_p12,
        )
        _, n_fn, d_fn, _, f_fn = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=1.25,
            symcap_pct=1.25,
            total_open_cap_pct=tot_fn,
            usd_cluster_cap_pct=u_fn,
            jpy_cluster_cap_pct=j_fn,
            idx_cluster_cap_pct=i_fn,
        )
        _, n_amb, d_amb, _, f_amb = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=0.65,
            symcap_pct=1.25,
            total_open_cap_pct=tot_fn,
            usd_cluster_cap_pct=u_fn,
            jpy_cluster_cap_pct=j_fn,
            idx_cluster_cap_pct=i_fn,
        )
        _, n_red, d_red, _, f_red = replay_shielded_stage(
            ext_days,
            pre,
            capital_usd=cap,
            mult=0.40,
            symcap_pct=1.25,
            total_open_cap_pct=tot_fn,
            usd_cluster_cap_pct=u_fn,
            jpy_cluster_cap_pct=j_fn,
            idx_cluster_cap_pct=i_fn,
        )
        raw = _simulate_ftmo_std_single_ticket_numba(
            idx_matrix,
            n_p1,
            d_p1,
            f_p1,
            n_p1l,
            d_p1l,
            f_p1l,
            n_p2,
            d_p2,
            f_p2,
            n_p2l,
            d_p2l,
            f_p2l,
            n_fn,
            d_fn,
            f_fn,
            n_amb,
            d_amb,
            f_amb,
            n_red,
            d_red,
            f_red,
            cap,
            float(fee_day0_usd),
            float(contract["fee_orig_usd"]),
            card_fx,
            wd_fee,
            float(contract["p1_target_frac"]),
            float(contract["p2_target_frac"]),
            float(contract["daily_loss_limit_frac"]),
            float(contract["static_loss_limit_frac"]),
            int(contract["min_trading_days"]),
            float(contract["payout_split_frac"]),
            10,  # 14 calendar days ~ 10 trading days (exact match to capital_optimizer)
            float(contract["min_payout_usd"]),
            float(C10_PHASE_BASE["p1_lock_trigger"]),
            float(C10_PHASE_BASE["p2_lock_trigger"]),
            float(C10_PHASE_BASE["amber_dd"]),
            float(C10_PHASE_BASE["red_dd"]),
            float(C10_PHASE_BASE["p1_ea_daily_stop"]),
            float(C10_PHASE_BASE["p2_ea_daily_stop"]),
            float(C10_PHASE_BASE["funded_ea_daily_stop"]),
            0.06,
            int(max_retries),
        )
        return summarize_mc_raw(
            raw,
            fee_day0_usd=fee_day0_usd,
            card_fx_fee_pct=card_fx,
            usd_vnd_rate=usd_vnd,
            horizon_days=756,
        )

    scenarios_out: dict[str, Any] = {}
    for sc in build_defense_scenarios():
        sid = sc["id"]
        tot_p12 = sc["total_open_p1p2_pct"]
        tot_fn = sc["total_open_funded_pct"]
        use_cl = bool(sc["use_clusters"])
        u_p12, j_p12, i_p12 = (2.25, 2.00, 1.75) if use_cl else (None, None, None)
        u_fn, j_fn, i_fn = (1.75, 1.50, 1.25) if use_cl else (None, None, None)

        pre_1x, gstats_1x = _get_pre(1.00, sc["calendar"], sc["news_pad_sec"], sc["spread_preset"])

        # Core Law-15 balanced metrics on 100K 1.0x Funded (direct parity with reconciliation doc)
        core_100k_1x, _, _, _, _ = replay_shielded_stage(
            ext_days,
            pre_1x,
            capital_usd=100_000.0,
            mult=1.00,
            symcap_pct=1.00,
            total_open_cap_pct=tot_fn,
            usd_cluster_cap_pct=u_fn,
            jpy_cluster_cap_pct=j_fn,
            idx_cluster_cap_pct=i_fn,
        )
        # P1 (4.0x) and P2 (3.5x) realized historical risk & worst intraday DD on 10K
        p1_10k_4x, _, _, _, _ = replay_shielded_stage(
            ext_days,
            pre_1x,
            capital_usd=10_000.0,
            mult=4.00,
            symcap_pct=1.75,
            total_open_cap_pct=tot_p12,
            usd_cluster_cap_pct=u_p12,
            jpy_cluster_cap_pct=j_p12,
            idx_cluster_cap_pct=i_p12,
        )
        p2_10k_35x, _, _, _, _ = replay_shielded_stage(
            ext_days,
            pre_1x,
            capital_usd=10_000.0,
            mult=3.50,
            symcap_pct=1.75,
            total_open_cap_pct=tot_p12,
            usd_cluster_cap_pct=u_p12,
            jpy_cluster_cap_pct=j_p12,
            idx_cluster_cap_pct=i_p12,
        )
        fn_10k_125x, _, _, _, _ = replay_shielded_stage(
            ext_days,
            pre_1x,
            capital_usd=10_000.0,
            mult=1.25,
            symcap_pct=1.25,
            total_open_cap_pct=tot_fn,
            usd_cluster_cap_pct=u_fn,
            jpy_cluster_cap_pct=j_fn,
            idx_cluster_cap_pct=i_fn,
        )

        # Honest Flash-Crash Simultaneous Shock Matrix (1.25x & 1.50x gap, ZERO clamping < 5%)
        shock_matrix = compute_honest_shock_matrix(
            total_open_cap_p1p2_pct=tot_p12,
            total_open_cap_funded_pct=tot_fn,
            usd_cluster_cap_p1p2_pct=u_p12,
            jpy_cluster_cap_p1p2_pct=j_p12,
            idx_cluster_cap_p1p2_pct=i_p12,
            usd_cluster_cap_funded_pct=u_fn,
            jpy_cluster_cap_funded_pct=j_fn,
            idx_cluster_cap_funded_pct=i_fn,
        )
        worst_gap_125x = max(r["gap_shock_125x_pct"] for r in shock_matrix)
        worst_gap_150x = max(r["gap_shock_150x_pct"] for r in shock_matrix)
        all_4_safe_450 = all(r["under_4_50_pct_at_125x"] for r in shock_matrix)

        # FTMO Standard 10K MC (BF 1.0x + Orig 1.0x)
        mc_10k_bf_1x = _eval_ftmo_mc(
            pre_1x,
            contract=c10k,
            fee_day0_usd=float(c10k["fee_promo_usd"]),
            max_retries=0,
            tot_p1p2=tot_p12,
            tot_fn=tot_fn,
            use_clusters=use_cl,
        )
        mc_10k_orig_1x = _eval_ftmo_mc(
            pre_1x,
            contract=c10k,
            fee_day0_usd=float(c10k["fee_orig_usd"]),
            max_retries=0,
            tot_p1p2=tot_p12,
            tot_fn=tot_fn,
            use_clusters=use_cl,
        )
        mc_100k_bf_1x = _eval_ftmo_mc(
            pre_1x,
            contract=c100k,
            fee_day0_usd=float(c100k["fee_promo_usd"]),
            max_retries=0,
            tot_p1p2=tot_p12,
            tot_fn=tot_fn,
            use_clusters=use_cl,
        )

        # Cost sensitivity at 0.66x (Demo), 1.50x (Stress), 1.75x (Red line)
        ftmo_10k_mc_bundle: dict[str, Any] = {
            "bf_1_00x": mc_10k_bf_1x,
            "orig_1_00x": mc_10k_orig_1x,
            "bf_100k_1_00x": mc_100k_bf_1x,
        }
        if sid in ("BASELINE_C10_NEWS_ON", "SHIELD_C_TOT300_5M", "SHIELD_C_TOT300_10M", "SHIELD_C_TOT250_10M"):
            for f_tag, f_val in (("bf_0_66x", 0.66), ("bf_1_50x", 1.50), ("bf_1_75x", 1.75)):
                pre_f, _ = _get_pre(f_val, sc["calendar"], sc["news_pad_sec"], sc["spread_preset"])
                ftmo_10k_mc_bundle[f_tag] = _eval_ftmo_mc(
                    pre_f,
                    contract=c10k,
                    fee_day0_usd=float(c10k["fee_promo_usd"]),
                    max_retries=0,
                    tot_p1p2=tot_p12,
                    tot_fn=tot_fn,
                    use_clusters=use_cl,
                )

        sc_caps = _resolve_spread_caps(sc["spread_preset"])
        scenarios_out[sid] = {
            "config": sc,
            "spread_guard_active": bool(sc_caps is not None),
            "spread_caps_used_pts": dict(sc_caps) if sc_caps is not None else None,
            "guard_stats_1x": gstats_1x,
            "core_100k_1x": core_100k_1x,
            "phase_replay_10k": {
                "p1_4x": p1_10k_4x,
                "p2_35x": p2_10k_35x,
                "funded_125x": fn_10k_125x,
            },
            "shock_matrix": shock_matrix,
            "worst_gap_125x_pct": round(worst_gap_125x, 2),
            "worst_gap_150x_pct": round(worst_gap_150x, 2),
            "all_profiles_le_4_50_pct": all_4_safe_450,
            "ftmo_std_10k_mc": ftmo_10k_mc_bundle,
        }

    # Select winning Shield C Pareto candidate:
    # Satisfy ALL profiles 1.25x gap shock <= 4.50% & maximize FTMO 10K BF EV/Fee with 6-CCY + SpreadGuard
    shield_c_ids = [
        sid
        for sid, obj in scenarios_out.items()
        if obj["config"]["group"] == "Shield_C" and obj["all_profiles_le_4_50_pct"]
    ]
    winner_id = max(
        shield_c_ids,
        key=lambda sid: (
            scenarios_out[sid]["ftmo_std_10k_mc"]["bf_1_00x"]["ev_npv_24m_usd"],
            -scenarios_out[sid]["worst_gap_125x_pct"],
        ),
    )

    # Compute exact friction break-even curves for Baseline + Winning Shield C + Shield C ±10m variant
    breakeven_curves: dict[str, Any] = {}
    if include_breakeven:
        for b_id in dict.fromkeys(("BASELINE_C10_NEWS_ON", winner_id, "SHIELD_C_TOT300_10M", "SHIELD_C_TOT250_10M")):
            sc = scenarios_out[b_id]["config"]
            cal_obj = cal_523 if sc["calendar"] == "523_6CCY" else cal_224
            scaps = _resolve_spread_caps(sc["spread_preset"])
            u_fn, j_fn, i_fn = (1.75, 1.50, 1.25) if sc["use_clusters"] else (None, None, None)
            breakeven_curves[b_id] = compute_exact_breakeven_friction(
                ext_days,
                raw_tapes,
                red_news_cal=cal_obj,
                news_pad_sec=sc["news_pad_sec"],
                spread_caps_pts=scaps,
                entry_spread_pts=entry_spread_pts,
                total_open_cap_pct=sc["total_open_funded_pct"],
                usd_cap=u_fn,
                jpy_cap=j_fn,
                idx_cap=i_fn,
            )

    # Strip large internal entry_spread_pts map before JSON serialization
    spread_calib_public = {k: v for k, v in spread_calib.items() if k != "entry_spread_pts"}

    return {
        "schema": "naqex-flashcrash-pareto-study-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "dev_window": f"{ext_days[0]}..{ext_days[-1]}",
        "n_dev_days": len(ext_days),
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "frozen_tapes_binding_sha256": data["binding_sha256"],
        "frozen_tapes_npz_sha256": data["npz_sha256"],
        "usd_vnd_rate": usd_vnd,
        "spread_guard_active": spread_guard_active,
        "shard": {
            "shard_index": shard_index,
            "shard_total": shard_total,
            "shard_n_paths": shard_n_paths,
            "total_n_paths": n_paths,
            "shard_seed": shard_seed,
        },
        "runtime_seconds": round(time.perf_counter() - t0, 3),
        "m1_spread_calibration": spread_calib_public,
        "winner_shield_c_id": winner_id,
        "breakeven_curves": breakeven_curves,
        "scenarios": scenarios_out,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Naqex Flash-Crash Defense Pareto Study (Dev 2018-2024 ONLY, X13-shardable)."
    )
    p.add_argument("--derived-dir", type=Path, default=DEFAULT_DERIVED_DIR)
    p.add_argument("--m1-cache-dir", type=Path, default=DEFAULT_M1_CACHE_DIR)
    p.add_argument("--cal-224", type=Path, default=DEFAULT_CAL_224_PATH)
    p.add_argument("--cal-523", type=Path, default=DEFAULT_CAL_523_PATH)
    p.add_argument("--fx-rates", type=Path, default=DEFAULT_FX_RATES_PATH)
    p.add_argument("--firms-catalog", type=Path, default=DEFAULT_FIRMS_CATALOG_PATH)
    p.add_argument("--n-paths", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--shard-index", type=int, default=0)
    p.add_argument("--shard-total", type=int, default=1)
    p.add_argument("--job-id", type=str, default=None)
    p.add_argument("--skip-m1-spread-scan", action="store_true")
    p.add_argument("--skip-breakeven", action="store_true")
    p.add_argument("--out-json", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.job_id is not None:
        _assert_no_forbidden_x13_tokens("job_id", str(args.job_id))
    if args.out_json is not None:
        _assert_no_forbidden_x13_tokens("out_json", args.out_json.name)
    res = run_pareto_study(
        derived_dir=args.derived_dir,
        m1_cache_dir=args.m1_cache_dir,
        cal_224_path=args.cal_224,
        cal_523_path=args.cal_523,
        fx_rates_path=args.fx_rates,
        firms_catalog_path=args.firms_catalog,
        n_paths=args.n_paths,
        seed=args.seed,
        shard_index=args.shard_index,
        shard_total=args.shard_total,
        skip_m1_spread_scan=args.skip_m1_spread_scan,
        include_breakeven=not args.skip_breakeven,
    )
    if args.job_id is not None:
        res["job_id"] = str(args.job_id)
    if args.out_json is not None:
        _atomic_write_json(args.out_json, res)
    # Compact stdout Pareto summary
    win = res["winner_shield_c_id"]
    print(
        f"FLASHCRASH_PARETO_OK dev={res['dev_window']} holdout_rows={res['holdout_rows_analysed']} "
        f"spread_guard_active={res['spread_guard_active']} "
        f"shard={args.shard_index}/{args.shard_total} n_paths={res['shard']['shard_n_paths']} "
        f"winner={win} runtime={res['runtime_seconds']}s"
    )
    for sid, obj in res["scenarios"].items():
        c = obj["core_100k_1x"]
        m = obj["ftmo_std_10k_mc"]["bf_1_00x"]
        print(
            f"  {sid:22s} | Gap1.25x={obj['worst_gap_125x_pct']:5.2f}% "
            f"Gap1.50x={obj['worst_gap_150x_pct']:5.2f}% "
            f"| 1x Ann={c['ann_pct']:+5.2f}% DD={c['peak_dd_pct']:4.2f}% "
            f"Calmar={c['calmar']:.3f} PF={c['profit_factor']:.3f} "
            f"| 10K BF NPV24={m['ev_npv_24m_vnd_tr']:+5.2f}tr "
            f"EV/Fee={m['ev_per_fee_npv24']:+5.2f}x "
            f"Pass24={m['pass_24m_pct']:5.2f}% Fail24={m['fail_24m_pct']:4.2f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
