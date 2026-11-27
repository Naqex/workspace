"""Regression tests for Offensive #3 G06 Causality & Blindness Fixes (Red-Team #1: P0-01, P1-01..P1-03).

Verifies (strictly `python -O` safe via `_check(...)`, ZERO bare `assert`s, `ORDER_SEND_COUNT == 0`,
`holdout_rows_analysed == 0`):
  1. `P0-01`: Yahoo `UK100` (`zero_gap_frac = 99.66%`) extra `+1` bar causal lag guard active in
     `fam11_statarb_pairs_prop`, `fam12_cleanroom_intel_top`, and `fam08_swing_trend_pullback`
     (both synthetic causal perturbation proofs AND real-Dev `F11_SW_GER40_UK100_KALMAN_Z200_H8`
     Sharpe collapse to negative with same-day overlap removed!).
  2. `P1-01`: `fam06_swing_tsmom_28` `swap_filter=True` has ZERO full-array `np.nanmedian` lookahead
     and ZERO 2026 live swap-snapshot dependency in signal generation (bit-for-bit identical Cl.A
     vs full-Dev prefix signals & swap-mutation invariance).
  3. `P1-02` & `P1-03`: Leader-inclusive canonical `blindness_tier` normalization across `fam04`,
     `fam05`, `fam12`, and `stage3_pipeline` (0 false-purity labels, 0 garbled `MIXED_*` strings),
     top-level `evaluated_by_blindness_tier` in `build_compact_funnel_payload()`, and exact
     `planning/research/OFFENSIVE3-ALPHA-FUNNEL-20261127.json` schema (`sum == 1,137`, `< 300 KB`).
"""

from __future__ import annotations

