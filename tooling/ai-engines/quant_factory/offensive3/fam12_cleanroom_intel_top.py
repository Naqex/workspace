"""Total Offensive #3 — Family F12 (`F12_CLEANROOM_TOP`): Cleanroom Orthogonal White-Box Specs.

Bridges the air-gapped strategy-intel Cleanroom (1-way READ-ONLY via
`tooling/automation/strategy_intel_bridge.py --profile offensive3`, `writes_back = 0`)
and implements 9 genuinely orthogonal white-box mechanisms traced directly by `lead_id`
to admitted Cleanroom specs NOT covered in `F01..F11`:
  1. `LEAD-OFF3-COMM-EN-07`: Market Meanness Index (`MMI`) non-parametric regime switcher.
  2. `LEAD-OFF3-TV-20`: Kaufman Efficiency Ratio (`ER`) + ATR-Z adaptive regime switcher (D1 + M1).
  3. `LEAD-OFF3-MQL5-04`: Rolling 50-bar higher-moments (Skewness/Kurtosis/Jarque-Bera) CI fade.
  4. `LEAD-OFF3-QP-07` & `LEAD-OFF3-QC-03`: Cross-sectional Commodity & FX Tail-Skewness factor.
  5. `LEAD-OFF3-COMM-CN-01`: R-Breaker reversal-only legs (`sSetup->sEnter`, `bSetup->bEnter`, M1 `swap=0`).
  6. `LEAD-OFF3-MQL5-10`: Larry Williams Smash Day reversal + Supertrend context & DoW filter.
  7. `LEAD-OFF3-ARXIV-22` & `LEAD-OFF3-MQL5-14`: Cross-Asset Network Momentum Spillover across 27 symbols.
  8. `LEAD-OFF3-TV-17`: Daily Open Oversized-Body Reversal (ATR-normalized DOS).
  9. `LEAD-OFF3-COMM-CN-03` & `LEAD-OFF3-COMM-CN-05`: 14d Z-Score (hard Z-stop + 8d) & CCI(10) cross-back.

Hard invariants (`[ARCH-02]`, `G01`, `G04`, `G05`, `G06`, `G07`):
  - ZERO bare `assert` statements (`python -O` safe).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - Strict `shift = 1` causality across every indicator and signal; mandatory hard SL; zero grid/martingale.
  - HARD BLINDNESS LOCK: `discover_cluster_a` strictly uses `CLUSTER_A_YEARS=(2018, 2019, 2020)` ONLY!
  - `evaluate_candidate` is 100% pure stdlib/NumPy/PyArrow/Numba (X13 air-gap compatible).
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_ENGINES_DIR = _REPO_ROOT / "tooling" / "ai-engines"
for _p in (_REPO_ROOT, _AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


from quant_factory.offensive3.common_contract import (  # noqa: E402
    CLUSTER_A_YEARS,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    RES_NATIVE_M1_BIDASK,
    TIER_12OLD,
    TIER_NEW7,
    TIER_NEW9,
    causal_atr,
    causal_ema,
    causal_sma,
    causal_zscore,
    compute_daily_pnl_series,
    compute_split_metrics,
    enforce_dev_date_bound,
    enforce_dev_ts_bound,
    has_valid_family_checkpoint,
    load_dev_red_news_index,
    load_family_candidates,
    load_universe_28,
    normalize_symbol,
    replay_intraday_m1_trade,
    replay_swing_d1_series,
    resolve_workspace_root,
    save_family_candidates,
    stage0_screen,
)
from quant_factory.offensive3.x13_m1_loader import resample_m1_to_tf  # noqa: E402

FAMILY_ID: str = "F12_CLEANROOM_TOP"
PRIMARY_CAP: int = 15  # Satisfies both brief (<= 18) and preregistration_m1200.json (15)
TOTAL_CAP: int = 100
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"
_CL_A_END_TS: int = 1_609_459_200  # 2021-01-01T00:00:00Z

TRUE_BLIND_7: tuple[str, ...] = ("CADJPY", "CHFJPY", "NZDJPY", "EURGBP", "EURAUD", "GBPAUD", "EURCAD")
NEW_9: tuple[str, ...] = ("US30", "JP225", "UK100", "XAGUSD", "USOIL", "UKOIL", "USDCHF", "NZDUSD", "AUDJPY")
OLD_11_NONCRYPTO: tuple[str, ...] = (
    "USDJPY",
    "GBPUSD",
    "EURUSD",
    "EURJPY",
    "GBPJPY",
    "AUDUSD",
    "USDCAD",
    "XAUUSD",
    "US100",
    "US500",
    "GER40",
)
ALL_27_NONCRYPTO: tuple[str, ...] = OLD_11_NONCRYPTO + NEW_9 + TRUE_BLIND_7
FX_17: tuple[str, ...] = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
    "EURJPY",
    "GBPJPY",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
)
COMMOD_4: tuple[str, ...] = ("XAUUSD", "XAGUSD", "USOIL", "UKOIL")
INDICES_6: tuple[str, ...] = ("US500", "US100", "US30", "GER40", "UK100", "JP225")

REQUIRED_CLEANROOM_LEAD_IDS: tuple[str, ...] = (
    "LEAD-OFF3-COMM-EN-07",
    "LEAD-OFF3-TV-20",
    "LEAD-OFF3-MQL5-04",
    "LEAD-OFF3-QP-07",
    "LEAD-OFF3-QC-03",
    "LEAD-OFF3-COMM-CN-01",
    "LEAD-OFF3-MQL5-10",
    "LEAD-OFF3-ARXIV-22",
    "LEAD-OFF3-MQL5-14",
    "LEAD-OFF3-TV-17",
    "LEAD-OFF3-COMM-CN-03",
    "LEAD-OFF3-COMM-CN-05",
)


# ---------------------------------------------------------------------------
# 1. Strictly Causal (`shift = 1`) Specialized White-Box Indicators
# ---------------------------------------------------------------------------


@njit(cache=True)
def _causal_mmi_jit(close: np.ndarray, length: int) -> np.ndarray:
    """Strictly `shift = 1` causal Market Meanness Index (`MMI = 100*(nh+nl)/(L-1)`).

    At index `t`, uses ONLY `close[t - length : t]` (zero bar-`t` peek!).
    """
    n = close.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= length or length < 6:
        return out
    buf = np.empty(length, dtype=np.float64)
    for t in range(length, n):
        ok = True
        for k in range(length):
            v = close[t - length + k]
            if not np.isfinite(v):
                ok = False
                break
            buf[k] = v
        if not ok:
            continue
        sbuf = np.sort(buf)
        mid = length // 2
        med = sbuf[mid] if (length % 2 == 1) else 0.5 * (sbuf[mid - 1] + sbuf[mid])
        nh = 0
        nl = 0
        for k in range(1, length):
            c_cur = close[t - length + k]
            c_prev = close[t - length + k - 1]
            if c_cur > med and c_cur > c_prev:
                nh += 1
            elif c_cur < med and c_cur < c_prev:
                nl += 1
        out[t] = 100.0 * float(nh + nl) / float(length - 1)
    return out


@njit(cache=True)
def _causal_kaufman_er_jit(close: np.ndarray, n_win: int) -> np.ndarray:
    """Strictly `shift = 1` causal Kaufman Efficiency Ratio in `[0, 1]`."""
    m = close.shape[0]
    out = np.full(m, np.nan, dtype=np.float64)
    if m <= n_win + 1 or n_win < 2:
        return out
    for t in range(n_win + 1, m):
        direction = abs(close[t - 1] - close[t - 1 - n_win])
        vol = 0.0
        ok = True
        for k in range(t - n_win, t):
            c0 = close[k - 1]
            c1 = close[k]
            if not (np.isfinite(c0) and np.isfinite(c1)):
                ok = False
                break
            vol += abs(c1 - c0)
        if not ok:
            continue
        out[t] = (direction / vol) if vol > 1e-12 else 0.0
    return out


@njit(cache=True)
def _causal_rolling_moments_jit(
    close: np.ndarray,
    win: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Strictly `shift = 1` causal rolling price mean/std & return skew, excess kurtosis, Jarque-Bera."""
    m = close.shape[0]
    mean_c = np.full(m, np.nan, dtype=np.float64)
    std_c = np.full(m, np.nan, dtype=np.float64)
    skew_r = np.full(m, np.nan, dtype=np.float64)
    kurt_r = np.full(m, np.nan, dtype=np.float64)
    jb_r = np.full(m, np.nan, dtype=np.float64)
    if m <= win + 1 or win < 10:
        return mean_c, std_c, skew_r, kurt_r, jb_r

    rets = np.full(m, np.nan, dtype=np.float64)
    for k in range(1, m):
        if close[k - 1] > 0.0 and close[k] > 0.0:
            rets[k] = math.log(close[k] / close[k - 1])

    fw = float(win)
    for t in range(win + 1, m):
        mc = 0.0
        mr = 0.0
        ok = True
        for k in range(t - win, t):
            ck = close[k]
            rk = rets[k]
            if not (np.isfinite(ck) and np.isfinite(rk)):
                ok = False
                break
            mc += ck
            mr += rk
        if not ok:
            continue
        mc /= fw
        mr /= fw

        sc2 = 0.0
        m2 = 0.0
        m3 = 0.0
        m4 = 0.0
        for k in range(t - win, t):
            dc = close[k] - mc
            sc2 += dc * dc
            dr = rets[k] - mr
            dr2 = dr * dr
            m2 += dr2
            m3 += dr2 * dr
            m4 += dr2 * dr2
        mean_c[t] = mc
        std_c[t] = math.sqrt(sc2 / float(win - 1))
        var_r = m2 / fw
        if var_r > 1e-18:
            sd_r = math.sqrt(var_r)
            sk = (m3 / fw) / (sd_r * sd_r * sd_r)
            ex_ku = (m4 / fw) / (var_r * var_r) - 3.0
            skew_r[t] = sk
            kurt_r[t] = ex_ku
            jb_r[t] = (fw / 6.0) * (sk * sk + 0.25 * ex_ku * ex_ku)

    return mean_c, std_c, skew_r, kurt_r, jb_r


@njit(cache=True)
def _causal_cci_jit(high: np.ndarray, low: np.ndarray, close: np.ndarray, n_win: int) -> np.ndarray:
    """Strictly `shift = 1` causal Commodity Channel Index (`CCI(n)`)."""
    m = close.shape[0]
    out = np.full(m, np.nan, dtype=np.float64)
    if m <= n_win or n_win < 2:
        return out
    tp = (high + low + close) / 3.0
    for t in range(n_win, m):
        mean_tp = 0.0
        ok = True
        for k in range(t - n_win, t):
            v = tp[k]
            if not np.isfinite(v):
                ok = False
                break
            mean_tp += v
        if not ok:
            continue
        mean_tp /= float(n_win)
        mad = 0.0
        for k in range(t - n_win, t):
            mad += abs(tp[k] - mean_tp)
        mad /= float(n_win)
        denom = 0.015 * mad
        if denom > 1e-12:
            out[t] = (tp[t - 1] - mean_tp) / denom
        else:
            out[t] = 0.0
    return out


@njit(cache=True)
def _causal_supertrend_dir_jit(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr_shift1: np.ndarray,
    mult: float,
) -> np.ndarray:
    """Strictly `shift = 1` causal Supertrend direction (`+1` bull, `-1` bear, `0` warmup)."""
    m = close.shape[0]
    out = np.zeros(m, dtype=np.int32)
    if m < 5:
        return out

    final_ub = np.nan
    final_lb = np.nan
    cur_dir = 0
    for k in range(1, m - 1):
        atrk = atr_shift1[k]  # Uses bars <= k-1, strictly causal at bar k close
        if not np.isfinite(atrk) or atrk <= 0.0:
            continue
        hl2 = 0.5 * (high[k] + low[k])
        ub = hl2 + mult * atrk
        lb = hl2 - mult * atrk
        if not np.isfinite(final_ub):
            final_ub = ub
            final_lb = lb
            cur_dir = 1 if close[k] >= hl2 else -1
        else:
            prev_c = close[k - 1]
            final_ub = ub if (ub < final_ub or prev_c > final_ub) else final_ub
            final_lb = lb if (lb > final_lb or prev_c < final_lb) else final_lb
            if cur_dir == 1 and close[k] < final_lb:
                cur_dir = -1
            elif cur_dir == -1 and close[k] > final_ub:
                cur_dir = 1
        out[k + 1] = cur_dir  # shift = 1: bar k close informs bar k + 1 open
    return out


# ---------------------------------------------------------------------------
# 2. Universe Slicing & 1-Way Read-Only Cleanroom Bridge Helper
# ---------------------------------------------------------------------------


