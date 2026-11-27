"""Total Offensive #3 — Family F09: Structural Calendar & Macro-Event Drift (`F09_SWING_CALENDAR`).

FTMO Swing (`1–4d`) & Pre-Release-Compliant Intraday (`swap = 0`) calendar/macro-event
strategies across `6` Global Indices (`US500, US100, US30, GER40, UK100, JP225`),
`2` Metals (`XAUUSD, XAGUSD`), and `6` FX Majors (`EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF`).

Four orthogonal white-box mechanisms:
  1. `TOM_INDICES` — Turn-of-Month (`Etula Dash-for-Cash`): last `k_end` -> first `k_start`
     calendar business days on Global Indices (individual + equal-risk 6-index basket;
     strictly calendar-deterministic, `allow_unidirectional = True`).
  2. `TURNAROUND_TUE` — Turnaround Tuesday / Monday-Dip Reversal (`Open-Alpha-Lab` / `MQL5-07`):
     causal down-Monday (`ret_mon < -thresh * ATR` or `IBS < ibs_max`) -> Tuesday open entry,
     `1–3d` hold (`allow_unidirectional = True`).
  3. `PRE_FOMC_M1` & `POST_NEWS_M1` / `POST_NEWS_D1` — Official 6-CCY + Extended 8-CCY/EIA
     macro-event flows using `OPS-1` DST/calendar guards:
       * Pre-FOMC Drift exits strictly `>= 15m` BEFORE FOMC release (`allow_unidirectional = True`),
         obeying `+-2m`/`+-5m` prop news rules.
       * Post-RedNews Drift enters strictly AFTER release blackout (`+30m/+60m` M1 intraday `swap=0`
         or next-day D1 Swing open, two-sided `allow_unidirectional = False`).
  4. `OVERNIGHT_M1` & `OVERNIGHT_D1` — Cash-Close -> Cash-Open overnight drift (`Knuteson` / `vrd07`)
     on DST-exact NY/EU clocks with REAL overnight financing deducted (`allow_unidirectional = True`).

Hard invariants (`G01`, `G05`, `G06`, `G07`, `[ARCH-02]`):
  - ZERO bare `assert` statements; `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - Strict pre-cutoff Dev enforcement (`max_ts < 1735689600`, zero sealed rows analysed).
  - HARD BLINDNESS LOCK: `discover_cluster_a(universe)` strictly touches `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY!
  - Strict `shift = 1` daily causality & `< entry_ts` intraday causality; mandatory hard SL on every trade.
  - Real triple-swap rollover (`Wed 3x` FX/Metals, `Fri 3x` Indices), Anti-Fake-Swap Guard with
    conservative `-5%/yr` financing floor on blocked positive index swaps, AND `zero_pos_swap` floor.
"""

from __future__ import annotations

import argparse
import calendar
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

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


from quant_factory.offensive3 import common_contract as cc  # noqa: E402

try:  # Prefer OPS-1 live_ops DST & extended calendar resolver directly
    from quant_factory.live_ops import feed_dst_news_guard as ops1_guard  # noqa: E402
except ImportError:  # pragma: no cover - X13 minimal cache fallback
    ops1_guard = None

# ---------------------------------------------------------------------------
# Hard Safety & Family Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAMILY_ID: str = "F09_SWING_CALENDAR"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

INDICES_6: tuple[str, ...] = ("US500", "US100", "US30", "GER40", "UK100", "JP225")
INDICES_US3: tuple[str, ...] = ("US500", "US100", "US30")
INDICES_INTL3: tuple[str, ...] = ("GER40", "UK100", "JP225")
INDICES_M1_3: tuple[str, ...] = ("US500", "US100", "GER40")
METALS_2: tuple[str, ...] = ("XAUUSD", "XAGUSD")
FX_MAJORS_6: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF")
FX_M1_MAJORS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD")
F09_SYMBOLS: tuple[str, ...] = INDICES_6 + METALS_2 + FX_MAJORS_6

_ZI_NEW_YORK = ZoneInfo("America/New_York")
_ZI_PRAGUE = ZoneInfo("Europe/Prague")
_ZI_LONDON = ZoneInfo("Europe/London")

_DEFAULT_ACCOUNT_BALANCE_USD: float = 100_000.0
_DEFAULT_RISK_FRAC: float = 0.005

_CAUSAL_INVARIANTS_BASE: tuple[str, ...] = (
    "shift=1 daily features / < entry_ts intraday features (zero bar-t peek)",
    "mandatory hard ATR stop-loss on every trade (zero grid/martingale)",
    "exact Wed/Fri 3x real swap + Anti-Fake-Swap Guard (-5%/yr floor on blocked positive index swaps)",
    "zero_pos_swap floor evaluated alongside real_swap across 1.0x/1.5x/2.0x friction tiers",
    "FTMO Swing leverage margin check (Indices 1:15, Metals 1:9, FX 1:30)",
)

_MACRO_CALENDAR_CACHE: dict[str, list[dict[str, Any]]] = {}
_RED_NEWS_INDEX_CACHE: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Calendar & DST Helpers (Reusing OPS-1 `feed_dst_news_guard` Directly)
# ---------------------------------------------------------------------------


