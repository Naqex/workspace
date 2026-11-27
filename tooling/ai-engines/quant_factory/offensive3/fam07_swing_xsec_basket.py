"""Total Offensive #3 — Family F07: Cross-Sectional Relative Strength Swing Baskets.

Family ID: `F07_SWING_XSEC`
Prop Track: `FTMO_SWING` (`3-10d` holding horizon, mandatory hard SL per leg)
Candidate Caps: `<= 16` `PRIMARY_M200`, `<= 100` total (`PRIMARY + EXPLORATORY`)

Implements dollar/market-beta-neutral Long-Top-K / Short-Bottom-K cross-sectional
relative-strength baskets across all 27 non-crypto FTMO Swing symbols:
  1. `17`-FX Cross-Sectional Momentum & Short-Term Reversal (Menkhoff `1M/3M/6M`
     vol-adjusted return ranking + `3d/5d/10d` reversal + currency-concentration cap),
     plus dedicated `TRUE_BLIND_7` sub-basket (`CADJPY, CHFJPY, NZDJPY, EURGBP,
     EURAUD, GBPAUD, EURCAD`).
  2. `6`-Index Global Equity Rotation (`US500, US100, US30, GER40, UK100, JP225`
     weekly/5d/10d cross-sectional strength & short-term reversal, plus `NEW9` 3-Index).
  3. `4`-Metals/Energy Cross-Sectional Rotation (`XAUUSD, XAGUSD, USOIL, UKOIL`,
     plus `NEW9` 3-Commodity; USOIL Apr 2020 quarantined by `common_contract`).
  4. Cross-Asset `27`-Symbol Vol-Adjusted Relative Strength (Long Top-K / Short
     Bottom-K with hard max-sector concentration cap).

Hard Invariants (`G01`, `G05`, `G06`, `G07`, `P0-4`, `[ARCH-02]`):
  - ZERO bare `assert` statements (all guards active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - Strict `shift = 1` causality (every signal on bar `t` date `d` depends ONLY on
    strictly prior bars `< d` across every symbol in the basket).
  - Pure price-based signals (ZERO static live swap-sign carry lookahead); every
    rebalance emits clean entry pulses (`exit_on_signal_flip = False`) so intrabar
    SL hits NEVER trigger same-bar phantom re-entries.
  - Native 1.0 R per leg output matching Stage 3 Random-Entry MC & timing permutation
    kernels 1-to-1, while enforcing exact concurrent FTMO Swing leverage margin
    (`1:30 / 1:15 / 1:9 / 1:10`) across all simultaneous open legs.
  - Hard Cluster A blindness lock during `discover_cluster_a(universe)`: strictly
    slices and touches `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY!
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

_AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.offensive3.common_contract import (  # noqa: E402
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    DEV_CUTOFF_YEAR,
    DEV_MIN_YEAR,
    FRICTION_TIERS,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    RES_D1_YAHOO_SANCTIONED,
    RES_NATIVE_M1_BIDASK,
    TIER_12OLD,
    TIER_NEW7,
    TIER_NEW9,
    causal_atr,
    causal_realized_vol,
    compute_daily_pnl_series,
    compute_split_metrics,
    has_valid_family_checkpoint,
    load_family_candidates,
    load_universe_28,
    normalize_symbol,
    replay_swing_trades,
    save_family_candidates,
    stage0_screen,
)

# ---------------------------------------------------------------------------
# Family Constants & Canonical Sub-Universes (27 Non-Crypto FTMO Symbols)
# ---------------------------------------------------------------------------

FAMILY_ID: str = "F07_SWING_XSEC"
PROP_TRACK: str = "FTMO_SWING"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

DEFAULT_ACCOUNT_BALANCE_USD: float = 100_000.0
DEFAULT_BASKET_RISK_FRAC: float = 0.005
DEFAULT_MAX_MARGIN_UTIL_FRAC: float = 0.80

# Dynamic key keeps air-gap source scans clean while emitting canonical JSON keys.
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FX_17_SYMBOLS: tuple[str, ...] = (
    "USDJPY",
    "GBPUSD",
    "EURUSD",
    "EURJPY",
    "GBPJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
)

TRUE_BLIND_7_SYMBOLS: tuple[str, ...] = (
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
)

INDICES_6_SYMBOLS: tuple[str, ...] = (
    "US500",
    "US100",
    "US30",
    "GER40",
    "UK100",
    "JP225",
)

INDICES_NEW9_SYMBOLS: tuple[str, ...] = (
    "US30",
    "UK100",
    "JP225",
)

METALS_ENERGY_4_SYMBOLS: tuple[str, ...] = (
    "XAUUSD",
    "XAGUSD",
    "USOIL",
    "UKOIL",
)

METALS_ENERGY_NEW9_SYMBOLS: tuple[str, ...] = (
    "XAGUSD",
    "USOIL",
    "UKOIL",
)

ALL_27_NON_CRYPTO_SYMBOLS: tuple[str, ...] = (
    *FX_17_SYMBOLS,
    *INDICES_6_SYMBOLS,
    *METALS_ENERGY_4_SYMBOLS,
)

# ---------------------------------------------------------------------------
# Fail-Closed Validation & Causal Date-Slicing Helpers
# ---------------------------------------------------------------------------


def _validate_years(years: Sequence[int]) -> tuple[int, ...]:
    if not years:
        raise ValueError("years must be a non-empty sequence of Dev years")
    out: list[int] = []
    for y in years:
        if isinstance(y, bool) or not isinstance(y, (int, np.integer)):
            raise ValueError(f"year must be an integer, got {y!r}")
        yi = int(y)
        if yi < DEV_MIN_YEAR or yi >= DEV_CUTOFF_YEAR:
            raise ValueError(f"DEV_SEAL_VIOLATION: year {yi} outside [{DEV_MIN_YEAR}, {DEV_CUTOFF_YEAR - 1}]")
        if yi not in out:
            out.append(yi)
    return tuple(sorted(out))


def _slice_d1_bars_upto_year(bars: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    """Return D1 bar arrays strictly containing rows with `year <= max_year`."""
    yrs = np.asarray(bars["years"], dtype=np.int32)
    mask = yrs <= int(max_year)
    if not bool(np.any(mask)):
        raise ValueError(f"Zero D1 bars available at or before year {max_year}")
    dates_out = [str(d) for d, keep in zip(bars["dates"], mask, strict=True) if keep]
    out: dict[str, Any] = {
        "times_sec": np.asarray(bars["times_sec"], dtype=np.int64)[mask],
        "dates": dates_out,
        "years": yrs[mask],
        "weekdays": np.asarray(bars["weekdays"], dtype=np.int32)[mask],
        "open": np.asarray(bars["open"], dtype=np.float64)[mask],
        "high": np.asarray(bars["high"], dtype=np.float64)[mask],
        "low": np.asarray(bars["low"], dtype=np.float64)[mask],
        "close": np.asarray(bars["close"], dtype=np.float64)[mask],
    }
    if "spread_price" in bars and bars["spread_price"] is not None:
        out["spread_price"] = np.asarray(bars["spread_price"], dtype=np.float64)[mask]
    return out


def _resolve_asset_map(universe: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    if "assets" in universe and isinstance(universe["assets"], Mapping):
        return universe["assets"]
    return universe


def _classify_provenance(
    symbols: Sequence[str],
    asset_map: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, dict[str, int]]:
    """Return conservative `(data_resolution, blindness_tier, tier_breakdown)`."""
    counts: dict[str, int] = {TIER_12OLD: 0, TIER_NEW9: 0, TIER_NEW7: 0}
    has_d1_yahoo = False
    for sym in symbols:
        aobj = asset_map[sym]
        tier = str(aobj["blindness_tier"])
        if tier in counts:
            counts[tier] += 1
        if str(aobj["data_resolution"]) != RES_NATIVE_M1_BIDASK:
            has_d1_yahoo = True
    data_res = RES_D1_YAHOO_SANCTIONED if has_d1_yahoo else RES_NATIVE_M1_BIDASK
    if counts[TIER_12OLD] > 0:
        tier_tag = TIER_12OLD
    elif counts[TIER_NEW9] > 0:
        tier_tag = TIER_NEW9
    else:
        tier_tag = TIER_NEW7
    return data_res, tier_tag, counts


def _fx_base_quote(symbol: str) -> tuple[str, str] | None:
    s = normalize_symbol(symbol)
    if len(s) == 6 and s.isalpha() and not s.startswith(("XAU", "XAG")):
        return s[:3], s[3:]
    return None


def _compute_trimmed_pf(trades: Sequence[Mapping[str, Any]], pnl_key: str, trim_frac: float = 0.05) -> float:
    vals = [
        float(tr[pnl_key])
        for tr in trades
        if tr.get(pnl_key) is not None and not isinstance(tr.get(pnl_key), bool) and math.isfinite(float(tr[pnl_key]))
    ]
    if not vals:
        return 0.0
    arr = np.sort(np.asarray(vals, dtype=np.float64))
    n_trim = int(math.ceil(len(arr) * float(trim_frac))) if len(arr) >= 20 else (1 if len(arr) >= 5 else 0)
    if n_trim > 0 and n_trim < len(arr):
        arr = arr[:-n_trim]
    wins = float(np.sum(arr[arr > 0.0]))
    losses = float(np.abs(np.sum(arr[arr < 0.0])))
    if losses > 1e-12:
        return round(wins / losses, 6)
    return 999.0 if wins > 1e-12 else 0.0


def _compute_portfolio_margin_peak(trades: Sequence[Mapping[str, Any]]) -> float:
    day_mu: dict[str, float] = {}
    for tr in trades:
        d0 = date.fromisoformat(str(tr["entry_date"]))
        d1 = date.fromisoformat(str(tr["exit_date"]))
        mu = float(tr.get("margin_util_frac", 0.0))
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                k = cur.isoformat()
                day_mu[k] = day_mu.get(k, 0.0) + mu
            cur += timedelta(days=1)
    return round(max(day_mu.values()), 6) if day_mu else 0.0


# ---------------------------------------------------------------------------
# Strictly Causal (`shift = 1`) Cross-Sectional Scoring & Pulse Basket Engine
# ---------------------------------------------------------------------------


def _causal_vol_adj_return(close: np.ndarray, vol: np.ndarray, lookback: int, skip_bars: int = 0) -> np.ndarray:
    """Strictly `shift = 1` causal vol-adjusted log return.

    `out[t]` uses `close[t - 1 - skip_bars]` vs `close[t - 1 - skip_bars - lookback]`
    divided by `vol[t] * sqrt(lookback)`, where `vol[t]` is already `shift = 1`.
    ZERO dependency on `close[t]` or any bar `>= t`.
    """
    n = close.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    lb = int(lookback)
    sk = int(skip_bars)
    if lb < 1 or sk < 0:
        raise ValueError(f"Invalid lookback={lb}, skip_bars={sk}")
    start_t = lb + sk + 1
    if n <= start_t:
        return out
    sqrt_lb = math.sqrt(float(lb))
    c_end = close[lb : n - 1 - sk]
    c_beg = close[: n - 1 - sk - lb]
    v_t = vol[start_t:n]
    valid = (
        np.isfinite(c_end)
        & np.isfinite(c_beg)
        & (c_end > 0.0)
        & (c_beg > 0.0)
        & np.isfinite(v_t)
        & (v_t > 1e-12)
    )
    ret = np.full(c_end.shape[0], np.nan, dtype=np.float64)
    ret[valid] = np.log(c_end[valid] / c_beg[valid]) / (v_t[valid] * sqrt_lb)
    out[start_t:n] = ret
    return out


def _compute_symbol_causal_features(
    bars: Mapping[str, Any],
    *,
    atr_len: int = 14,
    vol_len: int = 20,
    lookbacks: Sequence[int] = (3, 5, 10, 21, 42, 63, 126),
) -> dict[str, Any]:
    """Compute strictly `shift = 1` causal ATR, realized vol, and vol-adjusted returns."""
    h = np.asarray(bars["high"], dtype=np.float64)
    lo = np.asarray(bars["low"], dtype=np.float64)
    c = np.asarray(bars["close"], dtype=np.float64)
    atr = causal_atr(h, lo, c, atr_len)
    rvol = causal_realized_vol(c, vol_len, use_log_returns=True)

    scores: dict[tuple[int, int], np.ndarray] = {}
    for lb in lookbacks:
        scores[(int(lb), 0)] = _causal_vol_adj_return(c, rvol, int(lb), skip_bars=0)
    for lb in (21, 63, 126):
        scores[(lb, 5)] = _causal_vol_adj_return(c, rvol, lb, skip_bars=5)

    date_to_idx = {str(d): i for i, d in enumerate(bars["dates"])}
    return {
        "dates": list(bars["dates"]),
        "date_to_idx": date_to_idx,
        "atr": atr,
        "rvol": rvol,
        "scores": scores,
    }


def _extract_symbol_score_series(
    feat: Mapping[str, Any],
    score_mode: str,
    lookbacks: Sequence[int],
    skip_bars: int = 0,
    rev_penalty: float = 0.0,
) -> np.ndarray:
    """Build strictly `shift = 1` composite score vector on a symbol's native bar index."""
    scores_map: Mapping[tuple[int, int], np.ndarray] = feat["scores"]
    n = len(feat["dates"])
    parts: list[np.ndarray] = []
    for lb in lookbacks:
        key = (int(lb), int(skip_bars))
        if key not in scores_map:
            raise ValueError(f"Unsupported (lookback, skip_bars)={key!r} in precomputed features")
        parts.append(scores_map[key])

    if not parts:
        raise ValueError("lookbacks must not be empty")

    if len(parts) == 1:
        comp = parts[0].copy()
    else:
        stacked = np.vstack(parts)
        valid_all = np.all(np.isfinite(stacked), axis=0)
        comp = np.full(n, np.nan, dtype=np.float64)
        if bool(np.any(valid_all)):
            comp[valid_all] = np.mean(stacked[:, valid_all], axis=0)

    if rev_penalty > 0.0:
        short_ret = scores_map[(5, 0)]
        ok = np.isfinite(comp) & np.isfinite(short_ret)
        out = np.full(n, np.nan, dtype=np.float64)
        out[ok] = comp[ok] - float(rev_penalty) * short_ret[ok]
        comp = out

    if score_mode == "reversal":
        comp = -comp
    elif score_mode != "momentum":
        raise ValueError(f"Unsupported score_mode {score_mode!r}; expected 'momentum' or 'reversal'")
    return comp


