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



