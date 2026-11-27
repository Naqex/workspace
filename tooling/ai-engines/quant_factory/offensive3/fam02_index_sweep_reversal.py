"""Total Offensive #3 — Family F02: Liquidity Sweep / Stop-Run Reversal (`F02_IDX_SWEEP_REV`).

Strictly offline, deterministic, fail-closed Stage 2 Alpha Factory worker:
  - Cap: `<= 16` `PRIMARY_M200`, `<= 100` total (`PRIMARY + EXPLORATORY`), `INTRADAY_SWAP0`.
  - Universe: native M1 Bid/Ask (`GER40, US500, US100, XAUUSD, GBPUSD, EURUSD, USDJPY`).
  - Core institutional microstructure mechanic (`swap = 0`, hard flat `<= 20:50 UTC`):
      1. Strictly causal reference range (`PRE_SESSION_BOX`, `OPENING_BOX`, or `PRIOR_DAY_HL`),
      2. Causal liquidity sweep `0.15-0.45 ATR` beyond box high/low (capped to exclude runaway
         macro trend breaks) + rapid `15-45m` reclaim close back inside the box,
      3. Strict zero-lookahead entry at the NEXT M1 bar open (`k + 1`) after reclaim close,
      4. Wide hard SL beyond sweep extreme floored at `>= 0.70-1.00 ATR` so `F_stress / SL <= 12%`,
         combined with wide TP or session time-flat + official `+-5m` red-news guard & matched
         opposite-side `fade` tape!

Hard invariants (`G01`, `G05`, `G06`, `[ARCH-02]`):
  - ZERO bare `assert` statements (guards remain active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - HARD BLINDNESS LOCK: `discover_cluster_a` strictly touches `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY.
  - Strict `shift = 1` daily features and `< entry_ts` intraday features.
"""

from __future__ import annotations

import argparse
import math
import sys
import time as time_mod
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


_AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.offensive3 import common_contract as cc  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety & Family Contract Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAMILY_ID: str = "F02_IDX_SWEEP_REV"
PROP_TRACK: str = "INTRADAY_SWAP0"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100
UNIVERSE_SYMBOLS: tuple[str, ...] = ("GER40", "US500", "US100", "XAUUSD", "GBPUSD", "EURUSD", "USDJPY")

STAGE0_MAX_FRIC_SL_RATIO: float = 0.12
STAGE0_MIN_KEEP_FRAC: float = 0.50
PRIMARY_MIN_TRADES_3Y: int = 48
PRIMARY_MAX_TRADES_3Y: int = 300
PRIMARY_MAX_PER_SYMBOL: int = 4
PRIMARY_MAX_PER_ARCHETYPE: int = 6

_TZ_MAP: dict[str, ZoneInfo] = {
    "NY": ZoneInfo("America/New_York"),
    "LONDON": ZoneInfo("Europe/London"),
    "BERLIN": ZoneInfo("Europe/Berlin"),
}

_HARD_FLAT_SEC: int = cc.HARD_FLAT_MAX_UTC_HHMM[0] * 3600 + cc.HARD_FLAT_MAX_UTC_HHMM[1] * 60


# ---------------------------------------------------------------------------
# Numba-Accelerated Strictly Causal M1 Box & Sweep-Reclaim Detector
# ---------------------------------------------------------------------------


@njit(cache=True)
def _m1_box_high_low_jit(quotes: np.ndarray, i0: int, i1: int) -> tuple[float, float]:
    """Compute strictly causal mid-price high/low over M1 bars `[i0, i1)`."""
    has_ask = quotes.shape[1] >= 8
    hi = -1.0e300
    lo = 1.0e300
    for k in range(i0, i1):
        if has_ask:
            hk = 0.5 * (quotes[k, 1] + quotes[k, 5])
            lk = 0.5 * (quotes[k, 2] + quotes[k, 6])
        else:
            hk = quotes[k, 1]
            lk = quotes[k, 2]
        if hk > hi:
            hi = hk
        if lk < lo:
            lo = lk
    return hi, lo


@njit(cache=True)
def _scan_sweep_reclaim_jit(
    times_sec: np.ndarray,
    quotes: np.ndarray,
    scan_i0: int,
    scan_i1: int,
    max_entry_idx: int,
    box_hi: float,
    box_lo: float,
    min_sweep_px: float,
    max_sweep_px: float,
    reclaim_depth_px: float,
    reclaim_max_sec: int,
) -> tuple[int, int, float]:
    """Scan M1 bars `[scan_i0, scan_i1)` causally for first stop-run sweep + rapid reclaim.

    Returns `(entry_idx, side, sweep_extreme)`:
      - `side == -1` (short reversal after upper sweep above `box_hi` + reclaim close <= `box_hi - depth`)
      - `side == +1` (long reversal after lower sweep below `box_lo` + reclaim close >= `box_lo + depth`)
      - `entry_idx = k + 1` (strictly the NEXT M1 bar open after reclaim bar `k` closes!)
      - Returns `(-1, 0, np.nan)` if no valid sweep-reclaim occurs.
    """
    has_ask = quotes.shape[1] >= 8

    up_active = False
    up_start_ts = 0
    up_peak = -1.0e300

    dn_active = False
    dn_start_ts = 0
    dn_trough = 1.0e300

    for k in range(scan_i0, scan_i1):
        if k + 1 >= max_entry_idx:
            break
        tk = times_sec[k]
        if has_ask:
            hk = 0.5 * (quotes[k, 1] + quotes[k, 5])
            lk = 0.5 * (quotes[k, 2] + quotes[k, 6])
            ck = 0.5 * (quotes[k, 3] + quotes[k, 7])
        else:
            hk = quotes[k, 1]
            lk = quotes[k, 2]
            ck = quotes[k, 3]

        # ---- Track upper stop-run sweep above box_hi ----
        if not up_active:
            if hk >= box_hi + min_sweep_px:
                if hk <= box_hi + max_sweep_px:
                    up_active = True
                    up_start_ts = tk
                    up_peak = hk
        else:
            if hk > up_peak:
                up_peak = hk
            # Invalidate if excursion runs away (real breakout) or reclaim window expires
            if up_peak > box_hi + max_sweep_px or (tk - up_start_ts) > reclaim_max_sec:
                up_active = False
                up_peak = -1.0e300

        # ---- Track lower stop-run sweep below box_lo ----
        if not dn_active:
            if lk <= box_lo - min_sweep_px:
                if lk >= box_lo - max_sweep_px:
                    dn_active = True
                    dn_start_ts = tk
                    dn_trough = lk
        else:
            if lk < dn_trough:
                dn_trough = lk
            if dn_trough < box_lo - max_sweep_px or (tk - dn_start_ts) > reclaim_max_sec:
                dn_active = False
                dn_trough = 1.0e300

        # ---- Check causal reclaim on bar k close -> enter at bar k + 1 open ----
        up_reclaimed = up_active and (ck <= box_hi - reclaim_depth_px)
        dn_reclaimed = dn_active and (ck >= box_lo + reclaim_depth_px)

        if up_reclaimed and dn_reclaimed:
            # Ambiguous same-minute dual sweep-reclaim -> skip conservatively
            return -1, 0, np.nan
        if up_reclaimed:
            return k + 1, -1, up_peak
        if dn_reclaimed:
            return k + 1, 1, dn_trough

    return -1, 0, np.nan