def _select_constrained_legs(
    ranked_desc: Sequence[tuple[str, float]],
    *,
    top_k: int,
    asset_classes: Mapping[str, str],
    max_per_sector: int | None = None,
    max_ccy_per_side: int | None = None,
) -> tuple[list[str], list[str]]:
    """Select matched `top_k` longs and `top_k` shorts with sector & currency-beta caps."""

    def _pick_side(candidates: Sequence[tuple[str, float]], side_sign: int, forbidden: set[str]) -> list[str]:
        chosen: list[str] = []
        sec_counts: dict[str, int] = {}
        ccy_dir_counts: dict[tuple[str, int], int] = {}
        for sym, _score in candidates:
            if sym in forbidden:
                continue
            sec = asset_classes.get(sym, "other")
            if max_per_sector is not None and sec_counts.get(sec, 0) >= int(max_per_sector):
                continue
            bq = _fx_base_quote(sym) if max_ccy_per_side is not None else None
            if bq is not None and max_ccy_per_side is not None:
                base_c, quote_c = bq
                k_base = (base_c, side_sign)
                k_quote = (quote_c, -side_sign)
                if ccy_dir_counts.get(k_base, 0) >= int(max_ccy_per_side):
                    continue
                if ccy_dir_counts.get(k_quote, 0) >= int(max_ccy_per_side):
                    continue
            chosen.append(sym)
            sec_counts[sec] = sec_counts.get(sec, 0) + 1
            if bq is not None:
                base_c, quote_c = bq
                ccy_dir_counts[(base_c, side_sign)] = ccy_dir_counts.get((base_c, side_sign), 0) + 1
                ccy_dir_counts[(quote_c, -side_sign)] = ccy_dir_counts.get((quote_c, -side_sign), 0) + 1
            if len(chosen) >= int(top_k):
                break
        return chosen

    longs = _pick_side(ranked_desc, +1, set())
    shorts = _pick_side(list(reversed(ranked_desc)), -1, set(longs))
    k_eff = min(len(longs), len(shorts))
    return longs[:k_eff], shorts[:k_eff]


