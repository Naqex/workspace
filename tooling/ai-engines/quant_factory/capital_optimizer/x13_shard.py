"""Pure NumPy/Numba X13 Shard Worker Mode (`--x13-shard` / `run_x13_mc_shard()`).

Air-gap & Python 3.14 safety invariants:
  - Reads `.runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.{json,npz}` DIRECTLY.
  - Verifies exact `npz_sha256` AND strict `max_day < "2025-01-01"` (and `stamps[-1] < 1735689600`).
  - NEVER imports or calls `assert_holdout_locked()`, `quant_factory.data_store`, `quant_factory.prop_engine`,
    `quant_core.holdout_guard`, `duckdb`, or legacy `pass27*`/`pass28*` modules.
  - Rejects any `job_id` or output path containing forbidden X13 air-gap tokens (`2025`, `2026`, `holdout`, ...).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `holdout_rows_analysed = 0`.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from quant_core.io_utils import atomic_write_json, sha256_file

from quant_factory.capital_optimizer.black_friday_option import evaluate_black_friday_2deadline_option
from quant_factory.capital_optimizer.catalog import (
    _find_program_by_hint,
    build_default_pricing_catalog,
    load_pricing_catalog,
)
from quant_factory.capital_optimizer.constants import (
    CORE7_IDS,
    DEFAULT_CATALOG_PATH,
    DEFAULT_CORE7_BASE_RISK,
    DEFAULT_DERIVED_TAPES_DIR,
    DEFAULT_DERIVED_TAPES_STEM,
    DEFAULT_X13_SHARD_SEED,
    HOLDOUT_CUTOFF_DAY,
    HOLDOUT_CUTOFF_UTC_TS,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    PRIMARY_VARIANT_DEFAULT,
    ROOT,
    TRADING_DAYS_PER_MONTH,
    VARIANT_PHASE_CONFIGS,
    X13_FORBIDDEN_TOKENS,
)
from quant_factory.capital_optimizer.lot_sizing import assert_strict_pre_holdout_days
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.rollover_reset import (
    run_rollover_reset_sensitivity,
    verify_tapes_flat_at_reset,
)
from quant_factory.capital_optimizer.simulator import make_block_bootstrap_indices

_SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_x13_job_id(job_id: str) -> str:
    """Fail-closed validation of X13 `job_id` (zero `2025`/`2026`/`holdout`/secret tokens)."""
    jid = str(job_id or "").strip()
    if not jid or not _SAFE_JOB_ID_RE.fullmatch(jid):
        raise ValueError(f"INVALID_X13_JOB_ID: must match [A-Za-z0-9._-], got {job_id!r}")
    low = jid.lower()
    for tok in X13_FORBIDDEN_TOKENS:
        if tok in low:
            raise ValueError(f"X13_AIRGAP_JOB_ID_VIOLATION: forbidden token {tok!r} in job_id {job_id!r}")
    return jid


def _require_strict_int(val: Any, name: str, *, min_val: int | None = None) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"INVALID_X13_INT: {name} must be int (not bool), got {type(val).__name__}")
    if min_val is not None and val < min_val:
        raise ValueError(f"INVALID_X13_RANGE: {name}={val} < {min_val}")
    return int(val)


def _validate_row_timestamps_pre_holdout(row: Any, eng: str, dk: str) -> None:
    if not isinstance(row, dict):
        raise ValueError(f"FROZEN_TAPES_CORRUPT_ROW: tape {eng} day {dk} row must be dict")
    for field in ("entry", "exit"):
        raw_v = row.get(field)
        if raw_v is None:
            continue
        if isinstance(raw_v, bool):
            raise ValueError(f"FROZEN_TAPES_INVALID_TS: tape {eng} day {dk} {field} is bool")
        try:
            ts_f = float(raw_v)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"FROZEN_TAPES_INVALID_TS: tape {eng} day {dk} {field}={raw_v!r}") from exc
        if not math.isfinite(ts_f):
            raise ValueError(f"FROZEN_TAPES_INVALID_TS: tape {eng} day {dk} {field}={raw_v!r}")
        if int(ts_f) >= HOLDOUT_CUTOFF_UTC_TS:
            raise ValueError(
                f"HOLDOUT_LOCK_VIOLATION: tape {eng} day {dk} {field}={int(ts_f)} >= {HOLDOUT_CUTOFF_UTC_TS}"
            )


def _assert_safe_x13_filename(name: str) -> str:
    low = str(name).lower()
    for tok in X13_FORBIDDEN_TOKENS:
        if tok in low:
            raise ValueError(f"X13_AIRGAP_FILENAME_VIOLATION: forbidden token {tok!r} in {name!r}")
    return name


def load_frozen_tapes_v2_direct(
    *,
    tapes_dir: Path = DEFAULT_DERIVED_TAPES_DIR,
    stem: str = DEFAULT_DERIVED_TAPES_STEM,
) -> dict[str, Any]:
    """Read `frozen_9e_tapes_v2.{json,npz}` directly with strict `npz_sha256` & `max_day < 2025-01-01` guards."""
    t0 = time.perf_counter()
    base = Path(tapes_dir)
    meta_path = base / f"{stem}.json"
    npz_path = base / f"{stem}.npz"
    if not meta_path.is_file():
        raise FileNotFoundError(f"FROZEN_TAPES_JSON_MISSING: {meta_path}")
    if not npz_path.is_file():
        raise FileNotFoundError(f"FROZEN_TAPES_NPZ_MISSING: {npz_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict):
        raise ValueError(f"FROZEN_TAPES_CORRUPT_META: root JSON in {meta_path} must be object")

    expected_sha = str(meta.get("npz_sha256") or "").strip().lower()
    if not _HEX64_RE.fullmatch(expected_sha):
        raise ValueError(f"NPZ_SHA256_MISSING_OR_INVALID: {expected_sha!r}")
    actual_sha = sha256_file(npz_path).lower()
    if actual_sha != expected_sha:
        raise ValueError(f"NPZ_SHA256_MISMATCH: expected={expected_sha} actual={actual_sha}")

    ext_days = [str(d) for d in (meta.get("ext_days") or [])]
    if not ext_days:
        raise ValueError("FROZEN_TAPES_EMPTY_EXT_DAYS: ext_days must be non-empty")
    holdout_rows = assert_strict_pre_holdout_days(ext_days)
    max_day = max(ext_days)
    min_day = min(ext_days)
    if max_day >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: max_day={max_day} >= {HOLDOUT_CUTOFF_DAY}")

    raw_tapes_meta = meta.get("tapes")
    if not isinstance(raw_tapes_meta, dict) or not raw_tapes_meta:
        raise ValueError("FROZEN_TAPES_MISSING_TAPES_MAP: meta['tapes'] must be non-empty dict")

    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    max_stamp = 0
    with np.load(npz_path, allow_pickle=False) as z:
        for eng, info in raw_tapes_meta.items():
            eng_days = [str(d) for d in info["days"]]
            assert_strict_pre_holdout_days(eng_days)
            stamps_all = np.asarray(z[f"{eng}__stamps"], dtype=np.int64)
            marks_all = np.asarray(z[f"{eng}__marks"], dtype=np.float64)
            offsets = np.asarray(z[f"{eng}__offsets"], dtype=np.int64)
            if len(stamps_all) > 0:
                eng_max_st = int(stamps_all.max())
                if eng_max_st >= HOLDOUT_CUTOFF_UTC_TS:
                    raise ValueError(
                        f"HOLDOUT_LOCK_VIOLATION: tape {eng} stamp {eng_max_st} >= {HOLDOUT_CUTOFF_UTC_TS}"
                    )
                if eng_max_st > max_stamp:
                    max_stamp = eng_max_st
            eng_map: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
            rows_dict = info["rows"]
            if len(offsets) != len(eng_days) + 1:
                raise ValueError(f"FROZEN_TAPES_CORRUPT_OFFSETS: tape {eng} offsets len mismatch")
            for i, dk in enumerate(eng_days):
                a, b = int(offsets[i]), int(offsets[i + 1])
                if a < 0 or b < a or b > len(stamps_all):
                    raise ValueError(f"FROZEN_TAPES_CORRUPT_OFFSETS: tape {eng} day {dk} slice [{a}:{b}]")
                row = rows_dict[dk]
                _validate_row_timestamps_pre_holdout(row, str(eng), dk)
                eng_map[dk] = (row, stamps_all[a:b], marks_all[a:b])
            tapes[str(eng)] = eng_map

    return {
        "stem": stem,
        "schema": str(meta.get("schema", "naqex-frozen-tapes-v2")),
        "binding_sha256": str(meta.get("binding_sha256", "")),
        "npz_sha256": actual_sha,
        "ext_days": ext_days,
        "min_day": min_day,
        "max_day": max_day,
        "max_stamp_utc": max_stamp,
        "max_day_strictly_lt_cutoff": bool(max_day < HOLDOUT_CUTOFF_DAY),
        "holdout_rows_analysed": holdout_rows,
        "load_seconds": round(time.perf_counter() - t0, 4),
        "tapes": tapes,
    }


def load_red_news_calendar_direct(
    calendar_path: Path | None = None,
) -> tuple[dict[str, list[tuple[int, str]]], dict[str, Any]]:
    """Load Dev-only (`<= 2024`) red-news calendar directly without `data_store` or `duckdb`."""
    cal_dir = ROOT / "tooling" / "ai-engines" / "configs" / "calendars"
    candidates: list[Path] = []
    if calendar_path is not None:
        candidates.append(Path(calendar_path))
    else:
        # Align exact default calendar with `data_store.load_red_news_calendar()` (`red_news_official_2018_2024.json`)
        # so Dev PC and X13 worker produce bit-identical results on identical seeds.
        candidates.extend(
            [
                cal_dir / "red_news_official_2018_2024.json",
                cal_dir / "red_news_official_2018_2024_6ccy.json",
            ]
        )

    chosen = next((p for p in candidates if p.is_file()), None)
    if chosen is None:
        if calendar_path is not None:
            raise FileNotFoundError(f"RED_NEWS_CALENDAR_NOT_FOUND: {calendar_path}")
        return {}, {"loaded": False, "source": "EMPTY_NO_CALENDAR", "event_count": 0}

    raw = json.loads(chosen.read_text(encoding="utf-8"))
    by_day: dict[str, list[tuple[int, str]]] = {}
    ev_cnt = 0
    if "events_by_day" in raw:
        for dk, evs in raw["events_by_day"].items():
            ds = str(dk)
            if ds >= HOLDOUT_CUTOFF_DAY:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION: red-news calendar date {ds} >= {HOLDOUT_CUTOFF_DAY}")
            pairs = [(int(ev["utc_ts"]), str(ev["ccy"])) for ev in evs]
            by_day[ds] = pairs
            ev_cnt += len(pairs)
    elif "events" in raw:
        for ev in raw["events"]:
            ts = int(ev["utc_ts"])
            if ts >= HOLDOUT_CUTOFF_UTC_TS:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION: red-news event ts {ts} >= {HOLDOUT_CUTOFF_UTC_TS}")
            dk = datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
            by_day.setdefault(dk, []).append((ts, str(ev["ccy"])))
            ev_cnt += 1
    else:
        raise ValueError(f"Unsupported red-news calendar schema in {chosen.name}")

    return by_day, {
        "loaded": True,
        "source": chosen.name,
        "sha256": sha256_file(chosen),
        "event_count": ev_cnt,
    }


def _load_catalog_for_x13(catalog_path: Path | None, *, allow_stale: bool = True) -> dict[str, Any]:
    """Load catalog if present on worker; otherwise use offline-safe canonical default fixture."""
    target = Path(catalog_path) if catalog_path is not None else DEFAULT_CATALOG_PATH
    if target.is_file():
        return load_pricing_catalog(
            target,
            allow_fallback=False,
            enforce_freshness=True,
            allow_stale=allow_stale,
        )
    if catalog_path is not None:
        raise FileNotFoundError(f"X13_CATALOG_NOT_FOUND: {target}")
    fb = build_default_pricing_catalog()
    fb["source_path"] = "X13_BUILTIN_DEFAULT_CATALOG"
    fb["source_sha256"] = "BUILTIN_DEFAULT"
    return fb


def _numba_available() -> bool:
    try:
        import numba  # noqa: F401

        return True
    except ImportError:
        return False


def run_x13_mc_shard(
    *,
    job_id: str = "cap_v3_mc_shard0",
    shard_id: int = 0,
    num_shards: int = 1,
    n_paths: int = 2_000,
    horizon_months: int = 36,
    base_seed: int = DEFAULT_X13_SHARD_SEED,
    primary_variant: str = PRIMARY_VARIANT_DEFAULT,
    tapes_dir: Path = DEFAULT_DERIVED_TAPES_DIR,
    tapes_stem: str = DEFAULT_DERIVED_TAPES_STEM,
    calendar_path: Path | None = None,
    catalog_path: Path | None = None,
    out_dir: Path | None = None,
    use_promo_prices: bool = True,
    allow_stale_catalog: bool = True,
) -> dict[str, Any]:
    """Execute one pure NumPy/Numba X13 MC shard reading `frozen_9e_tapes_v2.{json,npz}` directly."""
    t0 = time.perf_counter()
    jid = validate_x13_job_id(job_id)
    shard_id = _require_strict_int(shard_id, "shard_id", min_val=0)
    num_shards = _require_strict_int(num_shards, "num_shards", min_val=1)
    if shard_id >= num_shards:
        raise ValueError(f"Invalid shard coordinates: shard_id={shard_id}, num_shards={num_shards}")
    n_paths = _require_strict_int(n_paths, "n_paths", min_val=1)
    horizon_months = _require_strict_int(horizon_months, "horizon_months", min_val=1)
    base_seed = _require_strict_int(base_seed, "base_seed", min_val=0)
    if primary_variant not in VARIANT_PHASE_CONFIGS:
        raise ValueError(f"Unknown primary_variant: {primary_variant!r}")

    frozen = load_frozen_tapes_v2_direct(tapes_dir=tapes_dir, stem=tapes_stem)
    ext_days = frozen["ext_days"]
    rn_cal, rn_meta = load_red_news_calendar_direct(calendar_path)
    catalog = _load_catalog_for_x13(catalog_path, allow_stale=allow_stale_catalog)

    usd_vnd = float(catalog["fx_rates"]["usd_vnd"])
    card_fx_fee = float(catalog["vn_transaction_costs"]["card_fx_buy_fee_pct"])
    horizon_days = int(horizon_months * TRADING_DAYS_PER_MONTH)
    shard_seed = int(base_seed) + int(shard_id) * 10_007

    cache = ExactTierReplayCache(ext_days, frozen["tapes"], DEFAULT_CORE7_BASE_RISK, rn_cal)
    flat_audit = verify_tapes_flat_at_reset(frozen["tapes"], engine_ids=CORE7_IDS)
    idx_shard = make_block_bootstrap_indices(
        len(ext_days),
        horizon=horizon_days,
        n_paths=n_paths,
        seed=shard_seed,
    )

    rollover = run_rollover_reset_sensitivity(
        catalog=catalog,
        cache=cache,
        idx_matrix=idx_shard,
        horizon_days=horizon_days,
        primary_var=primary_variant,
        use_promo_prices=use_promo_prices,
        usd_vnd=usd_vnd,
        card_fx_fee=card_fx_fee,
        flat_at_reset_audit=flat_audit,
    )

    ftmo_std = _find_program_by_hint(
        catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
    )
    bf_option: dict[str, Any] = {}
    if ftmo_std is not None:
        bf_option = evaluate_black_friday_2deadline_option(
            catalog=catalog,
            ftmo_std=ftmo_std,
            cache=cache,
            idx_matrix=idx_shard,
            primary_var=primary_variant,
            usd_vnd=usd_vnd,
            card_fx_fee=card_fx_fee,
        )

    elapsed = round(time.perf_counter() - t0, 3)
    payload: dict[str, Any] = {
        "schema": "naqex-capital-optimizer-x13-shard-v3",
        "job_id": jid,
        "shard_id": int(shard_id),
        "num_shards": int(num_shards),
        "shard_seed": int(shard_seed),
        "n_paths": int(n_paths),
        "horizon_months": int(horizon_months),
        "primary_variant": primary_variant,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": int(frozen["holdout_rows_analysed"]),
        "runtime": {
            "python_version": sys.version.split()[0],
            "numba_available": _numba_available(),
            "elapsed_seconds": elapsed,
            "data_store_imported": "quant_factory.data_store" in sys.modules,
            "prop_engine_imported": "quant_factory.prop_engine" in sys.modules,
            "holdout_guard_imported": "quant_core.holdout_guard" in sys.modules,
            "duckdb_imported": "duckdb" in sys.modules,
        },
        "tape_integrity": {
            "stem": frozen["stem"],
            "npz_sha256": frozen["npz_sha256"],
            "binding_sha256": frozen["binding_sha256"],
            "min_day": frozen["min_day"],
            "max_day": frozen["max_day"],
            "dev_days_count": len(ext_days),
            "max_day_strictly_lt_cutoff": frozen["max_day_strictly_lt_cutoff"],
            "cutoff_day": HOLDOUT_CUTOFF_DAY,
        },
        "red_news_calendar": rn_meta,
        "flat_at_reset_audit": flat_audit,
        "rollover_reset_sensitivity": rollover,
        "black_friday_2deadline_option": bf_option,
    }

    target_dir = out_dir
    if target_dir is None and os.environ.get("NAQEX_RESULT_DIR"):
        target_dir = Path(os.environ["NAQEX_RESULT_DIR"])
    if target_dir is not None:
        fname = _assert_safe_x13_filename(f"{jid}_shard{shard_id}.json")
        out_path = Path(target_dir) / fname
        atomic_write_json(out_path, payload, indent=2)
        payload["saved_path"] = str(out_path)

    return payload


def merge_x13_mc_shards(shards: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministically merge `K` verified X13 shard payloads (weighted by `n_paths`)."""
    if not shards:
        raise ValueError("Cannot merge empty shard list")

    ref_sha = shards[0]["tape_integrity"]["npz_sha256"]
    ref_cal_sha = (shards[0].get("red_news_calendar") or {}).get("sha256")
    ref_variant = shards[0].get("primary_variant")
    ref_horizon = _require_strict_int(shards[0].get("horizon_months"), "horizon_months", min_val=1)
    seen_ids: set[int] = set()
    total_paths = 0
    for sh in shards:
        ho = sh.get("holdout_rows_analysed", -1)
        if isinstance(ho, bool) or int(ho) != 0:
            raise ValueError("HOLDOUT_LOCK_VIOLATION: shard reports non-zero holdout_rows_analysed")
        osc = sh.get("order_send_count", -1)
        if isinstance(osc, bool) or int(osc) != 0:
            raise ValueError("ORDER_SEND_VIOLATION: shard reports non-zero order_send_count")
        if sh["tape_integrity"]["npz_sha256"] != ref_sha:
            raise ValueError("SHARD_TAPE_SHA_MISMATCH: shards were not computed on identical frozen_9e_tapes_v2")
        if (sh.get("red_news_calendar") or {}).get("sha256") != ref_cal_sha:
            raise ValueError("SHARD_CALENDAR_SHA_MISMATCH: shards used different red-news calendars")
        if sh.get("primary_variant") != ref_variant:
            raise ValueError("SHARD_VARIANT_MISMATCH: shards used different primary_variant")
        hm = _require_strict_int(sh.get("horizon_months"), "horizon_months", min_val=1)
        if hm != ref_horizon:
            raise ValueError("SHARD_HORIZON_MISMATCH: shards used different horizon_months")
        sid = _require_strict_int(sh.get("shard_id"), "shard_id", min_val=0)
        if sid in seen_ids:
            raise ValueError(f"DUPLICATE_SHARD_ID: shard_id={sid}")
        seen_ids.add(sid)
        n_p = _require_strict_int(sh.get("n_paths"), "n_paths", min_val=1)
        total_paths += n_p

    # Weighted average of rollover rows by (label, rollover_anchor_mode, midnight_floating_shock_pct)
    row_groups: dict[tuple[str, int, float], list[tuple[int, dict[str, Any]]]] = {}
    for sh in shards:
        w = _require_strict_int(sh.get("n_paths"), "n_paths", min_val=1)
        for row in sh["rollover_reset_sensitivity"]["rows"]:
            key = (str(row["label"]), int(row["rollover_anchor_mode"]), float(row["midnight_floating_shock_pct"]))
            row_groups.setdefault(key, []).append((w, row))

    num_fields = (
        "pass_24m_pct",
        "fail_eval_24m_pct",
        "pending_eval_24m_pct",
        "firm_hard_breach_pct",
        "firm_hard_breach_daily_pct",
        "firm_hard_breach_maxdd_pct",
        "funded_12m_breach_pct",
        "bot_auto_kill_pct",
        "ev_npv_24m_usd",
        "ev_npv_24m_vnd_tr",
        "p_net_le_0_24m_pct",
        "ev_per_fee_npv24",
        "delta_npv24_vs_flat_usd",
        "delta_npv24_vs_flat_vnd_tr",
        "delta_daily_breach_pp",
        "delta_pass_24m_pp",
    )
    merged_rows: list[dict[str, Any]] = []
    for _key, items in row_groups.items():
        w_sum = sum(w for w, _ in items)
        base = dict(items[0][1])
        # Medians cannot be merged via weighted average; omit shard-0 median rather than misreporting it.
        base.pop("med_npv_24m_vnd_tr", None)
        for f in num_fields:
            acc = 0.0
            for w, r in items:
                raw_val = r[f]
                if isinstance(raw_val, bool):
                    raise ValueError(f"NON_FINITE_SHARD_METRIC: field {f!r} is bool")
                fv = float(raw_val)
                if not math.isfinite(fv):
                    raise ValueError(f"NON_FINITE_SHARD_METRIC: field {f!r}={raw_val!r}")
                acc += w * fv
            base[f] = round(acc / w_sum, 2)
        merged_rows.append(base)

    return {
        "schema": "naqex-capital-optimizer-x13-merged-v3",
        "shards_merged": len(shards),
        "shard_ids": sorted(seen_ids),
        "total_paths": total_paths,
        "npz_sha256": ref_sha,
        "red_news_calendar_sha256": ref_cal_sha,
        "primary_variant": ref_variant,
        "horizon_months": ref_horizon,
        "median_merge_policy": "OMITTED_CANNOT_AVERAGE_MEDIANS",
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "flat_at_reset_verified": all(bool(sh["flat_at_reset_audit"]["flat_at_reset_verified"]) for sh in shards),
        "rollover_rows": merged_rows,
    }
