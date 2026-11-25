"""Pass 28: Final Pre-Holdout Orthogonal Discovery (m_total=40), Official Red-News Guard (±5m) Audit
& Exact 3-6 Month Short-Horizon Passing Frontier (FTMO 2-Step, The5ers High Stakes 2-Step & Hyper Growth 1-Step).

Strictly causal Development 2018-2024 (holdout_rows = 0, OrderSend = 0, network_calls = 0).
"""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from math import fsum
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass18_opensource_non_usdjpy as p18
import pass19_us500_supertrend_yencross as p19
import pass22_gbpusd_volhigh_3engine as p22
import pass23_ftmo_lifecycle_sim as p23l
import pass23_xau_indices_discovery as p23d
import pass24_mtf_new_archetypes as p24
import pass26_cross_asset_rs as p26
import pass27_portfolio_m1_phase_audit as p27
import whitebox_discovery as wbd
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "a9de160e0de945d37804025166fb1743e7f7bd1e"
SEED = 20261123
MC_DRAWS = 1000
BOOTSTRAP_PATHS = 2000

NY_TZ = ZoneInfo("America/New_York")
BERLIN_TZ = ZoneInfo("Europe/Berlin")
LONDON_TZ = ZoneInfo("Europe/London")

# ==============================================================================
# OFFICIAL PRIMARY-SOURCE MACRO CALENDAR (2018-2024): FOMC + BLS CPI + BLS NFP
# ==============================================================================

OFFICIAL_FOMC_DATES = (
    # 2018
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13", "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020
    "2020-01-29", "2020-03-18", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
)

OFFICIAL_US_CPI_DATES = (
    # 2018
    "2018-01-12", "2018-02-14", "2018-03-13", "2018-04-12", "2018-05-10", "2018-06-12",
    "2018-07-12", "2018-08-10", "2018-09-13", "2018-10-11", "2018-11-14", "2018-12-11",
    # 2019
    "2019-01-11", "2019-02-13", "2019-03-12", "2019-04-10", "2019-05-10", "2019-06-12",
    "2019-07-11", "2019-08-13", "2019-09-12", "2019-10-10", "2019-11-13", "2019-12-11",
    # 2020
    "2020-01-14", "2020-02-13", "2020-03-10", "2020-04-10", "2020-05-12", "2020-06-10",
    "2020-07-14", "2020-08-12", "2020-09-11", "2020-10-13", "2020-11-12", "2020-12-10",
    # 2021
    "2021-01-13", "2021-02-10", "2021-03-10", "2021-04-13", "2021-05-12", "2021-06-10",
    "2021-07-13", "2021-08-11", "2021-09-14", "2021-10-13", "2021-11-10", "2021-12-10",
    # 2022
    "2022-01-12", "2022-02-10", "2022-03-10", "2022-04-12", "2022-05-11", "2022-06-10",
    "2022-07-13", "2022-08-10", "2022-09-13", "2022-10-13", "2022-11-10", "2022-12-13",
    # 2023
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12", "2023-05-10", "2023-06-13",
    "2023-07-12", "2023-08-10", "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    # 2024
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15", "2024-06-12",
    "2024-07-11", "2024-08-14", "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
)


def _local_ts(day_iso: str, hour: int, minute: int, tz: ZoneInfo) -> int:
    d = date.fromisoformat(day_iso)
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz).timestamp())


def build_official_red_news_calendar(*, include_uk_proxy: bool = False) -> dict[str, list[tuple[int, str]]]:
    """Build exact UTC timestamps for official US Red News (FOMC 14:00 ET, CPI 08:30 ET, NFP 1st-Fri 08:30 ET).

    Returns map: day_iso -> list of (utc_ts_sec, currency_code).
    """
    events = defaultdict(list)
    for d in OFFICIAL_FOMC_DATES:
        events[d].append((_local_ts(d, 14, 0, NY_TZ), "USD"))
    for d in OFFICIAL_US_CPI_DATES:
        events[d].append((_local_ts(d, 8, 30, NY_TZ), "USD"))
    # BLS NFP: 1st Friday of each month 2018-2024 at 08:30 ET
    for yr in range(2018, 2025):
        for mo in range(1, 13):
            d1 = date(yr, mo, 1)
            fri = d1 + timedelta(days=(4 - d1.weekday()) % 7)
            # If Jan 1 is Friday (2021-01-01), NFP shifts to 2nd Friday (2021-01-08)
            if mo == 1 and fri.day == 1:
                fri += timedelta(days=7)
            events[fri.isoformat()].append((_local_ts(fri.isoformat(), 8, 30, NY_TZ), "USD"))
            if include_uk_proxy:
                # Conservative UK CPI proxy: 3rd Wednesday at 07:00 London
                w1 = d1 + timedelta(days=(2 - d1.weekday()) % 7)
                uk_cpi = w1 + timedelta(days=14)
                events[uk_cpi.isoformat()].append((_local_ts(uk_cpi.isoformat(), 7, 0, LONDON_TZ), "GBP"))
                # Conservative BoE MPC proxy: 1st Thursday of BoE meeting months at 12:00 London
                if mo in (2, 3, 5, 6, 8, 9, 11, 12):
                    th1 = d1 + timedelta(days=(3 - d1.weekday()) % 7)
                    events[th1.isoformat()].append((_local_ts(th1.isoformat(), 12, 0, LONDON_TZ), "GBP"))
    for dk in events:
        events[dk].sort()
    return dict(events)


def asset_currencies(asset: str) -> tuple[str, ...]:
    if asset in ("US100", "US500", "XAUUSD"):
        return ("USD",)
    if asset == "GER40":
        return ("EUR",)
    if len(asset) == 6:
        return (asset[:3], asset[3:])
    return ("USD",)


def apply_red_news_guard_to_tape(
    tape: dict[str, tuple],
    news_cal: dict[str, list[tuple[int, str]]],
    *,
    mode: str = "FLATTEN_5M",
    pad_sec: int = 300,
) -> tuple[dict[str, tuple], dict]:
    """Apply strictly causal ±pad_sec red-news compliance guard to an exact M1 trade tape.

    - FLATTEN_5M: blocks any entry inside [t_news - pad_sec, t_news + pad_sec]; forcibly flattens any open
      affected trade at the last M1 bar <= (t_news - pad_sec) so ZERO SL/TP can trigger inside ±2 min.
    - SKIP_DAY: skips affected trades on any red-news day.
    """
    out = {}
    stats = {"total_in": len(tape), "kept_untouched": 0, "blocked_entry": 0, "flattened_pre_news": 0, "skipped_day": 0}
    for dk, (row, stamps, marks) in tape.items():
        asset = row.get("asset", "USDJPY")
        ccys = set(asset_currencies(asset))
        day_ev = [ts for ts, c in news_cal.get(dk, []) if c in ccys]
        if not day_ev:
            out[dk] = (row, stamps, marks)
            stats["kept_untouched"] += 1
            continue

        if mode == "SKIP_DAY":
            stats["skipped_day"] += 1
            continue

        t_ent = int(stamps[0])
        t_ext = int(row["exit"])
        # Check entry inside ±pad_sec window
        if any(abs(t_ent - tn) <= pad_sec for tn in day_ev):
            stats["blocked_entry"] += 1
            continue

        # Check earliest news event that occurs while trade is still open (after entry)
        cut_events = [tn - pad_sec for tn in day_ev if t_ent < (tn - pad_sec) < t_ext]
        if not cut_events:
            out[dk] = (row, stamps, marks)
            stats["kept_untouched"] += 1
            continue

        t_cut = min(cut_events)
        k = int(stamps.searchsorted(t_cut, side="right")) - 1
        if k < 0:
            stats["blocked_entry"] += 1
            continue
        new_stamps = stamps[:k + 1].copy()
        new_marks = marks[:k + 1].copy()
        term_pnl = float(new_marks[-1, 3])
        new_marks[-1, 3] = term_pnl
        new_row = {
            **row,
            "exit": int(new_stamps[-1]) + 60,
            "at_open": False,
            "reason": "NEWS_PRE_FLATTEN",
            "net_usd_per_lot": term_pnl,
            "net_R": float(term_pnl / row["stop_risk_with_cost_usd"]),
        }
        out[dk] = (new_row, new_stamps, new_marks)
        stats["flattened_pre_news"] += 1
    return out, stats


# ==============================================================================
# TRACK 1: FINAL PRE-HOLDOUT ORTHOGONAL DISCOVERY (m_total = 40, ZERO LOOKAHEAD)
# ==============================================================================