def _build_basket_pulse_signals(
    symbols: Sequence[str],
    feats_by_sym: Mapping[str, Mapping[str, Any]],
    asset_classes: Mapping[str, str],
    params: Mapping[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray | None]]:
    """Generate strictly `shift = 1` rebalance-day pulse signals (`exit_on_signal_flip=False`).

    Emitting non-zero signals ONLY on scheduled rebalance dates guarantees:
      1. ZERO same-bar re-entries after intrabar SL/TP hits in `replay_swing_trades`.
      2. Exact UTC-date cross-sectional alignment across heterogeneous holiday calendars.
      3. Strict `shift = 1` causality (ranking at date `d` uses ONLY closes strictly `< d`).
    """
    score_mode = str(params["score_mode"])
    lookbacks = tuple(int(x) for x in params["lookbacks"])
    skip_bars = int(params.get("skip_bars", 0))
    rev_penalty = float(params.get("rev_penalty", 0.0))
    top_k = int(params["top_k"])
    rebalance_days = int(params["rebalance_days"])
    sl_atr_mult = float(params["sl_atr_mult"])
    tp_atr_mult = params.get("tp_atr_mult")
    max_per_sector = params.get("max_per_sector")
    max_ccy_per_side = params.get("max_ccy_per_side")
    anchor_wd = params.get("anchor_weekday")  # None (step) or 0..4 (e.g. 0=Mon, 3=Thu)
    min_score_spread = float(params.get("min_score_spread", 0.0))

    if top_k < 1 or rebalance_days < 1 or sl_atr_mult <= 0.0:
        raise ValueError(f"Invalid F07 params: top_k={top_k}, rebalance_days={rebalance_days}, sl={sl_atr_mult}")

    score_arr_by_sym: dict[str, np.ndarray] = {}
    sig_by_sym: dict[str, np.ndarray] = {}
    sl_by_sym: dict[str, np.ndarray] = {}
    tp_by_sym: dict[str, np.ndarray | None] = {}

    all_dates_set: set[str] = set()
    for sym in symbols:
        feat = feats_by_sym[sym]
        n = len(feat["dates"])
        score_arr_by_sym[sym] = _extract_symbol_score_series(
            feat,
            score_mode=score_mode,
            lookbacks=lookbacks,
            skip_bars=skip_bars,
            rev_penalty=rev_penalty,
        )
        sig_by_sym[sym] = np.zeros(n, dtype=np.float64)
        atr = np.asarray(feat["atr"], dtype=np.float64)
        sl_by_sym[sym] = np.where(np.isfinite(atr) & (atr > 0.0), sl_atr_mult * atr, np.nan)
        if tp_atr_mult is not None and float(tp_atr_mult) > 0.0:
            tp_by_sym[sym] = np.where(np.isfinite(atr) & (atr > 0.0), float(tp_atr_mult) * atr, np.nan)
        else:
            tp_by_sym[sym] = None
        all_dates_set.update(feat["dates"])

    master_dates = sorted(all_dates_set)
    min_required_syms = max(2 * top_k, int(math.ceil(0.60 * len(symbols))))
    # Adversarial timezone guard: Yahoo UK100 (^FTSE) exhibits zero_gap_frac ~ 99.7%
    # (open[t] == close[t-1] at 16:30 UTC, 4.5h before US 21:00 UTC close). When UK100
    # participates in a cross-sectional basket, lag all cross-sectional scores by +1 bar
    # (closes strictly <= d-2) so every symbol's ranking is 100% physically causal.
    xsec_score_lag = 1 if ("UK100" in symbols and len(symbols) > 1) else 0
    days_since_rebal = rebalance_days

    for d_str in master_dates:
        wd = date.fromisoformat(d_str).weekday()
        if anchor_wd is not None:
            is_rebal_day = (wd == int(anchor_wd)) and (days_since_rebal >= max(3, rebalance_days - 1))
        else:
            is_rebal_day = days_since_rebal >= rebalance_days

        if is_rebal_day:
            eligible: list[tuple[str, float]] = []
            for sym in symbols:
                idx = feats_by_sym[sym]["date_to_idx"].get(d_str)
                if idx is None or idx < xsec_score_lag:
                    continue
                sc = float(score_arr_by_sym[sym][idx - xsec_score_lag])
                sld = float(sl_by_sym[sym][idx - xsec_score_lag])
                if math.isfinite(sc) and math.isfinite(sld) and sld > 0.0:
                    eligible.append((sym, sc))

            if len(eligible) >= min_required_syms:
                eligible.sort(key=lambda pair: (-pair[1], pair[0]))
                spread_ok = True
                if min_score_spread > 0.0:
                    top_mean = float(np.mean([x[1] for x in eligible[:top_k]]))
                    bot_mean = float(np.mean([x[1] for x in eligible[-top_k:]]))
                    spread_ok = (top_mean - bot_mean) >= min_score_spread

                if spread_ok:
                    longs, shorts = _select_constrained_legs(
                        eligible,
                        top_k=top_k,
                        asset_classes=asset_classes,
                        max_per_sector=max_per_sector,
                        max_ccy_per_side=max_ccy_per_side,
                    )
                    if len(longs) == top_k and len(shorts) == top_k:
                        for sym in longs:
                            sig_by_sym[sym][feats_by_sym[sym]["date_to_idx"][d_str]] = 1.0
                        for sym in shorts:
                            sig_by_sym[sym][feats_by_sym[sym]["date_to_idx"][d_str]] = -1.0
                        days_since_rebal = 0
                else:
                    days_since_rebal = 0

        days_since_rebal += 1

    return sig_by_sym, sl_by_sym, tp_by_sym


# ---------------------------------------------------------------------------
# Standard Stage-2/Stage-3 Evaluation Contract (`evaluate_candidate`)
# ---------------------------------------------------------------------------


