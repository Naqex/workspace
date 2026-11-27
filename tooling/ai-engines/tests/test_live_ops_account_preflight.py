"""Fail-closed unit & integration tests for OPS-2 Account-Phase Preflight Guard.

Covers every Fail-Closed rejection path + clean PASS baselines:
  - Account login & DEMO/REAL trade mode binding
  - Eval-vs-Funded Lock (`risk_mult > 1.25`, `amber_dd_pct > 4.0`, `phase == EVAL`, real `.set` parsing)
  - Asset-class leverage (`FTMO Swing`, `FTMO Standard`, `The5ers HS 5K`)
  - MarketWatch & symbol contract parity (`digits`, `contract_size`, `trade_mode == FULL`, `stops_level`, `.cash`)
  - Multi-account compliance (Magic collision/range overlap, group hedging, Inactivity 21d/27d/30d, Best-Day Share)
  - B8 primary live preset safety (`InpAllowManualHaltFile=true`, `InpWritePrimaryHeartbeat=true`)
  - Safety & `[ARCH-02]` invariants (`ORDER_SEND_CAPABLE=False`, zero `MetaTrader5` import, zero bare `assert`s)

All account logins used in this file are strictly synthetic placeholders (`9900001`, `9900002`).
"""

from __future__ import annotations

import ast
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from quant_factory.live_ops import account_phase_preflight as preflight
from quant_factory.live_ops.account_phase_preflight import (
    DEFAULT_FTMO_SPECS_28,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    load_symbol_specs,
    parse_mt5_set_file,
    validate_account_deployment,
)

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
PRESETS_DIR = AI_ENGINES_DIR / "exports" / "deployment_kit" / "presets"

# Synthetic placeholder logins ONLY (Layer-1 OPSEC compliant)
SYNTH_LOGIN_A = 9900001
SYNTH_LOGIN_B = 9900002


def _funded_safe_preset(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "InpContractSku": "FTMO_STD_10K_FUNDED_SAFE_1X",
        "InpTargetProfitPct": 0.0,
        "InpBasePhaseMult": 1.0,
        "InpProfitLockMult": 1.0,
        "InpAmberDdPct": 3.5,
        "InpRedDdPct": 6.0,
        "InpKillDailyDdPct": 2.5,
        "InpKillStaticDdPct": 7.5,
        "InpAllowManualHaltFile": True,
        "InpWritePrimaryHeartbeat": True,
        "InpSymUSDJPY": "USDJPY",
        "InpSymGBPUSD": "GBPUSD",
        "InpSymEURJPY": "EURJPY",
        "InpSymUS100": "US100.cash",
    }
    base.update(overrides)
    return base


def _eval_sprint_preset(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "InpContractSku": "FTMO_STD_10K_P1_SPRINT_4X",
        "InpTargetProfitPct": 10.0,
        "InpBasePhaseMult": 4.0,
        "InpProfitLockMult": 2.5,
        "InpAmberDdPct": 3.5,
        "InpRedDdPct": 6.0,
        "InpKillDailyDdPct": 3.5,
        "InpKillStaticDdPct": 8.0,
        "InpAllowManualHaltFile": True,
        "InpWritePrimaryHeartbeat": True,
        "InpSymUSDJPY": "USDJPY",
        "InpSymGBPUSD": "GBPUSD",
        "InpSymEURJPY": "EURJPY",
        "InpSymUS100": "US100.cash",
    }
    base.update(overrides)
    return base


def _valid_ftmo_marketwatch(symbols: tuple[str, ...] = ("USDJPY", "GBPUSD", "EURJPY", "US100.cash")) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for sym in symbols:
        sp = DEFAULT_FTMO_SPECS_28[sym]
        out[sym] = {
            "symbol": sym,
            "in_market_watch": True,
            "trade_mode": "FULL",
            "digits": sp["digits"],
            "point": 10.0 ** (-int(sp["digits"])),
            "contract_size": sp["contract_size"],
            "stops_level": sp["stops_level"],
        }
    return out


