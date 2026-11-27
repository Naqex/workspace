"""Comprehensive unit, oracle-parity, and negative-mutation tests for Naqex Quant Core SSOT."""

from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError
from quant_core.decimal_oracle import (
    DailyObservation,
    DecimalOracleParams,
    assert_penny_parity,
    replay_prop_lifecycle_decimal,
)
from quant_core.metrics import (
    _hansen_hac_variance,
    combinatorial_purged_cv,
    compute_drawdowns,
    compute_pbo_cscv,
    compute_sharpe,
    deflated_sharpe_ratio_empirical,
    firm_reset_day_key,
    firm_reset_midnight_utc,
    hansen_spa_test,
    white_reality_check,
)
from quant_core.mql_contract_drift import main as drift_cli_main
from quant_core.mql_contract_drift import run_drift_audit
from quant_core.prop_sim import (
    STAGE_DEAD,
    STAGE_FUNDED,
    STAGE_P1,
    PropSimParams,
    simulate_lifecycle,
    simulate_single_path,
)
from quant_core.schemas import (
    AdversarialAuditReceipt,
    FirmTierContract,
    FxRatesConfig,
    HandoffEnvelope,
    NegativeMutationRecord,
    SSOTFirmsCatalog,
    SSOTRiskProfiles,
)

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
SSOT_DIR = AI_ENGINES_DIR / "configs/ssot"
LEGACY_CONFIGS_DIR = AI_ENGINES_DIR / "configs"
EXPORTS_DIR = AI_ENGINES_DIR / "exports"
QUANT_CORE_DIR = AI_ENGINES_DIR / "quant_core"


