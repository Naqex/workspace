"""Unit tests for prop_pricing_catalog.json and prop_pricing_refresh.py.

Offline-safe (zero live HTTP calls; FX refresh tested with mocked urlopen).
Compatible with both `pytest -q` and `unittest`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

try:
    from quant_factory import prop_pricing_refresh as ppr  # noqa: E402
except ModuleNotFoundError:
    _mod_path = AI_ENGINES_DIR / "quant_factory" / "prop_pricing_refresh.py"
    _spec = importlib.util.spec_from_file_location("prop_pricing_refresh", _mod_path)
    assert _spec is not None and _spec.loader is not None
    ppr = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(ppr)

CATALOG_PATH = AI_ENGINES_DIR / "configs" / "prop_pricing_catalog.json"


class _FakeHttpResponse:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class PropPricingCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = ppr.load_catalog(CATALOG_PATH)

    def test_schema_and_read_only_invariants(self) -> None:
        self.assertEqual(ppr.ORDER_SEND_COUNT, 0)
        self.assertEqual(ppr.HOLDOUT_ROWS_ANALYSED, 0)
        self.assertEqual(self.catalog["schema"], "naqex-prop-pricing-catalog-v1")
        self.assertEqual(self.catalog["staleness_max_days"], 7)
        self.assertEqual(self.catalog["order_send_count"], 0)
        self.assertEqual(self.catalog["holdout_rows_analysed"], 0)

        fx = self.catalog["fx_rates"]
        self.assertGreater(fx["usd_vnd"], 20000.0)
        self.assertGreater(fx["eur_vnd"], fx["usd_vnd"])
        self.assertIn("source_url", fx)
        self.assertTrue(fx["source_url"].startswith("https://"))

        costs = self.catalog["vn_transaction_costs"]
        self.assertAlmostEqual(costs["card_fx_buy_fee_pct"], 2.5, places=4)
        for firm_id in ("ftmo", "the5ers", "ic_funded", "e8_markets"):
            self.assertIn(firm_id, costs["payout_rail_fee_pct_by_firm"])
            fee = costs["payout_rail_fee_pct_by_firm"][firm_id]
            self.assertGreaterEqual(fee, 1.0)
            self.assertLessEqual(fee, 3.5)

    def test_four_verified_firms_and_execution_evidence_tags(self) -> None:
        firms = self.catalog["firms"]
        self.assertEqual(set(firms.keys()), {"ftmo", "the5ers", "ic_funded", "e8_markets"})

        for firm_id, firm in firms.items():
            self.assertTrue(firm["vietnam_eligible"], f"{firm_id} must be Vietnam eligible")
            self.assertTrue(firm["mt5_supported"], f"{firm_id} must support MT5")
            self.assertTrue(firm["ea_policy"]["allowed"], f"{firm_id} must allow own EAs")
            self.assertGreater(len(firm["source_urls"]), 0)
            for u in firm["source_urls"]:
                self.assertTrue(u.startswith("https://"), f"Non-https URL for {firm_id}: {u}")
            ppr.parse_utc(firm["verified_utc"])

            if firm_id == "ftmo":
                self.assertEqual(firm["execution_evidence_tag"], "MEASURED_DEMO_EXECUTION")
                self.assertEqual(firm["pricing_source_tag"], "LIVE_VN_CHECKOUT_20261126")
            else:
                self.assertEqual(firm["execution_evidence_tag"], "TERMS_VERIFIED_EXECUTION_UNMEASURED")

            for prog_id, prog in firm["programs"].items():
                self.assertEqual(prog["execution_evidence_tag"], firm["execution_evidence_tag"])
                self.assertIn(prog["dd_type"], ppr.ALLOWED_DD_TYPES)
                for req_key in (
                    "fee_refund_pct",
                    "dd_daily_pct",
                    "dd_max_pct",
                    "dd_type",
                    "best_day_cap_pct",
                    "daily_profit_cap_pct",
                    "min_trading_days",
                    "min_profitable_days",
                    "news_rule",
                    "ea_policy",
                    "max_allocation_usd",
                    "min_payout_usd",
                    "profit_split_pct",
                    "source_urls",
                    "verified_utc",
                ):
                    self.assertIn(req_key, prog, f"Missing {req_key} in {firm_id}/{prog_id}")

    def test_exact_live_ftmo_vn_checkout_prices(self) -> None:
        ftmo_progs = self.catalog["firms"]["ftmo"]["programs"]

        expected_std = {
            "10K": (98.61, 68.70, 30.0),
            "25K": (277.01, 220.50, 20.0),
            "50K": (382.28, 305.83, 20.0),
            "100K": (598.35, 478.68, 20.0),
            "200K": (1196.70, 957.36, 20.0),
        }
        std_tiers = ftmo_progs["ftmo_2step_standard"]["tiers"]
        for k, (orig, promo, pct) in expected_std.items():
            self.assertTrue(std_tiers[k]["available_vn"])
            self.assertAlmostEqual(std_tiers[k]["orig_usd"], orig, places=2)
            self.assertAlmostEqual(std_tiers[k]["active_promo_usd"], promo, places=2)
            self.assertAlmostEqual(std_tiers[k]["active_promo_pct"], pct, places=2)

        swing_tiers = ftmo_progs["ftmo_2step_swing"]["tiers"]
        self.assertTrue(swing_tiers["10K"]["available_vn"])
        self.assertAlmostEqual(swing_tiers["10K"]["orig_usd"], 109.69, places=2)
        self.assertAlmostEqual(swing_tiers["10K"]["active_promo_usd"], 109.69, places=2)
        self.assertTrue(swing_tiers["25K"]["available_vn"])
        self.assertAlmostEqual(swing_tiers["25K"]["orig_usd"], 309.14, places=2)
        self.assertAlmostEqual(swing_tiers["25K"]["active_promo_usd"], 309.14, places=2)
        for blocked in ("50K", "100K", "200K"):
            self.assertFalse(swing_tiers[blocked]["available_vn"])
            self.assertIsNone(swing_tiers[blocked]["orig_usd"])
            self.assertIsNone(swing_tiers[blocked]["active_promo_usd"])
            self.assertIn("Không áp dụng", swing_tiers[blocked]["unavailable_reason_vn"])

        expected_1step = {
            "10K": (87.53, 60.94, 30.0),
            "25K": (220.50, 176.18, 20.0),
            "50K": (353.47, 282.56, 20.0),
            "100K": (552.89, 442.12, 20.0),
            "200K": (1106.95, 885.34, 20.0),
        }
        one_prog = ftmo_progs["ftmo_1step"]
        self.assertEqual(one_prog["dd_type"], "eod_trailing")
        self.assertAlmostEqual(one_prog["dd_daily_pct"], 3.0)
        self.assertAlmostEqual(one_prog["best_day_cap_pct"], 50.0)
        self.assertAlmostEqual(one_prog["fee_refund_pct"], 0.0)
        self.assertAlmostEqual(one_prog["profit_split_pct"], 90.0)
        for k, (orig, promo, pct) in expected_1step.items():
            t = one_prog["tiers"][k]
            self.assertAlmostEqual(t["orig_usd"], orig, places=2)
            self.assertAlmostEqual(t["active_promo_usd"], promo, places=2)
            self.assertAlmostEqual(t["active_promo_pct"], pct, places=2)

        expected_instant = {
            "5K": (187.25, 130.75, 30.0),
            "10K": (375.36, 300.29, 20.0),
            "25K": (829.66, 663.73, 20.0),
            "50K": (1660.98, 1328.57, 20.0),
            "100K": (3322.80, 2658.24, 20.0),
        }
        inst_prog = ftmo_progs["ftmo_instant"]
        self.assertEqual(inst_prog["dd_type"], "intraday_trailing")
        self.assertAlmostEqual(inst_prog["dd_daily_pct"], 3.0)
        self.assertAlmostEqual(inst_prog["best_day_cap_pct"], 30.0)
        self.assertAlmostEqual(inst_prog["fee_refund_pct"], 0.0)
        for k, (orig, promo, pct) in expected_instant.items():
            t = inst_prog["tiers"][k]
            self.assertAlmostEqual(t["orig_usd"], orig, places=2)
            self.assertAlmostEqual(t["active_promo_usd"], promo, places=2)
            self.assertAlmostEqual(t["active_promo_pct"], pct, places=2)

    def test_the5ers_ic_funded_and_e8_exact_terms_and_prices(self) -> None:
        # The5ers High Stakes Classic ($39/$78/$195/$279/$455) & New ($35/$69/$176/$249/$405)
        t5_progs = self.catalog["firms"]["the5ers"]["programs"]
        expected_t5_classic = {"5K": 39.0, "10K": 78.0, "25K": 195.0, "50K": 279.0, "100K": 455.0}
        expected_t5_new = {"5K": 35.0, "10K": 69.0, "25K": 176.0, "50K": 249.0, "100K": 405.0}
        for k, price in expected_t5_classic.items():
            self.assertAlmostEqual(t5_progs["the5ers_high_stakes_classic"]["tiers"][k]["orig_usd"], price, places=2)
        for k, price in expected_t5_new.items():
            self.assertAlmostEqual(t5_progs["the5ers_high_stakes_new"]["tiers"][k]["orig_usd"], price, places=2)
            self.assertAlmostEqual(t5_progs["the5ers_high_stakes_new"]["tiers"][k]["active_promo_usd"], price, places=2)

        # IC Funded 2-Step Pro ($74/$125/$249/$449/$689/$1275, 3rd-payout refund)
        ic_prog = self.catalog["firms"]["ic_funded"]["programs"]["ic_funded_2step_pro"]
        self.assertEqual(ic_prog["fee_refund_milestone"], "THIRD_PAYOUT")
        for k, price in {"5K": 74.0, "10K": 125.0, "25K": 249.0, "50K": 449.0, "100K": 689.0, "200K": 1275.0}.items():
            self.assertAlmostEqual(ic_prog["tiers"][k]["orig_usd"], price, places=2)

        # E8 Pro: 2.0% Daily Profit Cap + exact list orig_usd vs -15% CODE_E8_15PCT active_promo_usd (no double-discount!)
        e8_prog = self.catalog["firms"]["e8_markets"]["programs"]["e8_pro_1step_static"]
        self.assertAlmostEqual(e8_prog["daily_profit_cap_pct"], 2.0, places=2)
        self.assertAlmostEqual(e8_prog["dd_daily_pct"], 2.5, places=2)
        self.assertAlmostEqual(e8_prog["payout_buffer_retention_pct"], 50.0, places=2)
        expected_e8 = {
            "5K": (32.0, 28.0, 12.5),
            "10K": (68.0, 58.0, 14.71),
            "25K": (148.0, 126.0, 14.86),
            "50K": (228.0, 194.0, 14.91),
            "100K": (488.0, 415.0, 14.96),
            "200K": (998.0, 849.0, 14.93),
        }
        for k, (orig, promo, pct) in expected_e8.items():
            t = e8_prog["tiers"][k]
            self.assertAlmostEqual(t["orig_usd"], orig, places=2)
            self.assertAlmostEqual(t["active_promo_usd"], promo, places=2)
            self.assertAlmostEqual(t["active_promo_pct"], pct, places=2)
            self.assertEqual(t["promo_label"], "CODE_E8_15PCT")

    def test_rejected_candidates_and_seasonal_confidence_tags(self) -> None:
        rejected = {r["firm_id"]: r for r in self.catalog["rejected_candidates"]}
        self.assertEqual(rejected["fundednext"]["status"], "REJECTED")
        self.assertFalse(rejected["fundednext"]["vietnam_eligible"])
        self.assertEqual(rejected["fundingpips"]["status"], "REJECTED")
        self.assertFalse(rejected["fundingpips"]["vietnam_eligible"])
        self.assertEqual(rejected["alpha_capital_group"]["status"], "REJECTED")
        self.assertFalse(rejected["alpha_capital_group"]["mt5_ea_fully_automated_allowed"])

        cal = self.catalog["seasonal_sale_calendar"]
        self.assertGreaterEqual(len(cal), 4)
        tags_seen = {ev["confidence_tag"] for ev in cal}
        self.assertTrue(tags_seen.issubset(ppr.ALLOWED_SEASONAL_CONFIDENCE))
        self.assertIn("CONTRACTUAL", tags_seen)
        self.assertIn("HISTORICAL_PATTERN", tags_seen)

    def test_pricing_traps_detection(self) -> None:
        traps = ppr.detect_pricing_traps(self.catalog)
        trap_keys = {(t["trap_type"], t["program_id"], t["tier"]) for t in traps}

        # FTMO Standard 25K > 10K fee ratio trap AND 200K == 2x 100K zero-discount trap
        self.assertIn(("FEE_RATIO_INVERSION_TRAP", "ftmo_2step_standard", "25K"), trap_keys)
        self.assertIn(("ZERO_VOLUME_DISCOUNT_2X_TRAP", "ftmo_2step_standard", "200K"), trap_keys)

        # FTMO Swing 50K/100K/200K disabled in Vietnam + 25K > 10K trap
        for tier in ("50K", "100K", "200K"):
            self.assertIn(("VN_UNAVAILABLE_TIER", "ftmo_2step_swing", tier), trap_keys)
        self.assertIn(("FEE_RATIO_INVERSION_TRAP", "ftmo_2step_swing", "25K"), trap_keys)

        # E8 Pro 100K ($415, 0.415%) > 50K ($194, 0.388%) trap
        self.assertIn(("FEE_RATIO_INVERSION_TRAP", "e8_pro_1step_static", "100K"), trap_keys)
        self.assertIn(("ZERO_VOLUME_DISCOUNT_2X_TRAP", "e8_pro_1step_static", "100K"), trap_keys)

    def test_staleness_detection_fresh_vs_stale(self) -> None:
        updated_dt = ppr.parse_utc(self.catalog["updated_utc"])
        fresh = ppr.check_staleness(self.catalog, now_utc=updated_dt + timedelta(days=3))
        self.assertEqual(fresh["status"], "FRESH")
        self.assertFalse(fresh["is_stale"])

        stale = ppr.check_staleness(self.catalog, now_utc=updated_dt + timedelta(days=8))
        self.assertEqual(stale["status"], "STALE_NEEDS_REFRESH")
        self.assertTrue(stale["is_stale"])
        self.assertGreater(stale["age_days"], 7.0)

    def test_refresh_fx_updates_fx_without_touching_checkout_prices(self) -> None:
        fake_payload = {
            "result": "success",
            "time_last_update_utc": "Thu, 26 Nov 2026 00:02:31 +0000",
            "rates": {"VND": 26100.5, "EUR": 0.90},
        }
        now = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)
        refreshed = ppr.refresh_fx_in_catalog(
            self.catalog,
            urlopen_fn=lambda req, timeout=10.0: _FakeHttpResponse(fake_payload),
            now_utc=now,
        )
        self.assertAlmostEqual(refreshed["fx_rates"]["usd_vnd"], 26100.5, places=2)
        self.assertAlmostEqual(refreshed["fx_rates"]["eur_vnd"], round(26100.5 / 0.90, 2), places=2)
        self.assertEqual(refreshed["fx_rates"]["rate_status"], "LIVE_PUBLIC_API")
        # Firm prices must remain completely identical
        self.assertEqual(refreshed["firms"], self.catalog["firms"])

    def test_refresh_fx_offline_fallback(self) -> None:
        def _boom(req, timeout=10.0):
            raise OSError("network offline")

        with self.assertRaises(OSError):
            ppr.refresh_fx_in_catalog(self.catalog, urlopen_fn=_boom, allow_fallback=False)

        fb = ppr.refresh_fx_in_catalog(self.catalog, urlopen_fn=_boom, allow_fallback=True)
        self.assertEqual(fb["fx_rates"]["rate_status"], "FALLBACK_OFFLINE")
        self.assertAlmostEqual(fb["fx_rates"]["usd_vnd"], self.catalog["fx_rates"]["fallback_usd_vnd"])
        self.assertEqual(fb["firms"], self.catalog["firms"])

    def test_apply_override_and_validation(self) -> None:
        override = {
            "pricing_source_tag": "LIVE_VN_CHECKOUT_20261203",
            "verified_utc": "2026-12-03T08:00:00Z",
            "tier_updates": [
                {
                    "firm_id": "ftmo",
                    "program_id": "ftmo_2step_standard",
                    "tier": "10K",
                    "active_promo_usd": 98.61,
                    "active_promo_pct": 0.0,
                    "promo_label": "REGULAR_POST_BF",
                }
            ],
        }
        merged = ppr.apply_override(self.catalog, override)
        self.assertEqual(merged["updated_utc"], "2026-12-03T08:00:00Z")
        self.assertEqual(merged["firms"]["ftmo"]["pricing_source_tag"], "LIVE_VN_CHECKOUT_20261203")
        t10 = merged["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"]
        self.assertAlmostEqual(t10["active_promo_usd"], 98.61, places=2)
        self.assertAlmostEqual(t10["active_promo_pct"], 0.0, places=2)
        # Untouched tier preserved AND its verified_utc MUST NOT be bumped by single-tier override (Astra R11 Q3a)!
        t100 = merged["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["100K"]
        self.assertAlmostEqual(t100["active_promo_usd"], 478.68, places=2)
        self.assertEqual(t10["verified_utc"], "2026-12-03T08:00:00Z")
        orig_std_ts = self.catalog["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["100K"]["verified_utc"]
        for sib in ("25K", "50K", "100K", "200K"):
            self.assertEqual(
                merged["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"][sib]["verified_utc"],
                orig_std_ts,
                f"Single-tier refresh MUST NOT bump sibling tier {sib} verified_utc",
            )
        self.assertEqual(
            merged["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["verified_utc"],
            self.catalog["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["verified_utc"],
        )

        # Updating only 10K on 2026-12-05 MUST still flag untouched 25K-200K as stale!
        stale_after_single = ppr.check_staleness(
            merged,
            now_utc=datetime(2026, 12, 5, 12, 0, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(stale_after_single["is_stale"])
        self.assertGreaterEqual(len(stale_after_single["stale_tiers"]), 4)

        # NaN / Inf price override MUST raise ValueError
        for bad_num in (float("nan"), float("inf"), -10.0):
            with self.assertRaises(ValueError):
                ppr.apply_override(
                    self.catalog,
                    {
                        "tier_updates": [
                            {
                                "firm_id": "ftmo",
                                "program_id": "ftmo_2step_standard",
                                "tier": "10K",
                                "active_promo_usd": bad_num,
                            }
                        ]
                    },
                )

        # Invalid promo > orig must raise
        bad_override = {
            "tier_updates": [
                {
                    "firm_id": "ftmo",
                    "program_id": "ftmo_2step_standard",
                    "tier": "10K",
                    "active_promo_usd": 150.0,
                }
            ]
        }
        with self.assertRaises(ValueError):
            ppr.apply_override(self.catalog, bad_override)

    def test_all_42_tiers_have_verified_utc_and_future_date_flagged(self) -> None:
        tier_count = 0
        for fid, firm in self.catalog["firms"].items():
            for pid, prog in firm["programs"].items():
                for tk, tier in prog["tiers"].items():
                    tier_count += 1
                    self.assertIn("verified_utc", tier, f"Missing verified_utc on {fid}/{pid}/{tk}")
                    ppr.parse_utc(tier["verified_utc"])
        self.assertEqual(tier_count, 42)

        # Year-2099 future timestamp MUST fail staleness check!
        fut_cat = json.loads(json.dumps(self.catalog))
        fut_cat["firms"]["ftmo"]["programs"]["ftmo_2step_standard"]["tiers"]["10K"]["verified_utc"] = "2099-01-01T00:00:00Z"
        chk_fut = ppr.check_staleness(
            fut_cat,
            now_utc=ppr.parse_utc(self.catalog["updated_utc"]) + timedelta(hours=2),
        )
        self.assertTrue(chk_fut["is_stale"])
        self.assertTrue(chk_fut["has_future_timestamps"])
        self.assertEqual(chk_fut["status"], "INVALID_FUTURE_TIMESTAMP")

    def test_cli_summary_and_override_roundtrip(self) -> None:
        summary_text = ppr.format_summary(
            self.catalog,
            now_utc=ppr.parse_utc(self.catalog["updated_utc"]) + timedelta(hours=2),
        )
        self.assertIn("FRESH", summary_text)
        self.assertIn("FTMO", summary_text)
        self.assertIn("The5ers", summary_text)
        self.assertIn("IC Funded", summary_text)
        self.assertIn("E8 Markets", summary_text)
        self.assertIn("MEASURED_DEMO", summary_text)
        self.assertIn("UNMEASURED_EXEC", summary_text)
        self.assertIn("FEE_RATIO_INVERSION_TRAP", summary_text)
        self.assertIn("ZERO_VOLUME_DISCOUNT_2X_TRAP", summary_text)
        self.assertIn("DISABLED_VN", summary_text)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cat = Path(tmpdir) / "catalog.json"
            tmp_ov = Path(tmpdir) / "override.json"
            ppr.save_catalog(self.catalog, tmp_cat)
            tmp_ov.write_text(
                json.dumps({
                    "verified_utc": ppr.format_utc(datetime.now(timezone.utc)),
                    "tier_updates": [
                        {
                            "firm_id": "e8_markets",
                            "program_id": "e8_pro_1step_static",
                            "tier": "50K",
                            "active_promo_usd": 182.40,
                            "active_promo_pct": 20.0,
                            "promo_label": "BF_20PCT_OFF_LIST_228",
                        }
                    ],
                }),
                encoding="utf-8",
            )
            buf = io.StringIO()
            old_stdout = sys.stdout
            try:
                sys.stdout = buf
                rc = ppr.main([
                    "--catalog", str(tmp_cat),
                    "--apply-override", str(tmp_ov),
                    "--summary",
                    "--check-staleness",
                ])
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("182.40", out)
            self.assertIn('"status": "FRESH"', out)


if __name__ == "__main__":
    unittest.main()
