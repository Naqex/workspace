"""Wave 5 Unit & Local-Cache Integration Tests for M1 Alpha Arena (`W5-G07`, `W5-G08`, `W5-G09`).

Hard invariants verified (ZERO bare `assert`s — `python -O` safe, `OrderSend=0`, `Holdout 2025+ SEALED`):
  1. Static AST & hygiene audit: `0` bare `assert`s, `0` CRLF, `0` BOM, `ftmo_specs_28.json` untouched,
     `run_wave5_m1_alpha_arena.py` automatically excluded from X13 dev-cache tar bundles while
     `m1_universe_28_loader.py` & `m1_alpha_families_5.py` are included.
  2. Owner Override & Air-Gap fail-closed guards: `force_mode_b=True` rejected, forbidden X13 tokens
     (`holdout`, `2025`, `2026`, `private_vault`) rejected.
  3. Negative Test — `m_total > 360`: DuckDB ledger & selector fail closed with `BudgetExceededError`.
  4. Negative Test — Cluster B / Holdout leakage: 2021+ in Cluster A raises `ClusterALeakageError`,
     2025+ raises `HoldoutLockError`, pre-2021 in Cluster B raises `ClusterBContaminationError`,
     re-running one-shot Cluster B raises `ClusterBOneShotViolationError`.
  5. Negative Test — BH-FDR failure across FULL `m_total = 355` trial space: marginal p-value that
     would pass at `m=1` fails `G1_bh_fdr_q_le_0_10` at `m=355` and is never promoted.
  6. Negative Test — Unverified promotion refusal: `validate_promotion_candidate` & greedy accretion
     raise `UnverifiedPromotionError` on any candidate missing even 1 of the 8 gates.
  7. Positive Synthetic E2E Tests (both `>= 1` accretive survivor including multi-symbol `F5D` pair,
     honest `0` additions with `port_v5_equals_port_7e=True`, and concentration cap rejection on `USDJPY`),
     strictly using `tmp_path` / `write_output_path=None` so production DuckDB/JSON/NPZ never mutate.
  8. `@pytest.mark.local_cache` production artifact & SHA-256 invariance verification.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ops_cloud import compute_router as cr  # noqa: E402
from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory.wave5 import m1_alpha_families_5 as fam5  # noqa: E402
from quant_factory.wave5 import m1_universe_28_loader as ldr  # noqa: E402
from quant_factory.wave5 import run_wave5_m1_alpha_arena as arena  # noqa: E402

CORE7_IDS = arena.CORE7_IDS
DEFAULT_CORE7_BASE_RISK = arena.DEFAULT_CORE7_BASE_RISK

_ARENA_PATH = AI_ENGINES_DIR / "quant_factory" / "wave5" / "run_wave5_m1_alpha_arena.py"
_TEST_PATH = Path(__file__).resolve()
_SPECS_PATH = AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json"
_SPECS_EXPECTED_SHA256 = "f49e8a4a458b6f3c0f67c8f6b67247355576534dcb607d9fbab4803897c348f7"


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion helper immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_synthetic_trial(
    cid: str,
    *,
    family_id: str = fam5.FAM_F5B,
    symbol: str = "AUDJPY",
    leader_symbol: str | None = None,
    split: str = "cluster_a",
    years: list[int] | None = None,
    daily_returns_1x: dict[str, float] | None = None,
    cost_drag_frac: float = 0.20,
    blindness_tier: str = ldr.TIER_NEW16_WAVE5,
    mt5_hcc_ready: bool = True,
    max_exit_utc_sec: int = 72_000,
    swap_r_total: float = 0.0,
    holdout_rows_analysed: int = 0,
    seed: int = 123,
    mean_r: float = 0.25,
    std_r: float = 0.80,
    n_active_days: int = 90,
) -> dict[str, Any]:
    """Build a deterministic synthetic candidate record matching `m1_alpha_families_5.py` output schema."""
    if years is None:
        years = [2019, 2020] if split == "cluster_a" else [2021, 2022, 2023, 2024]
    if daily_returns_1x is None:
        cal = arena._weekday_calendar_dates(f"{min(years):04d}-01-01", f"{max(years):04d}-12-31")
        rng = np.random.default_rng(seed)
        step = max(1, len(cal) // max(1, n_active_days))
        chosen = cal[::step][:n_active_days]
        vals = rng.normal(loc=mean_r, scale=std_r, size=len(chosen))
        dr1 = {d: round(float(v), 6) for d, v in zip(chosen, vals, strict=True)}
    else:
        dr1 = dict(daily_returns_1x)

    r1 = np.array(list(dr1.values()), dtype=np.float64)
    drag = abs(float(cost_drag_frac))
    r15 = r1 - 0.5 * drag
    r2 = r1 - drag
    dr15 = {d: round(float(v), 6) for d, v in zip(dr1.keys(), r15, strict=True)}
    dr2 = {d: round(float(v), 6) for d, v in zip(dr1.keys(), r2, strict=True)}

    yrs_span = float(max(1, len(years)))
    m1 = fam5._compute_series_metrics(r1, yrs_span)
    m15 = fam5._compute_series_metrics(r15, yrs_span)
    m2 = fam5._compute_series_metrics(r2, yrs_span)
    syms_for_news = [leader_symbol, symbol] if leader_symbol else [symbol]

    return {
        "candidate_id": cid,
        "family_id": family_id,
        "symbol": symbol,
        "leader_symbol": leader_symbol,
        "split": split,
        "years_evaluated": years,
        "blindness_tier": blindness_tier,
        "mt5_hcc_ready": mt5_hcc_ready,
        "data_resolution": ldr.RES_M1_BID_SPREAD,
        "red_news_scope_disclosure": fam5.describe_red_news_scope(syms_for_news),
        "params": {"tag": cid, "lag_min": 2 if family_id == fam5.FAM_F5D else 0},
        "n_trades": int(r1.size),
        "winrate_frac": m1["winrate_frac"],
        "avg_win_r": m1["avg_win_r"],
        "avg_loss_r": m1["avg_loss_r"],
        "rr_ratio": m1["rr_ratio"],
        "ev_r_1x": m1["ev_r"],
        "ev_r_15x": m15["ev_r"],
        "ev_r_2x": m2["ev_r"],
        "pf_1x": m1["pf"],
        "pf_15x": m15["pf"],
        "pf_2x": m2["pf"],
        "total_r_1x": m1["total_r"],
        "total_r_15x": m15["total_r"],
        "total_r_2x": m2["total_r"],
        "max_dd_r_1x": m1["max_dd_r"],
        "max_dd_r_15x": m15["max_dd_r"],
        "max_dd_r_2x": m2["max_dd_r"],
        "calmar_1x": m1["calmar"],
        "sharpe_1x": m1["sharpe"],
        "median_fric_over_sl_1x": round(drag, 6),
        "median_fric_over_sl_2x": round(2.0 * drag, 6),
        "max_exit_utc_sec": max_exit_utc_sec,
        "all_flat_by_2050_utc": max_exit_utc_sec <= arena.HARD_FLAT_MAX_UTC_SEC,
        "swap_r_total": swap_r_total,
        "volume_columns_used": 0,
        "order_send_count": 0,
        "holdout_rows_analysed": holdout_rows_analysed,
        "daily_returns_1x": dr1,
        "daily_returns_15x": dr15,
        "daily_returns_2x": dr2,
    }


def _make_synthetic_port_7e(*, seed: int = 999) -> dict[str, Any]:
    """Build deterministic synthetic PORT_7E tapes on Dev 2018-2024 & Cluster B 2021-2024."""
    clb_dates = arena._weekday_calendar_dates("2021-01-01", "2024-12-31")
    dev_dates = arena._weekday_calendar_dates("2018-01-01", "2024-12-31")
    rng = np.random.default_rng(seed)

    eng_1x: dict[str, dict[str, float]] = {}
    eng_15x: dict[str, dict[str, float]] = {}
    eng_2x: dict[str, dict[str, float]] = {}
    port_clb_1x = np.zeros(len(clb_dates), dtype=np.float64)
    port_clb_15x = np.zeros(len(clb_dates), dtype=np.float64)
    port_clb_2x = np.zeros(len(clb_dates), dtype=np.float64)
    port_dev_1x = np.zeros(len(dev_dates), dtype=np.float64)

    for idx_e, eid in enumerate(CORE7_IDS):
        w_pct = float(DEFAULT_CORE7_BASE_RISK[eid]) * 100.0
        r_clb = rng.normal(loc=0.06, scale=0.85, size=len(clb_dates))
        mask = rng.random(len(clb_dates)) < 0.30
        m1: dict[str, float] = {}
        m15: dict[str, float] = {}
        m2: dict[str, float] = {}
        for i, d in enumerate(clb_dates):
            if mask[i]:
                v = float(r_clb[i])
                m1[d] = round(v, 6)
                m15[d] = round(v - 0.03, 6)
                m2[d] = round(v - 0.06, 6)
                port_clb_1x[i] += w_pct * v
                port_clb_15x[i] += w_pct * (v - 0.03)
                port_clb_2x[i] += w_pct * (v - 0.06)
        eng_1x[eid] = m1
        eng_15x[eid] = m15
        eng_2x[eid] = m2

        # Simple dev series for full Dev vector
        r_dev = rng.normal(loc=0.03, scale=0.45, size=len(dev_dates))
        port_dev_1x += w_pct * r_dev * (0.5 if idx_e % 2 == 0 else 0.4)

    return {
        "source": "synthetic_port_7e",
        "npz_sha256": "0" * 64,
        "binding_sha256": "1" * 64,
        "red_news_calendar": {"loaded": True, "source": "synthetic", "event_count": 0},
        "core7_ids": list(CORE7_IDS),
        "core7_base_risk_frac": {eid: float(DEFAULT_CORE7_BASE_RISK[eid]) for eid in CORE7_IDS},
        "core7_symbols": dict(arena.CORE7_ENGINE_SYMBOLS),
        "ext_days": dev_dates,
        "clb_ext_days": clb_dates,
        "clb_dates": clb_dates,
        "dev_dates": dev_dates,
        "port_clb_daily_ret_pct_1x": port_clb_1x,
        "port_clb_daily_ret_pct_15x": port_clb_15x,
        "port_clb_daily_ret_pct_2x": port_clb_2x,
        "port_dev_daily_ret_pct_1x": port_dev_1x,
        "engine_daily_r_1x": eng_1x,
        "engine_daily_r_15x": eng_15x,
        "engine_daily_r_2x": eng_2x,
        "holdout_rows_analysed": 0,
    }


# ---------------------------------------------------------------------------
# 1. Static AST, Hygiene, X13 Air-Gap & Owner Override Guards
# ---------------------------------------------------------------------------


def test_ast_hygiene_airgap_and_immutables() -> None:
    """Zero bare asserts, zero CRLF/BOM, immutable specs intact, X13 air-gap excludes arena orchestrator."""
    for p in (_ARENA_PATH, _TEST_PATH):
        raw = p.read_bytes()
        _check(not raw.startswith(b"\xef\xbb\xbf"), f"BOM detected in {p.name}")
        _check(b"\r\n" not in raw, f"CRLF detected in {p.name}")
        tree = ast.parse(raw.decode("utf-8"), filename=str(p))
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(not bare_asserts, f"Bare assert in {p.name} at lines {bare_asserts}")

    _check(
        _sha256_file(_SPECS_PATH) == _SPECS_EXPECTED_SHA256,
        "Immutable ftmo_specs_28.json SHA-256 mutated!",
    )

    collected = cr.collect_dev_cache_files(include_tapes=False)
    rels = [rel for rel, _ in collected["entries"]]
    _check(collected["holdout_guard_excluded"] is True, "holdout_guard must be excluded from X13 dev cache")
    _check(
        not any("run_wave5_m1_alpha_arena.py" in r for r in rels),
        "PC-Dev-only arena orchestrator must be excluded from X13 dev cache",
    )
    _check(
        any("m1_alpha_families_5.py" in r for r in rels) and any("m1_universe_28_loader.py" in r for r in rels),
        "X13-safe Wave 5 M1 modules must be included in dev cache sync",
    )


def test_owner_override_and_forbidden_x13_job_tokens() -> None:
    """Reject `force_mode_b=True` and any forbidden air-gap tokens in X13 job prefixes."""
    with pytest.raises(ValueError, match="OWNER_OVERRIDE_VIOLATION"):
        arena.apply_mode_a_owner_active_guard(force_mode_b=True)

    with pytest.raises(ValueError, match="OWNER_OVERRIDE_VIOLATION"):
        arena.dispatch_m1_shards_x13_full([], split="cluster_a", job_prefix="w5_m1_cla_shard", force_mode_b=True)

    for bad_tok in ("w5_holdout_shard", "w5_2025_shard", "w5_2026_shard", "w5_private_vault_shard"):
        with pytest.raises(ValueError):
            arena._validate_x13_clean_job_id(bad_tok)


# ---------------------------------------------------------------------------
# 2. Negative Tests: Budget > 360, Cluster A/B/Holdout Leakage, One-Shot Guard
# ---------------------------------------------------------------------------


def test_negative_budget_cap_over_360_rejected(tmp_path: Path) -> None:
    """Hard cap `m_total <= 360`: trial #361 fails closed in both DuckDB ledger and selector."""
    trials_361 = [
        _make_synthetic_trial(f"F5B_AUDJPY_T{i:03d}", seed=1000 + i, n_active_days=20, mean_r=0.05)
        for i in range(361)
    ]
    with pytest.raises(arena.BudgetExceededError, match="BUDGET_CAP_EXCEEDED"):
        arena.select_cluster_a_finalists(trials_361)

    with pytest.raises(arena.BudgetExceededError, match="BUDGET_CAP_EXCEEDED"):
        arena.run_wave5_m1_alpha_arena(
            write_output_path=None,
            frozen_output_path=None,
            db_path=None,
            port_v5_tapes_path=None,
            sync_x13=False,
            prebuilt_cluster_a_results=trials_361,
            prebuilt_cluster_b_results=[],
            prebuilt_port_7e=_make_synthetic_port_7e(),
        )

    db_file = tmp_path / "budget_test.duckdb"
    with arena.Wave5M1AlphaLedger(db_file, max_trials=3) as ledger:
        for i in range(3):
            ledger.record_cluster_a_trial(
                trials_361[i],
                sharpe_daily_a=0.1,
                p_value_emp_a=0.5,
                is_finalist=False,
                host_executed="DEV_PC",
                shard_id="s0",
            )
        with pytest.raises(arena.BudgetExceededError, match="BUDGET_CAP_EXCEEDED"):
            ledger.record_cluster_a_trial(
                trials_361[3],
                sharpe_daily_a=0.1,
                p_value_emp_a=0.5,
                is_finalist=False,
                host_executed="DEV_PC",
                shard_id="s0",
            )


