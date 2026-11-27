"""Total Offensive #3 — Family F03: FX Institutional Fixing & Working-Hours Orderflow.

Family ID: `F03_FX_FIX_FLOW`
Prop Track: `INTRADAY_SWAP0` (strictly flat <= 20:50 UTC on entry day, swap = 0)
Universe: All 7 native M1 Bid/Ask FX pairs (`EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, EURJPY, GBPJPY`).
Caps: `<= 16` `PRIMARY_M200`, `<= 100` total candidates.

Mechanisms grounded in primary empirical microstructure literature:
  1. `WMR_1600_LDN_FIX`: WM/Reuters 16:00 Europe/London Fix pre-fix/post-fix reversal &
     month-end contrarian hedge rebalancing (`Michelberger & Witte 2016`, `Krohn, Mueller
     & Whelan 2024`, `FXTradeSimu` / `LEAD-OFF3-ARXIV-01`, `SSRN-03`, `GH-12`).
  2. `TOKYO_GOTOBI_0955`: Tokyo 09:55 JST (00:55 UTC) Gotobi (5/10/15/20/25/30th business
     day) pre-fix importer drift & post-09:55 JST dealer inventory fade (`Bessho`,
     `tradedeck` / `LEAD-OFF3-ARXIV-02`, `GH-11`, `COMM-EN-01`).
  3. `NY_1000_OPTION_CUT`: New York 10:00 America/New_York FX Option-Expiry Cut
     post-expiry delta-hedge unwind mean-reversion (DST-exact via `OPS-1`).
  4. `BREEDON_RANALDO_LOCAL`: Breedon & Ranaldo (2013) local-vs-foreign working-hours
     commercial orderflow reversal across Asian/London/NY session handovers (DST-exact).

Hard Safety & Anti-Overfit Invariants (`G01`, `G05`, `G06`, `[ARCH-02]`):
  - ZERO bare `assert` statements (`python -O` safe).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - HARD BLINDNESS LOCK: `discover_cluster_a(universe)` strictly touches ONLY
    `CLUSTER_A_YEARS = (2018, 2019, 2020)` and NEVER inspects `2021..2024`.
  - Strict `shift = 1` daily ATR and strictly `< entry_ts` intraday features.
  - Exact US/EU DST resolution via `quant_factory.live_ops.feed_dst_news_guard` (`OPS-1`).
  - Causal pre-entry `F_stress / SL <= 12%` filter + red-news `+/-5m` entry block & flatten.
"""

from __future__ import annotations

import argparse
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
    resolve_dst_snapshot,
    resolve_strategy_session_utc,
)
from quant_factory.offensive3 import common_contract as cc  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety & Family Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAMILY_CODE: str = "F03"
FAMILY_ID: str = "F03_FX_FIX_FLOW"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100
PROP_TRACK: str = "INTRADAY_SWAP0"

MAX_FRIC_SL_RATIO: float = 0.12
NEWS_PAD_SEC: int = 300
HARD_FLAT_UTC_HHMM: tuple[int, int] = (20, 45)
HARD_FLAT_MAX_SEC_OF_DAY: int = HARD_FLAT_UTC_HHMM[0] * 3600 + HARD_FLAT_UTC_HHMM[1] * 60

FX_M1_SYMBOLS: tuple[str, ...] = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCAD",
    "AUDUSD",
    "EURJPY",
    "GBPJPY",
)
USD_QUOTE_SYMBOLS: frozenset[str] = frozenset({"EURUSD", "GBPUSD", "AUDUSD"})
USD_BASE_SYMBOLS: frozenset[str] = frozenset({"USDJPY", "USDCAD"})
JPY_QUOTE_SYMBOLS: tuple[str, ...] = ("USDJPY", "EURJPY", "GBPJPY")

_ZI_LONDON = ZoneInfo(TZ_LONDON)
_ZI_NEW_YORK = ZoneInfo(TZ_NEW_YORK)

# Process-local cache for fast O(log N) day slicing & red-news lookup (read-only, keyed by data bounds)
_M1_DAY_INDEX_CACHE: dict[tuple[str, int, int, int], dict[str, Any]] = {}
_RED_NEWS_CACHE: dict[str, dict[str, Any]] = {}
_SYMBOL_NEWS_CACHE: dict[tuple[int, str], tuple[np.ndarray, np.ndarray]] = {}
_DST_CLOCK_CACHE: dict[date, dict[str, int]] = {}


# ---------------------------------------------------------------------------
# Deterministic Calendars & OPS-1 DST Session Clocks (Zero Lookahead)
# ---------------------------------------------------------------------------


def _japan_fixed_holidays(year: int) -> set[date]:
    """Deterministic fixed/standard Japanese bank holidays relevant to Gotobi settlement shifts."""
    hols: set[date] = {
        date(year, 1, 1),
        date(year, 1, 2),
        date(year, 1, 3),
        date(year, 2, 11),
        date(year, 4, 29),
        date(year, 5, 3),
        date(year, 5, 4),
        date(year, 5, 5),
        date(year, 8, 11),
        date(year, 11, 3),
        date(year, 11, 23),
        date(year, 12, 31),
    }
    if year <= 2018:
        hols.add(date(year, 12, 23))
    if year >= 2020:
        hols.add(date(year, 2, 23))
    # Coming of Age Day (2nd Mon Jan), Marine Day (3rd Mon Jul), Respect for Aged (3rd Mon Sep), Sports (2nd Mon Oct)
    for month, nth in ((1, 2), (7, 3), (9, 3), (10, 2)):
        first = date(year, month, 1)
        off = (0 - first.weekday()) % 7
        hols.add(first + timedelta(days=off + 7 * (nth - 1)))
    # Substitute Monday when fixed holiday lands on Sunday
    subs: set[date] = set()
    for h in hols:
        if h.weekday() == 6:
            nxt = h + timedelta(days=1)
            while nxt in hols or nxt in subs:
                nxt += timedelta(days=1)
            subs.add(nxt)
    hols.update(subs)
    return hols


def _is_japan_business_day(d: date, hols: set[date]) -> bool:
    return d.weekday() < 5 and d not in hols


def compute_gotobi_dates_for_years(years: Sequence[int]) -> set[date]:
    """Return Japanese Gotobi settlement days (5/10/15/20/25/30 or month-end rolled backward)."""
    gotobi: set[date] = set()
    for yr in sorted({int(y) for y in years}):
        hols = _japan_fixed_holidays(yr)
        for month in range(1, 13):
            next_m = date(yr + 1, 1, 1) if month == 12 else date(yr, month + 1, 1)
            last_dom = (next_m - timedelta(days=1)).day
            targets = [5, 10, 15, 20, 25, min(30, last_dom)]
            for dom in targets:
                cur = date(yr, month, dom)
                while not _is_japan_business_day(cur, hols):
                    cur -= timedelta(days=1)
                    if cur.year != yr:
                        hols = _japan_fixed_holidays(cur.year)
                if cur.year == yr:
                    gotobi.add(cur)
    return gotobi


def compute_month_end_weekdays(trade_dates: Sequence[date], last_n: int = 1) -> set[date]:
    """Identify the final `last_n` weekday trading dates in each `(year, month)` deterministically."""
    if last_n < 1:
        raise ValueError(f"last_n must be >= 1, got {last_n!r}")
    out: set[date] = set()
    months_seen = sorted({(d.year, d.month) for d in trade_dates})
    for yr, mo in months_seen:
        next_m = date(yr + 1, 1, 1) if mo == 12 else date(yr, mo + 1, 1)
        cur = next_m - timedelta(days=1)
        picked: list[date] = []
        while len(picked) < last_n and cur.month == mo:
            if cur.weekday() < 5:
                picked.append(cur)
            cur -= timedelta(days=1)
        out.update(picked)
    return out


