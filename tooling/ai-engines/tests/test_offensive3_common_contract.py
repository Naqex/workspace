"""Offline verification suite for Total Offensive #3 Shared 28-Symbol Engine Contract.

Validates every invariant of `quant_factory/offensive3/common_contract.py` with
`OrderSend = 0`, `holdout_rows_analysed == 0`, and full `python -O` compatibility
via `_check(...)`:
  1. AST zero bare `assert`s, X13 air-gap purity, and `compute_router` cache inclusion.
  2. Full 28/28 real universe load (`12` NATIVE_M1_BIDASK + `9` NEW9 + `7` TRUE_BLIND_NEW7,
     `holdout_rows == 0`, `max_ts < 1735689600`).
  3. Critical USOIL `2020-04-20..2020-04-21` hygiene quarantine (`min(open) > 0`, `min(low) >= 1.0`).
  4. Strict `shift = 1` causality check across all 6 indicators AND Swing replay.
  5. Intraday M1 replay (`swap = 0`, hard flat <= `20:50 UTC`, MARKET/STOP/LIMIT Bid/Ask,
     SL-before-TP tie-break, `1.0x/1.5x/2.0x` friction, `6-CCY + 8-CCY/EIA` red-news filter).
  6. Triple-swap Wed/Fri, Anti-Fake-Swap Guard (`US100/US500/UK100/USOIL/UKOIL` capped at 0),
     `BTCUSD swap_mode=5 (-30%/yr)`, `real_swap` vs `zero_pos_swap` floor.
  7. FTMO Swing leverage margin check across all 5 asset classes (`30/15/9/10/1`).
  8. Stage-0 filter, daily PnL series, split metrics, and atomic `--resume` candidate checkpoints.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
OPS_CLOUD_DIR = AI_ENGINES_DIR / "ops_cloud"
for _p in (REPO_ROOT, AI_ENGINES_DIR, OPS_CLOUD_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import compute_router as cr  # noqa: E402
from quant_factory.offensive3 import common_contract as cc  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` stripping."""
    if not cond:
        raise AssertionError(msg)


def _make_synthetic_d1_bars(
    start_day: str,
    n_days: int,
    *,
    base_price: float = 100.0,
    drift: float = 0.05,
    spread_h_l: float = 1.0,
) -> dict[str, Any]:
    dates: list[str] = []
    ts_list: list[int] = []
    wds: list[int] = []
    cur = date.fromisoformat(start_day)
    while len(dates) < n_days:
        if cur.weekday() < 5:
            dates.append(cur.isoformat())
            ts_list.append(int(datetime(cur.year, cur.month, cur.day, 0, 0, tzinfo=UTC).timestamp()))
            wds.append(cur.weekday())
        cur += timedelta(days=1)
    idx = np.arange(n_days, dtype=np.float64)
    o = base_price + idx * drift
    c = o + drift * 0.8
    h = np.maximum(o, c) + spread_h_l
    lo = np.minimum(o, c) - spread_h_l
    return {
        "times_sec": np.array(ts_list, dtype=np.int64),
        "dates": dates,
        "years": np.array([int(d[:4]) for d in dates], dtype=np.int32),
        "weekdays": np.array(wds, dtype=np.int32),
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
    }


def _make_synthetic_m1_day(
    day_iso: str,
    *,
    start_hour: int = 8,
    end_hour: int = 22,
    base_price: float = 1.10000,
    spread: float = 0.00010,
) -> tuple[np.ndarray, np.ndarray]:
    y, m, d = (int(x) for x in day_iso.split("-"))
    t0 = int(datetime(y, m, d, start_hour, 0, tzinfo=UTC).timestamp())
    n_min = (end_hour - start_hour) * 60 + 1
    times = t0 + np.arange(n_min, dtype=np.int64) * 60
    q = np.zeros((n_min, 8), dtype=np.float64)
    for i in range(n_min):
        bp = base_price + i * 0.00001
        q[i, 0] = bp
        q[i, 1] = bp + 0.00015
        q[i, 2] = bp - 0.00015
        q[i, 3] = bp + 0.00001
        q[i, 4:8] = q[i, 0:4] + spread
    return times, q


# ==============================================================================
# 1. Static Hard Invariants: Zero Bare Asserts, Air-Gap Purity, X13 Dev Cache
# ==============================================================================