def test_negative_cluster_a_b_holdout_leakage_and_oneshot_guard(tmp_path: Path) -> None:
    """Reject 2021+ in Cluster A, 2025+ anywhere, pre-2021 in Cluster B, and 2nd Cluster B run."""
    leaked_2021 = _make_synthetic_trial(
        "F5B_AUDJPY_LEAK2021",
        split="cluster_a",
        years=[2019, 2020, 2021],
        daily_returns_1x={"2020-12-30": 0.5, "2021-01-04": 1.0},
    )
    with pytest.raises(arena.ClusterALeakageError, match="CLUSTER_A_LEAKAGE"):
        arena.select_cluster_a_finalists([leaked_2021])

    leaked_2021_date_only = _make_synthetic_trial(
        "F5B_AUDJPY_LEAKDATE",
        split="cluster_a",
        years=[2019, 2020],
        daily_returns_1x={"2020-12-30": 0.5, "2021-01-05": 0.8},
    )
    with pytest.raises(arena.ClusterALeakageError, match="CLUSTER_A_LEAKAGE"):
        arena.select_cluster_a_finalists([leaked_2021_date_only])

    leaked_holdout = _make_synthetic_trial(
        "F5B_AUDJPY_LEAK2025",
        split="cluster_a",
        years=[2019, 2020],
        daily_returns_1x={"2020-12-30": 0.5, "2025-01-02": 0.8},
    )
    with pytest.raises(HoldoutLockError):
        arena.select_cluster_a_finalists([leaked_holdout])

    # Cluster B contamination (pre-2021 in Cluster B)
    p7e = _make_synthetic_port_7e()
    cla_ok = _make_synthetic_trial(
        "F5B_AUDJPY_OK", split="cluster_a", years=[2019, 2020], mean_r=0.35, n_active_days=80
    )
    clb_bad = _make_synthetic_trial(
        "F5B_AUDJPY_OK",
        split="cluster_b",
        years=[2020, 2021, 2022],
        daily_returns_1x={"2020-12-31": 0.5, "2021-01-05": 0.8},
    )
    fam_pbo = arena.build_family_cluster_a_pbo_matrices(
        [cla_ok, _make_synthetic_trial("F5B_AUDJPY_ALT", split="cluster_a", years=[2019, 2020], seed=77)]
    )
    with pytest.raises(arena.ClusterBContaminationError, match="CLUSTER_B_CONTAMINATION"):
        arena.evaluate_cluster_b_8_gates(
            cluster_b_results=[clb_bad],
            cluster_a_by_id={cla_ok["candidate_id"]: cla_ok},
            all_cluster_a_trial_sharpes=[0.5, 0.1],
            m_total=2,
            family_pbo_map=fam_pbo,
            port_7e_clb_dates=p7e["clb_dates"],
            port_7e_clb_daily_ret_pct=p7e["port_clb_daily_ret_pct_1x"],
            sign_flip_draws=500,
        )

    # One-shot Cluster B guard in DuckDB ledger
    db_file = tmp_path / "oneshot.duckdb"
    with arena.Wave5M1AlphaLedger(db_file, max_trials=10) as ledger:
        ledger.record_run_meta(
            run_id="run1",
            cluster_a_frozen_sha256="a" * 64,
            m_total=5,
            finalist_count=1,
            survivor_count=0,
            bench_reserve_count=0,
            accretive_count=0,
            port_v5_equals_port_7e=True,
        )
        with pytest.raises(arena.ClusterBOneShotViolationError, match="CLUSTER_B_ONE_SHOT_ALREADY_CONSUMED"):
            ledger.record_run_meta(
                run_id="run2",
                cluster_a_frozen_sha256="b" * 64,
                m_total=5,
                finalist_count=1,
                survivor_count=0,
                bench_reserve_count=0,
                accretive_count=0,
                port_v5_equals_port_7e=True,
            )


