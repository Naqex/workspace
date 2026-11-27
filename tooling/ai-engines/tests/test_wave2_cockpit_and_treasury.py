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
import pytest

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

@pytest.mark.local_cache
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

        # 2. Live JSON API endpoints (including upgraded /api/overview, /api/live-telemetry & /api/stress)
        for ep, required_keys in (
            ("/api/health", {"ok", "order_send_count"}),
            ("/api/summary", {"schema", "safety_seal", "registry", "pod_snapshot", "red_team_stress"}),
            ("/api/overview?capital_usd=50000&usd_vnd=25500", {"schema", "summary", "live_telemetry", "stress"}),
            ("/api/allocations", {"schema", "available", "sleeve_order", "equity_curves", "underwater_dd_pct", "correlation_matrix"}),
            ("/api/live-telemetry", {"schema", "mt5_heartbeat", "mt5_live_spreads", "crypto_shadow", "crypto_maker_shadow", "mt5_realtick_tca", "upcoming_red_news"}),
            ("/api/stress?capital_usd=50000&usd_vnd=25500", {"schema", "status", "available", "capital_usd", "black_swan_matrix", "multi_prop_highlights", "cex_group_cap_recommendation"}),
            ("/api/vnd-calculator?capital_vnd=300000000&usd_vnd=25500&prop_nominal_usd=10000&risk_profile=balanced&cost_mult=1.5",
             {"schema", "absolute_pain_table", "owner_profile_assessment", "red_team_stress", "crossover", "own_book_sleeve_allocation"}),
            ("/api/rebalancer?mode=M5_VOL_PARITY_TREND_GUARD&equity_usd=25000", {"schema", "order_send_count", "dry_run_only"}),
        ):
            with urllib.request.urlopen(f"{base}{ep}", timeout=15) as resp:
                assert resp.status == 200
                payload = json.loads(resp.read().decode("utf-8"))
                assert required_keys.issubset(payload.keys()), f"Missing keys in {ep}: {required_keys - set(payload.keys())}"
                assert payload.get("order_send_count", 0) == 0

        # 2b. Verify live stress scaling proportionality (200k == 4x of 50k) & real parsed figures
        with urllib.request.urlopen(f"{base}/api/stress?capital_usd=50000&usd_vnd=25500", timeout=10) as r50:
            st50 = json.loads(r50.read().decode("utf-8"))
        with urllib.request.urlopen(f"{base}/api/stress?capital_usd=200000&usd_vnd=25500", timeout=10) as r200:
            st200 = json.loads(r200.read().decode("utf-8"))
        assert st50["available"] is True and st50["status"] == "AVAILABLE"
        nco50 = next(x for x in st50["black_swan_matrix"] if x["allocator"] == "NCO_Capped35")
        nco200 = next(x for x in st200["black_swan_matrix"] if x["allocator"] == "NCO_Capped35")
        hrp50 = next(x for x in st50["black_swan_matrix"] if x["allocator"] == "HRP")
        assert abs(nco200["cex_50"]["usd"] - 4.0 * nco50["cex_50"]["usd"]) <= 1.0
        assert hrp50["cex_50"]["pct"] > nco50["cex_50"]["pct"] > 0.0
        assert len(st50["multi_prop_highlights"]) >= 6

        # 2c. Verify live-telemetry reads active Crypto Shadow L2 & Real-Tick summary when present
        with urllib.request.urlopen(f"{base}/api/live-telemetry", timeout=10) as rtel:
            tel = json.loads(rtel.read().decode("utf-8"))
        assert tel["schema"] == "naqex-cockpit-live-telemetry-v2"
        if (ROOT / ".runtime/live-overnight/crypto_shadow_latest.json").is_file():
            assert tel["crypto_shadow"]["status"] == "ACTIVE"
            assert "BTCUSDT" in tel["crypto_shadow"]["majors_l2"]
            assert tel["crypto_shadow"]["tca_summary"]["budget_10k_bps"] == 5.0
        if (ROOT / ".runtime/mt5-realtick-results/realtick_matrix_summary.json").is_file():
            assert tel["mt5_realtick_tca"]["status"] == "AVAILABLE"
            assert tel["mt5_realtick_tca"]["model"] == 4

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


def test_cockpit_graceful_missing_file_fallback_and_synthetic_live_pickup(tmp_path: Path):
    """Missing runtime telemetry / stress files must NEVER 500 — must return HTTP 200 with status='pending'."""
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=tmp_path)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        # Empty root: every endpoint returns 200 with clean pending degradation
        for ep in ("/api/overview", "/api/live-telemetry", "/api/stress?capital_usd=10000", "/api/allocations", "/api/summary", "/api/rebalancer"):
            with urllib.request.urlopen(f"{base}{ep}", timeout=10) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert data.get("order_send_count", 0) == 0

        with urllib.request.urlopen(f"{base}/api/live-telemetry", timeout=10) as resp:
            tel0 = json.loads(resp.read().decode("utf-8"))
        assert tel0["crypto_shadow"]["status"] == "pending"
        assert tel0["crypto_maker_shadow"]["status"] == "pending"
        assert tel0["mt5_live_spreads"]["status"] == "pending"
        assert tel0["mt5_realtick_tca"]["status"] == "pending"

        with urllib.request.urlopen(f"{base}/api/stress?capital_usd=10000", timeout=10) as resp:
            st0 = json.loads(resp.read().decode("utf-8"))
        assert st0["status"] == "pending" and st0["available"] is False

        # Drop synthetic maker shadow + MT5 spread tail -> verify instant ACTIVE pickup!
        live_dir = tmp_path / ".runtime/live-overnight"
        live_dir.mkdir(parents=True, exist_ok=True)
        (live_dir / "crypto_maker_shadow_latest.json").write_text(
            json.dumps({"cycle_num": 3, "fill_rate_pct": 78.5, "effective_cost_bps": 4.92, "timestamp_utc": "2026-11-24T01:25:00Z"}),
            encoding="utf-8",
        )
        (live_dir / "mt5_live_spread_log.jsonl").write_text(
            json.dumps({"login": 1515343166, "server": "FTMO-Demo", "balance": 10000.0, "equity": 10012.5, "usdjpy_spread_pts": 8}) + "\n",
            encoding="utf-8",
        )
        with urllib.request.urlopen(f"{base}/api/live-telemetry", timeout=10) as resp:
            tel1 = json.loads(resp.read().decode("utf-8"))
        assert tel1["crypto_maker_shadow"]["status"] == "ACTIVE"
        assert tel1["crypto_maker_shadow"]["cycle_num"] == 3
        assert tel1["mt5_live_spreads"]["status"] == "ACTIVE"
        assert tel1["mt5_live_spreads"]["demo_account"]["equity"] == 10012.5
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
    ledger_doc = ROOT / "knowledge/topics/alpha-hypothesis-ledger.md"
    launcher_ps1 = ROOT / "tooling/ai-engines/cockpit/launch_cockpit.ps1"

    assert the5ers_doc.is_file()
    assert gov_doc.is_file()
    assert ledger_doc.is_file()
    assert launcher_ps1.is_file()

    # Check zero bare `$` in prose & valid links across all Wave-2 docs + updated alpha ledger
    for doc in (the5ers_doc, gov_doc, ledger_doc):
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