def test_common_contract_static_invariants_and_x13_purity() -> None:
    src_path = AI_ENGINES_DIR / "quant_factory" / "offensive3" / "common_contract.py"
    _check(src_path.is_file(), f"Missing {src_path}")
    src = src_path.read_text(encoding="utf-8")

    # Zero bare asserts ([ARCH-02])
    tree = ast.parse(src, filename=str(src_path))
    asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    _check(not asserts, f"Bare assert statement(s) in common_contract.py: {asserts}")

    # Pure X13 air-gap check: no forbidden imports or restricted tokens
    forbidden_tokens = ("2025", "2026", "holdout", "duckdb", "holdout_guard", "scipy", "metatrader5", "pandas")
    low_src = src.lower()
    for tok in forbidden_tokens:
        _check(tok not in low_src, f"Forbidden token {tok!r} in common_contract.py")

    _check(cc.ORDER_SEND_CAPABLE is False and cc.ORDER_SEND_COUNT == 0, "OrderSend invariants failed")
    _check(cc.CLUSTER_A_YEARS == (2018, 2019, 2020), f"Bad CLUSTER_A_YEARS: {cc.CLUSTER_A_YEARS}")
    _check(cc.CLUSTER_B_YEARS == (2021, 2022, 2023, 2024), f"Bad CLUSTER_B_YEARS: {cc.CLUSTER_B_YEARS}")
    _check(cc.ALL_DEV_YEARS == (2018, 2019, 2020, 2021, 2022, 2023, 2024), "Bad ALL_DEV_YEARS")
    _check(cc.DEV_CUTOFF_SEC == 1_735_689_600, "Bad DEV_CUTOFF_SEC")

    # Verify compute_router picks up common_contract.py cleanly without violating air-gap
    collected = cr.collect_dev_cache_files(root=REPO_ROOT, include_tapes=False)
    arcs = {arc for arc, _ in collected["entries"]}
    _check(
        "tooling/ai-engines/quant_factory/offensive3/common_contract.py" in arcs,
        "common_contract.py not in X13 cache",
    )


# ==============================================================================
# 2. Full 28/28 Universe Load & USOIL 2020-04-21 Quarantine Verification
# ==============================================================================


@pytest.mark.local_cache
def test_load_universe_28_real_data_hygiene_and_usoil_quarantine() -> None:
    specs = cc.load_ftmo_specs_28()
    _check(specs["symbol_count"] == 28 and len(specs["symbols"]) == 28, "Expected 28 specs")

    # Full 28/28 D1 + H4 load across ALL_DEV_YEARS (2018..2024) with SHA-256 verification
    uni = cc.load_universe_28(load_m1=False, load_d1=True, verify_sha=True)
    _check(uni["symbol_count"] == 28, f"Expected 28 symbols, got {uni['symbol_count']}")
    _check(uni["holdout_rows_analysed"] == 0 and uni["order_send_count"] == 0, "Safety fields must be 0")
    _check(uni["max_ts"] < cc.DEV_CUTOFF_SEC, f"max_ts breach: {uni['max_ts']}")
    _check(uni["tier_counts"][cc.TIER_12OLD] == 12, f"Tier 12OLD mismatch: {uni['tier_counts']}")
    _check(uni["tier_counts"][cc.TIER_NEW9] == 9, f"Tier NEW9 mismatch: {uni['tier_counts']}")
    _check(uni["tier_counts"][cc.TIER_NEW7] == 7, f"Tier NEW7 mismatch: {uni['tier_counts']}")
    _check(uni["resolution_counts"][cc.RES_NATIVE_M1_BIDASK] == 12, f"M1 res mismatch: {uni['resolution_counts']}")
    _check(uni["resolution_counts"][cc.RES_D1_YAHOO_SANCTIONED] == 16, f"D1 res mismatch: {uni['resolution_counts']}")

    for sym, aobj in uni["assets"].items():
        _check(aobj["holdout_rows"] == 0, f"{sym} holdout_rows != 0")
        _check(aobj["max_ts"] < cc.DEV_CUTOFF_SEC, f"{sym} max_ts >= DEV_CUTOFF_SEC")
        _check(aobj["max_date"] < "2025-01-01", f"{sym} max_date >= 2025-01-01")
        d1 = aobj["d1"]
        n_d1 = len(d1["dates"]) if d1 else 0
        _check(d1 is not None and n_d1 >= 1500, f"{sym} D1 bar count too small: {n_d1}")
        _check(float(np.min(d1["open"])) > 0.0, f"{sym} min(open) <= 0")
        _check(float(np.min(d1["high"])) > 0.0, f"{sym} min(high) <= 0")
        _check(float(np.min(d1["low"])) > 0.0, f"{sym} min(low) <= 0")
        _check(float(np.min(d1["close"])) > 0.0, f"{sym} min(close) <= 0")
        if aobj["data_resolution"] == cc.RES_NATIVE_M1_BIDASK:
            _check(aobj["h4"] is not None and len(aobj["h4"]["dates"]) > len(d1["dates"]), f"{sym} H4 missing")
        else:
            _check(aobj["m1"] is None and aobj["h4"] is None, f"{sym} unexpected M1/H4 on D1 asset")

    # CRITICAL DATA HYGIENE (#690): Verify USOIL 2020-04-21 (-14.0 open!) was quarantined cleanly
    usoil = uni["assets"]["USOIL"]
    _check(
        "2020-04-21" in usoil["hygiene"]["quarantined_dates"],
        f"USOIL 2020-04-21 not quarantined: {usoil['hygiene']}",
    )
    _check("2020-04-21" not in usoil["d1"]["dates"], "USOIL 2020-04-21 survived in D1 dates")
    _check("2020-04-20" not in usoil["d1"]["dates"], "USOIL 2020-04-20 survived in D1 dates")
    _check(float(np.min(usoil["d1"]["open"])) >= 1.0, f"USOIL min(open)={np.min(usoil['d1']['open'])}")
    _check(float(np.min(usoil["d1"]["low"])) >= 1.0, f"USOIL min(low)={np.min(usoil['d1']['low'])}")

    # Also verify load_m1=True on a native M1 symbol in Cluster A only (strictly < 2021-01-01)
    uni_m1_a = cc.load_universe_28(
        load_m1=True,
        load_d1=True,
        years=cc.CLUSTER_A_YEARS,
        symbols=("USDJPY", "USOIL"),
        verify_sha=False,
    )
    usdjpy_m1 = uni_m1_a["assets"]["USDJPY"]["m1"]
    _check(usdjpy_m1 is not None and usdjpy_m1["quotes"].shape[1] == 8, "USDJPY native M1 quotes missing")
    cl_a_end_ts = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp())
    _check(int(usdjpy_m1["times_sec"][-1]) < cl_a_end_ts, "Cluster A leaked >= 2021")
    _check(usdjpy_m1["median_spread_pts"] > 0.0, "USDJPY median spread must be > 0")