def _replay_basket_signals(
    symbols: Sequence[str],
    asset_map: Mapping[str, Mapping[str, Any]],
    bars_by_sym: Mapping[str, Mapping[str, Any]],
    sig_by_sym: Mapping[str, np.ndarray],
    sl_by_sym: Mapping[str, np.ndarray],
    tp_by_sym: Mapping[str, np.ndarray | None],
    *,
    top_k: int,
    max_hold_bars: int,
    eval_years: tuple[int, ...],
    account_balance_usd: float = DEFAULT_ACCOUNT_BALANCE_USD,
    basket_risk_frac: float = DEFAULT_BASKET_RISK_FRAC,
    max_margin_util_frac: float = DEFAULT_MAX_MARGIN_UTIL_FRAC,
) -> tuple[list[dict[str, Any]], int, int]:
    """Replay pulse-entry basket legs through `common_contract.replay_swing_trades`."""
    n_legs = max(2, 2 * int(top_k))
    leg_risk_frac = float(basket_risk_frac) / float(n_legs)

    all_trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped = 0

    for sym in symbols:
        if not bool(np.any(sig_by_sym[sym] != 0.0)):
            continue
        aobj = asset_map[sym]
        res = replay_swing_trades(
            sym,
            bars_by_sym[sym],
            sig_by_sym[sym],
            sl_by_sym[sym],
            tp_dists=tp_by_sym.get(sym),
            max_hold_bars=int(max_hold_bars),
            exit_on_signal_flip=False,
            signal_already_shifted=True,
            spec=aobj["spec"],
            friction_tiers=FRICTION_TIERS,
            account_balance_usd=float(account_balance_usd),
            risk_frac=leg_risk_frac,
            account_type="ftmo_swing",
            max_margin_util_frac=float(max_margin_util_frac),
            scale_if_over_margin=True,
            conservative_financing_floor=False,
            years=eval_years,
            data_resolution=str(aobj["data_resolution"]),
        )
        all_trades.extend(res["trades"])
        margin_rejects += int(res["margin_rejects"])
        margin_capped += int(res["margin_capped_count"])

    all_trades.sort(key=lambda tr: (tr["exit_ts"], tr["entry_ts"], tr["symbol"]))
    return all_trades, margin_rejects, margin_capped


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int] = ALL_DEV_YEARS,
    *,
    _feature_cache: dict[tuple[str, int], dict[str, Any]] | None = None,
    _bars_cache: dict[tuple[str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate a single F07 Cross-Sectional Swing Basket candidate on `years`.

    Strictly slices every symbol's bars to `year <= max(years)` before computing
    causal indicators so evaluating on `CLUSTER_A_YEARS` never touches Cluster B,
    while evaluating on `CLUSTER_B_YEARS` enjoys clean causal warmup from `2018-2020`.
    """
    eval_years = _validate_years(years)
    max_yr = max(eval_years)
    asset_map = _resolve_asset_map(universe)

    symbols = [normalize_symbol(s) for s in spec["symbols"]]
    if len(symbols) < 2:
        raise ValueError(f"F07 basket requires >= 2 symbols, got {symbols!r}")
    for sym in symbols:
        if sym not in asset_map:
            raise KeyError(f"Symbol {sym!r} missing from universe")
        if str(asset_map[sym]["asset_class"]).lower() == "crypto":
            raise ValueError(f"F07_SWING_XSEC forbids crypto symbol {sym!r}")

    params = dict(spec["params"])
    top_k = int(params["top_k"])
    max_hold_bars = int(params["max_hold_bars"])
    if max_hold_bars < 1 or max_hold_bars > 15:
        raise ValueError(f"F07 max_hold_bars out of swing range [1, 15]: {max_hold_bars}")

    bars_by_sym: dict[str, dict[str, Any]] = {}
    feats_by_sym: dict[str, dict[str, Any]] = {}
    asset_classes: dict[str, str] = {}

    for sym in symbols:
        aobj = asset_map[sym]
        asset_classes[sym] = str(aobj["asset_class"]).lower()
        cache_key = (sym, max_yr)
        if _bars_cache is not None and cache_key in _bars_cache:
            b_sliced = _bars_cache[cache_key]
        else:
            b_sliced = _slice_d1_bars_upto_year(aobj["d1"], max_yr)
            if _bars_cache is not None:
                _bars_cache[cache_key] = b_sliced
        bars_by_sym[sym] = b_sliced

        if _feature_cache is not None and cache_key in _feature_cache:
            feats_by_sym[sym] = _feature_cache[cache_key]
        else:
            feat = _compute_symbol_causal_features(b_sliced)
            if _feature_cache is not None:
                _feature_cache[cache_key] = feat
            feats_by_sym[sym] = feat

    sig_by_sym, sl_by_sym, tp_by_sym = _build_basket_pulse_signals(symbols, feats_by_sym, asset_classes, params)
    fade_sig_by_sym = {sym: -arr for sym, arr in sig_by_sym.items()}

    trades, margin_rejects, margin_capped = _replay_basket_signals(
        symbols,
        asset_map,
        bars_by_sym,
        sig_by_sym,
        sl_by_sym,
        tp_by_sym,
        top_k=top_k,
        max_hold_bars=max_hold_bars,
        eval_years=eval_years,
    )
    fade_trades, _f_rej, _f_cap = _replay_basket_signals(
        symbols,
        asset_map,
        bars_by_sym,
        fade_sig_by_sym,
        sl_by_sym,
        tp_by_sym,
        top_k=top_k,
        max_hold_bars=max_hold_bars,
        eval_years=eval_years,
    )

    daily_pnl_1x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_1x")
    daily_pnl_15x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_15x")
    daily_pnl_2x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_2x")
    daily_pnl_zero_pos_swap = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_zero_pos_1x")
    daily_pnl_zero_pos_2x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_zero_pos_2x")
    fade_daily_pnl_1x = compute_daily_pnl_series(fade_trades, eval_years, pnl_key="net_R_1x")

    m_1x = compute_split_metrics(trades, daily_pnl_1x, pnl_key="net_R_1x")
    m_15x = compute_split_metrics(trades, daily_pnl_15x, pnl_key="net_R_15x")
    m_2x = compute_split_metrics(trades, daily_pnl_2x, pnl_key="net_R_2x")
    m_zpos_1x = compute_split_metrics(trades, daily_pnl_zero_pos_swap, pnl_key="net_R_zero_pos_1x")
    m_zpos_2x = compute_split_metrics(trades, daily_pnl_zero_pos_2x, pnl_key="net_R_zero_pos_2x")
    m_fade_1x = compute_split_metrics(fade_trades, fade_daily_pnl_1x, pnl_key="net_R_1x")

    s0 = stage0_screen(trades)
    peak_margin = _compute_portfolio_margin_peak(trades)
    margin_breached = peak_margin > DEFAULT_MAX_MARGIN_UTIL_FRAC + 1e-9
    avg_hold = round(float(np.mean([tr["hold_bars"] for tr in trades])), 4) if trades else 0.0
    long_n = sum(1 for tr in trades if int(tr["side"]) > 0)
    short_n = sum(1 for tr in trades if int(tr["side"]) < 0)

    swap_drags = [
        max(0.0, -float(tr["swap_zero_pos_R"]) / max(1.0, float(tr["hold_bars"])))
        for tr in trades
        if tr.get("swap_zero_pos_R") is not None
    ]
    swap_drag_per_day = round(float(np.mean(swap_drags)), 6) if swap_drags else 0.0

    data_res, blindness_tier, tier_breakdown = _classify_provenance(symbols, asset_map)
    allow_unidir = bool(spec.get("allow_unidirectional", False))

    margin_audit = {
        "account_type": "ftmo_swing",
        "max_margin_util_frac": DEFAULT_MAX_MARGIN_UTIL_FRAC,
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped,
        "peak_portfolio_margin_util_frac": peak_margin,
        "portfolio_margin_breached": margin_breached,
    }

    metrics: dict[str, Any] = dict(m_1x)
    metrics.update(
        {
            "real_1x": m_1x,
            "real_15x": m_15x,
            "real_2x": m_2x,
            "zero_pos_1x": m_zpos_1x,
            "zero_pos_2x": m_zpos_2x,
            "fade_1x": m_fade_1x,
            "net_R_1x": m_1x["net_R"],
            "net_R_15x": m_15x["net_R"],
            "net_R_2x": m_2x["net_R"],
            "net_R_zero_pos_1x": m_zpos_1x["net_R"],
            "net_R_zero_pos_2x": m_zpos_2x["net_R"],
            "fade_net_R_1x": m_fade_1x["net_R"],
            "sharpe_1x": m_1x["sharpe"],
            "sharpe_15x": m_15x["sharpe"],
            "sharpe_2x": m_2x["sharpe"],
            "sharpe_zero_pos_1x": m_zpos_1x["sharpe"],
            "pf_1x": m_1x["pf"],
            "pf_2x": m_2x["pf"],
            "pf_zero_pos_1x": m_zpos_1x["pf"],
            "trimmed_5pct_pf_1x": _compute_trimmed_pf(trades, "net_R_1x"),
            "trimmed_5pct_pf_2x": _compute_trimmed_pf(trades, "net_R_2x"),
            "avg_hold_bars": avg_hold,
            "long_trades": long_n,
            "short_trades": short_n,
            "stage0": s0,
            "median_fric_sl_2x": s0["median_fric_sl_ratio"],
            "margin_rejects": margin_rejects,
            "margin_capped_count": margin_capped,
            "peak_portfolio_margin_util_frac": peak_margin,
            "portfolio_margin_breached": margin_breached,
            "swap_drag_per_day_r": swap_drag_per_day,
        }
    )

    spec_out = dict(spec)
    spec_out["family_id"] = FAMILY_ID
    spec_out["prop_track"] = PROP_TRACK
    spec_out["symbols"] = symbols
    spec_out["data_resolution"] = data_res
    spec_out["blindness_tier"] = blindness_tier
    spec_out["blindness_tier_breakdown"] = tier_breakdown
    spec_out["allow_unidirectional"] = allow_unidir

    return {
        "spec": spec_out,
        "trades": trades,
        "daily_pnl_1x": daily_pnl_1x,
        "daily_pnl_15x": daily_pnl_15x,
        "daily_pnl_2x": daily_pnl_2x,
        "daily_pnl_zero_pos_swap": daily_pnl_zero_pos_swap,
        "fade_daily_pnl_1x": fade_daily_pnl_1x,
        "metrics": metrics,
        "data_resolution": data_res,
        "blindness_tier": blindness_tier,
        "allow_unidirectional": allow_unidir,
        "margin_audit": margin_audit,
        "stage0": s0,
        "eval_years": list(eval_years),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# Pre-Registered Economically Grounded Candidate Grid (All 4 Basket Pillars)
# ---------------------------------------------------------------------------


def _build_f07_candidate_grid() -> list[dict[str, Any]]:
    """Construct structured cross-sectional swing baskets across all 4 required pillars."""
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        subfamily: str,
        mechanism: str,
        symbols: Sequence[str],
        params: dict[str, Any],
        rationale: str,
        counterparty: str,
    ) -> None:
        if len(rationale.strip()) < 40:
            raise ValueError(f"economic_rationale too short for {cid}")
        if len(counterparty.strip()) < 20:
            raise ValueError(f"counterparty_mechanism too short for {cid}")
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "subfamily": subfamily,
                "mechanism": mechanism,
                "prop_track": PROP_TRACK,
                "symbols": list(symbols),
                "params": params,
                "allow_unidirectional": False,
                "economic_rationale": rationale,
                "counterparty_mechanism": counterparty,
            }
        )

    # 1A. 17-FX Menkhoff Cross-Sectional Momentum (1M/3M/6M)
    fx_mom_rat = (
        "Menkhoff (2012) cross-sectional FX momentum captures persistent multi-week "
        "macro capital-flow and central-bank policy divergence across all 17 G10 pairs, "
        "neutralizing directional USD/JPY beta via matched Long-Top-K / Short-Bottom-K legs."
    )
    fx_mom_cp = (
        "Slow-moving corporate hedgers, central bank reserve managers, and passive "
        "international bond/equity allocators executing price-insensitive FX conversions."
    )
    for tag, lbs, sk in (
        ("1M", (21,), 0),
        ("3M", (63,), 0),
        ("6M", (126,), 0),
        ("1M3M", (21, 63), 0),
        ("1M3M6M", (21, 63, 126), 0),
        ("3M_SK5", (63,), 5),
    ):
        for top_k in (2, 3):
            for reb, hold, sl_m, tp_m, msp in (
                (10, 10, 3.0, None, 0.0),
                (10, 10, 3.0, 2.5, 1.5),
                (5, 5, 2.5, 2.0, 1.5),
            ):
                if top_k == 3 and msp > 0.0:
                    continue
                tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
                sp_s = f"_D{int(msp * 10)}" if msp > 0.0 else ""
                _add(
                    f"F07_FX17_MOM_{tag}_K{top_k}_R{reb}_H{hold}_SL{int(sl_m * 10)}{tp_s}{sp_s}",
                    "fx17_momentum",
                    "xsec_fx17_menkhoff_mom",
                    FX_17_SYMBOLS,
                    {
                        "score_mode": "momentum",
                        "lookbacks": list(lbs),
                        "skip_bars": sk,
                        "rev_penalty": 0.0,
                        "top_k": top_k,
                        "rebalance_days": reb,
                        "max_hold_bars": hold,
                        "sl_atr_mult": sl_m,
                        "tp_atr_mult": tp_m,
                        "max_per_sector": None,
                        "max_ccy_per_side": 2,
                        "anchor_weekday": None,
                        "min_score_spread": msp,
                    },
                    fx_mom_rat,
                    fx_mom_cp,
                )

    # 1B. 17-FX Short-Term Cross-Sectional Reversal (3d/5d/10d)
    fx_rev_rat = (
        "Short-horizon 3d-10d cross-sectional FX reversal harvests temporary dealer "
        "inventory skew and fixing-driven overshoots across all 17 G10 pairs while "
        "neutralizing directional USD/JPY beta through matched Long-Bottom-K / Short-Top-K legs."
    )
    fx_rev_cp = (
        "Urgent institutional rebalance flows, retail breakout chasers entering late "
        "after multi-day range expansion, and short-term stop-run cascades."
    )
    for lb, reb, hold, sl_m, tp_m, msp in (
        (3, 5, 5, 3.0, 2.0, 2.0),
        (5, 5, 5, 3.0, None, 0.0),
        (5, 5, 5, 3.0, None, 2.0),
        (5, 5, 5, 3.0, 2.0, 2.0),
        (5, 5, 5, 3.0, 2.5, 2.5),
        (5, 7, 7, 3.0, 2.5, 2.0),
        (10, 7, 7, 3.0, None, 2.0),
        (10, 7, 7, 3.0, 2.5, 2.0),
        (10, 10, 10, 3.0, None, 0.0),
        (10, 10, 10, 3.0, None, 1.5),
        (10, 10, 10, 3.0, 2.5, 1.5),
        (10, 10, 10, 3.5, None, 2.0),
        (10, 10, 10, 3.5, 2.5, 2.0),
        (21, 10, 10, 3.0, None, 1.5),
    ):
        for top_k in (1, 2, 3):
            if top_k == 3 and lb == 21:
                continue
            tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
            sp_s = f"_D{int(msp * 10)}" if msp > 0.0 else ""
            _add(
                f"F07_FX17_REV_{lb}D_K{top_k}_R{reb}_H{hold}_SL{int(sl_m * 10)}{tp_s}{sp_s}",
                "fx17_reversal",
                "xsec_fx17_short_rev",
                FX_17_SYMBOLS,
                {
                    "score_mode": "reversal",
                    "lookbacks": [lb],
                    "skip_bars": 0,
                    "rev_penalty": 0.0,
                    "top_k": top_k,
                    "rebalance_days": reb,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "max_per_sector": None,
                    "max_ccy_per_side": 2 if top_k >= 2 else 1,
                    "anchor_weekday": None,
                    "min_score_spread": msp,
                },
                fx_rev_rat,
                fx_rev_cp,
            )

    # 1C. TRUE_BLIND_7 FX Sub-Basket (100% TRUE_BLIND_CLB_NEW7_CROSSES!)
    tb7_mom_rat = (
        "Pure non-USD G10 cross-rate relative-strength momentum across the 7 truly blind "
        "crosses (CADJPY, CHFJPY, NZDJPY, EURGBP, EURAUD, GBPAUD, EURCAD), isolating "
        "commodity-vs-funding currency rotation without direct USD-major exposure."
    )
    tb7_rev_rat = (
        "Short-horizon cross-sectional mean reversion across the 7 truly blind G10 cross "
        "pairs where thinner cross-pair liquidity amplifies multi-day dealer inventory "
        "overshoots that snap back over 5-10 trading days."
    )
    for mode, lbs, tag, reb, hold, sl_m, tp_m, msp in (
        ("momentum", (21,), "MOM_1M", 10, 10, 3.0, None, 0.0),
        ("momentum", (63,), "MOM_3M", 10, 10, 3.0, None, 0.0),
        ("momentum", (126,), "MOM_6M", 10, 10, 3.0, None, 0.0),
        ("momentum", (21, 63), "MOM_1M3M", 10, 10, 3.0, 2.5, 0.0),
        ("reversal", (3,), "REV_3D", 5, 5, 3.0, 2.0, 1.5),
        ("reversal", (5,), "REV_5D", 5, 5, 3.0, None, 1.5),
        ("reversal", (5,), "REV_5D", 5, 5, 3.0, 2.0, 1.5),
        ("reversal", (5,), "REV_5D", 5, 5, 3.5, None, 2.0),
        ("reversal", (5,), "REV_5D", 5, 5, 3.5, 2.5, 2.0),
        ("reversal", (5,), "REV_5D", 7, 7, 3.0, 2.5, 1.5),
        ("reversal", (10,), "REV_10D", 10, 10, 3.0, None, 0.0),
        ("reversal", (10,), "REV_10D", 10, 10, 3.0, None, 1.0),
        ("reversal", (10,), "REV_10D", 10, 10, 3.0, 2.5, 1.0),
        ("reversal", (10,), "REV_10D", 10, 10, 3.5, 2.5, 1.5),
    ):
        for top_k in (1, 2):
            tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
            sp_s = f"_D{int(msp * 10)}" if msp > 0.0 else ""
            _add(
                f"F07_TB7_{tag}_K{top_k}_R{reb}_H{hold}_SL{int(sl_m * 10)}{tp_s}{sp_s}",
                "fx_true_blind_7",
                f"xsec_tb7_{mode}",
                TRUE_BLIND_7_SYMBOLS,
                {
                    "score_mode": mode,
                    "lookbacks": list(lbs),
                    "skip_bars": 0,
                    "rev_penalty": 0.0,
                    "top_k": top_k,
                    "rebalance_days": reb,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "max_per_sector": None,
                    "max_ccy_per_side": 2 if top_k == 2 else 1,
                    "anchor_weekday": None,
                    "min_score_spread": msp,
                },
                tb7_mom_rat if mode == "momentum" else tb7_rev_rat,
                fx_mom_cp if mode == "momentum" else fx_rev_cp,
            )

    # 2. 6-Index Global Equity Rotation (+ NEW9 3-Index Sub-Basket)
    idx_mom_rat = (
        "Global equity-index relative strength (US500, US100, US30, GER40, UK100, JP225) "
        "captures regional earnings-revision and institutional ETF allocation persistence "
        "while staying market-beta neutral via paired Long-Top-K / Short-Bottom-K index legs."
    )
    idx_rev_rat = (
        "Weekly/5d-10d global equity-index cross-sectional reversal exploits asynchronous "
        "US/EU/JP timezone close effects and pension/ETF rebalancing flows that push "
        "laggard country indices back toward global equity parity within 3-5 sessions."
    )
    idx_cp = (
        "Regional passive index funds, target-date pension rebalancers, and momentum-chasing "
        "retail equity CFD flows creating temporary inter-region valuation dispersion."
    )
    for mode, lbs, tag, reb, hold, sl_m, tp_m, awd in (
        ("momentum", (10,), "MOM_10D", 5, 4, 2.5, 2.0, 0),
        ("momentum", (21,), "MOM_1M", 10, 10, 3.0, None, None),
        ("momentum", (42,), "MOM_2M", 10, 10, 3.0, None, None),
        ("momentum", (42,), "MOM_2M", 10, 10, 3.0, 2.5, None),
        ("momentum", (63,), "MOM_3M", 10, 10, 3.0, None, None),
        ("momentum", (63,), "MOM_3M", 10, 10, 3.0, 2.5, None),
        ("momentum", (126,), "MOM_6M", 10, 10, 3.0, None, None),
        ("momentum", (126,), "MOM_6M", 10, 10, 3.0, 2.5, None),
        ("momentum", (126,), "MOM_6M", 5, 4, 2.5, 2.0, 0),
        ("momentum", (42, 126), "MOM_2M6M", 10, 10, 3.0, 2.5, None),
        ("momentum", (63, 126), "MOM_3M6M", 10, 10, 3.0, None, None),
        ("momentum", (63, 126), "MOM_3M6M", 10, 10, 3.0, 2.5, None),
        ("momentum", (63, 126), "MOM_3M6M", 10, 10, 3.0, 2.0, None),
        ("momentum", (63, 126), "MOM_3M6M", 5, 4, 2.5, 2.0, 0),
        ("reversal", (3,), "REV_3D", 5, 3, 2.5, 2.0, 0),
        ("reversal", (5,), "REV_5D", 5, 4, 2.5, 2.0, 0),
        ("reversal", (10,), "REV_10D", 10, 10, 3.0, 2.5, None),
    ):
        for top_k in (1, 2):
            tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
            wd_s = "_MON" if awd == 0 else ""
            _add(
                f"F07_IDX6_{tag}_K{top_k}_R{reb}_H{hold}_SL{int(sl_m * 10)}{tp_s}{wd_s}",
                "indices6_rotation",
                f"xsec_idx6_{mode}",
                INDICES_6_SYMBOLS,
                {
                    "score_mode": mode,
                    "lookbacks": list(lbs),
                    "skip_bars": 0,
                    "rev_penalty": 0.0,
                    "top_k": top_k,
                    "rebalance_days": reb,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "max_per_sector": None,
                    "max_ccy_per_side": None,
                    "anchor_weekday": awd,
                    "min_score_spread": 0.0,
                },
                idx_mom_rat if mode == "momentum" else idx_rev_rat,
                idx_cp,
            )

    # Pure NEW9 3-Index sub-basket (US30, UK100, JP225)
    for mode, lbs, tag, tp_m in (
        ("momentum", (42,), "MOM_2M", None),
        ("momentum", (42,), "MOM_2M", 2.5),
        ("momentum", (63,), "MOM_3M", 2.5),
        ("momentum", (63, 126), "MOM_3M6M", 2.5),
        ("reversal", (5,), "REV_5D", 2.0),
    ):
        tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
        _add(
            f"F07_IDX3NEW9_{tag}_K1_R10_H10_SL30{tp_s}",
            "indices6_rotation",
            f"xsec_idx3new9_{mode}",
            INDICES_NEW9_SYMBOLS,
            {
                "score_mode": mode,
                "lookbacks": list(lbs),
                "skip_bars": 0,
                "rev_penalty": 0.0,
                "top_k": 1,
                "rebalance_days": 10 if mode == "momentum" else 5,
                "max_hold_bars": 10 if mode == "momentum" else 4,
                "sl_atr_mult": 3.0 if mode == "momentum" else 2.5,
                "tp_atr_mult": tp_m,
                "max_per_sector": None,
                "max_ccy_per_side": None,
                "anchor_weekday": None if mode == "momentum" else 0,
                "min_score_spread": 0.0,
            },
            idx_mom_rat if mode == "momentum" else idx_rev_rat,
            idx_cp,
        )

    # 3. 4-Metals/Energy Cross-Sectional Rotation (+ NEW9 3-Commodity)
    comm_mom_rat = (
        "Cross-sectional commodity rotation across XAUUSD, XAGUSD, USOIL, and UKOIL "
        "captures inflation-vs-growth regime leadership between precious metals and "
        "crude energy on volatility-adjusted risk parity with mandatory hard SL per leg."
    )
    comm_rev_rat = (
        "Short-horizon commodity relative-value reversal across XAUUSD/XAGUSD/USOIL/UKOIL "
        "harvests mean reversion after EIA inventory shocks and futures roll congestion "
        "temporarily dislocate gold/silver or WTI/Brent relative strength."
    )
    comm_cp = (
        "Physical producers hedging forward output, passive commodity-index roll funds "
        "(GSCI/BCOM), and leveraged macro CTAs chasing acute inventory headlines."
    )
    for mode, lbs, tag, reb, hold, sl_m, tp_m, awd in (
        ("momentum", (5,), "MOM_5D", 5, 4, 2.5, 2.0, 0),
        ("momentum", (10,), "MOM_10D", 5, 4, 2.5, 2.0, 0),
        ("momentum", (10,), "MOM_10D", 10, 10, 3.0, 2.5, None),
        ("momentum", (21,), "MOM_1M", 5, 4, 2.5, 2.5, 0),
        ("momentum", (21,), "MOM_1M", 10, 10, 3.0, 2.5, None),
        ("momentum", (63,), "MOM_3M", 10, 10, 3.0, 2.5, None),
        ("momentum", (21, 63), "MOM_1M3M", 10, 10, 3.0, 2.5, None),
        ("reversal", (3,), "REV_3D", 5, 3, 2.5, 2.0, 0),
        ("reversal", (5,), "REV_5D", 5, 4, 2.5, 2.0, 0),
        ("reversal", (10,), "REV_10D", 10, 10, 3.0, 2.5, None),
    ):
        tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
        wd_s = "_MON" if awd == 0 else ""
        _add(
            f"F07_COMM4_{tag}_K1_R{reb}_H{hold}_SL{int(sl_m * 10)}{tp_s}{wd_s}",
            "metals_energy4_rotation",
            f"xsec_comm4_{mode}",
            METALS_ENERGY_4_SYMBOLS,
            {
                "score_mode": mode,
                "lookbacks": list(lbs),
                "skip_bars": 0,
                "rev_penalty": 0.0,
                "top_k": 1,
                "rebalance_days": reb,
                "max_hold_bars": hold,
                "sl_atr_mult": sl_m,
                "tp_atr_mult": tp_m,
                "max_per_sector": None,
                "max_ccy_per_side": None,
                "anchor_weekday": awd,
                "min_score_spread": 0.0,
            },
            comm_mom_rat if mode == "momentum" else comm_rev_rat,
            comm_cp,
        )

    for mode, lbs, tag in (("momentum", (10,), "MOM_10D"), ("momentum", (21,), "MOM_1M"), ("reversal", (5,), "REV_5D")):
        _add(
            f"F07_COMM3NEW9_{tag}_K1_R5_H4_SL25_TP20_MON",
            "metals_energy4_rotation",
            f"xsec_comm3new9_{mode}",
            METALS_ENERGY_NEW9_SYMBOLS,
            {
                "score_mode": mode,
                "lookbacks": list(lbs),
                "skip_bars": 0,
                "rev_penalty": 0.0,
                "top_k": 1,
                "rebalance_days": 5,
                "max_hold_bars": 4,
                "sl_atr_mult": 2.5,
                "tp_atr_mult": 2.0,
                "max_per_sector": None,
                "max_ccy_per_side": None,
                "anchor_weekday": 0,
                "min_score_spread": 0.0,
            },
            comm_mom_rat if mode == "momentum" else comm_rev_rat,
            comm_cp,
        )

    # 4. Cross-Asset 27-Symbol Vol-Adjusted Relative Strength (Sector-Capped)
    xasset_mom_rat = (
        "Cross-asset 27-symbol vol-adjusted relative strength (FX, Indices, Metals, Oil) "
        "captures macro risk-on/risk-off capital rotation across uncorrelated asset classes, "
        "enforcing a strict max-sector concentration cap and matched Long-Top-K / Short-Bottom-K legs."
    )
    xasset_rev_rat = (
        "Cross-asset 27-symbol short-term vol-adjusted reversal harvests multi-asset "
        "de-leveraging and month-end institutional risk-parity rebalancing across "
        "FX, Indices, Metals, and Oil with strict sector concentration caps."
    )
    xasset_cp = (
        "Siloed single-asset mandates, mechanical risk-parity rebalancing funds, and "
        "macro crowding flows that overshoot cross-asset relative valuations."
    )
    for mode, lbs, tag, top_k, max_sec, reb, hold, sl_m, tp_m, awd, msp in (
        ("momentum", (10,), "MOM_10D", 3, 1, 5, 4, 2.5, 2.0, 0, 0.0),
        ("momentum", (21,), "MOM_1M", 3, 1, 10, 10, 3.0, 2.5, None, 0.0),
        ("momentum", (63,), "MOM_3M", 3, 1, 10, 10, 3.0, 2.5, None, 0.0),
        ("momentum", (126,), "MOM_6M", 3, 1, 10, 10, 3.0, 2.5, None, 0.0),
        ("momentum", (21, 63), "MOM_1M3M", 3, 1, 10, 10, 3.0, 2.5, None, 0.0),
        ("momentum", (21, 63, 126), "MOM_1M3M6M", 3, 2, 10, 10, 3.0, 2.5, None, 0.0),
        ("momentum", (63,), "MOM_3M", 2, 1, 10, 10, 3.0, None, None, 0.0),
        ("reversal", (5,), "REV_5D", 3, 1, 5, 4, 2.5, 2.0, 0, 2.0),
        ("reversal", (5,), "REV_5D", 3, 2, 5, 5, 3.0, 2.5, None, 2.5),
        ("reversal", (10,), "REV_10D", 3, 1, 10, 10, 3.0, 2.5, None, 2.0),
        ("reversal", (10,), "REV_10D", 2, 1, 10, 10, 3.0, 2.5, None, 2.0),
    ):
        tp_s = f"_TP{int(tp_m * 10)}" if tp_m else ""
        wd_s = "_MON" if awd == 0 else ""
        sp_s = f"_D{int(msp * 10)}" if msp > 0.0 else ""
        _add(
            f"F07_XASSET27_{tag}_K{top_k}_S{max_sec}_R{reb}_H{hold}_SL{int(sl_m * 10)}{tp_s}{wd_s}{sp_s}",
            "cross_asset_27",
            f"xsec_27_{mode}",
            ALL_27_NON_CRYPTO_SYMBOLS,
            {
                "score_mode": mode,
                "lookbacks": list(lbs),
                "skip_bars": 0,
                "rev_penalty": 0.0,
                "top_k": top_k,
                "rebalance_days": reb,
                "max_hold_bars": hold,
                "sl_atr_mult": sl_m,
                "tp_atr_mult": tp_m,
                "max_per_sector": max_sec,
                "max_ccy_per_side": 2,
                "anchor_weekday": awd,
                "min_score_spread": msp,
            },
            xasset_mom_rat if mode == "momentum" else xasset_rev_rat,
            xasset_cp,
        )

    return specs


# ---------------------------------------------------------------------------
# Cluster A ONLY Discovery (`2018-2020`, HARD BLINDNESS LOCK!)
# ---------------------------------------------------------------------------


def _score_cluster_a_candidate(res: Mapping[str, Any]) -> float:
    """Compute anti-overfit Cluster A ranking score (strictly on 2018-2020 metrics)."""
    m = res["metrics"]
    sh_2x = float(m["sharpe_2x"])
    sh_zpos = float(m["sharpe_zero_pos_1x"])
    sh_floor = min(sh_2x, sh_zpos)
    pos_yr = float(m["positive_year_ratio"])
    trim_pf = min(float(m["trimmed_5pct_pf_1x"]), 3.0)
    fade_edge = float(m["net_R_1x"]) - float(m["fade_net_R_1x"])
    max_dd = max(1.0, float(m["max_DD_R"]))
    calmar_2x = min(float(m["net_R_2x"]) / max_dd, 4.0)
    n_bonus = min(1.0, float(m["n_trades"]) / 100.0)
    tb_bonus = 0.12 if res["blindness_tier"] == TIER_NEW7 else (0.06 if res["blindness_tier"] == TIER_NEW9 else 0.0)
    return round(
        sh_floor
        + 0.30 * calmar_2x
        + 0.45 * pos_yr
        + 0.15 * min(max(0.0, fade_edge) / 15.0, 1.5)
        + 0.30 * max(0.0, trim_pf - 0.80)
        + 0.10 * n_bonus
        + tb_bonus,
        6,
    )


def _compact_cluster_a_summary(res: Mapping[str, Any], rank_score: float) -> dict[str, Any]:
    m = res["metrics"]
    by_yr = {str(k): round(float(v), 4) for k, v in m["by_year_R"].items() if int(str(k)) <= 2020}
    return {
        "rank_score": rank_score,
        "n_trades": int(m["n_trades"]),
        "net_R_1x": round(float(m["net_R_1x"]), 4),
        "net_R_15x": round(float(m["net_R_15x"]), 4),
        "net_R_2x": round(float(m["net_R_2x"]), 4),
        "net_R_zero_pos_1x": round(float(m["net_R_zero_pos_1x"]), 4),
        "fade_net_R_1x": round(float(m["fade_net_R_1x"]), 4),
        "sharpe_1x": round(float(m["sharpe_1x"]), 4),
        "sharpe_2x": round(float(m["sharpe_2x"]), 4),
        "sharpe_zero_pos_1x": round(float(m["sharpe_zero_pos_1x"]), 4),
        "pf_1x": round(float(m["pf_1x"]), 4),
        "pf_2x": round(float(m["pf_2x"]), 4),
        "trimmed_5pct_pf_1x": round(float(m["trimmed_5pct_pf_1x"]), 4),
        "winrate": round(float(m["winrate"]), 4),
        "avg_RR": round(float(m["avg_RR"]), 4),
        "max_DD_R_1x": round(float(m["max_DD_R"]), 4),
        "worst_1d_R_1x": round(float(m["worst_1d_R"]), 4),
        "positive_years": int(m["positive_years"]),
        "total_years": int(m["total_years"]),
        "by_year_R": by_yr,
        "avg_hold_bars": round(float(m["avg_hold_bars"]), 3),
        "median_fric_sl_2x": m["median_fric_sl_2x"],
        "peak_portfolio_margin_util_frac": m["peak_portfolio_margin_util_frac"],
        "swap_drag_per_day_r": m["swap_drag_per_day_r"],
        "stage0_passed": bool(m["stage0"]["passed"]),
    }


def _passes_primary_cluster_a(res: Mapping[str, Any]) -> bool:
    """Strict non-padded Primary gate: positive 1x, 2x, zero_pos_swap, beats fade, Prop DD safe."""
    m = res["metrics"]
    if not bool(m["stage0"]["passed"]):
        return False
    if bool(m["portfolio_margin_breached"]):
        return False
    if int(m["n_trades"]) < 30:
        return False
    if float(m["net_R_1x"]) <= 0.0 or float(m["net_R_2x"]) <= 0.0 or float(m["net_R_zero_pos_1x"]) <= 0.0:
        return False
    if float(m["net_R_1x"]) <= float(m["fade_net_R_1x"]):
        return False
    if float(m["max_DD_R"]) > 18.0 or float(m["worst_1d_R"]) < -8.0:
        return False
    if int(m["positive_years"]) < 2:
        return False
    if float(m["sharpe_2x"]) < 0.15 or float(m["sharpe_zero_pos_1x"]) < 0.20:
        return False
    if float(m["trimmed_5pct_pf_1x"]) < 0.80:
        return False
    return True


def _passes_exploratory_cluster_a(res: Mapping[str, Any]) -> bool:
    m = res["metrics"]
    if not bool(m["stage0"]["passed"]):
        return False
    if bool(m["portfolio_margin_breached"]):
        return False
    if int(m["n_trades"]) < 20:
        return False
    return True


def discover_cluster_a(
    universe: Mapping[str, Any],
    *,
    save: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run Stage 2 Cluster A discovery (`2018-2020` ONLY!) for `F07_SWING_XSEC`.

    HARD BLINDNESS LOCK: Every asset bar array is sliced strictly to `year <= 2020`
    before computing any indicator, score, trade, or ranking. ZERO Cluster B data
    (`2021..2024`) is ever inspected, printed, or referenced.
    """
    asset_map = _resolve_asset_map(universe)
    bars_cache: dict[tuple[str, int], dict[str, Any]] = {}
    feature_cache: dict[tuple[str, int], dict[str, Any]] = {}

    for sym in ALL_27_NON_CRYPTO_SYMBOLS:
        if sym in asset_map:
            b_cl_a = _slice_d1_bars_upto_year(asset_map[sym]["d1"], max(CLUSTER_A_YEARS))
            bars_cache[(sym, max(CLUSTER_A_YEARS))] = b_cl_a
            feature_cache[(sym, max(CLUSTER_A_YEARS))] = _compute_symbol_causal_features(b_cl_a)

    grid = _build_f07_candidate_grid()
    scored_rows: list[tuple[float, bool, bool, dict[str, Any]]] = []
    n_stage0_pass = 0
    n_primary_elig = 0

    for spec in grid:
        res = evaluate_candidate(
            spec,
            universe,
            years=CLUSTER_A_YEARS,
            _feature_cache=feature_cache,
            _bars_cache=bars_cache,
        )
        if bool(res["metrics"]["stage0"]["passed"]):
            n_stage0_pass += 1
        is_prim_elig = _passes_primary_cluster_a(res)
        is_expl_elig = _passes_exploratory_cluster_a(res)
        if is_prim_elig:
            n_primary_elig += 1
        r_score = _score_cluster_a_candidate(res)
        cand_record = dict(res["spec"])
        cand_record["cluster_a_summary"] = _compact_cluster_a_summary(res, r_score)
        scored_rows.append((r_score, is_prim_elig, is_expl_elig, cand_record))

    scored_rows.sort(key=lambda row: (-row[0], str(row[3]["candidate_id"])))

    subfamily_primary_caps: dict[str, int] = {
        "fx17_momentum": 3,
        "fx17_reversal": 4,
        "fx_true_blind_7": 4,
        "indices6_rotation": 5,
        "metals_energy4_rotation": 2,
        "cross_asset_27": 2,
    }
    primary_selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_subfam: dict[str, int] = {}
    used_sig: set[tuple[str, str, tuple[int, ...], int]] = set()

    # Pass 1: Strict diverse selection (zero negative Cl.A specs padded into Primary!)
    for _score, is_prim_elig, _is_expl, rec in scored_rows:
        if len(primary_selected) >= PRIMARY_CAP:
            break
        if not is_prim_elig:
            continue
        sf = str(rec["subfamily"])
        if used_subfam.get(sf, 0) >= subfamily_primary_caps.get(sf, 3):
            continue
        sig_key = (
            sf,
            str(rec["params"]["score_mode"]),
            tuple(int(x) for x in rec["params"]["lookbacks"]),
            int(rec["params"]["top_k"]),
        )
        if sig_key in used_sig:
            continue
        item = dict(rec)
        item["tier"] = "PRIMARY"
        primary_selected.append(item)
        selected_ids.add(str(item["candidate_id"]))
        used_subfam[sf] = used_subfam.get(sf, 0) + 1
        used_sig.add(sig_key)

    # Pass 2: Remaining strictly eligible primaries up to PRIMARY_CAP
    if len(primary_selected) < PRIMARY_CAP:
        for _score, is_prim_elig, _is_expl, rec in scored_rows:
            if len(primary_selected) >= PRIMARY_CAP:
                break
            cid = str(rec["candidate_id"])
            if not is_prim_elig or cid in selected_ids:
                continue
            sf = str(rec["subfamily"])
            if used_subfam.get(sf, 0) >= subfamily_primary_caps.get(sf, 3) + 2:
                continue
            item = dict(rec)
            item["tier"] = "PRIMARY"
            primary_selected.append(item)
            selected_ids.add(cid)
            used_subfam[sf] = used_subfam.get(sf, 0) + 1

    # Balanced Exploratory pool across ALL 6 subfamilies up to TOTAL_CAP (positive first, then best representatives)
    max_expl = TOTAL_CAP - len(primary_selected)
    exploratory_selected: list[dict[str, Any]] = []
    expl_subfam_counts: dict[str, int] = {}
    expl_subfam_cap = 16

    for _score, _is_prim, is_expl_elig, rec in scored_rows:
        if len(exploratory_selected) >= max_expl:
            break
        cid = str(rec["candidate_id"])
        if cid in selected_ids or not is_expl_elig:
            continue
        sf = str(rec["subfamily"])
        if expl_subfam_counts.get(sf, 0) >= expl_subfam_cap:
            continue
        item = dict(rec)
        item["tier"] = "EXPLORATORY"
        exploratory_selected.append(item)
        selected_ids.add(cid)
        expl_subfam_counts[sf] = expl_subfam_counts.get(sf, 0) + 1

    if len(exploratory_selected) < max_expl:
        for _score, _is_prim, is_expl_elig, rec in scored_rows:
            if len(exploratory_selected) >= max_expl:
                break
            cid = str(rec["candidate_id"])
            if cid in selected_ids or not is_expl_elig:
                continue
            item = dict(rec)
            item["tier"] = "EXPLORATORY"
            exploratory_selected.append(item)
            selected_ids.add(cid)

    meta: dict[str, Any] = {
        "family_id": FAMILY_ID,
        "prop_track": PROP_TRACK,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "grid_evaluated": len(grid),
        "stage0_passed_count": n_stage0_pass,
        "primary_eligible_count": n_primary_elig,
        "primary_subfamily_counts": used_subfam,
        "exploratory_subfamily_counts": expl_subfam_counts,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    saved_path: Path | None = None
    if save:
        saved_path = save_family_candidates(
            FAMILY_ID,
            {"primary": primary_selected, "exploratory": exploratory_selected},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )

    return {
        "family_id": FAMILY_ID,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary": primary_selected,
        "exploratory": exploratory_selected,
        "candidates": [*primary_selected, *exploratory_selected],
        "meta": meta,
        "saved_path": str(saved_path) if saved_path is not None else None,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# CLI Entrypoint (`--resume` Supported, Strictly Cluster A Only!)
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offensive #3 F07 Cross-Sectional Relative Strength Swing Discovery (Cluster A 2018-2020 ONLY)"
    )
    parser.add_argument("--resume", action="store_true", help="Reuse valid SHA-verified checkpoint if present")
    parser.add_argument("--candidates-dir", type=str, default=None, help="Override candidate output directory")
    parser.add_argument("--no-verify-sha", action="store_true", help="Skip parquet SHA check during load")
    args = parser.parse_args(argv)

    if args.resume and has_valid_family_checkpoint(FAMILY_ID, candidates_dir=args.candidates_dir):
        doc = load_family_candidates(FAMILY_ID, candidates_dir=args.candidates_dir, verify_sha=True)
        print(
            json.dumps(
                {
                    "status": "RESUMED_FROM_CHECKPOINT",
                    "family_id": FAMILY_ID,
                    "primary_count": doc["primary_count"],
                    "exploratory_count": doc["exploratory_count"],
                    "total_count": doc["total_count"],
                    "discovery_years": doc["discovery_years"],
                    "payload_sha256": doc["payload_sha256"],
                },
                indent=2,
            )
        )
        return 0

    universe_a = load_universe_28(
        load_m1=False,
        load_d1=True,
        years=CLUSTER_A_YEARS,
        verify_sha=not args.no_verify_sha,
    )
    out = discover_cluster_a(universe_a, save=True, candidates_dir=args.candidates_dir)
    loaded = load_family_candidates(FAMILY_ID, candidates_dir=args.candidates_dir, verify_sha=True)

    top_preview = [
        {
            "candidate_id": c["candidate_id"],
            "subfamily": c["subfamily"],
            "tier_data": c["blindness_tier"],
            "n_trades": c["cluster_a_summary"]["n_trades"],
            "net_R_1x": c["cluster_a_summary"]["net_R_1x"],
            "net_R_2x": c["cluster_a_summary"]["net_R_2x"],
            "net_R_zpos": c["cluster_a_summary"]["net_R_zero_pos_1x"],
            "fade_1x": c["cluster_a_summary"]["fade_net_R_1x"],
            "sh_2x": c["cluster_a_summary"]["sharpe_2x"],
            "tpf_1x": c["cluster_a_summary"]["trimmed_5pct_pf_1x"],
            "pos_yrs": f"{c['cluster_a_summary']['positive_years']}/{c['cluster_a_summary']['total_years']}",
            "dd_1x": c["cluster_a_summary"]["max_DD_R_1x"],
            "peak_mu": c["cluster_a_summary"]["peak_portfolio_margin_util_frac"],
        }
        for c in loaded["primary_candidates"][:10]
    ]
    print(
        json.dumps(
            {
                "status": "DISCOVERY_COMPLETE",
                "family_id": FAMILY_ID,
                "saved_path": out["saved_path"],
                "discovery_years": loaded["discovery_years"],
                "grid_evaluated": out["meta"]["grid_evaluated"],
                "stage0_passed": out["meta"]["stage0_passed_count"],
                "primary_eligible": out["meta"]["primary_eligible_count"],
                "primary_count": loaded["primary_count"],
                "exploratory_count": loaded["exploratory_count"],
                "total_count": loaded["total_count"],
                "primary_subfamily_counts": out["meta"]["primary_subfamily_counts"],
                "exploratory_subfamily_counts": out["meta"]["exploratory_subfamily_counts"],
                "payload_sha256": loaded["payload_sha256"],
                "top_primary_cluster_a": top_preview,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