def _sample_valid_contract(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "contract_id": "test_ftmo_10k",
        "firm_id": "ftmo",
        "program_id": "ftmo_2step_standard",
        "display_name": "Test FTMO 10K",
        "account_type": "Standard",
        "steps": 2,
        "capital_usd": 10000.0,
        "available_vn": True,
        "fee_orig_usd": 98.61,
        "fee_promo_usd": 68.70,
        "promo_discount_frac": 0.30,
        "promo_label": "BLACK_FRIDAY_2026_VN",
        "p1_target_frac": 0.10,
        "p2_target_frac": 0.05,
        "daily_loss_limit_frac": 0.05,
        "static_loss_limit_frac": 0.10,
        "dd_type": "static",
        "daily_pause_only": False,
        "dd_anchor_tag": "DD_ANCHOR_BALANCE_VERIFIED",
        "daily_dd_anchor_mode": "MIDNIGHT_BALANCE_OVER_INITIAL",
        "reset_tz": "Europe/Prague",
        "min_trading_days": 4,
        "min_profitable_days": 0,
        "profitable_day_threshold_frac": 0.0,
        "payout_split_frac": 0.80,
        "payout_split_max_frac": 0.90,
        "payout_cycle_cal_days": 14,
        "payout_settlement_lag_cal_days": 3,
        "min_payout_usd": 50.0,
        "fee_refund_external_cash_frac": 1.0,
        "fee_refund_hub_credit_frac": 0.0,
        "fee_refund_milestone": "FIRST_PAYOUT",
        "card_fx_fee_frac": 0.025,
        "withdrawal_fee_frac": 0.015,
        "leverage_fx": 100,
        "leverage_indices": 50,
        "news_restricted_eval": False,
        "news_restricted_funded": True,
        "news_window_sec": 120,
        "overnight_weekend_allowed": False,
        "requires_ea_written_clearance": False,
        "execution_status": "MEASURED_DEMO_EXECUTION",
        "verified_utc": "2026-11-26T11:25:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Pydantic v2 SSOT Schemas & Reconciled Configs
# ---------------------------------------------------------------------------


class TestSSOTConfigsAndSchemas:
    def test_ssot_fx_rates_matches_pricing_catalog(self) -> None:
        fx = FxRatesConfig.model_validate(json.loads((SSOT_DIR / "fx_rates.json").read_text(encoding="utf-8")))
        legacy_pricing = json.loads((LEGACY_CONFIGS_DIR / "prop_pricing_catalog.json").read_text(encoding="utf-8"))
        assert fx.usd_vnd == pytest.approx(legacy_pricing["fx_rates"]["usd_vnd"])
        assert fx.eur_usd == pytest.approx(legacy_pricing["fx_rates"]["eur_usd"])
        assert fx.eur_vnd == pytest.approx(legacy_pricing["fx_rates"]["eur_vnd"])
        assert len(fx.fingerprint()) == 64

    def test_ssot_firms_catalog_reconciled_truth(self) -> None:
        cat = SSOTFirmsCatalog.model_validate(json.loads((SSOT_DIR / "firms_catalog.json").read_text(encoding="utf-8")))
        assert cat.vn_card_fx_fee_frac == pytest.approx(0.025)
        assert cat.vn_withdrawal_fee_frac == pytest.approx(0.015)

        ftmo_std = cat.contracts["ftmo_standard_10k"]
        assert ftmo_std.available_vn is True
        assert ftmo_std.fee_orig_usd == pytest.approx(98.61)
        assert ftmo_std.fee_promo_usd == pytest.approx(68.70)
        assert ftmo_std.payout_cycle_cal_days == 14
        assert ftmo_std.card_fx_fee_frac == pytest.approx(0.025)
        assert ftmo_std.withdrawal_fee_frac == pytest.approx(0.015)
        assert ftmo_std.reset_tz == "Europe/Prague"
        assert ftmo_std.execution_status == "MEASURED_DEMO_EXECUTION"
        assert ftmo_std.dd_anchor_tag == "DD_ANCHOR_BALANCE_VERIFIED"

        ftmo_sw10 = cat.contracts["ftmo_swing_10k"]
        assert ftmo_sw10.available_vn is True
        assert ftmo_sw10.fee_orig_usd == pytest.approx(109.69)
        for unavailable_id in ("ftmo_swing_50k", "ftmo_swing_100k", "ftmo_swing_200k"):
            assert cat.contracts[unavailable_id].available_vn is False

        t5_classic = cat.contracts["the5ers_hs_5k_classic"]
        t5_new = cat.contracts["the5ers_hs_5k_new"]
        assert t5_classic.fee_orig_usd == pytest.approx(39.0)
        assert t5_classic.p1_target_frac == pytest.approx(0.08)
        assert t5_new.fee_orig_usd == pytest.approx(35.0)
        assert t5_new.p1_target_frac == pytest.approx(0.10)
        assert t5_classic.reset_tz == "America/New_York"
        assert t5_classic.execution_status == "TERMS_VERIFIED_EXECUTION_UNMEASURED"
        assert t5_classic.dd_anchor_tag == "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET"

        ic10 = cat.contracts["ic_funded_2step_10k"]
        assert ic10.fee_orig_usd == pytest.approx(125.0)
        assert ic10.payout_cycle_cal_days == 14
        assert ic10.fee_refund_milestone == "THIRD_PAYOUT"

        for cid, contract in cat.contracts.items():
            assert contract.payout_cycle_cal_days == 14, f"{cid} must unify payout_cycle_cal_days=14"
            assert contract.card_fx_fee_frac == pytest.approx(0.025)

    def test_ssot_risk_profiles_c10_news_on(self) -> None:
        rp = SSOTRiskProfiles.model_validate(json.loads((SSOT_DIR / "risk_profiles.json").read_text(encoding="utf-8")))
        assert rp.primary_profile_id == "C10_NEWS_ON"
        c10 = rp.profiles["C10_NEWS_ON"]
        assert c10.portfolio_id == "PORT_7E"
        assert c10.brake_mode == "RELATIVE_TO_PHASE_MULT"
        assert c10.amber_mult == pytest.approx(0.65)
        assert c10.red_mult == pytest.approx(0.40)
        assert c10.daily_headroom_taper_threshold_frac == pytest.approx(0.02)
        assert len(c10.engines) == 7
        assert c10.engines[0].base_risk_pct == pytest.approx(0.1606)
        assert c10.engines[1].base_risk_pct == pytest.approx(0.5894)
        for pkey in ("p1", "p2", "funded"):
            assert c10.phases[pkey].enable_red_news_guard is True

    def test_legacy_configs_remain_backward_compatible(self) -> None:
        contracts_v2 = json.loads((LEGACY_CONFIGS_DIR / "prop_contracts_v2.json").read_text(encoding="utf-8"))
        assert "ftmo_standard_10k" in contracts_v2["contracts"]
        firm_files = sorted((LEGACY_CONFIGS_DIR / "firms").glob("*.json"))
        assert len(firm_files) >= 4
        for fp in firm_files:
            data = json.loads(fp.read_text(encoding="utf-8"))
            assert "id" in data and "capital_usd" in data

    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_pydantic_rejects_nan_and_inf(self, bad_val: float) -> None:
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(fee_orig_usd=bad_val))
        with pytest.raises(ValidationError):
            FxRatesConfig.model_validate(
                {
                    "usd_vnd": bad_val,
                    "eur_usd": 1.09595,
                    "eur_vnd": 28238.19,
                    "verified_utc": "2026-11-26T11:26:20Z",
                    "source": "test",
                }
            )

    @pytest.mark.parametrize(
        "field,bad_val",
        [
            ("capital_usd", True),
            ("fee_orig_usd", False),
            ("p1_target_frac", True),
            ("payout_cycle_cal_days", True),
            ("steps", True),
            ("min_trading_days", False),
            ("leverage_fx", True),
        ],
    )
    def test_pydantic_rejects_bool_disguised_as_number(self, field: str, bad_val: bool) -> None:
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(**{field: bad_val}))

    def test_pydantic_rejects_future_timestamp_and_naive_datetime(self) -> None:
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(verified_utc="2099-01-01T00:00:00Z"))
        near_future = (datetime.now(UTC) + timedelta(seconds=600)).isoformat()
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(verified_utc=near_future))
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(verified_utc="2026-11-26T11:25:00"))
        # Raw Unix numeric / bool timestamps MUST fail closed (never silently coerce 0 -> 1970-01-01)
        for bad_ts in (0, 1700000000, 0.0, True, False, ""):
            with pytest.raises(ValidationError):
                FirmTierContract.model_validate(_sample_valid_contract(verified_utc=bad_ts))

    def test_pydantic_rejects_mixed_frac_pct_and_bad_tz_and_extra_and_mutation(self) -> None:
        # Mixed percent (> 1.0) in _frac field
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(p1_target_frac=10.0))
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(card_fx_fee_frac=2.5))
        # Invalid IANA reset_tz
        for bad_tz in ("UTC+2", "NY_CLOSE_SERVER", "Not/AZone", " Europe/Prague"):
            with pytest.raises(ValidationError):
                FirmTierContract.model_validate(_sample_valid_contract(reset_tz=bad_tz))
        # Extra field forbidden
        with pytest.raises(ValidationError):
            FirmTierContract.model_validate(_sample_valid_contract(mystery_key=123))
        # Frozen immutability
        valid = FirmTierContract.model_validate(_sample_valid_contract())
        with pytest.raises(ValidationError):
            setattr(valid, "fee_orig_usd", 1.0)  # noqa: B010

    def test_adversarial_audit_receipt_and_handoff_envelope_contracts(self) -> None:
        sha_a = "a" * 64
        sha_b = "b" * 64
        # Passed receipt with zero mutations MUST fail
        with pytest.raises(ValidationError):
            AdversarialAuditReceipt(
                audit_id="audit-001",
                target_path="tooling/ai-engines/quant_core/prop_sim.py",
                target_sha256=sha_a,
                audited_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
                vectors_checked=("V1_POISONED_INPUT",),
                negative_mutations=(),
                passed=True,
            )
        # Passed receipt with observed_failed=False MUST fail
        with pytest.raises(ValidationError):
            AdversarialAuditReceipt(
                audit_id="audit-002",
                target_path="tooling/ai-engines/quant_core/prop_sim.py",
                target_sha256=sha_a,
                audited_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
                vectors_checked=("V7_NEGATIVE_MUTATION",),
                negative_mutations=(
                    NegativeMutationRecord(
                        mutation_id="mut-1",
                        description="inject 2c error",
                        observed_failed=False,
                        evidence_ref="pytest",
                    ),
                ),
                passed=True,
            )

        receipt = AdversarialAuditReceipt(
            audit_id="audit-003",
            target_path="tooling/ai-engines/quant_core/prop_sim.py",
            target_sha256=sha_a,
            audited_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
            vectors_checked=("V1_POISONED_INPUT", "V4_STATE_MACHINE", "V7_NEGATIVE_MUTATION"),
            negative_mutations=(
                NegativeMutationRecord(
                    mutation_id="mut-1",
                    description="raw 6% daily loss with 3.5% EA stop must breach",
                    observed_failed=True,
                    evidence_ref="test_prop_sim_breach_before_ea_cut",
                ),
            ),
            caveats=("Offline Dev tape only; live broker tick latency unmeasured for The5ers/IC Funded.",),
            passed=True,
        )
        assert len(receipt.fingerprint()) == 64

        # HandoffEnvelope rejects self-loop and VERIFIED without audit_receipt_sha256
        with pytest.raises(ValidationError):
            HandoffEnvelope(
                handoff_id="h-1",
                from_stage="strategy-qualification",
                to_stage="strategy-qualification",
                created_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
                artifact_paths=("a.json",),
                artifact_sha256={"a.json": sha_a},
                summary="self loop",
                status="READY",
            )
        with pytest.raises(ValidationError):
            HandoffEnvelope(
                handoff_id="h-2",
                from_stage="strategy-qualification",
                to_stage="adversarial-self-audit",
                created_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
                artifact_paths=("a.json",),
                artifact_sha256={"a.json": sha_a},
                summary="missing receipt hash",
                status="VERIFIED",
            )

        env = HandoffEnvelope(
            handoff_id="h-3",
            from_stage="quant-factory-ops",
            to_stage="adversarial-self-audit",
            created_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
            artifact_paths=("tooling/ai-engines/quant_core/prop_sim.py",),
            artifact_sha256={"tooling/ai-engines/quant_core/prop_sim.py": sha_b},
            summary="SSOT prop simulator handed off for adversarial verification",
            status="VERIFIED",
            audit_receipt_sha256=receipt.fingerprint(),
        )
        assert env.execution_capability is False
        assert env.order_send_count == 0
        assert env.holdout_rows_analysed == 0


# ---------------------------------------------------------------------------
# 2. Canonical Metrics & DST Reset Clock
# ---------------------------------------------------------------------------


