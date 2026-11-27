"""100% Offline Mocked Unit & Invariant Tests for Wave 4 Multi-Source Compliant M1 Harvester (W4-G16).

Verifies (zero live MT5 launches, zero live QDM invocations, zero HTTP/WAF bypass, OrderSend = 0):
  1. Exact 16-symbol remaining inventory discovery (`28` in `ASSET_DEFAULT_SCALES` minus `12` in manifest).
  2. Direct `qdmcli.exe` command builder & runner (rejects `broker=SQ Default` whitespace bug, rejects
     `action=update`, enforces `dateto <= 2024.12.31`, passes `creationflags=_NO_WINDOW_FLAGS`,
     enforces single-process file lock, zero `trading_workspace_v2` / `psycopg` imports).
  3. Honest source provenance tagging across all 4 tags (`DUKASCOPY_TRUE_BID_ASK`,
     `QDM_PROVIDER_DEFAULT_SINGLE_SIDE`, `FTMO_BID_PLUS_SPREAD`, `HISTDATA_BID_ONLY`) in sealed
     Parquets, zero-pickle `.npz`, fragments, and merged `manifest.json` — plus anti-masquerade
     blocks against spoofing single-side / FTMO spread as true 2-side Bid/Ask.
  4. Hard `< 2025-01-01` Holdout fail-closed rejection under both `python` AND `python -O`
     across Tier 1 QDM, Tier 2 FTMO-Demo, Tier 3 HistData/TrueFX (including EST_FIXED -> UTC
     boundary rollover!), and `seal_generic_m1_arrays`.
  5. Poisoned input fail-closed rejection: `<= 0` prices, `NaN`/`Inf`, broken OHLC ordering,
     non-monotonic/duplicate timestamps, negative spreads, `bool` disguised as numeric, ZIP slip,
     and `waf_bypass_attempted=True`.
  6. 3-tier cascade (`QDM CLI -> FTMO-Demo -> HistData/TrueFX`) + `[MT5 LOCK]` fail-closed guard
     + `x13_m1_loader` compatibility + AST zero-assert & creationflags verification.

All invariant checks use `_check(...)` so they remain 100% effective under `python -O`.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import numpy as np
import pyarrow.parquet as pq
import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory import seal_asset_m1 as sam  # noqa: E402
from quant_factory.offensive3 import x13_m1_loader as x13_loader  # noqa: E402
from quant_factory.wave4 import multi_source_m1_harvester as harv  # noqa: E402

EXPECTED_PRESENT_12: tuple[str, ...] = (
    "EURUSD",
    "GBPUSD",
    "AUDUSD",
    "USDCAD",
    "USDJPY",
    "EURJPY",
    "GBPJPY",
    "US100",
    "US500",
    "GER40",
    "XAUUSD",
    "BTCUSD",
)
EXPECTED_MISSING_16: tuple[str, ...] = (
    "USDCHF",
    "NZDUSD",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "US30",
    "JP225",
    "UK100",
    "XAGUSD",
    "USOIL",
    "UKOIL",
)


def _check(cond: bool, msg: str) -> None:
    """Explicit invariant check immune to `python -O` assert stripping."""
    if not cond:
        raise AssertionError(msg)


def _make_dev_7y_arrays(
    *,
    base_price: float = 1.12000,
    spread: float = 0.00015,
    bars_per_year: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate clean strictly-dev (2018-2024) M1 timestamps, bid OHLC, ask OHLC, and spread pts."""
    ts_list: list[int] = []
    bid_list: list[list[float]] = []
    ask_list: list[list[float]] = []
    sp_pts_list: list[float] = []
    for y in range(2018, 2025):
        t0 = int(datetime(y, 4, 20, 12, 0, tzinfo=UTC).timestamp())
        for k in range(bars_per_year):
            o = base_price + 0.0005 * k
            c = o + 0.0002
            h = max(o, c) + 0.0003
            lo = min(o, c) - 0.0003
            ts_list.append(t0 + 60 * k)
            bid_list.append([o, h, lo, c])
            ask_list.append([o + spread, h + spread, lo + spread, c + spread])
            sp_pts_list.append(15.0)
    return (
        np.asarray(ts_list, dtype=np.int64),
        np.asarray(bid_list, dtype=np.float64),
        np.asarray(ask_list, dtype=np.float64),
        np.asarray(sp_pts_list, dtype=np.float64),
    )