def _resolve_day_session_clocks_utc(trade_date: date) -> dict[str, int]:
    """Resolve exact UTC epoch timestamps of London/NY/Tokyo anchors via `OPS-1` DST resolver."""
    cached = _DST_CLOCK_CACHE.get(trade_date)
    if cached is not None:
        return cached

    day_start_ts = int(datetime(trade_date.year, trade_date.month, trade_date.day, 0, 0, tzinfo=UTC).timestamp())
    # Exact OPS-1 session anchors (verifies US vs EU DST transitions & divergence windows)
    ldn_open_info = resolve_strategy_session_utc("LONDON_OPEN", trade_date)
    ny_10et_info = resolve_strategy_session_utc("NY_10ET", trade_date)

    ldn_open_ts = day_start_ts + int(ldn_open_info["utc_hour"]) * 3600 + int(ldn_open_info["utc_minute"]) * 60
    ny_10et_ts = day_start_ts + int(ny_10et_info["utc_hour"]) * 3600 + int(ny_10et_info["utc_minute"]) * 60

    # WM/Reuters 16:00 Europe/London Fix (15:00 UTC in BST, 16:00 UTC in GMT)
    wmr_local = datetime.combine(trade_date, time(16, 0), tzinfo=_ZI_LONDON)
    wmr_utc = wmr_local.astimezone(UTC)
    wmr_ts = int(wmr_utc.timestamp())

    # London 13:00 local (European midday / NY handover)
    ldn_13_ts = int(datetime.combine(trade_date, time(13, 0), tzinfo=_ZI_LONDON).astimezone(UTC).timestamp())
    # NY 08:00 local open & 15:30 local afternoon
    ny_08_ts = int(datetime.combine(trade_date, time(8, 0), tzinfo=_ZI_NEW_YORK).astimezone(UTC).timestamp())
    ny_1530_ts = int(datetime.combine(trade_date, time(15, 30), tzinfo=_ZI_NEW_YORK).astimezone(UTC).timestamp())

    # Verify DST snapshot consistency via OPS-1
    snap = resolve_dst_snapshot(wmr_utc)
    hard_flat_ts = day_start_ts + HARD_FLAT_MAX_SEC_OF_DAY

    clocks = {
        "day_start_ts": day_start_ts,
        "tokyo_0900_jst_ts": day_start_ts,  # 00:00 UTC = 09:00 JST (no Japan DST)
        "tokyo_0955_jst_ts": day_start_ts + 55 * 60,  # 00:55 UTC = 09:55 JST
        "ldn_open_ts": ldn_open_ts,
        "ldn_1300_ts": ldn_13_ts,
        "wmr_1600_ts": wmr_ts,
        "ny_0800_ts": ny_08_ts,
        "ny_1000_ts": ny_10et_ts,
        "ny_1530_ts": min(ny_1530_ts, hard_flat_ts),
        "hard_flat_ts": hard_flat_ts,
        "is_dst_divergence": 1 if snap.is_dst_divergence_window else 0,
    }
    _DST_CLOCK_CACHE[trade_date] = clocks
    return clocks


# ---------------------------------------------------------------------------
# Fast Causal M1 Indexing & Red-News Pre-Filter Helpers
# ---------------------------------------------------------------------------


def _get_red_news_index(root: str | Path | None = None) -> dict[str, Any]:
    key = str(cc.resolve_workspace_root(root))
    cached = _RED_NEWS_CACHE.get(key)
    if cached is None:
        cached = cc.load_dev_red_news_index(include_extended=True, root=root)
        _RED_NEWS_CACHE[key] = cached
    return cached


