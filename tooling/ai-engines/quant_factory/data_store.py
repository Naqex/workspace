"""Layer 1: Zero-pickle precomputed derived tape cache (<0.30s load), declarative JSON config loader & Holdout Lock."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES_DIR.parents[1]
STOP = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())
LOCK_SHA = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"
DEFAULT_JOBS = Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs")
DEFAULT_CACHE = ROOT / ".runtime" / "hot-m1-cache"

CONFIGS_DIR = ROOT / "tooling/ai-engines/configs"
REGISTRY_PATH = ROOT / "planning/research/PORTFOLIO-REGISTRY.json"
DERIVED_CACHE_DIR = DEFAULT_CACHE / "_derived"
HOLDOUT_CUTOFF_DAY = "2025-01-01"

_TAPE_BUILDER_FILES: tuple[str, ...] = (
    "pass24_mtf_new_archetypes.py",
    "pass27_portfolio_m1_phase_audit.py",
    "pass28_final_discovery_rednews_frontier.py",
    "whitebox_discovery.py",
)


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace a text file after flush + fsync (zero torn-write corruption)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            temp_path = Path(fh.name)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def assert_holdout_locked() -> str:
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    digest = _sha256_file(lock_path)
    if digest != LOCK_SHA:
        raise ValueError(f"HOLDOUT_LOCK_SHA_MISMATCH: expected={LOCK_SHA[:12]} got={digest[:12]}")
    return digest


def assert_dev_series_strictly_pre_holdout(
    days: list[str] | tuple[str, ...],
    tapes: dict[str, dict] | None = None,
    *,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
    stop_ts: int = STOP,
) -> None:
    """Programmatically verify loaded dev days and timestamps stay strictly `< 2025-01-01` (`stamps[-1] < STOP`)."""
    bad_days = [str(d) for d in days if str(d) >= cutoff_day]
    if bad_days:
        raise ValueError(
            f"HOLDOUT_LOCK_VIOLATION: Dev day series contains holdout dates >= {cutoff_day}: {bad_days[:5]}"
        )
    if tapes is not None:
        for eng, day_map in tapes.items():
            for dk, item in day_map.items():
                if str(dk) >= cutoff_day:
                    raise ValueError(
                        f"HOLDOUT_LOCK_VIOLATION: Tape '{eng}' contains holdout day '{dk}' >= {cutoff_day}"
                    )
                stamps = item[1]
                if len(stamps) > 0 and int(stamps[-1]) >= int(stop_ts):
                    raise ValueError(
                        f"HOLDOUT_LOCK_VIOLATION: Tape '{eng}' day '{dk}' "
                        f"timestamp {int(stamps[-1])} >= STOP ({int(stop_ts)})"
                    )


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_firm_config(name: str) -> dict:
    p = CONFIGS_DIR / "firms" / (name if name.endswith(".json") else f"{name}.json")
    return json.loads(p.read_text(encoding="utf-8"))


def load_profile_config(name: str) -> dict:
    p = CONFIGS_DIR / "profiles" / (name if name.endswith(".json") else f"{name}.json")
    return json.loads(p.read_text(encoding="utf-8"))


def load_red_news_calendar(name: str = "red_news_official_2018_2024") -> dict[str, list[tuple[int, str]]]:
    """Load red-news calendar supporting both `events_by_day` and flat `events` schemas (or `quant_core.red_news`)."""
    p = CONFIGS_DIR / "calendars" / (name if name.endswith(".json") else f"{name}.json")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if "events_by_day" in raw:
        return {
            str(dk): [(int(ev["utc_ts"]), str(ev["ccy"])) for ev in evs]
            for dk, evs in raw["events_by_day"].items()
        }
    if "events" in raw:
        by_day: dict[str, list[tuple[int, str]]] = {}
        for ev in raw["events"]:
            ts = int(ev["utc_ts"])
            dk = datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
            by_day.setdefault(dk, []).append((ts, str(ev["ccy"])))
        return by_day
    raise ValueError(f"Unsupported red-news calendar schema in {p.name}: expected 'events_by_day' or 'events'")


def compute_tapes_binding(
    lock_sha: str,
    reg_sha: str,
    *,
    profile_mode: str = "Swing",
    cache_dir: Path = DEFAULT_CACHE,
    builders_dir: Path = AI_ENGINES_DIR,
) -> tuple[str, str]:
    """Compute builder-aware cryptographic cache binding `(binding_sha256, stem)`.

    Hashes Holdout lock SHA, registry engines SHA, `profile_mode`, `hot-m1-cache/manifest.json`
    (if present), and SHA-256 of the core tape builder source files so any upstream signal/lookahead
    fix automatically invalidates stale derived caches.
    """
    parts: list[str] = [lock_sha, reg_sha, str(profile_mode), "v2"]
    manifest_path = cache_dir / "manifest.json"
    if manifest_path.is_file():
        parts.append(f"manifest:{_sha256_file(manifest_path)}")
    else:
        parts.append("manifest:MISSING")

    for fname in _TAPE_BUILDER_FILES:
        fpath = builders_dir / fname
        if fpath.is_file():
            parts.append(f"{fname}:{_sha256_file(fpath)}")
        else:
            parts.append(f"{fname}:MISSING")

    binding = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return binding, "frozen_9e_tapes_v2"


def _save_tapes_safe_npz(cache_dir: Path, stem: str, meta: dict, tapes: dict[str, dict]) -> None:
    """Persist exact M1 minute-by-minute trade tapes atomically using zero-pickle JSON + uncompressed NPZ."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    tape_index: dict[str, dict] = {}
    for eng, day_map in tapes.items():
        eng_rows = {}
        stamps_list = []
        marks_list = []
        offsets = [0]
        sorted_days = sorted(day_map.keys())
        for dk in sorted_days:
            row, stamps, marks = day_map[dk]
            # Keep only JSON-serializable scalar metadata fields in row
            eng_rows[dk] = {
                k: (float(v) if isinstance(v, (np.floating,)) else (int(v) if isinstance(v, (np.integer,)) else v))
                for k, v in row.items()
                if isinstance(v, (str, int, float, bool, np.integer, np.floating)) or v is None
            }
            stamps_list.append(np.asarray(stamps, dtype=np.int64))
            marks_list.append(np.asarray(marks, dtype=np.float64))
            offsets.append(offsets[-1] + len(stamps))
        tape_index[eng] = {"days": sorted_days, "rows": eng_rows}
        if stamps_list:
            arrays[f"{eng}__stamps"] = np.concatenate(stamps_list)
            arrays[f"{eng}__marks"] = np.concatenate(marks_list, axis=0)
            arrays[f"{eng}__offsets"] = np.asarray(offsets, dtype=np.int64)
        else:
            arrays[f"{eng}__stamps"] = np.empty(0, dtype=np.int64)
            arrays[f"{eng}__marks"] = np.empty((0, 4), dtype=np.float64)
            arrays[f"{eng}__offsets"] = np.zeros(1, dtype=np.int64)

    npz_path = cache_dir / f"{stem}.npz"
    meta_path = cache_dir / f"{stem}.json"
    tmp_npz: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=cache_dir,
            prefix=f".{stem}.",
            suffix=".npz.tmp",
            delete=False,
        ) as fh:
            np.savez(fh, **cast(Any, arrays))  # Uncompressed NPZ on local SSD loads 5-10x faster than zlib
            fh.flush()
            os.fsync(fh.fileno())
            tmp_npz = Path(fh.name)
        npz_sha = _sha256_file(tmp_npz)
        os.replace(tmp_npz, npz_path)
        tmp_npz = None
    finally:
        if tmp_npz is not None:
            tmp_npz.unlink(missing_ok=True)

    payload = {**meta, "npz_sha256": npz_sha, "tapes": tape_index}
    _atomic_write_text(meta_path, json.dumps(payload, ensure_ascii=False))