def _compute_vol_ratio_map(bundle: dict) -> dict[str, float]:
    """Causal prior-day ATR5 / ATR20 compression ratio per day_iso (strictly completed D1 bars)."""
    # Compute daily range series from bundle["days"] chronologically
    days = bundle["days"]
    times, quotes = bundle["times"], bundle["quotes"]
    rngs = []
    for d in days:
        q = quotes[d["fi"]:d["flat_idx"] + 1]
        if len(q) > 0:
            rngs.append(float(q[:, 1].max() - q[:, 2].min()))
        else:
            rngs.append(np.nan)
    rngs = np.asarray(rngs, dtype=np.float64)
    out = {}
    for i in range(21, len(days)):
        r5 = rngs[i - 5:i]
        r20 = rngs[i - 20:i]
        if np.all(np.isfinite(r20)) and r20.mean() > 1e-9:
            out[days[i]["day"]] = float(r5.mean() / r20.mean())
    return out


def _calendar_tom_and_me_sets(all_days: list[str]) -> tuple[set[str], set[str]]:
    """Purely calendar-known Turn-of-Month (last 2 + first 2 trading days) and Month-End (last 2 days)."""
    by_ym = defaultdict(list)
    for dk in sorted(all_days):
        by_ym[dk[:7]].append(dk)
    tom, me = set(), set()
    for ym, dlist in by_ym.items():
        for d in dlist[:2]:
            tom.add(d)
        for d in dlist[-2:]:
            tom.add(d)
            me.add(d)
    return tom, me


def _session_cont_window(bundle: dict, d: dict, ts_ms: int, ts_me: int, ts_we: int, *, min_move: float, mode: str, sl_atr: float, close_pct: float = 0.70):
    times, quotes = bundle["times"], bundle["quotes"]
    m0 = int(times.searchsorted(ts_ms, side="left"))
    m1 = int(times.searchsorted(ts_me, side="left"))
    if m1 - m0 < 20:
        return None, None
    mq = quotes[m0:m1]
    mo, mc = float(mq[0, 0]), float(mq[-1, 3])
    mh, ml = float(mq[:, 1].max()), float(mq[:, 2].min())
    mrng = mh - ml
    a_val = d["atr"]
    if mrng <= 1e-9 or abs(mc - mo) < min_move * a_val:
        return None, None
    pos = (mc - ml) / mrng
    if mc > mo and pos >= close_pct:
        side = 1
    elif mc < mo and pos <= (1.0 - close_pct):
        side = -1
    else:
        return None, None
    if mode == "BRK":
        return p24._scan_stop_breakout(bundle, d, ts_me, ts_we, mh, ml, sl_atr * a_val, ok_b=(side == 1), ok_s=(side == -1))
    return p26.market_entry_at(bundle, d, ts_me, side, sl_atr)


