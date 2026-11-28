"""Unit & production-invariance tests for Wave 5 Gate W5-G05 (`baseline_profiles_audit.py`).

Hard invariants verified (ZERO bare asserts, 100% `python -O` safe, `tmp_path`-only writes):
  1. P2-4 Guardrail: `summarize_4phase_lifecycle` rejects `max_retries != 0`, rejects mismatched
     `funded_enter_day != eval_pass_day`, and enforces EXACT `Pass + Fail + Pending == 100.0%`
     across ALL horizons for `p1`, `p2` (conditional on entering P2), and `pass_eval`.
  2. Law 13 Honesty: `cond_med_pay1_cal_days` and `uncond_med_pay1_cal_days_cap730` are strictly
     distinct when failure/pending rate is non-trivial and NEVER conflated.
  3. Mandatory `v1.04-ML` tags: `FEATURE_SKEW_UNFIXED`, `OOF_SUBSET_WINDOW`, and
     `CONSUMED_DEV_CLB_TEMPORAL_OOS` are strictly present on `V104_ML`, paired with
     `V103_OOF_CONTROL`, with ZERO forbidden blind labels.
  4. Full synthetic end-to-end 4-profile x 4-phase run + `UnifiedEvaluationCatalog` registration
     (`runs_catalog` + `mc_cases_catalog` campaign `offensive5_baseline`) inside `tmp_path`
     passes `verify_integrity() == True` with ZERO writes to production `.runtime/`.
  5. `@pytest.mark.local_cache` read-only check verifies production `.runtime/offensive5/audits/`
     baseline report, receipts, and `.runtime/experiments/unified_eval_catalog.duckdb` SHA
     invariance after pytest!
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

from quant_factory.offensive3.m1_v103_sprint_optimizer import (  # noqa: E402
    CALENDAR_DAYS_PER_TRADING_DAY,
    CORE7_IDS,
    ENGINE_ASSET_MAP,
    make_block_bootstrap_indices,
    prealign_days_for_tapes,
)
from quant_factory.wave4.ml_walkforward_cv import CONSUMED_CLB_TAG  # noqa: E402
from quant_factory.wave5 import baseline_profiles_audit as bpa  # noqa: E402
from quant_factory.wave5 import evaluation_catalog as ec  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit guard immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_synthetic_tapes_and_days(n_days: int = 80) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Build deterministic pre-2025 synthetic M1 tapes for fast offline unit tests."""
    # All days strictly inside 2022-01..2022-05 (pre-Holdout)
    from datetime import date, timedelta

    d0 = date(2022, 1, 3)
    days: list[str] = []
    cur = d0
    while len(days) < n_days:
        if cur.weekday() < 5:
            days.append(cur.isoformat())
        cur += timedelta(days=1)

    rng = np.random.default_rng(20261128)
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {e: {} for e in CORE7_IDS}
    base_ts0 = 1_641_168_000  # 2022-01-03T00:00:00Z
    for di, dk in enumerate(days):
        day_base = base_ts0 + di * 86_400
        for ei, eng in enumerate(CORE7_IDS):
            if (di + ei) % 2 != 0:
                continue
            asset = ENGINE_ASSET_MAP[eng]
            entry_ts = day_base + (2 + ei * 2) * 3600
            stamps = np.array([entry_ts, entry_ts + 60, entry_ts + 120, entry_ts + 180], dtype=np.int64)
            stop_cost = 500.0
            win = bool(rng.random() < 0.56)
            net_r = float(rng.uniform(0.65, 1.45)) if win else -float(rng.uniform(0.45, 1.0))
            net_1lot = net_r * stop_cost
            dd_1lot = -abs(float(rng.uniform(0.15, 0.75))) * stop_cost if win else min(net_1lot, -0.5 * stop_cost)
            marks = np.array(
                [
                    [0.0, 0.0, dd_1lot * 0.5, dd_1lot * 0.3],
                    [dd_1lot * 0.3, max(0.0, net_1lot * 0.4), dd_1lot, net_1lot * 0.3],
                    [net_1lot * 0.3, max(net_1lot * 0.8, 0.0), min(dd_1lot * 0.5, net_1lot), net_1lot * 0.8],
                    [net_1lot * 0.8, max(net_1lot, 0.0), min(net_1lot, 0.0), net_1lot],
                ],
                dtype=np.float64,
            )
            ep = 150.0 if "JPY" in asset else (15000.0 if asset == "US100" else 1.25)
            row = {
                "asset": asset,
                "side": 1 if (di + ei) % 3 != 0 else -1,
                "entry": int(stamps[0]),
                "exit": int(stamps[-1]) + 60,
                "at_open": False,
                "entry_price": ep,
                "stop_risk_with_cost_usd": stop_cost,
                "initial_risk_usd": stop_cost * 0.94,
                "net_usd_per_lot": net_1lot,
                "net_R": net_r,
                "gross_R": net_r,
            }
            tapes[eng][dk] = (row, stamps, marks)
    return days, tapes