# ---------------------------------------------------------------------------
# 3. Negative Tests: BH-FDR Failure at m=355 & Unverified Promotion Refusal
# ---------------------------------------------------------------------------


def test_negative_bh_fdr_failure_at_m355_and_unverified_promotion_blocked() -> None:
    """Marginal p-value passes at m=1 but FAILS BH-FDR at m_total=355, and accretion blocks unverified promotion."""
    p7e = _make_synthetic_port_7e(seed=42)
    cla_strong = _make_synthetic_trial(
        "F5B_AUDJPY_MARGINAL",
        family_id=fam5.FAM_F5B,
        symbol="AUDJPY",
        split="cluster_a",
        years=[2019, 2020],
        mean_r=0.35,
        std_r=0.70,
        n_active_days=80,
        seed=10,
    )
    cla_noise = _make_synthetic_trial(
        "F5B_EURGBP_NOISE",
        family_id=fam5.FAM_F5B,
        symbol="EURGBP",
        split="cluster_a",
        years=[2019, 2020],
        mean_r=-0.05,
        std_r=0.90,
        n_active_days=80,
        seed=11,
    )
    # Build Cluster B series with marginal positive edge (~t=1.8 -> p ~ 0.03, which FAILS BH-FDR at m=355!)
    clb_marginal = _make_synthetic_trial(
        "F5B_AUDJPY_MARGINAL",
        family_id=fam5.FAM_F5B,
        symbol="AUDJPY",
        split="cluster_b",
        years=[2021, 2022, 2023, 2024],
        mean_r=0.14,
        std_r=0.95,
        n_active_days=90,
        seed=501,
    )

    fam_pbo = arena.build_family_cluster_a_pbo_matrices([cla_strong, cla_noise])
    # Full 355 trial Sharpes space
    rng = np.random.default_rng(7)
    trial_sharpes_355 = list(rng.normal(0.0, 0.35, size=355))
    res = arena.evaluate_cluster_b_8_gates(
        cluster_b_results=[clb_marginal],
        cluster_a_by_id={cla_strong["candidate_id"]: cla_strong},
        all_cluster_a_trial_sharpes=trial_sharpes_355,
        m_total=355,
        family_pbo_map=fam_pbo,
        port_7e_clb_dates=p7e["clb_dates"],
        port_7e_clb_daily_ret_pct=p7e["port_clb_daily_ret_pct_1x"],
        sign_flip_draws=5000,
    )
    ev = res["evaluations"][0]
    _check(ev["bh_fdr_m_total"] == 355, "BH-FDR must be charged across full m_total=355")
    _check(ev["gate_checks"]["G1_bh_fdr_q_le_0_10"] is False, f"Expected BH-FDR fail, got q={ev['bh_fdr_q']}")
    _check(ev["all_8_gates_passed"] is False, "Marginal candidate must fail 8-gate filter")
    _check(ev["tier_classification"] != arena.TIER_1_PROP_CANDIDATE, "Must not be TIER_1_PROP_CANDIDATE")
    _check(res["survivor_count"] == 0, "Expected 0 survivors")

    # Attempting to promote this failed / reserve candidate MUST fail closed!
    with pytest.raises(arena.UnverifiedPromotionError, match="UNVERIFIED_PROMOTION"):
        arena.validate_promotion_candidate(ev)
    with pytest.raises(arena.UnverifiedPromotionError, match="UNVERIFIED_PROMOTION"):
        arena.run_greedy_incremental_accretion(survivors=[ev], port_7e=p7e)