def test_usoil_quarantine_synthetic_both_days_and_cutoff_rejection(tmp_path: Path) -> None:
    spec_oil = cc.get_symbol_spec("USOIL")
    p_oil = tmp_path / "USOIL.parquet"
    tbl = pa.table(
        {
            "date": ["2020-04-17", "2020-04-20", "2020-04-21", "2020-04-22"],
            "ts_sec": [1587110400, 1587369600, 1587456000, 1587542400],
            "open": [18.5, 17.7, -14.0, 13.2],
            "high": [19.1, 18.0, 13.86, 14.5],
            "low": [17.8, -40.3, 1e-6, 12.1],
            "close": [18.2, -37.63, 10.01, 13.8],
        }
    )
    pq.write_table(tbl, p_oil)
    d1, hyg = cc._load_and_sanitize_d1_parquet("USOIL", p_oil, spec_oil, req_years=(2020,), verify_sha=False)
    _check(d1["dates"] == ["2020-04-17", "2020-04-22"], f"Expected both Apr 20-21 quarantined, got {d1['dates']}")
    _check(hyg["quarantined_dates"] == ["2020-04-20", "2020-04-21"], f"Bad quarantine log: {hyg}")
    _check(float(np.min(d1["low"])) >= 1.0 and float(np.min(d1["open"])) > 0.0, "Post-quarantine OHLC check failed")

    # Fail-closed rejection if any 2025 row sneaks into a D1 parquet
    p_bad = tmp_path / "BAD.parquet"
    tbl_bad = pa.table(
        {
            "date": ["2024-12-31", "2025-01-02"],
            "ts_sec": [1735603200, 1735776000],
            "open": [70.0, 71.0],
            "high": [71.0, 72.0],
            "low": [69.0, 70.0],
            "close": [70.5, 71.5],
        }
    )
    pq.write_table(tbl_bad, p_bad)
    with pytest.raises(ValueError, match="DEV_CUTOFF_BREACH"):
        cc._load_and_sanitize_d1_parquet("USOIL", p_bad, spec_oil, req_years=(2024,), verify_sha=False)


# ==============================================================================
# 3. Strict `shift = 1` Causality Check (All 6 Indicators + Swing Replay)
# ==============================================================================