def _load_tapes_safe_npz(cache_dir: Path, stem: str, expected_binding: str) -> tuple[dict, dict[str, dict]] | None:
    npz_path = cache_dir / f"{stem}.npz"
    meta_path = cache_dir / f"{stem}.json"
    if not (npz_path.exists() and meta_path.exists()):
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("binding_sha256") != expected_binding:
        return None
    if _sha256_file(npz_path) != meta.get("npz_sha256"):
        return None
    tapes: dict[str, dict] = {}
    with np.load(npz_path, allow_pickle=False) as z:
        for eng, info in meta["tapes"].items():
            stamps_all = z[f"{eng}__stamps"]
            marks_all = z[f"{eng}__marks"]
            offsets = z[f"{eng}__offsets"]
            eng_map = {}
            for i, dk in enumerate(info["days"]):
                a, b = int(offsets[i]), int(offsets[i + 1])
                eng_map[dk] = (info["rows"][dk], stamps_all[a:b], marks_all[a:b])
            tapes[eng] = eng_map
    return meta, tapes


def compute_registry_engines_sha() -> str:
    if not REGISTRY_PATH.exists():
        return "NO_REG"
    reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps(reg.get("engines", []), sort_keys=True).encode("utf-8")).hexdigest()


def _merge_ext_days_with_tapes(ext_days: list[str] | tuple[str, ...], tapes: dict[str, dict]) -> list[str]:
    """Ensure `ext_days` is the sorted union of reference days and every engine tape day (RC-6)."""
    merged = {str(d) for d in ext_days}
    for day_map in tapes.values():
        merged.update(str(dk) for dk in day_map)
    return sorted(merged)


