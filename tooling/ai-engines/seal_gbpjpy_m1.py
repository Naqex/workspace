"""Seal GBPJPY M1 Bid/Ask (2018-2024) raw JSON pairs into SHA-verified Zstd Parquets and sync into D: SSD Hot Cache."""

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
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write

SCALE = 1000


def seal_gbpjpy(job_dir: Path, cache_dir: Path = hcache.DEFAULT_CACHE) -> dict:
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    raw_dir = job_dir / "raw-json"
    out_dir = job_dir / "development-m1"
    out_dir.mkdir(parents=True, exist_ok=True)

    years_meta = {}
    for y in clock.YEAR:
        bid_rows = json.loads((raw_dir / f"gbpjpy-m1-bid-{y}.json").read_text(encoding="utf-8"))
        ask_rows = json.loads((raw_dir / f"gbpjpy-m1-ask-{y}.json").read_text(encoding="utf-8"))
        b_map = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in bid_rows}
        a_map = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in ask_rows}
        common_ms = sorted(set(b_map.keys()) & set(a_map.keys()))
        if not common_ms:
            raise ValueError(f"No common Bid/Ask minutes for GBPJPY {y}")
        assert START * 1000 <= common_ms[0] <= common_ms[-1] < STOP * 1000, f"Holdout/clock leak in GBPJPY {y}"

        mins = np.array([ms // 60000 for ms in common_ms], dtype=np.int64)
        b_arr = np.array([b_map[ms] for ms in common_ms], dtype=np.float64)
        a_arr = np.array([a_map[ms] for ms in common_ms], dtype=np.float64)
        # Ensure non-negative spread integrity (fix tiny 1-tick feed anomalies conservatively: ask = max(ask, bid))
        crossed = int(np.sum(a_arr[:, 0] < b_arr[:, 0]))
        a_arr = np.maximum(a_arr, b_arr)

        cols = {"minute": mins}
        for i, name in enumerate(("bo", "bh", "bl", "bc")):
            cols[name] = np.rint(b_arr[:, i] * SCALE).astype(np.int64)
        for i, name in enumerate(("ao", "ah", "al", "ac")):
            cols[name] = np.rint(a_arr[:, i] * SCALE).astype(np.int64)

        pfile = out_dir / f"GBPJPY-M1-BIDASK-{y}.parquet"
        pq.write_table(pa.table(cols), pfile, compression="zstd")
        med_spread_pips = float(np.median(a_arr[:, 0] - b_arr[:, 0]) * 100.0)
        years_meta[str(y)] = {
            "parquet": pfile.name,
            "parquet_sha256": sha(pfile),
            "minutes": int(len(mins)),
            "bytes": pfile.stat().st_size,
            "crossed_clamped": crossed,
            "median_spread_pips": round(med_spread_pips, 2),
        }
        print(f"SEALED GBPJPY {y}: {len(mins):,} mins | med_spread={med_spread_pips:.2f} pips | {pfile.stat().st_size/1e6:.1f} MB", flush=True)

    manifest = {
        "schema": "naqex-gbpjpy-m1-bidask-v1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "source": "dukascopy-node-m1-bid-ask-paired",
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "native_Ask": True,
        "scale": SCALE,
        "years": years_meta,
    }
    mpath = out_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Sync sealed GBPJPY into D: SSD Hot M1 Parquet Cache!
    dst_dir = cache_dir / "gbpjpy"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for y, ym in years_meta.items():
        src = out_dir / ym["parquet"]
        dst = dst_dir / ym["parquet"]
        shutil.copy2(src, dst)
        assert sha(dst) == ym["parquet_sha256"]
    hot_m = read(cache_dir / "manifest.json")
    hot_m["assets"]["GBPJPY"] = {
        "dir": "gbpjpy",
        "native_Ask": True,
        "scale": SCALE,
        "source_manifest_sha256": sha(mpath),
        "years": {
            y: {k: ym[k] for k in ("parquet", "parquet_sha256", "minutes", "bytes")}
            for y, ym in years_meta.items()
        },
    }
    hot_m["total_bytes"] = sum(v["bytes"] for a in hot_m["assets"].values() for v in a["years"].values())
    (cache_dir / "manifest.json").write_text(json.dumps(hot_m, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("GBPJPY_SEALED_AND_CACHED_ON_D_SSD", flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, default=Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\pass21-gbpjpy-m1-20261123"))
    args = parser.parse_args()
    seal_gbpjpy(args.job)
