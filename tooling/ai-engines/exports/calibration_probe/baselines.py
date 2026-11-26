"""Dev M1 (2018-2024, holdout=0) spread baseline loader from `.runtime/hot-m1-cache`."""

from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
from exports.calibration_probe.constants import (
    CORE_SYMBOLS,
    DEFAULT_HOLDOUT_LOCK_JSON,
    DEFAULT_HOT_M1_CACHE,
    HOLDOUT_START_UTC_TS,
    SYMBOL_META,
)
from exports.calibration_probe.math_schedule import estimate_notional_usd
from exports.calibration_probe.models import SafetyLockError
from exports.calibration_probe.validators import assert_holdout_lock_intact
from quant_core.io_utils import sha256_file


def compute_dev_m1_spread_baselines(
    *,
    hot_cache_dir: Path = DEFAULT_HOT_M1_CACHE,
    holdout_lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON,
    verify_sha: bool = False,
) -> dict[str, Any]:
    """Compute Dev M1 (2018-2024, strictly < 2025-01-01, holdout_rows_analysed=0) median spreads by symbol & session."""
    pq = cast(Any, importlib.import_module("pyarrow.parquet"))

    lock_sha = assert_holdout_lock_intact(holdout_lock_path)
    manifest_path = Path(hot_cache_dir) / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing hot M1 cache manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("holdout_rows", -1)) != 0 or manifest.get("holdout_lock_sha256") != lock_sha:
        raise SafetyLockError("HOT_M1_CACHE_HOLDOUT_GUARD_MISMATCH")

    holdout_rows_analysed = 0
    max_ts_seen = 0
    by_symbol: dict[str, dict[str, Any]] = {}

    for ftmo_sym in CORE_SYMBOLS:
        meta = SYMBOL_META[ftmo_sym]
        cache_asset = str(meta["cache_asset"])
        am = manifest["assets"][cache_asset]
        folder = Path(hot_cache_dir) / am["dir"]
        scale = float(am["scale"])
        broker_point = float(meta["point"])

        ts_parts = []
        bo_parts = []
        ao_parts = []
        for year_str, ym in sorted(am["years"].items()):
            if int(year_str) >= 2025:
                raise SafetyLockError(f"HOLDOUT_YEAR_DETECTED_IN_HOT_CACHE: {year_str}")
            pq_path = folder / ym["parquet"]
            if verify_sha:
                actual_sha = sha256_file(pq_path)
                if actual_sha != ym["parquet_sha256"]:
                    raise SafetyLockError(f"HOT_CACHE_SHA_DRIFT: {cache_asset} {year_str}")
            tbl = pq.read_table(pq_path, columns=["minute", "bo", "ao"])
            ts = tbl["minute"].to_numpy().astype(np.int64) * 60
            # Strict causal holdout assertion on every row!
            n_hold = int(np.sum(ts >= HOLDOUT_START_UTC_TS))
            if n_hold > 0:
                raise SafetyLockError(f"HOLDOUT_ROWS_DETECTED: {cache_asset} {year_str} count={n_hold}")
            holdout_rows_analysed += n_hold
            if len(ts) > 0:
                max_ts_seen = max(max_ts_seen, int(ts[-1]))
            ts_parts.append(ts)
            bo_parts.append(tbl["bo"].to_numpy().astype(np.float64) / scale)
            ao_parts.append(tbl["ao"].to_numpy().astype(np.float64) / scale)

        ts_all = np.concatenate(ts_parts)
        bid_all = np.concatenate(bo_parts)
        ask_all = np.concatenate(ao_parts)
        valid = (bid_all > 0.0) & (ask_all >= bid_all)
        ts_all = ts_all[valid]
        bid_all = bid_all[valid]
        ask_all = ask_all[valid]

        spread_px = ask_all - bid_all
        mid_px = 0.5 * (ask_all + bid_all)
        spread_pts = spread_px / broker_point
        spread_bps = (spread_px / mid_px) * 10_000.0
        hours = ((ts_all // 3600) % 24).astype(np.int8)

        sess_masks = {
            "ASIA": (hours < 7) | (hours >= 21),
            "LONDON": (hours >= 7) & (hours < 12),
            "NY_OVERLAP": (hours >= 12) & (hours < 16),
            "NY_AFTERNOON": (hours >= 16) & (hours < 21),
            "OVERALL": np.ones_like(hours, dtype=bool),
        }

        sess_stats: dict[str, dict[str, Any]] = {}
        for sess_name, mask in sess_masks.items():
            cnt = int(np.sum(mask))
            if cnt == 0:
                sess_stats[sess_name] = {
                    "rows": 0,
                    "median_spread_px": 0.0,
                    "median_spread_pts": 0.0,
                    "p90_spread_pts": 0.0,
                    "median_spread_bps": 0.0,
                    "p90_spread_bps": 0.0,
                }
                continue
            sp_px = spread_px[mask]
            sp_pt = spread_pts[mask]
            sp_bp = spread_bps[mask]
            sess_stats[sess_name] = {
                "rows": cnt,
                "median_spread_px": round(float(np.median(sp_px)), 6),
                "median_spread_pts": round(float(np.median(sp_pt)), 3),
                "p90_spread_pts": round(float(np.percentile(sp_pt, 90)), 3),
                "median_spread_bps": round(float(np.median(sp_bp)), 4),
                "p90_spread_bps": round(float(np.percentile(sp_bp, 90)), 4),
            }

        med_mid = float(np.median(mid_px))
        by_symbol[ftmo_sym] = {
            "cache_asset": cache_asset,
            "dev_rows": int(len(ts_all)),
            "dev_median_mid": round(med_mid, 5),
            "sessions": sess_stats,
        }

    # Resolve Dev 1.00x total round-turn friction budgets (spread + commission + base slip)
    usdjpy_dev_mid = float(by_symbol["USDJPY"]["dev_median_mid"]) if "USDJPY" in by_symbol else 130.0
    for ftmo_sym, sym_d in by_symbol.items():
        meta = SYMBOL_META[ftmo_sym]
        ov = sym_d["sessions"]["OVERALL"]
        ref_mid = float(sym_d["dev_median_mid"])
        notional_1lot = estimate_notional_usd(
            symbol=ftmo_sym,
            volume=1.0,
            price=ref_mid,
            usdjpy_ref=usdjpy_dev_mid,
        )
        comm_rt_bps = (float(meta["dev_comm_rt_usd_per_lot"]) / notional_1lot) * 10_000.0
        base_slip_rt_bps = (float(meta["dev_base_slip_rt_px"]) / ref_mid) * 10_000.0
        stress_slip_rt_bps = (float(meta["dev_stress_slip_rt_px"]) / ref_mid) * 10_000.0
        dev_1x_rt_bps = float(ov["median_spread_bps"]) + comm_rt_bps + base_slip_rt_bps
        dev_stress_rt_bps = float(ov["median_spread_bps"]) + comm_rt_bps + stress_slip_rt_bps
        sym_d["dev_1x_budget"] = {
            "spread_rt_bps": round(float(ov["median_spread_bps"]), 4),
            "commission_rt_bps": round(comm_rt_bps, 4),
            "base_slip_rt_bps": round(base_slip_rt_bps, 4),
            "stress_slip_rt_bps": round(stress_slip_rt_bps, 4),
            "total_1x_rt_bps": round(dev_1x_rt_bps, 4),
            "total_stress_rt_bps": round(dev_stress_rt_bps, 4),
            "tracker_budget_rt_bps": round(2.0 * float(meta["tracker_oneway_budget_bps"]), 4),
        }

    return {
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": holdout_rows_analysed,
        "dev_m1_max_utc": datetime.fromtimestamp(max_ts_seen, UTC).isoformat() if max_ts_seen > 0 else None,
        "by_symbol": by_symbol,
    }
