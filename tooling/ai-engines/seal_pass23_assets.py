"""Seal Pass 23 M1 Bid/Ask raw JSON pairs (XAUUSD, US100, GER40; 2018-2024) into Zstd Parquets & D: SSD Hot Cache."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha

ASSET_SPECS = {
    "XAUUSD": {"prefix": "xauusd", "scale": 100, "job_sub": "pass23-xauusd-m1-20261123", "unit": "USD/oz"},
    "US100": {"prefix": "us100", "scale": 1000, "job_sub": "pass23-us100-m1-20261123", "unit": "pts"},
    "GER40": {"prefix": "ger40", "scale": 1000, "job_sub": "pass23-ger40-m1-20261123", "unit": "pts"},
}


def seal_asset(asset: str, jobs_root: Path = hcache.DEFAULT_JOBS, cache_dir: Path = hcache.DEFAULT_CACHE) -> dict:
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    cfg = ASSET_SPECS[asset]
    prefix, scale, unit = cfg["prefix"], cfg["scale"], cfg["unit"]
    job_dir = jobs_root / cfg["job_sub"]
    raw_dir = job_dir / "raw-json"
    out_dir = job_dir / "development-m1"
    out_dir.mkdir(parents=True, exist_ok=True)

    years_meta = {}
    for y in clock.YEAR:
        bid_rows = json.loads((raw_dir / f"{prefix}-m1-bid-{y}.json").read_text(encoding="utf-8"))
        ask_rows = json.loads((raw_dir / f"{prefix}-m1-ask-{y}.json").read_text(encoding="utf-8"))
        b_map = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in bid_rows}
        a_map = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in ask_rows}
        common_ms = sorted(set(b_map.keys()) & set(a_map.keys()))
        if not common_ms:
            raise ValueError(f"No common Bid/Ask minutes for {asset} {y}")
        assert START * 1000 <= common_ms[0] <= common_ms[-1] < STOP * 1000, f"Holdout/clock leak in {asset} {y}"

        mins = np.array([ms // 60000 for ms in common_ms], dtype=np.int64)
        b_arr = np.array([b_map[ms] for ms in common_ms], dtype=np.float64)
        a_arr = np.array([a_map[ms] for ms in common_ms], dtype=np.float64)
        crossed = int(np.sum(a_arr[:, 0] < b_arr[:, 0]))
        a_arr = np.maximum(a_arr, b_arr)

        cols = {"minute": mins}
        for i, name in enumerate(("bo", "bh", "bl", "bc")):
            cols[name] = np.rint(b_arr[:, i] * scale).astype(np.int64)
        for i, name in enumerate(("ao", "ah", "al", "ac")):
            cols[name] = np.rint(a_arr[:, i] * scale).astype(np.int64)

        pfile = out_dir / f"{asset}-M1-BIDASK-{y}.parquet"
        pq.write_table(pa.table(cols), pfile, compression="zstd")
        med_spread = float(np.median(a_arr[:, 0] - b_arr[:, 0]))
        p90_spread = float(np.percentile(a_arr[:, 0] - b_arr[:, 0], 90))
        years_meta[str(y)] = {
            "parquet": pfile.name,
            "parquet_sha256": sha(pfile),
            "minutes": int(len(mins)),
            "bytes": pfile.stat().st_size,
            "crossed_clamped": crossed,
            "median_spread": round(med_spread, 4),
            "p90_spread": round(p90_spread, 4),
            "spread_unit": unit,
        }
        print(
            f"SEALED {asset:6s} {y}: {len(mins):,} mins | med_spread={med_spread:.3f} {unit} (p90={p90_spread:.3f}) | {pfile.stat().st_size/1e6:.1f} MB",
            flush=True,
        )

    manifest = {
        "schema": f"naqex-{prefix}-m1-bidask-v1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "source": "dukascopy-node-m1-bid-ask-paired",
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "native_Ask": True,
        "scale": scale,
        "years": years_meta,
    }
    mpath = out_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Sync sealed Parquets into D: SSD Hot Cache (clean stale Bid-only files if upgrading XAUUSD)
    dst_dir = cache_dir / prefix
    if dst_dir.exists():
        for old_p in dst_dir.glob("*.parquet"):
            if old_p.name not in {ym["parquet"] for ym in years_meta.values()}:
                old_p.unlink()
    dst_dir.mkdir(parents=True, exist_ok=True)
    for y, ym in years_meta.items():
        src = out_dir / ym["parquet"]
        dst = dst_dir / ym["parquet"]
        shutil.copy2(src, dst)
        assert sha(dst) == ym["parquet_sha256"]

    hot_m = read(cache_dir / "manifest.json")
    hot_m["assets"][asset] = {
        "dir": prefix,
        "native_Ask": True,
        "scale": scale,
        "source_manifest_sha256": sha(mpath),
        "years": {
            y: {k: ym[k] for k in ("parquet", "parquet_sha256", "minutes", "bytes")}
            for y, ym in years_meta.items()
        },
    }
    hot_m["total_bytes"] = sum(v["bytes"] for a in hot_m["assets"].values() for v in a["years"].values())
    (cache_dir / "manifest.json").write_text(json.dumps(hot_m, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{asset}_SEALED_AND_CACHED_ON_D_SSD (total_cache={hot_m['total_bytes']/1e6:.1f} MB)", flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", nargs="+", default=["XAUUSD", "US100", "GER40"])
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    args = parser.parse_args()
    for a in args.assets:
        seal_asset(a.upper(), args.jobs, args.cache)


if __name__ == "__main__":
    main()
