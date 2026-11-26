"""Wave-2 Cycle 4E Tests: 1-Command Daily Operations Briefing CLI & Single Roadmap SSOT Playbook.

Covers:
  1. Live workspace briefing execution + CLI `--out-md` / `--out-json` artifact output (`OrderSend = 0`).
  2. Graceful missing-file degradation on an empty root (all 6 checks -> `PENDING`, `health_score == 0`, no crashes).
  3. Health-score invariants: 100/100 `GREEN_OPERATIONAL` when all 6 pillars pass; hard fail-closed cap `<= 40`
     (`CRITICAL_FAIL_CLOSED`) whenever `orphan_no_sl > 0` OR `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 mismatches!
  4. `knowledge/playbooks/naqex-master-roadmap-2026-2027.md` + canonical Single Roadmap SSOT
     `planning/TOP1-SOLO-QUANT-MASTER-PLAN.md`: size caps, LF-only, YAML frontmatter, `0` bare `$`,
     all 4 evidence-gated milestones (`Mốc 0..3`), Round-3/Step-8 verified invariants, `0` broken local links,
     and clean `brain_cli` vault audit.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))
if str(ROOT / "tooling/knowledge") not in sys.path:
    sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli  # noqa: E402
from quant_factory import daily_ops_briefing as dob  # noqa: E402

PLAYBOOK_PATH = ROOT / "knowledge/playbooks/naqex-master-roadmap-2026-2027.md"
MASTER_PLAN_PATH = ROOT / "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"
HOLDOUT_LOCK_SRC = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
POD_V2_MD_SRC = ROOT / "planning/research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md"


def test_daily_ops_briefing_live_workspace_and_cli_outputs(tmp_path: Path) -> None:
    assert dob.ORDER_SEND_COUNT == 0
    out_md = tmp_path / "briefing.md"
    out_json = tmp_path / "briefing.json"

    rc = dob.main(
        [
            "--capital-usd",
            "50000",
            "--usd-vnd",
            "25500",
            "--out-md",
            str(out_md),
            "--out-json",
            str(out_json),
        ]
    )
    assert rc == 0
    assert out_md.is_file() and out_json.is_file()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "naqex-daily-ops-briefing-v1"
    assert data["order_send_count"] == 0
    assert data["max_score"] == 100
    assert 0 <= data["health_score"] <= 100
    assert len(data["checks"]) == 6

    by_id = {c["id"]: c for c in data["checks"]}
    assert by_id["holdout_lock"]["status"] == "PASS"
    assert by_id["holdout_lock"]["score"] == 25
    assert by_id["pod_v2_risk_caps"]["status"] == "PASS"
    assert by_id["pod_v2_risk_caps"]["data"]["cap_enforced_le_25pct"] is True
    assert by_id["pod_v2_risk_caps"]["data"]["nco_worst_loss_usd"] == 6445.0

    # If live Maker probe landed, confirm exact fill_rate_pct & effective_cost_bps parsing (not None)
    if (ROOT / ".runtime/live-overnight/crypto_maker_shadow_latest.json").is_file():
        mk = by_id["crypto_maker_probe"]["data"]
        assert mk["fill_rate_pct"] is not None
        assert mk["effective_cost_bps"] is not None

    md_txt = out_md.read_text(encoding="utf-8")
    assert md_txt.startswith("---\n")
    assert "$" not in md_txt
    assert "NCO_CexCap25" in md_txt


def test_daily_ops_briefing_graceful_missing_files_empty_root(tmp_path: Path) -> None:
    payload = dob.build_daily_ops_briefing(root=tmp_path, capital_usd=10_000.0, usd_vnd=25_500.0)
    assert payload["order_send_count"] == 0
    assert payload["health_score"] == 0
    assert payload["overall_grade"] == "STANDBY_AWAITING_DAEMONS"
    assert payload["status_counts"] == {"PASS": 0, "WARN": 0, "PENDING": 6, "FAIL": 0}

    md = dob.render_daily_ops_briefing_md(payload)
    assert "$" not in md
    assert "PENDING=6" in md


def test_daily_ops_briefing_fail_closed_orphan_and_holdout_breach_caps_score(tmp_path: Path) -> None:
    """Verify full 100/100 healthy state AND fail-closed <= 40 cap on orphan_no_sl or Holdout SHA tampering."""
    fixed_now = datetime(2026, 11, 24, 1, 30, 0, tzinfo=UTC)

    # 1. Copy authentic Holdout lock & Pod v2 report
    pr_dir = tmp_path / "planning/research"
    pr_dir.mkdir(parents=True, exist_ok=True)
    lock_dst = pr_dir / "NATIVE_FTMO_HOLDOUT_LOCK.json"
    lock_dst.write_bytes(HOLDOUT_LOCK_SRC.read_bytes())
    (pr_dir / "QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md").write_bytes(POD_V2_MD_SRC.read_bytes())

    # 2. Populate healthy Crypto Shadow & Crypto Maker Probe
    ov = tmp_path / ".runtime/live-overnight"
    ov.mkdir(parents=True, exist_ok=True)
    (ov / "crypto_shadow_latest.json").write_text(
        json.dumps(
            {
                "cycle_num": 12,
                "order_send_count": 0,
                "tca_summary_top15": {
                    "median_spread_bps": 1.2,
                    "median_slip_10k_bps": 1.8,
                    "backtest_assumed_oneway_slip_bps": 5.0,
                    "tca_within_budget_10k": True,
                },
                "sleeve2_f4_4h_ema": {"btc_regime_bull": True, "active_count": 3},
                "sleeve3a_carry_btc_eth": {
                    "perp_live_basis": {
                        "BTCUSDT": {"next_funding_ann_pct": 8.0},
                        "ETHUSDT": {"next_funding_ann_pct": 6.5},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (ov / "crypto_maker_shadow_latest.json").write_text(
        json.dumps(
            {
                "cycle_num": 4,
                "order_send_count": 0,
                "passive_limit_probe_active_basket": {
                    "15m": {
                        "fill_rate": 0.79,
                        "mean_adv_sel_5m_bps": 0.5,
                        "effective_cost_bps": 4.10,
                        "passes_m2_hurdle": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    # 3. Populate healthy MT5 Heartbeat + Exec Audit CSV + Real-Tick Matrix
    mql_files = tmp_path / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files"
    mql_files.mkdir(parents=True, exist_ok=True)
    hb_path = mql_files / "naqex_heartbeat.json"
    hb_ok = {
        "utc_ts": int(fixed_now.timestamp() - 30),
        "balance": 10_000.0,
        "equity": 10_025.0,
        "open_positions": 1,
        "orphan_no_sl": 0,
        "kill_switch": False,
        "dry_run": True,
    }
    hb_path.write_text(json.dumps(hb_ok), encoding="utf-8")
    (mql_files / "naqex_exec_audit.csv").write_text(
        "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,lots,spread_pts,latency_ms,retcode,comment\n"
        "1795455000,101,USDJPY,BUY,ENTRY,155.0,155.002,154.2,0.10,8.0,45.0,10009,OK\n",
        encoding="utf-8",
    )
    rt_dir = tmp_path / ".runtime/mt5-realtick-results"
    rt_dir.mkdir(parents=True, exist_ok=True)
    (rt_dir / "realtick_matrix_summary.json").write_text(
        json.dumps(
            {
                "model": 4,
                "window": "2024-09-01..2024-12-31",
                "latencies_ms": [50, 150, 250],
                "engines_run": 1,
                "reconciliation": {
                    "E2_USDJPY_EXP80": {
                        "verdict": "MATCH",
                        "latency_drag_50_to_250ms_usd": -2.5,
                        "latency_curve": {"50ms": {"ok": True, "swap_zero_ok": True}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    # Healthy check -> 100 / 100 GREEN_OPERATIONAL
    res_ok = dob.build_daily_ops_briefing(root=tmp_path, now_utc=fixed_now)
    assert res_ok["health_score"] == 100
    assert res_ok["overall_grade"] == "GREEN_OPERATIONAL"
    assert res_ok["status_counts"] == {"PASS": 6, "WARN": 0, "PENDING": 0, "FAIL": 0}

    # Inject orphan_no_sl = 1 -> CRITICAL_FAIL_CLOSED and score capped <= 40!
    hb_path.write_text(json.dumps({**hb_ok, "orphan_no_sl": 1}), encoding="utf-8")
    res_orphan = dob.build_daily_ops_briefing(root=tmp_path, now_utc=fixed_now)
    assert res_orphan["overall_grade"] == "CRITICAL_FAIL_CLOSED"
    assert res_orphan["health_score"] <= 40
    assert next(c for c in res_orphan["checks"] if c["id"] == "mt5_demo_live")["status"] == "FAIL"

    # Restore heartbeat, tamper Holdout lock -> CRITICAL_FAIL_CLOSED and score capped <= 40!
    hb_path.write_text(json.dumps(hb_ok), encoding="utf-8")
    lock_dst.write_text('{"tampered": true}\n', encoding="utf-8")
    res_tamper = dob.build_daily_ops_briefing(root=tmp_path, now_utc=fixed_now)
    assert res_tamper["overall_grade"] == "CRITICAL_FAIL_CLOSED"
    assert res_tamper["health_score"] <= 40
    assert next(c for c in res_tamper["checks"] if c["id"] == "holdout_lock")["status"] == "FAIL"


def _assert_relative_markdown_links_resolve(md_path: Path, text: str, *, min_links: int) -> None:
    link_re = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
    links = link_re.findall(text)
    assert len(links) >= min_links, f"Expected >= {min_links} Markdown links in {md_path.name}, got {len(links)}"
    root_resolved = ROOT.resolve()
    for target in links:
        if target.startswith(("http://", "https://", "mailto:", "file://")):
            continue
        resolved = (md_path.parent / target).resolve()
        assert resolved.is_relative_to(root_resolved), f"Link '{target}' escapes workspace in {md_path.name}"
        assert resolved.exists(), f"Broken relative link '{target}' in {md_path.name}"


def test_master_roadmap_playbook_hygiene_links_and_verified_figures() -> None:
    assert PLAYBOOK_PATH.is_file(), f"Missing {PLAYBOOK_PATH}"
    assert MASTER_PLAN_PATH.is_file(), f"Missing {MASTER_PLAN_PATH}"

    raw_bytes = PLAYBOOK_PATH.read_bytes()
    assert b"\r" not in raw_bytes, "CRLF detected in roadmap playbook — must be LF-only"
    raw = raw_bytes.decode("utf-8")
    assert PLAYBOOK_PATH.stat().st_size < 18 * 1024, "Playbook exceeds 18 KB cap"
    assert raw.startswith("---\n") and raw.count("\n---\n") >= 1
    assert "$" not in raw, "Bare '$' detected in roadmap playbook — use USD!"

    plan_bytes = MASTER_PLAN_PATH.read_bytes()
    assert b"\r" not in plan_bytes, "CRLF detected in Single Roadmap SSOT — must be LF-only"
    plan_raw = plan_bytes.decode("utf-8")
    assert MASTER_PLAN_PATH.stat().st_size < 24 * 1024, "Single Roadmap SSOT exceeds 24 KB cap"
    assert plan_raw.startswith("---\n") and plan_raw.count("\n---\n") >= 1
    assert "$" not in plan_raw, "Bare '$' detected in Single Roadmap SSOT — use USD!"

    # Playbook must cleanly delegate to the Single Roadmap SSOT without competing legacy doctrine
    for tok in (
        "status: pointer_to_single_ssot",
        'canonical_owner: "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md"',
        "order_send_count: 0",
        "holdout_rows_analysed: 0",
        "planning/TOP1-SOLO-QUANT-MASTER-PLAN.md",
        "Naqex_Master_Prop7E.mq5",
        "C10_NEWS_ON",
        "naqex_red_news_utc.csv",
        "Settled Cash",
        "treasury_ledger.py",
        "holdout_v1",
        "holdout_v2_prospective",
        "R4 -> R3 -> R2 -> R1",
        "NATIVE_FTMO_HOLDOUT_LOCK.json",
        "C10-POST-SSOT-LOOKAHEAD-RECONCILIATION-20261127.md",
    ):
        assert tok in raw, f"Missing SSOT pointer anchor '{tok}' in playbook"

    # Retired pre-Round-3 doctrine must not leak back into the playbook stub
    for retired in ("DUAL_2FIRM_STAGGER_42D", "E40_APPROVED_EQW_ENSEMBLE"):
        assert retired not in raw, f"Retired pre-Round-3 anchor '{retired}' leaked back into playbook"

    # Canonical Single Roadmap SSOT must preserve all 4 evidence-gated milestones and locked invariants
    for milestone in ("Mốc 0", "Mốc 1", "Mốc 2", "Mốc 3"):
        assert milestone in plan_raw, f"Missing milestone '{milestone}' in Single Roadmap SSOT"

    for tok in (
        "ssot_role: SINGLE_ROADMAP_OWNER",
        'active_candidate: "C10_NEWS_ON"',
        "order_send_count: 0",
        "holdout_rows_analysed: 0",
        "Naqex_Master_Prop7E.mq5",
        "naqex_red_news_utc.csv",
        "Settled Cash",
        "treasury_ledger.py",
        "NATIVE_FTMO_HOLDOUT_LOCK.json",
        "firms_catalog.json",
        "check_architecture.py",
        "holdout_v1",
        "holdout_v2_prospective",
        "R4 -> R3 -> R2 -> R1",
        "CEX <= 25%",
    ):
        assert tok in plan_raw, f"Missing verified SSOT anchor '{tok}' in {MASTER_PLAN_PATH.name}"

    # Every relative Markdown link in BOTH playbook and canonical Single Roadmap SSOT resolves cleanly on disk
    _assert_relative_markdown_links_resolve(PLAYBOOK_PATH, raw, min_links=10)
    _assert_relative_markdown_links_resolve(MASTER_PLAN_PATH, plan_raw, min_links=15)

    # Full knowledge vault audit stays spotless
    assert brain_cli.find_broken_knowledge_links(ROOT) == []
    assert brain_cli.find_near_duplicate_topic_headings(ROOT) == []
