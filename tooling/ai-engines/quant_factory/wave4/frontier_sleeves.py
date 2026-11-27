"""Wave 4 Dev Cluster A & Blind Cluster B Screening Engine for 3 Frontier Non-CFD Alpha Sleeves.

Implements strictly causal, white-box, fail-closed screening for the 3 pre-registered Frontier
non-CFD sleeves from `tooling/automation/configs/frontier_alpha_candidates.json`:
  1. `FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY`:
     Pure-NumPy Statistical Jump Model (SJM, Shu/Yu/Mulvey 2024) asset-specific regime switching
     with jump penalty `lambda` + Nested Clustered Optimization (NCO) / Hierarchical Risk Parity
     (HRP) on `.runtime/etf40-cache/`.
  2. `FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR`:
     Forward-looking `IDX_VIX / IDX_VIX3M` term-structure VRP hysteresis + multifactor realized
     volatility/covariance scaling + L1 rebalancing deadband + `BIL/SHY` safe-harbor on
     `.runtime/etf40-cache/` (`IDX_VIX` and `IDX_VIX3M` strictly weight = `0.0`).
  3. `FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM`:
     Low-turnover (`>= D1` rebalance) cross-sectional perpetual funding-crowding carry + spot-perp
     basis deviation + slow (`>= 4H/D1`) causal momentum overlay with Cross-Margin liquidation
     audit (`2.0x`-`2.5x` buffer) on `.runtime/crypto-spot-cache/`.

Hard safety & anti-leakage invariants (ZERO bare `assert`s; active under `python -O`):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed = 0`).
  - Hard Cluster A boundary guard: `split="cluster_a"` slices strictly `<= cluster_a_end` at load
    time AND rejects any preloaded panel containing Cluster B or Holdout dates with `ValueError`.
  - Shared `evaluate_sleeve(sleeve_id, params, split="cluster_a" | "cluster_b_blind", cutoff_utc=...)`
    so Wave 2A (`w4-m2b-blind`) evaluates the exact same audited engine ONCE on `cluster_b_blind`.
  - DuckDB Experiment Budget `wave4_frontier_m36 <= 36` (`<= 8` per sleeve -> `<= 24` in Cluster A),
    dual-backed with `ExperimentLedger` (`SQLiteRunRegistry` SHA-256 hash chain + DuckDB).
  - Top-level imports use stdlib + NumPy + lightweight `quant_core` only (lazy SciPy/Arrow/DuckDB).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import warnings
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
)
from quant_core.io_utils import (  # noqa: E402
    atomic_write_json,
    canonical_json,
    sha256_file,
    sha256_json_canonical,
)

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Identifiers
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-frontier-sleeves-v1"
FROZEN_SCHEMA_VERSION: str = "naqex-wave4-frontier-cluster-a-frozen-v1"
RECEIPT_SCHEMA_VERSION: str = "naqex-wave4-worker-receipt-v1"

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SPEND_VND: int = 0

HOLDOUT_CUTOFF_DATE: str = "2024-12-31"
HOLDOUT_START_DATE: str = HOLDOUT_CUTOFF_DAY  # "2025-01-01"

WAVE4_FRONTIER_FAMILY_ID: str = "wave4_frontier_m36"
WAVE4_FRONTIER_BUDGET_CAP: int = 36
MAX_CLUSTER_A_TRIALS_PER_SLEEVE: int = 8
MAX_CLUSTER_A_TOTAL_TRIALS: int = 24

FRONTIER_01_ID: str = "FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY"
FRONTIER_02_ID: str = "FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR"
FRONTIER_03_ID: str = "FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM"

FRONTIER_SLEEVE_IDS: tuple[str, ...] = (
    FRONTIER_01_ID,
    FRONTIER_02_ID,
    FRONTIER_03_ID,
)

SIGNAL_ONLY_SYMBOLS: frozenset[str] = frozenset({"IDX_VIX", "IDX_VIX3M", "^VIX", "^VIX3M"})

CONFIG_PATH: Path = REPO_ROOT / "tooling" / "automation" / "configs" / "frontier_alpha_candidates.json"
ETF40_CACHE_DIR: Path = REPO_ROOT / ".runtime" / "etf40-cache"
CRYPTO_CACHE_DIR: Path = REPO_ROOT / ".runtime" / "crypto-spot-cache"
RETURNS_DIR: Path = REPO_ROOT / ".runtime" / "quant-pod-returns"
FRONTIER_OUT_DIR: Path = REPO_ROOT / ".runtime" / "offensive4" / "frontier"
DEFAULT_FROZEN_JSON_PATH: Path = FRONTIER_OUT_DIR / "frontier_cluster_a_frozen.json"
DEFAULT_DUCKDB_PATH: Path = FRONTIER_OUT_DIR / "wave4_frontier_m36.duckdb"
DEFAULT_REGISTRY_PATH: Path = FRONTIER_OUT_DIR / "wave4_frontier_m36_registry.sqlite3"
DEFAULT_RECEIPT_PATH: Path = REPO_ROOT / ".runtime" / "offensive4" / "audits" / "w4_m2b_frontier_receipt.json"
DEFAULT_DROPBOX_PATH: Path = REPO_ROOT / ".tmp" / "swarm_dropbox" / "w4-m2b-frontier.json"

_NO_WINDOW_FLAGS: int = 0x08000000 if sys.platform == "win32" else 0
_EPS: float = 1e-12


# ---------------------------------------------------------------------------
# Strict Input & Date Guards (ZERO bare `assert`s; `-O` safe)
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_non_empty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _require_finite_float(
    value: Any,
    name: str,
    *,
    lo: float | None = None,
    hi: float | None = None,
    strict_lo: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"{name} must be a finite numeric value (not bool), got {value!r} ({type(value).__name__})")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if lo is not None:
        if strict_lo and out <= lo:
            raise ValueError(f"{name}={out} must be > {lo}")
        if not strict_lo and out < lo:
            raise ValueError(f"{name}={out} must be >= {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}={out} must be <= {hi}")
    return out


def _require_int(
    value: Any,
    name: str,
    *,
    lo: int | None = None,
    hi: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer (not bool), got {value!r} ({type(value).__name__})")
    out = int(value)
    if lo is not None and out < lo:
        raise ValueError(f"{name}={out} must be >= {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}={out} must be <= {hi}")
    return out


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool, got {value!r} ({type(value).__name__})")
    return value


def _validate_iso_day(value: Any, name: str) -> str:
    txt = _require_non_empty_str(value, name)
    if len(txt) != 10:
        raise HoldoutLockError(f"{name} must be YYYY-MM-DD, got {value!r}")
    try:
        parsed = date.fromisoformat(txt)
    except ValueError as exc:
        raise HoldoutLockError(f"{name} is not a valid calendar date: {value!r}") from exc
    return parsed.isoformat()


def _validate_cutoff_utc(cutoff_utc: Any, *, context: str = "frontier_sleeves") -> str:
    day = _validate_iso_day(cutoff_utc, f"{context}.cutoff_utc")
    enforce_pre_holdout_dates(day, context=f"{context}.cutoff_utc", cutoff_day=HOLDOUT_START_DATE)
    if day > HOLDOUT_CUTOFF_DATE:
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_utc={day!r} exceeds sealed {HOLDOUT_CUTOFF_DATE!r}"
        )
    return day


def _parse_date_range(range_text: str, *, context: str) -> tuple[str, str]:
    txt = _require_non_empty_str(range_text, context)
    if ".." not in txt:
        raise ValueError(f"{context} must be 'YYYY-MM-DD..YYYY-MM-DD', got {range_text!r}")
    lo_raw, hi_raw = txt.split("..", 1)
    lo = _validate_iso_day(lo_raw, f"{context}.start")
    hi = _validate_iso_day(hi_raw, f"{context}.end")
    if hi < lo:
        raise ValueError(f"{context} inverted date range: {lo}..{hi}")
    enforce_pre_holdout_dates([lo, hi], context=context, cutoff_day=HOLDOUT_START_DATE)
    return lo, hi


def _ms_to_utc_date(ms: int) -> str:
    return datetime.fromtimestamp(float(ms) / 1000.0, UTC).strftime("%Y-%m-%d")


def _safe_etf_filename(symbol: str) -> str:
    clean = _require_non_empty_str(symbol, "symbol")
    if clean.startswith("^"):
        return f"IDX_{clean[1:]}.parquet"
    return f"{clean}.parquet"


def _canonical_symbol(symbol: str) -> str:
    clean = _require_non_empty_str(symbol, "symbol")
    if clean == "^VIX":
        return "IDX_VIX"
    if clean == "^VIX3M":
        return "IDX_VIX3M"
    return clean


def _is_signal_only(symbol: str) -> bool:
    return symbol in SIGNAL_ONLY_SYMBOLS or _canonical_symbol(symbol) in SIGNAL_ONLY_SYMBOLS


def _git_head_sha() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        sha = res.stdout.strip()
        return sha if sha else "workspace-offline"
    except Exception:
        return "workspace-offline"


# ---------------------------------------------------------------------------
# Config & Pre-Registered Gate Loader
# ---------------------------------------------------------------------------


def load_frontier_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and validate `tooling/automation/configs/frontier_alpha_candidates.json`."""
    p = Path(config_path)
    if not p.is_file():
        raise FileNotFoundError(f"Frontier config not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("candidates"), list):
        raise ValueError(f"Malformed frontier config at {p}")
    enforce_holdout_zero_rows(raw.get("holdout_rows_analysed", -1), context="frontier_config")
    _validate_cutoff_utc(raw.get("dev_cutoff_utc"), context="frontier_config")
    return raw


def get_sleeve_spec(
    sleeve_id: str,
    *,
    config: Mapping[str, Any] | None = None,
    config_path: str | Path = CONFIG_PATH,
) -> dict[str, Any]:
    """Return normalized pre-registered spec and date boundaries for a Frontier sleeve."""
    sid = _require_non_empty_str(sleeve_id, "sleeve_id")
    if sid not in FRONTIER_SLEEVE_IDS:
        raise ValueError(f"Unknown frontier sleeve_id={sid!r}; expected one of {FRONTIER_SLEEVE_IDS}")
    cfg = dict(config) if config is not None else load_frontier_config(config_path)
    match: dict[str, Any] | None = None
    for cand in cfg.get("candidates", []):
        if isinstance(cand, dict) and cand.get("mechanism_id") == sid:
            match = cand
            break
    if match is None:
        raise ValueError(f"Sleeve {sid!r} missing from frontier_alpha_candidates.json")

    gate = match.get("pre_registered_falsification_gate")
    if not isinstance(gate, dict):
        raise ValueError(f"Sleeve {sid!r} missing pre_registered_falsification_gate")

    a_start, a_end = _parse_date_range(gate["dev_cluster_a"], context=f"{sid}.dev_cluster_a")
    b_start, b_end = _parse_date_range(gate["dev_cluster_b_blind"], context=f"{sid}.dev_cluster_b_blind")
    if b_start <= a_end:
        raise ValueError(f"{sid}: Cluster B start {b_start} overlaps Cluster A end {a_end}")
    cutoff = _validate_cutoff_utc(gate.get("dev_cutoff_utc", HOLDOUT_CUTOFF_DATE), context=sid)
    if b_end > cutoff:
        raise HoldoutLockError(f"{sid}: Cluster B end {b_end} exceeds dev_cutoff_utc {cutoff}")

    return {
        "mechanism_id": sid,
        "title": str(match.get("title", sid)),
        "asset_class": str(match.get("asset_class", "")),
        "available_dev_cache": str(match.get("available_dev_cache", "")),
        "required_dev_symbols": tuple(str(s) for s in match.get("required_dev_symbols", ())),
        "dev_cutoff_utc": cutoff,
        "cluster_a_start": a_start,
        "cluster_a_end": a_end,
        "cluster_b_start": b_start,
        "cluster_b_end": b_end,
        "gate": dict(gate),
    }


def enforce_split_bounds(
    dates: Sequence[str],
    *,
    sleeve_id: str,
    split: str,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    config: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """Fail-closed `-O`-safe guard enforcing Holdout `< 2025-01-01` AND Cluster A boundary isolation.

    Returns `(eval_start, eval_end)` for the requested split.
    """
    if split not in ("cluster_a", "cluster_b_blind"):
        raise ValueError(f"split must be 'cluster_a' or 'cluster_b_blind', got {split!r}")
    cut = _validate_cutoff_utc(cutoff_utc, context=f"{sleeve_id}.{split}")
    spec = get_sleeve_spec(sleeve_id, config=config)

    if not dates:
        raise ValueError(f"EMPTY_DATE_SERIES [{sleeve_id}.{split}]: dates cannot be empty")
    parsed_days: list[str] = []
    prev_day: str | None = None
    for raw_d in dates:
        d_iso = _validate_iso_day(raw_d, f"{sleeve_id}.{split}.date")
        if prev_day is not None and d_iso <= prev_day:
            raise ValueError(
                f"NON_MONOTONIC_DATES [{sleeve_id}.{split}]: {d_iso!r} <= previous {prev_day!r}"
            )
        prev_day = d_iso
        parsed_days.append(d_iso)

    # Hard Holdout lock (< 2025-01-01) via quant_core.holdout_guard (immune to python -O)
    enforce_pre_holdout_dates(parsed_days, context=f"{sleeve_id}.{split}", cutoff_day=HOLDOUT_START_DATE)

    max_day = parsed_days[-1]
    if max_day > cut:
        raise HoldoutLockError(
            f"CUTOFF_BREACH [{sleeve_id}.{split}]: max date {max_day!r} > cutoff_utc {cut!r}"
        )

    if split == "cluster_a":
        a_end = spec["cluster_a_end"]
        b_leak = [d for d in parsed_days if d > a_end]
        if b_leak:
            raise ValueError(
                f"CLUSTER_B_LEAKAGE_VIOLATION [{sleeve_id}.cluster_a]: "
                f"detected {len(b_leak)} date(s) > cluster_a_end {a_end!r}: {b_leak[:5]}"
            )
        return spec["cluster_a_start"], a_end

    # split == "cluster_b_blind"
    b_start = spec["cluster_b_start"]
    b_end = min(spec["cluster_b_end"], cut)
    return b_start, b_end


# ---------------------------------------------------------------------------
# Strictly Bounded Offline Cache Loaders (Zero Network Calls, Zero Holdout)
# ---------------------------------------------------------------------------


def load_etf_panel_strict(
    symbols: Sequence[str],
    *,
    max_date: str,
    cache_dir: str | Path = ETF40_CACHE_DIR,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Load local ETF parquet cache strictly `<= max_date <= cutoff_utc < 2025-01-01`.

    - Slices strictly `date <= max_date` at load time (`holdout_rows_analysed == 0`).
    - Anchors NYSE calendar strictly to tradable ETFs (excludes CBOE VIX prints on US holidays).
    - Zero pre-listing forward-fill: unlisted dates remain `NaN`.
    """
    import pyarrow.parquet as pq

    cut = _validate_cutoff_utc(cutoff_utc, context="load_etf_panel_strict")
    hi = _validate_iso_day(max_date, "load_etf_panel_strict.max_date")
    enforce_pre_holdout_dates(hi, context="load_etf_panel_strict.max_date", cutoff_day=HOLDOUT_START_DATE)
    if hi > cut:
        raise HoldoutLockError(f"max_date {hi!r} > cutoff_utc {cut!r}")

    cdir = Path(cache_dir)
    if not cdir.is_dir():
        raise FileNotFoundError(f"ETF cache directory not found: {cdir}")

    loaded_syms: list[str] = []
    maps: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    hasher = hashlib.sha256()

    for raw_sym in symbols:
        sym = _canonical_symbol(raw_sym)
        fpath = cdir / _safe_etf_filename(sym)
        if not fpath.is_file():
            raise FileNotFoundError(f"Required ETF parquet missing: {fpath}")
        tbl = pq.read_table(fpath, columns=["date", "adjclose"])
        ds = tbl["date"].to_pylist()
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False)
        mp: dict[str, float] = {}
        for d_raw, val in zip(ds, ac, strict=True):
            d_str = str(d_raw)
            if d_str > hi:
                continue
            if d_str >= HOLDOUT_START_DATE:
                raise HoldoutLockError(f"HOLDOUT_SLICE_LEAK: {sym} date {d_str}")
            fv = float(val)
            if math.isfinite(fv) and fv > 0.0:
                mp[d_str] = fv
        if not mp:
            raise ValueError(f"ETF {sym!r} has zero valid rows <= {hi!r} in {cdir}")
        loaded_syms.append(sym)
        maps[sym] = mp
        if not _is_signal_only(sym):
            all_dates.update(mp.keys())
        sorted_items = sorted(mp.items())
        hasher.update(f"{sym}:{len(sorted_items)}:{sorted_items[0][0]}:{sorted_items[-1][0]}:".encode())
        hasher.update(np.asarray([v for _, v in sorted_items], dtype=np.float64).tobytes())

    dates = sorted(all_dates)
    enforce_pre_holdout_dates(dates, context="load_etf_panel_strict.dates", cutoff_day=HOLDOUT_START_DATE)
    if not dates or dates[-1] > hi:
        raise HoldoutLockError(f"Loaded ETF dates violate max_date={hi!r}")

    n_t, n_k = len(dates), len(loaded_syms)
    adjclose = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for j, sym in enumerate(loaded_syms):
        mp = maps[sym]
        for i, d_iso in enumerate(dates):
            if d_iso in mp:
                adjclose[i, j] = mp[d_iso]

    return {
        "kind": "etf",
        "dates": dates,
        "symbols": loaded_syms,
        "adjclose": adjclose,
        "max_loaded_date": dates[-1],
        "holdout_rows_analysed": 0,
        "data_sha256": hasher.hexdigest(),
    }


def load_crypto_panel_strict(
    symbols: Sequence[str],
    *,
    max_date: str,
    cache_dir: str | Path = CRYPTO_CACHE_DIR,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    include_4h: bool = True,
) -> dict[str, Any]:
    """Load local crypto funding + perp_1d + spot 1d (+ optional 4h trend) strictly `<= max_date`.

    Zero `< 4H` bars are read, zero pre-listing backfill is performed, and every row `> max_date`
    or `>= 2025-01-01` is excluded at load time (`holdout_rows_analysed == 0`).
    """
    import pyarrow.parquet as pq

    cut = _validate_cutoff_utc(cutoff_utc, context="load_crypto_panel_strict")
    hi = _validate_iso_day(max_date, "load_crypto_panel_strict.max_date")
    enforce_pre_holdout_dates(hi, context="load_crypto_panel_strict.max_date", cutoff_day=HOLDOUT_START_DATE)
    if hi > cut:
        raise HoldoutLockError(f"max_date {hi!r} > cutoff_utc {cut!r}")

    cdir = Path(cache_dir)
    fdir = cdir / "funding"
    if not fdir.is_dir():
        raise FileNotFoundError(f"Crypto funding cache directory not found: {fdir}")

    loaded_syms: list[str] = []
    all_days: set[str] = set()
    fund_sum_map: dict[str, dict[str, float]] = {}
    pos_8h_map: dict[str, dict[str, int]] = {}
    tot_8h_map: dict[str, dict[str, int]] = {}
    perp_c_map: dict[str, dict[str, float]] = {}
    perp_h_map: dict[str, dict[str, float]] = {}
    perp_qv_map: dict[str, dict[str, float]] = {}
    spot_c_map: dict[str, dict[str, float]] = {}
    spot_h_map: dict[str, dict[str, float]] = {}
    h4_trend_map: dict[str, dict[str, float]] = {}
    hasher = hashlib.sha256()

    for raw_sym in symbols:
        sym = _require_non_empty_str(raw_sym, "symbol")
        rp = fdir / "rates" / f"{sym}.parquet"
        kp = fdir / "perp_1d" / f"{sym}.parquet"
        sp = cdir / "1d" / f"{sym}.parquet"
        if not rp.is_file() or not kp.is_file() or not sp.is_file():
            raise FileNotFoundError(
                f"Missing crypto parquet for {sym}: "
                f"rates={rp.is_file()}, perp={kp.is_file()}, spot={sp.is_file()}"
            )

        # 1. Funding 8h settlements aggregated strictly <= hi
        rtbl = pq.read_table(rp, columns=["funding_time_ms", "funding_rate"])
        ft_arr = rtbl["funding_time_ms"].to_numpy(zero_copy_only=False)
        fr_arr = rtbl["funding_rate"].to_numpy(zero_copy_only=False)
        dsum: dict[str, float] = defaultdict(float)
        dcnt: dict[str, int] = defaultdict(int)
        pcnt: dict[str, int] = defaultdict(int)
        for ts, rate in zip(ft_arr, fr_arr, strict=True):
            fv = float(rate)
            if not math.isfinite(fv):
                continue
            dk = _ms_to_utc_date(int(ts))
            if dk < "2020-01-01" or dk > hi:
                continue
            if dk >= HOLDOUT_START_DATE:
                raise HoldoutLockError(f"HOLDOUT_SLICE_LEAK: funding {sym} {dk}")
            dsum[dk] += fv
            dcnt[dk] += 1
            if fv > 0.0:
                pcnt[dk] += 1
            all_days.add(dk)

        # 2. Perp 1D klines strictly <= hi
        ktbl = pq.read_table(kp, columns=["open_time_ms", "high", "close", "quote_volume"])
        p_c: dict[str, float] = {}
        p_h: dict[str, float] = {}
        p_qv: dict[str, float] = {}
        for ts, hv, cv, qv in zip(
            ktbl["open_time_ms"].to_numpy(zero_copy_only=False),
            ktbl["high"].to_numpy(zero_copy_only=False),
            ktbl["close"].to_numpy(zero_copy_only=False),
            ktbl["quote_volume"].to_numpy(zero_copy_only=False),
            strict=True,
        ):
            dk = _ms_to_utc_date(int(ts))
            if dk < "2020-01-01" or dk > hi:
                continue
            if dk >= HOLDOUT_START_DATE:
                raise HoldoutLockError(f"HOLDOUT_SLICE_LEAK: perp_1d {sym} {dk}")
            cf, hf, qf = float(cv), float(hv), float(qv)
            if math.isfinite(cf) and cf > 0.0:
                p_c[dk] = cf
            if math.isfinite(hf) and hf > 0.0:
                p_h[dk] = hf
            if math.isfinite(qf) and qf >= 0.0:
                p_qv[dk] = qf

        # 3. Spot 1D klines strictly <= hi
        stbl = pq.read_table(sp, columns=["open_time_ms", "high", "close"])
        s_c: dict[str, float] = {}
        s_h: dict[str, float] = {}
        for ts, hv, cv in zip(
            stbl["open_time_ms"].to_numpy(zero_copy_only=False),
            stbl["high"].to_numpy(zero_copy_only=False),
            stbl["close"].to_numpy(zero_copy_only=False),
            strict=True,
        ):
            dk = _ms_to_utc_date(int(ts))
            if dk < "2020-01-01" or dk > hi:
                continue
            if dk >= HOLDOUT_START_DATE:
                raise HoldoutLockError(f"HOLDOUT_SLICE_LEAK: spot_1d {sym} {dk}")
            cf, hf = float(cv), float(hv)
            if math.isfinite(cf) and cf > 0.0:
                s_c[dk] = cf
            if math.isfinite(hf) and hf > 0.0:
                s_h[dk] = hf

        # 4. Optional causal 4H slow EMA trend confirmation aggregated strictly within UTC day <= hi
        #    Every 4H bar opening on UTC day `dk` (00, 04, 08, 12, 16, 20 UTC) closes by 24:00 UTC of `dk`.
        h4_map: dict[str, float] = {}
        h4p = cdir / "4h" / f"{sym}.parquet"
        if include_4h and h4p.is_file():
            h4tbl = pq.read_table(h4p, columns=["open_time_ms", "close"])
            h4_ts = h4tbl["open_time_ms"].to_numpy(zero_copy_only=False)
            h4_cl = h4tbl["close"].to_numpy(zero_copy_only=False)
            alpha42 = 2.0 / (42.0 + 1.0)  # 42 * 4H = 7 calendar days slow EMA
            ema42 = math.nan
            bar_count = 0
            day_above: dict[str, list[float]] = defaultdict(list)
            for ts, cv in zip(h4_ts, h4_cl, strict=True):
                dk = _ms_to_utc_date(int(ts))
                if dk > hi:
                    break
                if dk >= HOLDOUT_START_DATE:
                    raise HoldoutLockError(f"HOLDOUT_SLICE_LEAK: spot_4h {sym} {dk}")
                cf = float(cv)
                if not math.isfinite(cf) or cf <= 0.0:
                    continue
                ema42 = cf if not math.isfinite(ema42) else (alpha42 * cf + (1.0 - alpha42) * ema42)
                bar_count += 1
                if dk >= "2020-01-01" and bar_count >= 42:
                    day_above[dk].append(1.0 if cf > ema42 else -1.0)
            for dk, vals in day_above.items():
                h4_map[dk] = float(sum(vals)) / float(len(vals))

        loaded_syms.append(sym)
        fund_sum_map[sym] = dict(dsum)
        pos_8h_map[sym] = dict(pcnt)
        tot_8h_map[sym] = dict(dcnt)
        perp_c_map[sym] = p_c
        perp_h_map[sym] = p_h
        perp_qv_map[sym] = p_qv
        spot_c_map[sym] = s_c
        spot_h_map[sym] = s_h
        h4_trend_map[sym] = h4_map

        hasher.update(f"{sym}:{len(dsum)}:{len(p_c)}:{len(s_c)}:{len(h4_map)}:".encode())
        if dsum:
            sd = sorted(dsum.items())
            hasher.update(np.asarray([v for _, v in sd], dtype=np.float64).tobytes())

    dates = sorted(all_days)
    enforce_pre_holdout_dates(dates, context="load_crypto_panel_strict.dates", cutoff_day=HOLDOUT_START_DATE)
    if not dates or dates[-1] > hi:
        raise HoldoutLockError(f"Loaded crypto dates violate max_date={hi!r}")

    n_t, n_k = len(dates), len(loaded_syms)
    funding_daily = np.full((n_t, n_k), np.nan, dtype=np.float64)
    pos_8h_cnt = np.zeros((n_t, n_k), dtype=np.int32)
    tot_8h_cnt = np.zeros((n_t, n_k), dtype=np.int32)
    perp_close = np.full((n_t, n_k), np.nan, dtype=np.float64)
    perp_high = np.full((n_t, n_k), np.nan, dtype=np.float64)
    perp_quote_vol = np.full((n_t, n_k), np.nan, dtype=np.float64)
    spot_close = np.full((n_t, n_k), np.nan, dtype=np.float64)
    spot_high = np.full((n_t, n_k), np.nan, dtype=np.float64)
    h4_trend = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, sym in enumerate(loaded_syms):
        fm = fund_sum_map[sym]
        pm = pos_8h_map[sym]
        tm = tot_8h_map[sym]
        pc = perp_c_map[sym]
        ph = perp_h_map[sym]
        pqv = perp_qv_map[sym]
        sc = spot_c_map[sym]
        sh = spot_h_map[sym]
        h4m = h4_trend_map[sym]
        for i, dk in enumerate(dates):
            if dk in fm:
                funding_daily[i, j] = fm[dk]
            if dk in pm:
                pos_8h_cnt[i, j] = pm[dk]
            if dk in tm:
                tot_8h_cnt[i, j] = tm[dk]
            if dk in pc:
                perp_close[i, j] = pc[dk]
            if dk in ph:
                perp_high[i, j] = ph[dk]
            if dk in pqv:
                perp_quote_vol[i, j] = pqv[dk]
            if dk in sc:
                spot_close[i, j] = sc[dk]
            if dk in sh:
                spot_high[i, j] = sh[dk]
            if dk in h4m:
                h4_trend[i, j] = h4m[dk]

    return {
        "kind": "crypto",
        "dates": dates,
        "symbols": loaded_syms,
        "funding_daily": funding_daily,
        "pos_8h_cnt": pos_8h_cnt,
        "tot_8h_cnt": tot_8h_cnt,
        "perp_close": perp_close,
        "perp_high": perp_high,
        "perp_quote_vol": perp_quote_vol,
        "spot_close": spot_close,
        "spot_high": spot_high,
        "h4_trend": h4_trend,
        "max_loaded_date": dates[-1],
        "holdout_rows_analysed": 0,
        "data_sha256": hasher.hexdigest(),
    }


def _load_incumbent_returns_strict(
    *,
    max_date: str,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    """Load incumbent `PORT_7E` (S1 Dev) and `S4` ETF40 daily returns strictly `<= max_date < 2025-01-01`."""
    cut = _validate_cutoff_utc(cutoff_utc, context="incumbent_returns")
    hi = min(_validate_iso_day(max_date, "incumbent_returns.max_date"), cut)
    enforce_pre_holdout_dates(hi, context="incumbent_returns.max_date", cutoff_day=HOLDOUT_START_DATE)

    s1_map: dict[str, float] | None = None
    try:
        from quant_factory.portfolio_allocator import load_sleeve1_dev_daily_returns

        raw_s1, _ = load_sleeve1_dev_daily_returns()
        s1_map = {
            str(d): float(v)
            for d, v in raw_s1.items()
            if str(d) <= hi and str(d) < HOLDOUT_START_DATE and math.isfinite(float(v))
        }
        if s1_map:
            enforce_pre_holdout_dates(sorted(s1_map.keys()), context="s1_dev_returns", cutoff_day=HOLDOUT_START_DATE)
    except Exception:
        s1_map = None

    s4_map: dict[str, float] | None = None
    s4_path = RETURNS_DIR / "sleeve4_etf40_multifactor.json"
    if s4_path.is_file():
        try:
            raw = json.loads(s4_path.read_text(encoding="utf-8"))
            dr = raw.get("daily_returns", {})
            s4_map = {
                str(d): float(v)
                for d, v in dr.items()
                if str(d) <= hi and str(d) < HOLDOUT_START_DATE and math.isfinite(float(v))
            }
            if s4_map:
                enforce_pre_holdout_dates(
                    sorted(s4_map.keys()),
                    context="s4_dev_returns",
                    cutoff_day=HOLDOUT_START_DATE,
                )
        except Exception:
            s4_map = None

    return s1_map, s4_map


# ---------------------------------------------------------------------------
# Pure-NumPy Statistical Jump Model (SJM) & NCO / HRP Portfolio Optimizers
# ---------------------------------------------------------------------------


def _shrink_covariance(returns_mat: np.ndarray, *, shrink_alpha: float = 0.20) -> np.ndarray:
    """Compute strictly positive-definite diagonal-shrunk covariance matrix in pure NumPy."""
    x = np.asarray(returns_mat, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] < 3 or x.shape[1] < 1:
        raise ValueError(f"returns_mat must be 2D with >= 3 rows and >= 1 col, got {x.shape}")
    k = x.shape[1]
    if k == 1:
        v = float(np.var(x[:, 0], ddof=1))
        return np.array([[max(v, 1e-10)]], dtype=np.float64)
    cov = np.cov(x, rowvar=False, ddof=1)
    cov = np.atleast_2d(np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0))
    cov = 0.5 * (cov + cov.T)
    diag = np.diag(np.maximum(np.diag(cov), 1e-10))
    alpha = float(np.clip(shrink_alpha, 0.0, 1.0))
    shrunk = (1.0 - alpha) * cov + alpha * diag
    shrunk = 0.5 * (shrunk + shrunk.T) + np.eye(k, dtype=np.float64) * 1e-10
    return shrunk


def _cluster_ivp_variance(cov: np.ndarray, indices: Sequence[int]) -> float:
    sub = cov[np.ix_(indices, indices)]
    diag = np.maximum(np.diag(sub), 1e-12)
    ivp = (1.0 / diag) / float(np.sum(1.0 / diag))
    return float(ivp @ sub @ ivp)


def compute_hrp_weights(cov: np.ndarray, *, max_single_weight: float = 0.35) -> np.ndarray:
    """Hierarchical Risk Parity (Lopez de Prado 2016) with lazy SciPy clustering import."""
    c = np.asarray(cov, dtype=np.float64)
    k = c.shape[0]
    if k == 0:
        return np.zeros(0, dtype=np.float64)
    if k == 1:
        return np.array([1.0], dtype=np.float64)

    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    c = 0.5 * (c + c.T) + np.eye(k, dtype=np.float64) * 1e-10
    sd = np.sqrt(np.maximum(np.diag(c), 1e-12))
    corr = np.clip(c / np.outer(sd, sd), -1.0, 1.0)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr)))
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="ward")
    order = [int(i) for i in leaves_list(link)]

    w = np.ones(k, dtype=np.float64)
    clusters: list[list[int]] = [order]
    while clusters:
        next_clusters: list[list[int]] = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            mid = len(cl) // 2
            left, right = cl[:mid], cl[mid:]
            v_l = max(_cluster_ivp_variance(c, left), 1e-12)
            v_r = max(_cluster_ivp_variance(c, right), 1e-12)
            alpha = 1.0 - v_l / (v_l + v_r)
            w[left] *= alpha
            w[right] *= 1.0 - alpha
            if len(left) > 1:
                next_clusters.append(left)
            if len(right) > 1:
                next_clusters.append(right)
        clusters = next_clusters

    return _waterfill_cap_weights(w, max_single_weight=max_single_weight)


def _minvar_long_only_weights(cov: np.ndarray) -> np.ndarray:
    """Fast regularized long-only minimum-variance allocation for small clusters."""
    k = cov.shape[0]
    if k == 1:
        return np.array([1.0], dtype=np.float64)
    diag = np.maximum(np.diag(cov), 1e-12)
    ivp = (1.0 / diag) / float(np.sum(1.0 / diag))
    try:
        reg = cov + np.eye(k, dtype=np.float64) * (1e-6 * float(np.mean(diag)))
        inv_ones = np.linalg.solve(reg, np.ones(k, dtype=np.float64))
        w = np.maximum(inv_ones, 0.0)
        s = float(np.sum(w))
        if s > 1e-12 and np.all(np.isfinite(w)):
            return w / s
    except np.linalg.LinAlgError:
        pass
    return ivp


def compute_nco_weights(
    cov: np.ndarray,
    *,
    max_clusters: int = 5,
    max_single_weight: float = 0.35,
) -> np.ndarray:
    """Nested Clustered Optimization (Lopez de Prado 2019; Supriadi & Siswoyo 2026).

    1. Cluster assets hierarchically on correlation distance `sqrt(0.5 * (1 - corr))`.
    2. Compute regularized intra-cluster minimum-variance weights `w_intra^(c)`.
    3. Project covariance to reduced `K x K` inter-cluster covariance `W^T Sigma W`.
    4. Allocate across clusters via HRP/inverse-variance risk parity on `Sigma_reduced`.
    5. Combine `w_i = w_inter[c(i)] * w_intra[i]` with water-filling cap enforcement.
    """
    c = np.asarray(cov, dtype=np.float64)
    k = c.shape[0]
    if k == 0:
        return np.zeros(0, dtype=np.float64)
    if k <= 2:
        return compute_hrp_weights(c, max_single_weight=max_single_weight)

    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    c = 0.5 * (c + c.T) + np.eye(k, dtype=np.float64) * 1e-10
    sd = np.sqrt(np.maximum(np.diag(c), 1e-12))
    corr = np.clip(c / np.outer(sd, sd), -1.0, 1.0)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr)))
    np.fill_diagonal(dist, 0.0)
    link = linkage(squareform(dist, checks=False), method="ward")

    n_cl = min(max(2, int(max_clusters)), max(2, k // 2))
    labels = fcluster(link, t=n_cl, criterion="maxclust")
    uniq = sorted({int(lbl) for lbl in labels})

    n_u = len(uniq)
    w_intra_mat = np.zeros((k, n_u), dtype=np.float64)
    for ci, lbl in enumerate(uniq):
        members = [idx for idx, x in enumerate(labels) if int(x) == lbl]
        sub_cov = c[np.ix_(members, members)]
        sub_w = _minvar_long_only_weights(sub_cov)
        for m_idx, w_val in zip(members, sub_w, strict=True):
            w_intra_mat[m_idx, ci] = float(w_val)

    cov_reduced = w_intra_mat.T @ c @ w_intra_mat
    cov_reduced = 0.5 * (cov_reduced + cov_reduced.T) + np.eye(n_u, dtype=np.float64) * 1e-10
    if n_u <= 2:
        d_red = np.maximum(np.diag(cov_reduced), 1e-12)
        w_inter = (1.0 / d_red) / float(np.sum(1.0 / d_red))
    else:
        w_inter = compute_hrp_weights(cov_reduced, max_single_weight=1.0)

    w_raw = w_intra_mat @ w_inter
    return _waterfill_cap_weights(w_raw, max_single_weight=max_single_weight)


def _waterfill_cap_weights(raw_w: np.ndarray, *, max_single_weight: float = 0.35) -> np.ndarray:
    """Normalize nonnegative weights with strict `<= max_single_weight` per asset."""
    w = np.maximum(np.nan_to_num(np.asarray(raw_w, dtype=np.float64), nan=0.0), 0.0)
    n = len(w)
    if n == 0:
        return w
    s = float(np.sum(w))
    if s <= _EPS:
        w = np.full(n, 1.0 / float(n), dtype=np.float64)
    else:
        w = w / s
    cap = float(max_single_weight)
    if cap >= 1.0:
        return w
    budget = min(1.0, float(n) * cap)
    w = w * budget
    for _ in range(30):
        over = w > cap + 1e-12
        if not np.any(over):
            break
        excess = float(np.sum(w[over] - cap))
        w[over] = cap
        under = w < cap - 1e-12
        if not np.any(under):
            break
        u_sum = float(np.sum(w[under]))
        if u_sum > _EPS:
            w[under] += excess * (w[under] / u_sum)
        else:
            w[under] += excess / float(np.sum(under))
    w = np.clip(w, 0.0, cap)
    tot = float(np.sum(w))
    if tot > 1.0 + 1e-12:
        w /= tot
    return w


def fit_sjm_2state_causal(
    features_window: np.ndarray,
    raw_returns_window: np.ndarray,
    *,
    jump_lambda: float = 50.0,
    max_iter: int = 15,
) -> np.ndarray:
    """Pure-NumPy vectorized 2-state Statistical Jump Model (Shu, Yu & Mulvey 2024).

    Parameters
    ----------
    features_window : (W, K, D) array
        Strictly causal historical standardized features for `W` past days across `K` assets.
        Standardization is performed strictly within the window `[t-W+1, t]`.
    raw_returns_window : (W, K) array
        Corresponding historical daily returns used deterministically to label State 0 (Calm/Bull)
        vs State 1 (Turbulent/Bear) with zero label-switching ambiguity.
    jump_lambda : float
        Nonnegative jump penalty `lambda` penalizing each state switch `s_tau != s_{tau-1}`.

    Returns
    -------
    states_t : (K,) int32 array
        Inferred regime at right endpoint `t` (`W - 1`): `0` = Calm/Bull, `1` = Turbulent/Bear.
    """
    lam = _require_finite_float(jump_lambda, "jump_lambda", lo=0.0)
    x = np.asarray(features_window, dtype=np.float64)
    r = np.asarray(raw_returns_window, dtype=np.float64)
    if x.ndim != 3:
        raise ValueError(f"features_window must be 3D (W, K, D), got {x.shape}")
    w_len, n_k, n_d = x.shape
    if r.shape != (w_len, n_k):
        raise ValueError(f"raw_returns_window shape {r.shape} != ({w_len}, {n_k})")
    if w_len < 20 or n_k == 0:
        return np.zeros(n_k, dtype=np.int32)

    # Window-local standardization (strictly <= t, zero look-ahead)
    x_clean = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    mu_win = np.mean(x_clean, axis=0, keepdims=True)
    sd_win = np.std(x_clean, axis=0, keepdims=True)
    sd_win = np.where(sd_win > 1e-8, sd_win, 1.0)
    z = np.clip((x_clean - mu_win) / sd_win, -5.0, 5.0)  # (W, K, D)

    # Deterministic initial partition: higher risk score (feature 2 = vol/downside - feature 0 = ret) -> state 1
    if n_d >= 3:
        init_risk = z[:, :, 2] - 0.5 * (z[:, :, 0] + z[:, :, 1])
    else:
        init_risk = -z[:, :, 0]
    med_risk = np.median(init_risk, axis=0, keepdims=True)
    states = (init_risk > med_risk).astype(np.int32)  # (W, K)

    # Coordinate descent alternating centroids & exact Viterbi DP
    for _ in range(int(max_iter)):
        m0 = states == 0
        m1 = states == 1
        c0 = np.maximum(np.sum(m0, axis=0), 1)[:, None]  # (K, 1)
        c1 = np.maximum(np.sum(m1, axis=0), 1)[:, None]
        mu0 = np.sum(z * m0[:, :, None], axis=0) / c0  # (K, D)
        mu1 = np.sum(z * m1[:, :, None], axis=0) / c1  # (K, D)

        # Squared Euclidean distances to each centroid: (W, K)
        d0 = np.sum((z - mu0[None, :, :]) ** 2, axis=2)
        d1 = np.sum((z - mu1[None, :, :]) ** 2, axis=2)

        # Vectorized forward Viterbi DP across all K assets
        v0 = d0[0].copy()
        v1 = d1[0].copy()
        ptr0 = np.zeros((w_len, n_k), dtype=np.int8)
        ptr1 = np.zeros((w_len, n_k), dtype=np.int8)

        for tau in range(1, w_len):
            stay0 = v0
            jump10 = v1 + lam
            from1_to0 = jump10 < stay0
            ptr0[tau] = from1_to0.astype(np.int8)
            new_v0 = d0[tau] + np.where(from1_to0, jump10, stay0)

            stay1 = v1
            jump01 = v0 + lam
            from0_to1 = jump01 < stay1
            ptr1[tau] = np.where(from0_to1, 0, 1).astype(np.int8)
            new_v1 = d1[tau] + np.where(from0_to1, jump01, stay1)

            v0 = new_v0
            v1 = new_v1

        new_states = np.empty((w_len, n_k), dtype=np.int32)
        cur = (v1 < v0).astype(np.int32)
        new_states[w_len - 1] = cur
        for tau in range(w_len - 1, 0, -1):
            cur = np.where(cur == 0, ptr0[tau], ptr1[tau]).astype(np.int32)
            new_states[tau - 1] = cur

        if np.array_equal(new_states, states):
            break
        states = new_states

    # Deterministic label resolution: State 1 (Turbulent/Bear) = lower mean return (or higher downside risk)
    r_clean = np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0)
    last_states = states[-1].copy()
    out = np.zeros(n_k, dtype=np.int32)
    for j in range(n_k):
        s_j = states[:, j]
        n0 = int(np.sum(s_j == 0))
        n1 = int(np.sum(s_j == 1))
        if n0 == 0 or n1 == 0:
            # Single-state window: classify bear iff trailing 63d return < 0 AND vol elevated
            r_tail = r_clean[-min(63, w_len) :, j]
            out[j] = 1 if float(np.sum(r_tail)) < 0.0 else 0
            continue
        mean_r0 = float(np.mean(r_clean[s_j == 0, j]))
        mean_r1 = float(np.mean(r_clean[s_j == 1, j]))
        vol_r0 = float(np.std(r_clean[s_j == 0, j]))
        vol_r1 = float(np.std(r_clean[s_j == 1, j]))
        # Risk-adjusted score: higher return / lower vol = Calm (0)
        score0 = mean_r0 * 252.0 - 0.5 * vol_r0 * math.sqrt(252.0)
        score1 = mean_r1 * 252.0 - 0.5 * vol_r1 * math.sqrt(252.0)
        calm_label = 0 if score0 >= score1 else 1
        out[j] = 0 if int(last_states[j]) == calm_label else 1
    return out


# ---------------------------------------------------------------------------
# Causal Feature & Weight Builders for FRONTIER_01, FRONTIER_02, FRONTIER_03
# ---------------------------------------------------------------------------


def _new_month_flags_causal(dates: Sequence[str]) -> np.ndarray:
    """Strictly causal first-trading-day-of-month flag (depends ONLY on `<= t`)."""
    n = len(dates)
    flags = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if dates[i][:7] != dates[i - 1][:7]:
            flags[i] = True
    return flags


def _compute_etf_daily_returns(px: np.ndarray) -> np.ndarray:
    """Compute strictly causal daily simple returns without forward-filling NaNs."""
    n_t, n_k = px.shape
    if np.any(np.isinf(px)) or np.any(np.where(np.isfinite(px), px <= 0.0, False)):
        raise ValueError("ETF adjclose contains non-positive or infinite prices")
    rets = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok = np.isfinite(px[1:]) & np.isfinite(px[:-1]) & (px[:-1] > 0.0)
    rets[1:][ok] = px[1:][ok] / px[:-1][ok] - 1.0
    return rets


def _build_frontier_01_weights(
    panel: Mapping[str, Any],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """Build strictly causal `FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY` target weights."""
    dates: list[str] = list(panel["dates"])
    syms: list[str] = [_canonical_symbol(s) for s in panel["symbols"]]
    px = np.asarray(panel["adjclose"], dtype=np.float64)
    n_t, n_k = px.shape
    sym_idx = {s: i for i, s in enumerate(syms)}

    allocator = _require_non_empty_str(params.get("allocator", "nco"), "allocator")
    if allocator not in ("nco", "hrp"):
        raise ValueError(f"FRONTIER_01 allocator must be 'nco' or 'hrp', got {allocator!r}")
    jump_lambda = _require_finite_float(params.get("jump_lambda", 50.0), "jump_lambda", lo=0.0, hi=1000.0)
    rebal_freq = _require_non_empty_str(params.get("rebal_freq", "monthly"), "rebal_freq")
    if rebal_freq not in ("monthly", "biweekly", "weekly"):
        raise ValueError(f"FRONTIER_01 rebal_freq must be monthly/biweekly/weekly, got {rebal_freq!r}")
    sjm_window = _require_int(params.get("sjm_window", 252), "sjm_window", lo=60, hi=756)
    cov_window = _require_int(params.get("cov_window", 126), "cov_window", lo=40, hi=504)
    bear_scale = _require_finite_float(params.get("bear_scale", 0.0), "bear_scale", lo=0.0, hi=1.0)
    target_vol = _require_finite_float(params.get("target_vol", 0.10), "target_vol", lo=0.02, hi=0.40)
    deadband = _require_finite_float(params.get("deadband", 0.05), "deadband", lo=0.0, hi=0.50)
    safe_harbor = _require_non_empty_str(params.get("safe_harbor", "bil_cash"), "safe_harbor")
    if safe_harbor not in ("bil_cash", "cash"):
        raise ValueError(f"FRONTIER_01 safe_harbor must be 'bil_cash' or 'cash', got {safe_harbor!r}")
    max_single = _require_finite_float(params.get("max_single_weight", 0.30), "max_single_weight", lo=0.10, hi=1.0)

    rets = _compute_etf_daily_returns(px)

    # Precompute strictly causal 3-channel SJM features per asset: (T, K, 3)
    # Ch0: 21d EWMA return, Ch1: 63d EWMA return, Ch2: 21d EWMA downside semideviation
    feats = np.full((n_t, n_k, 3), np.nan, dtype=np.float64)
    a21 = 2.0 / (21.0 + 1.0)
    a63 = 2.0 / (63.0 + 1.0)
    for j in range(n_k):
        e21 = math.nan
        e63 = math.nan
        dd21 = math.nan
        streak = 0
        for t in range(1, n_t):
            rt = rets[t, j]
            if not math.isfinite(rt):
                e21 = math.nan
                e63 = math.nan
                dd21 = math.nan
                streak = 0
                continue
            neg_sq = min(0.0, rt) ** 2
            if not math.isfinite(e21):
                e21 = rt
                e63 = rt
                dd21 = neg_sq
                streak = 1
            else:
                e21 = a21 * rt + (1.0 - a21) * e21
                e63 = a63 * rt + (1.0 - a63) * e63
                dd21 = a21 * neg_sq + (1.0 - a21) * dd21
                streak += 1
            if streak >= 21:
                feats[t, j, 0] = e21
                feats[t, j, 1] = e63
                feats[t, j, 2] = math.sqrt(max(dd21, 0.0))

    cash_like = {"BIL", "SHY"}
    risk_asset_js = [j for j, s in enumerate(syms) if (not _is_signal_only(s)) and (s not in cash_like)]
    bil_j = sym_idx.get("BIL")
    shy_j = sym_idx.get("SHY")

    is_new_month = _new_month_flags_causal(dates)
    step_days = 5 if rebal_freq == "weekly" else (10 if rebal_freq == "biweekly" else 0)

    w_out = np.zeros((n_t, n_k), dtype=np.float64)
    last_w = np.zeros(n_k, dtype=np.float64)
    min_warmup = max(cov_window, 63) + 1
    rebal_count = 0

    for t in range(min_warmup, n_t):
        do_rebal = bool(is_new_month[t]) if rebal_freq == "monthly" else (t % step_days == 0)
        if not do_rebal:
            # Zero out any asset whose price is missing at t (strict zero-backfill invariant)
            cur_w = np.where(np.isfinite(px[t]) & (px[t] > 0.0), last_w, 0.0)
            w_out[t] = cur_w
            continue

        # Identify risk assets eligible at day t (finite price & >= cov_window valid returns <= t)
        elig_js: list[int] = []
        r_slice_all = rets[t - cov_window + 1 : t + 1]
        for j in risk_asset_js:
            if not (math.isfinite(px[t, j]) and px[t, j] > 0.0):
                continue
            valid_cov = int(np.sum(np.isfinite(r_slice_all[:, j])))
            if valid_cov < max(40, int(0.85 * cov_window)):
                continue
            valid_f = int(np.sum(np.isfinite(feats[max(0, t - sjm_window + 1) : t + 1, j, 0])))
            if valid_f >= 40:
                elig_js.append(j)

        tmp = np.zeros(n_k, dtype=np.float64)
        if elig_js:
            w_start = max(0, t - sjm_window + 1)
            f_win = feats[w_start : t + 1, elig_js, :]
            r_win = rets[w_start : t + 1, elig_js]
            states_t = fit_sjm_2state_causal(f_win, r_win, jump_lambda=jump_lambda)

            cov_sub_r = np.nan_to_num(r_slice_all[:, elig_js], nan=0.0)
            cov_mat = _shrink_covariance(cov_sub_r, shrink_alpha=0.20)

            # Compute NCO or HRP base risk-parity weights across eligible risk assets
            if allocator == "nco":
                base_w = compute_nco_weights(cov_mat, max_clusters=5, max_single_weight=max_single)
            else:
                base_w = compute_hrp_weights(cov_mat, max_single_weight=max_single)

            # Regime-conditioned scaling: assets in SJM turbulent/bear state (1) scale down by bear_scale
            regime_mult = np.where(states_t == 0, 1.0, bear_scale)
            adj_w = base_w * regime_mult

            # Portfolio ex-ante annualized volatility targeting (cash-only: no leverage > 1.0)
            sum_adj = float(np.sum(adj_w))
            if sum_adj > _EPS:
                port_var_daily = float(adj_w @ cov_mat @ adj_w)
                port_vol_ann = math.sqrt(max(port_var_daily, 1e-12)) * math.sqrt(252.0)
                vol_scale = min(1.0 / max(sum_adj, 1.0), target_vol / max(port_vol_ann, 1e-6))
                vol_scale = min(1.0, max(0.0, vol_scale))
                final_risk_w = adj_w * vol_scale
                tot_risk = float(np.sum(final_risk_w))
                if tot_risk > 1.0:
                    final_risk_w /= tot_risk
                    tot_risk = 1.0
                for local_i, j in enumerate(elig_js):
                    tmp[j] = float(final_risk_w[local_i])
            else:
                tot_risk = 0.0
        else:
            tot_risk = 0.0

        # Park residual cash budget safely (BIL when listed, else SHY when listed, else 0% cash)
        residual = max(0.0, 1.0 - tot_risk)
        if safe_harbor == "bil_cash" and residual > 1e-6:
            if bil_j is not None and math.isfinite(px[t, bil_j]) and px[t, bil_j] > 0.0:
                tmp[bil_j] += residual
            elif shy_j is not None and math.isfinite(px[t, shy_j]) and px[t, shy_j] > 0.0:
                # Only use SHY if causal 63d return >= 0 (protects against rate spikes)
                if t >= 63 and math.isfinite(px[t - 63, shy_j]) and px[t, shy_j] >= px[t - 63, shy_j]:
                    tmp[shy_j] += residual

        # Hard zero on any signal-only ticker
        for j, s in enumerate(syms):
            if _is_signal_only(s):
                tmp[j] = 0.0

        # L1 deadband to curb turnover
        l1_diff = float(np.sum(np.abs(tmp - last_w)))
        if l1_diff >= deadband or float(np.sum(last_w)) <= _EPS:
            last_w = tmp
            rebal_count += 1
        w_out[t] = last_w

    return {
        "target_w": w_out,
        "rebal_events": rebal_count,
        "max_gross_leverage": 1.0,
    }


def _build_frontier_02_weights(
    panel: Mapping[str, Any],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """Build strictly causal `FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR` target weights."""
    syms: list[str] = [_canonical_symbol(s) for s in panel["symbols"]]
    px = np.asarray(panel["adjclose"], dtype=np.float64)
    n_t, n_k = px.shape
    sym_idx = {s: i for i, s in enumerate(syms)}

    scaling = _require_non_empty_str(params.get("scaling", "inv_var"), "scaling")
    if scaling not in ("inv_var", "inv_vol", "cov_mfm"):
        raise ValueError(f"FRONTIER_02 scaling must be inv_var/inv_vol/cov_mfm, got {scaling!r}")
    r_enter = _require_finite_float(params.get("r_enter", 0.95), "r_enter", lo=0.70, hi=1.10)
    r_exit = _require_finite_float(params.get("r_exit", 1.02), "r_exit", lo=0.80, hi=1.30)
    if r_exit <= r_enter:
        raise ValueError(f"r_exit ({r_exit}) must be > r_enter ({r_enter})")
    vix_smooth = _require_int(params.get("vix_smooth", 5), "vix_smooth", lo=1, hi=30)
    vol_lookback = _require_int(params.get("vol_lookback", 21), "vol_lookback", lo=10, hi=126)
    target_vol = _require_finite_float(params.get("target_vol", 0.10), "target_vol", lo=0.03, hi=0.35)
    deadband = _require_finite_float(params.get("deadband", 0.15), "deadband", lo=0.0, hi=0.50)
    rebal_days = _require_int(params.get("rebal_days", 5), "rebal_days", lo=1, hi=63)
    safe_harbor = _require_non_empty_str(params.get("safe_harbor", "bil_shy"), "safe_harbor")
    if safe_harbor not in ("bil_shy", "cash"):
        raise ValueError(f"FRONTIER_02 safe_harbor must be 'bil_shy' or 'cash', got {safe_harbor!r}")
    def_gld_cap = _require_finite_float(params.get("def_gld_cap", 0.10), "def_gld_cap", lo=0.0, hi=0.40)

    rets = _compute_etf_daily_returns(px)

    vix_j = sym_idx.get("IDX_VIX")
    vix3m_j = sym_idx.get("IDX_VIX3M")
    eq_factors = [sym_idx[s] for s in ("SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV") if s in sym_idx]
    bil_j = sym_idx.get("BIL")
    shy_j = sym_idx.get("SHY")
    gld_j = sym_idx.get("GLD")
    tip_j = sym_idx.get("TIP")

    # Strictly causal VIX term-structure ratio R_t = VIX / VIX3M (with causal fallback if VIX3M NaN)
    raw_ratio = np.full(n_t, np.nan, dtype=np.float64)
    vix_level = np.full(n_t, np.nan, dtype=np.float64)
    if vix_j is not None:
        vix_level = px[:, vix_j].copy()
        for t in range(n_t):
            v = px[t, vix_j]
            if not (math.isfinite(v) and v > 0.0):
                continue
            if vix3m_j is not None and math.isfinite(px[t, vix3m_j]) and px[t, vix3m_j] > 0.0:
                raw_ratio[t] = v / px[t, vix3m_j]
            elif t >= 59:
                win = px[t - 59 : t + 1, vix_j]
                if int(np.sum(np.isfinite(win))) >= 45:
                    raw_ratio[t] = v / max(float(np.nanmean(win)), 1e-6)

    # Strictly causal SMA smoothing of term ratio
    smooth_ratio = np.full(n_t, np.nan, dtype=np.float64)
    for t in range(vix_smooth - 1, n_t):
        win = raw_ratio[t - vix_smooth + 1 : t + 1]
        if int(np.sum(np.isfinite(win))) >= max(1, vix_smooth - 1):
            smooth_ratio[t] = float(np.nanmean(win))

    # Strictly causal SMA126 for defensive GLD / TIP trend gate
    sma126 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for t in range(125, n_t):
            w126 = px[t - 125 : t + 1]
            ok126 = np.sum(np.isfinite(w126), axis=0) >= 120
            sma126[t] = np.where(ok126, np.nanmean(w126, axis=0), np.nan)

    # Strictly causal rolling realized volatility for equity factors
    roll_vol = np.full((n_t, n_k), np.nan, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for t in range(vol_lookback, n_t):
            rw = rets[t - vol_lookback + 1 : t + 1]
            cnt = np.sum(np.isfinite(rw), axis=0)
            sd = np.nanstd(rw, axis=0, ddof=1)
            min_obs = max(8, int(0.85 * vol_lookback))
            roll_vol[t] = np.where((cnt >= min_obs) & (sd > 1e-6), sd * math.sqrt(252.0), np.nan)

    w_out = np.zeros((n_t, n_k), dtype=np.float64)
    last_w = np.zeros(n_k, dtype=np.float64)
    risk_on = False
    rebal_count = 0
    min_warmup = max(vol_lookback, 63) + 1

    for t in range(min_warmup, n_t):
        rt = smooth_ratio[t]
        vl = vix_level[t]
        prev_risk_on = risk_on
        if math.isfinite(rt) and math.isfinite(vl):
            if risk_on:
                if rt >= r_exit or vl >= 32.0:
                    risk_on = False
            else:
                if rt <= r_enter and vl < 26.0:
                    risk_on = True
        else:
            risk_on = False

        regime_flipped = risk_on != prev_risk_on
        do_check = regime_flipped or (t % rebal_days == 0)

        if not do_check:
            cur_w = np.where(np.isfinite(px[t]) & (px[t] > 0.0), last_w, 0.0)
            # Enforce zero signal-only weights unconditionally
            for j, s in enumerate(syms):
                if _is_signal_only(s):
                    cur_w[j] = 0.0
            w_out[t] = cur_w
            continue

        tmp = np.zeros(n_k, dtype=np.float64)
        eq_exposure = 0.0

        if risk_on and eq_factors:
            elig_eq = [
                j
                for j in eq_factors
                if (
                    math.isfinite(px[t, j])
                    and px[t, j] > 0.0
                    and math.isfinite(roll_vol[t, j])
                    and roll_vol[t, j] > 0.02
                )
            ]
            if elig_eq:
                vols = np.array([max(0.06, float(roll_vol[t, j])) for j in elig_eq], dtype=np.float64)
                if scaling == "inv_var":
                    raw_f = 1.0 / (vols**2)
                    w_eq_rel = raw_f / float(np.sum(raw_f))
                elif scaling == "inv_vol":
                    raw_f = 1.0 / vols
                    w_eq_rel = raw_f / float(np.sum(raw_f))
                else:
                    # cov_mfm: joint multifactor covariance inverse-variance / min-var
                    cov_lb = max(vol_lookback, 42)
                    if t >= cov_lb:
                        r_eq = np.nan_to_num(rets[t - cov_lb + 1 : t + 1, elig_eq], nan=0.0)
                        cov_eq = _shrink_covariance(r_eq, shrink_alpha=0.25)
                        w_eq_rel = _minvar_long_only_weights(cov_eq)
                    else:
                        raw_f = 1.0 / (vols**2)
                        w_eq_rel = raw_f / float(np.sum(raw_f))

                w_eq_rel = _waterfill_cap_weights(w_eq_rel, max_single_weight=0.35)

                # Joint portfolio realized volatility (Moreira-Muir + DeMiguel et al. 2024)
                r_eq_win = np.nan_to_num(rets[t - vol_lookback + 1 : t + 1, elig_eq], nan=0.0)
                cov_cur = _shrink_covariance(r_eq_win, shrink_alpha=0.15)
                port_vol_ann = math.sqrt(max(float(w_eq_rel @ cov_cur @ w_eq_rel), 1e-12)) * math.sqrt(252.0)

                # Forward-looking term-structure slope scalar in [0.4, 1.0] while risk_on
                contango_margin = max(0.0, r_exit - float(rt)) / max(r_exit - 0.85, 0.05)
                vrp_mult = float(np.clip(0.45 + 0.55 * contango_margin, 0.45, 1.0))

                if scaling == "inv_var":
                    # Variance-managed scaling capped cleanly in [0, 1]
                    vol_mult = min(1.0, (target_vol / max(port_vol_ann, 0.04)) ** 1.5)
                else:
                    vol_mult = min(1.0, target_vol / max(port_vol_ann, 0.04))

                eq_exposure = float(np.clip(vrp_mult * vol_mult, 0.0, 1.0))
                for local_i, j in enumerate(elig_eq):
                    tmp[j] = eq_exposure * float(w_eq_rel[local_i])

        # Remaining defensive budget -> trend-gated GLD/TIP (capped) + BIL/SHY safe-harbor (ZERO TLT!)
        rem = max(0.0, 1.0 - eq_exposure)
        if def_gld_cap > 0.0 and rem > 1e-6:
            gld_alloc = 0.0
            if gld_j is not None and math.isfinite(px[t, gld_j]) and math.isfinite(sma126[t, gld_j]):
                if px[t, gld_j] > sma126[t, gld_j]:
                    gld_alloc = min(rem, def_gld_cap)
                    tmp[gld_j] += gld_alloc
                    rem -= gld_alloc
            if rem > 1e-6 and tip_j is not None and math.isfinite(px[t, tip_j]) and math.isfinite(sma126[t, tip_j]):
                if px[t, tip_j] > sma126[t, tip_j]:
                    tip_alloc = min(rem, 0.5 * def_gld_cap)
                    tmp[tip_j] += tip_alloc
                    rem -= tip_alloc

        if safe_harbor == "bil_shy" and rem > 1e-6:
            if bil_j is not None and math.isfinite(px[t, bil_j]) and px[t, bil_j] > 0.0:
                tmp[bil_j] += rem
            elif shy_j is not None and math.isfinite(px[t, shy_j]) and px[t, shy_j] > 0.0:
                tmp[shy_j] += rem

        # Hard zero on signal-only volatility indices
        for j, s in enumerate(syms):
            if _is_signal_only(s):
                tmp[j] = 0.0

        # Apply L1 rebalancing deadband (always allow immediate de-risk on regime flip to Risk-Off!)
        l1_diff = float(np.sum(np.abs(tmp - last_w)))
        crash_exit = (not risk_on) and prev_risk_on
        if crash_exit or l1_diff >= deadband or float(np.sum(last_w)) <= _EPS:
            last_w = tmp
            rebal_count += 1
        w_out[t] = last_w

    return {
        "target_w": w_out,
        "rebal_events": rebal_count,
        "max_gross_leverage": 1.0,
    }


def _invvol_capped_dict(
    active_idxs: Sequence[int],
    vol_row: np.ndarray,
    *,
    max_single: float = 0.25,
) -> dict[int, float]:
    if not active_idxs:
        return {}
    vols = np.array(
        [max(0.005, float(vol_row[j])) if math.isfinite(float(vol_row[j])) else 0.04 for j in active_idxs],
        dtype=np.float64,
    )
    w = _waterfill_cap_weights(1.0 / vols, max_single_weight=max_single)
    return {int(active_idxs[i]): float(w[i]) for i in range(len(active_idxs))}


def _zscore_cross_section(vals: Mapping[int, float]) -> dict[int, float]:
    if not vals:
        return {}
    arr = np.array(list(vals.values()), dtype=np.float64)
    mu = float(np.mean(arr))
    sd = float(np.std(arr))
    if sd <= 1e-12:
        return {k: 0.0 for k in vals}
    return {k: float(np.clip((v - mu) / sd, -3.0, 3.0)) for k, v in vals.items()}


def _build_frontier_03_weights(
    panel: Mapping[str, Any],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """Build strictly causal `FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM` target notional weights."""
    syms: list[str] = list(panel["symbols"])
    f_daily = np.asarray(panel["funding_daily"], dtype=np.float64)
    spot_c = np.asarray(panel["spot_close"], dtype=np.float64)
    perp_c = np.asarray(panel["perp_close"], dtype=np.float64)
    pos_8h = np.asarray(panel["pos_8h_cnt"], dtype=np.int32)
    tot_8h = np.asarray(panel["tot_8h_cnt"], dtype=np.int32)
    perp_qv = np.asarray(panel["perp_quote_vol"], dtype=np.float64)
    h4_trend = (
        np.asarray(panel["h4_trend"], dtype=np.float64)
        if "h4_trend" in panel and panel["h4_trend"] is not None
        else np.full_like(spot_c, np.nan)
    )
    n_t, n_k = f_daily.shape

    k_max = _require_int(params.get("k_max", 6), "k_max", lo=1, hi=20)
    keep_rank = _require_int(params.get("keep_rank", 10), "keep_rank", lo=k_max, hi=20)
    enter_ann = _require_finite_float(params.get("enter_ann", 0.08), "enter_ann", lo=0.0, hi=1.0)
    exit_ann = _require_finite_float(params.get("exit_ann", 0.01), "exit_ann", lo=-0.20, hi=enter_ann)
    rebal_days = _require_int(params.get("rebal_days", 7), "rebal_days", lo=1, hi=30)
    w_fund = _require_finite_float(params.get("w_fund", 0.60), "w_fund", lo=0.0, hi=1.0)
    w_basis = _require_finite_float(params.get("w_basis", 0.20), "w_basis", lo=0.0, hi=1.0)
    w_mom = _require_finite_float(params.get("w_mom", 0.20), "w_mom", lo=0.0, hi=1.0)
    mom_lb = _require_int(params.get("mom_lb", 21), "mom_lb", lo=7, hi=90)
    equity_buffer = _require_finite_float(params.get("equity_buffer", 2.0), "equity_buffer", lo=2.0, hi=4.0)
    max_single = _require_finite_float(params.get("max_single", 0.25), "max_single", lo=0.05, hi=0.50)
    deadband = _require_finite_float(params.get("deadband", 0.06), "deadband", lo=0.0, hi=0.40)
    mom_gate = _require_bool(bool(params.get("mom_gate", False)), "mom_gate")
    use_4h_confirm = _require_bool(bool(params.get("use_4h_confirm", False)), "use_4h_confirm")
    neg_med_brake = _require_bool(bool(params.get("neg_med_brake", False)), "neg_med_brake")
    min_persist14 = _require_finite_float(params.get("min_persist14", 0.0), "min_persist14", lo=0.0, hi=1.0)
    bear_scale = _require_finite_float(params.get("bear_scale", 1.0), "bear_scale", lo=0.10, hi=1.0)

    # Validate non-poisoned prices
    for arr_name, arr in (("spot_close", spot_c), ("perp_close", perp_c)):
        if np.any(np.isinf(arr)) or np.any(np.where(np.isfinite(arr), arr <= 0.0, False)):
            raise ValueError(f"{arr_name} contains non-positive or infinite values")

    # Tradable mask strictly at day t (zero pre-listing allocation)
    tradable = (
        np.isfinite(f_daily)
        & np.isfinite(spot_c)
        & (spot_c > 0.0)
        & np.isfinite(perp_c)
        & (perp_c > 0.0)
        & (tot_8h > 0)
    )

    # Causal rolling funding (3d, 7d, 14d), persistence14, basis (7d), slow momentum (mom_lb), vol20, liquidity dv30
    roll3 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    roll7 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    roll14 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    persist14 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    basis_daily = np.where(
        np.isfinite(perp_c) & np.isfinite(spot_c) & (perp_c > 0.0) & (spot_c > 0.0),
        np.log(perp_c / np.maximum(spot_c, 1e-12)),
        np.nan,
    )
    roll_basis7 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    slow_mom = np.full((n_t, n_k), np.nan, dtype=np.float64)
    dv30 = np.full((n_t, n_k), np.nan, dtype=np.float64)

    perp_ret = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok_p = np.isfinite(perp_c[1:]) & np.isfinite(perp_c[:-1]) & (perp_c[:-1] > 0.0)
    perp_ret[1:][ok_p] = perp_c[1:][ok_p] / perp_c[:-1][ok_p] - 1.0
    vol20 = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for t in range(n_t):
        if t >= 2:
            w3 = f_daily[t - 2 : t + 1]
            v3 = np.isfinite(w3)
            c3 = np.sum(v3, axis=0)
            roll3[t] = np.where(c3 >= 3, np.sum(np.where(v3, w3, 0.0), axis=0) / np.maximum(1, c3), np.nan)
        if t >= 6:
            w7 = f_daily[t - 6 : t + 1]
            v7 = np.isfinite(w7)
            c7 = np.sum(v7, axis=0)
            roll7[t] = np.where(c7 >= 6, np.sum(np.where(v7, w7, 0.0), axis=0) / np.maximum(1, c7), np.nan)

            b7 = basis_daily[t - 6 : t + 1]
            vb7 = np.isfinite(b7)
            cb7 = np.sum(vb7, axis=0)
            roll_basis7[t] = np.where(cb7 >= 5, np.sum(np.where(vb7, b7, 0.0), axis=0) / np.maximum(1, cb7), np.nan)
        if t >= 13:
            w14 = f_daily[t - 13 : t + 1]
            v14 = np.isfinite(w14)
            c14 = np.sum(v14, axis=0)
            roll14[t] = np.where(c14 >= 12, np.sum(np.where(v14, w14, 0.0), axis=0) / np.maximum(1, c14), np.nan)
            t14 = np.sum(tot_8h[t - 13 : t + 1], axis=0)
            p14 = np.sum(pos_8h[t - 13 : t + 1], axis=0)
            persist14[t] = np.where(t14 >= 36, p14 / np.maximum(1, t14), np.nan)
        if t >= 19:
            wr = perp_ret[t - 19 : t + 1]
            for j in range(n_k):
                vals = wr[:, j]
                vals = vals[np.isfinite(vals)]
                if len(vals) >= 12:
                    vol20[t, j] = max(0.005, float(np.std(vals, ddof=1)))
        if t >= mom_lb:
            ok_m = np.isfinite(spot_c[t]) & np.isfinite(spot_c[t - mom_lb]) & (spot_c[t - mom_lb] > 0.0)
            raw_m = np.where(ok_m, spot_c[t] / np.maximum(spot_c[t - mom_lb], 1e-12) - 1.0, np.nan)
            v_denom = np.where(np.isfinite(vol20[t]), vol20[t] * math.sqrt(float(mom_lb)), 0.15)
            slow_mom[t] = np.where(ok_m, raw_m / np.maximum(v_denom, 0.05), np.nan)
        if t >= 14:
            lo_q = max(0, t - 29)
            wq = perp_qv[lo_q : t + 1]
            vq = np.isfinite(wq)
            cq = np.sum(vq, axis=0)
            dv30[t] = np.where(cq >= 15, np.sum(np.where(vq, wq, 0.0), axis=0) / np.maximum(1, cq), np.nan)

    # Strictly causal BTC EMA(200) bear guard & cross-sectional median 3d funding
    btc_idx = syms.index("BTCUSDT") if "BTCUSDT" in syms else 0
    btc_px = np.where(
        np.isfinite(spot_c[:, btc_idx]) & (spot_c[:, btc_idx] > 0.0),
        spot_c[:, btc_idx],
        perp_c[:, btc_idx],
    )
    btc_ema200 = np.full(n_t, np.nan, dtype=np.float64)
    alpha_ema = 2.0 / (200.0 + 1.0)
    ema_v = math.nan
    for t in range(n_t):
        px_b = btc_px[t]
        if math.isfinite(px_b) and px_b > 0.0:
            ema_v = float(px_b) if not math.isfinite(ema_v) else (alpha_ema * float(px_b) + (1.0 - alpha_ema) * ema_v)
            btc_ema200[t] = ema_v

    med_fund3 = np.full(n_t, np.nan, dtype=np.float64)
    for t in range(n_t):
        vals = roll3[t, tradable[t]]
        vals = vals[np.isfinite(vals)]
        if len(vals) >= 2:
            med_fund3[t] = float(np.median(vals))

    enter_d = enter_ann / 365.0
    exit_d = exit_ann / 365.0

    w_out = np.zeros((n_t, n_k), dtype=np.float64)
    held: set[int] = set()
    prev_w: dict[int, float] = {}
    rebal_count = 0
    min_warmup = max(21, mom_lb)

    for t in range(min_warmup, n_t):
        # Emergency daily funding brake if enabled and median 3d funding turns negative
        if neg_med_brake and math.isfinite(med_fund3[t]) and med_fund3[t] < 0.0:
            if held:
                rebal_count += 1
            held = set()
            prev_w = {}
            continue

        # Enforce zero weight if any previously held coin becomes untradable at day t
        held = {j for j in held if tradable[t, j]}

        # Check rebalance cadence (strictly >= D1; weekly/5d/14d keeps turnover <= 6.0x/yr)
        if (t % rebal_days != 0) and prev_w:
            for j, wj in prev_w.items():
                if j in held and tradable[t, j]:
                    w_out[t, j] = wj
            continue

        # Causal Tier-1 liquidity screen: keep top-16 by 30d perp quote volume if volume available
        elig = [j for j in range(n_k) if tradable[t, j] and math.isfinite(roll7[t, j])]
        if not elig:
            held = set()
            prev_w = {}
            continue
        if any(math.isfinite(dv30[t, j]) for j in elig):
            elig_ranked = sorted(
                elig,
                key=lambda j: (-(float(dv30[t, j]) if math.isfinite(dv30[t, j]) else 0.0), j),
            )
            elig = elig_ranked[: min(16, len(elig_ranked))]

        # Cross-sectional z-scores strictly at day t
        f_vals = {j: float(roll7[t, j]) for j in elig}
        b_vals = {j: float(roll_basis7[t, j]) if math.isfinite(roll_basis7[t, j]) else 0.0 for j in elig}
        m_vals: dict[int, float] = {}
        for j in elig:
            m_d1 = float(slow_mom[t, j]) if math.isfinite(slow_mom[t, j]) else 0.0
            if use_4h_confirm and math.isfinite(h4_trend[t, j]):
                m_vals[j] = 0.65 * m_d1 + 0.35 * float(h4_trend[t, j])
            else:
                m_vals[j] = m_d1

        zf = _zscore_cross_section(f_vals)
        zb = _zscore_cross_section(b_vals)
        zm = _zscore_cross_section(m_vals)

        composite = [
            (w_fund * zf[j] + w_basis * zb[j] + w_mom * zm[j], j)
            for j in elig
        ]
        composite.sort(key=lambda x: (-x[0], x[1]))
        rank_pos = {j: idx for idx, (_sc, j) in enumerate(composite)}

        # Hysteresis retention for currently held coins
        next_held: set[int] = set()
        for j in held:
            if j not in rank_pos:
                continue
            r7 = float(roll7[t, j])
            if rank_pos[j] < keep_rank and r7 >= exit_d:
                if (
                    min_persist14 > 0.0
                    and math.isfinite(persist14[t, j])
                    and persist14[t, j] < max(0.50, min_persist14 - 0.15)
                ):
                    continue
                next_held.add(j)

        # Fill open slots up to k_max with high-composite coins passing entry gates
        for _sc, j in composite:
            if len(next_held) >= k_max:
                break
            if j in next_held:
                continue
            if float(roll7[t, j]) <= enter_d:
                continue
            if min_persist14 > 0.0:
                p14 = persist14[t, j]
                if not math.isfinite(p14) or float(p14) < min_persist14:
                    continue
            if mom_gate:
                m_val = m_vals[j]
                if m_val < -0.25:
                    continue
            next_held.add(j)

        held = next_held
        if not held:
            if prev_w:
                rebal_count += 1
            prev_w = {}
            continue

        act = sorted(held)
        w_raw = _invvol_capped_dict(act, vol20[t], max_single=max_single)

        scale = 1.0
        if bear_scale < 1.0 and math.isfinite(btc_px[t]) and math.isfinite(btc_ema200[t]) and btc_px[t] < btc_ema200[t]:
            scale = bear_scale
        w_fresh = {j: wj * scale for j, wj in w_raw.items()}

        # L1 deadband across full weight vector to crush unnecessary churn
        all_keys = set(w_fresh.keys()) | set(prev_w.keys())
        l1_diff = sum(abs(w_fresh.get(j, 0.0) - prev_w.get(j, 0.0)) for j in all_keys)
        if l1_diff >= deadband or set(w_fresh.keys()) != set(prev_w.keys()) or not prev_w:
            prev_w = dict(w_fresh)
            rebal_count += 1

        for j, wj in prev_w.items():
            w_out[t, j] = wj

    return {
        "target_w": w_out,
        "rebal_events": rebal_count,
        "equity_buffer_mult": equity_buffer,
    }


def build_sleeve_weights(
    sleeve_id: str,
    panel: Mapping[str, Any],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """Dispatch strictly causal weight builder for any pre-registered Frontier sleeve."""
    sid = _require_non_empty_str(sleeve_id, "sleeve_id")
    if sid == FRONTIER_01_ID:
        return _build_frontier_01_weights(panel, params)
    if sid == FRONTIER_02_ID:
        return _build_frontier_02_weights(panel, params)
    if sid == FRONTIER_03_ID:
        return _build_frontier_03_weights(panel, params)
    raise ValueError(f"Unsupported sleeve_id={sid!r}")


# ---------------------------------------------------------------------------
# Strictly Causal Simulators (t -> t+1) & Metrics
# ---------------------------------------------------------------------------


def _simulate_etf_causal(
    adjclose: np.ndarray,
    target_w: np.ndarray,
    symbols: Sequence[str],
    *,
    cost_bps_oneway: float = 5.0,
    max_gross_leverage: float = 1.0,
) -> dict[str, Any]:
    """Strictly causal `t -> t+1` cash ETF simulator with zero pre-listing & zero signal-only checks."""
    px = np.asarray(adjclose, dtype=np.float64)
    tw = np.nan_to_num(np.asarray(target_w, dtype=np.float64), nan=0.0)
    n_t, n_k = px.shape
    if tw.shape != (n_t, n_k):
        raise ValueError(f"target_w shape {tw.shape} != adjclose shape {(n_t, n_k)}")

    # Verify signal-only indices receive strictly 0.0 target weight
    sig_max_w = 0.0
    for j, s in enumerate(symbols):
        if _is_signal_only(s):
            sig_max_w = max(sig_max_w, float(np.max(np.abs(tw[:, j]))))
    if sig_max_w > 0.0:
        raise ValueError(f"SIGNAL_ONLY_WEIGHT_VIOLATION: signal-only symbol received weight={sig_max_w}")

    gross_row = np.sum(np.abs(tw), axis=1, keepdims=True)
    tw = np.where(gross_row > max_gross_leverage, tw * (max_gross_leverage / np.maximum(gross_row, _EPS)), tw)

    rets = np.zeros((n_t, n_k), dtype=np.float64)
    valid_ret = np.isfinite(px[1:]) & np.isfinite(px[:-1]) & (px[:-1] > 0.0)
    rets[1:][valid_ret] = px[1:][valid_ret] / px[:-1][valid_ret] - 1.0

    # Pre-listing check on target_w: never allocate to an asset whose price is NaN at day t
    unlisted_target = (~np.isfinite(px)) & (np.abs(tw) > 1e-12)
    pre_listing_violations = int(np.sum(unlisted_target))
    if pre_listing_violations > 0:
        raise ValueError(f"PRE_LISTING_BACKFILL_VIOLATION: {pre_listing_violations} non-zero weights on NaN price rows")

    held = np.zeros_like(tw)
    held[1:] = np.where(valid_ret, tw[:-1], 0.0)

    prev = np.zeros_like(held)
    prev[1:] = held[:-1]
    turnover = np.sum(np.abs(held - prev), axis=1)
    trade_cost = turnover * (float(cost_bps_oneway) / 10_000.0)
    gross_ret = np.sum(held * rets, axis=1)
    net_ret = gross_ret - trade_cost
    return {
        "net_returns": net_ret,
        "gross_returns": gross_ret,
        "turnover": turnover,
        "held_w": held,
        "signal_only_max_abs_weight": sig_max_w,
        "pre_listing_weight_violations": pre_listing_violations,
    }


def _simulate_crypto_carry_causal(
    panel: Mapping[str, Any],
    target_notional_w: np.ndarray,
    *,
    equity_buffer_mult: float = 2.0,
    oneway_pair_cost_bps: float = 20.0,
    basis_cross_slip_bps: float = 3.0,
    exit_shock_mult: float = 1.0,
) -> dict[str, Any]:
    """Strictly causal `t -> t+1` delta-neutral crypto perp carry + basis MTM + exit-shock + Cross-Margin audit."""
    f_daily = np.asarray(panel["funding_daily"], dtype=np.float64)
    spot_c = np.asarray(panel["spot_close"], dtype=np.float64)
    spot_h = np.asarray(panel["spot_high"], dtype=np.float64)
    perp_c = np.asarray(panel["perp_close"], dtype=np.float64)
    perp_h = np.asarray(panel["perp_high"], dtype=np.float64)
    n_t, n_k = f_daily.shape

    notional_cap = 1.0 / max(1.0, float(equity_buffer_mult))
    perp_margin_per_notional = max(0.05, float(equity_buffer_mult) - 1.0)
    liq_threshold_jump = perp_margin_per_notional - 0.05

    tw_raw = np.clip(np.nan_to_num(np.asarray(target_notional_w, dtype=np.float64), nan=0.0), 0.0, 1.0)
    unlisted_mask = (~np.isfinite(f_daily) | ~np.isfinite(spot_c) | ~np.isfinite(perp_c)) & (tw_raw > 1e-12)
    pre_listing_violations = int(np.sum(unlisted_mask))
    if pre_listing_violations > 0:
        raise ValueError(f"PRE_LISTING_CRYPTO_VIOLATION: {pre_listing_violations} non-zero weights on unlisted rows")

    rs = tw_raw.sum(axis=1, keepdims=True)
    tw = np.where(rs > 1.0, tw_raw / np.maximum(rs, _EPS), tw_raw) * notional_cap

    held = np.zeros_like(tw)
    valid_f = np.isfinite(f_daily[1:])
    held[1:] = np.where(valid_f, tw[:-1], 0.0)

    prev = np.zeros_like(held)
    prev[1:] = held[:-1]
    turnover = np.sum(np.abs(held - prev), axis=1)
    total_oneway_bps = float(oneway_pair_cost_bps) + float(basis_cross_slip_bps)
    fee_cost = turnover * (total_oneway_bps / 10_000.0)

    safe_f = np.where(np.isfinite(f_daily), f_daily, 0.0)
    funding_pnl = np.sum(held * safe_f, axis=1)

    r_spot = np.zeros((n_t, n_k), dtype=np.float64)
    r_perp = np.zeros((n_t, n_k), dtype=np.float64)
    ok_both = (
        np.isfinite(spot_c[1:])
        & np.isfinite(spot_c[:-1])
        & (spot_c[:-1] > 0.0)
        & np.isfinite(perp_c[1:])
        & np.isfinite(perp_c[:-1])
        & (perp_c[:-1] > 0.0)
    )
    r_spot[1:][ok_both] = spot_c[1:][ok_both] / spot_c[:-1][ok_both] - 1.0
    r_perp[1:][ok_both] = perp_c[1:][ok_both] / perp_c[:-1][ok_both] - 1.0
    diff_sp = np.clip(r_spot - r_perp, -0.15, 0.15)
    basis_pnl = np.sum(held * diff_sp, axis=1)

    # Adverse negative-funding / basis-widening exit shock penalty (Lab #9 standard)
    exit_notional = np.maximum(0.0, prev - held)
    adverse_rate = np.clip(
        0.5 * np.maximum(0.0, -diff_sp) + np.maximum(0.0, -safe_f),
        0.0,
        0.0025,
    )
    exit_shock_cost = float(exit_shock_mult) * np.sum(exit_notional * adverse_rate, axis=1)

    # Mark-Price Cross-Margin & Isolated-Margin liquidation audit
    mark_high = np.where(np.isfinite(spot_h), np.minimum(perp_h, spot_h), perp_h)
    max_single_jump = 0.0
    max_cross_draw = 0.0
    isolated_liq_events = 0
    cross_liq_events = 0
    for t in range(1, n_t):
        act = held[t] > 1e-6
        if not np.any(act):
            continue
        ok = act & np.isfinite(mark_high[t]) & np.isfinite(perp_c[t - 1]) & (perp_c[t - 1] > 0.0)
        if not np.any(ok):
            continue
        jumps = mark_high[t, ok] / perp_c[t - 1, ok] - 1.0
        mx = float(np.max(jumps))
        max_single_jump = max(max_single_jump, mx)
        if mx >= liq_threshold_jump:
            isolated_liq_events += 1
        spot_used = float(np.sum(held[t]))
        futures_margin_pool = max(1e-6, 1.0 - spot_used)
        worst_short_loss = float(np.sum(held[t, ok] * np.maximum(0.0, jumps)))
        cm_draw = worst_short_loss / futures_margin_pool
        max_cross_draw = max(max_cross_draw, cm_draw)
        if cm_draw >= 0.90:
            cross_liq_events += 1

    gross_ret = funding_pnl + basis_pnl
    net_ret = gross_ret - fee_cost - exit_shock_cost
    return {
        "net_returns": net_ret,
        "gross_returns": gross_ret,
        "funding_pnl": funding_pnl,
        "basis_pnl": basis_pnl,
        "fee_cost": fee_cost,
        "exit_shock_cost": exit_shock_cost,
        "turnover": turnover,
        "held_w": held,
        "max_single_coin_mark_jump_pct": round(max_single_jump * 100.0, 2),
        "max_cross_margin_draw_pct": round(max_cross_draw * 100.0, 2),
        "isolated_liq_events": int(isolated_liq_events),
        "cross_liq_events": int(cross_liq_events),
        "pre_listing_weight_violations": pre_listing_violations,
        "signal_only_max_abs_weight": 0.0,
    }


def compute_series_metrics(returns: np.ndarray, *, ann_days: float = 252.0) -> dict[str, float | int]:
    """Compute CAGR, annualized vol, Sharpe, Sortino, Max DD, Calmar, total net return, and t-test p-value."""
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 5:
        return {
            "n_days": int(n),
            "total_net_return_pct": 0.0,
            "cagr_pct": 0.0,
            "ann_vol_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd_pct": 0.0,
            "calmar": 0.0,
            "p_value": 1.0,
        }
    eq = np.cumprod(1.0 + r)
    total_ret = float(eq[-1] - 1.0)
    yrs = float(n) / float(ann_days)
    cagr = (float(eq[-1]) ** (1.0 / max(1e-6, yrs))) - 1.0 if eq[-1] > 0.0 else -1.0
    sd = float(np.std(r, ddof=1))
    ann_vol = sd * math.sqrt(float(ann_days))
    mean_r = float(np.mean(r))
    sharpe = (mean_r / sd * math.sqrt(float(ann_days))) if sd > _EPS else 0.0
    neg = r[r < 0.0]
    down_sd = float(np.sqrt(np.mean(neg**2))) if len(neg) > 0 else 1e-12
    sortino = (mean_r / max(down_sd, 1e-12)) * math.sqrt(float(ann_days))
    peaks = np.maximum.accumulate(np.r_[1.0, eq])
    dd_arr = (peaks[1:] - eq) / np.maximum(peaks[1:], 1e-12)
    max_dd = float(np.max(dd_arr))
    calmar = cagr / max_dd if max_dd > 1e-9 else 0.0
    t_stat = (mean_r / (sd / math.sqrt(float(n)))) if sd > _EPS else 0.0
    p_val = float(0.5 * math.erfc(t_stat / math.sqrt(2.0)))
    return {
        "n_days": int(n),
        "total_net_return_pct": round(100.0 * total_ret, 4),
        "cagr_pct": round(100.0 * cagr, 4),
        "ann_vol_pct": round(100.0 * ann_vol, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_dd_pct": round(100.0 * max_dd, 4),
        "calmar": round(calmar, 4),
        "p_value": round(float(np.clip(p_val, 0.0, 1.0)), 6),
    }


def _compute_cost_breakeven_mult(
    gross_r: np.ndarray,
    cost_1x_r: np.ndarray,
    *,
    max_mult: float = 30.0,
) -> float:
    """Compute exact compounded net-return breakeven cost multiplier via bisection."""
    g = np.asarray(gross_r, dtype=np.float64)
    c = np.asarray(cost_1x_r, dtype=np.float64)
    if len(g) == 0:
        return 0.0

    def _net_eq(mult: float) -> float:
        r = g - mult * c
        if np.any(r <= -0.999999):
            return -1.0
        return float(np.prod(1.0 + r)) - 1.0

    if _net_eq(0.0) <= 0.0:
        return 0.0
    if float(np.sum(np.abs(c))) <= _EPS:
        return round(max_mult, 2)
    if _net_eq(max_mult) > 0.0:
        return round(max_mult, 2)

    lo, hi = 0.0, max_mult
    for _ in range(36):
        mid = 0.5 * (lo + hi)
        if _net_eq(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return round(lo, 3)


def _align_business_days_pair(
    cand_map: Mapping[str, float],
    ref_map: Mapping[str, float],
    *,
    start_day: str,
    end_day: str,
    compound_weekends: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Align two daily return dicts over `[start_day, end_day]`, optionally compounding Sat/Sun to Monday."""
    if not cand_map or not ref_map:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)
    lo = max(start_day, min(cand_map.keys()), min(ref_map.keys()))
    hi = min(end_day, max(cand_map.keys()), max(ref_map.keys()))
    if hi < lo:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    if not compound_weekends:
        common = sorted(d for d in cand_map if d in ref_map and lo <= d <= hi)
        c_arr = np.array([float(cand_map[d]) for d in common], dtype=np.float64)
        r_arr = np.array([float(ref_map[d]) for d in common], dtype=np.float64)
        return c_arr, r_arr

    d0 = date.fromisoformat(lo)
    d1 = date.fromisoformat(hi)
    c_out: list[float] = []
    r_out: list[float] = []
    carry_c = 1.0
    carry_r = 1.0
    cur = d0
    while cur <= d1:
        iso = cur.isoformat()
        if cur.weekday() >= 5:
            carry_c *= 1.0 + float(cand_map.get(iso, 0.0))
            carry_r *= 1.0 + float(ref_map.get(iso, 0.0))
        else:
            if iso in ref_map or iso in cand_map:
                eff_c = carry_c * (1.0 + float(cand_map.get(iso, 0.0))) - 1.0
                eff_r = carry_r * (1.0 + float(ref_map.get(iso, 0.0))) - 1.0
                c_out.append(eff_c)
                r_out.append(eff_r)
            carry_c = 1.0
            carry_r = 1.0
        cur += timedelta(days=1)
    return np.asarray(c_out, dtype=np.float64), np.asarray(r_out, dtype=np.float64)


def _compute_corr_and_tail_corr(
    cand_map: Mapping[str, float],
    ref_map: Mapping[str, float] | None,
    *,
    start_day: str,
    end_day: str,
    compound_weekends: bool = False,
) -> tuple[float | None, float | None, int]:
    """Compute Pearson correlation and worst-5% reference tail correlation on aligned dates."""
    if not ref_map:
        return None, None, 0
    c_arr, r_arr = _align_business_days_pair(
        cand_map,
        ref_map,
        start_day=start_day,
        end_day=end_day,
        compound_weekends=compound_weekends,
    )
    n = len(c_arr)
    if n < 20 or float(np.std(c_arr)) <= _EPS or float(np.std(r_arr)) <= _EPS:
        return None, None, n
    corr = round(float(np.corrcoef(c_arr, r_arr)[0, 1]), 4)
    tail_corr: float | None = None
    cut = float(np.quantile(r_arr, 0.05))
    mask = r_arr <= cut
    if int(np.sum(mask)) >= 5 and float(np.std(c_arr[mask])) > _EPS and float(np.std(r_arr[mask])) > _EPS:
        tail_corr = round(float(np.corrcoef(c_arr[mask], r_arr[mask])[0, 1]), 4)
    return corr, tail_corr, n


# ---------------------------------------------------------------------------
# Shared Evaluation Harness (Used by Wave 1A Cluster A AND Wave 2A Blind B)
# ---------------------------------------------------------------------------


def evaluate_sleeve(
    sleeve_id: str,
    params: Mapping[str, Any],
    split: str = "cluster_a",
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    *,
    panel: Mapping[str, Any] | None = None,
    s1_dev_returns: Mapping[str, float] | None = None,
    s4_dev_returns: Mapping[str, float] | None = None,
    etf_cache_dir: str | Path = ETF40_CACHE_DIR,
    crypto_cache_dir: str | Path = CRYPTO_CACHE_DIR,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a single Frontier sleeve configuration on `cluster_a` OR `cluster_b_blind`.

    Hard anti-leakage contract:
      - Rejects any `cutoff_utc >= "2025-01-01"` or any date `>= "2025-01-01"` under `python -O`.
      - When `split == "cluster_a"`: loads data strictly `<= cluster_a_end` AND rejects any
        caller-supplied `panel` containing dates `> cluster_a_end` (`CLUSTER_B_LEAKAGE_VIOLATION`).
      - When `split == "cluster_b_blind"`: loads causal history strictly `<= cutoff_utc <= 2024-12-31`
        and computes evaluation metrics strictly over `[cluster_b_start, cluster_b_end]`.
    """
    sid = _require_non_empty_str(sleeve_id, "sleeve_id")
    if not isinstance(params, Mapping):
        raise ValueError(f"params must be a mapping, got {type(params).__name__}")
    cut = _validate_cutoff_utc(cutoff_utc, context=f"evaluate_sleeve.{sid}")
    spec = get_sleeve_spec(sid, config=config)
    gate = spec["gate"]

    if split not in ("cluster_a", "cluster_b_blind"):
        raise ValueError(f"split must be 'cluster_a' or 'cluster_b_blind', got {split!r}")

    max_load_date = spec["cluster_a_end"] if split == "cluster_a" else min(spec["cluster_b_end"], cut)
    is_crypto = sid == FRONTIER_03_ID

    if panel is None:
        if is_crypto:
            loaded_panel: Mapping[str, Any] = load_crypto_panel_strict(
                spec["required_dev_symbols"],
                max_date=max_load_date,
                cache_dir=crypto_cache_dir,
                cutoff_utc=cut,
                include_4h=True,
            )
        else:
            loaded_panel = load_etf_panel_strict(
                spec["required_dev_symbols"],
                max_date=max_load_date,
                cache_dir=etf_cache_dir,
                cutoff_utc=cut,
            )
    else:
        loaded_panel = panel

    dates = list(loaded_panel["dates"])
    eval_start, eval_end = enforce_split_bounds(
        dates,
        sleeve_id=sid,
        split=split,
        cutoff_utc=cut,
        config=config,
    )

    # Also validate any caller-supplied incumbent return maps against Holdout & split bounds
    if s1_dev_returns is not None and len(s1_dev_returns) > 0:
        enforce_pre_holdout_dates(
            sorted(s1_dev_returns.keys()),
            context=f"{sid}.s1_dev_returns",
            cutoff_day=HOLDOUT_START_DATE,
        )
    if s4_dev_returns is not None and len(s4_dev_returns) > 0:
        enforce_pre_holdout_dates(
            sorted(s4_dev_returns.keys()),
            context=f"{sid}.s4_dev_returns",
            cutoff_day=HOLDOUT_START_DATE,
        )

    # Build strictly causal target weights
    built = build_sleeve_weights(sid, loaded_panel, params)
    target_w = np.asarray(built["target_w"], dtype=np.float64)

    # Run 1x and 2x cost stress simulations
    cost_1x_bps = _require_finite_float(gate["cost_model_1x_bps_one_way"], "cost_model_1x_bps_one_way", lo=0.0)
    if is_crypto:
        eq_buf = float(built["equity_buffer_mult"])
        pair_1x_bps = max(0.0, cost_1x_bps - 3.0)
        basis_1x_bps = min(3.0, cost_1x_bps)
        sim_1x = _simulate_crypto_carry_causal(
            loaded_panel,
            target_w,
            equity_buffer_mult=eq_buf,
            oneway_pair_cost_bps=pair_1x_bps,
            basis_cross_slip_bps=basis_1x_bps,
            exit_shock_mult=1.0,
        )
        sim_2x = _simulate_crypto_carry_causal(
            loaded_panel,
            target_w,
            equity_buffer_mult=eq_buf,
            oneway_pair_cost_bps=2.0 * pair_1x_bps,
            basis_cross_slip_bps=2.0 * basis_1x_bps,
            exit_shock_mult=2.0,
        )
        ann_days = 365.0
        cost_1x_arr = sim_1x["fee_cost"] + sim_1x["exit_shock_cost"]
    else:
        sim_1x = _simulate_etf_causal(
            loaded_panel["adjclose"],
            target_w,
            loaded_panel["symbols"],
            cost_bps_oneway=cost_1x_bps,
            max_gross_leverage=float(built.get("max_gross_leverage", 1.0)),
        )
        sim_2x = _simulate_etf_causal(
            loaded_panel["adjclose"],
            target_w,
            loaded_panel["symbols"],
            cost_bps_oneway=2.0 * cost_1x_bps,
            max_gross_leverage=float(built.get("max_gross_leverage", 1.0)),
        )
        ann_days = 252.0
        cost_1x_arr = sim_1x["gross_returns"] - sim_1x["net_returns"]

    # Slice strictly onto the evaluation window [eval_start, eval_end]
    eval_mask = np.array([(d >= eval_start) and (d <= eval_end) for d in dates], dtype=bool)
    n_eval = int(np.sum(eval_mask))
    if n_eval < 5:
        raise ValueError(
            f"INSUFFICIENT_EVAL_ROWS [{sid}.{split}]: only {n_eval} rows in [{eval_start}, {eval_end}] "
            f"(loaded [{dates[0]}, {dates[-1]}])"
        )

    r_1x_eval = sim_1x["net_returns"][eval_mask]
    r_2x_eval = sim_2x["net_returns"][eval_mask]
    gross_eval = sim_1x["gross_returns"][eval_mask]
    cost_1x_eval = cost_1x_arr[eval_mask]
    turn_eval = sim_1x["turnover"][eval_mask]
    eval_dates = [d for d, flag in zip(dates, eval_mask, strict=True) if flag]

    m_1x = compute_series_metrics(r_1x_eval, ann_days=ann_days)
    m_2x = compute_series_metrics(r_2x_eval, ann_days=ann_days)
    annual_turnover = round(float(np.sum(turn_eval)) / max(1e-6, float(n_eval) / ann_days), 4)
    breakeven_mult = _compute_cost_breakeven_mult(gross_eval, cost_1x_eval)

    daily_returns_map = {d: round(float(v), 8) for d, v in zip(eval_dates, r_1x_eval, strict=True)}

    # Strictly bound reference return series to <= eval_end when computing correlations!
    s1_sliced = (
        {d: v for d, v in s1_dev_returns.items() if d <= eval_end and d < HOLDOUT_START_DATE}
        if s1_dev_returns is not None
        else None
    )
    s4_sliced = (
        {d: v for d, v in s4_dev_returns.items() if d <= eval_end and d < HOLDOUT_START_DATE}
        if s4_dev_returns is not None
        else None
    )

    corr_7e, tail_corr_7e, overlap_7e = _compute_corr_and_tail_corr(
        daily_returns_map,
        s1_sliced,
        start_day=eval_start,
        end_day=eval_end,
        compound_weekends=is_crypto,
    )
    corr_s4, _, overlap_s4 = _compute_corr_and_tail_corr(
        daily_returns_map,
        s4_sliced,
        start_day=eval_start,
        end_day=eval_end,
        compound_weekends=is_crypto,
    )

    params_clean = dict(sorted((str(k), v) for k, v in params.items()))
    params_sha = sha256_json_canonical(params_clean)

    diagnostics: dict[str, Any] = {
        "rebal_events": int(built.get("rebal_events", 0)),
        "pre_listing_weight_violations": int(sim_1x["pre_listing_weight_violations"]),
        "signal_only_max_abs_weight": float(sim_1x["signal_only_max_abs_weight"]),
        "overlap_days_vs_7e": int(overlap_7e),
        "overlap_days_vs_s4": int(overlap_s4),
    }
    if is_crypto:
        diagnostics.update(
            {
                "equity_buffer_mult": float(built["equity_buffer_mult"]),
                "max_single_coin_mark_jump_pct": float(sim_1x["max_single_coin_mark_jump_pct"]),
                "max_cross_margin_draw_pct": float(sim_1x["max_cross_margin_draw_pct"]),
                "isolated_liq_events": int(sim_1x["isolated_liq_events"]),
                "cross_liq_events": int(sim_1x["cross_liq_events"]),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "sleeve_id": sid,
        "split": split,
        "cutoff_utc": cut,
        "eval_start_date": eval_dates[0],
        "eval_end_date": eval_dates[-1],
        "max_loaded_date": dates[-1],
        "n_eval_days": n_eval,
        "annualization_days": ann_days,
        "params": params_clean,
        "params_sha256": params_sha,
        "data_sha256": str(loaded_panel.get("data_sha256", "")),
        "metrics_1x": m_1x,
        "metrics_2x": m_2x,
        "sharpe": float(m_1x["sharpe"]),
        "calmar": float(m_1x["calmar"]),
        "max_dd_pct": float(m_1x["max_dd_pct"]),
        "cagr_pct": float(m_1x["cagr_pct"]),
        "p_value": float(m_1x["p_value"]),
        "cost_2x_net": float(m_2x["total_net_return_pct"]),
        "cost_2x_cagr_pct": float(m_2x["cagr_pct"]),
        "cost_2x_sharpe": float(m_2x["sharpe"]),
        "cost_breakeven_mult": float(breakeven_mult),
        "annual_turnover": float(annual_turnover),
        "corr_vs_7e": corr_7e,
        "tail_corr_vs_7e": tail_corr_7e,
        "corr_vs_s4_etf": corr_s4,
        "holdout_rows_analysed": 0,
        "cluster_b_touched": bool(split == "cluster_b_blind"),
        "order_send_count": ORDER_SEND_COUNT,
        "diagnostics": diagnostics,
        "daily_returns": daily_returns_map,
    }


# ---------------------------------------------------------------------------
# DuckDB + SQLite Hash-Chain Experiment Ledger (`wave4_frontier_m36 <= 36`)
# ---------------------------------------------------------------------------


_WAVE4_TRIALS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wave4_frontier_trials (
    trial_id VARCHAR PRIMARY KEY,
    family_budget_id VARCHAR NOT NULL,
    sleeve_id VARCHAR NOT NULL,
    split VARCHAR NOT NULL,
    params_json VARCHAR NOT NULL,
    params_sha256 VARCHAR NOT NULL,
    cluster_a_sharpe DOUBLE,
    cluster_a_calmar DOUBLE,
    cluster_a_dd DOUBLE,
    cluster_a_cagr DOUBLE,
    cluster_a_turnover DOUBLE,
    corr_vs_7e DOUBLE,
    tail_corr_vs_7e DOUBLE,
    cost_2x_net DOUBLE,
    cost_breakeven_mult DOUBLE,
    holdout_rows_analysed INTEGER NOT NULL,
    cluster_b_touched BOOLEAN NOT NULL,
    p_value DOUBLE NOT NULL,
    created_utc VARCHAR NOT NULL
);
"""


class FrontierExperimentLedger:
    """Dual-backed Wave 4 Frontier ledger enforcing `wave4_frontier_m36 <= 36` fail-closed.

    Stores:
      1. Canonical `ExperimentLedger` (`SQLiteRunRegistry` SHA-256 hash chain + DuckDB `experiments`)
         following exact `tooling/ai-engines/quant_factory/experiment_ledger.py` convention.
      2. Detailed `wave4_frontier_trials` table in the same DuckDB file with exact Wave 4 columns
         (`trial_id`, `sleeve_id`, `params_json`, `cluster_a_sharpe`, `cluster_a_calmar`,
         `cluster_a_dd`, `corr_vs_7e`, `cost_2x_net`, `holdout_rows_analysed = 0`).
    """

    def __init__(
        self,
        duckdb_path: str | Path = DEFAULT_DUCKDB_PATH,
        registry_path: str | Path | None = None,
        *,
        budget_cap: int = WAVE4_FRONTIER_BUDGET_CAP,
        max_cluster_a_per_sleeve: int = MAX_CLUSTER_A_TRIALS_PER_SLEEVE,
        family_id: str = WAVE4_FRONTIER_FAMILY_ID,
    ) -> None:
        from quant_factory.experiment_ledger import ExperimentLedger

        self.budget_cap = _require_int(budget_cap, "budget_cap", lo=1, hi=1000)
        self.max_cluster_a_per_sleeve = _require_int(
            max_cluster_a_per_sleeve,
            "max_cluster_a_per_sleeve",
            lo=1,
            hi=self.budget_cap,
        )
        self.family_id = _require_non_empty_str(family_id, "family_id")
        self.duckdb_path = Path(duckdb_path)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path = (
            Path(registry_path)
            if registry_path is not None
            else self.duckdb_path.with_name(f"{self.duckdb_path.stem}_registry.sqlite3")
        )
        self._base = ExperimentLedger(duckdb_path=self.duckdb_path, registry_path=self.registry_path)
        with self._base._connect() as con:
            con.execute(_WAVE4_TRIALS_SCHEMA_SQL)

    def close(self) -> None:
        self._base.close()

    def __enter__(self) -> FrontierExperimentLedger:
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()

    def get_total_trial_count(self) -> int:
        with self._base._connect(read_only=True) as con:
            row = con.execute(
                "SELECT COUNT(*) FROM wave4_frontier_trials WHERE family_budget_id = ?",
                [self.family_id],
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def get_sleeve_trial_count(self, sleeve_id: str, *, split: str | None = None) -> int:
        sid = _require_non_empty_str(sleeve_id, "sleeve_id")
        with self._base._connect(read_only=True) as con:
            if split is None:
                row = con.execute(
                    "SELECT COUNT(*) FROM wave4_frontier_trials WHERE family_budget_id = ? AND sleeve_id = ?",
                    [self.family_id, sid],
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT COUNT(*) FROM wave4_frontier_trials "
                    "WHERE family_budget_id = ? AND sleeve_id = ? AND split = ?",
                    [self.family_id, sid, split],
                ).fetchone()
        return int(row[0]) if row is not None else 0

    def record_trial(
        self,
        *,
        trial_id: str,
        sleeve_id: str,
        split: str,
        params: Mapping[str, Any],
        cluster_a_sharpe: float | None,
        cluster_a_calmar: float | None,
        cluster_a_dd: float | None,
        corr_vs_7e: float | None,
        cost_2x_net: float,
        holdout_rows_analysed: int = 0,
        cluster_b_touched: bool = False,
        p_value: float = 1.0,
        cluster_a_cagr: float | None = None,
        cluster_a_turnover: float | None = None,
        tail_corr_vs_7e: float | None = None,
        cost_breakeven_mult: float | None = None,
        git_sha: str | None = None,
        data_sha: str | None = None,
        created_utc: str | None = None,
    ) -> dict[str, Any]:
        """Atomically record a Frontier trial enforcing hard `<= 36` budget & `holdout_rows == 0`."""
        tid = _require_non_empty_str(trial_id, "trial_id")
        sid = _require_non_empty_str(sleeve_id, "sleeve_id")
        if sid not in FRONTIER_SLEEVE_IDS:
            raise ValueError(f"Unsupported sleeve_id={sid!r}")
        if split not in ("cluster_a", "cluster_b_blind"):
            raise ValueError(f"Unsupported split={split!r}")
        enforce_holdout_zero_rows(holdout_rows_analysed, context=f"ledger.{tid}")
        cb_flag = _require_bool(cluster_b_touched, "cluster_b_touched")
        if split == "cluster_a" and cb_flag:
            raise ValueError(f"CLUSTER_B_FLAG_CONFLICT [{tid}]: split='cluster_a' cannot set cluster_b_touched=True")

        p_val = _require_finite_float(p_value, "p_value", lo=0.0, hi=1.0)
        c2x = _require_finite_float(cost_2x_net, "cost_2x_net")
        sh = None if cluster_a_sharpe is None else _require_finite_float(cluster_a_sharpe, "cluster_a_sharpe")
        cal = None if cluster_a_calmar is None else _require_finite_float(cluster_a_calmar, "cluster_a_calmar")
        dd = None if cluster_a_dd is None else _require_finite_float(cluster_a_dd, "cluster_a_dd", lo=0.0)
        cagr = None if cluster_a_cagr is None else _require_finite_float(cluster_a_cagr, "cluster_a_cagr")
        turn = (
            None
            if cluster_a_turnover is None
            else _require_finite_float(cluster_a_turnover, "cluster_a_turnover", lo=0.0)
        )
        c7e = None if corr_vs_7e is None else _require_finite_float(corr_vs_7e, "corr_vs_7e", lo=-1.0, hi=1.0)
        tc7e = (
            None
            if tail_corr_vs_7e is None
            else _require_finite_float(tail_corr_vs_7e, "tail_corr_vs_7e", lo=-1.0, hi=1.0)
        )
        be_m = (
            None
            if cost_breakeven_mult is None
            else _require_finite_float(cost_breakeven_mult, "cost_breakeven_mult", lo=0.0)
        )

        params_clean = dict(sorted((str(k), v) for k, v in params.items()))
        params_json = canonical_json(params_clean)
        params_sha = sha256_json_canonical(params_clean)
        ts_utc = created_utc or _utc_now_iso()

        with self._base._connect() as con:
            exists = con.execute(
                "SELECT trial_id FROM wave4_frontier_trials WHERE trial_id = ?",
                [tid],
            ).fetchone()
            if exists is not None:
                raise ValueError(f"DUPLICATE_TRIAL_ID: {tid!r} already exists in {self.duckdb_path}")

            total_now = self.get_total_trial_count()
            if total_now >= self.budget_cap:
                raise ValueError(
                    f"WAVE4_FRONTIER_BUDGET_EXCEEDED: family={self.family_id} already has "
                    f"{total_now}/{self.budget_cap} trials; refusing trial_id={tid!r}"
                )

            if split == "cluster_a":
                sleeve_a_now = self.get_sleeve_trial_count(sid, split="cluster_a")
                if sleeve_a_now >= self.max_cluster_a_per_sleeve:
                    raise ValueError(
                        f"SLEEVE_CLUSTER_A_BUDGET_EXCEEDED: sleeve={sid} already has "
                        f"{sleeve_a_now}/{self.max_cluster_a_per_sleeve} Cluster A trials; refusing {tid!r}"
                    )

            # 1. Record in canonical ExperimentLedger (SQLite hash chain + DuckDB `experiments`)
            exp_rec = self._base.record_experiment(
                run_id=tid,
                git_sha=git_sha or _git_head_sha(),
                data_sha=data_sha or params_sha,
                strategy_id=f"{sid}:{tid}",
                family_id=self.family_id,
                p_value=p_val,
                sharpe=sh,
                created_utc=ts_utc,
            )

            # 2. Record detailed Wave 4 Frontier trial row
            con.execute(
                """
                INSERT INTO wave4_frontier_trials (
                    trial_id, family_budget_id, sleeve_id, split, params_json, params_sha256,
                    cluster_a_sharpe, cluster_a_calmar, cluster_a_dd, cluster_a_cagr, cluster_a_turnover,
                    corr_vs_7e, tail_corr_vs_7e, cost_2x_net, cost_breakeven_mult,
                    holdout_rows_analysed, cluster_b_touched, p_value, created_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    tid,
                    self.family_id,
                    sid,
                    split,
                    params_json,
                    params_sha,
                    sh,
                    cal,
                    dd,
                    cagr,
                    turn,
                    c7e,
                    tc7e,
                    c2x,
                    be_m,
                    0,
                    cb_flag,
                    p_val,
                    ts_utc,
                ],
            )

        return {
            "trial_id": tid,
            "family_budget_id": self.family_id,
            "sleeve_id": sid,
            "split": split,
            "params_json": params_json,
            "params_sha256": params_sha,
            "cluster_a_sharpe": sh,
            "cluster_a_calmar": cal,
            "cluster_a_dd": dd,
            "corr_vs_7e": c7e,
            "cost_2x_net": c2x,
            "holdout_rows_analysed": 0,
            "cluster_b_touched": cb_flag,
            "p_value": p_val,
            "registry_event_hash": exp_rec["registry_event_hash"],
        }

    def list_trials(self, *, sleeve_id: str | None = None) -> list[dict[str, Any]]:
        cols = (
            "trial_id",
            "family_budget_id",
            "sleeve_id",
            "split",
            "params_json",
            "params_sha256",
            "cluster_a_sharpe",
            "cluster_a_calmar",
            "cluster_a_dd",
            "cluster_a_cagr",
            "cluster_a_turnover",
            "corr_vs_7e",
            "tail_corr_vs_7e",
            "cost_2x_net",
            "cost_breakeven_mult",
            "holdout_rows_analysed",
            "cluster_b_touched",
            "p_value",
            "created_utc",
        )
        col_sql = ", ".join(cols)
        with self._base._connect(read_only=True) as con:
            if sleeve_id is None:
                rows = con.execute(
                    f"SELECT {col_sql} FROM wave4_frontier_trials ORDER BY created_utc ASC, trial_id ASC"
                ).fetchall()
            else:
                rows = con.execute(
                    f"SELECT {col_sql} FROM wave4_frontier_trials WHERE sleeve_id = ? "
                    "ORDER BY created_utc ASC, trial_id ASC",
                    [sleeve_id],
                ).fetchall()
        return [dict(zip(cols, r, strict=True)) for r in rows]

    def verify_integrity(self) -> dict[str, Any]:
        base_ver = self._base.verify_integrity()
        total = self.get_total_trial_count()
        if total > self.budget_cap:
            raise ValueError(f"WAVE4_FRONTIER_BUDGET_BREACH: {total} > {self.budget_cap}")
        with self._base._connect(read_only=True) as con:
            bad_ho = con.execute(
                "SELECT COUNT(*) FROM wave4_frontier_trials WHERE holdout_rows_analysed != 0"
            ).fetchone()
        if bad_ho is not None and int(bad_ho[0]) != 0:
            raise HoldoutLockError(f"LEDGER_HOLDOUT_VIOLATION: {int(bad_ho[0])} rows with holdout_rows_analysed != 0")
        return {
            **base_ver,
            "wave4_frontier_trials_count": total,
            "budget_cap": self.budget_cap,
            "budget_headroom": self.budget_cap - total,
            "holdout_rows_analysed": 0,
        }


# ---------------------------------------------------------------------------
# Pre-Registered Cluster A Candidate Grids (8 + 8 + 8 = 24 <= 36)
# ---------------------------------------------------------------------------


PRE_REGISTERED_CLUSTER_A_GRIDS: dict[str, tuple[tuple[str, dict[str, Any]], ...]] = {
    FRONTIER_01_ID: (
        (
            "F01_T1_NCO_LAM25_M_BIL",
            {
                "allocator": "nco",
                "jump_lambda": 25.0,
                "rebal_freq": "monthly",
                "sjm_window": 252,
                "cov_window": 126,
                "bear_scale": 0.0,
                "target_vol": 0.10,
                "deadband": 0.05,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.30,
            },
        ),
        (
            "F01_T2_NCO_LAM50_M_BIL",
            {
                "allocator": "nco",
                "jump_lambda": 50.0,
                "rebal_freq": "monthly",
                "sjm_window": 252,
                "cov_window": 126,
                "bear_scale": 0.0,
                "target_vol": 0.10,
                "deadband": 0.05,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.30,
            },
        ),
        (
            "F01_T3_NCO_LAM100_M_BIL",
            {
                "allocator": "nco",
                "jump_lambda": 100.0,
                "rebal_freq": "monthly",
                "sjm_window": 378,
                "cov_window": 126,
                "bear_scale": 0.0,
                "target_vol": 0.10,
                "deadband": 0.05,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.30,
            },
        ),
        (
            "F01_T4_HRP_LAM50_M_BIL",
            {
                "allocator": "hrp",
                "jump_lambda": 50.0,
                "rebal_freq": "monthly",
                "sjm_window": 252,
                "cov_window": 126,
                "bear_scale": 0.0,
                "target_vol": 0.10,
                "deadband": 0.05,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.30,
            },
        ),
        (
            "F01_T5_NCO_LAM50_BW_SOFT",
            {
                "allocator": "nco",
                "jump_lambda": 50.0,
                "rebal_freq": "biweekly",
                "sjm_window": 252,
                "cov_window": 126,
                "bear_scale": 0.20,
                "target_vol": 0.08,
                "deadband": 0.08,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.25,
            },
        ),
        (
            "F01_T6_HRP_LAM25_BW_BIL",
            {
                "allocator": "hrp",
                "jump_lambda": 25.0,
                "rebal_freq": "biweekly",
                "sjm_window": 252,
                "cov_window": 126,
                "bear_scale": 0.0,
                "target_vol": 0.08,
                "deadband": 0.08,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.25,
            },
        ),
        (
            "F01_T7_NCO_LAM75_M_CASH0",
            {
                "allocator": "nco",
                "jump_lambda": 75.0,
                "rebal_freq": "monthly",
                "sjm_window": 378,
                "cov_window": 252,
                "bear_scale": 0.0,
                "target_vol": 0.08,
                "deadband": 0.05,
                "safe_harbor": "cash",
                "max_single_weight": 0.30,
            },
        ),
        (
            "F01_T8_HRP_LAM100_W_DB10",
            {
                "allocator": "hrp",
                "jump_lambda": 100.0,
                "rebal_freq": "weekly",
                "sjm_window": 252,
                "cov_window": 126,
                "bear_scale": 0.0,
                "target_vol": 0.08,
                "deadband": 0.10,
                "safe_harbor": "bil_cash",
                "max_single_weight": 0.25,
            },
        ),
    ),
    FRONTIER_02_ID: (
        (
            "F02_T1_INVVAR_HYST_BIL_DB15",
            {
                "scaling": "inv_var",
                "r_enter": 0.95,
                "r_exit": 1.02,
                "vix_smooth": 5,
                "vol_lookback": 21,
                "target_vol": 0.10,
                "deadband": 0.15,
                "rebal_days": 5,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.0,
            },
        ),
        (
            "F02_T2_INVVOL_HYST_BIL_DB15",
            {
                "scaling": "inv_vol",
                "r_enter": 0.95,
                "r_exit": 1.02,
                "vix_smooth": 5,
                "vol_lookback": 21,
                "target_vol": 0.10,
                "deadband": 0.15,
                "rebal_days": 5,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.0,
            },
        ),
        (
            "F02_T3_INVVAR_TIGHT_GLD15",
            {
                "scaling": "inv_var",
                "r_enter": 0.92,
                "r_exit": 1.00,
                "vix_smooth": 3,
                "vol_lookback": 21,
                "target_vol": 0.12,
                "deadband": 0.12,
                "rebal_days": 5,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.15,
            },
        ),
        (
            "F02_T4_INVVOL_BW_DB20",
            {
                "scaling": "inv_vol",
                "r_enter": 0.94,
                "r_exit": 1.01,
                "vix_smooth": 5,
                "vol_lookback": 42,
                "target_vol": 0.10,
                "deadband": 0.20,
                "rebal_days": 10,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.15,
            },
        ),
        (
            "F02_T5_COVMFM_BIL_DB15",
            {
                "scaling": "cov_mfm",
                "r_enter": 0.95,
                "r_exit": 1.02,
                "vix_smooth": 5,
                "vol_lookback": 42,
                "target_vol": 0.10,
                "deadband": 0.15,
                "rebal_days": 5,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.10,
            },
        ),
        (
            "F02_T6_COVMFM_TIGHT_GLD20",
            {
                "scaling": "cov_mfm",
                "r_enter": 0.92,
                "r_exit": 1.00,
                "vix_smooth": 5,
                "vol_lookback": 21,
                "target_vol": 0.08,
                "deadband": 0.15,
                "rebal_days": 5,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.20,
            },
        ),
        (
            "F02_T7_INVVAR_CASH0_DB15",
            {
                "scaling": "inv_var",
                "r_enter": 0.95,
                "r_exit": 1.02,
                "vix_smooth": 5,
                "vol_lookback": 21,
                "target_vol": 0.10,
                "deadband": 0.15,
                "rebal_days": 5,
                "safe_harbor": "cash",
                "def_gld_cap": 0.0,
            },
        ),
        (
            "F02_T8_INVVOL_MONTHLY_DB10",
            {
                "scaling": "inv_vol",
                "r_enter": 0.96,
                "r_exit": 1.03,
                "vix_smooth": 5,
                "vol_lookback": 42,
                "target_vol": 0.10,
                "deadband": 0.10,
                "rebal_days": 21,
                "safe_harbor": "bil_shy",
                "def_gld_cap": 0.15,
            },
        ),
    ),
    FRONTIER_03_ID: (
        (
            "F03_T1_CARRY_MOM_W7_BUF20",
            {
                "k_max": 6,
                "keep_rank": 10,
                "enter_ann": 0.08,
                "exit_ann": 0.01,
                "rebal_days": 7,
                "w_fund": 0.60,
                "w_basis": 0.20,
                "w_mom": 0.20,
                "mom_lb": 21,
                "equity_buffer": 2.0,
                "max_single": 0.25,
                "deadband": 0.06,
                "mom_gate": True,
                "use_4h_confirm": False,
                "neg_med_brake": False,
                "min_persist14": 0.0,
                "bear_scale": 1.0,
            },
        ),
        (
            "F03_T2_CARRY_MOM_W7_BUF25",
            {
                "k_max": 8,
                "keep_rank": 12,
                "enter_ann": 0.06,
                "exit_ann": 0.01,
                "rebal_days": 7,
                "w_fund": 0.60,
                "w_basis": 0.20,
                "w_mom": 0.20,
                "mom_lb": 21,
                "equity_buffer": 2.5,
                "max_single": 0.20,
                "deadband": 0.06,
                "mom_gate": True,
                "use_4h_confirm": False,
                "neg_med_brake": False,
                "min_persist14": 0.0,
                "bear_scale": 1.0,
            },
        ),
        (
            "F03_T3_CARRY_MOM_D5_HYST10",
            {
                "k_max": 5,
                "keep_rank": 9,
                "enter_ann": 0.10,
                "exit_ann": 0.02,
                "rebal_days": 5,
                "w_fund": 0.50,
                "w_basis": 0.20,
                "w_mom": 0.30,
                "mom_lb": 30,
                "equity_buffer": 2.0,
                "max_single": 0.25,
                "deadband": 0.08,
                "mom_gate": True,
                "use_4h_confirm": False,
                "neg_med_brake": False,
                "min_persist14": 0.0,
                "bear_scale": 1.0,
            },
        ),
        (
            "F03_T4_CARRY_BASIS_W7_BEAR",
            {
                "k_max": 6,
                "keep_rank": 10,
                "enter_ann": 0.08,
                "exit_ann": 0.01,
                "rebal_days": 7,
                "w_fund": 0.55,
                "w_basis": 0.25,
                "w_mom": 0.20,
                "mom_lb": 21,
                "equity_buffer": 2.0,
                "max_single": 0.25,
                "deadband": 0.06,
                "mom_gate": False,
                "use_4h_confirm": False,
                "neg_med_brake": False,
                "min_persist14": 0.0,
                "bear_scale": 0.50,
            },
        ),
        (
            "F03_T5_PERSIST14_MOM_W7",
            {
                "k_max": 8,
                "keep_rank": 12,
                "enter_ann": 0.06,
                "exit_ann": 0.00,
                "rebal_days": 7,
                "w_fund": 0.50,
                "w_basis": 0.15,
                "w_mom": 0.35,
                "mom_lb": 14,
                "equity_buffer": 2.0,
                "max_single": 0.20,
                "deadband": 0.06,
                "mom_gate": False,
                "use_4h_confirm": False,
                "neg_med_brake": False,
                "min_persist14": 0.70,
                "bear_scale": 1.0,
            },
        ),
        (
            "F03_T6_SLOW_W14_BUF25",
            {
                "k_max": 5,
                "keep_rank": 9,
                "enter_ann": 0.08,
                "exit_ann": 0.00,
                "rebal_days": 14,
                "w_fund": 0.60,
                "w_basis": 0.15,
                "w_mom": 0.25,
                "mom_lb": 30,
                "equity_buffer": 2.5,
                "max_single": 0.25,
                "deadband": 0.08,
                "mom_gate": False,
                "use_4h_confirm": False,
                "neg_med_brake": False,
                "min_persist14": 0.0,
                "bear_scale": 1.0,
            },
        ),
        (
            "F03_T7_TOP6_H4CONF_W7",
            {
                "k_max": 6,
                "keep_rank": 10,
                "enter_ann": 0.08,
                "exit_ann": 0.01,
                "rebal_days": 7,
                "w_fund": 0.50,
                "w_basis": 0.20,
                "w_mom": 0.30,
                "mom_lb": 21,
                "equity_buffer": 2.0,
                "max_single": 0.25,
                "deadband": 0.06,
                "mom_gate": False,
                "use_4h_confirm": True,
                "neg_med_brake": False,
                "min_persist14": 0.0,
                "bear_scale": 1.0,
            },
        ),
        (
            "F03_T8_BRAKE_W7_BUF25",
            {
                "k_max": 8,
                "keep_rank": 12,
                "enter_ann": 0.06,
                "exit_ann": 0.01,
                "rebal_days": 7,
                "w_fund": 0.55,
                "w_basis": 0.20,
                "w_mom": 0.25,
                "mom_lb": 21,
                "equity_buffer": 2.5,
                "max_single": 0.20,
                "deadband": 0.06,
                "mom_gate": False,
                "use_4h_confirm": False,
                "neg_med_brake": True,
                "min_persist14": 0.0,
                "bear_scale": 0.50,
            },
        ),
    ),
}


def _check_cluster_a_sanity(eval_res: Mapping[str, Any], gate: Mapping[str, Any]) -> dict[str, Any]:
    """Check pre-registered structural & friction constraints strictly on Cluster A."""
    max_turn = float(gate["max_annual_turnover"])
    min_be = float(gate["min_cost_breakeven_mult"])
    max_corr = float(gate["max_abs_corr_vs_7e"])
    diag = eval_res["diagnostics"]

    checks: dict[str, bool] = {
        "cost_2x_net_positive": float(eval_res["cost_2x_net"]) > 0.0,
        "turnover_within_gate": float(eval_res["annual_turnover"]) <= max_turn,
        "breakeven_mult_within_gate": float(eval_res["cost_breakeven_mult"]) >= min_be,
        "zero_pre_listing_violations": int(diag["pre_listing_weight_violations"]) == 0,
        "zero_signal_only_weights": float(diag["signal_only_max_abs_weight"]) == 0.0,
    }
    corr_7e = eval_res.get("corr_vs_7e")
    if corr_7e is not None:
        checks["abs_corr_vs_7e_within_gate"] = abs(float(corr_7e)) < max_corr
    if eval_res["sleeve_id"] == FRONTIER_03_ID:
        checks["zero_cross_margin_liquidations"] = int(diag.get("cross_liq_events", 0)) == 0
        checks["zero_isolated_liquidations"] = int(diag.get("isolated_liq_events", 0)) == 0

    return {
        "all_cluster_a_sanity_pass": all(checks.values()),
        "checks": checks,
    }


def _cluster_a_selection_score(eval_res: Mapping[str, Any], sanity: Mapping[str, Any]) -> tuple[int, float]:
    """Deterministic Cluster A selection ranking (prefer sanity-passing, then Sharpe + Calmar + 2x-Sharpe)."""
    tier = 1 if sanity["all_cluster_a_sanity_pass"] else 0
    sh1 = float(eval_res["sharpe"])
    sh2 = float(eval_res["cost_2x_sharpe"])
    cal = float(eval_res["calmar"])
    score = 0.50 * sh1 + 0.30 * sh2 + 0.20 * min(cal, 5.0)
    return (tier, round(score, 6))


# ---------------------------------------------------------------------------
# Wave 1A Cluster A Screening Orchestrator (NEVER Peeks at Cluster B!)
# ---------------------------------------------------------------------------


def run_cluster_a_screening(
    *,
    config_path: str | Path = CONFIG_PATH,
    etf_cache_dir: str | Path = ETF40_CACHE_DIR,
    crypto_cache_dir: str | Path = CRYPTO_CACHE_DIR,
    frozen_json_path: str | Path = DEFAULT_FROZEN_JSON_PATH,
    duckdb_path: str | Path = DEFAULT_DUCKDB_PATH,
    registry_path: str | Path | None = DEFAULT_REGISTRY_PATH,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    reset_ledger: bool = True,
    s1_dev_returns: Mapping[str, float] | None = None,
    s4_dev_returns: Mapping[str, float] | None = None,
    grids: Mapping[str, Sequence[tuple[str, dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    """Execute Wave 1A Dev Cluster A screening ONLY (`<= 8` trials/sleeve = `<= 24` total).

    STRICT ANTI-LEAKAGE GUARANTEE:
      - `split="cluster_a"` is hard-coded for every trial (`cluster_b_touched == False`).
      - All panels are sliced strictly `<= cluster_a_end` at load time (`holdout_rows_analysed == 0`).
      - Locks top frozen candidate per sleeve with SHA-256 into `frontier_cluster_a_frozen.json`
        and dual-backed DuckDB + SQLite hash-chain ledger (`wave4_frontier_m36.duckdb`).
    """
    cut = _validate_cutoff_utc(cutoff_utc, context="run_cluster_a_screening")
    cfg = load_frontier_config(config_path)
    active_grids = grids if grids is not None else PRE_REGISTERED_CLUSTER_A_GRIDS

    # Validate planned trial budget BEFORE executing a single trial
    total_planned = 0
    for sid in FRONTIER_SLEEVE_IDS:
        g_items = list(active_grids.get(sid, ()))
        if not g_items:
            raise ValueError(f"Empty Cluster A trial grid for {sid}")
        if len(g_items) > MAX_CLUSTER_A_TRIALS_PER_SLEEVE:
            raise ValueError(
                f"SLEEVE_CLUSTER_A_BUDGET_EXCEEDED: {sid} has {len(g_items)} > {MAX_CLUSTER_A_TRIALS_PER_SLEEVE} trials"
            )
        total_planned += len(g_items)
    if total_planned > MAX_CLUSTER_A_TOTAL_TRIALS or total_planned > WAVE4_FRONTIER_BUDGET_CAP:
        raise ValueError(
            f"WAVE4_FRONTIER_BUDGET_EXCEEDED: planned Cluster A trials {total_planned} exceeds "
            f"cap ({MAX_CLUSTER_A_TOTAL_TRIALS}/{WAVE4_FRONTIER_BUDGET_CAP})"
        )

    db_p = Path(duckdb_path)
    reg_p = Path(registry_path) if registry_path is not None else db_p.with_name(f"{db_p.stem}_registry.sqlite3")
    if reset_ledger:
        for p in (db_p, db_p.with_suffix(".duckdb.wal"), reg_p):
            if p.exists():
                p.unlink()

    git_sha = _git_head_sha()
    frozen_candidates: dict[str, Any] = {}
    all_trials_by_sleeve: dict[str, list[dict[str, Any]]] = {}

    with FrontierExperimentLedger(
        duckdb_path=db_p,
        registry_path=reg_p,
        budget_cap=WAVE4_FRONTIER_BUDGET_CAP,
        max_cluster_a_per_sleeve=MAX_CLUSTER_A_TRIALS_PER_SLEEVE,
    ) as ledger:
        for sid in FRONTIER_SLEEVE_IDS:
            spec = get_sleeve_spec(sid, config=cfg)
            a_end = spec["cluster_a_end"]

            # Load strictly <= cluster_a_end ONCE per sleeve (Cluster B never enters memory!)
            if sid == FRONTIER_03_ID:
                panel = load_crypto_panel_strict(
                    spec["required_dev_symbols"],
                    max_date=a_end,
                    cache_dir=crypto_cache_dir,
                    cutoff_utc=cut,
                    include_4h=True,
                )
            else:
                panel = load_etf_panel_strict(
                    spec["required_dev_symbols"],
                    max_date=a_end,
                    cache_dir=etf_cache_dir,
                    cutoff_utc=cut,
                )

            if s1_dev_returns is None and s4_dev_returns is None:
                s1_ref, s4_ref = _load_incumbent_returns_strict(max_date=a_end, cutoff_utc=cut)
            else:
                s1_ref = (
                    {d: v for d, v in s1_dev_returns.items() if d <= a_end and d < HOLDOUT_START_DATE}
                    if s1_dev_returns is not None
                    else None
                )
                s4_ref = (
                    {d: v for d, v in s4_dev_returns.items() if d <= a_end and d < HOLDOUT_START_DATE}
                    if s4_dev_returns is not None
                    else None
                )

            sleeve_rows: list[dict[str, Any]] = []
            for trial_id, params in active_grids[sid]:
                res = evaluate_sleeve(
                    sid,
                    params,
                    split="cluster_a",
                    cutoff_utc=cut,
                    panel=panel,
                    s1_dev_returns=s1_ref,
                    s4_dev_returns=s4_ref,
                    config=cfg,
                )
                if res["cluster_b_touched"] is not False:
                    raise ValueError(f"CLUSTER_B_LEAKAGE_VIOLATION: {trial_id} set cluster_b_touched=True")
                enforce_holdout_zero_rows(res["holdout_rows_analysed"], context=trial_id)

                sanity = _check_cluster_a_sanity(res, spec["gate"])
                sel_score = _cluster_a_selection_score(res, sanity)

                rec = ledger.record_trial(
                    trial_id=trial_id,
                    sleeve_id=sid,
                    split="cluster_a",
                    params=res["params"],
                    cluster_a_sharpe=res["sharpe"],
                    cluster_a_calmar=res["calmar"],
                    cluster_a_dd=res["max_dd_pct"],
                    cluster_a_cagr=res["cagr_pct"],
                    cluster_a_turnover=res["annual_turnover"],
                    corr_vs_7e=res["corr_vs_7e"],
                    tail_corr_vs_7e=res["tail_corr_vs_7e"],
                    cost_2x_net=res["cost_2x_net"],
                    cost_breakeven_mult=res["cost_breakeven_mult"],
                    holdout_rows_analysed=0,
                    cluster_b_touched=False,
                    p_value=res["p_value"],
                    git_sha=git_sha,
                    data_sha=res["data_sha256"],
                )

                row_summary = {
                    "trial_id": trial_id,
                    "sleeve_id": sid,
                    "split": "cluster_a",
                    "eval_window": f"{res['eval_start_date']}..{res['eval_end_date']}",
                    "max_loaded_date": res["max_loaded_date"],
                    "n_eval_days": res["n_eval_days"],
                    "params": res["params"],
                    "params_sha256": res["params_sha256"],
                    "cluster_a_sharpe": res["sharpe"],
                    "cluster_a_calmar": res["calmar"],
                    "cluster_a_dd_pct": res["max_dd_pct"],
                    "cluster_a_cagr_pct": res["cagr_pct"],
                    "cluster_a_turnover": res["annual_turnover"],
                    "cost_2x_net_pct": res["cost_2x_net"],
                    "cost_2x_cagr_pct": res["cost_2x_cagr_pct"],
                    "cost_2x_sharpe": res["cost_2x_sharpe"],
                    "cost_breakeven_mult": res["cost_breakeven_mult"],
                    "corr_vs_7e": res["corr_vs_7e"],
                    "tail_corr_vs_7e": res["tail_corr_vs_7e"],
                    "corr_vs_s4_etf": res["corr_vs_s4_etf"],
                    "p_value": res["p_value"],
                    "cluster_a_sanity": sanity,
                    "selection_tier": sel_score[0],
                    "selection_score": sel_score[1],
                    "diagnostics": res["diagnostics"],
                    "registry_event_hash": rec["registry_event_hash"],
                    "holdout_rows_analysed": 0,
                    "cluster_b_touched": False,
                }
                sleeve_rows.append(row_summary)

            ranked = sorted(
                sleeve_rows,
                key=lambda r: (-int(r["selection_tier"]), -float(r["selection_score"]), r["trial_id"]),
            )
            winner = ranked[0]
            runner_up = ranked[1] if len(ranked) > 1 else None

            freeze_payload = {
                "sleeve_id": sid,
                "frozen_trial_id": winner["trial_id"],
                "params": winner["params"],
                "params_sha256": winner["params_sha256"],
                "dev_cluster_a": spec["gate"]["dev_cluster_a"],
                "dev_cluster_b_blind_pending": spec["gate"]["dev_cluster_b_blind"],
                "dev_cutoff_utc": cut,
            }
            candidate_sha256 = sha256_json_canonical(freeze_payload)

            frozen_candidates[sid] = {
                **freeze_payload,
                "candidate_sha256": candidate_sha256,
                "cluster_a_trials_run": len(sleeve_rows),
                "cluster_a_metrics": {
                    "eval_window": winner["eval_window"],
                    "max_loaded_date": winner["max_loaded_date"],
                    "n_eval_days": winner["n_eval_days"],
                    "sharpe": winner["cluster_a_sharpe"],
                    "calmar": winner["cluster_a_calmar"],
                    "max_dd_pct": winner["cluster_a_dd_pct"],
                    "cagr_pct": winner["cluster_a_cagr_pct"],
                    "annual_turnover": winner["cluster_a_turnover"],
                    "cost_2x_net_pct": winner["cost_2x_net_pct"],
                    "cost_2x_cagr_pct": winner["cost_2x_cagr_pct"],
                    "cost_2x_sharpe": winner["cost_2x_sharpe"],
                    "cost_breakeven_mult": winner["cost_breakeven_mult"],
                    "corr_vs_7e": winner["corr_vs_7e"],
                    "tail_corr_vs_7e": winner["tail_corr_vs_7e"],
                    "corr_vs_s4_etf": winner["corr_vs_s4_etf"],
                    "p_value": winner["p_value"],
                    "diagnostics": winner["diagnostics"],
                    "cluster_a_sanity": winner["cluster_a_sanity"],
                },
                "runner_up_trial_id": runner_up["trial_id"] if runner_up is not None else None,
                "runner_up_sharpe": runner_up["cluster_a_sharpe"] if runner_up is not None else None,
                "pre_registered_falsification_gate": spec["gate"],
                "data_sha256": panel["data_sha256"],
                "holdout_rows_analysed": 0,
                "cluster_b_touched": False,
            }
            all_trials_by_sleeve[sid] = sleeve_rows

        ledger_integrity = ledger.verify_integrity()
        total_trials_logged = ledger.get_total_trial_count()

    frozen_doc: dict[str, Any] = {
        "schema_version": FROZEN_SCHEMA_VERSION,
        "generated_utc": _utc_now_iso(),
        "worker": "w4-m2b-frontier",
        "wave": "Wave 1A (Total Offensive #4 v4.8.1 FINAL)",
        "family_budget_id": WAVE4_FRONTIER_FAMILY_ID,
        "budget_cap": WAVE4_FRONTIER_BUDGET_CAP,
        "cluster_a_trials_total": total_trials_logged,
        "budget_headroom_remaining": WAVE4_FRONTIER_BUDGET_CAP - total_trials_logged,
        "dev_cutoff_utc": cut,
        "holdout_rows_analysed": 0,
        "cluster_b_touched": False,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        "git_sha": git_sha,
        "duckdb_path": str(db_p.relative_to(REPO_ROOT).as_posix()) if db_p.is_relative_to(REPO_ROOT) else str(db_p),
        "registry_path": (
            str(reg_p.relative_to(REPO_ROOT).as_posix()) if reg_p.is_relative_to(REPO_ROOT) else str(reg_p)
        ),
        "ledger_integrity": ledger_integrity,
        "frozen_candidates": frozen_candidates,
        "all_cluster_a_trials": all_trials_by_sleeve,
    }
    frozen_doc["manifest_sha256"] = sha256_json_canonical(
        {k: v for k, v in frozen_doc.items() if k != "manifest_sha256"}
    )
    atomic_write_json(frozen_json_path, frozen_doc, indent=2)
    return frozen_doc


def verify_frozen_artifact(frozen_json_path: str | Path = DEFAULT_FROZEN_JSON_PATH) -> dict[str, Any]:
    """Fail-closed verifier for `frontier_cluster_a_frozen.json` (used by Wave 2A & tests)."""
    p = Path(frozen_json_path)
    if not p.is_file():
        raise FileNotFoundError(f"Frozen Cluster A artifact not found: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema_version") != FROZEN_SCHEMA_VERSION:
        raise ValueError(f"Unexpected schema_version={doc.get('schema_version')!r}")
    enforce_holdout_zero_rows(doc.get("holdout_rows_analysed", -1), context="verify_frozen_artifact")
    if doc.get("cluster_b_touched") is not False:
        raise ValueError(f"CLUSTER_B_LEAKAGE_VIOLATION: cluster_b_touched={doc.get('cluster_b_touched')!r}")
    if doc.get("order_send_count") != 0 or doc.get("order_send_capable") is not False:
        raise ValueError("ORDER_SEND_SAFETY_VIOLATION in frozen artifact")

    total = _require_int(
        doc.get("cluster_a_trials_total"),
        "cluster_a_trials_total",
        lo=1,
        hi=MAX_CLUSTER_A_TOTAL_TRIALS,
    )
    cap = _require_int(doc.get("budget_cap"), "budget_cap", lo=total, hi=WAVE4_FRONTIER_BUDGET_CAP)
    if cap != WAVE4_FRONTIER_BUDGET_CAP:
        raise ValueError(f"Unexpected budget_cap={cap} != {WAVE4_FRONTIER_BUDGET_CAP}")

    expected_sha = sha256_json_canonical({k: v for k, v in doc.items() if k != "manifest_sha256"})
    if doc.get("manifest_sha256") != expected_sha:
        raise ValueError(f"FROZEN_MANIFEST_SHA256_MISMATCH: {doc.get('manifest_sha256')} != {expected_sha}")

    fc = doc.get("frozen_candidates", {})
    for sid in FRONTIER_SLEEVE_IDS:
        if sid not in fc:
            raise ValueError(f"Missing frozen candidate for {sid}")
        c = fc[sid]
        enforce_holdout_zero_rows(c.get("holdout_rows_analysed", -1), context=f"verify_frozen.{sid}")
        if c.get("cluster_b_touched") is not False:
            raise ValueError(f"CLUSTER_B_LEAKAGE_VIOLATION in {sid}")
        fp = {
            "sleeve_id": c["sleeve_id"],
            "frozen_trial_id": c["frozen_trial_id"],
            "params": c["params"],
            "params_sha256": c["params_sha256"],
            "dev_cluster_a": c["dev_cluster_a"],
            "dev_cluster_b_blind_pending": c["dev_cluster_b_blind_pending"],
            "dev_cutoff_utc": c["dev_cutoff_utc"],
        }
        cand_sha = sha256_json_canonical(fp)
        if c.get("candidate_sha256") != cand_sha:
            raise ValueError(f"CANDIDATE_SHA256_MISMATCH for {sid}: {c.get('candidate_sha256')} != {cand_sha}")
        max_loaded = str(c["cluster_a_metrics"]["max_loaded_date"])
        _, a_end = _parse_date_range(c["dev_cluster_a"], context=f"verify_frozen.{sid}")
        if max_loaded > a_end:
            raise ValueError(f"CLUSTER_B_LEAKAGE_VIOLATION: {sid} max_loaded_date={max_loaded} > {a_end}")

    return {
        "verified": True,
        "path": str(p),
        "file_sha256": sha256_file(p),
        "manifest_sha256": expected_sha,
        "cluster_a_trials_total": total,
        "budget_cap": cap,
        "holdout_rows_analysed": 0,
        "cluster_b_touched": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 4 Dev Cluster A screening engine for 3 Frontier non-CFD alpha sleeves (OrderSend=0)."
    )
    parser.add_argument(
        "--run-cluster-a",
        action="store_true",
        help="Run Dev Cluster A screening and freeze candidates.",
    )
    parser.add_argument(
        "--verify-frozen",
        action="store_true",
        help="Verify frozen Cluster A JSON & SHA-256 integrity.",
    )
    parser.add_argument("--frozen-path", type=Path, default=DEFAULT_FROZEN_JSON_PATH)
    parser.add_argument("--duckdb-path", type=Path, default=DEFAULT_DUCKDB_PATH)
    args = parser.parse_args(argv)

    if args.run_cluster_a:
        doc = run_cluster_a_screening(
            frozen_json_path=args.frozen_path,
            duckdb_path=args.duckdb_path,
        )
        summary = {
            "status": "PASS",
            "cluster_a_trials_total": doc["cluster_a_trials_total"],
            "budget_cap": doc["budget_cap"],
            "holdout_rows_analysed": doc["holdout_rows_analysed"],
            "cluster_b_touched": doc["cluster_b_touched"],
            "manifest_sha256": doc["manifest_sha256"],
            "frozen_winners": {
                sid: {
                    "trial_id": c["frozen_trial_id"],
                    "candidate_sha256": c["candidate_sha256"][:16],
                    "sharpe": c["cluster_a_metrics"]["sharpe"],
                    "calmar": c["cluster_a_metrics"]["calmar"],
                    "max_dd_pct": c["cluster_a_metrics"]["max_dd_pct"],
                    "annual_turnover": c["cluster_a_metrics"]["annual_turnover"],
                    "cost_2x_net_pct": c["cluster_a_metrics"]["cost_2x_net_pct"],
                    "corr_vs_7e": c["cluster_a_metrics"]["corr_vs_7e"],
                    "sanity_pass": c["cluster_a_metrics"]["cluster_a_sanity"]["all_cluster_a_sanity_pass"],
                }
                for sid, c in doc["frozen_candidates"].items()
            },
        }
        print(json.dumps(summary, indent=2))
        return 0

    if args.verify_frozen:
        ver = verify_frozen_artifact(args.frozen_path)
        print(json.dumps(ver, indent=2))
        return 0

    parser.print_help()
    return 0


__all__ = [
    "CONFIG_PATH",
    "CRYPTO_CACHE_DIR",
    "DEFAULT_DROPBOX_PATH",
    "DEFAULT_DUCKDB_PATH",
    "DEFAULT_FROZEN_JSON_PATH",
    "DEFAULT_RECEIPT_PATH",
    "DEFAULT_REGISTRY_PATH",
    "ETF40_CACHE_DIR",
    "FRONTIER_01_ID",
    "FRONTIER_02_ID",
    "FRONTIER_03_ID",
    "FRONTIER_OUT_DIR",
    "FRONTIER_SLEEVE_IDS",
    "FROZEN_SCHEMA_VERSION",
    "HOLDOUT_CUTOFF_DATE",
    "HOLDOUT_START_DATE",
    "MAX_CLUSTER_A_TOTAL_TRIALS",
    "MAX_CLUSTER_A_TRIALS_PER_SLEEVE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRE_REGISTERED_CLUSTER_A_GRIDS",
    "SCHEMA_VERSION",
    "SIGNAL_ONLY_SYMBOLS",
    "WAVE4_FRONTIER_BUDGET_CAP",
    "WAVE4_FRONTIER_FAMILY_ID",
    "FrontierExperimentLedger",
    "build_sleeve_weights",
    "compute_hrp_weights",
    "compute_nco_weights",
    "compute_series_metrics",
    "enforce_split_bounds",
    "evaluate_sleeve",
    "fit_sjm_2state_causal",
    "get_sleeve_spec",
    "load_crypto_panel_strict",
    "load_etf_panel_strict",
    "load_frontier_config",
    "run_cluster_a_screening",
    "verify_frozen_artifact",
]

if __name__ == "__main__":
    raise SystemExit(main())