def test_causal_indicators_strict_shift1_perturbation_invariance() -> None:
    rng = np.random.default_rng(20240101)
    n = 120
    rets = rng.normal(0.0005, 0.012, size=n)
    c = 100.0 * np.exp(np.cumsum(rets))
    h = c * (1.0 + rng.uniform(0.002, 0.015, size=n))
    lo = c * (1.0 - rng.uniform(0.002, 0.015, size=n))

    t_probe = 65
    c_pert = c.copy()
    h_pert = h.copy()
    lo_pert = lo.copy()
    # Massively perturb bar t_probe (10x spike!) — MUST NOT change indicator[t_probe] or earlier!
    c_pert[t_probe] *= 5.0
    h_pert[t_probe] *= 6.0
    lo_pert[t_probe] *= 0.2

    pairs = [
        ("sma", cc.causal_sma(c, 14), cc.causal_sma(c_pert, 14)),
        ("ema", cc.causal_ema(c, 14), cc.causal_ema(c_pert, 14)),
        ("atr", cc.causal_atr(h, lo, c, 14), cc.causal_atr(h_pert, lo_pert, c_pert, 14)),
        ("rsi", cc.causal_rsi(c, 14), cc.causal_rsi(c_pert, 14)),
        ("rvol", cc.causal_realized_vol(c, 20), cc.causal_realized_vol(c_pert, 20)),
        ("zscore", cc.causal_zscore(c, 20), cc.causal_zscore(c_pert, 20)),
    ]

    for name, base, pert in pairs:
        _check(np.isnan(base[0]), f"{name}[0] must be NaN (shift=1)")
        _check(np.isfinite(base[t_probe]), f"{name}[{t_probe}] must be finite after warmup")
        _check(
            np.allclose(base[: t_probe + 1], pert[: t_probe + 1], equal_nan=True, rtol=0.0, atol=0.0),
            f"LOOKAHEAD_VIOLATION in {name}: perturbing bar {t_probe} changed indicator at <= {t_probe}!",
        )
        # Bar t_probe + 1 MUST reflect the perturbation (proving indicator isn't dead/constant)
        _check(
            not math.isclose(float(base[t_probe + 1]), float(pert[t_probe + 1]), rel_tol=1e-9, abs_tol=1e-9),
            f"{name}[{t_probe + 1}] did not respond to bar {t_probe} perturbation",
        )

    # Extra range/formula checks: RSI strictly in [0, 100], SMA exact mean of previous n bars
    rsi_vals = cc.causal_rsi(c, 14)
    fin_rsi = rsi_vals[np.isfinite(rsi_vals)]
    _check(float(np.min(fin_rsi)) >= 0.0 and float(np.max(fin_rsi)) <= 100.0, "RSI out of [0, 100]")
    sma10 = cc.causal_sma(c, 10)
    _check(math.isclose(float(sma10[25]), float(np.mean(c[15:25])), rel_tol=1e-12), "causal_sma exact shift=1 math")

    # 2D matrix support sanity
    mat = np.column_stack([c, c * 2.0])
    sma_2d = cc.causal_sma(mat, 10)
    _check(sma_2d.shape == (n, 2) and np.allclose(sma_2d[:, 0], sma10, equal_nan=True), "2D causal_sma mismatch")


# ==============================================================================
# 4. Intraday M1 Replay (Bid/Ask, Hard Flat <= 20:50 UTC, SL>TP Tie, Red-News)
# ==============================================================================


def test_replay_intraday_m1_trade_mechanics_tiebreak_friction_and_red_news() -> None:
    # Day 2018-01-05 has official US_NFP at 13:30:00Z!
    times, q = _make_synthetic_m1_day("2018-01-05", start_hour=8, end_hour=22, base_price=1.20000, spread=0.00010)
    spec = cc.get_symbol_spec("EURUSD")

    # (A) Conservative SL-before-TP tie-break on SAME M1 bar
    q_tie = q.copy()
    entry_i = 60  # 09:00 UTC
    entry_ask = float(q_tie[entry_i, 4])
    sl_p = entry_ask - 0.00100
    tp_p = entry_ask + 0.00200
    # Bar entry_i + 5 hits BOTH SL and TP on Bid -> conservative SL MUST WIN!
    q_tie[entry_i + 5, 2] = sl_p - 0.00020
    q_tie[entry_i + 5, 1] = tp_p + 0.00030

    tr_tie = cc.replay_intraday_m1_trade(
        "EURUSD", times, q_tie, entry_i, +1, sl_p, tp_price=tp_p, spec=spec, firm_profile="FTMO_STANDARD"
    )
    _check(tr_tie["filled"] is True, f"Expected filled trade: {tr_tie}")
    _check(tr_tie["exit_reason"] == "SL_HIT", f"Conservative SL must beat TP on same bar, got {tr_tie['exit_reason']}")
    _check(tr_tie["swap_R"] == 0.0, "Intraday swap_R must be strictly 0.0")
    _check(
        tr_tie["net_R_1x"] >= tr_tie["net_R_15x"] >= tr_tie["net_R_2x"],
        f"Friction tiers must be monotonic: {tr_tie['net_R_by_tier']}",
    )
    _check(tr_tie["friction_over_sl"] > 0.0, "Stage-0 friction_over_sl must be > 0")

    # (B) Hard flat strictly <= 20:50 UTC even when flat_idx points to 21:45 UTC
    entry_late = 10 * 60  # 18:00 UTC
    flat_too_late = 13 * 60 + 45  # 21:45 UTC
    tr_flat = cc.replay_intraday_m1_trade(
        "EURUSD",
        times,
        q,
        entry_late,
        +1,
        float(q[entry_late, 4]) - 0.05000,
        flat_idx=flat_too_late,
        spec=spec,
    )
    _check(
        tr_flat["filled"] is True and tr_flat["exit_reason"] == "HARD_FLAT_2050",
        f"Expected HARD_FLAT_2050: {tr_flat}",
    )
    dt_ex = datetime.fromtimestamp(int(tr_flat["exit_ts"]), tz=UTC)
    _check((dt_ex.hour, dt_ex.minute) <= (20, 50), f"Hard flat breached 20:50 UTC: {dt_ex}")

    # (C) Buy STOP order trigger + gap slippage realism
    q_stop = q.copy()
    trig = float(q_stop[entry_i, 4]) + 0.00050
    q_stop[entry_i + 3, 4] = trig + 0.00020  # Ask opens ABOVE trigger -> realistic gap fill at ask_open!
    q_stop[entry_i + 3, 5] = trig + 0.00030
    tr_stop = cc.replay_intraday_m1_trade(
        "EURUSD",
        times,
        q_stop,
        entry_i,
        +1,
        trig - 0.00200,
        entry_order_type="STOP",
        entry_trigger_price=trig,
        order_expire_idx=entry_i + 10,
        spec=spec,
    )
    _check(tr_stop["filled"] is True and tr_stop["entry_idx"] == entry_i + 3, f"STOP fill failed: {tr_stop}")
    _check(tr_stop["entry_price"] >= trig + 0.00019, "Buy STOP gap fill must execute at ask_open > trigger")

    # (D) Red-News 6-CCY + Extended 8-CCY/EIA integration (block entry & pre-news flatten)
    news_idx = cc.load_dev_red_news_index(include_extended=True)
    _check(news_idx["extended_loaded"] is True and news_idx["total_events"] >= 900, f"Bad news index: {news_idx}")
    _check(news_idx["max_ts"] < cc.DEV_CUTOFF_SEC, "Red-news index breached DEV_CUTOFF_SEC")
    oil_codes = cc.match_symbol_red_news_codes("USOIL")
    _check("EIA" in oil_codes and "USD" in oil_codes, f"USOIL news codes: {oil_codes}")
    _check("CHF" in cc.match_symbol_red_news_codes("USDCHF"), "USDCHF CHF news code")

    # 2018-01-05 13:28 UTC is inside +-300s of 13:30 UTC US_NFP -> MUST block!
    nfp_entry_idx = (13 - 8) * 60 + 28
    tr_blk = cc.replay_intraday_m1_trade(
        "EURUSD",
        times,
        q,
        nfp_entry_idx,
        +1,
        float(q[nfp_entry_idx, 4]) - 0.00200,
        spec=spec,
        red_news_index=news_idx,
        news_pad_sec=300,
    )
    _check(tr_blk["filled"] is False and tr_blk["status"] == "BLOCKED_RED_NEWS", f"Expected BLOCKED_RED_NEWS: {tr_blk}")

    # Entry at 12:00 UTC before 13:30 UTC US_NFP -> MUST flatten at 13:25 UTC!
    pre_nfp_idx = (12 - 8) * 60
    tr_nf = cc.replay_intraday_m1_trade(
        "EURUSD",
        times,
        q,
        pre_nfp_idx,
        +1,
        float(q[pre_nfp_idx, 4]) - 0.05000,
        spec=spec,
        red_news_index=news_idx,
        news_pad_sec=300,
        flatten_before_news=True,
    )
    _check(
        tr_nf["filled"] is True and tr_nf["exit_reason"] == "RED_NEWS_FLATTEN",
        f"Expected RED_NEWS_FLATTEN: {tr_nf}",
    )
    dt_nf = datetime.fromtimestamp(int(tr_nf["exit_ts"]), tz=UTC)
    _check((dt_nf.hour, dt_nf.minute) == (13, 25), f"Expected 13:25 UTC pre-NFP flatten, got {dt_nf}")


