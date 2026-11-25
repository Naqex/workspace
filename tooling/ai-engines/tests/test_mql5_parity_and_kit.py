"""Regression, Parity, Tamper-Detection & Watchdog Tests for Naqex MQL5 Production Suite (M1.1-M1.5)."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

AI_ENGINES = Path(__file__).resolve().parents[1]
EXPORTS_DIR = AI_ENGINES / "exports"
KIT_DIR = EXPORTS_DIR / "deployment_kit"
REPO_ROOT = AI_ENGINES.parents[1]
EX5_DIR = REPO_ROOT / ".runtime/mt5-compiled-ex5"

for p in (AI_ENGINES, EXPORTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import mql5_parity_checker as parity  # noqa: E402
import verify_deployment_kit as kit  # noqa: E402
from quant_factory.data_store import assert_holdout_locked  # noqa: E402


EXPECTED_PROFILES = {
    "FTMO_FreeTrial_DryRun",
    "FTMO_FreeTrial_Demo",
    "FTMO_P1_Balanced_3to6m",
    "FTMO_P1_Sprint_1to3m",
    "FTMO_P2_Verify",
    "FTMO_Funded_Swing_Safe",
    "FTMO_Funded_Std_RedNews",
    "The5ers_HighStakes_P1_Balanced",
    "The5ers_HighStakes_P1_Sprint",
    "The5ers_HighStakes_Funded",
}


class Mql5ParityAndDeploymentKitTests(unittest.TestCase):
    def test_mql5_parity_audit_passes_all_8_eas_orchestrator_propguard_and_9_ex5(self):
        has_local_ex5 = EX5_DIR.is_dir() and len(list(EX5_DIR.glob("*.ex5"))) >= 10
        rep = parity.run_parity_audit(exports_dir=EXPORTS_DIR, ex5_dir=EX5_DIR, require_ex5=has_local_ex5)
        self.assertTrue(rep["ok"], f"Parity audit failed: {json.dumps(rep, indent=2)}")
        self.assertEqual(rep["engines_checked"], 8)
        self.assertEqual(rep["engines_passed"], 8)
        self.assertEqual(rep["unique_magics"], list(range(20261122, 20261130)))
        self.assertTrue(rep["propguard"]["ok"])
        self.assertTrue(rep["orchestrator"]["ok"])
        self.assertTrue(rep["red_news_csv"]["ok"])
        self.assertGreaterEqual(rep["red_news_csv"]["rows"], 200)
        self.assertTrue(rep["master_ea"]["ok"])

        # Verify all 10 compiled .ex5 binaries when local .runtime build dir is present (gitignored on clean CI)
        if has_local_ex5:
            comp = rep["compile_artifacts"]
            self.assertTrue(comp["ok"], f"Compile artifacts failed: {comp['errors']}")
            self.assertEqual(len(comp["files"]), 10)
            for stem, info in comp["files"].items():
                self.assertTrue(info["ex5_exists"], f"Missing .ex5 for {stem}")
                self.assertGreater(info["ex5_bytes"], 10_000, f"Suspiciously small .ex5 for {stem}")
                self.assertEqual(info["errors"], 0, f"Compile errors in {stem}")
                self.assertEqual(info["warnings"], 0, f"Compile warnings in {stem}")

        # Verify zero red flags and InpDryRunLogOnly=true across all 8 EAs
        for eid, er in rep["engines"].items():
            self.assertTrue(er["ok"], f"{eid} failed: {er['errors']}")
            self.assertIs(er["dry_run_default"], True, f"{eid} must default InpDryRunLogOnly=true")
            self.assertEqual(er["red_flags"], [], f"{eid} had red flags")

    def test_parity_checker_rejects_dryrun_disabled_or_duplicate_magic(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_exp = Path(td) / "exports"
            shutil.copytree(EXPORTS_DIR / "Include", tmp_exp / "Include")
            shutil.copytree(EXPORTS_DIR / "Files", tmp_exp / "Files")
            for mq5 in EXPORTS_DIR.glob("*.mq5"):
                shutil.copy2(mq5, tmp_exp / mq5.name)

            # Mutate E2 to disable dry-run AND collide with E1 magic
            e2 = tmp_exp / "Naqex_WB_EXP080_USDJPY.mq5"
            src = e2.read_text(encoding="utf-8")
            src = src.replace("InpDryRunLogOnly     = true;", "InpDryRunLogOnly     = false;")
            src = src.replace("InpMagicNumber       = 20261123;", "InpMagicNumber       = 20261122;")
            e2.write_text(src, encoding="utf-8")

            rep = parity.run_parity_audit(exports_dir=tmp_exp, ex5_dir=None, require_ex5=False)
            self.assertFalse(rep["ok"])
            e2_errs = " | ".join(rep["engines"]["E2_USDJPY_EXP80"]["errors"])
            self.assertIn("InpDryRunLogOnly", e2_errs)
            self.assertIn("Magic mismatch", e2_errs)

    def test_deployment_kit_self_verification_and_all_10_profiles(self):
        has_local_ex5 = EX5_DIR.is_dir() and len(list(EX5_DIR.glob("*.ex5"))) >= 10
        rep = kit.verify_kit(exports_dir=EXPORTS_DIR, kit_dir=KIT_DIR, ex5_dir=EX5_DIR, require_ex5=has_local_ex5)
        self.assertTrue(rep["ok"], f"Deployment kit verification failed: {rep['errors']}")
        self.assertEqual(rep["profiles_expected"], 10)
        self.assertEqual(rep["presets_checked"], 90)
        if has_local_ex5:
            self.assertEqual(rep["verified_ex5_files"], 10)

        manifest = json.loads((KIT_DIR / "manifest.sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["profiles"].keys()), EXPECTED_PROFILES)
        self.assertEqual(manifest["order_send_count"], 0)
        self.assertEqual(manifest["compiled_ex5_count"], 10)

        # Verify M2.2 calibrated multipliers & PropGuard [0.20, 3.50] clamp compatibility
        bal_orch = kit.parse_set_file(KIT_DIR / "presets/FTMO_P1_Balanced_3to6m/Naqex_AccountOrchestrator.set")
        bal_e4 = kit.parse_set_file(KIT_DIR / "presets/FTMO_P1_Balanced_3to6m/Naqex_WB_SESS_CONT_BRK40_US100.set")
        self.assertAlmostEqual(float(bal_orch["InpBasePhaseMult"]), 2.67, places=2)
        self.assertAlmostEqual(float(bal_e4["InpRiskPercent"]), 0.75, places=2)  # 0.50 * 1.50x EA scale
        self.assertGreaterEqual(float(bal_e4["InpGuardMaxSpreadPoints"]), 450.0)
        self.assertEqual(bal_orch["InpDryRunLogOnly"], "true")
        self.assertEqual(bal_e4["InpDryRunLogOnly"], "true")

        spr_orch = kit.parse_set_file(KIT_DIR / "presets/FTMO_P1_Sprint_1to3m/Naqex_AccountOrchestrator.set")
        self.assertAlmostEqual(float(spr_orch["InpBasePhaseMult"]), 3.17, places=2)
        self.assertEqual(spr_orch["InpDryRunLogOnly"], "true")

        p2_s6 = kit.parse_set_file(KIT_DIR / "presets/FTMO_P2_Verify/Naqex_WB_FX_USD_BASKET_12U_Z35.set")
        self.assertAlmostEqual(float(p2_s6["InpRiskPercent"]), 0.0, places=2)

        funded_std = kit.parse_set_file(KIT_DIR / "presets/FTMO_Funded_Std_RedNews/Naqex_WB_EXP080_USDJPY.set")
        self.assertEqual(funded_std["InpGuardEnableRedNews"], "true")
        self.assertAlmostEqual(float(funded_std["InpGuardMaxSymbolRiskPct"]), 1.00, places=2)
        self.assertEqual(funded_std["InpDryRunLogOnly"], "true")

        demo_e2 = kit.parse_set_file(KIT_DIR / "presets/FTMO_FreeTrial_Demo/Naqex_WB_EXP080_USDJPY.set")
        dry_e2 = kit.parse_set_file(KIT_DIR / "presets/FTMO_FreeTrial_DryRun/Naqex_WB_EXP080_USDJPY.set")
        self.assertEqual(demo_e2["InpDryRunLogOnly"], "false")
        self.assertEqual(dry_e2["InpDryRunLogOnly"], "true")

    def test_deployment_kit_detects_manifest_tampering_and_zero_ex5_in_exports(self):
        # Confirm zero binary .ex5 files live inside tracked exports/
        self.assertEqual(list(EXPORTS_DIR.rglob("*.ex5")), [])

        # Tamper a manifest hash in a temp kit copy and confirm verify_kit catches it
        with tempfile.TemporaryDirectory() as td:
            tmp_kit = Path(td) / "deployment_kit"
            shutil.copytree(KIT_DIR, tmp_kit)
            mpath = tmp_kit / "manifest.sha256.json"
            mdata = json.loads(mpath.read_text(encoding="utf-8"))
            first_key = next(iter(mdata["tracked_files"]))
            mdata["tracked_files"][first_key]["sha256"] = "0" * 64
            mpath.write_text(json.dumps(mdata), encoding="utf-8")

            rep = kit.verify_kit(exports_dir=EXPORTS_DIR, kit_dir=tmp_kit, ex5_dir=EX5_DIR, require_ex5=False)
            self.assertFalse(rep["ok"])
            self.assertTrue(any("SHA-256 mismatch" in e for e in rep["errors"]))

    def test_powershell_watchdog_dryrun_alerts_and_log_rotation(self):
        ps_script = KIT_DIR / "ops_watchdog/naqex_mt5_watchdog.ps1"
        self.assertTrue(ps_script.exists())

        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            hb = d / "naqex_heartbeat.json"
            state = d / "state"
            now_ts = 1_795_450_000

            # 1. Healthy heartbeat in DryRun mode -> status OK, exit 0, local alert file written, webhook untouched
            hb.write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts - 15,
                        "quote_ts": now_ts - 10,
                        "terminal_connected": True,
                        "positions_state": "CONFIRMED",
                        "balance": 10000.0,
                        "equity": 10025.0,
                        "day_anchor_eq": 10000.0,
                        "daily_dd_pct": 0.0,
                        "static_dd_pct": 0.0,
                        "regime": "NORMAL",
                        "risk_mult": 1.0,
                        "kill_switch": False,
                        "open_positions": 0,
                        "orphan_no_sl": 0,
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )
            p_ok = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps_script),
                    "-DryRun",
                    "-SkipProcessCheck",
                    "-HeartbeatPath",
                    str(hb),
                    "-StateDir",
                    str(state),
                    "-NowUtcOverride",
                    str(now_ts),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(p_ok.returncode, 0, p_ok.stderr)
            out_ok = json.loads(p_ok.stdout)
            self.assertEqual(out_ok["status"], "OK")
            self.assertEqual(out_ok["alerts"], [])
            self.assertTrue(out_ok["alert_sink"]["local_alert_written"])
            self.assertFalse(out_ok["alert_sink"]["webhook_sent"])

            # 2. Stale + KillSwitch + Orphan + RED_BRAKE -> CRITICAL, exit 2 (non-dry-run)
            hb.write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts - 500,
                        "balance": 10000.0,
                        "equity": 9350.0,
                        "day_anchor_eq": 10000.0,
                        "daily_dd_pct": 3.2,
                        "static_dd_pct": 6.5,
                        "regime": "RED_BRAKE",
                        "risk_mult": 0.4,
                        "kill_switch": True,
                        "open_positions": 1,
                        "orphan_no_sl": 1,
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )
            p_crit = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps_script),
                    "-SkipProcessCheck",
                    "-HeartbeatPath",
                    str(hb),
                    "-StateDir",
                    str(state),
                    "-NowUtcOverride",
                    str(now_ts),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(p_crit.returncode, 2, p_crit.stderr)
            out_crit = json.loads(p_crit.stdout)
            self.assertEqual(out_crit["status"], "CRITICAL")
            joined = " | ".join(out_crit["alerts"])
            self.assertIn("HEARTBEAT_STALE", joined)
            self.assertIn("GLOBAL_KILLSWITCH_ACTIVE", joined)
            self.assertIn("ORPHAN_NO_SL_POSITIONS", joined)
            self.assertIn("RISK_REGIME=RED_BRAKE", joined)

            # 3. Log rotation check (seed oversized log > 100 bytes and run non-dry-run with healthy hb)
            hb.write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts - 10,
                        "quote_ts": now_ts - 5,
                        "terminal_connected": True,
                        "positions_state": "CONFIRMED",
                        "balance": 10000.0,
                        "equity": 10000.0,
                        "daily_dd_pct": 0.0,
                        "static_dd_pct": 0.0,
                        "regime": "NORMAL",
                        "risk_mult": 1.0,
                        "kill_switch": False,
                        "open_positions": 0,
                        "orphan_no_sl": 0,
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )
            big_log = state / "naqex_watchdog.log"
            big_log.write_text("X" * 300, encoding="utf-8")
            p_rot = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps_script),
                    "-SkipProcessCheck",
                    "-HeartbeatPath",
                    str(hb),
                    "-StateDir",
                    str(state),
                    "-MaxLogBytes",
                    "100",
                    "-NowUtcOverride",
                    str(now_ts),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(p_rot.returncode, 0, p_rot.stderr)
            out_rot = json.loads(p_rot.stdout)
            self.assertEqual(out_rot["status"], "OK")
            self.assertTrue(out_rot["log_rotations"][0]["rotated"])
            self.assertTrue(list(state.glob("naqex_watchdog.log.*.bak")))

            # 4. Astra F17 regression: future clock skew (>60s) & terminal_connected=false -> CRITICAL exit 2!
            hb.write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts + 200,
                        "terminal_connected": False,
                        "balance": 10000.0,
                        "equity": 10000.0,
                        "daily_dd_pct": 0.0,
                        "static_dd_pct": 0.0,
                        "regime": "NORMAL",
                        "risk_mult": 1.0,
                        "kill_switch": False,
                        "open_positions": 0,
                        "orphan_no_sl": 0,
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )
            p_f17 = subprocess.run(
                [
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(ps_script), "-SkipProcessCheck",
                    "-HeartbeatPath", str(hb), "-StateDir", str(state),
                    "-NowUtcOverride", str(now_ts),
                ],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_f17.returncode, 2, p_f17.stderr)
            out_f17 = json.loads(p_f17.stdout)
            joined_f17 = " | ".join(out_f17["alerts"])
            self.assertIn("HEARTBEAT_FUTURE_TIMESTAMP", joined_f17)
            self.assertIn("BROKER_DISCONNECTED", joined_f17)

    def test_activation_card_and_holdout_lock_invariants(self):
        # Holdout 2025+ lock remains strictly untouched
        self.assertEqual(len(assert_holdout_locked()), 64)

        card = (KIT_DIR / "ACTIVATION-CARD-LOCAL-MT5.md").read_text(encoding="utf-8")
        for pname in EXPECTED_PROFILES:
            self.assertIn(pname, card, f"Activation card missing profile {pname}")
        # Ensure zero bare dollar-pair markdown math accidents in Vietnamese prose
        self.assertIsNone(re.search(r"\$\d+", card), "Use 'USD' instead of bare $ amounts in prose")

    def test_patch1_nas100_and_broker_symbol_aliases_and_firm_chart_mapping(self):
        mqh_src = (EXPORTS_DIR / "Include/Naqex_PropGuard.mqh").read_text(encoding="utf-8")
        self.assertIn("StringToUpper(", mqh_src)
        for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "XAU", "BTC", "GER40", "DE40", "DAX", "UK100", "FTSE"):
            self.assertIn(f'"{tok}"', mqh_src, f"PropGuard missing broker symbol alias {tok}")

        # E5 .mq5 default benchmark remains US500.cash for parity
        e5_parsed = parity.parse_mq5_source(EXPORTS_DIR / "Naqex_WB_IDX_RS_US100_LEAD_1130.mq5")
        self.assertEqual(e5_parsed["inputs"]["InpBenchmarkSymbol"]["value"], "US500.cash")

        # Per-firm chart mapping: The5ers uses NAS100 + verification note; FTMO uses US100.cash
        for pname, cfg in kit.OPERATIONAL_PROFILES.items():
            meta = json.loads((KIT_DIR / "presets" / pname / "profile_meta.json").read_text(encoding="utf-8"))
            att = meta["chart_attachments"]
            if cfg["firm"] == "The5ers":
                self.assertEqual(att["E4_US100_SESS40"]["symbol"], "NAS100")
                self.assertEqual(att["E5_US100_RS1130"]["symbol"], "NAS100")
                note = meta.get("broker_symbol_verification_note", "")
                self.assertIn("SPX500", note)
                self.assertIn("US500", note)
                e5_set_txt = (KIT_DIR / "presets" / pname / "Naqex_WB_IDX_RS_US100_LEAD_1130.set").read_text(encoding="utf-8")
                self.assertIn("Attach: NAS100 M5", e5_set_txt)
                self.assertIn("SPX500 vs US500", e5_set_txt)
                e5_set = kit.parse_set_file(KIT_DIR / "presets" / pname / "Naqex_WB_IDX_RS_US100_LEAD_1130.set")
                self.assertEqual(e5_set["InpBenchmarkSymbol"], "SPX500")
                e7_set = kit.parse_set_file(KIT_DIR / "presets" / pname / "Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.set")
                self.assertEqual(e7_set["InpEquitySymbol"], "NAS100")
            else:
                self.assertEqual(att["E4_US100_SESS40"]["symbol"], "US100.cash")
                self.assertEqual(att["E5_US100_RS1130"]["symbol"], "US100.cash")

    def test_patch2b_safe_pre_flatten_window_vs_hard_ban_in_propguard_and_all_8_eas(self):
        mqh_src = (EXPORTS_DIR / "Include/Naqex_PropGuard.mqh").read_text(encoding="utf-8")
        mqh_parsed = parity.parse_mq5_source(EXPORTS_DIR / "Include/Naqex_PropGuard.mqh")
        self.assertEqual(mqh_parsed["inputs"]["InpGuardNewsPadSec"]["value"], 300)
        self.assertEqual(mqh_parsed["inputs"]["InpGuardNewsHardBanSec"]["value"], 135)
        self.assertIn("IsInRedNewsPreFlattenWindowFor", mqh_src)
        self.assertIn("MathAbs(diff) <= InpGuardNewsHardBanSec", mqh_src)
        self.assertIn("diff > InpGuardNewsHardBanSec && diff <= effPad", mqh_src)
        self.assertIn("MathMax(InpGuardNewsPadSec, 3600)", mqh_src)

        for eid, contract in parity.ENGINE_PARITY_CONTRACTS.items():
            ea_src = (EXPORTS_DIR / contract["file"]).read_text(encoding="utf-8")
            if eid == "S6_FX_USD_BSK":
                self.assertIn("HasOwnPositionInPreFlattenWindow()", ea_src)
                self.assertIn('CloseOwnPositionsInPreFlatten("NEWS_PRE_FLATTEN")', ea_src)
            else:
                self.assertIn("g_guard.IsInRedNewsPreFlattenWindow()", ea_src, f"{eid} missing pre-flatten guard")
                self.assertNotIn(
                    'if(HasOpenPosition()) CloseOwnPositions("NEWS_PRE_FLATTEN");',
                    ea_src,
                    f"{eid} still flattens unconditionally inside hard +/-2m news ban",
                )

        # Every .set file carries InpGuardNewsPadSec=300 and InpGuardNewsHardBanSec=135
        for set_file in (KIT_DIR / "presets").rglob("*.set"):
            kv = kit.parse_set_file(set_file)
            self.assertEqual(kv.get("InpGuardNewsPadSec"), "300", f"{set_file} bad pad")
            self.assertEqual(kv.get("InpGuardNewsHardBanSec"), "135", f"{set_file} bad hard ban")

    def test_patch3_tightened_p1_p2_symcap_and_invariant_rejection(self):
        expected_symcap = {
            "FTMO_FreeTrial_DryRun": 1.00,
            "FTMO_FreeTrial_Demo": 1.00,
            "FTMO_P1_Balanced_3to6m": 1.75,
            "FTMO_P1_Sprint_1to3m": 2.00,
            "FTMO_P2_Verify": 1.50,
            "FTMO_Funded_Swing_Safe": 1.00,
            "FTMO_Funded_Std_RedNews": 1.00,
            "The5ers_HighStakes_P1_Balanced": 1.75,
            "The5ers_HighStakes_P1_Sprint": 2.00,
            "The5ers_HighStakes_Funded": 1.00,
        }
        for pname, exp_cap in expected_symcap.items():
            for sp in (KIT_DIR / "presets" / pname).glob("*.set"):
                kv = kit.parse_set_file(sp)
                self.assertAlmostEqual(
                    float(kv["InpGuardMaxSymbolRiskPct"]),
                    exp_cap,
                    places=2,
                    msg=f"{pname}/{sp.name} SYMCAP mismatch",
                )

        # Confirm verify_kit catches an overly loose P1 SYMCAP (> 2.00) even if manifest SHA is re-signed
        with tempfile.TemporaryDirectory() as td:
            tmp_kit = Path(td) / "deployment_kit"
            shutil.copytree(KIT_DIR, tmp_kit)
            target_set = tmp_kit / "presets/FTMO_P1_Balanced_3to6m/Naqex_WB_EXP080_USDJPY.set"
            target_set.write_text(
                target_set.read_text(encoding="utf-8").replace(
                    "InpGuardMaxSymbolRiskPct=1.75", "InpGuardMaxSymbolRiskPct=3.00"
                ),
                encoding="utf-8",
            )
            rep = kit.verify_kit(exports_dir=EXPORTS_DIR, kit_dir=tmp_kit, ex5_dir=EX5_DIR, require_ex5=False)
            self.assertFalse(rep["ok"])
            self.assertTrue(any("P1 SYMCAP violated" in e for e in rep["errors"]), rep["errors"])

    def test_patch4a_orchestrator_profit_lock_prague_server_reset_and_heartbeat(self):
        orch_src = (EXPORTS_DIR / "Naqex_AccountOrchestrator.mq5").read_text(encoding="utf-8")
        orch_parsed = parity.parse_mq5_source(EXPORTS_DIR / "Naqex_AccountOrchestrator.mq5")
        self.assertAlmostEqual(float(orch_parsed["inputs"]["InpProfitLockPct"]["value"]), 0.00, places=2)
        self.assertAlmostEqual(float(orch_parsed["inputs"]["InpProfitLockMult"]["value"]), 2.00, places=2)
        self.assertEqual(orch_parsed["inputs"]["InpDailyResetMode"]["value"], 1)
        self.assertIs(orch_parsed["inputs"]["InpAllowManualHaltFile"]["value"], False)
        for tok in ("PragueUtcOffsetHours", "CurrentResetDayKey", '"PROFIT_LOCK"', '\\"profit_pct\\":%.3f', '\\"reset_mode\\":%d'):
            self.assertIn(tok, orch_src, f"Orchestrator missing {tok}")

        for pname, cfg in kit.OPERATIONAL_PROFILES.items():
            kv = kit.parse_set_file(KIT_DIR / "presets" / pname / "Naqex_AccountOrchestrator.set")
            exp_reset = "1" if cfg["firm"] == "FTMO" else "0"
            self.assertEqual(kv["InpDailyResetMode"], exp_reset, f"{pname} reset mode")
            self.assertEqual(kv["InpAllowManualHaltFile"], "false", f"{pname} manual halt must default false")
            if "_P1_" in pname:
                exp_pl = 4.00 if cfg["firm"] == "The5ers" else 5.00
                self.assertAlmostEqual(float(kv["InpProfitLockPct"]), exp_pl, places=2)
                self.assertAlmostEqual(float(kv["InpProfitLockMult"]), 1.34, places=2)
                self.assertAlmostEqual(float(cfg["ea_risk_scale"]) * float(kv["InpProfitLockMult"]), 2.01, places=2)
            elif "_P2_" in pname:
                self.assertAlmostEqual(float(kv["InpProfitLockPct"]), 3.00, places=2)
                self.assertAlmostEqual(float(kv["InpProfitLockMult"]), 1.50, places=2)
            else:
                self.assertAlmostEqual(float(kv["InpProfitLockPct"]), 0.00, places=2)

        # Verify manifest snapshots the expanded 6-currency red-news CSV (USD/EUR/GBP/JPY/AUD/CAD)
        manifest = json.loads((KIT_DIR / "manifest.sha256.json").read_text(encoding="utf-8"))
        csv_dep = manifest["external_dependencies"]["tooling/ai-engines/exports/Files/naqex_red_news_utc.csv"]
        self.assertGreaterEqual(csv_dep["rows_at_build"], 430)
        self.assertEqual(len(csv_dep["snapshot_sha256"]), 64)
        csv_rep = parity.verify_red_news_csv(EXPORTS_DIR / "Files/naqex_red_news_utc.csv")
        self.assertEqual(csv_dep["snapshot_sha256"], csv_rep["sha256"])
        self.assertEqual(csv_rep["currencies"], ["AUD", "CAD", "EUR", "GBP", "JPY", "USD"])

    def test_cycle2_scaled_tier_config_and_the5ers_4_8_fail_closed(self):
        # 1. FTMO Swing 10K / 25K / 50K / 100K (5%/10% DD, Prague reset, SYMCAP 1.75 / 1.50 / 1.00)
        for cap in (10000.0, 25000.0, 50000.0, 100000.0):
            p1 = kit.build_scaled_tier_config("FTMO_Swing", cap, phase="P1_Balanced", dd_mode="5_10")
            self.assertEqual(p1["firm"], "FTMO")
            self.assertEqual(p1["capital_usd"], cap)
            self.assertEqual(p1["daily_reset_mode"], 1)
            self.assertAlmostEqual(p1["max_symbol_risk_pct"], 1.75, places=2)
            self.assertAlmostEqual(p1["profit_lock_pct"], 5.00, places=2)
            self.assertAlmostEqual(p1["profit_lock_mult"], 1.34, places=2)
            self.assertTrue(p1["dry_run_preset"] and p1["arm_locked"])
            self.assertEqual(p1["order_send_count"], 0)
            self.assertEqual(p1["chart_attachments"]["E4_US100_SESS40"]["symbol"], "US100.cash")

        p2 = kit.build_scaled_tier_config("FTMO_Swing", 25000.0, phase="P2_Verify", dd_mode="5_10")
        self.assertAlmostEqual(p2["max_symbol_risk_pct"], 1.50, places=2)
        self.assertAlmostEqual(p2["profit_lock_pct"], 3.00, places=2)

        funded_sw = kit.build_scaled_tier_config("FTMO_Swing", 50000.0, phase="Funded", dd_mode="5_10", enable_red_news=False)
        self.assertFalse(funded_sw["enable_red_news"])
        self.assertAlmostEqual(funded_sw["max_symbol_risk_pct"], 1.00, places=2)
        self.assertAlmostEqual(funded_sw["profit_lock_pct"], 0.00, places=2)

        # 2. The5ers High Stakes 5K / 20K (5%/10% DD, NAS100, Server midnight reset, Red-News ON)
        for cap in (5000.0, 20000.0):
            t5 = kit.build_scaled_tier_config("The5ers", cap, phase="P1_Balanced", dd_mode="5_10")
            self.assertEqual(t5["daily_reset_mode"], 0)
            self.assertTrue(t5["enable_red_news"])
            self.assertAlmostEqual(t5["max_symbol_risk_pct"], 1.75, places=2)
            self.assertEqual(t5["chart_attachments"]["E4_US100_SESS40"]["symbol"], "NAS100")

        # 3. The5ers >= 50K MUST fail-closed on dd_mode="5_10" unless explicitly overridden!
        for cap in (50000.0, 60000.0, 100000.0):
            with self.assertRaises(ValueError) as cm:
                kit.build_scaled_tier_config("The5ers", cap, phase="P1_Balanced", dd_mode="5_10")
            self.assertIn("4% daily / 8% static", str(cm.exception))

            # Calibrated 4%/8% envelope must match Cycle-1 empirical caps exactly
            c48 = kit.build_scaled_tier_config("The5ers", cap, phase="P1_Balanced", dd_mode="4_8")
            self.assertEqual(c48["dd_mode"], "4_8")
            self.assertEqual(c48["daily_reset_mode"], 0)
            self.assertAlmostEqual(c48["ea_risk_scale"], 1.00, places=2)
            self.assertAlmostEqual(c48["base_phase_mult"], 2.75, places=2)
            self.assertAlmostEqual(c48["profit_lock_pct"], 4.00, places=2)
            self.assertAlmostEqual(c48["profit_lock_mult"], 1.50, places=2)
            self.assertAlmostEqual(c48["max_symbol_risk_pct"], 1.15, places=2)
            self.assertAlmostEqual(c48["kill_daily_dd_pct"], 2.80, places=2)
            self.assertAlmostEqual(c48["kill_static_dd_pct"], 6.50, places=2)
            self.assertAlmostEqual(c48["ea_daily_stop_pct"], 2.80, places=2)
            self.assertLess(c48["kill_daily_dd_pct"], 4.00)
            self.assertLess(c48["kill_static_dd_pct"], 8.00)
            self.assertTrue(c48["dry_run_preset"] and c48["arm_locked"])
            self.assertEqual(c48["orchestrator_inputs"]["InpKillDailyDdPct"], 2.80)
            self.assertEqual(c48["orchestrator_inputs"]["InpGuardNewsHardBanSec"], 135)

        # Refuse disabling red-news on The5ers
        with self.assertRaises(ValueError):
            kit.build_scaled_tier_config("The5ers", 20000.0, phase="Funded", dd_mode="5_10", enable_red_news=False)

        # 4. CLI --preview-tier-json read-only check (PASS for 4_8, FAIL exit 2 for unsafe 5_10 >= 50K)
        py = sys.executable
        cli = str(EXPORTS_DIR / "verify_deployment_kit.py")
        p_ok = subprocess.run(
            [py, cli, "--preview-tier-json", "The5ers:50000:P1_Balanced:4_8"],
            capture_output=True, text=True, check=False, timeout=20,
        )
        self.assertEqual(p_ok.returncode, 0, p_ok.stderr)
        js_ok = json.loads(p_ok.stdout)
        self.assertEqual(js_ok["order_send_count"], 0)
        self.assertAlmostEqual(js_ok["max_symbol_risk_pct"], 1.15, places=2)
        self.assertAlmostEqual(js_ok["kill_daily_dd_pct"], 2.80, places=2)

        p_bad = subprocess.run(
            [py, cli, "--preview-tier-json", "The5ers:50000:P1_Balanced:5_10"],
            capture_output=True, text=True, check=False, timeout=20,
        )
        self.assertEqual(p_bad.returncode, 2)
        self.assertIn("SAFETY ABORT", p_bad.stderr)

    def test_cycle2_flat_sync_copies_ex5_and_red_news_csv_with_sha256_and_profile_preserves_inputs(self):
        import build_ftmo_profile as prof

        sync_ps = KIT_DIR / "vps_kit/sync_updated_ex5_when_flat.ps1"
        src_csv = EXPORTS_DIR / "Files/naqex_red_news_utc.csv"
        exp_csv_sha = kit.sha256_file(src_csv)

        with tempfile.TemporaryDirectory() as td:
            mt5_root = Path(td) / "mock_node1_mt5"
            files_dir = mt5_root / "MQL5/Files"
            experts_dir = mt5_root / "MQL5/Experts/Naqex"
            files_dir.mkdir(parents=True)
            experts_dir.mkdir(parents=True)

            now_ts = 1_795_500_000
            # 1. Fail-closed when open_positions == 1: exit 2, zero files copied
            (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 1, "total_account_positions": 1, "pending_orders": 0, "terminal_connected": True, "positions_state": "CONFIRMED", "utc_ts": now_ts - 10}), encoding="utf-8")
            p_blk = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync_ps), "-TargetMt5Root", str(mt5_root), "-NowUtcOverride", str(now_ts)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_blk.returncode, 2)
            self.assertEqual(json.loads(p_blk.stdout)["status"], "BLOCKED_OPEN_POSITIONS")
            self.assertEqual(list(experts_dir.glob("*.ex5")), [])
            self.assertFalse((files_dir / "naqex_red_news_utc.csv").exists())

            # 1a. Astra R2-03 CRITICAL regression: disconnected heartbeat MUST NEVER allow sync even if open_positions==0!
            (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 0, "terminal_connected": False, "positions_state": "UNKNOWN", "utc_ts": now_ts - 2}), encoding="utf-8")
            p_disc = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync_ps), "-TargetMt5Root", str(mt5_root), "-NowUtcOverride", str(now_ts)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_disc.returncode, 2)
            self.assertEqual(json.loads(p_disc.stdout)["status"], "BLOCKED_BROKER_DISCONNECTED")
            self.assertEqual(list(experts_dir.glob("*.ex5")), [])

            # 1a-ii. Astra R2-03: non-Naqex account position or pending order blocks flat-sync!
            (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 0, "total_account_positions": 1, "pending_orders": 0, "terminal_connected": True, "positions_state": "CONFIRMED", "utc_ts": now_ts - 5}), encoding="utf-8")
            p_nonnq = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync_ps), "-TargetMt5Root", str(mt5_root), "-NowUtcOverride", str(now_ts)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_nonnq.returncode, 2)
            self.assertEqual(json.loads(p_nonnq.stdout)["status"], "BLOCKED_OPEN_POSITIONS")

            # 1b. Astra F19 regression: stale heartbeat (> 180s) MUST fail closed (exit 2) even when connected & flat!
            (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 0, "total_account_positions": 0, "pending_orders": 0, "terminal_connected": True, "positions_state": "CONFIRMED", "utc_ts": now_ts - 600}), encoding="utf-8")
            p_stale = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync_ps), "-TargetMt5Root", str(mt5_root), "-NowUtcOverride", str(now_ts)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_stale.returncode, 2)
            self.assertEqual(json.loads(p_stale.stdout)["status"], "BLOCKED_STALE_HEARTBEAT")
            self.assertEqual(list(experts_dir.glob("*.ex5")), [])

            # 2. Live sync when connected, confirmed flat & fresh (runs when gitignored .runtime .ex5 binaries exist locally)
            has_local_ex5 = EX5_DIR.is_dir() and len(list(EX5_DIR.glob("*.ex5"))) >= 9
            if has_local_ex5:
                (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 0, "total_account_positions": 0, "pending_orders": 0, "terminal_connected": True, "positions_state": "CONFIRMED", "account_login": 1515343166, "account_server": "FTMO-Demo", "utc_ts": now_ts - 10}), encoding="utf-8")
                p_sync = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync_ps), "-TargetMt5Root", str(mt5_root), "-ExpectedLogin", "1515343166", "-ExpectedServer", "FTMO-Demo", "-NowUtcOverride", str(now_ts)],
                    capture_output=True, text=True, check=False, timeout=30,
                )
                self.assertEqual(p_sync.returncode, 0, p_sync.stderr)
                out = json.loads(p_sync.stdout)
                self.assertEqual(out["status"], "SYNCED_CLEAN_FLAT")
                self.assertEqual(out["files_count"], 9)
                self.assertTrue(out["sha256_verified"])
                self.assertTrue(out["manifest_checked"])
                self.assertEqual(out["order_send"], 0)
                self.assertGreaterEqual(out["red_news_csv"]["rows"], 470)
                self.assertEqual(out["red_news_csv"]["sha256"], exp_csv_sha)
                self.assertTrue(out["red_news_csv"]["synced"])
                self.assertEqual(len(list(experts_dir.glob("*.ex5"))), 9)
                self.assertEqual(kit.sha256_file(files_dir / "naqex_red_news_utc.csv"), exp_csv_sha)

            # 3. build_ftmo_profile preserves Cycle-1 inputs & applies firm-specific NAS100 mapping for The5ers
            res_ftmo = prof.build_mt5_chart_profile(
                data_dir=mt5_root, preset_profile="FTMO_P1_Balanced_3to6m", mt5_profile_name="Naqex_FTMO_P1"
            )
            c1_ftmo = (Path(res_ftmo["profile_dir"]) / "chart01.chr").read_bytes().decode("utf-16")
            self.assertIn("InpGuardNewsHardBanSec=135", c1_ftmo)
            self.assertIn("InpProfitLockPct=5.00", c1_ftmo)
            self.assertIn("InpProfitLockMult=1.34", c1_ftmo)
            self.assertIn("InpDailyResetMode=1", c1_ftmo)
            self.assertIn("InpGuardMaxSymbolRiskPct=1.75", c1_ftmo)

            res_t5 = prof.build_mt5_chart_profile(
                data_dir=mt5_root, preset_profile="The5ers_HighStakes_P1_Balanced", mt5_profile_name="Naqex_The5ers_P1"
            )
            c1_t5 = (Path(res_t5["profile_dir"]) / "chart01.chr").read_bytes().decode("utf-16")
            c5_t5 = (Path(res_t5["profile_dir"]) / "chart05.chr").read_bytes().decode("utf-16")
            self.assertIn("InpDailyResetMode=0", c1_t5)
            self.assertIn("InpProfitLockPct=4.00", c1_t5)
            self.assertIn("InpGuardNewsHardBanSec=135", c5_t5)
            self.assertIn("symbol=NAS100", c5_t5)

    def test_vps_live_regressions_share_read_disconnected_guard_and_shallow_sync_path(self):
        exp_dir = Path(__file__).resolve().parents[1] / "exports"
        pg = (exp_dir / "Include" / "Naqex_PropGuard.mqh").read_text(encoding="utf-8")
        orch = (exp_dir / "Naqex_AccountOrchestrator.mq5").read_text(encoding="utf-8")
        sync_ps = (exp_dir / "deployment_kit" / "vps_kit" / "sync_updated_ex5_when_flat.ps1").read_text(encoding="utf-8")

        # 1. Multi-EA parallel startup must open red-news CSV with FILE_SHARE_READ | FILE_SHARE_WRITE + retry
        self.assertIn("FILE_READ | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE", pg)
        self.assertIn("[PROPGUARD-OK] Loaded %d red-news events", pg)
        # 2. Orchestrator must never latch sticky g_autoKillActive or fake 100% DD before broker login
        self.assertIn("bool IsAccountSynced(", orch)
        self.assertIn('"DISCONNECTED"', orch)
        self.assertIn("[ORCH-INIT]", orch)
        # 3. Flat-sync script must safely handle shallow VPS paths (e.g. C:\Naqex\ops\vps_kit)
        self.assertIn("function Get-AncestorPath", sync_ps)
        self.assertNotIn("Split-Path -Parent (Split-Path -Parent (Split-Path -Parent", sync_ps)

        # 4. Astra R2-02 / R2-03 / R2-04 / R2-05 / R2-07 & Round-3 Master_Prop7E architectural invariants
        self.assertIn("CurrentAccountServerHash()", pg)
        self.assertIn("IsRedNewsCalendarHealthyFor(", pg)
        self.assertIn("EST03UTC", pg)
        self.assertIn("ComputeFactorHeadroomPct(", pg)
        self.assertIn("if(refPx <= 0.0 || freeMargin <= 0.0) return 0.0;", pg)
        self.assertIn('"UNKNOWN", -1, -1, -1, -1', orch)
        self.assertIn("CurrentResetStartServerTime()", orch)

        master = (exp_dir / "Naqex_Master_Prop7E.mq5").read_text(encoding="utf-8")
        sigs = (exp_dir / "Include" / "Naqex_Signals_7E.mqh").read_text(encoding="utf-8")
        self.assertIn("CopyTicksRange(", sigs)
        self.assertIn("ReconstructM1Window(", sigs)
        self.assertIn("OnTradeTransaction(", master)
        self.assertIn("InpMaxJpyClusterPct", master)
        self.assertIn("InpMaxUsdClusterPct", master)
        self.assertIn("BARRIER_TAPER", master)

    def test_blackfriday_master_prop7e_4_lifecycle_presets_fail_closed_and_checklist(self):
        has_local_ex5 = EX5_DIR.is_dir() and len(list(EX5_DIR.glob("*.ex5"))) >= 10
        rep = kit.verify_kit(exports_dir=EXPORTS_DIR, kit_dir=KIT_DIR, ex5_dir=EX5_DIR, require_ex5=has_local_ex5)
        self.assertTrue(rep["ok"], f"Kit verification failed: {rep['errors']}")
        self.assertEqual(rep["presets_checked"], 90)
        self.assertEqual(rep["master_presets_checked"], 4)
        self.assertEqual(rep["total_presets_checked"], 94)

        master_keys = (
            set(parity.parse_mq5_source(EXPORTS_DIR / "Naqex_Master_Prop7E.mq5")["inputs"])
            | set(parity.parse_mq5_source(EXPORTS_DIR / "Include/Naqex_PropGuard.mqh")["inputs"])
        )
        manifest = json.loads((KIT_DIR / "manifest.sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["master_lifecycle_presets_count"], 4)

        expected_specs = {
            "FTMO_Std10K_MasterProp7E_P1_Balanced_3x.set": (3.00, 10.00, 5.00, 1.50, 3.00, 7.50, 1.50, 2.00, 1.75, 1.50, 2.50),
            "FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set": (4.00, 10.00, 5.00, 2.01, 3.50, 8.00, 1.75, 2.25, 2.00, 1.75, 3.00),
            "FTMO_Std10K_MasterProp7E_P2_Verify_2x.set": (2.00, 5.00, 2.50, 1.00, 2.50, 7.50, 1.25, 1.75, 1.50, 1.25, 2.25),
            "FTMO_Std10K_MasterProp7E_Funded_Safe_1x.set": (1.00, 0.00, 0.00, 1.00, 2.50, 7.50, 1.00, 1.50, 1.25, 1.00, 2.00),
        }
        for fname, exp in expected_specs.items():
            p = KIT_DIR / "presets" / fname
            self.assertTrue(p.exists(), f"Missing MasterProp7E preset: {fname}")
            rel = p.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
            self.assertIn(rel, manifest["tracked_files"], f"{fname} not hashed in manifest.sha256.json")

            raw = p.read_text(encoding="utf-8")
            self.assertNotIn("$", raw)
            self.assertNotIn("Password=", raw)
            self.assertNotIn("Login=", raw)

            kv = kit.parse_set_file(p)
            self.assertEqual(set(kv) - master_keys, set(), f"Unknown keys in {fname}")

            # Fail-closed safety & spread/news locks
            self.assertEqual(kv["InpDryRunLogOnly"], "true")
            self.assertEqual(kv["InpGuardDryRunLogOnly"], "true")
            self.assertEqual(kv["InpShadowCompareMode"], "false")
            self.assertEqual(kv["InpGuardUseOrchestrator"], "false")
            self.assertEqual(kv["InpDailyResetMode"], "1")
            self.assertEqual(kv["InpGuardEnableRedNews"], "true")
            self.assertEqual(kv["InpGuardRedNewsCsvFile"], "naqex_red_news_utc.csv")
            self.assertEqual(int(kv["InpGuardNewsHardBanSec"]), 135)
            self.assertAlmostEqual(float(kv["InpGuardMaxSpreadPoints"]), 35.0, places=2)
            self.assertAlmostEqual(float(kv["InpMaxEurJpySpreadPoints"]), 45.0, places=2)
            self.assertAlmostEqual(float(kv["InpMaxIndexSpreadPoints"]), 450.0, places=2)

            mult, tgt, pl_pct, pl_mult, k_day, k_st, sym_r, usd_c, jpy_c, idx_c, tot_r = exp
            self.assertAlmostEqual(float(kv["InpBasePhaseMult"]), mult, places=2)
            self.assertAlmostEqual(float(kv["InpTargetProfitPct"]), tgt, places=2)
            self.assertAlmostEqual(float(kv["InpProfitLockPct"]), pl_pct, places=2)
            self.assertAlmostEqual(float(kv["InpProfitLockMult"]), pl_mult, places=2)
            self.assertAlmostEqual(float(kv["InpKillDailyDdPct"]), k_day, places=2)
            self.assertAlmostEqual(float(kv["InpKillStaticDdPct"]), k_st, places=2)
            self.assertAlmostEqual(float(kv["InpGuardMaxDailyLossPct"]), k_day, places=2)
            self.assertAlmostEqual(float(kv["InpMaxSymbolRiskPct"]), sym_r, places=2)
            self.assertAlmostEqual(float(kv["InpGuardMaxSymbolRiskPct"]), sym_r, places=2)
            self.assertAlmostEqual(float(kv["InpMaxUsdClusterPct"]), usd_c, places=2)
            self.assertAlmostEqual(float(kv["InpMaxJpyClusterPct"]), jpy_c, places=2)
            self.assertAlmostEqual(float(kv["InpMaxIdxClusterPct"]), idx_c, places=2)
            self.assertAlmostEqual(float(kv["InpMaxAccountOpenRiskPct"]), tot_r, places=2)

        # Checklist artifact hygiene & manifest tracking
        chk = KIT_DIR / "BLACKFRIDAY-FTMO-10K-ACTIVATION-CHECKLIST.md"
        self.assertTrue(chk.exists())
        chk_rel = chk.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        self.assertIn(chk_rel, manifest["tracked_files"])
        chk_txt = chk.read_text(encoding="utf-8")
        self.assertNotIn("$", chk_txt)
        self.assertIn("30/11/2026", chk_txt)
        self.assertIn("node_ctl.py", chk_txt)
        self.assertIn("Naqex_Master_Prop7E", chk_txt)
        self.assertIsNone(re.search(r"(Password=|100\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)", chk_txt))

        # Negative test: verify_kit catches fail-closed breach, bad US100 spread cap, and unknown input keys
        with tempfile.TemporaryDirectory() as td:
            tmp_kit = Path(td) / "deployment_kit"
            shutil.copytree(KIT_DIR, tmp_kit)
            bad_set = tmp_kit / "presets/FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set"
            txt = bad_set.read_text(encoding="utf-8")
            txt = txt.replace("InpDryRunLogOnly=true", "InpDryRunLogOnly=false")
            txt = txt.replace("InpMaxIndexSpreadPoints=450.00", "InpMaxIndexSpreadPoints=35.00")
            txt += "InpBogusUnknownParam=123\n"
            bad_set.write_text(txt, encoding="utf-8")

            bad_rep = kit.verify_kit(exports_dir=EXPORTS_DIR, kit_dir=tmp_kit, ex5_dir=EX5_DIR, require_ex5=False)
            self.assertFalse(bad_rep["ok"])
            joined = " | ".join(bad_rep["errors"])
            self.assertIn("InpDryRunLogOnly=true", joined)
            self.assertIn("InpMaxIndexSpreadPoints must be 450.0", joined)
            self.assertIn("InpBogusUnknownParam", joined)

    def test_master_vs_legacy_7e_1to1_parity_and_drift_detection(self):
        # 1. Positive verification on real production sources
        rep = parity.audit_master_vs_legacy_7e(exports_dir=EXPORTS_DIR)
        self.assertTrue(rep["ok"], f"Master vs Legacy 7E parity failed: {rep['unintended_drifts']}")
        self.assertEqual(rep["engines_checked"], 7)
        self.assertEqual(rep["engines_matched"], 7)
        self.assertEqual(rep["unintended_drifts"], [])
        self.assertTrue(rep["orchestrator_parity"]["ok"])
        self.assertGreaterEqual(rep["orchestrator_parity"]["shared_inputs_verified"], 15)
        self.assertGreaterEqual(len(rep["intentional_differences"]), 7)
        self.assertGreaterEqual(len(rep["operational_notes"]), 2)

        for eid in (
            "E1_USDJPY_TOKYO",
            "E2_USDJPY_EXP80",
            "E3_GBPUSD_VH",
            "E4_US100_SESS40",
            "E5_US100_RS1130",
            "E6_EURJPY_VOLCOMP",
            "E7_USDJPY_NY10ET",
        ):
            self.assertIn(eid, rep["engine_comparisons"])
            self.assertTrue(rep["engine_comparisons"][eid]["ok"], f"{eid} failed: {rep['engine_comparisons'][eid]}")

        # 2. Full parity audit includes master_vs_legacy_7e
        full_rep = parity.run_parity_audit(exports_dir=EXPORTS_DIR, ex5_dir=None, require_ex5=False)
        self.assertTrue(full_rep["ok"])
        self.assertTrue(full_rep["master_vs_legacy_7e"]["ok"])

        # 3. Negative drift-injection check on temp copy of exports/
        with tempfile.TemporaryDirectory() as td:
            tmp_exp = Path(td) / "exports"
            shutil.copytree(EXPORTS_DIR / "Include", tmp_exp / "Include")
            shutil.copytree(EXPORTS_DIR / "Files", tmp_exp / "Files")
            for mq5 in EXPORTS_DIR.glob("*.mq5"):
                shutil.copy2(mq5, tmp_exp / mq5.name)

            # Mutate Signals header: break E2 risk %, E2 trigger mult, and E6 magic
            sig_p = tmp_exp / "Include/Naqex_Signals_7E.mqh"
            sig_txt = sig_p.read_text(encoding="utf-8")
            sig_txt = sig_txt.replace("m_baseRisk[1] = 0.59;", "m_baseRisk[1] = 0.99;")
            sig_txt = sig_txt.replace("dayOpen + 0.80 * atrD1", "dayOpen + 0.99 * atrD1", 1)
            sig_txt = sig_txt.replace("it.magic = 20261128;", "it.magic = 20261199;")
            sig_p.write_text(sig_txt, encoding="utf-8")

            # Mutate Master EA: drift KillDailyDdPct away from Legacy Orchestrator
            m_p = tmp_exp / "Naqex_Master_Prop7E.mq5"
            m_txt = m_p.read_text(encoding="utf-8")
            m_txt = m_txt.replace("InpKillDailyDdPct         = 3.00;", "InpKillDailyDdPct         = 9.00;")
            m_p.write_text(m_txt, encoding="utf-8")

            bad = parity.audit_master_vs_legacy_7e(exports_dir=tmp_exp)
            self.assertFalse(bad["ok"])
            joined = " | ".join(bad["unintended_drifts"])
            self.assertIn("E2_USDJPY_EXP80: Signals m_baseRisk[1]=0.99 != legacy InpRiskPercent=0.59", joined)
            self.assertIn("E2_USDJPY_EXP80: trigger mult mismatch", joined)
            self.assertIn("E6_EURJPY_VOLCOMP: Signals block missing exact magic 20261128", joined)
            self.assertIn("Orchestrator parity input InpKillDailyDdPct", joined)

        # 4. Verify plain-Vietnamese parity receipt hygiene
        receipt = REPO_ROOT / "planning/research/MASTER-7E-VS-LEGACY-PARITY-AUDIT-20261125.md"
        self.assertTrue(receipt.exists(), "Missing Mũi 4 parity receipt document")
        self.assertLessEqual(receipt.stat().st_size, 15 * 1024)
        rec_txt = receipt.read_text(encoding="utf-8")
        self.assertNotIn("$", rec_txt)
        self.assertIsNone(re.search(r"(Password=|100\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)", rec_txt))


if __name__ == "__main__":
    unittest.main()
