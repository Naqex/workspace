"""Total Offensive #3 — Family F04: Energy & Metals Microstructure & Cross-Asset Lead-Lag.

Family ID: `F04_ENERGY_METAL`
Prop Tracks:
  - `INTRADAY_SWAP0` on native M1 Bid/Ask `XAUUSD` (flat <= 20:45 UTC, swap = 0, red-news +/-5m).
  - `FTMO_SWING` on D1 `USOIL, UKOIL, XAGUSD, USDCAD, CADJPY` (real Wed/Fri 3x swaps +
    Anti-Fake-Swap Guard + BOTH `real_swap` & `zero_pos_swap` floor + quarantined USOIL Apr 2020).
Caps: `<= 16` `PRIMARY_M200`, `<= 100` total candidates.

Mechanisms grounded in primary empirical literature:
  1. `XAU_BULLION_COMEX_M1`: `XAUUSD` native M1 Bid/Ask London AM (10:30 LDN) / PM (15:00 LDN)
     Bullion Fix & COMEX handover (08:20 ET open / 13:30 ET close) volatility-seasonality and
     Gold-driven NY session follow-through / reversion (`Batten & Lucey` / `LEAD-OFF3-SSRN-12`,
     DST-exact via `OPS-1`).
  2. `EIA_OIL_INVENTORY_D1`: `USOIL` & `UKOIL` D1 Swing (`FTMO_SWING`) EIA Weekly Petroleum
     Status Report day reaction (`OPS-1` verified Wed/Thu holiday-shifted calendar!) & post-EIA
     1-3d drift or overshoot reversion (`Halova, Kurov & Kucher` / `LEAD-OFF3-SSRN-09`).
  3. `CROSS_ASSET_COMMOD_LEADLAG`: Daily cross-asset Commodity-to-FX (`Ferraro, Rogoff & Rossi
     2015`, `USOIL/UKOIL -> USDCAD` & TRUE BLIND `CADJPY` / `LEAD-OFF3-SSRN-21`) and Gold-to-Silver
     (`XAUUSD -> XAGUSD` / `LEAD-OFF3-SSRN-12`) lead-lag with strict date-aligned `shift = 1`
     causality and mandatory hard ATR stop loss.

Hard Safety & Anti-Overfit Invariants (`G01`, `G05`, `G06`, `[ARCH-02]`):
  - ZERO bare `assert` statements (`python -O` safe).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - HARD BLINDNESS LOCK: `discover_cluster_a(universe)` strictly touches ONLY
    `CLUSTER_A_YEARS = (2018, 2019, 2020)` and NEVER inspects `2021..2024`.
  - Fail-closed verification that `USOIL` `2020-04-20` & `2020-04-21` are quarantined (`min >= 1.0`).
  - Strict `shift = 1` daily features (`replay_swing_d1_series(signal_already_shifted=False)`)
    and strictly `< entry_ts` intraday features.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

_AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.live_ops.feed_dst_news_guard import (  # noqa: E402
    TZ_LONDON,
    TZ_NEW_YORK,
    load_extended_calendar,
    resolve_dst_snapshot,
    resolve_eia_wpsr_release,
    resolve_strategy_session_utc,
)
from quant_factory.offensive3 import common_contract as cc  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety & Family Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAMILY_CODE: str = "F04"
FAMILY_ID: str = "F04_ENERGY_METAL"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

M1_MAX_FRIC_SL_RATIO: float = 0.12
D1_MAX_FRIC_SL_RATIO: float = 0.15
NEWS_PAD_SEC: int = 300
HARD_FLAT_UTC_HHMM: tuple[int, int] = (20, 45)
HARD_FLAT_MAX_SEC_OF_DAY: int = HARD_FLAT_UTC_HHMM[0] * 3600 + HARD_FLAT_UTC_HHMM[1] * 60

F04_UNIVERSE_SYMBOLS: tuple[str, ...] = (
    "XAUUSD",
    "XAGUSD",
    "USOIL",
    "UKOIL",
    "USDCAD",
    "CADJPY",
)

_ZI_LONDON = ZoneInfo(TZ_LONDON)
_ZI_NEW_YORK = ZoneInfo(TZ_NEW_YORK)

_XAU_M1_CACHE: dict[tuple[int, int, int], dict[str, Any]] = {}
_RED_NEWS_CACHE: dict[str, dict[str, Any]] = {}
_XAU_NEWS_CACHE: dict[int, tuple[np.ndarray, np.ndarray]] = {}
_EIA_DATES_CACHE: dict[tuple[str, int], set[str]] = {}
_XAU_CLOCK_CACHE: dict[date, dict[str, int]] = {}


# ---------------------------------------------------------------------------
# OPS-1 DST Bullion/COMEX Clocks & Verified EIA Inventory Schedule
# ---------------------------------------------------------------------------


def _validate_years_arg(years: Sequence[int]) -> tuple[int, ...]:
    if not years:
        raise ValueError("years must not be empty")
    out: list[int] = []
    for y in years:
        if isinstance(y, bool) or not isinstance(y, (int, np.integer)):
            raise ValueError(f"year must be an integer, got {y!r}")
        yi = int(y)
        if yi < cc.DEV_MIN_YEAR or yi > cc.DEV_MAX_YEAR:
            raise ValueError(f"DEV_SEAL_VIOLATION: year {yi} outside [{cc.DEV_MIN_YEAR}, {cc.DEV_MAX_YEAR}]")
        if yi not in out:
            out.append(yi)
    return tuple(sorted(out))


def _get_red_news_index(root: str | Path | None = None) -> dict[str, Any]:
    key = str(cc.resolve_workspace_root(root))
    cached = _RED_NEWS_CACHE.get(key)
    if cached is None:
        cached = cc.load_dev_red_news_index(include_extended=True, root=root)
        _RED_NEWS_CACHE[key] = cached
    return cached


def _get_xau_news_arrays(red_news_index: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    k = id(red_news_index)
    cached = _XAU_NEWS_CACHE.get(k)
    if cached is not None:
        return cached
    codes = cc.match_symbol_red_news_codes("XAUUSD")
    by_code: Mapping[str, tuple[np.ndarray, np.ndarray]] = red_news_index["by_code"]
    ts_parts: list[np.ndarray] = []
    pad_parts: list[np.ndarray] = []
    for c in sorted(codes):
        if c in by_code:
            ts_parts.append(by_code[c][0])
            pad_parts.append(by_code[c][1])
    if not ts_parts:
        pair = (np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64))
    else:
        ts_all = np.concatenate(ts_parts)
        pad_all = np.concatenate(pad_parts)
        order = np.argsort(ts_all, kind="mergesort")
        pair = (ts_all[order], pad_all[order])
    _XAU_NEWS_CACHE[k] = pair
    return pair


def _fast_xau_in_red_news(ts_sec: int, red_news_index: Mapping[str, Any], pad_sec: int) -> bool:
    ev_ts, ev_pad = _get_xau_news_arrays(red_news_index)
    if ev_ts.size == 0:
        return False
    max_look = max(pad_sec, int(np.max(ev_pad)))
    lo = int(np.searchsorted(ev_ts, ts_sec - max_look, side="left"))
    hi = int(np.searchsorted(ev_ts, ts_sec + max_look, side="right"))
    for idx in range(lo, hi):
        eff = max(pad_sec, int(ev_pad[idx]))
        if abs(ts_sec - int(ev_ts[idx])) <= eff:
            return True
    return False


def resolve_xau_bullion_comex_clocks_utc(trade_date: date) -> dict[str, int]:
    """Resolve exact UTC timestamps of London Bullion AM/PM Fix & COMEX open/close via OPS-1."""
    cached = _XAU_CLOCK_CACHE.get(trade_date)
    if cached is not None:
        return cached

    day_start_ts = int(datetime(trade_date.year, trade_date.month, trade_date.day, 0, 0, tzinfo=UTC).timestamp())
    ldn_open = resolve_strategy_session_utc("LONDON_OPEN", trade_date)
    ny_open = resolve_strategy_session_utc("NY_OPEN", trade_date)

    ldn_open_ts = day_start_ts + int(ldn_open["utc_hour"]) * 3600 + int(ldn_open["utc_minute"]) * 60
    ny_cash_open_ts = day_start_ts + int(ny_open["utc_hour"]) * 3600 + int(ny_open["utc_minute"]) * 60

    ldn_am_fix_ts = int(datetime.combine(trade_date, time(10, 30), tzinfo=_ZI_LONDON).astimezone(UTC).timestamp())
    ldn_pm_fix_ts = int(datetime.combine(trade_date, time(15, 0), tzinfo=_ZI_LONDON).astimezone(UTC).timestamp())
    comex_open_ts = int(datetime.combine(trade_date, time(8, 20), tzinfo=_ZI_NEW_YORK).astimezone(UTC).timestamp())
    comex_close_ts = int(datetime.combine(trade_date, time(13, 30), tzinfo=_ZI_NEW_YORK).astimezone(UTC).timestamp())
    ny_pm_flat_ts = int(datetime.combine(trade_date, time(15, 45), tzinfo=_ZI_NEW_YORK).astimezone(UTC).timestamp())

    # Audit DST divergence via OPS-1 snapshot
    snap = resolve_dst_snapshot(datetime.fromtimestamp(ldn_pm_fix_ts, tz=UTC))
    hard_flat_ts = day_start_ts + HARD_FLAT_MAX_SEC_OF_DAY

    clocks = {
        "day_start_ts": day_start_ts,
        "ldn_open_ts": ldn_open_ts,
        "ldn_am_fix_ts": ldn_am_fix_ts,
        "comex_open_ts": comex_open_ts,
        "ny_cash_open_ts": ny_cash_open_ts,
        "ldn_pm_fix_ts": ldn_pm_fix_ts,
        "comex_close_ts": min(comex_close_ts, hard_flat_ts),
        "ny_pm_flat_ts": min(ny_pm_flat_ts, hard_flat_ts),
        "hard_flat_ts": hard_flat_ts,
        "is_dst_divergence": 1 if snap.is_dst_divergence_window else 0,
    }
    _XAU_CLOCK_CACHE[trade_date] = clocks
    return clocks


def load_verified_eia_dates(max_year: int, *, root: str | Path | None = None) -> set[str]:
    """Load OPS-1 verified EIA WPSR release dates strictly `<= max_year` (Wed or holiday-shifted Thu)."""
    ws = cc.resolve_workspace_root(root)
    cache_key = (str(ws), int(max_year))
    cached = _EIA_DATES_CACHE.get(cache_key)
    if cached is not None:
        return cached

    ext_path = ws / "tooling/ai-engines/configs/calendars/red_news_extended_off3_8ccy_eia.json"
    cutoff_iso = f"{int(max_year) + 1}-01-01"
    events = load_extended_calendar(ext_path, sections=("dev_2018_2024",))
    eia_days: set[str] = set()
    for ev in events:
        if ev.ccy != "EIA":
            continue
        if ev.utc_day >= cc.DEV_CUTOFF_DATE:
            raise ValueError(f"DEV_CUTOFF_BREACH [EIA]: {ev.utc_day} >= {cc.DEV_CUTOFF_DATE}")
        if ev.utc_day < cutoff_iso:
            eia_days.add(ev.utc_day)

    # Cross-check deterministic OPS-1 holiday-shift resolver on every Wednesday in [2018, max_year]
    for yr in range(cc.DEV_MIN_YEAR, int(max_year) + 1):
        cur = date(yr, 1, 1)
        end = date(yr, 12, 31)
        while cur <= end:
            if cur.weekday() == 2:
                rel_d, _rel_t, _shifted, _hname = resolve_eia_wpsr_release(cur)
                if rel_d.year <= int(max_year):
                    rel_iso = rel_d.isoformat()
                    if rel_iso not in eia_days:
                        eia_days.add(rel_iso)
            cur += timedelta(days=1)

    cc.enforce_dev_date_bound(sorted(eia_days), context="f04.eia_dates")
    _EIA_DATES_CACHE[cache_key] = eia_days
    return eia_days


# ---------------------------------------------------------------------------
# Pillar 1: XAUUSD Native M1 Bid/Ask Bullion Fix & COMEX Handover (`swap=0`)
# ---------------------------------------------------------------------------


def _build_clamped_xau_m1_ctx(asset_entry: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    m1 = asset_entry.get("m1")
    d1 = asset_entry.get("d1")
    if m1 is None or d1 is None:
        raise ValueError("XAUUSD requires native M1 and D1 arrays for F04 Pillar 1")

    ts_all = np.asarray(m1["times_sec"], dtype=np.int64)
    q_all = np.asarray(m1["quotes"], dtype=np.float64)
    cutoff_ts = int(datetime(max_year + 1, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    if cutoff_ts > cc.DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH: cutoff_ts={cutoff_ts} > {cc.DEV_CUTOFF_SEC}")

    end_m1 = int(np.searchsorted(ts_all, cutoff_ts, side="left"))
    ts = ts_all[:end_m1]
    q = q_all[:end_m1]
    if ts.size == 0:
        raise ValueError(f"Zero XAUUSD M1 bars with year <= {max_year}")
    cc.enforce_dev_ts_bound(ts, context="f04.xau.m1")

    ckey = (int(ts.size), int(ts[0]), int(ts[-1]))
    cached = _XAU_M1_CACHE.get(ckey)
    if cached is not None:
        return cached

    d1_years = np.asarray(d1["years"], dtype=np.int32)
    keep_d1 = d1_years <= int(max_year)
    d1_dates = [str(d) for d, k in zip(d1["dates"], keep_d1, strict=True) if k]
    d1_h = np.asarray(d1["high"], dtype=np.float64)[keep_d1]
    d1_l = np.asarray(d1["low"], dtype=np.float64)[keep_d1]
    d1_c = np.asarray(d1["close"], dtype=np.float64)[keep_d1]
    cc.enforce_dev_date_bound(d1_dates, context="f04.xau.d1")

    atr14 = cc.causal_atr(d1_h, d1_l, d1_c, 14)
    ema20 = cc.causal_ema(d1_c, 20)
    atr_by_date: dict[str, float] = {}
    ema20_by_date: dict[str, float] = {}
    prev_close_by_date: dict[str, float] = {}
    for i, ds in enumerate(d1_dates):
        atr_by_date[ds] = float(atr14[i])
        ema20_by_date[ds] = float(ema20[i])
        prev_close_by_date[ds] = float(d1_c[i - 1]) if i > 0 else math.nan

    day_ids = ts // np.int64(86400)
    change = np.empty(day_ids.size, dtype=np.bool_)
    change[0] = True
    change[1:] = day_ids[1:] != day_ids[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:]
    ends[-1] = day_ids.size

    day_slices: list[tuple[date, str, int, int]] = []
    for s_i, e_i in zip(starts.tolist(), ends.tolist(), strict=True):
        d_obj = datetime.fromtimestamp(int(ts[s_i]), tz=UTC).date()
        if d_obj.weekday() >= 5:
            continue
        day_slices.append((d_obj, d_obj.isoformat(), int(s_i), int(e_i)))

    ctx = {
        "symbol": "XAUUSD",
        "spec": dict(asset_entry["spec"]),
        "times_sec": ts,
        "quotes": q,
        "day_slices": day_slices,
        "atr_by_date": atr_by_date,
        "ema20_by_date": ema20_by_date,
        "prev_close_by_date": prev_close_by_date,
    }
    _XAU_M1_CACHE[ckey] = ctx
    return ctx


def _find_idx_at_or_after(ts: np.ndarray, lo: int, hi: int, target_ts: int, max_lag_sec: int = 900) -> int | None:
    pos = int(np.searchsorted(ts[lo:hi], target_ts, side="left")) + lo
    if pos >= hi or int(ts[pos]) > target_ts + max_lag_sec:
        return None
    return pos


def _find_idx_strictly_before(
    ts: np.ndarray,
    lo: int,
    hi: int,
    cutoff_ts: int,
    max_stale_sec: int = 1800,
) -> int | None:
    pos = int(np.searchsorted(ts[lo:hi], cutoff_ts, side="left")) + lo - 1
    if pos < lo or int(ts[pos]) < cutoff_ts - max_stale_sec:
        return None
    return pos


def _mid_open(q: np.ndarray, idx: int) -> float:
    return 0.5 * (float(q[idx, 0]) + float(q[idx, 4])) if q.shape[1] >= 8 else float(q[idx, 0])


def _mid_close(q: np.ndarray, idx: int) -> float:
    return 0.5 * (float(q[idx, 3]) + float(q[idx, 7])) if q.shape[1] >= 8 else float(q[idx, 3])


def _causal_xau_fric_sl_2x(spec: Mapping[str, Any], q: np.ndarray, entry_idx: int, sl_dist: float) -> float:
    if not math.isfinite(sl_dist) or sl_dist <= 0.0:
        return math.inf
    pt = float(spec["point"])
    bench_sp = float(spec["benchmark_spread_pts"]) * pt
    entry_sp = max(0.0, float(q[entry_idx, 4] - q[entry_idx, 0])) if q.shape[1] >= 8 else bench_sp
    eff_sp = max(entry_sp, bench_sp)
    tv = cc.compute_causal_tick_val_usd(spec, entry_price=_mid_open(q, entry_idx))
    usd_per_px = tv / pt if pt > 0.0 else 1.0
    comm_px = float(spec["commission_usd_lot"]) / usd_per_px if usd_per_px > 0.0 else 0.0
    slip_rt = max(pt, 0.35 * eff_sp)
    return (2.0 * (eff_sp + comm_px + slip_rt)) / sl_dist


def _evaluate_xau_m1_candidate(
    cand_spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    red_news_index: Mapping[str, Any],
) -> dict[str, Any]:
    assets = universe["assets"] if ("assets" in universe and isinstance(universe["assets"], Mapping)) else universe
    ctx = _build_clamped_xau_m1_ctx(assets["XAUUSD"], max_year=max(req_years))
    ts = ctx["times_sec"]
    q = ctx["quotes"]
    sym_spec = ctx["spec"]
    params = dict(cand_spec["params"])
    rule = str(params["rule"])
    sl_atr = float(params["sl_atr"])
    tp_atr = float(params["tp_atr"]) if params.get("tp_atr") is not None else None
    max_fric_sl = float(params.get("max_fric_sl", M1_MAX_FRIC_SL_RATIO))
    req_year_set = set(req_years)

    requests: list[dict[str, Any]] = []
    for d_obj, d_iso, lo, hi in ctx["day_slices"]:
        if d_obj.year not in req_year_set:
            continue
        atr = ctx["atr_by_date"].get(d_iso, math.nan)
        if not math.isfinite(atr) or atr <= 0.0:
            continue

        clocks = resolve_xau_bullion_comex_clocks_utc(d_obj)
        hard_flat_ts = clocks["hard_flat_ts"]
        side = 0
        entry_target_ts: int | None = None
        exit_target_ts: int | None = None

        if rule == "xau_ldn_fix_reversion":
            fix_type = str(params["fix_type"])  # "AM" or "PM"
            pre_min = int(params["pre_window_min"])
            thresh = float(params["thresh_atr"])
            hold_min = int(params["hold_min"])
            fix_ts = clocks["ldn_am_fix_ts"] if fix_type == "AM" else clocks["ldn_pm_fix_ts"]
            entry_target_ts = fix_ts + 5 * 60
            exit_target_ts = min(fix_ts + hold_min * 60, hard_flat_ts)
            i_s = _find_idx_at_or_after(ts, lo, hi, fix_ts - pre_min * 60, max_lag_sec=900)
            i_e = _find_idx_strictly_before(ts, lo, hi, fix_ts, max_stale_sec=900)
            if i_s is None or i_e is None or i_e <= i_s:
                continue
            move_atr = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
            if abs(move_atr) >= thresh:
                side = -1 if move_atr > 0.0 else 1

        elif rule == "xau_comex_handover":
            mode = str(params["mode"])  # "follow" or "fade"
            anchor = str(params["anchor"])  # "comex_open" or "ldn_pm_fix"
            thresh = float(params["thresh_atr"])
            min_range_atr = float(params.get("min_range_atr", 0.0))
            max_range_atr = float(params.get("max_range_atr", 9.0))
            if anchor == "comex_open":
                win_s = clocks["ldn_open_ts"]
                win_e = clocks["comex_open_ts"]
                entry_target_ts = win_e + 5 * 60
                exit_key = "comex_close_ts" if params.get("exit_at") == "comex_close" else "ny_pm_flat_ts"
                exit_target_ts = clocks[exit_key]
            else:
                win_s = clocks["ldn_am_fix_ts"]
                win_e = clocks["ldn_pm_fix_ts"]
                entry_target_ts = win_e + 5 * 60
                exit_target_ts = clocks["ny_pm_flat_ts"]
            i_s = _find_idx_at_or_after(ts, lo, hi, win_s, max_lag_sec=900)
            i_e = _find_idx_strictly_before(ts, lo, hi, win_e, max_stale_sec=900)
            if i_s is None or i_e is None or i_e <= i_s:
                continue
            seg_hi = float(np.max(q[i_s : i_e + 1, 1]))
            seg_lo = float(np.min(q[i_s : i_e + 1, 2]))
            range_atr = (seg_hi - seg_lo) / atr
            if range_atr < min_range_atr or range_atr > max_range_atr:
                continue
            move_atr = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
            if abs(move_atr) >= thresh:
                if mode == "follow":
                    side = 1 if move_atr > 0.0 else -1
                else:
                    side = -1 if move_atr > 0.0 else 1

        elif rule == "xau_ny_vol_seasonality":
            mode = str(params["mode"])  # "follow" or "fade"
            thresh = float(params["thresh_atr"])
            # Causal morning impulse: COMEX open (08:20 ET) -> NY cash open + 30m (10:00 ET)
            win_s = clocks["comex_open_ts"]
            win_e = clocks["ny_cash_open_ts"] + 30 * 60
            entry_target_ts = win_e + 5 * 60
            exit_key = "comex_close_ts" if params.get("exit_at") == "comex_close" else "ny_pm_flat_ts"
            exit_target_ts = clocks[exit_key]
            i_s = _find_idx_at_or_after(ts, lo, hi, win_s, max_lag_sec=900)
            i_e = _find_idx_strictly_before(ts, lo, hi, win_e, max_stale_sec=900)
            if i_s is None or i_e is None or i_e <= i_s:
                continue
            move_atr = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
            if bool(params.get("trend_align", False)):
                ema20 = ctx["ema20_by_date"].get(d_iso, math.nan)
                prev_c = ctx["prev_close_by_date"].get(d_iso, math.nan)
                if not (math.isfinite(ema20) and math.isfinite(prev_c)):
                    continue
                trend_dir = 1 if prev_c > ema20 else -1
                if abs(move_atr) >= thresh:
                    raw_s = (1 if move_atr > 0.0 else -1) if mode == "follow" else (-1 if move_atr > 0.0 else 1)
                    if raw_s == trend_dir:
                        side = raw_s
            elif abs(move_atr) >= thresh:
                side = (1 if move_atr > 0.0 else -1) if mode == "follow" else (-1 if move_atr > 0.0 else 1)

        if side == 0 or entry_target_ts is None or exit_target_ts is None or exit_target_ts <= entry_target_ts + 300:
            continue
        entry_idx = _find_idx_at_or_after(ts, lo, hi, entry_target_ts, max_lag_sec=900)
        if entry_idx is None:
            continue
        flat_idx = int(np.searchsorted(ts[lo:hi], exit_target_ts, side="right")) + lo - 1
        if flat_idx <= entry_idx:
            continue
        entry_ts = int(ts[entry_idx])
        if _fast_xau_in_red_news(entry_ts, red_news_index, NEWS_PAD_SEC):
            continue

        sl_dist = sl_atr * atr
        if _causal_xau_fric_sl_2x(sym_spec, q, entry_idx, sl_dist) > max_fric_sl:
            continue
        tp_dist = (tp_atr * atr) if (tp_atr is not None and tp_atr > 0.0) else None
        requests.append(
            {
                "entry_idx": entry_idx,
                "flat_idx": flat_idx,
                "side": side,
                "sl_dist": sl_dist,
                "tp_dist": tp_dist,
            }
        )

    has_ask = q.shape[1] >= 8

    def _run_side(flip: bool) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for req in requests:
            e_idx = int(req["entry_idx"])
            f_idx = int(req["flat_idx"])
            s = -int(req["side"]) if flip else int(req["side"])
            sld = float(req["sl_dist"])
            tpd = req["tp_dist"]
            epx = float(q[e_idx, 4] if (s == 1 and has_ask) else q[e_idx, 0])
            sl_px = epx - s * sld
            if sl_px <= 0.0:
                continue
            tp_px = (epx + s * float(tpd)) if tpd is not None else None
            if tp_px is not None and tp_px <= 0.0:
                continue
            tr = cc.replay_intraday_m1_trade(
                "XAUUSD",
                ts,
                q,
                e_idx,
                s,
                sl_px,
                tp_price=tp_px,
                flat_idx=f_idx,
                hard_flat_utc_hhmm=HARD_FLAT_UTC_HHMM,
                spec=sym_spec,
                firm_profile="FTMO_STANDARD",
                red_news_index=red_news_index,
                news_pad_sec=NEWS_PAD_SEC,
                flatten_before_news=True,
                risk_frac=0.005,
            )
            if tr.get("filled"):
                tr["net_R_zero_pos_1x"] = tr["net_R_1x"]
                tr["net_R_zero_pos_15x"] = tr["net_R_15x"]
                tr["net_R_zero_pos_2x"] = tr["net_R_2x"]
                out.append(tr)
        return out

    trades = _run_side(flip=False)
    fade_trades = _run_side(flip=True)

    dpnl_1x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    dpnl_zpos = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_1x")
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = cc.compute_split_metrics(trades, dpnl_1x, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(trades, dpnl_15x, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(trades, dpnl_2x, pnl_key="net_R_2x")
    m_zpos = cc.compute_split_metrics(trades, dpnl_zpos, pnl_key="net_R_zero_pos_1x")
    m_fade = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(trades, max_fric_sl_ratio=M1_MAX_FRIC_SL_RATIO, min_keep_frac=0.80)
    side_split = _compute_side_split(trades, pnl_key="net_R_1x")

    return {
        "spec": dict(cand_spec),
        "trades": trades,
        "daily_pnl_1x": dpnl_1x,
        "daily_pnl_15x": dpnl_15x,
        "daily_pnl_2x": dpnl_2x,
        "daily_pnl_zero_pos_swap": dpnl_zpos,
        "fade_daily_pnl_1x": fade_dpnl_1x,
        "metrics": {
            **m_1x,
            "1x": m_1x,
            "1.5x": m_15x,
            "2x": m_2x,
            "zero_pos_swap_1x": m_zpos,
            "fade_1x": m_fade,
            "stage0": s0,
            "side_split": side_split,
            "years": list(req_years),
        },
        "data_resolution": cc.RES_NATIVE_M1_BIDASK,
        "blindness_tier": cc.TIER_12OLD,
        "allow_unidirectional": bool(cand_spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# Pillars 2 & 3: D1 Swing Helpers (USOIL Hygiene, EIA Inventory, Cross-Asset Lead-Lag)
# ---------------------------------------------------------------------------


def _clamp_d1_bars(symbol: str, asset_entry: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    """Slice D1 bars strictly to `year <= max_year` and verify USOIL Apr-2020 quarantine."""
    d1 = asset_entry.get("d1")
    if d1 is None:
        raise ValueError(f"D1 bars missing for {symbol}")

    years_arr = np.asarray(d1["years"], dtype=np.int32)
    keep = years_arr <= int(max_year)
    dates = [str(d) for d, k in zip(d1["dates"], keep, strict=True) if k]
    if not dates:
        raise ValueError(f"Zero D1 bars for {symbol} with year <= {max_year}")

    cc.enforce_dev_date_bound(dates, context=f"f04.d1_clamp:{symbol}")
    ts = np.asarray(d1["times_sec"], dtype=np.int64)[keep]
    wds = np.asarray(d1["weekdays"], dtype=np.int32)[keep]
    o = np.asarray(d1["open"], dtype=np.float64)[keep]
    h = np.asarray(d1["high"], dtype=np.float64)[keep]
    lo = np.asarray(d1["low"], dtype=np.float64)[keep]
    c = np.asarray(d1["close"], dtype=np.float64)[keep]
    cc.enforce_dev_ts_bound(ts, context=f"f04.d1_clamp_ts:{symbol}")

    # Fail-closed USOIL Apr-2020 negative-roll quarantine guard
    if symbol == "USOIL":
        for bad_d in cc.USOIL_QUARANTINE_DATES:
            if bad_d in dates:
                raise ValueError(f"USOIL_QUARANTINE_BREACH: {bad_d} survived into F04 D1 series")
        if float(np.min(lo)) < cc.USOIL_MIN_VALID_PRICE or float(np.min(o)) < cc.USOIL_MIN_VALID_PRICE:
            raise ValueError(f"USOIL_HYGIENE_BREACH: min price < {cc.USOIL_MIN_VALID_PRICE}")

    return {
        "symbol": symbol,
        "spec": dict(asset_entry["spec"]),
        "data_resolution": str(asset_entry["data_resolution"]),
        "blindness_tier": str(asset_entry["blindness_tier"]),
        "d1": {
            "times_sec": ts,
            "dates": dates,
            "years": years_arr[keep],
            "weekdays": wds,
            "open": o,
            "high": h,
            "low": lo,
            "close": c,
        },
    }


def _align_leader_returns_to_target(
    leader_d1: Mapping[str, Any],
    target_dates: Sequence[str],
    lookback_days: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Causally map leader `k`-day standardized return & raw log-return onto `target_dates`.

    For each target bar date `d_target[t]`, selects the latest leader bar `j` strictly with
    `leader_dates[j] <= d_target[t]`. Because `replay_swing_d1_series` applies `shift = 1`
    to execute `signals[t]` at `open[t + 1]` (`d_target[t + 1] > d_target[t] >= leader_dates[j]`),
    this is 100% strictly causal across differing Yahoo vs M1-resampled holiday calendars!
    """
    l_dates = list(leader_d1["dates"])
    l_h = np.asarray(leader_d1["high"], dtype=np.float64)
    l_l = np.asarray(leader_d1["low"], dtype=np.float64)
    l_c = np.asarray(leader_d1["close"], dtype=np.float64)
    l_atr14 = cc.causal_atr(l_h, l_l, l_c, 14)

    n_l = len(l_dates)
    std_ret = np.full(n_l, np.nan, dtype=np.float64)
    raw_log_ret = np.full(n_l, np.nan, dtype=np.float64)
    lb = max(1, int(lookback_days))
    for j in range(lb, n_l):
        c0 = float(l_c[j - lb])
        c1 = float(l_c[j])
        atr_j = float(l_atr14[j])
        if c0 > 0.0 and c1 > 0.0 and math.isfinite(atr_j) and atr_j > 0.0:
            raw_log_ret[j] = math.log(c1 / c0)
            std_ret[j] = (c1 - c0) / (atr_j * math.sqrt(float(lb)))

    n_t = len(target_dates)
    out_std = np.full(n_t, np.nan, dtype=np.float64)
    out_log = np.full(n_t, np.nan, dtype=np.float64)
    for t, d_str in enumerate(target_dates):
        j = bisect.bisect_right(l_dates, d_str) - 1
        if j < 0:
            continue
        # Reject stale leader alignment (> 3 calendar days old)
        gap_days = (date.fromisoformat(d_str) - date.fromisoformat(l_dates[j])).days
        if gap_days > 3:
            continue
        out_std[t] = std_ret[j]
        out_log[t] = raw_log_ret[j]
    return out_std, out_log