# ==============================================================================
# 5. Triple-Swap Wed/Fri, Anti-Fake-Swap Guard, BTCUSD swap_mode=5, Leverage Margin
# ==============================================================================


def test_swap_triple_rollover_anti_fake_swap_guard_and_btcusd_mode5() -> None:
    specs = cc.load_ftmo_specs_28()["symbols"]

    # (A) FX Wed 3x rollover (`swap_rollover3days=3` -> py_weekday=2) + real_swap vs zero_pos_swap
    usdjpy = specs["USDJPY"]
    sw_mon_l = cc.compute_daily_swap_frac(usdjpy, 150.0, +1, py_weekday=0, zero_positive_swap=False)
    sw_wed_l = cc.compute_daily_swap_frac(usdjpy, 150.0, +1, py_weekday=2, zero_positive_swap=False)
    sw_fri_l = cc.compute_daily_swap_frac(usdjpy, 150.0, +1, py_weekday=4, zero_positive_swap=False)
    _check(sw_mon_l > 0.0 and math.isclose(sw_wed_l, 3.0 * sw_mon_l, rel_tol=1e-12), "USDJPY Wed 3x failed")
    _check(math.isclose(sw_fri_l, sw_mon_l, rel_tol=1e-12), "USDJPY Fri must be 1x, not 3x")
    # zero_positive_swap floor zeroes positive FX carry while paying 100% of negative FX swap
    sw_wed_l_z = cc.compute_daily_swap_frac(usdjpy, 150.0, +1, py_weekday=2, zero_positive_swap=True)
    sw_wed_s_z = cc.compute_daily_swap_frac(usdjpy, 150.0, -1, py_weekday=2, zero_positive_swap=True)
    _check(sw_wed_l_z == 0.0 and sw_wed_s_z < 0.0, "USDJPY zero_pos_swap floor failed")

    # (B) Metals Wed 3x rollover (XAUUSD)
    xau = specs["XAUUSD"]
    sw_xau_mon = cc.compute_daily_swap_frac(xau, 2000.0, +1, py_weekday=0)
    sw_xau_wed = cc.compute_daily_swap_frac(xau, 2000.0, +1, py_weekday=2)
    _check(sw_xau_mon < 0.0 and math.isclose(sw_xau_wed, 3.0 * sw_xau_mon, rel_tol=1e-12), "XAUUSD Wed 3x failed")

    # (C) Anti-Fake-Swap Guard: ALL 5 positive anomalies MUST be capped at 0.0 (zero fake swap credit!)
    anomalies = [
        ("US100", 15000.0, +1),
        ("US500", 4500.0, +1),
        ("UK100", 7800.0, -1),
        ("USOIL", 75.0, +1),
        ("UKOIL", 80.0, +1),
    ]
    for sym, px, side in anomalies:
        sw_real = cc.compute_daily_swap_frac(specs[sym], px, side, py_weekday=4, zero_positive_swap=False)
        sw_floor = cc.compute_daily_swap_frac(
            specs[sym], px, side, py_weekday=4, zero_positive_swap=False, conservative_financing_floor=True
        )
        _check(sw_real == 0.0, f"Anti-Fake-Swap Guard failed on {sym} side={side}: got {sw_real}")
        _check(sw_floor < 0.0, f"Conservative financing floor failed on {sym}: got {sw_floor}")

    # Verify negative swaps on Indices/Oil pay full Fri 3x (`py_weekday=4`)
    sw_oil_mon = cc.compute_daily_swap_frac(specs["USOIL"], 75.0, -1, py_weekday=0)
    sw_oil_fri = cc.compute_daily_swap_frac(specs["USOIL"], 75.0, -1, py_weekday=4)
    _check(sw_oil_mon < 0.0 and math.isclose(sw_oil_fri, 3.0 * sw_oil_mon, rel_tol=1e-12), "USOIL short Fri 3x failed")

    # (D) BTCUSD swap_mode=5 (-30%/yr, Fri 3x)
    btc = specs["BTCUSD"]
    sw_btc_mon = cc.compute_daily_swap_frac(btc, 50000.0, +1, py_weekday=0)
    sw_btc_fri = cc.compute_daily_swap_frac(btc, 50000.0, +1, py_weekday=4)
    sw_btc_short = cc.compute_daily_swap_frac(btc, 50000.0, -1, py_weekday=0)
    exp_btc_daily = -0.30 / 365.0
    _check(math.isclose(sw_btc_mon, exp_btc_daily, rel_tol=1e-12), f"BTCUSD mode=5 daily mismatch: {sw_btc_mon}")
    _check(math.isclose(sw_btc_fri, 3.0 * exp_btc_daily, rel_tol=1e-12), f"BTCUSD Fri 3x mismatch: {sw_btc_fri}")
    _check(math.isclose(sw_btc_short, exp_btc_daily, rel_tol=1e-12), "BTCUSD short mode=5 mismatch")


