"""Wave 2B (`W4-G17`) Tests: Unified Chief-of-Staff Morning Briefing Wire (All 4 Inside-Out Tiers).

Verifies:
  1. All 4 Wave 4 upstream feeds wire cleanly into ONE unified `tooling/automation/morning_briefing.py`:
       - Section A (Tier 1/4 Prop Fleet `S0..S7` + `E1..E6`): `fleet_ledger.json` -> `sample_fleet_ledger.json`
         -> `NOT_INITIALIZED`, active Challenges/Funded vs `400K USD` cap, active `E1..E6`, `21/27/30d` inactivity.
       - Section B (Tier 3 Own-Book Shadow `OPS-4`): `ownbook_shadow_ops_summary.json`, `GREEN/AMBER/RED`,
         `CEX % <= 25%`, annualized funding % & `FUNDING_COMPRESSION_ALERT (< 3%)`.
       - Section C (Tier 4 AI Radar & Macro Supervisor): `ai_model_radar_latest.json` (top budget supervisor
         + `price_delta` alerts), `prospective_shadow_ledger.json` (`2026-11-30`), `wave4_pit24_and_ai_rubric.json`,
         hard monthly API budget `<= 5.00 USD`.
  2. Graceful degradation when `.runtime/offensive4/` is missing or corrupt (CI `-m "not local_cache"` safe).
  3. Zero bare `$`, zero `G12` prop-firm support nudges, zero OPSEC leaks, zero CRLF/BOM, zero bare `assert`.
  4. AST scan confirming `0` `subprocess.run/Popen/call/check_call/check_output` calls missing `creationflags`
     across ALL `.py` files under `tooling/automation/` AND `tooling/ai-engines/ops_cloud/`, plus runtime
     `creationflags=_NO_WINDOW_FLAGS` verification in `morning_briefing.py`.
  5. Live `pythonw.exe tooling/automation/morning_briefing.py --offline-dry-run` smoke (`@pytest.mark.local_cache`).

All checks use `_check(...)` so tests remain 100% effective under BOTH `python` AND `python -O`.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tooling.automation import morning_briefing as mb  # noqa: E402

_SUBPROCESS_CALL_ATTRS: frozenset[str] = frozenset({"run", "Popen", "call", "check_call", "check_output"})
_G12_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bliên hệ\s+(?:support|hỗ trợ|ftmo|the5ers)"),
    re.compile(r"(?i)\bcontact\s+(?:support|ftmo|the5ers)"),
    re.compile(r"(?i)\bemail\s+(?:support|ftmo|the5ers)"),
    re.compile(r"(?i)\blive[\s-]?chat\b"),
    re.compile(r"(?i)\bnhắn\s+(?:support|hỗ trợ|ftmo|the5ers)"),
    re.compile(r"(?i)\bgửi\s+(?:mail|email|ticket)\s+(?:cho\s+)?(?:support|hỗ trợ|ftmo|the5ers)"),
)
_FIXED_NOW = datetime(2026, 11, 28, 0, 30, 0, tzinfo=UTC)


def _check(cond: bool, msg: str) -> None:
    """Explicit invariant check immune to `python -O` assert stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha(tag: str) -> str:
    return hashlib.sha256(f"W4_BRIEFING_WIRE|{tag}".encode()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _build_fixture_fleet_ledger(
    *,
    ledger_id: str = "fixture-fleet-v1",
    accounts: list[dict[str, Any]] | None = None,
    transitions: list[dict[str, Any]] | None = None,
    active_signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sha_f1 = _sha("FUNDED-1X")
    sha_p1 = _sha("EVAL-P1")
    default_accounts = [
        {
            "account_id": "FTMO-STD10K-001",
            "contract_id": "ftmo_standard_10k",
            "firm_id": "ftmo",
            "firm_profile": "FTMO_STANDARD",
            "capital_usd": 10_000.0,
            "base_capital_usd": 10_000.0,
            "state": "S5_FUNDED_ACTIVE",
            "preset_mode": "FUNDED_1X",
            "preset_name": "FTMO_Std10K_Funded_Safe_1x.set",
            "preset_sha256": sha_f1,
            "expected_preset_sha256": sha_f1,
            "ops2_preflight_pass": True,
            "ops4_traffic_light": "GREEN",
            "open_positions": 0,
            "equity_usd": 10_350.0,
            "balance_usd": 10_350.0,
            "daily_dd_pct": 0.4,
            "static_dd_pct": 0.8,
            "days_since_last_trade": 4.0,
            "payout_cycles_completed": 1,
            "opened_utc": "2026-10-01T08:00:00Z",
            "last_transition_utc": "2026-11-16T07:30:00Z",
            "magic_range": [20261100, 20261199],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_std10k_001",
        },
        {
            "account_id": "THE5ERS-HS5K-003",
            "contract_id": "the5ers_hs_5k_classic",
            "firm_id": "the5ers",
            "firm_profile": "THE5ERS_HS_5K",
            "capital_usd": 5_000.0,
            "base_capital_usd": 5_000.0,
            "state": "S1_CHALLENGE_P1",
            "preset_mode": "EVAL_P1_SPRINT_4_5X",
            "preset_name": "The5ers_HS5K_P1_Sprint_4_5x.set",
            "preset_sha256": sha_p1,
            "expected_preset_sha256": sha_p1,
            "ops2_preflight_pass": True,
            "ops4_traffic_light": "GREEN",
            "open_positions": 0,
            "equity_usd": 5_185.0,
            "balance_usd": 5_185.0,
            "daily_dd_pct": 0.0,
            "static_dd_pct": 0.0,
            "days_since_last_trade": 2.0,
            "opened_utc": "2026-11-18T08:00:00Z",
            "last_transition_utc": "2026-11-18T08:15:00Z",
            "magic_range": [20261200, 20261299],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\the5ers_hs5k_003",
        },
    ]
    payload: dict[str, Any] = {
        "schema_version": "naqex-prop-fleet-ledger-v1",
        "ledger_id": ledger_id,
        "updated_utc": "2026-11-27T18:00:00Z",
        "holdout_cutoff_date": "2024-12-31",
        "holdout_rows_analysed": 0,
        "order_send_capable": False,
        "order_send_count": 0,
        "usd_vnd_rate": 25_765.94,
        "fleet_policy": {
            "concurrency_mode": "GATED_STAGGER",
            "max_concurrent_evals": 2,
            "max_concurrent_funded": 4,
            "max_accounts_per_firm": 3,
        },
        "accounts": accounts if accounts is not None else default_accounts,
        "transitions": transitions if transitions is not None else [],
        "fleet_summary": {
            "next_actions": [
                {
                    "account_id": "FTMO-STD10K-001",
                    "state": "S5_FUNDED_ACTIVE",
                    "action_code": "MONITOR_OPS4_AND_INACTIVITY",
                }
            ]
        },
    }
    if active_signals is not None:
        payload["active_signals"] = active_signals
    return payload


def _build_fixture_ownbook(
    *,
    traffic_light: str = "GREEN",
    cex_exposure_pct: float = 24.5,
    funding_pct: float = 8.4,
    compression_active: bool = False,
    active_alerts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "naqex-wave4-ownbook-shadow-ops-v1",
        "gate_id": "W4-G08",
        "generated_utc": "2026-11-27T18:42:07Z",
        "invariants": {
            "order_send_capable": False,
            "order_send_count": 0,
            "spend_vnd": 0,
            "holdout_cutoff_inclusive": "2024-12-31",
            "holdout_rows_analysed": 0,
            "hard_cex_cap_pct": 25.0,
            "funding_compression_threshold_pct": 3.0,
        },
        "ownbook_dev_performance": {
            "guarded_metrics": {
                "cagr_pct": 6.69,
                "sharpe": 1.36,
                "max_dd_pct": 8.09,
                "calmar": 0.83,
            }
        },
        "ops4_health_snapshot": {
            "as_of_date": "2024-12-31",
            "traffic_light": traffic_light,
            "action": "KEEP_CURRENT_RISK_1_0X" if traffic_light == "GREEN" else "REDUCE_RISK_0_5X",
            "risk_multiplier": 1.0 if traffic_light == "GREEN" else (0.5 if traffic_light == "AMBER" else 0.0),
            "cex_exposure_pct": cex_exposure_pct,
            "cex_cap_pct": 25.0,
            "cex_cap_compliant": cex_exposure_pct <= 25.0,
            "annualized_funding_rate_pct": funding_pct,
            "funding_compression_threshold_pct": 3.0,
            "funding_compression_active": compression_active,
            "rotated_carry_to_tbill_pct": 15.0 if compression_active else 0.0,
            "tbill_buffer_vehicle": "SGOV/BIL",
            "current_dd_pct": 2.34,
            "active_alerts": active_alerts if active_alerts is not None else [],
            "stress_summary": {"passed": 4, "total": 4, "all_passed": True},
        },
    }


def _build_fixture_ai_radar(
    *,
    top_monthly_usd: float = 0.0196,
    budget_cap_usd: float = 5.0,
    price_changes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    changes = price_changes if price_changes is not None else []
    drops = sum(1 for c in changes if c.get("direction") == "PRICE_DROP")
    incs = sum(1 for c in changes if c.get("direction") == "PRICE_INCREASE")
    return {
        "schema_version": "naqex-wave4-ai-model-radar-v1",
        "generated_utc": "2026-11-27T18:29:08Z",
        "hard_invariants": {
            "order_send_capable": False,
            "order_send_count": 0,
            "spend_vnd": 0,
            "holdout_rows_analysed": 0,
            "max_official_api_usd_per_month": budget_cap_usd,
        },
        "workload_assumptions": {
            "supervisor_runs_per_month": 44,
            "budget_cap_usd_per_month": budget_cap_usd,
            "usd_vnd_rate": 25_500.0,
        },
        "leaderboards": {
            "budget_macro_supervisor_monthly_usd": [
                {
                    "rank": 1,
                    "id": "qwen/qwen3.7-flash",
                    "name": "Qwen: Qwen3.7 Flash",
                    "monthly_usd": top_monthly_usd,
                    "monthly_vnd": int(round(top_monthly_usd * 25_500.0)),
                    "budget_utilization_pct": round((top_monthly_usd / budget_cap_usd) * 100.0, 2),
                    "within_budget_cap": top_monthly_usd <= budget_cap_usd,
                }
            ],
            "local_open_weight_fit": [
                {
                    "rank": 1,
                    "id": "qwen/qwen3.5-9b",
                    "q4_estimated_gb": 5.66,
                    "q4_fit_tier": "FULL_VRAM_FIT",
                }
            ],
        },
        "leaderboard_summary": {"budget_eligible_count": 302},
        "price_delta": {
            "has_previous_snapshot": True,
            "new_models": [],
            "removed_models": [],
            "price_changes_pct": changes,
            "counts": {
                "new_models": 0,
                "removed_models": 0,
                "price_changes": len(changes),
                "price_drops": drops,
                "price_increases": incs,
            },
        },
    }


def _build_fixture_prospective_ledger(
    *,
    commitments_count: int = 3,
    distinct_session_dates: int = 3,
    calendar_span_days: int = 4,
    verified: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": "naqex-wave4-prospective-shadow-ledger-v1",
        "prospective_only": True,
        "order_send_capable": False,
        "holdout_cutoff_date": "2024-12-31",
        "first_live_session_date": "2026-11-30",
        "min_audit_calendar_days": 30,
        "summary": {
            "verified": verified,
            "prospective_only": True,
            "first_live_session_date": "2026-11-30",
            "commitments_count": commitments_count,
            "distinct_session_dates": distinct_session_dates,
            "calendar_span_days": calendar_span_days,
            "min_audit_calendar_days": 30,
            "ready_for_prospective_oos_audit": calendar_span_days >= 30,
            "head_sha256": _sha("SHADOW-HEAD"),
        },
        "commitments": [{"seq": i + 1} for i in range(commitments_count)],
    }


def _build_fixture_pit24_rubric() -> dict[str, Any]:
    return {
        "schema_version": "naqex-wave4-pit24-and-ai-rubric-v1",
        "generated_utc": "2026-11-27T18:56:53Z",
        "hard_invariants": {
            "order_send_capable": False,
            "order_send_count": 0,
            "spend_vnd": 0,
            "holdout_rows_analysed": 0,
            "max_official_api_usd_per_month": 5.0,
        },
        "pit24_benchmark": {
            "outcome_status": "LIVE_24_PASS",
            "selected_model": "gpt-6-luna",
            "scenarios_total": 24,
            "scenarios_ok": 24,
            "json_schema_valid_rate_of_24_pct": 100.0,
            "regime_agreement_rate_of_ok_pct": 100.0,
            "latency_ms_ok": {"p50_ms": 3708.25, "p95_ms": 6287.86},
        },
        "ai_architecture_benchmark_6criteria": {
            "recommended_hybrid_stack": {
                "execution_path_filter": "MT5 ONNX / Pure-MQL5 v1.04-ML",
                "pre_session_macro_advisory": "Official API <= 5 USD/mo",
                "offline_degraded_fallback": "Local Ollama RTX 2070S",
            }
        },
    }


def _assert_briefing_hygiene(md_path: Path, json_path: Path) -> tuple[str, dict[str, Any]]:
    md_bytes = md_path.read_bytes()
    json_bytes = json_path.read_bytes()
    _check(not md_bytes.startswith(b"\xef\xbb\xbf"), "Markdown output contains UTF-8 BOM")
    _check(not json_bytes.startswith(b"\xef\xbb\xbf"), "JSON output contains UTF-8 BOM")
    _check(b"\r\n" not in md_bytes, "Markdown output contains CRLF (must be LF-only)")
    _check(b"\r\n" not in json_bytes, "JSON output contains CRLF (must be LF-only)")

    md_text = md_bytes.decode("utf-8")
    data = json.loads(json_bytes.decode("utf-8"))

    _check("$" not in md_text, "Bare '$' detected in generated morning briefing Markdown!")
    for pat in _G12_PATTERNS:
        _check(pat.search(md_text) is None, f"G12 prop-firm support nudge leaked: {pat.pattern!r}")
    _check(data.get("order_send_capable") is False, "order_send_capable must be False")
    _check(data.get("order_send_count") == 0, "order_send_count must be 0")
    _check(data.get("spend_vnd") == 0, "spend_vnd must be 0")
    _check(data.get("holdout_rows_analysed") == 0, "holdout_rows_analysed must be 0")
    return md_text, data


def _scan_subprocess_creationflags(roots: tuple[Path, ...]) -> tuple[int, int, list[str]]:
    """AST-scan all `.py` files under `roots` for subprocess spawn calls missing `creationflags`."""
    files_scanned = 0
    calls_scanned = 0
    violations: list[str] = []

    for root in roots:
        _check(root.is_dir(), f"Missing scan root: {root}")
        for py_path in sorted(root.rglob("*.py")):
            if "__pycache__" in py_path.parts:
                continue
            files_scanned += 1
            tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))

            subprocess_aliases: set[str] = {"subprocess"}
            direct_spawn_names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "subprocess":
                            subprocess_aliases.add(alias.asname or "subprocess")
                elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                    for alias in node.names:
                        if alias.name in _SUBPROCESS_CALL_ATTRS:
                            direct_spawn_names.add(alias.asname or alias.name)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                call_name: str | None = None
                if (
                    isinstance(fn, ast.Attribute)
                    and isinstance(fn.value, ast.Name)
                    and fn.value.id in subprocess_aliases
                    and fn.attr in _SUBPROCESS_CALL_ATTRS
                ):
                    call_name = f"{fn.value.id}.{fn.attr}"
                elif isinstance(fn, ast.Name) and fn.id in direct_spawn_names:
                    call_name = fn.id

                if call_name is not None:
                    calls_scanned += 1
                    has_cf = any(kw.arg == "creationflags" for kw in node.keywords)
                    if not has_cf:
                        rel = py_path.relative_to(REPO_ROOT).as_posix()
                        violations.append(f"{rel}:{node.lineno} ({call_name})")

    return files_scanned, calls_scanned, violations


# ---------------------------------------------------------------------------
# 1. All 4 Wave 4 Feeds Render Cleanly in ONE Unified Briefing
# ---------------------------------------------------------------------------


def test_01_all_4_wave4_sections_render_cleanly_from_fixtures(tmp_path: Path) -> None:
    """Verify Sections A/B/C + 4 Inside-Out Tiers wire cleanly from synthetic offline fixtures."""
    _write_json(tmp_path / mb.FLEET_LEDGER_LIVE_REL, _build_fixture_fleet_ledger(ledger_id="live-prod-fleet"))
    _write_json(tmp_path / mb.FLEET_LEDGER_SAMPLE_REL, _build_fixture_fleet_ledger(ledger_id="sample-ignored"))
    _write_json(tmp_path / mb.OWNBOOK_SHADOW_SUMMARY_REL, _build_fixture_ownbook())
    _write_json(
        tmp_path / mb.AI_MODEL_RADAR_REL,
        _build_fixture_ai_radar(
            price_changes=[
                {
                    "id": "deepseek/deepseek-v4.1-flash",
                    "direction": "PRICE_DROP",
                    "monthly_delta_pct": -18.5,
                    "curr_monthly_usd": 0.026,
                }
            ]
        ),
    )
    _write_json(tmp_path / mb.PROSPECTIVE_SHADOW_LEDGER_REL, _build_fixture_prospective_ledger())
    _write_json(tmp_path / mb.AI_PIT24_RUBRIC_REL, _build_fixture_pit24_rubric())

    out_json = tmp_path / "out/morning_briefing.json"
    out_md = tmp_path / "out/morning_briefing.md"
    payload = mb.build_morning_briefing(
        root=tmp_path,
        out_json=out_json,
        out_md=out_md,
        offline=True,
        dry_run=True,
        now_utc=_FIXED_NOW,
    )

    md_text, disk_data = _assert_briefing_hygiene(out_md, out_json)
    _check(payload["schema"] == "naqex-morning-briefing-v1", "Legacy schema version must be preserved")
    _check(disk_data["overall_status"] == "DRY_RUN_READY", f"Unexpected overall_status: {disk_data['overall_status']}")

    # Section A — Tier 1/4 Prop Fleet (prefers live fleet_ledger.json over sample)
    pf = disk_data["prop_fleet"]
    _check(pf["present"] is True and pf["source_mode"] == "LIVE_LEDGER", f"Expected LIVE_LEDGER, got {pf}")
    _check(pf["ledger_id"] == "live-prod-fleet", "Live ledger must override sample fallback")
    _check(pf["active_challenges_count"] == 1, f"Expected 1 active challenge, got {pf['active_challenges_count']}")
    _check(pf["active_funded_count"] == 1, f"Expected 1 active funded, got {pf['active_funded_count']}")
    _check(pf["ftmo_committed_funded_usd"] == 10_000.0, f"Unexpected FTMO funded: {pf['ftmo_committed_funded_usd']}")
    _check(pf["ftmo_funded_cap_usd"] == 400_000.0, "FTMO cap must be 400,000 USD")
    _check(pf["ftmo_cap_utilization_pct"] == 2.5, f"Expected 2.5% util, got {pf['ftmo_cap_utilization_pct']}")
    _check(pf["active_e1_to_e6_alerts"] == [], f"Expected 0 E1..E6 alerts, got {pf['active_e1_to_e6_alerts']}")
    _check(len(pf["inactivity_countdown"]) == 2, "Expected 2 live accounts in inactivity countdown")
    _check(pf["inactivity_countdown"][0]["days_to_lock_30d"] == 26.0, "Expected 26.0d left to 30d lock")

    # Section B — Tier 3 Own-Book Shadow (OPS-4)
    ob = disk_data["ownbook_shadow"]
    _check(ob["present"] is True and ob["traffic_light"] == "GREEN", f"Expected GREEN ownbook, got {ob}")
    _check(ob["cex_exposure_pct"] == 24.5 and ob["cex_cap_compliant"] is True, "Expected CEX 24.5% <= 25%")
    _check(ob["annualized_funding_rate_pct"] == 8.4 and ob["funding_compression_active"] is False, "Bad funding")

    # Section C — Tier 4 AI Radar & Macro Supervisor
    ai = disk_data["ai_radar_supervisor"]
    _check(ai["present"] is True and ai["budget_compliant"] is True, f"Expected compliant AI feed, got {ai}")
    _check(ai["monthly_api_budget_cap_usd"] == 5.0, "Expected 5.00 USD monthly cap")
    _check(ai["radar"]["top_budget_supervisor"]["id"] == "qwen/qwen3.7-flash", "Unexpected top budget supervisor")
    _check(ai["radar"]["price_delta"]["has_alert"] is True, "Expected price_delta alert on PRICE_DROP")
    _check(ai["prospective_shadow"]["commitments_count"] == 3, "Expected 3 shadow commitments")
    _check(ai["prospective_shadow"]["first_live_session_date"] == "2026-11-30", "Expected 2026-11-30 anchor")
    _check(ai["pit24_and_rubric"]["scenarios_ok"] == 24, "Expected 24/24 PIT-24 scenarios")

    # Unified 4-tier Inside-Out table + all Markdown anchors present
    tiers = disk_data["wave4_inside_out_tiers"]
    _check(len(tiers) == 4, f"Expected 4 Inside-Out tiers, got {list(tiers.keys())}")
    for anchor in (
        "## 5. Tổng Quan 4 Tầng Inside-Out",
        "### 5A. Tầng 1/4 — Đội Tài Khoản Prop",
        "### 5B. Tầng 3 — Own-Book Shadow",
        "### 5C. Tầng 4 — AI Model Radar & Macro Supervisor",
        "400,000 USD",
        "21/27/30",
        "FUNDING_COMPRESSION_ALERT",
        "qwen/qwen3.7-flash",
        "5.00 USD/tháng",
        "2026-11-30",
        "LIVE_24_PASS",
        "deepseek/deepseek-v4.1-flash",
    ):
        _check(anchor in md_text, f"Missing expected unified briefing Markdown anchor: {anchor!r}")

    # Test Own-Book AMBER FUNDING_COMPRESSION_ALERT (< 3%) & RED CEX > 25% escalation
    _write_json(
        tmp_path / mb.OWNBOOK_SHADOW_SUMMARY_REL,
        _build_fixture_ownbook(
            traffic_light="AMBER",
            cex_exposure_pct=10.0,
            funding_pct=1.8,
            compression_active=True,
            active_alerts=["FUNDING_COMPRESSION_ALERT"],
        ),
    )
    ob_amber = mb.collect_ownbook_shadow_summary(root=tmp_path)
    _check(ob_amber["traffic_light"] == "AMBER", f"Expected AMBER, got {ob_amber}")
    _check(ob_amber["funding_compression_active"] is True, "Expected funding_compression_active=True")
    _check("FUNDING_COMPRESSION_ALERT" in ob_amber["active_alerts"], "Missing FUNDING_COMPRESSION_ALERT")

    _write_json(
        tmp_path / mb.OWNBOOK_SHADOW_SUMMARY_REL,
        _build_fixture_ownbook(traffic_light="GREEN", cex_exposure_pct=27.5, funding_pct=7.0),
    )
    ob_red = mb.collect_ownbook_shadow_summary(root=tmp_path)
    _check(
        ob_red["traffic_light"] == "RED" and ob_red["cex_cap_compliant"] is False,
        f"CEX > 25% must force RED: {ob_red}",
    )
    _check("CEX_CAP_25PCT_BREACH" in ob_red["active_alerts"], "Missing CEX_CAP_25PCT_BREACH")

    # Test AI monthly budget > 5.00 USD fail-closed alert
    _write_json(tmp_path / mb.AI_MODEL_RADAR_REL, _build_fixture_ai_radar(top_monthly_usd=6.25))
    ai_over = mb.collect_ai_radar_and_supervisor_summary(root=tmp_path)
    _check(ai_over["budget_compliant"] is False, "Monthly USD > 5.00 must fail budget compliance")
    _check("AI_MONTHLY_API_BUDGET_CAP_5USD_EXCEEDED" in ai_over["alerts"], "Missing 5 USD cap breach alert")


# ---------------------------------------------------------------------------
# 2. Prop Fleet Fallback, 400K Cap, E1..E6 Alerts & 21/27/30d Inactivity
# ---------------------------------------------------------------------------


def test_02_prop_fleet_sample_fallback_e1_to_e6_alerts_and_inactivity(tmp_path: Path) -> None:
    """Verify sample_fleet_ledger fallback + E1..E6 blocking/warning alerts + 21/27/30d inactivity countdown."""
    # 2a. Fallback to sample_fleet_ledger.json when fleet_ledger.json is absent
    _write_json(tmp_path / mb.FLEET_LEDGER_SAMPLE_REL, _build_fixture_fleet_ledger(ledger_id="sample-fallback-only"))
    pf_sample = mb.collect_prop_fleet_summary(root=tmp_path, now_utc=_FIXED_NOW)
    _check(pf_sample["present"] is True and pf_sample["source_mode"] == "SAMPLE_FALLBACK", f"Bad fallback: {pf_sample}")
    _check(pf_sample["ledger_id"] == "sample-fallback-only", "Expected sample_fleet_ledger.json")
    _check(
        pf_sample["status"] == "GREEN_READY",
        f"Clean sample ledger should be GREEN_READY, got {pf_sample['status']}",
    )

    # 2b. Trigger E1, E2, E3, E4 (>400K), E5 (duplicate magic), E6 (21d/27d/30d + preset SHA drift)
    sha_ok = _sha("OK-PRESET")
    sha_bad = _sha("DRIFT-PRESET")
    stressed_accounts = [
        {
            "account_id": "FTMO-F1",
            "firm_id": "ftmo",
            "capital_usd": 250_000.0,
            "base_capital_usd": 250_000.0,
            "state": "S5_FUNDED_ACTIVE",
            "preset_mode": "FUNDED_1X",
            "preset_sha256": sha_bad,
            "expected_preset_sha256": sha_ok,
            "ops4_traffic_light": "AMBER",
            "open_positions": 0,
            "daily_dd_pct": 1.0,
            "static_dd_pct": 4.2,
            "days_since_last_trade": 30.5,
            "magic_range": [1000, 1099],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\f1",
        },
        {
            "account_id": "FTMO-F2",
            "firm_id": "ftmo",
            "capital_usd": 200_000.0,
            "base_capital_usd": 200_000.0,
            "state": "S5_FUNDED_ACTIVE",
            "preset_mode": "FUNDED_1X",
            "preset_sha256": sha_ok,
            "expected_preset_sha256": sha_ok,
            "ops4_traffic_light": "GREEN",
            "open_positions": 0,
            "daily_dd_pct": 0.2,
            "static_dd_pct": 0.5,
            "days_since_last_trade": 27.5,
            "magic_range": [1050, 1150],  # overlaps FTMO-F1 -> E5!
            "mt5_portable_dir": "C:\\Naqex\\mt5\\f2",
        },
        {
            "account_id": "THE5ERS-C1",
            "firm_id": "the5ers",
            "capital_usd": 5_000.0,
            "state": "S1_CHALLENGE_P1",
            "preset_mode": "EVAL_P1_SPRINT_4_5X",
            "preset_sha256": sha_ok,
            "expected_preset_sha256": sha_ok,
            "ops4_traffic_light": "GREEN",
            "open_positions": 0,
            "daily_dd_pct": 0.0,
            "static_dd_pct": 0.0,
            "days_since_last_trade": 22.0,
            "magic_range": [2000, 2099],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\c1",
        },
        {
            "account_id": "FTMO-BREACH-01",
            "firm_id": "ftmo",
            "capital_usd": 10_000.0,
            "state": "E3_FUNDED_BREACH_POSTMORTEM",
            "last_transition_utc": "2026-11-20T12:00:00Z",
        },
    ]
    stressed_transitions = [
        {"account_id": "EVAL-FAIL-1", "to_state": "E1_EVAL_FAIL_COOLDOWN", "utc_ts": "2026-11-10T10:00:00Z"},
        {"account_id": "EVAL-FAIL-2", "to_state": "E1_EVAL_FAIL_COOLDOWN", "utc_ts": "2026-11-22T10:00:00Z"},
        {"account_id": "FTMO-BREACH-01", "to_state": "E3_FUNDED_BREACH_POSTMORTEM", "utc_ts": "2026-11-20T12:00:00Z"},
    ]
    _write_json(
        tmp_path / mb.FLEET_LEDGER_LIVE_REL,
        _build_fixture_fleet_ledger(
            ledger_id="all-6-guards-stressed",
            accounts=stressed_accounts,
            transitions=stressed_transitions,
        ),
    )

    pf_stress = mb.collect_prop_fleet_summary(root=tmp_path, now_utc=_FIXED_NOW)
    _check(pf_stress["status"] == "BLOCK_ATTENTION", f"Expected BLOCK_ATTENTION, got {pf_stress['status']}")
    _check(pf_stress["ftmo_committed_funded_usd"] == 450_000.0, "Expected 450K committed FTMO funded")
    _check(
        pf_stress["fleet_scale_factor"] == 0.5,
        f"Expected 0.5x scale under Amber DD, got {pf_stress['fleet_scale_factor']}",
    )

    expected_blocking = {
        "E1_EVAL_FAIL_COOLDOWN",
        "E2_FUNDED_DD_FREEZE",
        "E3_FUNDED_BREACH_POSTMORTEM",
        "E4_CAP_OR_VPS_OVERFLOW",
        "E5_CROSS_ACCOUNT_OPPOSITE_HEDGE",
        "E6_INACTIVITY_OR_FEED_STALE_LOCK",
    }
    _check(
        expected_blocking.issubset(set(pf_stress["blocking_guards"])),
        f"Expected all 6 E1..E6 blocking guards, got {pf_stress['blocking_guards']}",
    )
    alerts = set(pf_stress["active_e1_to_e6_alerts"])
    for code in (
        "E1_EVAL_FAIL_COOLDOWN_BLOCKED",
        "E2_FUNDED_DD_AMBER_FREEZE",
        "E3_FUNDED_BREACH_UNRESOLVED_POSTMORTEM",
        "E4_FTMO_400K_FUNDED_CAP_EXCEEDED",
        "E6_INACTIVITY_30D_LOCK",
        "PRESET_SHA256_DRIFT",
    ):
        _check(code in alerts, f"Missing expected alert code {code!r} in {sorted(alerts)}")

    inact_by_id = {row["account_id"]: row for row in pf_stress["inactivity_countdown"]}
    _check(
        inact_by_id["FTMO-F1"]["level"] == "LOCK_30D" and inact_by_id["FTMO-F1"]["days_to_lock_30d"] == 0.0,
        "Bad 30d inactivity countdown",
    )
    _check(
        inact_by_id["FTMO-F2"]["level"] == "URGENT_27D" and inact_by_id["FTMO-F2"]["days_to_lock_30d"] == 2.5,
        "Bad 27d inactivity countdown",
    )
    _check(
        inact_by_id["THE5ERS-C1"]["level"] == "WARNING_21D"
        and inact_by_id["THE5ERS-C1"]["days_to_lock_30d"] == 8.0,
        "Bad 21d inactivity countdown",
    )

    # 2c. Fail-closed safety tamper detection
    tampered = _build_fixture_fleet_ledger()
    tampered["order_send_capable"] = True
    _write_json(tmp_path / mb.FLEET_LEDGER_LIVE_REL, tampered)
    pf_tamper = mb.collect_prop_fleet_summary(root=tmp_path, now_utc=_FIXED_NOW)
    _check(pf_tamper["status"] == "SAFETY_TAMPER_BLOCKED", f"Tampered ledger must fail closed: {pf_tamper}")


# ---------------------------------------------------------------------------
# 3. Graceful Degradation When .runtime/offensive4/ Is Missing or Corrupt (CI-Safe)
# ---------------------------------------------------------------------------


def test_03_graceful_degradation_missing_and_corrupt_offensive4_ci_safe(tmp_path: Path) -> None:
    """Empty CI workspace with NO `.runtime/offensive4/` MUST exit 0 and emit clean NOT_INITIALIZED."""
    out_json = tmp_path / ".runtime/automation/morning_briefing_latest.json"
    out_md = tmp_path / ".runtime/automation/morning_briefing_latest.md"

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mb.main(
            [
                "--root",
                str(tmp_path),
                "--out-json",
                str(out_json),
                "--out-md",
                str(out_md),
                "--offline-dry-run",
                "--now-utc",
                "2026-11-28T00:30:00Z",
                "--json",
            ]
        )
    _check(rc == 0, f"Expected rc=0 on empty CI root, got {rc}")
    stdout_payload = json.loads(buf.getvalue())
    md_text, disk_data = _assert_briefing_hygiene(out_md, out_json)

    _check(
        stdout_payload["overall_status"] == "DRY_RUN_READY",
        f"Unexpected CI status: {stdout_payload['overall_status']}",
    )
    _check(disk_data["prop_fleet"]["status"] == "NOT_INITIALIZED", "Missing fleet ledger must be NOT_INITIALIZED")
    _check(disk_data["ownbook_shadow"]["status"] == "NOT_INITIALIZED", "Missing ownbook must be NOT_INITIALIZED")
    _check(disk_data["ai_radar_supervisor"]["status"] == "NOT_INITIALIZED", "Missing AI feeds must be NOT_INITIALIZED")
    _check("NOT_INITIALIZED" in md_text, "Markdown must state NOT_INITIALIZED gracefully")

    # Backward compatibility: render_morning_briefing_md on a legacy v1 payload lacking Wave 4 keys
    legacy_payload = {
        k: v
        for k, v in disk_data.items()
        if k not in ("prop_fleet", "ownbook_shadow", "ai_radar_supervisor", "wave4_inside_out_tiers")
    }
    legacy_md = mb.render_morning_briefing_md(legacy_payload, root=tmp_path)
    _check("$" not in legacy_md and "NOT_INITIALIZED" in legacy_md, "Legacy v1 payload render must succeed cleanly")

    # Corrupt JSON files under .runtime/offensive4/ MUST degrade gracefully without crashing
    for rel in (
        mb.FLEET_LEDGER_LIVE_REL,
        mb.OWNBOOK_SHADOW_SUMMARY_REL,
        mb.AI_MODEL_RADAR_REL,
        mb.PROSPECTIVE_SHADOW_LEDGER_REL,
        mb.AI_PIT24_RUBRIC_REL,
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{corrupt-json", encoding="utf-8")

    corrupt_payload = mb.build_morning_briefing(
        root=tmp_path,
        out_json=out_json,
        out_md=out_md,
        offline=True,
        dry_run=True,
        now_utc=_FIXED_NOW,
    )
    _assert_briefing_hygiene(out_md, out_json)
    _check(corrupt_payload["prop_fleet"]["status"] == "INVALID_JSON", "Expected INVALID_JSON for corrupt fleet")
    _check(corrupt_payload["ownbook_shadow"]["status"] == "INVALID_JSON", "Expected INVALID_JSON for corrupt ownbook")
    _check(corrupt_payload["ai_radar_supervisor"]["radar"]["status"] == "INVALID_JSON", "Expected INVALID_JSON radar")


# ---------------------------------------------------------------------------
# 4. Formatting Guards: 0 Bare '$', 0 G12 Nudges, 0 OPSEC Leaks, 0 Bare Asserts
# ---------------------------------------------------------------------------


def test_04_dollar_g12_opsec_guards_and_zero_bare_asserts(tmp_path: Path) -> None:
    """Verify `$` scrubbing, fail-closed G12 guard, OPSEC scrubbing, and zero bare asserts."""
    # Inject bare `$` and synthetic secret/IP/path into AI radar model name
    radar_dirty = _build_fixture_ai_radar()
    win_path = "C:" + "\\Us" + "ers\\" + "alice_demo\\secret.txt"
    priv_ip = "192.168." + "55.77"
    radar_dirty["leaderboards"]["budget_macro_supervisor_monthly_usd"][0]["id"] = (
        f"vendor/model-$99-{priv_ip}-{win_path}"
    )
    _write_json(tmp_path / mb.AI_MODEL_RADAR_REL, radar_dirty)

    out_json = tmp_path / "dirty_briefing.json"
    out_md = tmp_path / "dirty_briefing.md"
    mb.build_morning_briefing(
        root=tmp_path,
        out_json=out_json,
        out_md=out_md,
        offline=True,
        dry_run=True,
        now_utc=_FIXED_NOW,
    )
    md_text, _ = _assert_briefing_hygiene(out_md, out_json)
    raw_json_txt = out_json.read_text(encoding="utf-8")
    _check(priv_ip not in md_text and priv_ip not in raw_json_txt, "Private LAN IP leaked!")
    _check("alice_demo" not in md_text and "alice_demo" not in raw_json_txt, "Windows user path leaked!")

    # Verify fail-closed G12 guard catches a prohibited prop-firm support nudge
    bad_payload = json.loads(raw_json_txt)
    bad_payload["milestones_6"][0]["action_vi"] = "Vui lòng liên hệ support FTMO qua live chat ngay."
    g12_caught = False
    try:
        mb.render_morning_briefing_md(bad_payload, root=tmp_path)
    except ValueError as exc:
        g12_caught = "G12 guard failed" in str(exc)
    _check(g12_caught, "Fail-closed G12 guard did not reject prop-firm support nudge!")

    # Zero bare `assert` statements in morning_briefing.py AND this test file (`-O` safety)
    for py_file in (REPO_ROOT / "tooling/automation/morning_briefing.py", Path(__file__).resolve()):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        assert_lines = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        _check(not assert_lines, f"Bare assert found in {py_file.name} at lines {assert_lines}")


# ---------------------------------------------------------------------------
# 5. AST Zero-Popup Scan Across ALL tooling/automation/ & ops_cloud/ + Runtime Check
# ---------------------------------------------------------------------------


def test_05_ast_zero_missing_creationflags_across_automation_and_ops_cloud(tmp_path: Path) -> None:
    """AST scan MUST prove 0 subprocess calls missing `creationflags` across ALL automation & ops_cloud."""
    scan_roots = (
        REPO_ROOT / "tooling" / "automation",
        REPO_ROOT / "tooling" / "ai-engines" / "ops_cloud",
    )
    files_scanned, calls_scanned, violations = _scan_subprocess_creationflags(scan_roots)
    _check(files_scanned >= 15, f"Expected >= 15 Python files scanned, got {files_scanned}")
    _check(calls_scanned >= 30, f"Expected >= 30 subprocess calls scanned, got {calls_scanned}")
    _check(not violations, f"Subprocess calls missing creationflags: {violations}")

    # Confirm morning_briefing.py defines `_NO_WINDOW_FLAGS` and passes it in `subprocess.run`
    expected_cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    _check(hasattr(mb, "_NO_WINDOW_FLAGS"), "morning_briefing must define _NO_WINDOW_FLAGS")
    _check(mb._NO_WINDOW_FLAGS == expected_cf, f"_NO_WINDOW_FLAGS mismatch: {mb._NO_WINDOW_FLAGS} != {expected_cf}")

    fixture_node = tmp_path / "node_fixture.json"
    _write_json(fixture_node, {"overall_status": "HEALTHY", "cutover_verdict": "READY"})

    captured_kwargs: list[dict[str, Any]] = []

    class _FakeProc:
        returncode = 0
        stdout = json.dumps({"overall_status": "HEALTHY", "cutover_verdict": "READY"})
        stderr = ""

    def _fake_run(*_args: Any, **kwargs: Any) -> _FakeProc:
        captured_kwargs.append(dict(kwargs))
        return _FakeProc()

    with patch.object(mb.subprocess, "run", side_effect=_fake_run):
        nd = mb.collect_node_weekly_digest(root=REPO_ROOT, fixture_path=fixture_node)
    _check(nd["overall_status"] == "HEALTHY", f"Unexpected node_digest: {nd}")
    _check(len(captured_kwargs) == 1, f"Expected 1 subprocess.run call, got {len(captured_kwargs)}")
    _check(
        captured_kwargs[0].get("creationflags") == expected_cf,
        f"Expected creationflags={expected_cf}, got {captured_kwargs[0].get('creationflags')!r}",
    )


# ---------------------------------------------------------------------------
# 6. Live Workspace Wave 4 Feeds & Real `pythonw.exe --offline-dry-run` Smoke
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_06_live_workspace_wave4_feeds_and_pythonw_offline_dry_run(tmp_path: Path) -> None:
    """Verify real `.runtime/offensive4/` feeds + live `pythonw.exe --offline-dry-run` exit 0 with 0 popup."""
    pythonw = REPO_ROOT / ".runtime/quant-audit-v24/Scripts/pythonw.exe"
    _check(pythonw.is_file(), f"Missing bundled pythonw.exe at {pythonw}")

    out_json = tmp_path / "pythonw_briefing.json"
    out_md = tmp_path / "pythonw_briefing.md"
    cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    proc = subprocess.run(
        [
            str(pythonw),
            str(REPO_ROOT / "tooling/automation/morning_briefing.py"),
            "--offline-dry-run",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        creationflags=cf,
        check=False,
    )
    _check(proc.returncode == 0, f"pythonw.exe exited rc={proc.returncode}, stderr={proc.stderr!r}")
    _check(out_json.is_file() and out_md.is_file(), "pythonw.exe did not produce JSON & Markdown outputs")

    md_text, data = _assert_briefing_hygiene(out_md, out_json)
    _check(data["prop_fleet"]["present"] is True, "Live workspace prop_fleet must be present")
    _check(data["ownbook_shadow"]["present"] is True, "Live workspace ownbook_shadow must be present")
    _check(data["ai_radar_supervisor"]["present"] is True, "Live workspace ai_radar_supervisor must be present")
    _check(data["ai_radar_supervisor"]["radar"]["present"] is True, "Live workspace AI radar must be present")
    _check(
        data["ai_radar_supervisor"]["prospective_shadow"]["present"] is True,
        "Live prospective shadow must be present",
    )
    _check(data["ai_radar_supervisor"]["pit24_and_rubric"]["present"] is True, "Live PIT-24 rubric must be present")
    _check(data["ownbook_shadow"]["cex_cap_compliant"] is True, "Live Own-Book CEX must be <= 25%")
    _check(data["ai_radar_supervisor"]["budget_compliant"] is True, "Live AI API budget must be <= 5.00 USD")
    _check("400,000 USD" in md_text and "qwen/qwen3.7-flash" in md_text, "Missing live Wave 4 highlights in MD")
