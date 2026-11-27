"""Offline-safe + live-receipt verification tests for Offensive #3 Stage 4 (`stage4_portfolio_v3.py`).

Verifies:
  - `[ARCH-02]` zero bare `assert`s and zero `MetaTrader5` imports in `stage4_portfolio_v3.py`,
    `ORDER_SEND_CAPABLE == False`, `ORDER_SEND_COUNT == 0`.
  - Gate `G09` Accretion Gate fail-closed enforcement (zero unapproved additions when `tier1 == 0`,
    hard rejection of any attempted promotion of killed/unqualified bots, Holdout cutoff `< 2025-01-01`).
  - Strictly diagnostic counterfactual note (`DIAG_COUNTERFACTUAL_NOT_PROMOTED`) for
    `F01_LOWFREQ_CAT::F01_US100_NY30_STOP_COIL` (`promoted == False`).
  - Exact 7-SKU SSOT table (`available_vn=true`, zero forbidden SKUs, balanced Law-15 metrics,
    monthly `3m/6m/12m/24m` Pass+Fail+Pending == 100%, Funded 1x breach `< 1%`, `1.25x` gap `<= 3.75%`).
  - All 4 Layer-2 `.set` presets (FTMO Std 10K & The5ers HS 5K Eval/Funded) have all 69 `v103.mq5` keys,
    `InpAllowManualHaltFile=true`, `InpWritePrimaryHeartbeat=true`, fail-closed DryRun defaults,
    The5ers `InpDailyResetMode=0` (`MAX_BALANCE_EQUITY`), PASS `OPS-2` preflight on matching phase,
    and HARD REJECT when Eval preset is attached to a Funded account!
  - Strategy Tester `.ini` configs strictly `< 2025` (`2018.01.02 - 2024.12.31`), fail-closed on `2025+`.
  - Zero `.ex5` files anywhere in `private_vault/` and `.tmp/off3_metaeditor_check/` absent.
"""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path

import pytest
from quant_factory.live_ops.account_phase_preflight import (
    DEFAULT_FTMO_SPECS_28,
    parse_mt5_set_file,
    validate_account_deployment,
)
from quant_factory.offensive3 import stage4_portfolio_v3 as s4

REPO_ROOT = Path(__file__).resolve().parents[3]
STAGE4_PY = REPO_ROOT / "tooling/ai-engines/quant_factory/offensive3/stage4_portfolio_v3.py"
FUNNEL_JSON = REPO_ROOT / "planning/research/OFFENSIVE3-ALPHA-FUNNEL-20261127.json"
SPRINT_JSON = REPO_ROOT / "private_vault/strategies/offensive3_v3/m1_v103_sprint_results.json"
PROP_V3_JSON = REPO_ROOT / "private_vault/strategies/offensive3_v3/prop_v3_metrics.json"
PRESETS_DIR = REPO_ROOT / "private_vault/presets/offensive3_v3"
PRIVATE_VAULT_DIR = REPO_ROOT / "private_vault"