# ---------------------------------------------------------------------------
# 1. Exact 100.0% Phase Partition, P2-4 Guardrail & Law 13 Separate Payout #1
# ---------------------------------------------------------------------------


class TestPhasePartitionsAndGuardrails:
    @pytest.mark.parametrize(
        "counts",
        [
            (1, 1, 1),
            (333, 333, 334),
            (7, 0, 0),
            (0, 0, 17),
            (5123, 2891, 1986),
            (13, 29, 71),
        ],
    )
    def test_exact_partition_pct_always_sums_to_100_0(self, counts: tuple[int, int, int]) -> None:
        res = bpa.exact_partition_pct(*counts)
        _check(abs(res["sum_pct"] - 100.0) <= 1e-9, f"sum != 100: {res}")
        _check(
            abs((res["pass_pct"] + res["fail_pct"] + res["pending_pct"]) - 100.0) <= 1e-9,
            f"components sum != 100: {res}",
        )
        _check(res["n_total"] == sum(counts), "n_total mismatch")
        # Must pass strict EvaluationCatalog HorizonPartitionPct validation!
        ec.HorizonPartitionPct(
            pass_pct=res["pass_pct"],
            fail_pct=res["fail_pct"],
            pending_pct=res["pending_pct"],
        )

    def test_p2_4_guardrail_rejects_nonzero_retries_and_eval_pass_drift(self) -> None:
        n = 10
        zeros_i32 = np.full(n, -1, dtype=np.int32)
        zeros_i8 = np.zeros(n, dtype=np.int8)
        ones_i32 = np.ones(n, dtype=np.int32)
        zeros_f64 = np.zeros(n, dtype=np.float64)
        raw = (
            zeros_i32,
            zeros_i32,
            zeros_i32,
            zeros_i8,
            zeros_i32,
            zeros_i32,
            zeros_i32,
            zeros_i8,
            zeros_i8,
            zeros_i8,
            zeros_i8,
            ones_i32,
            zeros_f64,
            zeros_f64,
            zeros_f64,
            zeros_f64,
            np.full(n, 100.0, dtype=np.float64),
            np.zeros(n, dtype=np.int32),
            np.zeros(n, dtype=np.int32),
        )
        dummy_fn = {
            "winrate_pct": 50.0,
            "avg_rr": 1.2,
            "ev_per_trade_r": 0.05,
            "ev_usd_per_trade": 10.0,
            "profit_factor": 1.2,
            "peak_dd_pct": 5.0,
            "max_daily_dd_pct": 2.0,
            "calmar": 1.0,
            "sharpe": 1.2,
            "ann_pct": 10.0,
            "sized_trades": 100,
            "peak_open_risk_pct": 1.5,
        }
        with pytest.raises(ValueError, match="P2_4_GUARDRAIL_VIOLATION"):
            bpa.summarize_4phase_lifecycle(
                raw,
                funded_replay_metrics=dummy_fn,
                fee_usd=100.0,
                card_fx_fee_pct=0.025,
                usd_vnd_rate=25_765.94,
                max_retries_used=1,
            )

        # Drift between eval_pass_day and funded_enter_day MUST fail closed
        bad_eval_pass = zeros_i32.copy()
        bad_eval_pass[0] = 50
        raw_drift = (raw[0], bad_eval_pass, *raw[2:])
        with pytest.raises(ValueError, match="P2_4_GUARDRAIL_VIOLATION"):
            bpa.summarize_4phase_lifecycle(
                raw_drift,
                funded_replay_metrics=dummy_fn,
                fee_usd=100.0,
                card_fx_fee_pct=0.025,
                usd_vnd_rate=25_765.94,
                max_retries_used=0,
            )

    def test_4phase_partitions_and_separate_cond_vs_uncond_payout1(self) -> None:
        # Construct 7 paths with known exact P1, P2, pass_eval, funded_12m, and pay1 outcomes:
        # Path 0: P1 pass d=30, P2 pass d=60, pay1 d=80 (no breach)
        # Path 1: P1 pass d=40, P2 pass d=90, pay1 d=120, funded breach d=200 (within 12m!)
        # Path 2: P1 pass d=50, P2 pass d=100, no pay1 (dry funded)
        # Path 3: P1 pass d=60, P2 fail d=110 (stage 2)
        # Path 4: P1 pass d=700, P2 pending at horizon=756
        # Path 5: P1 fail d=25 (stage 1)
        # Path 6: P1 pending at horizon=756
        p1_pass = np.array([30, 40, 50, 60, 700, -1, -1], dtype=np.int32)
        fn_enter = np.array([60, 90, 100, -1, -1, -1, -1], dtype=np.int32)
        eval_fail = np.array([-1, -1, -1, 110, -1, 25, -1], dtype=np.int32)
        fail_st = np.array([0, 0, 0, 2, 0, 1, 0], dtype=np.int8)
        pay1 = np.array([80, 120, -1, -1, -1, -1, -1], dtype=np.int32)
        fn_br = np.array([-1, 200, -1, -1, -1, -1, -1], dtype=np.int32)
        n = 7
        raw = (
            p1_pass,
            fn_enter.copy(),
            eval_fail,
            fail_st,
            pay1,
            fn_enter,
            fn_br,
            np.zeros(n, dtype=np.int8),
            np.array([0, 1, 0, 1, 0, 1, 0], dtype=np.int8),
            np.zeros(n, dtype=np.int8),
            np.array([0, 1, 0, 1, 0, 1, 0], dtype=np.int8),
            np.ones(n, dtype=np.int32),
            np.full(n, 0.2, dtype=np.float64),
            np.full(n, 0.2, dtype=np.float64),
            np.array([800.0, 200.0, -100.0, -100.0, -100.0, -100.0, -100.0], dtype=np.float64),
            np.array([850.0, 220.0, -100.0, -100.0, -100.0, -100.0, -100.0], dtype=np.float64),
            np.full(n, 101.08, dtype=np.float64),
            np.array([12, 5, 12, 0, 0, 0, 0], dtype=np.int32),
            np.array([2, 1, 12, 0, 0, 0, 0], dtype=np.int32),
        )
        dummy_fn = {
            "winrate_pct": 51.0,
            "avg_rr": 1.25,
            "ev_per_trade_r": 0.06,
            "ev_usd_per_trade": 18.0,
            "profit_factor": 1.24,
            "peak_dd_pct": 6.2,
            "max_daily_dd_pct": 2.1,
            "calmar": 1.35,
            "sharpe": 1.42,
            "ann_pct": 14.0,
            "sized_trades": 250,
            "peak_open_risk_pct": 1.8,
        }
        res = bpa.summarize_4phase_lifecycle(
            raw,
            funded_replay_metrics=dummy_fn,
            fee_usd=98.61,
            card_fx_fee_pct=0.025,
            usd_vnd_rate=25_765.94,
            horizon_days=756,
            max_retries_used=0,
        )

        # Verify EXACT 100.0% partition across EVERY horizon of p1, p2, pass_eval
        for ph_key in ("p1", "p2", "pass_eval"):
            for hkey, hval in res[ph_key]["horizons"].items():
                tot = hval["pass_pct"] + hval["fail_pct"] + hval["pending_pct"]
                _check(abs(tot - 100.0) <= 1e-9, f"{ph_key}.{hkey} sum={tot} != 100.0")

        # Verify P2 conditional counts: 5 entered P2 -> 3 passed, 1 failed, 1 pending at full horizon
        p2_full = res["p2"]["horizons"]["full_horizon_36m"]
        _check(res["p2"]["entered_p2_count"] == 5, f"expected 5 entered P2, got {res['p2']['entered_p2_count']}")
        _check((p2_full["n_pass"], p2_full["n_fail"], p2_full["n_pending"]) == (3, 1, 1), f"bad p2 counts: {p2_full}")

        # Verify Law 13 separate Payout #1: only 2/7 paid -> cond median = 100d*cal (~144.9d), uncond = 730.0d!
        fn12 = res["funded_12m"]
        expected_cond = round(100.0 * CALENDAR_DAYS_PER_TRADING_DAY, 1)
        _check(fn12["cond_med_pay1_cal_days"] == expected_cond, f"bad cond pay1: {fn12['cond_med_pay1_cal_days']}")
        uncond_p1 = fn12["uncond_med_pay1_cal_days_cap730"]
        _check(uncond_p1 == 730.0, f"bad uncond pay1: {uncond_p1}")
        _check(fn12["cond_med_pay1_cal_days"] < uncond_p1, "cond/uncond must be separate!")
        _check(fn12["funded_entered_count"] == 3 and fn12["funded_breach_12m_count"] == 1, "bad funded 12m counts")