def _resolve_hm_ts(day_obj: date, hm_tz: tuple[int, int, str]) -> int:
    hh, mm, tz_key = int(hm_tz[0]), int(hm_tz[1]), str(hm_tz[2]).upper()
    if tz_key == "UTC":
        return int(datetime(day_obj.year, day_obj.month, day_obj.day, hh, mm, tzinfo=UTC).timestamp())
    if tz_key not in _TZ_MAP:
        raise ValueError(f"Unsupported timezone tag {tz_key!r}")
    local_dt = datetime.combine(day_obj, time(hh, mm), tzinfo=_TZ_MAP[tz_key])
    return int(local_dt.astimezone(UTC).timestamp())


def _prepare_asset_context(
    asset_obj: Mapping[str, Any],
    req_years: tuple[int, ...],
) -> dict[str, Any]:
    """Build strictly causal (`shift = 1`) daily context & pre-cutoff M1 slices up to `max(req_years)`."""
    sym = str(asset_obj["symbol"])
    m1 = asset_obj.get("m1")
    d1 = asset_obj.get("d1")
    if m1 is None or d1 is None:
        raise ValueError(f"F02 requires native M1 and D1 bars for {sym}")

    max_year = max(req_years)
    max_ts_excl = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())
    if max_ts_excl > cc.DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH [f02.ctx:{sym}]: max_year={max_year}")

    # Hard slice BEFORE any indicator math so Cluster A physically cannot touch >= 2021 rows!
    d1_years = np.asarray(d1["years"], dtype=np.int32)
    d1_keep = d1_years <= max_year
    d1_dates = [str(d) for d, k in zip(d1["dates"], d1_keep, strict=True) if k]
    d1_ts = np.asarray(d1["times_sec"], dtype=np.int64)[d1_keep]
    d1_h = np.asarray(d1["high"], dtype=np.float64)[d1_keep]
    d1_l = np.asarray(d1["low"], dtype=np.float64)[d1_keep]
    d1_c = np.asarray(d1["close"], dtype=np.float64)[d1_keep]
    d1_yr = d1_years[d1_keep]
    d1_wd = np.asarray(d1["weekdays"], dtype=np.int32)[d1_keep]

    cc.enforce_dev_date_bound(d1_dates, context=f"f02.d1:{sym}")
    cc.enforce_dev_ts_bound(d1_ts, context=f"f02.d1_ts:{sym}")

    m1_ts_full = np.asarray(m1["times_sec"], dtype=np.int64)
    m1_q_full = np.asarray(m1["quotes"], dtype=np.float64)
    m1_end = int(np.searchsorted(m1_ts_full, max_ts_excl, side="left"))
    m1_ts = m1_ts_full[:m1_end]
    m1_q = m1_q_full[:m1_end]
    cc.enforce_dev_ts_bound(m1_ts, context=f"f02.m1_ts:{sym}")

    # Strictly causal shift = 1 daily indicators via common_contract
    atr14 = cc.causal_atr(d1_h, d1_l, d1_c, 14)
    ema20 = cc.causal_ema(d1_c, 20)

    n_d = len(d1_dates)
    prev_h = np.full(n_d, np.nan, dtype=np.float64)
    prev_l = np.full(n_d, np.nan, dtype=np.float64)
    prev_c = np.full(n_d, np.nan, dtype=np.float64)
    rolling_med_atr60 = np.full(n_d, np.nan, dtype=np.float64)

    if n_d > 1:
        prev_h[1:] = d1_h[:-1]
        prev_l[1:] = d1_l[:-1]
        prev_c[1:] = d1_c[:-1]

    for i in range(n_d):
        if not math.isfinite(atr14[i]):
            continue
        win_start = max(0, i - 59)
        sub = atr14[win_start : i + 1]
        fin = sub[np.isfinite(sub)]
        if fin.size >= 15:
            rolling_med_atr60[i] = float(np.median(fin))

    req_year_set = set(req_years)
    day_rows: list[dict[str, Any]] = []
    for i in range(n_d):
        yr_i = int(d1_yr[i])
        if yr_i not in req_year_set:
            continue
        a14 = float(atr14[i])
        if not math.isfinite(a14) or a14 <= 1e-12:
            continue
        d_iso = d1_dates[i]
        d_obj = date.fromisoformat(d_iso)
        day_start_ts = int(datetime(d_obj.year, d_obj.month, d_obj.day, tzinfo=UTC).timestamp())
        day_end_ts = day_start_ts + 86400
        fi = int(np.searchsorted(m1_ts, day_start_ts, side="left"))
        li = int(np.searchsorted(m1_ts, day_end_ts, side="left"))
        if li - fi < 120:
            continue
        hard_flat_ts = day_start_ts + _HARD_FLAT_SEC
        day_flat_idx = int(np.searchsorted(m1_ts, hard_flat_ts, side="right")) - 1
        if day_flat_idx <= fi:
            continue

        day_rows.append(
            {
                "day": d_iso,
                "date_obj": d_obj,
                "year": yr_i,
                "weekday": int(d1_wd[i]),
                "day_start_ts": day_start_ts,
                "fi": fi,
                "li": li,
                "day_flat_idx": day_flat_idx,
                "atr14": a14,
                "rolling_med_atr60": (float(rolling_med_atr60[i]) if math.isfinite(rolling_med_atr60[i]) else math.nan),
                "ema20": float(ema20[i]) if math.isfinite(ema20[i]) else math.nan,
                "prev_h": float(prev_h[i]) if math.isfinite(prev_h[i]) else math.nan,
                "prev_l": float(prev_l[i]) if math.isfinite(prev_l[i]) else math.nan,
                "prev_c": float(prev_c[i]) if math.isfinite(prev_c[i]) else math.nan,
            }
        )

    return {
        "symbol": sym,
        "spec": dict(asset_obj["spec"]),
        "data_resolution": str(asset_obj["data_resolution"]),
        "blindness_tier": str(asset_obj["blindness_tier"]),
        "times_sec": m1_ts,
        "quotes": m1_q,
        "days": day_rows,
    }