def _mw_for_core7() -> dict[str, dict[str, object]]:
    return {
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


def _synthetic_funnel(tier1_count: int = 0) -> dict[str, object]:
    return {
        "campaign_run_id": "off3-clb-synth",
        "cluster_a_years": [2018, 2019, 2020],
        "cluster_b_years": [2021, 2022, 2023, 2024],
        "holdout_rows_analysed": 0,
        "order_send_capable": False,
        "order_send_count": 0,
        "duckdb_ledger_summary": {
            "integrity_verified": True,
            "primary_bh_fdr_pass_count": 0,
            "exploratory_bh_fdr_pass_count": 0,
        },
        "effective_trials_n_eff": {
            "primary_m200": {"n_eff": 72.0019},
        },
        "funnel_counts": {
            "total_evaluated": 1137,
            "primary_evaluated": 142,
            "exploratory_only_evaluated": 995,
            "tier1_ftmo_ready": tier1_count,
            "tier2_personal_vault": 0,
            "tier3_dead_no_edge": 1137 - tier1_count,
            "conditional_retest_rejected_count": 0,
            "g7_pbo_executed_count": 1137,
        },
        "tier1_ftmo_ready": [],
        "tier2_personal_vault": [],
        "tier3_dead_top20_near_misses": [
            {
                "strategy_id": s4.TOP_NEAR_MISS_ID,
                "alpha_family_id": "F01_LOWFREQ_CAT",
                "pool_tier": "PRIMARY",
                "tier": "TIER_3_DEAD_NO_EDGE",
                "council_verdict": "REJECT_KILLED",
                "blindness_tier": "DEV_CLB_CONSUMED_12OLD",
                "data_resolution": "NATIVE_M1_BIDASK",
                "n_trades_clb": 216,
                "sharpe_clb": 1.325,
                "net_r_1x": 18.107,
                "net_r_15x": 17.349,
                "net_r_2x": 16.59,
                "net_r_zero_pos_swap": 18.107,
                "fade_net_r_1x": -29.112,
                "trim5_win_pf": 1.36,
                "p_sign_flip_50k": 0.00351993,
                "p_newey_west": 0.00175804,
                "timing_p": 0.005199,
                "bh_q_primary": 0.49983,
                "bh_q_exploratory": 1.0,
                "dsr_council": 0.5174,
                "dsr_empirical": 0.374,
                "pbo_cscv": 0.1603,
                "corr_port7e": 0.0466,
                "tail_corr_port7e": 0.1397,
                "crisis_passed": True,
            }
        ],
    }


def test_arch02_zero_bare_asserts_and_safety_constants() -> None:
    """Enforce `[ARCH-02]` zero bare `assert`s, zero `MetaTrader5` imports, and `ORDER_SEND_CAPABLE=False`."""
    if s4.ORDER_SEND_CAPABLE is not False or s4.ORDER_SEND_COUNT != 0:
        raise AssertionError("ORDER_SEND safety invariants violated")
    if "MetaTrader5" in sys.modules:
        raise AssertionError("MetaTrader5 module must never be imported")

    tree = ast.parse(STAGE4_PY.read_text(encoding="utf-8"))
    bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    if bare_asserts:
        raise AssertionError(f"[ARCH-02] Bare assert statements in stage4_portfolio_v3.py at lines {bare_asserts}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "MetaTrader5":
                    raise AssertionError("Forbidden MetaTrader5 import")
        elif isinstance(node, ast.ImportFrom) and node.module == "MetaTrader5":
            raise AssertionError("Forbidden MetaTrader5 import")


def test_g09_accretion_gate_fail_closed_and_counterfactual_not_promoted() -> None:
    """Verify G09 blocks unapproved additions, rejects tampered promotions, and keeps near-miss excluded."""
    good_funnel = _synthetic_funnel(tier1_count=0)
    gate = s4.enforce_g09_accretion_gate(good_funnel)
    if gate["prop_v3_champion"] != s4.PROP_V3_CHAMPION_ID:
        raise AssertionError(f"Unexpected champion: {gate['prop_v3_champion']}")
    if gate["promoted_count"] != 0 or gate["promoted_additions"] != [] or gate["gates_relaxed"] is not False:
        raise AssertionError(f"G09 must promote 0 unproven bots: {gate}")

    # Attempted promotion of a killed candidate (`q=0.4998 > 0.10`) MUST fail closed
    tampered = copy.deepcopy(good_funnel)
    tampered["funnel_counts"]["tier1_ftmo_ready"] = 1  # type: ignore[index]
    tampered["funnel_counts"]["tier3_dead_no_edge"] = 1136  # type: ignore[index]
    tampered["tier1_ftmo_ready"] = [copy.deepcopy(good_funnel["tier3_dead_top20_near_misses"][0])]  # type: ignore[index]
    with pytest.raises(ValueError, match="G09_ACCRETION_GATE_VIOLATION"):
        s4.enforce_g09_accretion_gate(tampered)

    # Attempted holdout year leak in funnel MUST fail closed
    leak = copy.deepcopy(good_funnel)
    leak["cluster_b_years"] = [2021, 2022, 2023, 2024, 2025]
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        s4.enforce_g09_accretion_gate(leak)

    # Diagnostic counterfactual note MUST stay strictly NOT promoted
    diag = s4.build_diagnostic_counterfactual_note(good_funnel)
    if diag["tag"] != "DIAG_COUNTERFACTUAL_NOT_PROMOTED" or diag["promoted"] is not False:
        raise AssertionError(f"Counterfactual note mislabeled: {diag}")
    if diag["included_in_prop_v3"] is not False or diag["strategy_id"] != s4.TOP_NEAR_MISS_ID:
        raise AssertionError(f"Counterfactual strategy must never be included in Prop V3: {diag}")
    if diag["multiple_testing_math"]["clears_bh_fdr_primary"] is not False:
        raise AssertionError("Near-miss must not clear BH-FDR primary")


def test_g09_vector_v1_rejects_bool_nan_inf_inputs() -> None:
    """P1-02: enforce_g09_accretion_gate MUST reject bool counts and NaN/+Inf/-Inf metrics fail-closed."""
    base = _synthetic_funnel(tier1_count=0)

    # 1. Reject bool for top-level integer safety counters & cluster_b_years
    for top_key in ("holdout_rows_analysed", "order_send_count"):
        for bval in (False, True):
            mut = copy.deepcopy(base)
            mut[top_key] = bval
            with pytest.raises(ValueError):
                s4.enforce_g09_accretion_gate(mut)

    for bad_yr in (False, True, 2024.0, float("nan")):
        mut = copy.deepcopy(base)
        mut["cluster_b_years"] = [2021, 2022, 2023, bad_yr]
        with pytest.raises(ValueError):
            s4.enforce_g09_accretion_gate(mut)

    # 2. Reject bool and float/NaN/Inf for EVERY integer count in funnel_counts & ledger
    count_fields = (
        "tier1_ftmo_ready",
        "tier2_personal_vault",
        "tier3_dead_no_edge",
        "total_evaluated",
        "primary_evaluated",
        "exploratory_only_evaluated",
        "conditional_retest_rejected_count",
        "g7_pbo_executed_count",
    )
    for field in count_fields:
        for bad_val in (False, True, float("nan"), float("inf"), float("-inf")):
            mut = copy.deepcopy(base)
            mut["funnel_counts"][field] = bad_val  # type: ignore[index]
            with pytest.raises(ValueError, match="G09_INVALID_INT_INPUT"):
                s4.enforce_g09_accretion_gate(mut)

    for bad_val in (False, True, float("nan"), float("inf")):
        mut = copy.deepcopy(base)
        mut["duckdb_ledger_summary"]["primary_bh_fdr_pass_count"] = bad_val  # type: ignore[index]
        with pytest.raises(ValueError, match="G09_INVALID_INT_INPUT"):
            s4.enforce_g09_accretion_gate(mut)

    # 3. Reject NaN, +Inf, -Inf, True, False for tier1 entry bh_q_primary, pbo_cscv, and float metrics
    poison_floats: tuple[object, ...] = (float("nan"), float("inf"), float("-inf"), True, False)
    for metric_key in ("bh_q_primary", "pbo_cscv", "sharpe_clb", "dsr_empirical"):
        for bad_val in poison_floats:
            mut = copy.deepcopy(base)
            mut["funnel_counts"]["tier1_ftmo_ready"] = 1  # type: ignore[index]
            mut["funnel_counts"]["tier3_dead_no_edge"] = 1136  # type: ignore[index]
            cand = copy.deepcopy(base["tier3_dead_top20_near_misses"][0])  # type: ignore[index]
            cand["tier"] = "TIER_1_FTMO_READY"
            cand["council_verdict"] = "ACCEPT"
            cand["bh_q_primary"] = 0.05
            cand["pbo_cscv"] = 0.20
            cand[metric_key] = bad_val
            mut["tier1_ftmo_ready"] = [cand]
            with pytest.raises(ValueError, match="G09_ACCRETION_GATE_VIOLATION"):
                s4.enforce_g09_accretion_gate(mut)


def test_tester_ini_strictly_pre_2025_fail_closed(tmp_path: Path) -> None:
    """Verify Strategy Tester `.ini` generator/validator rejects `2025+` dates and live trading flags."""
    good_ini = tmp_path / "good_dev.ini"
    s4.atomic_write_text(
        good_ini,
        s4.render_dev_strategy_tester_ini(
            preset_filename="FTMO_Std10K_v103_Sprint_Eval.set",
            report_name="v103_Sprint_Eval_tester_dev",
        ),
    )
    kv = s4.validate_tester_ini_file(good_ini)
    if kv["FromDate"] != "2018.01.02" or kv["ToDate"] != "2024.12.31":
        raise AssertionError(f"Unexpected Dev Tester date bounds: {kv}")

    # Any 2025+ ToDate MUST fail closed
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        s4.render_dev_strategy_tester_ini(
            preset_filename="FTMO_Std10K_v103_Sprint_Eval.set",
            report_name="bad",
            to_date="2025.01.01",
        )

    bad_ini = tmp_path / "bad_2025.ini"
    s4.atomic_write_text(bad_ini, good_ini.read_text(encoding="utf-8").replace("2024.12.31", "2025.06.01"))
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        s4.validate_tester_ini_file(bad_ini)

    live_ini = tmp_path / "bad_live.ini"
    live_text = good_ini.read_text(encoding="utf-8").replace("AllowLiveTrading=0", "AllowLiveTrading=1")
    s4.atomic_write_text(live_ini, live_text)
    with pytest.raises(ValueError, match="TESTER_INI_SAFETY_ERROR"):
        s4.validate_tester_ini_file(live_ini)


def test_all_four_presets_pass_ops2_and_reject_eval_on_funded(tmp_path: Path) -> None:
    """Verify all 4 Layer-2 `.set` presets (69 keys, B8 flags, OPS-2 PASS, Eval-on-Funded HARD REJECT)."""
    v103_inputs = set(s4.parse_v103_mq5_inputs())
    if len(v103_inputs) != 69:
        raise AssertionError(f"Expected 69 v103.mq5 inputs, got {len(v103_inputs)}")

    mw = _mw_for_core7()
    cases = (
        ("FTMO_Std10K_v103_Sprint_Eval.set", "FTMO_STANDARD", "EVAL", 1, {"FX": 100, "INDICES": 50, "METALS": 30}),
        ("FTMO_Std10K_v103_Funded_1x.set", "FTMO_STANDARD", "FUNDED", 1, {"FX": 100, "INDICES": 50, "METALS": 30}),
        ("The5ers_HS5K_v103_Sprint_Eval.set", "THE5ERS_HS_5K", "EVAL", 0, {"FX": 100, "INDICES": 20, "METALS": 33}),
        ("The5ers_HS5K_v103_Funded_1x.set", "THE5ERS_HS_5K", "FUNDED", 0, {"FX": 100, "INDICES": 20, "METALS": 33}),
    )

    for fname, firm_profile, phase, expected_reset_mode, asset_levs in cases:
        p = PRESETS_DIR / fname
        if not p.is_file():
            raise AssertionError(f"Missing Layer-2 preset: {p}")
        raw = p.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise AssertionError(f"{fname} must not contain UTF-8 BOM")
        if b"\r\n" in raw:
            raise AssertionError(f"{fname} must be LF-only")
        raw_text = raw.decode("utf-8")
        if firm_profile == "THE5ERS_HS_5K":
            if "; PROVISIONAL_SYMBOL_ALIASES" not in raw_text or "the5ers_specs.json" not in raw_text:
                raise AssertionError(
                    f"P1-04 violated: {fname} missing PROVISIONAL_SYMBOL_ALIASES / the5ers_specs.json header"
                )
        parsed = parse_mt5_set_file(p)
        if set(parsed.keys()) != v103_inputs:
            raise AssertionError(
                f"{fname} keys != 69 v103.mq5 inputs: missing={v103_inputs - set(parsed.keys())} "
                f"extra={set(parsed.keys()) - v103_inputs}"
            )
        if parsed["InpDailyResetMode"] != expected_reset_mode:
            raise AssertionError(
                f"{fname} InpDailyResetMode={parsed['InpDailyResetMode']} != {expected_reset_mode}"
            )
        for flag in (
            "InpAllowManualHaltFile",
            "InpWritePrimaryHeartbeat",
            "InpDryRunLogOnly",
            "InpShadowCompareMode",
            "InpGuardDryRunLogOnly",
        ):
            if parsed.get(flag) is not True:
                raise AssertionError(f"{fname} must set {flag}=true, got {parsed.get(flag)!r}")

        # Positive matching-phase OPS-2 PASS
        rep_ok = validate_account_deployment(
            expected_login=9900001,
            actual_login=9900001,
            expected_trade_mode="DEMO",
            actual_trade_mode="DEMO",
            firm_profile=firm_profile,
            account_phase=phase,
            preset=p,
            account_leverage=100,
            asset_class_leverages=asset_levs,
            market_watch_symbols=mw,
            required_symbols=list(s4.CORE_7E_SYMBOLS),
            strict_funded_1x=(phase == "FUNDED"),
        )
        if not rep_ok.passed or rep_ok.verdict != "PASS":
            raise AssertionError(f"{fname} failed OPS-2 preflight ({phase}): {rep_ok.reject_codes}")

        # Negative Eval-on-Funded HARD REJECT
        if phase == "EVAL":
            rep_bad = validate_account_deployment(
                expected_login=9900001,
                actual_login=9900001,
                expected_trade_mode="REAL",
                actual_trade_mode="REAL",
                firm_profile=firm_profile,
                account_phase="FUNDED",
                preset=p,
                account_leverage=100,
                asset_class_leverages=asset_levs,
                market_watch_symbols=mw,
                required_symbols=list(s4.CORE_7E_SYMBOLS),
                strict_funded_1x=True,
            )
            if rep_bad.passed or "EVAL_PRESET_ON_FUNDED_ACCOUNT" not in rep_bad.reject_codes:
                raise AssertionError(
                    f"Eval preset {fname} was NOT hard-rejected on FUNDED account: {rep_bad.reject_codes}"
                )


    # P1-04 negative test: stripping PROVISIONAL_SYMBOL_ALIASES header from The5ers preset MUST fail closed
    stripped_path = tmp_path / "The5ers_stripped.set"
    raw_the5 = (PRESETS_DIR / "The5ers_HS5K_v103_Funded_1x.set").read_text(encoding="utf-8")
    stripped_lines = [ln for ln in raw_the5.splitlines() if "PROVISIONAL_SYMBOL_ALIASES" not in ln]
    s4.atomic_write_text(stripped_path, "\n".join(stripped_lines) + "\n")
    with pytest.raises(ValueError, match="THE5ERS_PROVISIONAL_ALIAS_HEADER_MISSING"):
        s4.verify_preset_with_ops2(stripped_path, firm_profile="THE5ERS_HS_5K", account_phase="FUNDED")


def test_real_stage4_receipt_tester_inis_and_zero_ex5_in_private_vault() -> None:
    """Verify generated `prop_v3_metrics.json`, Dev `.ini` files, G11 compile log, and 0 `.ex5` in `private_vault/`."""
    if not FUNNEL_JSON.is_file() or not SPRINT_JSON.is_file() or not PROP_V3_JSON.is_file():
        pytest.skip("Stage 3 / Front 1 / Stage 4 receipts not present")

    doc = json.loads(PROP_V3_JSON.read_text(encoding="utf-8"))
    expected_sha = s4.canonical_json_sha256(doc)
    if doc.get("receipt_payload_sha256") != expected_sha:
        raise AssertionError("prop_v3_metrics.json receipt_payload_sha256 mismatch")
    if doc["order_send_capable"] is not False or doc["order_send_count"] != 0 or doc["holdout_rows_analysed"] != 0:
        raise AssertionError("Safety counters violated in prop_v3_metrics.json")
    if doc["max_day"] >= "2025-01-01":
        raise AssertionError(f"Holdout leak in max_day={doc['max_day']}")
    if doc["prop_v3_champion"] != s4.PROP_V3_CHAMPION_ID:
        raise AssertionError(f"Unexpected champion: {doc['prop_v3_champion']}")

    g09 = doc["g09_accretion_gate"]
    if g09["tier1_ftmo_ready_count"] != 0 or g09["promoted_count"] != 0 or g09["gates_relaxed"] is not False:
        raise AssertionError(f"G09 invariant mismatch: {g09}")

    diag = doc["diagnostic_counterfactual_not_promoted"]
    if diag["tag"] != "DIAG_COUNTERFACTUAL_NOT_PROMOTED" or diag["promoted"] is not False:
        raise AssertionError(f"Counterfactual note mismatch: {diag}")

    # Verify all 7 SSOT SKUs + unified KS=8.00% + per-SKU 0.01-lot-floored Law-15 + Law-15 monthly sum == 100%
    sprint_doc = json.loads(SPRINT_JSON.read_text(encoding="utf-8"))
    summary = doc["champion_portfolio_summary"]
    target_skus = tuple(summary["target_skus"])
    sku_table = summary["sku_table_7_ssot"]
    if target_skus != s4.TARGET_SKUS or set(sku_table.keys()) != set(s4.TARGET_SKUS):
        raise AssertionError(f"7-SKU table mismatch: target={target_skus} keys={tuple(sku_table.keys())}")

    # P1-01: Single KS=8.00% source of truth & exact SHA-256 reconciliation across M1 receipt, Stage 4, and disk
    harm = summary["ops2_funded_static_kill_harmonization"]
    if (
        harm.get("unified_ks_source_of_truth") is not True
        or float(harm["m1_sprint_receipt_funded_kill_static_pct"]) != 8.00
        or float(harm["exported_preset_funded_kill_static_pct"]) != 8.00
    ):
        raise AssertionError(f"P1-01 unified KS=8.00% violated: {harm}")
    if "verified_10k_ks80_metrics" in harm:
        raise AssertionError("P1-01 violated: stale hardcoded 3-SKU verified_10k_ks80_metrics still present")
    all7_ks80 = harm.get("all_7_ssot_skus_ks80_metrics") or {}
    if set(all7_ks80.keys()) != set(s4.TARGET_SKUS) or len(all7_ks80) != len(s4.TARGET_SKUS):
        raise AssertionError(f"P1-01 violated: harmonization must report all 7/7 SKUs, got {tuple(all7_ks80.keys())}")
    presets_meta = doc["layer2_presets_and_tester_exports"]["presets"]
    pw = sprint_doc.get("presets_written") or {}
    for pw_key, fname in (
        ("eval_set_sha256", "FTMO_Std10K_v103_Sprint_Eval.set"),
        ("funded_set_sha256", "FTMO_Std10K_v103_Funded_1x.set"),
    ):
        disk_sha = s4.sha256_file(PRESETS_DIR / fname)
        if pw.get(pw_key) != disk_sha or presets_meta[fname]["sha256"] != disk_sha:
            raise AssertionError(
                f"P1-01 SHA-256 drift for {fname}: m1={pw.get(pw_key)} "
                f"prop_v3={presets_meta[fname]['sha256']} disk={disk_sha}"
            )

    # P1-03: Verify true per-SKU 0.01-lot-floored Funded 1.0x metrics & explicit Eval 24m fail band disclosure
    disc = summary.get("eval_fail_band_disclosure") or {}
    if disc.get("selection_anchor_sku") != "ftmo_standard_10k":
        raise AssertionError(f"P1-03 violated: missing eval_fail_band_disclosure anchor: {disc}")
    for sku_id in s4.TARGET_SKUS:
        if sku_id not in (disc.get("by_sku") or {}):
            raise AssertionError(f"P1-03 violated: {sku_id} missing from eval_fail_band_disclosure.by_sku")
    if sku_table["the5ers_hs_5k_classic"]["ev_usd_per_trade_funded_1x"] >= 0.85:
        raise AssertionError(
            f"P1-03 violated: $5K ev_usd_per_trade_funded_1x still linearly scaled: "
            f"{sku_table['the5ers_hs_5k_classic']['ev_usd_per_trade_funded_1x']}"
        )
    if sku_table["ftmo_standard_10k"]["ev_usd_per_trade_funded_1x"] >= 1.74:
        raise AssertionError(
            f"P1-03 violated: $10K ev_usd_per_trade_funded_1x still linearly scaled: "
            f"{sku_table['ftmo_standard_10k']['ev_usd_per_trade_funded_1x']}"
        )

    for sku_id, row in sku_table.items():
        if row.get("funded_1x_metrics_source") != "DIRECT_PER_SKU_M1_REPLAY_001_LOT_FLOORED":
            raise AssertionError(f"P1-03 violated: {sku_id} missing direct replay source tag")
        if int(row.get("trades_funded_1x", 0)) <= 0:
            raise AssertionError(f"P1-03 violated: {sku_id} missing trades_funded_1x")
        if float(row["funded_kill_static_dd_pct"]) != 8.00:
            raise AssertionError(
                f"P1-01 violated: {sku_id} funded_kill_static_dd_pct={row['funded_kill_static_dd_pct']}"
            )
        if row["funded_12m_breach_pct"] >= 1.0:
            raise AssertionError(f"{sku_id} funded_12m_breach_pct >= 1%: {row['funded_12m_breach_pct']}")
        if all7_ks80[sku_id]["funded_12m_breach_pct"] != row["funded_12m_breach_pct"]:
            raise AssertionError(f"P1-01 drift between sku_table and harmonization for {sku_id}")
        if row["gap_shock_eval_125x_pct"] > 3.75:
            raise AssertionError(f"{sku_id} gap_shock_eval_125x_pct > 3.75%: {row['gap_shock_eval_125x_pct']}")
        for mkey in ("3m", "6m", "12m", "24m"):
            b = row["monthly_pass_fail_pending"][mkey]
            if abs((b["pass_pct"] + b["fail_pct"] + b["pending_pct"]) - 100.0) > 0.02:
                raise AssertionError(f"{sku_id} {mkey} sum != 100%: {b}")

    # P1-04: Verify The5ers provisional symbol alias & unmeasured execution tags in prop_v3_metrics.json
    for the5_fname in ("The5ers_HS5K_v103_Sprint_Eval.set", "The5ers_HS5K_v103_Funded_1x.set"):
        pm = presets_meta[the5_fname]
        if pm.get("execution_status") != "TERMS_VERIFIED_EXECUTION_UNMEASURED":
            raise AssertionError(f"P1-04 violated on {the5_fname}: execution_status={pm.get('execution_status')!r}")
        if pm.get("symbol_aliases_provisional") is not True:
            raise AssertionError(f"P1-04 violated on {the5_fname}: symbol_aliases_provisional != True")
        if pm.get("specs_source_for_offline_ops2") != "ftmo_specs_28_placeholder_until_the5ers_marketwatch_capture":
            raise AssertionError(f"P1-04 violated on {the5_fname}: specs_source_for_offline_ops2 mismatch")
        if pm.get("live_non_dryrun_blocked_until") != "the5ers_specs.json":
            raise AssertionError(f"P1-04 violated on {the5_fname}: live_non_dryrun_blocked_until mismatch")

    # Verify both Dev Strategy Tester `.ini` files exist and stay strictly `< 2025`
    for ini_name in ("v103_Sprint_Eval_tester_dev.ini", "v103_Funded_1x_tester_dev.ini"):
        kv = s4.validate_tester_ini_file(PRESETS_DIR / ini_name)
        if kv["FromDate"] != "2018.01.02" or kv["ToDate"] != "2024.12.31":
            raise AssertionError(f"{ini_name} date window drift: {kv}")

    # Verify G11 MetaEditor64 compile proof recorded 0 errors, 0 warnings on both targets & 0 .ex5 remaining
    g11 = doc["g11_metaeditor_compile_proof"]
    if g11["status"] != "PASS_0_ERRORS_0_WARNINGS":
        raise AssertionError(f"G11 compile proof did not pass: {g11}")
    for tgt in ("Naqex_Master_Prop7E_v103.mq5", "Naqex_V3_Headers_Harness.mq5"):
        res = g11["targets"][tgt]
        if res["errors"] != 0 or res["warnings"] != 0:
            raise AssertionError(f"G11 non-zero errors/warnings on {tgt}: {res}")
    if s4.DEFAULT_METAEDITOR_CHECK_DIR.exists():
        raise AssertionError(f"Isolated check dir was not deleted: {s4.DEFAULT_METAEDITOR_CHECK_DIR}")
    pv_ex5 = list(PRIVATE_VAULT_DIR.rglob("*.ex5"))
    if pv_ex5:
        raise AssertionError(f"Found forbidden .ex5 files in private_vault/: {pv_ex5}")