class TestQuantMetrics:
    def test_metrics_module_has_zero_scipy_imports(self) -> None:
        tree = ast.parse((QUANT_CORE_DIR / "metrics.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("scipy"), f"forbidden scipy import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("scipy"), f"forbidden scipy import: {node.module}"

    def test_compute_sharpe_active_vs_calendar_days(self) -> None:
        returns = [0.01, 0.0, 0.0, 0.02, 0.0, -0.005, 0.0, 0.015, 0.0, 0.0]
        cal = compute_sharpe(returns, annualization_days=252, calendar_aligned=True)
        act = compute_sharpe(returns, annualization_days=252, calendar_aligned=False)
        assert cal.calendar_days == 10
        assert cal.active_days == 4
        assert act.calendar_days == 10
        assert act.active_days == 4

        arr = np.array(returns, dtype=np.float64)
        expected_cal = float(np.mean(arr) / np.std(arr, ddof=1) * math.sqrt(252.0))
        arr_act = arr[arr != 0.0]
        expected_act = float(np.mean(arr_act) / np.std(arr_act, ddof=1) * math.sqrt(252.0))
        assert cal.sharpe_annualized == pytest.approx(expected_cal, rel=1e-12)
        assert act.sharpe_annualized == pytest.approx(expected_act, rel=1e-12)
        assert act.sharpe_annualized != pytest.approx(cal.sharpe_annualized)

    def test_compute_drawdowns_both_initial_and_peak_with_intraday_lows(self) -> None:
        # Initial 10k -> rises to 12k -> dips intraday to 9.4k (closes 9.6k) -> recovers to 11k
        eq = [10000.0, 12000.0, 9600.0, 11000.0]
        lows = [9900.0, 11800.0, 9400.0, 10800.0]
        dd_close = compute_drawdowns(eq, 10000.0)
        assert dd_close.dd_of_initial_frac == pytest.approx((10000.0 - 9600.0) / 10000.0)
        assert dd_close.dd_of_peak_frac == pytest.approx((12000.0 - 9600.0) / 12000.0)

        dd_intra = compute_drawdowns(eq, 10000.0, intraday_lows=lows)
        assert dd_intra.dd_of_initial_frac == pytest.approx((10000.0 - 9400.0) / 10000.0)
        assert dd_intra.dd_of_peak_frac == pytest.approx((12000.0 - 9400.0) / 12000.0)
        assert dd_intra.used_intraday_lows is True

        with pytest.raises(ValueError):
            compute_drawdowns(eq, 10000.0, intraday_lows=[10500.0, 12000.0, 9600.0, 11000.0])

    def test_dsr_empirical_oracle_and_fail_closed_no_proxy(self) -> None:
        rng = np.random.default_rng(42)
        rets = rng.normal(loc=0.002, scale=0.01, size=250)

        # MUST raise ValueError when n_trials > 1 without trial_sharpes or sr_trials_var
        with pytest.raises(ValueError, match="no 1/\\(T-1\\) proxy"):
            deflated_sharpe_ratio_empirical(rets, n_trials=20)

        trial_srs = np.array([0.05, 0.10, 0.12, 0.18, 0.22, 0.08, 0.14, 0.03, 0.19, 0.11])
        res = deflated_sharpe_ratio_empirical(rets, trial_sharpes=trial_srs)

        # Direct independent oracle calculation (Bailey & Lopez de Prado 2014 Eq. 2 & 8)
        sr_obs = float(np.mean(rets) / np.std(rets, ddof=1))
        c = rets - np.mean(rets)
        m2 = float(np.mean(c**2))
        skew = float(np.mean(c**3) / (m2**1.5))
        kurt = float(np.mean(c**4) / (m2**2))
        var_trials = float(np.var(trial_srs, ddof=1))
        nd = NormalDist(0.0, 1.0)
        emc = 0.5772156649015329
        n_tr = len(trial_srs)
        sr_star = math.sqrt(var_trials) * (
            (1.0 - emc) * nd.inv_cdf(1.0 - 1.0 / n_tr) + emc * nd.inv_cdf(1.0 - 1.0 / (n_tr * math.e))
        )
        z_exp = ((sr_obs - sr_star) * math.sqrt(len(rets) - 1)) / math.sqrt(
            1.0 - skew * sr_obs + ((kurt - 1.0) / 4.0) * sr_obs**2
        )
        dsr_exp = nd.cdf(z_exp)

        assert res.expected_max_sr == pytest.approx(sr_star, rel=1e-12)
        assert res.dsr == pytest.approx(dsr_exp, rel=1e-12)
        assert res.n_trials == n_tr

        # Explicit sr_trials_var reproduces exact same DSR
        res2 = deflated_sharpe_ratio_empirical(rets, sr_trials_var=var_trials, n_trials=n_tr)
        assert res2.dsr == pytest.approx(res.dsr, rel=1e-12)

        # More trials strictly lowers DSR
        res_more = deflated_sharpe_ratio_empirical(rets, sr_trials_var=var_trials, n_trials=200)
        assert res_more.dsr < res.dsr

        # Single trial reduces to PSR against SR* = 0
        res1 = deflated_sharpe_ratio_empirical(rets, n_trials=1)
        assert res1.expected_max_sr == 0.0
        assert res1.dsr > res.dsr

    def test_pbo_cscv_matches_bruteforce_oracle_and_detects_overfitting(self) -> None:
        rng = np.random.default_rng(123)
        mat = rng.normal(0.0, 0.01, size=(24, 4))
        fast = compute_pbo_cscv(mat, n_slices=4)

        # Brute-force naive CSCV oracle
        slices = [mat[i * 6 : (i + 1) * 6] for i in range(4)]
        naive_logits: list[float] = []
        for combo in itertools.combinations(range(4), 2):
            comp = [i for i in range(4) if i not in combo]
            is_data = np.vstack([slices[i] for i in combo])
            oos_data = np.vstack([slices[i] for i in comp])
            is_sr = np.mean(is_data, axis=0) / np.std(is_data, axis=0, ddof=1)
            oos_sr = np.mean(oos_data, axis=0) / np.std(oos_data, axis=0, ddof=1)
            w = int(np.argmax(is_sr))
            n_less = int(np.sum(oos_sr < oos_sr[w]))
            n_eq = int(np.sum(oos_sr == oos_sr[w]))
            rank = n_less + 0.5 * (n_eq + 1.0)
            omega = rank / 5.0
            naive_logits.append(math.log(omega / (1.0 - omega)))

        assert fast.n_combinations == 6
        assert len(fast.logit_distribution) == 6
        assert np.allclose(fast.logit_distribution, naive_logits, atol=1e-12)

        # Dominant true-alpha strategy -> low PBO, is_overfit=False (full 16 slices = 12,870 combos)
        alpha_mat = rng.normal(0.0, 0.01, size=(160, 8))
        alpha_mat[:, 0] += 0.012
        res_alpha = compute_pbo_cscv(alpha_mat, n_slices=16)
        assert res_alpha.n_combinations == math.comb(16, 8)
        assert res_alpha.pbo < 0.05
        assert res_alpha.is_overfit is False

        # Adversarial overfit: each strategy wins ONLY in one specific slice and loses everywhere else
        overfit_mat = np.full((160, 16), -0.002, dtype=np.float64)
        for s in range(16):
            overfit_mat[s * 10 : (s + 1) * 10, s] = 0.05 + 0.001 * s
            overfit_mat[:, s] += rng.normal(0.0, 0.0002, size=160)
        res_overfit = compute_pbo_cscv(overfit_mat, n_slices=8)
        assert res_overfit.pbo > 0.50
        assert res_overfit.is_overfit is True

    def test_cpcv_zero_overlap_and_exact_purge_embargo(self) -> None:
        splits = combinatorial_purged_cv(60, n_groups=6, k_test_groups=2, purge_bars=2, embargo_bars=3)
        assert len(splits) == math.comb(6, 2) == 15

        for sp in splits:
            train_set = set(sp.train_indices)
            test_set = set(sp.test_indices)
            assert train_set.isdisjoint(test_set)
            assert train_set.isdisjoint(set(sp.purged_indices))
            assert train_set.isdisjoint(set(sp.embargoed_indices))
            # Check exact distance across every boundary
            for te in sp.test_indices:
                for p in range(1, 3):
                    if te - p >= 0 and (te - p) not in test_set:
                        assert (te - p) not in train_set
                for e in range(1, 4):
                    if te + e < 60 and (te + e) not in test_set:
                        assert (te + e) not in train_set

        # Verify adjacent test groups (1, 2) -> indices 10..29 merge into 1 segment:
        # purge = {8, 9}, embargo = {30, 31, 32}
        adj = next(s for s in splits if s.test_groups == (1, 2))
        assert adj.purged_indices == (8, 9)
        assert adj.embargoed_indices == (30, 31, 32)

        # Verify disjoint test groups (1, 4) -> 10..19 and 40..49:
        # purge = {8, 9, 38, 39}, embargo = {20, 21, 22, 50, 51, 52}
        disj = next(s for s in splits if s.test_groups == (1, 4))
        assert disj.purged_indices == (8, 9, 38, 39)
        assert disj.embargoed_indices == (20, 21, 22, 50, 51, 52)

    def test_hansen_spa_and_white_rc_oracle_and_ordering(self) -> None:
        rng = np.random.default_rng(2026)
        # Verify FFT HAC variance matches naive double-sum Hansen (2005) Eq. 5 to 1e-12
        small = rng.normal(0.0, 0.01, size=(40, 3))
        block_len = 5
        q = 1.0 / block_len
        fast_hac = _hansen_hac_variance(small, block_len)
        c = small - np.mean(small, axis=0, keepdims=True)
        n = small.shape[0]
        gamma0 = np.mean(c * c, axis=0)
        naive_hac = gamma0.copy()
        for lag in range(1, n):
            gam = np.sum(c[: n - lag] * c[lag:], axis=0) / float(n)
            kappa = ((n - lag) / n) * ((1.0 - q) ** lag) + (lag / n) * ((1.0 - q) ** (n - lag))
            naive_hac += 2.0 * kappa * gam
        assert np.allclose(fast_hac, naive_hac, atol=1e-12)

        # Multi-model with strong winner + irrelevant deeply negative decoy models
        # (showcases Hansen's lower <= consistent <= upper ordering!)
        mixed = rng.normal(0.0, 0.01, size=(200, 6))
        mixed[:, 0] += 0.0025  # moderate winner
        mixed[:, 3:] -= 0.015  # deeply losing decoys
        spa = hansen_spa_test(mixed, n_boot=500, block_len=5, seed=20261127)
        assert 0.0 <= spa.spa_p_lower <= spa.spa_p_consistent <= spa.spa_p_upper <= 1.0
        assert spa.best_model_index == 0
        assert spa.spa_p_consistent < 0.05

        wrc = white_reality_check(mixed, n_boot=500, block_len=5, seed=20261127)
        assert 0.0 <= wrc.p_value <= 1.0
        assert wrc.best_model_index == 0
        assert wrc.p_value < 0.05

        # All-losing models -> SPA t_stat == 0, p == 1.0; White RC p > 0.50
        losers = rng.normal(-0.01, 0.01, size=(120, 4))
        spa_lose = hansen_spa_test(losers, n_boot=300, block_len=5, seed=20261127)
        assert spa_lose.t_stat == 0.0
        assert spa_lose.spa_p_consistent == 1.0
        wrc_lose = white_reality_check(losers, n_boot=300, block_len=5, seed=20261127)
        assert wrc_lose.p_value > 0.50

        # Vector-1 fail-closed validation on invalid bootstrap params (even on all-losing early-return path!)
        for bad_kw in (
            {"block_len": 0},
            {"block_len": -5},
            {"block_len": True},
            {"n_boot": 0},
            {"n_boot": -5},
            {"n_boot": True},
            {"seed": True},
        ):
            with pytest.raises(ValueError):
                hansen_spa_test(losers, **bad_kw)  # type: ignore[arg-type]
            with pytest.raises(ValueError):
                white_reality_check(losers, **bad_kw)  # type: ignore[arg-type]
        for bad_bl in (0, -3, True):
            with pytest.raises(ValueError):
                _hansen_hac_variance(losers, bad_bl)  # type: ignore[arg-type]

    def test_firm_reset_day_key_dst_prague_and_new_york(self) -> None:
        # Europe/Prague Spring Forward: Last Sunday of March 2026 is 2026-03-29 (01:00 UTC: CET+1 -> CEST+2)
        assert firm_reset_day_key(datetime(2026, 3, 28, 22, 59, 59, tzinfo=UTC), "Europe/Prague") == "2026-03-28"
        assert firm_reset_day_key(datetime(2026, 3, 28, 23, 0, 0, tzinfo=UTC), "Europe/Prague") == "2026-03-29"
        assert firm_reset_day_key(datetime(2026, 3, 29, 0, 59, 59, tzinfo=UTC), "Europe/Prague") == "2026-03-29"
        assert firm_reset_day_key(datetime(2026, 3, 29, 1, 0, 0, tzinfo=UTC), "Europe/Prague") == "2026-03-29"
        assert firm_reset_day_key(datetime(2026, 3, 29, 21, 59, 59, tzinfo=UTC), "Europe/Prague") == "2026-03-29"
        assert firm_reset_day_key(datetime(2026, 3, 29, 22, 0, 0, tzinfo=UTC), "Europe/Prague") == "2026-03-30"
        # Exact midnight UTC for midday on Spring-Forward Sunday is 2026-03-28T23:00:00Z (NOT 22:00:00Z!)
        expected_spring_mid = int(datetime(2026, 3, 28, 23, 0, 0, tzinfo=UTC).timestamp())
        assert (
            firm_reset_midnight_utc(datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC), "Europe/Prague") == expected_spring_mid
        )

        # Europe/Prague Fall Back: Last Sunday of Oct 2026 is 2026-10-25 (01:00 UTC: CEST+2 -> CET+1)
        assert firm_reset_day_key(datetime(2026, 10, 24, 21, 59, 59, tzinfo=UTC), "Europe/Prague") == "2026-10-24"
        assert firm_reset_day_key(datetime(2026, 10, 24, 22, 0, 0, tzinfo=UTC), "Europe/Prague") == "2026-10-25"
        assert firm_reset_day_key(datetime(2026, 10, 25, 22, 59, 59, tzinfo=UTC), "Europe/Prague") == "2026-10-25"
        assert firm_reset_day_key(datetime(2026, 10, 25, 23, 0, 0, tzinfo=UTC), "Europe/Prague") == "2026-10-26"
        expected_fall_mid = int(datetime(2026, 10, 24, 22, 0, 0, tzinfo=UTC).timestamp())
        assert (
            firm_reset_midnight_utc(datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC), "Europe/Prague") == expected_fall_mid
        )

        # America/New_York Spring Forward (2026-03-08: EST-5 -> EDT-4)
        assert firm_reset_day_key(datetime(2026, 3, 8, 4, 59, 59, tzinfo=UTC), "America/New_York") == "2026-03-07"
        assert firm_reset_day_key(datetime(2026, 3, 8, 5, 0, 0, tzinfo=UTC), "America/New_York") == "2026-03-08"
        assert firm_reset_day_key(datetime(2026, 3, 9, 3, 59, 59, tzinfo=UTC), "America/New_York") == "2026-03-08"
        assert firm_reset_day_key(datetime(2026, 3, 9, 4, 0, 0, tzinfo=UTC), "America/New_York") == "2026-03-09"

        with pytest.raises(ValueError):
            firm_reset_day_key(datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC), "UTC+2")
        with pytest.raises(ValueError):
            firm_reset_day_key(datetime(2026, 3, 29, 12, 0, 0), "Europe/Prague")