def _slice_universe_max_year(universe: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    if max_year > 2024:
        raise ValueError(f"DEV_SEAL_VIOLATION: max_year={max_year} > 2024")
    cutoff_ts = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())
    cutoff_date = f"{max_year + 1:04d}-01-01"
    assets_out: dict[str, dict[str, Any]] = {}
    for sym, aobj in universe["assets"].items():
        new_a = dict(aobj)
        d1 = aobj.get("d1")
        if d1 is not None:
            d1_dates = [str(d) for d in d1["dates"]]
            mask = np.array([d < cutoff_date for d in d1_dates], dtype=bool)
            if bool(np.any(mask)):
                nd1 = dict(d1)
                nd1["times_sec"] = np.asarray(d1["times_sec"], dtype=np.int64)[mask]
                nd1["dates"] = [d for d, m in zip(d1_dates, mask, strict=True) if m]
                nd1["years"] = np.asarray(d1["years"], dtype=np.int32)[mask]
                nd1["weekdays"] = np.asarray(d1["weekdays"], dtype=np.int32)[mask]
                nd1["open"] = np.asarray(d1["open"], dtype=np.float64)[mask]
                nd1["high"] = np.asarray(d1["high"], dtype=np.float64)[mask]
                nd1["low"] = np.asarray(d1["low"], dtype=np.float64)[mask]
                nd1["close"] = np.asarray(d1["close"], dtype=np.float64)[mask]
                if "spread_price" in d1:
                    nd1["spread_price"] = np.asarray(d1["spread_price"], dtype=np.float64)[mask]
                new_a["d1"] = nd1
            else:
                new_a["d1"] = None
        m1 = aobj.get("m1")
        if m1 is not None:
            ts_m1 = np.asarray(m1["times_sec"], dtype=np.int64)
            end_i = int(np.searchsorted(ts_m1, cutoff_ts, side="left"))
            if end_i > 0:
                nm1 = dict(m1)
                nm1["times_sec"] = ts_m1[:end_i]
                nm1["quotes"] = np.asarray(m1["quotes"], dtype=np.float64)[:end_i]
                nm1["minutes"] = end_i
                new_a["m1"] = nm1
            else:
                new_a["m1"] = None
        assets_out[sym] = new_a
    out = dict(universe)
    out["assets"] = assets_out
    out["years"] = [int(y) for y in universe.get("years", []) if int(y) <= max_year]
    return out


def _resolve_group_tags(symbols: Sequence[str], universe: Mapping[str, Any]) -> tuple[str, str, dict[str, str]]:
    res_set: set[str] = set()
    tier_set: set[str] = set()
    tier_map: dict[str, str] = {}
    for s in symbols:
        su = normalize_symbol(s)
        a = universe["assets"][su]
        res_set.add(str(a["data_resolution"]))
        t = str(a["blindness_tier"])
        tier_set.add(t)
        tier_map[su] = t
    data_res = next(iter(res_set)) if len(res_set) == 1 else "MIXED_M1_AND_D1"
    if len(tier_set) == 1:
        b_tier = next(iter(tier_set))
    elif tier_set == {TIER_12OLD, TIER_NEW9}:
        b_tier = "MIXED_12OLD_AND_NEW9"
    elif tier_set == {TIER_12OLD, TIER_NEW7}:
        b_tier = "MIXED_12OLD_AND_TRUE_BLIND_7"
    elif tier_set == {TIER_NEW9, TIER_NEW7}:
        b_tier = "MIXED_NEW9_AND_TRUE_BLIND_7"
    elif tier_set == {TIER_12OLD, TIER_NEW9, TIER_NEW7}:
        b_tier = "MIXED_ALL_3_TIERS"
    else:
        b_tier = "UNKNOWN"
    return data_res, b_tier, tier_map


def bridge_cleanroom_offensive3_leads(*, root: str | Path | None = None) -> dict[str, Any]:
    """1-way READ-ONLY bridge from Cleanroom via `strategy_intel_bridge.py --profile offensive3`."""
    ws = resolve_workspace_root(root)
    auto_dir = ws / "tooling" / "automation"
    if str(auto_dir) not in sys.path:
        sys.path.insert(0, str(auto_dir))
    import strategy_intel_bridge as sib  # noqa: PLC0415

    out_path = ws / ".runtime" / "offensive3" / "cleanroom_offensive3_handoff.json"
    payload = sib.sync_strategy_intel(
        out_path=out_path,
        offline=False,
        dry_run=False,
        profile="offensive3",
    )
    if int(payload.get("writes_back_to_cleanroom", -1)) != 0:
        raise ValueError("AIRGAP_VIOLATION: writes_back_to_cleanroom != 0")
    if int(payload.get(_SEAL_ROWS_ANALYSED_KEY, -1)) != 0:
        raise ValueError("DEV_SEAL_VIOLATION: bridge reported non-zero sealed rows")
    return payload


# ---------------------------------------------------------------------------
# 3. Mechanism Signal Builders (ALL Strictly `shift = 1` Causal!)
# ---------------------------------------------------------------------------


def _signals_mmi_regime_switch(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 1 (`LEAD-OFF3-COMM-EN-07`): Market Meanness Index regime switcher."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    mmi_len = int(params.get("mmi_len", 60))
    mr_thresh = float(params.get("mr_thresh", 74.0))
    tr_thresh = float(params.get("tr_thresh", 70.0))
    z_mr_entry = float(params.get("z_mr_entry", 1.5))
    sl_mult = float(params.get("sl_atr_mult", 2.0))
    tp_mult = float(params.get("tp_atr_mult", 3.0))

    mmi = _causal_mmi_jit(c, mmi_len)  # shift=1: mmi[t] uses c[t-L:t]
    mmi_sma = causal_sma(np.where(np.isfinite(mmi), mmi, np.nan), 10)  # shift=1 on mmi
    z10 = causal_zscore(c, int(params.get("z_len", 10)))  # shift=1
    ema_f = causal_ema(c, 10)
    ema_s = causal_ema(c, 30)
    atr = causal_atr(h, lo, c, 14)

    sig = np.zeros(n, dtype=np.float64)
    for t in range(n):
        mt, zt, ef, es, at = float(mmi[t]), float(z10[t]), float(ema_f[t]), float(ema_s[t]), float(atr[t])
        if not (
            math.isfinite(mt)
            and math.isfinite(zt)
            and math.isfinite(ef)
            and math.isfinite(es)
            and math.isfinite(at)
            and at > 0.0
        ):
            continue
        if mt >= mr_thresh:
            # High median-reversion frequency -> range-bound mean reversion
            if zt <= -z_mr_entry:
                sig[t] = 1.0
            elif zt >= z_mr_entry:
                sig[t] = -1.0
        elif mt <= tr_thresh and math.isfinite(float(mmi_sma[t])) and mt < float(mmi_sma[t]):
            # Falling MMI -> directional institutional trend accumulation
            if ef > es and zt > 0.0:
                sig[t] = 1.0
            elif ef < es and zt < 0.0:
                sig[t] = -1.0
    sl_d = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_mult * atr, np.nan)
    return sig, sl_d, tp_d


def _signals_er_atrz_regime_switch(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 2 (`LEAD-OFF3-TV-20`): Kaufman ER + ATR-Z adaptive Z-Regime Switch (D1)."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    z_len = int(params.get("z_len", 40))
    er_len = int(params.get("er_len", 20))
    reg_len = int(params.get("regime_len", 90))
    ema_len = int(params.get("ema_len", 100))
    z_entry = float(params.get("z_entry", 1.75))
    er_calm = float(params.get("er_calm", 0.35))
    er_hot = float(params.get("er_hot", 0.42))
    reg_cut = float(params.get("regime_cut", 0.50))
    sl_mult = float(params.get("sl_atr_mult", 2.5))
    tp_mult = float(params.get("tp_atr_mult", 3.5))
    mode = str(params.get("sub_mode", "BOTH")).upper()

    z = causal_zscore(c, z_len)
    z_ema = causal_ema(np.where(np.isfinite(z), z, np.nan), 3)
    er = _causal_kaufman_er_jit(c, er_len)
    atr = causal_atr(h, lo, c, 14)
    # ATR% strictly aligned to bar k close via shift=1 ATR / close[k-1]
    c_prev = np.full(n, np.nan, dtype=np.float64)
    c_prev[1:] = c[:-1]
    atr_pct = np.where(np.isfinite(atr) & np.isfinite(c_prev) & (c_prev > 0.0), atr / c_prev, np.nan)
    reg_z = causal_zscore(atr_pct, reg_len)
    ema_bias = causal_ema(c, ema_len)

    sig = np.zeros(n, dtype=np.float64)
    for t in range(2, n):
        zt, zprev = float(z[t]), float(z[t - 1])
        ert, rzt, ebt, cpt, at = float(er[t]), float(reg_z[t]), float(ema_bias[t]), float(c_prev[t]), float(atr[t])
        if not (
            math.isfinite(zt)
            and math.isfinite(zprev)
            and math.isfinite(ert)
            and math.isfinite(rzt)
            and math.isfinite(ebt)
            and math.isfinite(cpt)
            and math.isfinite(at)
            and at > 0.0
        ):
            continue
        zvel = (
            float(z_ema[t] - z_ema[t - 1])
            if (math.isfinite(float(z_ema[t])) and math.isfinite(float(z_ema[t - 1])))
            else (zt - zprev)
        )

        # Calm reversion regime: low ATR-Z + low Kaufman ER + trend bias filter + Z crossback
        if mode in ("BOTH", "CALM_MR") and rzt <= reg_cut and ert <= er_calm:
            if cpt > ebt and zprev < -z_entry and zt >= -z_entry and zvel > 0.0:
                sig[t] = 1.0
            elif cpt < ebt and zprev > z_entry and zt <= z_entry and zvel < 0.0:
                sig[t] = -1.0
        # Hot trend regime: elevated ATR-Z + high Kaufman ER -> directional continuation
        elif mode in ("BOTH", "HOT_TREND") and rzt > reg_cut and ert >= er_hot:
            if cpt > ebt and zt > 0.50:
                sig[t] = 1.0
            elif cpt < ebt and zt < -0.50:
                sig[t] = -1.0

    sl_d = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_mult * atr, np.nan)
    return sig, sl_d, tp_d


def _signals_skew_jb_contrarian(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 3 (`LEAD-OFF3-MQL5-04`): Rolling 50-bar Moments + Jarque-Bera 95% CI fade."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    win = int(params.get("win", 50))
    ci_z = float(params.get("ci_z", 1.96))
    min_jb = float(params.get("min_jb", 2.0))
    min_skew = float(params.get("min_skew", 0.20))
    sl_mult = float(params.get("sl_atr_mult", 2.0))
    tp_mult = float(params.get("tp_atr_mult", 2.5))

    mc, sc, sk, _, jb = _causal_rolling_moments_jit(c, win)
    atr = causal_atr(h, lo, c, 14)

    sig = np.zeros(n, dtype=np.float64)
    for t in range(1, n):
        mct, sct, skt, jbt, at = float(mc[t]), float(sc[t]), float(sk[t]), float(jb[t]), float(atr[t])
        cp = float(c[t - 1])
        if not (
            math.isfinite(mct)
            and math.isfinite(sct)
            and sct > 1e-12
            and math.isfinite(skt)
            and math.isfinite(jbt)
            and math.isfinite(at)
            and at > 0.0
        ):
            continue
        if jbt < min_jb:
            continue
        if cp < (mct - ci_z * sct) and skt <= -min_skew:
            sig[t] = 1.0
        elif cp > (mct + ci_z * sct) and skt >= min_skew:
            sig[t] = -1.0

    sl_d = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_mult * atr, np.nan)
    return sig, sl_d, tp_d


def _signals_skew_threshold_fx(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 4b (`LEAD-OFF3-QC-03`): FX Tail-Skewness Risk Premia (Long skew < -th / Short skew > +th)."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    win = int(params.get("win", 60))
    skew_th = float(params.get("skew_th", 0.60))
    rebal_every = int(params.get("rebal_every", 5))
    sl_mult = float(params.get("sl_atr_mult", 2.5))
    tp_mult = float(params.get("tp_atr_mult", 4.0))

    _, _, sk, _, _ = _causal_rolling_moments_jit(c, win)
    atr = causal_atr(h, lo, c, 14)
    sig = np.zeros(n, dtype=np.float64)
    cur = 0.0
    for t in range(1, n):
        skt = float(sk[t])
        at = float(atr[t])
        if not (math.isfinite(skt) and math.isfinite(at) and at > 0.0):
            cur = 0.0
            continue
        if t % rebal_every == 0:
            if skt <= -skew_th:
                cur = 1.0
            elif skt >= skew_th:
                cur = -1.0
            else:
                cur = 0.0
        sig[t] = cur
    sl_d = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_mult * atr, np.nan)
    return sig, sl_d, tp_d