# ---------------------------------------------------------------------------
# 2. Mandatory v1.04-ML Tags, Profile Specs & Synthetic End-to-End Catalog Test
# ---------------------------------------------------------------------------


class TestBaselineSpecsAndSyntheticE2E:
    def test_profile_specs_and_mandatory_v104_ml_tags(self) -> None:
        specs = bpa.build_baseline_profile_specs()
        ids = [s.profile_id for s in specs]
        _check(
            ids == ["C00", "C10_NEWS_ON", "V103_SPRINT", "V104_ML", "V103_OOF_CONTROL"],
            f"unexpected profile order: {ids}",
        )
        by_id = {s.profile_id: s for s in specs}

        # Verify exact SSOT multipliers & KS 8.00% on v1.03-Sprint
        _check((by_id["C00"].p1_mult, by_id["C00"].p2_mult, by_id["C00"].funded_mult) == (4.0, 2.0, 1.0), "C00 mults")
        _check(
            (by_id["C10_NEWS_ON"].p1_mult, by_id["C10_NEWS_ON"].p2_mult, by_id["C10_NEWS_ON"].funded_mult)
            == (4.0, 3.5, 1.25),
            "C10_NEWS_ON mults",
        )
        spr = by_id["V103_SPRINT"]
        _check((spr.p1_mult, spr.p2_mult, spr.funded_mult) == (4.5, 3.5, 1.0), "V103_SPRINT mults")
        _check(abs(spr.funded_kill_static_pct - 8.0) < 1e-9, f"expected KS 8.00%, got {spr.funded_kill_static_pct}")

        # Verify mandatory tags on V104_ML & paired OOF control
        ml_tags = set(by_id["V104_ML"].mandatory_tags)
        _check(bpa.TAG_FEATURE_SKEW_UNFIXED in ml_tags, "V104_ML missing FEATURE_SKEW_UNFIXED")
        _check(bpa.TAG_OOF_SUBSET_WINDOW in ml_tags, "V104_ML missing OOF_SUBSET_WINDOW")
        _check(CONSUMED_CLB_TAG in ml_tags, "V104_ML missing CONSUMED_DEV_CLB_TEMPORAL_OOS")
        ctrl_tags = set(by_id["V103_OOF_CONTROL"].mandatory_tags)
        _check(bpa.TAG_OOF_SUBSET_WINDOW in ctrl_tags, "V103_OOF_CONTROL missing OOF_SUBSET_WINDOW")
        _check(bpa.TAG_PAIRED_OOF_CONTROL in ctrl_tags, "V103_OOF_CONTROL missing PAIRED_OOF_CONTROL")

    def test_synthetic_profile_eval_grading_and_tmp_catalog_registration(self, tmp_path: Path) -> None:
        days, tapes = _make_synthetic_tapes_and_days(n_days=75)
        pre = prealign_days_for_tapes(days, tapes)
        idx = make_block_bootstrap_indices(len(days), horizon=300, n_paths=120, block_len=5, seed=12345)
        firms_doc = json.loads((REPO_ROOT / "tooling/ai-engines/configs/ssot/firms_catalog.json").read_text("utf-8"))
        c10k = firms_doc["contracts"]["ftmo_standard_10k"]
        specs = bpa.build_baseline_profile_specs()
        specs_by_id = {s.profile_id: s for s in specs}

        profiles_dict: dict[str, Any] = {}
        for sp in specs[:3]:
            cell = bpa.evaluate_profile_on_contract(
                spec=sp,
                contract=c10k,
                ext_days=days,
                pre_days=pre,
                idx_matrix=idx,
                usd_vnd_rate=25_765.94,
                friction_mult=1.0,
                slippage_breakeven_mult=1.65,
            )
            sc = cell["scorecard"]
            # Every single phase MUST be strictly instrumented (never UNKNOWN_LEGACY_UNINSTRUMENTED)
            for ph_k in ("p1", "p2", "pass_eval", "funded_12m"):
                _check(
                    sc["phase_grades"][ph_k]["grade"] != "UNKNOWN_LEGACY_UNINSTRUMENTED",
                    f"{sp.profile_id} phase {ph_k} was uninstrumented!",
                )
            profiles_dict[sp.profile_id] = {"evaluations": {"ftmo_standard_10k": {"1.0x": cell}}}

        fake_report = {
            "report_sha256": hashlib.sha256(b"synthetic-w5-baseline").hexdigest(),
            "profiles": profiles_dict,
        }
        cat_db = tmp_path / "unified_eval_catalog.duckdb"
        cat_reg = tmp_path / "unified_eval_registry.sqlite3"
        reg_res = bpa.register_baseline_results_to_catalog(
            report=fake_report,
            specs_by_id=specs_by_id,
            usd_vnd_rate=25_765.94,
            duckdb_path=cat_db,
            registry_path=cat_reg,
        )
        _check(reg_res["runs_recorded_count"] == 3, "expected 3 registered runs")
        _check(reg_res["mc_cases_recorded"]["total_mc_cases"] == 3, "expected 3 registered MC cases")
        _check(reg_res["integrity"]["verified"] is True, "tmp catalog integrity failed")
        _check(reg_res["integrity"]["runs_catalog_count"] == 3, "runs_catalog_count mismatch")
        _check(reg_res["integrity"]["mc_by_campaign"][bpa.CAMPAIGN_ID] == 3, "mc_by_campaign mismatch")

    def test_zero_bare_asserts_zero_crlf_zero_bom_zero_bare_dollar(self) -> None:
        targets = (
            REPO_ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave5" / "baseline_profiles_audit.py",
            Path(__file__).resolve(),
            REPO_ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave5" / "evaluation_catalog.py",
            Path(__file__).resolve().with_name("test_wave5_evaluation_catalog.py"),
        )
        for fp in targets:
            raw = fp.read_bytes()
            _check(b"\r\n" not in raw, f"CRLF detected in {fp.name}")
            _check(not raw.startswith(b"\xef\xbb\xbf"), f"BOM detected in {fp.name}")
            tree = ast.parse(raw.decode("utf-8"), filename=str(fp))
            for node in ast.walk(tree):
                _check(
                    not isinstance(node, ast.Assert),
                    f"bare assert forbidden in {fp.name}:{getattr(node, 'lineno', 0)}",
                )