def build_or_load_frozen_tapes(
    *,
    jobs_root: Path = DEFAULT_JOBS,
    cache_dir: Path = DEFAULT_CACHE,
    derived_dir: Path = DERIVED_CACHE_DIR,
    force_rebuild: bool = False,
    profile_mode: str = "Swing",
) -> dict:
    """Load exact M1 minute-by-minute tapes for all 9 frozen engines (<0.30s warm hit, ~15s cold rebuild)."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    reg_sha = compute_registry_engines_sha()
    binding, stem = compute_tapes_binding(
        lock_sha,
        reg_sha,
        profile_mode=profile_mode,
        cache_dir=cache_dir,
    )

    if not force_rebuild:
        hit = _load_tapes_safe_npz(derived_dir, stem, binding)
        if hit is not None:
            meta, tapes = hit
            ext_days = _merge_ext_days_with_tapes(meta["ext_days"], tapes)
            assert_dev_series_strictly_pre_holdout(ext_days, tapes)
            assert_dev_series_strictly_pre_holdout(meta["strict_cluster_a_days"])
            return {
                "cache_hit": True,
                "load_seconds": round(time.perf_counter() - t0, 4),
                "binding_sha256": binding,
                "holdout_lock_sha256": lock_sha,
                "ext_days": ext_days,
                "strict_cluster_a_days": meta["strict_cluster_a_days"],
                "tapes": tapes,
            }

    # Cold-rebuild branch ONLY: defer all heavy pyarrow / pass5..pass28 imports here
    import pass11_portfolio as portfolio
    import pass14_intel_top15_batch as p14
    import pass17_usdjpy_forensic_cross as p17
    import pass19_us500_supertrend_yencross as p19
    import pass22_gbpusd_volhigh_3engine as p22
    import pass24_mtf_new_archetypes as p24
    import pass27_portfolio_m1_phase_audit as p27
    import pass28_final_discovery_rednews_frontier as p28
    from quant_core.ftmo_track_replay import profiles

    specs, _ = profiles()
    mode_specs = specs[profile_mode]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {
        datetime.fromtimestamp(int(t), UTC).date(): float(cv) for t, cv in zip(ts_j, c_j, strict=True)
    }

    assets11 = (
        "USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD",
        "USDCAD", "EURJPY", "XAUUSD", "US500", "US100", "GER40",
    )
    bundles = {a: p24.build_unified_asset(a, jobs_root, cache_dir, mode_specs, usdjpy_close_map) for a in assets11}
    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in assets11}
    all_days = sorted({d for dm in day_maps.values() for d in dm})
    vol_ratios = {a: p28._compute_vol_ratio_map(bundles[a]) for a in assets11}

    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    ext_days = sorted(ref_days["extended"])
    strict_a_days = sorted(d for d in ref_days["strict"] if d < "2021-01-01")
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, mode_specs["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, mode_specs["USDJPY"])
    exp_usd = {
        r["day"]: (r, t, m)
        for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
    }
    gbp_vh_rows = p22.build_gbpusd_volhigh_tape(
        gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50
    )[0]
    gbp_vh = {r["day"]: (r, t, m) for r, t, m in gbp_vh_rows}
    for eng_d, aname in ((ref_trades, "USDJPY"), (exp_usd, "USDJPY"), (gbp_vh, "GBPUSD")):
        for _dk, (r, _t, _m) in eng_d.items():
            r["asset"] = aname

    tapes = {
        "E1_USDJPY_TOKYO": ref_trades,
        "E2_USDJPY_EXP80": exp_usd,
        "E3_GBPUSD_VH": gbp_vh,
        "E4_US100_SESS40": p27.build_us100_e4_tape(bundles["US100"]),
        "E5_US100_RS1130": p27.build_us100_e5_tape(bundles, day_maps, all_days),
        "E6_EURJPY_VOLCOMP": p28.build_volcomp_m1_tape(bundles["EURJPY"], vol_ratios["EURJPY"], thr=0.75, sl_atr=0.75),
        "E7_USDJPY_NY10ET": p28.build_usdjpy_ny_risk_10et_m1_tape(bundles, day_maps, all_days, thr=0.25, sl_atr=0.75),
        "S6_FX_USD_BSK": p27.build_fx_usd_basket_s6_tape(bundles, day_maps, all_days),
        "S7_XAU_EXP120": p27.build_xau_exp120_s7_tape(bundles["XAUUSD"]),
    }
    ext_days = _merge_ext_days_with_tapes(ext_days, tapes)
    assert_dev_series_strictly_pre_holdout(ext_days, tapes)
    assert_dev_series_strictly_pre_holdout(strict_a_days)
    meta = {
        "schema": "naqex-frozen-tapes-v2",
        "profile_mode": profile_mode,
        "built_utc": datetime.now(UTC).isoformat(),
        "binding_sha256": binding,
        "holdout_lock_sha256": lock_sha,
        "ext_days": ext_days,
        "strict_cluster_a_days": strict_a_days,
    }
    _save_tapes_safe_npz(derived_dir, stem, meta, tapes)
    return {
        "cache_hit": False,
        "load_seconds": round(time.perf_counter() - t0, 4),
        "binding_sha256": binding,
        "holdout_lock_sha256": lock_sha,
        "ext_days": ext_days,
        "strict_cluster_a_days": strict_a_days,
        "tapes": tapes,
    }