def test_ftmo_swing_leverage_margin_check_and_swing_d1_replay() -> None:
    specs = cc.load_ftmo_specs_28()["symbols"]

    # Check exact leverage schedule across all 5 asset classes
    expected_lev = {"EURUSD": 30, "US100": 15, "XAUUSD": 9, "USOIL": 10, "BTCUSD": 1}
    for sym, lev in expected_lev.items():
        _, _, got_lev = cc.compute_notional_and_margin_per_lot_usd(specs[sym], 100.0, account_type="ftmo_swing")
        _check(got_lev == lev, f"{sym} Swing leverage mismatch: expected {lev}, got {got_lev}")

    # Over-margined BTCUSD 1:1 trade on 10K Swing (0.25% SL + 1% risk wants 4x notional = 400% margin!)
    chk_scaled = cc.check_leverage_margin(
        specs["BTCUSD"],
        50_000.0,
        49_875.0,  # 0.25% SL
        account_balance_usd=10_000.0,
        risk_frac=0.01,
        account_type="ftmo_swing",
        max_margin_util_frac=0.80,
        scale_if_over_margin=True,
    )
    _check(chk_scaled["accepted"] is True and chk_scaled["margin_capped"] is True, f"BTCUSD should scale: {chk_scaled}")
    _check(chk_scaled["margin_util_frac"] <= 0.80 + 1e-9, f"Scaled margin breached 80%: {chk_scaled}")
    _check(chk_scaled["eff_risk_scale"] < 0.25, f"Expected heavy risk scale-down on 1:1 Crypto: {chk_scaled}")

    chk_reject = cc.check_leverage_margin(
        specs["BTCUSD"],
        50_000.0,
        49_875.0,
        account_balance_usd=10_000.0,
        risk_frac=0.01,
        account_type="ftmo_swing",
        max_margin_util_frac=0.80,
        scale_if_over_margin=False,
    )
    _check(
        chk_reject["accepted"] is False and chk_reject["reason"] == "OVER_MARGIN_REJECTED",
        f"Expected reject: {chk_reject}",
    )

    # Test Swing replay shift=1 causality, mandatory hard SL, and real_swap vs zero_pos_swap on synthetic bars
    bars = _make_synthetic_d1_bars("2020-01-02", 40, base_price=108.0, drift=0.15, spread_h_l=0.40)
    sig = np.zeros(40, dtype=np.float64)
    sig[5:20] = 1.0  # signal at bar 5 close -> enters at bar 6 open!
    sl_d = np.full(40, 2.0, dtype=np.float64)
    tp_d = np.full(40, 6.0, dtype=np.float64)

    res = cc.replay_swing_trades("USDJPY", bars, sig, sl_d, tp_dists=tp_d, max_hold_bars=12, spec=specs["USDJPY"])
    _check(res["n_trades"] >= 1, "Expected >= 1 Swing trade")
    tr0 = res["trades"][0]
    _check(tr0["entry_idx"] == 6, f"Strict shift=1 must enter on bar 6 open, got {tr0['entry_idx']}")
    _check(tr0["swap_real_R"] > 0.0 and tr0["swap_zero_pos_R"] == 0.0, f"Expected positive real swap vs 0 floor: {tr0}")
    _check(tr0["net_R_1x"] >= tr0["net_R_15x"] >= tr0["net_R_2x"], "Swing friction tiers not monotonic")

    # Missing hard SL MUST fail closed!
    with pytest.raises(ValueError, match="MISSING_HARD_SL"):
        cc.replay_swing_trades("USDJPY", bars, sig, np.zeros(40), spec=specs["USDJPY"])

    # Window boundary clamp: passing 2020..2021 bars with years=CLUSTER_A_YEARS MUST NOT step into 2021!
    bars_cross = _make_synthetic_d1_bars("2020-12-15", 25, base_price=104.0, drift=0.10, spread_h_l=0.30)
    sig_cross = np.ones(25, dtype=np.float64)
    res_cross = cc.replay_swing_trades(
        "USDJPY",
        bars_cross,
        sig_cross,
        np.full(25, 2.0),
        max_hold_bars=30,
        years=cc.CLUSTER_A_YEARS,
        spec=specs["USDJPY"],
    )
    _check(res_cross["n_trades"] == 1, f"Expected 1 clamped trade, got {res_cross['n_trades']}")
    _check(res_cross["trades"][0]["exit_date"] < "2021-01-01", f"Leaked into 2021: {res_cross['trades'][0]}")
    _check(res_cross["trades"][0]["exit_reason"] == "END_OF_WINDOW", f"Bad exit reason: {res_cross['trades'][0]}")


