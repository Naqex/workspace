"""Layer 1: Zero-pickle precomputed derived tape cache (<0.35s load), declarative JSON config loader & Holdout Lock."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass19_us500_supertrend_yencross as p19
import pass22_gbpusd_volhigh_3engine as p22
import pass24_mtf_new_archetypes as p24
import pass27_portfolio_m1_phase_audit as p27
import pass28_final_discovery_rednews_frontier as p28
from native_ftmo_monfri_seal import ROOT, STOP, sha
from quant_core.ftmo_track_replay import profiles

CONFIGS_DIR = ROOT / "tooling/ai-engines/configs"
REGISTRY_PATH = ROOT / "planning/research/PORTFOLIO-REGISTRY.json"
DERIVED_CACHE_DIR = hcache.DEFAULT_CACHE / "_derived"
HOLDOUT_CUTOFF_DAY = "2025-01-01"


def assert_holdout_locked() -> str:
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    digest = sha(lock_path)
    if digest != clock.LOCK_SHA:
        raise ValueError(f"HOLDOUT_LOCK_SHA_MISMATCH: expected={clock.LOCK_SHA[:12]} got={digest[:12]}")
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
                        f"HOLDOUT_LOCK_VIOLATION: Tape '{eng}' day '{dk}' timestamp {int(stamps[-1])} >= STOP ({int(stop_ts)})"
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
    p = CONFIGS_DIR / "calendars" / (name if name.endswith(".json") else f"{name}.json")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {dk: [(int(ev["utc_ts"]), str(ev["ccy"])) for ev in evs] for dk, evs in raw["events_by_day"].items()}


def _save_tapes_safe_npz(cache_dir: Path, stem: str, meta: dict, tapes: dict[str, dict]) -> None:
    """Persist exact M1 minute-by-minute trade tapes using safe zero-pickle JSON + compressed NPZ arrays."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    arrays = {}
    tape_index = {}
    for eng, day_map in tapes.items():
        eng_rows = {}
        stamps_list = []
        marks_list = []
        offsets = [0]
        sorted_days = sorted(day_map.keys())
        for dk in sorted_days:
            row, stamps, marks = day_map[dk]
            # Keep only JSON-serializable scalar metadata fields in row
            eng_rows[dk] = {k: (float(v) if isinstance(v, (np.floating,)) else (int(v) if isinstance(v, (np.integer,)) else v))
                            for k, v in row.items() if isinstance(v, (str, int, float, bool, np.integer, np.floating)) or v is None}
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
    np.savez(npz_path, **arrays)  # Uncompressed NPZ on local SSD loads 5-10x faster than zlib!
    npz_sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    payload = {**meta, "npz_sha256": npz_sha, "tapes": tape_index}
    meta_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8", newline="\n")


def _load_tapes_safe_npz(cache_dir: Path, stem: str, expected_binding: str) -> tuple[dict, dict[str, dict]] | None:
    npz_path = cache_dir / f"{stem}.npz"
    meta_path = cache_dir / f"{stem}.json"
    if not (npz_path.exists() and meta_path.exists()):
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("binding_sha256") != expected_binding:
        return None
    if hashlib.sha256(npz_path.read_bytes()).hexdigest() != meta.get("npz_sha256"):
        return None
    z = np.load(npz_path, allow_pickle=False)
    tapes = {}
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


def build_or_load_frozen_tapes(
    *,
    jobs_root: Path = hcache.DEFAULT_JOBS,
    cache_dir: Path = hcache.DEFAULT_CACHE,
    derived_dir: Path = DERIVED_CACHE_DIR,
    force_rebuild: bool = False,
) -> dict:
    """Load exact M1 minute-by-minute tapes for all 9 frozen engines (<0.35s cache hit, ~15s cold rebuild)."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    reg_sha = compute_registry_engines_sha()
    binding = hashlib.sha256(f"{lock_sha}|{reg_sha}|v1".encode()).hexdigest()
    stem = "frozen_9e_tapes_v1"

    if not force_rebuild:
        hit = _load_tapes_safe_npz(derived_dir, stem, binding)
        if hit is not None:
            meta, tapes = hit
            assert_dev_series_strictly_pre_holdout(meta["ext_days"], tapes)
            assert_dev_series_strictly_pre_holdout(meta["strict_cluster_a_days"])
            return {
                "cache_hit": True,
                "load_seconds": round(time.perf_counter() - t0, 4),
                "binding_sha256": binding,
                "holdout_lock_sha256": lock_sha,
                "ext_days": meta["ext_days"],
                "strict_cluster_a_days": meta["strict_cluster_a_days"],
                "tapes": tapes,
            }

    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    assets11 = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY", "XAUUSD", "US500", "US100", "GER40")
    bundles = {a: p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map) for a in assets11}
    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in assets11}
    all_days = sorted({d for dm in day_maps.values() for d in dm})
    vol_ratios = {a: p28._compute_vol_ratio_map(bundles[a]) for a in assets11}

    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    ext_days = sorted(ref_days["extended"])
    strict_a_days = sorted(d for d in ref_days["strict"] if d < "2021-01-01")
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, swing_specs["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, swing_specs["USDJPY"])
    exp_usd = {r["day"]: (r, t, m) for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)}
    gbp_vh = {r["day"]: (r, t, m) for r, t, m in p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50)[0]}
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
    assert_dev_series_strictly_pre_holdout(ext_days, tapes)
    assert_dev_series_strictly_pre_holdout(strict_a_days)
    meta = {
        "schema": "naqex-frozen-tapes-v1",
        "built_utc": datetime.now(timezone.utc).isoformat(),
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