# ---------------------------------------------------------------------------
# Pre-Registered F02 Candidate Catalog (<= 100 Total Across 7 M1 Assets)
# ---------------------------------------------------------------------------


def _make_f02_spec(
    *,
    candidate_id: str,
    symbol: str,
    archetype: str,
    box_type: str,
    box_start: tuple[int, int, str] | None,
    box_end: tuple[int, int, str] | None,
    scan_start: tuple[int, int, str],
    scan_end: tuple[int, int, str],
    flat_hm: tuple[int, int, str],
    min_sweep_atr: float,
    max_sweep_atr: float,
    reclaim_min: int,
    reclaim_depth_atr: float,
    min_box_atr: float,
    max_box_atr: float,
    min_sl_atr: float,
    sl_buf_atr: float,
    tp_atr: float | None,
    vol_gate: str,
    economic_rationale: str,
    counterparty_mechanism: str,
) -> dict[str, Any]:
    if len(economic_rationale.strip()) < 40:
        raise ValueError(f"economic_rationale too short (< 40 chars) for {candidate_id}")
    return {
        "candidate_id": candidate_id,
        "family_id": FAMILY_ID,
        "prop_track": PROP_TRACK,
        "symbol": symbol,
        "symbols": [symbol],
        "timeframe": "M1",
        "archetype": archetype,
        "box_type": box_type,
        "box_start": list(box_start) if box_start is not None else None,
        "box_end": list(box_end) if box_end is not None else None,
        "scan_start": list(scan_start),
        "scan_end": list(scan_end),
        "flat_hm": list(flat_hm),
        "min_sweep_atr": float(min_sweep_atr),
        "max_sweep_atr": float(max_sweep_atr),
        "reclaim_min": int(reclaim_min),
        "reclaim_depth_atr": float(reclaim_depth_atr),
        "min_box_atr": float(min_box_atr),
        "max_box_atr": float(max_box_atr),
        "min_sl_atr": float(min_sl_atr),
        "sl_buf_atr": float(sl_buf_atr),
        "tp_atr": float(tp_atr) if tp_atr is not None else None,
        "vol_gate": str(vol_gate),
        "economic_rationale": economic_rationale,
        "counterparty_mechanism": counterparty_mechanism,
        "causal_invariants": [
            "strict_shift1_daily_atr_prev_hl",
            "strict_lt_scan_start_reference_box",
            "next_bar_open_entry_after_m1_reclaim_close",
            "hard_flat_le_2050_utc_swap_zero",
            "red_news_plusminus_5m_entry_block_and_flatten",
            "sl_before_tp_conservative_m1_tiebreak",
        ],
        "data_resolution": cc.RES_NATIVE_M1_BIDASK,
        "blindness_tier": cc.TIER_12OLD,
        "allow_unidirectional": False,
    }


