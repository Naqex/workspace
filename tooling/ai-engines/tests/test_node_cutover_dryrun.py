"""Unit tests for fail-closed read-only `ops_cloud/node_cutover_dryrun.py` (`OrderSend = 0`)."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

AI_ENGINES = Path(__file__).resolve().parents[1]
OPS_CLOUD = AI_ENGINES / "ops_cloud"
EXPORTS_DIR = AI_ENGINES / "exports"
REPO_ROOT = AI_ENGINES.parents[1]

for p in (OPS_CLOUD, EXPORTS_DIR, AI_ENGINES):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import node_cutover_dryrun as cutover  # noqa: E402


def _make_clean_fixture(csv_sha16: str, *, date_str: str = "2026-11-25") -> dict:
    return {
        "now_utc": f"{date_str}T12:00:00Z",
        "status": {
            "checked_utc": f"{date_str}T12:00:00Z",
            "order_send_count": 0,
            "heartbeat": {
                "terminal_connected": True,
                "positions_state": "CONFIRMED",
                "open_positions": 0,
                "total_account_positions": 0,
                "pending_orders": 0,
                "orphan_no_sl": 0,
                "kill_switch": False,
                "regime": "NORMAL",
                "dry_run": False,
                "age_sec": 12,
            },
            "propguard_ok_count": 9,
            "propguard_warn_count": 0,
            "ntp_offset": "+0.021s",
            "system": {
                "wu_reboot": False,
                "cbs_reboot": False,
                "no_auto_update": 1,
                "auto_logon": "1",
            },
        },
        "integrity": {
            "checked_utc": f"{date_str}T12:00:00Z",
            "order_send_count": 0,
            "ok": True,
            "ex5_found_count": 10,
            "ex5_expected_matched": 10,
            "ex5_mismatches": [],
            "red_news_csv": {
                "exists": True,
                "rows": 492,
                "sha256": csv_sha16,
                "sha_match": True,
            },
            "common_ini": {"exists": True, "keep_private": "1", "has_login_override": False},
            "connector_ini": {"exists": True, "keep_private": "1", "has_login_override": False},
        },
        "maint": {
            "checked_utc": f"{date_str}T12:00:00Z",
            "order_send_count": 0,
            "ok": True,
            "wu_reboot_required": False,
            "cbs_reboot_pending": False,
            "au_policy": {"NoAutoUpdate": 1, "NoAutoReboot": 1},
            "auto_admin_logon": "1",
            "latest_daily_backup": date_str,
        },
        "audit": {
            "checked_utc": f"{date_str}T12:00:00Z",
            "order_send_count": 0,
            "total_audit_rows": 0,
            "events_by_type": {},
            "rejects_tail": [],
        },
    }


def _clean_local_kit(csv_sha16: str) -> dict:
    return {
        "preset_name": cutover.DEFAULT_PRESET,
        "preset_exists": True,
        "preset_fail_closed": True,
        "preset_sku": "FTMO_STD_10K_P1_SPRINT_4X",
        "kit_ok": True,
        "kit_errors": [],
        "local_ex5_verified_count": 10,
        "local_ex5_dir_present": True,
        "local_csv_rows": 492,
        "local_csv_sha16": csv_sha16,
    }


class NodeCutoverDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        csv_path = EXPORTS_DIR / "Files/naqex_red_news_utc.csv"
        self.csv_sha16 = cutover.sha256_file(csv_path).lower()[:16]
        self.now_dt = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)

    def test_clean_fixture_passes_all_10_gates_ready_for_cutover(self):
        fx = _make_clean_fixture(self.csv_sha16)
        local_kit = cutover.verify_local_kit_and_preset(cutover.DEFAULT_PRESET)
        # Allow CI without local .runtime compiled .ex5 to use mocked local_ex5 count while keeping real preset/kit check
        if not local_kit["local_ex5_dir_present"]:
            local_kit["local_ex5_verified_count"] = 10
        res = cutover.evaluate_cutover_readiness(
            status=fx["status"],
            integrity=fx["integrity"],
            maint=fx["maint"],
            audit=fx["audit"],
            local_kit=local_kit,
            now_utc=self.now_dt,
        )
        self.assertEqual(res["verdict"], "READY_FOR_CUTOVER", res["failed_gates"])
        self.assertEqual(res["gates_passed"], 10)
        self.assertEqual(res["gates_total"], 10)
        self.assertEqual(res["failed_gates"], [])
        self.assertEqual(res["order_send_count"], 0)
        self.assertFalse(cutover.ORDER_SEND_CAPABLE)

        txt = cutover.render_vietnamese_report(res)
        self.assertIn("READY_FOR_CUTOVER", txt)
        self.assertNotIn("$", txt)

    def test_blocks_on_open_position_or_orphan_or_disconnected(self):
        # 1. Open position > 0
        fx = _make_clean_fixture(self.csv_sha16)
        fx["status"]["heartbeat"]["open_positions"] = 1
        fx["status"]["heartbeat"]["total_account_positions"] = 1
        res = cutover.evaluate_cutover_readiness(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"],
            audit=fx["audit"], local_kit=_clean_local_kit(self.csv_sha16), now_utc=self.now_dt,
        )
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertIn("flat_positions_zero", res["failed_gates"])

        # 2. Orphan no-SL > 0
        fx2 = _make_clean_fixture(self.csv_sha16)
        fx2["status"]["heartbeat"]["orphan_no_sl"] = 1
        res2 = cutover.evaluate_cutover_readiness(
            status=fx2["status"], integrity=fx2["integrity"], maint=fx2["maint"],
            audit=fx2["audit"], local_kit=_clean_local_kit(self.csv_sha16), now_utc=self.now_dt,
        )
        self.assertEqual(res2["verdict"], "BLOCKED")
        self.assertIn("orphan_no_sl_zero", res2["failed_gates"])

        # 3. Disconnected / stale heartbeat
        fx3 = _make_clean_fixture(self.csv_sha16)
        fx3["status"]["heartbeat"]["terminal_connected"] = False
        fx3["status"]["heartbeat"]["age_sec"] = 400
        res3 = cutover.evaluate_cutover_readiness(
            status=fx3["status"], integrity=fx3["integrity"], maint=fx3["maint"],
            audit=fx3["audit"], local_kit=_clean_local_kit(self.csv_sha16), now_utc=self.now_dt,
        )
        self.assertEqual(res3["verdict"], "BLOCKED")
        self.assertIn("terminal_connected_and_heartbeat_fresh", res3["failed_gates"])

    def test_blocks_on_keep_private_autologon_and_pending_reboot(self):
        fx = _make_clean_fixture(self.csv_sha16)
        fx["integrity"]["common_ini"]["keep_private"] = "0"
        fx["maint"]["auto_admin_logon"] = "0"
        fx["maint"]["wu_reboot_required"] = True
        res = cutover.evaluate_cutover_readiness(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"],
            audit=fx["audit"], local_kit=_clean_local_kit(self.csv_sha16), now_utc=self.now_dt,
        )
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertIn("keep_private_and_ini_clean", res["failed_gates"])
        self.assertIn("windows_24x5_autologon_and_no_reboot", res["failed_gates"])

    def test_blocks_on_ex5_sha_mismatch_csv_mismatch_stale_backup_missing_preset_and_fill_unresolved(self):
        fx = _make_clean_fixture(self.csv_sha16)
        fx["integrity"]["ex5_found_count"] = 9
        fx["integrity"]["ex5_expected_matched"] = 9
        fx["integrity"]["ex5_mismatches"] = [{"file": "Naqex_Master_Prop7E.ex5", "expected": "aaaa", "actual": "MISSING"}]
        fx["integrity"]["red_news_csv"]["sha256"] = "0000000000000000"
        fx["maint"]["latest_daily_backup"] = "2026-11-10"
        fx["audit"]["events_by_type"] = {"FILL_UNRESOLVED": 1}

        bad_kit = _clean_local_kit(self.csv_sha16)
        bad_kit["preset_exists"] = False

        res = cutover.evaluate_cutover_readiness(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"],
            audit=fx["audit"], local_kit=bad_kit, now_utc=self.now_dt,
        )
        self.assertEqual(res["verdict"], "BLOCKED")
        for expected_gate in (
            "ex5_sha256_10_of_10_match",
            "red_news_492_csv_sha_match",
            "target_preset_and_kit_schema_valid",
            "daily_backup_fresh",
            "exec_audit_and_propguard_clean",
        ):
            self.assertIn(expected_gate, res["failed_gates"])

    def test_opsec_sanitization_strips_ips_urls_passwords_ssh_host_and_bare_dollar(self):
        fx = _make_clean_fixture(self.csv_sha16)
        fx["status"]["_ssh_host"] = "naqex-node1-ts"
        fx["status"]["ntp_offset"] = "+0.01s from 192.168.1.44 & 100.88.77.66 password=TopSecret webhook=https://hooks.example.com/x $100"
        res = cutover.evaluate_cutover_readiness(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"],
            audit=fx["audit"], local_kit=_clean_local_kit(self.csv_sha16), now_utc=self.now_dt,
        )
        dumped = json.dumps(res)
        report = cutover.render_vietnamese_report(res)
        for blob in (dumped, report):
            self.assertNotIn("192.168.1.44", blob)
            self.assertNotIn("100.88.77.66", blob)
            self.assertNotIn("TopSecret", blob)
            self.assertNotIn("hooks.example.com", blob)
            self.assertNotIn("_ssh_host", blob)
            self.assertNotIn("$", blob)
            self.assertIsNone(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", blob))

    def test_cli_offline_fixture_returns_exit_0_ready_and_exit_2_blocked(self):
        script = str(OPS_CLOUD / "node_cutover_dryrun.py")
        with tempfile.TemporaryDirectory() as td:
            ok_path = Path(td) / "ready.json"
            blk_path = Path(td) / "blocked.json"

            fx_ok = _make_clean_fixture(self.csv_sha16)
            ok_path.write_text(json.dumps(fx_ok), encoding="utf-8")

            fx_blk = _make_clean_fixture(self.csv_sha16)
            fx_blk["status"]["heartbeat"]["open_positions"] = 2
            blk_path.write_text(json.dumps(fx_blk), encoding="utf-8")

            has_ex5 = cutover.DEFAULT_EX5_DIR.is_dir() and len(list(cutover.DEFAULT_EX5_DIR.glob("*.ex5"))) >= 10
            if has_ex5:
                p_ok = subprocess.run(
                    [sys.executable, script, "--offline-fixture", str(ok_path), "--preset", cutover.DEFAULT_PRESET, "--json"],
                    capture_output=True, text=True, check=False, timeout=30,
                )
                self.assertEqual(p_ok.returncode, 0, p_ok.stdout + p_ok.stderr)
                js_ok = json.loads(p_ok.stdout)
                self.assertEqual(js_ok["verdict"], "READY_FOR_CUTOVER")

            p_blk = subprocess.run(
                [sys.executable, script, "--offline-fixture", str(blk_path), "--preset", cutover.DEFAULT_PRESET, "--json"],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_blk.returncode, 2, p_blk.stdout + p_blk.stderr)
            js_blk = json.loads(p_blk.stdout)
            self.assertEqual(js_blk["verdict"], "BLOCKED")
            self.assertIn("flat_positions_zero", js_blk["failed_gates"])


if __name__ == "__main__":
    unittest.main()