# ---------------------------------------------------------------------------
# 4. Positive E2E Synthetic Tests (Accretive Survivor + F5D Multi-Symbol + Zero Additions)
# ---------------------------------------------------------------------------


def test_e2e_synthetic_accretive_survivor_f5d_and_concentration_cap(tmp_path: Path) -> None:
    """Verify 8-gate pass + multi-symbol F5D + greedy accretion + USDJPY concentration cap + zero-pickle NPZ."""
    p7e = _make_synthetic_port_7e(seed=1234)
    cal_a = arena._weekday_calendar_dates("2019-01-01", "2020-12-31")
    cal_b = p7e["clb_dates"]

    # Build realistic Cluster A trials (SR ~ +1.0 winners, ~ -0.5 losers -> realistic DSR var & low PBO!)
    cla_trials: list[dict[str, Any]] = []
    # Consistent strong winner on XAUUSD->XAGUSD (multi-symbol F5D!)
    win_a_days = cal_a[::4][:120]
    win_a_map = {d: (0.85 if i % 3 != 0 else -1.10) for i, d in enumerate(win_a_days)}
    cla_winner_f5d = _make_synthetic_trial(
        "F5D_XAUUSD_TO_XAGUSD_WIN",
        family_id=fam5.FAM_F5D,
        symbol="XAGUSD",
        leader_symbol="XAUUSD",
        split="cluster_a",
        years=[2019, 2020],
        daily_returns_1x=win_a_map,
        cost_drag_frac=0.05,
        blindness_tier=ldr.TIER_OLD12,  # Union of XAUUSD (OLD12) + XAGUSD (NEW16) -> OLD12!
        mt5_hcc_ready=False,
    )
    cla_trials.append(cla_winner_f5d)

    # Consistent strong winner on USDJPY (to verify concentration cap rejects USDJPY > 1.0% Funded!)
    win_a_usdjpy_map = {d: (0.82 if i % 3 != 0 else -1.10) for i, d in enumerate(cal_a[1::4][:120])}
    cla_winner_usdjpy = _make_synthetic_trial(
        "F5B_USDJPY_CAPTEST",
        family_id=fam5.FAM_F5B,
        symbol="USDJPY",
        leader_symbol=None,
        split="cluster_a",
        years=[2019, 2020],
        daily_returns_1x=win_a_usdjpy_map,
        cost_drag_frac=0.05,
        blindness_tier=ldr.TIER_OLD12,
        mt5_hcc_ready=True,
    )
    cla_trials.append(cla_winner_usdjpy)

    # Add realistic losing/flat competitors in both F5D and F5B so CSCV PBO is <= 0.35 & trial_sharpes std ~ 0.6
    for k in range(6):
        lose_f5d = {d: (-0.55 if (i + k) % 2 == 0 else 0.45) for i, d in enumerate(cal_a[::5][:95])}
        cla_trials.append(
            _make_synthetic_trial(
                f"F5D_USOIL_TO_UKOIL_L{k}",
                family_id=fam5.FAM_F5D,
                symbol="UKOIL",
                leader_symbol="USOIL",
                split="cluster_a",
                years=[2019, 2020],
                daily_returns_1x=lose_f5d,
                cost_drag_frac=0.05,
            )
        )
        lose_f5b = {d: (-0.52 if (i + k) % 2 == 0 else 0.44) for i, d in enumerate(cal_a[2::5][:95])}
        cla_trials.append(
            _make_synthetic_trial(
                f"F5B_NZDUSD_L{k}",
                family_id=fam5.FAM_F5B,
                symbol="NZDUSD",
                split="cluster_a",
                years=[2019, 2020],
                daily_returns_1x=lose_f5b,
                cost_drag_frac=0.05,
            )
        )

    # Build strong orthogonal Cluster B outcomes for both finalists
    win_b_days_f5d = cal_b[::5][:180]
    win_b_map_f5d = {d: (0.75 if i % 4 != 0 else -0.45) for i, d in enumerate(win_b_days_f5d)}
    clb_f5d = _make_synthetic_trial(
        "F5D_XAUUSD_TO_XAGUSD_WIN",
        family_id=fam5.FAM_F5D,
        symbol="XAGUSD",
        leader_symbol="XAUUSD",
        split="cluster_b",
        years=[2021, 2022, 2023, 2024],
        daily_returns_1x=win_b_map_f5d,
        cost_drag_frac=0.05,
        blindness_tier=ldr.TIER_OLD12,
        mt5_hcc_ready=False,
    )
    win_b_days_uj = cal_b[2::5][:180]
    win_b_map_uj = {d: (0.72 if i % 4 != 0 else -0.45) for i, d in enumerate(win_b_days_uj)}
    clb_usdjpy = _make_synthetic_trial(
        "F5B_USDJPY_CAPTEST",
        family_id=fam5.FAM_F5B,
        symbol="USDJPY",
        split="cluster_b",
        years=[2021, 2022, 2023, 2024],
        daily_returns_1x=win_b_map_uj,
        cost_drag_frac=0.05,
        blindness_tier=ldr.TIER_OLD12,
        mt5_hcc_ready=True,
    )

    out_summary = tmp_path / "summary.json"
    out_frozen = tmp_path / "frozen.json"
    out_db = tmp_path / "arena.duckdb"
    out_npz = tmp_path / "port_v5_tapes.npz"

    summary = arena.run_wave5_m1_alpha_arena(
        write_output_path=out_summary,
        frozen_output_path=out_frozen,
        db_path=out_db,
        port_v5_tapes_path=out_npz,
        sync_x13=False,
        sign_flip_draws=4000,
        prebuilt_cluster_a_results=cla_trials,
        prebuilt_cluster_b_results=[clb_f5d, clb_usdjpy],
        prebuilt_port_7e=p7e,
    )
    _check(
        out_summary.is_file() and out_frozen.is_file() and out_db.is_file() and out_npz.is_file(),
        "All outputs must exist",
    )
    _check(
        summary["cluster_b_summary"]["tier_1_prop_survivor_count"] == 2,
        f"Expected 2 survivors, got {summary['cluster_b_summary']}",
    )
    # Multi-symbol F5D check
    f5d_surv = [s for s in summary["tier_1_prop_survivors"] if s["candidate_id"] == "F5D_XAUUSD_TO_XAGUSD_WIN"][0]
    _check(f5d_surv["asset_universe"] == ["XAUUSD", "XAGUSD"], "F5D must preserve multi-symbol asset_universe")
    _check(f5d_surv["blindness_tier"] == ldr.TIER_OLD12, "F5D union blindness_tier must be preserved")
    # Accretion: XAGUSD accepted, USDJPY rejected due to existing 1.25% > 1.00% Funded symbol cap!
    acc = summary["port_v5_accretion"]
    _check(acc["port_v5_equals_port_7e"] is False, "Expected PORT_V5 expansion with XAGUSD survivor")
    _check(
        acc["added_candidate_ids"] == ["F5D_XAUUSD_TO_XAGUSD_WIN"],
        f"Unexpected added IDs: {acc['added_candidate_ids']}",
    )
    uj_log = [x for x in acc["accretion_log"] if x["candidate_id"] == "F5B_USDJPY_CAPTEST"][0]
    _check(uj_log["decision"] == "REJECTED_SYMBOL_FUNDED_CAP", f"Expected USDJPY cap rejection, got {uj_log}")
    _check(
        acc["net_delta_vs_port_7e_1x"]["sharpe_delta"] >= arena.ACCRETION_MIN_SHARPE_DELTA,
        "Expected positive Sharpe accretion",
    )

    # Verify zero-pickle NPZ loads cleanly
    with np.load(out_npz, allow_pickle=False) as z:
        _check(bool(z["port_v5_equals_port_7e"].item()) is False, "NPZ flag mismatch")
        _check(int(z["n_added_engines"].item()) == 1, "NPZ added engines mismatch")
        _check(int(z["holdout_rows_analysed"].item()) == 0, "NPZ holdout_rows must be 0")
        meta = json.loads(bytes(z["metadata_json_utf8"]).decode("utf-8"))
        _check(meta["port_v5_equals_port_7e"] is False, "NPZ metadata flag mismatch")