@pytest.mark.local_cache
def test_replay_swing_d1_series_real_3tier_cache() -> None:
    """Multi-asset `replay_swing_d1_series` across M1-resampled D1 (EURUSD) & Yahoo D1 (USOIL + CADJPY)."""
    uni_sub = cc.load_universe_28(
        load_m1=False,
        load_d1=True,
        years=cc.CLUSTER_A_YEARS,
        symbols=("EURUSD", "USOIL", "CADJPY"),
        verify_sha=False,
    )
    sigs_map = {}
    sls_map = {}
    for sym in ("EURUSD", "USOIL", "CADJPY"):
        d1 = uni_sub["assets"][sym]["d1"]
        ema_f = cc.causal_ema(d1["close"], 10)
        ema_s = cc.causal_ema(d1["close"], 30)
        atr14 = cc.causal_atr(d1["high"], d1["low"], d1["close"], 14)
        s_arr = np.where(np.isfinite(ema_f) & np.isfinite(ema_s) & (ema_f > ema_s), 1.0, 0.0)
        sigs_map[sym] = s_arr
        sls_map[sym] = np.where(np.isfinite(atr14) & (atr14 > 0.0), 2.0 * atr14, np.nan)

    series_res = cc.replay_swing_d1_series(uni_sub, sigs_map, sls_map, max_hold_bars=10, years=cc.CLUSTER_A_YEARS)
    _check(series_res["n_trades"] >= 10, f"Expected multi-asset trades across 3 tiers: {series_res['n_trades']}")
    _check(series_res["holdout_rows_analysed"] == 0 and series_res["order_send_count"] == 0, "Safety fields")
    _check(set(series_res["years"]) == {2018, 2019, 2020}, f"Bad years: {series_res['years']}")
    _check(series_res["stage0"]["n_total"] == series_res["n_trades"], "Stage-0 trade count mismatch")
    # USOIL long swaps in real_swap MUST be <= 0.0 (Anti-Fake-Swap Guard!)
    for tr in series_res["per_symbol"]["USOIL"]["trades"]:
        _check(tr["swap_real_R"] <= 1e-12, f"USOIL long received fake positive swap: {tr}")


# ==============================================================================
# 6. Stage-0 Filter, Split Metrics & Atomic `--resume` Candidate Checkpoints
# ==============================================================================