import ast
import copy
import inspect
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES.parents[1]
for _p in (AI_ENGINES, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.offensive3 import (  # noqa: E402
    common_contract as cc,
)
from quant_factory.offensive3 import (  # noqa: E402
    fam04_energy_metals_micro as fam04,
)
from quant_factory.offensive3 import (  # noqa: E402
    fam05_index_intermarket as fam05,
)
from quant_factory.offensive3 import (  # noqa: E402
    fam06_swing_tsmom_28 as fam06,
)
from quant_factory.offensive3 import (  # noqa: E402
    fam08_swing_trend_pullback as fam08,
)
from quant_factory.offensive3 import (  # noqa: E402
    fam11_statarb_pairs_prop as fam11,
)
from quant_factory.offensive3 import (  # noqa: E402
    fam12_cleanroom_intel_top as fam12,
)
from quant_factory.offensive3 import (  # noqa: E402
    stage3_pipeline as s3,
)

FUNNEL_JSON = REPO_ROOT / "planning" / "research" / "OFFENSIVE3-ALPHA-FUNNEL-20261127.json"
PATCHED_MODULES = (
    AI_ENGINES / "quant_factory" / "offensive3" / "fam04_energy_metals_micro.py",
    AI_ENGINES / "quant_factory" / "offensive3" / "fam05_index_intermarket.py",
    AI_ENGINES / "quant_factory" / "offensive3" / "fam06_swing_tsmom_28.py",
    AI_ENGINES / "quant_factory" / "offensive3" / "fam08_swing_trend_pullback.py",
    AI_ENGINES / "quant_factory" / "offensive3" / "fam11_statarb_pairs_prop.py",
    AI_ENGINES / "quant_factory" / "offensive3" / "fam12_cleanroom_intel_top.py",
    AI_ENGINES / "quant_factory" / "offensive3" / "stage3_pipeline.py",
)


def _check(cond: bool, msg: str) -> None:
    """Explicit guard immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _make_d1_bars(
    dates: list[str],
    *,
    base_price: float = 100.0,
    drift: float = 0.0002,
    vol: float = 0.01,
    zero_gap: bool = False,
    seed: int = 123,
    close_override: np.ndarray | None = None,
) -> dict[str, Any]:
    n = len(dates)
    rng = np.random.default_rng(seed)
    ts = np.array(
        [int(datetime.fromisoformat(f"{d}T00:00:00+00:00").timestamp()) for d in dates],
        dtype=np.int64,
    )
    yrs = np.array([int(d[:4]) for d in dates], dtype=np.int32)
    wds = np.array([date.fromisoformat(d).weekday() for d in dates], dtype=np.int32)

    if close_override is not None:
        c = np.asarray(close_override, dtype=np.float64).copy()
    else:
        rets = drift + rng.normal(0.0, vol, size=n)
        c = base_price * np.exp(np.cumsum(rets))

    o = np.empty(n, dtype=np.float64)
    o[0] = c[0] * (1.0 if zero_gap else (1.0 + rng.normal(0.0, vol * 0.25)))
    if zero_gap:
        o[1:] = c[:-1]
    else:
        o[1:] = c[:-1] * (1.0 + rng.normal(0.0, vol * 0.35, size=n - 1))

    h = np.maximum(o, c) * (1.0 + vol * 0.75)
    lo = np.minimum(o, c) * (1.0 - vol * 0.75)
    return {
        "times_sec": ts,
        "dates": list(dates),
        "years": yrs,
        "weekdays": wds,
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
        "spread_price": np.full(n, base_price * 0.0002, dtype=np.float64),
    }


def _make_asset_entry(
    symbol: str,
    d1: dict[str, Any],
    *,
    specs_map: dict[str, Any],
    data_resolution: str | None = None,
    blindness_tier: str | None = None,
    asset_class: str | None = None,
) -> dict[str, Any]:
    base_sym = symbol if symbol in specs_map else "UK100"
    sp = copy.deepcopy(specs_map[base_sym])
    sp["symbol"] = symbol
    default_res = (
        cc.RES_NATIVE_M1_BIDASK if sp.get("blindness_tier") == cc.TIER_12OLD else cc.RES_D1_YAHOO_SANCTIONED
    )
    return {
        "symbol": symbol,
        "spec": sp,
        "asset_class": asset_class or str(sp.get("asset_class", "indices")),
        "data_resolution": data_resolution or str(sp.get("data_resolution", default_res)),
        "blindness_tier": blindness_tier or str(sp.get("blindness_tier", cc.TIER_NEW9)),
        "m1": None,
        "d1": d1,
    }


# ==============================================================================
# 0. [ARCH-02] Zero Bare Asserts & Hard Safety Constants Across All Patched Files
# ==============================================================================


def test_arch02_zero_bare_asserts_and_safety_constants_in_patched_modules() -> None:
    for mod_path in PATCHED_MODULES:
        _check(mod_path.is_file(), f"Missing patched module: {mod_path}")
        tree = ast.parse(mod_path.read_text(encoding="utf-8"), filename=str(mod_path))
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(not bare_asserts, f"[ARCH-02] Bare assert(s) found in {mod_path.name} at lines {bare_asserts}")

    for mod in (fam04, fam05, fam06, fam08, fam11, fam12, s3):
        _check(mod.ORDER_SEND_CAPABLE is False, f"{mod.__name__}.ORDER_SEND_CAPABLE must be False")
        _check(mod.ORDER_SEND_COUNT == 0, f"{mod.__name__}.ORDER_SEND_COUNT must be 0")


# ==============================================================================
# 1. P0-01: UK100 Yahoo Zero-Gap +1 Causal Lag Guard in fam11, fam12, fam08
# ==============================================================================


def test_p0_01_fam11_uk100_zero_gap_guard_synthetic_and_real_kalman_collapse() -> None:
    specs_map = cc.load_ftmo_specs_28()["symbols"]
    dates = cc._build_weekday_calendar((2021, 2022))

    # 1A. Synthetic zero-gap detection & V1 causal perturbation invariance
    d1_ger = _make_d1_bars(dates, base_price=15000.0, vol=0.012, zero_gap=False, seed=10)
    d1_uk = _make_d1_bars(dates, base_price=7200.0, vol=0.010, zero_gap=True, seed=20)
    d1_synth_zg = _make_d1_bars(dates, base_price=5000.0, vol=0.010, zero_gap=True, seed=30)
    d1_eur = _make_d1_bars(dates, base_price=1.10, vol=0.005, zero_gap=False, seed=40)
    d1_chf = _make_d1_bars(dates, base_price=0.92, vol=0.005, zero_gap=False, seed=50)

    mask_uk = fam11._causal_zero_gap_lag_mask("UK100", d1_uk["open"], d1_uk["close"])
    _check(bool(np.all(mask_uk)), "UK100 must trigger zero-gap lag mask on every bar")

    mask_zg_a = fam11._causal_zero_gap_lag_mask("SYNTHZG", d1_synth_zg["open"], d1_synth_zg["close"])
    _check(bool(np.all(mask_zg_a[11:])), "Synthetic zero-gap asset (zero_gap_frac=100%) must trigger for t >= 11")
    # Perturb future bars >= 50 on SYNTHZG -> prefix mask[:50] MUST remain bit-for-bit identical!
    o_mut = d1_synth_zg["open"].copy()
    o_mut[50:] *= 1.07
    mask_zg_b = fam11._causal_zero_gap_lag_mask("SYNTHZG", o_mut, d1_synth_zg["close"])
    _check(bool(np.array_equal(mask_zg_a[:50], mask_zg_b[:50])), "Zero-gap mask must be strictly causal")

    mask_ger = fam11._causal_zero_gap_lag_mask("GER40", d1_ger["open"], d1_ger["close"])
    _check(not bool(np.any(mask_ger)), "Normal non-zero-gap GER40 must not trigger zero-gap lag")

    uni_synth = {
        "assets": {
            "GER40": _make_asset_entry("GER40", d1_ger, specs_map=specs_map),
            "UK100": _make_asset_entry("UK100", d1_uk, specs_map=specs_map),
            "SYNTHZG": _make_asset_entry("SYNTHZG", d1_synth_zg, specs_map=specs_map),
            "EURUSD": _make_asset_entry("EURUSD", d1_eur, specs_map=specs_map),
            "USDCHF": _make_asset_entry("USDCHF", d1_chf, specs_map=specs_map),
        }
    }
    params = {"hedge_model": "KALMAN", "z_win": 25, "z_entry": 1.8, "z_exit": 0.3, "z_stop": 3.5, "max_hold_bars": 8}

    res_uk = fam11._replay_d1_pair_single("GER40", "UK100", uni_synth, params, (2021, 2022))
    _check(res_uk["zero_gap_lag_applied"] is True and res_uk["causal_extra_lag"] == 1, "GER40/UK100 must apply +1 lag")

    res_zg = fam11._replay_d1_pair_single("GER40", "SYNTHZG", uni_synth, params, (2021, 2022))
    _check(
        res_zg["zero_gap_lag_applied"] is True and res_zg["causal_extra_lag"] == 1,
        "GER40/SYNTHZG (zero_gap_frac>=0.90) must apply +1 lag",
    )

    res_ctrl = fam11._replay_d1_pair_single("EURUSD", "USDCHF", uni_synth, params, (2021, 2022))
    _check(
        res_ctrl["zero_gap_lag_applied"] is False and res_ctrl["causal_extra_lag"] == 0,
        "Non-zero-gap control pair EURUSD/USDCHF must keep causal_extra_lag == 0",
    )

    # 1B. Real sealed Dev verification: F11_SW_GER40_UK100_KALMAN_Z200_H8 Sharpe MUST collapse negative!
    ckpt_path = REPO_ROOT / ".runtime" / "offensive3" / "candidates" / "F11_PAIRS_STATARB.json"
    if ckpt_path.is_file():
        uni_real = cc.load_universe_28(
            load_m1=False,
            load_d1=True,
            years=cc.ALL_DEV_YEARS,
            symbols=("GER40", "UK100"),
            verify_sha=False,
        )
        f11_doc = cc.load_family_candidates("F11_PAIRS_STATARB", verify_sha=False)
        all_f11 = [*f11_doc["primary_candidates"], *f11_doc["exploratory_candidates"]]
        kalman_rec = next(c for c in all_f11 if c["candidate_id"] == "F11_SW_GER40_UK100_KALMAN_Z200_H8")
        kalman_spec = kalman_rec.get("spec", kalman_rec)

        res_clb = fam11.evaluate_candidate(kalman_spec, uni_real, cc.CLUSTER_B_YEARS)
        res_cla = fam11.evaluate_candidate(kalman_spec, uni_real, cc.CLUSTER_A_YEARS)
        _check(res_clb["holdout_rows_analysed"] == 0, "Holdout rows analysed must be 0")
        _check(
            float(res_clb["metrics"]["sharpe"]) < 0.0,
            f"Expected F11_SW_GER40_UK100_KALMAN_Z200_H8 Cl.B Sharpe < 0, got {res_clb['metrics']['sharpe']}",
        )
        _check(
            float(res_cla["metrics"]["sharpe"]) < 0.0,
            f"Expected F11_SW_GER40_UK100_KALMAN_Z200_H8 Cl.A Sharpe < 0, got {res_cla['metrics']['sharpe']}",
        )
        _check(
            res_clb["blindness_tier"] == "MIXED_12OLD_AND_NEW9",
            f"Expected canonical MIXED_12OLD_AND_NEW9 for GER40/UK100, got {res_clb['blindness_tier']!r}",
        )


def test_p0_01_fam12_uk100_zero_gap_guard_xsec_and_network_spillover() -> None:
    dates = cc._build_weekday_calendar((2021, 2022))
    n = len(dates)
    syms = ["GER40", "US500", "UK100", "CADJPY"]
    bars_base = {
        "GER40": _make_d1_bars(dates, base_price=15000.0, vol=0.012, zero_gap=False, seed=101),
        "US500": _make_d1_bars(dates, base_price=4200.0, vol=0.011, zero_gap=False, seed=102),
        "UK100": _make_d1_bars(dates, base_price=7200.0, vol=0.010, zero_gap=True, seed=103),
        "CADJPY": _make_d1_bars(dates, base_price=95.0, vol=0.008, zero_gap=False, seed=104),
    }
    close_base = np.column_stack([bars_base[s]["close"] for s in syms])

    # Perturb late-closing peer US500 & GER40 at bar `t_probe - 1` (evening before UK100 open[t_probe]):
    # With the +1 bar causal zero-gap lag guard active, signals at `t_probe` MUST be bit-for-bit identical!
    t_probe = 120  # Divisible by both rebal=10 (xsec skew) and rebal=5 (network spillover)
    bars_mut = copy.deepcopy(bars_base)
    bars_mut["GER40"]["close"][t_probe - 1] *= 1.18
    bars_mut["GER40"]["high"][t_probe - 1] *= 1.18
    bars_mut["US500"]["close"][t_probe - 1] *= 0.85
    bars_mut["US500"]["low"][t_probe - 1] *= 0.85
    close_mut = np.column_stack([bars_mut[s]["close"] for s in syms])

    skew_params = {"win": 40, "rebal_every": 10, "top_k": 1, "sl_atr_mult": 2.5}
    sigs_sk_a, _, _ = fam12._signals_xsec_commodity_skew(syms, bars_base, close_base, skew_params)
    sigs_sk_b, _, _ = fam12._signals_xsec_commodity_skew(syms, bars_mut, close_mut, skew_params)
    for s in syms:
        _check(
            sigs_sk_a[s][t_probe] == sigs_sk_b[s][t_probe],
            f"fam12 xsec skew leaked day t-1 peer close into bar {t_probe} for {s}",
        )

    net_params = {
        "corr_win": 40,
        "mom_fast": 15,
        "mom_slow": 40,
        "min_corr": 0.05,
        "use_lagged_graph": False,
        "sig_thresh": 0.05,
        "top_k": 2,
        "rebal_every": 5,
        "sl_atr_mult": 2.5,
    }
    sigs_nt_a, _, _ = fam12._signals_network_spillover(syms, syms, bars_base, close_base, net_params)
    sigs_nt_b, _, _ = fam12._signals_network_spillover(syms, syms, bars_mut, close_mut, net_params)
    for s in syms:
        _check(
            sigs_nt_a[s][t_probe] == sigs_nt_b[s][t_probe],
            f"fam12 network spillover leaked day t-1 peer close into bar {t_probe} for {s}",
        )

    # Verify panel mask is False when NO zero-gap asset is present
    no_uk_syms = ["GER40", "US500", "CADJPY"]
    mask_no_uk = fam12._panel_zero_gap_lag_mask(no_uk_syms, bars_base, n)
    _check(not bool(np.any(mask_no_uk)), "Non-UK100 normal panel must not force extra lag")


def test_p0_01_fam08_uk100_pool_slot_contention_causal_lag_guard() -> None:
    specs_map = cc.load_ftmo_specs_28()["symbols"]
    dates = cc._build_weekday_calendar((2021,))
    n = len(dates)

    d1_ger = _make_d1_bars(dates, base_price=15000.0, vol=0.012, zero_gap=False, seed=201)
    d1_uk = _make_d1_bars(dates, base_price=7200.0, vol=0.010, zero_gap=True, seed=202)
    d1_eur = _make_d1_bars(dates, base_price=1.10, vol=0.005, zero_gap=False, seed=203)

    ind_ger = fam08._compute_pullback_indicators(d1_ger)
    ind_uk = fam08._compute_pullback_indicators(d1_uk)
    ind_map = {"GER40": ind_ger, "UK100": ind_uk}

    # Direct slot-contention perturbation proof at bar `t_probe`:
    # UK100 has a pullback trigger already visible at `t_probe - 1` (eligible on `t_probe` under +1 lag).
    # Mutating GER40's trigger/strength at index `t_probe` (which comes from GER40 close[t_probe - 1] at
    # 22:00 UTC) MUST NOT affect UK100's slot allocation on bar `t_probe`!
    t_probe = 80
    ed_uk = np.zeros(n, dtype=np.float64)
    st_uk = np.zeros(n, dtype=np.float64)
    ed_uk[t_probe - 1] = 1.0
    st_uk[t_probe - 1] = 0.60

    ed_ger_a = np.zeros(n, dtype=np.float64)
    st_ger_a = np.zeros(n, dtype=np.float64)
    ed_ger_b = np.zeros(n, dtype=np.float64)
    st_ger_b = np.zeros(n, dtype=np.float64)
    # Huge GER40 trigger at `t_probe` (evening close of day t_probe - 1) ONLY in scenario B
    ed_ger_b[t_probe] = 1.0
    st_ger_b[t_probe] = 99.0

    sl_map = {"GER40": np.full(n, 200.0, dtype=np.float64), "UK100": np.full(n, 100.0, dtype=np.float64)}
    tp_map: dict[str, np.ndarray | None] = {"GER40": None, "UK100": None}

    sig_a = fam08._build_causal_pulse_signals_pool(
        ["GER40", "UK100"],
        ind_map,
        {"GER40": ed_ger_a, "UK100": ed_uk},
        {"GER40": st_ger_a, "UK100": st_uk},
        sl_map,
        tp_map,
        max_hold_bars=4,
        max_concurrent=1,
        eval_year_set={2021},
    )
    sig_b = fam08._build_causal_pulse_signals_pool(
        ["GER40", "UK100"],
        ind_map,
        {"GER40": ed_ger_b, "UK100": ed_uk},
        {"GER40": st_ger_b, "UK100": st_uk},
        sl_map,
        tp_map,
        max_hold_bars=4,
        max_concurrent=1,
        eval_year_set={2021},
    )
    _check(sig_a["UK100"][t_probe] == 1.0, "UK100 should enter at t_probe from strictly causal t_probe-1 trigger")
    _check(
        sig_a["UK100"][t_probe] == sig_b["UK100"][t_probe] and sig_a["GER40"][t_probe] == sig_b["GER40"][t_probe],
        "fam08 pool leaked GER40 bar t_probe (22:00 UTC day t-1) into UK100 slot contention on bar t_probe",
    )

    # Verify evaluate_candidate flags causal_extra_lag==1 for UK100 pool and 0 for single-asset / non-UK100 pool
    uni = {
        "assets": {
            "GER40": _make_asset_entry("GER40", d1_ger, specs_map=specs_map),
            "UK100": _make_asset_entry("UK100", d1_uk, specs_map=specs_map),
            "EURUSD": _make_asset_entry("EURUSD", d1_eur, specs_map=specs_map),
        }
    }
    base_spec = {
        "candidate_id": "TEST_F08_POOL",
        "mechanism": "ibs_pullback",
        "symbols": ["GER40", "UK100"],
        "params": {"trend_len": 20, "ibs_lo": 0.25, "max_hold_bars": 4, "sl_atr_mult": 2.0, "max_concurrent": 1},
    }
    res_pool_uk = fam08.evaluate_candidate(base_spec, uni, (2021,))
    _check(res_pool_uk["causal_extra_lag"] == 1, "Multi-asset pool with UK100 must set causal_extra_lag == 1")
    _check(res_pool_uk["blindness_tier"] == "MIXED_12OLD_AND_NEW9", f"Unexpected tier: {res_pool_uk['blindness_tier']}")

    res_single_uk = fam08.evaluate_candidate({**base_spec, "symbols": ["UK100"]}, uni, (2021,))
    _check(res_single_uk["causal_extra_lag"] == 0, "Single-asset UK100 has no cross-asset overlap (lag == 0)")

    res_pool_no_uk = fam08.evaluate_candidate({**base_spec, "symbols": ["GER40", "EURUSD"]}, uni, (2021,))
    _check(res_pool_no_uk["causal_extra_lag"] == 0, "Non-UK100 normal pool must keep causal_extra_lag == 0")


# ==============================================================================
# 2. P1-01: fam06 swap_filter Zero nanmedian & Zero 2026 Swap-Snapshot Dependency
# ==============================================================================


def test_p1_01_fam06_swap_filter_causal_price_vol_only() -> None:
    # 2A. Static AST verification: ZERO nanmedian/median and ZERO compute_daily_swap_frac in signal builder!
    src = inspect.getsource(fam06._build_tsmom_signal_and_weights)
    tree = ast.parse(src)
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
    _check("nanmedian" not in called_names, "P1-01 breach: nanmedian still called in fam06 signal generation!")
    _check("median" not in called_names, "P1-01 breach: median still called in fam06 signal generation!")
    _check(
        "compute_daily_swap_frac" not in called_names,
        "P1-01 breach: compute_daily_swap_frac still called in fam06 signal generation!",
    )

    # 2B. Cl.A vs Full-Dev zero decision flip proof (even when 2021-2024 price triples!)
    specs_map = cc.load_ftmo_specs_28()["symbols"]
    dates_all = cc._build_weekday_calendar(cc.ALL_DEV_YEARS)
    n_all = len(dates_all)
    n_cla = sum(1 for d in dates_all if int(d[:4]) <= 2020)

    rng = np.random.default_rng(303)
    rets = rng.normal(0.0005, 0.011, size=n_all)
    closes = 2800.0 * np.exp(np.cumsum(rets))
    # Simulate massive 2021-2024 regime price jump (previously flipped US500/XAGUSD swap_filter decisions!)
    closes[n_cla:] *= 3.0
    d1_all = _make_d1_bars(dates_all, vol=0.011, close_override=closes, seed=303)
    d1_cla = fam06._slice_d1_upto_year(d1_all, 2020)

    feat_all = fam06._compute_asset_tsmom_features(d1_all)
    feat_cla = fam06._compute_asset_tsmom_features(d1_cla)
    prm = {
        "forecast_key": "ewmac_16_64_yz",
        "entry_thresh": 0.65,
        "cadence": "continuous",
        "vol_mode": "mm_inv_var",
        "sl_atr_mult": 2.0,
        "tp_atr_mult": None,
        "max_hold_bars": 4,
        "swap_filter": True,
    }
    sp_us500 = copy.deepcopy(specs_map["US500"])

    sig_cla, sl_cla, _, w_cla = fam06._build_tsmom_signal_and_weights(feat_cla, sp_us500, prm)
    sig_all, sl_all, _, w_all = fam06._build_tsmom_signal_and_weights(feat_all, sp_us500, prm)
    _check(
        bool(np.array_equal(sig_cla, sig_all[:n_cla])),
        "fam06 swap_filter=True flipped 2018-2020 signals when 2021-2024 bars were appended!",
    )
    _check(bool(np.array_equal(w_cla, w_all[:n_cla])), "fam06 mm_weights must be strictly causal")
    _check(
        bool(np.array_equal(np.isnan(sl_cla), np.isnan(sl_all[:n_cla]))),
        "fam06 sl_arr mask must be strictly causal",
    )

    # 2C. Zero 2026 live swap-snapshot dependency in signal generation!
    sp_poisoned = copy.deepcopy(sp_us500)
    sp_poisoned["swap_long"] = -9999.0
    sp_poisoned["swap_short"] = -9999.0
    sig_pois, _, _, w_pois = fam06._build_tsmom_signal_and_weights(feat_all, sp_poisoned, prm)
    _check(
        bool(np.array_equal(sig_all, sig_pois)) and bool(np.array_equal(w_all, w_pois)),
        "fam06 signal generation must NEVER depend on 2026 live swap_long/swap_short snapshots!",
    )


# ==============================================================================
# 3. P1-02 & P1-03: Leader-Inclusive Canonical blindness_tier & Tracked Funnel
# ==============================================================================


def test_p1_02_p1_03_leader_inclusive_canonical_blindness_tier_normalization() -> None:
    # 3A. Canonical normalization across all 7 valid combinations + garbled legacy inputs
    _check(s3.normalize_blindness_tier([cc.TIER_12OLD]) == cc.TIER_12OLD, "Pure 12OLD")
    _check(s3.normalize_blindness_tier([cc.TIER_NEW9]) == cc.TIER_NEW9, "Pure NEW9")
    _check(s3.normalize_blindness_tier([cc.TIER_NEW7]) == cc.TIER_NEW7, "Pure NEW7")
    _check(s3.normalize_blindness_tier([cc.TIER_12OLD, cc.TIER_NEW9]) == "MIXED_12OLD_AND_NEW9", "12OLD+NEW9")
    _check(s3.normalize_blindness_tier([cc.TIER_12OLD, cc.TIER_NEW7]) == "MIXED_12OLD_AND_TRUE_BLIND_7", "12OLD+NEW7")
    _check(s3.normalize_blindness_tier([cc.TIER_NEW9, cc.TIER_NEW7]) == "MIXED_NEW9_AND_TRUE_BLIND_7", "NEW9+NEW7")
    _check(
        s3.normalize_blindness_tier([cc.TIER_12OLD, cc.TIER_NEW9, cc.TIER_NEW7]) == "MIXED_ALL_3_TIERS",
        "All 3 tiers",
    )
    garbled = (
        "MIXED_DEV_CLB_CONSUMED_12OLD_MIXED_12OLD_AND_NEW9_MIXED_NEW9_AND_TRUE_BLIND_7_"
        "MULTI_TIER_MIXED_NEW9_D1_VIEWED_M1_UNSEEN_TRUE_BLIND_CLB_NEW7_CROSSES"
    )
    norm_garbled = s3.normalize_blindness_tier([garbled, "MIXED_MULTI_TIER"])
    _check(norm_garbled == "MIXED_ALL_3_TIERS", f"Garbled string failed to normalize cleanly: {norm_garbled!r}")
    _check(norm_garbled in s3.CANONICAL_BLINDNESS_TIERS, "Normalized tier must be in CANONICAL_BLINDNESS_TIERS")

    # 3B. fam04 build_f04_candidate_specs MUST include leader tiers (0 false-purity!)
    f04_specs = fam04.build_f04_candidate_specs()
    by_id_04 = {sp["candidate_id"]: sp for sp in f04_specs}
    for cid, sp in by_id_04.items():
        _check(sp["blindness_tier"] in s3.CANONICAL_BLINDNESS_TIERS, f"Non-canonical F04 tier on {cid}")
        if "TO_CADJPY" in cid:
            _check(
                sp["blindness_tier"] == "MIXED_NEW9_AND_TRUE_BLIND_7",
                f"F04 Oil->CADJPY must be MIXED_NEW9_AND_TRUE_BLIND_7, got {sp['blindness_tier']!r}",
            )
        if "XAU_TO_XAG" in cid:
            _check(
                sp["blindness_tier"] == "MIXED_12OLD_AND_NEW9",
                f"F04 XAU->XAG must be MIXED_12OLD_AND_NEW9, got {sp['blindness_tier']!r}",
            )
        if "TO_USDCAD" in cid:
            _check(
                sp["blindness_tier"] == "MIXED_12OLD_AND_NEW9",
                f"F04 Oil->USDCAD must be MIXED_12OLD_AND_NEW9, got {sp['blindness_tier']!r}",
            )

    # 3C. fam05 _resolve_resolution_and_tier MUST include leader_symbols & emit canonical labels
    specs_map = cc.load_ftmo_specs_28()["symbols"]
    dates = cc._build_weekday_calendar((2021,))
    mini_syms = (
        "US100",
        "US500",
        "JP225",
        "UK100",
        "XAUUSD",
        "XAGUSD",
        "USOIL",
        "CADJPY",
        "CHFJPY",
        "USDJPY",
        "AUDJPY",
    )
    uni_mini = {
        "assets": {
            sym: _make_asset_entry(sym, _make_d1_bars(dates, seed=400 + i), specs_map=specs_map)
            for i, sym in enumerate(mini_syms)
        }
    }
    res_f05_1, tier_f05_1 = fam05._resolve_resolution_and_tier(["JP225"], uni_mini, leader_symbols=["US100"])
    _check(res_f05_1 == cc.RES_D1_YAHOO_SANCTIONED, f"Expected D1_YAHOO_SANCTIONED, got {res_f05_1}")
    _check(tier_f05_1 == "MIXED_12OLD_AND_NEW9", f"US100->JP225 must be MIXED_12OLD_AND_NEW9, got {tier_f05_1}")

    _, tier_f05_2 = fam05._resolve_resolution_and_tier(["CHFJPY"], uni_mini, leader_symbols=["US500"])
    _check(
        tier_f05_2 == "MIXED_12OLD_AND_TRUE_BLIND_7",
        f"US500->CHFJPY must be MIXED_12OLD_AND_TRUE_BLIND_7, got {tier_f05_2}",
    )

    _, tier_f05_3 = fam05._resolve_resolution_and_tier(
        ["USDJPY", "AUDJPY", "CHFJPY"], uni_mini, leader_symbols=["US500"]
    )
    _check(tier_f05_3 == "MIXED_ALL_3_TIERS", f"US500->JPYBASKET3 must be MIXED_ALL_3_TIERS, got {tier_f05_3}")

    # 3D. stage3_pipeline._extract_candidate_symbols & _resolve_resolution_and_blindness
    # Even when `trades` is non-empty AND stale `spec['blindness_tier']` has false purity or garbled MIXED_*!
    stale_f04_spec = {
        "candidate_id": "F04_LEADLAG_XAU_TO_XAG_DIRECT_FOLLOW_LB2_T100_H3",
        "symbols": ["XAGUSD"],
        "leader_symbols": ["XAUUSD"],
        "blindness_tier": cc.TIER_NEW9,  # Stale false-purity tag from old checkpoint
        "data_resolution": cc.RES_D1_YAHOO_SANCTIONED,
    }
    trades_xag = [{"symbol": "XAGUSD", "blindness_tier": cc.TIER_NEW9, "data_resolution": cc.RES_D1_YAHOO_SANCTIONED}]
    syms_f04 = s3._extract_candidate_symbols(stale_f04_spec, trades_xag)
    _check({"XAGUSD", "XAUUSD"}.issubset(set(syms_f04)), f"Leader XAUUSD missing from extracted symbols: {syms_f04}")
    _, bt_f04 = s3._resolve_resolution_and_blindness(stale_f04_spec, {"blindness_tier": garbled}, trades_xag, uni_mini)
    _check(bt_f04 == "MIXED_12OLD_AND_NEW9", f"stage3 failed to fix F04 false purity: got {bt_f04!r}")

    stale_f05_spec = {
        "candidate_id": "F05B_TZ_US100_to_JP225_cont_1d_z10_h3",
        "symbols": ["JP225"],
        "params": {"leader_symbol": "US100"},
        "blindness_tier": cc.TIER_NEW9,
    }
    trades_jp = [{"symbol": "JP225", "blindness_tier": cc.TIER_NEW9}]
    syms_f05 = s3._extract_candidate_symbols(stale_f05_spec, trades_jp)
    _check({"JP225", "US100"}.issubset(set(syms_f05)), f"Leader US100 missing from extracted symbols: {syms_f05}")
    _, bt_f05 = s3._resolve_resolution_and_blindness(stale_f05_spec, {}, trades_jp, uni_mini)
    _check(bt_f05 == "MIXED_12OLD_AND_NEW9", f"stage3 failed to fix F05 false purity: got {bt_f05!r}")

    # F12 network spillover graph_symbols inclusion
    f12_net_spec = {
        "candidate_id": "F12_M07_NETMOM_TRUE_BLIND7_FROM27_C60",
        "symbols": ["CADJPY"],
        "graph_symbols": ["US500", "UK100", "CADJPY"],
        "blindness_tier": cc.TIER_NEW7,
    }
    _, bt_f12 = s3._resolve_resolution_and_blindness(f12_net_spec, {}, [{"symbol": "CADJPY"}], uni_mini)
    _check(bt_f12 == "MIXED_ALL_3_TIERS", f"F12 network graph must propagate MIXED_ALL_3_TIERS, got {bt_f12!r}")

    # 3E. build_compact_funnel_payload emits top-level `evaluated_by_blindness_tier` with canonical keys only
    mock_cands = [
        {
            "strategy_id": f"F01::C{i}",
            "alpha_family_id": "F01",
            "pool_tier": "EXPLORATORY",
            "symbols": ["US500"],
            "data_resolution": cc.RES_NATIVE_M1_BIDASK,
            "blindness_tier": bt,
            "is_swing": False,
            "n_trades_clb": 50,
            "net_r_1x": 1.0,
            "net_r_15x": 0.8,
            "net_r_2x": 0.6,
            "net_r_zero_pos_swap": 1.0,
            "fade_net_r_1x": -1.0,
            "sharpe_clb": 0.5,
            "dsr_council": 0.2,
            "dsr_empirical": 0.1,
            "p_sign_flip_50k": 0.05,
            "analytical_p": {"p_newey_west": 0.05},
            "bh_q_primary": None,
            "bh_q_exploratory": 1.0,
            "robustness_gate": {"pillars": {"R1_random_entry_mc": {}, "R3_top5_outlier_trim": {}}},
            "timing_permutation": {"p_value": 0.1},
            "crisis_stress_2018_2024": {"passed": True, "worst_crisis_dd_r": 1.0},
            "research_council": {"verdict": "REJECT_KILLED", "gates": {}},
            "classification": {
                "tier": s3.TIER_3_DEAD_NO_EDGE,
                "tier1_resolution_tag": None,
                "failed_core_gates": ["CORE_BH_FDR_GT_010"],
                "failed_prop_gates": ["PROP_COUNCIL_REJECT_KILLED"],
            },
        }
        for i, bt in enumerate((cc.TIER_12OLD, garbled, "MIXED_12OLD_AND_NEW9"))
    ]
    payload = s3.build_compact_funnel_payload(
        {
            "generated_utc": "2026-11-27T14:50:00Z",
            "campaign_run_id": "unit-test",
            "git_sha": "abc",
            "data_sha": "0" * 64,
            "holdout_lock_sha256": "1" * 64,
            "statistical_config": {},
            "duckdb_ledger_summary": {},
            "effective_trials_n_eff": {},
            "campaign_pbo": {},
            "funnel_counts": {"total_evaluated": 3},
            "family_summaries": {},
            "candidates": mock_cands,
        }
    )
    ebt = payload["evaluated_by_blindness_tier"]
    _check(sum(ebt.values()) == 3, f"evaluated_by_blindness_tier sum != 3: {ebt}")
    _check(set(ebt.keys()).issubset(s3.CANONICAL_BLINDNESS_TIERS), f"Non-canonical keys in funnel payload: {ebt}")
    _check(ebt.get("MIXED_ALL_3_TIERS") == 1, f"Garbled string must normalize into MIXED_ALL_3_TIERS: {ebt}")


def test_p1_03_tracked_funnel_json_canonical_breakdown_size_and_uk100_annotation() -> None:
    if not FUNNEL_JSON.is_file():
        pytest.skip("Tracked funnel JSON not present")

    raw_bytes = FUNNEL_JSON.read_bytes()
    _check(
        len(raw_bytes) < s3.MAX_TRACKED_FUNNEL_BYTES,
        f"Tracked funnel exceeds 300 KB: {len(raw_bytes)} >= {s3.MAX_TRACKED_FUNNEL_BYTES}",
    )
    doc = json.loads(raw_bytes.decode("utf-8"))
    _check(doc["holdout_rows_analysed"] == 0, "Funnel holdout_rows_analysed must be 0")
    _check(doc["order_send_capable"] is False and doc["order_send_count"] == 0, "Funnel order_send must be 0")
    _check(doc["funnel_counts"]["tier1_ftmo_ready"] == 0, "TIER_1 must stay 0")
    _check(doc["funnel_counts"]["tier2_personal_vault"] == 0, "TIER_2 must stay 0")
    _check(doc["funnel_counts"]["tier3_dead_no_edge"] == 1137, "TIER_3 must stay 1,137")

    _check("evaluated_by_blindness_tier" in doc, "Top-level evaluated_by_blindness_tier missing from funnel JSON!")
    ebt = doc["evaluated_by_blindness_tier"]
    _check(isinstance(ebt, dict) and len(ebt) > 0, "evaluated_by_blindness_tier must be non-empty dict")
    _check(sum(ebt.values()) == 1137, f"evaluated_by_blindness_tier must sum to 1,137, got {sum(ebt.values())}: {ebt}")
    bad_keys = [k for k in ebt if k not in s3.CANONICAL_BLINDNESS_TIERS]
    _check(not bad_keys, f"Non-canonical keys in evaluated_by_blindness_tier: {bad_keys}")

    # Verify Top-20 near-miss cards have ONLY canonical blindness_tier AND leader-inclusive fixes!
    for card in doc.get("tier3_dead_top20_near_misses", []):
        sid = str(card["strategy_id"])
        bt = str(card["blindness_tier"])
        _check(bt in s3.CANONICAL_BLINDNESS_TIERS, f"Non-canonical blindness_tier {bt!r} on {sid}")
        if "XAU_TO_XAG" in sid or "US100_to_JP225" in sid:
            _check(
                bt == "MIXED_12OLD_AND_NEW9",
                f"Cross-asset near-miss {sid} must be MIXED_12OLD_AND_NEW9 (leader-inclusive), got {bt!r}",
            )

    # Verify honest Red-Team #1 UK100 zero-gap debunking annotation is recorded!
    audit_note = doc.get("redteam_1_causality_audit")
    _check(isinstance(audit_note, dict), "Missing redteam_1_causality_audit annotation in tracked funnel JSON")
    _check(
        audit_note.get("verdict_unchanged_tier1_0_tier2_0_tier3_1137") is True,
        "Funnel audit annotation must confirm TIER_1=0 / TIER_2=0 / TIER_3=1,137 unchanged",
    )
    kalman_note = audit_note.get("debunked_uk100_zero_gap_artifact") or {}
    _check(
        kalman_note.get("strategy_id") == "F11_PAIRS_STATARB::F11_SW_GER40_UK100_KALMAN_Z200_H8",
        "Missing F11_SW_GER40_UK100_KALMAN_Z200_H8 debunking record",
    )
    _check(
        float(kalman_note.get("post_fix_sharpe_clb", 1.0)) < 0.0,
        f"Debunked post_fix_sharpe_clb must be < 0, got {kalman_note.get('post_fix_sharpe_clb')}",
    )
