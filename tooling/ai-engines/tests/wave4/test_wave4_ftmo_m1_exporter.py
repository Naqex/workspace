"""Offline mocked + local_cache verification tests for Wave 4 FTMO-Demo M1 Exporter.

All checks avoid bare `assert` so EVERY check remains 100% enforced under `python -O -m pytest`!

CI (`-m "not local_cache"`) runs 100% offline with synthetic arrays and mocked MT5:
  - Lazy MetaTrader5 import check (no top-level MetaTrader5 import, zero order_send AST refs)
  - `[ARCH-02]` zero bare `assert` statements in `ftmo_m1_exporter.py` (safe under `python -O`)
  - Forbidden Exness/Program Files MT5 path fail-closed rejection
  - Demo-account / server / login / bool / trade_mode fail-closed guards
  - Empirical EU (`<= 2019`) vs US NY+7 (`>= 2020`) DST decoding across transition windows
  - Full synthetic 8-symbol mocked MT5 export -> NPZ `allow_pickle=False` -> manifest SHA-256 verification
  - Negative mutation tests:
      * Injecting a `2025-01-01T00:00:00Z` Holdout bar into mocked MT5 stream -> `HoldoutViolationError`
      * Injecting a `2025-01-01` bar into `validate_m1_arrays` -> `HoldoutViolationError` (safe under `-O`!)
      * Mutating a saved `.npz` to inject a `2025-01-01` bar -> post-export verifier fails closed
      * Poisoned `NaN`, `Inf`, `<= 0` price, OHLC inversion, non-monotonic timestamp, negative spread/volume

Local-cache test (`@pytest.mark.local_cache`):
  - Validates the real exported `.runtime/offensive4/m1/ftmo_dev_m1/manifest.json` + all 8 `PORT_7E`
    `.npz` files: SHA-256 integrity, `< 2025-01-01` seal, `holdout_rows_analysed == 0`, 0 NaN/Inf,
    strict monotonicity, and empirical alignment against Dukascopy UTC (`2022..2024`).
"""

from __future__ import annotations

import ast
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from quant_factory.wave4 import ftmo_m1_exporter as exp

_MT5_RATE_DTYPE = np.dtype(
    [
        ("time", "<i8"),
        ("open", "<f8"),
        ("high", "<f8"),
        ("low", "<f8"),
        ("close", "<f8"),
        ("tick_volume", "<i8"),
        ("spread", "<i4"),
        ("real_volume", "<i8"),
    ]
)


def _check(condition: bool, message: str) -> None:
    """Assertion helper immune to `python -O` bytecode stripping."""
    if not condition:
        raise AssertionError(message)


def _make_rates(
    server_timestamps: list[int],
    *,
    base_price: float = 150.0,
    spread: int = 8,
    volume: int = 42,
) -> np.ndarray:
    arr = np.zeros(len(server_timestamps), dtype=_MT5_RATE_DTYPE)
    for i, ts in enumerate(server_timestamps):
        px = base_price + 0.001 * i
        arr[i] = (ts, px, px + 0.02, px - 0.01, px + 0.005, volume, spread, 0)
    return arr


