"""Build and read the local D: SSD Hot M1 Parquet Cache (~240 MB) from sealed E: sources (UTC 2018-2024)."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as clock
import pass13_us500_explicit as us500
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write
from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_ts

DEFAULT_JOBS = Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs")
DEFAULT_CACHE = ROOT / ".runtime" / "hot-m1-cache"

FX_SOURCES = {
    "USDJPY": ("pass7b-usdjpy-qdm-equity-20261120/development-m1", 1000, True),
    "GBPUSD": ("pass11-gbpusd-m1-20261120/development-m1", 100000, True),
    "EURUSD": ("pass13-triple-track-20261123/data/eurusd-m1", 100000, True),
    "XAUUSD": ("pass13-triple-track-20261123/data/xauusd-m1", 100, False),
}


def _verify_holdout_lock_file() -> None:
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    try:
        lock_doc = read(lock_path)
        lock_sha = sha(lock_path)
    except Exception as exc:
        raise HoldoutLockError(f"Holdout lock file unreadable or corrupt: {exc}") from exc
    if not isinstance(lock_doc, dict) or lock_sha != clock.LOCK_SHA:
        raise HoldoutLockError("Holdout lock SHA mismatch")


def build_cache(jobs_root: Path = DEFAULT_JOBS, cache_dir: Path = DEFAULT_CACHE) -> dict:
    _verify_holdout_lock_file()
    cache_dir.mkdir(parents=True, exist_ok=True)
    assets_meta = {}
    t0 = time.monotonic()

    # 1. Copy & SHA-verify the 4 already-sealed parquet datasets (USDJPY, GBPUSD, EURUSD, XAUUSD)
    for asset, (rel_dir, scale, native_ask) in FX_SOURCES.items():
        src_dir = jobs_root / rel_dir
        src_manifest = read(src_dir / "manifest.json")
        dst_dir = cache_dir / asset.lower()
        dst_dir.mkdir(parents=True, exist_ok=True)
        years_out = {}
        for y in clock.YEAR:
            ym = src_manifest["years"][str(y)]
            fname = ym["parquet"]
            src_file = src_dir / fname
            dst_file = dst_dir / fname
            expected_sha = ym["parquet_sha256"]
            if not dst_file.exists() or sha(dst_file) != expected_sha:
                if sha(src_file) != expected_sha:
                    raise HoldoutLockError(f"Source SHA mismatch for {asset} {y}")
                shutil.copy2(src_file, dst_file)
                if sha(dst_file) != expected_sha:
                    raise HoldoutLockError(f"Copied SHA mismatch for {asset} {y}")
            years_out[str(y)] = {
                "parquet": fname,
                "parquet_sha256": expected_sha,
                "minutes": int(ym["minutes"]),
                "bytes": dst_file.stat().st_size,
            }
        assets_meta[asset] = {
            "dir": asset.lower(),
            "native_Ask": native_ask,
            "scale": scale,
            "source_manifest_sha256": sha(src_dir / "manifest.json"),
            "years": years_out,
        }
        total_mb = sum(v["bytes"] for v in years_out.values()) / (1024 * 1024)
        print(f"HOT_CACHE {asset:6s}: 7 parquets verified ({total_mb:.1f} MB)", flush=True)

    # 2. Convert sealed US500 Explicit M1 Bid/Ask JSONs (680 MB) -> compact Zstd parquets (~35 MB)
    us_dir = cache_dir / "us500"
    us_dir.mkdir(parents=True, exist_ok=True)
    us_years = {}
    us_scale = 1000
    for y in clock.YEAR:
        dst_file = us_dir / f"US500-M1-BIDASK-{y}.parquet"
        meta_file = us_dir / f"{y}.json"
        if dst_file.exists() and meta_file.exists():
            rec = read(meta_file)
            if sha(dst_file) == rec["parquet_sha256"]:
                us_years[str(y)] = rec
                continue
        times, quotes, ymeta = us500.load_explicit_year(jobs_root, y)
        enforce_pre_holdout_ts(times, START, STOP, context=f"hot_m1_cache.build:US500:{y}")
        mins = (times // 60).astype(np.int64)
        cols = {"minute": mins}
        for idx, cname in enumerate(("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")):
            cols[cname] = np.rint(quotes[:, idx] * us_scale).astype(np.int64)
        pq.write_table(pa.table(cols), dst_file, compression="zstd")
        rec = {
            "parquet": dst_file.name,
            "parquet_sha256": sha(dst_file),
            "minutes": int(len(mins)),
            "bytes": dst_file.stat().st_size,
            "source_quarters": ymeta["quarters"],
        }
        meta_file.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
        us_years[str(y)] = rec
    assets_meta["US500"] = {
        "dir": "us500",
        "native_Ask": True,
        "scale": us_scale,
        "source_policy": "paired-explicit-source-M1-v1",
        "years": us_years,
    }
    us_mb = sum(v["bytes"] for v in us_years.values()) / (1024 * 1024)
    print(f"HOT_CACHE US500 : 7 parquets sealed ({us_mb:.1f} MB from 680 MB JSON)", flush=True)

    manifest = {
        "schema": "naqex-hot-m1-cache-v1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "total_bytes": sum(
            v["bytes"] for a in assets_meta.values() for v in a["years"].values()
        ),
        "assets": assets_meta,
    }
    mpath = cache_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        f"HOT_CACHE READY: {manifest['total_bytes'] / (1024 * 1024):.1f} MB total in {manifest['elapsed_seconds']}s",
        flush=True,
    )
    return manifest


def load_asset(asset: str, cache_dir: Path = DEFAULT_CACHE, *, verify_sha: bool = True):
    """Fast load of all 7 Development years (2018-2024) from D: SSD Hot Cache.

    Returns (times_sec: int64[N], quotes: float64[N, 8 or 4], asset_meta: dict).
    """
    _verify_holdout_lock_file()
    try:
        manifest = read(cache_dir / "manifest.json")
    except Exception as exc:
        raise HoldoutLockError(f"Hot cache manifest invalid or unreadable: {exc}") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("holdout_rows") != 0
        or manifest.get("holdout_lock_sha256") != clock.LOCK_SHA
    ):
        raise HoldoutLockError("Hot cache holdout guard mismatch")
    try:
        am = manifest["assets"][asset]
        folder = cache_dir / am["dir"]
        scale = float(am["scale"])
        cols = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac") if am["native_Ask"] else ("bo", "bh", "bl", "bc")
    except Exception as exc:
        raise HoldoutLockError(f"Hot cache manifest schema invalid for {asset}: {exc}") from exc
    ts_parts, q_parts = [], []
    for y in clock.YEAR:
        try:
            ym = am["years"][str(y)]
            path = folder / ym["parquet"]
            expected_sha = ym["parquet_sha256"]
        except Exception as exc:
            raise HoldoutLockError(f"Hot cache year metadata missing for {asset} {y}: {exc}") from exc
        if verify_sha:
            try:
                actual_sha = sha(path)
            except Exception as exc:
                raise HoldoutLockError(f"Hot cache parquet unreadable for {asset} {y}: {exc}") from exc
            if actual_sha != expected_sha:
                raise HoldoutLockError(f"Hot cache SHA drift: {asset} {y}")
        tbl = pq.read_table(path, columns=["minute", *cols])
        ts = tbl["minute"].to_numpy() * 60
        enforce_pre_holdout_ts(ts, START, STOP, context=f"hot_m1_cache.load:{asset}:{y}")
        q = np.column_stack([tbl[c].to_numpy() for c in cols]).astype(np.float64) / scale
        ts_parts.append(ts)
        q_parts.append(q)
    times = np.concatenate(ts_parts)
    quotes = np.vstack(q_parts)
    if not bool((np.diff(times) > 0).all()):
        raise HoldoutLockError(f"Hot cache non-monotonic timestamps for {asset}")
    return times, quotes, am


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    build_cache(args.jobs, args.cache)
    if args.benchmark:
        t0 = time.monotonic()
        for sym in ("USDJPY", "GBPUSD", "EURUSD", "XAUUSD", "US500"):
            ts, q, _ = load_asset(sym, args.cache, verify_sha=False)
            print(f"  BENCH_LOAD {sym:6s}: {len(ts):,} bars ({q.shape[1]} cols)", flush=True)
        print(f"ALL 5 ASSETS LOADED IN {time.monotonic() - t0:.2f}s", flush=True)