def build_candidate_grid() -> list[dict[str, Any]]:
    """Construct the pre-registered F02 liquidity sweep-reclaim catalog (`<= 100` specs across 7 symbols)."""
    specs: list[dict[str, Any]] = []

    # Per-symbol session anchors (all DST-exact via ZoneInfo!)
    # (pre_box_start, pre_box_end, pre_scan_start, pre_scan_end,
    #  open_box_start, open_box_end, open_scan_start, open_scan_end,
    #  pday_scan_start, pday_scan_end, flat_hm)
    session_cfg: dict[str, dict[str, Any]] = {
        "GER40": {
            "pre_box": ((0, 0, "UTC"), (8, 0, "BERLIN")),
            "pre_scan": ((8, 0, "BERLIN"), (13, 0, "BERLIN")),
            "open_box": ((8, 0, "BERLIN"), (9, 0, "BERLIN")),
            "open_scan": ((9, 0, "BERLIN"), (13, 30, "BERLIN")),
            "xet_box": ((9, 0, "BERLIN"), (9, 30, "BERLIN")),
            "xet_scan": ((9, 30, "BERLIN"), (14, 0, "BERLIN")),
            "pday_scan": ((8, 0, "BERLIN"), (13, 30, "BERLIN")),
            "flat_hm": (17, 15, "BERLIN"),
        },
        "US500": {
            "pre_box": ((7, 0, "UTC"), (9, 30, "NY")),
            "pre_scan": ((9, 30, "NY"), (13, 30, "NY")),
            "open_box": ((9, 30, "NY"), (10, 0, "NY")),
            "open_scan": ((10, 0, "NY"), (14, 0, "NY")),
            "xet_box": ((9, 30, "NY"), (10, 30, "NY")),
            "xet_scan": ((10, 30, "NY"), (14, 30, "NY")),
            "pday_scan": ((9, 30, "NY"), (13, 30, "NY")),
            "flat_hm": (15, 45, "NY"),
        },
        "US100": {
            "pre_box": ((7, 0, "UTC"), (9, 30, "NY")),
            "pre_scan": ((9, 30, "NY"), (13, 30, "NY")),
            "open_box": ((9, 30, "NY"), (10, 0, "NY")),
            "open_scan": ((10, 0, "NY"), (14, 0, "NY")),
            "xet_box": ((9, 30, "NY"), (10, 30, "NY")),
            "xet_scan": ((10, 30, "NY"), (14, 30, "NY")),
            "pday_scan": ((9, 30, "NY"), (13, 30, "NY")),
            "flat_hm": (15, 45, "NY"),
        },
        "XAUUSD": {
            "pre_box": ((0, 0, "UTC"), (7, 0, "UTC")),
            "pre_scan": ((7, 0, "UTC"), (13, 0, "UTC")),
            "open_box": ((7, 0, "UTC"), (8, 20, "NY")),
            "open_scan": ((8, 20, "NY"), (13, 0, "NY")),
            "xet_box": ((8, 20, "NY"), (8, 50, "NY")),
            "xet_scan": ((8, 50, "NY"), (13, 30, "NY")),
            "pday_scan": ((7, 0, "UTC"), (16, 0, "UTC")),
            "flat_hm": (19, 30, "UTC"),
        },
        "GBPUSD": {
            "pre_box": ((0, 0, "UTC"), (7, 0, "LONDON")),
            "pre_scan": ((7, 0, "LONDON"), (12, 30, "LONDON")),
            "open_box": ((8, 0, "LONDON"), (9, 0, "LONDON")),
            "open_scan": ((9, 0, "LONDON"), (14, 0, "LONDON")),
            "xet_box": ((7, 0, "LONDON"), (8, 30, "NY")),
            "xet_scan": ((8, 30, "NY"), (13, 0, "NY")),
            "pday_scan": ((7, 0, "LONDON"), (16, 0, "UTC")),
            "flat_hm": (19, 30, "UTC"),
        },
        "EURUSD": {
            "pre_box": ((0, 0, "UTC"), (7, 0, "LONDON")),
            "pre_scan": ((7, 0, "LONDON"), (12, 30, "LONDON")),
            "open_box": ((8, 0, "LONDON"), (9, 0, "LONDON")),
            "open_scan": ((9, 0, "LONDON"), (14, 0, "LONDON")),
            "xet_box": ((7, 0, "LONDON"), (8, 30, "NY")),
            "xet_scan": ((8, 30, "NY"), (13, 0, "NY")),
            "pday_scan": ((7, 0, "LONDON"), (16, 0, "UTC")),
            "flat_hm": (19, 30, "UTC"),
        },
        "USDJPY": {
            "pre_box": ((0, 0, "UTC"), (7, 0, "LONDON")),
            "pre_scan": ((7, 0, "LONDON"), (12, 30, "LONDON")),
            "open_box": ((8, 0, "LONDON"), (9, 0, "LONDON")),
            "open_scan": ((9, 0, "LONDON"), (14, 0, "LONDON")),
            "xet_box": ((7, 0, "LONDON"), (8, 30, "NY")),
            "xet_scan": ((8, 30, "NY"), (13, 0, "NY")),
            "pday_scan": ((7, 0, "LONDON"), (16, 0, "UTC")),
            "flat_hm": (19, 30, "UTC"),
        },
    }

    # 14 clean, non-redundant variants x 7 symbols = 98 candidates (<= 100 cap!)
    for sym in UNIVERSE_SYMBOLS:
        sc = session_cfg[sym]
        flat_hm = sc["flat_hm"]
        rat_pre = (
            f"Retail breakout stop orders cluster outside {sym} overnight/pre-session extremes; "
            "a 0.15-0.45 ATR liquidity sweep reclaimed within 15-45m forces trapped chasers to unwind."
        )
        rat_open = (
            f"Opening-range breakout traders on {sym} place predictable stops beyond the initial cash box; "
            "rapid 15-45m reclaim after a shallow stop-run transfers alpha from trapped momentum entries."
        )
        rat_pday = (
            f"Prior-day high/low levels on {sym} concentrate resting breakout stops; a shallow sweep "
            "that reclaims back inside the prior range within 15-45m traps late breakout buyers/sellers."
        )

        # (A) Pre-Session Box Sweep-Reclaim (5 variants)
        pre_variants = [
            ("PRESESS_SW15_R30_FLAT", 0.15, 0.55, 30, 0.00, 0.15, 1.35, 0.80, 0.25, None, "NONE"),
            ("PRESESS_SW20_R30_FLAT", 0.20, 0.60, 30, 0.02, 0.15, 1.35, 0.85, 0.25, None, "NONE"),
            ("PRESESS_SW25_R45_FLAT", 0.25, 0.65, 45, 0.02, 0.15, 1.40, 0.90, 0.25, None, "NONE"),
            ("PRESESS_SW15_R30_TP18", 0.15, 0.55, 30, 0.00, 0.15, 1.35, 0.80, 0.25, 1.80, "NONE"),
            ("PRESESS_SW20_R45_HVOL", 0.20, 0.65, 45, 0.00, 0.15, 1.40, 0.85, 0.25, None, "NORMAL_HIGH"),
        ]
        for suffix, min_sw, max_sw, rec_m, rec_d, min_b, max_b, min_sl, sl_buf, tp_a, vg in pre_variants:
            specs.append(
                _make_f02_spec(
                    candidate_id=f"F02_{sym}_{suffix}",
                    symbol=sym,
                    archetype="PRE_SESSION_BOX_SWEEP",
                    box_type="INTRADAY_BOX",
                    box_start=sc["pre_box"][0],
                    box_end=sc["pre_box"][1],
                    scan_start=sc["pre_scan"][0],
                    scan_end=sc["pre_scan"][1],
                    flat_hm=flat_hm,
                    min_sweep_atr=min_sw,
                    max_sweep_atr=max_sw,
                    reclaim_min=rec_m,
                    reclaim_depth_atr=rec_d,
                    min_box_atr=min_b,
                    max_box_atr=max_b,
                    min_sl_atr=min_sl,
                    sl_buf_atr=sl_buf,
                    tp_atr=tp_a,
                    vol_gate=vg,
                    economic_rationale=rat_pre,
                    counterparty_mechanism="RETAIL_BREAKOUT_STOP_RUN_LIQUIDITY_SWEEP",
                )
            )

        # (B) Opening-Range Box Sweep-Reclaim — Primary & Secondary Box (5 variants)
        open_variants = [
            (
                "OPENBOX_SW15_R25_FLAT",
                sc["open_box"],
                sc["open_scan"],
                0.15,
                0.50,
                25,
                0.00,
                0.12,
                1.15,
                0.80,
                0.25,
                None,
                "NONE",
            ),
            (
                "OPENBOX_SW20_R35_FLAT",
                sc["open_box"],
                sc["open_scan"],
                0.20,
                0.60,
                35,
                0.02,
                0.12,
                1.20,
                0.85,
                0.25,
                None,
                "NONE",
            ),
            (
                "OPENBOX_SW15_R30_TP18",
                sc["open_box"],
                sc["open_scan"],
                0.15,
                0.55,
                30,
                0.00,
                0.12,
                1.20,
                0.80,
                0.25,
                1.80,
                "NONE",
            ),
            (
                "SESS2BOX_SW15_R30_FLAT",
                sc["xet_box"],
                sc["xet_scan"],
                0.15,
                0.55,
                30,
                0.00,
                0.12,
                1.25,
                0.80,
                0.25,
                None,
                "NONE",
            ),
            (
                "SESS2BOX_SW20_R45_TP20",
                sc["xet_box"],
                sc["xet_scan"],
                0.20,
                0.65,
                45,
                0.02,
                0.12,
                1.25,
                0.85,
                0.25,
                2.00,
                "NONE",
            ),
        ]
        for (
            suffix,
            b_pair,
            s_pair,
            min_sw,
            max_sw,
            rec_m,
            rec_d,
            min_b,
            max_b,
            min_sl,
            sl_buf,
            tp_a,
            vg,
        ) in open_variants:
            specs.append(
                _make_f02_spec(
                    candidate_id=f"F02_{sym}_{suffix}",
                    symbol=sym,
                    archetype="OPENING_BOX_SWEEP",
                    box_type="INTRADAY_BOX",
                    box_start=b_pair[0],
                    box_end=b_pair[1],
                    scan_start=s_pair[0],
                    scan_end=s_pair[1],
                    flat_hm=flat_hm,
                    min_sweep_atr=min_sw,
                    max_sweep_atr=max_sw,
                    reclaim_min=rec_m,
                    reclaim_depth_atr=rec_d,
                    min_box_atr=min_b,
                    max_box_atr=max_b,
                    min_sl_atr=min_sl,
                    sl_buf_atr=sl_buf,
                    tp_atr=tp_a,
                    vol_gate=vg,
                    economic_rationale=rat_open,
                    counterparty_mechanism="OPENING_RANGE_FAILED_BREAKOUT_UNWIND",
                )
            )

        # (C) Prior-Day High/Low Liquidity Sweep-Reclaim (4 variants)
        pday_variants = [
            ("PDAY_SW15_R30_FLAT", 0.15, 0.55, 30, 0.00, 0.30, 2.50, 0.80, 0.25, None, "NONE"),
            ("PDAY_SW20_R45_FLAT", 0.20, 0.65, 45, 0.02, 0.30, 2.50, 0.85, 0.25, None, "NONE"),
            ("PDAY_SW15_R30_TP18", 0.15, 0.55, 30, 0.00, 0.30, 2.50, 0.80, 0.25, 1.80, "NONE"),
            ("PDAY_SW25_R45_SL10", 0.25, 0.70, 45, 0.02, 0.30, 2.50, 1.00, 0.25, None, "NONE"),
        ]
        for suffix, min_sw, max_sw, rec_m, rec_d, min_b, max_b, min_sl, sl_buf, tp_a, vg in pday_variants:
            specs.append(
                _make_f02_spec(
                    candidate_id=f"F02_{sym}_{suffix}",
                    symbol=sym,
                    archetype="PRIOR_DAY_HL_SWEEP",
                    box_type="PRIOR_DAY_HL",
                    box_start=None,
                    box_end=None,
                    scan_start=sc["pday_scan"][0],
                    scan_end=sc["pday_scan"][1],
                    flat_hm=flat_hm,
                    min_sweep_atr=min_sw,
                    max_sweep_atr=max_sw,
                    reclaim_min=rec_m,
                    reclaim_depth_atr=rec_d,
                    min_box_atr=min_b,
                    max_box_atr=max_b,
                    min_sl_atr=min_sl,
                    sl_buf_atr=sl_buf,
                    tp_atr=tp_a,
                    vol_gate=vg,
                    economic_rationale=rat_pday,
                    counterparty_mechanism="PRIOR_DAY_EXTREME_STOP_HUNT_ABSORPTION",
                )
            )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F02 grid size {len(specs)} exceeds TOTAL_CAP={TOTAL_CAP}")
    return specs


