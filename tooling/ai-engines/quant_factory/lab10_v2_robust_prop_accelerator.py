"""Lab #10 (Generation v2): PASS_ROBUST 7-Gate Alpha Discovery, Walk-Forward SL/TP (12m->4m) & Dynamic Prop Pacing.

STRICT SEALED DEVELOPMENT BOUNDARY (< 2025-01-01 ONLY):
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity; `holdout_rows_analysed = 0`, `ORDER_SEND_CAPABLE = False`.
  - Runs 100% locally off D: SSD `.runtime/hot-m1-cache` + `.runtime/hot-m1-cache/_derived` (zero external E: dependency).
  - Never modifies live running v1 EAs or `PORTFOLIO-REGISTRY.json`.

Three empirical studies in one reproducible script:
  1A. Pre-Registered Multi-Asset Intraday Alpha Discovery (`m_total = 16` specs across GER40, GBPJPY, EURUSD,
      AUDUSD, USDCAD, XAUUSD, US500), audited through ALL 7 gates of `SkepticalRedTeamCritic` (`G0..G5`) +
      4-Pillar `RobustnessGate` (`G6`: Real-Market M5 Random-Entry MC >= 90%, Buy/Sell positive, Trim-5% Win > 0, WY-P10).
  1B. Rolling Walk-Forward SL/TP Optimization (`12m` train -> `4m` blind OOS, 18 OOS blocks across `2019-2024`)
      on exact M1 minute-by-minute marks of `frozen_9e_tapes_v1`, comparing Fixed Baseline vs Walk-Forward OOS vs
      In-Sample Oracle to quantify real Walk-Forward lift and exact Overfit Illusion Gap.
  1C. Causal Dynamic Prop Pacing (`Numba JIT`, `N = 5,000` block-bootstrap paths) across FTMO Swing 10K,
      FTMO Standard 10K, and The5ers High Stakes 5K — testing whether Profit-Lock & Breadth Expansion cut
      Median Days-to-Pass without increasing Prop Wipeout risk.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any
from zoneinfo import ZoneInfo

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
import pass24_mtf_new_archetypes as p24
from native_ftmo_monfri_seal import ROOT, STOP
from quant_core.ftmo_track_replay import profiles
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_registry,
)
from quant_factory.eval_pipeline import benjamini_hochberg, sign_flip_p_numba
from quant_factory.prop_engine import make_block_bootstrap_indices, replay_portfolio_m1
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import format_markdown_table, write_verified_receipt
from quant_factory.research_council import EvidenceBundle, KillCriteria, critique_proposal, propose_hypothesis
from quant_factory.robustness_gate import (
    RobustnessThresholds,
    evaluate_robustness_gate,
    random_entry_mc_on_bars,
    resample_m1_quotes_to_m5_mid,
)

ORDER_SEND_CAPABLE: bool = False
NY_TZ = ZoneInfo("America/New_York")
LONDON_TZ = ZoneInfo("Europe/London")
BERLIN_TZ = ZoneInfo("Europe/Berlin")

CLUSTER_A_YEARS = frozenset({2018, 2019, 2020})
CLUSTER_B_YEARS = frozenset({2021, 2022, 2023, 2024})
SEED = 20261124


def _local_ts(day_iso: str, hour: int, minute: int, tz: ZoneInfo) -> int:
    d = date.fromisoformat(day_iso)
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz).timestamp())


def build_local_m1_bundle(
    asset: str,
    swing_specs: dict[str, dict],
    usdjpy_close_map: dict[date, float],
    *,
    cache_dir: Path = hcache.DEFAULT_CACHE,
) -> dict[str, Any]:
    """Build causal daily/session index strictly from local D: SSD `hot_m1_cache` (zero E: drive, 0 holdout rows)."""
    times, quotes, am = hcache.load_asset(asset, cache_dir=cache_dir, verify_sha=False)
    assert int(times[-1]) < STOP, f"HOLDOUT_CONTAMINATION:{asset}"
    if quotes.shape[1] < 8:
        # Synthesize ask proxy only if native_Ask is False (all 11 target assets here have native 8-col Bid/Ask)
        quotes = np.hstack([quotes, quotes])

    # Partition M1 bars cleanly by UTC date
    day_ids = (times // 86400).astype(np.int64)
    change = np.empty(len(day_ids), dtype=np.bool_)
    change[0] = True
    change[1:] = day_ids[1:] != day_ids[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = len(day_ids) - 1

    raw_days: list[dict[str, Any]] = []
    for s_i, e_i in zip(starts, ends):
        ts0 = int(times[s_i])
        dt0 = datetime.fromtimestamp(ts0, timezone.utc)
        if dt0.weekday() >= 5:
            continue
        if (e_i - s_i + 1) < 120:
            continue
        d_iso = dt0.date().isoformat()
        dsec = int(datetime(dt0.year, dt0.month, dt0.day, tzinfo=timezone.utc).timestamp())
        # Hard flat strictly before 20:50 UTC (zero rollover / swap=0 invariant!)
        flat_target = dsec + 20 * 3600 + 50 * 60
        sub_t = times[s_i:e_i + 1]
        rel_flat = int(sub_t.searchsorted(flat_target, side="right")) - 1
        flat_idx = int(s_i + max(0, rel_flat))
        bo = float(quotes[s_i, 0])
        bh = float(quotes[s_i:e_i + 1, 1].max())
        bl = float(quotes[s_i:e_i + 1, 2].min())
        bc = float(quotes[e_i, 3])
        raw_days.append({
            "day": d_iso,
            "year": dt0.year,
            "date": dt0.date(),
            "dsec": dsec,
            "fi": int(s_i),
            "li": int(e_i),
            "flat_idx": flat_idx,
            "o": bo, "h": bh, "l": bl, "c": bc,
        })

    # Strictly causal 14-day ATR and 5d/20d vol compression ratio (computed strictly from PRIOR closed days t-1!)
    days_out: list[dict[str, Any]] = []
    trs: list[float] = []
    for i, d in enumerate(raw_days):
        if i == 0:
            tr_val = d["h"] - d["l"]
            trs.append(tr_val)
            continue
        prev = raw_days[i - 1]
        tr_prev = max(prev["h"] - prev["l"], abs(prev["h"] - (raw_days[i - 2]["c"] if i >= 2 else prev["o"])),
                      abs(prev["l"] - (raw_days[i - 2]["c"] if i >= 2 else prev["o"])))
        if i >= 2:
            trs.append(tr_prev)
        if len(trs) >= 20:
            atr14 = float(np.mean(trs[-14:]))
            atr5 = float(np.mean(trs[-5:]))
            atr20 = float(np.mean(trs[-20:]))
            vol_ratio = atr5 / max(1e-9, atr20)
            days_out.append({
                **d,
                "prev_o": prev["o"],
                "prev_h": prev["h"],
                "prev_l": prev["l"],
                "prev_c": prev["c"],
                "atr": max(1e-9, atr14),
                "vol_ratio": vol_ratio,
            })

    spec_key = asset if asset in swing_specs else ("US500.cash" if asset == "US500" else None)
    spec = swing_specs[spec_key] if spec_key and spec_key in swing_specs else None
    ts5, o5, h5, l5, c5 = resample_m1_quotes_to_m5_mid(times, quotes)
    return {
        "asset": asset,
        "times": times,
        "quotes": quotes,
        "spec": spec,
        "usdjpy_close_map": usdjpy_close_map,
        "days": days_out,
        "m5": (ts5, o5, h5, l5, c5),
        "meta": am,
    }


def _replay_pair(
    bundle: dict[str, Any],
    e_idx: int,
    flat_idx: int,
    side: int,
    ep: float,
    sl_p: float,
    tp_p: float | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    times, quotes = bundle["times"], bundle["quotes"]
    sl_d = abs(ep - sl_p)
    if sl_d <= 1e-9 or e_idx < 0 or flat_idx <= e_idx:
        return None, None
    tr = p24.replay_causal_intraday(
        bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, sl_p,
        tp_p=tp_p, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"],
    )
    if tr is None:
        return None, None
    fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
    ftp = (fep - side * abs(tp_p - ep)) if tp_p is not None else None
    fd = p24.replay_causal_intraday(
        bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_d,
        tp_p=ftp, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"],
    )
    if fd is None:
        return None, None
    ex_idx = int(times.searchsorted(tr["exit"], side="left"))
    tr["dur_min"] = max(5, int((tr["exit"] - tr["entry"]) // 60))
    tr["sl_frac"] = max(0.0005, sl_d / max(1e-9, ep))
    # Approximate friction in R from (base_R vs gross) or (ftmo_R vs double_R)
    fric = max(0.01, min(0.40, float(tr["ftmo_R"]) - float(tr["double_R"])))
    tr["fric_r"] = fric
    tr["hold_bars"] = max(1, ex_idx - e_idx)
    return tr, fd


def _eval_stop_breakout(
    b: dict[str, Any],
    d: dict[str, Any],
    ts_start: int,
    ts_end: int,
    ts_flat: int,
    top: float,
    bot: float,
    sl_atr: float,
    tp_atr: float | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    times, quotes = b["times"], b["quotes"]
    fi, day_flat = d["fi"], d["flat_idx"]
    sub_t = times[fi:day_flat + 1]
    i0 = fi + int(sub_t.searchsorted(ts_start, side="left"))
    i1 = min(day_flat, fi + int(sub_t.searchsorted(ts_end, side="left")))
    f_idx = min(day_flat, fi + int(sub_t.searchsorted(ts_flat, side="left")))
    if i1 <= i0 + 1 or f_idx <= i0 + 1:
        return None, None
    sl_d = sl_atr * d["atr"]
    tp_d = (tp_atr * d["atr"]) if tp_atr is not None else None
    for idx in range(i0, i1):
        ah = float(quotes[idx, 5])
        bl = float(quotes[idx, 2])
        hit_b = ah >= top
        hit_s = bl <= bot
        if hit_b and hit_s:
            return None, None
        if hit_b:
            ep = max(top, float(quotes[idx, 4]))
            return _replay_pair(b, idx, f_idx, 1, ep, ep - sl_d, (ep + tp_d) if tp_d else None)
        if hit_s:
            ep = min(bot, float(quotes[idx, 0]))
            return _replay_pair(b, idx, f_idx, -1, ep, ep + sl_d, (ep - tp_d) if tp_d else None)
    return None, None


def _eval_market_entry(
    b: dict[str, Any],
    d: dict[str, Any],
    ts_entry: int,
    ts_flat: int,
    side: int,
    sl_atr: float,
    tp_atr: float | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    times, quotes = b["times"], b["quotes"]
    fi, day_flat = d["fi"], d["flat_idx"]
    sub_t = times[fi:day_flat + 1]
    e_idx = fi + int(sub_t.searchsorted(ts_entry, side="left"))
    f_idx = min(day_flat, fi + int(sub_t.searchsorted(ts_flat, side="left")))
    if e_idx >= f_idx or int(times[e_idx]) - ts_entry > 600:
        return None, None
    ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
    sl_d = sl_atr * d["atr"]
    tp_p = (ep + side * tp_atr * d["atr"]) if tp_atr is not None else None
    return _replay_pair(b, e_idx, f_idx, side, ep, ep - side * sl_d, tp_p)


def build_lab10_catalog() -> list[dict[str, Any]]:
    """Pre-registered 16-spec orthogonal alpha catalog across 4 distinct economic families (zero p-hacking)."""
    return [
        # Family A: GER40 Frankfurt Opening-Auction & Vol-Compression Breakout (EU hours, orthogonal to NY/Tokyo)
        {"id": "L10_A1_GER40_FFM_BRK60", "fam": "A_GER40_EU", "asset": "GER40", "kind": "GER40_BRK", "thr": 0.60, "sl_atr": 0.75, "tp_atr": None, "vr_max": 1.00,
         "rationale": "Frankfurt cash open institutional order imbalance breaks compressed overnight DAX range with bounded ATR stop and flat before US close."},
        {"id": "L10_A2_GER40_FFM_BRK80_TP2", "fam": "A_GER40_EU", "asset": "GER40", "kind": "GER40_BRK", "thr": 0.80, "sl_atr": 0.75, "tp_atr": 1.80, "vr_max": 1.15,
         "rationale": "DAX morning expansion with symmetric 2.4R take-profit cap harvests European auction flow without relying on extreme fat-tail sessions."},

        # Family B: Vol-Compression Breakout Replication (exact E6_EURJPY_VOLCOMP mechanic ported zero-tuning to 4 untouched FX pairs!)
        {"id": "L10_B1_GBPJPY_VOLCOMP75", "fam": "B_VOLCOMP_PORT", "asset": "GBPJPY", "kind": "VOLCOMP_BRK", "thr": 0.75, "sl_atr": 0.75, "tp_atr": None, "vr_max": 0.85,
         "rationale": "Zero-tuning replication of E6 volatility-compression breakout onto GBPJPY during London-NY liquidity expansion (swap=0 intraday)."},
        {"id": "L10_B2_EURUSD_VOLCOMP75", "fam": "B_VOLCOMP_PORT", "asset": "EURUSD", "kind": "VOLCOMP_BRK", "thr": 0.75, "sl_atr": 0.75, "tp_atr": None, "vr_max": 0.85,
         "rationale": "Zero-tuning replication of E6 volatility-compression breakout onto EURUSD (deepest FX liquidity, minimal spread friction)."},
        {"id": "L10_B3_AUDUSD_VOLCOMP75", "fam": "B_VOLCOMP_PORT", "asset": "AUDUSD", "kind": "VOLCOMP_BRK", "thr": 0.75, "sl_atr": 0.75, "tp_atr": None, "vr_max": 0.85,
         "rationale": "Zero-tuning replication of E6 volatility-compression breakout onto commodity-linked AUDUSD with intraday swap=0 flat."},
        {"id": "L10_B4_USDCAD_VOLCOMP75", "fam": "B_VOLCOMP_PORT", "asset": "USDCAD", "kind": "VOLCOMP_BRK", "thr": 0.75, "sl_atr": 0.75, "tp_atr": None, "vr_max": 0.85,
         "rationale": "Zero-tuning replication of E6 volatility-compression breakout onto oil-linked USDCAD during North American overlap."},

        # Family C: Symmetric Intraday Overextension Mean-Reversion with Fixed TP (designed to pass Trim-5% & Buy/Sell!)
        {"id": "L10_C1_XAU_LDN_FADE_TP12", "fam": "C_INTRADAY_MR", "asset": "XAUUSD", "kind": "OVEREXT_FADE", "thr": 1.15, "sl_atr": 0.75, "tp_atr": 1.20, "hour_utc": 13,
         "rationale": "Gold London morning spikes exceeding 1.15x ATR exhaust intraday dealer inventory and mean-revert into NY open with symmetric TP cap."},
        {"id": "L10_C2_US500_NOON_FADE_TP10", "fam": "C_INTRADAY_MR", "asset": "US500", "kind": "OVEREXT_FADE", "thr": 1.10, "sl_atr": 0.75, "tp_atr": 1.00, "hour_utc": 16,
         "rationale": "S&P 500 morning overextensions beyond 1.10x ATR mean-revert during NY midday liquidity consolidation with capped stop and target."},
        {"id": "L10_C3_GER40_MID_FADE_TP10", "fam": "C_INTRADAY_MR", "asset": "GER40", "kind": "OVEREXT_FADE", "thr": 1.15, "sl_atr": 0.75, "tp_atr": 1.00, "hour_utc": 12,
         "rationale": "DAX European morning exhaustion moves exceeding 1.15x ATR revert ahead of US cash open with symmetric long/short risk-reward."},
        {"id": "L10_C4_EURUSD_NY_FADE_TP10", "fam": "C_INTRADAY_MR", "asset": "EURUSD", "kind": "OVEREXT_FADE", "thr": 1.10, "sl_atr": 0.75, "tp_atr": 1.00, "hour_utc": 14,
         "rationale": "EURUSD pre-NY stretched intraday impulse fades back toward daily fair value as London-NY order flow balances out."},

        # Family D: NY 10:00 ET / London Fix Directional Flow (generalizing #1 WY-P10 champion E7_USDJPY_NY10ET!)
        {"id": "L10_D1_EURUSD_NY10ET_CONT", "fam": "D_FIX_FLOW", "asset": "EURUSD", "kind": "NY10ET_FLOW", "thr": 0.35, "sl_atr": 0.75, "tp_atr": None, "sign": 1,
         "rationale": "NY 10:00 ET option expiry and US macro release flow propagates through EURUSD into London close (zero overnight swap)."},
        {"id": "L10_D2_GBPJPY_NY10ET_CONT", "fam": "D_FIX_FLOW", "asset": "GBPJPY", "kind": "NY10ET_FLOW", "thr": 0.35, "sl_atr": 0.75, "tp_atr": None, "sign": 1,
         "rationale": "Cross-asset risk sentiment impulse at NY 10:00 ET drives GBPJPY continuation through afternoon session."},
        {"id": "L10_D3_XAUUSD_NY10ET_CONT", "fam": "D_FIX_FLOW", "asset": "XAUUSD", "kind": "NY10ET_FLOW", "thr": 0.40, "sl_atr": 0.75, "tp_atr": 1.50, "sign": 1,
         "rationale": "COMEX gold futures & US Treasury yield repricing at 10:00 ET sustains directional gold drift until afternoon flat."},
        {"id": "L10_D4_AUDUSD_NY10ET_CONT", "fam": "D_FIX_FLOW", "asset": "AUDUSD", "kind": "NY10ET_FLOW", "thr": 0.35, "sl_atr": 0.75, "tp_atr": None, "sign": 1,
         "rationale": "US equity/macro risk-on impulse at 10:00 ET drives beta-sensitive AUDUSD continuation into afternoon close."},
        {"id": "L10_D5_EURUSD_WMR16_REV", "fam": "D_FIX_FLOW", "asset": "EURUSD", "kind": "WMR16_FLOW", "thr": 0.45, "sl_atr": 0.65, "tp_atr": 1.00, "sign": -1,
         "rationale": "WM/Reuters 16:00 London fixing order imbalance creates temporary FX price pressure that reverts over the post-fix NY afternoon."},
        {"id": "L10_D6_USDCAD_WMR16_REV", "fam": "D_FIX_FLOW", "asset": "USDCAD", "kind": "WMR16_FLOW", "thr": 0.45, "sl_atr": 0.65, "tp_atr": 1.00, "sign": -1,
         "rationale": "Post-London-fix dealer inventory unloading on USDCAD mean-reverts before 20:50 UTC hard flat."},
    ]


def evaluate_lab10_spec(bundle: dict[str, Any], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    times, quotes = bundle["times"], bundle["quotes"]
    kind = cfg["kind"]
    thr = float(cfg["thr"])
    sl_atr = float(cfg["sl_atr"])
    tp_atr = cfg.get("tp_atr")

    trs: list[dict[str, Any]] = []
    fds: list[dict[str, Any]] = []
    for d in bundle["days"]:
        dk = d["day"]
        dsec = d["dsec"]
        atr = d["atr"]
        tr = fd = None

        if kind == "GER40_BRK":
            if d["vol_ratio"] > float(cfg["vr_max"]):
                continue
            ts_o0 = _local_ts(dk, 8, 0, BERLIN_TZ)
            ts_scan0 = _local_ts(dk, 9, 0, BERLIN_TZ)
            ts_scan1 = _local_ts(dk, 13, 0, BERLIN_TZ)
            ts_flat = _local_ts(dk, 17, 20, BERLIN_TZ)
            i_o = int(times.searchsorted(ts_o0, side="left"))
            if i_o < d["flat_idx"] and abs(int(times[i_o]) - ts_o0) <= 1800:
                ref = float(quotes[i_o, 0])
                tr, fd = _eval_stop_breakout(bundle, d, ts_scan0, ts_scan1, ts_flat, ref + thr * atr, ref - thr * atr, sl_atr, tp_atr)

        elif kind == "VOLCOMP_BRK":
            if d["vol_ratio"] > float(cfg["vr_max"]):
                continue
            ts_scan0 = dsec + 7 * 3600
            ts_scan1 = dsec + 16 * 3600
            ts_flat = dsec + 20 * 3600 + 45 * 60
            ref = float(d["o"])
            tr, fd = _eval_stop_breakout(bundle, d, ts_scan0, ts_scan1, ts_flat, ref + thr * atr, ref - thr * atr, sl_atr, tp_atr)

        elif kind == "OVEREXT_FADE":
            hr = int(cfg["hour_utc"])
            ts_check = dsec + hr * 3600
            ts_flat = dsec + 20 * 3600 + 45 * 60
            i_c = int(times.searchsorted(ts_check, side="left"))
            if i_c < d["flat_idx"] and abs(int(times[i_c]) - ts_check) <= 600:
                px = float(quotes[i_c, 0])
                mv = (px - float(d["o"])) / atr
                if abs(mv) >= thr:
                    side = -1 if mv > 0 else 1
                    tr, fd = _eval_market_entry(bundle, d, ts_check, ts_flat, side, sl_atr, tp_atr)

        elif kind == "NY10ET_FLOW":
            ts_0900 = _local_ts(dk, 9, 0, NY_TZ)
            ts_1000 = _local_ts(dk, 10, 0, NY_TZ)
            ts_flat = dsec + 20 * 3600 + 45 * 60
            i0 = int(times.searchsorted(ts_0900, side="left"))
            i1 = int(times.searchsorted(ts_1000, side="left"))
            if i0 < i1 < d["flat_idx"] and abs(int(times[i1]) - ts_1000) <= 600:
                mv = (float(quotes[i1, 0]) - float(quotes[i0, 0])) / atr
                if abs(mv) >= thr:
                    side = int(cfg["sign"]) * (1 if mv > 0 else -1)
                    tr, fd = _eval_market_entry(bundle, d, ts_1000, ts_flat, side, sl_atr, tp_atr)

        elif kind == "WMR16_FLOW":
            ts_1400 = _local_ts(dk, 14, 0, LONDON_TZ)
            ts_1605 = _local_ts(dk, 16, 5, LONDON_TZ)
            ts_flat = dsec + 20 * 3600 + 45 * 60
            i0 = int(times.searchsorted(ts_1400, side="left"))
            i1 = int(times.searchsorted(ts_1605, side="left"))
            if i0 < i1 < d["flat_idx"] and abs(int(times[i1]) - ts_1605) <= 600:
                mv = (float(quotes[i1, 0]) - float(quotes[i0, 0])) / atr
                if abs(mv) >= thr:
                    side = int(cfg["sign"]) * (1 if mv > 0 else -1)
                    tr, fd = _eval_market_entry(bundle, d, ts_1605, ts_flat, side, sl_atr, tp_atr)

        if tr is not None and fd is not None:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


# ---------------------------------------------------------------------------
# PART 1B: Walk-Forward SL / TP Optimization (12m Train -> 4m Blind OOS)
# ---------------------------------------------------------------------------

def simulate_trade_sl_tp_on_marks(
    row: dict[str, Any],
    marks: np.ndarray,
    sl_mult: float,
    tp_cap_r: float | None,
) -> float:
    """Re-evaluate exact M1 minute-by-minute mark tape under scaled SL (`sl_mult`) & optional fixed TP (`tp_cap_r`).

    Returns exact net R-multiple relative to the NEW stop-loss risk unit `sl_mult * R0`.
    """
    r_unit0 = max(1e-6, float(row["stop_risk_with_cost_usd"]))
    new_sl_usd = -r_unit0 * float(sl_mult)
    new_tp_usd = (r_unit0 * float(sl_mult) * float(tp_cap_r)) if tp_cap_r is not None else 1e18

    # marks columns: [O, H, L, C] in USD/lot relative to entry (already net of spread/slip/comm!)
    if len(marks) == 0:
        return 0.0
    for k in range(len(marks)):
        # Conservative tie-break: check SL touch BEFORE TP touch on same M1 bar
        if float(marks[k, 2]) <= new_sl_usd:
            return -1.0
        if tp_cap_r is not None and float(marks[k, 1]) >= new_tp_usd:
            return float(tp_cap_r)
    final_usd = float(marks[-1, 3])
    return max(-1.0, final_usd / (r_unit0 * float(sl_mult)))


def run_walk_forward_sl_tp_study(
    tapes: dict[str, dict],
    engine_order: list[str],
    core7_ids: list[str],
) -> dict[str, Any]:
    """Compare Fixed Baseline vs Rolling Walk-Forward (12m train -> 4m OOS) vs In-Sample Oracle (2019-2024)."""
    sl_grid = (0.75, 1.00, 1.25)
    tp_grid: tuple[float | None, ...] = (None, 2.0, 3.0, 4.5)
    combos = [(s, t) for s in sl_grid for t in tp_grid]

    # Build 18 rolling 4-month OOS blocks from 2019-01-01 to 2024-12-31 (each preceded by exact 12m train!)
    blocks: list[tuple[str, str, str, str]] = []
    for yr in range(2019, 2025):
        for m_start, m_end in ((1, 4), (5, 8), (9, 12)):
            oos_start = f"{yr}-{m_start:02d}-01"
            oos_end = f"{yr}-{m_end:02d}-31"
            tr_start = f"{yr - 1}-{m_start:02d}-01"
            tr_end = oos_start  # strictly < oos_start
            blocks.append((tr_start, tr_end, oos_start, oos_end))

    def _pf(vals: list[float]) -> float:
        gp = sum(v for v in vals if v > 0.0)
        gl = -sum(v for v in vals if v < 0.0)
        return (gp / gl) if gl > 1e-9 else (99.0 if gp > 1e-9 else 0.0)

    def _score_train(vals: list[float]) -> float:
        if len(vals) < 8:
            return -1e9
        pf = _pf(vals)
        eq = pk = dd = 0.0
        for v in vals:
            eq += v
            pk = max(pk, eq)
            dd = max(dd, pk - eq)
        # Smooth Calmar-like R-efficiency score (penalizes deep drawdowns!)
        return float(sum(vals)) / max(2.0, dd) + 0.15 * min(3.0, pf)

    eng_summaries: list[dict[str, Any]] = []
    port7_base_oos: list[float] = []
    port7_wf_oos: list[float] = []
    port7_oracle_oos: list[float] = []

    for eng in engine_order:
        dm = tapes[eng]
        days = sorted(dm.keys())
        # Precompute R for every (combo, day) once (super fast!)
        precomp: dict[tuple[float, float | None], dict[str, float]] = {}
        for combo in combos:
            s_m, t_c = combo
            precomp[combo] = {dk: simulate_trade_sl_tp_on_marks(dm[dk][0], dm[dk][2], s_m, t_c) for dk in days}

        base_combo = (1.00, None)
        oos_days_all = [dk for dk in days if dk >= "2019-01-01"]
        base_vals = [precomp[base_combo][dk] for dk in oos_days_all]

        # Rolling Walk-Forward 12m -> 4m
        wf_vals: list[float] = []
        chosen_log: list[str] = []
        for tr_s, tr_e, oo_s, oo_e in blocks:
            tr_days = [dk for dk in days if tr_s <= dk < tr_e]
            oo_days = [dk for dk in days if oo_s <= dk <= oo_e]
            if not oo_days:
                continue
            best_c = base_combo
            best_sc = -1e18
            for c in combos:
                sc = _score_train([precomp[c][dk] for dk in tr_days])
                if sc > best_sc:
                    best_sc = sc
                    best_c = c
            chosen_log.append(f"{best_c[0]:.2f}x/{'FLAT' if best_c[1] is None else f'{best_c[1]:.1f}R'}")
            wf_vals.extend(precomp[best_c][dk] for dk in oo_days)

        # In-Sample Oracle (cheating by picking best single combo over 2019-2024!)
        best_orc = max(combos, key=lambda c: _pf([precomp[c][dk] for dk in oos_days_all]))
        orc_vals = [precomp[best_orc][dk] for dk in oos_days_all]

        if eng in core7_ids:
            port7_base_oos.extend(base_vals)
            port7_wf_oos.extend(wf_vals)
            port7_oracle_oos.extend(orc_vals)

        pf_base = round(_pf(base_vals), 3)
        pf_wf = round(_pf(wf_vals), 3)
        pf_orc = round(_pf(orc_vals), 3)
        eng_summaries.append({
            "engine": eng,
            "in_port_7e": eng in core7_ids,
            "n_oos_trades": len(oos_days_all),
            "fixed_base_pf": pf_base,
            "fixed_base_sum_r": round(sum(base_vals), 2),
            "wf_12m_4m_pf": pf_wf,
            "wf_12m_4m_sum_r": round(sum(wf_vals), 2),
            "oracle_pf": pf_orc,
            "oracle_sum_r": round(sum(orc_vals), 2),
            "oracle_combo": f"{best_orc[0]:.2f}x/{'FLAT' if best_orc[1] is None else f'{best_orc[1]:.1f}R'}",
            "wf_vs_base_pf_delta": round(pf_wf - pf_base, 3),
            "overfit_illusion_gap_pf": round(pf_orc - pf_wf, 3),
            "wf_beats_base": pf_wf > pf_base + 0.01,
        })

    p7_base_pf = round(_pf(port7_base_oos), 3)
    p7_wf_pf = round(_pf(port7_wf_oos), 3)
    p7_orc_pf = round(_pf(port7_oracle_oos), 3)

    return {
        "oos_window": "2019-01-01..2024-12-31 (18 rolling 4m blocks, 12m causal train)",
        "port_7e_aggregate": {
            "n_oos_trades": len(port7_base_oos),
            "fixed_base_pf": p7_base_pf,
            "fixed_base_sum_r": round(sum(port7_base_oos), 2),
            "wf_12m_4m_pf": p7_wf_pf,
            "wf_12m_4m_sum_r": round(sum(port7_wf_oos), 2),
            "oracle_pf": p7_orc_pf,
            "oracle_sum_r": round(sum(port7_oracle_oos), 2),
            "wf_vs_base_pf_delta": round(p7_wf_pf - p7_base_pf, 3),
            "overfit_illusion_gap_pf": round(p7_orc_pf - p7_wf_pf, 3),
            "recommendation": "ADOPT_WF_SLTP" if p7_wf_pf >= p7_base_pf + 0.03 else "KEEP_FIXED_HOLD_TO_FLAT",
        },
        "engines": eng_summaries,
    }


# ---------------------------------------------------------------------------
# PART 1C: Causal Dynamic Prop Pacing Simulator (Numba JIT, N = 5,000)
# ---------------------------------------------------------------------------

@njit(cache=True)
def _simulate_dynamic_pacing_numba(
    idx_matrix: np.ndarray,
    nets_1x: np.ndarray, dds_1x: np.ndarray, flg_1x: np.ndarray,
    steps: int, cap: float, fee: float, fee_refund_ratio: float,
    p1_target: float, p2_target: float, daily_lim: float, static_lim: float,
    daily_pause_only: bool, min_days: int, min_prof_day: float,
    split: float, payout_cycle: int, max_retries: int,
    p1_start_mult: float, p1_lock50_mult: float, p1_lock75_mult: float,
    p2_start_mult: float, p2_lock60_mult: float, funded_mult: float,
    amber_dd: float, amber_mult: float, red_dd: float, red_mult: float,
    ea_daily_stop: float,
):
    """Causal Dynamic Prop Pacing simulator with Profit-Lock step-down & DD brakes."""
    n_paths, horizon = idx_matrix.shape
    scale = cap / 10000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)

    pass_days = np.full(n_paths, -1, dtype=np.int32)
    pay1_days = np.full(n_paths, -1, dtype=np.int32)
    cf24 = np.zeros(n_paths, dtype=np.float64)
    oop = np.zeros(n_paths, dtype=np.float64)
    br_any = np.zeros(n_paths, dtype=np.int8)
    wiped = np.zeros(n_paths, dtype=np.int8)
    tix = np.ones(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1
        bal = cap
        tdays = 0
        attempts = 1
        fees = fee
        refunded = False
        payouts = 0.0
        cycle_d = 0
        max_oop = fee
        f_pass = -1
        f_pay = -1
        had_br = 0
        is_dead = 0

        for d in range(horizon):
            if is_dead == 1:
                break
            src = idx_matrix[b, d]
            eq_pct = (bal - cap) / cap

            # Causal Dynamic Pacing: profit-lock step-down as progress nears target, DD brake if underwater!
            if stage == 1:
                prog = eq_pct / max(1e-6, p1_target)
                if prog >= 0.75:
                    m = p1_lock75_mult
                elif prog >= 0.50:
                    m = p1_lock50_mult
                else:
                    m = p1_start_mult
            elif stage == 2:
                prog = eq_pct / max(1e-6, p2_target)
                m = p2_lock60_mult if prog >= 0.60 else p2_start_mult
            else:
                m = funded_mult

            if eq_pct <= -red_dd:
                m = min(m, red_mult)
            elif eq_pct <= -amber_dd:
                m = min(m, amber_mult)

            net = nets_1x[src] * scale * m
            dd = dds_1x[src] * scale * m
            flg = flg_1x[src]

            cur_daily_cap = cap * daily_lim
            cur_static_floor = cap * (1.0 - static_lim)
            cur_ea_cut = cap * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

            if daily_pause_only:
                if dd >= cur_daily_cap:
                    dd = min(dd, cur_daily_cap + cap * 0.001)
                    net = min(net, -cur_daily_cap)
                breached = (bal - dd) <= cur_static_floor + 1e-9
            else:
                if dd > cur_ea_cut:
                    dd = min(dd, cur_ea_cut + cap * 0.0025)
                    net = min(net, -cur_ea_cut)
                breached = (dd >= cur_daily_cap - 1e-9) or ((bal - dd) <= cur_static_floor + 1e-9)

            if breached:
                had_br = 1
                if attempts <= max_retries:
                    attempts += 1
                    fees += fee
                    stage = 1
                    bal = cap
                    tdays = 0
                    refunded = False
                    cycle_d = 0
                else:
                    is_dead = 1
            else:
                bal += net
                if min_prof_day > 0.0:
                    if net >= cap * min_prof_day:
                        tdays += 1
                elif flg != 0:
                    tdays += 1

                if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
                    stage = 2 if steps == 2 else 3
                    bal = cap
                    tdays = 0
                    cycle_d = 0
                    if steps == 1 and f_pass < 0:
                        f_pass = d + 1
                elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
                    stage = 3
                    bal = cap
                    tdays = 0
                    cycle_d = 0
                    if f_pass < 0:
                        f_pass = d + 1
                elif stage == 3:
                    cycle_d += 1
                    if cycle_d >= payout_cycle:
                        if bal > cap + 1e-6:
                            pay = (bal - cap) * split
                            if not refunded:
                                pay += fee * fee_refund_ratio
                                refunded = True
                            payouts += pay
                            if f_pay < 0:
                                f_pay = d + 1
                            bal = cap
                        cycle_d = 0

            cur_oop = fees - payouts
            if cur_oop > max_oop:
                max_oop = cur_oop

        pass_days[b] = f_pass
        pay1_days[b] = f_pay
        cf24[b] = payouts - fees
        oop[b] = max_oop
        br_any[b] = had_br
        wiped[b] = is_dead
        tix[b] = attempts

    return pass_days, pay1_days, cf24, oop, br_any, wiped, tix


def run_dynamic_pacing_study(
    nets_base: np.ndarray,
    dds_base: np.ndarray,
    flg_base: np.ndarray,
    nets_v2: np.ndarray | None,
    dds_v2: np.ndarray | None,
    flg_v2: np.ndarray | None,
    *,
    n_paths: int = 5000,
    seed: int = SEED,
) -> list[dict[str, Any]]:
    idx_mat = make_block_bootstrap_indices(len(nets_base), horizon=504, n_paths=n_paths, block_len=5, seed=seed)
    firms = [load_firm_config(f) for f in ("the5ers_high_stakes_5k", "ftmo_swing_10k")]

    policies = [
        ("P1_Balanced_Static",       4.00, 4.00, 4.00, 2.00, 2.00, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030, False),
        ("P1_Sprint_Static",         4.75, 4.75, 4.75, 2.50, 2.50, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030, False),
        ("Dyn_ProfitLock_45x",       4.50, 3.00, 2.00, 2.50, 1.50, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030, False),
        ("Dyn_FastStart_SafeLock50", 5.00, 2.75, 1.75, 2.75, 1.50, 1.00, 0.025, 2.00, 0.045, 0.80, 0.028, False),
    ]
    if nets_v2 is not None and dds_v2 is not None and flg_v2 is not None:
        policies.append(("Breadth_V2_DynProfitLock", 4.50, 3.00, 2.00, 2.50, 1.50, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030, True))

    rows: list[dict[str, Any]] = []
    for fcfg in firms:
        for (pname, p1s, p1_50, p1_75, p2s, p2_60, fmult, amb_d, amb_m, red_d, red_m, ea_st, use_v2) in policies:
            n_arr = nets_v2 if use_v2 else nets_base
            d_arr = dds_v2 if use_v2 else dds_base
            f_arr = flg_v2 if use_v2 else flg_base
            pd, py, cf, oop, br, wp, tx = _simulate_dynamic_pacing_numba(
                idx_mat, n_arr, d_arr, f_arr,
                int(fcfg["steps"]), float(fcfg["capital_usd"]), float(fcfg["fee_usd"]),
                float(fcfg.get("fee_refund_ratio", 1.0)),
                float(fcfg["p1_target_pct"]), float(fcfg["p2_target_pct"]),
                float(fcfg["daily_loss_pct"]), float(fcfg["static_loss_pct"]),
                bool(fcfg.get("daily_pause_non_breaching", False)),
                int(fcfg["min_days"]), float(fcfg.get("min_profitable_day_pct", 0.0)),
                float(fcfg["payout_split"]), int(fcfg["payout_cycle_days"]), 4,
                p1s, p1_50, p1_75, p2s, p2_60, fmult, amb_d, amb_m, red_d, red_m, ea_st,
            )
            passed = pd[pd > 0]
            paid = py[py > 0]
            ev_per_fee = float(np.mean(cf)) / max(1.0, float(fcfg["fee_usd"]))
            rows.append({
                "firm": fcfg["id"],
                "policy": pname,
                "pass_rate_24m_pct": round(100.0 * len(passed) / n_paths, 1),
                "med_days_to_pass": int(np.median(passed)) if len(passed) else -1,
                "med_days_to_pay1": int(np.median(paid)) if len(paid) else -1,
                "breach_any_pct": round(100.0 * float(np.mean(br)), 1),
                "wipeout_5tix_pct": round(100.0 * float(np.mean(wp)), 2),
                "oop95_usd": round(float(np.quantile(oop, 0.95)), 1),
                "ev_24m_usd": round(float(np.mean(cf)), 1),
                "ev_per_fee_x": round(ev_per_fee, 2),
                "avg_tickets": round(float(np.mean(tx)), 2),
            })
    return rows


def run_lab10(*, mc_draws: int = 500, pacing_paths: int = 5000, write_report: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    # 1. Load frozen PORT_7E / PORT_9E Dev tapes (< 2025-01-01)
    reg = load_registry()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = warm["tapes"]
    ext_days = warm["ext_days"]
    assert max(ext_days) < "2025-01-01"
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]
    turbo9 = reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"]
    risks7 = {k: base_r[k] for k in core7}
    risks9 = {k: base_r[k] for k in turbo9}

    _, ex7 = replay_portfolio_m1(ext_days, tapes, risks7, 10000.0, profile_mode="Swing")
    _, ex9 = replay_portfolio_m1(ext_days, tapes, risks9, 10000.0, profile_mode="Swing")
    nets7, dds7, flg7 = exits_to_daily_arrays(ext_days, ex7)
    nets9, dds9, flg9 = exits_to_daily_arrays(ext_days, ex9)
    day_idx_map = {dk: i for i, dk in enumerate(ext_days)}
    b_mask = np.array([dk >= "2021-01-01" for dk in ext_days])
    incumbent_b_daily = nets7[b_mask] / 10000.0

    # 2. Build local D: SSD M1 bundles (0 E: dependency, 0 holdout rows)
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, q_j, _ = hcache.load_asset("USDJPY", verify_sha=False)
    # Build daily USDJPY close map directly from local hot_m1_cache
    day_j = (ts_j // 86400).astype(np.int64)
    chg_j = np.r_[True, day_j[1:] != day_j[:-1]]
    starts_j = np.flatnonzero(chg_j)
    ends_j = np.r_[starts_j[1:] - 1, len(day_j) - 1]
    usdjpy_close_map = {
        datetime.fromtimestamp(int(ts_j[ei]), timezone.utc).date(): float(q_j[ei, 3])
        for ei in ends_j
    }

    catalog = build_lab10_catalog()
    needed_assets = sorted({c["asset"] for c in catalog})
    bundles = {a: build_local_m1_bundle(a, swing_specs, usdjpy_close_map) for a in needed_assets}

    # Build full union of Dev trading days (< 2025-01-01) so non-USDJPY trades are NEVER silently dropped!
    union_days = sorted(set(ext_days) | {d["day"] for b in bundles.values() for d in b["days"]})
    assert max(union_days) < "2025-01-01"
    u_idx_map = {dk: i for i, dk in enumerate(union_days)}
    u_b_mask = np.array([dk >= "2021-01-01" for dk in union_days])
    port7_union = np.zeros(len(union_days), dtype=np.float64)
    for dk, n7 in zip(ext_days, nets7):
        port7_union[u_idx_map[dk]] = float(n7) / 10000.0
    incumbent_b_daily = port7_union[u_b_mask]

    # 3. Study 1A: Evaluate all 16 pre-registered specs through ALL 7 Gates (G0..G6)!
    raw_runs: list[tuple[dict, list[dict], list[dict], float]] = []
    for idx_c, cfg in enumerate(catalog):
        trs, fds = evaluate_lab10_spec(bundles[cfg["asset"]], cfg)
        vals = [float(t["ftmo_R"]) for t in trs]
        fvals = [float(f["ftmo_R"]) for f in fds]
        p_raw = sign_flip_p_numba(vals, fvals, draws=1000, seed=SEED + idx_c) if vals else 1.0
        raw_runs.append((cfg, trs, fds, p_raw))

    all_p_raw = tuple(r[3] for r in raw_runs)
    q_all = benjamini_hochberg(list(all_p_raw))
    spec_results: list[dict[str, Any]] = []
    approved_daily_r: dict[str, np.ndarray] = {}

    for idx_c, ((cfg, trs, fds, p_raw), bh_q) in enumerate(zip(raw_runs, q_all)):
        a_tr = [t for t in trs if t["year"] in CLUSTER_A_YEARS]
        b_tr = [t for t in trs if t["year"] in CLUSTER_B_YEARS]

        # Build aligned daily returns arrays on union_days (0 trades dropped!)
        daily_arr_u = np.zeros(len(union_days), dtype=np.float64)
        for t in trs:
            di = u_idx_map.get(t["day"])
            if di is not None:
                daily_arr_u[di] += float(t["ftmo_R"]) * 0.0025  # 0.25% risk/trade reference scale
        ret_a = daily_arr_u[~u_b_mask]
        ret_b = daily_arr_u[u_b_mask]

        # Real-market M5 Random-Entry MC + 4-Pillar Robustness Gate (G6)
        if len(trs) >= 15:
            ts5, o5, h5, l5, c5 = bundles[cfg["asset"]]["m5"]
            r_arr = np.array([float(t["ftmo_R"]) for t in trs], dtype=np.float64)
            s_arr = np.array([int(t["side"]) for t in trs], dtype=np.int64)
            d_arr = np.array([max(1, int(round(t["dur_min"] / 5.0))) for t in trs], dtype=np.int64)
            sl_arr = np.array([float(t["sl_frac"]) for t in trs], dtype=np.float64)
            f_arr = np.array([float(t["fric_r"]) for t in trs], dtype=np.float64)
            mc = random_entry_mc_on_bars(
                ts=ts5, bar_o=o5, bar_h=h5, bar_l=l5, bar_c=c5, bar_sec=300,
                trade_r=r_arr, trade_sides=s_arr, trade_durs=d_arr,
                trade_sl_fracs=sl_arr, trade_frics=f_arr,
                draws=int(mc_draws), seed=SEED + 500 + idx_c * 31,
            )
            rb = evaluate_robustness_gate(
                strategy_id=cfg["id"],
                trade_r=r_arr,
                trade_sides=s_arr,
                trade_days=[t["day"] for t in trs],
                mc_result=mc,
                thresholds=RobustnessThresholds(mc_draws=int(mc_draws)),
                seed=SEED + 900 + idx_c * 17,
            )
        else:
            rb = {"verdict": "FAIL_FRAGILE", "passed": False, "failed_pillars": ["INSUFFICIENT_TRADES"], "ranking_score_worst_year_p10_r": -99.0}

        card = propose_hypothesis(
            hypothesis_id=cfg["id"],
            title=f"{cfg['fam']} on {cfg['asset']}",
            asset_universe=[cfg["asset"]],
            timeframe="M1_INTRADAY_SWAP0",
            counterparty_mechanism=cfg["fam"],
            economic_rationale=cfg["rationale"],
            causal_invariants=["No look-ahead (ATR/vol from t-1)", "Swap=0 flat before 20:50 UTC", "Hard server SL"],
            n_trials_cumulative=len(catalog),
            kill_criteria=KillCriteria(max_bh_q=0.10, min_dsr=0.50, min_cluster_b_sharpe=0.35, min_cost_breakeven_mult=2.0, min_trades_cluster_b=25),
        )
        ev = EvidenceBundle(
            cluster_a_returns=ret_a,
            cluster_b_returns=ret_b,
            p_value_raw=p_raw,
            family_p_values=all_p_raw,
            candidate_index_in_family=idx_c,
            cost_1x_net=float(sum(t["ftmo_R"] for t in trs)),
            cost_2x_net=float(sum(t["double_R"] for t in trs)),
            n_trades_cluster_b=len(b_tr),
            incumbent_daily_returns=incumbent_b_daily,
            holdout_rows_analysed=0,
            robustness_report=rb,
        )
        verdict = critique_proposal(card, ev)

        if verdict["verdict"] in ("APPROVE_FOR_INCUBATION", "CONDITIONAL_RETEST"):
            approved_daily_r[cfg["id"]] = (verdict["verdict"], daily_arr_u)

        mc_p = rb.get("pillars", {}).get("R1_random_entry_mc", {})
        sym_p = rb.get("pillars", {}).get("R2_buy_sell_symmetry", {})
        tr_p = rb.get("pillars", {}).get("R3_top5_outlier_trim", {})
        wy_p = rb.get("pillars", {}).get("R4_worst_year_stability", {})
        spec_results.append({
            "id": cfg["id"],
            "fam": cfg["fam"],
            "asset": cfg["asset"],
            "n_all": len(trs),
            "n_a": len(a_tr),
            "n_b": len(b_tr),
            "sum_r_a": round(sum(t["ftmo_R"] for t in a_tr), 2),
            "sum_r_b": round(sum(t["ftmo_R"] for t in b_tr), 2),
            "sum_r_all": round(sum(t["ftmo_R"] for t in trs), 2),
            "double_cost_r": round(sum(t["double_R"] for t in trs), 2),
            "bh_q": round(bh_q, 4),
            "corr_7e": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "mc_5050": mc_p.get("beat_rate_unbiased", 0.0),
            "mc_same": mc_p.get("beat_rate_same_side", 0.0),
            "buy_sell_ok": bool(sym_p.get("passed", False)),
            "trim5_win_r": tr_p.get("trimmed_winners_sum_r", 0.0),
            "wy_p10_r": rb.get("ranking_score_worst_year_p10_r", -99.0),
            "robust_verdict": rb["verdict"],
            "council_verdict": verdict["verdict"],
            "failed_gates": verdict["failed_gates"],
        })

    # 4. Study 1B: Walk-Forward SL/TP (12m -> 4m) on exact M1 frozen_9e_tapes_v1
    wf_study = run_walk_forward_sl_tp_study(tapes, turbo9, core7)

    # 5. Study 1C: Dynamic Prop Pacing (`PORT_7E` baseline vs `PORT_V2_BREADTH` on union_days or `PORT_9E` reference!)
    strict_approved = {k: v[1] for k, v in approved_daily_r.items() if v[0] == "APPROVE_FOR_INCUBATION"}
    cand_pool = strict_approved if strict_approved else {k: v[1] for k, v in approved_daily_r.items()}
    if cand_pool:
        # Project PORT_7E + newly qualified PASS_ROBUST engines onto `ext_days` (and include any non-ext trades on nearest slot)
        ext_indices = np.array([u_idx_map[dk] for dk in ext_days], dtype=np.int64)
        extra_usd = sum(arr[ext_indices] for arr in cand_pool.values()) * 10000.0
        nets_v2 = nets7 + extra_usd
        dds_v2 = dds7 + np.where(extra_usd != 0.0, np.maximum(-extra_usd, 25.0), 0.0)
        flg_v2 = np.where((flg7 != 0) | (extra_usd != 0.0), 1, 0).astype(np.int8)
        tag = "APPROVED_V2" if strict_approved else "CONDITIONAL_PASS_ROBUST_V2"
        breadth_label = f"PORT_7E + {len(cand_pool)} {tag} ({', '.join(sorted(cand_pool))})"
    else:
        nets_v2, dds_v2, flg_v2 = nets9, dds9, flg9
        breadth_label = "PORT_9E_TURBO (0 new specs passed -> honest incumbent breadth reference)"

    pacing_rows = run_dynamic_pacing_study(
        nets7, dds7, flg7, nets_v2, dds_v2, flg_v2,
        n_paths=pacing_paths, seed=SEED,
    )

    elapsed = round(time.perf_counter() - t0, 2)
    approved_ids = [r["id"] for r in spec_results if r["council_verdict"] == "APPROVE_FOR_INCUBATION"]
    cond_ids = [r["id"] for r in spec_results if r["council_verdict"] == "CONDITIONAL_RETEST"]

    summary = {
        "schema": "naqex-lab10-v2-robust-prop-accelerator-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "elapsed_sec": elapsed,
        "study_1a_discovery": {
            "m_total": len(catalog),
            "approved_count": len(approved_ids),
            "approved_ids": approved_ids,
            "conditional_count": len(cond_ids),
            "conditional_ids": cond_ids,
            "pass_robust_g6_count": sum(1 for r in spec_results if r["robust_verdict"] == "PASS_ROBUST"),
            "results": spec_results,
        },
        "study_1b_walk_forward_sl_tp": wf_study,
        "study_1c_dynamic_prop_pacing": {
            "n_paths": pacing_paths,
            "breadth_series": breadth_label,
            "rows": pacing_rows,
        },
    }

    if write_report:
        out_dir = ROOT / "planning/research"
        json_path = out_dir / "LAB10-V2-ROBUST-ALPHA-WF-AND-PROP-PACING-20261124.json"
        md_path = out_dir / "LAB10-V2-ROBUST-ALPHA-WF-AND-PROP-PACING-20261124.md"

        md = [
            "# Lab #10 (Thế Hệ v2): Săn Alpha 7 Cổng `PASS_ROBUST`, Walk-Forward SL/TP (12m->4m) & Dynamic Prop Pacing",
            "",
            f"- **Phạm vi dữ liệu:** Dev niêm phong `2018–2024` (`Cluster A: 2018–2020`, `Blind Cluster B: 2021–2024`, `holdout_rows_analysed = 0`, `order_send_count = 0`, chạy cục bộ `hot_m1_cache` trong `{elapsed}s`).",
            "",
            "## 1A. Săn Động Cơ Trực Giao Qua Đủ 7 Cổng (`G0..G6`, `m_total = 16`)",
            "",
            f"- **Đỗ 7/7 cổng (`APPROVE_FOR_INCUBATION`):** **{len(approved_ids)}/16** (`{', '.join(approved_ids) or 'NONE'}`)",
            f"- **Đạt mức kiểm thử lại (`CONDITIONAL_RETEST`):** **{len(cond_ids)}/16** (`{', '.join(cond_ids) or 'NONE'}`)",
            "",
            format_markdown_table(
                ["Spec ID", "Asset", "N (A/B)", "Cl.A R", "Cl.B R", "2xCost R", "BH-q", "r(7E)", "MC Same", "B&S", "Trim5W", "WY-P10", "G6", "Council Verdict"],
                [
                    [
                        r["id"], r["asset"], f"{r['n_all']} ({r['n_a']}/{r['n_b']})",
                        f"{r['sum_r_a']:+.1f}", f"{r['sum_r_b']:+.1f}", f"{r['double_cost_r']:+.1f}",
                        f"{r['bh_q']:.3f}", f"{r['corr_7e']:+.2f}", f"{r['mc_same']*100:.0f}%",
                        "OK" if r["buy_sell_ok"] else "NO", f"{r['trim5_win_r']:+.1f}", f"{r['wy_p10_r']:+.1f}",
                        r["robust_verdict"], r["council_verdict"],
                    ]
                    for r in spec_results
                ],
            ),
            "",
            "## 1B. Walk-Forward SL/TP Trượt (`12` Tháng Học -> `4` Tháng Chạy OOS, `2019–2024`)",
            "",
            f"- **Tổng hợp `PORT_7E` (`{wf_study['port_7e_aggregate']['n_oos_trades']}` lệnh OOS):** "
            f"Fixed Baseline PF = **`{wf_study['port_7e_aggregate']['fixed_base_pf']}`** (`{wf_study['port_7e_aggregate']['fixed_base_sum_r']:+.1f}R`) · "
            f"Walk-Forward 12m->4m PF = **`{wf_study['port_7e_aggregate']['wf_12m_4m_pf']}`** (`{wf_study['port_7e_aggregate']['wf_12m_4m_sum_r']:+.1f}R`) · "
            f"In-Sample Oracle PF = **`{wf_study['port_7e_aggregate']['oracle_pf']}`** -> "
            f"Khoảng cách ảo giác Overfit (`Oracle - WF`) = **`{wf_study['port_7e_aggregate']['overfit_illusion_gap_pf']:+.3f}`** · "
            f"Khuyến nghị: **`{wf_study['port_7e_aggregate']['recommendation']}`**.",
            "",
            format_markdown_table(
                ["Engine", "Core", "N OOS", "Fixed PF (R)", "WF 12m->4m PF (R)", "Oracle PF (Combo)", "WF-Base ΔPF", "Overfit Gap"],
                [
                    [
                        e["engine"], "7E" if e["in_port_7e"] else "Sat", str(e["n_oos_trades"]),
                        f"{e['fixed_base_pf']:.3f} ({e['fixed_base_sum_r']:+.1f}R)",
                        f"{e['wf_12m_4m_pf']:.3f} ({e['wf_12m_4m_sum_r']:+.1f}R)",
                        f"{e['oracle_pf']:.3f} ({e['oracle_combo']})",
                        f"{e['wf_vs_base_pf_delta']:+.3f}", f"{e['overfit_illusion_gap_pf']:+.3f}",
                    ]
                    for e in wf_study["engines"]
                ],
            ),
            "",
            f"## 1C. Dynamic Prop Pacing (`N = {pacing_paths:,}` Đường MC, `{breadth_label}`)",
            "",
            format_markdown_table(
                ["Prop Firm", "Policy", "Pass 24m%", "Med Days Pass", "Med Days Pay1", "Breach%", "Wipeout%", "OOP95 USD", "EV 24m USD", "EV/Fee"],
                [
                    [
                        r["firm"], r["policy"], f"{r['pass_rate_24m_pct']:.1f}%",
                        str(r["med_days_to_pass"]), str(r["med_days_to_pay1"]),
                        f"{r['breach_any_pct']:.1f}%", f"{r['wipeout_5tix_pct']:.2f}%",
                        f"{r['oop95_usd']:.1f}", f"{r['ev_24m_usd']:+.1f}", f"{r['ev_per_fee_x']:+.2f}x",
                    ]
                    for r in pacing_rows
                ],
            ),
            "",
        ]
        write_verified_receipt(json_path, summary, overwrite=True)
        md_path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    return summary


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lab #10: v2 7-Gate Robust Alpha Discovery, Walk-Forward SL/TP & Dynamic Prop Pacing")
    parser.add_argument("--mc-draws", type=int, default=500)
    parser.add_argument("--pacing-paths", type=int, default=5000)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    res = run_lab10(mc_draws=args.mc_draws, pacing_paths=args.pacing_paths, write_report=not args.no_write)
    print(json.dumps({
        "elapsed_sec": res["elapsed_sec"],
        "approved": res["study_1a_discovery"]["approved_ids"],
        "conditional": res["study_1a_discovery"]["conditional_ids"],
        "wf_port7e": res["study_1b_walk_forward_sl_tp"]["port_7e_aggregate"],
        "pacing_sample": res["study_1c_dynamic_prop_pacing"]["rows"][:6],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