def _base_funded_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "expected_login": SYNTH_LOGIN_A,
        "actual_login": SYNTH_LOGIN_A,
        "expected_trade_mode": "REAL",
        "actual_trade_mode": "REAL",
        "firm_profile": "FTMO_STANDARD",
        "account_phase": "FUNDED",
        "preset": _funded_safe_preset(),
        "account_leverage": 100,
        "asset_class_leverages": {"FX": 100, "INDICES": 50, "METALS": 30},
        "market_watch_symbols": _valid_ftmo_marketwatch(),
        "required_symbols": ["USDJPY", "GBPUSD", "EURJPY", "US100.cash"],
        "days_since_last_trade": 4,
    }
    kwargs.update(overrides)
    return kwargs


class LiveOpsAccountPreflightTests(unittest.TestCase):
    def test_safety_and_arch02_invariants(self) -> None:
        self.assertFalse(ORDER_SEND_CAPABLE)
        self.assertEqual(ORDER_SEND_COUNT, 0)
        self.assertNotIn("MetaTrader5", sys.modules)

        src_path = Path(preflight.__file__)
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        assert_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertEqual(assert_nodes, [], "ARCH-02 forbids bare assert statements inside quant_factory/")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "MetaTrader5")
            elif isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "MetaTrader5")

    def test_clean_pass_funded_ftmo_standard_1x(self) -> None:
        report = validate_account_deployment(**_base_funded_kwargs())
        self.assertTrue(report.passed)
        self.assertTrue(report.can_launch)
        self.assertEqual(report.verdict, "PASS")
        self.assertEqual(report.alert_level, "GREEN")
        self.assertEqual(report.reject_codes, ())
        self.assertEqual(report.inactivity_status, "GREEN")
        self.assertFalse(report.order_send_capable)
        self.assertEqual(report.order_send_count, 0)

    def test_clean_pass_ftmo_swing_all_asset_classes(self) -> None:
        mw = _valid_ftmo_marketwatch(("USDJPY", "US100.cash", "JP225.cash", "XAUUSD", "USOIL.cash", "BTCUSD"))
        report = validate_account_deployment(
            **_base_funded_kwargs(
                firm_profile="FTMO Swing",
                account_leverage=30,
                asset_class_leverages={"FX": 30, "INDICES": 15, "METALS": 9, "OIL": 10, "CRYPTO": 1},
                market_watch_symbols=mw,
                required_symbols=list(mw.keys()),
            )
        )
        self.assertTrue(report.passed)
        self.assertEqual(report.verdict, "PASS")
        self.assertEqual(report.firm_profile, "FTMO_SWING")

    def test_clean_pass_the5ers_hs_5k_eval(self) -> None:
        report = validate_account_deployment(
            expected_login=SYNTH_LOGIN_A,
            actual_login=SYNTH_LOGIN_A,
            expected_trade_mode="DEMO",
            actual_trade_mode="DEMO",
            firm_profile="The5ers HS 5K",
            account_phase="EVAL",
            preset=_eval_sprint_preset(InpBasePhaseMult=2.67, InpContractSku="THE5ERS_HS_5K_P1"),
            account_leverage=100,
            asset_class_leverages={"FX": 100, "INDICES": 20, "METALS": 33},
            market_watch_symbols=_valid_ftmo_marketwatch(("USDJPY", "GBPUSD", "US100.cash")),
            required_symbols=["USDJPY", "GBPUSD", "US100.cash"],
            max_day_profit_usd=160.0,
            total_profit_target_usd=400.0,
            days_since_last_trade=2,
        )
        self.assertTrue(report.passed)
        self.assertEqual(report.verdict, "PASS")
        self.assertEqual(report.best_day_share, 0.4)

    def test_reject_wrong_login_and_trade_mode_mismatch(self) -> None:
        rep_login = validate_account_deployment(**_base_funded_kwargs(actual_login=SYNTH_LOGIN_B))
        self.assertFalse(rep_login.passed)
        self.assertEqual(rep_login.verdict, "REJECT")
        self.assertIn("ACCOUNT_LOGIN_MISMATCH", rep_login.reject_codes)

        rep_missing = validate_account_deployment(**_base_funded_kwargs(actual_login=None))
        self.assertFalse(rep_missing.passed)
        self.assertIn("INVALID_ACTUAL_LOGIN", rep_missing.reject_codes)

        rep_mode = validate_account_deployment(
            **_base_funded_kwargs(expected_trade_mode="REAL", actual_trade_mode="DEMO")
        )
        self.assertFalse(rep_mode.passed)
        self.assertIn("ACCOUNT_TRADE_MODE_MISMATCH", rep_mode.reject_codes)

        rep_contest = validate_account_deployment(**_base_funded_kwargs(actual_trade_mode="CONTEST"))
        self.assertFalse(rep_contest.passed)
        self.assertIn("INVALID_ACTUAL_TRADE_MODE", rep_contest.reject_codes)

    def test_reject_eval_preset_on_funded_account(self) -> None:
        # 1. Explicit Eval/Sprint preset attached to FUNDED
        rep_eval = validate_account_deployment(
            **_base_funded_kwargs(preset=_eval_sprint_preset(), account_phase="FUNDED")
        )
        self.assertFalse(rep_eval.passed)
        self.assertIn("EVAL_PRESET_ON_FUNDED_ACCOUNT", rep_eval.reject_codes)
        self.assertIn("FUNDED_RISK_MULT_EXCEEDED", rep_eval.reject_codes)
        self.assertIn("EVAL_TARGET_ON_FUNDED_ACCOUNT", rep_eval.reject_codes)

        # 2. Risk mult > 1.25 even if SKU claims FUNDED
        rep_mult = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpBasePhaseMult=1.26))
        )
        self.assertFalse(rep_mult.passed)
        self.assertIn("FUNDED_RISK_MULT_EXCEEDED", rep_mult.reject_codes)

        # 3. Strict 1.0x Funded mode rejects 1.25x while default allows <= 1.25x
        rep_125_default = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpBasePhaseMult=1.25, InpProfitLockMult=1.25))
        )
        self.assertTrue(rep_125_default.passed)
        rep_125_strict = validate_account_deployment(
            **_base_funded_kwargs(
                preset=_funded_safe_preset(InpBasePhaseMult=1.25, InpProfitLockMult=1.25),
                strict_funded_1x=True,
            )
        )
        self.assertFalse(rep_125_strict.passed)
        self.assertIn("FUNDED_RISK_MULT_EXCEEDED", rep_125_strict.reject_codes)

        # 4. Loose amber_dd_pct > 4.0 on FUNDED
        rep_amber = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpAmberDdPct=4.5))
        )
        self.assertFalse(rep_amber.passed)
        self.assertIn("FUNDED_AMBER_DD_TOO_LOOSE", rep_amber.reject_codes)

        # 5. Explicit phase == EVAL with safe mult still rejected on FUNDED
        rep_phase = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(), preset_phase="EVAL")
        )
        self.assertFalse(rep_phase.passed)
        self.assertIn("EVAL_PRESET_ON_FUNDED_ACCOUNT", rep_phase.reject_codes)

        # 6. NaN risk_mult fails closed
        rep_nan = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpBasePhaseMult=math.nan))
        )
        self.assertFalse(rep_nan.passed)
        self.assertIn("INVALID_RISK_MULT", rep_nan.reject_codes)

    def test_reject_real_repo_sprint_set_file_on_funded(self) -> None:
        sprint_set = PRESETS_DIR / "FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set"
        self.assertTrue(sprint_set.is_file(), f"Missing fixture preset: {sprint_set}")
        parsed = parse_mt5_set_file(sprint_set)
        self.assertEqual(parsed["InpBasePhaseMult"], 4.0)
        self.assertFalse(parsed["InpAllowManualHaltFile"])

        report = validate_account_deployment(**_base_funded_kwargs(preset=sprint_set))
        self.assertFalse(report.passed)
        self.assertIn("EVAL_PRESET_ON_FUNDED_ACCOUNT", report.reject_codes)
        self.assertIn("FUNDED_RISK_MULT_EXCEEDED", report.reject_codes)
        self.assertIn("B8_MANUAL_HALT_FILE_DISABLED", report.reject_codes)

    def test_reject_wrong_leverage_per_firm_and_asset_class(self) -> None:
        # FTMO Standard account accidentally given Swing 1:30 leverage
        rep_acct = validate_account_deployment(**_base_funded_kwargs(account_leverage=30))
        self.assertFalse(rep_acct.passed)
        self.assertIn("ACCOUNT_LEVERAGE_MISMATCH", rep_acct.reject_codes)

        # FTMO Standard Indices given 1:15 instead of 1:50
        rep_idx = validate_account_deployment(
            **_base_funded_kwargs(asset_class_leverages={"FX": 100, "INDICES": 15})
        )
        self.assertFalse(rep_idx.passed)
        self.assertIn("ASSET_CLASS_LEVERAGE_MISMATCH", rep_idx.reject_codes)

        # The5ers HS 5K Indices given 1:50 instead of 1:20
        rep_5ers = validate_account_deployment(
            **_base_funded_kwargs(
                firm_profile="THE5ERS_HS_5K",
                account_leverage=100,
                asset_class_leverages={"FX": 100, "INDICES": 50},
            )
        )
        self.assertFalse(rep_5ers.passed)
        self.assertIn("ASSET_CLASS_LEVERAGE_MISMATCH", rep_5ers.reject_codes)

        # FTMO Swing Metals given 1:30 instead of 1:9
        rep_swing_metal = validate_account_deployment(
            **_base_funded_kwargs(
                firm_profile="FTMO_SWING",
                account_leverage=30,
                asset_class_leverages={"FX": 30, "INDICES": 15, "METALS": 30},
            )
        )
        self.assertFalse(rep_swing_metal.passed)
        self.assertIn("ASSET_CLASS_LEVERAGE_MISMATCH", rep_swing_metal.reject_codes)

    def test_reject_marketwatch_contract_parity_violations(self) -> None:
        # 1. Disabled trade_mode
        mw_disabled = _valid_ftmo_marketwatch()
        mw_disabled["USDJPY"]["trade_mode"] = "DISABLED"
        rep_dis = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_disabled))
        self.assertFalse(rep_dis.passed)
        self.assertIn("SYMBOL_TRADE_MODE_NOT_FULL", rep_dis.reject_codes)

        # 2. CLOSEONLY trade_mode (MT5 enum int 3)
        mw_close = _valid_ftmo_marketwatch()
        mw_close["US100.cash"]["trade_mode"] = 3
        rep_close = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_close))
        self.assertFalse(rep_close.passed)
        self.assertIn("SYMBOL_TRADE_MODE_NOT_FULL", rep_close.reject_codes)

        # 3. Wrong digits
        mw_digits = _valid_ftmo_marketwatch()
        mw_digits["USDJPY"]["digits"] = 5
        rep_digits = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_digits))
        self.assertFalse(rep_digits.passed)
        self.assertIn("SYMBOL_DIGITS_MISMATCH", rep_digits.reject_codes)

        # 4. Wrong contract size (US100.cash=10.0 instead of 1.0)
        mw_cs = _valid_ftmo_marketwatch()
        mw_cs["US100.cash"]["contract_size"] = 10.0
        rep_cs = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_cs))
        self.assertFalse(rep_cs.passed)
        self.assertIn("SYMBOL_CONTRACT_SIZE_MISMATCH", rep_cs.reject_codes)

        # 5. Excessive stops_level
        mw_stops = _valid_ftmo_marketwatch()
        mw_stops["GBPUSD"]["stops_level"] = 40
        rep_stops = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_stops))
        self.assertFalse(rep_stops.passed)
        self.assertIn("SYMBOL_STOPS_LEVEL_EXCEEDED", rep_stops.reject_codes)

        # 6. Missing `.cash` broker suffix in MarketWatch or preset
        mw_nosuf = _valid_ftmo_marketwatch(("USDJPY", "GBPUSD", "EURJPY"))
        mw_nosuf["US100"] = {
            "symbol": "US100",
            "in_market_watch": True,
            "trade_mode": "FULL",
            "digits": 2,
            "contract_size": 1.0,
            "stops_level": 0,
        }
        rep_suf = validate_account_deployment(
            **_base_funded_kwargs(
                market_watch_symbols=mw_nosuf,
                preset=_funded_safe_preset(InpSymUS100="US100"),
                required_symbols=["USDJPY", "GBPUSD", "EURJPY", "US100"],
            )
        )
        self.assertFalse(rep_suf.passed)
        self.assertIn("SYMBOL_SUFFIX_MISMATCH", rep_suf.reject_codes)

        # 7. Not selected in MarketWatch
        mw_hidden = _valid_ftmo_marketwatch()
        mw_hidden["EURJPY"]["in_market_watch"] = False
        rep_hid = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_hidden))
        self.assertFalse(rep_hid.passed)
        self.assertIn("SYMBOL_NOT_IN_MARKETWATCH", rep_hid.reject_codes)

    def test_custom_ftmo_specs_28_json_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ftmo_specs_28.json"
            p.write_text(json.dumps({"symbols": DEFAULT_FTMO_SPECS_28}), encoding="utf-8")
            loaded = load_symbol_specs(p)
            self.assertEqual(loaded["JP225.cash"]["contract_size"], 10.0)
            self.assertEqual(loaded["XAGUSD"]["contract_size"], 5000.0)
            self.assertEqual(loaded["USOIL.cash"]["digits"], 3)

    def test_reject_magic_collision_and_range_overlap(self) -> None:
        rep_col = validate_account_deployment(
            **_base_funded_kwargs(
                active_eas=[
                    {"ea_id": "Master_7E", "account_login": SYNTH_LOGIN_A, "magics": [20261122, 20261123]},
                    {"ea_id": "Shadow_EA", "account_login": SYNTH_LOGIN_A, "magic": 20261123},
                ]
            )
        )
        self.assertFalse(rep_col.passed)
        self.assertIn("MAGIC_NUMBER_COLLISION", rep_col.reject_codes)

        rep_rng = validate_account_deployment(
            **_base_funded_kwargs(
                active_eas=[
                    {"ea_id": "EA_A", "account_login": SYNTH_LOGIN_A, "magic_range": (20261120, 20261160)},
                    {"ea_id": "EA_B", "account_login": SYNTH_LOGIN_A, "magic_range": (20261150, 20261199)},
                ]
            )
        )
        self.assertFalse(rep_rng.passed)
        self.assertIn("MAGIC_RANGE_OVERLAP", rep_rng.reject_codes)

        # Clean disjoint magics PASS
        rep_ok = validate_account_deployment(
            **_base_funded_kwargs(
                active_eas=[
                    {"ea_id": "Master_7E", "account_login": SYNTH_LOGIN_A, "magic_range": (20261120, 20261149)},
                    {"ea_id": "Swing_Sleeve", "account_login": SYNTH_LOGIN_A, "magic_range": (20261150, 20261179)},
                ]
            )
        )
        self.assertTrue(rep_ok.passed)

    def test_reject_group_hedging_across_same_firm_accounts(self) -> None:
        # Opposite directions on US100.cash vs US100 across two FTMO accounts -> HARD REJECT
        rep_hedge = validate_account_deployment(
            **_base_funded_kwargs(
                active_signals=[
                    {
                        "firm": "FTMO",
                        "account_login": SYNTH_LOGIN_A,
                        "symbol": "US100.cash",
                        "direction": "BUY",
                        "timestamp_utc": 1764000000,
                    },
                    {
                        "firm": "FTMO_STANDARD",
                        "account_login": SYNTH_LOGIN_B,
                        "symbol": "US100",
                        "direction": "SELL",
                        "timestamp_utc": 1764000120,
                    },
                ]
            )
        )
        self.assertFalse(rep_hedge.passed)
        self.assertIn("GROUP_HEDGING_CONFLICT", rep_hedge.reject_codes)

        # Different firms (FTMO vs The5ers) is NOT same-firm group hedging -> PASS
        rep_diff_firm = validate_account_deployment(
            **_base_funded_kwargs(
                active_signals=[
                    {
                        "firm": "FTMO",
                        "account_login": SYNTH_LOGIN_A,
                        "symbol": "USDJPY",
                        "direction": "BUY",
                        "timestamp_utc": 1764000000,
                    },
                    {
                        "firm": "The5ers",
                        "account_login": SYNTH_LOGIN_B,
                        "symbol": "USDJPY",
                        "direction": "SELL",
                        "timestamp_utc": 1764000060,
                    },
                ]
            )
        )
        self.assertTrue(rep_diff_firm.passed)

    def test_inactivity_rule_amber_21d_red_27d_and_expired_30d(self) -> None:
        rep_21 = validate_account_deployment(**_base_funded_kwargs(days_since_last_trade=21))
        self.assertTrue(rep_21.passed)
        self.assertEqual(rep_21.inactivity_status, "AMBER")
        self.assertEqual(rep_21.verdict, "PASS_WITH_AMBER")
        self.assertIn("INACTIVITY_AMBER_WARNING", rep_21.amber_codes)

        rep_27 = validate_account_deployment(**_base_funded_kwargs(days_since_last_trade=27))
        self.assertTrue(rep_27.passed)
        self.assertEqual(rep_27.inactivity_status, "RED")
        self.assertEqual(rep_27.verdict, "PASS_WITH_RED")
        self.assertIn("INACTIVITY_RED_ALERT", rep_27.red_codes)

        rep_30 = validate_account_deployment(**_base_funded_kwargs(days_since_last_trade=30))
        self.assertFalse(rep_30.passed)
        self.assertEqual(rep_30.inactivity_status, "EXPIRED")
        self.assertIn("INACTIVITY_LIMIT_BREACHED", rep_30.reject_codes)

    def test_best_day_share_sprint_warning_and_hard_consistency_breach(self) -> None:
        eval_kwargs = dict(
            expected_login=SYNTH_LOGIN_A,
            actual_login=SYNTH_LOGIN_A,
            expected_trade_mode="DEMO",
            actual_trade_mode="DEMO",
            firm_profile="FTMO_STANDARD",
            account_phase="EVAL",
            preset=_eval_sprint_preset(),
            account_leverage=100,
            market_watch_symbols=_valid_ftmo_marketwatch(),
            required_symbols=["USDJPY", "GBPUSD", "EURJPY", "US100.cash"],
            total_profit_target_usd=1000.0,
        )

        # 0.45 exact -> GREEN PASS
        rep_ok = validate_account_deployment(**eval_kwargs, max_day_profit_usd=450.0)
        self.assertTrue(rep_ok.passed)
        self.assertEqual(rep_ok.verdict, "PASS")
        self.assertEqual(rep_ok.best_day_share, 0.45)

        # 0.48 (> 0.45 under Sprint) -> AMBER warning
        rep_amber = validate_account_deployment(**eval_kwargs, max_day_profit_usd=480.0)
        self.assertTrue(rep_amber.passed)
        self.assertEqual(rep_amber.verdict, "PASS_WITH_AMBER")
        self.assertIn("BEST_DAY_SHARE_SPRINT_WARNING", rep_amber.amber_codes)

        # 0.56 (> 0.50 under Sprint) -> RED warning
        rep_red = validate_account_deployment(**eval_kwargs, daily_profits_usd=[120.0, 560.0, -80.0])
        self.assertTrue(rep_red.passed)
        self.assertEqual(rep_red.verdict, "PASS_WITH_RED")
        self.assertIn("BEST_DAY_SHARE_SPRINT_RED", rep_red.red_codes)
        self.assertEqual(rep_red.best_day_share, 0.56)

        # Hard firm consistency cap breach -> REJECT
        rep_breach = validate_account_deployment(
            **eval_kwargs,
            max_day_profit_usd=520.0,
            firm_consistency_cap_ratio=0.50,
        )
        self.assertFalse(rep_breach.passed)
        self.assertIn("BEST_DAY_CONSISTENCY_BREACH", rep_breach.reject_codes)

    def test_b8_primary_live_preset_manual_halt_and_heartbeat_required(self) -> None:
        rep_halt = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpAllowManualHaltFile=False))
        )
        self.assertFalse(rep_halt.passed)
        self.assertIn("B8_MANUAL_HALT_FILE_DISABLED", rep_halt.reject_codes)

        rep_hb = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpWritePrimaryHeartbeat=False))
        )
        self.assertFalse(rep_hb.passed)
        self.assertIn("B8_PRIMARY_HEARTBEAT_DISABLED", rep_hb.reject_codes)

        # Shadow-only deployment (`is_primary_live_preset=False`) does not fail B8 primary flags
        rep_shadow = validate_account_deployment(
            **_base_funded_kwargs(
                preset=_funded_safe_preset(InpAllowManualHaltFile=False, InpWritePrimaryHeartbeat=False),
                is_primary_live_preset=False,
            )
        )
        self.assertTrue(rep_shadow.passed)

    def test_fail_closed_edge_cases_and_cli_exit_codes(self) -> None:
        # Loose Red DD & undetermined preset phase on FUNDED
        rep_red_loose = validate_account_deployment(
            **_base_funded_kwargs(preset=_funded_safe_preset(InpRedDdPct=7.5))
        )
        self.assertFalse(rep_red_loose.passed)
        self.assertIn("FUNDED_RED_DD_TOO_LOOSE", rep_red_loose.reject_codes)

        rep_undet = validate_account_deployment(
            **_base_funded_kwargs(
                preset={
                    "InpBasePhaseMult": 1.0,
                    "InpAmberDdPct": 3.5,
                    "InpAllowManualHaltFile": True,
                    "InpWritePrimaryHeartbeat": True,
                }
            )
        )
        self.assertFalse(rep_undet.passed)
        self.assertIn("UNDETERMINED_PRESET_PHASE_ON_FUNDED", rep_undet.reject_codes)

        # Missing MarketWatch & unknown symbol fail closed
        rep_no_mw = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=None))
        self.assertFalse(rep_no_mw.passed)
        self.assertIn("MISSING_MARKETWATCH_SNAPSHOT", rep_no_mw.reject_codes)

        rep_unk_sym = validate_account_deployment(**_base_funded_kwargs(required_symbols=["FAKEUSD"]))
        self.assertFalse(rep_unk_sym.passed)
        self.assertIn("UNKNOWN_SYMBOL_SPEC", rep_unk_sym.reject_codes)

        # Per-symbol effective leverage mismatch in MarketWatch
        mw_bad_lev = _valid_ftmo_marketwatch()
        mw_bad_lev["US100.cash"]["effective_leverage"] = 15
        rep_sym_lev = validate_account_deployment(**_base_funded_kwargs(market_watch_symbols=mw_bad_lev))
        self.assertFalse(rep_sym_lev.passed)
        self.assertIn("SYMBOL_LEVERAGE_MISMATCH", rep_sym_lev.reject_codes)

        # CLI returns 0 on PASS and 2 on REJECT
        with tempfile.TemporaryDirectory() as tmp:
            ok_cfg = Path(tmp) / "ok.json"
            bad_cfg = Path(tmp) / "bad.json"
            ok_cfg.write_text(json.dumps(_base_funded_kwargs()), encoding="utf-8")
            bad_cfg.write_text(json.dumps(_base_funded_kwargs(actual_login=SYNTH_LOGIN_B)), encoding="utf-8")
            self.assertEqual(preflight.main(["--config-json", str(ok_cfg)]), 0)
            self.assertEqual(preflight.main(["--config-json", str(bad_cfg)]), 2)

    def test_p1_03_poisoned_nan_inf_bool_caps_fail_closed(self) -> None:
        # Exact P1-03 repro: poisoned NaN ceilings MUST NEVER bypass Eval-vs-Funded locks
        unsafe_preset = {"phase": "FUNDED", "risk_mult": 4.0, "amber_dd_pct": 8.0, "red_dd_pct": 9.5}
        findings = preflight.check_eval_vs_funded_lock(
            account_phase="FUNDED",
            preset=unsafe_preset,
            max_funded_risk_mult=float("nan"),
            max_funded_amber_dd_pct=float("nan"),
            max_funded_red_dd_pct=float("nan"),
        )
        reject_codes = {f.code for f in findings if f.severity == "REJECT"}
        self.assertIn("INVALID_FUNDED_RISK_MULT_CAP", reject_codes)
        self.assertIn("INVALID_FUNDED_AMBER_DD_CAP", reject_codes)
        self.assertIn("INVALID_FUNDED_RED_DD_CAP", reject_codes)
        self.assertIn("FUNDED_RISK_MULT_EXCEEDED", reject_codes)
        self.assertIn("FUNDED_AMBER_DD_TOO_LOOSE", reject_codes)
        self.assertIn("FUNDED_RED_DD_TOO_LOOSE", reject_codes)

        # Even on a clean safe preset, poisoned NaN / Inf / bool / out-of-range caps MUST REJECT
        for bad_val in (float("nan"), float("inf"), float("-inf"), -1.0, 0.0, True, False, 5.0):
            rep_mult = validate_account_deployment(**_base_funded_kwargs(max_funded_risk_mult=bad_val))
            self.assertFalse(rep_mult.passed, f"max_funded_risk_mult={bad_val!r} must fail closed")
            self.assertIn("INVALID_FUNDED_RISK_MULT_CAP", rep_mult.reject_codes)

        for bad_val in (float("nan"), float("inf"), -0.5, 0.0, True, 9.0):
            rep_amb = validate_account_deployment(**_base_funded_kwargs(max_funded_amber_dd_pct=bad_val))
            self.assertFalse(rep_amb.passed, f"max_funded_amber_dd_pct={bad_val!r} must fail closed")
            self.assertIn("INVALID_FUNDED_AMBER_DD_CAP", rep_amb.reject_codes)

        for bad_val in (float("nan"), float("inf"), -0.5, 0.0, False, 10.0):
            rep_red = validate_account_deployment(**_base_funded_kwargs(max_funded_red_dd_pct=bad_val))
            self.assertFalse(rep_red.passed, f"max_funded_red_dd_pct={bad_val!r} must fail closed")
            self.assertIn("INVALID_FUNDED_RED_DD_CAP", rep_red.reject_codes)

        # Poisoned NaN tolerance & threshold arguments across leverage / MarketWatch / compliance fail closed
        lev_f = preflight.check_asset_class_leverage(
            firm_profile="FTMO_STANDARD",
            account_leverage=30,
            leverage_rel_tol=float("nan"),
        )
        lev_codes = {f.code for f in lev_f if f.severity == "REJECT"}
        self.assertIn("INVALID_LEVERAGE_REL_TOL", lev_codes)
        self.assertIn("ACCOUNT_LEVERAGE_MISMATCH", lev_codes)

        mw_bad = _valid_ftmo_marketwatch()
        mw_bad["US100.cash"]["contract_size"] = 10.0
        mw_f, _ = preflight.check_marketwatch_contract_parity(
            market_watch_symbols=mw_bad,
            contract_size_rel_tol=float("nan"),
            leverage_rel_tol=float("inf"),
            max_allowed_stops_level=True,  # type: ignore[arg-type]
        )
        mw_codes = {f.code for f in mw_f if f.severity == "REJECT"}
        self.assertIn("INVALID_CONTRACT_SIZE_REL_TOL", mw_codes)
        self.assertIn("INVALID_LEVERAGE_REL_TOL", mw_codes)
        self.assertIn("INVALID_MAX_ALLOWED_STOPS_LEVEL", mw_codes)
        self.assertIn("SYMBOL_CONTRACT_SIZE_MISMATCH", mw_codes)

        comp_f, _, _ = preflight.check_multi_account_compliance(
            best_day_warn_ratio=float("nan"),
            hedging_window_sec=float("nan"),  # type: ignore[arg-type]
            firm_consistency_cap_ratio=float("nan"),
        )
        comp_codes = {f.code for f in comp_f if f.severity == "REJECT"}
        self.assertIn("INVALID_BEST_DAY_WARN_RATIO", comp_codes)
        self.assertIn("INVALID_HEDGING_WINDOW_SEC", comp_codes)
        self.assertIn("INVALID_CONSISTENCY_CAP", comp_codes)


if __name__ == "__main__":
    unittest.main()