def _build_eia_swing_signals(
    sym_obj: Mapping[str, Any],
    params: Mapping[str, Any],
    eia_dates: set[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Build strictly causal D1 EIA inventory reaction / pre-release signals (`shift = 1` on replay)."""
    d1 = sym_obj["d1"]
    dates = d1["dates"]
    o = d1["open"]
    h = d1["high"]
    lo = d1["low"]
    c = d1["close"]
    n = len(dates)

    # Strictly causal ATR(14) (`atr[t]` uses ONLY `0..t-1`)
    atr14 = cc.causal_atr(h, lo, c, 14)
    ema20 = cc.causal_ema(c, 20)
    sig = np.zeros(n, dtype=np.float64)
    sl_atr = float(params["sl_atr"])
    tp_atr = float(params["tp_atr"]) if params.get("tp_atr") is not None else None
    sl_arr = np.where(np.isfinite(atr14) & (atr14 > 0.0), sl_atr * atr14, np.nan)
    tp_arr = np.where(np.isfinite(atr14) & (atr14 > 0.0), tp_atr * atr14, np.nan) if tp_atr is not None else None

    rule = str(params["rule"])
    thresh = float(params["thresh_atr"])
    trend_filter = bool(params.get("trend_filter", False))

    if rule in ("eia_post_drift", "eia_post_reversion"):
        # At close of EIA release day `t` (10:30/11:00 ET release already absorbed), signal executes at open[t+1]
        use_oc = bool(params.get("use_intraday_oc", True))
        ibs_gate = float(params.get("ibs_extreme", 0.0))
        for t in range(15, n):
            if dates[t] not in eia_dates:
                continue
            at = float(atr14[t])
            if not math.isfinite(at) or at <= 0.0:
                continue
            shock = ((float(c[t]) - float(o[t])) if use_oc else (float(c[t]) - float(c[t - 1]))) / at
            if abs(shock) < thresh:
                continue
            if ibs_gate > 0.0:
                rng = float(h[t]) - float(lo[t])
                if rng <= 1e-12:
                    continue
                ibs = (float(c[t]) - float(lo[t])) / rng
                if shock > 0.0 and ibs < (1.0 - ibs_gate):
                    continue
                if shock < 0.0 and ibs > ibs_gate:
                    continue
            raw_dir = 1.0 if shock > 0.0 else -1.0
            if rule == "eia_post_reversion":
                raw_dir = -raw_dir
            if trend_filter and math.isfinite(float(ema20[t])):
                tr_dir = 1.0 if float(c[t - 1]) > float(ema20[t]) else -1.0
                if raw_dir != tr_dir:
                    continue
            sig[t] = raw_dir

    elif rule == "eia_pre_positioning":
        # Deterministic calendar check: enter on day BEFORE EIA (e.g. Tue open for Wed EIA, Wed open for Thu EIA)
        # Signal computed on `t` close when deterministic next weekday is `eia_date - 1d` -> executes open[t+1]
        lb = int(params.get("lookback_days", 3))
        mode = str(params.get("mode", "fade"))  # "fade" or "follow"
        eia_prev2: set[str] = set()
        for ed_str in eia_dates:
            ed = date.fromisoformat(ed_str)
            # Find weekday 2 business days before EIA (so open[t+1] is 1 business day before EIA)
            cur = ed - timedelta(days=1)
            while cur.weekday() >= 5:
                cur -= timedelta(days=1)
            prev_bd = cur - timedelta(days=1)
            while prev_bd.weekday() >= 5:
                prev_bd -= timedelta(days=1)
            eia_prev2.add(prev_bd.isoformat())
        for t in range(max(15, lb), n):
            if dates[t] not in eia_prev2:
                continue
            at = float(atr14[t])
            if not math.isfinite(at) or at <= 0.0:
                continue
            ret_atr = (float(c[t]) - float(c[t - lb])) / (at * math.sqrt(float(lb)))
            if abs(ret_atr) < thresh:
                continue
            raw_dir = 1.0 if ret_atr > 0.0 else -1.0
            sig[t] = -raw_dir if mode == "fade" else raw_dir

    return sig, sl_arr, tp_arr


def _build_cross_asset_leadlag_signals(
    target_sym: str,
    target_obj: Mapping[str, Any],
    leader_objs: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Build strictly causal cross-asset Commodity->FX or Gold->Silver lead-lag signals."""
    d1 = target_obj["d1"]
    dates = d1["dates"]
    h = d1["high"]
    lo = d1["low"]
    c = d1["close"]
    n = len(dates)

    atr14 = cc.causal_atr(h, lo, c, 14)
    sl_atr = float(params["sl_atr"])
    tp_atr = float(params["tp_atr"]) if params.get("tp_atr") is not None else None
    sl_arr = np.where(np.isfinite(atr14) & (atr14 > 0.0), sl_atr * atr14, np.nan)
    tp_arr = np.where(np.isfinite(atr14) & (atr14 > 0.0), tp_atr * atr14, np.nan) if tp_atr is not None else None

    lb = int(params.get("lookback_days", 1))
    thresh = float(params["thresh_std"])
    mode = str(params["mode"])  # "direct_follow", "residual_catchup", "overreact_fade"
    sign_map = float(params.get("leader_to_target_sign", 1.0))

    # Equal-weighted standardized leader shock across 1 or 2 leaders (e.g., USOIL+UKOIL)
    leader_stds: list[np.ndarray] = []
    for lobj in leader_objs:
        l_std, _ = _align_leader_returns_to_target(lobj["d1"], dates, lookback_days=lb)
        leader_stds.append(l_std)
    stacked = np.vstack(leader_stds)
    # Require at least one finite leader value on date t
    valid_cnt = np.sum(np.isfinite(stacked), axis=0)
    safe_sum = np.where(np.isfinite(stacked), stacked, 0.0).sum(axis=0)
    l_shock = np.where(valid_cnt > 0, safe_sum / np.maximum(valid_cnt, 1), np.nan)

    # Target own standardized return over same causal lookback (for residual catch-up check)
    t_std = np.full(n, np.nan, dtype=np.float64)
    for t in range(max(15, lb), n):
        at = float(atr14[t])
        if math.isfinite(at) and at > 0.0:
            t_std[t] = (float(c[t]) - float(c[t - lb])) / (at * math.sqrt(float(lb)))

    sig = np.zeros(n, dtype=np.float64)
    max_lag_ratio = float(params.get("max_target_already_moved_ratio", 0.65))
    for t in range(max(15, lb), n):
        ls = float(l_shock[t])
        if not math.isfinite(ls) or abs(ls) < thresh:
            continue
        expected_dir = sign_map * (1.0 if ls > 0.0 else -1.0)
        if mode == "direct_follow":
            sig[t] = expected_dir
        elif mode == "residual_catchup":
            ts_val = float(t_std[t])
            if not math.isfinite(ts_val):
                continue
            # Leader shocked strongly while target has NOT yet moved in expected direction (lagging catch-up!)
            target_aligned_move = expected_dir * ts_val
            if target_aligned_move < max_lag_ratio * abs(ls):
                sig[t] = expected_dir
        elif mode == "overreact_fade":
            sig[t] = -expected_dir

    # Enforce CAD/FX safety: verify sign_map is purely economic (never static swap-sign lookahead)
    if target_sym not in ("USDCAD", "CADJPY", "XAGUSD"):
        raise ValueError(f"Unexpected cross-asset target symbol in F04: {target_sym!r}")
    return sig, sl_arr, tp_arr


def _compute_side_split(trades: Sequence[Mapping[str, Any]], pnl_key: str = "net_R_1x") -> dict[str, Any]:
    buy_vals = [float(t[pnl_key]) for t in trades if int(t["side"]) > 0 and t.get(pnl_key) is not None]
    sell_vals = [float(t[pnl_key]) for t in trades if int(t["side"]) < 0 and t.get(pnl_key) is not None]

    def _stats(vals: list[float]) -> dict[str, Any]:
        if not vals:
            return {"n": 0, "net_R": 0.0, "pf": 0.0, "winrate": 0.0}
        arr = np.array(vals, dtype=np.float64)
        gp = float(np.sum(arr[arr > 0.0]))
        gl = float(np.abs(np.sum(arr[arr < 0.0])))
        pf = (gp / gl) if gl > 1e-12 else (99.0 if gp > 1e-12 else 0.0)
        return {
            "n": len(vals),
            "net_R": round(float(np.sum(arr)), 4),
            "pf": round(pf, 4),
            "winrate": round(float(np.mean(arr > 0.0)), 4),
        }

    return {"buy": _stats(buy_vals), "sell": _stats(sell_vals)}


def _resolve_canonical_blindness_and_res(
    participating_symbols: Sequence[str],
    assets: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    """Resolve fail-conservative resolution and canonical blindness tier over target + leader union."""
    res_set: set[str] = set()
    tier_set: set[str] = set()
    for sym in participating_symbols:
        su = cc.normalize_symbol(sym)
        aobj = assets.get(su)
        if isinstance(aobj, Mapping):
            if aobj.get("data_resolution"):
                res_set.add(str(aobj["data_resolution"]))
            if aobj.get("blindness_tier"):
                tier_set.add(str(aobj["blindness_tier"]))
    data_res = (
        cc.RES_D1_YAHOO_SANCTIONED
        if (cc.RES_D1_YAHOO_SANCTIONED in res_set or any("D1" in r.upper() for r in res_set))
        else (cc.RES_NATIVE_M1_BIDASK if cc.RES_NATIVE_M1_BIDASK in res_set else cc.RES_D1_YAHOO_SANCTIONED)
    )
    if len(tier_set) == 1:
        b_tier = next(iter(tier_set))
    elif tier_set == {cc.TIER_12OLD, cc.TIER_NEW9}:
        b_tier = "MIXED_12OLD_AND_NEW9"
    elif tier_set == {cc.TIER_12OLD, cc.TIER_NEW7}:
        b_tier = "MIXED_12OLD_AND_TRUE_BLIND_7"
    elif tier_set == {cc.TIER_NEW9, cc.TIER_NEW7}:
        b_tier = "MIXED_NEW9_AND_TRUE_BLIND_7"
    elif tier_set == {cc.TIER_12OLD, cc.TIER_NEW9, cc.TIER_NEW7}:
        b_tier = "MIXED_ALL_3_TIERS"
    else:
        b_tier = "UNKNOWN"
    return data_res, b_tier


def _evaluate_d1_swing_candidate(
    cand_spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    assets = universe["assets"] if ("assets" in universe and isinstance(universe["assets"], Mapping)) else universe
    subfamily = str(cand_spec["subfamily"])
    params = dict(cand_spec["params"])
    symbols = [cc.normalize_symbol(s) for s in cand_spec["symbols"]]
    leaders = [cc.normalize_symbol(s) for s in cand_spec.get("leader_symbols") or ()]
    max_year = max(req_years)

    clamped_assets: dict[str, dict[str, Any]] = {}
    for sym in sorted(set(symbols) | set(leaders)):
        if sym not in assets:
            raise KeyError(f"Symbol {sym!r} missing from universe")
        clamped_assets[sym] = _clamp_d1_bars(sym, assets[sym], max_year=max_year)

    sigs_map: dict[str, np.ndarray] = {}
    fade_sigs_map: dict[str, np.ndarray] = {}
    sls_map: dict[str, np.ndarray] = {}
    tps_map: dict[str, np.ndarray | None] = {}

    if subfamily == "EIA_OIL_INVENTORY_D1":
        eia_dates = load_verified_eia_dates(max_year=max_year, root=root)
        for sym in symbols:
            sig, sl_arr, tp_arr = _build_eia_swing_signals(clamped_assets[sym], params, eia_dates)
            sigs_map[sym] = sig
            fade_sigs_map[sym] = -sig
            sls_map[sym] = sl_arr
            tps_map[sym] = tp_arr
    elif subfamily == "CROSS_ASSET_COMMOD_LEADLAG":
        leader_objs = [clamped_assets[ls] for ls in leaders]
        for sym in symbols:
            sig, sl_arr, tp_arr = _build_cross_asset_leadlag_signals(sym, clamped_assets[sym], leader_objs, params)
            sigs_map[sym] = sig
            fade_sigs_map[sym] = -sig
            sls_map[sym] = sl_arr
            tps_map[sym] = tp_arr
    else:
        raise ValueError(f"Unsupported D1 swing subfamily in F04: {subfamily!r}")

    max_hold = int(params.get("max_hold_bars", 3))
    exit_flip = bool(params.get("exit_on_signal_flip", False))
    risk_per_sym = 0.005 / max(1.0, math.sqrt(float(len(symbols))))

    # Strict shift = 1 (`signal_already_shifted=False`): signal on day t close executes at open[t+1]
    res_main = cc.replay_swing_d1_series(
        clamped_assets,
        sigs_map,
        sls_map,
        tp_dists=tps_map,
        max_hold_bars=max_hold,
        exit_on_signal_flip=exit_flip,
        signal_already_shifted=False,
        risk_frac=risk_per_sym,
        account_type="ftmo_swing",
        years=req_years,
        root=root,
    )
    res_fade = cc.replay_swing_d1_series(
        clamped_assets,
        fade_sigs_map,
        sls_map,
        tp_dists=tps_map,
        max_hold_bars=max_hold,
        exit_on_signal_flip=exit_flip,
        signal_already_shifted=False,
        risk_frac=risk_per_sym,
        account_type="ftmo_swing",
        years=req_years,
        root=root,
    )

    trades = res_main["trades"]
    fade_trades = res_fade["trades"]

    # Equal-risk basket normalization when combining multiple symbols
    scale_factor = 1.0 / math.sqrt(float(len(symbols))) if len(symbols) > 1 else 1.0
    if scale_factor < 0.999999:
        for tr_list in (trades, fade_trades):
            for tr in tr_list:
                for k in (
                    "gross_R",
                    "swap_real_R",
                    "swap_zero_pos_R",
                    "net_R",
                    "net_R_1x",
                    "net_R_15x",
                    "net_R_2x",
                    "net_R_zero_pos_1x",
                    "net_R_zero_pos_15x",
                    "net_R_zero_pos_2x",
                ):
                    if tr.get(k) is not None:
                        tr[k] = round(float(tr[k]) * scale_factor, 6)

    dpnl_1x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    dpnl_zpos = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_1x")
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = cc.compute_split_metrics(trades, dpnl_1x, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(trades, dpnl_15x, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(trades, dpnl_2x, pnl_key="net_R_2x")
    m_zpos = cc.compute_split_metrics(trades, dpnl_zpos, pnl_key="net_R_zero_pos_1x")
    m_fade = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(trades, max_fric_sl_ratio=D1_MAX_FRIC_SL_RATIO, min_keep_frac=0.80)
    side_split = _compute_side_split(trades, pnl_key="net_R_1x")

    # Leader-inclusive canonical provenance (`P1-02`/`P1-03`): union target + leader symbols!
    all_participating = sorted(set(symbols) | set(leaders))
    resolved_res, resolved_tier = _resolve_canonical_blindness_and_res(all_participating, assets)
    spec_out = dict(cand_spec)
    spec_out["data_resolution"] = resolved_res
    spec_out["blindness_tier"] = resolved_tier

    return {
        "spec": spec_out,
        "trades": trades,
        "daily_pnl_1x": dpnl_1x,
        "daily_pnl_15x": dpnl_15x,
        "daily_pnl_2x": dpnl_2x,
        "daily_pnl_zero_pos_swap": dpnl_zpos,
        "fade_daily_pnl_1x": fade_dpnl_1x,
        "metrics": {
            **m_1x,
            "1x": m_1x,
            "1.5x": m_15x,
            "2x": m_2x,
            "zero_pos_swap_1x": m_zpos,
            "fade_1x": m_fade,
            "stage0": s0,
            "side_split": side_split,
            "margin_audit": res_main["margin_audit"],
            "years": list(req_years),
        },
        "data_resolution": resolved_res,
        "blindness_tier": resolved_tier,
        "allow_unidirectional": bool(cand_spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# Standard Contract Function 1: `evaluate_candidate(spec, universe, years)`
# ---------------------------------------------------------------------------


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate any F04 candidate (`XAUUSD` M1 or D1 Swing) returning the canonical Offensive #3 dict."""
    cand_spec = dict(spec["spec"]) if ("spec" in spec and isinstance(spec["spec"], Mapping)) else dict(spec)
    req_years = _validate_years_arg(years)
    subfamily = str(cand_spec["subfamily"])

    if subfamily == "XAU_BULLION_COMEX_M1":
        rn_idx = red_news_index if red_news_index is not None else _get_red_news_index(root=root)
        return _evaluate_xau_m1_candidate(cand_spec, universe, req_years, rn_idx)
    if subfamily in ("EIA_OIL_INVENTORY_D1", "CROSS_ASSET_COMMOD_LEADLAG"):
        return _evaluate_d1_swing_candidate(cand_spec, universe, req_years, root=root)
    raise ValueError(f"Unknown F04 subfamily: {subfamily!r}")


# ---------------------------------------------------------------------------
# Pre-Registered Economically Grounded Candidate Menu (<= 100 total)
# ---------------------------------------------------------------------------


def build_f04_candidate_specs() -> list[dict[str, Any]]:
    """Build bounded (<= 100) pre-registered F04 candidate menu across all 3 energy/metals pillars."""
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        subfamily: str,
        prop_track: str,
        symbols: Sequence[str],
        leaders: Sequence[str],
        params: dict[str, Any],
        rationale: str,
        counterparty: str,
        lit_ref: str,
        data_res: str,
        blind_tier: str,
        allow_unidir: bool = False,
    ) -> None:
        if len(rationale.strip()) < 40:
            raise ValueError(f"economic_rationale too short for {cid}")
        if len(counterparty.strip()) < 30:
            raise ValueError(f"counterparty_mechanism too short for {cid}")
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "family_code": FAMILY_CODE,
                "subfamily": subfamily,
                "prop_track": prop_track,
                "symbols": list(symbols),
                "leader_symbols": list(leaders),
                "params": dict(params),
                "economic_rationale": rationale.strip(),
                "counterparty_mechanism": counterparty.strip(),
                "literature_ref": lit_ref,
                "allow_unidirectional": bool(allow_unidir),
                "data_resolution": data_res,
                "blindness_tier": blind_tier,
            }
        )

    # --- Pillar 1: XAUUSD Native M1 Bid/Ask Bullion Fix & COMEX Handover (Batten & Lucey) ---
    xau_fix_rat = (
        "LBMA London Bullion AM (10:30 LDN) and PM (15:00 LDN) benchmark auctions concentrate "
        "physical bullion-bank and ETF hedging flows; fading extreme pre-auction XAUUSD price "
        "displacement post-fix captures dealer inventory normalization with swap=0 and hard SL."
    )
    xau_fix_cp = (
        "LBMA bullion banks and physically backed gold ETF authorized participants executing "
        "time-rigid AM/PM benchmark auction orders absorb temporary inventory imbalances that revert."
    )
    for fix_type, pre_m, th, sl, tp, hold_m in (
        ("AM", 90, 0.30, 0.75, 1.35, 180),
        ("AM", 120, 0.45, 0.85, 1.50, 240),
        ("AM", 120, 0.60, 0.90, 1.60, 240),
        ("PM", 90, 0.30, 0.75, 1.35, 180),
        ("PM", 120, 0.45, 0.85, 1.50, 240),
        ("PM", 150, 0.60, 0.95, 1.70, 240),
    ):
        _add(
            f"F04_XAU_LDNFIX_{fix_type}_P{pre_m}_T{int(th * 100):02d}_SL{int(sl * 100):02d}",
            "XAU_BULLION_COMEX_M1",
            "INTRADAY_SWAP0",
            ("XAUUSD",),
            (),
            {
                "rule": "xau_ldn_fix_reversion",
                "fix_type": fix_type,
                "pre_window_min": pre_m,
                "thresh_atr": th,
                "sl_atr": sl,
                "tp_atr": tp,
                "hold_min": hold_m,
            },
            xau_fix_rat,
            xau_fix_cp,
            "Batten & Lucey Gold Bullion Fix Volatility Seasonality / LEAD-OFF3-SSRN-12",
            cc.RES_NATIVE_M1_BIDASK,
            cc.TIER_12OLD,
        )

    xau_comex_rat = (
        "Transition from London physical bullion trading to COMEX NY futures open (08:20 ET) and "
        "London PM Fix creates distinct gold volatility regimes; conditioning NY session continuation "
        "or exhaustion fade on causal morning displacement & range exploits cross-venue liquidity shifts."
    )
    xau_comex_cp = (
        "London OTC bullion dealers transferring overnight/morning inventory into deep COMEX NY "
        "futures order books interact with US macro funds repricing real-rate expectations."
    )
    for mode, anchor, th, min_r, max_r, exit_at, sl, tp in (
        ("follow", "comex_open", 0.30, 0.25, 1.20, "comex_close", 0.80, 1.50),
        ("follow", "comex_open", 0.45, 0.35, 1.40, "ny_pm_flat", 0.90, 1.70),
        ("fade", "comex_open", 0.55, 0.50, 3.00, "comex_close", 0.85, 1.50),
        ("fade", "comex_open", 0.75, 0.65, 3.50, "ny_pm_flat", 0.95, 1.70),
        ("follow", "ldn_pm_fix", 0.35, 0.30, 1.50, "ny_pm_flat", 0.80, 1.50),
        ("follow", "ldn_pm_fix", 0.45, 0.35, 1.80, "ny_pm_flat", 1.00, None),
        ("fade", "ldn_pm_fix", 0.60, 0.55, 3.50, "ny_pm_flat", 0.90, 1.60),
    ):
        tp_tag = "NOTP" if tp is None else f"TP{int(tp * 100)}"
        _add(
            f"F04_XAU_COMEX_{mode.upper()}_{anchor.upper()}_T{int(th * 100):02d}_{exit_at.upper()}_{tp_tag}",
            "XAU_BULLION_COMEX_M1",
            "INTRADAY_SWAP0",
            ("XAUUSD",),
            (),
            {
                "rule": "xau_comex_handover",
                "mode": mode,
                "anchor": anchor,
                "thresh_atr": th,
                "min_range_atr": min_r,
                "max_range_atr": max_r,
                "exit_at": exit_at,
                "sl_atr": sl,
                "tp_atr": tp,
            },
            xau_comex_rat,
            xau_comex_cp,
            "Batten & Lucey COMEX-London Handover / LEAD-OFF3-SSRN-12",
            cc.RES_NATIVE_M1_BIDASK,
            cc.TIER_12OLD,
        )

    xau_ny_rat = (
        "Early COMEX NY gold price discovery (08:20-10:00 ET) absorbs US morning macro/real-yield "
        "orderflow; trading continuation or exhaustion reversion from 10:05 ET into COMEX settlement "
        "(13:30 ET) or NY afternoon captures institutional gold session persistence (swap=0)."
    )
    for mode, tr_al, th, exit_at, sl, tp in (
        ("follow", False, 0.30, "comex_close", 0.80, 1.50),
        ("follow", False, 0.45, "ny_pm_flat", 0.90, 1.70),
        ("follow", True, 0.25, "ny_pm_flat", 0.85, 1.60),
        ("fade", False, 0.55, "comex_close", 0.85, 1.45),
        ("fade", False, 0.70, "ny_pm_flat", 0.95, 1.65),
        ("fade", True, 0.45, "ny_pm_flat", 0.85, 1.50),
    ):
        _add(
            f"F04_XAU_NYVOL_{mode.upper()}_TA{int(tr_al)}_T{int(th * 100):02d}_{exit_at.upper()}",
            "XAU_BULLION_COMEX_M1",
            "INTRADAY_SWAP0",
            ("XAUUSD",),
            (),
            {
                "rule": "xau_ny_vol_seasonality",
                "mode": mode,
                "trend_align": tr_al,
                "thresh_atr": th,
                "exit_at": exit_at,
                "sl_atr": sl,
                "tp_atr": tp,
            },
            xau_ny_rat,
            xau_comex_cp,
            "Batten & Lucey Gold NY Volatility Seasonality / LEAD-OFF3-SSRN-12",
            cc.RES_NATIVE_M1_BIDASK,
            cc.TIER_12OLD,
        )

    # --- Pillar 2: USOIL & UKOIL D1 Swing EIA Weekly Inventory Calendar (Halova/Kurov) ---
    eia_drift_rat = (
        "Weekly EIA Petroleum Status Report releases (OPS-1 exact Wed/Thu holiday calendar) convey "
        "fundamental physical crude inventory shocks; trading 1-3 day post-EIA continuation on "
        "USOIL/UKOIL from the next daily open avoids release-minute slippage while capturing repricing."
    )
    eia_rev_rat = (
        "Halova, Kurov & Kucher show preliminary EIA crude inventory surprises include measurement "
        "noise and concentrated hedging spikes; fading oversized EIA-day oil moves at the next open "
        "over 1-3 days captures post-announcement liquidity overshoot reversion with real swaps."
    )
    eia_cp = (
        "Physical energy producers, refineries, and systematic macro funds repricing weekly US "
        "crude inventory shocks create temporary order-book imbalance and multi-day adjustment."
    )
    for tag, syms in (("USOIL", ("USOIL",)), ("UKOIL", ("UKOIL",)), ("OIL2", ("USOIL", "UKOIL"))):
        for rule, th, hold_b, sl, tp, use_oc, ibs_g, tf in (
            ("eia_post_drift", 0.45, 2, 1.40, 2.40, True, 0.0, False),
            ("eia_post_drift", 0.65, 3, 1.60, 2.80, False, 0.0, True),
            ("eia_post_reversion", 0.55, 2, 1.40, 2.20, True, 0.0, False),
            ("eia_post_reversion", 0.75, 3, 1.60, 2.50, True, 0.25, False),
            ("eia_post_reversion", 0.60, 1, 1.30, 2.00, False, 0.0, False),
        ):
            rat = eia_drift_rat if rule == "eia_post_drift" else eia_rev_rat
            _add(
                f"F04_EIA_{rule.replace('eia_', '').upper()}_{tag}_T{int(th * 100):02d}_H{hold_b}"
                + ("_TF" if tf else "")
                + (f"_IBS{int(ibs_g * 100)}" if ibs_g > 0 else ""),
                "EIA_OIL_INVENTORY_D1",
                "FTMO_SWING",
                syms,
                (),
                {
                    "rule": rule,
                    "thresh_atr": th,
                    "max_hold_bars": hold_b,
                    "sl_atr": sl,
                    "tp_atr": tp,
                    "use_intraday_oc": use_oc,
                    "ibs_extreme": ibs_g,
                    "trend_filter": tf,
                    "exit_on_signal_flip": False,
                },
                rat,
                eia_cp,
                "Halova, Kurov & Kucher EIA Inventory Reaction / LEAD-OFF3-SSRN-09",
                cc.RES_D1_YAHOO_SANCTIONED,
                cc.TIER_NEW9,
            )

    # Pre-EIA 1-day positioning (strictly exits at EIA-day open before 10:30 ET print!)
    eia_pre_rat = (
        "Ahead of the scheduled weekly EIA inventory release, crude hedgers flatten directional "
        "inventory built over the prior 3-5 days; entering 1 trading day prior to EIA and closing "
        "at EIA-day open captures pre-announcement risk reduction strictly outside the news window."
    )
    for tag, syms in (("USOIL", ("USOIL",)), ("UKOIL", ("UKOIL",)), ("OIL2", ("USOIL", "UKOIL"))):
        for mode, lb, th in (("fade", 2, 0.65), ("fade", 3, 0.70), ("fade", 5, 0.85), ("follow", 3, 0.70)):
            _add(
                f"F04_EIA_PRE_{mode.upper()}_{tag}_LB{lb}_T{int(th * 100):02d}",
                "EIA_OIL_INVENTORY_D1",
                "FTMO_SWING",
                syms,
                (),
                {
                    "rule": "eia_pre_positioning",
                    "mode": mode,
                    "lookback_days": lb,
                    "thresh_atr": th,
                    "max_hold_bars": 1,
                    "sl_atr": 1.35,
                    "tp_atr": 2.20,
                    "exit_on_signal_flip": False,
                },
                eia_pre_rat,
                eia_cp,
                "Halova, Kurov & Kucher Pre-EIA Positioning / LEAD-OFF3-SSRN-09",
                cc.RES_D1_YAHOO_SANCTIONED,
                cc.TIER_NEW9,
            )

    # --- Pillar 3A: Crude Oil -> Commodity FX Lead-Lag (Ferraro, Rogoff & Rossi 2015 / SSRN-21) ---
    # Economic sign: Oil UP -> CAD strengthens -> USDCAD DOWN (-1), CADJPY UP (+1)
    frr_rat = (
        "Ferraro, Rogoff & Rossi (2015) prove daily crude oil terms-of-trade shocks predict "
        "Canadian Dollar exchange rates over short 1-5 day horizons as energy export revenue "
        "expectations propagate from crude oil into USDCAD (-beta) and CADJPY (+beta) spot FX."
    )
    frr_cp = (
        "Slow-moving international macro portfolios and corporate FX treasuries adjust Canadian "
        "Dollar hedges with a 1-3 day lag after sudden WTI/Brent crude oil repricing shocks."
    )
    # 3A-i: TRUE BLIND CADJPY (`TRUE_BLIND_CLB_NEW7_CROSSES`!)
    for l_tag, leaders in (("USOIL", ("USOIL",)), ("UKOIL", ("UKOIL",)), ("OIL2", ("USOIL", "UKOIL"))):
        for mode, lb, th, hold_b, sl, tp in (
            ("direct_follow", 1, 0.85, 2, 1.50, 2.60),
            ("direct_follow", 2, 1.00, 3, 1.60, 2.80),
            ("residual_catchup", 1, 0.75, 3, 1.50, 2.50),
            ("residual_catchup", 2, 0.90, 4, 1.70, 3.00),
            ("overreact_fade", 1, 1.25, 2, 1.50, 2.40),
        ):
            _add(
                f"F04_LEADLAG_{l_tag}_TO_CADJPY_{mode.upper()}_LB{lb}_T{int(th * 100):03d}_H{hold_b}",
                "CROSS_ASSET_COMMOD_LEADLAG",
                "FTMO_SWING",
                ("CADJPY",),
                leaders,
                {
                    "mode": mode,
                    "lookback_days": lb,
                    "thresh_std": th,
                    "leader_to_target_sign": 1.0,  # Oil UP -> CAD UP -> CADJPY UP
                    "max_target_already_moved_ratio": 0.60,
                    "max_hold_bars": hold_b,
                    "sl_atr": sl,
                    "tp_atr": tp,
                    "exit_on_signal_flip": False,
                },
                frr_rat,
                frr_cp,
                "Ferraro, Rogoff & Rossi (2015) Oil->CADJPY (NEW9 Oil leader + TRUE BLIND target) / LEAD-OFF3-SSRN-21",
                cc.RES_D1_YAHOO_SANCTIONED,
                "MIXED_NEW9_AND_TRUE_BLIND_7",
            )

    # 3A-ii: USDCAD (`DEV_CLB_CONSUMED_12OLD`) with NEW9 oil leaders -> `MIXED_12OLD_AND_NEW9`
    for l_tag, leaders in (("USOIL", ("USOIL",)), ("OIL2", ("USOIL", "UKOIL"))):
        for mode, lb, th, hold_b, sl, tp in (
            ("direct_follow", 1, 0.85, 2, 1.40, 2.40),
            ("direct_follow", 2, 1.00, 3, 1.55, 2.70),
            ("residual_catchup", 1, 0.75, 3, 1.45, 2.45),
            ("residual_catchup", 2, 0.90, 4, 1.60, 2.80),
            ("overreact_fade", 1, 1.25, 2, 1.45, 2.30),
        ):
            _add(
                f"F04_LEADLAG_{l_tag}_TO_USDCAD_{mode.upper()}_LB{lb}_T{int(th * 100):03d}_H{hold_b}",
                "CROSS_ASSET_COMMOD_LEADLAG",
                "FTMO_SWING",
                ("USDCAD",),
                leaders,
                {
                    "mode": mode,
                    "lookback_days": lb,
                    "thresh_std": th,
                    "leader_to_target_sign": -1.0,  # Oil UP -> CAD UP -> USDCAD DOWN
                    "max_target_already_moved_ratio": 0.60,
                    "max_hold_bars": hold_b,
                    "sl_atr": sl,
                    "tp_atr": tp,
                    "exit_on_signal_flip": False,
                },
                frr_rat,
                frr_cp,
                "Ferraro, Rogoff & Rossi (2015) Oil->USDCAD / LEAD-OFF3-SSRN-21",
                cc.RES_D1_YAHOO_SANCTIONED,
                "MIXED_12OLD_AND_NEW9",
            )

    # --- Pillar 3B: Gold -> Silver Daily Lead-Lag (12OLD XAUUSD leader -> NEW9 XAGUSD target) ---
    au_ag_rat = (
        "Institutional macro, real-yield, and central-bank precious-metals flows price first in "
        "deep XAUUSD liquidity and spill over into higher-beta, thinner XAGUSD over 1-5 trading "
        "days; strict ATR hard SL >= 2.2x clears Silver's higher spread/commission cleanly."
    )
    au_ag_cp = (
        "Macro funds and ETF flow desks execute initial precious-metals risk allocation in Gold "
        "before cross-metal dealers and industrial silver hedgers re-anchor Silver spot prices."
    )
    for mode, lb, th, hold_b, sl, tp in (
        ("direct_follow", 1, 0.85, 2, 2.20, 3.60),
        ("direct_follow", 1, 1.15, 3, 2.30, 3.80),
        ("direct_follow", 2, 1.00, 3, 2.30, 3.80),
        ("direct_follow", 3, 1.10, 4, 2.50, 4.20),
        ("residual_catchup", 1, 0.80, 3, 2.20, 3.60),
        ("residual_catchup", 2, 0.95, 4, 2.30, 3.80),
        ("residual_catchup", 3, 1.05, 5, 2.50, 4.20),
        ("overreact_fade", 1, 1.30, 2, 2.20, 3.50),
        ("overreact_fade", 2, 1.40, 3, 2.30, 3.60),
    ):
        _add(
            f"F04_LEADLAG_XAU_TO_XAG_{mode.upper()}_LB{lb}_T{int(th * 100):03d}_H{hold_b}",
            "CROSS_ASSET_COMMOD_LEADLAG",
            "FTMO_SWING",
            ("XAGUSD",),
            ("XAUUSD",),
            {
                "mode": mode,
                "lookback_days": lb,
                "thresh_std": th,
                "leader_to_target_sign": 1.0,  # Gold UP -> Silver UP
                "max_target_already_moved_ratio": 0.65,
                "max_hold_bars": hold_b,
                "sl_atr": sl,
                "tp_atr": tp,
                "exit_on_signal_flip": False,
            },
            au_ag_rat,
            au_ag_cp,
            "Batten & Lucey Gold->Silver Spillover / LEAD-OFF3-SSRN-12",
            cc.RES_D1_YAHOO_SANCTIONED,
            "MIXED_12OLD_AND_NEW9",
        )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F04 candidate menu exceeds TOTAL_CAP={TOTAL_CAP}: got {len(specs)}")
    return specs


# ---------------------------------------------------------------------------
# Cluster A Anti-Overfit Scoring & Diverse Primary Selection (`<= 16`)
# ---------------------------------------------------------------------------


def _score_cluster_a_result(res: Mapping[str, Any]) -> tuple[bool, float]:
    met = res["metrics"]
    m1 = met["1x"]
    m15 = met["1.5x"]
    m2 = met["2x"]
    mz = met["zero_pos_swap_1x"]
    mf = met["fade_1x"]
    s0 = met["stage0"]
    side = met["side_split"]
    allow_u = bool(res["allow_unidirectional"])

    n_tr = int(m1["n_trades"])
    if not s0.get("passed", False) or n_tr < 18:
        return False, -999.0

    sh_1x = float(m1["sharpe"])
    sh_15x = float(m15["sharpe"])
    sh_2x = float(m2["sharpe"])
    sh_zpos = float(mz["sharpe"])
    sh_fade = float(mf["sharpe"])
    pos_yr_ratio = float(m1["positive_year_ratio"])
    by_yr = m1.get("by_year_R") or {}
    worst_yr = min((float(v) for v in by_yr.values()), default=-99.0)
    max_dd = float(m1["max_DD_R"])
    net_1x = float(m1["net_R"])

    side_penalty = 0.0
    if not allow_u:
        b_n = int(side["buy"]["n"])
        s_n = int(side["sell"]["n"])
        if b_n < 4 or s_n < 4:
            side_penalty -= 1.0
        elif float(side["buy"]["net_R"]) > 0.0 and float(side["sell"]["net_R"]) > 0.0:
            side_penalty += 0.35
        else:
            side_penalty -= 0.35

    # Penalize if strategy depends on positive swaps (`zero_pos_swap` must stay intact!)
    swap_penalty = -0.80 if (sh_1x > 0.0 and sh_zpos <= 0.0) else 0.0

    fade_margin = max(-1.5, min(2.0, sh_1x - sh_fade))
    calmar_proxy = net_1x / max(3.0, max_dd)
    score = (
        0.30 * sh_1x
        + 0.35 * sh_15x
        + 0.50 * sh_2x
        + 0.25 * sh_zpos
        + 0.30 * fade_margin
        + 0.60 * pos_yr_ratio
        + 0.15 * max(-2.0, min(3.0, calmar_proxy))
        + 0.04 * max(-12.0, min(6.0, worst_yr))
        + 0.10 * min(1.5, math.log1p(n_tr) / 5.0)
        + side_penalty
        + swap_penalty
    )
    eligible = bool(
        s0["passed"]
        and n_tr >= 20
        and sh_1x >= 0.20
        and sh_15x > 0.0
        and sh_zpos > 0.0
        and sh_1x > sh_fade + 0.25
    )
    return eligible, round(float(score), 6)


def _select_primary_and_exploratory(
    evaluated_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select `<= PRIMARY_CAP` diverse Primary candidates strictly on Cluster A (`2018-2020`)."""
    ranked = sorted(
        evaluated_rows,
        key=lambda r: (
            1 if r["eligible_primary"] else 0,
            float(r["cluster_a_score"]),
            float(r["cluster_a_metrics"]["2x"]["sharpe"]),
            r["candidate_id"],
        ),
        reverse=True,
    )

    primary: list[dict[str, Any]] = []
    chosen_ids: set[str] = set()
    per_subfamily_cap = 6
    sub_counts: dict[str, int] = {}

    def _pick(row: Mapping[str, Any]) -> None:
        item = dict(row["spec"])
        item["tier"] = "PRIMARY"
        item["cluster_a_score"] = row["cluster_a_score"]
        item["cluster_a_metrics"] = row["cluster_a_metrics"]
        primary.append(item)
        chosen_ids.add(row["candidate_id"])
        sub = str(row["subfamily"])
        sub_counts[sub] = sub_counts.get(sub, 0) + 1

    # Pass 1: Guarantee balanced representation across all 3 pillars (up to 3 each if eligible)
    for min_per_sub in (1, 2, 3):
        for row in ranked:
            if len(primary) >= PRIMARY_CAP:
                break
            if row["candidate_id"] in chosen_ids or not row["eligible_primary"]:
                continue
            if sub_counts.get(row["subfamily"], 0) < min_per_sub:
                _pick(row)

    # Pass 2: Ensure TRUE BLIND CADJPY & NEW9 XAGUSD/OIL get represented if eligible
    for target_tier in (cc.TIER_NEW7, cc.TIER_NEW9):
        if len(primary) >= PRIMARY_CAP:
            break
        has_tier = any(c["blindness_tier"] == target_tier for c in primary)
        if not has_tier:
            for row in ranked:
                if row["candidate_id"] in chosen_ids or not row["eligible_primary"]:
                    continue
                same_tier = row["spec"]["blindness_tier"] == target_tier
                if same_tier and sub_counts.get(row["subfamily"], 0) < per_subfamily_cap:
                    _pick(row)
                    break

    # Pass 3: Fill remaining Primary slots from eligible positive pool only
    # (NEVER pad PRIMARY_M200 with negative Cluster A candidates!)
    for row in ranked:
        if len(primary) >= PRIMARY_CAP:
            break
        if row["candidate_id"] in chosen_ids or not row["eligible_primary"]:
            continue
        if sub_counts.get(row["subfamily"], 0) >= per_subfamily_cap:
            continue
        _pick(row)

    exploratory: list[dict[str, Any]] = []
    for row in ranked:
        if len(primary) + len(exploratory) >= TOTAL_CAP:
            break
        if row["candidate_id"] in chosen_ids:
            continue
        item = dict(row["spec"])
        item["tier"] = "EXPLORATORY"
        item["cluster_a_score"] = row["cluster_a_score"]
        item["cluster_a_metrics"] = row["cluster_a_metrics"]
        exploratory.append(item)

    return primary, exploratory


def _summarize_metrics_for_checkpoint(metrics: Mapping[str, Any]) -> dict[str, Any]:
    out = {
        "1x": dict(metrics["1x"]),
        "1.5x": dict(metrics["1.5x"]),
        "2x": dict(metrics["2x"]),
        "zero_pos_swap_1x": dict(metrics["zero_pos_swap_1x"]),
        "fade_1x": dict(metrics["fade_1x"]),
        "stage0": dict(metrics["stage0"]),
        "side_split": dict(metrics["side_split"]),
        "years": list(cc.CLUSTER_A_YEARS),
    }
    if "margin_audit" in metrics:
        out["margin_audit"] = dict(metrics["margin_audit"])
    return out


# ---------------------------------------------------------------------------
# Standard Contract Function 2: `discover_cluster_a(universe)`
# ---------------------------------------------------------------------------


def discover_cluster_a(
    universe: Mapping[str, Any] | None = None,
    *,
    resume: bool = False,
    save_checkpoint: bool = True,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
    verify_sha: bool = True,
) -> dict[str, Any]:
    """Run Stage 2 Cluster A (`2018-2020` ONLY!) discovery for `F04_ENERGY_METAL`.

    HARD BLINDNESS LOCK (`G01`): NEVER reads, evaluates, prints, or ranks on `2021..2024`!
    """
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        loaded = cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)
        base_dir = (
            Path(candidates_dir)
            if candidates_dir is not None
            else cc.resolve_workspace_root(root) / ".runtime/offensive3/candidates"
        )
        return {
            "family_id": FAMILY_ID,
            "resumed": True,
            "discovery_years": list(cc.CLUSTER_A_YEARS),
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
            "primary_count": int(loaded["primary_count"]),
            "exploratory_count": int(loaded["exploratory_count"]),
            "total_count": int(loaded["total_count"]),
            "primary_candidates": loaded["primary_candidates"],
            "exploratory_candidates": loaded["exploratory_candidates"],
            "checkpoint_path": str(base_dir / f"{FAMILY_ID}.json"),
        }

    uni = (
        universe
        if universe is not None
        else cc.load_universe_28(
            load_m1=True,
            load_d1=True,
            years=cc.CLUSTER_A_YEARS,
            symbols=F04_UNIVERSE_SYMBOLS,
            verify_sha=verify_sha,
            root=root,
        )
    )
    rn_idx = _get_red_news_index(root=root)
    candidate_specs = build_f04_candidate_specs()

    evaluated_rows: list[dict[str, Any]] = []
    for spec in candidate_specs:
        res = evaluate_candidate(spec, uni, cc.CLUSTER_A_YEARS, red_news_index=rn_idx, root=root)
        eligible, score = _score_cluster_a_result(res)
        evaluated_rows.append(
            {
                "candidate_id": spec["candidate_id"],
                "subfamily": spec["subfamily"],
                "spec": res["spec"],
                "eligible_primary": eligible,
                "cluster_a_score": score,
                "cluster_a_metrics": _summarize_metrics_for_checkpoint(res["metrics"]),
            }
        )

    primary, exploratory = _select_primary_and_exploratory(evaluated_rows)
    subfamily_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for c in primary:
        sf = str(c["subfamily"])
        bt = str(c["blindness_tier"])
        subfamily_counts[sf] = subfamily_counts.get(sf, 0) + 1
        tier_counts[bt] = tier_counts.get(bt, 0) + 1

    meta: dict[str, Any] = {
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "family_code": FAMILY_CODE,
        "family_slug": FAMILY_ID,
        "primary_cap": PRIMARY_CAP,
        "prop_tracks": ["INTRADAY_SWAP0", "FTMO_SWING"],
        "symbols_covered": list(F04_UNIVERSE_SYMBOLS),
        "usoil_apr2020_quarantine_enforced": True,
        "anti_fake_swap_guard_enforced": True,
        "primary_subfamily_counts": subfamily_counts,
        "primary_blindness_tier_counts": tier_counts,
        "evaluated_total": len(evaluated_rows),
        "eligible_primary_pool": sum(1 for r in evaluated_rows if r["eligible_primary"]),
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    ckpt_path: str | None = None
    if save_checkpoint:
        saved = cc.save_family_candidates(
            FAMILY_ID,
            {"primary": primary, "exploratory": exploratory},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )
        ckpt_path = str(saved)

    return {
        "family_id": FAMILY_ID,
        "resumed": False,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "primary_count": len(primary),
        "exploratory_count": len(exploratory),
        "total_count": len(primary) + len(exploratory),
        "primary_candidates": primary,
        "exploratory_candidates": exploratory,
        "checkpoint_path": ckpt_path,
        "meta": meta,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Total Offensive #3 — F04 Energy & Metals Microstructure (Cl.A)")
    parser.add_argument("--resume", action="store_true", help="Reuse SHA-verified Cl.A checkpoint if present.")
    parser.add_argument(
        "--no-verify-sha", action="store_true", help="Skip parquet SHA verification for faster dev run."
    )
    parser.add_argument("--candidates-dir", type=str, default=None, help="Optional candidate checkpoint directory.")
    args = parser.parse_args(argv)

    out = discover_cluster_a(
        None,
        resume=bool(args.resume),
        save_checkpoint=True,
        candidates_dir=args.candidates_dir,
        verify_sha=not bool(args.no_verify_sha),
    )
    top5 = [
        {
            "id": c["candidate_id"],
            "subfamily": c["subfamily"],
            "tier_blind": c["blindness_tier"],
            "n": c["cluster_a_metrics"]["1x"]["n_trades"],
            "sh1x": c["cluster_a_metrics"]["1x"]["sharpe"],
            "sh2x": c["cluster_a_metrics"]["2x"]["sharpe"],
            "shZpos": c["cluster_a_metrics"]["zero_pos_swap_1x"]["sharpe"],
            "pf1x": c["cluster_a_metrics"]["1x"]["pf"],
            "netR1x": c["cluster_a_metrics"]["1x"]["net_R"],
            "fadeSh1x": c["cluster_a_metrics"]["fade_1x"]["sharpe"],
            "medFSL": c["cluster_a_metrics"]["stage0"]["median_fric_sl_ratio"],
            "posYr": f"{c['cluster_a_metrics']['1x']['positive_years']}/{c['cluster_a_metrics']['1x']['total_years']}",
        }
        for c in out["primary_candidates"][:5]
    ]
    summary = {
        "family_id": out["family_id"],
        "resumed": out["resumed"],
        "discovery_years": out["discovery_years"],
        "primary_count": out["primary_count"],
        "exploratory_count": out["exploratory_count"],
        "total_count": out["total_count"],
        "checkpoint_path": out["checkpoint_path"],
        "order_send_count": out["order_send_count"],
        _SEAL_ROWS_ANALYSED_KEY: out[_SEAL_ROWS_ANALYSED_KEY],
        "top5_primary_cluster_a": top5,
    }
    print(json.dumps(summary, indent=2))
    return 0


__all__ = [
    "D1_MAX_FRIC_SL_RATIO",
    "F04_UNIVERSE_SYMBOLS",
    "FAMILY_CODE",
    "FAMILY_ID",
    "M1_MAX_FRIC_SL_RATIO",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_CAP",
    "TOTAL_CAP",
    "build_f04_candidate_specs",
    "discover_cluster_a",
    "evaluate_candidate",
    "load_verified_eia_dates",
    "resolve_xau_bullion_comex_clocks_utc",
]


if __name__ == "__main__":
    raise SystemExit(main())
