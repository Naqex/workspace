"""Offline CI-safe unit tests for `tooling/automation/prop_terms_radar.py`.

Covers:
  - Hard read-only invariants (`ORDER_SEND_COUNT = 0`, `HOLDOUT_ROWS_ANALYSED = 0`,
    `SPEND_VND = 0`, `UNTRUSTED_EXTERNAL_DATA = True`) enforced under `python -O`
  - Strict trust-tier classification & spoofing resistance
  - Supply-chain URL guard blocking non-HTTPS, credentials, localhost, private IP,
    login, and checkout submission URLs
  - Dual Black Friday deadline tracking (`2026-11-30T16:00:00+07:00` bill lock &
    `2026-12-14T16:00:00+07:00` 14-day cutoff) across all timeline states
  - Cross-catalog SSOT parity (`firms_catalog.json` <-> `prop_pricing_catalog.json`)
    plus injected drift & staleness / future-timestamp detection
  - External rules & promo drift detection (IC Funded ±3m vs 600s, Section 12
    qualitative consistency, FTMO $20/$50 min payout, 14-day unpaid invoice
    NOT_DISCLOSED flag, T3 promo verification gating)
  - `--offline`, `--dry-run`, and mocked `--live` modes (anti-bot stop + timeout handling)
  - OPSEC scrubbing & LF-only atomic JSON persistence
"""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
RADAR_PATH = REPO_ROOT / "tooling" / "automation" / "prop_terms_radar.py"

