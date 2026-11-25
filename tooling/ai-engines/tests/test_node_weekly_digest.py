"""Unit tests for read-only 1-command Morning/Weekly Ops Digest (`ops_cloud/node_weekly_digest.py`)."""
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

for p in (OPS_CLOUD, EXPORTS_DIR, AI_ENGINES):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import node_cutover_dryrun as cutover  # noqa: E402
import node_weekly_digest as digest_mod  # noqa: E402


def _healthy_fixture(csv_sha16: str, day_iso: str = "2026-11-25") -> dict:
    return {
        "now_utc": f"{day_iso}T08:00:00Z",
        "status": {
            "order_send_count": 0,
            "heartbeat": {
                "terminal_connected": True,
                "positions_state": "CONFIRMED",
                "regime": "NORMAL",
                "dry_run": False,
                "age_sec": 8,
                "balance": 10000.0,
                "equity": 10042.5,
                "daily_dd_pct": 0.0,
                "static_dd_pct": 0.0,
                "open_positions": 0,
                "total_account_positions": 0,
                "pending_orders": 0,
                "orphan_no_sl": 0,
                "kill_switch": False,
            },
            "propguard_ok_count": 9,
            "propguard_warn_count": 0,
            "ntp_offset": "+0.014s",
            "disks": {"C": {"free_gb": 120.5}, "D": {"free_gb": 410.2}},
            "heroku_last": {"status": "OK"},
            "system": {"uptime_hr": 36.5, "free_ram_gb": 11.2, "wu_reboot": False, "cbs_reboot": False, "no_auto_update": 1, "auto_logon": "1"},
        },
        "integrity": {
            "ok": True,
            "ex5_found_count": 10,
            "ex5_expected_matched": 10,
            "ex5_mismatches": [],
            "red_news_csv": {"exists": True, "rows": 492, "sha256": csv_sha16, "sha_match": True},
            "common_ini": {"exists": True, "keep_private": "1", "has_login_override": False},
            "connector_ini": {"exists": True, "keep_private": "1", "has_login_override": False},
        },
        "maint": {
            "ok": True,
            "wu_reboot_required": False,
            "cbs_reboot_pending": False,
            "au_policy": {"NoAutoUpdate": 1, "NoAutoReboot": 1},
            "auto_admin_logon": "1",
            "latest_daily_backup": day_iso.replace("-", ""),
        },
        "audit": {
            "total_audit_rows": 12,
            "events_by_type": {"ORDER_FILL": 6},
            "latency_ms": {"median": 94.2},
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


class NodeWeeklyDigestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.csv_sha16 = cutover.sha256_file(EXPORTS_DIR / "Files/naqex_red_news_utc.csv").lower()[:16]
        self.now_dt = datetime(2026, 11, 25, 8, 0, 0, tzinfo=timezone.utc)

    def test_healthy_digest_compact_under_35_lines_and_plain_vietnamese(self):
        fx = _healthy_fixture(self.csv_sha16)
        with tempfile.TemporaryDirectory() as td:
            sb_path = Path(td) / "prop_challenge_scoreboard.json"
            sb_path.write_text(json.dumps({"verdict": "PASS_TO_PAID", "total_trades": 14, "net_pnl_usd": 128.4, "swap_zero_ok": True}), encoding="utf-8")
            sb = digest_mod.load_optional_scoreboard(sb_path)

        d = digest_mod.build_ops_digest(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"], audit=fx["audit"],
            local_kit=_clean_local_kit(self.csv_sha16), scoreboard=sb, now_utc=self.now_dt,
        )
        self.assertEqual(d["overall_status"], "HEALTHY")
        self.assertEqual(d["cutover_verdict"], "READY_FOR_CUTOVER")
        self.assertEqual(d["gates_passed"], 10)
        self.assertEqual(d["order_send_count"], 0)
        self.assertFalse(digest_mod.ORDER_SEND_CAPABLE)

        txt = digest_mod.render_morning_digest_vi(d)
        lines = txt.splitlines()
        self.assertLessEqual(len(lines), 35, f"Digest exceeded 35 lines ({len(lines)})")
        self.assertIn("KHOE MANH", txt)
        self.assertIn("PASS_TO_PAID", txt)
        self.assertNotIn("$", txt)

    def test_degraded_and_offline_fallback_with_absent_scoreboard(self):
        sb_absent = digest_mod.load_optional_scoreboard(Path("/nonexistent/scoreboard.json"))
        self.assertFalse(sb_absent["present"])
        self.assertEqual(sb_absent["status"], "ABSENT")

        # 1. Degraded node (disconnected + open position + reboot pending)
        fx = _healthy_fixture(self.csv_sha16)
        fx["status"]["heartbeat"]["terminal_connected"] = False
        fx["status"]["heartbeat"]["open_positions"] = 1
        fx["maint"]["wu_reboot_required"] = True
        d_deg = digest_mod.build_ops_digest(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"], audit=fx["audit"],
            local_kit=_clean_local_kit(self.csv_sha16), scoreboard=sb_absent, now_utc=self.now_dt,
        )
        self.assertEqual(d_deg["overall_status"], "DEGRADED")
        self.assertEqual(d_deg["cutover_verdict"], "BLOCKED")
        txt_deg = digest_mod.render_morning_digest_vi(d_deg)
        self.assertLessEqual(len(txt_deg.splitlines()), 35)
        self.assertIn("Cong chan", txt_deg)

        # 2. Offline SSH failure fallback
        d_off = digest_mod.build_ops_digest(
            status=None, integrity=None, maint=None, audit=None,
            local_kit=_clean_local_kit(self.csv_sha16), scoreboard=sb_absent,
            probe_error="SSH timeout to 100.64.10.22 https://deadman.example.com",
            now_utc=self.now_dt,
        )
        self.assertEqual(d_off["overall_status"], "OFFLINE")
        txt_off = digest_mod.render_morning_digest_vi(d_off)
        self.assertNotIn("100.64.10.22", txt_off)
        self.assertNotIn("deadman.example.com", txt_off)
        self.assertIn("OFFLINE", txt_off)

    def test_opsec_scrub_eliminates_ips_urls_tokens_passwords_and_bare_dollar(self):
        fx = _healthy_fixture(self.csv_sha16)
        fx["status"]["_ssh_host"] = "naqex-node1-ts"
        fx["status"]["ntp_offset"] = "+0.02s 192.168.10.5 100.77.88.99 token=abc123 password=MyPass https://api.telegram.org/bot123 $500"
        d = digest_mod.build_ops_digest(
            status=fx["status"], integrity=fx["integrity"], maint=fx["maint"], audit=fx["audit"],
            local_kit=_clean_local_kit(self.csv_sha16), scoreboard={"present": False, "status": "ABSENT"},
            now_utc=self.now_dt,
        )
        blob_json = json.dumps(d)
        blob_txt = digest_mod.render_morning_digest_vi(d)
        for blob in (blob_json, blob_txt):
            self.assertNotIn("192.168.10.5", blob)
            self.assertNotIn("100.77.88.99", blob)
            self.assertNotIn("abc123", blob)
            self.assertNotIn("MyPass", blob)
            self.assertNotIn("api.telegram.org", blob)
            self.assertNotIn("_ssh_host", blob)
            self.assertNotIn("$", blob)
            self.assertIsNone(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", blob))

    def test_cli_offline_fixture_text_and_json(self):
        script = str(OPS_CLOUD / "node_weekly_digest.py")
        with tempfile.TemporaryDirectory() as td:
            fx_path = Path(td) / "fx.json"
            fx_path.write_text(json.dumps(_healthy_fixture(self.csv_sha16)), encoding="utf-8")

            p_txt = subprocess.run(
                [sys.executable, script, "--offline-fixture", str(fx_path), "--scoreboard", str(Path(td) / "missing.json")],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_txt.returncode, 0, p_txt.stdout + p_txt.stderr)
            self.assertLessEqual(len(p_txt.stdout.strip().splitlines()), 35)
            self.assertNotIn("$", p_txt.stdout)

            p_js = subprocess.run(
                [sys.executable, script, "--offline-fixture", str(fx_path), "--scoreboard", str(Path(td) / "missing.json"), "--json"],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p_js.returncode, 0, p_js.stdout + p_js.stderr)
            payload = json.loads(p_js.stdout)
            self.assertEqual(payload["overall_status"], "HEALTHY")
            self.assertEqual(payload["order_send_count"], 0)


if __name__ == "__main__":
    unittest.main()