def test_prop_metrix_buffers_rules_mae_mfe_and_calendar(tmp_path: Path):
    live_dir = tmp_path / ".runtime/live-overnight"
    live_dir.mkdir(parents=True, exist_ok=True)
    snaps = [
        {
            "captured_utc": "2026-11-24T05:25:00+00:00",
            "account": {"balance": 9999.82, "equity": 9998.72},
            "naqex_positions_count": 1,
            "orphan_no_sl": 0,
            "quotes": {"USDJPY": {"bid": 159.070, "ask": 159.073}},
            "naqex_positions": [{"ticket": 591010790, "symbol": "USDJPY", "type": "BUY", "volume": 0.07, "price_open": 159.095, "sl": 158.753, "profit": -1.10, "swap": 0.0}],
        },
        {
            "captured_utc": "2026-11-24T08:17:00+00:00",
            "account": {"balance": 9999.82, "equity": 10011.15},
            "naqex_positions_count": 1,
            "orphan_no_sl": 0,
            "quotes": {"USDJPY": {"bid": 159.403, "ask": 159.406}},
            "naqex_positions": [{"ticket": 591010790, "symbol": "USDJPY", "type": "BUY", "volume": 0.07, "price_open": 159.095, "sl": 158.753, "profit": 11.33, "swap": 0.0}],
        },
    ]
    (live_dir / "mt5_live_spread_log.jsonl").write_text(
        "\n".join(json.dumps(s) for s in snaps) + "\n", encoding="utf-8"
    )

    mx = cockpit_server.build_prop_metrix_payload(tmp_path, program="ftmo_free_trial_10k", allow_cloud_fetch=False)
    assert mx["order_send_count"] == 0
    assert abs(mx["buffers"]["permitted_daily_loss_usd"] - 511.15) < 0.25
    assert abs(mx["buffers"]["permitted_max_loss_usd"] - 1011.15) < 0.05
    mm = mx["positions_mae_mfe"]["591010790"]
    assert mm["mae_pips"] == -2.5
    assert mm["mfe_pips"] == 30.8
    rules_by_id = {r["id"]: r for r in mx["rules"]}
    assert rules_by_id["max_daily_loss"]["status"] == "PASS"
    assert rules_by_id["safety_guard"]["status"] == "PASS"
    assert any(c.get("has_trade") and c.get("day") == "2026-11-24" for c in mx["calendar"]["cells"])

    # Also verify HTTP endpoint + updated HTML panel markers
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=tmp_path)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/prop-metrix?program=the5ers_hs_5k_p1&offline=1", timeout=5) as r:
            body = json.loads(r.read().decode("utf-8"))
        assert body["program"]["id"] == "the5ers_hs_5k_p1"
        assert body["buffers"]["daily_limit_usd"] == 250.0
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
            html_txt = r.read().decode("utf-8")
        assert 'id="panel-prop-metrix"' in html_txt
        assert "MAE/MFE (pip)" in html_txt
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