class FakeMT5:
    """Offline mock of MetaTrader5 (ZERO process launch, OrderSend = 0)."""

    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_CONTEST = 1
    ACCOUNT_TRADE_MODE_REAL = 2
    TIMEFRAME_M1 = 1

    def __init__(
        self,
        *,
        rates_by_symbol_year: dict[tuple[str, int], np.ndarray],
        login: int = 1515343166,
        server: str = "FTMO-Demo",
        trade_mode: int = 0,
        data_path: Path | None = None,
    ) -> None:
        self.rates_by_symbol_year = rates_by_symbol_year
        self.login = login
        self.server = server
        self.trade_mode = trade_mode
        self.data_path = data_path
        self.initialized = False
        self.shutdown_called = 0
        self.selected_symbols: list[str] = []

    def initialize(self, *, path: str, portable: bool = True, timeout: int = 30000) -> bool:
        self.initialized = True
        self.init_args = {"path": path, "portable": portable, "timeout": timeout}
        return True

    def shutdown(self) -> None:
        self.shutdown_called += 1
        self.initialized = False

    def last_error(self) -> tuple[int, str]:
        return (1, "Success")

    def account_info(self) -> Any:
        return SimpleNamespace(
            login=self.login,
            server=self.server,
            trade_mode=self.trade_mode,
            currency="USD",
            leverage=100,
            trade_allowed=False,
            trade_expert=False,
        )

    def terminal_info(self) -> Any:
        dp = str(self.data_path) if self.data_path is not None else ""
        return SimpleNamespace(
            path=dp,
            data_path=dp,
            build=6230,
            maxbars=100_000_000,
            connected=True,
            trade_allowed=False,
        )

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        self.selected_symbols.append(symbol)
        return True

    def symbol_info(self, symbol: str) -> Any:
        spec = exp.DEFAULT_SYMBOL_SPECS.get(symbol, {"digits": 5, "point": 1e-5})
        return SimpleNamespace(digits=spec["digits"], point=spec["point"])

    def copy_rates_range(self, symbol: str, timeframe: int, dt_from: datetime, dt_to: datetime) -> np.ndarray | None:
        if timeframe != self.TIMEFRAME_M1:
            return None
        return self.rates_by_symbol_year.get((symbol, dt_from.year))


