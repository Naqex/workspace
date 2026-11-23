"""M8.1 — Pass 31: Red-Team-Guarded Orthogonal Intraday Discovery (HARD CAP m_total <= 20, DEV < 2025-01-01 ONLY!).

STRICT SEALED DEVELOPMENT & GOVERNANCE BOUNDARIES:
  - Asserts NATIVE_FTMO_HOLDOUT_LOCK.json SHA integrity on startup (`holdout_rows_analysed = 0`, `OrderSend = 0`).
  - Reads ONLY .runtime/hot-m1-cache/ (verified max_ts < 2025-01-01T00:00:00Z).
  - HARD CAP: M_TOTAL_CAP = 20 (`len(catalog) == 18 <= 20`).
  - Wires EVERY hypothesis through `quant_factory.research_council` (`HypothesisCard` + `SkepticalRedTeamCritic`)
    with `KillCriteria(max_bh_q=0.10, min_dsr=0.50, min_cluster_b_sharpe=0.40, min_cost_breakeven_mult=2.0,
    max_corr_vs_incumbent=0.15, max_tail_corr_vs_incumbent=0.35, min_trades_cluster_b=30)`
    PLUS Zero-Leakage Random-Day Matched-Hold Timing Null (`p < 0.05`).
  - 3 genuinely new economic families (not tested in Pass 29-30):
      FA: Cross-Session Volatility Compression (bottom 30th pct causal 20d range) -> Expansion Breakout (6 specs)
      FB: Time- & Vol-Conditioned Liquidity Sweep / Stop-Run Reversal (sweep 0.15-0.35 ATR + 15-30m reclaim) (6 specs)
      FC: Cross-Asset NY-Open Spillover (US500/US100/EURUSD/XAUUSD -> XAUUSD/USDJPY) (6 specs)
  - Cluster A (Discovery): 2018-2021 -> Blind Cluster B (Validation): 2022-2024.
  - Retains ALL negative/killed hypotheses transparently.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import fsum
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
import pass19_us500_supertrend_yencross as p19
import pass24_mtf_new_archetypes as p24
import pass26_cross_asset_rs as p26
import pass27_portfolio_m1_phase_audit as p27
from native_ftmo_monfri_seal import STOP
from quant_core.ftmo_track_replay import profiles
from quant_factory.data_store import assert_holdout_locked, build_or_load_frozen_tapes, load_registry
from quant_factory.eval_pipeline import sign_flip_p_numba
from quant_factory.pass29_gold_index_dev import (
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    CLUSTER_B_YEARS,
    MATCHED_HOLD_DRAWS,
    NY_TZ,
    SEED,
    SIGN_FLIP_DRAWS,
    _market_entry_window,
    _replay_with_meta,
    _stop_breakout_window,
    compute_matched_hold_p,
    local_ts,
    split_stats,
)
from quant_factory.prop_engine import replay_portfolio_m1
from quant_factory.research_council import (
    EvidenceBundle,
    HypothesisCard,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

M_TOTAL_CAP = 20
PASS31_ASSETS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US100", "US500")
PASS31_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.40,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.15,
    max_tail_corr_vs_incumbent=0.35,
    min_trades_cluster_b=30,
)
COMMON_INVARIANTS: tuple[str, ...] = (
    "holdout_2025_2026_strictly_sealed_zero_rows",
    "native_m1_bid_ask_fills_with_stress_and_double_cost_tiers",
    "swap_zero_hard_intraday_flat_and_server_hard_sl",
    "strict_causal_lookback_closed_bars_only",
)


def build_pass31_catalog() -> list[dict[str, Any]]:
    """Pre-registered 18-spec catalog (<= M_TOTAL_CAP=20) with explicit economic rationale per family."""
    cat = [
        # Family A: Cross-Session Volatility Compression -> Expansion Breakout (6)
        {"id": "P31_FA_EURUSD_ASIA_P30_LDN_BRK", "fam": "FA_CROSS_SESS_VOL_COMP", "asset": "EURUSD", "kind": "ASIA_P30_LDN", "sl_atr": 0.70,
         "counterparty": "Stop-cluster cascade when Asian liquidity compression traps breakout hedgers at London open",
         "rationale": "Bottom-30% causal 20-day Asian session range on EURUSD concentrates dealer inventory and stop orders just outside the box, generating directional London expansion."},
        {"id": "P31_FA_GBPUSD_ASIA_P30_LDN_BRK", "fam": "FA_CROSS_SESS_VOL_COMP", "asset": "GBPUSD", "kind": "ASIA_P30_LDN", "sl_atr": 0.70,
         "counterparty": "Stop-cluster cascade when Asian range compression breaks at London liquidity handover",
         "rationale": "Bottom-30% causal 20-day Asian range on GBPUSD signals compressed overnight positioning that expands directionally once UK/EU institutional desks open."},
        {"id": "P31_FA_USDJPY_ASIA_P30_LDN_BRK", "fam": "FA_CROSS_SESS_VOL_COMP", "asset": "USDJPY", "kind": "ASIA_P30_LDN", "sl_atr": 0.70,
         "counterparty": "Tokyo range-bound market makers forced to chase hedges when London breaks compressed Asian bounds",
         "rationale": "Bottom-30% causal 20-day Asian session range on USDJPY concentrates stops tightly around Tokyo bounds, triggering directional continuation into London/NY."},
        {"id": "P31_FA_XAUUSD_ASIA_P30_LDN_BRK", "fam": "FA_CROSS_SESS_VOL_COMP", "asset": "XAUUSD", "kind": "ASIA_P30_LDN", "sl_atr": 0.75,
         "counterparty": "Bullion dealers re-hedging compressed Asian inventory during London/COMEX handover",
         "rationale": "Bottom-30% causal 20-day Asian Gold range precedes directional London/NY liquidity releases when bullion desks re-price macro flows."},
        {"id": "P31_FA_US100_MORN_P30_NY_BRK", "fam": "FA_CROSS_SESS_VOL_COMP", "asset": "US100", "kind": "US100_MORN_P30", "sl_atr": 0.65,
         "counterparty": "0DTE/intraday option dealers forced to delta-hedge breakouts out of compressed opening-hour balance",
         "rationale": "Bottom-30% causal 20-day US100 first-hour (09:30-10:30 ET) range indicates coiled volatility that expands forcefully during mid-day trend discovery."},
        {"id": "P31_FA_XAUUSD_LDN_P30_NY_BRK", "fam": "FA_CROSS_SESS_VOL_COMP", "asset": "XAUUSD", "kind": "XAU_LDN_P30_NY", "sl_atr": 0.75,
         "counterparty": "Quiet London morning bullion book swept by COMEX/US macro institutional execution",
         "rationale": "Bottom-30% causal 20-day London morning Gold range (07:00-12:00 UTC) releases pent-up directional order flow upon NY/COMEX open."},

        # Family B: Time- & Vol-Conditioned Liquidity Sweep / Stop-Run Reversal (6)
        {"id": "P31_FB_EURUSD_ASIA_SWEEP_15M", "fam": "FB_LIQ_SWEEP_REVERSAL", "asset": "EURUSD", "kind": "ASIA_SWEEP_15", "sl_atr": 0.65,
         "counterparty": "Trapped breakout retail/CTA stops swept 0.15-0.35 ATR beyond Asia H/L that fail within 15 minutes",
         "rationale": "London stop-run sweeps 0.15-0.35 ATR outside EURUSD Asian extremes that rapidly reclaim inside within 15m trap breakout buyers/sellers and revert."},
        {"id": "P31_FB_GBPUSD_ASIA_SWEEP_15M", "fam": "FB_LIQ_SWEEP_REVERSAL", "asset": "GBPUSD", "kind": "ASIA_SWEEP_15", "sl_atr": 0.65,
         "counterparty": "Trapped breakout stops swept beyond GBPUSD Asian range during London open liquidity grab",
         "rationale": "GBPUSD frequently exhibits sharp stop-runs 0.15-0.35 ATR beyond Asian extremes before snapping back inside within 15m as institutional limit liquidity absorbs stops."},
        {"id": "P31_FB_USDJPY_ASIA_SWEEP_30M", "fam": "FB_LIQ_SWEEP_REVERSAL", "asset": "USDJPY", "kind": "ASIA_SWEEP_30", "sl_atr": 0.70,
         "counterparty": "Failed breakout chasers beyond Tokyo extremes forced to unwind during London/NY handover",
         "rationale": "USDJPY sweeps 0.15-0.35 ATR outside Tokyo H/L that close back inside within 30m indicate absorbed stop liquidity and short-term mean reversion."},
        {"id": "P31_FB_XAUUSD_ASIA_SWEEP_30M", "fam": "FB_LIQ_SWEEP_REVERSAL", "asset": "XAUUSD", "kind": "ASIA_SWEEP_30", "sl_atr": 0.70,
         "counterparty": "Retail Gold breakout stops triggered above/below Asian box and absorbed by London bullion liquidity",
         "rationale": "Gold sweeps 0.15-0.35 ATR beyond Asian range that reclaim inside within 30m trap leveraged intraday stops and revert into the prior balance."},
        {"id": "P31_FB_EURUSD_LDN_SWEEP_NY_30M", "fam": "FB_LIQ_SWEEP_REVERSAL", "asset": "EURUSD", "kind": "LDN_SWEEP_NY30", "sl_atr": 0.65,
         "counterparty": "NY-overlap fakeout stops beyond London H/L absorbed by WMR fix/corporate opposing flow",
         "rationale": "NY-overlap sweeps 0.15-0.35 ATR beyond London morning EURUSD extremes that reclaim inside within 30m signal failed continuation and trapped stop unwind."},
        {"id": "P31_FB_US100_OR30_SWEEP_15M", "fam": "FB_LIQ_SWEEP_REVERSAL", "asset": "US100", "kind": "US100_OR30_SWEEP15", "sl_atr": 0.65,
         "counterparty": "Trapped ORB chasers swept 0.15-0.35 ATR outside US100 30m range before swift 15m reclaim",
         "rationale": "US100 false opening-range sweeps of 0.15-0.35 ATR that close back inside within 15m force momentum chasers to liquidate back across the opening balance."},

        # Family C: Cross-Asset NY-Open Spillover (6)
        {"id": "P31_FC_US500_TO_XAU_INV_1015ET", "fam": "FC_NY_OPEN_SPILLOVER", "asset": "XAUUSD", "kind": "US500_XAU_INV", "sl_atr": 0.70,
         "counterparty": "Cross-asset multi-strategy desks rotating between US equities and Gold safe-haven duration",
         "rationale": "Strong US500 opening impulse (09:30-10:15 ET, |z| >= 0.35) drives inverse safe-haven/risk-off hedging spillover into Gold through the NY afternoon."},
        {"id": "P31_FC_US100_TO_XAU_ALIGN_1015ET", "fam": "FC_NY_OPEN_SPILLOVER", "asset": "XAUUSD", "kind": "US100_XAU_ALIGN", "sl_atr": 0.70,
         "counterparty": "Real-rate/duration repricing simultaneously lifting long-duration tech (US100) and zero-yield Gold",
         "rationale": "Strong US100 opening impulse (09:30-10:15 ET, |z| >= 0.35) reflects real-yield repricing that spills over in the same direction into XAUUSD."},
        {"id": "P31_FC_EURUSD_TO_XAU_NY_1330U", "fam": "FC_NY_OPEN_SPILLOVER", "asset": "XAUUSD", "kind": "EU_XAU_1330U", "sl_atr": 0.75,
         "counterparty": "Broad USD liquidity shocks priced first in EURUSD spot spilling into NY Gold bullion flow",
         "rationale": "Directional EURUSD impulse during London (07:00-13:30 UTC, |z| >= 0.35) reflects broad USD repricing that spills positively into XAUUSD during NY session."},
        {"id": "P31_FC_EURUSD_TO_USDJPY_NY_1330U", "fam": "FC_NY_OPEN_SPILLOVER", "asset": "USDJPY", "kind": "EU_UJ_1330U", "sl_atr": 0.75,
         "counterparty": "Delayed USD broad-factor transmission from European EURUSD flows into NY USDJPY execution",
         "rationale": "Strong EURUSD London impulse (07:00-13:30 UTC, |z| >= 0.35) captures broad USD strength/weakness spilling inversely into USDJPY through NY afternoon."},
        {"id": "P31_FC_US500_TO_USDJPY_1030ET", "fam": "FC_NY_OPEN_SPILLOVER", "asset": "USDJPY", "kind": "US500_UJ_1030ET", "sl_atr": 0.70,
         "counterparty": "Risk-parity and carry desks adjusting JPY funding hedges after first-hour US500 equity shock",
         "rationale": "Strong first-hour US500 direction (09:30-10:30 ET, |z| >= 0.35) drives risk-on/risk-off JPY carry rebalancing in USDJPY through NY close."},
        {"id": "P31_FC_XAU_TO_USDJPY_INV_1015ET", "fam": "FC_NY_OPEN_SPILLOVER", "asset": "USDJPY", "kind": "XAU_UJ_INV_1015ET", "sl_atr": 0.75,
         "counterparty": "US real-yield shocks priced rapidly in COMEX Gold spilling inversely into rate-sensitive USDJPY",
         "rationale": "Strong COMEX Gold morning impulse (08:20-10:15 ET, |z| >= 0.35) proxies US Treasury real-yield surprises spilling inversely into USDJPY."},
    ]
    assert len(cat) <= M_TOTAL_CAP, f"Catalog {len(cat)} exceeds HARD CAP {M_TOTAL_CAP}"
    return cat


def _session_box(times: np.ndarray, quotes: np.ndarray, ts_s: int, ts_e: int) -> tuple[float, float, float] | None:
    m0 = int(times.searchsorted(ts_s, side="left"))
    m1 = int(times.searchsorted(ts_e, side="left"))
    if m1 - m0 < 15:
        return None
    sub = quotes[m0:m1]
    hi, lo = float(sub[:, 1].max()), float(sub[:, 2].min())
    return hi, lo, hi - lo


def _eval_liq_sweep_reclaim(
    bundle: dict[str, Any],
    day_rec: dict[str, Any],
    box_hi: float,
    box_lo: float,
    ts_scan_start: int,
    ts_scan_end: int,
    ts_flat: int,
    *,
    reclaim_bars: int,
    sl_atr: float,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, tuple[int, int, int, float, float] | None]:
    """Strictly causal stop-run liquidity sweep (0.15-0.35 ATR beyond box) + close back inside within reclaim_bars."""
    times, quotes = bundle["times"], bundle["quotes"]
    fi, day_flat = day_rec["fi"], day_rec["flat_idx"]
    atr = float(day_rec["atr"])
    sub_t = times[fi:day_flat + 1]
    i0 = int(sub_t.searchsorted(ts_scan_start, side="left"))
    i1 = int(sub_t.searchsorted(ts_scan_end, side="left"))
    i_fl = min(day_flat, fi + int(sub_t.searchsorted(ts_flat, side="left")))
    if i1 <= i0 + 2:
        return None, None, None

    lo_sw = 0.15 * atr
    hi_sw = 0.35 * atr
    scan_end = min(fi + i1, i_fl - 2)
    # Scan chronologically for FIRST valid sweep -> reclaim event (100% causal bar-by-bar!)
    sweep_dir = 0  # +1 = swept above box_hi (looking to SHORT), -1 = swept below box_lo (looking to LONG)
    sweep_bar = -1
    sweep_ext = 0.0
    for idx in range(fi + i0, scan_end):
        h_b = float(quotes[idx, 1])
        l_b = float(quotes[idx, 2])
        c_b = float(quotes[idx, 3])
        if sweep_dir == 0:
            up_ext = h_b - box_hi
            dn_ext = box_lo - l_b
            if lo_sw <= up_ext <= hi_sw and not (dn_ext >= lo_sw):
                sweep_dir = 1
                sweep_bar = idx
                sweep_ext = h_b
            elif lo_sw <= dn_ext <= hi_sw and not (up_ext >= lo_sw):
                sweep_dir = -1
                sweep_bar = idx
                sweep_ext = l_b
        else:
            if idx - sweep_bar > reclaim_bars:
                return None, None, None
            if sweep_dir == 1:
                sweep_ext = max(sweep_ext, h_b)
                if sweep_ext - box_hi > 0.55 * atr:
                    return None, None, None  # Genuine breakout, not a shallow stop-run
                if c_b < box_hi:
                    # Closed back inside box on bar `idx` -> enter SHORT on NEXT bar `idx + 1` open!
                    e_idx = idx + 1
                    if e_idx >= i_fl:
                        return None, None, None
                    ep = float(quotes[e_idx, 0])  # Bid open for short
                    sl_p = max(sweep_ext + 0.15 * atr, ep + sl_atr * atr)
                    tr, fd = _replay_with_meta(bundle, day_rec, e_idx, i_fl, -1, ep, sl_p, win_start_idx=fi + i0)
                    return tr, fd, (e_idx, i_fl, -1, ep, sl_p)
            else:
                sweep_ext = min(sweep_ext, l_b)
                if box_lo - sweep_ext > 0.55 * atr:
                    return None, None, None
                if c_b > box_lo:
                    # Closed back inside box on bar `idx` -> enter LONG on NEXT bar `idx + 1` open!
                    e_idx = idx + 1
                    if e_idx >= i_fl:
                        return None, None, None
                    ep = float(quotes[e_idx, 4])  # Ask open for long
                    sl_p = min(sweep_ext - 0.15 * atr, ep - sl_atr * atr)
                    tr, fd = _replay_with_meta(bundle, day_rec, e_idx, i_fl, 1, ep, sl_p, win_start_idx=fi + i0)
                    return tr, fd, (e_idx, i_fl, 1, ep, sl_p)
    return None, None, None


def eval_pass31_spec(
    bundles: dict[str, Any],
    day_maps: dict[str, dict[str, Any]],
    all_days: list[str],
    cfg: dict[str, Any],
    *,
    build_m1_tape: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, tuple]]:
    asset = cfg["asset"]
    kind = cfg["kind"]
    sl_atr = float(cfg["sl_atr"])
    b = bundles[asset]
    times, quotes = b["times"], b["quotes"]
    trs, fds = [], []
    tape_out: dict[str, tuple] = {}

    # Precompute causal trailing 20-day session ranges for Family A specs
    prior_ranges: list[float] = []

    for dk in all_days:
        if dk not in day_maps[asset]:
            continue
        d = day_maps[asset][dk]
        dsec = d["day_sec"]
        atr = float(d["atr"])
        tr = fd = None
        tape_args: tuple[int, int, int, float, float] | None = None

        if kind in ("ASIA_P30_LDN", "US100_MORN_P30", "XAU_LDN_P30_NY"):
            if kind == "ASIA_P30_LDN":
                box = _session_box(times, quotes, dsec, dsec + 7 * 3600)
                ts_w0, ts_w1 = dsec + 7 * 3600, dsec + 16 * 3600
            elif kind == "US100_MORN_P30":
                box = _session_box(times, quotes, dsec, dsec + 60 * 60)
                ts_w0, ts_w1 = dsec + 60 * 60, dsec + 330 * 60
            else:
                box = _session_box(times, quotes, dsec + 7 * 3600, dsec + 12 * 3600)
                ts_w0, ts_w1 = dsec + 12 * 3600, dsec + 18 * 3600
            if box is None:
                continue
            bh, bl, brng = box
            norm_rng = brng / max(1e-9, atr)
            # Strictly causal 30th percentile over PRIOR 20 days ONLY (never includes today!)
            if len(prior_ranges) >= 20:
                p30 = float(np.quantile(prior_ranges[-20:], 0.30))
                if brng > 1e-9 and norm_rng <= p30:
                    buf = 0.10 * atr
                    tr, fd = _stop_breakout_window(b, d, ts_w0, ts_w1, bh + buf, bl - buf, sl_atr)
                    if build_m1_tape and tr is not None:
                        m = tr["_meta"]
                        sd = m["side"]
                        ep = max(bh + buf, float(quotes[m["e_idx"], 4])) if sd == 1 else min(bl - buf, float(quotes[m["e_idx"], 0]))
                        tape_args = (m["e_idx"], d["flat_idx"], sd, ep, ep - sd * sl_atr * atr)
            prior_ranges.append(norm_rng)

        elif kind in ("ASIA_SWEEP_15", "ASIA_SWEEP_30", "LDN_SWEEP_NY30", "US100_OR30_SWEEP15"):
            if kind in ("ASIA_SWEEP_15", "ASIA_SWEEP_30"):
                box = _session_box(times, quotes, dsec, dsec + 7 * 3600)
                if box is not None and box[2] >= 0.15 * atr:
                    tr, fd, tape_args = _eval_liq_sweep_reclaim(
                        b, d, box[0], box[1], dsec + 7 * 3600, dsec + 14 * 3600, dsec + 18 * 3600,
                        reclaim_bars=15 if kind == "ASIA_SWEEP_15" else 30, sl_atr=sl_atr,
                    )
            elif kind == "LDN_SWEEP_NY30":
                box = _session_box(times, quotes, dsec + 7 * 3600, dsec + 12 * 3600)
                if box is not None and box[2] >= 0.20 * atr:
                    tr, fd, tape_args = _eval_liq_sweep_reclaim(
                        b, d, box[0], box[1], dsec + 12 * 3600, dsec + 16 * 3600, dsec + 20 * 3600 + 55 * 60,
                        reclaim_bars=30, sl_atr=sl_atr,
                    )
            else:
                box = _session_box(times, quotes, dsec, dsec + 30 * 60)
                if box is not None and box[2] >= 0.20 * atr:
                    tr, fd, tape_args = _eval_liq_sweep_reclaim(
                        b, d, box[0], box[1], dsec + 30 * 60, dsec + 210 * 60, dsec + 385 * 60,
                        reclaim_bars=15, sl_atr=sl_atr,
                    )

        elif kind in ("US500_XAU_INV", "US100_XAU_ALIGN", "EU_XAU_1330U", "EU_UJ_1330U", "US500_UJ_1030ET", "XAU_UJ_INV_1015ET"):
            if kind in ("US500_XAU_INV", "US100_XAU_ALIGN"):
                src = "US500" if kind == "US500_XAU_INV" else "US100"
                if dk not in day_maps[src]:
                    continue
                sd_rec = day_maps[src][dk]
                ts_s, ts_e, ts_f = sd_rec["day_sec"], sd_rec["day_sec"] + 45 * 60, sd_rec["day_sec"] + 385 * 60
                z = p26.causal_z_return(bundles[src], ts_s, ts_e, sd_rec["atr"])
                if z is not None and abs(z) >= 0.35:
                    side = (-1 if z > 0 else 1) if kind == "US500_XAU_INV" else (1 if z > 0 else -1)
                    tr, fd = _market_entry_window(b, d, ts_e, ts_f, side, sl_atr, win_start_ts=ts_s)
            elif kind in ("EU_XAU_1330U", "EU_UJ_1330U"):
                if dk not in day_maps["EURUSD"]:
                    continue
                de = day_maps["EURUSD"][dk]
                ts_s, ts_e, ts_f = dsec + 7 * 3600, dsec + 13 * 3600 + 30 * 60, dsec + 20 * 3600 + 55 * 60
                z = p26.causal_z_return(bundles["EURUSD"], ts_s, ts_e, de["atr"])
                if z is not None and abs(z) >= 0.35:
                    side = (1 if z > 0 else -1) if kind == "EU_XAU_1330U" else (-1 if z > 0 else 1)
                    tr, fd = _market_entry_window(b, d, ts_e, ts_f, side, sl_atr, win_start_ts=dsec + 7 * 3600)
            elif kind == "US500_UJ_1030ET":
                if dk not in day_maps["US500"]:
                    continue
                du = day_maps["US500"][dk]
                ts_s, ts_e, ts_f = du["day_sec"], du["day_sec"] + 60 * 60, du["day_sec"] + 385 * 60
                z = p26.causal_z_return(bundles["US500"], ts_s, ts_e, du["atr"])
                if z is not None and abs(z) >= 0.35:
                    side = 1 if z > 0 else -1
                    tr, fd = _market_entry_window(b, d, ts_e, ts_f, side, sl_atr, win_start_ts=ts_s)
            elif kind == "XAU_UJ_INV_1015ET":
                if dk not in day_maps["XAUUSD"]:
                    continue
                dx = day_maps["XAUUSD"][dk]
                ts_s, ts_e, ts_f = local_ts(dk, 8, 20, NY_TZ), local_ts(dk, 10, 15, NY_TZ), local_ts(dk, 15, 55, NY_TZ)
                z = p26.causal_z_return(bundles["XAUUSD"], ts_s, ts_e, dx["atr"])
                if z is not None and abs(z) >= 0.35:
                    side = -1 if z > 0 else 1
                    tr, fd = _market_entry_window(b, d, ts_e, ts_f, side, sl_atr, win_start_ts=ts_s)
            if build_m1_tape and tr is not None:
                m = tr["_meta"]
                sd = m["side"]
                ep = float(quotes[m["e_idx"], 4] if sd == 1 else quotes[m["e_idx"], 0])
                tape_args = (m["e_idx"], m["flat_idx"], sd, ep, ep - sd * sl_atr * atr)

        if tr is not None and fd is not None:
            trs.append(tr)
            fds.append(fd)
            if build_m1_tape and tape_args is not None:
                e_i, f_i, sd, ep_v, sl_v = tape_args
                item = p27.replay_causal_m1_tape_trade(
                    asset, times, quotes, e_i, f_i, sd, ep_v, sl_v,
                    spec=b["spec"], usdjpy_close_map=b["usdjpy_close_map"],
                )
                if item is not None:
                    tape_out[item[0]["day"]] = item

    return trs, fds, tape_out


def run_pass31(*, cache_dir: Path = hcache.DEFAULT_CACHE, jobs_root: Path = hcache.DEFAULT_JOBS) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    warm = build_or_load_frozen_tapes(jobs_root=jobs_root, cache_dir=cache_dir, force_rebuild=False)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    ext_days = warm["ext_days"]
    _, dev_ex7 = replay_portfolio_m1(ext_days, warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    port7_by_day = {e["day"]: float(e["net_usd"]) / 10000.0 for e in dev_ex7}

    days_a = [d for d in ext_days if int(d[:4]) in CLUSTER_A_YEARS]
    days_b = [d for d in ext_days if int(d[:4]) in CLUSTER_B_YEARS]
    incumbent_b_arr = np.array([port7_by_day.get(d, 0.0) for d in days_b], dtype=np.float64)

    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    bundles = {}
    for a in PASS31_ASSETS:
        b = p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map)
        assert int(b["times"].max()) < STOP, f"HOLDOUT_CONTAMINATION:{a}"
        bundles[a] = b

    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in PASS31_ASSETS}
    all_days = sorted({d for dm in day_maps.values() for d in dm})

    catalog = build_pass31_catalog()
    m_total = len(catalog)
    assert m_total <= M_TOTAL_CAP

    # Stage 1: Evaluate all 18 specs & collect raw sign-flip p-values across full family
    raw_eval = []
    family_p_all: list[float] = []
    for idx_c, cfg in enumerate(catalog):
        trs, fds, _ = eval_pass31_spec(bundles, day_maps, all_days, cfg, build_m1_tape=False)
        vals_all = [float(t["ftmo_R"]) for t in trs]
        fade_all = [float(f["ftmo_R"]) for f in fds]
        p_sf_all = sign_flip_p_numba(vals_all, fade_all, draws=SIGN_FLIP_DRAWS, seed=SEED + 1000 + idx_c) if vals_all else 1.0
        p_mh_all = compute_matched_hold_p(trs, bundles, years_filter=set(ALL_DEV_YEARS), draws=MATCHED_HOLD_DRAWS, seed=SEED + 1100 + idx_c) if trs else 1.0
        trs_b = [t for t in trs if t["year"] in CLUSTER_B_YEARS]
        p_mh_b = compute_matched_hold_p(trs_b, bundles, years_filter=CLUSTER_B_YEARS, draws=MATCHED_HOLD_DRAWS, seed=SEED + 1200 + idx_c) if trs_b else 1.0
        family_p_all.append(p_sf_all)
        raw_eval.append((cfg, trs, fds, p_sf_all, p_mh_all, p_mh_b))

    # Stage 2: Wire EVERY hypothesis through Research Council (Proposer -> SkepticalRedTeamCritic)
    rows = []
    survivors = []
    for idx_c, (cfg, trs, _fds, p_sf_all, p_mh_all, p_mh_b) in enumerate(raw_eval):
        card: HypothesisCard = propose_hypothesis(
            hypothesis_id=cfg["id"],
            title=f"Pass 31 {cfg['fam']} on {cfg['asset']}",
            asset_universe=(cfg["asset"],),
            timeframe="M1_INTRADAY_SWAP0",
            counterparty_mechanism=cfg["counterparty"],
            economic_rationale=cfg["rationale"],
            causal_invariants=COMMON_INVARIANTS,
            n_trials_cumulative=m_total,
            kill_criteria=PASS31_KILL_CRITERIA,
        )
        # Convert trades into 0.50% risk/trade daily fractional returns aligned to ext_days
        tr_by_day = {t["day"]: float(t["ftmo_R"]) * 0.005 for t in trs}
        ret_a_arr = np.array([tr_by_day.get(d, 0.0) for d in days_a], dtype=np.float64)
        ret_b_arr = np.array([tr_by_day.get(d, 0.0) for d in days_b], dtype=np.float64)

        mA = split_stats(trs, CLUSTER_A_YEARS)
        mB = split_stats(trs, CLUSTER_B_YEARS)
        mAll = split_stats(trs, set(ALL_DEV_YEARS))

        ev = EvidenceBundle(
            cluster_a_returns=ret_a_arr,
            cluster_b_returns=ret_b_arr,
            p_value_raw=p_sf_all,
            family_p_values=tuple(family_p_all),
            candidate_index_in_family=idx_c,
            cost_1x_net=float(mAll["net_R"]),
            cost_2x_net=float(mAll["double_R"]),
            n_trades_cluster_b=int(mB["n"]),
            incumbent_daily_returns=incumbent_b_arr,
            annualization_days=252.0,
            holdout_rows_analysed=0,
        )
        verdict_obj = critique_proposal(card, ev)
        mh_pass = p_mh_all < 0.05
        final_pass = (verdict_obj["verdict"] == "APPROVE_FOR_INCUBATION") and mh_pass

        if final_pass:
            survivors.append(cfg["id"])

        rows.append({
            "id": cfg["id"],
            "fam": cfg["fam"],
            "asset": cfg["asset"],
            "cluster_a_2018_2021": mA,
            "cluster_b_2022_2024": mB,
            "dev_all_2018_2024": mAll,
            "sign_flip_p_all": round(p_sf_all, 4),
            "bh_q_all": verdict_obj["gates"]["G1_bh_fdr"]["bh_q"],
            "dsr_b": verdict_obj["gates"]["G2_dsr_and_sharpe"]["dsr_b"],
            "sr_b": verdict_obj["gates"]["G2_dsr_and_sharpe"]["sr_ann_b"],
            "breakeven_cost_mult": verdict_obj["gates"]["G3_cost_stress"]["breakeven_mult"],
            "corr_b_port7e": verdict_obj["gates"]["G4_orthogonality"]["corr_all"],
            "tail_corr_b_port7e": verdict_obj["gates"]["G4_orthogonality"]["corr_tail_5pct"],
            "matched_hold_p_all": round(p_mh_all, 4),
            "matched_hold_p_b": round(p_mh_b, 4),
            "council_verdict": verdict_obj["verdict"],
            "council_verdict_sha": verdict_obj["verdict_sha256"],
            "failed_gates": verdict_obj["failed_gates"] + ([] if mh_pass else ["G_MATCHED_HOLD_NULL"]),
            "final_pass": final_pass,
        })

    summary = {
        "schema": "naqex-pass31-redteam-discovery-dev-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "m_total_cap": M_TOTAL_CAP,
        "m_total": m_total,
        "passed_count": len(survivors),
        "passed_ids": survivors,
        "results": rows,
    }
    out_p = ROOT / ".runtime" / "quant-pod-returns" / "pass31_redteam_summary.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M8.1 Pass 31 Red-Team-Guarded Orthogonal Discovery (Dev < 2025 ONLY)")
    ap.parse_args()
    s = run_pass31()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "holdout_rows_analysed": s["holdout_rows_analysed"],
        "m_total": s["m_total"],
        "m_total_cap": s["m_total_cap"],
        "passed_count": s["passed_count"],
        "passed_ids": s["passed_ids"],
        "summary_rows": [
            (r["id"], r["cluster_a_2018_2021"]["net_R"], r["cluster_b_2022_2024"]["net_R"], r["bh_q_all"], r["dsr_b"], r["matched_hold_p_all"], r["council_verdict"])
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