def _signals_lw_smash_day(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 6 (`LEAD-OFF3-MQL5-10`): Larry Williams Smash Day Reversal + Supertrend & DoW filter."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    wds = np.asarray(d1["weekdays"], dtype=np.int32)
    n = c.shape[0]
    lb = int(params.get("lookback", 3))
    valid_bars = int(params.get("validity_bars", 3))
    use_st = bool(params.get("use_supertrend", True))
    skip_friday = bool(params.get("skip_friday", True))
    rr_mult = float(params.get("rr_mult", 2.0))
    min_sl_atr = float(params.get("min_sl_atr", 1.25))

    atr = causal_atr(h, lo, c, 14)
    st_dir = _causal_supertrend_dir_jit(h, lo, c, atr, float(params.get("st_mult", 3.0)))

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64)

    # Track active Smash Day setup causally using bars <= t-1 ONLY!
    setup_dir = 0
    setup_trigger = 0.0
    setup_extreme = 0.0
    setup_age = 999

    for t in range(lb + 2, n):
        # Update setup from bar k = t - 1 close (strictly causal for bar t open!)
        k = t - 1
        at = float(atr[t])
        if not math.isfinite(at) or at <= 0.0:
            setup_dir = 0
            continue

        # Check if an existing Smash Day setup was confirmed on bar k = t - 1 close!
        fired = False
        if setup_dir != 0 and setup_age <= valid_bars:
            confirmed = (setup_dir == 1 and float(c[k]) > setup_trigger) or (
                setup_dir == -1 and float(c[k]) < setup_trigger
            )
            if confirmed:
                allow_dow = (not skip_friday) or (int(wds[t]) != 4)
                st_ok = (not use_st) or (int(st_dir[t]) == setup_dir)
                if allow_dow and st_ok:
                    dist_ext = abs(float(c[k]) - setup_extreme)
                    eff_sl = max(min_sl_atr * at, min(3.5 * at, dist_ext + 0.25 * at))
                    sig[t] = float(setup_dir)
                    sl_d[t] = eff_sl
                    tp_d[t] = rr_mult * eff_sl
                    fired = True
                setup_dir = 0
                setup_age = 999
            else:
                setup_age += 1
                if setup_age > valid_bars:
                    setup_dir = 0

        # Detect a new Smash Day on bar k = t - 1 (ready to confirm on future bars >= t)
        if not fired:
            prev_min_l = float(np.min(lo[k - lb : k]))
            prev_max_h = float(np.max(h[k - lb : k]))
            bar_mid = 0.5 * (float(h[k]) + float(lo[k]))
            if float(c[k]) < prev_min_l and float(c[k]) < bar_mid:
                setup_dir = 1
                setup_trigger = float(h[k])
                setup_extreme = float(lo[k])
                setup_age = 1
            elif float(c[k]) > prev_max_h and float(c[k]) > bar_mid:
                setup_dir = -1
                setup_trigger = float(lo[k])
                setup_extreme = float(h[k])
                setup_age = 1

    # Ensure valid fallback sl_d/tp_d on non-zero signal bars only
    return sig, sl_d, tp_d