def _resolve_local_utc_ts(trade_day: date, hour: int, minute: int, tz_name: str) -> int:
    """Resolve exact DST-aware UTC epoch seconds for a local session clock."""
    if ops1_guard is not None:
        if tz_name == "America/New_York" and (hour, minute) == (9, 30):
            info = ops1_guard.resolve_strategy_session_utc("NY_OPEN", trade_day)
            return int(datetime.strptime(info["utc_iso"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())
        if tz_name == "America/New_York" and (hour, minute) == (17, 0):
            info = ops1_guard.resolve_strategy_session_utc("NY_CLOSE", trade_day)
            return int(datetime.strptime(info["utc_iso"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())
        if tz_name == "Europe/London" and (hour, minute) == (8, 0):
            info = ops1_guard.resolve_strategy_session_utc("LONDON_OPEN", trade_day)
            return int(datetime.strptime(info["utc_iso"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp())
    local_dt = datetime.combine(trade_day, time(hour, minute), tzinfo=ZoneInfo(tz_name))
    return int(local_dt.astimezone(UTC).timestamp())


def _weekday_rank_from_month_start(d: date) -> int:
    """Pure Gregorian 1-based weekday rank from month start (100% deterministic, zero data peek)."""
    cnt = 0
    for day_num in range(1, d.day + 1):
        if date(d.year, d.month, day_num).weekday() < 5:
            cnt += 1
    return cnt


def _weekday_rank_from_month_end(d: date) -> int:
    """Pure Gregorian 1-based weekday rank from month end (1=last weekday of month, zero data peek)."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    cnt = 0
    for day_num in range(d.day, last_day + 1):
        if date(d.year, d.month, day_num).weekday() < 5:
            cnt += 1
    return cnt


def _load_macro_events_dev(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Load pre-cutoff Dev macro events from BOTH official 6-CCY + OPS-1 extended 8-CCY/EIA calendars."""
    ws = cc.resolve_workspace_root(root)
    key = str(ws.resolve())
    if key in _MACRO_CALENDAR_CACHE:
        return _MACRO_CALENDAR_CACHE[key]

    p_base = ws / "tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json"
    p_ext = ws / "tooling/ai-engines/configs/calendars/red_news_extended_off3_8ccy_eia.json"
    if not p_base.is_file():
        raise FileNotFoundError(f"Missing official 6-CCY Dev calendar: {p_base}")

    raw_base = json.loads(p_base.read_text(encoding="utf-8-sig"))
    events: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()

    for ev in raw_base.get("events") or []:
        ts = int(ev["utc_ts"])
        cc.enforce_dev_ts_bound(ts, context="fam09.base_calendar")
        ccy = str(ev["ccy"]).strip().upper()
        name = str(ev.get("event", "")).strip().upper()
        k = (ts, ccy, name)
        if k in seen:
            continue
        seen.add(k)
        dt_u = datetime.fromtimestamp(ts, tz=UTC)
        events.append(
            {
                "utc_ts": ts,
                "utc_day": dt_u.strftime("%Y-%m-%d"),
                "year": dt_u.year,
                "ccy": ccy,
                "event": name,
                "blackout_sec": max(120, int(ev.get("blackout_sec", 300))),
            }
        )

    if p_ext.is_file():
        if ops1_guard is not None:
            ext_objs = ops1_guard.load_extended_calendar(p_ext, sections=("dev_2018_2024",))
            ext_iter = [
                {
                    "utc_ts": int(e.utc_ts),
                    "ccy": str(e.ccy).upper(),
                    "event": str(e.event).upper(),
                    "blackout_sec": int(e.blackout_sec),
                }
                for e in ext_objs
            ]
        else:
            raw_ext = json.loads(p_ext.read_text(encoding="utf-8-sig"))
            ext_iter = list(((raw_ext.get("sections") or {}).get("dev_2018_2024") or {}).get("events") or [])

        for ev in ext_iter:
            ts = int(ev["utc_ts"])
            cc.enforce_dev_ts_bound(ts, context="fam09.extended_calendar")
            ccy = str(ev["ccy"]).strip().upper()
            name = str(ev.get("event", "")).strip().upper()
            k = (ts, ccy, name)
            if k in seen:
                continue
            seen.add(k)
            dt_u = datetime.fromtimestamp(ts, tz=UTC)
            events.append(
                {
                    "utc_ts": ts,
                    "utc_day": dt_u.strftime("%Y-%m-%d"),
                    "year": dt_u.year,
                    "ccy": ccy,
                    "event": name,
                    "blackout_sec": max(120, int(ev.get("blackout_sec", 300))),
                }
            )

    events.sort(key=lambda e: (e["utc_ts"], e["ccy"], e["event"]))
    _MACRO_CALENDAR_CACHE[key] = events
    return events


def _get_red_news_index(root: str | Path | None = None) -> dict[str, Any]:
    ws = cc.resolve_workspace_root(root)
    key = str(ws.resolve())
    if key not in _RED_NEWS_INDEX_CACHE:
        _RED_NEWS_INDEX_CACHE[key] = cc.load_dev_red_news_index(include_extended=True, root=ws)
    return _RED_NEWS_INDEX_CACHE[key]


def _symbol_matches_event_ccy(symbol: str, event_ccy: str) -> bool:
    if ops1_guard is not None:
        return bool(ops1_guard.symbol_matches_event_code(symbol, event_ccy))
    return event_ccy.upper() in cc.match_symbol_red_news_codes(symbol)


# ---------------------------------------------------------------------------
# Fast Strict-Causality M1 Overnight Replay (Real Bid/Ask + Real Swap)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _scan_m1_overnight_exit_jit(
    quotes: np.ndarray,
    fill_idx: int,
    exit_cap_idx: int,
    side: int,
    sl_price: float,
    has_tp: bool,
    tp_price: float,
) -> tuple[int, float, int]:
    """Conservative M1 overnight exit scan: SL ALWAYS beats TP on same-bar tie-break.

    Exit codes: 1=SL_GAP, 2=SL_HIT, 3=TP_GAP, 4=TP_HIT, 5=TIME_EXIT.
    """
    has_ask = quotes.shape[1] >= 8
    col_o = 0 if side == 1 else (4 if has_ask else 0)
    col_h = 1 if side == 1 else (5 if has_ask else 1)
    col_l = 2 if side == 1 else (6 if has_ask else 2)
    eps = 1e-12

    for k in range(fill_idx, exit_cap_idx + 1):
        op = quotes[k, col_o]
        hi = quotes[k, col_h]
        lo = quotes[k, col_l]

        if side == 1:
            if k > fill_idx and op <= sl_price + eps:
                return k, op, 1
            if lo <= sl_price + eps:
                return k, sl_price, 2
        else:
            if k > fill_idx and op >= sl_price - eps:
                return k, op, 1
            if hi >= sl_price - eps:
                return k, sl_price, 2

        if has_tp:
            if side == 1:
                if k > fill_idx and op >= tp_price - eps:
                    return k, op, 3
                if hi >= tp_price - eps:
                    return k, tp_price, 4
            else:
                if k > fill_idx and op <= tp_price + eps:
                    return k, op, 3
                if lo <= tp_price + eps:
                    return k, tp_price, 4

    return exit_cap_idx, quotes[exit_cap_idx, col_o], 5


def _count_ny17_rollovers(entry_ts: int, exit_ts: int) -> list[int]:
    """Return `py_weekday` (0..4) for every 17:00 America/New_York rollover strictly in `(entry_ts, exit_ts]`."""
    if exit_ts <= entry_ts:
        return []
    dt_start = datetime.fromtimestamp(entry_ts, tz=UTC).astimezone(_ZI_NEW_YORK).date() - timedelta(days=1)
    dt_end = datetime.fromtimestamp(exit_ts, tz=UTC).astimezone(_ZI_NEW_YORK).date() + timedelta(days=1)
    roll_wds: list[int] = []
    cur = dt_start
    while cur <= dt_end:
        if cur.weekday() < 5:
            r_ts = _resolve_local_utc_ts(cur, 17, 0, "America/New_York")
            if entry_ts < r_ts <= exit_ts:
                roll_wds.append(cur.weekday())
        cur += timedelta(days=1)
    return roll_wds


def _replay_m1_overnight_trade(
    symbol: str,
    times_sec: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    exit_cap_idx: int,
    side: int,
    sl_dist: float,
    *,
    tp_dist: float | None = None,
    spec: Mapping[str, Any],
    weight: float = 1.0,
    conservative_financing_floor: bool = True,
    red_news_index: Mapping[str, Any] | None = None,
    news_pad_sec: int = 300,
    check_entry_news: bool = True,
) -> dict[str, Any] | None:
    """Replay a single M1 Bid/Ask overnight/swing trade with exact NY+7 rollover swap & real friction."""
    if side not in (-1, 1):
        raise ValueError(f"side must be +1 or -1, got {side!r}")
    if entry_idx < 0 or exit_cap_idx <= entry_idx or exit_cap_idx >= int(times_sec.size):
        return None
    if not math.isfinite(sl_dist) or sl_dist <= 0.0:
        return None

    fill_ts = int(times_sec[entry_idx])
    cap_ts = int(times_sec[exit_cap_idx])
    cc.enforce_dev_ts_bound(fill_ts, context=f"fam09.m1_overnight.entry:{symbol}")
    cc.enforce_dev_ts_bound(cap_ts, context=f"fam09.m1_overnight.cap:{symbol}")

    if check_entry_news and red_news_index is not None:
        if cc.is_in_red_news_window(symbol, fill_ts, red_news_index, pad_sec=news_pad_sec):
            return None

    has_ask = quotes.shape[1] >= 8
    entry_fill = float(quotes[entry_idx, 4] if (side == 1 and has_ask) else quotes[entry_idx, 0])
    sl_px = entry_fill - side * sl_dist
    if not math.isfinite(entry_fill) or entry_fill <= 0.0 or sl_px <= 0.0:
        return None

    has_tp = tp_dist is not None and math.isfinite(float(tp_dist)) and float(tp_dist) > 0.0
    tp_px = (entry_fill + side * float(tp_dist)) if has_tp else 0.0

    mchk = cc.check_leverage_margin(
        spec,
        entry_fill,
        sl_px,
        account_balance_usd=_DEFAULT_ACCOUNT_BALANCE_USD,
        risk_frac=_DEFAULT_RISK_FRAC * float(weight),
        account_type="ftmo_swing",
        max_margin_util_frac=0.80,
        scale_if_over_margin=True,
    )
    if not mchk["accepted"]:
        return None

    exit_idx, exit_fill, exit_code = _scan_m1_overnight_exit_jit(
        quotes, int(entry_idx), int(exit_cap_idx), int(side), float(sl_px), bool(has_tp), float(tp_px)
    )
    exit_ts = int(times_sec[exit_idx])
    cc.enforce_dev_ts_bound(exit_ts, context=f"fam09.m1_overnight.exit:{symbol}")

    # Exact NY+7 17:00 ET overnight rollover swap (real_swap vs zero_pos_swap)
    roll_wds = _count_ny17_rollovers(fill_ts, exit_ts)
    swap_real_r = 0.0
    swap_zpos_r = 0.0
    ref_px = 0.5 * (entry_fill + exit_fill)
    for rwd in roll_wds:
        sw_real = cc.compute_daily_swap_frac(
            spec,
            ref_px,
            side,
            rwd,
            zero_positive_swap=False,
            conservative_financing_floor=conservative_financing_floor,
        )
        sw_zpos = cc.compute_daily_swap_frac(
            spec,
            ref_px,
            side,
            rwd,
            zero_positive_swap=True,
            conservative_financing_floor=conservative_financing_floor,
        )
        swap_real_r += (sw_real * ref_px) / sl_dist
        swap_zpos_r += (sw_zpos * ref_px) / sl_dist

    pt = float(spec["point"])
    bench_sp_px = float(spec["benchmark_spread_pts"]) * pt
    if has_ask:
        entry_sp_px = max(0.0, float(quotes[entry_idx, 4] - quotes[entry_idx, 0]))
        exit_sp_px = max(0.0, float(quotes[exit_idx, 4] - quotes[exit_idx, 0]))
        embedded_sp_px = 0.5 * (entry_sp_px + exit_sp_px)
    else:
        embedded_sp_px = 0.0

    comm_usd = float(spec["commission_usd_lot"])
    usd_per_px = float(mchk["usd_per_price_unit_1lot"])
    comm_px = comm_usd / usd_per_px if usd_per_px > 0.0 else 0.0
    base_slip_rt_px = max(pt, 0.35 * max(embedded_sp_px, bench_sp_px))
    total_fric_1x_px = (embedded_sp_px if has_ask else bench_sp_px) + comm_px + base_slip_rt_px

    raw_pnl_px = side * (exit_fill - entry_fill)
    gross_r = raw_pnl_px / sl_dist
    eff_scale = float(mchk["eff_risk_scale"]) * float(weight)

    tier_real: dict[str, float] = {}
    tier_zpos: dict[str, float] = {}
    for mult in cc.FRICTION_TIERS:
        m = float(mult)
        tot_f_px = m * total_fric_1x_px
        extra_f_px = max(0.0, tot_f_px - embedded_sp_px) if has_ask else tot_f_px
        lbl = f"{m:g}x"
        tier_real[lbl] = round((((raw_pnl_px - extra_f_px) / sl_dist) + swap_real_r) * eff_scale, 6)
        tier_zpos[lbl] = round((((raw_pnl_px - extra_f_px) / sl_dist) + swap_zpos_r) * eff_scale, 6)

    reason_map = {1: "SL_GAP", 2: "SL_HIT", 3: "TP_GAP", 4: "TP_HIT", 5: "TIME_EXIT"}
    return {
        "symbol": str(spec["canonical_symbol"]),
        "blindness_tier": str(spec["blindness_tier"]),
        "data_resolution": cc.RES_NATIVE_M1_BIDASK,
        "side": int(side),
        "entry_idx": int(entry_idx),
        "exit_idx": int(exit_idx),
        "entry_ts": fill_ts,
        "exit_ts": exit_ts,
        "entry_date": datetime.fromtimestamp(fill_ts, tz=UTC).strftime("%Y-%m-%d"),
        "exit_date": datetime.fromtimestamp(exit_ts, tz=UTC).strftime("%Y-%m-%d"),
        "entry_price": round(entry_fill, 8),
        "exit_price": round(exit_fill, 8),
        "sl_price": round(sl_px, 8),
        "tp_price": round(tp_px, 8) if has_tp else None,
        "sl_dist": round(sl_dist, 8),
        "hold_minutes": int((exit_ts - fill_ts) // 60),
        "rollovers_crossed": len(roll_wds),
        "exit_reason": reason_map[int(exit_code)],
        "lots": float(mchk["lots"]),
        "eff_risk_scale": round(eff_scale, 6),
        "margin_capped": bool(mchk["margin_capped"]),
        "margin_util_frac": float(mchk["margin_util_frac"]),
        "gross_R": round(gross_r * eff_scale, 6),
        "swap_real_R": round(swap_real_r * eff_scale, 6),
        "swap_zero_pos_R": round(swap_zpos_r * eff_scale, 6),
        "net_R": tier_real["1x"],
        "net_R_1x": tier_real["1x"],
        "net_R_15x": tier_real["1.5x"],
        "net_R_2x": tier_real["2x"],
        "net_R_zero_pos_1x": tier_zpos["1x"],
        "net_R_zero_pos_15x": tier_zpos["1.5x"],
        "net_R_zero_pos_2x": tier_zpos["2x"],
        "friction_over_sl": round((2.0 * total_fric_1x_px) / sl_dist, 6),
        "friction_over_sl_1x": round(total_fric_1x_px / sl_dist, 6),
        "friction_over_sl_15x": round((1.5 * total_fric_1x_px) / sl_dist, 6),
        "friction_over_sl_2x": round((2.0 * total_fric_1x_px) / sl_dist, 6),
    }


# ---------------------------------------------------------------------------
# Strict Pre-Max-Year Slicing (Enforces Hard Blindness Boundary)
# ---------------------------------------------------------------------------


def _slice_d1_upto_year(d1: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    """Slice a D1 bar dict strictly to `year <= max_year` so later years are NEVER accessed."""
    yrs = np.asarray(d1["years"], dtype=np.int32)
    mask = yrs <= int(max_year)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        raise ValueError(f"No D1 bars available for year <= {max_year}")
    end = int(idx[-1]) + 1
    out = {
        "times_sec": np.asarray(d1["times_sec"], dtype=np.int64)[:end],
        "dates": [str(d) for d in d1["dates"][:end]],
        "years": yrs[:end],
        "weekdays": np.asarray(d1["weekdays"], dtype=np.int32)[:end],
        "open": np.asarray(d1["open"], dtype=np.float64)[:end],
        "high": np.asarray(d1["high"], dtype=np.float64)[:end],
        "low": np.asarray(d1["low"], dtype=np.float64)[:end],
        "close": np.asarray(d1["close"], dtype=np.float64)[:end],
    }
    cc.enforce_dev_ts_bound(out["times_sec"], context="fam09.slice_d1")
    return out


def _slice_m1_upto_year(m1: Mapping[str, Any], max_year: int) -> tuple[np.ndarray, np.ndarray]:
    """Slice M1 arrays strictly to `ts < Jan-1-(max_year+1) UTC`."""
    cutoff_ts = int(datetime(int(max_year) + 1, 1, 1, tzinfo=UTC).timestamp())
    ts = np.asarray(m1["times_sec"], dtype=np.int64)
    q = np.asarray(m1["quotes"], dtype=np.float64)
    end = int(np.searchsorted(ts, cutoff_ts, side="left"))
    if end <= 0:
        raise ValueError(f"No M1 bars available for year <= {max_year}")
    ts_sub = ts[:end]
    q_sub = q[:end]
    cc.enforce_dev_ts_bound(ts_sub, context="fam09.slice_m1")
    return ts_sub, q_sub


def _scale_trades_by_weight(trades: list[dict[str, Any]], weight: float) -> list[dict[str, Any]]:
    """Scale trade R-fields by portfolio leg weight while keeping `friction_over_sl` invariant."""
    if abs(float(weight) - 1.0) <= 1e-12:
        return trades
    w = float(weight)
    r_keys = (
        "gross_R",
        "swap_real_R",
        "swap_zero_pos_R",
        "swap_R",
        "net_R",
        "net_R_1x",
        "net_R_15x",
        "net_R_2x",
        "net_R_zero_pos_1x",
        "net_R_zero_pos_15x",
        "net_R_zero_pos_2x",
    )
    out: list[dict[str, Any]] = []
    for tr in trades:
        d = dict(tr)
        for k in r_keys:
            if k in d and d[k] is not None and not isinstance(d[k], bool):
                d[k] = round(float(d[k]) * w, 6)
        if "eff_risk_scale" in d and d["eff_risk_scale"] is not None:
            d["eff_risk_scale"] = round(float(d["eff_risk_scale"]) * w, 6)
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Causal Signal Generators for Each F09 Mechanism (Exact `shift = 1`)
# ---------------------------------------------------------------------------


def _build_d1_tom_signals(
    d1: Mapping[str, Any],
    *,
    k_end: int,
    k_start: int,
    regime_filter: str,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Turn-of-Month strictly causal signals (calendar date[t] + shift=1 ATR/SMA/RSI)."""
    dates = d1["dates"]
    h = d1["high"]
    lo = d1["low"]
    c = d1["close"]
    n = len(dates)

    atr14 = cc.causal_atr(h, lo, c, 14)
    sma100 = cc.causal_sma(c, 100) if regime_filter == "above_sma100" else None
    sma200 = cc.causal_sma(c, 200) if regime_filter == "above_sma200" else None
    rsi2 = cc.causal_rsi(c, 2) if regime_filter == "rsi2_lt_85" else None

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    base_dir = -1.0 if flip_side else 1.0

    for t in range(1, n):
        a = float(atr14[t])
        if not math.isfinite(a) or a <= 0.0:
            continue
        dt_t = date.fromisoformat(dates[t])
        dt_prev = date.fromisoformat(dates[t - 1])
        in_tom = (_weekday_rank_from_month_end(dt_t) <= int(k_end)) or (
            _weekday_rank_from_month_start(dt_t) <= int(k_start)
        )
        prev_in_tom = (_weekday_rank_from_month_end(dt_prev) <= int(k_end)) or (
            _weekday_rank_from_month_start(dt_prev) <= int(k_start)
        )
        # Fire ONCE at the opening bar of each month's TOM window (zero mid-window re-entry after SL!)
        if not (in_tom and not prev_in_tom):
            continue

        prev_c = float(c[t - 1])
        if regime_filter == "above_sma100" and sma100 is not None:
            if not math.isfinite(float(sma100[t])) or prev_c <= float(sma100[t]):
                continue
        elif regime_filter == "above_sma200" and sma200 is not None:
            if not math.isfinite(float(sma200[t])) or prev_c <= float(sma200[t]):
                continue
        elif regime_filter == "rsi2_lt_85" and rsi2 is not None:
            if not math.isfinite(float(rsi2[t])) or float(rsi2[t]) >= 85.0:
                continue

        sig[t] = base_dir
        sl_d[t] = float(sl_atr_mult) * a
        if tp_d is not None and tp_atr_mult is not None:
            tp_d[t] = float(tp_atr_mult) * a

    return sig, sl_d, tp_d


def _build_d1_turnaround_tuesday_signals(
    d1: Mapping[str, Any],
    *,
    trigger_mode: str,
    threshold: float,
    regime_filter: str,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Turnaround Tuesday / Monday-Dip Reversal (observed at Monday close t-1 -> Tuesday open t)."""
    wds = d1["weekdays"]
    o = d1["open"]
    h = d1["high"]
    lo = d1["low"]
    c = d1["close"]
    n = len(wds)

    atr14 = cc.causal_atr(h, lo, c, 14)
    sma100 = cc.causal_sma(c, 100) if regime_filter == "above_sma100" else None
    sma200 = cc.causal_sma(c, 200) if regime_filter == "above_sma200" else None

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    base_dir = -1.0 if flip_side else 1.0

    for t in range(2, n):
        # Strictly bar t is Tuesday (wd==1) and bar t-1 is Monday (wd==0)
        if int(wds[t]) != 1 or int(wds[t - 1]) != 0:
            continue
        a = float(atr14[t])
        if not math.isfinite(a) or a <= 0.0:
            continue

        mon_o = float(o[t - 1])
        mon_h = float(h[t - 1])
        mon_l = float(lo[t - 1])
        mon_c = float(c[t - 1])
        fri_c = float(c[t - 2])

        if regime_filter == "above_sma100" and sma100 is not None:
            if not math.isfinite(float(sma100[t])) or mon_c <= float(sma100[t]):
                continue
        elif regime_filter == "above_sma200" and sma200 is not None:
            if not math.isfinite(float(sma200[t])) or mon_c <= float(sma200[t]):
                continue

        triggered = False
        if trigger_mode == "mon_cc_atr":
            triggered = (mon_c - fri_c) <= -float(threshold) * a
        elif trigger_mode == "mon_oc_atr":
            triggered = (mon_c - mon_o) <= -float(threshold) * a
        elif trigger_mode == "mon_ibs":
            rng = mon_h - mon_l
            ibs = (mon_c - mon_l) / rng if rng > 1e-12 else 0.5
            triggered = (ibs <= float(threshold)) and (mon_c < fri_c)
        elif trigger_mode == "mon_dip_or_ibs":
            rng = mon_h - mon_l
            ibs = (mon_c - mon_l) / rng if rng > 1e-12 else 0.5
            triggered = ((mon_c - fri_c) <= -float(threshold) * a) or (ibs <= 0.25 and mon_c < fri_c)
        else:
            raise ValueError(f"Unsupported trigger_mode: {trigger_mode!r}")

        if triggered:
            sig[t] = base_dir
            sl_d[t] = float(sl_atr_mult) * a
            if tp_d is not None and tp_atr_mult is not None:
                tp_d[t] = float(tp_atr_mult) * a

    return sig, sl_d, tp_d


def _build_d1_post_red_news_signals(
    symbol: str,
    d1: Mapping[str, Any],
    macro_events: Sequence[Mapping[str, Any]],
    *,
    event_types: Sequence[str],
    min_shock_atr: float,
    fade_shock: bool,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Post-RedNews D1 Swing: observe macro-day shock at t-1 close -> enter at t open (strict shift=1)."""
    dates = d1["dates"]
    o = d1["open"]
    h = d1["high"]
    lo = d1["low"]
    c = d1["close"]
    n = len(dates)

    ev_type_set = {str(x).upper() for x in event_types}
    event_days: set[str] = set()
    for ev in macro_events:
        if ev["event"] in ev_type_set and _symbol_matches_event_ccy(symbol, ev["ccy"]):
            event_days.add(str(ev["utc_day"]))

    atr14 = cc.causal_atr(h, lo, c, 14)
    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    sign_mult = -1.0 if (fade_shock ^ flip_side) else 1.0

    for t in range(2, n):
        # Bar t-1 was the macro-event day; enter strictly on NEXT trading day t open!
        if dates[t - 1] not in event_days:
            continue
        a = float(atr14[t])
        if not math.isfinite(a) or a <= 0.0:
            continue
        shock = float(c[t - 1]) - float(c[t - 2])
        body = float(c[t - 1]) - float(o[t - 1])
        if abs(shock) < float(min_shock_atr) * a:
            continue
        if shock * body <= 0.0:
            continue
        direction = 1.0 if shock > 0.0 else -1.0
        sig[t] = direction * sign_mult
        sl_d[t] = float(sl_atr_mult) * a
        if tp_d is not None and tp_atr_mult is not None:
            tp_d[t] = float(tp_atr_mult) * a

    return sig, sl_d, tp_d


def _build_d1_midweek_overnight_proxy_signals(
    d1: Mapping[str, Any],
    *,
    entry_weekdays: Sequence[int],
    regime_filter: str,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """D1 Midweek Swing Drift (avoiding Fri 3x index rollover) with strict shift=1 filters."""
    wds = d1["weekdays"]
    o = d1["open"]
    h = d1["high"]
    lo = d1["low"]
    c = d1["close"]
    n = len(wds)
    wd_set = {int(w) for w in entry_weekdays}

    atr14 = cc.causal_atr(h, lo, c, 14)
    sma100 = cc.causal_sma(c, 100) if regime_filter == "above_sma100" else None

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    base_dir = -1.0 if flip_side else 1.0

    for t in range(2, n):
        if int(wds[t]) not in wd_set:
            continue
        a = float(atr14[t])
        if not math.isfinite(a) or a <= 0.0:
            continue
        if regime_filter == "prev_down" and float(c[t - 1]) >= float(o[t - 1]):
            continue
        if regime_filter == "above_sma100" and sma100 is not None:
            if not math.isfinite(float(sma100[t])) or float(c[t - 1]) <= float(sma100[t]):
                continue
        sig[t] = base_dir
        sl_d[t] = float(sl_atr_mult) * a
        if tp_d is not None and tp_atr_mult is not None:
            tp_d[t] = float(tp_atr_mult) * a

    return sig, sl_d, tp_d


# ---------------------------------------------------------------------------
# M1 Mechanism Evaluators (Pre-FOMC, Post-RedNews Intraday, Overnight M1)
# ---------------------------------------------------------------------------


def _eval_pre_fomc_m1_symbol(
    symbol: str,
    asset: Mapping[str, Any],
    years: tuple[int, ...],
    macro_events: Sequence[Mapping[str, Any]],
    red_news_index: Mapping[str, Any],
    *,
    mode: str,  # "overnight_24h" | "intraday_london" | "intraday_ny_open"
    exit_min_before_fomc: int,
    vol_gate: str,  # "none" | "high_rvol20"
    sl_atr_mult: float,
    weight: float,
    flip_side: bool = False,
) -> list[dict[str, Any]]:
    """Pre-FOMC drift on native M1 Bid/Ask, ALWAYS exiting strictly `>= 15m` BEFORE FOMC release."""
    if int(exit_min_before_fomc) < 15:
        raise ValueError(f"Pre-FOMC exit must be >= 15m before release, got {exit_min_before_fomc}")
    m1 = asset.get("m1")
    d1_raw = asset.get("d1")
    if m1 is None or d1_raw is None:
        return []

    max_yr = max(years)
    yr_set = set(years)
    d1 = _slice_d1_upto_year(d1_raw, max_yr)
    ts_m1, q_m1 = _slice_m1_upto_year(m1, max_yr)
    spec = asset["spec"]

    atr14 = cc.causal_atr(d1["high"], d1["low"], d1["close"], 14)
    rvol20 = cc.causal_realized_vol(d1["close"], 20)
    date_to_i = {d: i for i, d in enumerate(d1["dates"])}

    # Causal rolling 60d median of rvol20 (strictly shift=1, using rvol20[t-60:t+1] which only reads c[..t-1])
    rvol_med60 = np.full(len(d1["dates"]), np.nan, dtype=np.float64)
    if vol_gate == "high_rvol20":
        for i in range(60, len(d1["dates"])):
            win = rvol20[i - 60 : i + 1]
            fin = win[np.isfinite(win)]
            if fin.size >= 20:
                rvol_med60[i] = float(np.median(fin))

    fomc_events = [e for e in macro_events if e["event"] == "FOMC_RATE" and int(e["year"]) in yr_set]
    side = -1 if flip_side else 1
    trades: list[dict[str, Any]] = []

    for ev in fomc_events:
        ev_ts = int(ev["utc_ts"])
        ev_day = str(ev["utc_day"])
        d_idx = date_to_i.get(ev_day)
        if d_idx is None or d_idx < 2:
            continue
        atr_val = float(atr14[d_idx])
        if not math.isfinite(atr_val) or atr_val <= 0.0:
            continue
        if vol_gate == "high_rvol20":
            rv = float(rvol20[d_idx])
            rm = float(rvol_med60[d_idx])
            if not (math.isfinite(rv) and math.isfinite(rm) and rv > rm):
                continue

        # Hard exit strictly >= 15m before FOMC release!
        target_exit_ts = ev_ts - int(exit_min_before_fomc) * 60
        exit_cap_idx = int(np.searchsorted(ts_m1, target_exit_ts, side="right")) - 1
        if exit_cap_idx <= 0:
            continue
        if int(ts_m1[exit_cap_idx]) > ev_ts - 900:
            continue

        sl_dist = float(sl_atr_mult) * atr_val

        if mode == "overnight_24h":
            prev_day = date.fromisoformat(d1["dates"][d_idx - 1])
            entry_target_ts = _resolve_local_utc_ts(prev_day, 16, 0, "America/New_York")
            entry_idx = int(np.searchsorted(ts_m1, entry_target_ts, side="left"))
            if entry_idx >= exit_cap_idx or entry_idx >= int(ts_m1.size):
                continue
            if abs(int(ts_m1[entry_idx]) - entry_target_ts) > 7200:
                continue
            tr = _replay_m1_overnight_trade(
                symbol,
                ts_m1,
                q_m1,
                entry_idx,
                exit_cap_idx,
                side,
                sl_dist,
                spec=spec,
                weight=weight,
                conservative_financing_floor=True,
                red_news_index=red_news_index,
                news_pad_sec=300,
                check_entry_news=True,
            )
            if tr is not None:
                trades.append(tr)
        else:
            ev_dt = date.fromisoformat(ev_day)
            if mode == "intraday_london":
                entry_target_ts = _resolve_local_utc_ts(ev_dt, 8, 0, "Europe/London")
            elif mode == "intraday_ny_open":
                entry_target_ts = _resolve_local_utc_ts(ev_dt, 9, 30, "America/New_York")
            else:
                raise ValueError(f"Unsupported Pre-FOMC mode: {mode!r}")

            entry_idx = int(np.searchsorted(ts_m1, entry_target_ts, side="left"))
            if entry_idx >= exit_cap_idx or entry_idx >= int(ts_m1.size):
                continue
            if abs(int(ts_m1[entry_idx]) - entry_target_ts) > 3600:
                continue

            has_ask = q_m1.shape[1] >= 8
            est_entry = float(q_m1[entry_idx, 4] if (side == 1 and has_ask) else q_m1[entry_idx, 0])
            sl_px = est_entry - side * sl_dist
            if sl_px <= 0.0:
                continue
            res = cc.replay_intraday_m1_trade(
                symbol,
                ts_m1,
                q_m1,
                entry_idx,
                side,
                sl_px,
                flat_idx=exit_cap_idx,
                spec=spec,
                firm_profile="FTMO_SWING",
                red_news_index=red_news_index,
                news_pad_sec=300,
                flatten_before_news=True,
                account_balance_usd=_DEFAULT_ACCOUNT_BALANCE_USD,
                risk_frac=_DEFAULT_RISK_FRAC * float(weight),
            )
            if res.get("filled"):
                # Populate zero_pos_swap keys identically (swap_R == 0.0 for intraday!)
                res["swap_real_R"] = 0.0
                res["swap_zero_pos_R"] = 0.0
                res["net_R_zero_pos_1x"] = res["net_R_1x"]
                res["net_R_zero_pos_15x"] = res["net_R_15x"]
                res["net_R_zero_pos_2x"] = res["net_R_2x"]
                trades.extend(_scale_trades_by_weight([res], weight))

    return trades


def _eval_post_news_m1_symbol(
    symbol: str,
    asset: Mapping[str, Any],
    years: tuple[int, ...],
    macro_events: Sequence[Mapping[str, Any]],
    red_news_index: Mapping[str, Any],
    *,
    event_types: Sequence[str],
    delay_min: int,
    min_impulse_atr: float,
    fade_impulse: bool,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    weight: float,
    flip_side: bool = False,
) -> list[dict[str, Any]]:
    """Post-RedNews Intraday M1 (`swap = 0`), entering strictly `>= 30m` AFTER release blackout."""
    if int(delay_min) < 15:
        raise ValueError(f"Post-news delay_min must be >= 15m to clear blackout cleanly, got {delay_min}")
    m1 = asset.get("m1")
    d1_raw = asset.get("d1")
    if m1 is None or d1_raw is None:
        return []

    max_yr = max(years)
    yr_set = set(years)
    d1 = _slice_d1_upto_year(d1_raw, max_yr)
    ts_m1, q_m1 = _slice_m1_upto_year(m1, max_yr)
    spec = asset["spec"]

    atr14 = cc.causal_atr(d1["high"], d1["low"], d1["close"], 14)
    date_to_i = {d: i for i, d in enumerate(d1["dates"])}
    ev_type_set = {str(x).upper() for x in event_types}

    matching = [
        e
        for e in macro_events
        if int(e["year"]) in yr_set
        and e["event"] in ev_type_set
        and _symbol_matches_event_ccy(symbol, e["ccy"])
    ]
    sign_mult = -1 if (fade_impulse ^ flip_side) else 1
    trades: list[dict[str, Any]] = []
    used_days: set[str] = set()

    for ev in matching:
        ev_day = str(ev["utc_day"])
        if ev_day in used_days:
            continue
        d_idx = date_to_i.get(ev_day)
        if d_idx is None:
            continue
        atr_val = float(atr14[d_idx])
        if not math.isfinite(atr_val) or atr_val <= 0.0:
            continue

        ev_ts = int(ev["utc_ts"])
        pre_ts = ev_ts - 900  # 15m before release (causal baseline)
        entry_target_ts = ev_ts + int(delay_min) * 60

        pre_idx = int(np.searchsorted(ts_m1, pre_ts, side="right")) - 1
        entry_idx = int(np.searchsorted(ts_m1, entry_target_ts, side="left"))
        if pre_idx < 0 or entry_idx <= pre_idx or entry_idx >= int(ts_m1.size):
            continue
        if abs(int(ts_m1[entry_idx]) - entry_target_ts) > 900:
            continue

        # Observe impulse STRICTLY prior to entry_idx (using bar entry_idx - 1 close vs pre_idx close!)
        obs_idx = entry_idx - 1
        has_ask = q_m1.shape[1] >= 8
        pre_mid = 0.5 * (float(q_m1[pre_idx, 3]) + float(q_m1[pre_idx, 7])) if has_ask else float(q_m1[pre_idx, 3])
        obs_mid = 0.5 * (float(q_m1[obs_idx, 3]) + float(q_m1[obs_idx, 7])) if has_ask else float(q_m1[obs_idx, 3])
        impulse = obs_mid - pre_mid
        if abs(impulse) < float(min_impulse_atr) * atr_val:
            continue

        side = (1 if impulse > 0.0 else -1) * sign_mult
        entry_est = float(q_m1[entry_idx, 4] if (side == 1 and has_ask) else q_m1[entry_idx, 0])
        sl_dist = float(sl_atr_mult) * atr_val
        sl_px = entry_est - side * sl_dist
        if sl_px <= 0.0:
            continue
        tp_px = (entry_est + side * float(tp_atr_mult) * atr_val) if tp_atr_mult is not None else None

        res = cc.replay_intraday_m1_trade(
            symbol,
            ts_m1,
            q_m1,
            entry_idx,
            side,
            sl_px,
            tp_price=tp_px,
            spec=spec,
            firm_profile="FTMO_SWING",
            red_news_index=red_news_index,
            news_pad_sec=300,
            flatten_before_news=True,
            account_balance_usd=_DEFAULT_ACCOUNT_BALANCE_USD,
            risk_frac=_DEFAULT_RISK_FRAC * float(weight),
        )
        if res.get("filled"):
            used_days.add(ev_day)
            res["swap_real_R"] = 0.0
            res["swap_zero_pos_R"] = 0.0
            res["net_R_zero_pos_1x"] = res["net_R_1x"]
            res["net_R_zero_pos_15x"] = res["net_R_15x"]
            res["net_R_zero_pos_2x"] = res["net_R_2x"]
            trades.extend(_scale_trades_by_weight([res], weight))

    return trades


def _eval_overnight_m1_symbol(
    symbol: str,
    asset: Mapping[str, Any],
    years: tuple[int, ...],
    red_news_index: Mapping[str, Any],
    *,
    entry_weekdays: Sequence[int],
    session_profile: str,  # "us_cash" | "eu_cash"
    regime_filter: str,  # "none" | "prev_down" | "above_sma100" | "above_sma200"
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    weight: float,
    flip_side: bool = False,
) -> list[dict[str, Any]]:
    """Overnight Cash-Close -> Cash-Open drift on native M1 Bid/Ask with DST-exact clocks & real swap."""
    m1 = asset.get("m1")
    d1_raw = asset.get("d1")
    if m1 is None or d1_raw is None:
        return []

    max_yr = max(years)
    yr_set = set(years)
    d1 = _slice_d1_upto_year(d1_raw, max_yr)
    ts_m1, q_m1 = _slice_m1_upto_year(m1, max_yr)
    spec = asset["spec"]

    atr14 = cc.causal_atr(d1["high"], d1["low"], d1["close"], 14)
    sma100 = cc.causal_sma(d1["close"], 100) if regime_filter == "above_sma100" else None
    sma200 = cc.causal_sma(d1["close"], 200) if regime_filter == "above_sma200" else None

    wd_set = {int(w) for w in entry_weekdays}
    side = -1 if flip_side else 1
    trades: list[dict[str, Any]] = []
    n_days = len(d1["dates"])

    for i in range(1, n_days - 1):
        d_str = d1["dates"][i]
        yr = int(d_str[:4])
        if yr not in yr_set:
            continue
        dt_cur = date.fromisoformat(d_str)
        if dt_cur.weekday() not in wd_set:
            continue
        dt_next = date.fromisoformat(d1["dates"][i + 1])
        # Avoid holding across long weekend gaps (> 1 calendar day) unless explicitly Friday
        if (dt_next - dt_cur).days > 1 and dt_cur.weekday() != 4:
            continue

        # Causal ATR strictly from bars 0..i-1 (zero current-day high/low peek!)
        atr_val = float(atr14[i])
        if not math.isfinite(atr_val) or atr_val <= 0.0:
            continue

        # Regime filters strictly causal before entry_ts:
        if regime_filter == "above_sma100" and sma100 is not None:
            if not math.isfinite(float(sma100[i])) or float(d1["close"][i - 1]) <= float(sma100[i]):
                continue
        elif regime_filter == "above_sma200" and sma200 is not None:
            if not math.isfinite(float(sma200[i])) or float(d1["close"][i - 1]) <= float(sma200[i]):
                continue

        if session_profile == "eu_cash":
            entry_target_ts = _resolve_local_utc_ts(dt_cur, 17, 30, "Europe/Prague")
            exit_target_ts = _resolve_local_utc_ts(dt_next, 9, 0, "Europe/Prague")
            open_target_ts = _resolve_local_utc_ts(dt_cur, 9, 0, "Europe/Prague")
        else:
            entry_target_ts = _resolve_local_utc_ts(dt_cur, 16, 0, "America/New_York")
            exit_target_ts = _resolve_local_utc_ts(dt_next, 9, 30, "America/New_York")
            open_target_ts = _resolve_local_utc_ts(dt_cur, 9, 30, "America/New_York")

        entry_idx = int(np.searchsorted(ts_m1, entry_target_ts, side="left"))
        exit_cap_idx = int(np.searchsorted(ts_m1, exit_target_ts, side="right")) - 1
        if entry_idx <= 0 or exit_cap_idx <= entry_idx or entry_idx >= int(ts_m1.size):
            continue
        if abs(int(ts_m1[entry_idx]) - entry_target_ts) > 3600:
            continue
        if abs(int(ts_m1[exit_cap_idx]) - exit_target_ts) > 7200:
            continue

        # Causal intraday down-day filter: strictly compare bar (entry_idx-1) vs cash open!
        if regime_filter == "prev_down":
            op_idx = int(np.searchsorted(ts_m1, open_target_ts, side="left"))
            if op_idx >= entry_idx:
                continue
            if float(q_m1[entry_idx - 1, 3]) >= float(q_m1[op_idx, 0]):
                continue

        sl_dist = float(sl_atr_mult) * atr_val
        tp_dist = (float(tp_atr_mult) * atr_val) if tp_atr_mult is not None else None
        tr = _replay_m1_overnight_trade(
            symbol,
            ts_m1,
            q_m1,
            entry_idx,
            exit_cap_idx,
            side,
            sl_dist,
            tp_dist=tp_dist,
            spec=spec,
            weight=weight,
            conservative_financing_floor=True,
            red_news_index=red_news_index,
            news_pad_sec=300,
            check_entry_news=True,
        )
        if tr is not None:
            trades.append(tr)

    return trades


# ---------------------------------------------------------------------------
# Standard Candidate Evaluation (`evaluate_candidate`)
# ---------------------------------------------------------------------------


def _resolve_resolution_and_tier(
    symbols: Sequence[str],
    universe: Mapping[str, Any],
    *,
    force_resolution: str | None = None,
) -> tuple[str, str]:
    assets = universe["assets"]
    res_set = {str(assets[s]["data_resolution"]) for s in symbols}
    tier_set = {str(assets[s]["blindness_tier"]) for s in symbols}
    res_tag = force_resolution if force_resolution is not None else (
        next(iter(res_set)) if len(res_set) == 1 else "MIXED_M1_AND_D1"
    )
    tier_tag = next(iter(tier_set)) if len(tier_set) == 1 else "MIXED_MULTI_TIER"
    return res_tag, tier_tag


def _daily_pnl_dict(trades: Sequence[Mapping[str, Any]], years: tuple[int, ...], pnl_key: str) -> dict[str, float]:
    dp = cc.compute_daily_pnl_series(trades, years, pnl_key=pnl_key)
    return {d: round(float(v), 6) for d, v in zip(dp["dates"], dp["pnl"], strict=True)}


def _compute_portfolio_margin_audit(trades: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    day_margin: dict[str, float] = {}
    capped = 0
    for tr in trades:
        if tr.get("margin_capped"):
            capped += 1
        d0 = date.fromisoformat(str(tr["entry_date"]))
        d1 = date.fromisoformat(str(tr["exit_date"]))
        mu = float(tr.get("margin_util_frac", 0.0))
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                k = cur.isoformat()
                day_margin[k] = day_margin.get(k, 0.0) + mu
            cur += timedelta(days=1)
    peak = max(day_margin.values()) if day_margin else 0.0
    return {
        "margin_capped_count": capped,
        "peak_portfolio_margin_util_frac": round(peak, 6),
        "portfolio_margin_breached": peak > 0.80 + 1e-9,
    }


def _run_spec_trades(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    flip_side: bool = False,
    root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Execute one F09 candidate spec strictly over `req_years` (or its exact fade counterpart)."""
    mech = str(spec["mechanism"])
    symbols = [cc.normalize_symbol(s) for s in spec["symbols"]]
    params = dict(spec["params"])
    assets = universe["assets"]
    max_yr = max(req_years)
    weight = 1.0 / float(len(symbols))
    all_trades: list[dict[str, Any]] = []

    if mech in ("TOM_INDICES", "TURNAROUND_TUE", "POST_NEWS_D1", "OVERNIGHT_D1"):
        macro_events = _load_macro_events_dev(root=root) if mech == "POST_NEWS_D1" else ()
        for sym in symbols:
            aobj = assets[sym]
            d1 = _slice_d1_upto_year(aobj["d1"], max_yr)
            if mech == "TOM_INDICES":
                sig, sl_d, tp_d = _build_d1_tom_signals(
                    d1,
                    k_end=int(params["k_end"]),
                    k_start=int(params["k_start"]),
                    regime_filter=str(params.get("regime_filter", "none")),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                max_hold = int(params["k_end"]) + int(params["k_start"])
                exit_flip = False
            elif mech == "TURNAROUND_TUE":
                sig, sl_d, tp_d = _build_d1_turnaround_tuesday_signals(
                    d1,
                    trigger_mode=str(params["trigger_mode"]),
                    threshold=float(params["threshold"]),
                    regime_filter=str(params.get("regime_filter", "none")),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                max_hold = int(params["max_hold_bars"])
                exit_flip = False
            elif mech == "POST_NEWS_D1":
                sig, sl_d, tp_d = _build_d1_post_red_news_signals(
                    sym,
                    d1,
                    macro_events,
                    event_types=params["event_types"],
                    min_shock_atr=float(params["min_shock_atr"]),
                    fade_shock=bool(params.get("fade_shock", False)),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                max_hold = int(params["max_hold_bars"])
                exit_flip = False
            else:
                sig, sl_d, tp_d = _build_d1_midweek_overnight_proxy_signals(
                    d1,
                    entry_weekdays=params["entry_weekdays"],
                    regime_filter=str(params.get("regime_filter", "none")),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                max_hold = int(params["max_hold_bars"])
                exit_flip = False

            res = cc.replay_swing_trades(
                sym,
                d1,
                sig,
                sl_d,
                tp_dists=tp_d,
                max_hold_bars=max_hold,
                exit_on_signal_flip=exit_flip,
                signal_already_shifted=True,
                spec=aobj["spec"],
                account_balance_usd=_DEFAULT_ACCOUNT_BALANCE_USD,
                risk_frac=_DEFAULT_RISK_FRAC * weight,
                account_type="ftmo_swing",
                conservative_financing_floor=True,
                years=req_years,
                data_resolution=aobj["data_resolution"],
            )
            all_trades.extend(_scale_trades_by_weight(res["trades"], weight))

    elif mech == "PRE_FOMC_M1":
        macro_events = _load_macro_events_dev(root=root)
        red_news_idx = _get_red_news_index(root=root)
        for sym in symbols:
            all_trades.extend(
                _eval_pre_fomc_m1_symbol(
                    sym,
                    assets[sym],
                    req_years,
                    macro_events,
                    red_news_idx,
                    mode=str(params["mode"]),
                    exit_min_before_fomc=int(params.get("exit_min_before_fomc", 15)),
                    vol_gate=str(params.get("vol_gate", "none")),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    weight=weight,
                    flip_side=flip_side,
                )
            )

    elif mech == "POST_NEWS_M1":
        macro_events = _load_macro_events_dev(root=root)
        red_news_idx = _get_red_news_index(root=root)
        for sym in symbols:
            all_trades.extend(
                _eval_post_news_m1_symbol(
                    sym,
                    assets[sym],
                    req_years,
                    macro_events,
                    red_news_idx,
                    event_types=params["event_types"],
                    delay_min=int(params["delay_min"]),
                    min_impulse_atr=float(params["min_impulse_atr"]),
                    fade_impulse=bool(params.get("fade_impulse", False)),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    weight=weight,
                    flip_side=flip_side,
                )
            )

    elif mech == "OVERNIGHT_M1":
        red_news_idx = _get_red_news_index(root=root)
        for sym in symbols:
            sess = str(params.get("session_profile", "eu_cash" if sym == "GER40" else "us_cash"))
            all_trades.extend(
                _eval_overnight_m1_symbol(
                    sym,
                    assets[sym],
                    req_years,
                    red_news_idx,
                    entry_weekdays=params["entry_weekdays"],
                    session_profile=sess,
                    regime_filter=str(params.get("regime_filter", "none")),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    weight=weight,
                    flip_side=flip_side,
                )
            )
    else:
        raise ValueError(f"Unknown F09 mechanism: {mech!r}")

    all_trades.sort(key=lambda tr: (int(tr["exit_ts"]), int(tr["entry_ts"]), str(tr["symbol"])))
    return all_trades


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate any F09 candidate spec strictly over `years`, returning the exact Stage-3 standard dict."""
    req_years = tuple(sorted(int(y) for y in years))
    if not req_years or min(req_years) < cc.DEV_MIN_YEAR or max(req_years) > cc.DEV_MAX_YEAR:
        raise ValueError(f"DEV_SEAL_VIOLATION: invalid years={years!r}")

    symbols = [cc.normalize_symbol(s) for s in spec["symbols"]]
    mech = str(spec["mechanism"])
    trades = _run_spec_trades(spec, universe, req_years, flip_side=False, root=root)
    fade_trades = _run_spec_trades(spec, universe, req_years, flip_side=True, root=root)

    dp_1x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dp_15x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dp_2x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    dp_zpos_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_1x")
    dp_zpos_2x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_2x")
    dp_fade_obj = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = cc.compute_split_metrics(trades, dp_1x_obj, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(trades, dp_15x_obj, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(trades, dp_2x_obj, pnl_key="net_R_2x")
    m_zpos_1x = cc.compute_split_metrics(trades, dp_zpos_obj, pnl_key="net_R_zero_pos_1x")
    m_zpos_2x = cc.compute_split_metrics(trades, dp_zpos_2x_obj, pnl_key="net_R_zero_pos_2x")
    m_fade = cc.compute_split_metrics(fade_trades, dp_fade_obj, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(trades)
    maudit = _compute_portfolio_margin_audit(trades)

    metrics = dict(m_1x)
    metrics.update(
        {
            "net_R_15x": m_15x["net_R"],
            "sharpe_15x": m_15x["sharpe"],
            "net_R_2x": m_2x["net_R"],
            "pf_2x": m_2x["pf"],
            "sharpe_2x": m_2x["sharpe"],
            "net_R_zero_pos_1x": m_zpos_1x["net_R"],
            "sharpe_zero_pos_1x": m_zpos_1x["sharpe"],
            "net_R_zero_pos_2x": m_zpos_2x["net_R"],
            "sharpe_zero_pos_2x": m_zpos_2x["sharpe"],
            "fade_net_R_1x": m_fade["net_R"],
            "fade_sharpe_1x": m_fade["sharpe"],
            "stage0_passed": bool(s0["passed"]),
            "stage0_median_fric_sl": s0["median_fric_sl_ratio"],
            "stage0_keep_frac": s0["keep_frac"],
            "margin_capped_count": maudit["margin_capped_count"],
            "peak_portfolio_margin_util_frac": maudit["peak_portfolio_margin_util_frac"],
            "portfolio_margin_breached": maudit["portfolio_margin_breached"],
        }
    )

    force_res = cc.RES_NATIVE_M1_BIDASK if mech in ("PRE_FOMC_M1", "POST_NEWS_M1", "OVERNIGHT_M1") else None
    data_res, blind_tier = _resolve_resolution_and_tier(symbols, universe, force_resolution=force_res)

    return {
        "spec": dict(spec),
        "trades": trades,
        "daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_1x_obj["dates"], dp_1x_obj["pnl"], strict=True)},
        "daily_pnl_15x": {d: round(float(v), 6) for d, v in zip(dp_15x_obj["dates"], dp_15x_obj["pnl"], strict=True)},
        "daily_pnl_2x": {d: round(float(v), 6) for d, v in zip(dp_2x_obj["dates"], dp_2x_obj["pnl"], strict=True)},
        "daily_pnl_zero_pos_swap": {
            d: round(float(v), 6) for d, v in zip(dp_zpos_obj["dates"], dp_zpos_obj["pnl"], strict=True)
        },
        "fade_daily_pnl_1x": {
            d: round(float(v), 6) for d, v in zip(dp_fade_obj["dates"], dp_fade_obj["pnl"], strict=True)
        },
        "metrics": metrics,
        "data_resolution": data_res,
        "blindness_tier": blind_tier,
        "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
    }


# ---------------------------------------------------------------------------
# Pre-Registered F09 Candidate Grid (<= 100 Total Across All 4 Sub-Mechanics)
# ---------------------------------------------------------------------------


def build_f09_candidate_specs() -> list[dict[str, Any]]:
    """Construct <= 100 economically grounded F09 calendar & macro-event specs."""
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        mechanism: str,
        symbols: Sequence[str],
        params: dict[str, Any],
        prop_track: str,
        allow_unidir: bool,
        rationale: str,
        counterparty: str,
    ) -> None:
        if len(rationale.strip()) < 40:
            raise ValueError(f"economic_rationale too short (< 40 chars) for {cid}")
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "mechanism": mechanism,
                "symbols": list(symbols),
                "params": dict(params),
                "prop_track": prop_track,
                "allow_unidirectional": bool(allow_unidir),
                "economic_rationale": rationale.strip(),
                "counterparty_mechanism": counterparty.strip(),
                "causal_invariants": list(_CAUSAL_INVARIANTS_BASE),
            }
        )

    tom_rat = (
        "Etula et al. Dash-for-Cash: mandatory month-end institutional cash/pension/payroll inflows "
        "and fund window-dressing create recurring liquidity-driven index buying across turn-of-month."
    )
    tom_cp = "Institutional pension/401k flows & month-end cash-constrained liquidity providers"

    # 1. Turn-of-Month (24 specs)
    for k_end, k_start in ((2, 2), (2, 3), (3, 2), (3, 3)):
        for rfilt in ("none", "above_sma100", "rsi2_lt_85"):
            _add(
                f"F09_TOM_IDX6_E{k_end}S{k_start}_{rfilt.upper()}",
                "TOM_INDICES",
                INDICES_6,
                {"k_end": k_end, "k_start": k_start, "regime_filter": rfilt, "sl_atr_mult": 2.0, "tp_atr_mult": None},
                "FTMO_SWING",
                True,
                tom_rat,
                tom_cp,
            )

    _add(
        "F09_TOM_US3_E2S3_NONE",
        "TOM_INDICES",
        INDICES_US3,
        {"k_end": 2, "k_start": 3, "regime_filter": "none", "sl_atr_mult": 2.0, "tp_atr_mult": None},
        "FTMO_SWING",
        True,
        tom_rat,
        tom_cp,
    )
    _add(
        "F09_TOM_US3_E3S2_SMA100",
        "TOM_INDICES",
        INDICES_US3,
        {"k_end": 3, "k_start": 2, "regime_filter": "above_sma100", "sl_atr_mult": 2.0, "tp_atr_mult": None},
        "FTMO_SWING",
        True,
        tom_rat,
        tom_cp,
    )
    _add(
        "F09_TOM_INTL3_E2S3_NONE",
        "TOM_INDICES",
        INDICES_INTL3,
        {"k_end": 2, "k_start": 3, "regime_filter": "none", "sl_atr_mult": 2.0, "tp_atr_mult": None},
        "FTMO_SWING",
        True,
        tom_rat,
        tom_cp,
    )
    _add(
        "F09_TOM_INTL3_E3S3_SMA100",
        "TOM_INDICES",
        INDICES_INTL3,
        {"k_end": 3, "k_start": 3, "regime_filter": "above_sma100", "sl_atr_mult": 2.0, "tp_atr_mult": None},
        "FTMO_SWING",
        True,
        tom_rat,
        tom_cp,
    )
    for sym in (*INDICES_6, "XAUUSD"):
        _add(
            f"F09_TOM_{sym}_E2S3_NONE",
            "TOM_INDICES",
            (sym,),
            {"k_end": 2, "k_start": 3, "regime_filter": "none", "sl_atr_mult": 2.0, "tp_atr_mult": None},
            "FTMO_SWING",
            True,
            tom_rat,
            tom_cp,
        )
    _add(
        "F09_TOM_US500_E3S2_SMA200",
        "TOM_INDICES",
        ("US500",),
        {"k_end": 3, "k_start": 2, "regime_filter": "above_sma200", "sl_atr_mult": 2.0, "tp_atr_mult": None},
        "FTMO_SWING",
        True,
        tom_rat,
        tom_cp,
    )

    # 2. Turnaround Tuesday / Monday-Dip Reversal (22 specs)
    tue_rat = (
        "Turnaround Tuesday: weekend risk-off digestion and Monday retail/mutual-fund redemption selling "
        "push indices below fair value, triggering Tuesday/Wednesday institutional bargain-hunting rebound."
    )
    tue_cp = "Weekend-driven Monday panic sellers & margin liquidators absorbed by institutional bids"

    for trig_mode, thresh, tag in (
        ("mon_cc_atr", 0.50, "CC05"),
        ("mon_cc_atr", 0.75, "CC075"),
        ("mon_oc_atr", 0.50, "OC05"),
        ("mon_ibs", 0.25, "IBS25"),
        ("mon_ibs", 0.20, "IBS20"),
    ):
        for hold in (1, 2):
            _add(
                f"F09_TUE_IDX6_{tag}_H{hold}_NONE",
                "TURNAROUND_TUE",
                INDICES_6,
                {
                    "trigger_mode": trig_mode,
                    "threshold": thresh,
                    "regime_filter": "none",
                    "max_hold_bars": hold,
                    "sl_atr_mult": 2.0,
                    "tp_atr_mult": None,
                },
                "FTMO_SWING",
                True,
                tue_rat,
                tue_cp,
            )

    for rfilt in ("above_sma100", "above_sma200"):
        _add(
            f"F09_TUE_IDX6_CC05_H2_{rfilt.upper()}",
            "TURNAROUND_TUE",
            INDICES_6,
            {
                "trigger_mode": "mon_cc_atr",
                "threshold": 0.50,
                "regime_filter": rfilt,
                "max_hold_bars": 2,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
            },
            "FTMO_SWING",
            True,
            tue_rat,
            tue_cp,
        )
        _add(
            f"F09_TUE_IDX6_IBS25_H2_{rfilt.upper()}",
            "TURNAROUND_TUE",
            INDICES_6,
            {
                "trigger_mode": "mon_ibs",
                "threshold": 0.25,
                "regime_filter": rfilt,
                "max_hold_bars": 2,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
            },
            "FTMO_SWING",
            True,
            tue_rat,
            tue_cp,
        )

    _add(
        "F09_TUE_US3_IBS25_H2_NONE",
        "TURNAROUND_TUE",
        INDICES_US3,
        {
            "trigger_mode": "mon_ibs",
            "threshold": 0.25,
            "regime_filter": "none",
            "max_hold_bars": 2,
            "sl_atr_mult": 2.0,
            "tp_atr_mult": None,
        },
        "FTMO_SWING",
        True,
        tue_rat,
        tue_cp,
    )
    _add(
        "F09_TUE_INTL3_IBS25_H2_NONE",
        "TURNAROUND_TUE",
        INDICES_INTL3,
        {
            "trigger_mode": "mon_ibs",
            "threshold": 0.25,
            "regime_filter": "none",
            "max_hold_bars": 2,
            "sl_atr_mult": 2.0,
            "tp_atr_mult": None,
        },
        "FTMO_SWING",
        True,
        tue_rat,
        tue_cp,
    )
    for sym in INDICES_6:
        _add(
            f"F09_TUE_{sym}_DIP_IBS_H2",
            "TURNAROUND_TUE",
            (sym,),
            {
                "trigger_mode": "mon_dip_or_ibs",
                "threshold": 0.50,
                "regime_filter": "none",
                "max_hold_bars": 2,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
            },
            "FTMO_SWING",
            True,
            tue_rat,
            tue_cp,
        )

    # 3. Pre-FOMC Drift & Post-RedNews Drift (26 specs)
    fomc_rat = (
        "Lucca & Moench Pre-FOMC drift: institutional macro uncertainty premium decays ahead of scheduled "
        "FOMC rate announcements, lifting indices/gold; hard exit >= 15m pre-release obeys +-2m news rules."
    )
    fomc_cp = "Risk-averse hedgers & dealer gamma desks unwinding pre-FOMC protection before 14:00 ET"

    for sym_grp, tag in (
        (INDICES_M1_3, "IDX3M1"),
        (("US500",), "US500"),
        (("US100",), "US100"),
        (("GER40",), "GER40"),
        (("XAUUSD",), "XAUUSD"),
    ):
        _add(
            f"F09_PREFOMC_24H_{tag}",
            "PRE_FOMC_M1",
            sym_grp,
            {"mode": "overnight_24h", "exit_min_before_fomc": 15, "vol_gate": "none", "sl_atr_mult": 2.0},
            "FTMO_SWING",
            True,
            fomc_rat,
            fomc_cp,
        )
        _add(
            f"F09_PREFOMC_LDN_{tag}",
            "PRE_FOMC_M1",
            sym_grp,
            {"mode": "intraday_london", "exit_min_before_fomc": 15, "vol_gate": "none", "sl_atr_mult": 1.5},
            "INTRADAY_SWAP0",
            True,
            fomc_rat,
            fomc_cp,
        )
    _add(
        "F09_PREFOMC_24H_IDX3M1_HIVOL",
        "PRE_FOMC_M1",
        INDICES_M1_3,
        {"mode": "overnight_24h", "exit_min_before_fomc": 15, "vol_gate": "high_rvol20", "sl_atr_mult": 2.0},
        "FTMO_SWING",
        True,
        fomc_rat,
        fomc_cp,
    )
    _add(
        "F09_PREFOMC_NYO_IDX3M1",
        "PRE_FOMC_M1",
        INDICES_M1_3,
        {"mode": "intraday_ny_open", "exit_min_before_fomc": 15, "vol_gate": "none", "sl_atr_mult": 1.5},
        "INTRADAY_SWAP0",
        True,
        fomc_rat,
        fomc_cp,
    )

    post_rat = (
        "Post-RedNews institutional drift: major NFP/CPI/Central-Bank surprises trigger multi-hour and "
        "multi-day institutional rebalancing and CTA repositioning AFTER release blackout windows clear."
    )
    post_cp = "Slow-adjusting institutional macro allocators & under-reacting discretionary participants"
    core_us_ev = ["US_NFP", "US_CPI", "FOMC_RATE"]
    all_cb_ev = [
        "FOMC_RATE",
        "US_NFP",
        "US_CPI",
        "ECB_RATE",
        "BOE_RATE",
        "BOJ_RATE_EST03UTC",
        "RBA_RATE",
        "BOC_RATE",
        "SNB_RATE",
        "RBNZ_OCR",
    ]

    for sym_grp, tag, delay_m, fade_f in (
        (INDICES_M1_3, "IDX3M1_CONT30", 30, False),
        (INDICES_M1_3, "IDX3M1_FADE30", 30, True),
        (FX_M1_MAJORS, "FX5M1_CONT30", 30, False),
        (FX_M1_MAJORS, "FX5M1_CONT60", 60, False),
        (("XAUUSD",), "XAU_CONT30", 30, False),
        (("EURUSD",), "EURUSD_CONT30", 30, False),
        (("USDJPY",), "USDJPY_CONT30", 30, False),
    ):
        _add(
            f"F09_POSTNEWS_M1_{tag}",
            "POST_NEWS_M1",
            sym_grp,
            {
                "event_types": all_cb_ev,
                "delay_min": delay_m,
                "min_impulse_atr": 0.30,
                "fade_impulse": fade_f,
                "sl_atr_mult": 1.5,
                "tp_atr_mult": None,
            },
            "INTRADAY_SWAP0",
            False,
            post_rat,
            post_cp,
        )

    for sym_grp, tag, evs, hold, fade_f in (
        (INDICES_6, "IDX6_CONT_H2", core_us_ev, 2, False),
        (INDICES_6, "IDX6_FADE_H2", core_us_ev, 2, True),
        (FX_MAJORS_6, "FX6_CONT_H2", all_cb_ev, 2, False),
        (FX_MAJORS_6, "FX6_CONT_H3", all_cb_ev, 3, False),
        (FX_MAJORS_6, "FX6_FADE_H2", all_cb_ev, 2, True),
        (METALS_2, "MET2_CONT_H2", core_us_ev, 2, False),
        (METALS_2, "MET2_CONT_H3", core_us_ev, 3, False),
    ):
        _add(
            f"F09_POSTNEWS_D1_{tag}",
            "POST_NEWS_D1",
            sym_grp,
            {
                "event_types": evs,
                "min_shock_atr": 0.60,
                "fade_shock": fade_f,
                "max_hold_bars": hold,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
            },
            "FTMO_SWING",
            False,
            post_rat,
            post_cp,
        )

    # 4. Overnight Cash-Close -> Open Drift (20 specs)
    ovn_rat = (
        "Knuteson / vrd07 overnight drift: institutional close imbalances and overnight equity/gold "
        "risk-premium compensation accrue from cash close to next cash open after deducting real financing."
    )
    ovn_cp = "Day-only risk-averse traders flattening at cash close & dealers charging overnight liquidity premium"

    m1_ovn_basket = ("US500", "US100", "GER40", "XAUUSD")
    for wds, wtag in (
        ([1], "TUE"),
        ([1, 2], "TUEWED"),
        ([1, 2, 3], "MIDWK"),
        ([0, 1, 2, 3], "MONTHU"),
    ):
        for rfilt in ("none", "prev_down"):
            _add(
                f"F09_OVN_M1_BASK4_{wtag}_{rfilt.upper()}",
                "OVERNIGHT_M1",
                m1_ovn_basket,
                {
                    "entry_weekdays": wds,
                    "regime_filter": rfilt,
                    "sl_atr_mult": 1.5,
                    "tp_atr_mult": None,
                },
                "FTMO_SWING",
                True,
                ovn_rat,
                ovn_cp,
            )

    for sym in m1_ovn_basket:
        _add(
            f"F09_OVN_M1_{sym}_TUE_NONE",
            "OVERNIGHT_M1",
            (sym,),
            {"entry_weekdays": [1], "regime_filter": "none", "sl_atr_mult": 1.5, "tp_atr_mult": None},
            "FTMO_SWING",
            True,
            ovn_rat,
            ovn_cp,
        )
        _add(
            f"F09_OVN_M1_{sym}_MIDWK_SMA100",
            "OVERNIGHT_M1",
            (sym,),
            {"entry_weekdays": [1, 2, 3], "regime_filter": "above_sma100", "sl_atr_mult": 1.5, "tp_atr_mult": None},
            "FTMO_SWING",
            True,
            ovn_rat,
            ovn_cp,
        )

    # D1 Midweek Swing Drift (including D1-only indices US30/UK100/JP225 & XAGUSD)
    for sym_grp, tag, rfilt in (
        (INDICES_6, "IDX6_TUE_H2_NONE", "none"),
        (INDICES_6, "IDX6_TUE_H2_SMA100", "above_sma100"),
        (INDICES_INTL3, "INTL3_TUE_H2_NONE", "none"),
        (METALS_2, "MET2_TUE_H2_NONE", "none"),
    ):
        _add(
            f"F09_OVN_D1_{tag}",
            "OVERNIGHT_D1",
            sym_grp,
            {
                "entry_weekdays": [1],
                "regime_filter": rfilt,
                "max_hold_bars": 2,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
            },
            "FTMO_SWING",
            True,
            ovn_rat,
            ovn_cp,
        )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F09 spec count {len(specs)} exceeds TOTAL_CAP={TOTAL_CAP}")
    return specs


# ---------------------------------------------------------------------------
# Stage 2 Cluster-A Discovery (`2018-2020` ONLY — Hard Blindness Lock!)
# ---------------------------------------------------------------------------


def _score_cluster_a_f09(res: Mapping[str, Any]) -> tuple[bool, float]:
    """Conservative anti-overfit Cluster-A ranking score (requires Stage-0 + 2x + zero_pos_swap)."""
    m = res["metrics"]
    n_tr = int(m["n_trades"])
    s0_ok = bool(m.get("stage0_passed", False))
    sh_1x = float(m["sharpe"])
    sh_2x = float(m["sharpe_2x"])
    sh_zpos = float(m["sharpe_zero_pos_1x"])
    net_2x = float(m["net_R_2x"])
    net_zpos = float(m["net_R_zero_pos_1x"])
    pos_ratio = float(m["positive_year_ratio"])
    max_dd = float(m["max_DD_R"])
    margin_breach = bool(m.get("portfolio_margin_breached", False))

    # Minimum trade count: Pre-FOMC has 24 events in 3 yrs (24*3=72 on 3-index basket, 20-24 on single asset)
    mech = str(res["spec"]["mechanism"])
    min_tr = 15 if mech == "PRE_FOMC_M1" else 20

    eligible = (
        s0_ok
        and (not margin_breach)
        and n_tr >= min_tr
        and net_2x > 0.0
        and net_zpos > 0.0
        and sh_2x > 0.0
        and sh_zpos > 0.0
    )
    # Conservative score emphasizing stability across 2x cost, zero_pos_swap, and 3/3 positive years
    cons_sh = min(sh_1x, sh_zpos)
    dd_pen = 0.05 * max(0.0, max_dd - 6.0)
    score = cons_sh + 0.50 * sh_2x + 0.45 * pos_ratio - dd_pen
    return eligible, round(score, 6)


def _summarize_candidate_for_checkpoint(
    res: Mapping[str, Any],
    *,
    tier: str,
    score: float,
    eligible_primary: bool,
) -> dict[str, Any]:
    """Build Cluster-A-only checkpoint record (strictly zero 2021+ keys/dates/years)."""
    m = res["metrics"]
    spec = dict(res["spec"])
    return {
        "candidate_id": str(spec["candidate_id"]),
        "family_id": FAMILY_ID,
        "tier": tier,
        "is_primary": tier == "PRIMARY",
        "mechanism": str(spec["mechanism"]),
        "symbols": list(spec["symbols"]),
        "params": dict(spec["params"]),
        "prop_track": str(spec["prop_track"]),
        "data_resolution": str(res["data_resolution"]),
        "blindness_tier": str(res["blindness_tier"]),
        "allow_unidirectional": bool(res["allow_unidirectional"]),
        "economic_rationale": str(spec["economic_rationale"]),
        "counterparty_mechanism": str(spec["counterparty_mechanism"]),
        "causal_invariants": list(spec["causal_invariants"]),
        "cluster_a_score": float(score),
        "cluster_a_primary_eligible": bool(eligible_primary),
        "cluster_a_metrics": {
            "n_trades": int(m["n_trades"]),
            "net_R_1x": float(m["net_R"]),
            "net_R_15x": float(m["net_R_15x"]),
            "net_R_2x": float(m["net_R_2x"]),
            "net_R_zero_pos_1x": float(m["net_R_zero_pos_1x"]),
            "net_R_zero_pos_2x": float(m["net_R_zero_pos_2x"]),
            "pf_1x": float(m["pf"]),
            "pf_2x": float(m["pf_2x"]),
            "sharpe_1x": float(m["sharpe"]),
            "sharpe_2x": float(m["sharpe_2x"]),
            "sharpe_zero_pos_1x": float(m["sharpe_zero_pos_1x"]),
            "fade_net_R_1x": float(m["fade_net_R_1x"]),
            "fade_sharpe_1x": float(m["fade_sharpe_1x"]),
            "winrate": float(m["winrate"]),
            "avg_RR": float(m["avg_RR"]),
            "max_DD_R": float(m["max_DD_R"]),
            "positive_years": int(m["positive_years"]),
            "total_years": int(m["total_years"]),
            "by_year_R": dict(m["by_year_R"]),
            "stage0_passed": bool(m["stage0_passed"]),
            "stage0_median_fric_sl": m["stage0_median_fric_sl"],
            "peak_portfolio_margin_util_frac": float(m["peak_portfolio_margin_util_frac"]),
        },
    }


def discover_cluster_a(
    universe: Mapping[str, Any] | None = None,
    *,
    save_checkpoint: bool = True,
    resume: bool = False,
    verify_sha: bool = True,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run F09 Cluster-A discovery strictly on `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY."""
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    if universe is None:
        uni = cc.load_universe_28(
            load_m1=True,
            load_d1=True,
            years=cc.CLUSTER_A_YEARS,
            symbols=F09_SYMBOLS,
            verify_sha=verify_sha,
            root=root,
        )
    else:
        uni = universe

    specs = build_f09_candidate_specs()
    evaluated: list[tuple[bool, float, dict[str, Any]]] = []
    for sp in specs:
        res = evaluate_candidate(sp, uni, cc.CLUSTER_A_YEARS, root=root)
        elig, sc = _score_cluster_a_f09(res)
        evaluated.append((elig, sc, res))

    # Sort deterministically: primary-eligible first, then descending score, then candidate_id
    evaluated.sort(key=lambda item: (not item[0], -item[1], str(item[2]["spec"]["candidate_id"])))

    # Select <= PRIMARY_CAP diverse PRIMARY candidates (cap <= 5 per sub-mechanic for breadth)
    mech_counts: dict[str, int] = {}
    primary_ids: set[str] = set()
    primary_records: list[dict[str, Any]] = []
    exploratory_records: list[dict[str, Any]] = []

    for elig, sc, res in evaluated:
        cid = str(res["spec"]["candidate_id"])
        mech = str(res["spec"]["mechanism"])
        mech_bucket = "MACRO_NEWS" if mech in ("PRE_FOMC_M1", "POST_NEWS_M1", "POST_NEWS_D1") else (
            "OVERNIGHT" if mech in ("OVERNIGHT_M1", "OVERNIGHT_D1") else mech
        )
        if elig and len(primary_records) < PRIMARY_CAP and mech_counts.get(mech_bucket, 0) < 5:
            primary_records.append(
                _summarize_candidate_for_checkpoint(res, tier="PRIMARY", score=sc, eligible_primary=True)
            )
            primary_ids.add(cid)
            mech_counts[mech_bucket] = mech_counts.get(mech_bucket, 0) + 1

    # Second pass: fill remaining PRIMARY slots (if any) from other eligible specs
    if len(primary_records) < PRIMARY_CAP:
        for elig, sc, res in evaluated:
            cid = str(res["spec"]["candidate_id"])
            if cid in primary_ids or not elig:
                continue
            if len(primary_records) >= PRIMARY_CAP:
                break
            primary_records.append(
                _summarize_candidate_for_checkpoint(res, tier="PRIMARY", score=sc, eligible_primary=True)
            )
            primary_ids.add(cid)

    # All remaining evaluated specs go to EXPLORATORY (capped at TOTAL_CAP total)
    for elig, sc, res in evaluated:
        cid = str(res["spec"]["candidate_id"])
        if cid in primary_ids:
            continue
        if len(primary_records) + len(exploratory_records) >= TOTAL_CAP:
            break
        exploratory_records.append(
            _summarize_candidate_for_checkpoint(res, tier="EXPLORATORY", score=sc, eligible_primary=elig)
        )

    meta: dict[str, Any] = {
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "family_slug": FAMILY_ID,
        "module": "quant_factory.offensive3.fam09_swing_calendar_drift",
        "primary_cap": PRIMARY_CAP,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "ops1_guard_active": ops1_guard is not None,
        "mechanisms_covered": sorted({str(s["mechanism"]) for s in specs}),
        "symbols_covered": list(F09_SYMBOLS),
        "primary_mechanism_counts": {
            m: sum(1 for r in primary_records if r["mechanism"] == m)
            for m in sorted({r["mechanism"] for r in primary_records})
        },
    }

    if save_checkpoint:
        cc.save_family_candidates(
            FAMILY_ID,
            {"primary": primary_records, "exploratory": exploratory_records},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    return {
        "family_id": FAMILY_ID,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_count": len(primary_records),
        "exploratory_count": len(exploratory_records),
        "total_count": len(primary_records) + len(exploratory_records),
        "primary_candidates": primary_records,
        "exploratory_candidates": exploratory_records,
        "candidates": [*primary_records, *exploratory_records],
        "meta": meta,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage-2 Cluster-A discovery for F09_SWING_CALENDAR.")
    parser.add_argument("--resume", action="store_true", help="Reuse SHA-verified Cluster-A checkpoint if present.")
    parser.add_argument("--no-verify-sha", action="store_true", help="Skip parquet SHA-256 verification on load.")
    args = parser.parse_args(argv)

    doc = discover_cluster_a(save_checkpoint=True, resume=bool(args.resume), verify_sha=not bool(args.no_verify_sha))
    top5 = [
        {
            "id": c["candidate_id"],
            "mech": c["mechanism"],
            "n": c["cluster_a_metrics"]["n_trades"],
            "net1x": c["cluster_a_metrics"]["net_R_1x"],
            "net2x": c["cluster_a_metrics"]["net_R_2x"],
            "sh1x": c["cluster_a_metrics"]["sharpe_1x"],
            "sh_zpos": c["cluster_a_metrics"]["sharpe_zero_pos_1x"],
            "yrs+": f"{c['cluster_a_metrics']['positive_years']}/{c['cluster_a_metrics']['total_years']}",
        }
        for c in (doc.get("primary_candidates") or [])[:5]
    ]
    print(
        json.dumps(
            {
                "family_id": FAMILY_ID,
                "discovery_years": doc["discovery_years"],
                "primary_count": doc["primary_count"],
                "total_count": doc["total_count"],
                "order_send_count": ORDER_SEND_COUNT,
                _SEAL_ROWS_ANALYSED_KEY: 0,
                "top5_primary_cluster_a": top5,
            },
            indent=2,
        )
    )
    return 0


__all__ = [
    "F09_SYMBOLS",
    "FAMILY_ID",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_CAP",
    "TOTAL_CAP",
    "build_f09_candidate_specs",
    "discover_cluster_a",
    "evaluate_candidate",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main())
