"""Offline-safe + local-cache test suite for Flash-Crash Defense Pareto Study & v1.03 EA.

Covers:
  - Offline synthetic invariants (zero external cache required; CI-safe & `python -O` safe):
    * Direct tape loader fail-closed on Holdout dates (`>= 2025-01-01`), Holdout timestamps,
      and `npz_sha256` tampering (NO `assert_holdout_locked` / `prop_engine` / `duckdb` imports!).
    * Shield A total simultaneous open-account risk cap, Shield B directional cluster caps
      (USD/JPY/US100) + SpreadGuard + 6-CCY red-news guard (including BoJ `±3600s` blackout).
    * Honest Flash-Crash Simultaneous Shock Matrix (`1.25x` / `1.50x` gap, ZERO clamping < 5%):
      proves unclamped baseline fails `7.19%..16.88%` while Shield C holds `<= 4.50%` across ALL profiles.
    * X13 deterministic shard splitting & exact shard merge (`merge_shard_summaries`).
    * `Naqex_Master_Prop7E_v103.mq5` static audit (`0` red flags under `audit_open_source_mq5`),
      `#define NAQEX_CUSTOM_GUARD_INPUTS`, `InpDryRunLogOnly = true`, `InpGuardDryRunLogOnly = true`,
      `InpMaxTotalOpenRiskPct`, `SpreadGuard`, `6-CCY ±10m` option, `0` `.ex5` in `exports/`,
      and LF-only / zero bare `$` checks on the Law-15 research report.
  - `@pytest.mark.local_cache`:
    * Real `frozen_9e_tapes_v2.{json,npz}` direct load + real M1 parquet SpreadGuard calibration +
      real 523-event 6-CCY calendar verification (`holdout_rows_analysed = 0`).
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = AI_ENGINES / "experiments"
EXPORTS_DIR = AI_ENGINES / "exports"
REPO_ROOT = AI_ENGINES.parents[1]
REPORT_MD = REPO_ROOT / "planning/research/FLASHCRASH-PARETO-DEFENSE-V103-20261127.md"
V103_MQ5 = EXPORTS_DIR / "Naqex_Master_Prop7E_v103.mq5"
STUDY_PY = EXPERIMENTS_DIR / "flashcrash_pareto_study.py"

for _p in (AI_ENGINES, EXPERIMENTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

fcp: Any = importlib.import_module("flashcrash_pareto_study")
wb_exp: Any = importlib.import_module("mq5_whitebox_exporter")


def _make_synthetic_tape_bundle(
    tmp_path: Path,
    *,
    day: str = "2024-06-10",
    entry_ts: int = 1718010000,
    corrupt_sha: bool = False,
) -> Path:
    """Create a minimal valid (or tampered) frozen_9e_tapes_v2.{json,npz} fixture."""
    stamps = np.array([entry_ts, entry_ts + 60, entry_ts + 120], dtype=np.int64)
    marks = np.array(
        [
            [-10.0, 20.0, -30.0, 15.0],
            [15.0, 80.0, -20.0, 60.0],
            [60.0, 120.0, 40.0, 100.0],
        ],
        dtype=np.float64,
    )
    offsets = np.array([0, 3], dtype=np.int64)
    npz_path = tmp_path / "frozen_9e_tapes_v2.npz"
    arrays: dict[str, np.ndarray] = {}
    tapes_meta: dict[str, Any] = {}
    for eng in fcp.CORE7_IDS:
        arrays[f"{eng}__stamps"] = stamps
        arrays[f"{eng}__marks"] = marks
        arrays[f"{eng}__offsets"] = offsets
        asset_sym = fcp.ENGINE_ASSET_MAP[eng]
        ep = 150.0 if "JPY" in asset_sym else (1.25 if "GBP" in asset_sym else 18000.0)
        tapes_meta[eng] = {
            "days": [day],
            "rows": {
                day: {
                    "day": day,
                    "year": int(day[:4]),
                    "entry": int(entry_ts),
                    "exit": int(entry_ts + 180),
                    "side": 1,
                    "asset": asset_sym,
                    "entry_price": ep,
                    "stop_risk_with_cost_usd": 200.0,
                    "initial_risk_usd": 190.0,
                    "net_usd_per_lot": 100.0,
                    "net_R": 0.5,
                    "at_open": False,
                }
            },
        }
    np.savez(npz_path, allow_pickle=False, **arrays)
    sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    if corrupt_sha:
        sha = "0" * 64
    meta = {
        "schema": "naqex-frozen-tapes-v2",
        "profile_mode": "Swing",
        "binding_sha256": "synthetic_binding_sha",
        "npz_sha256": sha,
        "ext_days": [day],
        "tapes": tapes_meta,
    }
    (tmp_path / "frozen_9e_tapes_v2.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp_path


def test_x13_compatibility_no_forbidden_imports_in_study() -> None:
    """Verify `flashcrash_pareto_study.py` never imports prop_engine, data_store, duckdb, or assert_holdout_locked."""
    src = STUDY_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = ("prop_engine", "data_store", "duckdb", "scipy", "pass27", "pass28")
    for mod in imported:
        for bad in forbidden:
            if bad in mod:
                raise AssertionError(f"X13-incompatible import found: {mod}")
    doc_note = "ZERO imports of `prop_engine`, `data_store`, `assert_holdout_locked`"
    if "assert_holdout_locked" in src.replace(doc_note, ""):
        raise AssertionError("flashcrash_pareto_study.py must NOT call assert_holdout_locked()")
    if fcp.ORDER_SEND_CAPABLE is not False or fcp.ORDER_SEND_COUNT != 0:
        raise AssertionError("ORDER_SEND invariants violated")


def test_direct_loader_verifies_sha_and_rejects_holdout_fail_closed(tmp_path: Path) -> None:
    """Direct frozen tape loader must verify npz_sha256 and reject >= 2025-01-01 dates/timestamps."""
    # 1. Valid synthetic Dev 2024 bundle loads cleanly
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    _make_synthetic_tape_bundle(ok_dir)
    loaded = fcp.load_frozen_tapes_direct(ok_dir)
    if loaded["holdout_rows_analysed"] != 0 or loaded["max_day"] >= "2025-01-01":
        raise AssertionError(f"Unexpected loaded metadata: {loaded}")

    # 2. Tampered npz_sha256 fails closed
    bad_sha_dir = tmp_path / "bad_sha"
    bad_sha_dir.mkdir()
    _make_synthetic_tape_bundle(bad_sha_dir, corrupt_sha=True)
    with pytest.raises(ValueError, match="FROZEN_TAPES_SHA_MISMATCH"):
        fcp.load_frozen_tapes_direct(bad_sha_dir)

    # 3. Holdout date 2025-01-02 fails closed
    bad_day_dir = tmp_path / "bad_day"
    bad_day_dir.mkdir()
    _make_synthetic_tape_bundle(bad_day_dir, day="2025-01-02", entry_ts=1735776000)
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        fcp.load_frozen_tapes_direct(bad_day_dir)

    # 4. Holdout timestamp inside a 2024-labeled day fails closed
    bad_ts_dir = tmp_path / "bad_ts"
    bad_ts_dir.mkdir()
    _make_synthetic_tape_bundle(bad_ts_dir, day="2024-12-31", entry_ts=1735689600)
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        fcp.load_frozen_tapes_direct(bad_ts_dir)


def test_shock_matrix_baseline_breaches_and_shield_c_under_4_50_pct() -> None:
    """Honest shock matrix must NOT clamp < 5%: baseline breaches 7.19%-16.88%, Shield C <= 4.50% all profiles."""
    base = fcp.compute_honest_shock_matrix(total_open_cap_p1p2_pct=None, total_open_cap_funded_pct=None)
    by_name = {r["profile"]: r for r in base}
    if abs(by_name["Funded (1.00x RedTeam / PORT_7E)"]["gap_shock_125x_pct"] - 4.06) > 1e-6:
        raise AssertionError(f"Expected Funded 4.06%, got {by_name['Funded (1.00x RedTeam / PORT_7E)']}")
    if abs(by_name["P2 (2.50x RedTeam / PORT_7E)"]["gap_shock_125x_pct"] - 7.19) > 1e-6:
        raise AssertionError(f"Expected P2 7.19%, got {by_name['P2 (2.50x RedTeam / PORT_7E)']}")
    if abs(by_name["P1 Bal (4.00x / PORT_9E)"]["gap_shock_125x_pct"] - 15.00) > 1e-6:
        raise AssertionError(f"Expected P1 Bal 15.00%, got {by_name['P1 Bal (4.00x / PORT_9E)']}")
    if abs(by_name["P1 Spr (4.75x / PORT_9E)"]["gap_shock_125x_pct"] - 16.88) > 1e-6:
        raise AssertionError(f"Expected P1 Spr 16.88%, got {by_name['P1 Spr (4.75x / PORT_9E)']}")

    # Shield C (3.00% P1/P2, 2.25% Funded + directional cluster caps) -> ALL profiles <= 4.50% at 1.25x & 1.50x!
    for cap_p12, cap_fn in ((3.00, 2.25), (2.50, 2.00), (2.00, 1.75)):
        sh = fcp.compute_honest_shock_matrix(
            total_open_cap_p1p2_pct=cap_p12,
            total_open_cap_funded_pct=cap_fn,
            usd_cluster_cap_p1p2_pct=2.25,
            jpy_cluster_cap_p1p2_pct=2.00,
            idx_cluster_cap_p1p2_pct=1.75,
            usd_cluster_cap_funded_pct=1.75,
            jpy_cluster_cap_funded_pct=1.50,
            idx_cluster_cap_funded_pct=1.25,
        )
        for row in sh:
            if not row["under_4_50_pct_at_125x"]:
                raise AssertionError(f"Shield C cap={cap_p12}% exceeded 4.50% at 1.25x gap: {row}")
            if row["gap_shock_125x_pct"] > cap_p12 * 1.25 + 1e-6:
                raise AssertionError(f"Shock exceeded analytical cap bound: {row}")


def test_shield_a_total_cap_and_shield_b_clusters_spread_news_on_synthetic(tmp_path: Path) -> None:
    """Verify Shield A total cap, Shield B directional clusters, SpreadGuard, and 6-CCY BoJ ±60m guard."""
    bundle_dir = _make_synthetic_tape_bundle(tmp_path, day="2024-06-10", entry_ts=1718010000)
    data = fcp.load_frozen_tapes_direct(bundle_dir)
    ext_days = data["ext_days"]
    tapes = data["tapes"]

    # 1. All 7 engines enter simultaneously at 4.0x:
    # Unclamped SYMCAP=1.75% allows up to 7.00% open risk; Shield A total_open_cap=3.00% must cap peak_open <= 3.00%!
    pre = fcp.prealign_days_for_tapes(ext_days, tapes)
    met_base, _, _, _, _ = fcp.replay_shielded_stage(
        ext_days, pre, capital_usd=100_000.0, mult=4.0, symcap_pct=1.75, total_open_cap_pct=None
    )
    met_a300, _, _, _, _ = fcp.replay_shielded_stage(
        ext_days, pre, capital_usd=100_000.0, mult=4.0, symcap_pct=1.75, total_open_cap_pct=3.00
    )
    met_a200, _, _, _, _ = fcp.replay_shielded_stage(
        ext_days, pre, capital_usd=100_000.0, mult=4.0, symcap_pct=1.75, total_open_cap_pct=2.00
    )
    if met_base["peak_open_risk_pct"] <= 3.5:
        raise AssertionError(f"Synthetic baseline should exceed 3.5% open risk, got {met_base['peak_open_risk_pct']}")
    if met_a300["peak_open_risk_pct"] > 3.00 + 1e-6:
        raise AssertionError(f"Shield A 3.00% leaked open risk: {met_a300['peak_open_risk_pct']}")
    if met_a200["peak_open_risk_pct"] > 2.00 + 1e-6:
        raise AssertionError(f"Shield A 2.00% leaked open risk: {met_a200['peak_open_risk_pct']}")

    # 2. Shield B SpreadGuard + 6-CCY BoJ ±3600s guard (using programmatic causal cap derivation)
    fake_cal = {"2024-06-10": [(1718010000 + 1800, "JPY", 3600)]}  # 30m after entry -> inside BoJ ±60m!
    fake_spreads = {("E4_US100_SESS40", "2024-06-10"): 290.0, ("E5_US100_RS1130", "2024-06-10"): 140.0}
    derived_caps = {
        "USDJPY": fcp.derive_causal_cluster_a_spread_cap([16.0], [21.8]),
        "GBPUSD": fcp.derive_causal_cluster_a_spread_cap([35.0], [26.8]),
        "EURJPY": fcp.derive_causal_cluster_a_spread_cap([23.0], [13.0]),
        "US100": fcp.derive_causal_cluster_a_spread_cap([248.0], [224.9]),
    }
    if derived_caps != {"USDJPY": 25.0, "GBPUSD": 35.0, "EURJPY": 25.0, "US100": 250.0}:
        raise AssertionError(f"Unexpected causal cap derivation: {derived_caps}")
    guarded, gstats = fcp.apply_red_news_and_spread_guard(
        tapes,
        red_news_cal=fake_cal,
        news_pad_sec=600,
        spread_caps_pts=derived_caps,
        entry_spread_pts=fake_spreads,
    )
    if gstats["blocked_spread"] != 1:
        raise AssertionError(f"Expected 1 spread block (E4 US100 290>250), got {gstats}")
    # All 4 JPY engines (E1, E2, E6, E7) must be blocked by BoJ ±3600s!
    if gstats["blocked_news_entry"] != 4:
        raise AssertionError(f"Expected 4 JPY entries blocked by BoJ ±3600s, got {gstats}")
    if "2024-06-10" not in guarded["E3_GBPUSD_VH"] or "2024-06-10" not in guarded["E5_US100_RS1130"]:
        raise AssertionError("Non-JPY low-spread engines should survive untouched")


def test_causal_cluster_a_spread_calibration_zero_cluster_b_leakage_and_boundaries(tmp_path: Path) -> None:
    """Prove 2021-2024 spread mutations change Cluster-A caps by 0.0, incomplete cache returns available=False,
    and entries before bar 0 never look forward."""
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    def _write_parquets(root: Path, b_multiplier: float) -> None:
        base_spreads = {"USDJPY": 14, "GBPUSD": 22, "EURJPY": 18, "US100": 1800}
        for sym, (sub, _div) in fcp.M1_SPREAD_SPECS.items():
            sdir = root / sub
            sdir.mkdir(parents=True, exist_ok=True)
            sp_a = base_spreads[sym]
            sp_b = int(round(sp_a * b_multiplier))
            for yr in range(2018, 2025):
                # 10 bars on June 10 15:00..15:09 UTC each year
                base_min = int((yr - 1970) * 525600 + 160 * 1440 + 15 * 60)
                mins = np.arange(base_min, base_min + 10, dtype=np.int64)
                bo = np.full(10, 100_000, dtype=np.int64)
                ao = bo + (sp_a if yr <= 2020 else sp_b)
                tbl = pa.table({"minute": mins, "bo": bo, "ao": ao})
                pq.write_table(tbl, sdir / f"{sym}-M1-BIDASK-{yr}.parquet")

    # Build synthetic tapes with one Cluster-A entry (2019), one Cluster-B entry (2023),
    # and one pre-cache entry (2018-01-02 before first M1 bar -> must NOT look forward!).
    min_2019 = int((2019 - 1970) * 525600 + 160 * 1440 + 15 * 60 + 2)
    min_2023 = int((2023 - 1970) * 525600 + 160 * 1440 + 15 * 60 + 2)
    min_pre0 = int((2018 - 1970) * 525600 + 10 * 1440)  # strictly < first 2018 bar
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    for eng in fcp.CORE7_IDS:
        sym = fcp.ENGINE_ASSET_MAP[eng]
        tapes[eng] = {
            "2018-01-11": ({"asset": sym, "entry": min_pre0 * 60}, np.array([min_pre0 * 60]), np.zeros((1, 4))),
            "2019-06-10": ({"asset": sym, "entry": min_2019 * 60}, np.array([min_2019 * 60]), np.zeros((1, 4))),
            "2023-06-10": ({"asset": sym, "entry": min_2023 * 60}, np.array([min_2023 * 60]), np.zeros((1, 4))),
        }

    dir_clean = tmp_path / "m1_clean"
    dir_mut_b = tmp_path / "m1_mut_b"
    _write_parquets(dir_clean, b_multiplier=1.0)
    _write_parquets(dir_mut_b, b_multiplier=50.0)  # Massive 50x Cluster-B mutation!

    cal_clean = fcp.calibrate_m1_spread_guard(tapes, m1_cache_dir=dir_clean)
    cal_mut_b = fcp.calibrate_m1_spread_guard(tapes, m1_cache_dir=dir_mut_b)
    if not cal_clean["available"] or not cal_mut_b["available"]:
        raise AssertionError("Synthetic M1 calibration should succeed")
    for sym in fcp.M1_SPREAD_SPECS:
        c0 = cal_clean["calibrated_dev_caps_a"][sym]
        c1 = cal_mut_b["calibrated_dev_caps_a"][sym]
        if abs(c0 - c1) != 0.0:
            raise AssertionError(f"CLUSTER_B_LEAKAGE on {sym}: clean={c0} vs mutated_B={c1}")
        # Verify pre-bar-0 entry was skipped (no forward lookahead!)
        if cal_clean["symbols"][sym]["missing_prior_bar_count"] < 1:
            raise AssertionError(f"Expected missing_prior_bar_count >= 1 on {sym}")
    for eng in fcp.CORE7_IDS:
        if (eng, "2018-01-11") in cal_clean["entry_spread_pts"]:
            raise AssertionError(f"Forward lookahead leaked bar 0 for {(eng, '2018-01-11')}")

    # Missing a non-2024 year parquet (e.g. 2019) must cleanly return available=False (NOT crash!)
    (dir_clean / "usdjpy" / "USDJPY-M1-BIDASK-2019.parquet").unlink()
    cal_incomplete = fcp.calibrate_m1_spread_guard(tapes, m1_cache_dir=dir_clean)
    if cal_incomplete["available"] is not False or cal_incomplete["reason"] != "m1_parquet_cache_incomplete":
        raise AssertionError(f"Incomplete cache must return available=False cleanly: {cal_incomplete}")


def test_calendar_loader_rejects_holdout_timestamp_inside_2024_day(tmp_path: Path) -> None:
    """Fail-closed on events_by_day carrying a >= 2025-01-01 utc_ts under a 2024 day key."""
    poisoned_cal = tmp_path / "poisoned_224.json"
    poisoned_cal.write_text(
        json.dumps({"events_by_day": {"2024-12-31": [{"utc_ts": 1735689600, "ccy": "USD"}]}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        fcp.load_red_news_calendar_rich(poisoned_cal)


def test_x13_shard_cli_rejects_zero_paths_and_forbidden_tokens(tmp_path: Path) -> None:
    """Fail-closed when n_paths < shard_total (no ZeroDivisionError) or forbidden tokens in job_id/out_json."""
    with pytest.raises(ValueError, match="INVALID_SHARD_PATHS"):
        fcp.run_pareto_study(
            derived_dir=tmp_path,
            n_paths=1,
            shard_index=1,
            shard_total=2,
            skip_m1_spread_scan=True,
            include_breakeven=False,
        )
    with pytest.raises(ValueError, match="FORBIDDEN_HOLDOUT_TOKEN"):
        fcp.main(["--job-id", "pareto_holdout_run"])
    with pytest.raises(ValueError, match="FORBIDDEN_HOLDOUT_TOKEN"):
        fcp.main(["--out-json", str(tmp_path / "pareto_2025_s0.json")])


def _make_mock_shard(
    *,
    shard_index: int,
    shard_total: int = 2,
    n_paths: int = 500,
    sum_npv: float = 300_000.0,
    pass_24: int = 340,
    fail_24: int = 2,
    holdout_rows: Any = 0,
    order_send: Any = 0,
    npz_sha: str = "a" * 64,
    usd_vnd: float = 25765.94,
    spread_guard_active: bool = True,
    eff_fee_exact: float = 70.4175,
) -> dict[str, Any]:
    pend_24 = n_paths - pass_24 - fail_24
    m_counts = {
        "3m": {"pass": 60, "fail": 0, "pending": n_paths - 60},
        "6m": {"pass": 160, "fail": 0, "pending": n_paths - 160},
        "12m": {"pass": 260, "fail": 1, "pending": n_paths - 261},
        "24m": {"pass": pass_24, "fail": fail_24, "pending": pend_24},
    }
    return {
        "dev_window": "2018-01-02..2024-12-31",
        "frozen_tapes_npz_sha256": npz_sha,
        "usd_vnd_rate": usd_vnd,
        "spread_guard_active": spread_guard_active,
        "holdout_rows_analysed": holdout_rows,
        "order_send_count": order_send,
        "shard": {"shard_index": shard_index, "shard_total": shard_total, "shard_n_paths": n_paths},
        "scenarios": {
            "SHIELD_C_TOT300_10M": {
                "config": {"id": "SHIELD_C_TOT300_10M", "group": "Shield_C"},
                "all_profiles_le_4_50_pct": True,
                "worst_gap_125x_pct": 3.75,
                "ftmo_std_10k_mc": {
                    "bf_1_00x": {
                        "effective_fee_usd": round(eff_fee_exact, 2),
                        "_shard_accum": {
                            "n_paths": n_paths,
                            "effective_fee_usd_exact": eff_fee_exact,
                            "monthly_counts": m_counts,
                            "sum_npv_24m": sum_npv,
                            "sum_cf_24m": sum_npv + 25_000.0,
                            "sum_fees_24m": eff_fee_exact * n_paths,
                            "cnt_npv24_le_0": 175,
                            "cnt_bot_kill": 45,
                            "cnt_firm_breach": 3,
                            "fn_entered": 400,
                            "fn_br_12m": 0 if shard_index == 0 else 1,
                            "fn_censored": 52,
                            "fn_m_tot": 2000,
                            "fn_m_dry": 1300 if shard_index == 0 else 1340,
                        },
                    }
                },
            }
        },
    }


def test_shard_merge_restores_law15_and_fails_closed_on_poisoned_or_duplicate_shards() -> None:
    """Verify exact Law-15/Law-13 shard merge + fail-closed rejection on all poisoned/duplicate mutations."""
    s0 = _make_mock_shard(shard_index=0, sum_npv=300_000.0, pass_24=340, fail_24=2)
    s1 = _make_mock_shard(shard_index=1, sum_npv=320_000.0, pass_24=350, fail_24=1)
    merged = fcp.merge_shard_summaries([s0, s1])
    if merged["winner_shield_c_id"] != "SHIELD_C_TOT300_10M" or merged["total_paths_merged"] != 1000:
        raise AssertionError(f"Missing winner or total paths in merged shard output: {merged}")
    m = merged["scenarios"]["SHIELD_C_TOT300_10M"]["ftmo_std_10k_mc"]["bf_1_00x"]
    if m["n_paths"] != 1000 or abs(m["ev_npv_24m_usd"] - 620.0) > 1e-6:
        raise AssertionError(f"Shard merge EV mismatch: {m}")
    if abs(m["pass_24m_pct"] - 69.0) > 1e-6 or abs(m["fail_24m_pct"] - 0.3) > 1e-6:
        raise AssertionError(f"Shard merge Pass/Fail mismatch: {m}")
    if abs(m["pending_24m_pct"] - 30.7) > 1e-6:
        raise AssertionError(f"Shard merge Pending mismatch: {m}")
    if abs(m["bot_auto_kill_pct"] - 9.0) > 1e-6 or abs(m["firm_hard_breach_pct"] - 0.6) > 1e-6:
        raise AssertionError(f"Shard merge Law-13 rates mismatch: {m}")
    if m["funded_entered_count"] != 800 or m["funded_breach_12m_count"] != 1 or m["funded_censored_count"] != 104:
        raise AssertionError(f"Shard merge Funded counts mismatch: {m}")
    if abs(m["funded_dry_months_pct"] - 66.0) > 1e-6:
        raise AssertionError(f"Shard merge dry months mismatch: {m}")
    for mk, mv in m["monthly_pass_fail_pending"].items():
        if abs(mv["sum_pct"] - 100.0) > 1e-6:
            raise AssertionError(f"Merged {mk} Pass+Fail+Pending != 100.00%: {mv}")

    # Negative mutations MUST ALL fail closed!
    bad_cases = [
        ("holdout_rows", [s0, _make_mock_shard(shard_index=1, holdout_rows=42)]),
        ("holdout_bool", [s0, _make_mock_shard(shard_index=1, holdout_rows=False)]),
        ("order_send", [s0, _make_mock_shard(shard_index=1, order_send=3)]),
        ("sha_mismatch", [s0, _make_mock_shard(shard_index=1, npz_sha="b" * 64)]),
        ("fx_mismatch", [s0, _make_mock_shard(shard_index=1, usd_vnd=26000.0)]),
        ("sg_mismatch", [s0, _make_mock_shard(shard_index=1, spread_guard_active=False)]),
        ("total_mismatch", [s0, _make_mock_shard(shard_index=1, shard_total=4)]),
        ("duplicate_idx", [s0, _make_mock_shard(shard_index=0)]),
        ("fee_mismatch", [s0, _make_mock_shard(shard_index=1, eff_fee_exact=99.99)]),
        ("zero_paths", [s0, _make_mock_shard(shard_index=1, n_paths=0, pass_24=0, fail_24=0)]),
    ]
    for label, pair in bad_cases:
        with pytest.raises(ValueError):
            fcp.merge_shard_summaries(pair)
        _ = label


def test_v103_mq5_static_audit_dryrun_and_zero_ex5_in_exports() -> None:
    """Verify v1.03 static audit (0 red flags), fail-closed DryRun=true, Shield C inputs, 0 .ex5 in exports/."""
    if not V103_MQ5.is_file():
        raise AssertionError(f"Missing {V103_MQ5}")
    raw_bytes = V103_MQ5.read_bytes()
    if b"\r\n" in raw_bytes:
        raise AssertionError("Naqex_Master_Prop7E_v103.mq5 must be LF-only (0 CRLF)")

    src = raw_bytes.decode("utf-8")
    audit = wb_exp.audit_open_source_mq5(src, filename=V103_MQ5.name)
    if audit["red_flags"]:
        raise AssertionError(f"v1.03 static audit reported red_flags: {audit['red_flags']}")
    if audit["intake_verdict"] != "CLEAN_FOR_PYTHON_REPLICATION":
        raise AssertionError(f"Unexpected static audit verdict: {audit}")

    required_tokens = (
        '#property version     "1.03"',
        "#define NAQEX_CUSTOM_GUARD_INPUTS",
        '#include "Include/Naqex_PropGuard.mqh"',
        '#include "Include/Naqex_Signals_7E.mqh"',
        "InpDryRunLogOnly",
        "InpGuardDryRunLogOnly",
        "InpMaxTotalOpenRiskPct",
        "InpEnableSpreadGuard",
        "InpUse6CcyNewsPad10m",
        "IsDryRunFailClosed()",
        "MathMin(InpHardTotalOpenCeilingPct, 3.00)",
        "InpHardTotalOpenCeilingPct > 3.00",
        "InpGuardNewsPadSec < InpGuardNewsHardBanSec",
        "actualRiskPct > effectiveHeadroom + 1e-6",
        "InpMaxEurJpySpreadPoints       = 25.0;",
    )
    for tok in required_tokens:
        if tok not in src:
            raise AssertionError(f"Missing required v1.03 contract token: {tok}")

    # Verify fail-closed DryRun defaults are literally `true`
    for inp_name in ("InpDryRunLogOnly", "InpGuardDryRunLogOnly", "InpShadowCompareMode", "InpGuardEnableRedNews"):
        m = re.search(rf"input\s+bool\s+{inp_name}\s*=\s*(true|false)\s*;", src)
        if not m or m.group(1) != "true":
            raise AssertionError(f"{inp_name} must default to true (fail-closed)")

    # Verify ZERO .ex5 binaries exist anywhere in tooling/ai-engines/exports/
    ex5_in_exports = list(EXPORTS_DIR.rglob("*.ex5"))
    if ex5_in_exports:
        raise AssertionError(f"Forbidden .ex5 binary found in exports/: {ex5_in_exports}")


def test_report_markdown_zero_bare_dollar_lf_only_and_law15_sections() -> None:
    """Verify Vietnamese Law-15 report has 0 bare `$`, LF-only line endings, and holdout_rows_analysed=0."""
    if not REPORT_MD.is_file():
        raise AssertionError(f"Missing research report: {REPORT_MD}")
    raw_bytes = REPORT_MD.read_bytes()
    if b"\r\n" in raw_bytes:
        raise AssertionError(f"{REPORT_MD.name} must be LF-only (0 CRLF)")
    text = raw_bytes.decode("utf-8")
    if "$" in text:
        raise AssertionError(f"{REPORT_MD.name} contains forbidden bare '$' character (use USD/VND)")
    for marker in ("holdout_rows_analysed: 0", "order_send_count: 0", "🔴", "🟡", "🟢", "🏆", "SHIELD_C_TOT300_10M"):
        if marker not in text:
            raise AssertionError(f"{REPORT_MD.name} missing required Law-15 marker: {marker}")


@pytest.mark.local_cache
def test_local_cache_direct_load_m1_spread_and_shield_c_pareto() -> None:
    """Integration test on real Dev 2018-2024 frozen_9e_tapes_v2 + M1 parquets + 523-event 6-CCY calendar."""
    if not (fcp.DEFAULT_DERIVED_DIR / "frozen_9e_tapes_v2.npz").is_file():
        pytest.skip("Local derived M1 tape cache absent")

    res = fcp.run_pareto_study(n_paths=400, seed=20261126, shard_index=0, shard_total=1, include_breakeven=False)
    if res["holdout_rows_analysed"] != 0 or res["order_send_count"] != 0:
        raise AssertionError("Safety counters must stay 0")
    if res["dev_window"] != "2018-01-02..2024-12-31":
        raise AssertionError(f"Unexpected dev_window: {res['dev_window']}")
    if not res["m1_spread_calibration"]["available"]:
        raise AssertionError("Real M1 parquet spread calibration failed")

    # Baseline breaches (>5%), Shield C winner stays <= 4.50% across ALL profiles
    base = res["scenarios"]["BASELINE_C10_NEWS_ON"]
    win_id = res["winner_shield_c_id"]
    win = res["scenarios"][win_id]
    if base["worst_gap_125x_pct"] < 15.0:
        raise AssertionError(f"Expected baseline worst gap >= 15%, got {base['worst_gap_125x_pct']}")
    if not win["all_profiles_le_4_50_pct"] or win["worst_gap_125x_pct"] > 4.50:
        raise AssertionError(f"Winner {win_id} breached 4.50% ceiling: {win['worst_gap_125x_pct']}")

    # Strict Pass+Fail+Pending == 100.00% check
    for mkey, mval in win["ftmo_std_10k_mc"]["bf_1_00x"]["monthly_pass_fail_pending"].items():
        if abs(mval["sum_pct"] - 100.0) > 0.02:
            raise AssertionError(f"Monthly {mkey} does not sum to 100%: {mval}")