# ---------------------------------------------------------------------------
# 3. Prop Lifecycle Simulator vs Zero-Shared-Import Decimal Oracle
# ---------------------------------------------------------------------------


def _to_oracle_params(p: PropSimParams) -> DecimalOracleParams:
    return DecimalOracleParams(
        steps=p.steps,
        capital_usd=Decimal(str(p.capital_usd)),
        fee_usd=Decimal(str(p.fee_usd)),
        fee_refund_ratio=Decimal(str(p.fee_refund_ratio)),
        p1_target_frac=Decimal(str(p.p1_target_frac)),
        p2_target_frac=Decimal(str(p.p2_target_frac)),
        daily_loss_limit_frac=Decimal(str(p.daily_loss_limit_frac)),
        static_loss_limit_frac=Decimal(str(p.static_loss_limit_frac)),
        daily_pause_only=p.daily_pause_only,
        min_days=p.min_days,
        min_prof_day_frac=Decimal(str(p.min_prof_day_frac)),
        funded_cap_mult=Decimal(str(p.funded_cap_mult)),
        payout_split_frac=Decimal(str(p.payout_split_frac)),
        payout_cycle_days=p.payout_cycle_days,
        max_retries=p.max_retries,
        retry_discounts=tuple(Decimal(str(x)) for x in p.retry_discounts),
        p1_mult=Decimal(str(p.p1_mult)),
        p2_mult=Decimal(str(p.p2_mult)),
        funded_mult=Decimal(str(p.funded_mult)),
        amber_dd_frac=Decimal(str(p.amber_dd_frac)),
        amber_mult=Decimal(str(p.amber_mult)),
        red_dd_frac=Decimal(str(p.red_dd_frac)),
        red_mult=Decimal(str(p.red_mult)),
        ea_daily_stop_frac=Decimal(str(p.ea_daily_stop_frac)),
        p1_profit_lock_trigger_frac=Decimal(str(p.p1_profit_lock_trigger_frac)),
        p1_profit_lock_mult=Decimal(str(p.p1_profit_lock_mult)),
        p2_profit_lock_trigger_frac=Decimal(str(p.p2_profit_lock_trigger_frac)),
        p2_profit_lock_mult=Decimal(str(p.p2_profit_lock_mult)),
        funded_profit_lock_trigger_frac=Decimal(str(p.funded_profit_lock_trigger_frac)),
        funded_profit_lock_mult=Decimal(str(p.funded_profit_lock_mult)),
        require_flat_for_pass=p.require_flat_for_pass,
    )