def build_pass28_catalog() -> list[dict]:
    """Fixed pre-registered 40-spec catalog across 5 orthogonal families (swap=0, zero repeat of closed families)."""
    return [
        # Family 1: IDX_INTRADAY_STRUCTURE (10)
        {"id": "GER40_EU_MORN_CONT_35", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "GER40_MORN", "thr": 0.35, "sl_atr": 0.65},
        {"id": "GER40_EU_MORN_CONT_45", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "GER40_MORN", "thr": 0.45, "sl_atr": 0.65},
        {"id": "GER40_POST_USOPEN_CONT_30", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "GER40_USOPEN", "thr": 0.30, "sl_atr": 0.65},
        {"id": "US100_POST10ET_BRK_30", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "US100_POST10", "thr": 0.30, "sl_atr": 0.65},
        {"id": "US100_POST10ET_BRK_45", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "US100_POST10", "thr": 0.45, "sl_atr": 0.65},
        {"id": "US500_POST10ET_US100_CONF", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "US500_POST10_CONF", "thr": 0.30, "sl_atr": 0.65},
        {"id": "US100_POWER_HOUR_1400_35", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "US100_PH14", "thr": 0.35, "sl_atr": 0.65},
        {"id": "US500_POWER_HOUR_1400_35", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "US500_PH14", "thr": 0.35, "sl_atr": 0.65},
        {"id": "US100_RS_GER40_LEAD_1130", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "US100_RS_GER40", "thr": 0.30, "sl_atr": 0.75},
        {"id": "GER40_RS_EUR_ALIGN_1130", "fam": "IDX_INTRADAY_STRUCTURE", "kind": "GER40_EUR_ALIGN", "thr": 0.30, "sl_atr": 0.65},
        # Family 2: GOLD_INSTITUTIONAL_SESSIONS (8)
        {"id": "XAU_LON_TO_NY_CONT_35", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "LON_NY_BRK", "thr": 0.35, "sl_atr": 0.75},
        {"id": "XAU_LON_TO_NY_CONT_50", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "LON_NY_BRK", "thr": 0.50, "sl_atr": 0.75},
        {"id": "XAU_LON_TO_NY_MKT_40", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "LON_NY_MKT", "thr": 0.40, "sl_atr": 0.75},
        {"id": "XAU_COMEX_DRIVE_CONT_35", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "COMEX_BRK", "thr": 0.35, "sl_atr": 0.75},
        {"id": "XAU_COMEX_DRIVE_MKT_35", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "COMEX_MKT", "thr": 0.35, "sl_atr": 0.75},
        {"id": "XAU_RS_VS_US100_1130", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "XAU_VS_US100", "thr": 0.40, "sl_atr": 0.75},
        {"id": "XAU_POST_LON_PMFIX_1500", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "LON_PMFIX", "thr": 0.50, "sl_atr": 0.75},
        {"id": "XAU_VOL_COMP_EXP_80", "fam": "GOLD_INSTITUTIONAL_SESSIONS", "kind": "XAU_COMP80", "thr": 0.80, "sl_atr": 0.75},
        # Family 3: RISK_REGIME_CROSS_ASSET (8)
        {"id": "AUDUSD_RISK_ON_1130ET", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "AUD_RISKON", "thr": 0.30, "sl_atr": 0.75},
        {"id": "EURJPY_RISK_ON_1130ET", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "EJ_RISKON", "thr": 0.30, "sl_atr": 0.75},
        {"id": "GBPJPY_RISK_ON_1130ET", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "GJ_RISKON", "thr": 0.30, "sl_atr": 0.75},
        {"id": "USDCAD_RISK_OFF_1130ET", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "CAD_RISKOFF", "thr": 0.30, "sl_atr": 0.75},
        {"id": "EURUSD_LON_GER40_CONF_10U", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "EU_GER_10U", "thr": 0.30, "sl_atr": 0.75},
        {"id": "GBPUSD_LON_GER40_CONF_10U", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "GU_GER_10U", "thr": 0.30, "sl_atr": 0.75},
        {"id": "USDJPY_NY_RISK_FLOW_10ET", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "UJ_NY_10ET", "thr": 0.25, "sl_atr": 0.75},
        {"id": "FX_USD_BASKET_08U_Z35", "fam": "RISK_REGIME_CROSS_ASSET", "kind": "USD_BSK_08U", "thr": 0.35, "sl_atr": 0.75},
        # Family 4: CALENDAR_INTRADAY_FLOWS (6)
        {"id": "US100_TOM_INTRADAY_LONG", "fam": "CALENDAR_INTRADAY_FLOWS", "kind": "TOM_US100", "thr": 0.0, "sl_atr": 0.75, "min_a": 30},
        {"id": "US500_TOM_INTRADAY_LONG", "fam": "CALENDAR_INTRADAY_FLOWS", "kind": "TOM_US500", "thr": 0.0, "sl_atr": 0.75, "min_a": 30},
        {"id": "XAU_TOM_INTRADAY_LONG", "fam": "CALENDAR_INTRADAY_FLOWS", "kind": "TOM_XAU", "thr": 0.0, "sl_atr": 0.75, "min_a": 30},
        {"id": "US100_TOM_CONFIRM_10ET", "fam": "CALENDAR_INTRADAY_FLOWS", "kind": "TOM_US100_10ET", "thr": 0.10, "sl_atr": 0.75, "min_a": 25},
        {"id": "US500_MON_TUE_CONT_35", "fam": "CALENDAR_INTRADAY_FLOWS", "kind": "US500_MONTUE", "thr": 0.35, "sl_atr": 0.65, "min_a": 30},
        {"id": "FX_MONTH_END_USD_FIX_14L", "fam": "CALENDAR_INTRADAY_FLOWS", "kind": "ME_USD_14L", "thr": 0.20, "sl_atr": 0.75, "min_a": 25},
        # Family 5: VOL_COMPRESSION_REGIME_EXP (8)
        {"id": "US100_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "US100", "thr": 0.75, "sl_atr": 0.75},
        {"id": "US500_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "US500", "thr": 0.75, "sl_atr": 0.75},
        {"id": "GER40_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "GER40", "thr": 0.75, "sl_atr": 0.75},
        {"id": "EURUSD_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "EURUSD", "thr": 0.75, "sl_atr": 0.75},
        {"id": "AUDUSD_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "AUDUSD", "thr": 0.75, "sl_atr": 0.75},
        {"id": "USDCAD_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "USDCAD", "thr": 0.75, "sl_atr": 0.75},
        {"id": "EURJPY_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "EURJPY", "thr": 0.75, "sl_atr": 0.75},
        {"id": "GBPUSD_VOLCOMP_EXP75", "fam": "VOL_COMPRESSION_REGIME_EXP", "asset": "GBPUSD", "thr": 0.75, "sl_atr": 0.75},
    ]


def eval_p28_spec(bundles: dict, day_maps: dict, all_days: list[str], vol_ratios: dict, tom_set: set[str], me_set: set[str], cfg: dict):
    fam = cfg["fam"]
    thr = float(cfg["thr"])
    sl_atr = float(cfg["sl_atr"])
    trs, fds = [], []

    if fam == "IDX_INTRADAY_STRUCTURE":
        kind = cfg["kind"]
        for dk in all_days:
            if kind == "GER40_MORN":
                if dk not in day_maps["GER40"]:
                    continue
                d = day_maps["GER40"][dk]
                ts_ms = _local_ts(dk, 9, 0, BERLIN_TZ)
                ts_me = _local_ts(dk, 11, 30, BERLIN_TZ)
                ts_we = _local_ts(dk, 17, 0, BERLIN_TZ)
                tr, fd = _session_cont_window(bundles["GER40"], d, ts_ms, ts_me, ts_we, min_move=thr, mode="BRK", sl_atr=sl_atr)
            elif kind == "GER40_USOPEN":
                if dk not in day_maps["GER40"] or dk not in day_maps["US100"]:
                    continue
                gd, u100 = day_maps["GER40"][dk], day_maps["US100"][dk]
                ts_s = _local_ts(dk, 9, 0, BERLIN_TZ)
                ts_e = u100["day_sec"] + 30 * 60  # 10:00 ET
                zg = p26.causal_z_return(bundles["GER40"], ts_s, ts_e, gd["atr"])
                zu = p26.causal_z_return(bundles["US100"], u100["day_sec"], ts_e, u100["atr"])
                if zg is None or zu is None or abs(zg) < thr or abs(zu) < 0.20 or zg * zu <= 0:
                    continue
                tr, fd = p26.market_entry_at(bundles["GER40"], gd, ts_e, 1 if zg > 0 else -1, sl_atr)
            elif kind == "US100_POST10":
                if dk not in day_maps["US100"]:
                    continue
                d = day_maps["US100"][dk]
                tr, fd = _session_cont_window(bundles["US100"], d, d["day_sec"], d["day_sec"] + 30 * 60, d["day_sec"] + 360 * 60, min_move=thr, mode="BRK", sl_atr=sl_atr, close_pct=0.65)
            elif kind == "US500_POST10_CONF":
                if dk not in day_maps["US500"] or dk not in day_maps["US100"]:
                    continue
                d5, d1 = day_maps["US500"][dk], day_maps["US100"][dk]
                ts_e = d5["day_sec"] + 30 * 60
                z1 = p26.causal_z_return(bundles["US100"], d1["day_sec"], ts_e, d1["atr"])
                z5 = p26.causal_z_return(bundles["US500"], d5["day_sec"], ts_e, d5["atr"])
                if z1 is None or z5 is None or abs(z1) < thr or z1 * z5 <= 0:
                    continue
                side = 1 if z1 > 0 else -1
                m0 = int(bundles["US500"]["times"].searchsorted(d5["day_sec"], side="left"))
                m1 = int(bundles["US500"]["times"].searchsorted(ts_e, side="left"))
                if m1 - m0 < 15:
                    continue
                mq = bundles["US500"]["quotes"][m0:m1]
                tr, fd = p24._scan_stop_breakout(bundles["US500"], d5, ts_e, d5["day_sec"] + 360 * 60, float(mq[:, 1].max()), float(mq[:, 2].min()), sl_atr * d5["atr"], ok_b=(side == 1), ok_s=(side == -1))
            elif kind in ("US100_PH14", "US500_PH14"):
                a = "US100" if "US100" in kind else "US500"
                if dk not in day_maps[a]:
                    continue
                d = day_maps[a][dk]
                tr, fd = _session_cont_window(bundles[a], d, d["day_sec"], d["day_sec"] + 270 * 60, d["day_sec"] + 375 * 60, min_move=thr, mode="BRK", sl_atr=sl_atr, close_pct=0.70)
            elif kind == "US100_RS_GER40":
                if dk not in day_maps["US100"] or dk not in day_maps["GER40"]:
                    continue
                d1, dg = day_maps["US100"][dk], day_maps["GER40"][dk]
                ts_s, ts_e = d1["day_sec"], d1["day_sec"] + 120 * 60
                z1 = p26.causal_z_return(bundles["US100"], ts_s, ts_e, d1["atr"])
                zg = p26.causal_z_return(bundles["GER40"], ts_s, ts_e, dg["atr"])
                if z1 is None or zg is None:
                    continue
                diff = z1 - zg
                if abs(diff) < thr or (z1 * diff <= 0):
                    continue
                tr, fd = p26.market_entry_at(bundles["US100"], d1, ts_e, 1 if diff > 0 else -1, sl_atr)
            elif kind == "GER40_EUR_ALIGN":
                if dk not in day_maps["GER40"] or dk not in day_maps["EURUSD"]:
                    continue
                dg, de = day_maps["GER40"][dk], day_maps["EURUSD"][dk]
                ts_s = _local_ts(dk, 9, 0, BERLIN_TZ)
                ts_e = _local_ts(dk, 11, 30, BERLIN_TZ)
                zg = p26.causal_z_return(bundles["GER40"], ts_s, ts_e, dg["atr"])
                ze = p26.causal_z_return(bundles["EURUSD"], ts_s, ts_e, de["atr"])
                if zg is None or ze is None or abs(zg) < thr or abs(ze) < 0.20 or zg * ze <= 0:
                    continue
                tr, fd = p26.market_entry_at(bundles["GER40"], dg, ts_e, 1 if zg > 0 else -1, sl_atr)
            else:
                continue
            if tr and fd:
                trs.append(tr); fds.append(fd)

    elif fam == "GOLD_INSTITUTIONAL_SESSIONS":
        kind = cfg["kind"]
        xb = bundles["XAUUSD"]
        for dk in all_days:
            if dk not in day_maps["XAUUSD"]:
                continue
            d = day_maps["XAUUSD"][dk]
            dsec = d["day_sec"]
            if kind in ("LON_NY_BRK", "LON_NY_MKT"):
                tr, fd = _session_cont_window(xb, d, dsec + 7 * 3600, dsec + 12 * 3600, dsec + 20 * 3600, min_move=thr, mode="BRK" if "BRK" in kind else "MKT", sl_atr=sl_atr)
            elif kind in ("COMEX_BRK", "COMEX_MKT"):
                ts_ms = _local_ts(dk, 8, 20, NY_TZ)
                ts_me = _local_ts(dk, 10, 30, NY_TZ)
                ts_we = _local_ts(dk, 15, 30, NY_TZ)
                tr, fd = _session_cont_window(xb, d, ts_ms, ts_me, ts_we, min_move=thr, mode="BRK" if "BRK" in kind else "MKT", sl_atr=sl_atr)
            elif kind == "XAU_VS_US100":
                if dk not in day_maps["US100"]:
                    continue
                u1 = day_maps["US100"][dk]
                ts_s, ts_e = u1["day_sec"], u1["day_sec"] + 120 * 60
                zx = p26.causal_z_return(xb, ts_s, ts_e, d["atr"])
                zu = p26.causal_z_return(bundles["US100"], ts_s, ts_e, u1["atr"])
                if zx is None or zu is None:
                    continue
                diff = zx - zu
                if abs(diff) < thr or (zx * diff <= 0):
                    continue
                tr, fd = p26.market_entry_at(xb, d, ts_e, 1 if diff > 0 else -1, sl_atr)
            elif kind == "LON_PMFIX":
                ts_fix = _local_ts(dk, 15, 0, LONDON_TZ)
                zx = p26.causal_z_return(xb, dsec + 7 * 3600, ts_fix, d["atr"])
                if zx is None or abs(zx) < thr:
                    continue
                tr, fd = p26.market_entry_at(xb, d, ts_fix, 1 if zx > 0 else -1, sl_atr)
            elif kind == "XAU_COMP80":
                vr = vol_ratios["XAUUSD"].get(dk)
                if vr is None or vr >= 0.85:
                    continue
                open_0 = float(xb["quotes"][d["fi"], 0])
                tr, fd = p24._scan_stop_breakout(xb, d, dsec + 7 * 3600, dsec + 17 * 3600, open_0 + thr * d["atr"], open_0 - thr * d["atr"], sl_atr * d["atr"])
            else:
                continue
            if tr and fd:
                trs.append(tr); fds.append(fd)

    elif fam == "RISK_REGIME_CROSS_ASSET":
        kind = cfg["kind"]
        if kind == "USD_BSK_08U":
            return p26.eval_fx_cs_momentum(bundles, day_maps, all_days, entry_h=8, lb_h=6, min_z=thr, usd_basket_only=True, sl_atr=sl_atr)
        for dk in all_days:
            if kind in ("AUD_RISKON", "EJ_RISKON", "GJ_RISKON", "CAD_RISKOFF"):
                tgt = {"AUD_RISKON": "AUDUSD", "EJ_RISKON": "EURJPY", "GJ_RISKON": "GBPJPY", "CAD_RISKOFF": "USDCAD"}[kind]
                if dk not in day_maps[tgt] or dk not in day_maps["US100"] or dk not in day_maps["GER40"] or dk not in day_maps["USDJPY"]:
                    continue
                u1 = day_maps["US100"][dk]
                ts_s, ts_e = u1["day_sec"], u1["day_sec"] + 120 * 60
                zu = p26.causal_z_return(bundles["US100"], ts_s, ts_e, u1["atr"])
                zg = p26.causal_z_return(bundles["GER40"], ts_s, ts_e, day_maps["GER40"][dk]["atr"])
                zj = p26.causal_z_return(bundles["USDJPY"], ts_s, ts_e, day_maps["USDJPY"][dk]["atr"])
                if zu is None or zg is None or zj is None:
                    continue
                if kind == "AUD_RISKON":
                    if abs(zu) < thr or abs(zg) < 0.20 or zu * zg <= 0:
                        continue
                    side = 1 if zu > 0 else -1
                elif kind in ("EJ_RISKON", "GJ_RISKON"):
                    if abs(zu) < thr or abs(zj) < 0.20 or zu * zj <= 0:
                        continue
                    side = 1 if zu > 0 else -1
                else:
                    if abs(zu) < thr or abs(zg) < 0.20 or zu * zg <= 0:
                        continue
                    # Risk-on -> CAD strengthens -> SELL USDCAD; Risk-off -> BUY USDCAD
                    side = -1 if zu > 0 else 1
                tr, fd = p26.market_entry_at(bundles[tgt], day_maps[tgt][dk], ts_e, side, sl_atr)
            elif kind in ("EU_GER_10U", "GU_GER_10U"):
                tgt = "EURUSD" if "EU_" in kind else "GBPUSD"
                if dk not in day_maps[tgt] or dk not in day_maps["GER40"]:
                    continue
                dt, dg = day_maps[tgt][dk], day_maps["GER40"][dk]
                ts_s, ts_e = dt["day_sec"] + 7 * 3600, dt["day_sec"] + 10 * 3600
                zt = p26.causal_z_return(bundles[tgt], ts_s, ts_e, dt["atr"])
                zg = p26.causal_z_return(bundles["GER40"], ts_s, ts_e, dg["atr"])
                if zt is None or zg is None or abs(zt) < thr or abs(zg) < 0.25 or zt * zg <= 0:
                    continue
                side = 1 if zt > 0 else -1
                m0 = int(bundles[tgt]["times"].searchsorted(ts_s, side="left"))
                m1 = int(bundles[tgt]["times"].searchsorted(ts_e, side="left"))
                if m1 - m0 < 30:
                    continue
                mq = bundles[tgt]["quotes"][m0:m1]
                tr, fd = p24._scan_stop_breakout(bundles[tgt], dt, ts_e, dt["day_sec"] + 18 * 3600, float(mq[:, 1].max()), float(mq[:, 2].min()), sl_atr * dt["atr"], ok_b=(side == 1), ok_s=(side == -1))
            elif kind == "UJ_NY_10ET":
                if dk not in day_maps["USDJPY"] or dk not in day_maps["US100"] or not all(dk in day_maps[a] for a in p26.FX7):
                    continue
                u1, dj = day_maps["US100"][dk], day_maps["USDJPY"][dk]
                ts_s, ts_e = u1["day_sec"], u1["day_sec"] + 30 * 60
                zu = p26.causal_z_return(bundles["US100"], ts_s, ts_e, u1["atr"])
                z_map = {a: p26.causal_z_return(bundles[a], dj["day_sec"] + 7 * 3600, ts_e, day_maps[a][dk]["atr"]) for a in p26.FX7}
                if zu is None or any(v is None for v in z_map.values()):
                    continue
                usd_s = p26.compute_g6_factors(z_map)["USD"]
                if abs(zu) < thr or abs(usd_s) < 0.25 or zu * usd_s <= 0:
                    continue
                tr, fd = p26.market_entry_at(bundles["USDJPY"], dj, ts_e, 1 if usd_s > 0 else -1, sl_atr)
            else:
                continue
            if tr and fd:
                trs.append(tr); fds.append(fd)

    elif fam == "CALENDAR_INTRADAY_FLOWS":
        kind = cfg["kind"]
        for dk in all_days:
            if kind in ("TOM_US100", "TOM_US500", "TOM_XAU"):
                if dk not in tom_set:
                    continue
                tgt = {"TOM_US100": "US100", "TOM_US500": "US500", "TOM_XAU": "XAUUSD"}[kind]
                if dk not in day_maps[tgt]:
                    continue
                d = day_maps[tgt][dk]
                ts_e = d["day_sec"] + (7 * 3600 if tgt == "XAUUSD" else 5 * 60)
                tr, fd = p26.market_entry_at(bundles[tgt], d, ts_e, 1, sl_atr)
            elif kind == "TOM_US100_10ET":
                if dk not in tom_set or dk not in day_maps["US100"]:
                    continue
                d = day_maps["US100"][dk]
                ts_e = d["day_sec"] + 30 * 60
                z1 = p26.causal_z_return(bundles["US100"], d["day_sec"], ts_e, d["atr"])
                if z1 is None or z1 < thr:
                    continue
                tr, fd = p26.market_entry_at(bundles["US100"], d, ts_e, 1, sl_atr)
            elif kind == "US500_MONTUE":
                if date.fromisoformat(dk).weekday() not in (0, 1) or dk not in day_maps["US500"]:
                    continue
                d = day_maps["US500"][dk]
                tr, fd = _session_cont_window(bundles["US500"], d, d["day_sec"], d["day_sec"] + 120 * 60, d["day_sec"] + 360 * 60, min_move=thr, mode="BRK", sl_atr=sl_atr)
            elif kind == "ME_USD_14L":
                if dk not in me_set or not all(dk in day_maps[a] for a in p26.FX7):
                    continue
                ts_e = _local_ts(dk, 14, 0, LONDON_TZ)
                ts_s = ts_e - 4 * 3600
                z_map = {a: p26.causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"]) for a in p26.FX7}
                if any(v is None for v in z_map.values()):
                    continue
                usd_s = p26.compute_g6_factors(z_map)["USD"]
                if abs(usd_s) < thr:
                    continue
                usd_dir = 1 if usd_s > 0 else -1
                best_a, best_sc, best_side = None, -1e9, 0
                for a in p26.USD_MAJORS_NOJPY:
                    base, _ = p26.PAIR_CCY[a]
                    s = usd_dir if base == "USD" else -usd_dir
                    if s * z_map[a] > best_sc:
                        best_a, best_sc, best_side = a, s * z_map[a], s
                if best_a is None or best_sc <= 0:
                    continue
                tr, fd = p26.market_entry_at(bundles[best_a], day_maps[best_a][dk], ts_e, best_side, sl_atr)
            else:
                continue
            if tr and fd:
                trs.append(tr); fds.append(fd)

    elif fam == "VOL_COMPRESSION_REGIME_EXP":
        asset = cfg["asset"]
        b = bundles[asset]
        vrm = vol_ratios[asset]
        for d in b["days"]:
            vr = vrm.get(d["day"])
            if vr is None or vr >= 0.85:
                continue
            open_0 = float(b["quotes"][d["fi"], 0])
            ws = d["day_sec"] + (30 * 60 if asset in ("US100", "US500", "GER40") else 7 * 3600)
            we = d["day_sec"] + (330 * 60 if asset in ("US100", "US500", "GER40") else 17 * 3600)
            tr, fd = p24._scan_stop_breakout(b, d, ws, we, open_0 + thr * d["atr"], open_0 - thr * d["atr"], sl_atr * d["atr"])
            if tr and fd:
                trs.append(tr); fds.append(fd)

    return trs, fds


def forensic_p28_survivor(bundles, day_maps, all_days, vol_ratios, tom_set, me_set, cfg, core5_daily) -> dict:
    trs, _ = eval_p28_spec(bundles, day_maps, all_days, vol_ratios, tom_set, me_set, cfg)
    res = {
        "strategy": cfg["id"],
        "family": cfg["fam"],
        "cost_tiers": {
            "Base": round(fsum(t["base_R"] for t in trs), 2),
            "Stress": round(fsum(t["ftmo_R"] for t in trs), 2),
            "Double": round(fsum(t["double_R"] for t in trs), 2),
        },
        "direction": p18.direction_breakdown(trs),
        "outlier": p23d.outlier_stress_trades(trs),
        "corr_5e": p18.daily_correlation(trs, core5_daily)["union_corr"],
    }
    s1 = {}
    base_thr = float(cfg["thr"])
    thr_grid = (0.0,) if base_thr == 0.0 else (round(max(0.05, base_thr - 0.10), 2), base_thr, round(base_thr + 0.10, 2))
    for th in thr_grid:
        for sa in (0.55, 0.75, 0.95):
            tt, _ = eval_p28_spec(bundles, day_maps, all_days, vol_ratios, tom_set, me_set, {**cfg, "thr": th, "sl_atr": sa})
            s1[f"t{th:.2f}_s{sa:.2f}"] = {
                "A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"],
                "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"],
            }
    res["surface_1"] = {"both_pos": sum(1 for v in s1.values() if v["A"] > 0 and v["B"] > 0), "total": len(s1), "cells": s1}
    res["trades"] = trs
    return res


def build_volcomp_m1_tape(bundle: dict, vol_ratios: dict[str, float], *, thr: float = 0.75, sl_atr: float = 0.75) -> dict[str, tuple]:
    """Exact M1 floating-equity tape for VOL_COMPRESSION_REGIME_EXP (ATR5/ATR20 < 0.85 -> daily-open breakout)."""
    out = {}
    asset = bundle["asset"]
    times, quotes = bundle["times"], bundle["quotes"]
    for d in bundle["days"]:
        vr = vol_ratios.get(d["day"])
        if vr is None or vr >= 0.85:
            continue
        fi, flat_idx = d["fi"], d["flat_idx"]
        open_0 = float(quotes[fi, 0])
        top, bot = open_0 + thr * d["atr"], open_0 - thr * d["atr"]
        ws = d["day_sec"] + (30 * 60 if asset in ("US100", "US500", "GER40") else 7 * 3600)
        we = d["day_sec"] + (330 * 60 if asset in ("US100", "US500", "GER40") else 17 * 3600)
        sub_t = times[fi:flat_idx + 1]
        i0 = int(sub_t.searchsorted(ws, side="left"))
        i1 = int(sub_t.searchsorted(we, side="left"))
        if i1 <= i0:
            continue
        scan = quotes[fi + i0:fi + i1]
        up = scan[:, 5] >= top - 1e-10
        dn = scan[:, 2] <= bot + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        e_idx = fi + i0 + j
        ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
        item = p27.replay_causal_m1_tape_trade(
            asset, times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_atr * d["atr"],
            spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"],
        )
        if item is not None:
            out[item[0]["day"]] = item
    return out


def build_usdjpy_ny_risk_10et_m1_tape(bundles: dict, day_maps: dict, all_days: list[str], *, thr: float = 0.25, sl_atr: float = 0.75) -> dict[str, tuple]:
    """Exact M1 floating-equity tape for USDJPY_NY_RISK_FLOW_10ET (10:00 ET post-macro market entry)."""
    out = {}
    bj = bundles["USDJPY"]
    times, quotes = bj["times"], bj["quotes"]
    for dk in all_days:
        if dk not in day_maps["USDJPY"] or dk not in day_maps["US100"] or not all(dk in day_maps[a] for a in p26.FX7):
            continue
        u1, dj = day_maps["US100"][dk], day_maps["USDJPY"][dk]
        ts_s, ts_e = u1["day_sec"], u1["day_sec"] + 30 * 60
        zu = p26.causal_z_return(bundles["US100"], ts_s, ts_e, u1["atr"])
        z_map = {a: p26.causal_z_return(bundles[a], dj["day_sec"] + 7 * 3600, ts_e, day_maps[a][dk]["atr"]) for a in p26.FX7}
        if zu is None or any(v is None for v in z_map.values()):
            continue
        usd_s = p26.compute_g6_factors(z_map)["USD"]
        if abs(zu) < thr or abs(usd_s) < 0.25 or zu * usd_s <= 0:
            continue
        side = 1 if usd_s > 0 else -1
        fi, flat_idx = dj["fi"], dj["flat_idx"]
        rel = int(times[fi:flat_idx + 1].searchsorted(ts_e, side="left"))
        e_idx = fi + rel
        if e_idx >= flat_idx or int(times[e_idx]) - ts_e > 600:
            continue
        ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
        item = p27.replay_causal_m1_tape_trade(
            "USDJPY", times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_atr * dj["atr"],
            spec=bj["spec"], usdjpy_close_map=bj["usdjpy_close_map"],
        )
        if item is not None:
            out[item[0]["day"]] = item
    return out


# ==============================================================================
# TRACK 3: EXACT 3-6 MONTH SHORT-HORIZON FRONTIER (2-STEP + 1-STEP HYPER GROWTH)
# ==============================================================================

def run_frontier_2step(
    idx_matrix: np.ndarray,
    nets: np.ndarray,
    dds: np.ndarray,
    flags: np.ndarray,
    *,
    firm: str,
    cap: float,
    fee: float,
    p1_mult: float,
    p2_mult: float,
    ea_daily_stop_pct: float | None = 0.035,
) -> dict:
    """2-Step lifecycle with optional internal EA daily circuit breaker & AMBER/RED equity throttle."""
    scale = cap / 10000.0
    p1_goal, p2_goal = cap * 1.10, cap * 1.05
    daily_cap, static_floor = cap * 0.05, cap * 0.90
    ea_cut = (cap * ea_daily_stop_pct) if ea_daily_stop_pct is not None else None
    is_5ers = ("5ERS" in firm.upper())
    min_d = 3 if is_5ers else 4

    pass_days, pay_days, cf12_l, cf24_l, oop_l, br1_c, brf_c, tix_l = [], [], [], [], [], 0, 0, []
    for b in range(len(idx_matrix)):
        stage, bal, tdays, attempts, fees, refunded, payouts, cycle_d = "P1", cap, 0, 1, fee, False, 0.0, 0
        f_pass = f_pay = cf12 = None
        had_br1 = had_brf = False
        max_oop = fee

        for day_num, src_i in enumerate(idx_matrix[b], start=1):
            eq_pct = (bal - cap) / cap
            m = p1_mult if stage == "P1" else (p2_mult if stage == "P2" else 1.0)
            if eq_pct <= -0.060:
                m = min(m, 0.40)
            elif eq_pct <= -0.035:
                m = min(m, 0.65)

            net = float(nets[src_i]) * scale * m
            dd = float(dds[src_i]) * scale * m
            # Internal EA daily circuit breaker caps intraday loss (with conservative +0.25% slippage tail)
            if ea_cut is not None and dd > ea_cut:
                dd = min(dd, ea_cut + cap * 0.0025)
                net = min(net, -ea_cut)

            if dd >= daily_cap - 1e-9 or (bal - dd) <= static_floor + 1e-9:
                if stage == "P1":
                    had_br1 = True
                elif stage == "FUNDED":
                    had_brf = True
                if attempts <= 3:
                    attempts += 1
                    fees += (fee * (0.90 if attempts == 2 else 0.80)) if is_5ers else fee
                    stage, bal, tdays, refunded, cycle_d = "P1", cap, 0, False, 0
            else:
                bal += net
                if is_5ers:
                    if net >= cap * 0.005:
                        tdays += 1
                elif flags[src_i]:
                    tdays += 1

                if stage == "P1" and bal >= p1_goal - 1e-9 and tdays >= min_d:
                    stage, bal, tdays = "P2", cap, 0
                elif stage == "P2" and bal >= p2_goal - 1e-9 and tdays >= min_d:
                    stage, bal, tdays, cycle_d = "FUNDED", cap, 0, 0
                    if f_pass is None:
                        f_pass = day_num
                elif stage == "FUNDED":
                    cycle_d += 1
                    if cycle_d >= 10:
                        if bal > cap + 1e-6:
                            pay = (bal - cap) * 0.80
                            if not refunded:
                                pay += (fee * 0.70 if is_5ers else fee)
                                refunded = True
                            payouts += pay
                            if f_pay is None:
                                f_pay = day_num
                            bal = cap
                        cycle_d = 0

            max_oop = max(max_oop, fees - payouts)
            if day_num == 252:
                cf12 = payouts - fees

        if f_pass is not None:
            pass_days.append(f_pass)
        if f_pay is not None:
            pay_days.append(f_pay)
        br1_c += int(had_br1)
        brf_c += int(had_brf)
        tix_l.append(attempts)
        cf12_l.append(cf12 if cf12 is not None else (payouts - fees))
        cf24_l.append(payouts - fees)
        oop_l.append(max_oop)

    n = len(idx_matrix)
    cf12_a, cf24_a = np.asarray(cf12_l), np.asarray(cf24_l)
    return {
        "pass_3m": round(100.0 * sum(d <= 63 for d in pass_days) / n, 1),
        "pass_6m": round(100.0 * sum(d <= 126 for d in pass_days) / n, 1),
        "pass_9m": round(100.0 * sum(d <= 189 for d in pass_days) / n, 1),
        "pass_12m": round(100.0 * sum(d <= 252 for d in pass_days) / n, 1),
        "pass_24m": round(100.0 * len(pass_days) / n, 1),
        "br1_pct": round(100.0 * br1_c / n, 1),
        "br_funded_pct": round(100.0 * brf_c / max(1, len(pass_days)), 1),
        "avg_tix": round(float(np.mean(tix_l)), 2),
        "med_pass_m": round(float(np.median(pass_days)) / 21.0, 1) if pass_days else None,
        "med_pay1_m": round(float(np.median(pay_days)) / 21.0, 1) if pay_days else None,
        "cf12_mean": round(float(cf12_a.mean()), 1),
        "cf24_mean": round(float(cf24_a.mean()), 1),
        "cf24_pos_pct": round(100.0 * float(np.mean(cf24_a > 0)), 1),
        "oop95": round(float(np.percentile(oop_l, 95)), 1),
    }


def run_frontier_hyper_growth_1step(
    idx_matrix: np.ndarray,
    nets: np.ndarray,
    dds: np.ndarray,
    *,
    cap: float = 5000.0,
    fee: float = 260.0,
    p1_mult: float = 2.0,
) -> dict:
    """Exact The5ers Hyper Growth 1-Step model: +10% SINGLE step, 6% static stop-out, 3% NON-BREACHING Daily Pause!"""
    scale = cap / 10000.0
    goal = cap * 1.10
    static_floor = cap * 0.94  # 6% static stop-out
    daily_pause = cap * 0.03   # 3% daily pause (closes trades & locks day, does NOT breach!)

    pass_days, cf12_l, cf24_l, br1_c, tix_l, oop_l = [], [], [], 0, [], []
    for b in range(len(idx_matrix)):
        stage, bal, attempts, fees, payouts, cycle_d = "P1", cap, 1, fee, 0.0, 0
        f_pass = cf12 = None
        had_br1 = False
        max_oop = fee

        for day_num, src_i in enumerate(idx_matrix[b], start=1):
            eq_pct = (bal - cap) / cap
            m = p1_mult if stage == "P1" else 0.85
            # Tighter throttle for 6% static floor
            if eq_pct <= -0.035:
                m = min(m, 0.35)
            elif eq_pct <= -0.020:
                m = min(m, 0.60)

            net = float(nets[src_i]) * scale * m
            dd = float(dds[src_i]) * scale * m
            # Non-breaching 3% daily pause caps daily loss at ~3.1%
            if dd >= daily_pause:
                dd = min(dd, daily_pause + cap * 0.001)
                net = min(net, -daily_pause)

            if (bal - dd) <= static_floor + 1e-9:
                if stage == "P1":
                    had_br1 = True
                if attempts <= 2:
                    attempts += 1
                    fees += fee
                    stage, bal, cycle_d = "P1", cap, 0
            else:
                bal += net
                if stage == "P1" and bal >= goal - 1e-9:
                    stage, bal, cycle_d = "FUNDED", cap * 2.0, 0  # Hyper Growth doubles capital to 10k on pass!
                    if f_pass is None:
                        f_pass = day_num
                elif stage == "FUNDED":
                    # On funded 10k (2x initial 5k), conservative 50%->75% split modeled at 60% blended
                    cycle_d += 1
                    if cycle_d >= 10:
                        if bal > cap * 2.0 + 1e-6:
                            payouts += (bal - cap * 2.0) * 0.60
                            bal = cap * 2.0
                        cycle_d = 0
            max_oop = max(max_oop, fees - payouts)
            if day_num == 252:
                cf12 = payouts - fees

        if f_pass is not None:
            pass_days.append(f_pass)
        br1_c += int(had_br1)
        tix_l.append(attempts)
        cf12_l.append(cf12 if cf12 is not None else (payouts - fees))
        cf24_l.append(payouts - fees)
        oop_l.append(max_oop)

    n = len(idx_matrix)
    cf12_a, cf24_a = np.asarray(cf12_l), np.asarray(cf24_l)
    return {
        "pass_3m": round(100.0 * sum(d <= 63 for d in pass_days) / n, 1),
        "pass_6m": round(100.0 * sum(d <= 126 for d in pass_days) / n, 1),
        "pass_9m": round(100.0 * sum(d <= 189 for d in pass_days) / n, 1),
        "pass_12m": round(100.0 * sum(d <= 252 for d in pass_days) / n, 1),
        "pass_24m": round(100.0 * len(pass_days) / n, 1),
        "br1_pct": round(100.0 * br1_c / n, 1),
        "avg_tix": round(float(np.mean(tix_l)), 2),
        "med_pass_m": round(float(np.median(pass_days)) / 21.0, 1) if pass_days else None,
        "cf12_mean": round(float(cf12_a.mean()), 1),
        "cf24_mean": round(float(cf24_a.mean()), 1),
        "cf24_pos_pct": round(100.0 * float(np.mean(cf24_a > 0)), 1),
        "oop95": round(float(np.percentile(oop_l, 95)), 1),
    }


# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================

def run_pass28(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")

    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    assets11 = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY", "XAUUSD", "US500", "US100", "GER40")
    bundles = {a: p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map) for a in assets11}
    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in assets11}
    all_days = sorted({d for dm in day_maps.values() for d in dm})
    vol_ratios = {a: _compute_vol_ratio_map(bundles[a]) for a in assets11}
    tom_set, me_set = _calendar_tom_and_me_sets(all_days)

    # Build frozen Pass 27 exact M1 tapes (E1..E5 + S6 + S7)
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    ext_days = sorted(ref_days["extended"])
    cluster_a_days = sorted(d for d in ref_days["strict"] if d < "2021-01-01")
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, swing_specs["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, swing_specs["USDJPY"])
    exp_usd_05 = {r["day"]: (r, t, m) for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)}
    gbp_vh_05_raw, _ = p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50)
    gbp_vh_05 = {r["day"]: (r, t, m) for r, t, m in gbp_vh_05_raw}
    for eng_d, a_name in ((ref_trades, "USDJPY"), (exp_usd_05, "USDJPY"), (gbp_vh_05, "GBPUSD")):
        for _dk, (r, _t, _m) in eng_d.items():
            r["asset"] = a_name

    e4_us100 = p27.build_us100_e4_tape(bundles["US100"])
    e5_us100 = p27.build_us100_e5_tape(bundles, day_maps, all_days)
    s6_usdbsk = p27.build_fx_usd_basket_s6_tape(bundles, day_maps, all_days)
    s7_xau120 = p27.build_xau_exp120_s7_tape(bundles["XAUUSD"])

    tapes = {
        "E1_USDJPY_TOKYO": ref_trades,
        "E2_USDJPY_EXP80": exp_usd_05,
        "E3_GBPUSD_VH": gbp_vh_05,
        "E4_US100_SESS40": e4_us100,
        "E5_US100_RS1130": e5_us100,
        "S6_FX_USD_BSK": s6_usdbsk,
        "S7_XAU_EXP120": s7_xau120,
    }
    a_dd_3 = {e: p27.replay_multi_engine_m1(cluster_a_days, tapes, {e: 0.003}, 10000.0)[0]["peak_dd_pct"] for e in ("E1_USDJPY_TOKYO", "E2_USDJPY_EXP80")}
    inv2 = {e: (1.0 / a_dd_3[e]) / fsum(1.0 / v for v in a_dd_3.values()) for e in a_dd_3}
    base_3e = {**{e: 0.0075 * w for e, w in inv2.items()}, "E3_GBPUSD_VH": 0.0075}
    risks_5e = {**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050}
    risks_7e = {**risks_5e, "S6_FX_USD_BSK": 0.0050, "S7_XAU_EXP120": 0.0050}

    _, led5_base = p27.replay_multi_engine_m1(ext_days, tapes, risks_5e, 10000.0, profile_mode="Swing")
    core5_daily = {r["day"]: r["net_usd"] / 100.0 for r in led5_base}

    # --- TRACK 1: FINAL PRE-HOLDOUT DISCOVERY (m_total = 40) ---
    catalog = build_pass28_catalog()
    m_total = len(catalog)
    p_all, stage1 = [], []
    for cfg in catalog:
        trs, fds = eval_p28_spec(bundles, day_maps, all_days, vol_ratios, tom_set, me_set, cfg)
        mA = wbd.split_metrics(trs, clock.CLUSTERS["A"])
        min_a = int(cfg.get("min_a", 40))
        passed_A = (mA["n"] >= min_a and mA["net_R"] > 0 and mA["pf"] >= 1.05)
        sf = p18.sign_flip_null_p(trs, fds, draws=MC_DRAWS) if (passed_A and trs) else {"gross_p": 1.0, "ftmo_net_p": 1.0}
        p_all.append(sf["ftmo_net_p"])
        stage1.append((cfg, trs, fds, mA, passed_A, sf))

    q_all = p14.benjamini_hochberg(p_all)
    survivors = []
    for (cfg, trs, fds, mA, passed_A, sf), q_full in zip(stage1, q_all):
        if not passed_A:
            continue
        mB = wbd.split_metrics(trs, clock.CLUSTERS["B"])
        tot_R = round(fsum(t["ftmo_R"] for t in trs), 2)
        base_R = round(fsum(t["base_R"] for t in trs), 2)
        dbl_R = round(fsum(t["double_R"] for t in trs), 2)
        fade_R = round(fsum(f["ftmo_R"] for f in fds), 2)
        yr_map = {y: round(fsum(t["ftmo_R"] for t in trs if t["year"] == y), 2) for y in clock.YEAR}
        pos_yrs = sum(v > 0 for v in yr_map.values())
        eq = np.cumsum([0.0] + [t["ftmo_R"] for t in trs])
        dd_R = round(float((np.maximum.accumulate(eq) - eq).max()), 2)
        wins = sorted((t["ftmo_R"] for t in trs if t["ftmo_R"] > 0), reverse=True)
        top10 = round(fsum(wins[:10]), 2)
        corr_5e = p18.daily_correlation(trs, core5_daily)["union_corr"]
        b_dir = p18.direction_breakdown(trs)

        t1 = (len(trs) >= 80 and mB["net_R"] > 0 and tot_R > top10 and tot_R > fade_R and pos_yrs >= 5 and dd_R <= 15.0 and sf["ftmo_net_p"] < 0.05 and q_full <= 0.10 and abs(corr_5e) <= 0.25)
        if t1:
            tier = "TIER_1_FTMO_READY"
        elif mB["net_R"] > 0 and tot_R > 0 and tot_R > fade_R and pos_yrs >= 4 and sf["ftmo_net_p"] < 0.10:
            tier = "TIER_2_PERSONAL_VAULT"
        else:
            tier = "TIER_3_DEAD_NO_EDGE"

        survivors.append({
            "strategy": cfg["id"], "family": cfg["fam"], "n_total": len(trs),
            "cluster_A": mA, "cluster_B_blind": mB,
            "ftmo_net_R": tot_R, "ftmo_base_R": base_R, "ftmo_double_R": dbl_R, "fade_ftmo_R": fade_R,
            "pos_years": pos_yrs, "years_R": yr_map, "closed_dd_R": dd_R,
            "p_sign_flip": round(sf["ftmo_net_p"], 4), "fdr_q_full_space": round(q_full, 4),
            "corr_5e": corr_5e, "direction": b_dir, "tier": tier, "spec": cfg,
        })

    survivors.sort(key=lambda r: (0 if "TIER_1" in r["tier"] else (1 if "TIER_2" in r["tier"] else 2), -r["ftmo_net_R"]))
    print(f"\n=== TRACK 1: PASS 28 FINAL PRE-HOLDOUT DISCOVERY (m_total={m_total}, 5 orthogonal families) ===", flush=True)
    print(f"  Passed Cluster A Gate: {len(survivors)} / {m_total}", flush=True)
    for r in survivors:
        print(
            f"  {r['strategy']:27s} ({r['family']:27s}) | n={r['n_total']:4d} "
            f"| A={r['cluster_A']['net_R']:+5.1f}R -> BLIND_B={r['cluster_B_blind']['net_R']:+5.1f}R "
            f"| Tot={r['ftmo_net_R']:+6.2f}R (B={r['ftmo_base_R']:+5.1f}, D={r['ftmo_double_R']:+5.1f}, yr+={r['pos_years']}/7, DD={r['closed_dd_R']:4.1f}R) "
            f"| p={r['p_sign_flip']:.3f} q={r['fdr_q_full_space']:.3f} | r5E={r['corr_5e']:+.3f} | {r['tier']}",
            flush=True,
        )

    targets = [r for r in survivors if "TIER_1" in r["tier"]]
    for r in survivors:
        if "TIER_2" in r["tier"] and r["p_sign_flip"] < 0.03 and abs(r["corr_5e"]) <= 0.25 and r not in targets:
            targets.append(r)

    forensic_reports = []
    if targets:
        print(f"\n=== TRACK 1B: DEEP FORENSIC ON PASS 28 TARGETS ({len(targets)}) ===", flush=True)
        for cand in targets[:6]:
            frep = forensic_p28_survivor(bundles, day_maps, all_days, vol_ratios, tom_set, me_set, cand["spec"], core5_daily)
            frep.pop("trades")
            s1 = frep["surface_1"]
            s1_ok = (s1["both_pos"] / max(1, s1["total"])) >= 0.50
            cost_ok = all(v > 0 for v in frep["cost_tiers"].values())
            out_ok = (frep["outlier"]["drop_top3_R"] > 0 and frep["outlier"]["excl_both_crises_R"] > 0)
            frep["forensic_pass"] = bool(cost_ok and s1_ok and out_ok)
            forensic_reports.append(frep)
            print(
                f"  FORENSIC {cand['strategy']:27s} | tiers={frep['cost_tiers']} "
                f"| out(-T3={frep['outlier']['drop_top3_R']:+.1f}, -T5={frep['outlier']['drop_top5_R']:+.1f}, exCr={frep['outlier']['excl_both_crises_R']:+.1f}) "
                f"| s1={s1['both_pos']}/{s1['total']} | r5E={frep['corr_5e']:+.3f} "
                f"| dir=B:{frep['direction']['BUY']['ftmo_R']:+.1f}/S:{frep['direction']['SELL']['ftmo_R']:+.1f} | PASS={frep['forensic_pass']}",
                flush=True,
            )

    # Build exact M1 tapes for any Pass 28 forensic-passing engines & add upgraded portfolio!
    passed_p28 = [f["strategy"] for f in forensic_reports if f["forensic_pass"]]
    risks_p28_core = dict(risks_5e)
    risks_p28_turbo = dict(risks_7e)
    if "EURJPY_VOLCOMP_EXP75" in passed_p28:
        tapes["E6_EURJPY_VOLCOMP"] = build_volcomp_m1_tape(bundles["EURJPY"], vol_ratios["EURJPY"], thr=0.75, sl_atr=0.75)
        risks_p28_core["E6_EURJPY_VOLCOMP"] = 0.0050
        risks_p28_turbo["E6_EURJPY_VOLCOMP"] = 0.0050
    if "USDJPY_NY_RISK_FLOW_10ET" in passed_p28:
        tapes["E7_USDJPY_NY10ET"] = build_usdjpy_ny_risk_10et_m1_tape(bundles, day_maps, all_days, thr=0.25, sl_atr=0.75)
        risks_p28_core["E7_USDJPY_NY10ET"] = 0.0050
        risks_p28_turbo["E7_USDJPY_NY10ET"] = 0.0050

    # --- TRACK 2: EXACT OFFICIAL RED-NEWS GUARD (±5m) IMPACT AUDIT (2018-2024) ---
    cal_us = build_official_red_news_calendar(include_uk_proxy=False)
    cal_us_uk = build_official_red_news_calendar(include_uk_proxy=True)
    n_us_events = sum(len(v) for v in cal_us.values())
    n_uk_events = sum(len(v) for v in cal_us_uk.values())
    print(f"\n=== TRACK 2: OFFICIAL RED-NEWS GUARD (±5m) AUDIT (US={n_us_events} official FOMC+CPI+NFP; US+UK={n_uk_events}) ===", flush=True)

    news_audit = {"counts": {"us_official": n_us_events, "us_plus_uk_proxy": n_uk_events}, "portfolios": {}}
    news_ledgers = {}
    audit_books = [("PORT_5E_RAW", risks_5e), ("PORT_7E_P1_TURBO", risks_7e)]
    if len(risks_p28_core) > len(risks_5e):
        audit_books.append((f"PORT_{len(risks_p28_core)}E_P28_CORE", risks_p28_core))
        audit_books.append((f"PORT_{len(risks_p28_turbo)}E_P28_TURBO", risks_p28_turbo))
    for pname, rk in audit_books:
        news_audit["portfolios"][pname] = {}
        print(f"\n  [{pname}]", flush=True)
        base_ann = None
        for mode_label, cal, gmode in (
            ("N0_SWING_UNRESTRICTED", None, None),
            ("N1_FLATTEN_5M_US_OFFICIAL", cal_us, "FLATTEN_5M"),
            ("N2_SKIP_US_NEWS_DAYS", cal_us, "SKIP_DAY"),
            ("N3_FLATTEN_5M_US_PLUS_UK", cal_us_uk, "FLATTEN_5M"),
        ):
            if cal is None:
                gtapes = tapes
                gstats = {}
            else:
                gtapes, gstats = {}, {}
                for eng in rk:
                    gt, st = apply_red_news_guard_to_tape(tapes[eng], cal, mode=gmode, pad_sec=300)
                    gtapes[eng] = gt
                    gstats[eng] = st
            met, led = p27.replay_multi_engine_m1(ext_days, gtapes, rk, 10000.0, profile_mode="Standard")
            if base_ann is None:
                base_ann = met["ann_pct"]["all"]
            ret_pct = round(100.0 * met["ann_pct"]["all"] / base_ann, 1) if base_ann > 0 else 0.0
            news_audit["portfolios"][pname][mode_label] = {"metrics": met, "retained_pct": ret_pct, "guard_stats": gstats}
            news_ledgers[(pname, mode_label)] = led
            tot_blk = sum(s["blocked_entry"] for s in gstats.values())
            tot_flt = sum(s["flattened_pre_news"] for s in gstats.values())
            tot_skp = sum(s["skipped_day"] for s in gstats.values())
            print(
                f"    {mode_label:26s} | Ann={met['ann_pct']['all']:+5.2f}% (A={met['ann_pct']['A']:+5.2f}%, B={met['ann_pct']['B']:+5.2f}%) "
                f"| Ret={ret_pct:5.1f}% | DailyDD={met['daily_loss_pct']:4.2f}% | FloatDD={met['peak_dd_pct']:4.2f}% | Calmar={met['calmar']:4.2f} "
                f"| blk={tot_blk} flat={tot_flt} skip={tot_skp}",
                flush=True,
            )

    # --- TRACK 3: TRUE 3-6 MONTH SHORT-HORIZON PASSING FRONTIER (N = 2,000 EXACT M1) ---
    idx_matrix = p27._draw_bootstrap_indices(len(ext_days), horizon=504, n_paths=BOOTSTRAP_PATHS, seed=SEED)
    _, n5, d5, f5 = p23l.build_full_daily_series(ext_days, news_ledgers[("PORT_5E_RAW", "N0_SWING_UNRESTRICTED")], 10000.0)
    _, n7, d7, f7 = p23l.build_full_daily_series(ext_days, news_ledgers[("PORT_7E_P1_TURBO", "N0_SWING_UNRESTRICTED")], 10000.0)
    _, n5_news, d5_news, f5_news = p23l.build_full_daily_series(ext_days, news_ledgers[("PORT_5E_RAW", "N1_FLATTEN_5M_US_OFFICIAL")], 10000.0)

    frontier_books = [
        ("PORT_5E_RAW", (n5, d5, f5, 0.50)),
        ("PORT_7E_P1_TURBO", (n7, d7, f7, 0.50)),
        ("PORT_5E_NEWS_GUARDED", (n5_news, d5_news, f5_news, 0.50)),
    ]
    p28_core_name = f"PORT_{len(risks_p28_core)}E_P28_CORE"
    p28_turbo_name = f"PORT_{len(risks_p28_turbo)}E_P28_TURBO"
    if (p28_core_name, "N0_SWING_UNRESTRICTED") in news_ledgers:
        _, nc, dc, fc = p23l.build_full_daily_series(ext_days, news_ledgers[(p28_core_name, "N0_SWING_UNRESTRICTED")], 10000.0)
        _, nt, dt, ft = p23l.build_full_daily_series(ext_days, news_ledgers[(p28_turbo_name, "N0_SWING_UNRESTRICTED")], 10000.0)
        frontier_books.append((p28_core_name, (nc, dc, fc, 0.50)))
        frontier_books.append((p28_turbo_name, (nt, dt, ft, 0.50)))

    print("\n=== TRACK 3A: TRUE 3-6 MONTH FRONTIER — 2-STEP (FTMO 10K & THE5ERS HS 5K, EXACT M1 + -3.5% EA DAILY GUARD) ===", flush=True)
    frontier_2step = {}
    for pname, (nn, dd, ff, max_single_base) in frontier_books:
        frontier_2step[pname] = {}
        print(f"\n  [{pname}]", flush=True)
        for p1m, p2m in ((2.0, 1.25), (2.5, 1.40), (3.0, 1.60), (3.5, 1.80), (4.0, 2.00)):
            tag = f"P1_{p1m:.1f}x_P2_{p2m:.2f}x"
            r_ft = run_frontier_2step(idx_matrix, nn, dd, ff, firm="FTMO_10K", cap=10000.0, fee=168.0, p1_mult=p1m, p2_mult=p2m, ea_daily_stop_pct=0.035)
            r_5e = run_frontier_2step(idx_matrix, nn, dd, ff, firm="THE5ERS_HS_5K", cap=5000.0, fee=39.0, p1_mult=p1m, p2_mult=p2m, ea_daily_stop_pct=0.035)
            max_trade_r = round(max_single_base * p1m, 2)
            frontier_2step[pname][tag] = {"max_single_trade_risk_pct": max_trade_r, "FTMO_10K": r_ft, "THE5ERS_HS_5K": r_5e}
            print(
                f"    {tag:16s} (1tr<={max_trade_r:4.2f}%) | 3/6/9/12/24m={r_ft['pass_3m']:4.1f}/{r_ft['pass_6m']:4.1f}/{r_ft['pass_9m']:4.1f}/{r_ft['pass_12m']:4.1f}/{r_ft['pass_24m']:4.1f}% "
                f"| Br1={r_ft['br1_pct']:4.1f}% Tix={r_ft['avg_tix']:.2f} | Med={str(r_ft['med_pass_m']):>4s}m "
                f"| FTMO CF12=${r_ft['cf12_mean']:+4.0f} CF24=${r_ft['cf24_mean']:+5.0f} (P>0={r_ft['cf24_pos_pct']:4.1f}%) "
                f"| 5ers CF12=${r_5e['cf12_mean']:+4.0f} CF24=${r_5e['cf24_mean']:+4.0f}",
                flush=True,
            )

    print("\n=== TRACK 3B: TRUE 3-6 MONTH FRONTIER — THE5ERS HYPER GROWTH 1-STEP (+10% SINGLE TARGET, 6% STATIC, 3% PAUSE) ===", flush=True)
    frontier_1step = {}
    hg_books = [("PORT_5E_RAW", (n5, d5)), ("PORT_7E_P1_TURBO", (n7, d7))]
    if (p28_turbo_name, "N0_SWING_UNRESTRICTED") in news_ledgers:
        hg_books.append((p28_core_name, (nc, dc)))
        hg_books.append((p28_turbo_name, (nt, dt)))
    for pname, (nn, dd) in hg_books:
        frontier_1step[pname] = {}
        print(f"\n  [{pname}]", flush=True)
        for p1m in (1.5, 2.0, 2.5, 3.0):
            r1 = run_frontier_hyper_growth_1step(idx_matrix, nn, dd, cap=5000.0, fee=260.0, p1_mult=p1m)
            frontier_1step[pname][f"HG_{p1m:.1f}x"] = r1
            print(
                f"    HG_{p1m:.1f}x | 3/6/9/12/24m={r1['pass_3m']:4.1f}/{r1['pass_6m']:4.1f}/{r1['pass_9m']:4.1f}/{r1['pass_12m']:4.1f}/{r1['pass_24m']:4.1f}% "
                f"| Br1={r1['br1_pct']:4.1f}% Tix={r1['avg_tix']:.2f} | Med={str(r1['med_pass_m']):>4s}m "
                f"| CF12=${r1['cf12_mean']:+5.0f} CF24=${r1['cf24_mean']:+6.0f} (P>0={r1['cf24_pos_pct']:4.1f}%) OOP95=${r1['oop95']:.0f}",
                flush=True,
            )

    return {
        "pass": "Pass 28 (Final Pre-Holdout Discovery, Red-News Guard Audit & 3-6 Month Frontier)",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "m_total_search_space": m_total,
        "survivors": survivors,
        "forensic_reports": forensic_reports,
        "red_news_audit": news_audit,
        "frontier_2step": frontier_2step,
        "frontier_1step_hyper_growth": frontier_1step,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass28(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass28-result.json", res)
    print("\nPASS28_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
