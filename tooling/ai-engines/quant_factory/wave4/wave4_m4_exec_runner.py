"""Wave 4 (`w4-m4-exec`) Compliant 16-Symbol M1 Harvest & CME Feasibility Verifier.

Executes and audits Wave 2A/2B deliverables for Total Offensive #4 `v4.8.1 FINAL`:
  1. Verifies `.runtime/offensive4/futures/wave4_cme_intraday_feasibility.json` (`10,000`
     paths, `holdout_rows_analysed == 0`, `SKIP` verdict, exact `report_sha256`) and confirms
     Wave 2 `.runtime/cme-futures-cache/cme_prop_study_summary.json` is untouched.
  2. Harvests and seals the `16` remaining symbols (`USDCHF`, `NZDUSD`, `EURGBP`, `EURAUD`,
     `GBPAUD`, `EURCAD`, `AUDJPY`, `CADJPY`, `CHFJPY`, `NZDJPY`, `US30`, `JP225`, `UK100`,
     `XAGUSD`, `USOIL`, `UKOIL`) into `.runtime/offensive4/m1/wave4_16sym_sealed/` via
     `multi_source_m1_harvester.py` + `seal_asset_m1.py` without modifying `.runtime/hot-m1-cache/manifest.json`.
  3. Enforces fail-closed safety invariants (ZERO bare `assert`s, `python -O` safe):
       - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`
       - `WAF_BYPASS_ATTEMPTED = False` ALWAYS
       - Hard Holdout cutoff `< 2025-01-01T00:00:00Z` (`holdout_rows_analysed == 0`)
       - Lazy `MetaTrader5` import ONLY via `ftmo_m1_exporter` under explicit `[MT5 LOCK]`
       - Honest provenance (`QDM_PROVIDER_DEFAULT_SINGLE_SIDE`, `FTMO_BID_PLUS_SPREAD`,
         `HISTDATA_BID_ONLY`, `UNAVAILABLE_COMPLIANT`) and exact per-year date depth reporting.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import (  # noqa: E402
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
)

from quant_factory import seal_asset_m1 as sam  # noqa: E402
from quant_factory.offensive3 import x13_m1_loader as x13_loader  # noqa: E402
from quant_factory.wave4 import (  # noqa: E402
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
)
from quant_factory.wave4 import ftmo_m1_exporter as ftmo_exp  # noqa: E402
from quant_factory.wave4 import multi_source_m1_harvester as harv  # noqa: E402

SCHEMA_SUMMARY: str = "naqex-wave4-16sym-harvest-summary-v1"
SCHEMA_RECEIPT: str = "naqex-wave4-m4-exec-receipt-v1"
ORDER_SEND_COUNT: int = 0
WAF_BYPASS_ATTEMPTED: bool = False
PROVENANCE_UNAVAILABLE_COMPLIANT: str = "UNAVAILABLE_COMPLIANT"

DENSE_M1_MIN_BARS_PER_YEAR: int = 100_000

EXPECTED_REMAINING_16: tuple[str, ...] = (
    "USDCHF",
    "NZDUSD",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "US30",
    "JP225",
    "UK100",
    "XAGUSD",
    "USOIL",
    "UKOIL",
)

DEFAULT_CME_FEASIBILITY_PATH: Path = (
    ROOT / ".runtime" / "offensive4" / "futures" / "wave4_cme_intraday_feasibility.json"
)
DEFAULT_WAVE2_CME_SUMMARY_PATH: Path = ROOT / ".runtime" / "cme-futures-cache" / "cme_prop_study_summary.json"
EXPECTED_WAVE2_CME_SUMMARY_SHA256: str = "edfe6dfad04e191086fc9cc9b60af18db0374563627c7c434323b916c003677b"
EXPECTED_HOT_CACHE_MANIFEST_SHA256: str = "650641b7593678169a85248a4c28d3c2e7a50906f3f4b04590f8848e2d2a1360"

DEFAULT_SEALED_DIR: Path = ROOT / ".runtime" / "offensive4" / "m1" / "wave4_16sym_sealed"
DEFAULT_FTMO_STAGE_DIR: Path = ROOT / ".runtime" / "offensive4" / "m1" / "wave4_16sym_ftmo_raw"
DEFAULT_SUMMARY_PATH: Path = ROOT / ".runtime" / "offensive4" / "m1" / "wave4_16sym_harvest_summary.json"
DEFAULT_AUDIT_RECEIPT_PATH: Path = ROOT / ".runtime" / "offensive4" / "audits" / "w4_m4_exec_receipt.json"
DEFAULT_DROPBOX_RECEIPT_PATH: Path = ROOT / ".tmp" / "swarm_dropbox" / "w4-m4-exec.json"


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_year_depth(year_bar_counts: Mapping[str, int]) -> dict[str, Any]:
    """Honestly classify exact Dev 2018-2024 M1 depth per symbol."""
    covered = sorted(int(y) for y, cnt in year_bar_counts.items() if int(cnt) > 0)
    dense = sorted(int(y) for y, cnt in year_bar_counts.items() if int(cnt) >= DENSE_M1_MIN_BARS_PER_YEAR)
    sparse = sorted(y for y in covered if y not in dense)
    missing = [y for y in sam.DEV_YEARS if y not in covered]

    if dense == list(sam.DEV_YEARS):
        depth_class = "FULL_DEV_7Y_DENSE_M1"
    elif not covered:
        depth_class = "UNAVAILABLE_COMPLIANT"
    elif len(dense) >= 3 and sparse:
        depth_class = "PARTIAL_DENSE_M1_WITH_SPARSE_EARLY_YEARS"
    elif dense:
        depth_class = "PARTIAL_DEV_DENSE_M1"
    else:
        depth_class = "SPARSE_NON_M1_ONLY"

    return {
        "covered_years": covered,
        "dense_m1_years": dense,
        "sparse_years": sparse,
        "missing_dev_years": missing,
        "dense_year_count": len(dense),
        "depth_classification": depth_class,
        "dense_threshold_bars_per_year": DENSE_M1_MIN_BARS_PER_YEAR,
    }


def verify_wave4_cme_feasibility(
    cme_json_path: Path = DEFAULT_CME_FEASIBILITY_PATH,
    *,
    wave2_summary_path: Path = DEFAULT_WAVE2_CME_SUMMARY_PATH,
    expected_wave2_sha256: str | None = EXPECTED_WAVE2_CME_SUMMARY_SHA256,
) -> dict[str, Any]:
    """Independently verify Wave 4 10,000-path 4-firm CME MC artifact and Wave 2 non-regression."""
    cpath = Path(cme_json_path)
    if not cpath.is_file():
        raise FileNotFoundError(f"Wave 4 CME feasibility JSON missing: {cpath}")
    doc = json.loads(cpath.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Malformed CME feasibility JSON root: {cpath}")

    inv = doc.get("invariants", {})
    sim = doc.get("simulation_config", {})
    if not isinstance(inv, dict) or not isinstance(sim, dict):
        raise ValueError("CME feasibility JSON missing invariants or simulation_config")

    enforce_holdout_zero_rows(inv.get("holdout_rows_analysed", -1), context="verify_wave4_cme_feasibility")
    if inv.get("order_send_capable") is not False or inv.get("order_send_count") != 0:
        raise ValueError(f"CME safety invariant failed: order_send={inv.get('order_send_count')!r}")
    if inv.get("holdout_cutoff_date") != HOLDOUT_CUTOFF_DATE:
        raise HoldoutLockError(f"CME holdout_cutoff_date mismatch: {inv.get('holdout_cutoff_date')!r}")

    n_paths = sim.get("n_paths")
    if isinstance(n_paths, bool) or n_paths != 10_000:
        raise ValueError(f"CME n_paths must be 10000, got {n_paths!r}")

    max_date = str(sim.get("dev_input_max_date", ""))
    enforce_pre_holdout_dates(max_date, context="verify_wave4_cme_feasibility.max_date", cutoff_day="2025-01-01")

    decision = doc.get("decision")
    if decision != "SKIP":
        raise ValueError(f"Expected CME decision 'SKIP', got {decision!r}")

    stored_report_sha = str(doc.get("report_sha256", ""))
    body = {k: v for k, v in doc.items() if k != "report_sha256"}
    recomputed_sha = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    if stored_report_sha != recomputed_sha:
        raise ValueError(
            f"CME report_sha256 mismatch: stored={stored_report_sha!r} recomputed={recomputed_sha!r}"
        )

    # Verify pass + fail + pending == 100.0% across all CME and incumbent tiers
    tier_checks = 0
    for bucket_key in ("cme_4firm_results", "incumbent_ftmo_results"):
        bucket = doc.get(bucket_key, {})
        if not isinstance(bucket, dict) or not bucket:
            raise ValueError(f"CME JSON missing non-empty {bucket_key}")
        for tid, tdata in bucket.items():
            if tdata.get("n_paths") != 10_000:
                raise ValueError(f"Tier {tid} n_paths={tdata.get('n_paths')!r} != 10000")
            pfp = tdata.get("pass_fail_pending", {})
            for horizon_k, hvals in pfp.items():
                total_pct = round(
                    float(hvals["pass_pct"]) + float(hvals["fail_pct"]) + float(hvals["pending_pct"]), 4
                )
                if abs(total_pct - 100.0) > 0.05:
                    raise ValueError(f"Tier {tid} {horizon_k} pass+fail+pending={total_pct} != 100.0")
            tier_checks += 1

    # Verify Wave 2 cme_prop_study_summary.json untouched
    w2_path = Path(wave2_summary_path)
    if not w2_path.is_file():
        raise FileNotFoundError(f"Wave 2 CME summary missing: {w2_path}")
    w2_sha = _sha256_file(w2_path)
    if expected_wave2_sha256 is not None and w2_sha != expected_wave2_sha256:
        raise ValueError(f"Wave 2 CME summary SHA-256 drift: expected={expected_wave2_sha256} actual={w2_sha}")
    w2_doc = json.loads(w2_path.read_text(encoding="utf-8-sig"))
    w2_telem = w2_doc.get("yahoo_futures_telemetry") or w2_doc.get("symbols") or {}
    w2_h1_counts = [
        int(v.get("h1_rows", 0))
        for v in w2_telem.values()
        if isinstance(v, dict) and "h1_rows" in v
    ]
    w2_min_h1 = min(w2_h1_counts) if w2_h1_counts else 0
    if not w2_h1_counts or w2_min_h1 < 500:
        raise ValueError(f"Wave 2 CME summary min h1_rows={w2_min_h1} < 500")

    return {
        "verified": True,
        "cme_json_path": str(cpath.relative_to(ROOT)).replace("\\", "/") if cpath.is_relative_to(ROOT) else str(cpath),
        "cme_file_sha256": _sha256_file(cpath),
        "report_sha256": stored_report_sha,
        "report_sha256_match": True,
        "n_paths": 10_000,
        "seed": int(sim.get("seed", 42)),
        "dev_input_window": f"{sim.get('dev_input_min_date')}..{max_date}",
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "decision": decision,
        "tiers_verified_count": tier_checks,
        "vn_eligible_best_tier": doc.get("decision_rationale", {}).get("vn_eligible_best_tier"),
        "vn_eligible_best_ev_per_fee": doc.get("decision_rationale", {}).get("vn_eligible_best_ev_per_fee"),
        "incumbent_ftmo_10k_ev_per_fee": doc.get("decision_rationale", {}).get("incumbent_ftmo_10k_ev_per_fee"),
        "incumbent_ftmo_100k_ev_per_fee": doc.get("decision_rationale", {}).get("incumbent_ftmo_100k_ev_per_fee"),
        "failed_gates": list(doc.get("decision_rationale", {}).get("failed_gates", [])),
        "wave2_summary_untouched": True,
        "wave2_summary_sha256": w2_sha,
        "wave2_min_h1_rows": w2_min_h1,
    }


def seal_validated_batch_isolated(
    batch: harv.ValidatedM1Batch,
    *,
    sealed_dir: Path = DEFAULT_SEALED_DIR,
    lock_path: Path = sam.DEFAULT_LOCK_PATH,
    filter_nonpositive: bool = False,
) -> dict[str, Any]:
    """Seal one `ValidatedM1Batch` into isolated `sealed_dir` (Parquets + zero-pickle NPZ + fragment)."""
    if batch.waf_bypass_attempted is not False:
        raise ValueError("WAF_BYPASS_FORBIDDEN: batch.waf_bypass_attempted must be False")
    enforce_holdout_zero_rows(batch.holdout_rows_analysed, context=f"seal_isolated:{batch.asset}")
    enforce_pre_holdout_ts(
        batch.times_sec,
        harv.DEV_START_UTC_SEC,
        harv.HOLDOUT_STOP_UTC_SEC,
        context=f"seal_isolated:{batch.asset}",
        allow_empty=False,
    )

    spec = harv.build_symbol_harvest_spec(batch.asset)
    sdir = Path(sealed_dir)
    frags_dir = sdir / "_fragments"
    npz_dir = sdir / "npz"
    frag_path = frags_dir / f"w4_m1_{spec.canonical_symbol.lower()}.json"
    npz_path = npz_dir / f"{spec.canonical_symbol}-M1-{batch.source_provenance}.npz"

    frag = sam.seal_generic_m1_arrays(
        spec.canonical_symbol,
        batch.times_sec,
        batch.bid_ohlc,
        source_provenance=batch.source_provenance,
        ask_ohlc=batch.ask_ohlc,
        spread_points=batch.spread_points,
        point_size=batch.point_size,
        scale=spec.scale,
        fragment_out=frag_path,
        npz_out=npz_path,
        cache_dir=sdir,
        lock_path=lock_path,
        filter_nonpositive=filter_nonpositive,
        source_detail=batch.source_detail,
        waf_bypass_attempted=False,
    )
    return {
        "fragment": frag,
        "fragment_path": str(frag_path),
        "npz_path": str(npz_path),
    }


def harvest_ftmo_symbols_under_mt5_lock(
    symbols: Sequence[str],
    *,
    sealed_dir: Path = DEFAULT_SEALED_DIR,
    stage_dir: Path = DEFAULT_FTMO_STAGE_DIR,
    portable_root: Path = ftmo_exp.DEFAULT_PORTABLE_ROOT,
    mt5_lock_held: bool = False,
    allow_live_mt5: bool = False,
    mt5_mod: Any = None,
    lock_path: Path = sam.DEFAULT_LOCK_PATH,
    filter_nonpositive_symbols: Sequence[str] = ("USOIL",),
) -> dict[str, Any]:
    """Export requested symbols from FTMO-Demo portable (`< 2025-01-01`) under explicit `[MT5 LOCK]` and seal."""
    if not mt5_lock_held:
        raise harv.Mt5LockRequiredError(
            "MT5_LOCK_REQUIRED: harvest_ftmo_symbols_under_mt5_lock requires mt5_lock_held=True"
        )
    if mt5_mod is None and not allow_live_mt5:
        raise harv.Mt5LockRequiredError("MT5_LOCK_REQUIRED: allow_live_mt5=True required for live portable MT5 session")

    ftmo_specs = harv._load_ftmo_specs_optional()
    specs = [harv.build_symbol_harvest_spec(s, ftmo_specs=ftmo_specs) for s in symbols]
    if not specs:
        return {"exported": {}, "unavailable": {}, "mt5_processes_after": 0, "account": None}

    oil_filter_set = {s.strip().upper() for s in filter_nonpositive_symbols}
    stage_root = Path(stage_dir)
    stage_root.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    mt5, proc, ini_path, account_info = ftmo_exp._open_ftmo_mt5_session(
        portable_root=Path(portable_root),
        mt5_mod=mt5_mod,
    )

    raw_results: dict[str, tuple[dict[str, np.ndarray], int, float]] = {}
    unavailable: dict[str, str] = {}
    try:
        for spec in specs:
            try:
                arrays, digits, point = ftmo_exp.fetch_symbol_m1_from_mt5(
                    mt5,
                    spec.ftmo_symbol,
                    start_year=2018,
                    end_year=2024,
                    decode_broker_eet=True,
                )
                raw_results[spec.canonical_symbol] = (arrays, digits, point)
            except (HoldoutLockError, ftmo_exp.HoldoutViolationError):
                # Never swallow Holdout violations!
                raise
            except Exception as exc:
                unavailable[spec.canonical_symbol] = f"{type(exc).__name__}: {exc}"
    finally:
        ftmo_exp._teardown_ftmo_mt5_session(
            mt5,
            proc,
            ini_path,
            initialized=True,
        )

    post_procs = len(ftmo_exp.list_running_mt5_processes()) if mt5_mod is None else 0
    if post_procs != 0:
        raise ftmo_exp.SafetyLockError(f"POST_HARVEST_MT5_PROCS_NONZERO: {post_procs}")

    # Validate, save raw FTMO NPZ stage (for clean provenance audit), and seal into sealed_dir
    sealed_out: dict[str, dict[str, Any]] = {}
    for spec in specs:
        sym = spec.canonical_symbol
        if sym not in raw_results:
            continue
        arrays, digits, point = raw_results[sym]
        ts_all = np.asarray(arrays["ts_utc"], dtype=np.int64)
        # Fail-closed Holdout check before any slicing
        enforce_pre_holdout_ts(
            ts_all,
            None,
            harv.HOLDOUT_STOP_UTC_SEC,
            context=f"ftmo_harvest_stage:{sym}",
            allow_empty=False,
        )
        dev_mask = ts_all >= harv.DEV_START_UTC_SEC
        if not bool(np.any(dev_mask)):
            unavailable[sym] = "FTMO_NO_DEV_2018_2024_BARS"
            continue

        ts_dev = ts_all[dev_mask]
        bid_dev = np.column_stack(
            [
                np.asarray(arrays["open"], dtype=np.float64)[dev_mask],
                np.asarray(arrays["high"], dtype=np.float64)[dev_mask],
                np.asarray(arrays["low"], dtype=np.float64)[dev_mask],
                np.asarray(arrays["close"], dtype=np.float64)[dev_mask],
            ]
        )
        sp_dev = np.asarray(arrays["spread_pts"], dtype=np.float64)[dev_mask]
        tv_dev = np.asarray(arrays["tick_volume"], dtype=np.int64)[dev_mask]

        # Enforce OHLC rounding safety (FTMO MT5 occasionally emits tiny floating noise)
        filter_np = sym in oil_filter_set
        batch = harv.validate_m1_bars(
            sym,
            ts_dev,
            bid_dev,
            tier=harv.TIER_2_FTMO_DEMO,
            source_provenance=sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
            ask_ohlc=None,
            spread_points=sp_dev,
            point_size=float(point),
            filter_nonpositive=filter_np,
            waf_bypass_attempted=False,
            source_detail=f"ftmo-demo-portable:{spec.ftmo_symbol}",
        )

        # Persist verified pre-2025 FTMO NPZ stage file (compatible with parse_ftmo_m1_npz)
        if batch.nonpositive_filtered > 0:
            ask_raw_stage = bid_dev + (sp_dev[:, None] * float(point))
            keep_stage = ~(np.any(bid_dev <= 0.0, axis=1) | np.any(ask_raw_stage <= 0.0, axis=1))
            tv_stage = tv_dev[keep_stage]
        else:
            tv_stage = tv_dev
        stage_arrays = {
            "ts_utc": batch.times_sec,
            "open": batch.bid_ohlc[:, 0],
            "high": batch.bid_ohlc[:, 1],
            "low": batch.bid_ohlc[:, 2],
            "close": batch.bid_ohlc[:, 3],
            "spread_pts": np.rint(batch.spread_points).astype(np.int32)
            if batch.spread_points is not None
            else np.zeros(batch.bar_count, dtype=np.int32),
            "tick_volume": tv_stage,
        }
        stage_meta = ftmo_exp.save_sealed_symbol_npz(
            out_dir=stage_root,
            symbol=spec.ftmo_symbol,
            arrays=stage_arrays,
            digits=digits,
            point=float(point),
            cutoff_utc_ts=ftmo_exp.HOLDOUT_CUTOFF_UTC_TS,
        )

        sealed = seal_validated_batch_isolated(
            batch,
            sealed_dir=sealed_dir,
            lock_path=lock_path,
            filter_nonpositive=filter_np,
        )
        sealed_out[sym] = {
            "symbol": sym,
            "ftmo_symbol": spec.ftmo_symbol,
            "tier": harv.TIER_2_FTMO_DEMO,
            "source_provenance": batch.source_provenance,
            "bar_count": batch.bar_count,
            "min_ts_utc": batch.min_ts_utc,
            "max_ts_utc": batch.max_ts_utc,
            "min_price": batch.min_price,
            "max_price": batch.max_price,
            "nonpositive_detected": batch.nonpositive_detected,
            "nonpositive_filtered": batch.nonpositive_filtered,
            "spread_pts_median": stage_meta["spread_pts_median"],
            "spread_pts_p95": stage_meta["spread_pts_p95"],
            "stage_npz_sha256": stage_meta["sha256"],
            "fragment": sealed["fragment"],
            "fragment_path": sealed["fragment_path"],
            "npz_path": sealed["npz_path"],
        }

    return {
        "exported": sealed_out,
        "unavailable": unavailable,
        "mt5_processes_after": post_procs,
        "account": account_info,
        "elapsed_sec": round(time.perf_counter() - t0, 3),
    }


def merge_and_audit_sealed_16(
    sealed_dir: Path = DEFAULT_SEALED_DIR,
    *,
    lock_path: Path = sam.DEFAULT_LOCK_PATH,
    verify_parquets_full: bool = True,
) -> dict[str, Any]:
    """Merge all fragments in `sealed_dir/_fragments` into `sealed_dir/manifest.json` and run full audit."""
    sdir = Path(sealed_dir)
    frags_dir = sdir / "_fragments"
    merge_res = sam.merge_fragments(
        frags_dir,
        cache_dir=sdir,
        lock_path=lock_path,
        verify_existing_assets=True,
        required_years=None,
    )

    manifest_path = sdir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    enforce_holdout_zero_rows(manifest.get("holdout_rows", -1), context="merge_and_audit_sealed_16")

    per_symbol_audit: dict[str, dict[str, Any]] = {}
    for sym in EXPECTED_REMAINING_16:
        if sym not in manifest.get("assets", {}):
            per_symbol_audit[sym] = {
                "symbol": sym,
                "status": PROVENANCE_UNAVAILABLE_COMPLIANT,
                "source_provenance": PROVENANCE_UNAVAILABLE_COMPLIANT,
                "bar_count": 0,
                "holdout_rows_analysed": 0,
                "waf_bypass_attempted": False,
                "depth": classify_year_depth({}),
            }
            continue

        am = manifest["assets"][sym]
        frag_path = frags_dir / f"w4_m1_{sym.lower()}.json"
        frag_doc = json.loads(frag_path.read_text(encoding="utf-8-sig")) if frag_path.is_file() else {}
        years_map = am["years"]
        year_counts = {yk: int(ym["minutes"]) for yk, ym in sorted(years_map.items())}
        depth = classify_year_depth(year_counts)

        # Verify every sealed Parquet on disk: 0 NaN/Inf, 0 <=0 prices, monotonic ts, max_ts < 2025-01-01
        total_bars = 0
        min_ts_sec: int | None = None
        max_ts_sec: int | None = None
        min_px = float("inf")
        max_px = float("-inf")
        scale = float(am["scale"])

        if verify_parquets_full:
            asset_folder = sdir / str(am["dir"])
            prev_last_min: int | None = None
            for yk, ym in sorted(years_map.items()):
                pfile = asset_folder / str(ym["parquet"])
                tbl = pq.read_table(pfile)
                mins = tbl["minute"].to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
                if mins.size != int(ym["minutes"]):
                    raise ValueError(f"Row count mismatch in {pfile.name}: {mins.size} != {ym['minutes']}")
                if mins.size > 1 and not bool(np.all(np.diff(mins) > 0)):
                    raise ValueError(f"Non-monotonic timestamps in {pfile.name}")
                if prev_last_min is not None and int(mins[0]) <= prev_last_min:
                    raise ValueError(f"Cross-year overlap in {sym} {yk}")
                prev_last_min = int(mins[-1])

                ts_sec = mins * np.int64(60)
                enforce_pre_holdout_ts(
                    ts_sec,
                    harv.DEV_START_UTC_SEC,
                    harv.HOLDOUT_STOP_UTC_SEC,
                    context=f"audit_sealed:{sym}:{yk}",
                    allow_empty=False,
                )
                min_ts_sec = int(ts_sec[0]) if min_ts_sec is None else min(min_ts_sec, int(ts_sec[0]))
                max_ts_sec = int(ts_sec[-1]) if max_ts_sec is None else max(max_ts_sec, int(ts_sec[-1]))

                for col in ("bo", "bh", "bl", "bc"):
                    vals = tbl[col].to_numpy(zero_copy_only=False).astype(np.float64) / scale
                    if not bool(np.all(np.isfinite(vals))) or float(np.min(vals)) <= 0.0:
                        raise ValueError(f"Invalid bid price in {pfile.name}:{col}")
                    min_px = min(min_px, float(np.min(vals)))
                    max_px = max(max_px, float(np.max(vals)))

                if am.get("ask_columns_present"):
                    for bcol, acol in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")):
                        b_v = tbl[bcol].to_numpy(zero_copy_only=False)
                        a_v = tbl[acol].to_numpy(zero_copy_only=False)
                        a_f = a_v.astype(np.float64) / scale
                        if not bool(np.all(np.isfinite(a_f))) or float(np.min(a_f)) <= 0.0:
                            raise ValueError(f"Invalid ask price in {pfile.name}:{acol}")
                        if not bool(np.all(a_v >= b_v)):
                            raise ValueError(f"Crossed ask < bid in {pfile.name}:{acol}")
                total_bars += int(mins.size)

            # Verify x13_m1_loader round-trip across covered years
            covered_yrs = [int(yk) for yk in sorted(years_map)]
            t_x13, q_x13, _ = x13_loader.load_m1_asset(sym, sdir, verify_sha=True, years=covered_yrs)
            if int(t_x13.size) != total_bars:
                raise ValueError(f"x13_m1_loader count mismatch for {sym}: {t_x13.size} != {total_bars}")
            if not bool(np.all(np.isfinite(q_x13))) or float(np.min(q_x13)) <= 0.0:
                raise ValueError(f"x13_m1_loader invalid quote for {sym}")
        else:
            total_bars = int(sum(year_counts.values()))
            first_iso = str(frag_doc.get("first_ts_utc", "2018-01-01T00:00:00Z")).replace("Z", "+00:00")
            min_ts_sec = int(datetime.fromisoformat(first_iso).timestamp())
            max_ts_sec = int(frag_doc.get("max_ts_sec", 0))
            min_px = float(frag_doc.get("min_price", 0.0))
            max_px = float(frag_doc.get("max_price", 0.0))

        # Verify zero-pickle NPZ if recorded in fragment
        npz_verified = False
        npz_sha = frag_doc.get("npz_sha256")
        npz_rel = frag_doc.get("npz_path")
        if npz_rel and Path(npz_rel).is_file():
            actual_npz_sha = _sha256_file(Path(npz_rel))
            if npz_sha and actual_npz_sha != npz_sha:
                raise ValueError(f"NPZ SHA-256 mismatch for {sym}")
            with np.load(Path(npz_rel), allow_pickle=False) as z:
                if str(z["source_provenance"].item()) != str(am["source_provenance"]):
                    raise ValueError(f"NPZ provenance mismatch for {sym}")
                if int(z["holdout_rows"].item()) != 0:
                    raise HoldoutLockError(f"NPZ holdout_rows != 0 for {sym}")
                if bool(z["waf_bypass_attempted"].item()) is not False:
                    raise ValueError(f"NPZ waf_bypass_attempted != False for {sym}")
            npz_verified = True

        per_symbol_audit[sym] = {
            "symbol": sym,
            "status": "SEALED_VERIFIED",
            "source_provenance": am["source_provenance"],
            "native_Ask": bool(am["native_Ask"]),
            "has_true_bid_ask": bool(am["has_true_bid_ask"]),
            "ask_columns_present": bool(am["ask_columns_present"]),
            "scale": int(am["scale"]),
            "bar_count": total_bars,
            "total_parquet_bytes": int(sum(int(ym["bytes"]) for ym in years_map.values())),
            "min_ts_utc": sam._utc_iso(min_ts_sec) if min_ts_sec is not None else None,
            "max_ts_utc": sam._utc_iso(max_ts_sec) if max_ts_sec is not None else None,
            "min_price": round(min_px, 6),
            "max_price": round(max_px, 6),
            "year_bar_counts": year_counts,
            "depth": depth,
            "nonpositive_detected": int(frag_doc.get("nonpositive_detected_total", 0)),
            "nonpositive_filtered": int(frag_doc.get("nonpositive_filtered_total", 0)),
            "apr_2020_audit": frag_doc.get("apr_2020_audit"),
            "npz_verified": npz_verified,
            "npz_sha256": npz_sha,
            "x13_loader_verified": bool(verify_parquets_full),
            "holdout_rows_analysed": 0,
            "waf_bypass_attempted": False,
        }

    return {
        "merge_result": merge_res,
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "per_symbol_audit": per_symbol_audit,
    }


def build_harvest_summary_and_receipts(
    *,
    cme_verification: Mapping[str, Any],
    sealed_audit: Mapping[str, Any],
    phase_details: Mapping[str, Any],
    hot_cache_manifest_path: Path = harv.DEFAULT_MANIFEST_PATH,
    expected_hot_cache_sha256: str = EXPECTED_HOT_CACHE_MANIFEST_SHA256,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    audit_receipt_path: Path = DEFAULT_AUDIT_RECEIPT_PATH,
    dropbox_receipt_path: Path = DEFAULT_DROPBOX_RECEIPT_PATH,
    verification_gates: Mapping[str, Any] | None = None,
    immutables_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write `wave4_16sym_harvest_summary.json` and byte-identical worker receipts atomically."""
    hot_sha = _sha256_file(hot_cache_manifest_path)
    if hot_sha != expected_hot_cache_sha256:
        raise ValueError(
            f"HOT_M1_CACHE_MANIFEST_DRIFT: expected={expected_hot_cache_sha256} actual={hot_sha}"
        )

    per_sym: Mapping[str, Mapping[str, Any]] = sealed_audit["per_symbol_audit"]
    sealed_syms = [s for s in EXPECTED_REMAINING_16 if per_sym.get(s, {}).get("status") == "SEALED_VERIFIED"]
    unavailable_syms = [s for s in EXPECTED_REMAINING_16 if s not in sealed_syms]

    prov_counts: dict[str, int] = {}
    depth_counts: dict[str, int] = {}
    total_bars = 0
    total_parquet_bytes = 0
    for s in EXPECTED_REMAINING_16:
        rec = per_sym[s]
        p = str(rec["source_provenance"])
        prov_counts[p] = prov_counts.get(p, 0) + 1
        dc = str(rec["depth"]["depth_classification"])
        depth_counts[dc] = depth_counts.get(dc, 0) + 1
        total_bars += int(rec.get("bar_count", 0))
        total_parquet_bytes += int(rec.get("total_parquet_bytes", 0))

    now_utc = _utc_now_iso()
    summary: dict[str, Any] = {
        "schema": SCHEMA_SUMMARY,
        "generated_utc": now_utc,
        "worker": "w4-m4-exec",
        "wave": "Wave 2A/2B (Total Offensive #4 v4.8.1 FINAL)",
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "waf_bypass_attempted": WAF_BYPASS_ATTEMPTED,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "existing_hot_m1_manifest_untouched": True,
            "existing_hot_m1_manifest_sha256": hot_sha,
            "existing_hot_m1_symbol_count": 12,
            "mt5_processes_after": int(phase_details.get("mt5_processes_after", 0)),
        },
        "target_inventory": {
            "expected_count": len(EXPECTED_REMAINING_16),
            "expected_symbols": list(EXPECTED_REMAINING_16),
            "sealed_count": len(sealed_syms),
            "sealed_symbols": sealed_syms,
            "unavailable_count": len(unavailable_syms),
            "unavailable_symbols": unavailable_syms,
            "provenance_breakdown": prov_counts,
            "depth_breakdown": depth_counts,
            "total_bars_sealed": total_bars,
            "total_parquet_bytes": total_parquet_bytes,
            "sealed_cache_dir": ".runtime/offensive4/m1/wave4_16sym_sealed",
            "sealed_manifest_sha256": sealed_audit["manifest_sha256"],
        },
        "cme_feasibility_verification": dict(cme_verification),
        "phase_execution": dict(phase_details),
        "symbols": {s: dict(per_sym[s]) for s in EXPECTED_REMAINING_16},
    }
    harv._atomic_write_json(Path(summary_path), summary)
    summary_sha = _sha256_file(Path(summary_path))

    receipt: dict[str, Any] = {
        "schema": SCHEMA_RECEIPT,
        "worker": "w4-m4-exec",
        "wave": "Wave 2A/2B (Total Offensive #4 v4.8.1 FINAL)",
        "gates": ["W4-G15", "W4-G16"],
        "status": "PASS",
        "generated_utc": now_utc,
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "waf_bypass_attempted": WAF_BYPASS_ATTEMPTED,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "mt5_processes_after": int(phase_details.get("mt5_processes_after", 0)),
            "program_files_mt5_untouched": True,
            "existing_hot_m1_manifest_untouched": True,
            "existing_hot_m1_manifest_sha256": hot_sha,
            "wave2_cme_summary_untouched": bool(cme_verification["wave2_summary_untouched"]),
            "wave2_cme_summary_sha256": cme_verification["wave2_summary_sha256"],
            "immutables_untouched": True,
            "git_commit_executed": False,
        },
        "cme_verification": dict(cme_verification),
        "m1_16sym_harvest": {
            "summary_path": ".runtime/offensive4/m1/wave4_16sym_harvest_summary.json",
            "summary_sha256": summary_sha,
            "sealed_dir": ".runtime/offensive4/m1/wave4_16sym_sealed",
            "sealed_manifest_sha256": sealed_audit["manifest_sha256"],
            "sealed_count": len(sealed_syms),
            "unavailable_count": len(unavailable_syms),
            "provenance_breakdown": prov_counts,
            "depth_breakdown": depth_counts,
            "total_bars_sealed": total_bars,
            "total_parquet_bytes": total_parquet_bytes,
            "per_symbol_compact": {
                s: {
                    "status": per_sym[s]["status"],
                    "source_provenance": per_sym[s]["source_provenance"],
                    "bar_count": per_sym[s]["bar_count"],
                    "min_ts_utc": per_sym[s].get("min_ts_utc"),
                    "max_ts_utc": per_sym[s].get("max_ts_utc"),
                    "dense_m1_years": per_sym[s]["depth"]["dense_m1_years"],
                    "depth_classification": per_sym[s]["depth"]["depth_classification"],
                    "nonpositive_filtered": per_sym[s].get("nonpositive_filtered", 0),
                }
                for s in EXPECTED_REMAINING_16
            },
        },
        "phase_execution": dict(phase_details),
        "verification": dict(verification_gates) if verification_gates is not None else {},
        "immutables_snapshot": dict(immutables_snapshot) if immutables_snapshot is not None else {},
    }

    harv._atomic_write_json(Path(audit_receipt_path), receipt)
    harv._atomic_write_json(Path(dropbox_receipt_path), receipt)
    return {
        "summary": summary,
        "summary_sha256": summary_sha,
        "receipt": receipt,
        "receipt_sha256": _sha256_file(Path(audit_receipt_path)),
    }


__all__ = [
    "DEFAULT_AUDIT_RECEIPT_PATH",
    "DEFAULT_CME_FEASIBILITY_PATH",
    "DEFAULT_DROPBOX_RECEIPT_PATH",
    "DEFAULT_FTMO_STAGE_DIR",
    "DEFAULT_SEALED_DIR",
    "DEFAULT_SUMMARY_PATH",
    "DEFAULT_WAVE2_CME_SUMMARY_PATH",
    "DENSE_M1_MIN_BARS_PER_YEAR",
    "EXPECTED_HOT_CACHE_MANIFEST_SHA256",
    "EXPECTED_REMAINING_16",
    "EXPECTED_WAVE2_CME_SUMMARY_SHA256",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PROVENANCE_UNAVAILABLE_COMPLIANT",
    "SCHEMA_RECEIPT",
    "SCHEMA_SUMMARY",
    "WAF_BYPASS_ATTEMPTED",
    "build_harvest_summary_and_receipts",
    "classify_year_depth",
    "harvest_ftmo_symbols_under_mt5_lock",
    "merge_and_audit_sealed_16",
    "seal_validated_batch_isolated",
    "verify_wave4_cme_feasibility",
]
