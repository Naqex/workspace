"""Offline CI-safe tests for tooling/automation/strategy_intel_bridge.py.

Verifies:
  1. Strictly 0 bytes written back to the strategy-intel cleanroom (directory entry & mtime/SHA-256 snapshot).
  2. Fail-closed rejection of 2025/2026 & OOS2 holdout leakage (remains active under `python -O`).
  3. Filtering against TOP1-SOLO-QUANT-MASTER-PLAN §3.4 Forbidden List + Grid/Martingale/No-SL.
  4. Graceful `--offline` and `--dry-run` behavior when cleanroom directory is absent (GitHub CI safe).
  5. Mandatory `untrusted_external_data=True`, `order_send_count=0`, `holdout_rows_analysed=0` tagging.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_core.holdout_guard import HoldoutLockError  # noqa: E402

from tooling.automation import strategy_intel_bridge as bridge  # noqa: E402


def _check(condition: bool, message: str = "assertion failed") -> None:
    """Explicit check that remains active even under `python -O`."""
    if not condition:
        raise AssertionError(message)


def _snapshot_tree(root: Path) -> dict[str, tuple[str, int, int, str]]:
    """Capture exact files, dirs, sizes, mtime_ns, and SHA-256 digests to verify 0-byte write-back."""
    snap: dict[str, tuple[str, int, int, str]] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        st = p.stat()
        if p.is_file():
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            snap[rel] = ("file", st.st_size, st.st_mtime_ns, digest)
        else:
            snap[rel] = ("dir", 0, st.st_mtime_ns, "")
    return snap


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _build_fixture_cleanroom(base: Path) -> Path:
    cleanroom = base / "cleanroom"
    handoff = cleanroom / "handoff"
    inbox = cleanroom / "inbox" / "vendor-drop"
    handoff.mkdir(parents=True)
    inbox.mkdir(parents=True)

    _write_json(
        handoff / "sanitized_master_leads.json",
        {
            "export_tier": "CLEANROOM_HOLDOUT_SANITIZED",
            "total_leads": 2,
            "leads": [
                {
                    "lead_id": "LEAD-MASTER-GOLD-D1",
                    "original_id": "SEA003",
                    "source": "stategy-netlify-app",
                    "name": "Turn-of-month gold",
                    "family": "Seasonality",
                    "symbol": "XAUUSD",
                    "timeframe": "D1",
                    "direction": "Long",
                    "rule_description": "Hold overnight across month boundary on XAUUSD D1",
                    "replicability": "REPLICABLE_FROM_PUBLIC",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": ["MISSING_PF_AND_DD_IN_PUBLIC_JSON"],
                    "performance_metrics": {
                        "oos1_2019_2023": {"n": 40, "wr": 55.0, "years_pos": "4/5", "nam_duong": {"2023": True}}
                    },
                },
                {
                    "lead_id": "LEAD-MASTER-GOLD-H1",
                    "original_id": "BRK035",
                    "source": "stategy-netlify-app",
                    "name": "Monday 4h box",
                    "family": "Breakout",
                    "symbol": "XAUUSD",
                    "timeframe": "H1",
                    "direction": "Both",
                    "rule_description": "Intraday Monday range breakout on XAUUSD H1",
                    "replicability": "PARTIAL_CONCEPT_ONLY",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": [],
                    "performance_metrics": {},
                },
            ],
        },
    )

    _write_json(
        handoff / "sanitized_auto_leads.json",
        {
            "export_tier": "CLEANROOM_HOLDOUT_SANITIZED_AUTO_INGEST",
            "total_leads": 6,
            "leads": [
                {
                    "lead_id": "LEAD-AUTO-ETF-TSMOM",
                    "original_id": "AUTO-ETF-01",
                    "source": "public-auto-ingest",
                    "name": "Macro ETF Time-Series Momentum",
                    "family": "Macro ETF Trend",
                    "symbol": "SPY/TLT/GLD",
                    "timeframe": "D1",
                    "direction": "Both",
                    "rule_description": (
                        "Liquid ETF trend with hard 2.0x ATR stop, zero overnight CFD swap, zero grid, zero martingale."
                    ),
                    "replicability": "REPLICABLE_FROM_PUBLIC",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": ["AUTO_INGESTED_UNTRUSTED_PUBLIC_SPEC"],
                    "performance_metrics": {},
                },
                {
                    "lead_id": "LEAD-AUTO-CRYPTO-D1",
                    "original_id": "AUTO-CRYP-D1",
                    "source": "public-auto-ingest",
                    "name": "Causal Crypto Spot Daily Breakout",
                    "family": "Crypto Spot Daily Trend",
                    "symbol": "BTCUSDT/ETHUSDT",
                    "timeframe": "D1",
                    "direction": "Long",
                    "rule_description": "Daily Donchian breakout with mandatory hard 2.5x ATR stop, zero martingale.",
                    "replicability": "REPLICABLE_FROM_PUBLIC",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": ["AUTO_INGESTED_UNTRUSTED_PUBLIC_SPEC"],
                    "performance_metrics": {},
                },
                {
                    "lead_id": "LEAD-AUTO-CRYPTO-M15",
                    "original_id": "AUTO-CRYP-M15",
                    "source": "public-auto-ingest",
                    "name": "Crypto Taker Scalper",
                    "family": "Crypto Spot",
                    "symbol": "BTCUSDT",
                    "timeframe": "M15",
                    "direction": "Both",
                    "rule_description": "Fast M15 taker breakout with hard stop.",
                    "replicability": "PARTIAL_CONCEPT_ONLY",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": [],
                    "performance_metrics": {},
                },
                {
                    "lead_id": "LEAD-AUTO-TOXIC-GRID",
                    "original_id": "AUTO-TOX-01",
                    "source": "public-auto-ingest",
                    "name": "Sneaky Recovery Grid",
                    "family": "Macro ETF",
                    "symbol": "SPY",
                    "timeframe": "D1",
                    "direction": "Long",
                    "rule_description": "Uses grid trading with 1.5x lot multiplier martingale.",
                    "replicability": "PARTIAL_CONCEPT_ONLY",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": [],
                    "performance_metrics": {},
                },
                {
                    "lead_id": "LEAD-AUTO-TOXIC-NOSL",
                    "original_id": "AUTO-TOX-02",
                    "source": "public-auto-ingest",
                    "name": "No-SL Trend",
                    "family": "Macro ETF",
                    "symbol": "SPY",
                    "timeframe": "D1",
                    "direction": "Long",
                    "rule_description": "Holds position without stop loss until signal flips.",
                    "replicability": "PARTIAL_CONCEPT_ONLY",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": [],
                    "performance_metrics": {},
                },
                {
                    "lead_id": "LEAD-AUTO-ML-UNPROVEN",
                    "original_id": "AUTO-ML-01",
                    "source": "public-auto-ingest",
                    "name": "XGBoost Meta Filter",
                    "family": "Macro ETF",
                    "symbol": "SPY/TLT",
                    "timeframe": "D1",
                    "direction": "Long",
                    "rule_description": "Applies XGBoost ML filter to white-box entries (Brier Skill <= 0).",
                    "replicability": "PARTIAL_CONCEPT_ONLY",
                    "evidence_tier": "SOURCE_CLAIM_ONLY",
                    "data_quality_flags": [],
                    "performance_metrics": {},
                },
            ],
        },
    )

    # Sample inbox files: 1 quarantined binary + 1 flagged .set + 1 clean open-source .py
    (inbox / "opaque_bot.ex5").write_bytes(b"EX5_DUMMY_BINARY")
    (inbox / "martingale_preset.set").write_text("LotMultiplier=2.0\nGridStep=50\n", encoding="utf-8")
    (inbox / "clean_idea.py").write_text("# pure reference idea\n", encoding="utf-8")
    return cleanroom


def test_zero_byte_writeback_and_s34_filtering(tmp_path: Path) -> None:
    cleanroom = _build_fixture_cleanroom(tmp_path)
    out_file = tmp_path / "out" / "strategy_intel_handoff_latest.json"

    before_snap = _snapshot_tree(cleanroom)
    before_root_mtime = cleanroom.stat().st_mtime_ns

    rc = bridge.main(["--intel-dir", str(cleanroom), "--out", str(out_file)])
    _check(rc == 0, f"expected rc=0, got {rc}")

    after_snap = _snapshot_tree(cleanroom)
    after_root_mtime = cleanroom.stat().st_mtime_ns
    _check(after_snap == before_snap, "Bridge MUST write 0 bytes back into strategy-intel cleanroom!")
    _check(after_root_mtime == before_root_mtime, "Cleanroom root directory mtime must not change!")
    _check(not (cleanroom / "inbox-triage-report.json").exists(), "Must not write inbox-triage-report.json")
    _check(not (cleanroom / "inbox-triage-report.md").exists(), "Must not write inbox-triage-report.md")

    data = json.loads(out_file.read_text(encoding="utf-8"))
    _check(data["status"] == "OK", f"unexpected status: {data['status']}")
    _check(data["untrusted_external_data"] is True, "untrusted_external_data must be True")
    _check(data["order_send_count"] == 0, "order_send_count must be 0")
    _check(data["spend_vnd"] == 0, "spend_vnd must be 0")
    _check(data["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(data["writes_back_to_cleanroom"] == 0, "writes_back_to_cleanroom must be 0")

    eligible_ids = {item["lead_id"] for item in data["eligible_dev_candidates"]}
    _check(eligible_ids == {"LEAD-AUTO-ETF-TSMOM", "LEAD-AUTO-CRYPTO-D1"}, f"unexpected eligible: {eligible_ids}")
    for item in data["eligible_dev_candidates"]:
        _check(item["untrusted_external_data"] is True, "lead must carry untrusted_external_data=True")
        _check(item["holdout_rows_analysed"] == 0, "lead must carry holdout_rows_analysed=0")

    filtered_map = {item["lead_id"]: set(item["filter_reasons"]) for item in data["filtered_out"]}
    _check("FORBIDDEN_S34_CFD_OVERNIGHT_NEG_SWAP" in filtered_map["LEAD-MASTER-GOLD-D1"], "missing gold D1 swap rule")
    _check("FORBIDDEN_S34_CFD_INTRADAY_SATURATED" in filtered_map["LEAD-MASTER-GOLD-H1"], "missing intraday CFD rule")
    _check("FORBIDDEN_S34_CRYPTO_SUB_4H_TAKER" in filtered_map["LEAD-AUTO-CRYPTO-M15"], "missing crypto <4H rule")
    _check("FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL" in filtered_map["LEAD-AUTO-TOXIC-GRID"], "missing grid rule")
    _check("FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL" in filtered_map["LEAD-AUTO-TOXIC-NOSL"], "missing no-SL rule")
    _check("FORBIDDEN_S34_ML_FILTER_NO_BRIER_SKILL" in filtered_map["LEAD-AUTO-ML-UNPROVEN"], "missing ML Brier rule")

    _check(data["summary"]["inbox_quarantined_binaries"] == 1, "expected 1 quarantined binary")
    _check(data["summary"]["inbox_set_flagged_anti_prop"] == 1, "expected 1 flagged .set file")
    _check(data["summary"]["inbox_open_source_clean"] == 1, "expected 1 clean open-source file")


@pytest.mark.parametrize(
    "poisoned_lead",
    [
        {"lead_id": "L1", "pnl_2025": 12.3},
        {"lead_id": "L2", "rule_description": "Tested live through 2026-03-15 with great profit"},
        {"lead_id": "L3", "performance_metrics": {"oos2_summary": {"wr": 60.0}}},
        {"lead_id": "L4", "holdout_year": 2025},
        {"lead_id": "L5", "rule_description": "Strong 2026Q1 momentum"},
    ],
)
def test_holdout_2025_2026_leak_rejected_even_under_dash_o(tmp_path: Path, poisoned_lead: dict[str, Any]) -> None:
    cleanroom = tmp_path / "poisoned_cleanroom"
    _write_json(
        cleanroom / "handoff" / "sanitized_auto_leads.json",
        {"export_tier": "TEST", "total_leads": 1, "leads": [poisoned_lead]},
    )
    out_file = tmp_path / "out.json"
    with pytest.raises(HoldoutLockError):
        bridge.sync_strategy_intel(intel_dir=cleanroom, out_path=out_file, offline=True)
    _check(not out_file.exists(), "Fail-closed holdout breach must not emit handoff output file")


def test_missing_cleanroom_graceful_offline_and_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing_dir = tmp_path / "nonexistent_cleanroom"
    out_file = tmp_path / "runtime" / "strategy_intel_handoff_latest.json"

    # Without --offline, missing directory fails closed
    with pytest.raises(FileNotFoundError):
        bridge.sync_strategy_intel(intel_dir=missing_dir, out_path=out_file, offline=False)

    # With --offline --dry-run --json, exits 0 and writes NO file
    rc = bridge.main(["--intel-dir", str(missing_dir), "--out", str(out_file), "--offline", "--dry-run", "--json"])
    _check(rc == 0, f"expected rc=0, got {rc}")
    _check(not out_file.exists(), "--dry-run must not write output file")
    parsed = json.loads(capsys.readouterr().out)
    _check(parsed["status"] == "OFFLINE_CLEANROOM_UNAVAILABLE", f"unexpected status: {parsed['status']}")
    _check(parsed["cleanroom_present"] is False, "cleanroom_present must be False")
    _check(parsed["untrusted_external_data"] is True, "untrusted_external_data must be True")
    _check(parsed["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(parsed["order_send_count"] == 0, "order_send_count must be 0")
    _check(parsed["writes_back_to_cleanroom"] == 0, "writes_back_to_cleanroom must be 0")

    # With --offline (no --dry-run), writes valid JSON receipt
    rc2 = bridge.main(["--intel-dir", str(missing_dir), "--out", str(out_file), "--offline"])
    _check(rc2 == 0, f"expected rc2=0, got {rc2}")
    _check(out_file.is_file(), "offline non-dry-run must emit handoff JSON")
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    _check(saved["status"] == "OFFLINE_CLEANROOM_UNAVAILABLE", "saved status mismatch")


def test_s34_edge_cases_cross_negation_decimal_sl_and_compound_tickers() -> None:
    """Regression suite for cross-category negation bypasses, decimal SL=0.5, compound crypto, and slash FX pairs."""
    # 1. Cross-category & hard-stop negation bypasses MUST still be rejected
    bypass_descriptions = (
        "Uses martingale recovery with a mandatory hard stop.",
        "Opens grid trading layers every 50 points with no martingale.",
        "Doubles the lot on loss (martingale) with zero grid.",
        "Applies strict hard stop while averaging down into losing layers.",
    )
    for desc in bypass_descriptions:
        reasons = bridge.evaluate_lead_against_s34(
            {
                "name": "Disguised ETF Bot",
                "family": "Macro ETF Trend",
                "symbol": "SPY",
                "timeframe": "D1",
                "rule_description": desc,
            }
        )
        _check(
            "FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL" in reasons,
            f"Expected toxic rejection for {desc!r}, got {reasons}",
        )

    # 2. Decimal SL=0.5 ATR / TP=1.5 ATR MUST NOT false-positive as No-SL
    clean_reasons = bridge.evaluate_lead_against_s34(
        {
            "name": "ETF ATR Breakout",
            "family": "Macro ETF Trend",
            "symbol": "SPY/TLT/GLD",
            "timeframe": "D1",
            "rule_description": "Breakout strategy with SL=0.5 ATR and TP=1.5 ATR.",
        }
    )
    _check(clean_reasons == [], f"False positive on decimal SL=0.5: {clean_reasons}")

    # Explicit SL=0.0 MUST still be rejected
    zero_sl_reasons = bridge.evaluate_lead_against_s34(
        {
            "name": "Zero SL ETF",
            "family": "Macro ETF Trend",
            "symbol": "SPY",
            "timeframe": "D1",
            "rule_description": "Trades with SL=0.0 until signal flips.",
        }
    )
    _check("FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL" in zero_sl_reasons, f"Missed SL=0.0: {zero_sl_reasons}")

    # 3. Compound crypto tickers (even without "crypto" in family!) MUST trigger sub-4H taker filter
    for sym, tf in (("BTCUSDT", "M15"), ("ETHUSD", "H1"), ("SOLUSDT", "M5"), ("BTC/USDT", "M30")):
        c_reasons = bridge.evaluate_lead_against_s34(
            {
                "name": "Fast Breakout",
                "family": "Breakout",
                "symbol": sym,
                "timeframe": tf,
                "rule_description": f"{tf} breakout with hard 1.5x ATR stop.",
            }
        )
        _check(
            "FORBIDDEN_S34_CRYPTO_SUB_4H_TAKER" in c_reasons,
            f"Missed compound crypto sub-4H filter for {sym} {tf}: {c_reasons}",
        )

    # 4. Slash-separated FX/metal pairs (XAU/USD D1, EUR/USD H1) MUST trigger CFD rules
    gold_slash = bridge.evaluate_lead_against_s34(
        {
            "name": "Gold Swing",
            "family": "Trend",
            "symbol": "XAU/USD",
            "timeframe": "D1",
            "rule_description": "Hold multi-day overnight on gold.",
        }
    )
    _check("FORBIDDEN_S34_CFD_OVERNIGHT_NEG_SWAP" in gold_slash, f"Missed XAU/USD D1 swap filter: {gold_slash}")

    eur_slash = bridge.evaluate_lead_against_s34(
        {
            "name": "Euro Intraday",
            "family": "Breakout",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "rule_description": "London session breakout with hard stop.",
        }
    )
    _check("FORBIDDEN_S34_CFD_INTRADAY_SATURATED" in eur_slash, f"Missed EUR/USD H1 CFD filter: {eur_slash}")
