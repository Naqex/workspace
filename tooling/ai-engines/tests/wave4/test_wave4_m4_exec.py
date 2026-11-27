"""Wave 4 (`w4-m4-exec`) Unit, Safety, and Local-Artifact Verification Tests.

Covers:
  - Offline CI-safe (`-m "not local_cache"`) tests:
      1. AST zero-bare-assert, lazy MetaTrader5 only, zero psycopg/trading_workspace_v2, zero legacy dir strings.
      2. Fail-closed `[MT5 LOCK]` enforcement in `harvest_ftmo_symbols_under_mt5_lock` (blocks without `mt5_lock_held`).
      3. Holdout `< 2025-01-01` fail-closed verification under BOTH `python` and `python -O` (CME verifier + sealer).
      4. Honest year-depth classification (`FULL_DEV_7Y_DENSE_M1` vs `PARTIAL_DENSE_M1_WITH_SPARSE_EARLY_YEARS`
         vs `UNAVAILABLE_COMPLIANT`) and full synthetic multi-tier seal -> merge -> audit -> receipt round-trip.
      5. Mocked Tier 2 FTMO-Demo session harvest (zero live MT5!) including Apr-2020 `USOIL` `<= 0` quarantine.
  - Local artifact `@pytest.mark.local_cache` tests:
      6. Independent verification of `.runtime/offensive4/futures/wave4_cme_intraday_feasibility.json` (`10,000`
         paths, `SKIP`, `holdout_rows_analysed == 0`, exact `report_sha256`) and untouched Wave 2 CME summary.
      7. Independent verification of `.runtime/offensive4/m1/wave4_16sym_sealed/`,
         `.runtime/offensive4/m1/wave4_16sym_harvest_summary.json`, untouched `.runtime/hot-m1-cache/manifest.json`
         (`12` Wave 3 symbols), and byte-identical `w4_m4_exec_receipt.json` / `w4-m4-exec.json` receipts.

All checks use `_check(...)` so every assertion stays active under `python -O`.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory import seal_asset_m1 as sam  # noqa: E402
from quant_factory.wave4 import ftmo_m1_exporter as ftmo_exp  # noqa: E402
from quant_factory.wave4 import multi_source_m1_harvester as harv  # noqa: E402
from quant_factory.wave4 import wave4_m4_exec_runner as runner  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _make_dev_7y_batch(
    asset: str,
    *,
    tier: str = harv.TIER_1_QDM_CLI,
    provenance: str = sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
    base_price: float = 0.90000,
    spread_pts: float | None = None,
    point_size: float | None = None,
) -> harv.ValidatedM1Batch:
    ts_list: list[int] = []
    bid_list: list[list[float]] = []
    sp_list: list[float] = []
    for y in range(2018, 2025):
        t0 = int(datetime(y, 5, 10, 12, 0, tzinfo=UTC).timestamp())
        for k in range(3):
            o = base_price + 0.0004 * k
            c = o + 0.0002
            h = max(o, c) + 0.0003
            lo = min(o, c) - 0.0003
            ts_list.append(t0 + 60 * k)
            bid_list.append([o, h, lo, c])
            sp_list.append(float(spread_pts or 0.0))
    return harv.validate_m1_bars(
        asset,
        np.asarray(ts_list, dtype=np.int64),
        np.asarray(bid_list, dtype=np.float64),
        tier=tier,
        source_provenance=provenance,
        spread_points=np.asarray(sp_list, dtype=np.float64) if spread_pts is not None else None,
        point_size=point_size,
        waf_bypass_attempted=False,
    )


class _FakeFtmoMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TIMEFRAME_M1 = 1

    def __init__(
        self,
        rates_by_symbol: dict[str, np.ndarray],
        points_by_symbol: dict[str, tuple[int, float]],
        *,
        bypass_range_filter: bool = False,
    ) -> None:
        self.rates_by_symbol = rates_by_symbol
        self.points_by_symbol = points_by_symbol
        self.bypass_range_filter = bypass_range_filter
        self.shutdown_called = False

    def initialize(self, **_kwargs: Any) -> bool:
        return True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def account_info(self) -> Any:
        return SimpleNamespace(
            login=1515343318,
            server="FTMO-Demo",
            trade_mode=0,
            currency="USD",
            leverage=100,
            trade_allowed=False,
            trade_expert=False,
        )

    def terminal_info(self) -> Any:
        return SimpleNamespace(build=6230, maxbars=100_000_000, connected=True, trade_allowed=False)

    def symbol_select(self, _sym: str, _enable: bool) -> bool:
        return True

    def symbol_info(self, sym: str) -> Any:
        digits, pt = self.points_by_symbol.get(sym, (5, 1e-5))
        return SimpleNamespace(digits=digits, point=pt)

    def copy_rates_range(self, sym: str, _tf: int, dt_from: datetime, dt_to: datetime) -> Any:
        arr = self.rates_by_symbol.get(sym)
        if arr is None:
            return None
        if self.bypass_range_filter:
            return arr
        t0 = int(dt_from.timestamp())
        t1 = int(dt_to.timestamp())
        mask = (arr["time"] >= t0) & (arr["time"] <= t1)
        return arr[mask]


# ==============================================================================
# 1. Static AST Safety & Invariant Audit (Zero Assert, Lazy MT5, Zero Legacy)
# ==============================================================================


def test_01_static_ast_zero_assert_lazy_mt5_and_safety_flags() -> None:
    runner_path = AI_ENGINES_DIR / "quant_factory" / "wave4" / "wave4_m4_exec_runner.py"
    test_path = Path(__file__).resolve()
    legacy_forbidden = "mt5-" + "tradingview-" + "backtester"

    src = runner_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(runner_path))
    asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(not asserts, f"Bare assert(s) in {runner_path.name}: lines {asserts}")
    _check(legacy_forbidden not in src, "Legacy directory string leaked in runner")
    _check(legacy_forbidden not in test_path.read_text(encoding="utf-8"), "Legacy string leaked in test file")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(
                    not alias.name.startswith(("MetaTrader5", "trading_workspace_v2", "psycopg")),
                    f"Forbidden direct import {alias.name!r} at line {node.lineno}",
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            _check(
                not mod.startswith(("MetaTrader5", "trading_workspace_v2", "psycopg")),
                f"Forbidden from-import {mod!r} at line {node.lineno}",
            )

    _check(runner.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be False")
    _check(runner.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be 0")
    _check(runner.WAF_BYPASS_ATTEMPTED is False, "WAF_BYPASS_ATTEMPTED must be False")
    _check(len(runner.EXPECTED_REMAINING_16) == 16, f"Expected 16 symbols, got {len(runner.EXPECTED_REMAINING_16)}")


# ==============================================================================
# 2. Honest Depth Classification & Synthetic CME Verifier Fail-Closed Checks
# ==============================================================================


def test_02_depth_classification_and_cme_verifier_fail_closed(tmp_path: Path) -> None:
    full = runner.classify_year_depth({str(y): 370_000 for y in range(2018, 2025)})
    _check(full["depth_classification"] == "FULL_DEV_7Y_DENSE_M1", f"Unexpected full class: {full}")
    _check(full["dense_year_count"] == 7, "Expected 7 dense years")

    partial = runner.classify_year_depth(
        {"2018": 258, "2019": 259, "2020": 259, "2021": 109_000, "2022": 349_000, "2023": 349_000, "2024": 350_000}
    )
    _check(
        partial["depth_classification"] == "PARTIAL_DENSE_M1_WITH_SPARSE_EARLY_YEARS",
        f"Unexpected partial class: {partial}",
    )
    _check(partial["dense_m1_years"] == [2021, 2022, 2023, 2024], f"Unexpected dense years: {partial}")
    _check(partial["sparse_years"] == [2018, 2019, 2020], f"Unexpected sparse years: {partial}")

    empty = runner.classify_year_depth({})
    _check(empty["depth_classification"] == "UNAVAILABLE_COMPLIANT", f"Unexpected empty class: {empty}")

    # Synthetic valid CME artifact + fail-closed mutation tests (active under python -O!)
    w2_path = tmp_path / "cme_prop_study_summary.json"
    w2_path.write_text(json.dumps({"yahoo_futures_telemetry": {"MES": {"h1_rows": 2883}}}) + "\n", encoding="utf-8")
    w2_sha = _sha256_file(w2_path)

    body: dict[str, Any] = {
        "invariants": {
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_cutoff_date": "2024-12-31",
            "holdout_rows_analysed": 0,
        },
        "simulation_config": {
            "n_paths": 10000,
            "seed": 42,
            "dev_input_min_date": "2018-01-02",
            "dev_input_max_date": "2024-12-31",
        },
        "decision": "SKIP",
        "decision_rationale": {
            "failed_gates": ["EV_PER_FEE_BELOW_3X"],
            "vn_eligible_best_tier": "topstep_100k_combine",
            "vn_eligible_best_ev_per_fee": 1.021,
            "incumbent_ftmo_10k_ev_per_fee": 3.485,
            "incumbent_ftmo_100k_ev_per_fee": 6.628,
        },
        "cme_4firm_results": {
            "topstep_100k_combine": {
                "n_paths": 10000,
                "pass_fail_pending": {
                    "24m": {"pass_pct": 43.56, "fail_pct": 56.40, "pending_pct": 0.04, "sum_pct": 100.0}
                },
            }
        },
        "incumbent_ftmo_results": {
            "ftmo_standard_10k": {
                "n_paths": 10000,
                "pass_fail_pending": {
                    "24m": {"pass_pct": 69.45, "fail_pct": 17.88, "pending_pct": 12.67, "sum_pct": 100.0}
                },
            }
        },
    }
    report_sha = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    good_cme = tmp_path / "wave4_cme_intraday_feasibility.json"
    good_cme.write_text(json.dumps({**body, "report_sha256": report_sha}) + "\n", encoding="utf-8")

    res = runner.verify_wave4_cme_feasibility(good_cme, wave2_summary_path=w2_path, expected_wave2_sha256=w2_sha)
    _check(
        res["verified"] is True and res["decision"] == "SKIP" and res["n_paths"] == 10_000,
        f"CME check failed: {res}",
    )

    # Tampered Holdout date >= 2025-01-01 must raise HoldoutLockError even under python -O
    bad_body = json.loads(json.dumps(body))
    bad_body["simulation_config"]["dev_input_max_date"] = "2025-01-02"
    bad_sha = hashlib.sha256(
        json.dumps(bad_body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    bad_cme = tmp_path / "bad_cme.json"
    bad_cme.write_text(json.dumps({**bad_body, "report_sha256": bad_sha}) + "\n", encoding="utf-8")
    with pytest.raises(HoldoutLockError):
        runner.verify_wave4_cme_feasibility(bad_cme, wave2_summary_path=w2_path, expected_wave2_sha256=w2_sha)


# ==============================================================================
# 3. [MT5 LOCK] Fail-Closed + Mocked Tier 2 Harvest (Incl. USOIL Apr-2020 Guard)
# ==============================================================================


def test_03_mt5_lock_guard_and_mocked_tier2_harvest_with_usoil_filter(tmp_path: Path) -> None:
    sealed_dir = tmp_path / "sealed"
    stage_dir = tmp_path / "stage"

    # Must fail closed without mt5_lock_held=True
    with pytest.raises(harv.Mt5LockRequiredError):
        runner.harvest_ftmo_symbols_under_mt5_lock(["US30"], sealed_dir=sealed_dir, mt5_lock_held=False)

    # Must fail closed for live MT5 without allow_live_mt5=True
    with pytest.raises(harv.Mt5LockRequiredError):
        runner.harvest_ftmo_symbols_under_mt5_lock(
            ["US30"], sealed_dir=sealed_dir, mt5_lock_held=True, allow_live_mt5=False
        )

    # Build structured MT5 rates for NZDUSD (clean) + USOIL.cash (with 1 Apr-2020 <= 0 bar quarantined)
    dtype = np.dtype(
        [
            ("time", "<i8"),
            ("open", "<f8"),
            ("high", "<f8"),
            ("low", "<f8"),
            ("close", "<f8"),
            ("tick_volume", "<i8"),
            ("spread", "<i4"),
            ("real_volume", "<i8"),
        ]
    )
    # 2020-04-20 12:00 UTC -> server wall time = UTC + 3h (US DST NY+7 in April 2020!)
    t_apr_srv = int(datetime(2020, 4, 20, 15, 0, tzinfo=UTC).timestamp())
    t_2024_srv = int(datetime(2024, 6, 3, 15, 0, tzinfo=UTC).timestamp())

    nzd_rates = np.array(
        [
            (t_apr_srv, 0.60100, 0.60200, 0.60050, 0.60150, 40, 8, 0),
            (t_2024_srv, 0.61500, 0.61600, 0.61450, 0.61550, 50, 7, 0),
        ],
        dtype=dtype,
    )
    usoil_rates = np.array(
        [
            (t_apr_srv, -2.500, 0.500, -5.000, -1.000, 99, 40, 0),
            (t_apr_srv + 60, 12.100, 12.300, 12.000, 12.200, 88, 35, 0),
            (t_2024_srv, 75.100, 75.300, 75.000, 75.200, 77, 30, 0),
        ],
        dtype=dtype,
    )
    fake_mt5 = _FakeFtmoMT5(
        rates_by_symbol={"NZDUSD": nzd_rates, "USOIL.cash": usoil_rates},
        points_by_symbol={"NZDUSD": (5, 1e-5), "USOIL.cash": (3, 0.001)},
    )

    out = runner.harvest_ftmo_symbols_under_mt5_lock(
        ["NZDUSD", "USOIL", "JP225"],
        sealed_dir=sealed_dir,
        stage_dir=stage_dir,
        portable_root=tmp_path / "portable",
        mt5_lock_held=True,
        mt5_mod=fake_mt5,
    )
    _check(fake_mt5.shutdown_called is True, "Fake MT5 must shut down cleanly")
    _check(out["mt5_processes_after"] == 0, "Expected 0 MT5 processes after mock run")
    _check("NZDUSD" in out["exported"] and "USOIL" in out["exported"], f"Missing expected exports: {out}")
    _check("JP225" in out["unavailable"], "Missing symbol should be recorded honestly in unavailable")
    _check(
        out["exported"]["USOIL"]["nonpositive_detected"] == 1 and out["exported"]["USOIL"]["nonpositive_filtered"] == 1,
        f"Apr-2020 USOIL nonpositive quarantine mismatch: {out['exported']['USOIL']}",
    )
    _check(out["exported"]["USOIL"]["bar_count"] == 2, "USOIL must keep 2 positive bars")

    # Add 1 Tier 1 QDM batch for USDCHF, merge, and run full audit + receipt generation
    qdm_batch = _make_dev_7y_batch("USDCHF")
    runner.seal_validated_batch_isolated(qdm_batch, sealed_dir=sealed_dir)
    audit = runner.merge_and_audit_sealed_16(sealed_dir, verify_parquets_full=True)
    _check(
        audit["per_symbol_audit"]["USDCHF"]["source_provenance"] == "QDM_PROVIDER_DEFAULT_SINGLE_SIDE",
        "USDCHF provenance mismatch",
    )
    _check(audit["per_symbol_audit"]["NZDUSD"]["source_provenance"] == "FTMO_BID_PLUS_SPREAD", "NZDUSD prov")
    _check(audit["per_symbol_audit"]["USOIL"]["min_price"] > 0.0, "Sealed USOIL min_price must be > 0")
    _check(audit["per_symbol_audit"]["JP225"]["source_provenance"] == "UNAVAILABLE_COMPLIANT", "JP225 unavailable prov")

    # Holdout 2025-01-01 bar returned by rogue MT5 MUST raise HoldoutViolationError (never swallowed!)
    t_2025_srv = int(datetime(2025, 1, 1, 2, 0, tzinfo=UTC).timestamp())
    bad_rates = np.array([(t_2025_srv, 0.615, 0.616, 0.614, 0.6155, 10, 5, 0)], dtype=dtype)
    bad_mt5 = _FakeFtmoMT5(
        rates_by_symbol={"NZDUSD": bad_rates},
        points_by_symbol={"NZDUSD": (5, 1e-5)},
        bypass_range_filter=True,
    )
    with pytest.raises((HoldoutLockError, ftmo_exp.HoldoutViolationError)):
        runner.harvest_ftmo_symbols_under_mt5_lock(
            ["NZDUSD"],
            sealed_dir=tmp_path / "sealed_ho",
            stage_dir=tmp_path / "stage_ho",
            portable_root=tmp_path / "portable_ho",
            mt5_lock_held=True,
            mt5_mod=bad_mt5,
        )


# ==============================================================================
# 4. Real Local Artifact Verification (@pytest.mark.local_cache)
# ==============================================================================


@pytest.mark.local_cache
def test_04_real_local_cme_and_16sym_sealed_artifacts_and_receipts() -> None:
    # 1. CME 10,000-path SKIP + Wave 2 untouched
    cme_res = runner.verify_wave4_cme_feasibility()
    _check(cme_res["verified"] is True, "CME verification failed")
    _check(cme_res["n_paths"] == 10_000, "CME n_paths != 10000")
    _check(cme_res["decision"] == "SKIP", "CME decision != SKIP")
    _check(cme_res["holdout_rows_analysed"] == 0, "CME holdout_rows_analysed != 0")
    _check(cme_res["wave2_summary_untouched"] is True, "Wave 2 CME summary modified")

    # 2. Existing Wave 3 12-symbol hot-m1-cache manifest untouched
    hot_manifest_path = harv.DEFAULT_MANIFEST_PATH
    _check(
        _sha256_file(hot_manifest_path) == runner.EXPECTED_HOT_CACHE_MANIFEST_SHA256,
        "Existing .runtime/hot-m1-cache/manifest.json was modified!",
    )
    hot_man = json.loads(hot_manifest_path.read_text(encoding="utf-8-sig"))
    _check(len(hot_man["assets"]) == 12, f"Expected 12 Wave 3 assets in hot-m1-cache, got {len(hot_man['assets'])}")

    # 3. Wave 4 16-symbol sealed directory & summary JSON
    summary_path = runner.DEFAULT_SUMMARY_PATH
    _check(summary_path.is_file(), f"Missing harvest summary JSON: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    hi = summary["hard_invariants"]
    _check(hi["order_send_capable"] is False and hi["order_send_count"] == 0, "OrderSend invariant failed")
    _check(hi["waf_bypass_attempted"] is False, "waf_bypass_attempted must be False")
    _check(hi["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(hi["mt5_processes_after"] == 0, "mt5_processes_after must be 0")
    _check(hi["existing_hot_m1_manifest_untouched"] is True, "existing_hot_m1_manifest_untouched must be True")

    ti = summary["target_inventory"]
    _check(ti["expected_count"] == 16, f"expected_count={ti['expected_count']} != 16")
    _check(tuple(ti["expected_symbols"]) == runner.EXPECTED_REMAINING_16, "Expected 16 symbol list mismatch")
    _check(ti["sealed_count"] + ti["unavailable_count"] == 16, "sealed + unavailable must equal 16")
    _check(ti["sealed_count"] == 16, f"Expected all 16 symbols sealed cleanly, got {ti['sealed_count']}")

    # Audit every sealed symbol's manifest, Parquet SHA-256, monotonicity, positive prices, < 2025-01-01
    sealed_dir = runner.DEFAULT_SEALED_DIR
    sealed_man_path = sealed_dir / "manifest.json"
    _check(sealed_man_path.is_file(), f"Missing sealed manifest: {sealed_man_path}")
    _check(
        _sha256_file(sealed_man_path) == ti["sealed_manifest_sha256"],
        "Sealed manifest SHA-256 drift vs summary",
    )
    sealed_man = json.loads(sealed_man_path.read_text(encoding="utf-8-sig"))
    _check(sealed_man["holdout_rows"] == 0, "Sealed manifest holdout_rows != 0")
    _check(len(sealed_man["assets"]) == ti["sealed_count"], "Sealed manifest asset count mismatch")

    valid_honest_provs = {
        sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
        sam.PROVENANCE_HISTDATA_BID_ONLY,
    }
    for sym in runner.EXPECTED_REMAINING_16:
        rec = summary["symbols"][sym]
        _check(rec["waf_bypass_attempted"] is False, f"{sym} waf_bypass_attempted != False")
        _check(rec["holdout_rows_analysed"] == 0, f"{sym} holdout_rows_analysed != 0")
        _check(rec["status"] == "SEALED_VERIFIED", f"{sym} not SEALED_VERIFIED: {rec['status']}")
        _check(rec["source_provenance"] in valid_honest_provs, f"{sym} invalid provenance: {rec['source_provenance']}")
        _check(rec["native_Ask"] is False and rec["has_true_bid_ask"] is False, f"{sym} spoofed native_Ask")
        _check(rec["bar_count"] > 0 and rec["min_price"] > 0.0, f"{sym} invalid bar_count or min_price")
        _check(str(rec["max_ts_utc"]) < "2025-01-01T00:00:00Z", f"{sym} Holdout breach: {rec['max_ts_utc']}")
        _check(rec["npz_verified"] is True and rec["x13_loader_verified"] is True, f"{sym} NPZ/x13 verify false")

    # 4. Byte-identical worker receipts
    r1 = runner.DEFAULT_AUDIT_RECEIPT_PATH
    r2 = runner.DEFAULT_DROPBOX_RECEIPT_PATH
    _check(r1.is_file() and r2.is_file(), "Worker receipt(s) missing")
    _check(r1.read_bytes() == r2.read_bytes(), "Audit receipt and swarm_dropbox receipt must be byte-identical")
    rdoc = json.loads(r1.read_text(encoding="utf-8-sig"))
    _check(rdoc["status"] == "PASS", f"Receipt status != PASS: {rdoc['status']}")
    _check(rdoc["hard_invariants"]["holdout_rows_analysed"] == 0, "Receipt holdout_rows_analysed != 0")
    _check(rdoc["hard_invariants"]["mt5_processes_after"] == 0, "Receipt mt5_processes_after != 0")
    _check(rdoc["hard_invariants"]["waf_bypass_attempted"] is False, "Receipt waf_bypass_attempted != False")