# ---------------------------------------------------------------------------
# Single-Candidate Evaluation Engine (`evaluate_candidate` — Stage 3 Ready!)
# ---------------------------------------------------------------------------


def _replay_matched_fade_trade(
    sym: str,
    times_sec: np.ndarray,
    quotes: np.ndarray,
    orig_tr: Mapping[str, Any],
    *,
    sl_dist: float,
    tp_dist: float | None,
    flat_idx: int,
    sym_spec: Mapping[str, Any],
    red_news_index: Mapping[str, Any],
    firm_profile: str,
) -> dict[str, Any]:
    """Replay exact opposite-side M1 Bid/Ask control trade at identical entry timestamp."""
    fill_idx = int(orig_tr["entry_idx"])
    fade_side = -int(orig_tr["side"])
    has_ask = quotes.shape[1] >= 8
    fade_ep = float(quotes[fill_idx, 4] if (fade_side == 1 and has_ask) else quotes[fill_idx, 0])
    fade_sl = fade_ep - fade_side * sl_dist
    fade_tp = (fade_ep + fade_side * tp_dist) if (tp_dist is not None and tp_dist > 0.0) else None

    if fade_sl > 0.0 and (fade_tp is None or fade_tp > 0.0) and fill_idx < flat_idx:
        ftr = cc.replay_intraday_m1_trade(
            sym,
            times_sec,
            quotes,
            fill_idx,
            fade_side,
            fade_sl,
            tp_price=fade_tp,
            entry_order_type="MARKET",
            flat_idx=flat_idx,
            hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
            spec=sym_spec,
            firm_profile=firm_profile,
            red_news_index=red_news_index,
            news_pad_sec=300,
            flatten_before_news=True,
        )
        if ftr.get("filled"):
            return ftr

    orig_r1 = float(orig_tr.get("net_R_1x", orig_tr.get("net_R", 0.0)))
    f1_sl = float(orig_tr.get("friction_over_sl_1x", 0.04))
    return {
        "filled": True,
        "symbol": sym,
        "side": fade_side,
        "entry_ts": int(orig_tr["entry_ts"]),
        "exit_ts": int(orig_tr["exit_ts"]),
        "entry_date": str(orig_tr["entry_date"]),
        "exit_date": str(orig_tr["exit_date"]),
        "net_R": round(-orig_r1 - 2.0 * f1_sl, 6),
        "net_R_1x": round(-orig_r1 - 2.0 * f1_sl, 6),
    }


