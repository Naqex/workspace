"""Wave 5 Unit & Local-Cache Integration Tests for 28-Symbol M1 Loader & 5 Intraday Alpha Families.

Hard invariants verified (ZERO bare `assert`s — `python -O` safe, `OrderSend=0`, `Holdout 2025+ SEALED`):
  1. AST X13 air-gap check: ZERO imports of `quant_core.holdout_guard`, `research_council`,
     `duckdb`, or any `wave4/` module in `m1_universe_28_loader.py` & `m1_alpha_families_5.py`;
     ZERO bare `assert`s; ZERO CRLF/BOM; `ftmo_specs_28.json` untouched.
  2. Fail-closed `ts >= 1_735_689_600` (2025-01-01T00:00:00Z) rejection BEFORE filtering, plus
     Cluster A `2021+` leakage rejection (`CLUSTER_A_LEAKAGE`).
  3. USOIL `2020-04-20..21` quarantine during load (synthetic + exact `2,753` rows on real cache).
  4. QDM single-side spread strictly from `ftmo_specs_28.json["point"]` (NEVER `1 / npz["scale"]`)
     + session-open spread penalty `1.5x / 2.0x`.
  5. Causal `zero_gap_frac` guard (`>= 0.90` rejected fail-closed), `native_Ask` vs `native_ask`
     reconciliation, and Wave 5 `blindness_tier` mapping without mutating `ftmo_specs_28.json`.
  6. Synthetic fast unit tests for ALL 5 families (`F5A..F5E`), verifying hard flat `<= 20:50 UTC`,
     `swap_r_total == 0.0`, `0` volume columns, E4/E5 & E6 non-overlap, strict `shift >= 1` lead-lag
     causality & union `blindness_tier` / `mt5_hcc_ready`, red-news blackout + 6-CCY NZD/CHF scope
     disclosure, and bounded candidate grid (`m_total <= 360`).
  7. `@pytest.mark.local_cache` real-disk verification (USOIL 2,753 quarantine, 18 vs 10 `.hcc`
     coverage, and 5-family Cluster A smoke shard).
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.wave5 import m1_alpha_families_5 as fam5  # noqa: E402
from quant_factory.wave5 import m1_universe_28_loader as ldr  # noqa: E402

_LOADER_PATH = AI_ENGINES_DIR / "quant_factory" / "wave5" / "m1_universe_28_loader.py"
_FAMILIES_PATH = AI_ENGINES_DIR / "quant_factory" / "wave5" / "m1_alpha_families_5.py"
_SPECS_PATH = AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json"
_SPECS_EXPECTED_SHA256 = "f49e8a4a458b6f3c0f67c8f6b67247355576534dcb607d9fbab4803897c348f7"


def _check(cond: bool, msg: str) -> None:
    """Explicit guard immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_synthetic_m1_asset(
    symbol: str,
    *,
    n_weekdays: int = 28,
    start_ymd: tuple[int, int, int] = (2020, 1, 2),
    base_price: float = 100.0,
    daily_amp: float = 1.0,
    with_ask: bool = True,
    spread_px: float = 0.01,
    pattern: str = "trend_or",
    blindness_tier: str = ldr.TIER_NEW16_WAVE5,
    mt5_hcc_ready: bool = True,
    spec_override: dict[str, Any] | None = None,
) -> ldr.LoadedM1Asset:
    """Build deterministic multi-day synthetic M1 data (pure price, 0 volume, strictly < 2021)."""
    specs_doc = ldr.load_ftmo_specs_28(specs_path=_SPECS_PATH)
    spec = dict(specs_doc["symbols"][symbol])
    if spec_override:
        spec.update(spec_override)

    # Start on a weekday (2020-01-02 is Thursday)
    day0_epoch = int(datetime(start_ymd[0], start_ymd[1], start_ymd[2], tzinfo=UTC).timestamp()) // 86400
    ts_list: list[np.ndarray] = []
    bid_list: list[np.ndarray] = []

    day_cur = day0_epoch
    created = 0
    while created < n_weekdays:
        wd = (day_cur + 3) % 7
        if wd >= 5:
            day_cur += 1
            continue

        # Generate M1 bars every 1 minute across 00:00..21:10 UTC (1271 bars/day -> tests hard flat 20:50!)
        n_m = 21 * 60 + 11
        mins = np.arange(n_m, dtype=np.int64)
        day_ts = day_cur * 86400 + mins * 60

        # Small overnight gap so zero_gap_frac << 0.90
        open_gap = ((created % 5) - 2) * 0.04 * daily_amp + 0.02 * daily_amp
        day_base = base_price + open_gap + 0.01 * created * daily_amp
        # Compress last 6 days before day 22+ so F5C NR5/NR20 < 0.80 triggers cleanly!
        amp = daily_amp * (0.45 if (pattern == "vol_comp" and created >= 17) else 1.0)
        if pattern == "vol_comp" and created >= 22:
            # Compression on days 17..21 -> ratio < 0.80 on day 22, then strong breakout!
            amp_day = daily_amp * 0.45 if created == 21 else daily_amp * 0.42
        else:
            amp_day = amp

        c = np.full(n_m, day_base, dtype=np.float64)
        h = np.empty(n_m, dtype=np.float64)
        lo = np.empty(n_m, dtype=np.float64)
        o = np.empty(n_m, dtype=np.float64)

        if pattern == "trend_or":
            # Clear 07:00..07:30 opening range (~0.30*amp), then strong directional breakout 07:30..13:20
            for m in range(n_m):
                if m < 7 * 60:
                    c[m] = day_base + 0.10 * amp_day * np.sin(m / 25.0)
                elif m < 7 * 60 + 30:
                    c[m] = day_base + 0.22 * amp_day * np.sin((m - 7 * 60) * np.pi / 15.0)
                elif m < 13 * 60 + 30:
                    prog = (m - (7 * 60 + 30)) / 360.0
                    c[m] = day_base + 0.22 * amp_day + 1.1 * amp_day * prog
                else:
                    c[m] = day_base + 1.32 * amp_day - 0.10 * amp_day * np.sin(m / 40.0)
        elif pattern == "sweep_mr":
            # Asian box [00:00..06:00] around day_base +- 0.25*amp; at 07:10 spike above +0.48*amp then reclaim inside!
            for m in range(n_m):
                if m < 6 * 60:
                    c[m] = day_base + 0.22 * amp_day * np.sin(m / 20.0)
                elif m < 7 * 60 + 5:
                    c[m] = day_base + 0.20 * amp_day
                elif m < 7 * 60 + 12:
                    c[m] = day_base + 0.46 * amp_day  # Sweep above box_hi (~0.25) by ~0.21 ATR
                elif m < 7 * 60 + 20:
                    c[m] = day_base + 0.05 * amp_day  # Rapid reclaim inside box!
                else:
                    c[m] = day_base - 0.55 * amp_day
        elif pattern == "vol_comp":
            # On days >= 22, strong breakout in Asia (01:00..06:50) AND Late NY (17:30..20:45)
            for m in range(n_m):
                if created < 22:
                    c[m] = day_base + 0.45 * amp_day * np.sin(m / 60.0)
                else:
                    if m < 60:
                        c[m] = day_base
                    elif m < 6 * 60 + 50:
                        c[m] = day_base + 0.65 * daily_amp * ((m - 60) / 350.0)
                    elif m < 17 * 60:
                        c[m] = day_base + 0.30 * daily_amp
                    elif m < 20 * 60 + 45:
                        c[m] = day_base + 0.30 * daily_amp + 0.70 * daily_amp * ((m - 17 * 60) / 225.0)
                    else:
                        c[m] = day_base + 0.95 * daily_amp
        elif pattern == "leader_impulse":
            # Strong leader impulse at 08:30..09:00 UTC (+0.70 ATR)
            for m in range(n_m):
                if m < 8 * 60 + 30:
                    c[m] = day_base + 0.08 * amp_day * np.sin(m / 30.0)
                elif m < 9 * 60:
                    c[m] = day_base + 0.75 * amp_day * ((m - (8 * 60 + 30)) / 30.0)
                else:
                    c[m] = day_base + 0.80 * amp_day
        elif pattern == "target_lag":
            # Target lags during 08:30..09:05, then catches up 09:05..12:00!
            for m in range(n_m):
                if m < 9 * 60 + 5:
                    c[m] = day_base + 0.06 * amp_day * np.sin(m / 30.0)
                elif m < 12 * 60:
                    c[m] = day_base + 0.85 * amp_day * ((m - (9 * 60 + 5)) / 175.0)
                else:
                    c[m] = day_base + 0.85 * amp_day
        elif pattern == "twap_fade":
            # Flat 00:00..07:30 around day_base, sharp spike to +2.4 std at 08:00 with upper wick, then fade back!
            for m in range(n_m):
                if m < 7 * 60 + 30:
                    c[m] = day_base + 0.08 * amp_day * np.sin(m / 18.0)
                elif m < 8 * 60:
                    c[m] = day_base + 0.32 * amp_day * ((m - (7 * 60 + 30)) / 30.0)
                elif m < 8 * 60 + 5:
                    c[m] = day_base + 0.28 * amp_day
                else:
                    c[m] = day_base - 0.15 * amp_day
        else:
            for m in range(n_m):
                c[m] = day_base + 0.25 * amp_day * np.sin(m / 30.0)

        o[0] = c[0] - 0.005 * daily_amp
        o[1:] = c[:-1] + 0.001 * daily_amp * ((np.arange(1, n_m) % 3) - 1)
        wick = 0.04 * amp_day
        h = np.maximum(o, c) + wick
        lo = np.minimum(o, c) - wick
        if pattern == "twap_fade":
            # Add clear upper rejection wick around 08:00..08:04 for TWAP fade confirmation
            h[8 * 60 : 8 * 60 + 5] = c[8 * 60 : 8 * 60 + 5] + 0.12 * amp_day

        bid_d = np.column_stack((o, h, lo, c))
        ts_list.append(day_ts)
        bid_list.append(bid_d)
        created += 1
        day_cur += 1

    ts_all = np.concatenate(ts_list)
    bid_all = np.vstack(bid_list)
    ask_all = (bid_all + spread_px) if with_ask else None
    zg = ldr.compute_causal_zero_gap_frac(ts_all, bid_all)

    return ldr.LoadedM1Asset(
        symbol=symbol,
        ftmo_symbol=str(spec["ftmo_symbol"]),
        asset_class=str(spec["asset_class"]),
        source_pool="SEALED16_NPZ",
        data_resolution=ldr.RES_M1_BID_SPREAD if with_ask else ldr.RES_M1_SINGLE_SIDE,
        source_provenance="SYNTHETIC_UNIT_TEST",
        native_ask=False,
        has_true_bid_ask=False,
        ask_columns_present=with_ask,
        legacy_blindness_tier=str(spec["blindness_tier"]),
        blindness_tier=blindness_tier,
        mt5_hcc_ready=mt5_hcc_ready,
        times_sec=ts_all,
        bid_ohlc=bid_all,
        ask_ohlc=ask_all,
        spec=spec,
        years_available=(2020,),
        years_loaded=(2020,),
        quarantined_rows=0,
        quarantined_dates=(),
        zero_gap_frac=zg["zero_gap_frac"],
        zero_gap_frac_m1=zg["zero_gap_frac_m1"],
        base_spread_price=ldr.compute_qdm_base_spread_price(spec),
        median_spread_price=spread_px,
        median_spread_pts=spread_px / float(spec["point"]),
        spread_model="SYNTHETIC",
        npz_scale_meta=int(spec.get("m1_scale", 1000)),
        source_filename=f"{symbol}-SYNTHETIC.npz",
        holdout_rows=0,
    )