class TestPropSimAndDecimalOracle:
    def test_decimal_oracle_has_zero_shared_imports(self) -> None:
        tree = ast.parse((QUANT_CORE_DIR / "decimal_oracle.py").read_text(encoding="utf-8"))
        allowed_roots = {"__future__", "collections", "dataclasses", "decimal", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root in allowed_roots, f"decimal_oracle must not import {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                assert root in allowed_roots, f"decimal_oracle must not import from {node.module}"

    def test_bug_a_fix_real_daily_breach_checked_before_ea_daily_stop(self) -> None:
        # Raw daily DD = $600 (6% > 5% firm daily limit) while ea_daily_stop = 3.5% ($350).
        # Legacy prop_engine.py silently capped DD to $375 and missed the breach!
        # Fixed prop_sim.py MUST detect the real daily breach BEFORE applying ea_daily_stop.
        params = PropSimParams(
            capital_usd=10000.0,
            fee_usd=98.61,
            daily_loss_limit_frac=0.05,
            static_loss_limit_frac=0.10,
            daily_pause_only=False,
            ea_daily_stop_frac=0.035,
            p1_mult=1.0,
            p2_mult=1.0,
            funded_mult=1.0,
            max_retries=0,
        )
        nets = [-550.0, 400.0, 400.0]
        dds = [600.0, 20.0, 20.0]
        flgs = [1, 1, 1]

        sim_nb = simulate_single_path(nets, dds, flgs, params, backend="numba")
        sim_py = simulate_single_path(nets, dds, flgs, params, backend="python")
        obs = [
            DailyObservation(Decimal(str(n)), Decimal(str(d)), f, 0) for n, d, f in zip(nets, dds, flgs, strict=True)
        ]
        oracle = replay_prop_lifecycle_decimal(obs, _to_oracle_params(params))

        assert oracle.breached_p1 is True
        assert oracle.final_stage == STAGE_DEAD
        assert oracle.dead_day == 1
        assert_penny_parity(oracle, sim_nb)
        assert_penny_parity(oracle, sim_py)

        # Contrast: raw DD = $400 (3.5% < 4.0% < 5.0% daily cap) does NOT breach and applies ea_daily_stop cut:
        # Day 1 closes -$380 -> bal=9620 (-3.8% triggers AMBER 0.65 on Day 2 -> +200*0.65=+130 -> 9750)
        nets_ok = [-380.0, 200.0]
        dds_ok = [400.0, 50.0]
        flgs_ok = [1, 1]
        sim_ok = simulate_single_path(nets_ok, dds_ok, flgs_ok, params, backend="numba")
        obs_ok = [
            DailyObservation(Decimal(str(n)), Decimal(str(d)), f, 0)
            for n, d, f in zip(nets_ok, dds_ok, flgs_ok, strict=True)
        ]
        oracle_ok = replay_prop_lifecycle_decimal(obs_ok, _to_oracle_params(params))
        assert oracle_ok.breached_p1 is False
        assert oracle_ok.final_stage == STAGE_P1
        assert oracle_ok.trace[0].eff_dd == Decimal("375.00000")
        assert oracle_ok.trace[1].mult == Decimal("0.650")
        assert oracle_ok.final_balance_usd == Decimal("9750.0")
        assert_penny_parity(oracle_ok, sim_ok)

    def test_daily_pause_only_mode_preserves_non_breaching_daily_cap_and_static_floor(self) -> None:
        params = PropSimParams(
            capital_usd=10000.0,
            fee_usd=100.0,
            daily_loss_limit_frac=0.05,
            static_loss_limit_frac=0.10,
            daily_pause_only=True,
            p1_mult=1.0,
            p2_mult=1.0,
            funded_mult=1.0,
            max_retries=0,
        )
        # Day 1: 6% intraday loss -> paused without daily breach (bal=9400, -6.0% triggers RED 0.40 on Day 2)
        # Day 2: -1200 * 0.40 = -480 -> 9400 - 480 = 8920 <= 9000 -> static floor breach -> DEAD!
        nets = [-600.0, -1200.0, 500.0]
        dds = [600.0, 1200.0, 0.0]
        flgs = [1, 1, 1]

        sim_nb = simulate_single_path(nets, dds, flgs, params, backend="numba")
        obs = [
            DailyObservation(Decimal(str(n)), Decimal(str(d)), f, 0) for n, d, f in zip(nets, dds, flgs, strict=True)
        ]
        oracle = replay_prop_lifecycle_decimal(obs, _to_oracle_params(params))

        assert oracle.trace[0].breached is False
        assert oracle.trace[0].bal_after == Decimal("9400.0")
        assert oracle.trace[1].mult == Decimal("0.40")
        assert oracle.trace[1].breached is True
        assert oracle.final_stage == STAGE_DEAD
        assert oracle.dead_day == 2
        assert_penny_parity(oracle, sim_nb)

    def test_bug_b_fix_zero_mulligan_dead_state_and_cf12_at_day_252(self) -> None:
        # max_retries=1 -> attempt 1 breaches on day 3 (retries as attempt 2), attempt 2 breaches on day 6 -> DEAD!
        # Remaining 254 days have huge +$400/day wins that MUST be ignored, while cf12 at day 252 MUST equal -2*fee!
        params = PropSimParams(
            capital_usd=10000.0,
            fee_usd=98.61,
            daily_loss_limit_frac=0.05,
            static_loss_limit_frac=0.10,
            max_retries=1,
            retry_discounts=(0.90,),
            p1_mult=1.0,
            p2_mult=1.0,
            funded_mult=1.0,
            ea_daily_stop_frac=0.035,
        )
        horizon = 260
        nets = [50.0] * horizon
        dds = [10.0] * horizon
        flgs = [1] * horizon
        # Breach attempt 1 on day 3 (index 2), breach attempt 2 on day 6 (index 5)
        nets[2], dds[2] = -600.0, 600.0
        nets[5], dds[5] = -600.0, 600.0
        for d in range(6, horizon):
            nets[d] = 400.0
            dds[d] = 0.0

        sim_nb = simulate_single_path(nets, dds, flgs, params, backend="numba")
        sim_py = simulate_single_path(nets, dds, flgs, params, backend="python")
        obs = [
            DailyObservation(Decimal(str(n)), Decimal(str(d)), f, 0) for n, d, f in zip(nets, dds, flgs, strict=True)
        ]
        oracle = replay_prop_lifecycle_decimal(obs, _to_oracle_params(params))

        expected_fees = Decimal("98.61") + Decimal("98.61") * Decimal("0.90")
        assert oracle.attempts == 2
        assert oracle.final_stage == STAGE_DEAD
        assert oracle.dead_day == 6
        assert oracle.pass_day == -1
        assert oracle.total_payouts_usd == Decimal("0")
        assert oracle.total_fees_usd == expected_fees
        assert oracle.cf12_usd == -expected_fees
        assert oracle.cf_terminal_usd == -expected_fees
        assert_penny_parity(oracle, sim_nb)
        assert_penny_parity(oracle, sim_py)

    def test_full_lifecycle_relative_amber_red_profit_lock_flat_pass_and_payouts(self) -> None:
        # Tests: relative AMBER (4*0.65=2.60) & RED (4*0.40=1.60), ProfitLock (+7% -> 2.50),
        # require_flat_for_pass=True blocking pass while open_positions=1, then P1->P2->Funded->2 Payouts!
        params = PropSimParams(
            steps=2,
            capital_usd=10000.0,
            fee_usd=98.61,
            fee_refund_ratio=1.0,
            p1_target_frac=0.10,
            p2_target_frac=0.05,
            daily_loss_limit_frac=0.05,
            static_loss_limit_frac=0.10,
            min_days=4,
            payout_split_frac=0.80,
            payout_cycle_days=5,
            max_retries=2,
            p1_mult=4.0,
            p2_mult=3.5,
            funded_mult=1.25,
            amber_dd_frac=0.035,
            amber_mult=0.65,
            red_dd_frac=0.060,
            red_mult=0.40,
            ea_daily_stop_frac=0.035,
            p1_profit_lock_trigger_frac=0.070,
            p1_profit_lock_mult=2.50,
            p2_profit_lock_trigger_frac=0.035,
            p2_profit_lock_mult=1.75,
            require_flat_for_pass=True,
        )
        # Tape of (net_1x, dd_1x, flg, open_pos)
        rows: list[tuple[float, float, int, int]] = [
            # Day 1 (P1, mult=4.0): -100 * 4 = -400 -> bal=9600 (-4% -> triggers AMBER next day!)
            (-100.0, 100.0, 1, 0),
            # Day 2 (P1 AMBER, rel mult=4.0*0.65=2.60): -100 * 2.6 = -260 -> bal=9340 (-6.6% -> RED next day!)
            (-100.0, 100.0, 1, 0),
            # Day 3 (P1 RED, rel mult=4.0*0.40=1.60): +250 * 1.6 = +400 -> bal=9740 (-2.6% -> NORMAL!)
            (250.0, 20.0, 1, 0),
            # Day 4 (P1 NORMAL, mult=4.0): +250 * 4.0 = +1000 -> bal=10740 (+7.4% -> ProfitLock 2.50 next day!)
            (250.0, 20.0, 1, 0),
            # Day 5 (P1 ProfitLock, mult=2.50): +120 * 2.5 = +300 -> bal=11040 >= 11000 & tdays=5>=4,
            # BUT open_positions=1 -> MUST NOT PASS P1 yet!
            (120.0, 10.0, 1, 1),
            # Day 6 (P1 ProfitLock, mult=2.50): +0, flat -> PASSES P1 -> P2!
            (0.0, 0.0, 0, 0),
            # Days 7..10 (P2, min_days=4): +60*3.5=+210 (10210), +60*3.5=+210 (10420, +4.2% -> PL 1.75),
            # +60*1.75=+105 (10525, tdays=3<4), +20*1.75=+35 (10560, tdays=4 -> PASSES P2 -> FUNDED!)
            (60.0, 10.0, 1, 0),
            (60.0, 10.0, 1, 0),
            (60.0, 10.0, 1, 0),
            (20.0, 5.0, 1, 0),
            # Days 11..15 (Funded, mult=1.25, cycle=5): +100*1.25=+125/d -> +625 -> payout #1 + fee refund!
            (100.0, 10.0, 1, 0),
            (100.0, 10.0, 1, 0),
            (100.0, 10.0, 1, 0),
            (100.0, 10.0, 1, 0),
            (100.0, 10.0, 1, 0),
            # Days 16..20 (Funded, cycle #2): +80*1.25=+100/d -> +500 -> payout #2 (NO second fee refund!)
            (80.0, 10.0, 1, 0),
            (80.0, 10.0, 1, 0),
            (80.0, 10.0, 1, 0),
            (80.0, 10.0, 1, 0),
            (80.0, 10.0, 1, 0),
        ]
        nets = [r[0] for r in rows]
        dds = [r[1] for r in rows]
        flgs = [r[2] for r in rows]
        opens = [r[3] for r in rows]

        sim_nb = simulate_single_path(nets, dds, flgs, params, open_positions=opens, backend="numba")
        sim_py = simulate_single_path(nets, dds, flgs, params, open_positions=opens, backend="python")
        obs = [DailyObservation(Decimal(str(n)), Decimal(str(d)), f, o) for n, d, f, o in rows]
        oracle = replay_prop_lifecycle_decimal(obs, _to_oracle_params(params))

        # Verify exact relative AMBER/RED and ProfitLock multipliers in trace
        assert oracle.trace[1].mult == Decimal("2.600")
        assert oracle.trace[2].mult == Decimal("1.600")
        assert oracle.trace[4].mult == Decimal("2.50")
        assert oracle.trace[4].stage_after == STAGE_P1  # blocked by open_positions=1!
        assert oracle.trace[5].stage_after == 2  # passed on flat day 6!
        assert oracle.pass_day == 10
        assert oracle.first_payout_day == 15
        assert oracle.final_stage == STAGE_FUNDED
        # Payout 1: 625 * 0.8 + 98.61 = 598.61; Payout 2: 500 * 0.8 = 400.00; Total = 998.61
        assert oracle.total_payouts_usd == Decimal("998.61")
        assert_penny_parity(oracle, sim_nb)
        assert_penny_parity(oracle, sim_py)

        # Negative-mutation proof: $0.02 perturbation MUST fail assert_penny_parity!
        poisoned = dict(sim_nb)
        poisoned["cf_terminal_usd"] = float(sim_nb["cf_terminal_usd"]) + 0.02
        with pytest.raises(AssertionError, match="cf_terminal_usd"):
            assert_penny_parity(oracle, poisoned)

    def test_prop_sim_and_decimal_oracle_reject_poisoned_inputs_fail_closed(self) -> None:
        # NaN / Inf / <=0 capital_usd / invalid steps / negative dd / OOB idx_matrix MUST raise ValueError
        for bad_params in (
            PropSimParams(capital_usd=float("nan")),
            PropSimParams(capital_usd=float("inf")),
            PropSimParams(capital_usd=0.0),
            PropSimParams(capital_usd=-1000.0),
            PropSimParams(funded_cap_mult=0.0),
            PropSimParams(fee_usd=-1.0),
            PropSimParams(steps=3),
            PropSimParams(payout_cycle_days=0),
            PropSimParams(max_retries=-1),
            PropSimParams(daily_loss_limit_frac=0.20, static_loss_limit_frac=0.10),
        ):
            with pytest.raises(ValueError):
                simulate_single_path([10.0], [5.0], [1], bad_params, backend="numba")

        # Negative intraday drawdown rejected in both prop_sim and decimal_oracle
        with pytest.raises(ValueError, match="drawdowns"):
            simulate_single_path([10.0], [-5.0], [1], PropSimParams(), backend="numba")
        with pytest.raises(ValueError, match="obs.dd"):
            replay_prop_lifecycle_decimal(
                [DailyObservation(Decimal("10"), Decimal("-5"), 1, 0)],
                DecimalOracleParams(),
            )

        # capital_usd=0 or NaN in decimal_oracle raises ValueError (not ZeroDivisionError/DivisionUndefined)
        with pytest.raises(ValueError, match="capital_usd"):
            replay_prop_lifecycle_decimal(
                [DailyObservation(Decimal("10"), Decimal("5"), 1, 0)],
                DecimalOracleParams(capital_usd=Decimal("0")),
            )
        with pytest.raises(ValueError, match="non-finite"):
            replay_prop_lifecycle_decimal(
                [DailyObservation(Decimal("NaN"), Decimal("5"), 1, 0)],
                DecimalOracleParams(),
            )

        # Out-of-bounds and negative idx_matrix rejected BEFORE entering @njit
        arr_n = np.array([10.0, 20.0], dtype=np.float64)
        arr_d = np.array([5.0, 5.0], dtype=np.float64)
        arr_f = np.array([1, 1], dtype=np.int8)
        for bad_idx in (
            np.array([[-1, 0]], dtype=np.int32),
            np.array([[0, 2]], dtype=np.int32),
        ):
            with pytest.raises(ValueError, match="idx_matrix"):
                simulate_lifecycle(bad_idx, arr_n, arr_d, arr_f, arr_n, arr_d, arr_f, PropSimParams())

        # Mismatched 1D lengths rejected before @njit
        with pytest.raises(ValueError, match="identical 1D lengths"):
            simulate_lifecycle(
                np.array([[0]], dtype=np.int32),
                arr_n,
                np.array([5.0], dtype=np.float64),
                arr_f,
                arr_n,
                arr_d,
                arr_f,
                PropSimParams(),
            )

    def test_randomized_20_paths_numba_python_decimal_100pct_parity(self) -> None:
        rng = np.random.default_rng(20261127)
        params = PropSimParams(
            steps=2,
            capital_usd=10000.0,
            fee_usd=68.70,
            fee_refund_ratio=1.0,
            max_retries=2,
            retry_discounts=(1.0, 0.85),
            payout_cycle_days=10,
            require_flat_for_pass=True,
        )
        n_paths, horizon = 20, 260
        nets = np.round(rng.normal(18.0, 55.0, size=(n_paths, horizon)), 2)
        dds = np.round(np.maximum(0.0, -nets + rng.uniform(0.0, 45.0, size=(n_paths, horizon))), 2)
        flgs = (np.abs(nets) > 0.0).astype(np.int8)
        opens = (rng.random(size=(n_paths, horizon)) < 0.08).astype(np.int32)

        # Flatten per-path check via batch Numba + Python vs Decimal Oracle
        oracle_params = _to_oracle_params(params)
        for p in range(n_paths):
            idx = np.arange(horizon, dtype=np.int32)[None, :]
            out_nb = simulate_lifecycle(
                idx,
                nets[p],
                dds[p],
                flgs[p],
                nets[p],
                dds[p],
                flgs[p],
                params,
                open_pos_p1=opens[p],
                open_pos_core=opens[p],
                backend="numba",
            )
            out_py = simulate_lifecycle(
                idx,
                nets[p],
                dds[p],
                flgs[p],
                nets[p],
                dds[p],
                flgs[p],
                params,
                open_pos_p1=opens[p],
                open_pos_core=opens[p],
                backend="python",
            )
            sim_nb = {
                "pass_day": int(out_nb.pass_days[0]),
                "first_payout_day": int(out_nb.pay1_days[0]),
                "dead_day": int(out_nb.dead_days[0]),
                "final_stage": int(out_nb.final_stage[0]),
                "cf12_usd": float(out_nb.cf12[0]),
                "cf_terminal_usd": float(out_nb.cf_terminal[0]),
                "max_oop_usd": float(out_nb.max_oop[0]),
                "total_fees_usd": float(out_nb.total_fees[0]),
                "total_payouts_usd": float(out_nb.total_payouts[0]),
                "final_balance_usd": float(out_nb.final_balance[0]),
                "breached_p1": bool(out_nb.br1[0] != 0),
                "breached_p2": bool(out_nb.br2[0] != 0),
                "breached_funded": bool(out_nb.brf[0] != 0),
                "attempts": int(out_nb.attempts[0]),
            }
            sim_py = {
                "pass_day": int(out_py.pass_days[0]),
                "first_payout_day": int(out_py.pay1_days[0]),
                "dead_day": int(out_py.dead_days[0]),
                "final_stage": int(out_py.final_stage[0]),
                "cf12_usd": float(out_py.cf12[0]),
                "cf_terminal_usd": float(out_py.cf_terminal[0]),
                "max_oop_usd": float(out_py.max_oop[0]),
                "total_fees_usd": float(out_py.total_fees[0]),
                "total_payouts_usd": float(out_py.total_payouts[0]),
                "final_balance_usd": float(out_py.final_balance[0]),
                "breached_p1": bool(out_py.br1[0] != 0),
                "breached_p2": bool(out_py.br2[0] != 0),
                "breached_funded": bool(out_py.brf[0] != 0),
                "attempts": int(out_py.attempts[0]),
            }
            obs = [
                DailyObservation(Decimal(str(nets[p, d])), Decimal(str(dds[p, d])), int(flgs[p, d]), int(opens[p, d]))
                for d in range(horizon)
            ]
            oracle = replay_prop_lifecycle_decimal(obs, oracle_params)
            assert_penny_parity(oracle, sim_nb)
            assert_penny_parity(oracle, sim_py)


# ---------------------------------------------------------------------------
# 4. Read-Only MQL5 Contract Drift Checker
# ---------------------------------------------------------------------------


class TestMqlContractDrift:
    def test_real_repo_drift_detection_is_read_only_and_accurate(self) -> None:
        watched = [
            EXPORTS_DIR / "Include/Naqex_Signals_7E.mqh",
            EXPORTS_DIR / "Include/Naqex_PropGuard.mqh",
            EXPORTS_DIR / "Naqex_AccountOrchestrator.mq5",
            EXPORTS_DIR / "deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_P1_4x_L70.set",
            EXPORTS_DIR / "deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_P2_35x.set",
            EXPORTS_DIR / "deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_Funded_125x.set",
        ]
        hashes_before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}

        report = run_drift_audit(
            risk_profiles_path=SSOT_DIR / "risk_profiles.json",
            exports_dir=EXPORTS_DIR,
        )

        hashes_after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
        assert hashes_before == hashes_after, "mql_contract_drift MUST remain 100% read-only"
        assert report["read_only"] is True
        assert report["mutated_files"] == 0
        assert report["order_send_count"] == 0
        assert report["orchestrator_status"] == "LEGACY_DEPRECATED_DST_BUG"
        assert report["scanned_c10_set_files"] == 3

        # 1. Active C10 blocking drifts MUST be zero (P1/P2/Funded all align with C10_NEWS_ON)
        assert report["active_c10_blocking_drifts"] == []
        assert report["active_c10_blocking_count"] == 0
        assert report["has_active_c10_blocking_drift"] is False
        assert report["active_c10_severity_counts"]["HIGH"] == 0
        news_drifts = [d for d in report["drifts"] if d["code"] == "C10_NEWS_ON_RED_NEWS_DISABLED_DRIFT"]
        assert news_drifts == []

        # 2. Active C10 advisory drifts (Signals base risk rounding: 0.1606 vs 0.16, 0.5894 vs 0.59)
        advisory = report["active_c10_advisory_drifts"]
        risk_drifts = [d for d in advisory if d["code"] == "BASE_RISK_ROUNDING_DRIFT"]
        assert len(risk_drifts) == 2
        e1_drift = next(d for d in risk_drifts if "E1_USDJPY_TOKYO" in d["field"])
        assert e1_drift["ssot_value"] == pytest.approx(0.1606)
        assert e1_drift["observed_value"] == pytest.approx(0.16)
        e2_drift = next(d for d in risk_drifts if "E2_USDJPY_EXP80" in d["field"])
        assert e2_drift["ssot_value"] == pytest.approx(0.5894)
        assert e2_drift["observed_value"] == pytest.approx(0.59)

        # 3. Legacy archived drifts transparently reported (18 locked FTMO_FreeTrial_Demo/*.set + Orchestrator)
        legacy = report["legacy_archived_drifts"]
        legacy_high = [d for d in legacy if d["severity"] == "HIGH"]
        assert len(legacy_high) == 19
        assert report["legacy_archived_blocking_count"] == 19
        assert report["has_blocking_drift"] is True

        orch_drifts = [d for d in legacy_high if d["code"] == "LEGACY_DEPRECATED_DST_BUG"]
        assert len(orch_drifts) == 1
        demo_disarmed = [
            d
            for d in legacy_high
            if d["code"] in {"SET_FAIL_CLOSED_DRYRUN_DISARMED", "SET_FAIL_CLOSED_GUARD_DRYRUN_DISARMED"}
        ]
        assert len(demo_disarmed) == 18
        assert all("FTMO_FreeTrial_Demo" in Path(d["file"]).parts for d in demo_disarmed)

        # 4. Exact disjoint partition across active blocking + active advisory + legacy archived
        assert len(report["active_c10_blocking_drifts"]) + len(advisory) + len(legacy) == len(report["drifts"])

    def test_cli_check_exit_codes_blocking_vs_clean_fixture(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Real repo: --check fails (19 legacy HIGH drifts), while --check-active passes (0 active C10 blocking drifts)
        rc_real = drift_cli_main(["--check"])
        captured_real = json.loads(capsys.readouterr().out)
        assert rc_real == 1
        assert captured_real["has_blocking_drift"] is True
        assert captured_real["has_active_c10_blocking_drift"] is False
        assert captured_real["active_c10_blocking_drifts"] == []
        assert captured_real["legacy_archived_blocking_count"] == 19

        rc_active_real = drift_cli_main(["--check-active"])
        captured_active_real = json.loads(capsys.readouterr().out)
        assert rc_active_real == 0
        assert captured_active_real["has_active_c10_blocking_drift"] is False
        assert captured_active_real["active_c10_blocking_drifts"] == []
        assert captured_active_real["legacy_archived_blocking_count"] == 19

        # Clean synthetic exports fixture -> both --check and --check-active return exit code 0
        exp = tmp_path / "exports"
        (exp / "Include").mkdir(parents=True)
        (exp / "deployment_kit/presets").mkdir(parents=True)
        (exp / "Include/Naqex_Signals_7E.mqh").write_text(
            "\n".join(
                [
                    "m_baseRisk[0] = 0.1606;",
                    "m_baseRisk[1] = 0.5894;",
                    "m_baseRisk[2] = 0.75;",
                    "m_baseRisk[3] = 0.50;",
                    "m_baseRisk[4] = 0.50;",
                    "m_baseRisk[5] = 0.50;",
                    "m_baseRisk[6] = 0.50;",
                    "if(magic == 20261122) return 0;",
                    "if(magic == 20261123) return 1;",
                    "if(magic == 20261125) return 2;",
                    "if(magic == 20261124) return 3;",
                    "if(magic == 20261126) return 4;",
                    "if(magic == 20261128) return 5;",
                    "if(magic == 20261129) return 6;",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (exp / "Include/Naqex_PropGuard.mqh").write_text(
            "\n".join(
                [
                    "input bool   InpGuardDryRunLogOnly    = true;",
                    "input bool   InpGuardEnableRedNews    = true;",
                    "input int    InpGuardNewsPadSec       = 300;",
                    "input int    InpGuardNewsHardBanSec   = 135;",
                    "input double InpGuardMaxDailyLossPct  = 2.50;",
                    "input double InpGuardMaxSymbolRiskPct = 1.25;",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        c10_p1_path = exp / "deployment_kit/presets/FTMO_Std10K_MasterProp7E_C10_P1_4x_L70.set"
        c10_p1_clean = (
            "\n".join(
                [
                    "InpDryRunLogOnly=true",
                    "InpGuardDryRunLogOnly=true",
                    "InpContractSku=FTMO_STD_10K_C10_P1_4X_L70",
                    "InpBasePhaseMult=4.00",
                    "InpProfitLockPct=7.00",
                    "InpProfitLockMult=2.50",
                    "InpAmberDdPct=3.50",
                    "InpAmberMult=0.65",
                    "InpRedDdPct=6.00",
                    "InpRedMult=0.40",
                    "InpKillDailyDdPct=3.50",
                    "InpKillStaticDdPct=8.00",
                    "InpMaxSymbolRiskPct=1.75",
                    "InpMaxUsdClusterPct=2.25",
                    "InpMaxJpyClusterPct=2.00",
                    "InpMaxIdxClusterPct=1.75",
                    "InpMaxAccountOpenRiskPct=3.00",
                    "InpGuardEnableRedNews=true",
                    "InpGuardNewsPadSec=300",
                    "InpGuardNewsHardBanSec=135",
                ]
            )
            + "\n"
        )
        c10_p1_path.write_text(c10_p1_clean, encoding="utf-8")

        rc_clean = drift_cli_main(["--check", "--exports-dir", str(exp)])
        captured_clean = json.loads(capsys.readouterr().out)
        assert rc_clean == 0
        assert captured_clean["has_blocking_drift"] is False
        assert captured_clean["has_active_c10_blocking_drift"] is False
        assert captured_clean["active_c10_blocking_drifts"] == []
        assert captured_clean["severity_counts"]["HIGH"] == 0
        assert captured_clean["severity_counts"]["MEDIUM"] == 0

        rc_clean_active = drift_cli_main(["--check-active", "--exports-dir", str(exp)])
        _ = capsys.readouterr()
        assert rc_clean_active == 0

        # Adding locked legacy FTMO_FreeTrial_Demo preset: --check fails (1) while --check-active stays green (0)
        legacy_demo_dir = exp / "deployment_kit/presets/FTMO_FreeTrial_Demo"
        legacy_demo_dir.mkdir(parents=True)
        (legacy_demo_dir / "Naqex_WB_EXP080_USDJPY.set").write_text(
            "InpDryRunLogOnly=false\nInpGuardDryRunLogOnly=false\n",
            encoding="utf-8",
        )
        rc_legacy_all = drift_cli_main(["--check", "--exports-dir", str(exp)])
        captured_legacy_all = json.loads(capsys.readouterr().out)
        assert rc_legacy_all == 1
        assert captured_legacy_all["legacy_archived_blocking_count"] == 2
        assert captured_legacy_all["active_c10_blocking_drifts"] == []

        rc_legacy_active = drift_cli_main(["--check-active", "--exports-dir", str(exp)])
        captured_legacy_active = json.loads(capsys.readouterr().out)
        assert rc_legacy_active == 0
        assert captured_legacy_active["has_active_c10_blocking_drift"] is False
        assert captured_legacy_active["legacy_archived_blocking_count"] == 2

        # Active C10 drift (InpGuardEnableRedNews=false) MUST fail --check-active with exit code 1
        c10_p1_path.write_text(
            c10_p1_clean.replace("InpGuardEnableRedNews=true", "InpGuardEnableRedNews=false"),
            encoding="utf-8",
        )
        rc_active_fail = drift_cli_main(["--check-active", "--exports-dir", str(exp)])
        captured_active_fail = json.loads(capsys.readouterr().out)
        assert rc_active_fail == 1
        assert captured_active_fail["has_active_c10_blocking_drift"] is True
        assert captured_active_fail["active_c10_blocking_count"] == 1
        assert captured_active_fail["active_c10_blocking_drifts"][0]["code"] == "C10_NEWS_ON_RED_NEWS_DISABLED_DRIFT"