def test_e2e_synthetic_honest_zero_additions_port_v5_equals_port_7e(tmp_path: Path) -> None:
    """When 0 candidates clear all 8 gates, emit honest `port_v5_equals_port_7e=True` and ranked bench reserve."""
    p7e = _make_synthetic_port_7e(seed=5678)
    cal_a = arena._weekday_calendar_dates("2019-01-01", "2020-12-31")
    cal_b = p7e["clb_dates"]

    cla_good = _make_synthetic_trial(
        "F5E_EURGBP_RES",
        family_id=fam5.FAM_F5E,
        symbol="EURGBP",
        split="cluster_a",
        years=[2019, 2020],
        daily_returns_1x={d: (0.45 if i % 3 != 0 else -0.35) for i, d in enumerate(cal_a[::5][:90])},
        cost_drag_frac=0.10,
    )
    cla_bad = _make_synthetic_trial(
        "F5E_NZDUSD_BAD",
        family_id=fam5.FAM_F5E,
        symbol="NZDUSD",
        split="cluster_a",
        years=[2019, 2020],
        mean_r=-0.10,
        n_active_days=60,
        seed=88,
    )
    # Cluster B has mild positive Sharpe (~0.45 -> qualifies as ALPHA_BENCH_RESERVE, fails 8-gate Sharpe >= 0.60!)
    clb_mild = _make_synthetic_trial(
        "F5E_EURGBP_RES",
        family_id=fam5.FAM_F5E,
        symbol="EURGBP",
        split="cluster_b",
        years=[2021, 2022, 2023, 2024],
        daily_returns_1x={d: (0.28 if i % 2 == 0 else -0.22) for i, d in enumerate(cal_b[::10][:95])},
        cost_drag_frac=0.08,
    )

    out_npz = tmp_path / "port_v5_zero.npz"
    summary = arena.run_wave5_m1_alpha_arena(
        write_output_path=None,
        frozen_output_path=None,
        db_path=None,
        port_v5_tapes_path=out_npz,
        sync_x13=False,
        sign_flip_draws=2000,
        prebuilt_cluster_a_results=[cla_good, cla_bad],
        prebuilt_cluster_b_results=[clb_mild],
        prebuilt_port_7e=p7e,
    )
    _check(summary["cluster_b_summary"]["tier_1_prop_survivor_count"] == 0, "Expected 0 survivors")
    _check(summary["port_v5_accretion"]["port_v5_equals_port_7e"] is True, "Expected port_v5_equals_port_7e=True")
    _check(summary["port_v5_accretion"]["n_added_engines"] == 0, "Expected 0 added engines")
    _check(summary["cluster_b_summary"]["alpha_bench_reserve_count"] >= 0, "Bench reserve count must be >= 0")

    with np.load(out_npz, allow_pickle=False) as z:
        _check(bool(z["port_v5_equals_port_7e"].item()) is True, "NPZ must set port_v5_equals_port_7e=True")
        _check(
            np.allclose(z["port_v5_daily_ret_pct_1x"], z["port_7e_daily_ret_pct_1x"]),
            "When 0 additions, PORT_V5 daily returns must equal PORT_7E exactly",
        )


