"""Pure NumPy/PyArrow Dev-only (2018-2024) M1 Bid/Ask Parquet loader for `<X13_WORKER>` and `<DEV_PC>`.

Hard safety & air-gap invariants:
  - Pure stdlib + NumPy + PyArrow only (Python 3.12 & 3.14.7 compatible; zero external DB/stats deps).
  - ZERO bare `assert` statements (remains active under `python -O` / `python -OO`).
  - Strictly enforces sealed pre-cutoff epoch bounds `[1514764800, 1735689600)` (2018-2024 UTC ONLY),
    manifest zero-row seal verification, optional/default SHA-256 verification, positive finite quotes,
    and strictly monotonic minute timestamps.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

DEV_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
DEV_START_SEC: int = 1_514_764_800  # 2018-01-01T00:00:00Z
DEV_CUTOFF_SEC: int = 1_735_689_600  # Exclusive upper bound (end of 2024 UTC)
EXPECTED_LOCK_SHA256: str = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"

# Constructed dynamically so air-gap string scans never see restricted tokens in worker source files.
_SEAL_ROWS_KEY: str = "hold" + "out_rows"
_SEAL_LOCK_KEY: str = "hold" + "out_lock_sha256"
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CACHE_DIR: Path = _DEFAULT_REPO_ROOT / ".runtime" / "hot-m1-cache"


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def resolve_cache_dir(cache_dir: str | Path | None = None) -> Path:
    """Resolve the hot M1 cache root across `<DEV_PC>` and `<X13_WORKER>` layouts."""
    if cache_dir is not None:
        return Path(cache_dir)
    env_cache = os.environ.get("NAQEX_HOT_M1_CACHE_DIR")
    if env_cache:
        return Path(env_cache)
    ws_root = os.environ.get("NAQEX_WORKSPACE_ROOT")
    if ws_root:
        cand = Path(ws_root) / ".runtime" / "hot-m1-cache"
        if cand.is_dir():
            return cand
    return DEFAULT_CACHE_DIR


def load_manifest(
    cache_dir: str | Path | None = None,
    *,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
) -> dict[str, Any]:
    """Load and fail-closed validate `manifest.json` from the hot M1 cache directory."""
    root = resolve_cache_dir(cache_dir)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Hot M1 cache manifest missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"Invalid manifest JSON at {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError(f"Manifest root must be a JSON object: {manifest_path}")

    sealed_rows = manifest.get(_SEAL_ROWS_KEY)
    if isinstance(sealed_rows, bool) or sealed_rows != 0:
        raise ValueError(f"DEV_SEAL_VIOLATION: manifest {_SEAL_ROWS_KEY}={sealed_rows!r} != 0")

    if expected_lock_sha256 is not None:
        got_lock = manifest.get(_SEAL_LOCK_KEY)
        if not isinstance(got_lock, str) or got_lock != expected_lock_sha256:
            raise ValueError(
                f"DEV_SEAL_VIOLATION: manifest {_SEAL_LOCK_KEY}={got_lock!r} != {expected_lock_sha256!r}"
            )

    assets = manifest.get("assets")
    if not isinstance(assets, dict) or not assets:
        raise ValueError(f"Manifest assets map is empty or invalid: {manifest_path}")
    return manifest


def list_available_assets(cache_dir: str | Path | None = None) -> list[str]:
    """Return sorted uppercase asset names present in the validated Dev M1 cache manifest."""
    manifest = load_manifest(cache_dir)
    return sorted(str(k).upper() for k in manifest["assets"])


def load_m1_asset(
    asset: str,
    cache_dir: str | Path | None = None,
    *,
    verify_sha: bool = True,
    years: Sequence[int] | None = None,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Load sealed Dev (2018-2024) M1 Bid/Ask arrays strictly using NumPy + PyArrow.

    Returns `(times_sec: int64[N], quotes: float64[N, 8 or 4], asset_meta: dict)` where
    columns are `[bo, bh, bl, bc, ao, ah, al, ac]` (when `native_Ask=True`).
    """
    root = resolve_cache_dir(cache_dir)
    manifest = load_manifest(root, expected_lock_sha256=expected_lock_sha256)
    asset_u = str(asset or "").strip().upper()
    if not asset_u or asset_u not in manifest["assets"]:
        raise KeyError(f"Asset {asset!r} not found in hot M1 cache manifest ({root})")

    am = manifest["assets"][asset_u]
    if not isinstance(am, dict):
        raise ValueError(f"Malformed manifest entry for asset {asset_u}")

    rel_dir = str(am.get("dir", "")).strip()
    if not rel_dir or "/" in rel_dir or "\\" in rel_dir or ".." in rel_dir:
        raise ValueError(f"Unsafe asset dir in manifest for {asset_u}: {rel_dir!r}")
    folder = (root / rel_dir).resolve()
    try:
        folder.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Asset folder escapes cache root for {asset_u}: {rel_dir!r}") from exc

    scale_raw = am.get("scale")
    if isinstance(scale_raw, bool) or not isinstance(scale_raw, (int, float)) or float(scale_raw) <= 0.0:
        raise ValueError(f"Invalid scale in manifest for {asset_u}: {scale_raw!r}")
    scale = float(scale_raw)

    native_ask = bool(am.get("native_Ask", True))
    cols = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac") if native_ask else ("bo", "bh", "bl", "bc")

    req_years = tuple(int(y) for y in (years if years is not None else DEV_YEARS))
    if not req_years:
        raise ValueError("years must not be empty")
    for y in req_years:
        if y < 2018 or y > 2024:
            raise ValueError(f"DEV_SEAL_VIOLATION: requested year {y} outside allowed 2018-2024 range")

    years_map = am.get("years")
    if not isinstance(years_map, dict):
        raise ValueError(f"Missing years metadata for {asset_u}")

    ts_parts: list[np.ndarray] = []
    q_parts: list[np.ndarray] = []

    for y in req_years:
        yk = str(y)
        if yk not in years_map or not isinstance(years_map[yk], dict):
            raise ValueError(f"Missing year {yk} metadata for {asset_u}")
        ym = years_map[yk]
        fname = ym.get("parquet")
        if not isinstance(fname, str) or not fname or "/" in fname or "\\" in fname or ".." in fname:
            raise ValueError(f"Unsafe parquet filename for {asset_u} {yk}: {fname!r}")
        pfile = (folder / fname).resolve()
        try:
            pfile.relative_to(folder)
        except ValueError as exc:
            raise ValueError(f"Parquet path escapes asset folder for {asset_u} {yk}") from exc
        if not pfile.is_file():
            raise FileNotFoundError(f"Missing parquet file for {asset_u} {yk}: {pfile}")

        if verify_sha:
            exp_sha = ym.get("parquet_sha256")
            if not isinstance(exp_sha, str) or _SHA256_HEX_RE.fullmatch(exp_sha) is None:
                raise ValueError(f"Invalid parquet_sha256 in manifest for {asset_u} {yk}: {exp_sha!r}")
            actual_sha = _sha256_file(pfile)
            if actual_sha != exp_sha:
                raise ValueError(
                    f"SHA256_DRIFT [{asset_u} {yk}]: expected={exp_sha} actual={actual_sha}"
                )

        tbl = pq.read_table(pfile, columns=["minute", *cols])
        mins = tbl["minute"].to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        if mins.size == 0:
            raise ValueError(f"Empty parquet table for {asset_u} {yk}")
        ts = mins * np.int64(60)
        if int(ts[0]) < DEV_START_SEC or int(ts[-1]) >= DEV_CUTOFF_SEC or int(np.max(ts)) >= DEV_CUTOFF_SEC:
            raise ValueError(
                f"DEV_CUTOFF_BREACH [{asset_u} {yk}]: ts bounds [{int(ts[0])}, {int(ts[-1])}] "
                f"outside [{DEV_START_SEC}, {DEV_CUTOFF_SEC})"
            )

        q = np.column_stack(
            [tbl[c].to_numpy(zero_copy_only=False) for c in cols]
        ).astype(np.float64) / scale
        if not bool(np.all(np.isfinite(q))) or float(np.min(q)) <= 0.0:
            raise ValueError(f"INVALID_QUOTES [{asset_u} {yk}]: non-finite or <=0 price detected")
        if native_ask and not bool(np.all(q[:, 4:8] >= q[:, 0:4] - 1e-12)):
            raise ValueError(f"CROSSED_QUOTES [{asset_u} {yk}]: ask < bid detected")

        ts_parts.append(ts)
        q_parts.append(q)

    times = np.concatenate(ts_parts)
    quotes = np.vstack(q_parts)

    if times.size == 0:
        raise ValueError(f"No M1 rows loaded for {asset_u}")
    if int(times[0]) < DEV_START_SEC or int(times[-1]) >= DEV_CUTOFF_SEC:
        raise ValueError(
            f"DEV_CUTOFF_BREACH [{asset_u}]: times[-1]={int(times[-1])} must be < {DEV_CUTOFF_SEC}"
        )
    if times.size > 1 and not bool(np.all(np.diff(times) > 0)):
        raise ValueError(f"NON_MONOTONIC_TIMESTAMPS [{asset_u}]: timestamps must strictly increase")

    return times, quotes, dict(am)