def _write_qdm_csv(path: Path, times_sec: np.ndarray, ohlc: np.ndarray) -> None:
    lines = ["Date,Time,Open,High,Low,Close,Volume"]
    for t, row in zip(times_sec, ohlc, strict=True):
        dt = datetime.fromtimestamp(int(t), tz=UTC)
        lines.append(
            f"{dt.strftime('%Y.%m.%d')},{dt.strftime('%H:%M:%S')},"
            f"{row[0]:.5f},{row[1]:.5f},{row[2]:.5f},{row[3]:.5f},100"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _write_mock_12_manifest(manifest_path: Path) -> None:
    payload = {
        "schema": "naqex-hot-m1-cache-v1",
        "holdout_lock_sha256": sam.LOCK_SHA,
        "holdout_rows": 0,
        "assets": {
            sym: {
                "dir": sym.lower(),
                "native_Ask": True,
                "scale": sam.ASSET_DEFAULT_SCALES[sym],
                "years": {},
            }
            for sym in EXPECTED_PRESENT_12
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


class _FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_REAL = 2
    TIMEFRAME_M1 = 1

    def __init__(
        self,
        *,
        rates: list[dict[str, Any]],
        trade_mode: int = 0,
        server: str = "FTMO-Demo",
        point: float = 0.00001,
    ) -> None:
        self.rates = rates
        self.trade_mode = trade_mode
        self.server = server
        self.point = point
        self.init_kwargs: dict[str, Any] = {}
        self.shutdown_called = False
        self.last_range_args: tuple[Any, ...] = ()

    def initialize(self, **kwargs: Any) -> bool:
        self.init_kwargs = dict(kwargs)
        return True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def account_info(self) -> Any:
        return SimpleNamespace(login=1515343318, server=self.server, trade_mode=self.trade_mode)

    def symbol_select(self, _sym: str, _enable: bool) -> bool:
        return True

    def symbol_info(self, _sym: str) -> Any:
        return SimpleNamespace(point=self.point)

    def copy_rates_range(self, symbol: str, timeframe: int, dt_from: datetime, dt_to: datetime) -> Any:
        self.last_range_args = (symbol, timeframe, dt_from, dt_to)
        return list(self.rates)


# ==============================================================================
# 1. Static Safety & Architecture Audits (Zero Assert, Zero psycopg, Creationflags)
# ==============================================================================


def test_01_static_safety_ast_guards_zero_assert_no_trader_import_creationflags() -> None:
    harv_path = AI_ENGINES_DIR / "quant_factory" / "wave4" / "multi_source_m1_harvester.py"
    seal_path = AI_ENGINES_DIR / "quant_factory" / "seal_asset_m1.py"
    test_path = Path(__file__).resolve()

    legacy_forbidden = "mt5-" + "tradingview-" + "backtester"
    for p in (harv_path, seal_path):
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(p))

        # ZERO bare assert statements (immune to python -O)
        asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        _check(not asserts, f"Bare assert(s) in {p.name} lines {asserts}")

        # NEVER import trading_workspace_v2 or psycopg or top-level MetaTrader5
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _check(
                        not alias.name.startswith(("trading_workspace_v2", "psycopg")),
                        f"Forbidden import {alias.name!r} in {p.name}:{node.lineno}",
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                _check(
                    not mod.startswith(("trading_workspace_v2", "psycopg")),
                    f"Forbidden from-import {mod!r} in {p.name}:{node.lineno}",
                )

        # NEVER embed legacy directory identifier
        _check(legacy_forbidden not in src, f"Legacy directory string leaked in {p.name}")

    # Verify MetaTrader5 is NEVER imported at top-level of multi_source_m1_harvester.py
    harv_tree = ast.parse(harv_path.read_text(encoding="utf-8"), filename=str(harv_path))
    for stmt in harv_tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                _check(alias.name != "MetaTrader5", "MetaTrader5 MUST be lazy-imported only!")
        elif isinstance(stmt, ast.ImportFrom):
            _check((stmt.module or "") != "MetaTrader5", "MetaTrader5 MUST be lazy-imported only!")

    # Verify EVERY subprocess.run/Popen call in multi_source_m1_harvester.py passes creationflags
    sub_calls = 0
    for node in ast.walk(harv_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                if node.func.attr in {"run", "Popen", "call", "check_call", "check_output"}:
                    sub_calls += 1
                    has_cf = any(kw.arg == "creationflags" for kw in node.keywords)
                    _check(has_cf, f"subprocess.{node.func.attr} at line {node.lineno} missing creationflags")
    _check(sub_calls >= 1, f"Expected >=1 subprocess call in harvester, got {sub_calls}")

    # Verify zero hardcoded legacy string in test file too
    _check(legacy_forbidden not in test_path.read_text(encoding="utf-8"), "Legacy dir string leaked in test file")

    # Module-level safety flags
    _check(harv.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be False")
    _check(harv.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be 0")
    _check(harv.WAF_BYPASS_ATTEMPTED is False, "WAF_BYPASS_ATTEMPTED must be False")
    _check(sam.WAF_BYPASS_ATTEMPTED is False, "seal_asset_m1.WAF_BYPASS_ATTEMPTED must be False")


# ==============================================================================
# 2. Exact 16-Symbol Inventory Discovery
# ==============================================================================


def test_02_exact_16_symbol_inventory_discovery_offline(tmp_path: Path) -> None:
    manifest_p = tmp_path / "manifest.json"
    _write_mock_12_manifest(manifest_p)

    inv = harv.discover_missing_m1_symbols(manifest_p)
    _check(inv["universe_count"] == 28, f"Expected 28 universe symbols, got {inv['universe_count']}")
    _check(inv["present_count"] == 12, f"Expected 12 present symbols, got {inv['present_count']}")
    _check(inv["missing_count"] == 16, f"Expected 16 missing symbols, got {inv['missing_count']}")
    _check(
        tuple(inv["missing_symbols"]) == EXPECTED_MISSING_16,
        f"Exact 16 missing mismatch: {inv['missing_symbols']}",
    )
    _check(inv["waf_bypass_attempted"] is False, "waf_bypass_attempted must be False")
    _check(inv["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")

    spec_by_sym = {s["canonical_symbol"]: s for s in inv["missing_specs"]}
    _check(spec_by_sym["US30"]["qdm_instrument_code"] == "USA30IDXUSD", "US30 QDM code mismatch")
    _check(spec_by_sym["JP225"]["qdm_instrument_code"] == "JPNIDXJPY", "JP225 QDM code mismatch")
    _check(spec_by_sym["UK100"]["qdm_instrument_code"] == "GBRIDXGBP", "UK100 QDM code mismatch")
    _check(spec_by_sym["USOIL"]["qdm_instrument_code"] == "LIGHTCMDUSD", "USOIL QDM code mismatch")
    _check(spec_by_sym["UKOIL"]["qdm_instrument_code"] == "BRENTCMDUSD", "UKOIL QDM code mismatch")
    _check(spec_by_sym["US30"]["ftmo_symbol"] == "US30.cash", "US30 FTMO symbol mismatch")
    _check(spec_by_sym["USDCHF"]["histdata_fx_eligible"] is True, "USDCHF should be HistData FX eligible")
    _check(spec_by_sym["US30"]["histdata_fx_eligible"] is False, "US30 should not be FX-only HistData eligible")


@pytest.mark.local_cache
def test_02b_real_local_manifest_confirms_exact_16_remaining() -> None:
    inv = harv.discover_missing_m1_symbols(harv.DEFAULT_MANIFEST_PATH)
    _check(inv["universe_count"] == 28, f"Expected 28 total, got {inv['universe_count']}")
    _check(inv["present_count"] == 12, f"Expected 12 present in local manifest, got {inv['present_count']}")
    _check(inv["missing_count"] == 16, f"Expected 16 missing in local manifest, got {inv['missing_count']}")
    _check(set(inv["missing_symbols"]) == set(EXPECTED_MISSING_16), f"Local missing mismatch: {inv['missing_symbols']}")


# ==============================================================================
# 3. Tier 1 QDM CLI Command Builder, Guards, Lock & Mocked Subprocess
# ==============================================================================


def test_03_qdm_command_builder_rejects_broker_whitespace_and_post2024_and_passes_creationflags(
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "qdm_home"
    fake_home.mkdir()
    fake_exe = fake_home / "qdmcli.exe"
    fake_exe.write_bytes(b"MZ")
    out_dir = tmp_path / "qdm_out"

    # Valid export command strictly <= 2024.12.31
    cmd = harv.build_qdm_export_command(
        fake_exe,
        qdm_symbol="USDCHF_TW",
        output_dir=out_dir,
        date_from="2018-01-01",
        date_to="2024-12-31",
    )
    _check("action=export" in cmd, f"Missing action=export: {cmd}")
    _check("dateto=2024.12.31" in cmd, f"Expected dateto=2024.12.31: {cmd}")
    _check("timezone=UTC" in cmd, f"Expected timezone=UTC: {cmd}")
    _check(not any(a.lower().startswith("broker=") for a in cmd[1:]), f"Unexpected broker arg: {cmd}")

    # Reject broker=SQ Default whitespace bug!
    with pytest.raises(ValueError, match="QDM_FORBIDDEN_BROKER_ARG"):
        harv.build_qdm_export_command(
            fake_exe,
            qdm_symbol="USDCHF_TW",
            output_dir=out_dir,
            extra_args=["broker=SQ Default"],
        )
    with pytest.raises(ValueError, match="QDM_FORBIDDEN_BROKER_ARG"):
        harv.validate_qdm_argv([str(fake_exe), "-symbol", "action=add", "broker=SQ Default"])

    # Reject action=update inside export command builder
    with pytest.raises(ValueError, match="QDM_FORBIDDEN_ACTION"):
        harv.build_qdm_export_command(
            fake_exe,
            qdm_symbol="USDCHF_TW",
            output_dir=out_dir,
            extra_args=["action=update"],
        )

    # Reject Holdout >= 2025-01-01 under both python and python -O
    for bad_date in ("2025.01.01", "2025-01-01", "2026.06.15"):
        with pytest.raises(HoldoutLockError):
            harv.build_qdm_export_command(
                fake_exe,
                qdm_symbol="USDCHF_TW",
                output_dir=out_dir,
                date_to=bad_date,
            )

    # Verify runtime creationflags=_NO_WINDOW_FLAGS & single-process lock on mocked subprocess.run
    ts, bid, _, _ = _make_dev_7y_arrays(base_price=0.91000)
    expected_cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    captured_calls: list[dict[str, Any]] = []

    def _fake_run(argv: list[str], **kwargs: Any) -> Any:
        captured_calls.append({"argv": list(argv), "kwargs": dict(kwargs)})
        # Simulate qdmcli exporting the CSV file into outputdir
        out_arg = next(a.split("=", 1)[1] for a in argv if a.startswith("outputdir="))
        _write_qdm_csv(Path(out_arg) / "USDCHF_TW_M1.csv", ts, bid)
        return SimpleNamespace(returncode=0, stdout="Export done.\nExit app - ok\n", stderr="")

    lock_f = tmp_path / ".qdm_cli.lock"
    adapter = harv.QdmCliAdapter(qdm_home=fake_home, lock_path=lock_f)
    spec = harv.build_symbol_harvest_spec("USDCHF")
    with patch.object(harv.subprocess, "run", side_effect=_fake_run):
        batch = adapter.export_symbol_m1(spec, out_dir)

    _check(len(captured_calls) == 1, f"Expected 1 subprocess call, got {len(captured_calls)}")
    _check("creationflags" in captured_calls[0]["kwargs"], "Missing creationflags in subprocess.run call")
    _check(
        int(captured_calls[0]["kwargs"]["creationflags"]) == expected_cf,
        f"creationflags={captured_calls[0]['kwargs']['creationflags']} != {expected_cf}",
    )
    _check(not lock_f.exists(), "Single-process QDM lock must be released after exit")
    _check(
        batch.source_provenance == sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        f"Wrong QDM provenance: {batch.source_provenance}",
    )
    _check(batch.native_ask is False and batch.has_true_bid_ask is False, "QDM MUST NOT claim true Bid/Ask")
    _check(batch.ask_ohlc is None, "QDM single-side batch must have ask_ohlc=None")
    _check(batch.waf_bypass_attempted is False, "waf_bypass_attempted must be False")

    # Pre-existing lock file must fail closed with QdmBusyError WITHOUT deleting holder's lock!
    lock_f.write_text('{"pid": 99999}\n', encoding="utf-8")
    with pytest.raises(harv.QdmBusyError):
        adapter.run_command(harv.build_qdm_symbol_list_command(fake_exe))
    _check(lock_f.exists(), "Rejected QDM caller MUST NOT delete another holder's lock file")
    lock_f.unlink()

    # Verify symbol list stdout parser & license error classification
    sample_list = (
        "Startup info\n"
        f"{harv.QDM_LIST_HEADER}\n"
        "USDCHF_TW,USDCHF,M1,UTC,2018.01.01,2024.12.31,2000,100000,dukascopy,M1\n"
        "Data listed.\nExit app - ok\n"
    )
    rows = harv.parse_qdm_symbol_list_output(sample_list)
    _check(len(rows) == 1 and rows[0]["Symbol"] == "USDCHF_TW", f"Unexpected QDM list parse: {rows}")
    with patch.object(
        harv.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=1, stdout="Missing license file", stderr=""),
    ):
        with pytest.raises(harv.QdmLicenseError):
            adapter.list_cached_symbols()


def test_04_qdm_dynamic_discovery_env_and_projects_glob(tmp_path: Path) -> None:
    # 1. Via TW_V2_QDM_HOME env var
    env_qdm = tmp_path / "env_qdm"
    env_qdm.mkdir()
    exe1 = env_qdm / "qdmcli.exe"
    exe1.write_bytes(b"MZ")
    found_env = harv.discover_qdm_executable(repo_root=tmp_path, env={"TW_V2_QDM_HOME": str(env_qdm)})
    _check(found_env == exe1.resolve(), f"Env discovery failed: {found_env}")

    # 2. Via dynamic projects/*/foundation_v2/.runtime/quantdatamanager/qdmcli.exe scan (zero hardcoded legacy name)
    dyn_dir = tmp_path / "projects" / "custom-checkout" / "foundation_v2" / ".runtime" / "quantdatamanager"
    dyn_dir.mkdir(parents=True)
    exe2 = dyn_dir / "qdmcli.exe"
    exe2.write_bytes(b"MZ")
    found_dyn = harv.discover_qdm_executable(repo_root=tmp_path, env={})
    _check(found_dyn == exe2.resolve(), f"Dynamic projects glob discovery failed: {found_dyn}")


# ==============================================================================
# 4. Honest Provenance Tagging, Sealing (.parquet + .npz + manifest) & Anti-Spoof
# ==============================================================================


def test_05_honest_provenance_sealing_parquet_npz_and_manifest_merge(tmp_path: Path) -> None:
    cache_dir = tmp_path / "hot_cache"
    frags_dir = cache_dir / "_fragments"
    npz_dir = tmp_path / "sealed_npz"

    ts, bid, ask, sp_pts = _make_dev_7y_arrays(base_price=0.91000, spread=0.00015)

    # A) QDM single-side -> QDM_PROVIDER_DEFAULT_SINGLE_SIDE (4 cols, native_Ask=False, NEVER TRUE_BID_ASK!)
    frag_qdm = sam.seal_generic_m1_arrays(
        "USDCHF",
        ts,
        bid,
        source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        fragment_out=frags_dir / "usdchf_qdm.json",
        npz_out=npz_dir / "USDCHF.npz",
        cache_dir=cache_dir,
    )
    _check(frag_qdm["source_provenance"] == "QDM_PROVIDER_DEFAULT_SINGLE_SIDE", "QDM provenance mismatch")
    _check(frag_qdm["native_Ask"] is False, "QDM native_Ask must be False")
    _check(frag_qdm["has_true_bid_ask"] is False, "QDM has_true_bid_ask must be False")
    _check(frag_qdm["ask_columns_present"] is False, "QDM ask_columns_present must be False")
    _check(frag_qdm["waf_bypass_attempted"] is False, "waf_bypass_attempted must be False")
    _check(frag_qdm["holdout_rows"] == 0, "holdout_rows must be 0")

    # Verify sealed Parquet has ONLY 5 cols (minute, bo, bh, bl, bc) — zero fabricated Ask cols
    p2024_qdm = cache_dir / "usdchf" / frag_qdm["years"]["2024"]["parquet"]
    _check("QDM_SINGLE" in p2024_qdm.name and "BIDASK" not in p2024_qdm.name, f"Misleading filename: {p2024_qdm.name}")
    tbl_qdm = pq.read_table(p2024_qdm)
    _check(tbl_qdm.column_names == ["minute", "bo", "bh", "bl", "bc"], f"Unexpected QDM cols: {tbl_qdm.column_names}")

    # Verify zero-pickle .npz records honest provenance
    with np.load(npz_dir / "USDCHF.npz", allow_pickle=False) as z:
        _check(str(z["source_provenance"].item()) == "QDM_PROVIDER_DEFAULT_SINGLE_SIDE", "NPZ QDM provenance mismatch")
        _check(bool(z["native_ask"].item()) is False, "NPZ native_ask must be False")
        _check(bool(z["has_true_bid_ask"].item()) is False, "NPZ has_true_bid_ask must be False")
        _check(bool(z["waf_bypass_attempted"].item()) is False, "NPZ waf_bypass must be False")
        _check("ask_ohlc" not in z.files, "Single-side NPZ must not contain ask_ohlc")

    # B) FTMO-Demo Bid + Spread -> FTMO_BID_PLUS_SPREAD (reconstructed Ask, native_Ask=False, ask_columns_present=True)
    frag_ftmo = sam.seal_generic_m1_arrays(
        "US30",
        ts,
        bid * 38000.0,
        source_provenance=sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
        spread_points=np.full(ts.size, 180.0, dtype=np.float64),
        point_size=0.01,
        fragment_out=frags_dir / "us30_ftmo.json",
        npz_out=npz_dir / "US30.npz",
        cache_dir=cache_dir,
    )
    _check(frag_ftmo["source_provenance"] == "FTMO_BID_PLUS_SPREAD", "FTMO provenance mismatch")
    _check(frag_ftmo["native_Ask"] is False and frag_ftmo["has_true_bid_ask"] is False, "FTMO is not native true Ask")
    _check(frag_ftmo["ask_columns_present"] is True, "FTMO should have reconstructed ask columns")
    with np.load(npz_dir / "US30.npz", allow_pickle=False) as z:
        _check(str(z["source_provenance"].item()) == "FTMO_BID_PLUS_SPREAD", "NPZ FTMO provenance mismatch")
        _check("ask_ohlc" in z.files, "FTMO NPZ must include ask_ohlc")
        _check(
            np.allclose(z["ask_ohlc"] - z["bid_ohlc"], 1.80, atol=1e-9),
            "FTMO reconstructed ask - bid must equal spread_points * point_size (180 * 0.01 = 1.80)",
        )

    # C) HistData Bid-Only -> HISTDATA_BID_ONLY
    frag_hd = sam.seal_generic_m1_arrays(
        "NZDUSD",
        ts,
        bid * 0.65,
        source_provenance=sam.PROVENANCE_HISTDATA_BID_ONLY,
        fragment_out=frags_dir / "nzdusd_histdata.json",
        npz_out=npz_dir / "NZDUSD.npz",
        cache_dir=cache_dir,
    )
    _check(frag_hd["source_provenance"] == "HISTDATA_BID_ONLY", "HistData provenance mismatch")
    _check(
        frag_hd["native_Ask"] is False and frag_hd["has_true_bid_ask"] is False,
        "HistData must not claim native Ask",
    )

    # D) True 2-side Dukascopy -> DUKASCOPY_TRUE_BID_ASK
    frag_dk = sam.seal_generic_m1_arrays(
        "EURGBP",
        ts,
        bid * 0.85,
        ask_ohlc=ask * 0.85,
        source_provenance=sam.PROVENANCE_DUKASCOPY_TRUE_BID_ASK,
        fragment_out=frags_dir / "eurgbp_dk.json",
        cache_dir=cache_dir,
    )
    _check(frag_dk["source_provenance"] == "DUKASCOPY_TRUE_BID_ASK", "Dukascopy provenance mismatch")
    _check(frag_dk["native_Ask"] is True and frag_dk["has_true_bid_ask"] is True, "Dukascopy must set native_Ask=True")

    # Merge ALL 4 provenance fragments into manifest.json and verify x13_m1_loader compatibility!
    summary = sam.merge_fragments(frags_dir, cache_dir=cache_dir)
    _check(summary["merged_count"] == 4, f"Expected 4 merged assets, got {summary['merged_count']}")
    man = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))
    _check(man["assets"]["USDCHF"]["source_provenance"] == "QDM_PROVIDER_DEFAULT_SINGLE_SIDE", "Manifest USDCHF prov")
    _check(man["assets"]["USDCHF"]["native_Ask"] is False, "Manifest USDCHF native_Ask")
    _check(man["assets"]["US30"]["source_provenance"] == "FTMO_BID_PLUS_SPREAD", "Manifest US30 prov")
    _check(man["assets"]["NZDUSD"]["source_provenance"] == "HISTDATA_BID_ONLY", "Manifest NZDUSD prov")
    _check(man["assets"]["EURGBP"]["source_provenance"] == "DUKASCOPY_TRUE_BID_ASK", "Manifest EURGBP prov")
    _check(man["assets"]["EURGBP"]["native_Ask"] is True, "Manifest EURGBP native_Ask")

    # Downstream x13_m1_loader reads 4-col QDM/HistData/FTMO AND 8-col Dukascopy cleanly!
    t_q, q_q, m_q = x13_loader.load_m1_asset("USDCHF", cache_dir, verify_sha=True)
    _check(t_q.size == ts.size and q_q.shape == (ts.size, 4), f"Unexpected USDCHF loaded shape: {q_q.shape}")
    _check(m_q["source_provenance"] == "QDM_PROVIDER_DEFAULT_SINGLE_SIDE", "Loaded meta provenance mismatch")

    t_d, q_d, m_d = x13_loader.load_m1_asset("EURGBP", cache_dir, verify_sha=True)
    _check(t_d.size == ts.size and q_d.shape == (ts.size, 8), f"Unexpected EURGBP loaded shape: {q_d.shape}")
    _check(m_d["source_provenance"] == "DUKASCOPY_TRUE_BID_ASK", "Loaded meta EURGBP provenance mismatch")

    # Anti-spoof checks: single-side provenance MUST reject ask_ohlc & spoofed native_Ask=True fragment!
    with pytest.raises(ValueError, match="PROVENANCE_MISMATCH"):
        sam.seal_generic_m1_arrays(
            "USDCHF",
            ts,
            bid,
            ask_ohlc=ask,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
            cache_dir=cache_dir,
        )
    with pytest.raises(ValueError, match="PROVENANCE_MISMATCH"):
        sam.seal_generic_m1_arrays(
            "EURGBP",
            ts,
            bid,
            ask_ohlc=None,
            source_provenance=sam.PROVENANCE_DUKASCOPY_TRUE_BID_ASK,
            cache_dir=cache_dir,
        )

    spoof_dir = tmp_path / "spoof_frags"
    spoof_dir.mkdir()
    bad_frag = dict(frag_qdm)
    bad_frag["native_Ask"] = True
    (spoof_dir / "spoof.json").write_text(json.dumps(bad_frag), encoding="utf-8")
    with pytest.raises(ValueError, match="PROVENANCE_SPOOF_BLOCKED"):
        sam.merge_fragments(spoof_dir, cache_dir=cache_dir)


# ==============================================================================
# 5. Hard Holdout < 2025-01-01 Fail-Closed Under python -O (All 3 Tiers + Sealer)
# ==============================================================================


def test_06_holdout_2025_bar_fails_closed_all_tiers_and_sealer(tmp_path: Path) -> None:
    ts_2025 = int(datetime(2025, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    ts_2024 = int(datetime(2024, 12, 31, 23, 59, tzinfo=UTC).timestamp())

    # Tier 1 QDM CSV containing 2025-01-01 00:00:00 -> HoldoutLockError
    qdm_bad = tmp_path / "qdm_2025.csv"
    _write_qdm_csv(
        qdm_bad,
        np.asarray([ts_2024, ts_2025], dtype=np.int64),
        np.asarray([[0.90, 0.91, 0.89, 0.905], [0.905, 0.915, 0.90, 0.91]], dtype=np.float64),
    )
    with pytest.raises(HoldoutLockError):
        harv.parse_qdm_m1_csv(qdm_bad, asset="USDCHF")

    # Tier 2 FTMO-Demo rates containing 2025-01-01 00:00:00 -> HoldoutLockError
    bad_ftmo_rates = [
        {"time": ts_2024, "open": 0.90, "high": 0.91, "low": 0.89, "close": 0.905, "spread": 10},
        {"time": ts_2025, "open": 0.905, "high": 0.915, "low": 0.90, "close": 0.91, "spread": 10},
    ]
    with pytest.raises(HoldoutLockError):
        harv.parse_ftmo_mt5_rates(bad_ftmo_rates, asset="USDCHF", point_size=1e-5)

    # Tier 3 HistData ZIP with EST_FIXED rollover: 20241231 190000 EST == 2025-01-01 00:00:00 UTC -> HoldoutLockError!
    zip_bad = tmp_path / "DAT_ASCII_USDCHF_M1_2024.zip"
    with zipfile.ZipFile(zip_bad, "w") as zf:
        zf.writestr(
            "DAT_ASCII_USDCHF_M1_2024.csv",
            "20241231 185900;0.90000;0.90050;0.89950;0.90020;0\n"
            "20241231 190000;0.90020;0.90060;0.89980;0.90040;0\n",
        )
    with pytest.raises(HoldoutLockError):
        harv.parse_histdata_m1_files(zip_bad, asset="USDCHF", source_timezone="EST_FIXED")

    # Sealer direct call with 2025-01-01 AND negative price + filter_nonpositive=True MUST STILL raise HoldoutLockError!
    with pytest.raises(HoldoutLockError):
        sam.seal_generic_m1_arrays(
            "USOIL",
            np.asarray([ts_2024, ts_2025], dtype=np.int64),
            np.asarray([[70.0, 71.0, 69.0, 70.5], [-5.0, -4.0, -6.0, -5.0]], dtype=np.float64),
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
            cache_dir=tmp_path / "cache_ho",
            filter_nonpositive=True,
        )


# ==============================================================================
# 6. Poisoned Data Fail-Closed (<=0, NaN/Inf, Bad OHLC, Non-Monotonic, Bool, WAF)
# ==============================================================================


def test_07_poisoned_prices_ohlc_bool_waf_and_zip_slip_fail_closed(tmp_path: Path) -> None:
    t0 = int(datetime(2024, 6, 3, 10, 0, tzinfo=UTC).timestamp())
    ts2 = np.asarray([t0, t0 + 60], dtype=np.int64)
    good2 = np.asarray([[1.10, 1.12, 1.09, 1.11], [1.11, 1.13, 1.10, 1.12]], dtype=np.float64)

    # 1. Price <= 0 fails closed by default; quarantined only with explicit filter_nonpositive=True
    neg_ohlc = np.asarray([[-1.0, 1.0, -5.0, 0.0], [1.11, 1.13, 1.10, 1.12]], dtype=np.float64)
    with pytest.raises(ValueError, match="NONPOSITIVE_PRICE_ANOMALY"):
        harv.validate_m1_bars(
            "USOIL",
            ts2,
            neg_ohlc,
            tier=harv.TIER_1_QDM_CLI,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        )
    filtered = harv.validate_m1_bars(
        "USOIL",
        ts2,
        neg_ohlc,
        tier=harv.TIER_1_QDM_CLI,
        source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        filter_nonpositive=True,
    )
    _check(filtered.bar_count == 1 and filtered.nonpositive_filtered == 1, "filter_nonpositive must keep 1 valid bar")

    # 2. NaN & Inf fail closed
    for bad_val in (float("nan"), float("inf"), float("-inf")):
        poisoned = good2.copy()
        poisoned[1, 3] = bad_val
        with pytest.raises(ValueError, match="NONFINITE_PRICE"):
            harv.validate_m1_bars(
                "USDCHF",
                ts2,
                poisoned,
                tier=harv.TIER_1_QDM_CLI,
                source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
            )

    # 3. Broken OHLC order: high < close or low > open fails closed
    bad_high = np.asarray([[1.10, 1.105, 1.09, 1.11], [1.11, 1.13, 1.10, 1.12]], dtype=np.float64)
    with pytest.raises(ValueError, match="OHLC_INTEGRITY_VIOLATION"):
        harv.validate_m1_bars(
            "USDCHF",
            ts2,
            bad_high,
            tier=harv.TIER_1_QDM_CLI,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        )
    bad_low = np.asarray([[1.10, 1.12, 1.105, 1.11], [1.11, 1.13, 1.10, 1.12]], dtype=np.float64)
    with pytest.raises(ValueError, match="OHLC_INTEGRITY_VIOLATION"):
        harv.validate_m1_bars(
            "USDCHF",
            ts2,
            bad_low,
            tier=harv.TIER_1_QDM_CLI,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        )

    # 4. Non-monotonic / duplicate timestamps fail closed
    with pytest.raises(ValueError, match="NON_MONOTONIC_TIMESTAMPS"):
        harv.validate_m1_bars(
            "USDCHF",
            np.asarray([t0, t0], dtype=np.int64),
            good2,
            tier=harv.TIER_1_QDM_CLI,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        )

    # 5. Bool disguised as numeric fails closed
    with pytest.raises(ValueError, match="INVALID_OHLC_DTYPE"):
        harv.validate_m1_bars(
            "USDCHF",
            ts2,
            np.ones((2, 4), dtype=np.bool_),
            tier=harv.TIER_1_QDM_CLI,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        )

    # 6. Negative spread fails closed
    with pytest.raises(ValueError, match="NEGATIVE_SPREAD"):
        harv.validate_m1_bars(
            "USDCHF",
            ts2,
            good2,
            tier=harv.TIER_2_FTMO_DEMO,
            source_provenance=sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
            spread_points=np.asarray([10.0, -1.0], dtype=np.float64),
            point_size=1e-5,
        )

    # 7. waf_bypass_attempted=True MUST fail closed everywhere
    with pytest.raises(ValueError, match="WAF_BYPASS_FORBIDDEN"):
        harv.validate_m1_bars(
            "USDCHF",
            ts2,
            good2,
            tier=harv.TIER_1_QDM_CLI,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
            waf_bypass_attempted=True,
        )
    with pytest.raises(ValueError, match="WAF_BYPASS_FORBIDDEN"):
        sam.seal_generic_m1_arrays(
            "USDCHF",
            ts2,
            good2,
            source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
            cache_dir=tmp_path / "cache_waf",
            waf_bypass_attempted=True,
        )

    # 8. ZIP path traversal rejected fail-closed
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../escape.csv", "20240603 100000;1.10;1.12;1.09;1.11;0\n")
    with pytest.raises(ValueError, match="HISTDATA_ZIP_UNSAFE_PATH"):
        harv.parse_histdata_m1_files(evil_zip, asset="USDCHF")


# ==============================================================================
# 7. 3-Tier Compliant Cascade, [MT5 LOCK] Guard & Dry-Run CLI
# ==============================================================================


def test_08_three_tier_cascade_mt5_lock_guard_and_dry_run_cli(tmp_path: Path) -> None:
    cache_dir = tmp_path / "hot_cache"
    work_dir = tmp_path / "work"
    _write_mock_12_manifest(cache_dir / "manifest.json")

    ts, bid, _, _ = _make_dev_7y_arrays(base_price=0.88000, spread=0.00010, bars_per_year=2)
    ftmo_rates = [
        {
            "time": int(t),
            "open": float(r[0]),
            "high": float(r[1]),
            "low": float(r[2]),
            "close": float(r[3]),
            "spread": 10,
        }
        for t, r in zip(ts, bid, strict=True)
    ]

    # A) Tier 2 FTMO-Demo MUST fail closed without mt5_lock_held=True (zero terminal64 launch!)
    ftmo_only = harv.FtmoDemoM1Adapter(terminal_exe=tmp_path / "portable" / "terminal64.exe")
    with pytest.raises(harv.Mt5LockRequiredError):
        ftmo_only.fetch_symbol_m1(harv.build_symbol_harvest_spec("US30"), mt5_lock_held=False)

    # Reject Program Files MT5 path fail-closed
    pf_exe = Path(r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe")
    pf_adapter = harv.FtmoDemoM1Adapter(terminal_exe=pf_exe)
    with pytest.raises(harv.HarvesterError, match="FORBIDDEN_PROGRAM_FILES_MT5"):
        pf_adapter.fetch_symbol_m1(
            harv.build_symbol_harvest_spec("US30"),
            mt5_lock_held=True,
            mt5_module=_FakeMT5(rates=ftmo_rates, point=0.01),
        )

    # Reject non-Demo REAL account fail-closed
    with pytest.raises(harv.HarvesterError, match="FTMO_NON_DEMO_BLOCKED"):
        ftmo_only.fetch_symbol_m1(
            harv.build_symbol_harvest_spec("US30"),
            mt5_lock_held=True,
            mt5_module=_FakeMT5(rates=ftmo_rates, trade_mode=2, point=0.01),
        )

    # Verify Tier 2 pre-exported FTMO CSV & delegated exporter paths
    ftmo_csv_dir = tmp_path / "ftmo_csv"
    ftmo_csv_dir.mkdir()
    csv_lines = ["time_utc,open,high,low,close,spread"]
    for rec in ftmo_rates:
        csv_lines.append(
            f"{rec['time']},{rec['open']:.5f},{rec['high']:.5f},{rec['low']:.5f},{rec['close']:.5f},{rec['spread']}"
        )
    (ftmo_csv_dir / "US30.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8", newline="\n")
    csv_batch = harv.FtmoDemoM1Adapter(export_dir=ftmo_csv_dir).fetch_symbol_m1(
        harv.build_symbol_harvest_spec("US30"),
        mt5_lock_held=False,
    )
    _check(csv_batch.source_provenance == sam.PROVENANCE_FTMO_BID_PLUS_SPREAD, "FTMO CSV provenance mismatch")
    _check(csv_batch.bar_count == len(ftmo_rates), "FTMO CSV bar count mismatch")

    del_adapter = harv.FtmoDemoM1Adapter(delegate_exporter=lambda **_kw: ftmo_rates)
    with pytest.raises(harv.Mt5LockRequiredError):
        del_adapter.fetch_symbol_m1(harv.build_symbol_harvest_spec("US30"), mt5_lock_held=False)
    del_batch = del_adapter.fetch_symbol_m1(harv.build_symbol_harvest_spec("US30"), mt5_lock_held=True)
    _check(del_batch.source_provenance == sam.PROVENANCE_FTMO_BID_PLUS_SPREAD, "FTMO delegate provenance mismatch")

    # Verify Tier 2 ftmo_m1_exporter.py .npz interoperability (incl. pre-2018 slice & 2025 Holdout fail-closed!)
    ftmo_npz_dir = tmp_path / "ftmo_npz"
    ftmo_npz_dir.mkdir()
    pre2018_ts = int(datetime(2017, 6, 1, 12, 0, tzinfo=UTC).timestamp())
    np.savez(
        ftmo_npz_dir / "US30.cash.npz",
        ts_utc=np.concatenate([np.asarray([pre2018_ts], dtype=np.int64), ts]),
        open=np.concatenate([np.asarray([21000.0]), bid[:, 0] * 38000.0]),
        high=np.concatenate([np.asarray([21010.0]), bid[:, 1] * 38000.0]),
        low=np.concatenate([np.asarray([20990.0]), bid[:, 2] * 38000.0]),
        close=np.concatenate([np.asarray([21005.0]), bid[:, 3] * 38000.0]),
        spread_pts=np.full(ts.size + 1, 180.0, dtype=np.float64),
        tick_volume=np.ones(ts.size + 1, dtype=np.int64),
    )
    npz_batch = harv.FtmoDemoM1Adapter(export_dir=ftmo_npz_dir).fetch_symbol_m1(
        harv.build_symbol_harvest_spec("US30"),
        mt5_lock_held=False,
    )
    _check(npz_batch.source_provenance == sam.PROVENANCE_FTMO_BID_PLUS_SPREAD, "FTMO NPZ provenance mismatch")
    _check(npz_batch.bar_count == ts.size, f"Expected pre-2018 sliced to {ts.size} bars, got {npz_batch.bar_count}")
    _check(npz_batch.ask_ohlc is not None and np.allclose(npz_batch.ask_ohlc - npz_batch.bid_ohlc, 1.80), "NPZ spread")

    ts_ho = int(datetime(2025, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    bad_npz = tmp_path / "bad_ho.npz"
    np.savez(
        bad_npz,
        ts_utc=np.asarray([int(ts[-1]), ts_ho], dtype=np.int64),
        open=np.asarray([38000.0, 38001.0]),
        high=np.asarray([38010.0, 38011.0]),
        low=np.asarray([37990.0, 37991.0]),
        close=np.asarray([38005.0, 38006.0]),
        spread_pts=np.asarray([180.0, 180.0]),
    )
    with pytest.raises(HoldoutLockError):
        harv.parse_ftmo_m1_npz(bad_npz, asset="US30", point_size=0.01)

    # B) Cascade Case 1: Tier 1 QDM missing -> cascades to Tier 2 FTMO (mocked under mt5_lock_held=True) -> SEALED_OK!
    fake_mt5 = _FakeMT5(rates=ftmo_rates, trade_mode=0, server="FTMO-Demo", point=1e-5)
    harvester_t2 = harv.MultiSourceM1Harvester(
        cache_dir=cache_dir,
        work_dir=work_dir,
        qdm_adapter=harv.QdmCliAdapter(qdm_home=tmp_path / "nonexistent_qdm", repo_root=tmp_path),
        ftmo_adapter=harv.FtmoDemoM1Adapter(terminal_exe=tmp_path / "portable" / "terminal64.exe"),
        histdata_adapter=harv.HistDataTrueFxAdapter(tmp_path / "empty_hd"),
    )
    res_t2 = harvester_t2.harvest_symbol("USDCHF", mt5_lock_held=True, mt5_module=fake_mt5)
    _check(res_t2.status == "SEALED_OK", f"Expected SEALED_OK via Tier 2, got {res_t2}")
    _check(res_t2.selected_tier == harv.TIER_2_FTMO_DEMO, f"Expected TIER_2, got {res_t2.selected_tier}")
    _check(res_t2.source_provenance == sam.PROVENANCE_FTMO_BID_PLUS_SPREAD, "Wrong Tier 2 provenance")
    _check(res_t2.native_ask is False and res_t2.has_true_bid_ask is False, "Tier 2 must not claim native Ask")
    _check(res_t2.waf_bypass_attempted is False and res_t2.holdout_rows_analysed == 0, "Safety flags")
    _check(fake_mt5.shutdown_called is True, "MT5 shutdown MUST always be called")
    _check(fake_mt5.init_kwargs.get("portable") is True, "MT5 MUST initialize with portable=True")

    # C) Cascade Case 2: Tier 1 QDM missing & Tier 2 blocked (mt5_lock_held=False) -> Tier 3 HistData ZIP -> SEALED_OK!
    hd_dir = tmp_path / "histdata_drop"
    hd_dir.mkdir()
    hd_zip = hd_dir / "DAT_ASCII_EURGBP_M1_2018_2024.zip"
    hd_lines = []
    for t, r in zip(ts, bid, strict=True):
        dt = datetime.fromtimestamp(int(t), tz=UTC)
        hd_lines.append(f"{dt.strftime('%Y%m%d %H%M%S')};{r[0]:.5f};{r[1]:.5f};{r[2]:.5f};{r[3]:.5f};0")
    with zipfile.ZipFile(hd_zip, "w") as zf:
        zf.writestr("DAT_ASCII_EURGBP_M1.csv", "\n".join(hd_lines) + "\n")

    harvester_t3 = harv.MultiSourceM1Harvester(
        cache_dir=cache_dir,
        work_dir=work_dir,
        qdm_adapter=harv.QdmCliAdapter(qdm_home=tmp_path / "nonexistent_qdm", repo_root=tmp_path),
        ftmo_adapter=harv.FtmoDemoM1Adapter(terminal_exe=tmp_path / "portable" / "terminal64.exe"),
        histdata_adapter=harv.HistDataTrueFxAdapter(hd_dir, source_timezone="UTC"),
    )
    res_t3 = harvester_t3.harvest_symbol("EURGBP", mt5_lock_held=False)
    _check(res_t3.status == "SEALED_OK", f"Expected SEALED_OK via Tier 3, got {res_t3}")
    _check(res_t3.selected_tier == harv.TIER_3_HISTDATA_TRUEFX, f"Expected TIER_3, got {res_t3.selected_tier}")
    _check(res_t3.source_provenance == sam.PROVENANCE_HISTDATA_BID_ONLY, "Wrong Tier 3 provenance")
    _check(len(res_t3.attempts) == 3, f"Expected 3 cascade attempts, got {len(res_t3.attempts)}")
    _check(
        res_t3.attempts[1].status == "FAILED_CASCADE_NEXT"
        and "Mt5LockRequiredError" in res_t3.attempts[1].reason,
        "Tier 2 must fail closed on missing MT5 lock",
    )
    _check(res_t3.waf_bypass_attempted is False, "waf_bypass_attempted must be False")

    # C2) Verify HistData MT4 dot-date format & EST_FIXED valid pre-cutoff boundary (18:59 EST -> 23:59 UTC)
    mt4_csv = tmp_path / "mt4_nzdusd.csv"
    mt4_csv.write_text(
        "2024.12.31,18:58,0.56100,0.56120,0.56080,0.56110,12\n"
        "2024.12.31,18:59,0.56110,0.56130,0.56090,0.56120,15\n",
        encoding="utf-8",
        newline="\n",
    )
    mt4_batch = harv.parse_histdata_m1_files(mt4_csv, asset="NZDUSD", source_timezone="EST_FIXED")
    _check(mt4_batch.max_ts_utc == "2024-12-31T23:59:00Z", f"EST->UTC shift wrong: {mt4_batch.max_ts_utc}")

    # C3) HoldoutLockError in Tier 1 MUST abort cascade immediately (NEVER swallowed into Tier 2/3!)
    qdm_ho_home = tmp_path / "qdm_ho"
    qdm_ho_home.mkdir()
    (qdm_ho_home / "qdmcli.exe").write_bytes(b"MZ")
    ts_2025 = int(datetime(2025, 1, 1, 0, 0, tzinfo=UTC).timestamp())

    def _fake_qdm_ho(argv: list[str], **_kwargs: Any) -> Any:
        out_arg = next(a.split("=", 1)[1] for a in argv if a.startswith("outputdir="))
        _write_qdm_csv(
            Path(out_arg) / "EURGBP_TW.csv",
            np.asarray([ts_2025], dtype=np.int64),
            np.asarray([[0.85, 0.86, 0.84, 0.855]], dtype=np.float64),
        )
        return SimpleNamespace(returncode=0, stdout="Exit app - ok\n", stderr="")

    harvester_ho = harv.MultiSourceM1Harvester(
        cache_dir=cache_dir,
        work_dir=work_dir / "ho_test",
        qdm_adapter=harv.QdmCliAdapter(qdm_home=qdm_ho_home, lock_path=tmp_path / ".ho.lock"),
        ftmo_adapter=harv.FtmoDemoM1Adapter(terminal_exe=tmp_path / "portable" / "terminal64.exe"),
        histdata_adapter=harv.HistDataTrueFxAdapter(hd_dir, source_timezone="UTC"),
    )
    with patch.object(harv.subprocess, "run", side_effect=_fake_qdm_ho):
        with pytest.raises(HoldoutLockError):
            harvester_ho.harvest_symbol("EURGBP", mt5_lock_held=False)

    # D) Cascade Case 3: All 3 tiers unavailable -> UNAVAILABLE_ALL_TIERS with waf_bypass_attempted == False
    res_none = harvester_t3.harvest_symbol("NZDUSD", mt5_lock_held=False)
    _check(res_none.status == "UNAVAILABLE_ALL_TIERS", f"Expected UNAVAILABLE_ALL_TIERS, got {res_none}")
    _check(res_none.waf_bypass_attempted is False, "Never fall back to WAF bypass")
    _check(all(a.waf_bypass_attempted is False for a in res_none.attempts), "All attempts must have waf_bypass=False")

    # E) Dry-Run CLI works cleanly without launching MT5 or QDM
    plan_out = tmp_path / "dry_run_plan.json"
    rc = harv.main(
        [
            "--dry-run",
            "--manifest",
            str(cache_dir / "manifest.json"),
            "--cache-dir",
            str(cache_dir),
            "--work-dir",
            str(work_dir),
            "--out",
            str(plan_out),
        ]
    )
    _check(rc == 0, f"CLI --dry-run failed rc={rc}")
    plan = json.loads(plan_out.read_text(encoding="utf-8"))
    _check(plan["missing_count"] == 16, f"Dry-run missing_count={plan['missing_count']}")
    _check(plan["waf_bypass_attempted"] is False, "Dry-run waf_bypass_attempted must be False")
    _check(plan["mt5_terminal_launched"] is False, "Dry-run must never launch MT5")
    _check(plan["order_send_count"] == 0 and plan["holdout_rows_analysed"] == 0, "Dry-run safety counters")
    _check(
        all(
            not sp["qdm_export_has_broker_arg"] and sp["qdm_export_dateto"] == "2024.12.31"
            for sp in plan["symbol_plans"]
        ),
        "Every dry-run QDM command must omit broker= and cap dateto=2024.12.31",
    )
