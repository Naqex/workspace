"""Unit, invariant, air-gap, and local-cache production tests for Wave 5 Gate W5-G14 Spectrum MC.

Hard invariants verified (ZERO bare `assert`s — 100% `python -O` safe):
  1. AST & P2-1 air-gap check on `spectrum_mc_kernel.py`: ZERO imports of `holdout_guard`,
     `quant_core`, `pareto_multi_account`, `research_council`, or `duckdb`; passes
     `compute_router.assert_dev_only_module(...)`; inline `DEV_CUTOFF_SEC = 1_735_689_600`.
  2. Static-kill floor zero-ratchet invariant (`s_bal > ea_static_floor + 1e-9`): proves no
     multi-day `-0.20%/day` downward ratchet occurs when balance sits below `ea_static_floor`.
  3. Exact `100.0%` partitions (`Pass + Fail + Pending`) for P1, P2, Pass Eval, and Fleet, plus
     strict `max_retries=0`, `funded_enter_day == eval_pass_day`, and separate conditional vs
     unconditional Payout #1 timing.
  4. Shared-path daily correlation `rho > 0.999` positive proof vs independent negative mutation.
  5. Trade-level / intraday DD audit proves detection of intra-day 5% Daily DD breaches masked
     by daily-close smoothing.
  6. `T5_MAX_THROTTLE_YOLO` carries mandatory `RESEARCH_BOUNDARY_ONLY` + `FTMO_GAMBLING_ALLIN_RISK`
     tags, `force_mode_b=True` fails closed, and all write tests isolate to `tmp_path` so
     production JSON/DuckDB SHA-256 NEVER mutates during pytest.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ops_cloud import compute_router as cr  # noqa: E402
from quant_factory.wave5 import evaluation_catalog as ec  # noqa: E402
from quant_factory.wave5 import run_challenge_spectrum_5tiers as rcs  # noqa: E402
from quant_factory.wave5 import spectrum_mc_kernel as sk  # noqa: E402

KERNEL_PATH = AI_ENGINES_DIR / "quant_factory" / "wave5" / "spectrum_mc_kernel.py"
RUNNER_PATH = AI_ENGINES_DIR / "quant_factory" / "wave5" / "run_challenge_spectrum_5tiers.py"
TEST_SELF_PATH = Path(__file__).resolve()


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion helper immune to `python -O` stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1. AST Air-Gap, P2-1 Guardrail, Zero Bare Asserts & LF/BOM Hygiene
# ---------------------------------------------------------------------------


class TestAirGapAndHygiene:
    def test_kernel_ast_zero_forbidden_imports_and_airgap_ok(self) -> None:
        cr.assert_dev_only_module(KERNEL_PATH)
        src = KERNEL_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(KERNEL_PATH))
        forbidden_tokens = (
            "holdout_guard",
            "quant_core",
            "pareto_multi_account",
            "research_council",
            "duckdb",
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    low = alias.name.lower()
                    for tok in forbidden_tokens:
                        _check(tok not in low, f"FORBIDDEN_IMPORT[{tok}] in kernel: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").lower()
                for tok in forbidden_tokens:
                    _check(tok not in mod, f"FORBIDDEN_IMPORT_FROM[{tok}] in kernel: {node.module}")
                for alias in node.names:
                    low = alias.name.lower()
                    for tok in forbidden_tokens:
                        _check(tok not in low, f"FORBIDDEN_IMPORT_ALIAS[{tok}] in kernel: {alias.name}")
            elif isinstance(node, ast.Call):
                fn = node.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
                if fname in ("import_module", "__import__") and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        low = arg0.value.lower()
                        for tok in forbidden_tokens:
                            _check(tok not in low, f"FORBIDDEN_DYNAMIC_IMPORT[{tok}] in kernel: {arg0.value}")

    def test_zero_bare_asserts_and_pure_lf_no_bom(self) -> None:
        for fp in (KERNEL_PATH, RUNNER_PATH, TEST_SELF_PATH):
            raw = fp.read_bytes()
            _check(raw.count(b"\r\n") == 0, f"CRLF detected in {fp.name}")
            _check(not raw.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM detected in {fp.name}")
            tree = ast.parse(raw.decode("utf-8"), filename=str(fp))
            bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
            _check(not bare_asserts, f"Bare assert(s) found in {fp.name} at lines {bare_asserts}")

    def test_inline_dev_cutoff_guards_fail_closed(self) -> None:
        _check(sk.DEV_CUTOFF_SEC == 1_735_689_600, f"unexpected DEV_CUTOFF_SEC={sk.DEV_CUTOFF_SEC}")
        _check(sk.ORDER_SEND_CAPABLE is False and sk.ORDER_SEND_COUNT == 0, "OrderSend invariant broken")
        _check(sk.verify_pre_cutoff_days(["2018-01-02", "2024-12-31"]) == 0, "valid Dev dates rejected")
        with pytest.raises(ValueError, match="DEV_CUTOFF_VIOLATION"):
            sk.verify_pre_cutoff_days(["2024-12-31", "2025-01-01"])
        _check(sk.verify_pre_cutoff_timestamps([1_514_851_200, 1_735_689_599]) == 0, "valid Dev ts rejected")
        with pytest.raises(ValueError, match="DEV_CUTOFF_VIOLATION"):
            sk.verify_pre_cutoff_timestamps([1_735_689_600])

    def test_owner_override_rejects_force_mode_b(self) -> None:
        with pytest.raises(ValueError, match="OWNER_OVERRIDE_VIOLATION"):
            rcs.run_challenge_spectrum_5tiers(force_mode_b=True, in_process_local=True, sync_x13=False)


# ---------------------------------------------------------------------------
# 2. Kernel Mathematical Invariants (Zero-Ratchet, Partitions, Rho, Intraday)
# ---------------------------------------------------------------------------


class TestKernelMathInvariants:
    def test_exact_partition_100_sum_edge_cases(self) -> None:
        for p, f, w in ((1, 1, 1), (333, 333, 334), (7, 13, 19), (0, 0, 100), (100, 0, 0), (0, 0, 0)):
            res = sk.exact_partition_pct(p, f, w)
            _check(abs(res["sum_pct"] - 100.0) < 1e-9, f"partition sum != 100.0: {res}")
            _check(
                abs((res["pass_pct"] + res["fail_pct"] + res["pending_pct"]) - 100.0) < 1e-9,
                f"component sum drift: {res}",
            )

    def test_fleet_static_kill_zero_ratchet_invariant(self) -> None:
        """Prove `s_bal > ea_static_floor + 1e-9` eliminates multi-day `-0.20%/day` static-kill ratchet."""
        n_obs = 60
        n_paths = 4
        # Deterministic sequential path 0..59
        idx = np.tile(np.arange(n_obs, dtype=np.int32), (n_paths, 1))
        cap = 10_000.0

        # P1 passes cleanly in 4 days (+3.0% / day -> +12.0% > 10.0%)
        sku_p1_nets = np.zeros((1, sk.MAX_EVAL_TIERS, n_obs), dtype=np.float64)
        sku_p1_dds = np.zeros((1, sk.MAX_EVAL_TIERS, n_obs), dtype=np.float64)
        sku_p1_flgs = np.ones((1, sk.MAX_EVAL_TIERS, n_obs), dtype=np.int8)
        sku_p1_nets[0, :, :] = 300.0

        # P2 passes cleanly in 4 days (+1.5% / day -> +6.0% > 5.0%)
        sku_p2_nets = np.zeros((1, sk.MAX_EVAL_TIERS, n_obs), dtype=np.float64)
        sku_p2_dds = np.zeros((1, sk.MAX_EVAL_TIERS, n_obs), dtype=np.float64)
        sku_p2_flgs = np.ones((1, sk.MAX_EVAL_TIERS, n_obs), dtype=np.int8)
        sku_p2_nets[0, :, :] = 150.0

        # Funded: drops smoothly into `-8.3%` (below `-8.0%` EA static floor, safely above `-10.0%` firm static DD)
        # across 3 mild down days (`-2.8%`, `-2.8%`, `-2.7%`), then stays FLAT (`0.0` net, `0.0` dd) for 40+ days!
        # With the old ratchet bug, every flat day below `-8.0%` would subtract `-0.20%` and breach `-10.0%`!
        sku_fn_nets = np.zeros((1, 3, n_obs), dtype=np.float64)
        sku_fn_dds = np.zeros((1, 3, n_obs), dtype=np.float64)
        sku_fn_flgs = np.ones((1, 3, n_obs), dtype=np.int8)
        # Account enters Funded on day 8 (after 4d P1 + 4d P2)
        for d_drop, loss_usd in ((8, -280.0), (9, -280.0), (10, -270.0)):
            sku_fn_nets[0, :, d_drop] = loss_usd
            sku_fn_dds[0, :, d_drop] = abs(loss_usd)
        # Days 11..59: tiny +1 USD gain, 10 USD intraday wiggle (still well above -10% firm floor!)
        sku_fn_nets[0, :, 11:] = 1.0
        sku_fn_dds[0, :, 11:] = 10.0

        zeros_t = np.zeros(sk.MAX_EVAL_TIERS, dtype=np.float64)
        ones_t = np.ones(sk.MAX_EVAL_TIERS, dtype=np.float64)
        raw = sk.simulate_fleet_6tier_numba(
            idx,
            sku_p1_nets,
            sku_p1_dds,
            sku_p1_flgs,
            sku_p2_nets,
            sku_p2_dds,
            sku_p2_flgs,
            sku_fn_nets,
            sku_fn_dds,
            sku_fn_flgs,
            0,
            zeros_t,
            zeros_t,
            ones_t,
            4,
            zeros_t,
            zeros_t,
            ones_t,
            4,
            0.0,
            0.0,
            1.0,
            1.0,
            0.035,
            0.65,
            0.06,
            0.40,
            0.035,
            0.030,
            0.080,
            0.075,
            0,
            0.035,
            0.060,
            0.025,
            0.080,  # fn_kill_static = 8.0%
            np.array([cap], dtype=np.float64),
            np.array([100.0], dtype=np.float64),
            np.array([0.025], dtype=np.float64),
            np.array([0.015], dtype=np.float64),
            np.array([1.0], dtype=np.float64),
            np.array([0.10], dtype=np.float64),
            np.array([0.05], dtype=np.float64),
            np.array([0.05], dtype=np.float64),
            np.array([0.10], dtype=np.float64),
            np.array([4], dtype=np.int32),
            np.array([0.80], dtype=np.float64),
            np.array([0.90], dtype=np.float64),
            np.array([10], dtype=np.int32),
            np.array([50.0], dtype=np.float64),
            0,  # CONSERVATIVE_1_TICKET
            1,  # P2_BALANCED
            500.0,
            4,
            5,
            0.035,
            400_000.0,
            200_000.0,
            2_000_000.0,
            True,
            3.0,
            0.40,
            0.40,
            0.20,
        )
        # indices: 16=first_funded_day, 23=bot_kill_events, 24=firm_breach_events, 26=funded_breach_events
        first_fn_day = raw[16]
        bot_kills = raw[23]
        firm_breaches = raw[24]
        fn_breaches = raw[26]
        acct_err = raw[12]

        _check(bool(np.all(first_fn_day == 8)), f"expected Funded entry on day 8, got {first_fn_day}")
        _check(bool(np.all(bot_kills >= 1)), f"expected static/daily kill to fire once on drop, got {bot_kills}")
        _check(
            bool(np.all(firm_breaches == 0)) and bool(np.all(fn_breaches == 0)),
            f"STATIC_KILL_RATCHET_BUG_DETECTED: firm_breaches={firm_breaches}, fn_breaches={fn_breaches}",
        )
        _check(float(np.max(acct_err)) < 1e-6, f"cash conservation drift: {float(np.max(acct_err))}")

    def test_single_ticket_dp_6tier_and_max_retries_zero(self) -> None:
        n_obs = 40
        horizon = 80
        n_paths = 30
        idx = sk.make_block_bootstrap_indices(n_obs, horizon=horizon, n_paths=n_paths, block_len=5, seed=42)
        cap = 10_000.0
        rng = np.random.default_rng(123)
        base_net = rng.normal(loc=45.0, scale=85.0, size=n_obs)
        base_dd = np.maximum(0.0, -base_net) + 25.0
        base_flg = np.ones(n_obs, dtype=np.int8)

        p1_mults = np.array([3.0, 2.0, 2.5, 2.0, 1.0, 0.5], dtype=np.float64)
        p1_eq_min = np.array([4.5, 8.0, -1.5, -4.5, -6.5, -10.0], dtype=np.float64)
        p1_eq_max = np.array([7.9999, 10.0, 4.4999, -1.5001, -4.5001, -6.5001], dtype=np.float64)
        p1_nets = p1_mults[:, None] * base_net[None, :]
        p1_dds = p1_mults[:, None] * base_dd[None, :]
        p1_flgs = np.broadcast_to(base_flg, (6, n_obs)).copy()

        fn_nets = np.vstack([base_net, 0.65 * base_net, 0.40 * base_net])
        fn_dds = np.vstack([base_dd, 0.65 * base_dd, 0.40 * base_dd])
        fn_flgs = np.broadcast_to(base_flg, (3, n_obs)).copy()

        raw = sk.simulate_single_ticket_6tier_numba(
            idx,
            p1_nets,
            p1_dds,
            p1_flgs,
            p1_eq_min,
            p1_eq_max,
            p1_mults,
            6,
            p1_nets * 0.7,
            p1_dds * 0.7,
            p1_flgs,
            p1_eq_min,
            p1_eq_max,
            p1_mults * 0.7,
            6,
            fn_nets,
            fn_dds,
            fn_flgs,
            cap,
            98.61,
            0.025,
            0.015,
            1.0,
            0.10,
            0.05,
            0.05,
            0.10,
            1,
            4,
            0,
            0.0,
            0.80,
            10,
            50.0,
            1,  # eval_is_dp = 1
            0.0,
            0.0,
            1.0,
            1.0,
            0.035,
            0.65,
            0.06,
            0.40,
            0.035,
            0.030,
            0.080,
            0.075,
            0,
            0.035,
            0.060,
            0.025,
            0.080,
            0.06,
            True,
        )
        summ = sk.summarize_single_ticket_lifecycle(
            raw,
            funded_replay_metrics={
                "winrate_pct": 52.0,
                "avg_rr": 1.3,
                "ev_per_trade_r": 0.08,
                "ev_usd_per_trade": 4.0,
                "profit_factor": 1.35,
                "peak_dd_pct": 4.2,
                "max_daily_dd_pct": 1.8,
                "calmar": 1.8,
                "sharpe": 1.6,
                "ann_pct": 8.5,
                "sized_trades": 200,
                "peak_open_risk_pct": 1.5,
            },
            fee_usd=98.61,
            card_fx_fee_pct=0.025,
            usd_vnd_rate=25765.94,
            horizon_days=horizon,
        )
        _check(summ["max_retries"] == 0, "max_retries must be 0")
        _check(summ["pass_eval"]["derived_from"] == "funded_enter_day", "must derive pass_eval from funded_enter_day")
        _check(abs(summ["p1"]["sum_12m_pct"] - 100.0) < 1e-9, "p1 12m sum != 100%")
        _check(abs(summ["p2"]["sum_12m_elapsed_pct"] - 100.0) < 1e-9, "p2 12m sum != 100%")
        _check(abs(summ["pass_eval"]["sum_12m_pct"] - 100.0) < 1e-9, "pass_eval 12m sum != 100%")
        _check("cond_med_pay1_cal_days" in summ["funded_12m"], "missing cond_med_pay1_cal_days")
        _check("uncond_med_pay1_cal_days_cap730" in summ["funded_12m"], "missing uncond_med_pay1_cal_days_cap730")

    def test_shared_path_rho_proof_positive_and_negative_mutation(self) -> None:
        rng = np.random.default_rng(77)
        a = rng.normal(0.0, 100.0, size=200)
        b = 2.0 * a + rng.normal(0.0, 0.5, size=200)  # tiny rounding diff like 100K vs 200K
        proof = sk.measure_shared_path_rho_proof(daily_net_acct_a=a, daily_net_acct_b=b, n_paths=100, horizon_days=120)
        _check(proof["shared_path_rho_gt_0_999"] is True, f"shared rho failed: {proof}")
        _check(proof["independent_rho_near_zero"] is True, f"independent negative mutation failed: {proof}")

    def test_trade_level_intraday_audit_exposes_daily_close_smoothing(self) -> None:
        """Day has Trade 1 = -5.5% intraday, Trade 2 = +6.0% -> close +0.5% masks 5% Daily DD breach!"""
        n_obs = 10
        idx = np.zeros((25, 10), dtype=np.int32)  # always day 0..0
        day_tr_offsets = np.arange(0, 2 * n_obs + 1, 2, dtype=np.int32)
        tr_net_frac = np.tile(np.array([-0.055, 0.060], dtype=np.float64), n_obs)
        tr_adv_frac = np.tile(np.array([0.056, 0.005], dtype=np.float64), n_obs)
        day_net_frac = np.full(n_obs, 0.005, dtype=np.float64)
        day_m1_dd_frac = np.full(n_obs, 0.056, dtype=np.float64)
        day_flg = np.ones(n_obs, dtype=np.int8)

        aud = sk.run_trade_level_intraday_dd_audit(
            schedule_id="T5_MAX_THROTTLE_YOLO",
            contract_id="ftmo_standard_100k",
            idx_matrix=idx,
            day_tr_offsets=day_tr_offsets,
            tr_net_frac=tr_net_frac,
            tr_adv_frac=tr_adv_frac,
            day_net_frac=day_net_frac,
            day_m1_dd_frac=day_m1_dd_frac,
            day_flg=day_flg,
            ea_kill_daily=0.0485,
            ea_kill_static=0.0990,
        )
        _check(aud["modes"]["daily_close_only_1_0x"]["daily_5pct_hard_breach_pct"] == 0.0, "close-only should be 0%")
        _check(
            aud["modes"]["trade_level_intraday_1_0x"]["daily_5pct_hard_breach_pct"] == 100.0,
            f"trade-level must catch 100% intraday 5% breach: {aud}",
        )
        _check(aud["drift_trade_minus_daily_close_pp"] == 100.0, f"expected +100pp drift: {aud}")


# ---------------------------------------------------------------------------
# 3. Schedule Tagging & Tmp-Path Isolated E2E Integration (Zero Prod Mutation)
# ---------------------------------------------------------------------------


class TestScheduleSpecsAndIsolatedE2E:
    def test_all_9_schedules_t5_tags_and_funded_safety(self) -> None:
        if not rcs.DEFAULT_BELLMAN_DP_PATH.is_file():
            pytest.skip("bellman_dp_schedule.json absent in minimal CI")
        schedules, dp_meta = rcs.build_all_9_spectrum_schedules()
        _check(set(schedules.keys()) == set(rcs.TIER_A_CORE_SCHEDULES), "must contain exact 9 Tier A schedules")
        _check(dp_meta["p1_tiers_count"] == 6 and dp_meta["p2_tiers_count"] == 6, "DP must have 6 P1 & 6 P2 tiers")
        t5 = schedules["T5_MAX_THROTTLE_YOLO"]
        _check(rcs.TAG_RESEARCH_BOUNDARY in t5.mandatory_tags, "T5 missing RESEARCH_BOUNDARY_ONLY")
        _check(rcs.TAG_FTMO_GAMBLING in t5.mandatory_tags, "T5 missing FTMO_GAMBLING_ALLIN_RISK")
        for sid in rcs.TIER_B_SCHEDULES:
            _check(abs(schedules[sid].funded_mult - 1.0) < 1e-9, f"Tier B {sid} must lock funded_mult=1.0")
            _check(schedules[sid].funded_total_open_cap_pct <= 2.25, f"Tier B {sid} Funded cap > 2.25%")

    @pytest.mark.local_cache
    def test_isolated_tmp_path_mini_e2e_preserves_prod_shas(self, tmp_path: Path) -> None:
        prod_db = ec.DEFAULT_CATALOG_DUCKDB_PATH
        prod_sum = rcs.DEFAULT_SUMMARY_PATH
        db_sha_before = _sha256_file(prod_db) if prod_db.is_file() else None
        sum_sha_before = _sha256_file(prod_sum) if prod_sum.is_file() else None

        tmp_all = tmp_path / "all.json"
        tmp_sum = tmp_path / "summary.json"
        tmp_db = tmp_path / "cat.duckdb"
        tmp_reg = tmp_path / "reg.sqlite3"
        tmp_work = tmp_path / "work"

        all_doc, sum_doc = rcs.run_challenge_spectrum_5tiers(
            n_paths=20,
            horizon_days=756,
            tier_a_schedules=("T1_ULTRA_SAFE", "T3_BALANCED_EV", "T5_MAX_THROTTLE_YOLO", "BELLMAN_DP_6TIER"),
            tier_a_contracts=("ftmo_standard_100k",),
            tier_a_frictions=(1.0,),
            tier_b_schedules=("T3_BALANCED_EV", "BELLMAN_DP_6TIER"),
            tier_b_frictions=(1.0,),
            bankroll_tiers_m_vnd=(10, 25),
            concurrency_modes=("GATED_STAGGER",),
            allocation_policies=("P2_BALANCED_40_40_20",),
            include_oof_ml=True,
            include_intraday_audit=True,
            skip_m1_spread_scan=True,
            sync_x13=False,
            in_process_local=True,
            work_dir=tmp_work,
            write_all_cases_path=tmp_all,
            write_summary_path=tmp_sum,
            catalog_duckdb_path=tmp_db,
            catalog_registry_path=tmp_reg,
        )
        _check(tmp_all.is_file() and tmp_sum.is_file(), "tmp outputs not written")
        _check(tmp_sum.stat().st_size < rcs.SUMMARY_MAX_BYTES, "tmp summary exceeded 400KB")
        _check(all_doc["hard_invariants"]["holdout_rows_analysed"] == 0, "holdout rows != 0")
        _check(all_doc["hard_invariants"]["order_send_count"] == 0, "order_send_count != 0")
        _check(sum_doc["catalog_registration"]["integrity"]["verified"] is True, "tmp catalog integrity failed")

        # Verify production files untouched
        if db_sha_before is not None:
            _check(_sha256_file(prod_db) == db_sha_before, "PRODUCTION DuckDB SHA mutated during tmp_path test!")
        if sum_sha_before is not None:
            _check(
                _sha256_file(prod_sum) == sum_sha_before,
                "PRODUCTION summary JSON SHA mutated during tmp_path test!",
            )


# ---------------------------------------------------------------------------
# 4. Production Artifacts & Unified DuckDB Read-Only Certification
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_w5_g14_artifacts_catalog_and_receipts_readonly() -> None:
    all_p = rcs.DEFAULT_ALL_CASES_PATH
    sum_p = rcs.DEFAULT_SUMMARY_PATH
    rec_p = rcs.DEFAULT_RECEIPT_PATH
    drp_p = rcs.DEFAULT_DROPBOX_PATH
    db_p = ec.DEFAULT_CATALOG_DUCKDB_PATH
    reg_p = ec.DEFAULT_CATALOG_REGISTRY_PATH

    for fp in (all_p, sum_p, rec_p, drp_p, db_p, reg_p):
        _check(fp.is_file(), f"Missing production artifact: {fp}")

    db_sha_0 = _sha256_file(db_p)
    reg_sha_0 = _sha256_file(reg_p)
    sum_sha_0 = _sha256_file(sum_p)

    # 1. Byte-identical audit & dropbox receipts, LF-only, zero BOM
    rec_bytes = rec_p.read_bytes()
    drp_bytes = drp_p.read_bytes()
    _check(rec_bytes == drp_bytes, "Receipt and swarm dropbox files are NOT byte-identical!")
    _check(rec_bytes.count(b"\r\n") == 0 and not rec_bytes.startswith(b"\xef\xbb\xbf"), "Receipt CRLF/BOM violation")

    # 2. Compact summary < 400 KB
    _check(sum_p.stat().st_size < rcs.SUMMARY_MAX_BYTES, f"summary too large: {sum_p.stat().st_size} bytes")

    sum_doc = json.loads(sum_p.read_text(encoding="utf-8"))
    rec_doc = json.loads(rec_bytes.decode("utf-8"))
    all_doc = json.loads(all_p.read_text(encoding="utf-8"))

    _check(sum_doc["counts"]["tier_a_core_cases"] == 54, f"expected 54 Tier A core cases: {sum_doc['counts']}")
    _check(sum_doc["counts"]["tier_a_oof_ml_cases"] == 36, f"expected 36 Tier A OOF cases: {sum_doc['counts']}")
    _check(sum_doc["counts"]["tier_b_fleet_cases"] == 972, f"expected 972 Tier B cases: {sum_doc['counts']}")
    _check(sum_doc["counts"]["total_graded_cases"] == 1062, f"expected 1062 total cases: {sum_doc['counts']}")

    _check(rec_doc["hard_invariants"]["holdout_rows_analysed"] == 0, "holdout_rows_analysed != 0")
    _check(rec_doc["hard_invariants"]["order_send_count"] == 0, "order_send_count != 0")
    _check(rec_doc["hard_invariants"]["spend_vnd"] == 0, "spend_vnd != 0")
    _check(rec_doc["hard_invariants"]["immutables_11_of_11_clean"] is True, "immutables not 11/11 clean")
    _check(sum_doc["shared_path_rho_proof"]["shared_path_rho_gt_0_999"] is True, "shared-path rho <= 0.999")
    _check(len(sum_doc["intraday_trade_dd_audit"]) == 4, "expected 4 intraday DD audits (T4/T5 x 10K/100K)")

    # 3. Verify 100% partitions, T5 tags, OOF tags, and zero UNKNOWN grades on ALL 1,062 cases
    for c in (*all_doc["tier_a_core_cases"], *all_doc["tier_a_oof_ml_cases"]):
        ph = c["phases"]
        _check(abs(ph["p1"]["sum_12m_pct"] - 100.0) < 1e-6, f"P1 sum != 100%: {c['record_id']}")
        _check(abs(ph["p2"]["sum_12m_elapsed_pct"] - 100.0) < 1e-6, f"P2 sum != 100%: {c['record_id']}")
        _check(abs(ph["pass_eval"]["sum_12m_pct"] - 100.0) < 1e-6, f"PassEval sum != 100%: {c['record_id']}")
        sc = c["scorecard"]
        _check(sc["overall_grade"] != "UNKNOWN_LEGACY_UNINSTRUMENTED", f"UNKNOWN overall grade: {c['record_id']}")
        for pk in ("p1", "p2", "pass_eval", "funded_12m"):
            _check(
                sc["phase_grades"][pk]["grade"] != "UNKNOWN_LEGACY_UNINSTRUMENTED",
                f"UNKNOWN phase {pk}: {c['record_id']}",
            )
        if c["schedule_id"] == "T5_MAX_THROTTLE_YOLO":
            _check(rcs.TAG_RESEARCH_BOUNDARY in c["mandatory_tags"], f"T5 missing boundary tag: {c['record_id']}")
            _check(rcs.TAG_FTMO_GAMBLING in c["mandatory_tags"], f"T5 missing gambling tag: {c['record_id']}")
        if c["cohort"] != "CORE_PORT_7E":
            _check(rcs.TAG_OOF_SUBSET in c["mandatory_tags"], f"OOF missing subset tag: {c['record_id']}")
            _check(rcs.TAG_RESEARCH_PROTO in c["mandatory_tags"], f"OOF missing prototype tag: {c['record_id']}")

    for c in all_doc["tier_b_fleet_cases"]:
        _check(c["max_cash_accounting_err_usd"] < 1e-5, f"accounting err in {c['record_id']}")
        _check(c["max_active_base_funded_usd"] <= 400_000.01, f"FTMO 400K cap breached in {c['record_id']}")
        for hk, hpart in c["monthly_pass_fail_pending"].items():
            _check(abs(hpart["sum_pct"] - 100.0) < 1e-6, f"Fleet {hk} sum != 100%: {c['record_id']}")
        sc = c["scorecard"]
        for pk in ("p1", "p2", "pass_eval", "funded_12m"):
            _check(
                sc["phase_grades"][pk]["grade"] != "UNKNOWN_LEGACY_UNINSTRUMENTED",
                f"Fleet UNKNOWN phase {pk}: {c['record_id']}",
            )

    # 4. Verify Unified DuckDB Catalog integrity & Wave 4 vs Wave 5 SQL comparison (read-only)
    with ec.UnifiedEvaluationCatalog(duckdb_path=db_p, registry_path=reg_p, read_only=True) as cat:
        ver = cat.verify_integrity()
        _check(ver["verified"] is True, "Production UnifiedEvaluationCatalog integrity FAILED!")
        _check(ver["mc_by_campaign"].get("offensive4") == 168, "Wave 4 rows altered!")
        _check(ver["mc_by_campaign"].get("offensive5_spectrum") == 1062, f"Unexpected spectrum rows: {ver}")
        sql_cmp = rcs.query_wave4_vs_wave5_sql(cat)
        _check(len(sql_cmp["paired_162_cell_deltas"]) == 6, "Expected 6 Wave 5 tiers in 162-cell SQL join")
        for row in sql_cmp["paired_162_cell_deltas"]:
            _check(row["n_matched_cells"] == 162, f"Expected 162 matched cells for {row}")

    _check(_sha256_file(db_p) == db_sha_0, "Production DuckDB SHA mutated during read-only test!")
    _check(_sha256_file(reg_p) == reg_sha_0, "Production registry SHA mutated during read-only test!")
    _check(_sha256_file(sum_p) == sum_sha_0, "Production summary SHA mutated during read-only test!")