# ---------------------------------------------------------------------------
# 3. Local-Cache Production Artifact & Catalog SHA Invariance Verification
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_w5_baseline_artifacts_and_catalog_sha_invariance() -> None:
    prod_db = ec.DEFAULT_CATALOG_DUCKDB_PATH
    prod_reg = ec.DEFAULT_CATALOG_REGISTRY_PATH
    report_p = bpa.DEFAULT_REPORT_PATH
    receipt_p = bpa.DEFAULT_RECEIPT_PATH
    dropbox_p = bpa.DEFAULT_DROPBOX_PATH

    for p in (prod_db, prod_reg, report_p, receipt_p, dropbox_p):
        _check(p.is_file(), f"missing production W5-G05 deliverable: {p}")

    db_sha_before = _sha256_file(prod_db)
    reg_sha_before = _sha256_file(prod_reg)

    # Receipts at audit path & swarm dropbox MUST be byte-identical
    _check(receipt_p.read_bytes() == dropbox_p.read_bytes(), "audit receipt != swarm dropbox receipt")

    report = json.loads(report_p.read_text(encoding="utf-8"))
    _check(report["hard_invariants"]["holdout_rows_analysed"] == 0, "holdout_rows_analysed != 0")
    _check(report["hard_invariants"]["order_send_count"] == 0, "order_send_count != 0")
    _check(report["hard_invariants"]["p2_4_max_retries_zero"] is True, "P2-4 flag missing")
    _check(report["simulation_settings"]["n_paths"] == 10_000, "production audit must use N=10,000 paths")

    # Verify all 4 profiles + paired OOF control present
    expected_profiles = {"C00", "C10_NEWS_ON", "V103_SPRINT", "V104_ML", "V103_OOF_CONTROL"}
    _check(set(report["profiles"].keys()) == expected_profiles, f"missing profiles: {report['profiles'].keys()}")

    # Mandatory V104_ML tags & exact 2,799-trade OOF window
    ml_prof = report["profiles"]["V104_ML"]
    ml_tags = set(ml_prof["mandatory_tags"])
    _check(bpa.TAG_FEATURE_SKEW_UNFIXED in ml_tags, "prod V104_ML missing FEATURE_SKEW_UNFIXED")
    _check(bpa.TAG_OOF_SUBSET_WINDOW in ml_tags, "prod V104_ML missing OOF_SUBSET_WINDOW")
    _check(CONSUMED_CLB_TAG in ml_tags, "prod V104_ML missing CONSUMED_DEV_CLB_TEMPORAL_OOS")
    _check(
        ml_prof["oof_trade_counts"]["raw_oof_trades"] == bpa.V104_ML_EXPECTED_OOF_TRADES,
        f"unexpected OOF trade count: {ml_prof['oof_trade_counts']}",
    )

    # Verify EXACT 100.0% partitions & separate cond/uncond Payout #1 across EVERY cell
    for pid, pdata in report["profiles"].items():
        for cid in bpa.TARGET_CONTRACTS:
            _check(cid in pdata["evaluations"], f"{pid} missing contract {cid}")
            for fkey in ("1.0x", "1.5x"):
                cell = pdata["evaluations"][cid][fkey]
                ph = cell["phases"]
                for ph_name in ("p1", "p2", "pass_eval"):
                    for hkey, hval in ph[ph_name]["horizons"].items():
                        s = hval["pass_pct"] + hval["fail_pct"] + hval["pending_pct"]
                        _check(abs(s - 100.0) <= 1e-9, f"{pid}/{cid}/{fkey} {ph_name}.{hkey} sum={s}")
                fn12 = ph["funded_12m"]
                _check("cond_med_pay1_cal_days" in fn12, "missing cond_med_pay1_cal_days")
                _check("uncond_med_pay1_cal_days_cap730" in fn12, "missing uncond_med_pay1_cal_days_cap730")
                for pk in ("p1", "p2", "pass_eval", "funded_12m"):
                    _check(
                        cell["scorecard"]["phase_grades"][pk]["grade"] != "UNKNOWN_LEGACY_UNINSTRUMENTED",
                        f"prod {pid}/{cid}/{fkey} phase {pk} uninstrumented",
                    )

    # Verify production UnifiedEvaluationCatalog integrity & exact counts (read-only!)
    with ec.UnifiedEvaluationCatalog(duckdb_path=prod_db, registry_path=prod_reg, read_only=True) as cat:
        ver = cat.verify_integrity()
        _check(ver["verified"] is True, "prod catalog integrity failed")
        expected_cells = len(expected_profiles) * len(bpa.TARGET_CONTRACTS) * len(bpa.TARGET_FRICTIONS)
        _check(
            ver["mc_by_campaign"].get(bpa.CAMPAIGN_ID) == expected_cells,
            f"expected {expected_cells} offensive5_baseline MC rows, got {ver['mc_by_campaign']}",
        )
        _check(
            ver["mc_by_campaign"].get("offensive4") == 168,
            f"Wave 4 168 rows disturbed: {ver['mc_by_campaign']}",
        )
        _check(
            ver["runs_catalog_count"] >= expected_cells,
            f"expected >= {expected_cells} runs_catalog rows, got {ver['runs_catalog_count']}",
        )

    # Confirm ZERO mutation to production DuckDB & SQLite during pytest!
    _check(_sha256_file(prod_db) == db_sha_before, "production DuckDB SHA mutated during pytest!")
    _check(_sha256_file(prod_reg) == reg_sha_before, "production SQLite SHA mutated during pytest!")