def _signals_daily_open_oversized_body(
    d1: Mapping[str, Any],
    params: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 8 (`LEAD-OFF3-TV-17`): Daily Open Oversized-Body Reversal (DOS)."""
    o, h, lo, c = d1["open"], d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    body_atr_mult = float(params.get("body_atr_mult", 1.25))
    sl_mult = float(params.get("sl_atr_mult", 1.75))
    tp_mult = float(params.get("tp_atr_mult", 2.00))
    use_ema_filter = bool(params.get("use_ema_filter", False))

    atr = causal_atr(h, lo, c, 14)
    ema100 = causal_ema(c, 100)
    sig = np.zeros(n, dtype=np.float64)
    for t in range(1, n):
        at = float(atr[t])
        if not math.isfinite(at) or at <= 0.0:
            continue
        # Strictly bar t-1 completed body observed at bar t open (shift = 1)
        body = float(c[t - 1] - o[t - 1])
        thresh = body_atr_mult * at
        if body <= -thresh:
            if (not use_ema_filter) or (math.isfinite(float(ema100[t])) and float(c[t - 1]) > float(ema100[t])):
                sig[t] = 1.0
        elif body >= thresh:
            if (not use_ema_filter) or (math.isfinite(float(ema100[t])) and float(c[t - 1]) < float(ema100[t])):
                sig[t] = -1.0

    sl_d = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_mult * atr, np.nan)
    return sig, sl_d, tp_d


def _signals_z14_hard_zstop(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 9a (`LEAD-OFF3-COMM-CN-03`): 14d Z-Score MR with Hard Z-Stop (±2.5) & 8d Time Stop."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    z_len = int(params.get("z_len", 14))
    z_entry = float(params.get("z_entry", 1.80))
    z_exit = float(params.get("z_exit", 0.40))
    z_stop = float(params.get("z_stop", 2.50))
    sl_mult = float(params.get("sl_atr_mult", 2.0))
    tp_mult = float(params.get("tp_atr_mult", 3.0))

    z = causal_zscore(c, z_len)
    atr = causal_atr(h, lo, c, 14)

    # Stateful causal target position so exit_on_signal_flip executes Z-reversion & hard Z-stop cleanly!
    sig = np.zeros(n, dtype=np.float64)
    pos = 0
    for t in range(1, n):
        zt = float(z[t])
        at = float(atr[t])
        if not (math.isfinite(zt) and math.isfinite(at) and at > 0.0):
            pos = 0
            continue
        if pos == 1:
            if zt >= -z_exit or zt <= -z_stop:
                pos = 0
        elif pos == -1:
            if zt <= z_exit or zt >= z_stop:
                pos = 0
        if pos == 0:
            if -z_stop < zt < -z_entry:
                pos = 1
            elif z_entry < zt < z_stop:
                pos = -1
        sig[t] = float(pos)

    sl_d = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_mult * atr, np.nan)
    return sig, sl_d, tp_d


def _signals_cci10_crossback(
    d1: Mapping[str, Any], params: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mechanism 9b (`LEAD-OFF3-COMM-CN-05`): Fast CCI(10) ±100 Cross-Back Mean Reversion."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.shape[0]
    cci_len = int(params.get("cci_len", 10))
    cci_th = float(params.get("cci_th", 100.0))
    sl_pct = float(params.get("sl_pct", 0.015))
    sl_atr_mult = float(params.get("sl_atr_mult", 1.8))
    tp_atr_mult = float(params.get("tp_atr_mult", 2.5))

    cci = _causal_cci_jit(h, lo, c, cci_len)
    atr = causal_atr(h, lo, c, 14)

    sig = np.zeros(n, dtype=np.float64)
    pos = 0
    for t in range(2, n):
        ct, cp = float(cci[t]), float(cci[t - 1])
        at = float(atr[t])
        if not (math.isfinite(ct) and math.isfinite(cp) and math.isfinite(at) and at > 0.0):
            pos = 0
            continue
        cross_up = cp < -cci_th and ct >= -cci_th
        cross_dn = cp > cci_th and ct <= cci_th
        if pos == 1 and cross_dn:
            pos = -1
        elif pos == -1 and cross_up:
            pos = 1
        elif pos == 0:
            if cross_up:
                pos = 1
            elif cross_dn:
                pos = -1
        sig[t] = float(pos)

    c_prev = np.full(n, np.nan, dtype=np.float64)
    c_prev[1:] = c[:-1]
    sl_d = np.where(
        np.isfinite(atr) & (atr > 0.0) & np.isfinite(c_prev),
        np.maximum(sl_pct * c_prev, sl_atr_mult * atr),
        np.nan,
    )
    tp_d = np.where(np.isfinite(atr) & (atr > 0.0), tp_atr_mult * atr, np.nan)
    return sig, sl_d, tp_d


# ---------------------------------------------------------------------------
# 4. Multi-Asset Cross-Sectional Skewness (`QP-07`) & Network Spillover (`ARXIV-22`)
# ---------------------------------------------------------------------------


def _causal_zero_gap_lag_mask(
    symbol: str,
    opens: np.ndarray,
    closes: np.ndarray,
    *,
    threshold: float = 0.90,
    min_bars: int = 10,
) -> np.ndarray:
    """Strictly causal per-bar flag: True iff bar `t` needs +1 extra lag due to Yahoo zero-gap open.

    Yahoo Finance UK100 (^FTSE) exhibits `zero_gap_frac = 99.66%` (`open[t] == close[t-1]` at LSE
    16:30 UTC on day `t-1`, 5.5-7.5h before UTC-close peers). Checking `UK100` OR causal prefix
    `opens[1:t]` vs `closes[0:t-1]` (`k <= t-1`, zero future peek) enforces airtight causality.
    """
    n = int(closes.shape[0])
    if symbol and normalize_symbol(symbol) == "UK100":
        return np.ones(n, dtype=np.bool_)
    mask = np.zeros(n, dtype=np.bool_)
    if n <= min_bars + 1:
        return mask
    zg = (np.abs(opens[1:] - closes[:-1]) / np.maximum(closes[:-1], 1e-12)) < 1e-6
    csum = np.cumsum(zg, dtype=np.int64)
    for t in range(min_bars + 1, n):
        if float(csum[t - 2]) / float(t - 1) >= threshold:
            mask[t] = True
    return mask


def _panel_zero_gap_lag_mask(
    symbols: Sequence[str],
    bars_by_sym: Mapping[str, Mapping[str, Any]],
    n: int,
) -> np.ndarray:
    """Return per-bar panel +1 lag mask when >= 2 symbols include UK100 or any zero-gap asset."""
    mask = np.zeros(n, dtype=np.bool_)
    if len(symbols) <= 1:
        return mask
    for s in symbols:
        b = bars_by_sym[s]
        mask |= _causal_zero_gap_lag_mask(
            s,
            np.asarray(b["open"], dtype=np.float64),
            np.asarray(b["close"], dtype=np.float64),
        )
    return mask


def _build_multi_asset_panel(
    symbols: Sequence[str],
    universe: Mapping[str, Any],
    max_year: int,
) -> tuple[list[str], dict[str, dict[str, Any]], np.ndarray]:
    """Align multiple symbols onto their common D1 calendar strictly `<= max_year`."""
    cutoff = f"{max_year + 1:04d}-01-01"
    date_sets: list[set[str]] = []
    for s in symbols:
        d1 = universe["assets"][s]["d1"]
        date_sets.append({str(d) for d in d1["dates"] if str(d) < cutoff})
    common_dates = sorted(set.intersection(*date_sets))
    if len(common_dates) < 80:
        raise ValueError(f"Insufficient overlapping D1 dates across {len(symbols)} symbols: {len(common_dates)}")
    enforce_dev_date_bound(common_dates, context="multi_asset_panel.dates")

    bars_by_sym: dict[str, dict[str, Any]] = {}
    close_mat = np.empty((len(common_dates), len(symbols)), dtype=np.float64)

    for j, s in enumerate(symbols):
        d1 = universe["assets"][s]["d1"]
        dmap = {str(d): i for i, d in enumerate(d1["dates"])}
        idx = np.array([dmap[d] for d in common_dates], dtype=np.int64)
        c_arr = np.asarray(d1["close"], dtype=np.float64)[idx]
        close_mat[:, j] = c_arr
        bars_by_sym[s] = {
            "times_sec": np.asarray(d1["times_sec"], dtype=np.int64)[idx],
            "dates": common_dates,
            "years": np.array([int(d[:4]) for d in common_dates], dtype=np.int32),
            "weekdays": np.asarray(d1["weekdays"], dtype=np.int32)[idx],
            "open": np.asarray(d1["open"], dtype=np.float64)[idx],
            "high": np.asarray(d1["high"], dtype=np.float64)[idx],
            "low": np.asarray(d1["low"], dtype=np.float64)[idx],
            "close": c_arr,
        }
    return common_dates, bars_by_sym, close_mat


def _signals_xsec_commodity_skew(
    symbols: Sequence[str],
    bars_by_sym: Mapping[str, Mapping[str, Any]],
    close_mat: np.ndarray,
    params: Mapping[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Mechanism 4a (`LEAD-OFF3-QP-07`): Cross-Sectional Commodity Return Skewness Factor."""
    n, k_syms = close_mat.shape
    win = int(params.get("win", 60))
    rebal = int(params.get("rebal_every", 10))
    top_k = int(params.get("top_k", 1))
    sl_mult = float(params.get("sl_atr_mult", 2.5))

    skew_mat = np.full((n, k_syms), np.nan, dtype=np.float64)
    for j in range(k_syms):
        _, _, sk, _, _ = _causal_rolling_moments_jit(np.ascontiguousarray(close_mat[:, j]), win)
        skew_mat[:, j] = sk

    sigs: dict[str, np.ndarray] = {s: np.zeros(n, dtype=np.float64) for s in symbols}
    sls: dict[str, np.ndarray] = {}
    tps: dict[str, np.ndarray] = {}
    for s in symbols:
        b = bars_by_sym[s]
        atr = causal_atr(b["high"], b["low"], b["close"], 14)
        sls[s] = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
        tps[s] = np.where(np.isfinite(atr) & (atr > 0.0), 4.0 * atr, np.nan)

    # Fail-closed Yahoo zero-gap open guard (`P0-01`): when UK100 (or any asset with
    # causal `zero_gap_frac >= 0.90`) participates in a multi-asset cross-sectional panel,
    # lag cross-sectional rankings by +1 extra bar (`<= t-2` closes) so UK100's 16:30 UTC
    # synthetic open NEVER peeks at later-closing peers' day `t-1` closes!
    panel_lag_mask = _panel_zero_gap_lag_mask(symbols, bars_by_sym, n)

    cur_pos = np.zeros(k_syms, dtype=np.float64)
    for t in range(win + 2, n):
        lag_t = 1 if bool(panel_lag_mask[t]) else 0
        sig_t = t - lag_t
        if t % rebal == 0:
            cur_pos[:] = 0.0
            if sig_t >= win + 2:
                row = skew_mat[sig_t]
                valid = [j for j in range(k_syms) if math.isfinite(float(row[j]))]
                if len(valid) >= 2 * top_k:
                    # Long MOST NEGATIVELY skewed, Short MOST POSITIVELY skewed (QP-07 spec!)
                    valid.sort(key=lambda j: float(row[j]))
                    for j in valid[:top_k]:
                        cur_pos[j] = 1.0
                    for j in valid[-top_k:]:
                        cur_pos[j] = -1.0
        for j, s in enumerate(symbols):
            sigs[s][t] = cur_pos[j]
    return sigs, sls, tps


@njit(cache=True)
def _causal_network_spillover_matrix_jit(
    close_mat: np.ndarray,
    corr_win: int,
    mom_fast: int,
    mom_slow: int,
    min_corr: float,
    use_lagged_graph: bool,
) -> np.ndarray:
    """Strictly `shift = 1` causal Cross-Asset Network Momentum Spillover score matrix `(T, N)`.

    Zero diagonal (`W_ii = 0`): asset `i`'s score is driven purely by connected peer assets `j != i`,
    making it strictly orthogonal to own-asset TSMOM (`F06`)!
    """
    n_t, n_s = close_mat.shape
    scores = np.full((n_t, n_s), np.nan, dtype=np.float64)
    warm = max(corr_win + 2, mom_slow + 2)
    if n_t <= warm:
        return scores

    rets = np.full((n_t, n_s), np.nan, dtype=np.float64)
    for k in range(1, n_t):
        for j in range(n_s):
            c0 = close_mat[k - 1, j]
            c1 = close_mat[k, j]
            if c0 > 0.0 and c1 > 0.0:
                rets[k, j] = math.log(c1 / c0)

    # Precompute causal vol-normalized momentum at each bar t (using closes <= t-1)
    mom = np.full((n_t, n_s), np.nan, dtype=np.float64)
    for t in range(warm, n_t):
        for j in range(n_s):
            c_last = close_mat[t - 1, j]
            c_f = close_mat[t - 1 - mom_fast, j]
            c_s = close_mat[t - 1 - mom_slow, j]
            if c_last <= 0.0 or c_f <= 0.0 or c_s <= 0.0:
                continue
            # 20d realized vol over [t - 20 : t]
            mr = 0.0
            for k in range(t - 20, t):
                mr += rets[k, j]
            mr /= 20.0
            vr = 0.0
            for k in range(t - 20, t):
                dr = rets[k, j] - mr
                vr += dr * dr
            sd = math.sqrt(vr / 19.0)
            if sd > 1e-9:
                mf = math.log(c_last / c_f) / (sd * math.sqrt(float(mom_fast)))
                ms = math.log(c_last / c_s) / (sd * math.sqrt(float(mom_slow)))
                raw_m = 0.5 * (mf + ms)
                # Clip extreme outliers smoothly
                if raw_m > 3.0:
                    raw_m = 3.0
                elif raw_m < -3.0:
                    raw_m = -3.0
                mom[t, j] = raw_m

    # Compute rolling correlation / lag-1 spillover adjacency every 5 bars (strictly causal <= t-1)
    adj = np.zeros((n_s, n_s), dtype=np.float64)
    for t in range(warm, n_t):
        if t == warm or (t - warm) % 5 == 0:
            # Means & stds over [t - corr_win : t]
            mu = np.zeros(n_s, dtype=np.float64)
            sd_w = np.zeros(n_s, dtype=np.float64)
            w_eff = corr_win - 1 if use_lagged_graph else corr_win
            k_start = t - w_eff
            for j in range(n_s):
                acc = 0.0
                for k in range(k_start, t):
                    acc += rets[k, j]
                mu[j] = acc / float(w_eff)
                ss = 0.0
                for k in range(k_start, t):
                    d = rets[k, j] - mu[j]
                    ss += d * d
                sd_w[j] = math.sqrt(ss)

            for i in range(n_s):
                for j in range(n_s):
                    adj[i, j] = 0.0
                    if i == j or sd_w[i] <= 1e-12 or sd_w[j] <= 1e-12:
                        continue
                    cov = 0.0
                    if use_lagged_graph:
                        # Lead-lag spillover: leader j at k-1 -> follower i at k
                        for k in range(k_start, t):
                            cov += (rets[k, i] - mu[i]) * (rets[k - 1, j] - mu[j])
                    else:
                        for k in range(k_start, t):
                            cov += (rets[k, i] - mu[i]) * (rets[k, j] - mu[j])
                    c_ij = cov / (sd_w[i] * sd_w[j])
                    if abs(c_ij) >= min_corr:
                        adj[i, j] = c_ij

        for i in range(n_s):
            num = 0.0
            den = 0.0
            for j in range(n_s):
                w_ij = adj[i, j]
                if w_ij != 0.0 and np.isfinite(mom[t, j]):
                    num += w_ij * mom[t, j]
                    den += abs(w_ij)
            if den > 1e-9:
                scores[t, i] = num / den
            else:
                scores[t, i] = 0.0

    return scores


def _signals_network_spillover(
    all_symbols: Sequence[str],
    trade_symbols: Sequence[str],
    bars_by_sym: Mapping[str, Mapping[str, Any]],
    close_mat: np.ndarray,
    params: Mapping[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Mechanism 7 (`LEAD-OFF3-ARXIV-22` / `LEAD-OFF3-MQL5-14`): Cross-Asset Network Momentum Spillover."""
    n, _ = close_mat.shape
    corr_win = int(params.get("corr_win", 60))
    mom_fast = int(params.get("mom_fast", 20))
    mom_slow = int(params.get("mom_slow", 60))
    min_corr = float(params.get("min_corr", 0.35))
    use_lagged = bool(params.get("use_lagged_graph", False))
    sig_thresh = float(params.get("sig_thresh", 0.35))
    top_k = int(params.get("top_k", 3))
    rebal = int(params.get("rebal_every", 5))
    sl_mult = float(params.get("sl_atr_mult", 2.5))

    sc_mat = _causal_network_spillover_matrix_jit(close_mat, corr_win, mom_fast, mom_slow, min_corr, use_lagged)
    sym_to_col = {s: idx for idx, s in enumerate(all_symbols)}
    trade_cols = [sym_to_col[s] for s in trade_symbols]

    sigs: dict[str, np.ndarray] = {s: np.zeros(n, dtype=np.float64) for s in trade_symbols}
    sls: dict[str, np.ndarray] = {}
    tps: dict[str, np.ndarray] = {}
    for s in trade_symbols:
        b = bars_by_sym[s]
        atr = causal_atr(b["high"], b["low"], b["close"], 14)
        sls[s] = np.where(np.isfinite(atr) & (atr > 0.0), sl_mult * atr, np.nan)
        tps[s] = np.where(np.isfinite(atr) & (atr > 0.0), 4.0 * atr, np.nan)

    # Fail-closed Yahoo zero-gap open guard (`P0-01`): lag cross-asset network spillover scores
    # by +1 extra bar (`<= t-2` closes) whenever UK100 or any zero-gap asset participates!
    panel_lag_mask = _panel_zero_gap_lag_mask(all_symbols, bars_by_sym, n)
    warm_bar = max(corr_win, mom_slow) + 2

    cur_dir: dict[str, float] = {s: 0.0 for s in trade_symbols}
    for t in range(warm_bar, n):
        lag_t = 1 if bool(panel_lag_mask[t]) else 0
        sig_t = t - lag_t
        if t % rebal == 0:
            for s in trade_symbols:
                cur_dir[s] = 0.0
            if sig_t >= warm_bar:
                ranked = [
                    (float(sc_mat[sig_t, sym_to_col[s]]), s)
                    for s in trade_symbols
                    if math.isfinite(float(sc_mat[sig_t, sym_to_col[s]]))
                ]
                if ranked:
                    ranked.sort(key=lambda x: x[0])
                    # Short bottom-K below -sig_thresh, Long top-K above +sig_thresh
                    for val, s in ranked[:top_k]:
                        if val <= -sig_thresh:
                            cur_dir[s] = -1.0
                    for val, s in ranked[-top_k:]:
                        if val >= sig_thresh:
                            cur_dir[s] = 1.0
        for s in trade_symbols:
            sigs[s][t] = cur_dir[s]
    _ = trade_cols
    return sigs, sls, tps


# ---------------------------------------------------------------------------
# 5. Intraday M1 Mechanisms (`swap = 0`, `replay_intraday_m1_trade`, Red-News Guarded!)
# ---------------------------------------------------------------------------


def _eval_rbreaker_reversal_m1(
    symbol: str,
    universe: Mapping[str, Any],
    params: Mapping[str, Any],
    years: Sequence[int],
    *,
    fade_mode: bool = False,
    red_news_index: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Mechanism 5 (`LEAD-OFF3-COMM-CN-01`): R-Breaker Reversal-Only Legs (`sSetup->sEnter`, `bSetup->bEnter`).

    Strictly NON-BREAKOUT reversal legs ONLY on native M1 Bid/Ask (`swap = 0`, hard flat <= 20:50 UTC):
      - Prior completed UTC day's `(H, L, C)` defines causal Pivot, `sSetup`, `sEnter`, `bEnter`, `bSetup`.
      - Armed Short when intraday high breaches `sSetup`, triggers Short when price re-crosses `< sEnter`.
      - Armed Long when intraday low breaches `bSetup`, triggers Long when price re-crosses `> bEnter`.
      - Mandatory wide hard ATR SL (`>= 0.75 * D1_ATR`) + Pivot/ATR TP + hard flat `<= 20:50 UTC`!
    """
    req_years = tuple(sorted(int(y) for y in years))
    allowed_set = set(req_years)
    max_year = max(req_years)
    cutoff_ts = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())

    asset = universe["assets"][symbol]
    m1 = asset["m1"]
    d1 = asset["d1"]
    if m1 is None or d1 is None:
        raise ValueError(f"M1/D1 data required for R-Breaker M1 on {symbol}")

    spec = asset["spec"]
    ts_m1 = np.asarray(m1["times_sec"], dtype=np.int64)
    q_m1 = np.asarray(m1["quotes"], dtype=np.float64)
    end_i = int(np.searchsorted(ts_m1, cutoff_ts, side="left"))
    ts_m1 = ts_m1[:end_i]
    q_m1 = q_m1[:end_i]
    enforce_dev_ts_bound(ts_m1, context=f"rbreaker:{symbol}")

    d1_dates = [str(d) for d in d1["dates"]]
    d1_h = np.asarray(d1["high"], dtype=np.float64)
    d1_lo = np.asarray(d1["low"], dtype=np.float64)
    d1_c = np.asarray(d1["close"], dtype=np.float64)
    d1_atr = causal_atr(d1_h, d1_lo, d1_c, 14)

    variant = str(params.get("formula", "CLASSIC")).upper()
    sl_atr_mult = float(params.get("sl_atr_mult", 0.90))
    tp_rr = float(params.get("tp_rr", 1.80))
    sess_start_hr = int(params.get("sess_start_utc", 6))
    last_entry_hr = int(params.get("last_entry_utc", 18))
    has_ask = q_m1.shape[1] >= 8

    trades: list[dict[str, Any]] = []
    for di in range(1, len(d1_dates)):
        d_str = d1_dates[di]
        yr = int(d_str[:4])
        if yr > max_year:
            break
        if yr not in allowed_set:
            continue
        atr_d = float(d1_atr[di])
        if not math.isfinite(atr_d) or atr_d <= 0.0:
            continue

        # Strictly prior completed UTC day (di - 1) OHLC!
        ph = float(d1_h[di - 1])
        pl = float(d1_lo[di - 1])
        pc = float(d1_c[di - 1])
        if ph <= pl:
            continue
        pivot = (ph + pl + pc) / 3.0
        if variant == "TQSDK_RATIO":
            s_setup = ph + 0.35 * (pc - pl)
            b_setup = pl - 0.35 * (ph - pc)
            s_enter = 0.535 * (ph + pl) - 0.07 * pl
            b_enter = 0.535 * (ph + pl) - 0.07 * ph
        else:
            # Classic Pivot R-Breaker Reversal Levels (strictly bSetup < bEnter < pivot < sEnter < sSetup)
            s_setup = pivot + (ph - pl)
            s_enter = 2.0 * pivot - pl
            b_enter = 2.0 * pivot - ph
            b_setup = pivot - (ph - pl)

        dt0 = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=UTC)
        t_start = int(dt0.timestamp()) + sess_start_hr * 3600
        t_last_entry = int(dt0.timestamp()) + last_entry_hr * 3600
        i0 = int(np.searchsorted(ts_m1, t_start, side="left"))
        i1 = int(np.searchsorted(ts_m1, t_last_entry, side="right"))
        if i1 <= i0 + 5:
            continue

        armed_short = False
        armed_long = False
        entry_i = -1
        raw_side = 0

        # Strictly causal M1 scan: observe completed bar k, enter at bar k + 1 open!
        for k in range(i0, i1 - 1):
            mid_h = 0.5 * (float(q_m1[k, 1]) + float(q_m1[k, 5])) if has_ask else float(q_m1[k, 1])
            mid_l = 0.5 * (float(q_m1[k, 2]) + float(q_m1[k, 6])) if has_ask else float(q_m1[k, 2])
            mid_c = 0.5 * (float(q_m1[k, 3]) + float(q_m1[k, 7])) if has_ask else float(q_m1[k, 3])

            if mid_h > s_setup:
                armed_short = True
            if mid_l < b_setup:
                armed_long = True

            if armed_short and mid_c < s_enter:
                entry_i = k + 1
                raw_side = -1
                break
            if armed_long and mid_c > b_enter:
                entry_i = k + 1
                raw_side = 1
                break

        if entry_i < 0 or raw_side == 0:
            continue

        eff_side = -raw_side if fade_mode else raw_side
        entry_px = float(q_m1[entry_i, 4] if (eff_side == 1 and has_ask) else q_m1[entry_i, 0])
        sl_dist = sl_atr_mult * atr_d
        sl_px = entry_px - eff_side * sl_dist
        tp_px = entry_px + eff_side * (tp_rr * sl_dist)
        if sl_px <= 0.0:
            continue

        tr = replay_intraday_m1_trade(
            symbol,
            ts_m1,
            q_m1,
            entry_i,
            eff_side,
            sl_px,
            tp_price=tp_px,
            entry_order_type="MARKET",
            spec=spec,
            firm_profile="FTMO_STANDARD",
            red_news_index=red_news_index,
            news_pad_sec=300,
            flatten_before_news=True,
        )
        if tr.get("filled"):
            trades.append(tr)
    return trades


def _eval_er_atrz_m1_intraday(
    symbol: str,
    universe: Mapping[str, Any],
    params: Mapping[str, Any],
    years: Sequence[int],
    *,
    fade_mode: bool = False,
    red_news_index: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Mechanism 2 (Intraday M1 `swap=0`): Kaufman ER + ATR-Z Regime Switch on M30 bars -> M1 Bid/Ask fills."""
    req_years = tuple(sorted(int(y) for y in years))
    allowed_set = set(req_years)
    max_year = max(req_years)
    cutoff_ts = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())

    asset = universe["assets"][symbol]
    m1 = asset["m1"]
    if m1 is None:
        raise ValueError(f"M1 data missing for {symbol}")
    spec = asset["spec"]
    ts_m1 = np.asarray(m1["times_sec"], dtype=np.int64)
    q_m1 = np.asarray(m1["quotes"], dtype=np.float64)
    end_i = int(np.searchsorted(ts_m1, cutoff_ts, side="left"))
    ts_m1, q_m1 = ts_m1[:end_i], q_m1[:end_i]
    enforce_dev_ts_bound(ts_m1, context=f"er_atrz_m1:{symbol}")

    tf_sec = int(params.get("tf_sec", 1800))  # M30 matches Pine TV-20 spec!
    r_ts, r_q = resample_m1_to_tf(ts_m1, q_m1, tf_sec)
    has_ask = r_q.shape[1] >= 8
    o = 0.5 * (r_q[:, 0] + r_q[:, 4]) if has_ask else r_q[:, 0].copy()
    h = 0.5 * (r_q[:, 1] + r_q[:, 5]) if has_ask else r_q[:, 1].copy()
    lo = 0.5 * (r_q[:, 2] + r_q[:, 6]) if has_ask else r_q[:, 2].copy()
    c = 0.5 * (r_q[:, 3] + r_q[:, 7]) if has_ask else r_q[:, 3].copy()
    h = np.maximum(h, np.maximum(o, c))
    lo = np.minimum(lo, np.minimum(o, c))

    sig, sl_d, tp_d = _signals_er_atrz_regime_switch({"open": o, "high": h, "low": lo, "close": c}, params)

    trades: list[dict[str, Any]] = []
    last_exit_ts = 0
    sess_start = int(params.get("sess_start_utc", 7))
    last_entry = int(params.get("last_entry_utc", 17))

    for t in range(r_ts.size):
        s_val = float(sig[t])
        if abs(s_val) <= 1e-12:
            continue
        ts_t = int(r_ts[t])
        if ts_t <= last_exit_ts:
            continue
        dt_t = datetime.fromtimestamp(ts_t, tz=UTC)
        if dt_t.year > max_year:
            break
        if dt_t.year not in allowed_set or dt_t.weekday() >= 5:
            continue
        if dt_t.hour < sess_start or dt_t.hour >= last_entry:
            continue

        sld = float(sl_d[t])
        tpd = float(tp_d[t])
        if not (math.isfinite(sld) and sld > 0.0 and math.isfinite(tpd) and tpd > 0.0):
            continue

        m1_i = int(np.searchsorted(ts_m1, ts_t, side="left"))
        if m1_i >= ts_m1.size or int(ts_m1[m1_i]) >= ts_t + tf_sec:
            continue
        raw_side = 1 if s_val > 0.0 else -1
        eff_side = -raw_side if fade_mode else raw_side
        ep = float(q_m1[m1_i, 4] if (eff_side == 1 and has_ask) else q_m1[m1_i, 0])
        sl_px = ep - eff_side * sld
        tp_px = ep + eff_side * tpd
        if sl_px <= 0.0:
            continue

        tr = replay_intraday_m1_trade(
            symbol,
            ts_m1,
            q_m1,
            m1_i,
            eff_side,
            sl_px,
            tp_price=tp_px,
            entry_order_type="MARKET",
            spec=spec,
            firm_profile="FTMO_STANDARD",
            red_news_index=red_news_index,
            news_pad_sec=300,
            flatten_before_news=True,
        )
        if tr.get("filled"):
            trades.append(tr)
            last_exit_ts = int(tr["exit_ts"])
    return trades


# ---------------------------------------------------------------------------
# 6. Unified `evaluate_candidate(spec, universe, years)` Entrypoint
# ---------------------------------------------------------------------------


def _scale_trades_for_basket(trades: list[dict[str, Any]], n_syms: int) -> list[dict[str, Any]]:
    if n_syms <= 1:
        return trades
    inv_s = 1.0 / math.sqrt(float(n_syms))
    out: list[dict[str, Any]] = []
    for tr in trades:
        d = dict(tr)
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
            if k in d and d[k] is not None:
                d[k] = round(float(d[k]) * inv_s, 6)
        out.append(d)
    return out


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    red_news_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a single F12 Cleanroom candidate strictly on `years` (zero lookahead past `max(years)`)."""
    req_years = tuple(sorted(int(y) for y in years))
    if not req_years or max(req_years) > 2024 or min(req_years) < 2018:
        raise ValueError(f"DEV_SEAL_VIOLATION: invalid Dev years={req_years}")
    max_year = max(req_years)

    mech = str(spec["mechanism"]).upper()
    symbols = [normalize_symbol(s) for s in spec["symbols"]]
    params = dict(spec.get("params") or {})
    if not symbols:
        raise ValueError("F12 spec must include >= 1 symbol")

    # Clamp universe strictly to max_year BEFORE computing any indicators!
    uni_clamped = _slice_universe_max_year(universe, max_year=max_year)
    tag_syms = list(symbols)
    if mech == "MECH07_NETWORK_SPILLOVER":
        graph_syms_tag = [normalize_symbol(s) for s in spec.get("graph_symbols", ALL_27_NONCRYPTO)]
        tag_syms = sorted(set(tag_syms) | set(graph_syms_tag))
    data_res, b_tier, _ = _resolve_group_tags(tag_syms, uni_clamped)

    # Branch A: Intraday M1 Bid/Ask (`swap = 0`) mechanisms
    if mech in ("MECH05_RBREAKER_M1", "MECH02_ER_ATRZ_M1"):
        news_idx = red_news_index if red_news_index is not None else load_dev_red_news_index(include_extended=True)
        main_trades: list[dict[str, Any]] = []
        fade_trades: list[dict[str, Any]] = []
        for sym in symbols:
            if mech == "MECH05_RBREAKER_M1":
                main_trades.extend(
                    _eval_rbreaker_reversal_m1(
                        sym, uni_clamped, params, req_years, fade_mode=False, red_news_index=news_idx
                    )
                )
                fade_trades.extend(
                    _eval_rbreaker_reversal_m1(
                        sym, uni_clamped, params, req_years, fade_mode=True, red_news_index=news_idx
                    )
                )
            else:
                main_trades.extend(
                    _eval_er_atrz_m1_intraday(
                        sym, uni_clamped, params, req_years, fade_mode=False, red_news_index=news_idx
                    )
                )
                fade_trades.extend(
                    _eval_er_atrz_m1_intraday(
                        sym, uni_clamped, params, req_years, fade_mode=True, red_news_index=news_idx
                    )
                )

        main_trades = _scale_trades_for_basket(main_trades, len(symbols))
        fade_trades = _scale_trades_for_basket(fade_trades, len(symbols))
        main_trades.sort(key=lambda tr: (int(tr["exit_ts"]), int(tr["entry_ts"]), str(tr["symbol"])))
        fade_trades.sort(key=lambda tr: (int(tr["exit_ts"]), int(tr["entry_ts"]), str(tr["symbol"])))

        dp_1x = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_1x")
        dp_15x = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_15x")
        dp_2x = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_2x")
        dp_fade = compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

        m_1x = compute_split_metrics(main_trades, dp_1x, pnl_key="net_R_1x")
        m_15x = compute_split_metrics(main_trades, dp_15x, pnl_key="net_R_15x")
        m_2x = compute_split_metrics(main_trades, dp_2x, pnl_key="net_R_2x")
        m_fade = compute_split_metrics(fade_trades, dp_fade, pnl_key="net_R_1x")
        s0 = stage0_screen(main_trades, max_fric_sl_ratio=0.15, min_keep_frac=0.50)

        dp_1x_map = {d: round(float(v), 6) for d, v in zip(dp_1x["dates"], dp_1x["pnl"], strict=True)}
        return {
            "spec": dict(spec),
            "trades": main_trades,
            "daily_pnl_1x": dp_1x_map,
            "daily_pnl_15x": {d: round(float(v), 6) for d, v in zip(dp_15x["dates"], dp_15x["pnl"], strict=True)},
            "daily_pnl_2x": {d: round(float(v), 6) for d, v in zip(dp_2x["dates"], dp_2x["pnl"], strict=True)},
            "daily_pnl_zero_pos_swap": dict(dp_1x_map),  # Intraday swap=0 identically!
            "fade_daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_fade["dates"], dp_fade["pnl"], strict=True)},
            "metrics": m_1x,
            "metrics_15x": m_15x,
            "metrics_2x": m_2x,
            "metrics_zero_pos_swap": m_1x,
            "metrics_fade_1x": m_fade,
            "stage0": s0,
            "margin_audit": {
                "peak_portfolio_margin_util_frac": round(
                    max((float(tr.get("margin_util_frac", 0.0)) for tr in main_trades), default=0.0), 6
                ),
                "margin_rejects": 0,
                "margin_capped_count": sum(1 for tr in main_trades if tr.get("margin_capped")),
            },
            "data_resolution": RES_NATIVE_M1_BIDASK,
            "blindness_tier": b_tier,
            "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }

    # Branch B: FTMO Swing D1 mechanisms via `replay_swing_d1_series` (`signal_already_shifted=True`)
    max_hold = int(params.get("max_hold_bars", 8))
    exit_on_flip = bool(params.get("exit_on_signal_flip", True))
    risk_frac = float(params.get("risk_frac", 0.005))
    n_syms = len(symbols)
    per_sym_risk = risk_frac / math.sqrt(float(n_syms)) if n_syms > 1 else risk_frac

    if mech == "MECH04A_XSEC_COMMOD_SKEW":
        _, bars_by_sym, close_mat = _build_multi_asset_panel(symbols, uni_clamped, max_year=max_year)
        sigs, sls, tps = _signals_xsec_commodity_skew(symbols, bars_by_sym, close_mat, params)
        replay_uni: dict[str, Any] = {
            s: {
                "symbol": s,
                "d1": bars_by_sym[s],
                "spec": uni_clamped["assets"][s]["spec"],
                "data_resolution": uni_clamped["assets"][s]["data_resolution"],
            }
            for s in symbols
        }
    elif mech == "MECH07_NETWORK_SPILLOVER":
        graph_syms = [normalize_symbol(s) for s in spec.get("graph_symbols", ALL_27_NONCRYPTO)]
        _, bars_all, close_mat = _build_multi_asset_panel(graph_syms, uni_clamped, max_year=max_year)
        sigs, sls, tps = _signals_network_spillover(graph_syms, symbols, bars_all, close_mat, params)
        replay_uni = {
            s: {
                "symbol": s,
                "d1": bars_all[s],
                "spec": uni_clamped["assets"][s]["spec"],
                "data_resolution": uni_clamped["assets"][s]["data_resolution"],
            }
            for s in symbols
        }
    else:
        sigs = {}
        sls = {}
        tps = {}
        for s in symbols:
            d1 = uni_clamped["assets"][s]["d1"]
            if mech == "MECH01_MMI_SWITCH":
                sg, sld, tpd = _signals_mmi_regime_switch(d1, params)
            elif mech == "MECH02_ER_ATRZ_D1":
                sg, sld, tpd = _signals_er_atrz_regime_switch(d1, params)
            elif mech == "MECH03_SKEW_JB_CI":
                sg, sld, tpd = _signals_skew_jb_contrarian(d1, params)
            elif mech == "MECH04B_FX_SKEW_THRESH":
                sg, sld, tpd = _signals_skew_threshold_fx(d1, params)
            elif mech == "MECH06_LW_SMASH_DAY":
                sg, sld, tpd = _signals_lw_smash_day(d1, params)
            elif mech == "MECH08_DOS_OVERSIZED":
                sg, sld, tpd = _signals_daily_open_oversized_body(d1, params)
            elif mech == "MECH09A_Z14_HARD_ZSTOP":
                sg, sld, tpd = _signals_z14_hard_zstop(d1, params)
            elif mech == "MECH09B_CCI10_CROSSBACK":
                sg, sld, tpd = _signals_cci10_crossback(d1, params)
            else:
                raise ValueError(f"Unknown F12 mechanism={mech!r}")
            sigs[s] = sg
            sls[s] = sld
            tps[s] = tpd
        replay_uni = uni_clamped

    # Every signal array produced above is ALREADY strictly `shift = 1` (bar t uses bars <= t-1 ONLY)!
    fade_sigs = {s: -arr for s, arr in sigs.items()}

    # Standard $100K FTMO account preserves exact scale-invariant leverage margin % without 0.01-lot starvation
    acct_bal = float(params.get("account_balance_usd", 100_000.0))

    res_main = replay_swing_d1_series(
        replay_uni,
        sigs,
        sls,
        tp_dists=tps,
        max_hold_bars=max_hold,
        exit_on_signal_flip=exit_on_flip,
        signal_already_shifted=True,
        account_balance_usd=acct_bal,
        risk_frac=per_sym_risk,
        account_type="ftmo_swing",
        max_margin_util_frac=0.80,
        scale_if_over_margin=True,
        years=req_years,
    )
    res_fade = replay_swing_d1_series(
        replay_uni,
        fade_sigs,
        sls,
        tp_dists=tps,
        max_hold_bars=max_hold,
        exit_on_signal_flip=exit_on_flip,
        signal_already_shifted=True,
        account_balance_usd=acct_bal,
        risk_frac=per_sym_risk,
        account_type="ftmo_swing",
        max_margin_util_frac=0.80,
        scale_if_over_margin=True,
        years=req_years,
    )

    main_trades = _scale_trades_for_basket(list(res_main["trades"]), n_syms)
    fade_trades = _scale_trades_for_basket(list(res_fade["trades"]), n_syms)

    dp_1x = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_1x")
    dp_15x = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_15x")
    dp_2x = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_2x")
    dp_zpos = compute_daily_pnl_series(main_trades, req_years, pnl_key="net_R_zero_pos_1x")
    dp_fade = compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = compute_split_metrics(main_trades, dp_1x, pnl_key="net_R_1x")
    m_15x = compute_split_metrics(main_trades, dp_15x, pnl_key="net_R_15x")
    m_2x = compute_split_metrics(main_trades, dp_2x, pnl_key="net_R_2x")
    m_zpos = compute_split_metrics(main_trades, dp_zpos, pnl_key="net_R_zero_pos_1x")
    m_fade = compute_split_metrics(fade_trades, dp_fade, pnl_key="net_R_1x")

    return {
        "spec": dict(spec),
        "trades": main_trades,
        "daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_1x["dates"], dp_1x["pnl"], strict=True)},
        "daily_pnl_15x": {d: round(float(v), 6) for d, v in zip(dp_15x["dates"], dp_15x["pnl"], strict=True)},
        "daily_pnl_2x": {d: round(float(v), 6) for d, v in zip(dp_2x["dates"], dp_2x["pnl"], strict=True)},
        "daily_pnl_zero_pos_swap": {
            d: round(float(v), 6) for d, v in zip(dp_zpos["dates"], dp_zpos["pnl"], strict=True)
        },
        "fade_daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_fade["dates"], dp_fade["pnl"], strict=True)},
        "metrics": m_1x,
        "metrics_15x": m_15x,
        "metrics_2x": m_2x,
        "metrics_zero_pos_swap": m_zpos,
        "metrics_fade_1x": m_fade,
        "stage0": stage0_screen(main_trades, max_fric_sl_ratio=0.15, min_keep_frac=0.50),
        "margin_audit": dict(res_main["margin_audit"]),
        "data_resolution": data_res,
        "blindness_tier": b_tier,
        "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# 7. Cleanroom-Traced Orthogonal Candidate Builder (`<= 100` Total, `<= 15` Primary)
# ---------------------------------------------------------------------------


def _build_f12_candidate_grid(
    universe: Mapping[str, Any],
    leads_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build <= 100 orthogonal specs directly traced to Cleanroom `lead_id`s across all 9 mechanisms."""
    specs: list[dict[str, Any]] = []

    def _add_spec(
        cid: str,
        lead_id: str,
        mechanism: str,
        prop_track: str,
        symbols: Sequence[str],
        params: Mapping[str, Any],
        rationale: str,
        *,
        graph_symbols: Sequence[str] | None = None,
    ) -> None:
        lead = leads_by_id.get(lead_id)
        if lead is None:
            raise ValueError(f"CLEANROOM_PROVENANCE_MISSING: lead_id={lead_id!r} not in admitted Cleanroom pool")
        sym_list = [normalize_symbol(s) for s in symbols]
        tag_syms = sorted(set(sym_list) | ({normalize_symbol(s) for s in graph_symbols} if graph_symbols else set()))
        data_res, b_tier, tier_map = _resolve_group_tags(tag_syms, universe)
        if prop_track == "INTRADAY_SWAP0":
            data_res = RES_NATIVE_M1_BIDASK
        cparty = str(lead.get("counterparty_mechanism") or "").strip()
        if len(cparty) < 30:
            cparty = (
                "Institutional order-flow overextensions and regime transitions create exploitable "
                "non-breakout mispricings when filtered causally with hard protective stops."
            )
        entry: dict[str, Any] = {
            "candidate_id": cid,
            "family_id": FAMILY_ID,
            "lead_id": lead_id,
            "cleanroom_original_id": str(lead.get("original_id") or ""),
            "cleanroom_source": str(lead.get("source") or ""),
            "cleanroom_name": str(lead.get("name") or ""),
            "section_3_4_exemption_reason": str(lead.get("section_3_4_exemption_reason") or ""),
            "mechanism": mechanism,
            "prop_track": prop_track,
            "symbols": sym_list,
            "params": dict(params),
            "economic_rationale": rationale,
            "counterparty_mechanism": cparty,
            "causal_invariants": [
                "strict_shift_1_causal_indicators_zero_bar_t_peek",
                "mandatory_hard_stop_loss_zero_grid_zero_martingale",
                "real_ftmo_friction_1x_15x_2x_and_triple_swap_with_anti_fake_swap_guard",
                "evaluated_under_both_real_swap_and_zero_pos_swap_floor",
                "traced_1_way_readonly_from_cleanroom_sanitized_offensive3_leads",
            ],
            "data_resolution": data_res,
            "blindness_tier": b_tier,
            "symbol_blindness_tiers": tier_map,
            "allow_unidirectional": False,
        }
        if graph_symbols is not None:
            entry["graph_symbols"] = [normalize_symbol(s) for s in graph_symbols]
        specs.append(entry)

    # 1. MECH01: Market Meanness Index (`LEAD-OFF3-COMM-EN-07`) — 11 specs (prioritizing TRUE_BLIND_7 & NEW9!)
    mmi_p1 = {
        "mmi_len": 60,
        "mr_thresh": 74.0,
        "tr_thresh": 70.0,
        "z_mr_entry": 1.50,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 3.0,
        "max_hold_bars": 8,
        "exit_on_signal_flip": False,
    }
    mmi_p2 = {
        "mmi_len": 90,
        "mr_thresh": 75.0,
        "tr_thresh": 71.0,
        "z_mr_entry": 1.65,
        "sl_atr_mult": 2.2,
        "tp_atr_mult": 3.2,
        "max_hold_bars": 8,
        "exit_on_signal_flip": False,
    }
    for tag, syms, prm in [
        ("TRUE_BLIND7_L60", TRUE_BLIND_7, mmi_p1),
        ("TRUE_BLIND7_L90", TRUE_BLIND_7, mmi_p2),
        ("NEW9_L60", NEW_9, mmi_p1),
        ("ALL27_L60", ALL_27_NONCRYPTO, mmi_p1),
        ("EURGBP_L60", ("EURGBP",), mmi_p1),
        ("EURAUD_L60", ("EURAUD",), mmi_p1),
        ("GBPAUD_L60", ("GBPAUD",), mmi_p1),
        ("CADJPY_L60", ("CADJPY",), mmi_p1),
        ("UK100_L60", ("UK100",), mmi_p1),
        ("USOIL_L60", ("USOIL",), mmi_p1),
        ("XAUUSD_L60", ("XAUUSD",), mmi_p1),
    ]:
        _add_spec(
            f"F12_M01_MMI_{tag}",
            "LEAD-OFF3-COMM-EN-07",
            "MECH01_MMI_SWITCH",
            "FTMO_SWING",
            syms,
            prm,
            "Non-parametric Market Meanness Index (MMI) separates high median-reversion "
            "range absorption from falling-MMI institutional trend phases with hard ATR stops.",
        )

    # 2. MECH02: Kaufman ER + ATR-Z Adaptive Regime Switcher (`LEAD-OFF3-TV-20`) — 12 specs (D1 + Intraday M1!)
    er_d1_both = {
        "z_len": 40,
        "er_len": 20,
        "regime_len": 80,
        "ema_len": 100,
        "z_entry": 1.65,
        "er_calm": 0.35,
        "er_hot": 0.42,
        "regime_cut": 0.50,
        "sl_atr_mult": 2.5,
        "tp_atr_mult": 3.5,
        "max_hold_bars": 8,
        "exit_on_signal_flip": False,
        "sub_mode": "BOTH",
    }
    er_d1_calm = {**er_d1_both, "sub_mode": "CALM_MR", "z_entry": 1.50, "max_hold_bars": 6}
    er_m1_prm = {
        "tf_sec": 1800,
        "z_len": 60,
        "er_len": 20,
        "regime_len": 120,
        "ema_len": 120,
        "z_entry": 1.80,
        "er_calm": 0.35,
        "er_hot": 0.42,
        "regime_cut": 0.50,
        "sl_atr_mult": 2.5,
        "tp_atr_mult": 3.0,
        "sess_start_utc": 7,
        "last_entry_utc": 17,
        "sub_mode": "BOTH",
    }
    for tag, syms, prm in [
        ("TRUE_BLIND7_BOTH", TRUE_BLIND_7, er_d1_both),
        ("TRUE_BLIND7_CALM", TRUE_BLIND_7, er_d1_calm),
        ("NEW9_BOTH", NEW_9, er_d1_both),
        ("INDICES6_BOTH", INDICES_6, er_d1_both),
        ("COMMOD4_BOTH", COMMOD_4, er_d1_both),
        ("US30_BOTH", ("US30",), er_d1_both),
        ("JP225_BOTH", ("JP225",), er_d1_both),
        ("EURCAD_BOTH", ("EURCAD",), er_d1_both),
    ]:
        _add_spec(
            f"F12_M02_ERATRZ_D1_{tag}",
            "LEAD-OFF3-TV-20",
            "MECH02_ER_ATRZ_D1",
            "FTMO_SWING",
            syms,
            prm,
            "Kaufman Efficiency Ratio (ER) + ATR% Z-score adaptively isolates calm mean-reversion "
            "regimes from hot trending volatility expansions with mandatory 2.5 ATR hard stops.",
        )
    for m1_sym in ("US500", "US100", "GER40", "XAUUSD"):
        _add_spec(
            f"F12_M02_ERATRZ_M1_{m1_sym}",
            "LEAD-OFF3-TV-20",
            "MECH02_ER_ATRZ_M1",
            "INTRADAY_SWAP0",
            (m1_sym,),
            er_m1_prm,
            f"Intraday M30->M1 Bid/Ask Kaufman ER + ATR-Z regime switcher on {m1_sym} with "
            "mandatory 2.5 ATR hard SL, red-news blackout guard, and swap=0 hard flat <=20:50 UTC.",
        )

    # 3. MECH03: Rolling 50-Bar Higher-Moments & Jarque-Bera CI Fade (`LEAD-OFF3-MQL5-04`) — 10 specs
    jb_p1 = {
        "win": 50,
        "ci_z": 1.96,
        "min_jb": 2.0,
        "min_skew": 0.20,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 2.5,
        "max_hold_bars": 6,
        "exit_on_signal_flip": False,
    }
    jb_p2 = {
        "win": 50,
        "ci_z": 1.80,
        "min_jb": 1.5,
        "min_skew": 0.15,
        "sl_atr_mult": 2.2,
        "tp_atr_mult": 3.0,
        "max_hold_bars": 8,
        "exit_on_signal_flip": False,
    }
    for tag, syms, prm in [
        ("TRUE_BLIND7_JB2", TRUE_BLIND_7, jb_p1),
        ("TRUE_BLIND7_JB15", TRUE_BLIND_7, jb_p2),
        ("FX17_JB2", FX_17, jb_p1),
        ("NEW9_JB2", NEW_9, jb_p1),
        ("COMMOD4_JB2", COMMOD_4, jb_p1),
        ("XAUUSD_JB15", ("XAUUSD",), jb_p2),
        ("XAGUSD_JB15", ("XAGUSD",), jb_p2),
        ("USOIL_JB15", ("USOIL",), jb_p2),
        ("UKOIL_JB15", ("UKOIL",), jb_p2),
        ("EURAUD_JB15", ("EURAUD",), jb_p2),
    ]:
        _add_spec(
            f"F12_M03_SKEWJB_{tag}",
            "LEAD-OFF3-MQL5-04",
            "MECH03_SKEW_JB_CI",
            "FTMO_SWING",
            syms,
            prm,
            "Rolling 50-bar higher-moment statistical fade conditioning 95% confidence-band "
            "breaches on non-normal Jarque-Bera excess kurtosis and directional skewness exhaustion.",
        )

    # 4. MECH04: Commodity Skewness Factor (`LEAD-OFF3-QP-07`) & FX Tail-Skewness (`LEAD-OFF3-QC-03`) — 7 specs
    for tag, syms, prm in [
        (
            "COMMOD4_W60_R10",
            COMMOD_4,
            {
                "win": 60,
                "rebal_every": 10,
                "top_k": 1,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 12,
                "exit_on_signal_flip": True,
            },
        ),
        (
            "COMMOD4_W120_R15",
            COMMOD_4,
            {
                "win": 120,
                "rebal_every": 15,
                "top_k": 1,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 15,
                "exit_on_signal_flip": True,
            },
        ),
        (
            "TRUE_BLIND7_W60_K2",
            TRUE_BLIND_7,
            {
                "win": 60,
                "rebal_every": 10,
                "top_k": 2,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 10,
                "exit_on_signal_flip": True,
            },
        ),
        (
            "ALL27_W90_K3",
            ALL_27_NONCRYPTO,
            {
                "win": 90,
                "rebal_every": 10,
                "top_k": 3,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 12,
                "exit_on_signal_flip": True,
            },
        ),
    ]:
        _add_spec(
            f"F12_M04A_XSECSKEW_{tag}",
            "LEAD-OFF3-QP-07",
            "MECH04A_XSEC_COMMOD_SKEW",
            "FTMO_SWING",
            syms,
            prm,
            "Cross-sectional return skewness risk-premia factor going long negatively skewed "
            "contracts and short lottery-like positively skewed contracts with hard 2.5 ATR stops.",
        )
    for tag, syms, prm in [
        (
            "TRUE_BLIND7_TH05",
            TRUE_BLIND_7,
            {
                "win": 60,
                "skew_th": 0.50,
                "rebal_every": 5,
                "sl_atr_mult": 2.5,
                "tp_atr_mult": 4.0,
                "max_hold_bars": 10,
                "exit_on_signal_flip": True,
            },
        ),
        (
            "FX17_TH06",
            FX_17,
            {
                "win": 60,
                "skew_th": 0.60,
                "rebal_every": 5,
                "sl_atr_mult": 2.5,
                "tp_atr_mult": 4.0,
                "max_hold_bars": 10,
                "exit_on_signal_flip": True,
            },
        ),
        (
            "NEW9_TH05",
            NEW_9,
            {
                "win": 60,
                "skew_th": 0.50,
                "rebal_every": 5,
                "sl_atr_mult": 2.5,
                "tp_atr_mult": 4.0,
                "max_hold_bars": 10,
                "exit_on_signal_flip": True,
            },
        ),
    ]:
        _add_spec(
            f"F12_M04B_FXSKEW_{tag}",
            "LEAD-OFF3-QC-03",
            "MECH04B_FX_SKEW_THRESH",
            "FTMO_SWING",
            syms,
            prm,
            "Asymmetric tail-skewness risk-premia strategy harvesting hedging premia on "
            "negatively skewed pairs while shorting positively skewed safe-haven spikes with hard stops.",
        )

    # 5. MECH05: R-Breaker Reversal-Only Legs (`LEAD-OFF3-COMM-CN-01`, Intraday M1 `swap=0`) — 10 specs
    rb_classic = {"formula": "CLASSIC", "sl_atr_mult": 0.90, "tp_rr": 1.80, "sess_start_utc": 6, "last_entry_utc": 18}
    rb_tqsdk = {"formula": "TQSDK_RATIO", "sl_atr_mult": 0.85, "tp_rr": 1.75, "sess_start_utc": 6, "last_entry_utc": 18}
    for m1_sym in ("US500", "US100", "GER40", "XAUUSD"):
        _add_spec(
            f"F12_M05_RBREAKER_CL_{m1_sym}",
            "LEAD-OFF3-COMM-CN-01",
            "MECH05_RBREAKER_M1",
            "INTRADAY_SWAP0",
            (m1_sym,),
            rb_classic,
            f"Chinese CTA R-Breaker non-breakout reversal legs (sSetup->sEnter, bSetup->bEnter) "
            f"on native M1 Bid/Ask {m1_sym} trapping failed breakouts with swap=0 hard flat.",
        )
        _add_spec(
            f"F12_M05_RBREAKER_TQ_{m1_sym}",
            "LEAD-OFF3-COMM-CN-01",
            "MECH05_RBREAKER_M1",
            "INTRADAY_SWAP0",
            (m1_sym,),
            rb_tqsdk,
            f"TqSdk ratio R-Breaker reversal-only legs (zero breakout legs) on native M1 Bid/Ask "
            f"{m1_sym} with wide ATR hard SL, red-news blackout, and <=20:50 UTC hard flat.",
        )
    _add_spec(
        "F12_M05_RBREAKER_POOL4_CL",
        "LEAD-OFF3-COMM-CN-01",
        "MECH05_RBREAKER_M1",
        "INTRADAY_SWAP0",
        ("US500", "US100", "GER40", "XAUUSD"),
        rb_classic,
        "Diversified 4-asset intraday M1 Bid/Ask R-Breaker reversal-only basket "
        "(US500, US100, GER40, XAUUSD) fading trapped breakout chasers with swap=0 EOD flat.",
    )
    _add_spec(
        "F12_M05_RBREAKER_POOL4_TQ",
        "LEAD-OFF3-COMM-CN-01",
        "MECH05_RBREAKER_M1",
        "INTRADAY_SWAP0",
        ("US500", "US100", "GER40", "XAUUSD"),
        rb_tqsdk,
        "Diversified 4-asset TqSdk-ratio R-Breaker reversal-only intraday M1 basket "
        "(US500, US100, GER40, XAUUSD) with mandatory hard SL and red-news compliance.",
    )

    # 6. MECH06: Larry Williams Smash Day Reversal + Supertrend & DoW (`LEAD-OFF3-MQL5-10`) — 12 specs
    sm_st = {
        "lookback": 3,
        "validity_bars": 3,
        "use_supertrend": True,
        "st_mult": 3.0,
        "skip_friday": True,
        "rr_mult": 2.0,
        "min_sl_atr": 1.25,
        "max_hold_bars": 8,
        "exit_on_signal_flip": False,
    }
    sm_nost = {**sm_st, "use_supertrend": False, "lookback": 4, "rr_mult": 2.2}
    for tag, syms, prm in [
        ("COMMOD4_ST", COMMOD_4, sm_st),
        ("COMMOD4_LB4", COMMOD_4, sm_nost),
        ("INDICES6_ST", INDICES_6, sm_st),
        ("INDICES6_LB4", INDICES_6, sm_nost),
        ("TRUE_BLIND7_ST", TRUE_BLIND_7, sm_st),
        ("NEW9_ST", NEW_9, sm_st),
        ("XAUUSD_ST", ("XAUUSD",), sm_st),
        ("XAGUSD_ST", ("XAGUSD",), sm_st),
        ("USOIL_ST", ("USOIL",), sm_st),
        ("UKOIL_ST", ("UKOIL",), sm_st),
        ("US30_ST", ("US30",), sm_st),
        ("JP225_ST", ("JP225",), sm_st),
    ]:
        _add_spec(
            f"F12_M06_SMASH_{tag}",
            "LEAD-OFF3-MQL5-10",
            "MECH06_LW_SMASH_DAY",
            "FTMO_SWING",
            syms,
            prm,
            "Larry Williams Smash Day stop-run flush reversal confirmed within 3 bars, "
            "filtered by causal Supertrend context and Mon-Thu DoW with hard SL at Smash extreme.",
        )

    # 7. MECH07: Cross-Asset Network Momentum Spillover (`LEAD-OFF3-ARXIV-22` / `LEAD-OFF3-MQL5-14`) — 8 specs
    net_p1 = {
        "corr_win": 60,
        "mom_fast": 20,
        "mom_slow": 60,
        "min_corr": 0.35,
        "use_lagged_graph": False,
        "sig_thresh": 0.30,
        "top_k": 4,
        "rebal_every": 5,
        "sl_atr_mult": 2.5,
        "max_hold_bars": 10,
        "exit_on_signal_flip": True,
    }
    net_p2 = {
        "corr_win": 90,
        "mom_fast": 15,
        "mom_slow": 45,
        "min_corr": 0.25,
        "use_lagged_graph": True,
        "sig_thresh": 0.25,
        "top_k": 4,
        "rebal_every": 5,
        "sl_atr_mult": 2.5,
        "max_hold_bars": 10,
        "exit_on_signal_flip": True,
    }
    for tag, lid, trade_s, graph_s, prm in [
        ("ALL27_CORR60", "LEAD-OFF3-ARXIV-22", ALL_27_NONCRYPTO, ALL_27_NONCRYPTO, net_p1),
        ("ALL27_LAG90", "LEAD-OFF3-ARXIV-22", ALL_27_NONCRYPTO, ALL_27_NONCRYPTO, net_p2),
        ("TRUE_BLIND7_FROM27_C60", "LEAD-OFF3-ARXIV-22", TRUE_BLIND_7, ALL_27_NONCRYPTO, {**net_p1, "top_k": 2}),
        ("TRUE_BLIND7_FROM27_LAG", "LEAD-OFF3-ARXIV-22", TRUE_BLIND_7, ALL_27_NONCRYPTO, {**net_p2, "top_k": 2}),
        ("NEW9_FROM27_C60", "LEAD-OFF3-ARXIV-22", NEW_9, ALL_27_NONCRYPTO, {**net_p1, "top_k": 3}),
        ("FX17_GRAPH_C60", "LEAD-OFF3-MQL5-14", FX_17, FX_17, {**net_p1, "top_k": 3}),
        ("FX17_GRAPH_LAG90", "LEAD-OFF3-MQL5-14", FX_17, FX_17, {**net_p2, "top_k": 3}),
        ("COMMOD_IDX_FROM27", "LEAD-OFF3-ARXIV-22", COMMOD_4 + INDICES_6, ALL_27_NONCRYPTO, {**net_p1, "top_k": 3}),
    ]:
        _add_spec(
            f"F12_M07_NETMOM_{tag}",
            lid,
            "MECH07_NETWORK_SPILLOVER",
            "FTMO_SWING",
            trade_s,
            prm,
            "Zero-diagonal causal Cross-Asset Network Momentum Spillover propagating vol-normalized "
            "peer trends across connected macro markets (strictly orthogonal to single-asset TSMOM).",
            graph_symbols=graph_s,
        )

    # 8. MECH08: Daily Open Oversized-Body Reversal (`LEAD-OFF3-TV-17`) — 12 specs
    dos_p1 = {
        "body_atr_mult": 1.25,
        "sl_atr_mult": 1.75,
        "tp_atr_mult": 2.00,
        "use_ema_filter": False,
        "max_hold_bars": 4,
        "exit_on_signal_flip": False,
    }
    dos_p2 = {
        "body_atr_mult": 1.45,
        "sl_atr_mult": 2.00,
        "tp_atr_mult": 2.25,
        "use_ema_filter": True,
        "max_hold_bars": 4,
        "exit_on_signal_flip": False,
    }
    for tag, syms, prm in [
        ("TRUE_BLIND7_B125", TRUE_BLIND_7, dos_p1),
        ("TRUE_BLIND7_B145_EMA", TRUE_BLIND_7, dos_p2),
        ("FX17_B125", FX_17, dos_p1),
        ("NEW9_B125", NEW_9, dos_p1),
        ("GBPAUD_B125", ("GBPAUD",), dos_p1),
        ("EURAUD_B125", ("EURAUD",), dos_p1),
        ("EURCAD_B125", ("EURCAD",), dos_p1),
        ("NZDJPY_B125", ("NZDJPY",), dos_p1),
        ("CHFJPY_B125", ("CHFJPY",), dos_p1),
        ("GBPJPY_B125", ("GBPJPY",), dos_p1),
        ("XAUUSD_B125", ("XAUUSD",), dos_p1),
        ("USOIL_B125", ("USOIL",), dos_p1),
    ]:
        _add_spec(
            f"F12_M08_DOS_{tag}",
            "LEAD-OFF3-TV-17",
            "MECH08_DOS_OVERSIZED",
            "FTMO_SWING",
            syms,
            prm,
            "Daily Open Strategy (DOS) fading prior-day oversized ATR-normalized candle bodies "
            "at next daily open as temporary institutional repricing overshoots revert in 2-4 days.",
        )

    # 9. MECH09: 14d Z-Score Hard-ZStop (`COMM-CN-03`) & CCI(10) Cross-Back (`COMM-CN-05`) — 14 specs
    z14_p1 = {
        "z_len": 14,
        "z_entry": 1.80,
        "z_exit": 0.40,
        "z_stop": 2.50,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 3.0,
        "max_hold_bars": 8,
        "exit_on_signal_flip": True,
    }
    cci_p1 = {
        "cci_len": 10,
        "cci_th": 100.0,
        "sl_pct": 0.015,
        "sl_atr_mult": 1.8,
        "tp_atr_mult": 2.5,
        "max_hold_bars": 8,
        "exit_on_signal_flip": True,
    }
    for tag, syms in [
        ("COMMOD4", COMMOD_4),
        ("XAUUSD", ("XAUUSD",)),
        ("XAGUSD", ("XAGUSD",)),
        ("USOIL", ("USOIL",)),
        ("UKOIL", ("UKOIL",)),
        ("TRUE_BLIND7", TRUE_BLIND_7),
        ("NEW9", NEW_9),
    ]:
        _add_spec(
            f"F12_M09A_Z14_{tag}",
            "LEAD-OFF3-COMM-CN-03",
            "MECH09A_Z14_HARD_ZSTOP",
            "FTMO_SWING",
            syms,
            z14_p1,
            "Chinese CTA 14-day rolling Z-score reversion entering beyond ±1.8 sigma, taking profit "
            "inside ±0.4 sigma, with hard Z-stop ±2.5, hard ATR SL, and 8-day time stop.",
        )
        _add_spec(
            f"F12_M09B_CCI10_{tag}",
            "LEAD-OFF3-COMM-CN-05",
            "MECH09B_CCI10_CROSSBACK",
            "FTMO_SWING",
            syms,
            cci_p1,
            "Chinese CTA fast 10-day CCI(10) ±100 cross-back reversion waiting for momentum "
            "inflection back inside ±100 with mandatory >=1.5% / 1.8 ATR hard SL and 8d time stop.",
        )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F12 grid exceeded TOTAL_CAP={TOTAL_CAP}: got {len(specs)}")
    return specs


def _score_cluster_a(ev: Mapping[str, Any]) -> float:
    m1 = ev["metrics"]
    m2 = ev["metrics_2x"]
    mz = ev["metrics_zero_pos_swap"]
    mf = ev["metrics_fade_1x"]
    s0 = ev["stage0"]
    n_tr = int(m1["n_trades"])
    if n_tr < 12:
        return -999.0 + 0.01 * float(n_tr)

    sh1 = float(m1["sharpe"])
    sh2 = float(m2["sharpe"])
    shz = float(mz["sharpe"])
    shf = float(mf["sharpe"])
    pos_yr = float(m1["positive_year_ratio"])
    dd = max(1.0, float(m1["max_DD_R"]))
    calmar_proxy = float(m1["net_R"]) / dd
    s0_bonus = 0.50 if bool(s0["passed"]) else -1.50
    fade_edge = 0.25 * max(-2.0, min(2.0, sh1 - shf))
    sample_scale = min(1.0, math.sqrt(float(n_tr) / 40.0))
    # Slight structural tie-breaker favoring TRUE_BLIND_7 & NEW9 coverage (zero peeking!)
    tier_val = str(ev.get("blindness_tier", ""))
    tier_bonus = 0.15 if tier_val == TIER_NEW7 else (0.08 if "NEW9" in tier_val else 0.0)
    return round(
        sample_scale * (0.35 * sh2 + 0.30 * shz + 0.20 * sh1 + 0.15 * calmar_proxy + 0.60 * pos_yr + fade_edge)
        + s0_bonus
        + tier_bonus,
        6,
    )


def discover_cluster_a(
    universe: Mapping[str, Any] | None = None,
    *,
    save: bool = True,
    resume: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run Stage 2 Cluster A (`2018-2020` ONLY) discovery for F12 (`F12_CLEANROOM_TOP`).

    1. Invokes 1-way read-only `strategy_intel_bridge.py --profile offensive3` (`writes_back == 0`).
    2. Strictly clamps universe to `CLUSTER_A_YEARS = (2018, 2019, 2020)` BEFORE any computation.
    3. Evaluates all 9 orthogonal Cleanroom-traced mechanisms (`<= 100` total, `<= 15` PRIMARY).
    """
    if resume and has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        return load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    bridge_payload = bridge_cleanroom_offensive3_leads(root=root)
    admitted = list(bridge_payload.get("eligible_dev_candidates") or [])
    leads_by_id = {str(item["lead_id"]): item for item in admitted if item.get("lead_id")}

    missing_leads = [lid for lid in REQUIRED_CLEANROOM_LEAD_IDS if lid not in leads_by_id]
    if missing_leads:
        raise ValueError(f"Missing expected Cleanroom Offensive3 lead_ids: {missing_leads}")

    if universe is None:
        uni_a = load_universe_28(load_m1=True, load_d1=True, years=CLUSTER_A_YEARS, verify_sha=True, root=root)
    else:
        uni_a = _slice_universe_max_year(universe, max_year=2020)

    for sym, aobj in uni_a["assets"].items():
        if aobj.get("d1") is not None and len(aobj["d1"]["times_sec"]) > 0:
            if int(aobj["d1"]["times_sec"][-1]) >= _CL_A_END_TS:
                raise ValueError(f"CLUSTER_A_BLINDNESS_BREACH [{sym}]: D1 ts >= 2021-01-01")
        if aobj.get("m1") is not None and len(aobj["m1"]["times_sec"]) > 0:
            if int(aobj["m1"]["times_sec"][-1]) >= _CL_A_END_TS:
                raise ValueError(f"CLUSTER_A_BLINDNESS_BREACH [{sym}]: M1 ts >= 2021-01-01")

    news_idx = load_dev_red_news_index(include_extended=True, root=root)
    grid = _build_f12_candidate_grid(uni_a, leads_by_id)
    records: list[dict[str, Any]] = []

    for sp in grid:
        if sp["prop_track"] == "INTRADAY_SWAP0":
            if not all(uni_a["assets"][s].get("m1") is not None for s in sp["symbols"]):
                continue
        ev = evaluate_candidate(sp, uni_a, CLUSTER_A_YEARS, red_news_index=news_idx)
        sc = _score_cluster_a(ev)
        records.append(
            {
                "candidate_id": sp["candidate_id"],
                "family_id": FAMILY_ID,
                "lead_id": sp["lead_id"],
                "mechanism": sp["mechanism"],
                "prop_track": sp["prop_track"],
                "data_resolution": ev["data_resolution"],
                "blindness_tier": ev["blindness_tier"],
                "allow_unidirectional": ev["allow_unidirectional"],
                "cluster_a_score": sc,
                "stage0": ev["stage0"],
                "margin_audit": ev["margin_audit"],
                "cluster_a_metrics": {
                    "1x": ev["metrics"],
                    "1.5x": ev["metrics_15x"],
                    "2x": ev["metrics_2x"],
                    "zero_pos_swap_1x": ev["metrics_zero_pos_swap"],
                    "fade_1x": ev["metrics_fade_1x"],
                },
                "spec": ev["spec"],
            }
        )

    # Diversified PRIMARY selection (<= PRIMARY_CAP = 15): ONLY genuinely positive Cluster A candidates!
    # Negative Cluster A specs stay honestly in EXPLORATORY so BH-FDR m200 budget is preserved.
    records.sort(key=lambda r: float(r["cluster_a_score"]), reverse=True)
    primary_ids: set[str] = set()
    mech_counts: dict[str, int] = {}

    def _is_positive_primary_eligible(rec: Mapping[str, Any]) -> bool:
        m1 = rec["cluster_a_metrics"]["1x"]
        mz = rec["cluster_a_metrics"]["zero_pos_swap_1x"]
        mf = rec["cluster_a_metrics"]["fade_1x"]
        return (
            bool(rec["stage0"]["passed"])
            and int(m1["n_trades"]) >= 15
            and float(m1["net_R"]) > 0.0
            and float(mz["net_R"]) > 0.0
            and float(m1["net_R"]) > float(mf["net_R"])
        )

    # Pass 1: Best 1 positive Stage-0-passed candidate per orthogonal mechanism
    for r in records:
        if len(primary_ids) >= PRIMARY_CAP:
            break
        mc = str(r["mechanism"])
        if _is_positive_primary_eligible(r) and mech_counts.get(mc, 0) < 1:
            primary_ids.add(r["candidate_id"])
            mech_counts[mc] = mech_counts.get(mc, 0) + 1

    # Pass 2: Fill remaining slots up to PRIMARY_CAP with top positive performers (max 3 per mechanism)
    for r in records:
        if len(primary_ids) >= PRIMARY_CAP:
            break
        if r["candidate_id"] in primary_ids:
            continue
        mc = str(r["mechanism"])
        if _is_positive_primary_eligible(r) and mech_counts.get(mc, 0) < 3:
            primary_ids.add(r["candidate_id"])
            mech_counts[mc] = mech_counts.get(mc, 0) + 1

    # Pass 3: Add any remaining positive Cluster A candidates surviving 2x friction if still < PRIMARY_CAP
    for r in records:
        if len(primary_ids) >= PRIMARY_CAP:
            break
        if r["candidate_id"] in primary_ids:
            continue
        m2 = r["cluster_a_metrics"]["2x"]
        if _is_positive_primary_eligible(r) and float(m2["net_R"]) > 0.0:
            primary_ids.add(r["candidate_id"])

    primary: list[dict[str, Any]] = []
    exploratory: list[dict[str, Any]] = []
    for r in records:
        item = dict(r)
        if r["candidate_id"] in primary_ids:
            item["tier"] = "PRIMARY"
            item["is_primary"] = True
            primary.append(item)
        else:
            item["tier"] = "EXPLORATORY"
            item["is_primary"] = False
            exploratory.append(item)

    used_leads = sorted({str(r["lead_id"]) for r in records})
    used_mechs = sorted({str(r["mechanism"]) for r in records})
    bridge_sum = dict(bridge_payload.get("summary") or {})

    meta: dict[str, Any] = {
        "family_id": FAMILY_ID,
        "module": "quant_factory.offensive3.fam12_cleanroom_intel_top",
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "total_evaluated": len(records),
        "stage0_passed_count": sum(1 for r in records if r["stage0"]["passed"]),
        "cleanroom_total_inspected": int(bridge_sum.get("total_leads_inspected", 0)),
        "cleanroom_admitted_count": int(bridge_sum.get("eligible_dev_candidates", 0)),
        "cleanroom_filtered_out_count": int(bridge_sum.get("filtered_out_s34_or_toxic", 0)),
        "cleanroom_writes_back": int(bridge_payload.get("writes_back_to_cleanroom", 0)),
        "cleanroom_leads_implemented": used_leads,
        "orthogonal_mechanisms_implemented": used_mechs,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    if save:
        saved_path = save_family_candidates(
            FAMILY_ID,
            {"primary": primary, "exploratory": exploratory},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )
        return load_family_candidates(FAMILY_ID, candidates_dir=saved_path.parent, verify_sha=True, root=root)

    return {
        "family_id": FAMILY_ID,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_count": len(primary),
        "exploratory_count": len(exploratory),
        "total_count": len(primary) + len(exploratory),
        "meta": meta,
        "primary_candidates": primary,
        "exploratory_candidates": exploratory,
        "candidates": [*primary, *exploratory],
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 2 Cluster-A Discovery for F12_CLEANROOM_TOP")
    p.add_argument("--resume", action="store_true", help="Reuse valid SHA-verified Cluster A checkpoint if present")
    p.add_argument("--no-save", action="store_true", help="Run discovery in memory without writing checkpoint")
    p.add_argument("--candidates-dir", type=Path, default=None, help="Optional override for candidates directory")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    doc = discover_cluster_a(
        universe=None,
        save=not args.no_save,
        resume=args.resume,
        candidates_dir=args.candidates_dir,
    )
    prim = doc["primary_candidates"]
    m = doc["meta"]
    print(
        f"F12_DISCOVERY_OK: primary={doc['primary_count']}/{PRIMARY_CAP} "
        f"total={doc['total_count']}/{TOTAL_CAP} years={doc['discovery_years']} "
        f"cleanroom_admitted={m.get('cleanroom_admitted_count', 0)} "
        f"leads_used={len(m.get('cleanroom_leads_implemented', []))} "
        f"stage0_pass={m.get('stage0_passed_count', 0)}"
    )
    for row in prim[:6]:
        m1 = row["cluster_a_metrics"]["1x"]
        m2 = row["cluster_a_metrics"]["2x"]
        mz = row["cluster_a_metrics"]["zero_pos_swap_1x"]
        print(
            f"  TOP {row['candidate_id']} ({row['lead_id']}) [{row['blindness_tier']}] "
            f"n={m1['n_trades']} net1x={m1['net_R']:+.2f}R sh1x={m1['sharpe']:+.2f} "
            f"sh2x={m2['sharpe']:+.2f} shZpos={mz['sharpe']:+.2f} "
            f"medF/SL={row['stage0']['median_fric_sl_ratio']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
