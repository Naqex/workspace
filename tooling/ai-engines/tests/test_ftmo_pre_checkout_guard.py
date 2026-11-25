"""Unit tests for read-only FTMO Pre-Checkout CGNAT/Geo-IP & 14-Day Red-News Guard (`OrderSend = 0`)."""
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

import ftmo_pre_checkout_guard as guard  # noqa: E402
import node_cutover_dryrun as cutover  # noqa: E402


def _clean_fixture(csv_sha16: str, *, country: str = "VN", hops: list[str] | None = None) -> dict:
    return {
        "now_utc": "2026-11-25T12:00:00Z",
        "network": {
            "geo_lookup_ok": True,
            "country_code": country,
            "hop_ips": hops if hops is not None else ["192.168.1.1", "203.113.131.1", "1.1.1.1"],
            "non_tailscale_iface_ips": ["192.168.1.50"],
        },
        "status": {
            "order_send_count": 0,
            "heartbeat": {
                "terminal_connected": True,
                "positions_state": "CONFIRMED",
                "regime": "NORMAL",
                "dry_run": False,
                "age_sec": 7,
                "open_positions": 0,
                "total_account_positions": 0,
                "pending_orders": 0,
                "orphan_no_sl": 0,
                "kill_switch": False,
            },
            "propguard_ok_count": 9,
            "propguard_warn_count": 0,
            "system": {"wu_reboot": False, "cbs_reboot": False, "no_auto_update": 1, "auto_logon": "1"},
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
            "latest_daily_backup": "20261125",
        },
        "audit": {"total_audit_rows": 0, "events_by_type": {}, "rejects_tail": []},
    }


def _ready_cutover() -> dict:
    return {
        "verdict": "READY_FOR_CUTOVER",
        "gates_passed": 10,
        "gates_total": 10,
        "failed_gates": [],
        "target_preset": cutover.DEFAULT_PRESET,
    }


class FtmoPreCheckoutGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.csv_path = EXPORTS_DIR / "Files/naqex_red_news_utc.csv"
        self.csv_sha16 = cutover.sha256_file(self.csv_path).lower()[:16]
        self.now_dt = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)

    def test_clean_non_us_no_cgnat_passes_pre_checkout_ready_with_zero_ip_leak(self):
        net = guard.classify_network_signals(
            country_code="VN",
            geo_lookup_ok=True,
            hop_ips=["192.168.1.1", "203.113.131.5", "1.1.1.1"],
            non_tailscale_iface_ips=["192.168.1.50"],
            probe_source="unit_test",
        )
        news = guard.extract_upcoming_red_news(self.csv_path, now_utc=self.now_dt, horizon_days=14)
        res = guard.evaluate_pre_checkout(network=net, news=news, cutover_result=_ready_cutover(), now_utc=self.now_dt)

        self.assertEqual(res["verdict"], "PRE_CHECKOUT_READY")
        self.assertEqual(res["hard_blocks"], [])
        self.assertEqual(res["warnings"], [])
        self.assertEqual(res["order_send_count"], 0)
        self.assertFalse(guard.ORDER_SEND_CAPABLE)
        self.assertTrue(res["network"]["non_us_verified"])
        self.assertFalse(res["network"]["is_cgnat"])
        self.assertGreaterEqual(res["red_news"]["total_csv_rows"], 492)
        self.assertGreater(res["red_news"]["dec_2026_count"], 5)
        self.assertGreater(res["red_news"]["upcoming_count"], 0)

        # Strict IP redaction proof: ZERO IPv4/IPv6 patterns anywhere, while HH:MM:SS timestamps stay readable!
        dumped = json.dumps(res)
        txt = guard.render_pre_checkout_vi(res)
        for blob in (dumped, txt):
            self.assertNotIn("203.113.131.5", blob)
            self.assertNotIn("192.168.1.1", blob)
            self.assertNotIn("192.168.1.50", blob)
            self.assertNotIn("[REDACTED_IPV6]", blob)
            self.assertNotIn("$", blob)
            self.assertIsNone(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", blob), f"IPv4 leaked in output: {blob}")
        # Verify real IPv6 addresses ARE redacted while HH:MM:SS stays intact
        scrubbed_v6 = guard.strict_opsec_scrub("time=13:25:00 ipv6=2405:4800:1234:5678::1 ll=fe80::1a2b")
        self.assertIn("13:25:00", scrubbed_v6)
        self.assertNotIn("2405:4800", scrubbed_v6)
        self.assertNotIn("fe80::1a2b", scrubbed_v6)

    def test_us_ip_hard_blocks_fail_closed(self):
        net = guard.classify_network_signals(
            country_code="US",
            geo_lookup_ok=True,
            hop_ips=["192.168.1.1", "8.8.8.8"],
            probe_source="unit_test",
        )
        news = guard.extract_upcoming_red_news(self.csv_path, now_utc=self.now_dt, horizon_days=14)
        res = guard.evaluate_pre_checkout(network=net, news=news, cutover_result=_ready_cutover(), now_utc=self.now_dt)

        self.assertEqual(res["verdict"], "ACTION_REQUIRED")
        self.assertTrue(res["network"]["is_us_ip_blocked"])
        self.assertIn("US_IP_PROHIBITED_BY_FTMO", res["hard_blocks"])

    def test_cgnat_100_64_hop_triggers_action_required_warning_and_redacts_ip(self):
        net = guard.classify_network_signals(
            country_code="VN",
            geo_lookup_ok=True,
            hop_ips=["192.168.1.1", "100.64.25.10", "203.113.131.1"],
            probe_source="unit_test",
        )
        news = guard.extract_upcoming_red_news(self.csv_path, now_utc=self.now_dt, horizon_days=14)
        res = guard.evaluate_pre_checkout(network=net, news=news, cutover_result=_ready_cutover(), now_utc=self.now_dt)

        self.assertEqual(res["verdict"], "ACTION_REQUIRED")
        self.assertTrue(res["network"]["is_cgnat"])
        self.assertEqual(res["hard_blocks"], [])
        self.assertIn("CGNAT_DETECTED_REQUEST_PUBLIC_IPV4_BEFORE_FUNDED", res["warnings"])
        blob = json.dumps(res) + "\n" + guard.render_pre_checkout_vi(res)
        self.assertNotIn("100.64.25.10", blob)
        self.assertIsNone(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", blob))

    def test_14_day_red_news_extraction_dec_2026_schedule(self):
        # From Monday 30/11/2026 + 14 days -> covers 30/11..14/12 (NFP, CPI, ECB/FOMC!)
        nov30 = datetime(2026, 11, 30, 0, 0, 0, tzinfo=timezone.utc)
        rn = guard.extract_upcoming_red_news(self.csv_path, now_utc=nov30, horizon_days=14)
        self.assertTrue(rn["ok"])
        self.assertEqual(rn["total_csv_rows"], 492)
        self.assertGreaterEqual(rn["upcoming_count"], 3)
        self.assertGreaterEqual(rn["dec_2026_count"], 10)
        for ev in rn["events"]:
            self.assertIn("UTC", ev["utc_iso"])
            self.assertIn("ICT", ev["ict_iso"])
            self.assertIn("..", ev["pre_flatten_utc"])

    def test_cli_offline_fixture_exit_codes_0_ready_and_2_action_required(self):
        script = str(OPS_CLOUD / "ftmo_pre_checkout_guard.py")
        has_ex5 = cutover.DEFAULT_EX5_DIR.is_dir() and len(list(cutover.DEFAULT_EX5_DIR.glob("*.ex5"))) >= 10
        with tempfile.TemporaryDirectory() as td:
            ok_p = Path(td) / "ok.json"
            us_p = Path(td) / "us.json"
            ok_p.write_text(json.dumps(_clean_fixture(self.csv_sha16, country="VN")), encoding="utf-8")
            us_p.write_text(json.dumps(_clean_fixture(self.csv_sha16, country="US")), encoding="utf-8")

            if has_ex5:
                p0 = subprocess.run(
                    [sys.executable, script, "--offline-fixture", str(ok_p), "--json"],
                    capture_output=True, text=True, check=False, timeout=30,
                )
                self.assertEqual(p0.returncode, 0, p0.stdout + p0.stderr)
                self.assertIsNone(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", p0.stdout))
                self.assertEqual(json.loads(p0.stdout)["verdict"], "PRE_CHECKOUT_READY")

            p2 = subprocess.run(
                [sys.executable, script, "--offline-fixture", str(us_p), "--json"],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(p2.returncode, 2, p2.stdout + p2.stderr)
            self.assertIsNone(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", p2.stdout))
            self.assertIn("US_IP_PROHIBITED_BY_FTMO", json.loads(p2.stdout)["hard_blocks"])


if __name__ == "__main__":
    unittest.main()
