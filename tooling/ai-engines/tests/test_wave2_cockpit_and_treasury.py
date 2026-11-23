"""Deterministic tests for Wave 2 Cycle 4 deliverables:
  - Treasury Ledger, 3-bucket reserve overflow, Prop->Own-Book crossover & GIPS-lite MD/HTML generator
  - IBKR Macro ETF Dry-Run Rebalancer (`OrderSend = 0`, exact parity with `macro_etf_trend.py`)
  - Local Web Control Room HTTP server (`127.0.0.1`, live endpoints, path-traversal guard, clean shutdown)
  - The5ers Launch Kit & Quarterly Governance Playbook integrity (YAML, 0 bare `$`, 0 broken links)
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re
import sys
import threading
import urllib.error
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))
if str(ROOT / "tooling/knowledge") not in sys.path:
    sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli
from cockpit import server as cockpit_server
from quant_factory import ibkr_macro_rebalancer, macro_etf_trend, treasury_ledger


# ---------------------------------------------------------------------------
# 1. Treasury Ledger, 3-Bucket Reserve, Crossover & GIPS-Lite Fact Sheet
# ---------------------------------------------------------------------------

def test_treasury_ledger_3bucket_overflow_refunds_and_gips(tmp_path: Path):
    assert treasury_ledger.ORDER_SEND_COUNT == 0
    ledger = treasury_ledger.TreasuryLedger(
        pod_name="Naqex Test Pod",
        usd_vnd_rate=25_500.0,
        policy=treasury_ledger.BucketPolicy(
            reserve_pct=0.30,
            own_book_pct=0.50,
            ops_tax_pct=0.20,
            reserve_cap_tickets=5.0,
            reference_ticket_usd=168.0,
        ),
    )
    ledger.add_account(treasury_ledger.PropAccountRecord(
        account_id="FTMO-10K-1", firm="FTMO", phase="FUNDED",
        nominal_usd=10_000.0, ticket_fee_usd=168.0, split_pct=0.80,
    ))
    ledger.add_account(treasury_ledger.PropAccountRecord(
        account_id="T5-5K-1", firm="The5ers", phase="FUNDED",
        nominal_usd=5_000.0, ticket_fee_usd=39.0, split_pct=0.80,
    ))

    # Challenge fees -> cash refund + hub credit -> 2 payouts (2nd payout hits 5x reserve cap = 840 USD!)
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-01-05", "CHALLENGE_FEE", 168.0, "FTMO-10K-1", "FTMO"))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-01-06", "CHALLENGE_FEE", 39.0, "T5-5K-1", "The5ers"))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-03-01", "FEE_REFUND", 168.0, "FTMO-10K-1", "FTMO", is_hub_credit=False))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-03-02", "FEE_REFUND", 11.7, "T5-5K-1", "The5ers", is_hub_credit=True))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-03-15", "PROP_PAYOUT", 1_000.0, "FTMO-10K-1", "FTMO", split_pct=0.80))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-04-15", "PROP_PAYOUT", 3_000.0, "FTMO-10K-1", "FTMO", split_pct=0.90))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-04-20", "OPS_EXPENSE", 40.0, "", "VPS"))
    ledger.add_event(treasury_ledger.TreasuryEvent("2026-04-30", "OWN_BOOK_PNL", 120.0, "", "OWN_BOOK"))

    # Roundtrip persistence check
    saved = tmp_path / "ledger.json"
    ledger.save(saved)
    reloaded = treasury_ledger.TreasuryLedger.load(saved)
    summ = reloaded.compute_summary()

    prop = summ["prop_accounting"]
    bkt = summ["buckets"]
    own = summ["own_book"]

    assert prop["active_prop_nominal_usd"] == 15_000.0
    assert prop["total_fees_paid_usd"] == 207.0
    assert prop["total_cash_refunds_usd"] == 168.0
    assert prop["total_hub_credits_usd"] == 11.7
    # Net payouts: 1000*0.80 + 3000*0.90 = 800 + 2700 = 3500 USD
    assert prop["total_net_payouts_usd"] == 3_500.0
    # Reserve cap = 5 * 168 = 840 USD -> capped cleanly and overflow spilled into own book!
    assert bkt["challenge_reserve_cap_usd"] == 840.0
    assert bkt["challenge_reserve_usd"] == 840.0
    assert bkt["reserve_fill_pct"] == 100.0
    # Payout 1 (800): reserve had 168 -> +240 = 408; own +400; ops +160.
    # Payout 2 (2700): raw_res = 810, room = 840-408 = 432 -> overflow = 378 -> own += 1350 + 378 = 1728!
    assert bkt["own_book_seed_from_prop_usd"] == 2_128.0
    assert own["equity_usd"] == 2_248.0  # 2128 seed + 120 realized pnl
    assert bkt["ops_tax_provision_usd"] == 660.0  # 160 + 540 - 40 VPS
    assert summ["crossover"]["crossover_equity_usd"] > 0.0

    # GIPS-lite Monthly Fact Sheet MD & HTML
    monthly = {
        "2026-01": 0.018, "2026-02": -0.006, "2026-03": 0.024,
        "2026-04": 0.015, "2026-05": 0.009, "2026-06": -0.004,
    }
    md = treasury_ledger.generate_gips_factsheet_md(reloaded, monthly)
    html_doc = treasury_ledger.generate_gips_factsheet_html(reloaded, monthly)
    assert "GIPS-Lite Monthly Fact Sheet" in md
    assert "SIMULATED_DEV_SEALED_NOT_LIVE_GIPS" in md
    assert "$" not in md  # Zero bare `$` in Markdown prose!
    assert "<!DOCTYPE html>" in html_doc
    assert "Calendar Monthly Returns" in html_doc


def test_prop_own_crossover_dominance_threshold():
    xo_low = treasury_ledger.compute_prop_own_crossover(
        own_book_equity_usd=5_000.0, active_prop_nominal_usd=150_000.0,
    )
    assert xo_low["own_book_beats_prop"] is False
    assert xo_low["recommended_phase"] == "PHASE_2_MULTI_PROP_SCALING"

    xo_high = treasury_ledger.compute_prop_own_crossover(
        own_book_equity_usd=100_000.0, active_prop_nominal_usd=150_000.0,
    )
    assert xo_high["own_book_beats_prop"] is True
    assert xo_high["recommended_phase"] == "PHASE_4_OWN_BOOK_DOMINANT"


# ---------------------------------------------------------------------------
# 2. IBKR Macro ETF Dry-Run Rebalancer (OrderSend = 0 & Parity)
# ---------------------------------------------------------------------------

def test_ibkr_macro_rebalancer_dryrun_and_exact_parity():
    assert ibkr_macro_rebalancer.ORDER_SEND_COUNT == 0
    assert ibkr_macro_rebalancer.DRY_RUN_ONLY is True

    # Test against real cached macro ETF panel if present, else build deterministic synthetic 300-day panel
    if (macro_etf_trend.MACRO_CACHE_DIR / "SPY.parquet").is_file():
        panel = macro_etf_trend.load_etf_panel()
    else:
        rng = np.random.default_rng(42)
        n_t = 300
        dates = [f"2025-{(i // 22) % 12 + 1:02d}-{(i % 22) + 1:02d}" for i in range(n_t)]
        syms = list(macro_etf_trend.ETF_UNIVERSE_12)
        px = 100.0 * np.cumprod(1.0 + rng.normal(0.0004, 0.01, size=(n_t, len(syms))), axis=0)
        panel = {"dates": dates, "symbols": syms, "adjclose": px}

    plan_m5 = ibkr_macro_rebalancer.generate_rebalance_plan(
        mode="M5_VOL_PARITY_TREND_GUARD", equity_usd=25_000.0, panel=panel,
    )
    assert plan_m5["order_send_count"] == 0
    assert plan_m5["dry_run_only"] is True
    assert plan_m5["allow_short"] is False
    assert 0.0 <= plan_m5["gross_exposure_pct"] <= 100.01
    assert all(a["target_weight_pct"] >= 0.0 for a in plan_m5["allocations"])

    # Exact parity check against macro_etf_trend.build_macro_strategies last row
    ref_w = macro_etf_trend.build_macro_strategies(panel)["M5_VOL_PARITY_TREND_GUARD"][2][-1]
    by_sym = {a["symbol"]: a["target_weight_pct"] for a in plan_m5["allocations"]}
    for j, sym in enumerate(panel["symbols"]):
        assert abs(by_sym[sym] - round(float(ref_w[j]) * 100.0, 2)) <= 0.01

    # Verify IBKR Basket CSV output schema & explicit DryRunOnly=TRUE guard
    csv_text = ibkr_macro_rebalancer.tickets_to_ibkr_csv(plan_m5)
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == plan_m5["ticket_count"]
    assert len(rows) > 0
    for r in rows:
        assert r["DryRunOnly"] == "TRUE"
        assert r["SecType"] == "STK"
        assert r["Currency"] == "USD"
        assert int(r["Quantity"]) > 0

    # Also check M1 Long/Short & Blend modes execute cleanly
    plan_m1 = ibkr_macro_rebalancer.generate_rebalance_plan(
        mode="M1_AHL_TSMOM_LS_VOL10", equity_usd=50_000.0, panel=panel,
    )
    plan_blend = ibkr_macro_rebalancer.generate_rebalance_plan(
        mode="BLEND_50_M5_50_M1", equity_usd=50_000.0, panel=panel,
    )
    assert plan_m1["gross_exposure_pct"] <= 150.05
    assert plan_blend["order_send_count"] == 0


# ---------------------------------------------------------------------------
# 3. Local Web Control Room HTTP Server Smoke & Security Tests
# ---------------------------------------------------------------------------

def test_cockpit_http_server_live_endpoints_and_clean_shutdown():
    assert cockpit_server.ORDER_SEND_COUNT == 0
    # Refuse non-localhost bind (fail-closed security boundary)
    try:
        cockpit_server.create_server(host="0.0.0.0", port=0)
        raise AssertionError("Server must refuse non-localhost binding")
    except ValueError:
        pass

    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=ROOT)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        # 1. Static HTML / CSS / JS
        for path, expected_snippet in (
            ("/", "Naqex Quant Pod Control Room"),
            ("/static/styles.css", "--bg: #0b0f17"),
            ("/static/app.js", "/api/vnd-calculator"),
        ):
            with urllib.request.urlopen(f"{base}{path}", timeout=10) as resp:
                assert resp.status == 200
                body = resp.read().decode("utf-8")
                assert expected_snippet in body

        # 2. Live JSON API endpoints
        for ep, required_keys in (
            ("/api/health", {"ok", "order_send_count"}),
            ("/api/summary", {"schema", "safety_seal", "registry", "pod_snapshot", "red_team_stress"}),
            ("/api/allocations", {"schema", "available", "sleeve_order", "equity_curves", "underwater_dd_pct", "correlation_matrix"}),
            ("/api/live-telemetry", {"schema", "mt5_heartbeat", "mt5_live_spreads", "crypto_shadow", "upcoming_red_news"}),
            ("/api/vnd-calculator?capital_vnd=300000000&usd_vnd=25500&prop_nominal_usd=10000&risk_profile=balanced&cost_mult=1.5",
             {"schema", "absolute_pain_table", "owner_profile_assessment", "red_team_stress", "crossover", "own_book_sleeve_allocation"}),
            ("/api/rebalancer?mode=M5_VOL_PARITY_TREND_GUARD&equity_usd=25000", {"schema", "order_send_count", "dry_run_only"}),
        ):
            with urllib.request.urlopen(f"{base}{ep}", timeout=15) as resp:
                assert resp.status == 200
                payload = json.loads(resp.read().decode("utf-8"))
                assert required_keys.issubset(payload.keys()), f"Missing keys in {ep}: {required_keys - set(payload.keys())}"
                assert payload.get("order_send_count", 0) == 0

        # 3. Verify POST /api/vnd-calculator
        req = urllib.request.Request(
            f"{base}/api/vnd-calculator",
            data=json.dumps({"capital_vnd": 1_200_000_000, "risk_profile": "p1_sprint", "cost_mult": 2.0}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            post_res = json.loads(resp.read().decode("utf-8"))
            # Very large capital >= 1B VND with high DD -> OVER_TOLERANCE_RED per PROFILE.md
            assert post_res["owner_profile_assessment"]["verdict"] == "OVER_TOLERANCE_RED"
            assert post_res["red_team_stress"]["PORT_7E"]["breakeven_mult"] > 2.0

        # 4. Path-traversal guard on /static/
        try:
            urllib.request.urlopen(f"{base}/static/../../server.py", timeout=5)
            raise AssertionError("Path traversal must be rejected")
        except urllib.error.HTTPError as exc:
            assert exc.code in (403, 404)
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


# ---------------------------------------------------------------------------
# 4. Docs Integrity: The5ers Launch Kit, Quarterly Governance & Knowledge Vault
# ---------------------------------------------------------------------------

def test_wave2_docs_frontmatter_links_and_zero_bare_dollar():
    the5ers_doc = ROOT / "tooling/ai-engines/exports/deployment_kit/the5ers_kit/THE5ERS-LAUNCH-AND-TERMS11-EMAIL.md"
    gov_doc = ROOT / "knowledge/topics/quarterly-quant-governance-playbook.md"
    launcher_ps1 = ROOT / "tooling/ai-engines/cockpit/launch_cockpit.ps1"

    assert the5ers_doc.is_file()
    assert gov_doc.is_file()
    assert launcher_ps1.is_file()

    # Check zero bare `$` in prose of both Markdown files
    for doc in (the5ers_doc, gov_doc):
        txt = doc.read_text(encoding="utf-8")
        assert txt.startswith("---\n"), f"Missing YAML frontmatter in {doc.name}"
        for line_no, line in brain_cli._iter_non_code_lines(txt):
            cleaned = brain_cli.INLINE_CODE_RE.sub("", line)
            assert "$" not in cleaned, f"Bare '$' in prose {doc.name}:{line_no}: {line}"
            # Also verify every relative link resolves cleanly
            for m in brain_cli.MD_LINK_RE.finditer(cleaned):
                raw_t = brain_cli._clean_link_target(m.group(1))
                if not raw_t or raw_t.startswith("#") or raw_t.lower().startswith(("http://", "https://", "mailto:")):
                    continue
                rel_p = raw_t.split("#", 1)[0].split("?", 1)[0]
                if rel_p:
                    assert (doc.parent / rel_p).resolve().exists(), f"Broken link in {doc.name}:{line_no} -> {raw_t}"

    # Verify Terms §11 email template & exact MQL5 PropGuard contract inputs exist in The5ers doc
    t5_txt = the5ers_doc.read_text(encoding="utf-8")
    assert "Terms §11" in t5_txt or "Section 11" in t5_txt
    assert "±5" in t5_txt and "±2" in t5_txt
    assert "0,5%" in t5_txt or "0.5%" in t5_txt
    assert "naqex_red_news_utc.csv" in t5_txt
    assert "InpGuardEnableRedNews = true" in t5_txt
    assert "InpGuardNewsPadSec = 300" in t5_txt

    # Verify full knowledge vault remains 0 broken links & 0 near-duplicate headings
    assert brain_cli.find_broken_knowledge_links(ROOT) == []
    assert brain_cli.find_near_duplicate_topic_headings(ROOT) == []
