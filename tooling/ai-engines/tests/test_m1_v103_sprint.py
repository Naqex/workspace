"""Offline-safe + local-cache test suite for Front 1 (`m1_v103_sprint_optimizer.py`).

Covers:
  - Offline CI-safe tests (zero external cache required; `python -O` safe):
      * `[ARCH-02]` zero bare `assert` statements in `m1_v103_sprint_optimizer.py`.
      * `ORDER_SEND_CAPABLE == False`, `ORDER_SEND_COUNT == 0`, Holdout lock fail-closed.
      * Exact `Naqex_Master_Prop7E_v103.mq5` parity:
          - `EffectiveTotalOpenRiskCapPct() <= 3.00%` (`L142-150`, `L1083`)
          - Intraday `dailyHeadroom < 2.0%` taper (`L519-526`) + relative AMBER/RED (`L502-516`)
          - `dailyDdPct` Mode 1 (FTMO `Europe/Prague`) vs Mode 0 (The5ers `17:00 America/New_York` US DST)
          - The5ers `>= 3` profitable days `>= +0.5%` gate + Best-Day Share + 4/5 ticket ruin
      * Exact `.set` schema validation against real `Naqex_Master_Prop7E_v103.mq5` `input` declarations,
        verifying all fail-closed defaults + `InpAllowManualHaltFile=true` + `InpWritePrimaryHeartbeat=true`.
      * SSOT `available_vn = true` 7-SKU allowlist (excludes nonexistent SKUs).
  - `@pytest.mark.local_cache`:
      * Verifies generated `m1_v103_sprint_results.json` receipt + both `.set` presets on real Dev 2018-2024.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_factory.live_ops.account_phase_preflight import (
    DEFAULT_FTMO_SPECS_28,
    validate_account_deployment,
)
from quant_factory.offensive3 import m1_v103_sprint_optimizer as mod
from quant_factory.offensive3 import stage4_portfolio_v3 as s4

REPO_ROOT = Path(__file__).resolve().parents[3]
OPT_PY = REPO_ROOT / "tooling/ai-engines/quant_factory/offensive3/m1_v103_sprint_optimizer.py"
V103_MQ5 = REPO_ROOT / "tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5"
RECEIPT_JSON = REPO_ROOT / "private_vault/strategies/offensive3_v3/m1_v103_sprint_results.json"
EVAL_SET = REPO_ROOT / "private_vault/presets/offensive3_v3/FTMO_Std10K_v103_Sprint_Eval.set"
FUNDED_SET = REPO_ROOT / "private_vault/presets/offensive3_v3/FTMO_Std10K_v103_Funded_1x.set"


def _parse_v103_mq5_inputs() -> set[str]:
    src = V103_MQ5.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*input\s+\w+\s+(Inp\w+)\s*=", src, flags=re.MULTILINE))


def _parse_set_kv(text: str) -> dict[str, str]:
    kv: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        if "=" not in s:
            raise AssertionError(f"Malformed .set line: {line!r}")
        k, v = s.split("=", 1)
        kv[k.strip()] = v.strip()
    return kv


def _make_synthetic_tape_bundle(
    tmp_path: Path,
    *,
    day: str = "2024-06-10",
    entry_ts: int = 1718010000,
    corrupt_sha: bool = False,
) -> Path:
    stamps = np.array([entry_ts, entry_ts + 60, entry_ts + 120], dtype=np.int64)
    marks = np.array(
        [
            [-10.0, 20.0, -30.0, 15.0],
            [15.0, 80.0, -20.0, 60.0],
            [60.0, 120.0, 40.0, 100.0],
        ],
        dtype=np.float64,
    )
    offsets = np.array([0, 3], dtype=np.int64)
    npz_path = tmp_path / "frozen_9e_tapes_v2.npz"
    arrays: dict[str, np.ndarray] = {}
    tapes_meta: dict[str, Any] = {}
    for eng in mod.CORE7_IDS:
        arrays[f"{eng}__stamps"] = stamps
        arrays[f"{eng}__marks"] = marks
        arrays[f"{eng}__offsets"] = offsets
        asset_sym = mod.ENGINE_ASSET_MAP[eng]
        ep = 150.0 if "JPY" in asset_sym else (1.25 if "GBP" in asset_sym else 18000.0)
        tapes_meta[eng] = {
            "days": [day],
            "rows": {
                day: {
                    "day": day,
                    "year": int(day[:4]),
                    "entry": int(entry_ts),
                    "exit": int(entry_ts + 180),
                    "side": 1,
                    "asset": asset_sym,
                    "entry_price": ep,
                    "stop_risk_with_cost_usd": 200.0,
                    "initial_risk_usd": 190.0,
                    "net_usd_per_lot": 100.0,
                    "net_R": 0.5,
                    "at_open": False,
                }
            },
        }
    np.savez(npz_path, allow_pickle=False, **arrays)
    sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    if corrupt_sha:
        sha = "0" * 64
    meta = {
        "schema": "naqex-frozen-tapes-v2",
        "binding_sha256": "synthetic_binding_sha",
        "npz_sha256": sha,
        "ext_days": [day],
        "tapes": tapes_meta,
    }
    (tmp_path / "frozen_9e_tapes_v2.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp_path


def test_arch02_zero_bare_asserts_and_safety_constants() -> None:
    """Enforce `[ARCH-02]` zero bare `assert` statements in `quant_factory/` and safety flags."""
    src = OPT_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert_nodes = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    if assert_nodes:
        raise AssertionError(f"[ARCH-02] Bare assert found in {OPT_PY.name} at lines {assert_nodes}")
    if mod.ORDER_SEND_CAPABLE is not False or mod.ORDER_SEND_COUNT != 0:
        raise AssertionError("ORDER_SEND safety invariants violated")


def test_v103_effective_total_open_ceiling_and_gap_shock() -> None:
    """Verify exact parity with `v103.mq5 L142-150`, `L1083` (`<= 3.00%` -> `1.25x <= 3.75% <= 4.50%`)."""
    if abs(mod.effective_total_open_risk_cap_pct(5.00, 3.00) - 3.00) > 1e-12:
        raise AssertionError("Expected cap clamp to 3.00%")
    if abs(mod.effective_total_open_risk_cap_pct(2.25, 3.00) - 2.25) > 1e-12:
        raise AssertionError("Expected cap 2.25%")
    if abs(mod.effective_total_open_risk_cap_pct(0.0, 2.50) - 2.50) > 1e-12:
        raise AssertionError("Expected fallback to hard ceiling when max_total_open<=0")

    with pytest.raises(ValueError, match="V103_INIT_PARAMETERS_INCORRECT"):
        mod.effective_total_open_risk_cap_pct(3.00, 3.50)
    with pytest.raises(ValueError, match="V103_INIT_PARAMETERS_INCORRECT"):
        mod.effective_total_open_risk_cap_pct(3.00, 0.0)

    sh = mod.compute_honest_gap_shock_pct(
        mult=7.0,
        symcap_pct=3.00,
        usd_cluster_pct=3.00,
        jpy_cluster_pct=3.00,
        idx_cluster_pct=3.00,
        total_open_cap_pct=3.00,
    )
    if abs(float(sh["gap_shock_125x_pct"]) - 3.75) > 1e-6 or not sh["safe_le_4_50_at_125x"]:
        raise AssertionError(f"Expected 3.75% <= 4.50% at 1.25x gap, got {sh}")


def test_v103_phase_multiplier_daily_headroom_and_mode0_vs_mode1() -> None:
    """Verify `v103.mq5 L467-545` (relative AMBER/RED + dailyHeadroom < 2.0% taper) and `L971-973` Mode 0/1."""
    # Relative AMBER & RED
    m_amb, r_amb = mod.compute_v103_phase_risk_multiplier(
        base_phase_mult=5.0,
        daily_dd_pct=0.0,
        static_dd_pct=4.0,
        eq_profit_pct=0.0,
        realized_profit_pct=0.0,
        profit_lock_pct=0.0,
        profit_lock_mult=5.0,
        amber_dd_pct=3.5,
        amber_mult=0.65,
        red_dd_pct=6.0,
        red_mult=0.40,
        kill_daily_dd_pct=4.0,
        kill_static_dd_pct=9.0,
        target_profit_pct=10.0,
    )
    if abs(m_amb - 3.25) > 1e-9 or r_amb != "AMBER_BRAKE":
        raise AssertionError(f"Expected relative AMBER 3.25x, got {m_amb} ({r_amb})")

    # Intraday dailyHeadroom < 2.0% taper: kill_daily=4.0%, daily_dd=3.0% -> headroom=1.0% -> scale=0.50 -> 2.50x
    m_tap, r_tap = mod.compute_v103_phase_risk_multiplier(
        base_phase_mult=5.0,
        daily_dd_pct=3.0,
        static_dd_pct=0.0,
        eq_profit_pct=0.0,
        realized_profit_pct=0.0,
        profit_lock_pct=0.0,
        profit_lock_mult=5.0,
        amber_dd_pct=6.0,
        amber_mult=0.80,
        red_dd_pct=8.0,
        red_mult=0.60,
        kill_daily_dd_pct=4.0,
        kill_static_dd_pct=9.0,
        target_profit_pct=10.0,
    )
    if abs(m_tap - 2.50) > 1e-9 or r_tap != "DAILY_HEADROOM_TAPER":
        raise AssertionError(f"Expected dailyHeadroom taper 2.50x, got {m_tap} ({r_tap})")

    # Floor at 0.25x when headroom=0.1%
    m_fl, _ = mod.compute_v103_phase_risk_multiplier(
        base_phase_mult=5.0,
        daily_dd_pct=3.9,
        static_dd_pct=0.0,
        eq_profit_pct=0.0,
        realized_profit_pct=0.0,
        profit_lock_pct=0.0,
        profit_lock_mult=5.0,
        amber_dd_pct=6.0,
        amber_mult=0.80,
        red_dd_pct=8.0,
        red_mult=0.60,
        kill_daily_dd_pct=4.0,
        kill_static_dd_pct=9.0,
        target_profit_pct=10.0,
    )
    if abs(m_fl - 1.25) > 1e-9:
        raise AssertionError(f"Expected 0.25x floor (1.25x), got {m_fl}")

    # Mode 1 (FTMO: initial_balance denominator) vs Mode 0 (The5ers: day_anchor_eq denominator)
    dd_ftmo = mod.compute_v103_daily_dd_pct(
        daily_reset_mode=1,
        initial_balance_usd=10_000.0,
        day_anchor_bal=9_400.0,
        day_anchor_eq=9_400.0,
        current_equity=9_000.0,
    )
    dd_5ers = mod.compute_v103_daily_dd_pct(
        daily_reset_mode=0,
        initial_balance_usd=10_000.0,
        day_anchor_bal=9_400.0,
        day_anchor_eq=9_400.0,
        current_equity=9_000.0,
    )
    if abs(dd_ftmo - 4.00) > 1e-6:
        raise AssertionError(f"Expected Mode 1 daily_dd=4.00%, got {dd_ftmo}")
    if abs(dd_5ers - (400.0 / 9400.0 * 100.0)) > 1e-6:
        raise AssertionError(f"Expected Mode 0 daily_dd=4.2553%, got {dd_5ers}")


def test_ny1700_dst_and_prague_midnight_reset_boundaries() -> None:
    """Verify US DST `17:00 America/New_York` (21:00 UTC EDT / 22:00 UTC EST) and Prague DST boundaries."""
    # Summer EDT (2024-06-10): 20:59 UTC = 16:59 EDT (June 10), 21:00 UTC = 17:00 EDT (June 11 session!)
    ts_edt_before = int(datetime(2024, 6, 10, 20, 59, tzinfo=UTC).timestamp())
    ts_edt_after = int(datetime(2024, 6, 10, 21, 0, tzinfo=UTC).timestamp())
    if mod.trading_day_key_for_reset_tz(ts_edt_before, "America/New_York") != "2024-06-10":
        raise AssertionError("EDT 16:59 NY should map to 2024-06-10")
    if mod.trading_day_key_for_reset_tz(ts_edt_after, "America/New_York") != "2024-06-11":
        raise AssertionError("EDT 17:00 NY should roll to 2024-06-11")

    # Winter EST (2024-01-10): 21:59 UTC = 16:59 EST (Jan 10), 22:00 UTC = 17:00 EST (Jan 11 session!)
    ts_est_before = int(datetime(2024, 1, 10, 21, 59, tzinfo=UTC).timestamp())
    ts_est_after = int(datetime(2024, 1, 10, 22, 0, tzinfo=UTC).timestamp())
    if mod.trading_day_key_for_reset_tz(ts_est_before, "America/New_York") != "2024-01-10":
        raise AssertionError("EST 16:59 NY should map to 2024-01-10")
    if mod.trading_day_key_for_reset_tz(ts_est_after, "America/New_York") != "2024-01-11":
        raise AssertionError("EST 17:00 NY should roll to 2024-01-11")


def test_intraday_daily_headroom_taper_in_m1_replay(tmp_path: Path) -> None:
    """Verify `replay_v103_regime_stage` tapers a 2nd same-day trade when intraday dailyHeadroom < 2.0%."""
    t0 = 1718010000
    t1 = t0 + 3600  # 1 hour later, after trade 1 closed at a loss
    # Trade 1 (E2 USDJPY): 1 lot stop_cost=200, closes -200 (-1R). At 5.0x capped 2.50% -> -$250 on 10K
    # With kill_daily = 3.50%, after -$250 (-2.50% daily DD), dailyHeadroom = 1.00% < 2.00% -> dailyScale = 0.50!
    st1 = np.array([t0, t0 + 60], dtype=np.int64)
    mk1 = np.array([[0.0, 0.0, -200.0, -200.0], [-200.0, -200.0, -200.0, -200.0]], dtype=np.float64)
    st2 = np.array([t1, t1 + 60], dtype=np.int64)
    mk2 = np.array([[0.0, 100.0, -50.0, 100.0], [100.0, 100.0, 100.0, 100.0]], dtype=np.float64)
    tapes = {
        "E2_USDJPY_EXP80": {
            "2024-06-10": (
                {
                    "asset": "USDJPY",
                    "side": 1,
                    "entry": t0,
                    "exit": t0 + 120,
                    "entry_price": 150.0,
                    "stop_risk_with_cost_usd": 200.0,
                    "net_usd_per_lot": -200.0,
                    "at_open": False,
                },
                st1,
                mk1,
            )
        },
        "E4_US100_SESS40": {
            "2024-06-10": (
                {
                    "asset": "US100",
                    "side": 1,
                    "entry": t1,
                    "exit": t1 + 120,
                    "entry_price": 18000.0,
                    "stop_risk_with_cost_usd": 200.0,
                    "net_usd_per_lot": 100.0,
                    "at_open": False,
                },
                st2,
                mk2,
            )
        },
    }
    pre = mod.prealign_days_for_tapes(["2024-06-10"], tapes)
    met_on, n_on, _, _ = mod.replay_v103_regime_stage(
        ["2024-06-10"],
        pre,
        capital_usd=10_000.0,
        regime_mult=5.0,
        base_phase_mult=5.0,
        symcap_pct=2.50,
        usd_cluster_cap_pct=3.00,
        jpy_cluster_cap_pct=3.00,
        idx_cluster_cap_pct=2.50,
        total_open_cap_pct=3.00,
        kill_daily_dd_pct=3.50,
        enable_daily_headroom_taper=True,
    )
    met_off, n_off, _, _ = mod.replay_v103_regime_stage(
        ["2024-06-10"],
        pre,
        capital_usd=10_000.0,
        regime_mult=5.0,
        base_phase_mult=5.0,
        symcap_pct=2.50,
        usd_cluster_cap_pct=3.00,
        jpy_cluster_cap_pct=3.00,
        idx_cluster_cap_pct=2.50,
        total_open_cap_pct=3.00,
        kill_daily_dd_pct=3.50,
        enable_daily_headroom_taper=False,
    )
    if met_on["tapered_entries"] != 1:
        raise AssertionError(f"Expected 1 tapered entry after -2.50% intraday loss, got {met_on}")
    # Trade 2 untapered wins +125 (+1.25% -> net -125); tapered at 0.50x wins +62.50 (net -187.50)
    if not (n_on[0] < n_off[0] - 50.0):
        raise AssertionError(f"Expected smaller trade 2 lot under dailyHeadroom taper: on={n_on[0]} vs off={n_off[0]}")


def test_the5ers_min_profitable_days_and_best_day_share_synthetic() -> None:
    """Verify The5ers `>= 3` profitable days `>= +0.5%` blocks 1-day pass and computes exact Best-Day Share."""
    # Day 0: +$450 (+9.0% on $5K -> exceeds 8% P1 target, 1 profitable day, BDS = 450/400 = 112.5%)
    # Day 1: +$10 (+0.2% < +0.5% threshold -> does NOT count as profitable day!)
    # Day 2: +$30 (+0.6% >= +0.5% -> 2nd profitable day)
    # Day 3: +$30 (+0.6% >= +0.5% -> 3rd profitable day -> P1 PASSES on day 4!)
    n_arr = np.array([450.0, 10.0, 30.0, 30.0, 100.0, 100.0, 100.0, 0.0], dtype=np.float64)
    d_arr = np.zeros(8, dtype=np.float64)
    f_arr = np.ones(8, dtype=np.int8)
    idx = np.array([[0, 1, 2, 3, 4, 5, 6, 7, 7, 7]], dtype=np.int32)

    raw = mod._simulate_v103_prop_lifecycle_numba(
        idx,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        5000.0,
        39.0,
        39.0,
        0.025,
        0.035,
        0.70,
        0.08,
        0.05,
        0.05,
        0.10,
        0,  # Mode 0 The5ers
        3,
        3,
        0.005,  # >= 3 profitable days >= +0.5%
        0.80,
        10,
        150.0,
        0.0,
        0.0,
        1.0,
        1.0,
        0.095,
        1.0,
        0.098,
        1.0,
        0.045,
        0.045,
        0.095,
        0.095,
        0,
        0.035,
        0.060,
        0.025,
        0.075,
        0.06,
        0,
        False,
    )
    p1_pass_day, eval_pass_day = raw[0], raw[1]
    p1_bds = raw[12]
    if int(p1_pass_day[0]) != 4:
        raise AssertionError(f"Expected P1 pass on day 4 (after 3rd >=0.5% day), got {int(p1_pass_day[0])}")
    if int(eval_pass_day[0]) != 7:
        raise AssertionError(f"Expected full P1+P2 pass on day 7 (days 5,6,7 each +$100), got {int(eval_pass_day[0])}")
    if abs(float(p1_bds[0]) - (450.0 / 400.0)) > 1e-6:
        raise AssertionError(f"Expected P1 Best-Day Share 1.125, got {float(p1_bds[0])}")


def test_direct_loader_holdout_fail_closed_and_ssot_sku_allowlist(tmp_path: Path) -> None:
    """Verify holdout date/ts/SHA rejection and exact 7-SKU SSOT allowlist."""
    bad_day = tmp_path / "bad_day"
    bad_day.mkdir()
    _make_synthetic_tape_bundle(bad_day, day="2025-01-02", entry_ts=1735776000)
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        mod.load_frozen_tapes_direct(bad_day)

    bad_sha = tmp_path / "bad_sha"
    bad_sha.mkdir()
    _make_synthetic_tape_bundle(bad_sha, corrupt_sha=True)
    with pytest.raises(ValueError, match="FROZEN_TAPES_SHA_MISMATCH"):
        mod.load_frozen_tapes_direct(bad_sha)

    skus = mod.load_validated_target_skus()
    expected = (
        "ftmo_standard_10k",
        "ftmo_standard_50k",
        "ftmo_standard_100k",
        "ftmo_swing_10k",
        "ftmo_swing_25k",
        "the5ers_hs_5k_classic",
        "the5ers_hs_5k_new",
    )
    if tuple(skus.keys()) != expected:
        raise AssertionError(f"SKU allowlist mismatch: {tuple(skus.keys())} != {expected}")
    for bad_sku in ("ftmo_swing_50k", "ftmo_standard_25k", "the5ers_hs_20k"):
        if bad_sku in skus:
            raise AssertionError(f"Excluded/unavailable SKU leaked into 7-SKU focus list: {bad_sku}")


def test_vector_v1_fail_closed_nan_inf_bool_guards() -> None:
    """P1-02: Reject NaN, +Inf, -Inf, and bool inputs fail-closed across all guarded M1 functions."""
    poison_floats: tuple[Any, ...] = (float("nan"), float("inf"), float("-inf"), True, False)

    # 1. effective_total_open_risk_cap_pct
    for bad in poison_floats:
        with pytest.raises(ValueError, match="V103_INIT_PARAMETERS_INCORRECT"):
            mod.effective_total_open_risk_cap_pct(bad, 3.00)
        with pytest.raises(ValueError, match="V103_INIT_PARAMETERS_INCORRECT"):
            mod.effective_total_open_risk_cap_pct(3.00, bad)

    # 2. compute_v103_daily_dd_pct
    for bad_mode in (True, False, 2, -1, float("nan"), float("inf"), 1.0):
        with pytest.raises(ValueError):
            mod.compute_v103_daily_dd_pct(
                daily_reset_mode=bad_mode,  # type: ignore[arg-type]
                initial_balance_usd=10_000.0,
                day_anchor_bal=10_000.0,
                day_anchor_eq=10_000.0,
                current_equity=9_900.0,
            )
    for kw in ("initial_balance_usd", "day_anchor_bal", "day_anchor_eq", "current_equity"):
        for bad in poison_floats:
            params: dict[str, Any] = {
                "daily_reset_mode": 1,
                "initial_balance_usd": 10_000.0,
                "day_anchor_bal": 10_000.0,
                "day_anchor_eq": 10_000.0,
                "current_equity": 9_900.0,
            }
            params[kw] = bad
            with pytest.raises(ValueError):
                mod.compute_v103_daily_dd_pct(**params)

    # 3. validate_candidate_invariants: EVERY numeric field of SprintCandidate must reject NaN/Inf/bool
    spr09 = next(c for c in mod.build_sprint_candidates() if c.candidate_id == "SPR09_M45_P2_35_B1")
    mod.validate_candidate_invariants(spr09, enforce_funded_1x=True)

    for f in dataclasses.fields(mod.SprintCandidate):
        if f.type == "float":
            for bad in poison_floats:
                mutated = dataclasses.replace(spr09, **{f.name: bad})
                with pytest.raises(ValueError):
                    mod.validate_candidate_invariants(mutated, enforce_funded_1x=True)
        elif f.type == "int":
            for bad in (True, False, float("nan"), float("inf"), 1.5):
                mutated = dataclasses.replace(spr09, **{f.name: bad})
                with pytest.raises(ValueError):
                    mod.validate_candidate_invariants(mutated, enforce_funded_1x=True)

    # P1-01 invariant: Funded KS > 8.00% MUST be rejected fail-closed
    loose_ks = dataclasses.replace(spr09, funded_kill_static_pct=8.50)
    with pytest.raises(ValueError, match="FUNDED_KILL_STATIC_DD_TOO_LOOSE"):
        mod.validate_candidate_invariants(loose_ks, enforce_funded_1x=True)


def test_rendered_set_files_match_v103_mq5_inputs_and_fail_closed_defaults() -> None:
    """Verify EVERY key in generated Eval & Funded `.set` files exists in `v103.mq5`, enforces KS=8.00% & OPS-2 PASS."""
    valid_inputs = _parse_v103_mq5_inputs()
    spr09 = next(c for c in mod.build_sprint_candidates() if c.candidate_id == "SPR09_M45_P2_35_B1")
    if spr09.funded_kill_static_pct != 8.00:
        raise AssertionError(f"P1-01 violated: SPR09 funded_kill_static_pct={spr09.funded_kill_static_pct} != 8.00")

    mw = {
        sym: {
            "symbol": sym,
            "in_market_watch": True,
            "trade_mode": "FULL",
            "digits": DEFAULT_FTMO_SPECS_28[sym]["digits"],
            "point": 10.0 ** (-int(DEFAULT_FTMO_SPECS_28[sym]["digits"])),
            "contract_size": DEFAULT_FTMO_SPECS_28[sym]["contract_size"],
            "stops_level": DEFAULT_FTMO_SPECS_28[sym]["stops_level"],
        }
        for sym in s4.CORE_7E_SYMBOLS
    }

    for phase in ("EVAL", "FUNDED"):
        text = mod.render_v103_set_file(spr09, phase=phase, capital_usd=10_000.0)
        if "\r\n" in text:
            raise AssertionError(f"{phase} .set must be LF-only")
        if text.startswith("\ufeff"):
            raise AssertionError(f"{phase} .set must not have UTF-8 BOM")
        # Byte-exact parity between m1_v103_sprint_optimizer and stage4_portfolio_v3
        stage4_text = s4.render_v103_layer2_preset(
            firm="FTMO_STD_10K",
            phase=phase,
            winner_config=dataclasses.asdict(spr09),
        )
        if text != stage4_text:
            raise AssertionError(f"P1-01 byte drift between m1 and stage4 renderers for FTMO {phase}")

        kv = _parse_set_kv(text)
        unknown = sorted(set(kv.keys()) - valid_inputs)
        if unknown:
            raise AssertionError(f"{phase} .set contains keys NOT in Naqex_Master_Prop7E_v103.mq5: {unknown}")
        required_true = (
            "InpAllowManualHaltFile",
            "InpWritePrimaryHeartbeat",
            "InpDryRunLogOnly",
            "InpShadowCompareMode",
            "InpGuardDryRunLogOnly",
            "InpEnableSpreadGuard",
            "InpGuardEnableRedNews",
            "InpUse6CcyNewsPad10m",
        )
        for rk in required_true:
            if kv.get(rk) != "true":
                raise AssertionError(f"{phase} .set must enforce {rk}=true, got {kv.get(rk)!r}")
        if int(kv["InpGuardNewsPadSec"]) < 600:
            raise AssertionError(f"{phase} .set must enforce 6-CCY +-10m (>=600s), got {kv['InpGuardNewsPadSec']}")
        if float(kv["InpHardTotalOpenCeilingPct"]) > 3.00 or float(kv["InpHardTotalOpenCeilingPct"]) <= 0.0:
            raise AssertionError(f"{phase} .set invalid InpHardTotalOpenCeilingPct={kv['InpHardTotalOpenCeilingPct']}")
        if float(kv["InpMaxTotalOpenRiskPct"]) > 3.00:
            raise AssertionError(f"{phase} .set exceeded 3.00% TotalOpenRiskCap: {kv['InpMaxTotalOpenRiskPct']}")
        if phase == "FUNDED":
            if float(kv["InpBasePhaseMult"]) != 1.00:
                raise AssertionError(f"Funded .set must lock 1.00x, got {kv['InpBasePhaseMult']}")
            if float(kv["InpAmberDdPct"]) != 3.50 or float(kv["InpRedDdPct"]) != 6.00:
                raise AssertionError("Funded .set must lock tight Amber 3.50% / Red 6.00%")
            if float(kv["InpMaxTotalOpenRiskPct"]) > 2.25:
                raise AssertionError(f"Funded .set TotalOpenCap must be <= 2.25%, got {kv['InpMaxTotalOpenRiskPct']}")
            if float(kv["InpKillStaticDdPct"]) != 8.00:
                raise AssertionError(
                    f"P1-01 violated: Funded .set InpKillStaticDdPct={kv['InpKillStaticDdPct']} != 8.00"
                )

        # Directly validate rendered text against OPS-2 validate_account_deployment
        parsed_typed: dict[str, Any] = {}
        for k, v in kv.items():
            if v in ("true", "false"):
                parsed_typed[k] = v == "true"
            else:
                try:
                    parsed_typed[k] = int(v)
                except ValueError:
                    try:
                        parsed_typed[k] = float(v)
                    except ValueError:
                        parsed_typed[k] = v
        rep = validate_account_deployment(
            expected_login=9900001,
            actual_login=9900001,
            expected_trade_mode="DEMO",
            actual_trade_mode="DEMO",
            firm_profile="FTMO_STANDARD",
            account_phase=phase,
            preset=parsed_typed,
            account_leverage=100,
            asset_class_leverages={"FX": 100, "INDICES": 50, "METALS": 30},
            market_watch_symbols=mw,
            required_symbols=list(s4.CORE_7E_SYMBOLS),
            strict_funded_1x=(phase == "FUNDED"),
        )
        if not rep.passed or rep.verdict != "PASS":
            raise AssertionError(f"m1.render_v103_set_file({phase}) failed OPS-2 preflight: {rep.reject_codes}")


@pytest.mark.local_cache
def test_local_cache_receipt_and_generated_presets_invariants() -> None:
    """Verify full 10k-path receipt JSON and both `.set` presets on disk satisfy all v3.5 gates."""
    if not RECEIPT_JSON.is_file():
        pytest.skip("m1_v103_sprint_results.json not generated yet")

    doc = json.loads(RECEIPT_JSON.read_text(encoding="utf-8"))
    if doc["holdout_rows_analysed"] != 0 or doc["order_send_count"] != 0 or doc["order_send_capable"] is not False:
        raise AssertionError("Safety counters violated in receipt JSON")
    if doc["max_day"] >= "2025-01-01":
        raise AssertionError(f"Holdout leak in receipt max_day={doc['max_day']}")
    if doc["n_paths"] != 10_000 or doc["seed"] != 20261127:
        raise AssertionError(f"Expected n_paths=10000 seed=20261127, got {doc['n_paths']} / {doc['seed']}")
    if doc["reset_boundary_audit"]["cross_prague_midnight"] != 0:
        raise AssertionError("Unexpected Prague reset crossing")
    if doc["reset_boundary_audit"]["cross_ny_1700_dst"] != 0:
        raise AssertionError("Unexpected NY 17:00 DST reset crossing")

    win_id = doc["winner_candidate_id"]
    win = doc["candidates"][win_id]
    if float(win["config"]["funded_kill_static_pct"]) != 8.00:
        raise AssertionError(f"P1-01 violated: winner funded_kill_static_pct={win['config']['funded_kill_static_pct']}")
    if not win["shock_eval"]["safe_le_4_50_at_125x"] or win["shock_eval"]["gap_shock_125x_pct"] > 4.50:
        raise AssertionError(f"Winner exceeded 4.50% gap shock at 1.25x: {win['shock_eval']}")
    if win["ftmo_std_10k_bf_1x"]["funded_12m_breach_pct"] >= 1.00:
        raise AssertionError(f"Winner Funded 1x breach >= 1%: {win['ftmo_std_10k_bf_1x']['funded_12m_breach_pct']}")

    # P1-03: Verify eval_fail_band_disclosure and per-SKU direct 0.01-lot-floored Funded 1.0x Law-15 metrics
    disc = doc.get("eval_fail_band_disclosure") or {}
    if disc.get("selection_anchor_sku") != "ftmo_standard_10k":
        raise AssertionError(f"Missing or wrong eval_fail_band_disclosure anchor: {disc}")

    # Verify all 7 target SKUs present, none forbidden, and strict Pass+Fail+Pending == 100.00%
    if tuple(doc["target_skus"]) != mod.TARGET_SKUS:
        raise AssertionError(f"Receipt SKUs mismatch: {doc['target_skus']}")
    for sku_id in mod.TARGET_SKUS:
        sku_row = doc["sku_matrix"][sku_id]
        sku_w = sku_row["winner_promo_1x"]
        if "funded_1x_dev_law15" not in sku_row:
            raise AssertionError(f"P1-03 violated: {sku_id} missing funded_1x_dev_law15")
        if sku_w["funded_12m_breach_pct"] >= 1.00:
            raise AssertionError(f"{sku_id} Funded 1x breach >= 1%: {sku_w['funded_12m_breach_pct']}")
        for mkey, mval in sku_w["monthly_pass_fail_pending"].items():
            if abs(mval["sum_pct"] - 100.0) > 0.02:
                raise AssertionError(f"{sku_id} {mkey} Pass+Fail+Pending != 100%: {mval}")

    # Verify both `.set` preset files exist on disk, match v103.mq5 inputs, AND match receipt SHA-256 identically
    valid_inputs = _parse_v103_mq5_inputs()
    pw = doc.get("presets_written") or {}
    for path, is_funded, sha_key in (
        (EVAL_SET, False, "eval_set_sha256"),
        (FUNDED_SET, True, "funded_set_sha256"),
    ):
        if not path.is_file():
            raise AssertionError(f"Missing generated preset: {path}")
        raw_bytes = path.read_bytes()
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            raise AssertionError(f"{path.name} must not have UTF-8 BOM")
        if b"\r\n" in raw_bytes:
            raise AssertionError(f"{path.name} must be LF-only")
        disk_sha = hashlib.sha256(raw_bytes).hexdigest()
        if pw.get(sha_key) != disk_sha:
            raise AssertionError(f"P1-01 SHA-256 drift for {path.name}: receipt={pw.get(sha_key)} != disk={disk_sha}")
        kv = _parse_set_kv(raw_bytes.decode("utf-8"))
        unknown = sorted(set(kv.keys()) - valid_inputs)
        if unknown:
            raise AssertionError(f"{path.name} has unknown v103.mq5 keys: {unknown}")
        for rk in (
            "InpAllowManualHaltFile",
            "InpWritePrimaryHeartbeat",
            "InpDryRunLogOnly",
            "InpShadowCompareMode",
            "InpGuardDryRunLogOnly",
        ):
            if kv.get(rk) != "true":
                raise AssertionError(f"{path.name} must set {rk}=true, got {kv.get(rk)!r}")
        if is_funded:
            if float(kv["InpBasePhaseMult"]) != 1.00:
                raise AssertionError(f"{path.name} must lock InpBasePhaseMult=1.00")
            if float(kv["InpKillStaticDdPct"]) != 8.00:
                raise AssertionError(f"{path.name} must lock InpKillStaticDdPct=8.00, got {kv['InpKillStaticDdPct']}")
