"""Focused offline tests for Total Offensive #3 (v3.5) Barrier #2 foundation deliverables.

Covers all 7 t0-ledger deliverables with 0 network/SSH/MT5 calls, OrderSend = 0,
Holdout 2025+ strictly sealed, and full `python -O` safety via `_check(...)`:
  1. `quant_factory/seal_asset_m1.py` (--seal, --merge-fragments, Holdout, <=0 USOIL guard, crossed ticks)
  2. `quant_factory/offensive3/x13_m1_loader.py` (pure NumPy/PyArrow, 0 forbidden tokens, 41 quant_core lock)
  3. `configs/ssot/ftmo_specs_28.json` (28 symbols, 16/28 zero tick_val fixed, Anti-Fake-Swap, Swing leverage)
  4. `configs/offensive3/preregistration_m1200.json` (m200 + m1200 caps, F01..F12, Gate G08 KillCriteria)
  5. `ops_cloud/compute_router.py` (--force-mode-b, --owner-approved-long-run, cache allowlist, M1 incremental sync)
  6. `tooling/automation/strategy_intel_bridge.py` (opt-in --profile offensive3 + §3.4 exemption logging)
  7. `quant_core/tca.py` (28-symbol POINT_SIZES & BENCHMARK_SPREAD_PTS, v1.03 NON_FILL_EVENT_TYPES)
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
OPS_CLOUD_DIR = AI_ENGINES_DIR / "ops_cloud"
for _p in (REPO_ROOT, AI_ENGINES_DIR, OPS_CLOUD_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import compute_router as cr  # noqa: E402
from quant_core import tca  # noqa: E402
from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory import seal_asset_m1 as sam  # noqa: E402
from quant_factory.offensive3 import x13_m1_loader as x13_loader  # noqa: E402
from quant_factory.research_council import KillCriteria  # noqa: E402

from tooling.automation import strategy_intel_bridge as bridge  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit guard immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _write_raw_dev_years(
    raw_dir: Path,
    asset_lower: str,
    *,
    base_price: float = 20.5,
    spread: float = 0.02,
    cross_first_bar: bool = False,
    month: int = 4,
    day: int = 20,
) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for y in range(2018, 2025):
        ts0 = int(datetime(y, month, day, 12, 0, tzinfo=UTC).timestamp()) * 1000
        bid_rows = [
            [ts0, base_price, base_price + 0.10, base_price - 0.10, base_price + 0.05],
            [ts0 + 60000, base_price + 0.05, base_price + 0.15, base_price - 0.05, base_price + 0.10],
        ]
        ask0_o = base_price - 0.01 if cross_first_bar else base_price + spread
        ask_rows = [
            [ts0, ask0_o, base_price + 0.10 + spread, base_price - 0.10 + spread, base_price + 0.05 + spread],
            [
                ts0 + 60000,
                base_price + 0.05 + spread,
                base_price + 0.15 + spread,
                base_price - 0.05 + spread,
                base_price + 0.10 + spread,
            ],
        ]
        (raw_dir / f"{asset_lower}-m1-bid-{y}.json").write_text(json.dumps(bid_rows), encoding="utf-8")
        (raw_dir / f"{asset_lower}-m1-ask-{y}.json").write_text(json.dumps(ask_rows), encoding="utf-8")


def _healthy_x13(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ssh_alias": "naqex-x13",
        "transport": "LAN",
        "probe_ms": 180.0,
        "reachable": True,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "battery_pct": 100,
        "cpu_util_pct": 4.0,
        "free_ram_gb": 12.0,
        "disk_free_gb": 140.0,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": -10.0,
        "forbidden_files": 0,
        "eligible": True,
        "ineligible_reasons": [],
    }
    base.update(overrides)
    return base


def _mode_a_active_dev(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "mode": "MODE_A_OWNER_ACTIVE",
        "idle_sec": 5.0,
        "in_overnight_window_ict": False,
        "gpu_util_pct": 55,
        "fullscreen_busy": True,
        "cpu_util_pct": 20.0,
        "free_ram_gb": 18.0,
        "ntp_offset_ms": -12.0,
        "ntp_ok": True,
    }
    base.update(overrides)
    return base


# ==============================================================================
# 1. seal_asset_m1.py (Generalized Sealer + Fragment Merge + Guards)
# ==============================================================================


def test_zero_bare_asserts_in_new_quant_factory_modules() -> None:
    targets = [
        AI_ENGINES_DIR / "quant_factory" / "seal_asset_m1.py",
        AI_ENGINES_DIR / "quant_factory" / "offensive3" / "__init__.py",
        AI_ENGINES_DIR / "quant_factory" / "offensive3" / "x13_m1_loader.py",
    ]
    for path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(not asserts, f"Bare assert statement(s) found in {path.name} at lines {asserts}")


def test_seal_asset_m1_seal_and_merge_fragments_roundtrip(tmp_path: Path) -> None:
    cache_dir = tmp_path / "hot_cache"
    frags_dir = cache_dir / "_fragments"
    raw_usoil = tmp_path / "raw_usoil"
    raw_eurgbp = tmp_path / "raw_eurgbp"

    _write_raw_dev_years(raw_usoil, "usoil", base_price=20.5, spread=0.03, cross_first_bar=True)
    _write_raw_dev_years(raw_eurgbp, "eurgbp", base_price=0.86500, spread=0.00012, cross_first_bar=False)

    rc1 = sam.main(
        [
            "--seal",
            "--asset",
            "USOIL",
            "--raw-dir",
            str(raw_usoil),
            "--scale",
            "1000",
            "--fragment-out",
            str(frags_dir / "t0_data_ab_usoil.json"),
            "--cache-dir",
            str(cache_dir),
        ]
    )
    rc2 = sam.main(
        [
            "--seal",
            "--asset",
            "EURGBP",
            "--raw-dir",
            str(raw_eurgbp),
            "--scale",
            "100000",
            "--fragment-out",
            str(frags_dir / "t0_data_cd_eurgbp.json"),
            "--cache-dir",
            str(cache_dir),
        ]
    )
    _check(rc1 == 0 and rc2 == 0, "Expected --seal CLI to exit 0 for USOIL and EURGBP")
    _check(not (cache_dir / "manifest.json").exists(), "--seal MUST NEVER edit manifest.json directly")

    frag_oil = json.loads((frags_dir / "t0_data_ab_usoil.json").read_text(encoding="utf-8"))
    _check(frag_oil["holdout_rows"] == 0, "holdout_rows must be 0")
    _check(frag_oil["scale"] == 1000, "USOIL scale must be 1000")
    _check(frag_oil["crossed_clamped_total"] == 7, "Expected 7 clamped crossed bars across 7 years")
    _check(frag_oil["apr_2020_audit"]["min_price"] > 0.0, "Apr-2020 audit min_price must be > 0")

    rc_m = sam.main(["--merge-fragments", str(frags_dir), "--cache-dir", str(cache_dir)])
    _check(rc_m == 0, "--merge-fragments must exit 0")
    man = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))
    _check(man["holdout_rows"] == 0, "Merged manifest holdout_rows must be 0")
    _check(set(man["assets"].keys()) == {"USOIL", "EURGBP"}, f"Unexpected merged assets: {man['assets'].keys()}")
    _check(man["assets"]["USOIL"]["scale"] == 1000 and man["assets"]["EURGBP"]["scale"] == 100000, "Scale mismatch")

    # Verify x13_m1_loader loads the merged parquets cleanly
    ts_oil, q_oil, meta_oil = x13_loader.load_m1_asset("USOIL", cache_dir, verify_sha=True)
    _check(ts_oil.shape == (14,) and q_oil.shape == (14, 8), f"Unexpected USOIL shapes: {ts_oil.shape}, {q_oil.shape}")
    _check(int(ts_oil[-1]) < x13_loader.DEV_CUTOFF_SEC, "USOIL last timestamp must be < 2025-01-01 UTC")
    _check(bool(np.all(q_oil[:, 4:8] >= q_oil[:, 0:4])), "Clamped ask must be >= bid everywhere")
    _check(meta_oil["scale"] == 1000, "Asset metadata scale mismatch")

    ts_5m, q_5m = x13_loader.resample_m1_to_tf(ts_oil, q_oil, 300)
    _check(ts_5m.size == 7 and q_5m.shape == (7, 8), f"Unexpected 5m resample shape: {ts_5m.shape}, {q_5m.shape}")


def test_seal_asset_m1_fails_closed_on_usoil_nonpositive_and_holdout_2025(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    raw_dir = tmp_path / "raw_usoil"
    _write_raw_dev_years(raw_dir, "usoil", base_price=20.0)

    # Inject Apr 2020 negative/zero WTI anomaly
    ts_apr = int(datetime(2020, 4, 20, 18, 0, tzinfo=UTC).timestamp()) * 1000
    (raw_dir / "usoil-m1-bid-2020.json").write_text(
        json.dumps([[ts_apr, -2.5, 1.0, -37.0, 0.0], [ts_apr + 60000, 12.0, 12.5, 11.5, 12.2]]),
        encoding="utf-8",
    )
    (raw_dir / "usoil-m1-ask-2020.json").write_text(
        json.dumps([[ts_apr, -2.0, 1.2, -36.5, 0.1], [ts_apr + 60000, 12.1, 12.6, 11.6, 12.3]]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="NONPOSITIVE_PRICE_ANOMALY"):
        sam.seal_asset("USOIL", raw_dir, 1000, fragment_out=cache_dir / "f1.json", cache_dir=cache_dir)

    filtered = sam.seal_asset(
        "USOIL",
        raw_dir,
        1000,
        fragment_out=cache_dir / "f_filt.json",
        cache_dir=cache_dir,
        filter_nonpositive=True,
    )
    _check(filtered["nonpositive_detected_total"] == 1, "Must report exact nonpositive count")
    _check(filtered["nonpositive_filtered_total"] == 1, "Must filter nonpositive bar under --filter-nonpositive")
    _check(filtered["nonpositive_anomaly_flagged"] is True, "Must flag nonpositive anomaly")
    _check(filtered["min_price"] > 0.0, "Sealed min_price must be strictly > 0.0")

    # Inject 2025-01-01 Holdout timestamp -> MUST raise HoldoutLockError (even under python -O!)
    _write_raw_dev_years(raw_dir, "usoil", base_price=20.0)
    ts_2025 = int(datetime(2025, 1, 1, 0, 0, tzinfo=UTC).timestamp()) * 1000
    (raw_dir / "usoil-m1-bid-2024.json").write_text(json.dumps([[ts_2025, 70.0, 71.0, 69.0, 70.5]]), encoding="utf-8")
    (raw_dir / "usoil-m1-ask-2024.json").write_text(json.dumps([[ts_2025, 70.1, 71.1, 69.1, 70.6]]), encoding="utf-8")
    with pytest.raises(HoldoutLockError):
        sam.seal_asset("USOIL", raw_dir, 1000, fragment_out=cache_dir / "f_ho.json", cache_dir=cache_dir)


# ==============================================================================
# 2. x13_m1_loader.py Air-Gap Purity & quant_core == 41 Lock
# ==============================================================================


def test_x13_m1_loader_purity_and_quant_core_count_lock(tmp_path: Path) -> None:
    # CRITICAL B1: quant_core MUST stay exactly 41 files on PC Dev (40 synced excluding holdout_guard)
    qc_files = sorted(p.name for p in (AI_ENGINES_DIR / "quant_core").glob("*.py"))
    _check(len(qc_files) == 41, f"quant_core file count drifted from 41: got {len(qc_files)}")

    off3_dir = AI_ENGINES_DIR / "quant_factory" / "offensive3"
    forbidden_tokens = ("2025", "2026", "holdout", "duckdb", "holdout_guard", "scipy")
    for py_file in (off3_dir / "__init__.py", off3_dir / "x13_m1_loader.py"):
        _check(py_file.is_file(), f"Missing {py_file}")
        low_name = py_file.name.lower()
        low_src = py_file.read_text(encoding="utf-8").lower()
        for tok in forbidden_tokens:
            _check(tok not in low_name, f"Forbidden token {tok!r} in filename {py_file.name}")
            _check(tok not in low_src, f"Forbidden token {tok!r} in source of {py_file.name}")

    # Negative tests on loader: nonzero holdout_rows & SHA drift must fail closed
    cache_dir = tmp_path / "loader_cache"
    raw_dir = tmp_path / "raw_us30"
    _write_raw_dev_years(raw_dir, "us30", base_price=38000.0, spread=2.0)
    frags = cache_dir / "_fragments"
    sam.seal_asset("US30", raw_dir, 1000, fragment_out=frags / "us30.json", cache_dir=cache_dir)
    sam.merge_fragments(frags, cache_dir=cache_dir)

    # Tamper parquet -> SHA verification must raise ValueError
    p2024 = cache_dir / "us30" / "US30-M1-BIDASK-2024.parquet"
    orig_bytes = p2024.read_bytes()
    p2024.write_bytes(orig_bytes + b"\x00")
    with pytest.raises(ValueError, match="SHA256_DRIFT"):
        x13_loader.load_m1_asset("US30", cache_dir, verify_sha=True)
    p2024.write_bytes(orig_bytes)

    # Tamper manifest holdout_rows -> must fail closed
    mpath = cache_dir / "manifest.json"
    man = json.loads(mpath.read_text(encoding="utf-8"))
    man["holdout_rows"] = 1
    mpath.write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(ValueError, match="DEV_SEAL_VIOLATION"):
        x13_loader.load_m1_asset("US30", cache_dir, verify_sha=False)


# ==============================================================================
# 3. configs/ssot/ftmo_specs_28.json (All 28 Symbols + Causal Conversion + Guard)
# ==============================================================================


def test_ftmo_specs_28_ssot_completeness_and_invariants() -> None:
    specs_path = AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json"
    _check(specs_path.is_file(), f"Missing {specs_path}")
    cr.assert_dev_only_path(specs_path.relative_to(REPO_ROOT).as_posix())

    doc = json.loads(specs_path.read_text(encoding="utf-8"))
    _check(doc["symbol_count"] == 28, f"Expected symbol_count=28, got {doc['symbol_count']}")
    _check(doc["order_send_count"] == 0 and doc["holdout_rows_analysed"] == 0, "Safety fields must be 0")
    syms: dict[str, dict[str, Any]] = doc["symbols"]
    _check(len(syms) == 28, f"Expected 28 symbols, got {len(syms)}")

    tiers: dict[str, int] = {}
    zero_fixed = 0
    for sym, spec in syms.items():
        tiers[spec["blindness_tier"]] = tiers.get(spec["blindness_tier"], 0) + 1
        _check(float(spec["contract_size"]) > 0.0, f"{sym} invalid contract_size")
        _check(float(spec["tick_val_loss_usd_ref"]) > 0.0, f"{sym} tick_val_loss_usd_ref must be > 0")
        _check(float(spec["oneway_bps"]) > 0.0, f"{sym} oneway_bps must be > 0")
        _check(isinstance(spec["causal_tick_val_usd_formula"], str) and spec["causal_tick_val_usd_formula"], sym)
        if spec["currency_profit"] != "USD":
            _check(spec["profit_to_usd_pair"] is not None, f"{sym} needs profit_to_usd_pair")
            _check(spec["profit_to_usd_op"] in ("multiply", "divide"), f"{sym} invalid profit_to_usd_op")
        if spec["live_snapshot_tick_val_loss_was_zero"]:
            zero_fixed += 1
        # Rollover 3-day check: 3 for FX/Metals, 5 for Indices/Oil/Crypto
        expected_roll = 3 if spec["asset_class"] in ("forex", "metals") else 5
        _check(spec["swap_rollover3days"] == expected_roll, f"{sym} rollover={spec['swap_rollover3days']}")

    _check(zero_fixed == 16, f"Expected exactly 16 fixed zero tick_val_loss symbols, got {zero_fixed}")
    _check(tiers["DEV_CLB_CONSUMED_12OLD"] == 12, f"Tier 12OLD mismatch: {tiers}")
    _check(tiers["NEW9_D1_VIEWED_M1_UNSEEN"] == 9, f"Tier NEW9 mismatch: {tiers}")
    _check(tiers["TRUE_BLIND_CLB_NEW7_CROSSES"] == 7, f"Tier NEW7 mismatch: {tiers}")

    # Exact broker quirks verified from live specs
    _check(syms["JP225"]["contract_size"] == 10.0, "JP225.cash contract_size must be 10.0")
    _check(syms["BTCUSD"]["swap_mode"] == 5 and syms["BTCUSD"]["swap_long"] == -30.0, "BTCUSD swap_mode=5 (-30%/yr)")
    _check(
        syms["EURUSD"]["commission_usd_lot"] == 5.0 and syms["EURUSD"]["commission_usd_lot_the5ers"] == 4.0,
        "FX comm",
    )

    # Anti-Fake-Swap Guard blocks positive swap anomalies on US100, US500, UK100 short, USOIL long, UKOIL long
    _check(syms["US100"]["anti_fake_swap_guard"]["long_anomaly_blocked"] is True, "US100 long anomaly blocked")
    _check(syms["US500"]["anti_fake_swap_guard"]["long_anomaly_blocked"] is True, "US500 long anomaly blocked")
    _check(syms["UK100"]["anti_fake_swap_guard"]["short_anomaly_blocked"] is True, "UK100 short anomaly blocked")
    _check(syms["USOIL"]["anti_fake_swap_guard"]["long_anomaly_blocked"] is True, "USOIL long anomaly blocked")
    _check(syms["UKOIL"]["anti_fake_swap_guard"]["long_anomaly_blocked"] is True, "UKOIL long anomaly blocked")

    # Swing leverage schedule
    _check(syms["EURUSD"]["leverage_ftmo_swing"] == 30, "FX swing leverage must be 30")
    _check(syms["US30"]["leverage_ftmo_swing"] == 15, "Indices swing leverage must be 15")
    _check(syms["XAUUSD"]["leverage_ftmo_swing"] in (9, 10), "Metals swing leverage must be 9 or 10")
    _check(syms["USOIL"]["leverage_ftmo_swing"] == 10, "Oil swing leverage must be 10")
    _check(syms["BTCUSD"]["leverage_ftmo_swing"] == 1, "Crypto swing leverage must be 1")


# ==============================================================================
# 4. configs/offensive3/preregistration_m1200.json
# ==============================================================================


def test_preregistration_m1200_contract_and_gate_g08_alignment() -> None:
    p = AI_ENGINES_DIR / "configs" / "offensive3" / "preregistration_m1200.json"
    _check(p.is_file(), f"Missing {p}")
    cr.assert_dev_only_path(p.relative_to(REPO_ROOT).as_posix())

    doc = json.loads(p.read_text(encoding="utf-8"))
    _check(doc["holdout_lock_sha256"] == sam.LOCK_SHA, "Holdout lock SHA mismatch")
    _check(doc["holdout_rows_analysed"] == 0 and doc["order_send_count"] == 0, "Safety counters must be 0")

    stat = doc["statistical_protocol"]
    _check(stat["sign_flip_draws"] == 50000, "sign_flip_draws must be 50000")
    _check(stat["pbo_returns_matrix_required"] is True, "pbo_returns_matrix_required must be True")

    fams = doc["duckdb_families"]
    _check(fams["offensive3_primary_m200"]["cap"] == 200, "primary cap must be 200")
    _check(fams["offensive3_primary_m200"]["max_per_family"] <= 20, "primary max_per_family must be <= 20")
    _check(fams["offensive3_exploratory_m1200"]["cap"] == 1200, "exploratory cap must be 1200")
    _check(fams["offensive3_exploratory_m1200"]["max_per_family"] <= 100, "exploratory max_per_family <= 100")

    codes = [f["family_code"] for f in doc["alpha_families"]]
    _check(codes == [f"F{i:02d}" for i in range(1, 13)], f"Expected F01..F12, got {codes}")
    _check(sum(f["primary_cap"] for f in doc["alpha_families"]) == 200, "Sum of primary_caps must equal 200")
    _check(sum(f["exploratory_cap"] for f in doc["alpha_families"]) == 1200, "Sum of exploratory_caps must equal 1200")

    # Verify kill_criteria instantiates research_council.KillCriteria cleanly
    kc_raw = doc["kill_criteria"]
    kc = KillCriteria(
        max_bh_q=kc_raw["max_bh_q"],
        min_dsr=kc_raw["min_dsr"],
        min_cluster_b_sharpe=kc_raw["min_cluster_b_sharpe"],
        min_cost_breakeven_mult=kc_raw["min_cost_breakeven_mult"],
        max_corr_vs_incumbent=kc_raw["max_corr_vs_incumbent"],
        max_tail_corr_vs_incumbent=kc_raw["max_tail_corr_vs_incumbent"],
        min_trades_cluster_b=kc_raw["min_trades_cluster_b"],
        max_pbo=kc_raw["max_pbo"],
        require_incumbent=kc_raw["require_incumbent"],
        require_robustness_gate=kc_raw["require_robustness_gate"],
    )
    _check(kc.max_bh_q == 0.10 and kc.min_cost_breakeven_mult == 2.0 and kc.require_robustness_gate is True, "KC")


# ==============================================================================
# 5. compute_router.py (--force-mode-b, --owner-approved-long-run, cache, M1 sync)
# ==============================================================================


def test_compute_router_mode_b_long_run_overrides_and_airgap_limits() -> None:
    dev_a = _mode_a_active_dev()
    x13 = _healthy_x13()

    # Default > 60m still blocks fail-closed
    blocked = cr.decide_route(dev_a, x13, est_minutes=120.0, shardable=True)
    _check(
        blocked["target"] == "BLOCKED_NEEDS_APPROVAL" and blocked["ask_owner_required"] is True,
        "Default >60m block",
    )

    # With both owner overrides -> Mode A forced to Mode B + >60m allowed -> PARALLEL_60_40
    allowed = cr.decide_route(
        dev_a,
        x13,
        est_minutes=180.0,
        shardable=True,
        force_mode_b=True,
        owner_approved_long_run=True,
    )
    _check(allowed["target"] == "PARALLEL_60_40", f"Expected PARALLEL_60_40, got {allowed}")
    _check(allowed["dev_pc_cores"] == 5 and allowed["dev_pc_priority"] == "NORMAL", "Expected Mode B resources")
    _check(allowed["ask_owner_required"] is False, "Owner-approved long run should proceed")

    # Hard air-gap gates (touches_holdout, touches_vps) MUST STILL stay blocked even with both flags!
    ho = cr.decide_route(
        dev_a,
        x13,
        est_minutes=180.0,
        touches_holdout=True,
        force_mode_b=True,
        owner_approved_long_run=True,
    )
    _check(ho["ask_owner_required"] is True and ho["target"] == "DEV_PC_ONLY", "Holdout air-gap must never bypass")

    vps = cr.decide_route(
        dev_a,
        x13,
        est_minutes=30.0,
        touches_vps=True,
        force_mode_b=True,
        owner_approved_long_run=True,
    )
    _check(vps["target"] == "BLOCKED_NEEDS_APPROVAL", "VPS block must never bypass")


def test_compute_router_dev_cache_includes_offensive3_and_preserves_quant_core_40() -> None:
    collected = cr.collect_dev_cache_files(root=REPO_ROOT, include_tapes=False)
    arcs = {arc for arc, _ in collected["entries"]}
    _check(collected["counts"]["quant_core"] == 40, f"quant_core must stay 40, got {collected['counts']['quant_core']}")
    _check(collected["holdout_guard_excluded"] is True, "holdout_guard must remain excluded")
    _check("tooling/ai-engines/quant_factory/offensive3/__init__.py" in arcs, "offensive3/__init__.py missing")
    _check("tooling/ai-engines/quant_factory/offensive3/x13_m1_loader.py" in arcs, "x13_m1_loader.py missing")
    _check(
        "tooling/ai-engines/configs/offensive3/preregistration_m1200.json" in arcs,
        "preregistration_m1200.json missing",
    )
    _check("tooling/ai-engines/configs/ssot/ftmo_specs_28.json" in arcs, "ftmo_specs_28.json missing")
    for arc in arcs:
        cr.assert_dev_only_path(arc)


def test_compute_router_sync_m1_parquets_incremental_sha_skip_airgap_and_fallback(tmp_path: Path) -> None:
    cache_dir = tmp_path / "local_repo" / ".runtime" / "hot-m1-cache"
    raw_dir = tmp_path / "raw_usoil"
    _write_raw_dev_years(raw_dir, "usoil", base_price=40.0)
    frags = cache_dir / "_fragments"
    sam.seal_asset("USOIL", raw_dir, 1000, fragment_out=frags / "usoil.json", cache_dir=cache_dir)
    sam.merge_fragments(frags, cache_dir=cache_dir)

    fake_remote_store: dict[str, str] = {}
    uploaded_log: list[str] = []

    def _query(_alias: str) -> dict[str, str]:
        return dict(fake_remote_store)

    def _upload(_alias: str, local_p: Path, rel_posix: str) -> None:
        uploaded_log.append(rel_posix)
        fake_remote_store[rel_posix] = hashlib.sha256(local_p.read_bytes()).hexdigest()

    # Pass 1: initial sync uploads all 7 parquets + manifest.json LAST
    with patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()):
        r1 = cr.sync_m1_parquets_incremental(
            cache_dir=cache_dir,
            query_remote_hashes_fn=_query,
            upload_fn=_upload,
        )
    _check(r1["ok"] is True and r1["status"] == "SYNCED_VERIFIED", f"Pass 1 failed: {r1}")
    _check(len(r1["uploaded_files"]) == 8 and r1["skipped_files"] == [], f"Expected 8 uploads: {r1}")
    _check(r1["uploaded_files"][-1] == ".runtime/hot-m1-cache/manifest.json", "manifest.json must upload LAST")

    # Pass 2: incremental sync skips ALL 8 identical files (0 bytes uploaded!)
    uploaded_log.clear()
    with patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()):
        r2 = cr.sync_m1_parquets_incremental(
            cache_dir=cache_dir,
            query_remote_hashes_fn=_query,
            upload_fn=_upload,
        )
    _check(r2["ok"] is True and r2["status"] == "ALREADY_UP_TO_DATE", f"Pass 2 failed: {r2}")
    _check(r2["uploaded_files"] == [] and len(r2["skipped_files"]) == 8, f"Expected 8 skipped: {r2}")
    _check(r2["bytes_uploaded"] == 0 and uploaded_log == [], "Must upload 0 bytes when SHA matches")

    # Pass 3: Silent fallback when X13 unreachable
    x13_off = _healthy_x13(reachable=False, eligible=False, ineligible_reasons=["x13_ssh_unreachable(naqex-x13)"])
    with patch.object(cr, "probe_x13_worker", return_value=x13_off):
        r3 = cr.sync_m1_parquets_incremental(cache_dir=cache_dir)
    _check(
        r3["ok"] is True and r3["fallback_used"] is True and r3["status"] == "FALLBACK_DEV_PC_LOCAL",
        f"Fallback: {r3}",
    )

    # Pass 4: Air-gap fail-closed on stray 2025 parquet file inside cache
    (cache_dir / "usoil" / "USOIL-M1-BIDASK-2025.parquet").write_bytes(b"BAD")
    with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
        cr.sync_m1_parquets_incremental(cache_dir=cache_dir)


# ==============================================================================
# 6. strategy_intel_bridge.py (--profile offensive3 opt-in + §3.4 exemption)
# ==============================================================================


def test_strategy_intel_bridge_offensive3_profile_opt_in_and_exemptions(tmp_path: Path) -> None:
    cleanroom = tmp_path / "cleanroom"
    handoff = cleanroom / "handoff"
    handoff.mkdir(parents=True)

    off3_payload = {
        "export_tier": "CLEANROOM_OFFENSIVE3_SANITIZED",
        "leads": [
            {
                "lead_id": "OFF3-INTRA-01",
                "title": "London WM/Reuters 16:00 Fixing Mean Reversion",
                "family_tag": "F01_FX_SESSION_FIXING_FLOW",
                "asset_universe": ["EURUSD", "GBPUSD"],
                "prop_track": "INTRADAY_SWAP0",
                "timeframe": "M15",
                "economic_rationale": "Dealer inventory unwind post 16:00 London fix with wide 1.5x ATR hard SL.",
                "counterparty_mechanism": "Passive benchmark index funds executing at fix",
                "sl_rule": "Hard 1.5x ATR stop loss, flat before 20:50 UTC",
                "replicability": "REPLICABLE_FROM_PUBLIC",
            },
            {
                "lead_id": "OFF3-SWING-01",
                "title": "H4 Trend Pullback on XAUUSD Swing",
                "family_tag": "F05_TREND_PULLBACK_H4_D1_SWING",
                "asset_universe": ["XAUUSD"],
                "prop_track": "FTMO_SWING",
                "timeframe": "D1",
                "economic_rationale": "Multi-day trend pullback with real swap filter and hard 2.0x ATR stop.",
                "counterparty_mechanism": "Short-term countertrend profit takers",
                "sl_rule": "Hard 2.0x ATR stop loss",
                "replicability": "REPLICABLE_FROM_PUBLIC",
            },
            {
                "lead_id": "OFF3-BRK-REJECT",
                "title": "Pure London Box Breakout",
                "family_tag": "Breakout",
                "asset_universe": ["EURUSD"],
                "prop_track": "INTRADAY_SWAP0",
                "timeframe": "M15",
                "economic_rationale": "London box breakout above high with hard SL.",
                "sl_rule": "Hard SL",
            },
            {
                "lead_id": "OFF3-TOXIC-REJECT",
                "title": "Martingale Recovery Fixer",
                "family_tag": "F04_MEAN_REVERSION_WIDE_ATR",
                "asset_universe": ["EURUSD"],
                "prop_track": "INTRADAY_SWAP0",
                "timeframe": "M15",
                "economic_rationale": "Mean reversion that doubles the lot on loss (martingale).",
                "sl_rule": "Hard SL",
            },
        ],
    }
    off3_file = handoff / "sanitized_offensive3_leads.json"
    off3_file.write_text(json.dumps(off3_payload, indent=2) + "\n", encoding="utf-8")
    before_sha = hashlib.sha256(off3_file.read_bytes()).hexdigest()

    out_file = tmp_path / "out_off3.json"
    rc = bridge.main(
        ["--intel-dir", str(cleanroom), "--out", str(out_file), "--profile", "offensive3"]
    )
    _check(rc == 0, f"Expected rc=0, got {rc}")
    _check(hashlib.sha256(off3_file.read_bytes()).hexdigest() == before_sha, "Must write 0 bytes back to cleanroom")

    data = json.loads(out_file.read_text(encoding="utf-8"))
    _check(data["profile"] == "offensive3", "Profile tag missing")
    _check(data["writes_back_to_cleanroom"] == 0 and data["holdout_rows_analysed"] == 0, "Safety fields")
    _check(data["sources_read"]["sanitized_offensive3_leads"] is True, "Must read sanitized_offensive3_leads.json")

    elig = {item["lead_id"]: item for item in data["eligible_dev_candidates"]}
    filt = {item["lead_id"]: set(item["filter_reasons"]) for item in data["filtered_out"]}
    _check(set(elig.keys()) == {"OFF3-INTRA-01", "OFF3-SWING-01"}, f"Unexpected eligible: {elig.keys()}")
    _check(
        "OFFENSIVE3_NON_BREAKOUT_PROP_INTRADAY_EXEMPTION" in elig["OFF3-INTRA-01"]["section_3_4_exemption_reason"],
        f"Missing intraday exemption reason: {elig['OFF3-INTRA-01']}",
    )
    _check(
        "OFFENSIVE3_FTMO_SWING_REAL_SWAP_EXEMPTION" in elig["OFF3-SWING-01"]["section_3_4_exemption_reason"],
        f"Missing swing exemption reason: {elig['OFF3-SWING-01']}",
    )
    _check("FORBIDDEN_OFFENSIVE3_PURE_BREAKOUT" in filt["OFF3-BRK-REJECT"], f"Missed breakout reject: {filt}")
    _check("FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL" in filt["OFF3-TOXIC-REJECT"], f"Missed toxic reject: {filt}")

    # Holdout 2025 leak in sanitized_offensive3_leads.json MUST still fail closed!
    off3_file.write_text(json.dumps({"leads": [{"lead_id": "BAD", "note": "Live 2025 profit"}]}), encoding="utf-8")
    with pytest.raises(HoldoutLockError):
        bridge.sync_strategy_intel(intel_dir=cleanroom, out_path=tmp_path / "never.json", profile="offensive3")


# ==============================================================================
# 7. quant_core/tca.py (28-symbol POINT_SIZES, BENCHMARK_SPREAD_PTS, v1.03 events)
# ==============================================================================


def test_tca_28_symbols_and_v103_non_fill_events() -> None:
    _check(tca.point_size_for_symbol("USOIL") == 0.001, "USOIL point size")
    _check(tca.point_size_for_symbol("USOIL.cash") == 0.001, "USOIL.cash point size")
    _check(tca.point_size_for_symbol("UKOIL") == 0.001, "UKOIL point size")
    _check(tca.point_size_for_symbol("UKOIL.cash") == 0.001, "UKOIL.cash point size")
    _check(tca.point_size_for_symbol("JP225") == 0.01, "JP225 point size")
    _check(tca.point_size_for_symbol("JP225.cash") == 0.01, "JP225.cash point size")
    _check(tca.point_size_for_symbol("BTCUSD") == 0.01, "BTCUSD point size")

    specs = json.loads((AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json").read_text(encoding="utf-8"))
    for sym, spec in specs["symbols"].items():
        pt = tca.point_size_for_symbol(sym)
        pt_ftmo = tca.point_size_for_symbol(spec["ftmo_symbol"])
        _check(abs(pt - float(spec["point"])) < 1e-12, f"Point mismatch for {sym}: {pt} != {spec['point']}")
        _check(abs(pt_ftmo - float(spec["point"])) < 1e-12, f"FTMO point mismatch for {spec['ftmo_symbol']}")
        sp = tca.benchmark_spread_for_symbol(sym)
        sp_ftmo = tca.benchmark_spread_for_symbol(spec["ftmo_symbol"])
        _check(sp is not None and sp > 0.0, f"Missing BENCHMARK_SPREAD_PTS for {sym}")
        _check(sp_ftmo is not None and sp_ftmo > 0.0, f"Missing BENCHMARK_SPREAD_PTS for {spec['ftmo_symbol']}")

    v103_events = (
        "ORDER_BLOCKED_NEWS",
        "ORDER_BLOCKED_SPREAD",
        "ORDER_BLOCKED_STOPS",
        "ORDER_BLOCKED_TOTAL_OR_CLUSTER_CAP",
        "ORDER_BLOCKED_MARGIN",
        "DRYRUN_SIGNAL_V103",
    )
    records = []
    for idx, ev in enumerate(v103_events):
        _check(ev in tca.NON_FILL_EVENT_TYPES, f"{ev} missing from NON_FILL_EVENT_TYPES")
        records.append(
            tca.parse_exec_audit_row(
                {
                    "utc_ts": 1700000000 + idx,
                    "symbol": "USOIL.cash",
                    "event_type": ev,
                    "swap_usd": "",
                }
            )
        )
    gate = tca.validate_tca_post_reconcile(records, require_zero_swap=True)
    _check(gate["passed"] is True and gate["closed_trades_checked"] == 0, f"v103 non-fills failed gate: {gate}")