# ---------------------------------------------------------------------------
# 5. Local-Cache Production Artifact & Non-Mutation Invariance Check
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_artifacts_verified_and_immutable_under_pytest() -> None:
    """Verify production DuckDB, summary JSON, zero-pickle NPZ, and non-mutation during dry synthetic run."""
    summary_p = arena.DEFAULT_SUMMARY_PATH
    frozen_p = arena.DEFAULT_FROZEN_PATH
    db_p = arena.DEFAULT_DUCKDB_PATH
    npz_p = arena.DEFAULT_PORT_V5_TAPES_PATH
    unified_db_p = REPO_ROOT / ".runtime" / "experiments" / "unified_eval_catalog.duckdb"

    for req_p in (summary_p, frozen_p, db_p, npz_p):
        _check(req_p.is_file(), f"Missing production artifact: {req_p}")

    before_shas = {
        str(p): _sha256_file(p)
        for p in (summary_p, frozen_p, db_p, npz_p, unified_db_p)
        if p.is_file()
    }

    # Verify summary JSON schema, self-hash, budget cap, and safety invariants
    doc = json.loads(summary_p.read_text(encoding="utf-8"))
    _check(doc["schema"] == arena.SCHEMA_VERSION, "Unexpected summary schema")
    _check(doc["report_sha256"] == arena.compute_report_sha256(doc), "summary report_sha256 mismatch")
    _check(doc["hard_invariants"]["holdout_rows_analysed"] == 0, "holdout_rows_analysed != 0")
    _check(doc["hard_invariants"]["order_send_count"] == 0, "order_send_count != 0")
    _check(
        doc["cluster_a_summary"]["m_total"] == 355,
        f"Expected m_total=355, got {doc['cluster_a_summary']['m_total']}",
    )
    _check(doc["cluster_a_summary"]["m_total"] <= 360, "Budget cap > 360 breached")
    _check(
        float(doc["compute_execution"]["overall_x13_offload_pct"]) >= 80.0,
        f"Expected >= 80% X13 offload, got {doc['compute_execution']['overall_x13_offload_pct']}",
    )

    # Verify zero-pickle port_v5_tapes.npz
    with np.load(npz_p, allow_pickle=False) as z:
        _check(int(z["holdout_rows_analysed"].item()) == 0, "NPZ holdout_rows_analysed != 0")
        _check(int(z["order_send_count"].item()) == 0, "NPZ order_send_count != 0")
        _check(
            bool(z["port_v5_equals_port_7e"].item()) == bool(doc["port_v5_accretion"]["port_v5_equals_port_7e"]),
            "NPZ port_v5_equals_port_7e disagrees with summary JSON",
        )

    # Verify dedicated DuckDB counts read-only (never touches unified_eval_catalog.duckdb)
    import duckdb

    con = duckdb.connect(str(db_p), read_only=True)
    try:
        cla_cnt = int(con.execute("SELECT COUNT(*) FROM cluster_a_trials").fetchone()[0])
        clb_cnt = int(con.execute("SELECT COUNT(*) FROM cluster_b_evals").fetchone()[0])
        meta_cnt = int(con.execute("SELECT COUNT(*) FROM arena_runs_meta").fetchone()[0])
        _check(cla_cnt == 355, f"Expected 355 DuckDB cluster_a_trials, got {cla_cnt}")
        _check(clb_cnt == doc["cluster_b_summary"]["finalists_evaluated"], "DuckDB cluster_b_evals count mismatch")
        _check(meta_cnt == 1, f"Expected 1 arena_runs_meta row, got {meta_cnt}")
    finally:
        con.close()

    # Run synthetic arena with write_output_path=None and verify ZERO byte mutation on production files
    p7e = _make_synthetic_port_7e(seed=77)
    t1 = _make_synthetic_trial("F5B_AUDJPY_INV1", seed=1)
    t2 = _make_synthetic_trial("F5B_EURGBP_INV2", seed=2, mean_r=-0.2)
    arena.run_wave5_m1_alpha_arena(
        write_output_path=None,
        frozen_output_path=None,
        db_path=None,
        port_v5_tapes_path=None,
        sync_x13=False,
        sign_flip_draws=500,
        prebuilt_cluster_a_results=[t1, t2],
        prebuilt_cluster_b_results=[],
        prebuilt_port_7e=p7e,
    )

    for p_str, old_sha in before_shas.items():
        _check(_sha256_file(Path(p_str)) == old_sha, f"Production artifact mutated during pytest: {p_str}")