def test_stage0_metrics_and_resume_candidate_checkpoint_guards(tmp_path: Path) -> None:
    trades = [
        {"exit_date": "2018-03-15", "net_R": 1.8, "friction_over_sl": 0.06},
        {"exit_date": "2018-09-20", "net_R": -1.0, "friction_over_sl": 0.08},
        {"exit_date": "2019-05-10", "net_R": 2.2, "friction_over_sl": 0.09},
        {"exit_date": "2020-07-14", "net_R": 1.5, "friction_over_sl": 0.12},
    ]
    s0_pass = cc.stage0_screen(trades, max_fric_sl_ratio=0.15, min_keep_frac=0.50)
    _check(s0_pass["passed"] is True and s0_pass["keep_frac"] == 1.0, f"Stage-0 pass failed: {s0_pass}")
    s0_fail = cc.stage0_screen(trades, max_fric_sl_ratio=0.07, min_keep_frac=0.50)
    _check(s0_fail["passed"] is False and s0_fail["n_kept"] == 1, f"Stage-0 fail check failed: {s0_fail}")

    dpnl = cc.compute_daily_pnl_series(trades, years=cc.CLUSTER_A_YEARS)
    met = cc.compute_split_metrics(trades, dpnl)
    _check(met["n_trades"] == 4 and math.isclose(met["net_R"], 4.5, rel_tol=1e-9), f"Bad metrics: {met}")
    _check(met["positive_years"] == 3 and met["total_years"] == 3, f"Expected 3/3 positive years: {met}")
    _check(met["pf"] > 4.0 and met["winrate"] == 0.75 and met["max_DD_R"] >= 1.0, f"Bad ratio stats: {met}")

    # Atomic save / load / --resume checkpoint for F01 (prereg primary_cap = 18)
    cdir = tmp_path / "candidates"
    prim = [{"candidate_id": f"F01_P{i:02d}", "tier": "PRIMARY", "cluster_a_net_R": 3.5} for i in range(18)]
    expl = [{"candidate_id": f"F01_E{i:02d}", "tier": "EXPLORATORY", "cluster_a_net_R": 1.2} for i in range(40)]
    meta = {"discovery_years": [2018, 2019, 2020], "family_slug": "F01_FX_SESSION_FIXING_FLOW"}

    saved_path = cc.save_family_candidates("F01", prim + expl, meta, candidates_dir=cdir)
    _check(
        saved_path.is_file() and cc.has_valid_family_checkpoint("F01", candidates_dir=cdir),
        "Checkpoint save failed",
    )

    loaded = cc.load_family_candidates("F01", candidates_dir=cdir, verify_sha=True)
    _check(loaded["primary_count"] == 18 and loaded["total_count"] == 58, f"Counts mismatch: {loaded}")
    _check(loaded["discovery_years"] == [2018, 2019, 2020], "discovery_years mismatch")
    _check(loaded["holdout_rows_analysed"] == 0 and loaded["order_send_count"] == 0, "Safety fields mismatch")

    # Tamper detection for --resume safety
    raw = json.loads(saved_path.read_text(encoding="utf-8"))
    raw["primary_candidates"][0]["cluster_a_net_R"] = 999.0
    saved_path.write_text(json.dumps(raw), encoding="utf-8")
    _check(not cc.has_valid_family_checkpoint("F01", candidates_dir=cdir), "Tampered checkpoint should fail validation")
    with pytest.raises(ValueError, match="CHECKPOINT_SHA256_DRIFT"):
        cc.load_family_candidates("F01", candidates_dir=cdir, verify_sha=True)

    # Enforce primary_cap <= 18 for F01
    too_many_prim = [{"candidate_id": f"F01_P{i:02d}", "tier": "PRIMARY"} for i in range(19)]
    with pytest.raises(ValueError, match="PRIMARY_CAP_EXCEEDED"):
        cc.save_family_candidates("F01", too_many_prim, meta, candidates_dir=cdir)

    # Enforce total <= 100
    too_many_tot = [{"candidate_id": f"F01_E{i:03d}", "tier": "EXPLORATORY"} for i in range(101)]
    with pytest.raises(ValueError, match="EXPLORATORY_CAP_EXCEEDED"):
        cc.save_family_candidates("F01", too_many_tot, meta, candidates_dir=cdir)

    # Enforce ZERO Cluster B data in Stage 2 discovery checkpoints!
    with pytest.raises(ValueError, match="CLUSTER_B_LEAK_BLOCKED"):
        cc.save_family_candidates("F01", prim[:2], {"discovery_years": [2018, 2019, 2020, 2021]}, candidates_dir=cdir)

    leaked_cand = [{"candidate_id": "F01_LEAK", "tier": "PRIMARY", "cluster_b_sharpe": 1.5}]
    with pytest.raises(ValueError, match="CLUSTER_B_LEAK_BLOCKED"):
        cc.save_family_candidates("F01", leaked_cand, meta, candidates_dir=cdir)

    leaked_date = [{"candidate_id": "F01_DATE_LEAK", "tier": "PRIMARY", "max_date": "2022-06-01"}]
    with pytest.raises(ValueError, match="CLUSTER_B_LEAK_BLOCKED"):
        cc.save_family_candidates("F01", leaked_date, meta, candidates_dir=cdir)