# ---------------------------------------------------------------------------
# 1. Static AST Air-Gap, Zero Bare Assert, LF/BOM, and Immutable SSOT Checks
# ---------------------------------------------------------------------------


def test_x13_airgap_zero_forbidden_imports_and_zero_bare_asserts() -> None:
    """BOTH core Wave 5 files must have ZERO holdout_guard/research_council/duckdb/wave4 imports."""
    forbidden_tokens = ("holdout_guard", "research_council", "duckdb", "wave4")
    for path in (_LOADER_PATH, _FAMILIES_PATH, Path(__file__)):
        raw = path.read_bytes()
        _check(not raw.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM detected in {path}")
        _check(b"\r" not in raw, f"CRLF detected in {path}")
        src = raw.decode("utf-8")
        tree = ast.parse(src, filename=str(path))
        asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        _check(not asserts, f"Bare assert statement(s) at lines {asserts} in {path}")

        if path in (_LOADER_PATH, _FAMILIES_PATH):
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        low = alias.name.lower()
                        for tok in forbidden_tokens:
                            _check(tok not in low, f"Forbidden import {alias.name!r} in {path}")
                elif isinstance(node, ast.ImportFrom):
                    mod = (node.module or "").lower()
                    for tok in forbidden_tokens:
                        _check(tok not in mod, f"Forbidden from-import {node.module!r} in {path}")
                    for alias in node.names:
                        low = alias.name.lower()
                        for tok in forbidden_tokens:
                            _check(tok not in low, f"Forbidden imported name {alias.name!r} in {path}")
                elif isinstance(node, ast.Call):
                    fn = node.func
                    fname = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
                    if fname in ("import_module", "__import__") and node.args:
                        a0 = node.args[0]
                        if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                            low = a0.value.lower()
                            for tok in forbidden_tokens:
                                _check(tok not in low, f"Forbidden dynamic import {a0.value!r} in {path}")

    # Verify immutable ftmo_specs_28.json SHA-256 untouched
    _check(_sha256_file(_SPECS_PATH) == _SPECS_EXPECTED_SHA256, "ftmo_specs_28.json SHA-256 mutated!")


# ---------------------------------------------------------------------------
# 2. Loader Fail-Closed Unit Tests (Synthetic, Zero .runtime Dependency)
# ---------------------------------------------------------------------------


def test_loader_rejects_2025_timestamp_and_nonzero_holdout_rows(tmp_path: Path) -> None:
    npz_dir = tmp_path / "npz"
    npz_dir.mkdir()
    # 1. Timestamp exactly == DEV_CUTOFF_SEC (2025-01-01T00:00:00Z) MUST fail BEFORE year filtering!
    bad_ts_npz = npz_dir / "US30-M1-QDM_PROVIDER_DEFAULT_SINGLE_SIDE.npz"
    np.savez(
        bad_ts_npz,
        times_sec=np.array([1_577_836_800, 1_577_836_860, ldr.DEV_CUTOFF_SEC], dtype=np.int64),
        bid_ohlc=np.array(
            [
                [28500.0, 28510.0, 28490.0, 28505.0],
                [28506.0, 28515.0, 28500.0, 28510.0],
                [42500.0, 42510.0, 42490.0, 42500.0],
            ],
            dtype=np.float64,
        ),
        ask_columns_present=np.bool_(False),
        native_ask=np.bool_(False),
        has_true_bid_ask=np.bool_(False),
        scale=np.int64(1000),
        holdout_rows=np.int64(0),
    )
    with pytest.raises(ValueError, match="DEV_CUTOFF_BREACH"):
        ldr.load_m1_symbol(
            "US30",
            years=(2020,),
            sealed16_npz_root=npz_dir,
            specs_path=_SPECS_PATH,
        )

    # 2. holdout_rows > 0 metadata MUST fail-closed
    bad_hr_npz = npz_dir / "UK100-M1-QDM_PROVIDER_DEFAULT_SINGLE_SIDE.npz"
    np.savez(
        bad_hr_npz,
        times_sec=np.array([1_577_836_800, 1_577_836_860], dtype=np.int64),
        bid_ohlc=np.array([[7500.0, 7510.0, 7490.0, 7505.0], [7506.0, 7515.0, 7500.0, 7510.0]], dtype=np.float64),
        ask_columns_present=np.bool_(False),
        native_ask=np.bool_(False),
        has_true_bid_ask=np.bool_(False),
        scale=np.int64(1000),
        holdout_rows=np.int64(1),
    )
    with pytest.raises(ValueError, match="DEV_SEAL_VIOLATION"):
        ldr.load_m1_symbol("UK100", sealed16_npz_root=npz_dir, specs_path=_SPECS_PATH)


def test_loader_usoil_quarantine_unscaled_and_zero_copy(tmp_path: Path) -> None:
    npz_dir = tmp_path / "npz"
    npz_dir.mkdir()
    usoil_npz = npz_dir / "USOIL-M1-QDM_PROVIDER_DEFAULT_SINGLE_SIDE.npz"
    # Build 20 bars on 2020-04-19 (valid), 5 bars on 2020-04-20..21 (quarantined), 20 bars on 2020-04-22 (valid)
    t_pre = int(datetime(2020, 4, 19, 10, 0, tzinfo=UTC).timestamp()) + np.arange(20, dtype=np.int64) * 60
    t_q = np.array(
        [
            ldr.USOIL_QUARANTINE_START_SEC,
            ldr.USOIL_QUARANTINE_START_SEC + 3600,
            ldr.USOIL_QUARANTINE_START_SEC + 86400,
            ldr.USOIL_QUARANTINE_END_SEC - 120,
            ldr.USOIL_QUARANTINE_END_SEC - 60,
        ],
        dtype=np.int64,
    )
    t_post = ldr.USOIL_QUARANTINE_END_SEC + np.arange(20, dtype=np.int64) * 60
    ts = np.concatenate((t_pre, t_q, t_post))

    bid = np.empty((ts.size, 4), dtype=np.float64)
    for i in range(ts.size):
        px = 0.50 if (20 <= i < 25) else (18.0 + 0.15 * i)
        bid[i] = [px, px + 0.1, max(0.25, px - 0.1), px + 0.05]

    np.savez(
        usoil_npz,
        times_sec=ts,
        bid_ohlc=bid,
        ask_columns_present=np.bool_(False),
        native_ask=np.bool_(False),
        has_true_bid_ask=np.bool_(False),
        scale=np.int64(1000),
        source_provenance=np.array("QDM_PROVIDER_DEFAULT_SINGLE_SIDE"),
        holdout_rows=np.int64(0),
    )
    before_files = sorted(p.name for p in npz_dir.iterdir())
    asset = ldr.load_m1_symbol("USOIL", sealed16_npz_root=npz_dir, specs_path=_SPECS_PATH)
    after_files = sorted(p.name for p in npz_dir.iterdir())

    _check(before_files == after_files, "Zero-copy invariant violated: new files written during load!")
    _check(asset.quarantined_rows == 5, f"Expected 5 quarantined USOIL rows, got {asset.quarantined_rows}")
    _check(asset.n_bars == 40, f"Expected 40 surviving USOIL rows, got {asset.n_bars}")
    _check(float(np.min(asset.bid_ohlc)) >= 17.0, "NPZ bid_ohlc must NOT be divided by scale=1000!")
    _check(asset.data_resolution == ldr.RES_M1_SINGLE_SIDE, f"Bad resolution: {asset.data_resolution}")
    _check(asset.blindness_tier == ldr.TIER_NEW16_WAVE5, f"Bad Wave 5 tier: {asset.blindness_tier}")


def test_qdm_point_spread_never_uses_inv_scale_and_open_penalty() -> None:
    specs_doc = ldr.load_ftmo_specs_28(specs_path=_SPECS_PATH)
    for sym in ("JP225", "UK100", "US30"):
        sp = specs_doc["symbols"][sym]
        # In NPZ metadata these 3 have scale=1000 (1/scale = 0.001), while ftmo_specs_28 point = 0.01!
        _check(sp["m1_scale"] == 1000 and abs(float(sp["point"]) - 0.01) < 1e-12, f"Spec precondition failed for {sym}")
        base_px = ldr.compute_qdm_base_spread_price(sp)
        expected = float(sp["benchmark_spread_pts"]) * 0.01
        wrong_inv_scale = float(sp["benchmark_spread_pts"]) / 1000.0
        _check(abs(base_px - expected) < 1e-12, f"{sym} base_px={base_px} != {expected}")
        _check(abs(base_px - wrong_inv_scale) > 1e-6, f"{sym} accidentally used 1/scale!")

    # Session-open penalty verification for US30 (2.0x open/rollover, 1.5x ramp, 1.0x liquid)
    d0 = int(datetime(2020, 6, 10, 0, 0, tzinfo=UTC).timestamp())
    test_ts = np.array(
        [
            d0 + 13 * 3600 + 35 * 60,  # 2.0x open
            d0 + 13 * 3600 + 55 * 60,  # 1.5x ramp
            d0 + 16 * 3600,            # 1.0x liquid
            d0 + 21 * 3600 + 30 * 60,  # 2.0x rollover
        ],
        dtype=np.int64,
    )
    mults = ldr.compute_session_open_spread_mult(test_ts, "US30", penalty_mode="tiered_1.5x_2.0x")
    _check(mults.tolist() == [2.0, 1.5, 1.0, 2.0], f"Unexpected US30 session-open multipliers: {mults.tolist()}")


def test_loader_zero_gap_frac_guard_and_manifest_native_ask_reconcile(tmp_path: Path) -> None:
    # 1. Synthetic zero-gap series (open[d] == close[d-1] on 100% of days) MUST fail-closed!
    d0 = int(datetime(2020, 1, 2, 0, 0, tzinfo=UTC).timestamp())
    ts_parts = []
    bid_parts = []
    px = 100.0
    for d in range(15):
        t = d0 + d * 86400 + np.array([0, 3600, 7200], dtype=np.int64)
        b = np.array(
            [
                [px, px + 0.5, px - 0.5, px + 0.2],
                [px + 0.2, px + 0.7, px, px + 0.4],
                [px + 0.4, px + 0.8, px + 0.1, px + 0.5],
            ],
            dtype=np.float64,
        )
        px = px + 0.5
        ts_parts.append(t)
        bid_parts.append(b)
    zg = ldr.compute_causal_zero_gap_frac(np.concatenate(ts_parts), np.vstack(bid_parts))
    _check(zg["zero_gap_frac"] >= 0.90, f"Expected synthetic zero_gap_frac >= 0.90, got {zg}")

    npz_dir = tmp_path / "npz"
    npz_dir.mkdir()
    np.savez(
        npz_dir / "UK100-M1-QDM_PROVIDER_DEFAULT_SINGLE_SIDE.npz",
        times_sec=np.concatenate(ts_parts),
        bid_ohlc=np.vstack(bid_parts),
        ask_columns_present=np.bool_(False),
        native_ask=np.bool_(False),
        has_true_bid_ask=np.bool_(False),
        scale=np.int64(1000),
        holdout_rows=np.int64(0),
    )
    with pytest.raises(ValueError, match="ZERO_GAP_FRAC_VIOLATION"):
        ldr.load_m1_symbol("UK100", sealed16_npz_root=npz_dir, specs_path=_SPECS_PATH, strict_zero_gap=True)

    # 2. Manifest `native_Ask` (capital A) mismatch against `.npz` `native_ask` MUST fail-closed!
    bad_man = tmp_path / "manifest.json"
    bad_man.write_text(
        json.dumps(
            {
                "holdout_rows": 0,
                "assets": {"UK100": {"native_Ask": True, "has_true_bid_ask": False}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="METADATA_MISMATCH"):
        ldr.load_m1_symbol(
            "UK100",
            sealed16_npz_root=npz_dir,
            sealed16_manifest_path=bad_man,
            specs_path=_SPECS_PATH,
            strict_zero_gap=False,
        )


def test_wave5_blindness_tier_mapping_and_split_years() -> None:
    _check(ldr.map_wave5_blindness_tier("DEV_CLB_CONSUMED_12OLD") == "DEV_CLB_CONSUMED_12OLD", "OLD12 map mismatch")
    _check(ldr.map_wave5_blindness_tier("NEW9_D1_VIEWED_M1_UNSEEN") == "M1_UNSEEN_D1_VIEWED", "NEW9 map mismatch")
    _check(ldr.map_wave5_blindness_tier("TRUE_BLIND_CLB_NEW7_CROSSES") == "M1_UNSEEN_D1_VIEWED", "NEW7 map mismatch")
    _check(
        ldr.resolve_split_years((2018, 2019, 2020, 2021, 2022, 2023, 2024), "cluster_a") == (2018, 2019, 2020),
        "7Y ClA",
    )
    _check(ldr.resolve_split_years((2019, 2020, 2021, 2022, 2023, 2024), "cluster_a") == (2019, 2020), "6Y ClA")
    _check(
        ldr.resolve_split_years((2019, 2020, 2021, 2022, 2023, 2024), "cluster_b") == (2021, 2022, 2023, 2024),
        "6Y ClB",
    )
    with pytest.raises(ValueError, match="DEV_CUTOFF_BREACH"):
        ldr.validate_requested_years((2024, 2025))


# ---------------------------------------------------------------------------
# 3. Synthetic Fast Unit Tests for ALL 5 Intraday M1 Alpha Families
# ---------------------------------------------------------------------------


def test_candidate_grid_budget_and_determinism() -> None:
    g1 = fam5.generate_cluster_a_candidate_grid()
    g2 = fam5.generate_cluster_a_candidate_grid()
    _check(g1 == g2, "Candidate grid must be 100% deterministic")
    _check(0 < len(g1) <= fam5.MAX_TOTAL_CANDIDATES, f"Grid size {len(g1)} > {fam5.MAX_TOTAL_CANDIDATES}")
    ids = [c["candidate_id"] for c in g1]
    _check(len(ids) == len(set(ids)), "Duplicate candidate_ids detected in grid!")
    fams = {c["family_id"] for c in g1}
    _check(fams == set(fam5.FAMILY_IDS), f"Missing families in grid: {set(fam5.FAMILY_IDS) - fams}")


def test_all_five_families_synthetic_hard_flat_causality_and_red_news(tmp_path: Path) -> None:
    """Fast synthetic E2E across all 5 families: hard flat <= 20:50 UTC, 0 swap, 0 vol, union meta, news filter."""
    # Synthetic red-news calendar with 1 USD event at 2020-01-30 07:35 UTC to verify blackout & 6-CCY disclosure
    ev_usd_ts = int(datetime(2020, 1, 30, 7, 35, tzinfo=UTC).timestamp())
    synth_cal = {
        "schema": "synthetic-6ccy-v1",
        "sources_used": ["synthetic_csv"],
        "total_events": 1,
        "covered_currencies": list(fam5.RED_NEWS_COVERED_CCYS),
        "uncovered_currencies": list(fam5.RED_NEWS_UNCOVERED_CCYS),
        "by_ccy": {"USD": (np.array([ev_usd_ts], dtype=np.int64), np.array([300], dtype=np.int64))},
    }

    assets = {
        "US30": _make_synthetic_m1_asset(
            "US30",
            base_price=28500.0,
            daily_amp=250.0,
            with_ask=False,
            spread_px=0.18,
            pattern="trend_or",
            mt5_hcc_ready=False,
        ),
        "AUDJPY": _make_synthetic_m1_asset(
            "AUDJPY",
            base_price=75.0,
            daily_amp=0.80,
            with_ask=True,
            spread_px=0.012,
            pattern="sweep_mr",
            mt5_hcc_ready=True,
        ),
        "CHFJPY": _make_synthetic_m1_asset(
            "CHFJPY",
            base_price=112.0,
            daily_amp=0.90,
            with_ask=True,
            spread_px=0.014,
            pattern="vol_comp",
            mt5_hcc_ready=True,
        ),
        "XAUUSD": _make_synthetic_m1_asset(
            "XAUUSD",
            base_price=1560.0,
            daily_amp=20.0,
            with_ask=True,
            spread_px=0.25,
            pattern="leader_impulse",
            blindness_tier=ldr.TIER_OLD12,
            mt5_hcc_ready=False,
        ),
        "XAGUSD": _make_synthetic_m1_asset(
            "XAGUSD",
            base_price=18.0,
            daily_amp=0.40,
            with_ask=True,
            spread_px=0.02,
            pattern="target_lag",
            blindness_tier=ldr.TIER_NEW16_WAVE5,
            mt5_hcc_ready=True,
        ),
        "NZDUSD": _make_synthetic_m1_asset(
            "NZDUSD",
            base_price=0.66,
            daily_amp=0.008,
            with_ask=True,
            spread_px=0.00010,
            pattern="twap_fade",
            mt5_hcc_ready=True,
        ),
    }

    cands = [
        {
            "candidate_id": "SYNTH_F5A",
            "family_id": fam5.FAM_F5A,
            "symbol": "US30",
            "leader_symbol": None,
            "params": {"session_code": 1, "or_minutes": 30, "buf_atr": 0.05, "sl_atr": 0.70, "tp_r": 1.8},
        },
        {
            "candidate_id": "SYNTH_F5B",
            "family_id": fam5.FAM_F5B,
            "symbol": "AUDJPY",
            "leader_symbol": None,
            "params": {
                "ref_start_h": 0, "ref_end_h": 6, "scan_end_h": 12, "flat_h": 17,
                "sweep_min_atr": 0.12, "sweep_max_atr": 0.50, "reclaim_depth_atr": 0.03,
                "reclaim_max_min": 45, "sl_atr_floor": 0.65, "tp_r": 1.5,
            },
        },
        {
            "candidate_id": "SYNTH_F5C",
            "family_id": fam5.FAM_F5C,
            "symbol": "CHFJPY",
            "leader_symbol": None,
            "params": {"window_code": 0, "comp_thresh": 0.85, "break_atr": 0.25, "sl_atr": 0.65, "tp_r": 1.6},
        },
        {
            "candidate_id": "SYNTH_F5D",
            "family_id": fam5.FAM_F5D,
            "symbol": "XAGUSD",
            "leader_symbol": "XAUUSD",
            "params": {
                "mode_code": 0, "scan_start_h": 7, "scan_end_h": 17, "flat_h": 20,
                "lag_min": 2, "lb_min": 30, "z_thresh": 0.25, "lag_gap_thresh": 0.10,
                "sl_atr": 0.75, "tp_r": 1.8,
            },
        },
        {
            "candidate_id": "SYNTH_F5E",
            "family_id": fam5.FAM_F5E,
            "symbol": "NZDUSD",
            "leader_symbol": None,
            "params": {
                "mode_code": 0, "scan_start_h": 7, "scan_end_h": 14, "flat_h": 20,
                "z_entry": 1.5, "z_max": 4.5, "sl_atr": 0.70, "tp_r": 1.5,
            },
        },
    ]

    npz_out = tmp_path / "shard_r.npz"
    res = fam5.evaluate_candidate_shard(
        cands,
        split="cluster_a",
        preloaded_assets=assets,
        red_news_calendar=synth_cal,
        output_npz_path=npz_out,
    )
    _check(res["order_send_count"] == 0, "order_send_count must be 0")
    _check(res["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(res["candidate_count"] == 5, f"Expected 5 results, got {res['candidate_count']}")
    _check(npz_out.is_file(), "Optional NPZ output was not created")

    by_id = {r["candidate_id"]: r for r in res["results"]}
    for cid in ("SYNTH_F5A", "SYNTH_F5B", "SYNTH_F5C", "SYNTH_F5D", "SYNTH_F5E"):
        r = by_id[cid]
        _check(r["n_trades"] >= 1, f"{cid} produced 0 trades on synthetic pattern!")
        _check(r["all_flat_by_2050_utc"] is True, f"{cid} violated 20:50 UTC hard flat!")
        _check(r["max_exit_utc_sec"] <= fam5.HARD_FLAT_MAX_UTC_SEC, f"{cid} max_exit_utc_sec={r['max_exit_utc_sec']}")
        _check(r["swap_r_total"] == 0.0, f"{cid} swap_r_total must be 0.0")
        _check(r["volume_columns_used"] == 0, f"{cid} must use 0 volume columns")

    # Verify F5D union blindness_tier & union mt5_hcc_ready over XAUUSD (OLD12, hcc=False) -> XAGUSD (NEW16, hcc=True)
    r5d = by_id["SYNTH_F5D"]
    _check(
        r5d["blindness_tier"] == ldr.TIER_OLD12,
        f"F5D union tier must downgrade to OLD12, got {r5d['blindness_tier']}",
    )
    _check(r5d["mt5_hcc_ready"] is False, "F5D union mt5_hcc_ready must be False when leader lacks .hcc!")

    # Verify explicit 6-CCY red-news scope disclosure flags CHF (CHFJPY) and NZD (NZDUSD)
    _check(by_id["SYNTH_F5C"]["red_news_scope_disclosure"]["has_nzd_chf_scope_gap"] is True, "CHFJPY must flag CHF gap")
    _check(by_id["SYNTH_F5E"]["red_news_scope_disclosure"]["has_nzd_chf_scope_gap"] is True, "NZDUSD must flag NZD gap")
    _check(by_id["SYNTH_F5B"]["red_news_scope_disclosure"]["has_nzd_chf_scope_gap"] is False, "AUDJPY is inside 6-CCY")

    # Verify F5D lag_min == 0 is REJECTED fail-closed
    bad_lag = dict(cands[3], candidate_id="BAD_LAG", params={**cands[3]["params"], "lag_min": 0})
    with pytest.raises(ValueError, match="CAUSALITY_VIOLATION"):
        fam5.evaluate_candidate_shard(
            [bad_lag], split="cluster_a", preloaded_assets=assets, red_news_calendar=synth_cal
        )

    # Verify flat_h == 21 is REJECTED fail-closed (violates <= 20:50 UTC)
    bad_flat = dict(cands[1], candidate_id="BAD_FLAT", params={**cands[1]["params"], "flat_h": 21})
    with pytest.raises(ValueError, match="HARD_FLAT_VIOLATION"):
        fam5.evaluate_candidate_shard(
            [bad_flat], split="cluster_a", preloaded_assets=assets, red_news_calendar=synth_cal
        )

    # Verify Cluster A NEVER accepts 2021 data (fail-closed CLUSTER_A_LEAKAGE)
    asset_2021 = _make_synthetic_m1_asset("AUDJPY", n_weekdays=20, start_ymd=(2021, 1, 4), pattern="sweep_mr")
    with pytest.raises(ValueError, match="CLUSTER_A_LEAKAGE"):
        fam5.evaluate_candidate_shard(
            [cands[1]],
            split="cluster_a",
            preloaded_assets={"AUDJPY": asset_2021},
            red_news_calendar=synth_cal,
        )


def test_red_news_blackout_blocks_entry_and_disclosure() -> None:
    """Verify red-news blackout directly blocks entries inside +-300s and pre-news flattens open trades."""
    asset = _make_synthetic_m1_asset(
        "US30", base_price=28500.0, daily_amp=250.0, with_ask=False, spread_px=0.18, pattern="trend_or"
    )
    cand = {
        "candidate_id": "NEWS_BLK_F5A",
        "family_id": fam5.FAM_F5A,
        "symbol": "US30",
        "leader_symbol": None,
        "params": {"session_code": 1, "or_minutes": 30, "buf_atr": 0.05, "sl_atr": 0.70, "tp_r": 1.8},
    }
    empty_cal = {
        "schema": "empty",
        "sources_used": ["empty"],
        "total_events": 0,
        "covered_currencies": list(fam5.RED_NEWS_COVERED_CCYS),
        "uncovered_currencies": list(fam5.RED_NEWS_UNCOVERED_CCYS),
        "by_ccy": {},
    }
    ctx = fam5._prepare_asset_context(asset, empty_cal)
    e_ts_base, x_ts_base, *_ = fam5._eval_f5a_session_or_breakout_jit(
        ctx["times_sec"],
        ctx["bid_ohlc"],
        ctx["ask_ohlc"],
        ctx["has_ask"],
        ctx["day_buckets"],
        ctx["day_starts"],
        ctx["day_ends"],
        ctx["day_weekdays"],
        ctx["d1_atr14"],
        ctx["ev_ts"],
        ctx["ev_pad"],
        1,
        30,
        0.05,
        0.70,
        1.8,
        0.08,
        0.90,
        ctx["point"],
        ctx["bench_sp_px"],
        ctx["comm_px"],
        ctx["qdm_class"],
    )
    n_base = int(e_ts_base.shape[0])
    _check(n_base >= 5, f"Expected >= 5 baseline trades without news, got {n_base}")

    # 1. Inject USD red-news events 120s after each baseline entry (strictly inside +-300s blackout) -> 0 entries!
    ev_ts_blk = (e_ts_base + 120).astype(np.int64)
    ev_pad_blk = np.full(ev_ts_blk.shape[0], 300, dtype=np.int64)
    heavy_cal = dict(empty_cal, total_events=int(ev_ts_blk.size), by_ccy={"USD": (ev_ts_blk, ev_pad_blk)})
    res_with_news = fam5.evaluate_candidate_shard(
        [cand], split="cluster_a", preloaded_assets={"US30": asset}, red_news_calendar=heavy_cal
    )
    n_blocked = res_with_news["results"][0]["n_trades"]
    _check(n_blocked == 0, f"Expected +-300s red-news blackout to block all entries, got {n_blocked}/{n_base}")

    # 2. Inject USD red-news events 600s after each entry -> entry allowed, pre-news flatten triggers at <= e_ts + 300s!
    ev_ts_flat = (e_ts_base + 600).astype(np.int64)
    ctx_f = fam5._prepare_asset_context(
        asset, dict(empty_cal, total_events=int(ev_ts_flat.size), by_ccy={"USD": (ev_ts_flat, ev_pad_blk)})
    )
    e_ts_f, x_ts_f, *_ = fam5._eval_f5a_session_or_breakout_jit(
        ctx_f["times_sec"],
        ctx_f["bid_ohlc"],
        ctx_f["ask_ohlc"],
        ctx_f["has_ask"],
        ctx_f["day_buckets"],
        ctx_f["day_starts"],
        ctx_f["day_ends"],
        ctx_f["day_weekdays"],
        ctx_f["d1_atr14"],
        ctx_f["ev_ts"],
        ctx_f["ev_pad"],
        1,
        30,
        0.05,
        0.70,
        1.8,
        0.08,
        0.90,
        ctx_f["point"],
        ctx_f["bench_sp_px"],
        ctx_f["comm_px"],
        ctx_f["qdm_class"],
    )
    _check(e_ts_f.shape[0] == n_base, f"Expected entries outside +-300s to fill: {e_ts_f.shape[0]} vs {n_base}")
    _check(bool(np.all((x_ts_f - e_ts_f) <= 300)), "Pre-news flatten failed to flatten open trade by ev_ts - 300s!")
    _check(bool(np.all(x_ts_f < x_ts_base)), "Pre-news flatten should exit strictly earlier than baseline exit!")


def test_f5d_pair_union_metadata_all_combinations() -> None:
    u1 = fam5.compute_pair_union_metadata(
        {
            "symbol": "AUDJPY",
            "blindness_tier": ldr.TIER_NEW16_WAVE5,
            "mt5_hcc_ready": True,
            "data_resolution": ldr.RES_M1_BID_SPREAD,
        },
        {
            "symbol": "NZDJPY",
            "blindness_tier": ldr.TIER_NEW16_WAVE5,
            "mt5_hcc_ready": True,
            "data_resolution": ldr.RES_M1_BID_SPREAD,
        },
    )
    _check(u1["blindness_tier"] == ldr.TIER_NEW16_WAVE5, "AUDJPY->NZDJPY must remain M1_UNSEEN_D1_VIEWED")
    _check(u1["mt5_hcc_ready"] is True, "AUDJPY->NZDJPY must be mt5_hcc_ready=True")
    _check(u1["red_news_scope_disclosure"]["has_nzd_chf_scope_gap"] is True, "NZDJPY pair must flag NZD scope gap")

    u2 = fam5.compute_pair_union_metadata(
        {
            "symbol": "XAUUSD",
            "blindness_tier": ldr.TIER_OLD12,
            "mt5_hcc_ready": False,
            "data_resolution": ldr.RES_M1_BID_ASK,
        },
        {
            "symbol": "XAGUSD",
            "blindness_tier": ldr.TIER_NEW16_WAVE5,
            "mt5_hcc_ready": True,
            "data_resolution": ldr.RES_M1_BID_SPREAD,
        },
    )
    _check(u2["blindness_tier"] == ldr.TIER_OLD12, "XAUUSD->XAGUSD must downgrade to DEV_CLB_CONSUMED_12OLD")
    _check(u2["mt5_hcc_ready"] is False, "XAUUSD->XAGUSD must be mt5_hcc_ready=False")
    _check(u2["data_resolution"] == ldr.RES_M1_BID_SPREAD, "Conservative union resolution must pick M1_BID_SPREAD")


# ---------------------------------------------------------------------------
# 4. Real-Disk Local Cache Integration Tests (`@pytest.mark.local_cache`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_local_cache_usoil_exact_2753_quarantine_and_hcc_18_vs_10() -> None:
    hcc = ldr.inspect_mt5_hcc_coverage()
    _check(hcc["audit_source"] == "LIVE_DISK_INSPECTION", f"Expected live .hcc inspection, got {hcc['audit_source']}")
    _check(hcc["mt5_hcc_ready_count"] == 18, f"Expected 18 ready symbols, got {hcc['mt5_hcc_ready_count']}")
    _check(hcc["mt5_hcc_missing_count"] == 10, f"Expected 10 missing symbols, got {hcc['mt5_hcc_missing_count']}")
    _check(hcc["mt5_hcc_missing_qdm_6"] == sorted(ldr.MT5_HCC_MISSING_10_QDM), "QDM 6 missing mismatch")
    _check(hcc["mt5_hcc_missing_hot12_4"] == sorted(ldr.MT5_HCC_MISSING_10_HOT12), "HOT12 4 missing mismatch")

    usoil = ldr.load_m1_symbol("USOIL")
    _check(usoil.quarantined_rows == 2753, f"Expected exact 2,753 quarantined USOIL rows, got {usoil.quarantined_rows}")
    _check(usoil.zero_gap_frac < 0.90, f"USOIL zero_gap_frac={usoil.zero_gap_frac} >= 0.90")
    _check(usoil.max_ts < ldr.DEV_CUTOFF_SEC, "USOIL max_ts breached Dev cutoff!")
    _check(usoil.holdout_rows == 0, "USOIL holdout_rows != 0")


@pytest.mark.local_cache
def test_local_cache_5_family_cluster_a_smoke_shard() -> None:
    grid = fam5.generate_cluster_a_candidate_grid()
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in grid:
        if c["family_id"] not in seen:
            picked.append(c)
            seen.add(c["family_id"])
        if len(picked) == 5:
            break
    res = fam5.evaluate_candidate_shard(picked, split="cluster_a", include_daily_returns=False)
    _check(res["candidate_count"] == 5, f"Expected 5 smoke results, got {res['candidate_count']}")
    _check(res["order_send_count"] == 0, "order_send_count != 0")
    _check(res["holdout_rows_analysed"] == 0, "holdout_rows_analysed != 0")
    _check(res["max_ts_seen"] < fam5.CLUSTER_B_START_SEC, "Cluster A smoke shard leaked 2021+ timestamp!")
    for r in res["results"]:
        _check(r["all_flat_by_2050_utc"] is True, f"{r['candidate_id']} breached 20:50 UTC hard flat!")
        _check(r["swap_r_total"] == 0.0, f"{r['candidate_id']} non-zero swap!")