def test_static_safety_lazy_mt5_import_and_zero_bare_asserts() -> None:
    """Verify `[ARCH-02]` zero bare asserts, lazy MetaTrader5 import, and zero order_send."""
    src_path = Path(exp.__file__).resolve()
    raw_bytes = src_path.read_bytes()
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "BOM detected in ftmo_m1_exporter.py")
    _check(b"\r\n" not in raw_bytes, "CRLF line endings detected in ftmo_m1_exporter.py")

    tree = ast.parse(raw_bytes.decode("utf-8"), filename=str(src_path))
    bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(not bare_asserts, f"Bare assert statement(s) forbidden under [ARCH-02]: lines {bare_asserts}")

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(alias.name != "MetaTrader5", "Top-level MetaTrader5 import forbidden (must be lazy)")
        elif isinstance(node, ast.ImportFrom):
            _check(node.module != "MetaTrader5", "Top-level MetaTrader5 from-import forbidden (must be lazy)")

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            _check(node.attr != "order_send", "order_send is strictly forbidden in read-only exporter")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run":
            kw_names = {kw.arg for kw in node.keywords}
            _check("creationflags" in kw_names, f"subprocess.run at line {node.lineno} missing creationflags")

    _check(exp.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be False")
    _check(exp.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be 0")
    _check("MetaTrader5" not in sys.modules, "Importing ftmo_m1_exporter must NOT eagerly import MetaTrader5")


def test_forbidden_paths_and_account_safety_locks() -> None:
    """Reject Exness Real paths, non-DEMO accounts, wrong servers, wrong logins, and bool spoofing."""
    for bad_path in (
        r"C:\Program Files\MetaTrader 5",
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"D:\some\path\D0E8209F77C8CF37AD8BF550E51FF075\terminal64.exe",
    ):
        with pytest.raises(exp.SafetyLockError):
            exp.assert_safe_portable_root(bad_path)

    safe = exp.assert_safe_portable_root(exp.DEFAULT_PORTABLE_ROOT)
    _check(safe.name == "ftmo-demo-portable-1515343166", f"unexpected portable root name: {safe.name}")

    with pytest.raises(exp.SafetyLockError):
        exp.validate_demo_account(SimpleNamespace(login=1515343166, server="FTMO-Demo", trade_mode=2))
    with pytest.raises(exp.SafetyLockError):
        exp.validate_demo_account(SimpleNamespace(login=1515343166, server="FTMO-Demo", trade_mode=False))
    with pytest.raises(exp.SafetyLockError):
        exp.validate_demo_account(SimpleNamespace(login=1515343166, server="Exness-MT5Real", trade_mode=0))
    with pytest.raises(exp.SafetyLockError):
        exp.validate_demo_account(SimpleNamespace(login=999999999, server="FTMO-Demo", trade_mode=0))
    with pytest.raises(exp.SafetyLockError):
        exp.assert_zero_mt5_processes(lambda: ['"terminal64.exe","1234"'], context="test")

    ini_txt = exp.render_readonly_export_ini()
    for token in ("KeepPrivate=1", "Enabled=0", "AllowLiveTrading=0", "AllowDllImport=0", "MaxBars=100000000"):
        _check(token in ini_txt, f"Missing safety token {token!r} in readonly export INI")


def test_empirical_ftmo_dst_decoder_eu_vs_us_regimes() -> None:
    """Verify <=2019 EU DST (+2 in mid-Mar/late-Oct) vs >=2020 US DST NY+7 (+3 in mid-Mar/late-Oct)."""
    cases = [
        ("2018-03-14T12:00:00Z", 2),
        ("2018-07-10T12:00:00Z", 3),
        ("2018-10-31T12:00:00Z", 2),
        ("2019-03-13T12:00:00Z", 2),
        ("2019-10-30T12:00:00Z", 2),
        ("2020-03-11T12:00:00Z", 3),
        ("2020-10-28T12:00:00Z", 3),
        ("2024-01-10T12:00:00Z", 2),
        ("2024-03-13T12:00:00Z", 3),
        ("2024-07-10T12:00:00Z", 3),
        ("2024-10-29T12:00:00Z", 3),
        ("2024-11-06T12:00:00Z", 2),
        ("2024-12-31T23:54:00Z", 2),
    ]
    raw_ts = np.array([int(datetime.fromisoformat(s).timestamp()) for s, _ in cases], dtype=np.int64)
    decoded = exp.decode_ftmo_server_times_to_utc(raw_ts)
    for idx, (_iso, exp_off) in enumerate(cases):
        actual_off = int(raw_ts[idx] - decoded[idx]) // 3600
        _check(actual_off == exp_off, f"Mismatch at {cases[idx]}: got UTC+{actual_off}")


def test_mocked_8sym_export_manifest_and_loader(tmp_path: Path) -> None:
    """Full offline 8-symbol mocked MT5 export -> zero-pickle NPZ -> SHA-256 manifest verification."""
    portable_dir = tmp_path / "ftmo-demo-portable-1515343166"
    portable_dir.mkdir(parents=True)
    out_dir = tmp_path / "ftmo_dev_m1"

    rates_map: dict[tuple[str, int], np.ndarray] = {}
    for s_idx, sym in enumerate(exp.PORT_7E_SYMBOLS):
        base = 150.0 if "JPY" in sym else (20000.0 if "US100" in sym else (5800.0 if "US500" in sym else 1.10))
        for yr in (2022, 2023, 2024):
            t0 = int(datetime(yr, 1, 3, 10, 0, tzinfo=UTC).timestamp())
            t_end = int(datetime(yr, 12, 31, 23, 50, tzinfo=UTC).timestamp())
            ts_list = [t0, t0 + 60, t0 + 120, t_end]
            rates_map[(sym, yr)] = _make_rates(ts_list, base_price=base + 0.01 * s_idx, spread=8 + s_idx)

    fake_mt5 = FakeMT5(rates_by_symbol_year=rates_map, login=1515343166, data_path=portable_dir)
    manifest = exp.export_ftmo_m1_suite(
        portable_root=portable_dir,
        out_dir=out_dir,
        symbols=exp.PORT_7E_SYMBOLS,
        start_year=2022,
        end_year=2024,
        mt5_mod=fake_mt5,
        process_lister=lambda: [],
    )

    _check(fake_mt5.shutdown_called == 1, "mt5.shutdown() must be called exactly once")
    _check(manifest["symbol_count"] == 8, f"expected 8 symbols, got {manifest['symbol_count']}")
    _check(manifest["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(manifest["source_provenance"] == "FTMO_BID_PLUS_SPREAD", "wrong source_provenance")
    _check(manifest["broker_tz"] == "EET_EEST", "wrong broker_tz")
    _check(manifest["mt5_processes_after_export"] == 0, "mt5_processes_after_export must be 0")
    _check(manifest["total_rows"] == 8 * 3 * 4, f"unexpected total_rows: {manifest['total_rows']}")
    _check(manifest["intersection"]["common_covered_years"] == [2022, 2023, 2024], "wrong common years")

    us100 = exp.load_exported_m1("US100", out_dir=out_dir, verify_sha=True)
    _check(us100["symbol"] == "US100.cash", f"alias resolution failed: {us100['symbol']}")
    _check(us100["ts_utc"].shape == (12,), f"unexpected shape: {us100['ts_utc'].shape}")
    expected_last = int(datetime(2024, 12, 31, 21, 50, tzinfo=UTC).timestamp())
    _check(int(us100["ts_utc"][-1]) == expected_last, "last decoded UTC bar mismatch")
    _check(int(us100["ts_utc"][-1]) < exp.HOLDOUT_CUTOFF_UTC_TS, "holdout cutoff breached")


def test_negative_mutation_holdout_2025_bar_fails_closed(tmp_path: Path) -> None:
    """Negative mutation: injecting a `2025-01-01` bar fails closed under both `python` and `python -O`."""
    with pytest.raises(exp.HoldoutViolationError):
        exp.assert_pre_holdout_date_window(2022, 2025)

    t_2024 = int(datetime(2024, 12, 31, 21, 59, tzinfo=UTC).timestamp())
    t_2025 = int(datetime(2025, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    with pytest.raises(exp.HoldoutViolationError):
        exp.validate_m1_arrays(
            symbol="USDJPY",
            ts_utc=np.array([t_2024, t_2025], dtype=np.int64),
            open_px=np.array([157.0, 157.1], dtype=np.float64),
            high_px=np.array([157.2, 157.3], dtype=np.float64),
            low_px=np.array([156.9, 157.0], dtype=np.float64),
            close_px=np.array([157.1, 157.2], dtype=np.float64),
            spread_pts=np.array([10, 10], dtype=np.int32),
            tick_volume=np.array([50, 50], dtype=np.int64),
        )

    # Server wall clock 2025-01-01T02:00:00Z (at UTC+2) decodes to 2025-01-01T00:00:00Z UTC -> MUST fail closed!
    srv_2024 = int(datetime(2024, 12, 31, 23, 54, tzinfo=UTC).timestamp())
    srv_2025_holdout = int(datetime(2025, 1, 1, 2, 0, tzinfo=UTC).timestamp())
    bad_mt5 = FakeMT5(
        rates_by_symbol_year={("USDJPY", 2024): _make_rates([srv_2024, srv_2025_holdout], base_price=157.0)},
        login=1515343166,
    )
    with pytest.raises(exp.HoldoutViolationError):
        exp.export_ftmo_m1_suite(
            portable_root=tmp_path / "ftmo-demo-portable-1515343166",
            out_dir=tmp_path / "out_bad",
            symbols=("USDJPY",),
            start_year=2024,
            end_year=2024,
            mt5_mod=bad_mt5,
            process_lister=lambda: [],
        )
    _check(bad_mt5.shutdown_called == 1, "mt5.shutdown() must run even after HoldoutViolationError")

    # Mutate an exported NPZ on disk to inject a 2025-01-01 bar -> post-export verifier MUST fail closed!
    good_dir = tmp_path / "out_tamper"
    good_mt5 = FakeMT5(
        rates_by_symbol_year={("USDJPY", 2024): _make_rates([srv_2024 - 60, srv_2024], base_price=157.0)},
        login=1515343166,
    )
    exp.export_ftmo_m1_suite(
        portable_root=tmp_path / "ftmo-demo-portable-1515343166",
        out_dir=good_dir,
        symbols=("USDJPY",),
        start_year=2024,
        end_year=2024,
        mt5_mod=good_mt5,
        process_lister=lambda: [],
    )
    npz_path = good_dir / "USDJPY.npz"
    with np.load(npz_path, allow_pickle=False) as z:
        mut = {k: z[k].copy() for k in z.files}
    mut["ts_utc"] = np.array([t_2024, t_2025], dtype=np.int64)
    mut["max_ts_utc"] = np.asarray(t_2025, dtype=np.int64)
    np.savez(npz_path, **mut)
    with pytest.raises(exp.HoldoutViolationError):
        exp.verify_exported_npz(npz_path, expected_symbol="USDJPY", expected_sha256=None)


def test_negative_ohlc_nan_nonpositive_and_monotonicity_guards() -> None:
    """Fail-closed validation on NaN/Inf, <=0 price, OHLC inversion, non-monotonic ts, and negative spread."""
    ts = np.array([1_704_200_000, 1_704_200_060], dtype=np.int64)
    base: dict[str, Any] = {
        "symbol": "EURUSD",
        "ts_utc": ts,
        "open_px": np.array([1.1000, 1.1010], dtype=np.float64),
        "high_px": np.array([1.1020, 1.1030], dtype=np.float64),
        "low_px": np.array([1.0990, 1.1000], dtype=np.float64),
        "close_px": np.array([1.1010, 1.1020], dtype=np.float64),
        "spread_pts": np.array([5, 6], dtype=np.int32),
        "tick_volume": np.array([10, 20], dtype=np.int64),
    }
    ok = exp.validate_m1_arrays(**base)
    _check(ok["row_count"] == 2 and ok["holdout_rows_analysed"] == 0, "clean series failed validation")

    mutations = (
        {"close_px": np.array([1.1010, np.nan], dtype=np.float64)},
        {"high_px": np.array([np.inf, 1.1030], dtype=np.float64)},
        {"low_px": np.array([0.0, 1.1000], dtype=np.float64)},
        {"high_px": np.array([1.1005, 1.1030], dtype=np.float64)},
        {"low_px": np.array([1.1005, 1.1000], dtype=np.float64)},
        {"ts_utc": np.array([1_704_200_060, 1_704_200_060], dtype=np.int64)},
        {"spread_pts": np.array([-1, 6], dtype=np.int32)},
        {"tick_volume": np.array([-5, 20], dtype=np.int64)},
    )
    for mut in mutations:
        with pytest.raises(exp.M1ValidationError):
            exp.validate_m1_arrays(**{**base, **mut})


@pytest.mark.local_cache
def test_local_cache_exported_ftmo_m1_manifest_and_holdout_seal() -> None:
    """Validate the real exported `.runtime/offensive4/m1/ftmo_dev_m1/manifest.json` + all 8 PORT_7E NPZs."""
    out_dir = exp.DEFAULT_OUT_DIR
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.is_file():
        pytest.skip(f"Local FTMO Dev M1 export not present at {manifest_path}")

    manifest = exp.verify_exported_manifest(out_dir, verify_sha=True)
    _check(manifest["symbol_count"] == 8, f"expected 8 symbols, got {manifest['symbol_count']}")
    _check(tuple(manifest["symbols"].keys()) == exp.PORT_7E_SYMBOLS, "symbol order/set mismatch vs PORT_7E_SYMBOLS")
    _check(manifest["holdout_rows_analysed"] == 0, "manifest holdout_rows_analysed != 0")
    _check(manifest["source_provenance"] == "FTMO_BID_PLUS_SPREAD", "manifest provenance mismatch")
    _check(manifest["broker_tz"] == "EET_EEST", "manifest broker_tz mismatch")
    _check(manifest["mt5_processes_after_export"] == 0, "mt5_processes_after_export != 0")
    _check(manifest["order_send_count"] == 0, "order_send_count != 0")

    for sym in exp.PORT_7E_SYMBOLS:
        entry = manifest["symbols"][sym]
        _check(entry["row_count"] >= 1_000_000, f"{sym} row_count unexpectedly small: {entry['row_count']}")
        _check(entry["max_ts_utc"] < exp.HOLDOUT_CUTOFF_UTC_TS, f"{sym} breached Holdout cutoff")
        _check(entry["max_ts_utc"] <= exp.MAX_ALLOWED_DEV_BAR_TS_UTC, f"{sym} exceeded 2024-12-31T23:59:00Z")
        _check(entry["holdout_rows_analysed"] == 0, f"{sym} holdout_rows_analysed != 0")
        for yr in (2022, 2023, 2024):
            _check(yr in entry["covered_years"], f"{sym} missing canonical intersection year {yr}")
            _check(int(entry["year_row_counts"].get(str(yr), 0)) >= 250_000, f"{sym} sparse year {yr}")

    receipt_path = exp.REPO_ROOT / ".runtime/offensive4/audits/w4_t0_ftmo_m1_receipt.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        _check(receipt["holdout_rows_analysed"] == 0, "receipt holdout_rows_analysed != 0")
        _check(receipt["mt5_processes_after_export"] == 0, "receipt mt5_processes_after_export != 0")
        _check(receipt["order_send_count"] == 0, "receipt order_send_count != 0")