_spec = importlib.util.spec_from_file_location("prop_terms_radar", RADAR_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Could not load prop_terms_radar from {RADAR_PATH}")
radar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(radar)


class PropTermsRadarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.firms_catalog = radar.load_json_file(
            radar.DEFAULT_FIRMS_CATALOG,
            expected_schema_key="schema_version",
            expected_schema="naqex-ssot-firms-catalog-v1",
        )
        cls.pricing_catalog = radar.load_json_file(
            radar.DEFAULT_PRICING_CATALOG,
            expected_schema_key="schema",
            expected_schema="naqex-prop-pricing-catalog-v1",
        )

    def test_hard_invariants_and_python_O_enforcement(self) -> None:
        self.assertEqual(radar.ORDER_SEND_COUNT, 0)
        self.assertEqual(radar.HOLDOUT_ROWS_ANALYSED, 0)
        self.assertEqual(radar.SPEND_VND, 0)
        self.assertTrue(radar.UNTRUSTED_EXTERNAL_DATA)
        radar.enforce_read_only_invariants()

        # Verify fail-closed checks do NOT depend on Python `assert` (stripped under -O).
        source_text = RADAR_PATH.read_text(encoding="utf-8")
        for line_no, line in enumerate(source_text.splitlines(), start=1):
            stripped = line.lstrip()
            self.assertFalse(
                stripped.startswith("assert "),
                f"Bare assert found in prop_terms_radar.py:{line_no} (forbidden under python -O)",
            )

        with patch.object(radar, "ORDER_SEND_COUNT", 1):
            with self.assertRaises(RuntimeError):
                radar.enforce_read_only_invariants()

    def test_trust_tier_classification_and_spoof_resistance(self) -> None:
        self.assertEqual(radar.classify_trust_tier("https://ftmo.com/en/black-friday/"), "T1_PRIMARY_OFFICIAL")
        self.assertEqual(radar.classify_trust_tier("https://trader.ftmo.com/start-challenge"), "T1_PRIMARY_OFFICIAL")
        self.assertEqual(radar.classify_trust_tier("https://the5ers.com/high-stakes/"), "T1_PRIMARY_OFFICIAL")
        self.assertEqual(radar.classify_trust_tier("https://icfunded.com/terms-and-conditions/"), "T1_PRIMARY_OFFICIAL")
        self.assertEqual(radar.classify_trust_tier("https://www.fxstreet.com/news/test"), "T2_TECHNICAL_COMMUNITY")
        self.assertEqual(radar.classify_trust_tier("https://www.reddit.com/r/PropFirmTester/"), "T3_FORUM_EXPERIENCE")
        # Spoofed lookalike hostnames must NEVER be elevated to T1.
        self.assertEqual(radar.classify_trust_tier("https://ftmo.com.evil.example/promo"), "T3_GENERAL_WEB")
        self.assertEqual(radar.classify_trust_tier("https://fake-the5ers.com/promo"), "T3_GENERAL_WEB")

    def test_supply_chain_url_guard(self) -> None:
        self.assertEqual(
            radar.validate_public_read_only_url("https://ftmo.com/en/black-friday/"),
            "https://ftmo.com/en/black-friday/",
        )
        blocked_urls = (
            "http://ftmo.com/en/black-friday/",
            "https://user:pass@ftmo.com/en/",
            "https://localhost/admin",
            "https://foo.localhost/secret",
            "https://intranet/secret",
            "https://metadata.google.internal/computeMetadata/v1/",
            "https://host.localdomain/status",
            "https://2130706433/secret",
            "https://0x7f000001/secret",
            "https://0177.0.0.1/secret",
            "https://0x7f.0.0.1/secret",
            "https://127.0.0.1/status",
            "https://" + "192.168." + "1.1/status",
            "https://ftmo.com/login",
            "https://trader.ftmo.com/checkout/submit",
            "https://icfunded.com/order/create",
        )
        for bad in blocked_urls:
            with self.assertRaises(ValueError, msg=f"URL should be blocked: {bad}"):
                radar.validate_public_read_only_url(bad)

        # Redirect handler must block 3xx redirects to internal or /login targets.
        handler = radar._SafeReadOnlyRedirectHandler()
        orig_req = urllib.request.Request("https://ftmo.com/en/black-friday/", method="GET")
        for bad_target in (
            "https://localhost/admin",
            "https://metadata.google.internal/latest",
            "/login",
            "http://ftmo.com/en/",
        ):
            with self.assertRaises(ValueError, msg=f"Redirect should be blocked: {bad_target}"):
                handler.redirect_request(orig_req, None, 302, "Found", {}, bad_target)

    def test_dual_black_friday_deadline_tracking_across_phases(self) -> None:
        # Phase 1: 2026-11-27 07:00 UTC (14:00 ICT) -> UPCOMING + PRE_LOCK_WINDOW
        d1 = radar.evaluate_deadlines(now_utc=datetime(2026, 11, 27, 7, 0, tzinfo=UTC))
        self.assertEqual(d1["bf_bill_lock"]["timestamp_ict"], "2026-11-30T16:00:00+07:00")
        self.assertEqual(d1["bf_14day_payment_cutoff"]["timestamp_ict"], "2026-12-14T16:00:00+07:00")
        self.assertEqual(d1["bf_bill_lock"]["status"], "UPCOMING")
        self.assertEqual(d1["bf_14day_payment_cutoff"]["status"], "PRE_LOCK_WINDOW")
        self.assertAlmostEqual(d1["bf_14day_payment_cutoff"]["hold_span_days"], 14.0, places=2)
        self.assertEqual(
            d1["bf_14day_payment_cutoff"]["contractual_price_lock_status"],
            "NOT_DISCLOSED_REQUIRES_SUPPORT_CONFIRMATION",
        )
        self.assertEqual(d1["bf_bill_lock"]["spend_vnd_required"], 0)
        self.assertEqual(len(d1["intermediate_macro_gates"]), 4)
        self.assertTrue(all(g["status"] == "UPCOMING" for g in d1["intermediate_macro_gates"]))

        # Phase 2: 12 hours before 30/11 16:00 ICT (2026-11-29 21:00 UTC) -> URGENT_WINDOW
        d2 = radar.evaluate_deadlines(now_utc=datetime(2026, 11, 29, 21, 0, tzinfo=UTC))
        self.assertEqual(d2["bf_bill_lock"]["status"], "URGENT_WINDOW")
        self.assertEqual(d2["bf_14day_payment_cutoff"]["status"], "PRE_LOCK_WINDOW")

        # Phase 3: 2026-12-11 09:00 UTC (after NFP 04/12, Trial 08/12, CPI 10/12; before 14/12)
        d3 = radar.evaluate_deadlines(now_utc=datetime(2026, 12, 11, 9, 0, tzinfo=UTC))
        self.assertEqual(d3["bf_bill_lock"]["status"], "EXPIRED")
        self.assertEqual(d3["bf_14day_payment_cutoff"]["status"], "ACTIVE_HOLD_WINDOW")
        self.assertTrue(all(g["status"] == "PASSED" for g in d3["intermediate_macro_gates"]))

        # Phase 4: 6 hours before 14/12 16:00 ICT (2026-12-14 03:00 UTC) -> URGENT_PAYMENT_WINDOW
        d4 = radar.evaluate_deadlines(now_utc=datetime(2026, 12, 14, 3, 0, tzinfo=UTC))
        self.assertEqual(d4["bf_14day_payment_cutoff"]["status"], "URGENT_PAYMENT_WINDOW")

        # Phase 5: After 14/12 16:00 ICT -> both EXPIRED
        d5 = radar.evaluate_deadlines(now_utc=datetime(2026, 12, 15, 0, 0, tzinfo=UTC))
        self.assertEqual(d5["bf_bill_lock"]["status"], "EXPIRED")
        self.assertEqual(d5["bf_14day_payment_cutoff"]["status"], "EXPIRED")

        # Inverted deadlines must fail closed with ValueError (even under -O)
        with self.assertRaises(ValueError):
            radar.evaluate_deadlines(
                now_utc=datetime(2026, 11, 27, 7, 0, tzinfo=UTC),
                bill_lock_iso="2026-12-14T16:00:00+07:00",
                cutoff_14d_iso="2026-11-30T16:00:00+07:00",
            )

    def test_cross_catalog_ssot_parity_and_injected_drift(self) -> None:
        # Real repo catalogs must have 17 contracts and zero internal cross-catalog mismatches.
        self.assertEqual(len(self.firms_catalog["contracts"]), 17)
        clean_drifts = radar.check_cross_catalog_parity(self.firms_catalog, self.pricing_catalog)
        self.assertEqual(clean_drifts, [], f"Unexpected cross-catalog drifts: {clean_drifts}")

        # Inject a price & DD mismatch into a deep copy and verify detection.
        mutated_firms = deepcopy(self.firms_catalog)
        mutated_firms["contracts"]["ftmo_standard_10k"]["fee_promo_usd"] = 75.00
        mutated_firms["contracts"]["the5ers_hs_5k_classic"]["daily_loss_limit_frac"] = 0.04
        drifts = radar.check_cross_catalog_parity(mutated_firms, self.pricing_catalog)
        drift_ids = {d["drift_id"] for d in drifts}
        self.assertIn("CROSS_FTMO_STANDARD_10K_FEE_PROMO_USD", drift_ids)
        self.assertIn("CROSS_THE5ERS_HS_5K_CLASSIC_DD_DAILY_PCT", drift_ids)
        dd_drift = next(d for d in drifts if d["drift_id"] == "CROSS_THE5ERS_HS_5K_CLASSIC_DD_DAILY_PCT")
        self.assertEqual(dd_drift["severity"], "CRITICAL")

    def test_catalog_staleness_and_future_timestamp_guard(self) -> None:
        fresh_now = datetime(2026, 11, 27, 7, 0, tzinfo=UTC)
        self.assertEqual(radar.check_catalog_staleness(self.firms_catalog, self.pricing_catalog, fresh_now), [])

        stale_now = datetime(2026, 12, 10, 7, 0, tzinfo=UTC)
        stale_drifts = radar.check_catalog_staleness(self.firms_catalog, self.pricing_catalog, stale_now)
        self.assertEqual({d["drift_id"] for d in stale_drifts}, {"STALE_FIRMS_CATALOG", "STALE_PROP_PRICING_CATALOG"})

        past_now = datetime(2026, 11, 20, 7, 0, tzinfo=UTC)
        future_drifts = radar.check_catalog_staleness(self.firms_catalog, self.pricing_catalog, past_now)
        self.assertEqual(
            {d["drift_id"] for d in future_drifts},
            {"FUTURE_TS_FIRMS_CATALOG", "FUTURE_TS_PROP_PRICING_CATALOG"},
        )

    def test_external_drift_detection_on_default_snapshot_and_missing_tag_rejection(self) -> None:
        now = datetime(2026, 11, 27, 7, 0, tzinfo=UTC)
        res = radar.detect_external_drift(
            self.firms_catalog,
            self.pricing_catalog,
            radar.DEFAULT_OFFLINE_SNAPSHOT,
            now_utc=now,
        )
        self.assertEqual(res["overall_status"], "DRIFT_DETECTED_ACTION_REQUIRED")
        ids = {d["drift_id"] for d in res["drifts"]}
        self.assertIn("EXT_IC_FUNDED_2STEP_PRO_NEWS_WINDOW_SEC", ids)
        self.assertIn("EXT_IC_FUNDED_2STEP_PRO_QUALITATIVE_CONSISTENCY", ids)
        self.assertIn("EXT_FTMO_2STEP_STANDARD_MIN_PAYOUT_CHANNEL", ids)
        self.assertIn("EXT_FTMO_14D_INVOICE_LOCK_UNVERIFIED", ids)
        self.assertIn("EXT_THE5ERS_14D_INVOICE_LOCK_UNVERIFIED", ids)
        self.assertIn("EXT_IC_FUNDED_2STEP_PRO_10K_PROMO_USD", ids)
        self.assertIn("EXT_THE5ERS_HIGH_STAKES_CLASSIC_5K_PROMO_USD", ids)

        # Unverified T3 promo must require checkout verification and stay MEDIUM (never elevated to T1).
        ic_promo = next(d for d in res["drifts"] if d["drift_id"] == "EXT_IC_FUNDED_2STEP_PRO_10K_PROMO_USD")
        self.assertEqual(ic_promo["trust_tier"], "T3_GENERAL_WEB")
        self.assertEqual(ic_promo["severity"], "MEDIUM")
        self.assertTrue(ic_promo["requires_checkout_verification"])
        self.assertTrue(ic_promo["untrusted_external_data"])

        # Snapshot missing `untrusted_external_data: true` must fail closed under -O.
        bad_snapshot = deepcopy(radar.DEFAULT_OFFLINE_SNAPSHOT)
        bad_snapshot["untrusted_external_data"] = False
        with self.assertRaises(ValueError):
            radar.detect_external_drift(self.firms_catalog, self.pricing_catalog, bad_snapshot, now_utc=now)

        # Critical drift test: Vietnam eligibility flip triggers CRITICAL_DRIFT.
        crit_snapshot = deepcopy(radar.DEFAULT_OFFLINE_SNAPSHOT)
        crit_snapshot["firms"]["ftmo"]["vietnam_eligible"] = False
        crit_res = radar.detect_external_drift(self.firms_catalog, self.pricing_catalog, crit_snapshot, now_utc=now)
        self.assertEqual(crit_res["overall_status"], "CRITICAL_DRIFT")
        self.assertGreaterEqual(crit_res["severity_counts"]["CRITICAL"], 1)

        # Anti-spoofing test: self-declared T1 on spoofed domain MUST be capped down to T3_GENERAL_WEB.
        spoof_snapshot = deepcopy(radar.DEFAULT_OFFLINE_SNAPSHOT)
        spoof_snapshot["firms"]["ftmo"]["trust_tier"] = "T1_PRIMARY_OFFICIAL"
        spoof_snapshot["firms"]["ftmo"]["source_urls"] = [
            "https://ftmo.com/en/",
            "https://ftmo.com.evil.example/promo",
        ]
        spoof_snapshot["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"]["promo_usd"] = 50.0
        spoof_snapshot["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"]["promo_trust_tier"] = (
            "T1_PRIMARY_OFFICIAL"
        )
        spoof_res = radar.detect_external_drift(self.firms_catalog, self.pricing_catalog, spoof_snapshot, now_utc=now)
        self.assertEqual(spoof_res["firms"]["ftmo"]["trust_tier"], "T3_GENERAL_WEB")
        self.assertEqual(spoof_res["firms"]["ftmo"]["black_friday_trust_tier"], "T3_GENERAL_WEB")
        spoof_promo = next(d for d in spoof_res["drifts"] if d["drift_id"] == "EXT_FTMO_2STEP_STANDARD_10K_PROMO_USD")
        self.assertEqual(spoof_promo["trust_tier"], "T3_GENERAL_WEB")
        self.assertEqual(spoof_promo["severity"], "MEDIUM")
        self.assertTrue(spoof_promo["requires_checkout_verification"])

    def test_offline_dry_run_and_atomic_write(self) -> None:
        now = datetime(2026, 11, 27, 7, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "prop_terms_radar_latest.json"

            # 1. --dry-run writes nothing to disk
            dry_rep = radar.run_radar(mode="offline", dry_run=True, output_path=out_path, now_utc=now)
            self.assertFalse(out_path.exists())
            self.assertFalse(dry_rep["output_written"])
            self.assertEqual(dry_rep["mode"], "offline")
            self.assertEqual(dry_rep["live_probes"], [])
            self.assertEqual(dry_rep["order_send_count"], 0)
            self.assertTrue(dry_rep["untrusted_external_data"])

            # 2. --offline writes valid LF-only JSON atomically
            off_rep = radar.run_radar(mode="offline", dry_run=False, output_path=out_path, now_utc=now)
            self.assertTrue(out_path.is_file())
            self.assertTrue(off_rep["output_written"])
            raw_bytes = out_path.read_bytes()
            self.assertNotIn(b"\r\n", raw_bytes)
            loaded = json.loads(raw_bytes.decode("utf-8"))
            self.assertTrue(loaded["output_written"])
            self.assertEqual(loaded["schema"], radar.SCHEMA_VERSION)
            self.assertEqual(loaded["order_send_count"], 0)
            self.assertEqual(loaded["holdout_rows_analysed"], 0)
            self.assertEqual(loaded["spend_vnd"], 0)
            self.assertEqual(loaded["deadlines"]["bf_bill_lock"]["timestamp_ict"], "2026-11-30T16:00:00+07:00")
            self.assertEqual(
                loaded["deadlines"]["bf_14day_payment_cutoff"]["timestamp_ict"],
                "2026-12-14T16:00:00+07:00",
            )

    def test_mocked_live_mode_antibot_stop_and_timeout_handling(self) -> None:
        now = datetime(2026, 11, 27, 7, 0, tzinfo=UTC)

        def fake_fetch(url: str, timeout: float) -> tuple[int, str]:
            if "ftmo.com/en/black-friday" in url:
                return 200, "<html><body>Black Friday 30% off until November 30 10:00 CET</body></html>"
            if "ftmo.com/en/terms-and-conditions" in url:
                # HTTP 200 HTML where anti-bot marker appears ONLY in raw HTML attributes/script tags.
                return (
                    200,
                    '<html><body><div class="cf-turnstile"></div>'
                    '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
                    "<p>Terms page</p></body></html>",
                )
            if "the5ers.com/high-stakes" in url:
                return 403, "<html><title>Just a moment...</title><div>Verify you are human cf-chl-</div></html>"
            raise TimeoutError("TLS handshake timed out")

        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "live_latest.json"
            rep = radar.run_radar(
                mode="live",
                dry_run=False,
                output_path=out_path,
                now_utc=now,
                fetch_fn=fake_fetch,
            )
            self.assertEqual(rep["mode"], "live")
            self.assertEqual(len(rep["live_probes"]), len(radar.LIVE_PUBLIC_PROBE_TARGETS))
            by_url = {p["url"]: p for p in rep["live_probes"]}

            ftmo_bf = by_url["https://ftmo.com/en/black-friday/"]
            self.assertEqual(ftmo_bf["probe_status"], "OK_PUBLIC_TEXT")
            self.assertEqual(ftmo_bf["trust_tier"], "T1_PRIMARY_OFFICIAL")
            self.assertTrue(ftmo_bf["untrusted_external_data"])
            self.assertIn("30%", ftmo_bf["matched_keywords"])
            self.assertIn("10:00", ftmo_bf["matched_keywords"])

            ftmo_tc = by_url["https://ftmo.com/en/terms-and-conditions/"]
            self.assertEqual(ftmo_tc["probe_status"], "ANTI_BOT_BLOCKED_STOPPED")
            self.assertEqual(ftmo_tc["http_status"], 200)

            t5 = by_url["https://the5ers.com/high-stakes/"]
            self.assertEqual(t5["probe_status"], "ANTI_BOT_BLOCKED_STOPPED")
            self.assertEqual(t5["http_status"], 403)

            ic = by_url["https://icfunded.com/"]
            self.assertEqual(ic["probe_status"], "UNREACHABLE_OR_TIMEOUT")

        # Verify fetch_public_url cleanly captures urllib.error.HTTPError 403 -> ANTI_BOT_BLOCKED_STOPPED
        class _Fake403Opener:
            def open(self, req: urllib.request.Request, timeout: float = 10.0) -> object:
                fp = io.BytesIO(b"<html><title>Attention Required! | Cloudflare</title></html>")
                raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", Message(), fp)

        status_403, body_403 = radar.fetch_public_url(
            "https://ftmo.com/en/black-friday/",
            opener=_Fake403Opener(),  # type: ignore[arg-type]
        )
        self.assertEqual(status_403, 403)
        self.assertIn("Cloudflare", body_403)
        probes_403 = radar.probe_live_public_urls(
            targets=({"firm_id": "ftmo", "label": "FTMO", "url": "https://ftmo.com/en/black-friday/"},),
            fetch_fn=lambda u, t: radar.fetch_public_url(u, t, opener=_Fake403Opener()),  # type: ignore[arg-type]
            now_utc=now,
        )
        self.assertEqual(probes_403[0]["probe_status"], "ANTI_BOT_BLOCKED_STOPPED")
        self.assertEqual(probes_403[0]["http_status"], 403)

    def test_cli_offline_dry_run_and_opsec_scrubber(self) -> None:
        fake_path = "C:" + "\\Users\\" + "AliceDemo\\file.txt"
        fake_tok = "ghp_" + ("1234567890" * 3)
        fake_lan_url = "http://" + "192.168." + "1.28/health"
        fake_ts_url = "https://" + "100.72." + "70.18/api/status"
        rfc6598_doc = "CGNAT range " + "100.64." + "0.0/10"
        scrubbed = radar.sanitize_opsec_text(
            f"Error at {fake_path} token {fake_tok} lan={fake_lan_url} ts={fake_ts_url} {rfc6598_doc}"
        )
        self.assertNotIn("AliceDemo", scrubbed)
        self.assertNotIn("ghp_", scrubbed)
        self.assertNotIn("192.168." + "1.28", scrubbed)
        self.assertNotIn("100.72." + "70.18", scrubbed)
        self.assertIn("<USER_HOME>", scrubbed)
        self.assertIn("<REDACTED_SECRET>", scrubbed)
        self.assertIn("http://<REDACTED_IP>/health", scrubbed)
        self.assertIn("https://<REDACTED_IP>/api/status", scrubbed)
        self.assertIn("100.64." + "0.0/10", scrubbed)

        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "cli_out.json"
            with patch("sys.stdout", buf):
                rc = radar.main(
                    [
                        "--offline",
                        "--dry-run",
                        "--json",
                        "--now-utc",
                        "2026-11-27T07:00:00Z",
                        "--out",
                        str(out_path),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertFalse(out_path.exists())
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["schema"], radar.SCHEMA_VERSION)
            self.assertEqual(parsed["order_send_count"], 0)


if __name__ == "__main__":
    unittest.main()