def test_prop_metrix_tiers_the5ers_profitable_days_and_r4_r1_attribution(tmp_path: Path):
    """Verify Patch #4b: new FTMO/The5ers tiers, >= +0.5% profitable-day rule, and R4->R3->R2->R1 attribution."""
    for req_id in (
        "ftmo_free_trial_10k", "ftmo_swing_10k_p1", "ftmo_swing_25k_p1",
        "ftmo_swing_50k_p1", "ftmo_swing_100k_p1", "the5ers_hs_5k_p1", "the5ers_hs_20k_p1",
    ):
        assert req_id in cockpit_server.PROP_METRIX_PROGRAMS
    assert cockpit_server.PROP_METRIX_PROGRAMS["the5ers_hs_5k_p1"]["min_profitable_day_pct"] == 0.5
    assert cockpit_server.PROP_METRIX_PROGRAMS["the5ers_hs_20k_p1"]["min_profitable_day_pct"] == 0.5
    assert cockpit_server.PROP_METRIX_PROGRAMS["ftmo_swing_50k_p1"]["min_profitable_day_pct"] == 0.0

    # 1. The5ers 5K (+0.5% = +25 USD/day): 2 days >= +25 USD & 1 day = +20 USD -> 2/3 PENDING
    live_dir = tmp_path / ".runtime/live-overnight"
    live_dir.mkdir(parents=True, exist_ok=True)
    snaps_2of3 = [
        {"captured_utc": "2026-11-20T09:00:00+00:00", "account": {"balance": 5000.0, "equity": 5000.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-20T18:00:00+00:00", "account": {"balance": 5030.0, "equity": 5030.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-21T09:00:00+00:00", "account": {"balance": 5030.0, "equity": 5030.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-21T18:00:00+00:00", "account": {"balance": 5056.0, "equity": 5056.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-22T09:00:00+00:00", "account": {"balance": 5056.0, "equity": 5056.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-22T18:00:00+00:00", "account": {"balance": 5076.0, "equity": 5076.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
    ]
    log_p = live_dir / "mt5_live_spread_log.jsonl"
    log_p.write_text("\n".join(json.dumps(s) for s in snaps_2of3) + "\n", encoding="utf-8")

    mx2 = cockpit_server.build_prop_metrix_payload(tmp_path, program="the5ers_hs_5k_p1", allow_cloud_fetch=False)
    assert mx2["profitable_days_count"] == 2
    assert mx2["min_profitable_day_usd"] == 25.0
    r_days = next(r for r in mx2["rules"] if r["id"] == "min_trading_days")
    assert r_days["label"] == "Ngày lãi tối thiểu >= +0,5% (3 ngày)"
    assert r_days["status"] == "PENDING"
    assert mx2["risk_attribution"]["active_label"] == "OK"

    # Bump Day 3 to +25.0 USD (5056 -> 5081) -> 3/3 PASS!
    snaps_2of3[-1]["account"] = {"balance": 5081.0, "equity": 5081.0}
    log_p.write_text("\n".join(json.dumps(s) for s in snaps_2of3) + "\n", encoding="utf-8")
    mx3 = cockpit_server.build_prop_metrix_payload(tmp_path, program="the5ers_hs_5k_p1", allow_cloud_fetch=False)
    assert mx3["profitable_days_count"] == 3
    r_days3 = next(r for r in mx3["rules"] if r["id"] == "min_trading_days")
    assert r_days3["status"] == "PASS"

    # 2. R4 -> R3 -> R2 -> R1 strict priority checks
    # 2a. R3 fault (orphan_no_sl = 1) -> active_label == "R3"
    snap_r3 = [{"captured_utc": "2026-11-24T10:00:00+00:00", "account": {"balance": 10000.0, "equity": 9990.0}, "naqex_positions_count": 1, "orphan_no_sl": 1}]
    log_p.write_text(json.dumps(snap_r3[0]) + "\n", encoding="utf-8")
    mx_r3 = cockpit_server.build_prop_metrix_payload(tmp_path, program="ftmo_swing_10k_p1", allow_cloud_fetch=False)
    assert mx_r3["risk_attribution"]["active_label"] == "R3"
    assert mx_r3["risk_attribution"]["layers"]["R3"]["status"] == "ALERT"
    assert mx_r3["risk_attribution"]["layers"]["R1"]["status"] == "OK"

    # 2b. R4 overrides R3 (kill_switch=True AND orphan_no_sl=1) -> active_label == "R4"
    snap_r4 = [{
        "captured_utc": "2026-11-24T10:00:00+00:00",
        "account": {"balance": 10000.0, "equity": 9990.0},
        "naqex_positions_count": 1,
        "orphan_no_sl": 1,
        "heartbeat": {"kill_switch": True, "regime": "HALT"},
    }]
    log_p.write_text(json.dumps(snap_r4[0]) + "\n", encoding="utf-8")
    mx_r4 = cockpit_server.build_prop_metrix_payload(tmp_path, program="ftmo_swing_10k_p1", allow_cloud_fetch=False)
    assert mx_r4["risk_attribution"]["active_label"] == "R4"
    assert mx_r4["risk_attribution"]["layers"]["R4"]["status"] == "ALERT"

    # 2c. R2 alert (Amber daily DD >= 70% of daily limit, clean R4/R3) -> active_label == "R2"
    snap_r2 = [
        {"captured_utc": "2026-11-24T09:00:00+00:00", "account": {"balance": 10000.0, "equity": 10000.0}, "naqex_positions_count": 1, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-24T11:00:00+00:00", "account": {"balance": 10000.0, "equity": 9620.0}, "naqex_positions_count": 1, "orphan_no_sl": 0, "heartbeat": {"regime": "AMBER"}},
    ]
    log_p.write_text("\n".join(json.dumps(s) for s in snap_r2) + "\n", encoding="utf-8")
    mx_r2 = cockpit_server.build_prop_metrix_payload(tmp_path, program="ftmo_swing_10k_p1", allow_cloud_fetch=False)
    assert mx_r2["risk_attribution"]["active_label"] == "R2"
    assert mx_r2["risk_attribution"]["layers"]["R2"]["status"] == "ALERT"

    # 2d. R1 pure strategy drawdown (-2.8% over 3 clean days, daily DD < Amber, clean R4/R3/R2) -> active_label == "R1"
    snap_r1 = [
        {"captured_utc": "2026-11-21T18:00:00+00:00", "account": {"balance": 9900.0, "equity": 9900.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-22T18:00:00+00:00", "account": {"balance": 9800.0, "equity": 9800.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
        {"captured_utc": "2026-11-23T18:00:00+00:00", "account": {"balance": 9720.0, "equity": 9720.0}, "naqex_positions_count": 0, "orphan_no_sl": 0},
    ]
    log_p.write_text("\n".join(json.dumps(s) for s in snap_r1) + "\n", encoding="utf-8")
    mx_r1 = cockpit_server.build_prop_metrix_payload(tmp_path, program="ftmo_swing_10k_p1", allow_cloud_fetch=False)
    assert mx_r1["risk_attribution"]["active_label"] == "R1"
    assert mx_r1["risk_attribution"]["layers"]["R1"]["status"] == "ALERT"

    # 3. Verify static HTML DOM markers & zero external CDNs
    html_txt = (ROOT / "tooling/ai-engines/cockpit/static/index.html").read_text(encoding="utf-8")
    for marker in (
        'id="prop-risk-strip"',
        'id="mx-risk-active"',
        'id="mx-risk-headline"',
        'id="mx-risk-layers"',
        'value="ftmo_swing_25k_p1"',
        'value="ftmo_swing_50k_p1"',
        'value="ftmo_swing_100k_p1"',
        'value="the5ers_hs_20k_p1"',
    ):
        assert marker in html_txt, f"Missing HTML marker {marker}"
    assert "http://" not in html_txt and "https://" not in html_txt


def test_prop_tier_scaling_and_symcap_audit_receipt_and_seal():
    """Verify verified quantitative receipt PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124.{md,json,sha256}."""
    import hashlib

    base = ROOT / "planning/research/PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124"
    md_p = base.with_suffix(".md")
    js_p = base.with_suffix(".json")
    sha_p = base.with_suffix(".sha256")
    for p in (md_p, js_p, sha_p):
        assert p.is_file(), f"Missing audit artifact: {p}"
        assert p.stat().st_size < 900 * 1024, f"Artifact exceeds 900 KB: {p}"

    # Verify SHA-256 matches exact JSON bytes
    raw_js = js_p.read_bytes()
    actual_sha = hashlib.sha256(raw_js).hexdigest()
    expected_sha = sha_p.read_text(encoding="utf-8").strip().split()[0]
    assert actual_sha == expected_sha

    # Verify Holdout seal & quantitative findings
    data = json.loads(raw_js.decode("utf-8"))
    assert data["order_send_count"] == 0
    assert data["order_send_capable"] is False
    assert data["holdout_rows_analysed"] == 0
    assert data["mc_paths"] == 10_000
    assert data["mc_seed"] == 20261124
    assert data["dev_window"].split("..")[1] < "2025-01-01"

    hl = data["highlights"]
    # Tightening SYMCAP 3.50% -> 1.75% must strictly lower 1st-try daily breach rate
    assert hl["ftmo_10k_daily_breach_1try_350_to_175_pct"][1] < hl["ftmo_10k_daily_breach_1try_350_to_175_pct"][0]
    # Scaling 10K -> 100K must multiply EV/Fee by >= 2.0x
    assert hl["ftmo_ev_per_fee_multiplier_10k_to_100k"] >= 2.0
    # Calibrating The5ers 50K for strict 4%/8% DD must slash daily breach vs naive 5K preset
    assert hl["the5ers_50k_naive_vs_calibrated_daily_breach_1try_pct"][2] < hl["the5ers_50k_naive_vs_calibrated_daily_breach_1try_pct"][0]

    # Verify Markdown prose hygiene (YAML frontmatter + zero bare '$')
    md_txt = md_p.read_text(encoding="utf-8")
    assert md_txt.startswith("---\n")
    for line_no, line in brain_cli._iter_non_code_lines(md_txt):
        cleaned = brain_cli.INLINE_CODE_RE.sub("", line)
        assert "$" not in cleaned, f"Bare '$' in {md_p.name}:{line_no}: {line}"


def test_astra_f18_cockpit_zero_equity_preserved_and_emergency_delivery_status(tmp_path: Path):
    """Astra F18: equity==0.0 must NEVER fall back to balance; emergency cover must state delivery_status."""
    live_dir = tmp_path / ".runtime/live-overnight"
    live_dir.mkdir(parents=True, exist_ok=True)
    snap_zero = {
        "captured_utc": "2026-11-24T10:00:00+00:00",
        "account": {"balance": 10000.0, "equity": 0.0},
        "naqex_positions_count": 0,
        "orphan_no_sl": 0,
    }
    (live_dir / "mt5_live_spread_log.jsonl").write_text(json.dumps(snap_zero) + "\n", encoding="utf-8")
    mx = cockpit_server.build_prop_metrix_payload(tmp_path, program="ftmo_swing_10k_p1", allow_cloud_fetch=False)
    assert mx["account"]["equity_usd"] == 0.0
    assert mx["buffers"]["permitted_max_loss_usd"] == 0.0

    # Emergency cover without bridge_dir -> explicit LOCAL_AUDIT_ONLY_NOT_DELIVERED_TO_MT5
    st1, res1 = cockpit_server.apply_emergency_cover_action(
        tmp_path,
        {"cover_opened": True, "action": "HALT_NEW_ENTRIES", "confirm_code": "HALT", "reason": "f18_test"},
        bridge_dir=None,
    )
    assert st1 == 200 and res1["mt5_bridge_written"] is False
    assert res1["delivery_status"] == "LOCAL_AUDIT_ONLY_NOT_DELIVERED_TO_MT5"

    # Emergency cover with bridge_dir -> explicit WRITTEN_TO_MT5_BRIDGE_AWAITING_ORCH_ACK
    bridge = tmp_path / "mt5_files"
    st2, res2 = cockpit_server.apply_emergency_cover_action(
        tmp_path,
        {"cover_opened": True, "action": "HALT_NEW_ENTRIES", "confirm_code": "HALT", "reason": "f18_bridge"},
        bridge_dir=bridge,
    )
    assert st2 == 200 and res2["mt5_bridge_written"] is True
    assert res2["delivery_status"] == "WRITTEN_TO_MT5_BRIDGE_AWAITING_ORCH_ACK"
    assert (bridge / "naqex_manual_halt.flag").is_file()


def test_astra_r2_06_and_round3_settled_cash_ledger():
    """Astra R2-06 + Round-3: strictly separate out-of-pocket, Hub Credit, receivable, principal recovery & surplus."""
    evs_short = [
        treasury_ledger.SettledCashEvent("2026-01-05", "OUT_OF_POCKET_FEE", 80.0, "A1", "The5ers"),
        treasury_ledger.SettledCashEvent("2026-02-01", "HUB_CREDIT_GRANT", 20.0, "A1", "The5ers"),
        treasury_ledger.SettledCashEvent("2026-02-15", "PAYOUT_SETTLED", 65.0, "A1", "The5ers", settled_date="2026-02-20", withdrawal_fee_usd=5.0, cycle_id="C1", operator_hours=4.0),
    ]
    s1 = treasury_ledger.compute_settled_cash_summary(evs_short, as_of_date="2026-02-25", required_next_ticket_fee_usd=168.0)
    assert s1["out_of_pocket_paid_usd"] == 80.0
    assert s1["settled_payouts_net_usd"] == 60.0
    assert s1["hub_credits_non_withdrawable_usd"] == 20.0
    assert s1["net_settled_cash_usd"] == -20.0
    assert s1["principal_recovered"] is False
    assert s1["principal_shortfall_usd"] == 20.0
    assert s1["allocatable_surplus_usd"] == 0.0
    assert s1["stage_promotion_ready"] is False

    # Add unsettled future payout (settled_date > as_of_date) -> MUST stay receivable, NOT boost settled cash!
    evs_more = list(evs_short) + [
        treasury_ledger.SettledCashEvent("2026-03-01", "PAYOUT_SETTLED", 500.0, "A1", "The5ers", settled_date="2026-03-06", withdrawal_fee_usd=17.5, cycle_id="C2", operator_hours=3.0),
    ]
    s_before = treasury_ledger.compute_settled_cash_summary(evs_more, as_of_date="2026-03-03", required_next_ticket_fee_usd=168.0)
    assert s_before["receivable_unsettled_usd"] == 482.5
    assert s_before["principal_recovered"] is False
    assert s_before["stage_promotion_ready"] is False

    # After settlement date (2026-03-06): 2 positive cycles, principal recovered, net = 462.5 >= 2*168 (336) -> READY!
    s_after = treasury_ledger.compute_settled_cash_summary(evs_more, as_of_date="2026-03-10", required_next_ticket_fee_usd=168.0)
    assert s_after["receivable_unsettled_usd"] == 0.0
    assert s_after["principal_recovered"] is True
    assert s_after["settled_positive_cycles"] == 2
    assert s_after["net_settled_cash_usd"] == 462.5
    assert s_after["allocatable_surplus_usd"] == 126.5
    assert s_after["stage_promotion_ready"] is True


# ---------------------------------------------------------------------------
# 5. Black Friday 30/11 Sprint & Sanitized Node1 Summary Endpoints
# ---------------------------------------------------------------------------

def test_blackfriday_sprint_endpoint_artifacts_vault_and_ci_fallback(tmp_path: Path):
    """Verify /api/blackfriday-sprint countdown, Mũi 1-3 pickup, vault mount status, 30s cache & CI absent-file fallback."""
    from datetime import datetime, timezone

    cockpit_server.clear_sprint_and_node1_caches()

    # 1. Clean empty tmp_path (CI runner without runtime artifacts or private_vault/)
    empty_root = tmp_path / "ci_empty"
    empty_root.mkdir(parents=True)
    fixed_now = datetime(2026, 11, 28, 7, 30, 0, tzinfo=timezone.utc)  # 49h 30m before 2026-11-30T09:00:00Z
    ci_pay = cockpit_server.build_blackfriday_sprint_payload(empty_root, now_utc=fixed_now, use_cache=False)
    assert ci_pay["order_send_count"] == 0
    assert ci_pay["holdout_sealed"] is True
    assert ci_pay["deadline_iso"] == "2026-11-30T09:00:00Z"
    assert ci_pay["remaining_hours"] == 49
    assert ci_pay["remaining_minutes"] == 30
    assert ci_pay["expired"] is False
    assert ci_pay["private_vault_status"] == "NOT_MOUNTED"
    assert ci_pay["mui3_realtick"]["status"] == "pending"
    assert ci_pay["mui3_realtick"]["available"] is False
    assert ci_pay["mui1_mui2"]["realized_friction"]["status"] == "pending"
    assert ci_pay["mui1_mui2"]["live_spreads"]["status"] == "pending"
    assert ci_pay["mui1_mui2"]["symbol_table"] == []

    # 2. Populate synthetic Mũi 3, Mũi 1-2 & Layer-2 private_vault/owner (with decoy private note never exposed!)
    full_root = tmp_path / "full_ws"
    (full_root / "private_vault/owner").mkdir(parents=True)
    (full_root / "private_vault/owner/SECRET_NOTE.md").write_text("TOP_SECRET_VND_999999", encoding="utf-8")

    rt_dir = full_root / ".runtime/mt5-realtick-results/MASTER_PROP7E_2024Q4_L30_50ms"
    rt_dir.mkdir(parents=True)
    (rt_dir / "parsed_result.json").write_text(
        json.dumps({
            "summary": {
                "label": "MASTER_PROP7E_2024Q4_L30_50ms",
                "from_date": "2024.09.01",
                "to_date": "2024.12.31",
                "leverage": 30,
                "elapsed_s": 267.1,
                "report_ok": True,
                "total_swap_usd": 0.0,
                "total_comm_usd": -34.0,
                "propguard_ok_lines": 1,
                "propguard_warn_lines": 0,
                "order_rejects": 0,
                "log_errors": [],
                "net_by_symbol_usd": {"USDJPY": 111.36, "US100.cash": 14.46},
                "report_path": r"C:\secret_local_path\hidden.htm",
            },
            "report": {
                "ok": True,
                "period": "M5 (2024.09.01 - 2024.12.31)",
                "total_net_profit": 138.79,
                "profit_factor": 1.12,
                "sharpe_ratio": 1.03,
                "balance_dd_pct": 2.18,
                "equity_dd_pct": 2.59,
                "total_trades": 156,
                "win_rate_pct": 52.56,
                "swap_total_usd": 0.0,
                "swap_zero_ok": True,
                "commission_total_usd": -34.0,
            },
        }),
        encoding="utf-8",
    )

    live_dir = full_root / ".runtime/live-overnight"
    live_dir.mkdir(parents=True)
    (live_dir / "ftmo_realized_friction_summary_20261125.json").write_text(
        json.dumps({
            "generated_utc": "2026-11-25T14:00:00Z",
            "verdict": "PASS_WITHIN_BUDGET",
            "fills_count": 28,
            "realized_friction_multiplier_p50": 1.08,
            "realized_friction_multiplier_p90": 1.42,
            "adverse_slippage_p50_bps": 0.25,
            "adverse_slippage_p90_bps": 0.65,
            "by_symbol": {
                "USDJPY": {"fills_count": 7, "live_median_spread_bps": 0.42, "spread_ratio_vs_dev": 0.84},
                "GBPUSD": {"fills_count": 7, "live_median_spread_bps": 0.55, "spread_ratio_vs_dev": 0.92},
            },
        }),
        encoding="utf-8",
    )
    (live_dir / "mt5_live_spread_log.jsonl").write_text(
        "\n".join([
            json.dumps({
                "captured_utc": "2026-11-25T13:00:00+00:00",
                "quotes": {
                    "USDJPY": {"bid": 155.000, "ask": 155.006},
                    "GBPUSD": {"bid": 1.26000, "ask": 1.26008},
                    "EURJPY": {"bid": 165.000, "ask": 165.012},
                    "US100.cash": {"bid": 20000.0, "ask": 20002.0},
                },
            }),
            json.dumps({
                "captured_utc": "2026-11-25T13:00:05+00:00",
                "quotes": {
                    "USDJPY": {"bid": 155.010, "ask": 155.018},
                    "GBPUSD": {"bid": 1.26010, "ask": 1.26020},
                    "EURJPY": {"bid": 165.010, "ask": 165.025},
                    "US100.cash": {"bid": 20010.0, "ask": 20012.5},
                },
            }),
        ]) + "\n",
        encoding="utf-8",
    )

    # Verify via live HTTP server + 30s cache behavior
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=full_root)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/blackfriday-sprint", timeout=5) as resp:
            assert resp.status == 200
            raw_txt = resp.read().decode("utf-8")
            body = json.loads(raw_txt)
        assert body["order_send_count"] == 0
        assert body["holdout_sealed"] is True
        assert body["deadline_iso"] == "2026-11-30T09:00:00Z"
        assert body["private_vault_status"] == "MOUNTED"
        assert body["mui3_realtick"]["status"] == "AVAILABLE"
        assert body["mui3_realtick"]["latest"]["total_trades"] == 156
        assert body["mui3_realtick"]["latest"]["total_net_profit_usd"] == 138.79
        assert body["mui3_realtick"]["latest"]["swap_zero_ok"] is True
        assert body["mui1_mui2"]["realized_friction"]["fills_count"] == 28
        assert body["mui1_mui2"]["realized_friction"]["p50_friction_mult"] == 1.08
        assert body["mui1_mui2"]["live_spreads"]["samples_count"] == 2
        assert len(body["mui1_mui2"]["symbol_table"]) == 4
        # Never leak private vault contents or local filesystem paths!
        assert "TOP_SECRET_VND_999999" not in raw_txt
        assert "SECRET_NOTE" not in raw_txt
        assert "secret_local_path" not in raw_txt

        # Verify 30s TTL cache serves cached snapshot without re-reading deleted file
        (live_dir / "ftmo_realized_friction_summary_20261125.json").unlink()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/blackfriday-sprint", timeout=5) as resp2:
            body_cached = json.loads(resp2.read().decode("utf-8"))
        assert body_cached["mui1_mui2"]["realized_friction"]["fills_count"] == 28

        # With ?nocache=1 it re-reads cleanly and degrades to pending
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/blackfriday-sprint?nocache=1", timeout=5) as resp3:
            body_fresh = json.loads(resp3.read().decode("utf-8"))
        assert body_fresh["mui1_mui2"]["realized_friction"]["status"] == "pending"
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)
        cockpit_server.clear_sprint_and_node1_caches()


def test_node1_summary_mocked_live_ssh_sanitization_and_offline_fallback(tmp_path: Path, monkeypatch):
    """Verify /api/node1-summary with mocked node_ctl (live_ssh + zero IP/token leak) & clean offline/error fallback."""
    from ops_cloud import node_ctl

    cockpit_server.clear_sprint_and_node1_caches()

    # 1. Mock live_ssh probe containing decoy LAN/Tailscale IPs, URLs & tokens -> MUST be stripped completely!
    mock_calls = {"n": 0}

    def _fake_probe_ok(command_key: str, *args, **kwargs):
        mock_calls["n"] += 1
        assert command_key == "status"
        return {
            "checked_utc": "2026-11-25T10:00:00Z",
            "order_send_count": 0,
            "_ssh_host": "203.0.113.77",
            "mt5_procs": [{"pid": 4242, "session": 1, "start": "2026-11-25T07:00:00"}],
            "heartbeat": {
                "balance": 10000.0,
                "equity": 10014.25,
                "open_positions": 1,
                "age_sec": 4,
            },
            "propguard_ok_count": 7,
            "propguard_warn_count": 0,
            "ntp_offset": "16:00:01, +0.014s from 198.51.100.10",
            "heroku_last": {
                "ok": True,
                "endpoint": "https://decoy-app.example.com/api/heartbeat?token=SECRET_INGEST_999",
            },
            "heroku_last_raw": "Bearer SECRET_RAW_TOKEN_888 100.64.99.88",
            "disks": {"C": {"free_gb": 54.3, "total_gb": 118.0}},
            "system": {"free_ram_gb": 9.8, "auto_logon": "1"},
        }

    monkeypatch.setattr(node_ctl, "run_remote_probe", _fake_probe_ok)

    live_res = cockpit_server.build_node1_summary_payload(tmp_path, allow_ssh=True, use_cache=True)
    raw_live = json.dumps(live_res)
    assert live_res["order_send_count"] == 0
    assert live_res["holdout_sealed"] is True
    assert live_res["source"] == "live_ssh"
    assert live_res["connected"] is True
    assert live_res["mt5_running"] is True
    assert live_res["open_positions"] == 1
    assert live_res["balance"] == 10000.0
    assert live_res["equity"] == 10014.25
    assert live_res["propguard_ok_count"] == 7
    assert live_res["propguard_warn_count"] == 0
    assert live_res["ntp_offset"] == "+0.014s"
    assert live_res["auto_logon"] is True
    assert live_res["heroku_status"] == "OK"
    assert live_res["free_ram_gb"] == 9.8
    assert live_res["c_free_gb"] == 54.3
    # Zero leaked IPs, URLs, or tokens!
    for forbidden in ("203.0.113.77", "198.51.100.10", "100.64.99.88", "SECRET_INGEST_999", "SECRET_RAW_TOKEN_888", "decoy-app.example.com"):
        assert forbidden not in raw_live

    # Second call hits 30s TTL cache (no duplicate SSH call)
    live_res2 = cockpit_server.build_node1_summary_payload(tmp_path, allow_ssh=True, use_cache=True)
    assert live_res2["source"] == "live_ssh"
    assert mock_calls["n"] == 1

    # 2. SSH failure -> clean fallback to local cached heartbeat (preserving equity == 0.0!)
    cockpit_server.clear_sprint_and_node1_caches()

    def _fake_probe_fail(command_key: str, *args, **kwargs):
        raise RuntimeError("ssh unreachable 203.0.113.99")

    monkeypatch.setattr(node_ctl, "run_remote_probe", _fake_probe_fail)
    live_dir = tmp_path / ".runtime/live-overnight"
    live_dir.mkdir(parents=True, exist_ok=True)
    (live_dir / "naqex_heartbeat.json").write_text(
        json.dumps({"balance": 10000.0, "equity": 0.0, "open_positions": 0, "mt5_running": False}),
        encoding="utf-8",
    )
    fb_res = cockpit_server.build_node1_summary_payload(tmp_path, allow_ssh=True, use_cache=False)
    assert fb_res["order_send_count"] == 0
    assert fb_res["source"] == "fallback"
    assert fb_res["connected"] is False
    assert fb_res["mt5_running"] is False
    assert fb_res["balance"] == 10000.0
    assert fb_res["equity"] == 0.0
    assert fb_res["open_positions"] == 0
    assert fb_res["heroku_status"] == "LOCAL_CACHE"
    assert "203.0.113.99" not in json.dumps(fb_res)

    # 3. HTTP /api/node1-summary?offline=1 on completely empty root (CI runner) + UI HTML/JS markers
    empty_ci = tmp_path / "empty_ci"
    empty_ci.mkdir()
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=empty_ci)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/node1-summary?offline=1", timeout=5) as r:
            assert r.status == 200
            off_pay = json.loads(r.read().decode("utf-8"))
        assert off_pay["order_send_count"] == 0
        assert off_pay["source"] == "fallback"
        assert off_pay["connected"] is False
        assert off_pay["heroku_status"] == "UNAVAILABLE"
        for req_k in (
            "connected", "mt5_running", "open_positions", "balance", "equity",
            "propguard_ok_count", "propguard_warn_count", "ntp_offset",
            "auto_logon", "heroku_status", "free_ram_gb", "c_free_gb", "source",
        ):
            assert req_k in off_pay

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r_html:
            html_txt = r_html.read().decode("utf-8")
        for marker in (
            'id="panel-bf-sprint"',
            'id="bf-countdown-badge"',
            'id="bf-vault-badge"',
            'id="btn-bf-refresh"',
            'id="bf-calib-strip"',
            'id="bf-calib-headline"',
            'id="bf-calib-bar"',
            'id="bf-calib-sym-pills"',
            'id="bf-node-pills"',
            'id="tbl-bf-mui3"',
            'id="tbl-bf-friction"',
        ):
            assert marker in html_txt, f"Missing Sprint/Node1 HTML marker {marker}"
        assert "http://" not in html_txt and "https://" not in html_txt

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/static/app.js", timeout=5) as r_js:
            js_txt = r_js.read().decode("utf-8")
        assert "/api/blackfriday-sprint" in js_txt
        assert "/api/node1-summary" in js_txt
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)
        cockpit_server.clear_sprint_and_node1_caches()


def test_blackfriday_sprint_five_mui3_scenarios_and_live_calibration_csv_partial_safety(tmp_path: Path):
    """Wave 2.5C: verify 5 Mũi 3 scenarios (4x Model=4 + 1x Model=1), live CSV progress (valid + partial + missing), & zero leaks."""
    cockpit_server.clear_sprint_and_node1_caches()

    # 1. Missing CSV + empty/header-only CSV -> clean pending fallback
    empty_ws = tmp_path / "empty_csv"
    empty_ws.mkdir()
    pay0 = cockpit_server.build_blackfriday_sprint_payload(empty_ws, use_cache=False)
    cp0 = pay0["mui1_mui2"]["calibration_progress"]
    assert cp0["status"] == "pending"
    assert cp0["available"] is False
    assert cp0["completed_round_trips"] == 0
    assert cp0["target_round_trips"] == 28
    assert cp0["swap_zero_ok"] is True

    live_dir = tmp_path / "wave25c/.runtime/live-overnight"
    live_dir.mkdir(parents=True)
    header_cols = (
        "utc_ts,utc_iso,session,account_login,server,trade_seq,position_id,order_id,deal_id,"
        "symbol,leg,side,position_side,exit_reason,volume,pre_bid,pre_ask,pre_spread_pts,"
        "pre_spread_bps,expected_price,fill_price,sl_price,adverse_slip_pts,adverse_slip_bps,"
        "latency_ms,commission_usd,commission_bps,swap_usd,pnl_usd,retcode,dry_run,comment"
    )
    csv_p = live_dir / "ftmo_calibration_fills_1515343318.csv"
    csv_p.write_text(header_cols + "\n", encoding="utf-8")
    pay_hdr = cockpit_server.build_blackfriday_sprint_payload(tmp_path / "wave25c", use_cache=False)
    assert pay_hdr["mui1_mui2"]["calibration_progress"]["status"] == "pending"
    assert pay_hdr["mui1_mui2"]["calibration_progress"]["completed_round_trips"] == 0

    # 2. Populate all 5 Mũi 3 scenarios (4x Model=4 via JSON & tester.ini fallback + 1x Model=1 M1OHLC)
    ws = tmp_path / "wave25c"
    rt_root = ws / ".runtime/mt5-realtick-results"
    specs = [
        ("MASTER_PROP7E_2024Q4_L30_50ms", None, "Model=4", 156, 138.79, 1.12, 1.03, 2.59),
        ("MASTER_PROP7E_2024Q4_STRESS_150ms", None, "Model=4", 156, 156.19, 1.13, 1.16, 2.50),
        ("MASTER_PROP7E_2024Q4_P1_4X_L100_50ms", None, "Model=4", 155, 754.60, 1.24, 2.02, 6.27),
        ("MASTER_PROP7E_2024Q4_P1_4X_STRESS_150ms", 4, "Model=4", 155, 755.69, 1.24, 2.03, 6.23),
        ("MASTER_PROP7E_2024FULL_L100_50ms_M1OHLC", 1, "Model=1", 469, 744.48, 1.19, 1.47, 3.97),
    ]
    for lbl, j_model, ini_line, tr, net, pf, sh, eqdd in specs:
        d = rt_root / lbl
        d.mkdir(parents=True, exist_ok=True)
        (d / "tester.ini").write_text(f"[Tester]\n{ini_line}\n", encoding="utf-8")
        summ_obj = {
            "label": lbl,
            "from_date": "2024.01.01" if "FULL" in lbl else "2024.09.01",
            "to_date": "2024.12.31",
            "leverage": 30 if "L30" in lbl else 100,
            "report_ok": True,
            "total_swap_usd": 0.0,
            "total_comm_usd": -34.0,
            "order_rejects": 0,
            "log_errors": [],
        }
        if j_model is not None:
            summ_obj["model"] = j_model
        (d / "parsed_result.json").write_text(
            json.dumps({
                "summary": summ_obj,
                "report": {
                    "ok": True,
                    "total_trades": tr,
                    "total_net_profit": net,
                    "profit_factor": pf,
                    "sharpe_ratio": sh,
                    "equity_dd_pct": eqdd,
                    "swap_total_usd": 0.0,
                    "swap_zero_ok": True,
                },
            }),
            encoding="utf-8",
        )

    # 3. Populate live calibration CSV with 2 completed round-trips + 1 open trade + 1 dry_run (ignored) + 1 reject + 1 truncated partial line!
    csv_lines = [
        header_cols,
        "1795603139,2026-11-25T10:38:59+00:00,LONDON,1515343318,FTMO-Demo,1,990001,990001,880001,USDJPY,ENTRY,BUY,BUY,,0.01,159.282,159.287,5.0,0.31,159.287,159.287,159.137,0.0,0.0,370.0,-0.03,0.3,0.0,0.0,10009,False,SECRET_TAG_1",
        "1795603320,2026-11-25T10:42:00+00:00,LONDON,1515343318,FTMO-Demo,1,990001,990002,880002,USDJPY,EXIT,SELL,BUY,TIME_EXIT,0.01,159.310,159.313,3.0,0.19,159.310,159.310,159.137,2.0,0.2,510.0,-0.03,0.3,0.0,0.14,10009,False,EXIT_TIME",
        "1795603605,2026-11-25T10:46:45+00:00,LONDON,1515343318,FTMO-Demo,2,990002,990003,880003,GBPUSD,ENTRY,SELL,SELL,,0.01,1.30751,1.30757,6.0,0.46,1.30751,1.30751,1.30901,0.0,0.0,450.0,-0.03,0.23,0.0,0.0,10009,False,ENTRY_2",
        "1795603846,2026-11-25T10:50:46+00:00,LONDON,1515343318,FTMO-Demo,2,990002,990004,880004,GBPUSD,EXIT,BUY,SELL,TIME_EXIT,0.01,1.30718,1.30720,2.0,0.15,1.30720,1.30751,1.30901,30.0,2.4,590.0,-0.03,0.23,0.0,-0.05,10009,False,EXIT_2",
        "1795604000,2026-11-25T10:53:20+00:00,LONDON,1515343318,FTMO-Demo,3,990003,990005,880005,EURJPY,ENTRY,BUY,BUY,,0.01,173.800,173.808,8.0,0.46,173.808,173.809,173.600,1.0,0.1,400.0,-0.03,0.25,0.0,0.0,10009,False,OPEN_TRADE",
        "1795604010,2026-11-25T10:53:30+00:00,LONDON,1515343318,FTMO-Demo,99,990099,990099,880099,US100.cash,ENTRY,BUY,BUY,,0.01,20000,20002,200,1.0,20002,20002,19950,99.0,99.0,999.0,0.0,0.0,5.0,0.0,10009,True,DRYRUN_IGNORED",
        "1795604020,2026-11-25T10:53:40+00:00,LONDON,1515343318,FTMO-Demo,4,0,0,0,US100.cash,ENTRY_REJECT,BUY,BUY,,0.01,20000,20002,200,1.0,20002,0,19950,0,0,120.0,0,0,0,0,10018,False,REJECTED",
        "1795604099,2026-11-25T10:54:59+00:00,LONDON,1515343318,FTMO-Demo,5,990005,TRUNCATED_MID_WRITE",
    ]
    csv_p.write_text("\n".join(csv_lines), encoding="utf-8")

    # 4. Also verify native ftmo_demo_calibration_probe.py summary JSON schema parsing
    (live_dir / "ftmo_realized_friction_summary_20261125.json").write_text(
        json.dumps({
            "schema": "naqex-ftmo-realized-friction-summary-v1",
            "generated_utc": "2026-11-25T15:05:00+00:00",
            "calibration_account_login": 1515343318,
            "verdict": "PASS_WITHIN_1_5X",
            "portfolio_core4": {
                "realized_friction_multiplier_p50": 1.12,
                "realized_friction_multiplier_p90": 1.48,
                "latency_p50_ms": 450.0,
            },
            "spread_vs_dev_m1": {
                "USDJPY": {"OVERALL": {"live_median_spread_bps": 0.31, "live_p90_spread_bps": 0.52, "dev_m1_median_spread_bps": 0.40, "live_to_dev_spread_ratio_bps": 0.78}},
            },
            "realized_friction_by_symbol": {
                "USDJPY": {"paired_roundtrips": 7, "realized_friction_multiplier_p50": 1.05, "realized_friction_multiplier_p90": 1.35},
            },
        }),
        encoding="utf-8",
    )

    pay = cockpit_server.build_blackfriday_sprint_payload(ws, use_cache=False)
    raw_pay = json.dumps(pay)
    assert pay["order_send_count"] == 0
    assert pay["holdout_sealed"] is True

    # Verify all 5 Mũi 3 scenarios (4x Model=4 first, then 1x Model=1)
    m3 = pay["mui3_realtick"]
    assert m3["scenarios_count"] == 5
    assert m3["model4_count"] == 4
    assert m3["model1_count"] == 1
    assert all(s["model_badge"] == "Model=4 Real Ticks" and s["is_real_ticks"] is True for s in m3["scenarios"][:4])
    assert m3["scenarios"][4]["model"] == 1
    assert m3["scenarios"][4]["model_badge"] == "Model=1 1m OHLC"
    assert m3["scenarios"][4]["is_real_ticks"] is False
    assert m3["scenarios"][4]["sharpe_ratio"] == 1.47

    # Verify live calibration progress metrics & partial-line safety
    cp = pay["mui1_mui2"]["calibration_progress"]
    assert cp["status"] == "IN_PROGRESS"
    assert cp["available"] is True
    assert cp["completed_round_trips"] == 2
    assert cp["open_in_progress_count"] == 1
    assert cp["valid_legs_count"] == 5
    assert cp["rejected_count"] == 1
    assert cp["skipped_partial_rows"] == 1
    assert cp["swap_zero_ok"] is True
    assert cp["mean_adverse_slip_pts"] == 6.6   # (0 + 2 + 0 + 30 + 1) / 5
    assert cp["max_adverse_slip_pts"] == 30.0
    assert cp["mean_adverse_slip_bps"] == 0.54  # (0 + 0.2 + 0 + 2.4 + 0.1) / 5
    assert cp["max_adverse_slip_bps"] == 2.4
    assert cp["median_latency_ms"] == 450.0     # median([370, 400, 450, 510, 590])
    assert cp["per_symbol_fills"]["USDJPY"]["completed"] == 1
    assert cp["per_symbol_fills"]["GBPUSD"]["completed"] == 1
    assert cp["per_symbol_fills"]["EURJPY"]["open"] == 1
    assert cp["per_symbol_fills"]["US100.cash"]["completed"] == 0

    # Verify native summary JSON schema pickup
    rf = pay["mui1_mui2"]["realized_friction"]
    assert rf["available"] is True
    assert rf["p50_friction_mult"] == 1.12
    assert rf["p90_friction_mult"] == 1.48
    assert rf["fills_count"] == 7
    usd_row = next(r for r in pay["mui1_mui2"]["symbol_table"] if r["symbol"] == "USDJPY")
    assert usd_row["ratio_vs_dev_1x"] == 0.78

    # Zero leaked login, ticket/position IDs, or comment secrets!
    for forbidden in ("1515343318", "990001", "880001", "SECRET_TAG_1", "TRUNCATED_MID_WRITE"):
        assert forbidden not in raw_pay


def test_fetch_heroku_node1_uses_header_auth_and_strips_query_token(tmp_path: Path, monkeypatch):
    """Wave 2.8A OPSEC: _fetch_heroku_node1_cached must send X-Naqex-View-Token header and NEVER ?token= in URL."""
    cfg_dir = tmp_path / ".runtime/ops-cloud"
    cfg_dir.mkdir(parents=True)
    secret_tok = "super-secret-view-token-98765"
    (cfg_dir / "heroku_connection_local.json").write_text(
        json.dumps({
            "web_url": f"https://example-deadman.herokuapp.com/?token={secret_tok}",
            "mobile_dashboard_url": f"https://example-deadman.herokuapp.com/?token={secret_tok}",
        }),
        encoding="utf-8",
    )

    seen: dict[str, object] = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return json.dumps({
                "nodes": [{
                    "account_label": "NAQEX_NODE1",
                    "status": "OK",
                    "age_sec": 7,
                    "mt5_running": True,
                    "balance": 10000.0,
                    "equity": 10005.0,
                    "daily_dd_pct": 0.0,
                    "static_dd_pct": 0.0,
                    "open_positions": 0,
                    "orphan_no_sl": 0,
                    "regime": "NORMAL",
                    "kill_switch": False,
                    "last_seen_utc": "2026-11-25T11:00:00Z",
                }]
            }).encode("utf-8")

    def _fake_urlopen(req, timeout=2.5):
        seen["url"] = req.full_url
        seen["headers"] = {k.lower(): v for k, v in req.header_items()}
        return _FakeResp()

    monkeypatch.setattr(cockpit_server.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(cockpit_server, "_HEROKU_STATUS_CACHE", (0.0, None))

    res = cockpit_server._fetch_heroku_node1_cached(tmp_path, ttl_sec=0.0)
    assert res is not None
    assert res["source"] == "HEROKU_EU_LIVE"
    assert res["account_label"] == "NAQEX_NODE1"
    assert seen["url"] == "https://example-deadman.herokuapp.com/api/status"
    assert "token=" not in str(seen["url"])
    assert secret_tok not in str(seen["url"])
    assert seen["headers"]["x-naqex-view-token"] == secret_tok
    monkeypatch.setattr(cockpit_server, "_HEROKU_STATUS_CACHE", (0.0, None))





