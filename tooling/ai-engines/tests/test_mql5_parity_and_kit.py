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
        rep = parity.run_parity_audit(exports_dir=EXPORTS_DIR, ex5_dir=EX5_DIR, require_ex5=True)
        self.assertTrue(rep["ok"], f"Parity audit failed: {json.dumps(rep, indent=2)}")
        self.assertEqual(rep["engines_checked"], 8)
        self.assertEqual(rep["engines_passed"], 8)
        self.assertEqual(rep["unique_magics"], list(range(20261122, 20261130)))
        self.assertTrue(rep["propguard"]["ok"])
        self.assertTrue(rep["orchestrator"]["ok"])
        self.assertTrue(rep["red_news_csv"]["ok"])
        self.assertGreaterEqual(rep["red_news_csv"]["rows"], 200)

        # Verify all 9 compiled .ex5 binaries + MetaEditor64 logs show 0 errors, 0 warnings
        comp = rep["compile_artifacts"]
        self.assertTrue(comp["ok"], f"Compile artifacts failed: {comp['errors']}")
        self.assertEqual(len(comp["files"]), 9)
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
        rep = kit.verify_kit(exports_dir=EXPORTS_DIR, kit_dir=KIT_DIR, ex5_dir=EX5_DIR, require_ex5=True)
        self.assertTrue(rep["ok"], f"Deployment kit verification failed: {rep['errors']}")
        self.assertEqual(rep["profiles_expected"], 10)
        self.assertEqual(rep["presets_checked"], 90)
        self.assertEqual(rep["verified_ex5_files"], 9)

        manifest = json.loads((KIT_DIR / "manifest.sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["profiles"].keys()), EXPECTED_PROFILES)
        self.assertEqual(manifest["order_send_count"], 0)
        self.assertEqual(manifest["compiled_ex5_count"], 9)

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
            self.assertTrue(out_rot["log_rotations"][0]["rotated"])
            self.assertTrue(list(state.glob("naqex_watchdog.log.*.bak")))

    def test_activation_card_and_holdout_lock_invariants(self):
        # Holdout 2025+ lock remains strictly untouched
        self.assertEqual(len(assert_holdout_locked()), 64)

        card = (KIT_DIR / "ACTIVATION-CARD-LOCAL-MT5.md").read_text(encoding="utf-8")
        for pname in EXPECTED_PROFILES:
            self.assertIn(pname, card, f"Activation card missing profile {pname}")
        # Ensure zero bare dollar-pair markdown math accidents in Vietnamese prose
        self.assertIsNone(re.search(r"\$\d+", card), "Use 'USD' instead of bare $ amounts in prose")


if __name__ == "__main__":
    unittest.main()