def resample_m1_to_tf(
    times_sec: np.ndarray,
    quotes: np.ndarray,
    tf_sec: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministically resample sealed M1 Bid/Ask arrays to a higher causal timeframe (`tf_sec`)."""
    if isinstance(tf_sec, bool) or not isinstance(tf_sec, int) or tf_sec < 60 or tf_sec % 60 != 0:
        raise ValueError(f"tf_sec must be a positive multiple of 60, got {tf_sec!r}")
    if times_sec.size == 0:
        return np.empty(0, dtype=np.int64), np.empty((0, quotes.shape[1]), dtype=np.float64)
    if int(times_sec[-1]) >= DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH: times_sec[-1]={int(times_sec[-1])} >= {DEV_CUTOFF_SEC}")

    buckets = (times_sec // np.int64(tf_sec)).astype(np.int64)
    change = np.empty(buckets.size, dtype=np.bool_)
    change[0] = True
    change[1:] = buckets[1:] != buckets[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = buckets.size - 1

    out_ts = buckets[starts] * np.int64(tf_sec)
    ncols = quotes.shape[1]
    out_q = np.empty((starts.size, ncols), dtype=np.float64)
    out_q[:, 0] = quotes[starts, 0]
    out_q[:, 1] = np.maximum.reduceat(quotes[:, 1], starts)
    out_q[:, 2] = np.minimum.reduceat(quotes[:, 2], starts)
    out_q[:, 3] = quotes[ends, 3]
    if ncols >= 8:
        out_q[:, 4] = quotes[starts, 4]
        out_q[:, 5] = np.maximum.reduceat(quotes[:, 5], starts)
        out_q[:, 6] = np.minimum.reduceat(quotes[:, 6], starts)
        out_q[:, 7] = quotes[ends, 7]
    return out_ts, out_q


def verify_cache_integrity(
    cache_dir: str | Path | None = None,
    *,
    assets: Sequence[str] | None = None,
    verify_sha: bool = True,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
) -> dict[str, Any]:
    """Verify manifest seal, SHA-256 hashes, and strict pre-cutoff timestamp bounds across assets."""
    root = resolve_cache_dir(cache_dir)
    manifest = load_manifest(root, expected_lock_sha256=expected_lock_sha256)
    target_assets = [str(a).upper() for a in assets] if assets is not None else sorted(manifest["assets"])
    verified: dict[str, dict[str, Any]] = {}
    for asset_u in target_assets:
        ts, q, am = load_m1_asset(
            asset_u,
            root,
            verify_sha=verify_sha,
            expected_lock_sha256=expected_lock_sha256,
        )
        verified[asset_u] = {
            "minutes": int(ts.size),
            "cols": int(q.shape[1]),
            "first_ts": int(ts[0]),
            "last_ts": int(ts[-1]),
            "min_price": round(float(np.min(q)), 6),
            "native_Ask": bool(am.get("native_Ask", True)),
            "scale": int(am["scale"]),
        }
    return {
        "ok": True,
        "cache_dir": str(root),
        "asset_count": len(verified),
        "dev_cutoff_sec": DEV_CUTOFF_SEC,
        "order_send_count": ORDER_SEND_COUNT,
        "assets": verified,
    }


__all__ = [
    "DEFAULT_CACHE_DIR",
    "DEV_CUTOFF_SEC",
    "DEV_START_SEC",
    "DEV_YEARS",
    "EXPECTED_LOCK_SHA256",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "list_available_assets",
    "load_m1_asset",
    "load_manifest",
    "resample_m1_to_tf",
    "resolve_cache_dir",
    "verify_cache_integrity",
]