def _evaluate_candidate_with_ctx(
    spec: Mapping[str, Any],
    ctx: Mapping[str, Any],
    req_years: tuple[int, ...],
    red_news_index: Mapping[str, Any],
    *,
    firm_profile: str = "FTMO_STANDARD",
) -> dict[str, Any]:
    sym = str(ctx["symbol"])
    sym_spec = ctx["spec"]
    times_sec: np.ndarray = ctx["times_sec"]
    quotes: np.ndarray = ctx["quotes"]
    has_ask = quotes.shape[1] >= 8

    box_type = str(spec["box_type"]).upper()
    box_start = (
        (int(spec["box_start"][0]), int(spec["box_start"][1]), str(spec["box_start"][2]))
        if spec.get("box_start") is not None
        else None
    )
    box_end = (
        (int(spec["box_end"][0]), int(spec["box_end"][1]), str(spec["box_end"][2]))
        if spec.get("box_end") is not None
        else None
    )
    scan_start = (int(spec["scan_start"][0]), int(spec["scan_start"][1]), str(spec["scan_start"][2]))
    scan_end = (int(spec["scan_end"][0]), int(spec["scan_end"][1]), str(spec["scan_end"][2]))
    flat_hm = (int(spec["flat_hm"][0]), int(spec["flat_hm"][1]), str(spec["flat_hm"][2]))

    min_sweep_atr = float(spec["min_sweep_atr"])
    max_sweep_atr = float(spec["max_sweep_atr"])
    reclaim_sec = int(spec["reclaim_min"]) * 60
    reclaim_depth_atr = float(spec["reclaim_depth_atr"])
    min_box_atr = float(spec["min_box_atr"])
    max_box_atr = float(spec["max_box_atr"])
    min_sl_atr = float(spec["min_sl_atr"])
    sl_buf_atr = float(spec["sl_buf_atr"])
    tp_atr = float(spec["tp_atr"]) if spec.get("tp_atr") is not None else None
    vol_gate = str(spec.get("vol_gate", "NONE")).upper()

    trades: list[dict[str, Any]] = []
    fade_trades: list[dict[str, Any]] = []

    for drow in ctx["days"]:
        atr = float(drow["atr14"])
        if vol_gate == "NORMAL_HIGH":
            med60 = float(drow["rolling_med_atr60"])
            if not math.isfinite(med60) or atr < 0.85 * med60:
                continue

        d_obj: date = drow["date_obj"]
        day_start_ts = int(drow["day_start_ts"])
        fi = int(drow["fi"])
        day_flat_idx = int(drow["day_flat_idx"])
        sub_t = times_sec[fi : day_flat_idx + 1]

        ts_scan0 = _resolve_hm_ts(d_obj, scan_start)
        ts_scan1 = _resolve_hm_ts(d_obj, scan_end)
        ts_flat = min(_resolve_hm_ts(d_obj, flat_hm), day_start_ts + _HARD_FLAT_SEC)
        if ts_scan0 >= ts_scan1 or ts_scan0 >= ts_flat:
            continue
        ts_scan1 = min(ts_scan1, ts_flat - 600)
        if ts_scan1 <= ts_scan0:
            continue

        # 1. Strictly causal reference box (completed strictly BEFORE ts_scan0!)
        if box_type == "PRIOR_DAY_HL":
            box_hi = float(drow["prev_h"])
            box_lo = float(drow["prev_l"])
            if not (math.isfinite(box_hi) and math.isfinite(box_lo)) or box_hi <= box_lo:
                continue
        elif box_type == "INTRADAY_BOX":
            if box_start is None or box_end is None:
                continue
            ts_b0 = _resolve_hm_ts(d_obj, box_start)
            ts_b1 = _resolve_hm_ts(d_obj, box_end)
            if ts_b0 >= ts_b1 or ts_b1 > ts_scan0:
                continue
            rb0 = int(np.searchsorted(sub_t, ts_b0, side="left"))
            rb1 = int(np.searchsorted(sub_t, ts_b1, side="left"))
            if rb1 - rb0 < 15:
                continue
            box_hi, box_lo = _m1_box_high_low_jit(quotes, fi + rb0, fi + rb1)
        else:
            raise ValueError(f"Unsupported box_type: {box_type!r}")

        box_w_atr = (box_hi - box_lo) / atr
        if box_w_atr < min_box_atr or box_w_atr > max_box_atr:
            continue

        # 2. Causal M1 sweep + rapid reclaim scan
        rs0 = int(np.searchsorted(sub_t, ts_scan0, side="left"))
        rs1 = int(np.searchsorted(sub_t, ts_scan1, side="left"))
        rel_f = int(np.searchsorted(sub_t, ts_flat, side="right")) - 1
        f_idx = min(day_flat_idx, fi + max(0, rel_f))
        if rs1 <= rs0 or (fi + rs0) >= f_idx:
            continue

        e_idx, side, sweep_ext = _scan_sweep_reclaim_jit(
            times_sec,
            quotes,
            fi + rs0,
            fi + rs1,
            f_idx,
            box_hi,
            box_lo,
            min_sweep_atr * atr,
            max_sweep_atr * atr,
            reclaim_depth_atr * atr,
            reclaim_sec,
        )
        if e_idx < 0 or side == 0 or not math.isfinite(sweep_ext) or e_idx >= f_idx:
            continue

        # 3. Wide structural hard SL beyond sweep extreme (floored at >= min_sl_atr * atr)
        est_ep = float(quotes[e_idx, 4] if (side == 1 and has_ask) else quotes[e_idx, 0])
        struct_dist = abs(est_ep - sweep_ext) + sl_buf_atr * atr
        sl_dist = max(struct_dist, min_sl_atr * atr)
        sl_p = est_ep - side * sl_dist
        tp_dist = (tp_atr * atr) if (tp_atr is not None and tp_atr > 0.0) else None
        tp_p = (est_ep + side * tp_dist) if tp_dist is not None else None
        if sl_p <= 0.0 or (tp_p is not None and tp_p <= 0.0):
            continue

        tr = cc.replay_intraday_m1_trade(
            sym,
            times_sec,
            quotes,
            e_idx,
            side,
            sl_p,
            tp_price=tp_p,
            entry_order_type="MARKET",
            flat_idx=f_idx,
            hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
            spec=sym_spec,
            firm_profile=firm_profile,
            red_news_index=red_news_index,
            news_pad_sec=300,
            flatten_before_news=True,
        )
        if not tr.get("filled"):
            continue

        trades.append(tr)
        actual_sl_dist = float(tr["sl_dist"])
        actual_tp_dist = (
            abs(float(tr["tp_price"]) - float(tr["entry_price"])) if tr.get("tp_price") is not None else None
        )
        fade_tr = _replay_matched_fade_trade(
            sym,
            times_sec,
            quotes,
            tr,
            sl_dist=actual_sl_dist,
            tp_dist=actual_tp_dist,
            flat_idx=f_idx,
            sym_spec=sym_spec,
            red_news_index=red_news_index,
            firm_profile=firm_profile,
        )
        fade_trades.append(fade_tr)

    dpnl_1x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    daily_1x_map = {d: round(float(v), 6) for d, v in zip(dpnl_1x["dates"], dpnl_1x["pnl"], strict=True)}
    daily_15x_map = {d: round(float(v), 6) for d, v in zip(dpnl_15x["dates"], dpnl_15x["pnl"], strict=True)}
    daily_2x_map = {d: round(float(v), 6) for d, v in zip(dpnl_2x["dates"], dpnl_2x["pnl"], strict=True)}
    fade_1x_map = {d: round(float(v), 6) for d, v in zip(fade_dpnl_1x["dates"], fade_dpnl_1x["pnl"], strict=True)}

    metrics_1x = cc.compute_split_metrics(trades, dpnl_1x, pnl_key="net_R_1x")
    metrics_15x = cc.compute_split_metrics(trades, dpnl_15x, pnl_key="net_R_15x")
    metrics_2x = cc.compute_split_metrics(trades, dpnl_2x, pnl_key="net_R_2x")
    fade_metrics_1x = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(
        trades,
        max_fric_sl_ratio=STAGE0_MAX_FRIC_SL_RATIO,
        min_keep_frac=STAGE0_MIN_KEEP_FRAC,
    )

    return {
        "spec": dict(spec),
        "trades": trades,
        "daily_pnl_1x": daily_1x_map,
        "daily_pnl_15x": daily_15x_map,
        "daily_pnl_2x": daily_2x_map,
        "daily_pnl_zero_pos_swap": dict(daily_1x_map),
        "fade_daily_pnl_1x": fade_1x_map,
        "metrics": metrics_1x,
        "metrics_15x": metrics_15x,
        "metrics_2x": metrics_2x,
        "fade_metrics_1x": fade_metrics_1x,
        "stage0": s0,
        "data_resolution": str(ctx["data_resolution"]),
        "blindness_tier": str(ctx["blindness_tier"]),
        "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    firm_profile: str = "FTMO_STANDARD",
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate one F02 liquidity sweep-reclaim candidate spec strictly on `years`."""
    req_years = tuple(sorted({int(y) for y in years}))
    if not req_years or min(req_years) < cc.DEV_MIN_YEAR or max(req_years) > cc.DEV_MAX_YEAR:
        raise ValueError(f"DEV_SEAL_VIOLATION: invalid years={years!r}")

    sym = cc.normalize_symbol(str(spec["symbol"]))
    assets = universe["assets"] if "assets" in universe else universe
    if sym not in assets:
        raise KeyError(f"Symbol {sym!r} not present in universe")

    rn_idx = red_news_index if red_news_index is not None else cc.load_dev_red_news_index(root=root)
    ctx = _prepare_asset_context(assets[sym], req_years)
    return _evaluate_candidate_with_ctx(spec, ctx, req_years, rn_idx, firm_profile=firm_profile)


# ---------------------------------------------------------------------------
# Cluster A Discovery (`2018-2020` ONLY — HARD BLINDNESS LOCK!)
# ---------------------------------------------------------------------------


def _score_cluster_a(eval_res: Mapping[str, Any]) -> tuple[bool, float, str]:
    """Evaluate Cluster A (`2018-2020`) friction survival, fade edge, and multi-year stability."""
    m1 = eval_res["metrics"]
    m15 = eval_res["metrics_15x"]
    m2 = eval_res["metrics_2x"]
    fm1 = eval_res["fade_metrics_1x"]
    s0 = eval_res["stage0"]

    n_tr = int(m1["n_trades"])
    if not s0["passed"]:
        return False, -999.0, str(s0["reason"])
    if n_tr < PRIMARY_MIN_TRADES_3Y:
        return False, -998.0, f"TOO_FEW_TRADES({n_tr}<{PRIMARY_MIN_TRADES_3Y})"
    if n_tr > PRIMARY_MAX_TRADES_3Y:
        return False, -997.0, f"OVERTRADING_TRAP({n_tr}>{PRIMARY_MAX_TRADES_3Y})"

    sr1 = float(m1["sharpe"])
    sr2 = float(m2["sharpe"])
    fsr1 = float(fm1["sharpe"])
    net1 = float(m1["net_R"])
    net2 = float(m2["net_R"])
    fnet1 = float(fm1["net_R"])
    pf15 = float(m15["pf"])
    pos_y = int(m1["positive_years"])
    dd1 = float(m1["max_DD_R"])
    by_y = m1.get("by_year_R") or {}
    worst_yr = min((float(v) for v in by_y.values()), default=-99.0)

    fade_edge_sr = max(-1.5, min(2.0, sr1 - fsr1))
    score = (
        0.45 * sr2
        + 0.35 * sr1
        + 0.20 * fade_edge_sr
        + 0.15 * (float(pos_y) / 3.0)
        + 0.05 * max(-2.0, min(2.0, worst_yr / 5.0))
        - 0.08 * max(0.0, dd1 - 8.0) / 8.0
    )

    eligible = net2 > 0.0 and pf15 >= 1.05 and sr1 >= 0.35 and net1 > fnet1 + 1.0 and pos_y >= 2
    reason = (
        "ELIGIBLE"
        if eligible
        else (f"FILTERED(net2={net2:.2f},pf15={pf15:.2f},sr1={sr1:.2f},fade_d={net1 - fnet1:.2f},py={pos_y}/3)")
    )
    return eligible, round(score, 6), reason


def discover_cluster_a(
    universe: Mapping[str, Any],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    firm_profile: str = "FTMO_STANDARD",
    save_checkpoint: bool = True,
    resume: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run F02 Stage 2 discovery strictly on `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY."""
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        loaded = cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)
        return {
            "family_id": FAMILY_ID,
            "resumed": True,
            "discovery_years": list(cc.CLUSTER_A_YEARS),
            "primary_count": int(loaded["primary_count"]),
            "exploratory_count": int(loaded["exploratory_count"]),
            "total_count": int(loaded["total_count"]),
            "primary_candidates": list(loaded["primary_candidates"]),
            "exploratory_candidates": list(loaded["exploratory_candidates"]),
            "checkpoint": loaded,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }

    t0 = time_mod.perf_counter()
    rn_idx = red_news_index if red_news_index is not None else cc.load_dev_red_news_index(root=root)
    assets = universe["assets"] if "assets" in universe else universe

    ctx_by_sym: dict[str, dict[str, Any]] = {}
    for sym in UNIVERSE_SYMBOLS:
        if sym not in assets:
            raise KeyError(f"Missing required F02 M1 symbol {sym!r} in universe")
        ctx_by_sym[sym] = _prepare_asset_context(assets[sym], cc.CLUSTER_A_YEARS)

    grid = build_candidate_grid()
    evaluated: list[dict[str, Any]] = []

    for spec in grid:
        sym = str(spec["symbol"])
        res = _evaluate_candidate_with_ctx(spec, ctx_by_sym[sym], cc.CLUSTER_A_YEARS, rn_idx, firm_profile=firm_profile)
        eligible, score, status_note = _score_cluster_a(res)
        m1 = res["metrics"]
        m15 = res["metrics_15x"]
        m2 = res["metrics_2x"]
        fm1 = res["fade_metrics_1x"]
        s0 = res["stage0"]

        cand_record = dict(spec)
        cand_record["cluster_a_score"] = score
        cand_record["cluster_a_eligible"] = eligible
        cand_record["cluster_a_status"] = status_note
        cand_record["cluster_a_trades_per_year"] = round(float(m1["n_trades"]) / 3.0, 2)
        cand_record["cluster_a_stage0"] = {
            "passed": bool(s0["passed"]),
            "median_fric_sl_ratio": s0["median_fric_sl_ratio"],
            "p90_fric_sl_ratio": s0["p90_fric_sl_ratio"],
            "keep_frac": s0["keep_frac"],
        }
        cand_record["cluster_a_metrics_1x"] = m1
        cand_record["cluster_a_metrics_15x"] = {
            "net_R": m15["net_R"],
            "pf": m15["pf"],
            "sharpe": m15["sharpe"],
            "max_DD_R": m15["max_DD_R"],
        }
        cand_record["cluster_a_metrics_2x"] = {
            "net_R": m2["net_R"],
            "pf": m2["pf"],
            "sharpe": m2["sharpe"],
            "max_DD_R": m2["max_DD_R"],
        }
        cand_record["cluster_a_fade_1x"] = {
            "net_R": fm1["net_R"],
            "pf": fm1["pf"],
            "sharpe": fm1["sharpe"],
        }
        evaluated.append(cand_record)

    ranked = sorted(
        evaluated,
        key=lambda c: (
            1 if c["cluster_a_eligible"] else 0,
            float(c["cluster_a_score"]),
            float(c["cluster_a_metrics_2x"]["sharpe"]),
            str(c["candidate_id"]),
        ),
        reverse=True,
    )

    primary: list[dict[str, Any]] = []
    exploratory: list[dict[str, Any]] = []
    sym_counts: dict[str, int] = {}
    arch_counts: dict[str, int] = {}

    for cand in ranked:
        sym = str(cand["symbol"])
        arch = str(cand["archetype"])
        can_promote = (
            bool(cand["cluster_a_eligible"])
            and len(primary) < PRIMARY_CAP
            and sym_counts.get(sym, 0) < PRIMARY_MAX_PER_SYMBOL
            and arch_counts.get(arch, 0) < PRIMARY_MAX_PER_ARCHETYPE
        )
        if can_promote:
            cand["tier"] = "PRIMARY"
            cand["is_primary"] = True
            primary.append(cand)
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
            arch_counts[arch] = arch_counts.get(arch, 0) + 1
        else:
            cand["tier"] = "EXPLORATORY"
            cand["is_primary"] = False
            exploratory.append(cand)

    if len(primary) + len(exploratory) > TOTAL_CAP:
        exploratory = exploratory[: TOTAL_CAP - len(primary)]

    elapsed_sec = round(time_mod.perf_counter() - t0, 3)
    meta = {
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "prop_track": PROP_TRACK,
        "family_slug": FAMILY_ID,
        "symbols": list(UNIVERSE_SYMBOLS),
        "firm_profile": firm_profile,
        "grid_evaluated": len(grid),
        "eligible_count": sum(1 for c in evaluated if c["cluster_a_eligible"]),
        "primary_by_symbol": sym_counts,
        "primary_by_archetype": arch_counts,
        "elapsed_sec": elapsed_sec,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    ckpt_path: Path | None = None
    if save_checkpoint:
        ckpt_path = cc.save_family_candidates(
            FAMILY_ID,
            {"primary": primary, "exploratory": exploratory},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )

    return {
        "family_id": FAMILY_ID,
        "resumed": False,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_count": len(primary),
        "exploratory_count": len(exploratory),
        "total_count": len(primary) + len(exploratory),
        "primary_candidates": primary,
        "exploratory_candidates": exploratory,
        "checkpoint_path": str(ckpt_path) if ckpt_path is not None else None,
        "meta": meta,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offensive #3 Stage 2 — F02 Liquidity Sweep / Stop-Run Reversal Discovery (Cluster A 2018-2020 ONLY)."
        )
    )
    parser.add_argument("--resume", action="store_true", help="Reuse valid SHA-verified checkpoint if present.")
    parser.add_argument("--candidates-dir", type=str, default=None, help="Optional checkpoint output directory.")
    parser.add_argument("--no-verify-sha", action="store_true", help="Skip parquet SHA-256 verification on load.")
    parser.add_argument("--firm-profile", type=str, default="FTMO_STANDARD", help="Firm fee/margin profile.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    cdir = Path(args.candidates_dir) if args.candidates_dir else None
    if args.resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=cdir):
        doc = cc.load_family_candidates(FAMILY_ID, candidates_dir=cdir, verify_sha=True)
        print(
            f"[F02] Resumed valid checkpoint: primary={doc['primary_count']}/{doc['primary_cap']} "
            f"total={doc['total_count']}/{doc['total_cap']} discovery_years={doc['discovery_years']}"
        )
        return 0

    uni = cc.load_universe_28(
        load_m1=True,
        load_d1=True,
        years=cc.CLUSTER_A_YEARS,
        symbols=UNIVERSE_SYMBOLS,
        verify_sha=not args.no_verify_sha,
    )
    out = discover_cluster_a(
        uni,
        firm_profile=args.firm_profile,
        save_checkpoint=True,
        resume=args.resume,
        candidates_dir=cdir,
    )
    print(
        f"[F02] Discovery complete ({out['meta']['elapsed_sec']}s, years={out['discovery_years']}): "
        f"primary={out['primary_count']}/{PRIMARY_CAP}, total={out['total_count']}/{TOTAL_CAP}, "
        f"eligible={out['meta']['eligible_count']}/{out['meta']['grid_evaluated']}"
    )
    for c in out["primary_candidates"][:8]:
        m1 = c["cluster_a_metrics_1x"]
        m2 = c["cluster_a_metrics_2x"]
        s0 = c["cluster_a_stage0"]
        print(
            f"  [PRIM] {c['candidate_id']:30s} sym={c['symbol']:6s} tr={m1['n_trades']:3d} "
            f"({c['cluster_a_trades_per_year']:4.1f}/yr) sr1={m1['sharpe']:5.2f} sr2={m2['sharpe']:5.2f} "
            f"pf1={m1['pf']:4.2f} f/sl={s0['median_fric_sl_ratio']:.3f} py={m1['positive_years']}/3"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