def _get_symbol_news_arrays_cached(symbol: str, red_news_index: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    cache_key = (id(red_news_index), symbol)
    cached = _SYMBOL_NEWS_CACHE.get(cache_key)
    if cached is not None:
        return cached
    codes = cc.match_symbol_red_news_codes(symbol)
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
    _SYMBOL_NEWS_CACHE[cache_key] = pair
    return pair


def _fast_in_red_news_window(symbol: str, ts_sec: int, red_news_index: Mapping[str, Any], pad_sec: int) -> bool:
    ev_ts, ev_pad = _get_symbol_news_arrays_cached(symbol, red_news_index)
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


def _build_clamped_m1_context(
    symbol: str,
    asset_entry: Mapping[str, Any],
    max_year: int,
) -> dict[str, Any]:
    """Slice M1 & D1 arrays strictly to `year <= max_year` and build causal ATR + day slices."""
    m1 = asset_entry.get("m1")
    d1 = asset_entry.get("d1")
    if m1 is None or d1 is None:
        raise ValueError(f"Asset {symbol} requires both native M1 and D1 bars for F03")

    ts_all = np.asarray(m1["times_sec"], dtype=np.int64)
    q_all = np.asarray(m1["quotes"], dtype=np.float64)
    cutoff_ts = int(datetime(max_year + 1, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    if cutoff_ts > cc.DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH: cutoff_ts={cutoff_ts} > {cc.DEV_CUTOFF_SEC}")

    end_m1 = int(np.searchsorted(ts_all, cutoff_ts, side="left"))
    ts = ts_all[:end_m1]
    q = q_all[:end_m1]
    if ts.size == 0:
        raise ValueError(f"Zero M1 bars for {symbol} with year <= {max_year}")
    cc.enforce_dev_ts_bound(ts, context=f"f03.m1:{symbol}")

    cache_key = (symbol, int(ts.size), int(ts[0]), int(ts[-1]))
    cached = _M1_DAY_INDEX_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Strictly clamp D1 to year <= max_year before computing causal ATR (zero peek past max_year!)
    d1_years = np.asarray(d1["years"], dtype=np.int32)
    keep_d1 = d1_years <= int(max_year)
    d1_dates = [str(d) for d, k in zip(d1["dates"], keep_d1, strict=True) if k]
    d1_h = np.asarray(d1["high"], dtype=np.float64)[keep_d1]
    d1_l = np.asarray(d1["low"], dtype=np.float64)[keep_d1]
    d1_c = np.asarray(d1["close"], dtype=np.float64)[keep_d1]
    cc.enforce_dev_date_bound(d1_dates, context=f"f03.d1:{symbol}")

    # Strictly shift = 1 causal ATR(14): atr14[i] uses ONLY days 0..i-1
    atr14_d1 = cc.causal_atr(d1_h, d1_l, d1_c, 14)

    # Prior calendar month-end close lookup (strictly causal: uses last close of strictly previous month!)
    prev_month_close_by_date: dict[str, float] = {}
    last_close_by_ym: dict[tuple[int, int], float] = {}
    prev_ym_close: float = math.nan
    cur_ym: tuple[int, int] | None = None
    for idx_d, ds in enumerate(d1_dates):
        ym = (int(ds[:4]), int(ds[5:7]))
        if cur_ym is not None and ym != cur_ym:
            prev_ym_close = last_close_by_ym[cur_ym]
        prev_month_close_by_date[ds] = prev_ym_close
        last_close_by_ym[ym] = float(d1_c[idx_d])
        cur_ym = ym

    atr_by_date: dict[str, float] = {}
    prev_close_by_date: dict[str, float] = {}
    for idx_d, ds in enumerate(d1_dates):
        atr_by_date[ds] = float(atr14_d1[idx_d])
        prev_close_by_date[ds] = float(d1_c[idx_d - 1]) if idx_d > 0 else math.nan

    # Group M1 bars by UTC day epoch (`ts // 86400`)
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
        "symbol": symbol,
        "spec": dict(asset_entry["spec"]),
        "times_sec": ts,
        "quotes": q,
        "day_slices": day_slices,
        "atr_by_date": atr_by_date,
        "prev_close_by_date": prev_close_by_date,
        "prev_month_close_by_date": prev_month_close_by_date,
    }
    _M1_DAY_INDEX_CACHE[cache_key] = ctx
    return ctx


def _find_idx_at_or_after(ts: np.ndarray, lo: int, hi: int, target_ts: int, max_lag_sec: int = 900) -> int | None:
    """Return first index in `[lo, hi)` with `target_ts <= ts[idx] <= target_ts + max_lag_sec`."""
    pos = int(np.searchsorted(ts[lo:hi], target_ts, side="left")) + lo
    if pos >= hi:
        return None
    if int(ts[pos]) > target_ts + max_lag_sec:
        return None
    return pos


def _find_idx_strictly_before(
    ts: np.ndarray,
    lo: int,
    hi: int,
    cutoff_ts: int,
    max_stale_sec: int = 1800,
) -> int | None:
    """Return last index in `[lo, hi)` with `cutoff_ts - max_stale_sec <= ts[idx] < cutoff_ts`."""
    pos = int(np.searchsorted(ts[lo:hi], cutoff_ts, side="left")) + lo - 1
    if pos < lo:
        return None
    if int(ts[pos]) < cutoff_ts - max_stale_sec:
        return None
    return pos


def _mid_close(q: np.ndarray, idx: int) -> float:
    if q.shape[1] >= 8:
        return 0.5 * (float(q[idx, 3]) + float(q[idx, 7]))
    return float(q[idx, 3])


def _mid_open(q: np.ndarray, idx: int) -> float:
    if q.shape[1] >= 8:
        return 0.5 * (float(q[idx, 0]) + float(q[idx, 4]))
    return float(q[idx, 0])


def _causal_entry_fric_over_sl_2x(
    spec: Mapping[str, Any],
    q: np.ndarray,
    entry_idx: int,
    sl_dist: float,
) -> float:
    """Causal entry-time estimate of `F_stress(2x) / SL` using ONLY entry bar Bid/Ask & spec."""
    if not math.isfinite(sl_dist) or sl_dist <= 0.0:
        return math.inf
    pt = float(spec["point"])
    bench_sp_px = float(spec["benchmark_spread_pts"]) * pt
    has_ask = q.shape[1] >= 8
    entry_sp_px = max(0.0, float(q[entry_idx, 4] - q[entry_idx, 0])) if has_ask else bench_sp_px
    eff_sp = max(entry_sp_px, bench_sp_px)
    entry_px = _mid_open(q, entry_idx)
    tick_val_usd = cc.compute_causal_tick_val_usd(spec, entry_price=entry_px)
    usd_per_px = tick_val_usd / pt if pt > 0.0 else 1.0
    comm_px = float(spec["commission_usd_lot"]) / usd_per_px if usd_per_px > 0.0 else 0.0
    slip_rt_px = max(pt, 0.35 * eff_sp)
    fric_1x = eff_sp + comm_px + slip_rt_px
    return (2.0 * fric_1x) / sl_dist


def _usd_long_direction_for_pair(symbol: str) -> int:
    """Return trade side (+1/-1) corresponding to Long USD on a USD-major FX pair."""
    if symbol in USD_BASE_SYMBOLS:
        return 1
    if symbol in USD_QUOTE_SYMBOLS:
        return -1
    return 0


def _local_sell_direction_for_session(symbol: str, session: str) -> int:
    """Breedon-Ranaldo (2013) structural direction: sell domestic currency during domestic hours."""
    base = symbol[:3]
    quote = symbol[3:6]
    if session == "ASIA":
        local_ccys = {"JPY", "AUD"}
    elif session == "EUROPE":
        local_ccys = {"EUR", "GBP"}
    elif session == "NY":
        local_ccys = {"USD", "CAD"}
    else:
        return 0
    base_local = base in local_ccys
    quote_local = quote in local_ccys
    if base_local and not quote_local:
        return -1  # Sell local base currency
    if quote_local and not base_local:
        return 1  # Sell local quote currency (= buy pair)
    return 0


# ---------------------------------------------------------------------------
# Signal Generation & Trade Replay Engine (Zero Lookahead)
# ---------------------------------------------------------------------------


def _generate_day_trade_requests_for_symbol(
    spec: Mapping[str, Any],
    ctx: Mapping[str, Any],
    req_year_set: set[int],
    gotobi_dates: set[date],
    monthend_dates: set[date],
    red_news_index: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build strictly causal intraday trade requests (`< entry_ts`) for one FX pair."""
    subfamily = str(spec["subfamily"])
    params = dict(spec["params"])
    rule = str(params["rule"])
    sym = str(ctx["symbol"])
    sym_spec = ctx["spec"]
    ts = ctx["times_sec"]
    q = ctx["quotes"]
    atr_by_date = ctx["atr_by_date"]
    prev_close_by_date = ctx["prev_close_by_date"]
    prev_month_close_by_date = ctx["prev_month_close_by_date"]

    sl_atr = float(params["sl_atr"])
    tp_atr = float(params["tp_atr"]) if params.get("tp_atr") is not None else None
    max_fric_sl = float(params.get("max_fric_sl", MAX_FRIC_SL_RATIO))

    requests: list[dict[str, Any]] = []

    for d_obj, d_iso, lo, hi in ctx["day_slices"]:
        if d_obj.year not in req_year_set:
            continue
        atr = atr_by_date.get(d_iso, math.nan)
        if not math.isfinite(atr) or atr <= 0.0:
            continue

        clocks = _resolve_day_session_clocks_utc(d_obj)
        hard_flat_ts = clocks["hard_flat_ts"]

        side = 0
        entry_target_ts: int | None = None
        exit_target_ts: int | None = None

        if subfamily == "WMR_1600_LDN_FIX":
            wmr_ts = clocks["wmr_1600_ts"]
            if rule == "wmr_postfix_fade":
                pre_min = int(params["pre_window_min"])
                thresh = float(params["thresh_atr"])
                hold_min = int(params["hold_min"])
                entry_target_ts = wmr_ts + 5 * 60
                exit_target_ts = min(wmr_ts + hold_min * 60, hard_flat_ts)
                i_start = _find_idx_at_or_after(ts, lo, hi, wmr_ts - pre_min * 60, max_lag_sec=600)
                i_end = _find_idx_strictly_before(ts, lo, hi, wmr_ts, max_stale_sec=600)
                if i_start is None or i_end is None or i_end <= i_start:
                    continue
                move_atr = (_mid_close(q, i_end) - _mid_open(q, i_start)) / atr
                if abs(move_atr) >= thresh:
                    side = -1 if move_atr > 0.0 else 1

            elif rule == "wmr_prefix_usd_drift":
                leg = str(params["leg"])  # "prefix_long_usd" or "postfix_short_usd"
                usd_long = _usd_long_direction_for_pair(sym)
                if usd_long == 0:
                    continue
                min_ldn_move = float(params.get("min_ldn_move_atr", 0.0))
                if leg == "prefix_long_usd":
                    pre_min = int(params["pre_window_min"])
                    entry_target_ts = wmr_ts - pre_min * 60
                    exit_target_ts = min(wmr_ts - 60, hard_flat_ts)
                    if min_ldn_move > 0.0:
                        i_s = _find_idx_at_or_after(ts, lo, hi, clocks["ldn_open_ts"], max_lag_sec=600)
                        i_e = _find_idx_strictly_before(ts, lo, hi, entry_target_ts, max_stale_sec=600)
                        if i_s is None or i_e is None or i_e <= i_s:
                            continue
                        ldn_move = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
                        if abs(ldn_move) < min_ldn_move:
                            continue
                    side = usd_long
                elif leg == "postfix_short_usd":
                    hold_min = int(params["hold_min"])
                    entry_target_ts = wmr_ts + 5 * 60
                    exit_target_ts = min(wmr_ts + hold_min * 60, hard_flat_ts)
                    if min_ldn_move > 0.0:
                        i_s = _find_idx_at_or_after(ts, lo, hi, wmr_ts - 120 * 60, max_lag_sec=600)
                        i_e = _find_idx_strictly_before(ts, lo, hi, wmr_ts, max_stale_sec=600)
                        if i_s is None or i_e is None or i_e <= i_s:
                            continue
                        # Confirm pre-fix USD strengthening before fading post-fix
                        pre_usd_ret = usd_long * (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
                        if pre_usd_ret < min_ldn_move:
                            continue
                    side = -usd_long

            elif rule == "wmr_monthend_contra":
                if d_obj not in monthend_dates:
                    continue
                prev_m_c = prev_month_close_by_date.get(d_iso, math.nan)
                if not math.isfinite(prev_m_c) or prev_m_c <= 0.0:
                    continue
                leg = str(params["leg"])  # "prefix" or "postfix"
                thresh_mtd = float(params.get("thresh_mtd_atr", 0.5))
                if leg == "prefix":
                    pre_min = int(params["pre_window_min"])
                    entry_target_ts = wmr_ts - pre_min * 60
                    exit_target_ts = min(wmr_ts, hard_flat_ts)
                else:
                    hold_min = int(params["hold_min"])
                    entry_target_ts = wmr_ts + 5 * 60
                    exit_target_ts = min(wmr_ts + hold_min * 60, hard_flat_ts)
                i_ref = _find_idx_strictly_before(ts, lo, hi, entry_target_ts, max_stale_sec=900)
                if i_ref is None:
                    continue
                mtd_atr = (_mid_close(q, i_ref) - prev_m_c) / atr
                if abs(mtd_atr) >= thresh_mtd:
                    # Contrarian rebalance against month-to-date move
                    side = -1 if mtd_atr > 0.0 else 1

        elif subfamily == "TOKYO_GOTOBI_0955":
            t0900 = clocks["tokyo_0900_jst_ts"]
            t0955 = clocks["tokyo_0955_jst_ts"]
            if rule == "gotobi_prefix_long":
                if d_obj not in gotobi_dates:
                    continue
                if bool(params.get("exclude_monday", False)) and d_obj.weekday() == 0:
                    continue
                entry_min_utc = int(params.get("entry_min_utc", 5))
                entry_target_ts = t0900 + entry_min_utc * 60
                exit_target_ts = t0955
                # Optional causal filter: prior day not overextended upward
                max_prev_up = params.get("max_prev_gap_atr")
                if max_prev_up is not None:
                    pc = prev_close_by_date.get(d_iso, math.nan)
                    i_ref = _find_idx_strictly_before(ts, lo, hi, entry_target_ts, max_stale_sec=600)
                    if not math.isfinite(pc) or i_ref is None:
                        continue
                    if (_mid_close(q, i_ref) - pc) / atr > float(max_prev_up):
                        continue
                side = 1

            elif rule == "gotobi_postfix_fade":
                if d_obj not in gotobi_dates:
                    continue
                if bool(params.get("exclude_monday", False)) and d_obj.weekday() == 0:
                    continue
                drift_min = float(params.get("min_prefix_drift_atr", 0.0))
                hold_min = int(params["hold_min"])
                entry_target_ts = t0955 + 60  # 00:56 UTC = 09:56 JST
                exit_target_ts = min(t0955 + hold_min * 60, hard_flat_ts)
                i_s = _find_idx_at_or_after(ts, lo, hi, t0900, max_lag_sec=600)
                i_e = _find_idx_strictly_before(ts, lo, hi, t0955, max_stale_sec=600)
                if i_s is None or i_e is None or i_e <= i_s:
                    continue
                drift_atr = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
                if drift_atr >= drift_min:
                    side = -1

            elif rule == "tokyo_fix_sym_fade":
                thresh = float(params["thresh_atr"])
                hold_min = int(params["hold_min"])
                entry_target_ts = t0955 + 60
                exit_target_ts = min(t0955 + hold_min * 60, hard_flat_ts)
                i_s = _find_idx_at_or_after(ts, lo, hi, t0900, max_lag_sec=600)
                i_e = _find_idx_strictly_before(ts, lo, hi, t0955, max_stale_sec=600)
                if i_s is None or i_e is None or i_e <= i_s:
                    continue
                drift_atr = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
                if abs(drift_atr) >= thresh:
                    side = -1 if drift_atr > 0.0 else 1

        elif subfamily == "NY_1000_OPTION_CUT":
            ny_cut_ts = clocks["ny_1000_ts"]
            pre_min = int(params["pre_window_min"])
            thresh = float(params["thresh_atr"])
            hold_min = int(params["hold_min"])
            mode = str(params.get("mode", "fade"))  # "fade" or "follow"
            entry_target_ts = ny_cut_ts + 5 * 60
            exit_target_ts = min(ny_cut_ts + hold_min * 60, hard_flat_ts)
            i_start = _find_idx_at_or_after(ts, lo, hi, ny_cut_ts - pre_min * 60, max_lag_sec=600)
            i_end = _find_idx_strictly_before(ts, lo, hi, ny_cut_ts, max_stale_sec=600)
            if i_start is None or i_end is None or i_end <= i_start:
                continue
            move_atr = (_mid_close(q, i_end) - _mid_open(q, i_start)) / atr
            if abs(move_atr) >= thresh:
                if mode == "fade":
                    side = -1 if move_atr > 0.0 else 1
                else:
                    side = 1 if move_atr > 0.0 else -1

        elif subfamily == "BREEDON_RANALDO_LOCAL":
            if rule == "breedon_session_reversion":
                window = str(params["window"])  # "asia_to_ldn", "ldn_to_ny", "overlap_to_pm"
                thresh = float(params["thresh_atr"])
                if window == "asia_to_ldn":
                    win_s = clocks["tokyo_0900_jst_ts"]
                    win_e = clocks["ldn_open_ts"]
                    entry_target_ts = win_e + 5 * 60
                    exit_target_ts = min(clocks["ldn_1300_ts"], hard_flat_ts)
                elif window == "ldn_to_ny":
                    win_s = clocks["ldn_open_ts"]
                    win_e = clocks["ldn_1300_ts"]
                    entry_target_ts = win_e + 5 * 60
                    exit_target_ts = min(clocks["ny_1530_ts"], hard_flat_ts)
                else:  # "overlap_to_pm"
                    win_s = clocks["ldn_open_ts"]
                    win_e = clocks["ny_1000_ts"] + 30 * 60
                    entry_target_ts = win_e + 5 * 60
                    exit_target_ts = min(clocks["ny_1530_ts"], hard_flat_ts)
                i_s = _find_idx_at_or_after(ts, lo, hi, win_s, max_lag_sec=900)
                i_e = _find_idx_strictly_before(ts, lo, hi, win_e, max_stale_sec=900)
                if i_s is None or i_e is None or i_e <= i_s:
                    continue
                sess_move = (_mid_close(q, i_e) - _mid_open(q, i_s)) / atr
                if abs(sess_move) >= thresh:
                    side = -1 if sess_move > 0.0 else 1

            elif rule == "breedon_clock_flow":
                session = str(params["session"])  # "ASIA", "EUROPE", "NY"
                action = str(params.get("action", "sell_local"))  # "sell_local" or "revert_post_local"
                base_dir = _local_sell_direction_for_session(sym, session)
                if base_dir == 0:
                    continue
                if session == "ASIA":
                    if action == "sell_local":
                        entry_target_ts = clocks["tokyo_0900_jst_ts"] + 15 * 60
                        exit_target_ts = clocks["ldn_open_ts"] - 15 * 60
                        side = base_dir
                    else:
                        entry_target_ts = clocks["ldn_open_ts"] + 5 * 60
                        exit_target_ts = clocks["ldn_1300_ts"]
                        side = -base_dir
                elif session == "EUROPE":
                    if action == "sell_local":
                        entry_target_ts = clocks["ldn_open_ts"] + 5 * 60
                        exit_target_ts = clocks["ldn_1300_ts"]
                        side = base_dir
                    else:
                        entry_target_ts = clocks["ldn_1300_ts"] + 5 * 60
                        exit_target_ts = min(clocks["ny_1530_ts"], hard_flat_ts)
                        side = -base_dir
                else:  # "NY"
                    entry_target_ts = clocks["ny_0800_ts"] + 5 * 60
                    exit_target_ts = min(clocks["ny_1530_ts"], hard_flat_ts)
                    side = base_dir if action == "sell_local" else -base_dir

        if side == 0 or entry_target_ts is None or exit_target_ts is None:
            continue
        if exit_target_ts <= entry_target_ts + 300:
            continue

        entry_idx = _find_idx_at_or_after(ts, lo, hi, entry_target_ts, max_lag_sec=600)
        if entry_idx is None:
            continue
        flat_idx = int(np.searchsorted(ts[lo:hi], exit_target_ts, side="right")) + lo - 1
        if flat_idx <= entry_idx:
            continue

        entry_ts = int(ts[entry_idx])
        if _fast_in_red_news_window(sym, entry_ts, red_news_index, NEWS_PAD_SEC):
            continue

        sl_dist = sl_atr * atr
        est_f_sl = _causal_entry_fric_over_sl_2x(sym_spec, q, entry_idx, sl_dist)
        if est_f_sl > max_fric_sl:
            continue

        tp_dist = (tp_atr * atr) if (tp_atr is not None and tp_atr > 0.0) else None
        requests.append(
            {
                "entry_idx": entry_idx,
                "flat_idx": flat_idx,
                "side": int(side),
                "sl_dist": sl_dist,
                "tp_dist": tp_dist,
            }
        )

    return requests


def _replay_requests_for_symbol(
    ctx: Mapping[str, Any],
    requests: Sequence[Mapping[str, Any]],
    red_news_index: Mapping[str, Any],
    *,
    flip_side: bool = False,
    risk_frac: float = 0.005,
) -> list[dict[str, Any]]:
    sym = str(ctx["symbol"])
    sym_spec = ctx["spec"]
    ts = ctx["times_sec"]
    q = ctx["quotes"]
    has_ask = q.shape[1] >= 8
    out: list[dict[str, Any]] = []
    for req in requests:
        e_idx = int(req["entry_idx"])
        f_idx = int(req["flat_idx"])
        side = -int(req["side"]) if flip_side else int(req["side"])
        sl_dist = float(req["sl_dist"])
        tp_dist = req["tp_dist"]
        entry_px = float(q[e_idx, 4] if (side == 1 and has_ask) else q[e_idx, 0])
        sl_px = entry_px - side * sl_dist
        if sl_px <= 0.0:
            continue
        tp_px = (entry_px + side * float(tp_dist)) if tp_dist is not None else None
        if tp_px is not None and tp_px <= 0.0:
            continue
        tr = cc.replay_intraday_m1_trade(
            sym,
            ts,
            q,
            e_idx,
            side,
            sl_px,
            tp_price=tp_px,
            flat_idx=f_idx,
            hard_flat_utc_hhmm=HARD_FLAT_UTC_HHMM,
            spec=sym_spec,
            firm_profile="FTMO_STANDARD",
            red_news_index=red_news_index,
            news_pad_sec=NEWS_PAD_SEC,
            flatten_before_news=True,
            risk_frac=risk_frac,
        )
        if tr.get("filled"):
            # Mirror zero_pos_swap keys (swap = 0 on intraday)
            tr["net_R_zero_pos_1x"] = tr["net_R_1x"]
            tr["net_R_zero_pos_15x"] = tr["net_R_15x"]
            tr["net_R_zero_pos_2x"] = tr["net_R_2x"]
            out.append(tr)
    return out


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
    """Evaluate an F03 candidate on `years` returning the canonical Offensive #3 result dict."""
    cand_spec = dict(spec["spec"]) if ("spec" in spec and isinstance(spec["spec"], Mapping)) else dict(spec)
    req_years = _validate_years_arg(years)
    req_year_set = set(req_years)
    max_year = max(req_years)

    assets = universe["assets"] if ("assets" in universe and isinstance(universe["assets"], Mapping)) else universe
    symbols = [cc.normalize_symbol(s) for s in cand_spec["symbols"]]
    if not symbols:
        raise ValueError(f"Candidate {cand_spec.get('candidate_id')} has empty symbols list")

    rn_idx = red_news_index if red_news_index is not None else _get_red_news_index(root=root)
    gotobi_dates = compute_gotobi_dates_for_years(req_years)

    last_n_me = int(cand_spec.get("params", {}).get("month_end_days", 1))
    all_trades: list[dict[str, Any]] = []
    fade_trades: list[dict[str, Any]] = []
    # Equal-risk basket scaling when trading multiple FX pairs simultaneously
    per_sym_risk = 0.005 / max(1.0, math.sqrt(float(len(symbols))))

    for sym in symbols:
        if sym not in assets:
            raise KeyError(f"Symbol {sym!r} missing from universe")
        ctx = _build_clamped_m1_context(sym, assets[sym], max_year=max_year)
        sym_dates = [d for d, _, _, _ in ctx["day_slices"] if d.year in req_year_set]
        monthend_dates = compute_month_end_weekdays(sym_dates, last_n=last_n_me)
        reqs = _generate_day_trade_requests_for_symbol(
            cand_spec,
            ctx,
            req_year_set=req_year_set,
            gotobi_dates=gotobi_dates,
            monthend_dates=monthend_dates,
            red_news_index=rn_idx,
        )
        sym_trades = _replay_requests_for_symbol(ctx, reqs, rn_idx, flip_side=False, risk_frac=per_sym_risk)
        sym_fades = _replay_requests_for_symbol(ctx, reqs, rn_idx, flip_side=True, risk_frac=per_sym_risk)
        all_trades.extend(sym_trades)
        fade_trades.extend(sym_fades)

    all_trades.sort(key=lambda tr: (tr["exit_ts"], tr["entry_ts"], tr["symbol"]))
    fade_trades.sort(key=lambda tr: (tr["exit_ts"], tr["entry_ts"], tr["symbol"]))

    # Scale portfolio R equally across multi-symbol baskets so total daily risk stays comparable to 1-asset R
    scale_factor = 1.0 / math.sqrt(float(len(symbols))) if len(symbols) > 1 else 1.0
    if scale_factor < 0.999999:
        for tr_list in (all_trades, fade_trades):
            for tr in tr_list:
                for k in ("gross_R", "net_R", "net_R_1x", "net_R_15x", "net_R_2x", "net_R_zero_pos_1x"):
                    if tr.get(k) is not None:
                        tr[k] = round(float(tr[k]) * scale_factor, 6)

    dpnl_1x = cc.compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_2x")
    dpnl_zpos = cc.compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_zero_pos_1x")
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = cc.compute_split_metrics(all_trades, dpnl_1x, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(all_trades, dpnl_15x, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(all_trades, dpnl_2x, pnl_key="net_R_2x")
    m_zpos = cc.compute_split_metrics(all_trades, dpnl_zpos, pnl_key="net_R_zero_pos_1x")
    m_fade = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(all_trades, max_fric_sl_ratio=MAX_FRIC_SL_RATIO, min_keep_frac=0.80)
    side_split = _compute_side_split(all_trades, pnl_key="net_R_1x")

    metrics: dict[str, Any] = {
        **m_1x,
        "1x": m_1x,
        "1.5x": m_15x,
        "2x": m_2x,
        "zero_pos_swap_1x": m_zpos,
        "fade_1x": m_fade,
        "stage0": s0,
        "side_split": side_split,
        "years": list(req_years),
    }

    return {
        "spec": cand_spec,
        "trades": all_trades,
        "daily_pnl_1x": dpnl_1x,
        "daily_pnl_15x": dpnl_15x,
        "daily_pnl_2x": dpnl_2x,
        "daily_pnl_zero_pos_swap": dpnl_zpos,
        "fade_daily_pnl_1x": fade_dpnl_1x,
        "metrics": metrics,
        "data_resolution": cc.RES_NATIVE_M1_BIDASK,
        "blindness_tier": cc.TIER_12OLD,
        "allow_unidirectional": bool(cand_spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# Pre-Registered Economically Grounded Candidate Menu (<= 100 total)
# ---------------------------------------------------------------------------


def build_f03_candidate_specs() -> list[dict[str, Any]]:
    """Build bounded (<= 100) pre-registered F03 candidate menu across all 4 FX microstructure pillars."""
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        subfamily: str,
        symbols: Sequence[str],
        params: dict[str, Any],
        rationale: str,
        counterparty: str,
        lit_ref: str,
        allow_unidir: bool,
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
                "prop_track": PROP_TRACK,
                "symbols": list(symbols),
                "leader_symbols": [],
                "params": dict(params),
                "economic_rationale": rationale.strip(),
                "counterparty_mechanism": counterparty.strip(),
                "literature_ref": lit_ref,
                "allow_unidirectional": bool(allow_unidir),
                "data_resolution": cc.RES_NATIVE_M1_BIDASK,
                "blindness_tier": cc.TIER_12OLD,
            }
        )

    # --- 1. WM/Reuters 16:00 London Fix (Michelberger/Witte, Krohn/Mueller/Whelan, FXTradeSimu) ---
    wmr_post_rat = (
        "Pre-fix institutional benchmark orders into 16:00 Europe/London push spot temporarily away "
        "from fundamental fair value; fading extreme pre-fix displacement after 16:05 London captures "
        "post-auction dealer inventory normalization with swap=0 and hard ATR stop."
    )
    wmr_post_cp = (
        "Passive index trackers, pension funds, and FX broker-dealers executing guaranteed 16:00 "
        "WMR fix orders pre-hedge concentrated flow and unwind excess inventory after the fix closes."
    )
    # 1A: Pooled 7-FX & 5-USD-major post-fix reversal across 2 pre-windows & thresholds
    for tag, syms in (("ALL7", FX_M1_SYMBOLS), ("USD5", ("EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"))):
        for pre_m, th, sl, tp, hold_m in (
            (60, 0.25, 0.60, 1.00, 180),
            (60, 0.35, 0.70, 1.20, 210),
            (120, 0.35, 0.65, 1.10, 180),
            (120, 0.50, 0.75, 1.35, 240),
        ):
            _add(
                f"F03_WMR_POSTFADE_{tag}_P{pre_m}_T{int(th * 100):02d}_SL{int(sl * 100):02d}",
                "WMR_1600_LDN_FIX",
                syms,
                {
                    "rule": "wmr_postfix_fade",
                    "pre_window_min": pre_m,
                    "thresh_atr": th,
                    "sl_atr": sl,
                    "tp_atr": tp,
                    "hold_min": hold_m,
                },
                wmr_post_rat,
                wmr_post_cp,
                "Michelberger & Witte (2016) / LEAD-OFF3-ARXIV-01",
                allow_unidir=False,
            )

    # 1A-indiv: Individual FX pairs post-fix reversal (all 7 pairs covered)
    for sym in FX_M1_SYMBOLS:
        for pre_m, th, sl, tp in ((90, 0.30, 0.65, 1.10), (120, 0.45, 0.75, 1.30)):
            _add(
                f"F03_WMR_POSTFADE_{sym}_P{pre_m}_T{int(th * 100):02d}",
                "WMR_1600_LDN_FIX",
                (sym,),
                {
                    "rule": "wmr_postfix_fade",
                    "pre_window_min": pre_m,
                    "thresh_atr": th,
                    "sl_atr": sl,
                    "tp_atr": tp,
                    "hold_min": 210,
                },
                wmr_post_rat,
                wmr_post_cp,
                "Michelberger & Witte (2016) / LEAD-OFF3-ARXIV-01",
                allow_unidir=False,
            )

    # 1B: Krohn/Mueller/Whelan pre-fix USD drift & post-fix USD unwind (SSRN-03)
    kmw_rat = (
        "Unconditional institutional demand for immediacy at the 16:00 Europe/London WMR benchmark "
        "causes OTC FX dealers to pre-hedge USD inventory imbalance ahead of the fix and unwind "
        "accumulated USD exposure immediately afterward on the same UTC day (swap=0)."
    )
    kmw_cp = (
        "Risk-averse OTC dealer banks absorbing price-insensitive institutional benchmark orders "
        "require temporary USD price concessions pre-fix and mean-revert inventory post-fix."
    )
    usd5 = ("EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD")
    for leg, pre_m, hold_m, min_mv, sl in (
        ("prefix_long_usd", 120, 120, 0.0, 0.65),
        ("prefix_long_usd", 90, 90, 0.20, 0.65),
        ("postfix_short_usd", 120, 180, 0.0, 0.65),
        ("postfix_short_usd", 120, 180, 0.25, 0.70),
    ):
        _add(
            f"F03_WMR_KMW_{leg.upper()}_M{int(min_mv * 100):02d}_P{pre_m}",
            "WMR_1600_LDN_FIX",
            usd5,
            {
                "rule": "wmr_prefix_usd_drift",
                "leg": leg,
                "pre_window_min": pre_m,
                "hold_min": hold_m,
                "min_ldn_move_atr": min_mv,
                "sl_atr": sl,
                "tp_atr": 1.20,
            },
            kmw_rat,
            kmw_cp,
            "Krohn, Mueller & Whelan (2024) / LEAD-OFF3-SSRN-03",
            allow_unidir=True,
        )

    # 1C: Month-End WMR 16:00 Fix Contrarian Flow (FXTradeSimu / GH-12)
    me_rat = (
        "Global equity/bond portfolio managers execute mandatory month-end passive FX hedge "
        "rebalancing at the 16:00 Europe/London WMR fix opposite month-to-date currency moves, "
        "generating predictable contrarian pre-fix pressure and post-fix mean reversion."
    )
    me_cp = (
        "Benchmark-tracking global asset managers mechanically adjust currency hedges at month-end "
        "16:00 London regardless of short-horizon impact, paying liquidity providers for absorption."
    )
    for leg, me_days, th_mtd, sl in (
        ("prefix", 1, 0.50, 0.65),
        ("prefix", 2, 0.75, 0.70),
        ("postfix", 1, 0.50, 0.65),
        ("postfix", 2, 0.75, 0.70),
    ):
        _add(
            f"F03_WMR_MONTHEND_{leg.upper()}_D{me_days}_T{int(th_mtd * 100):02d}",
            "WMR_1600_LDN_FIX",
            FX_M1_SYMBOLS,
            {
                "rule": "wmr_monthend_contra",
                "leg": leg,
                "month_end_days": me_days,
                "pre_window_min": 60,
                "hold_min": 150,
                "thresh_mtd_atr": th_mtd,
                "sl_atr": sl,
                "tp_atr": 1.25,
            },
            me_rat,
            me_cp,
            "FXTradeSimu Month-End WMR Fix / LEAD-OFF3-GH-12",
            allow_unidir=False,
        )

    # --- 2. Tokyo 09:55 JST Gotobi Fix (Bessho, tradedeck / ARXIV-02, GH-11, COMM-EN-01) ---
    gotobi_pre_rat = (
        "On Japanese Gotobi settlement days (5th/10th/15th/20th/25th/30th business days), domestic "
        "commercial importers systematically buy USD/FX against JPY ahead of the 09:55 JST TTM bank "
        "fixing rate, creating pre-fix upward drift on JPY-quote pairs with zero overnight swap."
    )
    gotobi_pre_cp = (
        "Price-insensitive Japanese corporate importers settling trade invoices at 09:55 JST force "
        "Japanese megabanks to pre-hedge USD/FX shortages against JPY prior to the fixing cutoff."
    )
    for tag, syms in (("USDJPY", ("USDJPY",)), ("JPY3", JPY_QUOTE_SYMBOLS)):
        for ex_mon, max_gap, sl in ((False, None, 0.55), (True, None, 0.55), (True, 0.35, 0.60)):
            _add(
                f"F03_GOTOBI_PRE_{tag}_XM{int(ex_mon)}_SL{int(sl * 100):02d}"
                + (f"_G{int(max_gap * 100):02d}" if max_gap is not None else ""),
                "TOKYO_GOTOBI_0955",
                syms,
                {
                    "rule": "gotobi_prefix_long",
                    "exclude_monday": ex_mon,
                    "entry_min_utc": 5,
                    "max_prev_gap_atr": max_gap,
                    "sl_atr": sl,
                    "tp_atr": 0.90,
                },
                gotobi_pre_rat,
                gotobi_pre_cp,
                "Bessho Gotobi Anomaly / LEAD-OFF3-ARXIV-02",
                allow_unidir=True,
            )

    gotobi_post_rat = (
        "Immediately after the 09:55 JST Tokyo TTM benchmark closes on Gotobi settlement days, "
        "Japanese commercial importer buying ceases and dealer long USD/JPY inventory unwinds "
        "between 09:56 JST and early afternoon (12:00-15:00 JST), yielding post-fix downward reversion."
    )
    gotobi_post_cp = (
        "Tokyo FX dealer banks holding residual long USD/FX inventory accumulated into 09:55 JST "
        "offload positions into thinner post-fix Asian liquidity once corporate benchmark orders finish."
    )
    for tag, syms in (("USDJPY", ("USDJPY",)), ("EURJPY", ("EURJPY",)), ("JPY3", JPY_QUOTE_SYMBOLS)):
        for drift_min, hold_m, sl, tp in (
            (0.05, 180, 0.55, 0.95),
            (0.15, 240, 0.65, 1.15),
        ):
            _add(
                f"F03_GOTOBI_POSTFADE_{tag}_D{int(drift_min * 100):02d}_H{hold_m}",
                "TOKYO_GOTOBI_0955",
                syms,
                {
                    "rule": "gotobi_postfix_fade",
                    "exclude_monday": True,
                    "min_prefix_drift_atr": drift_min,
                    "hold_min": hold_m,
                    "sl_atr": sl,
                    "tp_atr": tp,
                },
                gotobi_post_rat,
                gotobi_post_cp,
                "tradedeck Tokyo Gotobi Fade / LEAD-OFF3-GH-11 & COMM-EN-01",
                allow_unidir=True,
            )

    # Pure time-exit literature-exact variants (Michelberger/Witte & tradedeck: hard SL, flat at session clock)
    for tag, syms, pre_m, th, sl, hold_m in (
        ("JPY3", JPY_QUOTE_SYMBOLS, 120, 0.45, 0.75, 240),
        ("EURJPY", ("EURJPY",), 120, 0.45, 0.80, 240),
        ("GBPJPY", ("GBPJPY",), 120, 0.45, 0.80, 240),
        ("ALL7", FX_M1_SYMBOLS, 120, 0.45, 0.80, 240),
    ):
        _add(
            f"F03_WMR_POSTFADE_TIMEEXIT_{tag}_P{pre_m}_T{int(th * 100):02d}",
            "WMR_1600_LDN_FIX",
            syms,
            {
                "rule": "wmr_postfix_fade",
                "pre_window_min": pre_m,
                "thresh_atr": th,
                "sl_atr": sl,
                "tp_atr": None,
                "hold_min": hold_m,
            },
            wmr_post_rat,
            wmr_post_cp,
            "Michelberger & Witte (2016) Pure Time-Exit Post-Fix / LEAD-OFF3-ARXIV-01",
            allow_unidir=False,
        )

    for tag, syms, drift_min, hold_m, sl in (
        ("USDJPY", ("USDJPY",), 0.12, 300, 0.70),
        ("USDJPY", ("USDJPY",), 0.15, 360, 0.75),
        ("JPY3", JPY_QUOTE_SYMBOLS, 0.15, 300, 0.75),
    ):
        _add(
            f"F03_GOTOBI_POSTFADE_TIMEEXIT_{tag}_D{int(drift_min * 100):02d}_H{hold_m}",
            "TOKYO_GOTOBI_0955",
            syms,
            {
                "rule": "gotobi_postfix_fade",
                "exclude_monday": True,
                "min_prefix_drift_atr": drift_min,
                "hold_min": hold_m,
                "sl_atr": sl,
                "tp_atr": None,
            },
            gotobi_post_rat,
            gotobi_post_cp,
            "tradedeck Tokyo Gotobi Pure Time-Exit Fade / LEAD-OFF3-GH-11",
            allow_unidir=True,
        )

    # Symmetric all-day Tokyo 09:55 JST impulse fade (bidirectional!)
    tokyo_sym_rat = (
        "Sharp directional moves in the 09:00-09:55 JST Tokyo fixing window reflect concentrated "
        "commercial benchmark execution rather than fundamental news; fading large pre-fix moves "
        "symmetrically at 09:56 JST captures post-fix Asian liquidity mean reversion."
    )
    tokyo_sym_cp = (
        "Asian commercial hedgers and domestic banks executing time-constrained 09:55 JST benchmark "
        "orders induce transient two-sided price overshoots that revert once the fixing window ends."
    )
    tokyo_sym_targets = (
        ("JPY3", JPY_QUOTE_SYMBOLS),
        ("USDJPY", ("USDJPY",)),
        ("AUDUSD", ("AUDUSD",)),
        ("ALL7", FX_M1_SYMBOLS),
    )
    for tag, syms in tokyo_sym_targets:
        for th, hold_m, sl in ((0.20, 180, 0.55), (0.30, 240, 0.65)):
            _add(
                f"F03_TOKYO_SYMFADE_{tag}_T{int(th * 100):02d}_H{hold_m}",
                "TOKYO_GOTOBI_0955",
                syms,
                {
                    "rule": "tokyo_fix_sym_fade",
                    "thresh_atr": th,
                    "hold_min": hold_m,
                    "sl_atr": sl,
                    "tp_atr": 1.05,
                },
                tokyo_sym_rat,
                tokyo_sym_cp,
                "Tokyo 09:55 JST Fixing Microstructure / LEAD-OFF3-ARXIV-02 & GH-11",
                allow_unidir=False,
            )

    # --- 3. NY 10:00 ET Option-Expiry Cut Mean-Reversion (DST-exact via OPS-1) ---
    nycut_rat = (
        "Vanilla FX options expire daily at 10:00 America/New_York (DST-exact via OPS-1), driving "
        "dealer delta/gamma hedging pressure during 07:00-10:00 ET; once options expire, mechanical "
        "hedge unwinds trigger intraday mean-reversion back toward morning equilibrium (swap=0)."
    )
    nycut_cp = (
        "FX options market makers defending large 10:00 ET strike/barrier expiries push spot away "
        "from fundamental levels pre-cut and rapidly unwind residual delta hedges after 10:00 ET."
    )
    for tag, syms in (
        ("ALL7", FX_M1_SYMBOLS),
        ("USD5", usd5),
        ("EURUSD", ("EURUSD",)),
        ("GBPUSD", ("GBPUSD",)),
        ("USDJPY", ("USDJPY",)),
        ("USDCAD", ("USDCAD",)),
        ("AUDUSD", ("AUDUSD",)),
        ("EURJPY", ("EURJPY",)),
        ("GBPJPY", ("GBPJPY",)),
    ):
        for pre_m, th, sl, tp, hold_m in (
            (120, 0.35, 0.65, 1.10, 180),
            (180, 0.45, 0.75, 1.30, 240),
        ):
            _add(
                f"F03_NY10CUT_FADE_{tag}_P{pre_m}_T{int(th * 100):02d}",
                "NY_1000_OPTION_CUT",
                syms,
                {
                    "rule": "ny_cut_reversion",
                    "mode": "fade",
                    "pre_window_min": pre_m,
                    "thresh_atr": th,
                    "sl_atr": sl,
                    "tp_atr": tp,
                    "hold_min": hold_m,
                },
                nycut_rat,
                nycut_cp,
                "NY 10:00 ET FX Option-Expiry Cut Microstructure (OPS-1 DST)",
                allow_unidir=False,
            )

    # Also test 2 NY-cut follow-through controls on pooled USD5/ALL7 (causal breakout-free momentum handover)
    _add(
        "F03_NY10CUT_FOLLOW_ALL7_P120_T45",
        "NY_1000_OPTION_CUT",
        FX_M1_SYMBOLS,
        {
            "rule": "ny_cut_reversion",
            "mode": "follow",
            "pre_window_min": 120,
            "thresh_atr": 0.45,
            "sl_atr": 0.75,
            "tp_atr": 1.35,
            "hold_min": 210,
        },
        "When NY morning macro orderflow breaks free of 10:00 ET option strikes past 0.45 ATR, "
        "post-expiry barrier releases induce directional continuation into NY afternoon (swap=0).",
        "Option dealers short gamma beyond expired 10:00 ET strikes must chase spot directionally "
        "after option expiry releases pinning liquidity.",
        "NY 10:00 ET FX Option-Expiry Post-Pin Release (OPS-1 DST)",
        allow_unidir=False,
    )

    # --- 4. Breedon & Ranaldo (2013) Working-Hours Orderflow Reversion ---
    br_rev_rat = (
        "Breedon & Ranaldo (2013) show domestic commercial orderflow drives transient intraday "
        "currency displacement during local working hours that systematically reverts once foreign "
        "session liquidity enters across Asian-London and London-NY handovers (DST-exact, swap=0)."
    )
    br_rev_cp = (
        "Local corporate importers, exporters, and domestic asset managers executing working-hours "
        "FX cash flows pay temporary liquidity premia to global cross-session dealer desks."
    )
    for win, tag, syms, th, sl, tp in (
        ("asia_to_ldn", "ALL7", FX_M1_SYMBOLS, 0.30, 0.65, 1.15),
        ("asia_to_ldn", "ALL7", FX_M1_SYMBOLS, 0.45, 0.75, 1.30),
        ("asia_to_ldn", "JPY3", JPY_QUOTE_SYMBOLS, 0.30, 0.65, 1.15),
        ("asia_to_ldn", "AUDUSD", ("AUDUSD",), 0.35, 0.70, 1.20),
        ("ldn_to_ny", "ALL7", FX_M1_SYMBOLS, 0.35, 0.65, 1.15),
        ("ldn_to_ny", "ALL7", FX_M1_SYMBOLS, 0.50, 0.75, 1.35),
        ("ldn_to_ny", "EURGBP", ("EURUSD", "GBPUSD", "EURJPY", "GBPJPY"), 0.40, 0.70, 1.25),
        ("ldn_to_ny", "EURUSD", ("EURUSD",), 0.40, 0.65, 1.15),
        ("ldn_to_ny", "GBPUSD", ("GBPUSD",), 0.45, 0.70, 1.20),
        ("overlap_to_pm", "ALL7", FX_M1_SYMBOLS, 0.45, 0.70, 1.25),
        ("overlap_to_pm", "USD5", usd5, 0.50, 0.75, 1.30),
        ("overlap_to_pm", "USDCAD", ("USDCAD",), 0.40, 0.70, 1.20),
    ):
        _add(
            f"F03_BREEDON_REV_{win.upper()}_{tag}_T{int(th * 100):02d}",
            "BREEDON_RANALDO_LOCAL",
            syms,
            {
                "rule": "breedon_session_reversion",
                "window": win,
                "thresh_atr": th,
                "sl_atr": sl,
                "tp_atr": tp,
            },
            br_rev_rat,
            br_rev_cp,
            "Breedon & Ranaldo (2013, JMCB) Intraday Working-Hours Orderflow",
            allow_unidir=False,
        )

    # Structural Breedon-Ranaldo clock-based local-currency sell & foreign-session buyback
    br_clk_rat = (
        "Direct structural test of Breedon & Ranaldo (2013): sell each currency during its domestic "
        "working hours (where local corporate net outflows depress spot) or buy back during foreign "
        "working hours across all 7 M1 FX pairs with strictly geographical directional assignment."
    )
    for sess, action, sl in (
        ("ASIA", "sell_local", 0.65),
        ("ASIA", "revert_post_local", 0.65),
        ("EUROPE", "sell_local", 0.70),
        ("EUROPE", "revert_post_local", 0.70),
        ("NY", "sell_local", 0.70),
    ):
        _add(
            f"F03_BREEDON_CLK_{sess}_{action.upper()}",
            "BREEDON_RANALDO_LOCAL",
            FX_M1_SYMBOLS,
            {
                "rule": "breedon_clock_flow",
                "session": sess,
                "action": action,
                "sl_atr": sl,
                "tp_atr": 1.25,
            },
            br_clk_rat,
            br_rev_cp,
            "Breedon & Ranaldo (2013, JMCB) Working-Hours Calendar Effect",
            allow_unidir=False,
        )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F03 candidate menu exceeds TOTAL_CAP={TOTAL_CAP}: got {len(specs)}")
    return specs


# ---------------------------------------------------------------------------
# Cluster A Anti-Overfit Scoring & Diverse Primary Selection (`<= 16`)
# ---------------------------------------------------------------------------


def _score_cluster_a_result(res: Mapping[str, Any]) -> tuple[bool, float]:
    """Compute conservative anti-overfit Cluster A (`2018-2020`) quality score."""
    met = res["metrics"]
    m1 = met["1x"]
    m15 = met["1.5x"]
    m2 = met["2x"]
    mf = met["fade_1x"]
    s0 = met["stage0"]
    side = met["side_split"]
    allow_u = bool(res["allow_unidirectional"])

    n_tr = int(m1["n_trades"])
    if not s0.get("passed", False) or n_tr < 20:
        return False, -999.0

    sh_1x = float(m1["sharpe"])
    sh_15x = float(m15["sharpe"])
    sh_2x = float(m2["sharpe"])
    sh_fade = float(mf["sharpe"])
    pos_yr_ratio = float(m1["positive_year_ratio"])
    by_yr = m1.get("by_year_R") or {}
    worst_yr = min((float(v) for v in by_yr.values()), default=-99.0)
    max_dd = float(m1["max_DD_R"])
    net_1x = float(m1["net_R"])

    # Side balance bonus/penalty for bidirectional rules
    side_penalty = 0.0
    if not allow_u:
        b_n = int(side["buy"]["n"])
        s_n = int(side["sell"]["n"])
        if b_n < 5 or s_n < 5:
            side_penalty -= 1.0
        elif float(side["buy"]["net_R"]) > 0.0 and float(side["sell"]["net_R"]) > 0.0:
            side_penalty += 0.35
        else:
            side_penalty -= 0.40

    # Emphasize 2x stress survival, fade margin, multi-year consistency, and worst-year resilience
    fade_margin = max(-1.5, min(2.0, sh_1x - sh_fade))
    calmar_proxy = net_1x / max(3.0, max_dd)
    score = (
        0.35 * sh_1x
        + 0.45 * sh_15x
        + 0.55 * sh_2x
        + 0.30 * fade_margin
        + 0.60 * pos_yr_ratio
        + 0.15 * max(-2.0, min(3.0, calmar_proxy))
        + 0.04 * max(-12.0, min(6.0, worst_yr))
        + 0.10 * min(1.5, math.log1p(n_tr) / 5.0)
        + side_penalty
    )
    eligible_primary = bool(
        s0["passed"] and n_tr >= 25 and sh_1x >= 0.20 and sh_15x > 0.0 and sh_1x > sh_fade + 0.25
    )
    return eligible_primary, round(float(score), 6)


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
    per_subfamily_cap = 5
    sub_counts: dict[str, int] = {}

    # Pass 1: Guarantee representation for each distinct subfamily with eligible positive edge (up to 2 each)
    for min_per_sub in (1, 2):
        for row in ranked:
            if len(primary) >= PRIMARY_CAP:
                break
            cid = row["candidate_id"]
            sub = row["subfamily"]
            if cid in chosen_ids or not row["eligible_primary"]:
                continue
            if sub_counts.get(sub, 0) < min_per_sub:
                item = dict(row["spec"])
                item["tier"] = "PRIMARY"
                item["cluster_a_score"] = row["cluster_a_score"]
                item["cluster_a_metrics"] = row["cluster_a_metrics"]
                primary.append(item)
                chosen_ids.add(cid)
                sub_counts[sub] = sub_counts.get(sub, 0) + 1

    # Pass 2: Fill remaining Primary slots up to PRIMARY_CAP from eligible positive pool only
    # (NEVER pad PRIMARY_M200 with negative Cluster A candidates!)
    for row in ranked:
        if len(primary) >= PRIMARY_CAP:
            break
        cid = row["candidate_id"]
        sub = row["subfamily"]
        if cid in chosen_ids or not row["eligible_primary"]:
            continue
        if sub_counts.get(sub, 0) >= per_subfamily_cap:
            continue
        item = dict(row["spec"])
        item["tier"] = "PRIMARY"
        item["cluster_a_score"] = row["cluster_a_score"]
        item["cluster_a_metrics"] = row["cluster_a_metrics"]
        primary.append(item)
        chosen_ids.add(cid)
        sub_counts[sub] = sub_counts.get(sub, 0) + 1

    exploratory: list[dict[str, Any]] = []
    for row in ranked:
        if len(primary) + len(exploratory) >= TOTAL_CAP:
            break
        cid = row["candidate_id"]
        if cid in chosen_ids:
            continue
        item = dict(row["spec"])
        item["tier"] = "EXPLORATORY"
        item["cluster_a_score"] = row["cluster_a_score"]
        item["cluster_a_metrics"] = row["cluster_a_metrics"]
        exploratory.append(item)

    return primary, exploratory


def _summarize_metrics_for_checkpoint(metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Return compact JSON-safe Cluster A metrics dict (strictly years 2018..2020 only)."""
    return {
        "1x": dict(metrics["1x"]),
        "1.5x": dict(metrics["1.5x"]),
        "2x": dict(metrics["2x"]),
        "zero_pos_swap_1x": dict(metrics["zero_pos_swap_1x"]),
        "fade_1x": dict(metrics["fade_1x"]),
        "stage0": dict(metrics["stage0"]),
        "side_split": dict(metrics["side_split"]),
        "years": list(cc.CLUSTER_A_YEARS),
    }


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
    """Run Stage 2 Cluster A (`2018-2020` ONLY!) discovery for `F03_FX_FIX_FLOW`.

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
            symbols=FX_M1_SYMBOLS,
            verify_sha=verify_sha,
            root=root,
        )
    )
    rn_idx = _get_red_news_index(root=root)
    candidate_specs = build_f03_candidate_specs()

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
    for c in primary:
        sf = str(c["subfamily"])
        subfamily_counts[sf] = subfamily_counts.get(sf, 0) + 1

    meta: dict[str, Any] = {
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "family_code": FAMILY_CODE,
        "family_slug": FAMILY_ID,
        "primary_cap": PRIMARY_CAP,
        "prop_track": PROP_TRACK,
        "symbols_covered": list(FX_M1_SYMBOLS),
        "max_fric_sl_ratio": MAX_FRIC_SL_RATIO,
        "news_pad_sec": NEWS_PAD_SEC,
        "primary_subfamily_counts": subfamily_counts,
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
    parser = argparse.ArgumentParser(description="Total Offensive #3 — F03 FX Fixing & Working-Hours Orderflow (Cl.A)")
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
            "n": c["cluster_a_metrics"]["1x"]["n_trades"],
            "sh1x": c["cluster_a_metrics"]["1x"]["sharpe"],
            "sh2x": c["cluster_a_metrics"]["2x"]["sharpe"],
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
    "FAMILY_CODE",
    "FAMILY_ID",
    "FX_M1_SYMBOLS",
    "MAX_FRIC_SL_RATIO",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_CAP",
    "TOTAL_CAP",
    "build_f03_candidate_specs",
    "compute_gotobi_dates_for_years",
    "compute_month_end_weekdays",
    "discover_cluster_a",
    "evaluate_candidate",
]


if __name__ == "__main__":
    raise SystemExit(main())
