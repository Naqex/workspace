"""Seal 2025-2026 Native M1 Bid/Ask Holdout JSONs into Zstd Parquets under .runtime/holdout-m1-cache/ (never modifies hot-m1-cache)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import hot_m1_cache as hcache
from native_ftmo_monfri_seal import ROOT, STOP, sha

HOLDOUT_CACHE = ROOT / ".runtime" / "holdout-m1-cache"
DEFAULT_HOLDOUT_JOB = hcache.DEFAULT_JOBS / "holdout-2025-2026-m1-20261123"

ASSET_SCALES = {
    "USDJPY": ("usdjpy", 1000, "px"),
    "GBPUSD": ("gbpusd", 100000, "px"),
    "EURUSD": ("eurusd", 100000, "px"),
    "GBPJPY": ("gbpjpy", 1000, "px"),
    "AUDUSD": ("audusd", 100000, "px"),
    "USDCAD": ("usdcad", 100000, "px"),
    "EURJPY": ("eurjpy", 1000, "px"),
    "XAUUSD": ("xauusd", 100, "USD/oz"),
    "US500":  ("us500", 1000, "pts"),
    "US100":  ("us100", 1000, "pts"),
}


def seal_holdout_all(job_dir: Path = DEFAULT_HOLDOUT_JOB, dst_cache: Path = HOLDOUT_CACHE) -> dict:
    raw_dir = job_dir / "raw-json"
    out_root = job_dir / "holdout-m1"
    out_root.mkdir(parents=True, exist_ok=True)
    dst_cache.mkdir(parents=True, exist_ok=True)

    assets_meta = {}
    for asset, (prefix, scale, unit) in ASSET_SCALES.items():
        years_meta = {}
        dst_dir = dst_cache / prefix
        dst_dir.mkdir(parents=True, exist_ok=True)
        for y in ("2025", "2026"):
            bf = raw_dir / f"{prefix}-m1-bid-{y}.json"
            af = raw_dir / f"{prefix}-m1-ask-{y}.json"
            if not (bf.exists() and af.exists()):
                continue
            bid_rows = json.loads(bf.read_text(encoding="utf-8"))
            ask_rows = json.loads(af.read_text(encoding="utf-8"))
            if not bid_rows or not ask_rows:
                continue
            b_map = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in bid_rows}
            a_map = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in ask_rows}
            common_ms = sorted(ms for ms in (set(b_map.keys()) & set(a_map.keys())) if ms >= STOP * 1000)
            if not common_ms:
                continue
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

            pfile = out_root / f"{asset}-M1-BIDASK-{y}.parquet"
            pq.write_table(pa.table(cols), pfile, compression="zstd")
            dst_file = dst_dir / pfile.name
            shutil.copy2(pfile, dst_file)
            digest = sha(dst_file)
            assert digest == sha(pfile)
            med_sp = float(np.median(a_arr[:, 0] - b_arr[:, 0]))
            first_iso = datetime.fromtimestamp(int(mins[0]) * 60, timezone.utc).isoformat()
            last_iso = datetime.fromtimestamp(int(mins[-1]) * 60, timezone.utc).isoformat()
            years_meta[y] = {
                "parquet": pfile.name,
                "parquet_sha256": digest,
                "minutes": int(len(mins)),
                "bytes": dst_file.stat().st_size,
                "first_utc": first_iso,
                "last_utc": last_iso,
                "crossed_clamped": crossed,
                "median_spread": round(med_sp, 5),
                "spread_unit": unit,
            }
            print(f"SEALED_HOLDOUT {asset:6s} {y}: {len(mins):,} mins ({first_iso[:10]}..{last_iso[:10]}) med_sp={med_sp:.4f} {unit}", flush=True)
        assets_meta[asset] = {"dir": prefix, "native_Ask": True, "scale": scale, "years": years_meta}

    manifest = {
        "schema": "naqex-holdout-m1-cache-v1",
        "protocol_commit": "521926f",
        "sealed_utc": datetime.now(timezone.utc).isoformat(),
        "total_bytes": sum(ym["bytes"] for a in assets_meta.values() for ym in a["years"].values()),
        "assets": assets_meta,
    }
    mpath = dst_cache / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"HOLDOUT_CACHE_SEALED: {len(assets_meta)} assets, {manifest['total_bytes']/1e6:.1f} MB", flush=True)
    return manifest


if __name__ == "__main__":
    seal_holdout_all()
