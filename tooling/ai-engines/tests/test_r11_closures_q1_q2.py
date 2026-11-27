"""Astra Round-11 Q1 & Q2 Closure Tests (Front 1 Defense — Lane D1).

Covers:
  - Offline-safe unit tests (ZERO `private_vault` import required) for `nfp_cpi_quote_collector.py`:
      * Zero bare `assert` statements (AST verified) and strict enforcement under `python -O`.
      * `same_ms_order_unrecoverable_count` & `same_ms_order_unrecoverable_events` preservation.
      * Mandatory `--expected-login` / `--expected-server` validation (fail-closed before MT5 init).
      * Strict `terminal_info.trade_allowed == False` enforcement (including missing attribute).
      * Full 3-phase completeness (`PRE_EVENT`, `IMPACT_CORE`, `POST_NORMALIZE`) + `>= 300s` span gate.
  - `@pytest.mark.local_cache` + `skipif` tests for `step7_1_l0_lot_divergence_audit.py`:
      * Zero bare `assert` statements (AST verified) and strict enforcement under `python -O`.
      * `reconstruct_intraday_equity_dd_curve()` on synthetic fixtures (hidden intraday DD `< 5%`,
        inter-snapshot breach `>= 5%`, Prague midnight rollover, Holdout `2025+` fail-closed lock).
      * `reconstruct_intraday_equity_dd_curve()` on real `2024-09..2024-12` M1 Bid/Ask cache proving
        true continuous worst intraday DD `< 5.0%` (`holdout_rows_analysed = 0`).
"""

from __future__ import annotations

import ast
import csv
import importlib.util
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
OPS_CLOUD = ROOT / "tooling/ai-engines/ops_cloud"
if str(OPS_CLOUD) not in sys.path:
    sys.path.insert(0, str(OPS_CLOUD))

import nfp_cpi_quote_collector as qc  # noqa: E402

COLLECTOR_SCRIPT = OPS_CLOUD / "nfp_cpi_quote_collector.py"
STEP7_1_SCRIPT = (
    ROOT
    / "private_vault/strategies/step7-astra-r10-closures-20261126/step7_1_l0_lot_divergence_audit.py"
)
STEP6_RAW_DIR = (
    ROOT
    / "private_vault/strategies/step6-c10-news-on-and-demo-ro-20261126/raw_mt5_logs"
)
M1_CACHE_DIR = ROOT / ".runtime/hot-m1-cache"


def _load_step7_1_module() -> Any:
    spec = importlib.util.spec_from_file_location("step7_1_l0_lot_divergence_audit_r11", STEP7_1_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {STEP7_1_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _OfflineFakeMT5:
    """Offline mock of MetaTrader5 (ZERO MT5 process launch, OrderSend = 0)."""

    COPY_TICKS_ALL = 0

    def __init__(
        self,
        *,
        login: int = 990001,
        server: str = "FTMO-Demo",
        connected: bool = True,
        trade_allowed: bool | None = False,
        positions_total: Any = 0,
        orders_total: Any = 0,
        symbols: tuple[str, ...] = qc.ALL8_SYMBOLS,
        initial_ticks: dict[str, dict[str, Any]] | None = None,
        snapshot_ticks_seq: dict[str, list[dict[str, Any]]] | None = None,
        poll_batches: dict[str, list[list[dict[str, Any]]]] | None = None,
    ) -> None:
        self._login = login
        self._server = server
        self._connected = connected
        self._trade_allowed = trade_allowed
        self._positions_total = positions_total
        self._orders_total = orders_total
        self._symbols = set(symbols)
        self._initial_ticks = initial_ticks or {}
        self._snapshot_seq = {k: list(v) for k, v in (snapshot_ticks_seq or {}).items()}
        self._snap_idx: dict[str, int] = {s: 0 for s in symbols}
        self._poll_batches = {k: list(v) for k, v in (poll_batches or {}).items()}
        self._poll_idx: dict[str, int] = {s: 0 for s in symbols}
        self.initialized = False
        self.shutdown_called = False

    def initialize(self, path: str, portable: bool = True) -> bool:
        self.initialized = True
        return True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def terminal_info(self) -> Any:
        if self._trade_allowed is None:
            return SimpleNamespace(connected=self._connected)
        return SimpleNamespace(connected=self._connected, trade_allowed=self._trade_allowed)

    def account_info(self) -> Any:
        return SimpleNamespace(login=self._login, server=self._server)

    def positions_total(self) -> Any:
        return self._positions_total

    def orders_total(self) -> Any:
        return self._orders_total

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        return symbol in self._symbols

    def symbol_info(self, symbol: str) -> Any:
        if symbol not in self._symbols:
            return None
        pt = 0.01 if ("cash" in symbol or "JPY" in symbol) else 0.00001
        return SimpleNamespace(point=pt)

    def symbol_info_tick(self, symbol: str) -> Any:
        seq = self._snapshot_seq.get(symbol)
        if seq:
            idx = self._snap_idx.get(symbol, 0)
            tk = seq[min(idx, len(seq) - 1)]
            self._snap_idx[symbol] = idx + 1
            return SimpleNamespace(**tk)
        tk = self._initial_ticks.get(symbol)
        return SimpleNamespace(**tk) if tk is not None else None

    def copy_ticks_range(self, symbol: str, from_dt: Any, to_dt: Any, flags: int) -> list[dict[str, Any]]:
        batches = self._poll_batches.get(symbol, [])
        if not batches:
            return []
        idx = self._poll_idx.get(symbol, 0)
        batch = batches[min(idx, len(batches) - 1)]
        self._poll_idx[symbol] = idx + 1
        from_msc = int(round(from_dt.timestamp() * 1000))
        return [t for t in batch if int(t["time_msc"]) >= from_msc]


def _write_valid_calendar(path: Path) -> Path:
    path.write_text(
        "utc_ts,ccy,event\n"
        "1796391000,USD,US_NFP\n"
        "1796909400,USD,US_CPI\n",
        encoding="utf-8",
    )
    return path


def _make_base_ticks(release_utc_ts: int, srv_off_ms: int, offset_sec: int = 1) -> dict[str, dict[str, Any]]:
    tm = (release_utc_ts + offset_sec) * 1000 + srv_off_ms
    out: dict[str, dict[str, Any]] = {}
    for sym in qc.ALL8_SYMBOLS:
        bid = 21000.0 if "cash" in sym else (150.0 if "JPY" in sym else 1.10000)
        spr = 1.5 if "cash" in sym else (0.02 if "JPY" in sym else 0.00010)
        out[sym] = {"time_msc": tm, "bid": bid, "ask": bid + spr, "flags": 6}
    return out


def _write_sample_csv(path: Path, *, record_tier: str = qc.RECORD_TIER, order_send_count: int = 0) -> Path:
    rel_ts = qc.EVENTS["US_NFP_20261204"]["release_utc_ts"]
    srv_off_ms = 2 * 3600 * 1000
    row = qc.build_tick_row(
        event_id="US_NFP_20261204",
        release_utc_ts=rel_ts,
        server_tick_msc=(rel_ts + 1) * 1000 + srv_off_ms,
        server_minus_utc_ms=srv_off_ms,
        local_recv_msc=(rel_ts + 1) * 1000 + 25,
        ntp_offset_ms=-5.0,
        account_alias="DEMO_SECONDARY",
        server="FTMO-Demo",
        symbol="US100.cash",
        bid=21000.0,
        ask=21001.5,
        point=0.01,
        tick_flags=6,
        prev_tick=None,
    )
    row["record_tier"] = record_tier
    row["order_send_count"] = order_send_count
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(qc.CSV_COLUMNS))
        writer.writeheader()
        writer.writerow(row)
    return path


# ===========================================================================
# Part 1: Offline-safe R11 Q2 tests (`nfp_cpi_quote_collector.py`, NO private_vault)
# ===========================================================================


def test_nfp_collector_zero_bare_asserts_ast_and_zero_order_send() -> None:
    src = COLLECTOR_SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert_lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert assert_lines == [], f"Bare assert(s) found in nfp_cpi_quote_collector.py at lines {assert_lines}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"order_send", "order_check"}
        if isinstance(node, ast.Name):
            assert node.id not in {"order_send", "order_check"}


def test_nfp_collector_summarize_guards_enforced_under_python_dash_O(tmp_path: Path) -> None:
    bad_tier_csv = _write_sample_csv(tmp_path / "bad_tier.csv", record_tier="FILL_GROUND_TRUTH", order_send_count=0)
    bad_orders_csv = _write_sample_csv(tmp_path / "bad_orders.csv", record_tier=qc.RECORD_TIER, order_send_count=1)

    with pytest.raises(RuntimeError, match="INVALID_RECORD_TIER"):
        qc.summarize_captured_csv(bad_tier_csv)
    with pytest.raises(RuntimeError, match="NONZERO_ORDER_SEND_COUNT"):
        qc.summarize_captured_csv(bad_orders_csv)

    # Explicitly execute in a `python -O` child process so enforcement is proven even under normal pytest!
    probe_lines = [
        "import sys",
        "from pathlib import Path",
        "if __debug__:",
        "    raise SystemExit('EXPECTED_DASH_O_MODE')",
        f"sys.path.insert(0, {str(OPS_CLOUD)!r})",
        "import nfp_cpi_quote_collector as qc",
        "cases = [",
        f"    ({str(bad_tier_csv)!r}, 'INVALID_RECORD_TIER'),",
        f"    ({str(bad_orders_csv)!r}, 'NONZERO_ORDER_SEND_COUNT'),",
        "]",
        "results = []",
        "for path_s, tag in cases:",
        "    try:",
        "        qc.summarize_captured_csv(Path(path_s))",
        "        raise SystemExit(f'FAILED_TO_RAISE:{tag}')",
        "    except RuntimeError as exc:",
        "        if tag not in str(exc):",
        "            raise SystemExit(f'WRONG_ERROR:{tag}:{exc}')",
        "        results.append(tag)",
        "print(','.join(results))",
    ]
    proc = subprocess.run(
        [sys.executable, "-O", "-c", "\n".join(probe_lines)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"python -O probe failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.stdout.strip() == "INVALID_RECORD_TIER,NONZERO_ORDER_SEND_COUNT"


def test_nfp_collector_same_ms_order_unrecoverable_in_cursor_and_live_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    rel_ts = qc.EVENTS["US_NFP_20261204"]["release_utc_ts"]
    srv_off_ms = 2 * 3600 * 1000
    t_ms = (rel_ts + 10) * 1000 + srv_off_ms

    tk_a = {"time_msc": t_ms, "bid": 21000.0, "ask": 21001.0, "flags": 6}
    tk_b = {"time_msc": t_ms, "bid": 21006.0, "ask": 21007.5, "flags": 6}
    tk_c = {"time_msc": t_ms, "bid": 21011.0, "ask": 21013.0, "flags": 6}

    # Direct cursor test: [B] snapshot -> [A, B, C] range preserves A & C and records audit event
    cur = qc.SameMsTickCursor(t_ms - 500)
    assert cur.consume_snapshot(tk_b) == [(t_ms, 21006.0, 21007.5, 6)]
    with caplog.at_level("WARNING", logger=qc.__name__):
        out = cur.consume_batch([tk_a, tk_b, tk_c])
    assert out == [(t_ms, 21000.0, 21001.0, 6), (t_ms, 21011.0, 21013.0, 6)]
    assert cur.same_ms_order_unrecoverable_count == 1
    assert len(cur.same_ms_order_unrecoverable_events) == 1
    evt = cur.same_ms_order_unrecoverable_events[0]
    assert evt["time_msc"] == t_ms
    assert evt["had_snapshot_fallback"] is True
    assert evt["late_emitted_prior_count"] == 1
    assert any("SAME_MS_ORDER_UNRECOVERABLE" in r.message for r in caplog.records)

    # End-to-end live capture report propagation of same_ms_order_unrecoverable_*
    base_init = _make_base_ticks(rel_ts, srv_off_ms, offset_sec=5)
    snap_seq = {sym: [base_init[sym], base_init[sym], base_init[sym]] for sym in qc.ALL8_SYMBOLS}
    snap_seq["US100.cash"] = [base_init["US100.cash"], base_init["US100.cash"], tk_b, tk_b]
    poll_batches: dict[str, list[list[dict[str, Any]]]] = {
        sym: [[base_init[sym]], [base_init[sym]]] for sym in qc.ALL8_SYMBOLS
    }
    poll_batches["US100.cash"] = [[], [tk_a, tk_b]]

    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 4.5})
    clock_vals = iter([
        float(rel_ts + 10),
        float(rel_ts + 10),
        float(rel_ts + 10.1),
        float(rel_ts + 10.2),
        float(rel_ts + 10.3),
        float(rel_ts + 12.0),
    ])
    monkeypatch.setattr(qc.time, "time", lambda: next(clock_vals, float(rel_ts + 15.0)))
    monkeypatch.setattr(qc.time, "sleep", lambda _s: None)

    fake_mt5 = _OfflineFakeMT5(initial_ticks=base_init, snapshot_ticks_seq=snap_seq, poll_batches=poll_batches)
    rep = qc.run_live_capture(
        terminal_exe=tmp_path / "terminal64.exe",
        event_id="SMOKE_PREFLIGHT",
        out_csv=tmp_path / "smoke_unrec.csv",
        duration_sec=1.0,
        red_news_csv=cal,
        expected_login=990001,
        expected_server="FTMO-Demo",
        mt5_module=fake_mt5,
        poll_sleep_sec=0.0,
        connect_wait_attempts=1,
        connect_wait_sleep_s=0.0,
    )
    assert rep["same_ms_order_unrecoverable_count"] == 1
    assert len(rep["same_ms_order_unrecoverable_events"]) == 1
    assert rep["same_ms_order_unrecoverable_events"][0]["symbol"] == "US100.cash"
    assert rep["order_send_count"] == 0


@pytest.mark.parametrize(
    ("expected_login", "expected_server", "err_match"),
    [
        (None, "FTMO-Demo", "PREFLIGHT_ABORT_EXPECTED_LOGIN_REQUIRED"),
        (False, "FTMO-Demo", "PREFLIGHT_ABORT_EXPECTED_LOGIN_REQUIRED"),
        (-10, "FTMO-Demo", "PREFLIGHT_ABORT_EXPECTED_LOGIN_REQUIRED"),
        (990001, None, "PREFLIGHT_ABORT_EXPECTED_SERVER_REQUIRED"),
        (990001, "", "PREFLIGHT_ABORT_EXPECTED_SERVER_REQUIRED"),
        (990001, "   ", "PREFLIGHT_ABORT_EXPECTED_SERVER_REQUIRED"),
    ],
)
def test_nfp_collector_required_login_and_server_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expected_login: Any,
    expected_server: Any,
    err_match: str,
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 1.0})
    fake_mt5 = _OfflineFakeMT5()
    with pytest.raises(RuntimeError, match=err_match):
        qc.run_live_capture(
            terminal_exe=tmp_path / "terminal64.exe",
            event_id="SMOKE_PREFLIGHT",
            out_csv=tmp_path / "out.csv",
            red_news_csv=cal,
            expected_login=expected_login,
            expected_server=expected_server,
            mt5_module=fake_mt5,
        )
    assert fake_mt5.initialized is False


@pytest.mark.parametrize("trade_allowed_val", [True, None])
def test_nfp_collector_trade_allowed_must_be_strictly_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trade_allowed_val: bool | None
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 2.0})
    fake_mt5 = _OfflineFakeMT5(trade_allowed=trade_allowed_val)
    with pytest.raises(RuntimeError, match="PREFLIGHT_ABORT_TRADE_ALLOWED"):
        qc.run_live_capture(
            terminal_exe=tmp_path / "terminal64.exe",
            event_id="SMOKE_PREFLIGHT",
            out_csv=tmp_path / "out.csv",
            red_news_csv=cal,
            expected_login=990001,
            expected_server="FTMO-Demo",
            mt5_module=fake_mt5,
            connect_wait_attempts=1,
            connect_wait_sleep_s=0.0,
        )
    assert fake_mt5.shutdown_called is True


def test_nfp_collector_three_phase_completeness_and_span_enforcement() -> None:
    def _mk_summary(
        *,
        window_span: float = 480.0,
        core4_span: float = 480.0,
        pre: int = 5,
        imp: int = 10,
        post: int = 5,
        drop_phase_sym: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        syms: dict[str, Any] = {}
        for s in qc.ALL8_SYMBOLS:
            pc = {"PRE_EVENT": pre, "IMPACT_CORE": imp, "POST_NORMALIZE": post}
            if drop_phase_sym is not None and s == drop_phase_sym[0]:
                pc[drop_phase_sym[1]] = 0
            syms[s] = {
                "tick_count": sum(pc.values()),
                "elapsed_span_sec": core4_span if s in qc.CORE4_SYMBOLS else window_span,
                "phase_counts": pc,
            }
        return {
            "total_rows": sum(v["tick_count"] for v in syms.values()),
            "window_elapsed_span_sec": window_span,
            "symbols": syms,
        }

    ok = qc.evaluate_window_completeness(_mk_summary(), event_id="US_NFP_20261204")
    assert ok["window_complete"] is True
    assert ok["status"] == "COMPLETE"
    assert ok["requires_all_three_phases"] is True

    miss_pre = qc.evaluate_window_completeness(
        _mk_summary(drop_phase_sym=("USDJPY", "PRE_EVENT")), event_id="US_NFP_20261204"
    )
    assert miss_pre["window_complete"] is False
    assert miss_pre["missing_pre_event_symbols"] == ["USDJPY"]

    miss_imp = qc.evaluate_window_completeness(
        _mk_summary(drop_phase_sym=("US100.cash", "IMPACT_CORE")), event_id="US_CPI_20261210"
    )
    assert miss_imp["window_complete"] is False
    assert miss_imp["missing_impact_core_symbols"] == ["US100.cash"]

    miss_post = qc.evaluate_window_completeness(
        _mk_summary(drop_phase_sym=("EURJPY", "POST_NORMALIZE")), event_id="US_CPI_20261210"
    )
    assert miss_post["window_complete"] is False
    assert miss_post["missing_post_normalize_symbols"] == ["EURJPY"]

    short_win = qc.evaluate_window_completeness(
        _mk_summary(window_span=120.0, core4_span=120.0), event_id="US_NFP_20261204"
    )
    assert short_win["window_complete"] is False
    assert any("INSUFFICIENT_WINDOW_ELAPSED_SPAN" in r for r in short_win["reasons"])
    assert set(short_win["short_span_core4_symbols"]) == set(qc.CORE4_SYMBOLS)

    smoke_ok = qc.evaluate_window_completeness(
        _mk_summary(window_span=2.0, core4_span=2.0, pre=0, imp=1, post=0), event_id="SMOKE_PREFLIGHT"
    )
    assert smoke_ok["window_complete"] is True
    assert smoke_ok["status"] == "COMPLETE"


# ===========================================================================
# Part 2: Step 7.1 R11 Q1 tests (`@pytest.mark.local_cache` + `skipif`)
# ===========================================================================


@pytest.mark.local_cache
@pytest.mark.skipif(
    not STEP7_1_SCRIPT.exists(),
    reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout",
)
def test_step7_1_zero_bare_asserts_ast_and_dash_O_enforcement() -> None:
    src = STEP7_1_SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert_lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert assert_lines == [], f"Bare assert(s) found in step7_1_l0_lot_divergence_audit.py at lines {assert_lines}"

    # Verify -O runtime enforcement in a child `python -O` interpreter:
    #   (1) run_audit rejects tampered holdout lock SHA under -O
    #   (2) reconstruct_intraday_equity_dd_curve rejects 2025-01-01 holdout data under -O
    probe_lines = [
        "import importlib.util",
        "from pathlib import Path",
        "if __debug__:",
        "    raise SystemExit('EXPECTED_DASH_O_MODE')",
        f"spec = importlib.util.spec_from_file_location('s71_o', Path({str(STEP7_1_SCRIPT)!r}))",
        "mod = importlib.util.module_from_spec(spec)",
        "spec.loader.exec_module(mod)",
        "mod.assert_holdout_locked = lambda: '0000000000000000tampered'",
        "checks = []",
        "try:",
        "    mod.run_audit(max_workers=1)",
        "    raise SystemExit('FAILED_LOCK_SHA_GUARD')",
        "except RuntimeError as exc:",
        "    if 'Unexpected holdout lock SHA' not in str(exc):",
        "        raise SystemExit(f'WRONG_LOCK_ERR:{exc}')",
        "    checks.append('LOCK_SHA_GUARD_OK')",
        "holdout_deal = {",
        "    'utc_ts': 1735689600,",
        "    'symbol': 'GBPUSD',",
        "    'direction': 'in',",
        "    'side': 'buy',",
        "    'volume': 0.1,",
        "    'price': 1.25,",
        "    'balance': 10000.0,",
        "}",
        "try:",
        "    mod.reconstruct_intraday_equity_dd_curve([holdout_deal], verify_holdout_lock=False)",
        "    raise SystemExit('FAILED_HOLDOUT_TS_GUARD')",
        "except ValueError as exc:",
        "    if 'HOLDOUT_LOCK_VIOLATION' not in str(exc):",
        "        raise SystemExit(f'WRONG_HOLDOUT_ERR:{exc}')",
        "    checks.append('HOLDOUT_TS_GUARD_OK')",
        "print(','.join(checks))",
    ]
    proc = subprocess.run(
        [sys.executable, "-O", "-c", "\n".join(probe_lines)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"python -O Step 7.1 probe failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.stdout.strip() == "LOCK_SHA_GUARD_OK,HOLDOUT_TS_GUARD_OK"


@pytest.mark.local_cache
@pytest.mark.skipif(
    not STEP7_1_SCRIPT.exists(),
    reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout",
)
def test_reconstruct_intraday_equity_dd_curve_synthetic_scenarios() -> None:
    s71 = _load_step7_1_module()

    # Base timestamp: 2024-10-15 10:00:00 UTC (strictly < 2025-01-01)
    t0 = int(datetime(2024, 10, 15, 10, 0, 0, tzinfo=UTC).timestamp())
    mins = np.array([t0 + 60 * i for i in range(40)], dtype=np.int64)

    # Scenario 1: Flat closed-deal DD = 0.0%, but hidden inter-snapshot M1 adverse dip = -3.80% (< 5.0% PASS!)
    bl = np.full(40, 1.30000, dtype=np.float64)
    bc = np.full(40, 1.30000, dtype=np.float64)
    bh = np.full(40, 1.30050, dtype=np.float64)
    al = np.full(40, 1.30010, dtype=np.float64)
    ac = np.full(40, 1.30010, dtype=np.float64)
    ah = np.full(40, 1.30060, dtype=np.float64)
    bl[15] = 1.29620  # -0.00380 * 100,000 * 1.0 lot = -$380.00 (-3.80% daily DD!)
    bc[15] = 1.29800  # close-of-M1 = -$200.00 (-2.00% daily DD)

    deals_pass = [
        {
            "utc_ts": t0,
            "symbol": "GBPUSD",
            "direction": "in",
            "side": "buy",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 10000.0,
        },
        {
            "utc_ts": t0 + 30 * 60,
            "symbol": "GBPUSD",
            "direction": "out",
            "side": "sell",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 10000.0,
        },
    ]
    res_pass = s71.reconstruct_intraday_equity_dd_curve(
        deals_pass,
        m1_bars={"GBPUSD": {"ts": mins, "bl": bl, "bc": bc, "bh": bh, "al": al, "ac": ac, "ah": ah}},
        start_balance_usd=10000.0,
        initial_balance_usd=10000.0,
        include_daily_series=True,
    )
    assert res_pass["holdout_rows_analysed"] == 0
    assert res_pass["order_send_count"] == 0
    assert res_pass["worst_intraday_daily_dd_adverse_pct"] == pytest.approx(3.8, abs=1e-4)
    assert res_pass["worst_intraday_daily_dd_close_pct"] == pytest.approx(2.0, abs=1e-4)
    assert res_pass["headroom_to_5pct_daily_adverse_pct"] == pytest.approx(1.2, abs=1e-4)
    assert res_pass["breached_5pct_daily_intraday"] is False
    assert res_pass["passes_daily_dd_limit"] is True
    assert res_pass["worst_intraday_daily_dd_point"]["utc_ts"] == int(mins[15])
    assert len(res_pass["daily_intraday_dd_series"]) == 1

    # Scenario 2: Hidden intraday breach >= 5.0% via concurrent SELL US100.cash + SELL EURJPY
    bl_u = np.full(40, 20000.0, dtype=np.float64)
    bc_u = np.full(40, 20000.0, dtype=np.float64)
    ac_u = np.full(40, 20001.0, dtype=np.float64)
    ah_u = np.full(40, 20001.0, dtype=np.float64)
    ah_u[20] = 20300.0  # SELL 1.0 US100.cash from 20000 -> -$300.00 adverse

    bl_ej = np.full(40, 160.0, dtype=np.float64)
    bc_ej = np.full(40, 160.0, dtype=np.float64)
    ac_ej = np.full(40, 160.02, dtype=np.float64)
    ah_ej = np.full(40, 160.02, dtype=np.float64)
    # SELL 1.0 EURJPY from 160.00 -> -36,000 JPY / 150.0 USDJPY_bl = -$240.00 (total -$540 = 5.40%!)
    ah_ej[20] = 160.36

    bl_uj = np.full(40, 150.0, dtype=np.float64)
    bc_uj = np.full(40, 150.5, dtype=np.float64)
    bh_uj = np.full(40, 151.0, dtype=np.float64)
    ac_uj = np.full(40, 150.52, dtype=np.float64)
    ah_uj = np.full(40, 151.02, dtype=np.float64)

    deals_breach = [
        {
            "utc_ts": t0,
            "symbol": "US100.cash",
            "direction": "in",
            "side": "sell",
            "volume": 1.0,
            "price": 20000.0,
            "balance": 10000.0,
        },
        {
            "utc_ts": t0,
            "symbol": "EURJPY",
            "direction": "in",
            "side": "sell",
            "volume": 1.0,
            "price": 160.00,
            "balance": 10000.0,
        },
        {
            "utc_ts": t0 + 30 * 60,
            "symbol": "US100.cash",
            "direction": "out",
            "side": "buy",
            "volume": 1.0,
            "price": 20000.0,
            "balance": 10000.0,
        },
        {
            "utc_ts": t0 + 30 * 60,
            "symbol": "EURJPY",
            "direction": "out",
            "side": "buy",
            "volume": 1.0,
            "price": 160.00,
            "balance": 10000.0,
        },
    ]
    res_breach = s71.reconstruct_intraday_equity_dd_curve(
        deals_breach,
        m1_bars={
            "US100.cash": {"ts": mins, "bl": bl_u, "bc": bc_u, "ac": ac_u, "ah": ah_u},
            "EURJPY": {"ts": mins, "bl": bl_ej, "bc": bc_ej, "ac": ac_ej, "ah": ah_ej},
            "USDJPY": {"ts": mins, "bl": bl_uj, "bc": bc_uj, "bh": bh_uj, "ac": ac_uj, "ah": ah_uj},
        },
        start_balance_usd=10000.0,
        initial_balance_usd=10000.0,
    )
    assert res_breach["worst_intraday_daily_dd_adverse_pct"] == pytest.approx(5.4, abs=1e-4)
    assert res_breach["breached_5pct_daily_intraday"] is True
    assert res_breach["passes_daily_dd_limit"] is False

    # Scenario 3: Prague midnight crossing resets daily anchor (CEST = UTC+2 -> midnight at 22:00 UTC)
    t_pre_mid = int(datetime(2024, 10, 15, 21, 55, 0, tzinfo=UTC).timestamp())
    mins_mid = np.array([t_pre_mid + 60 * i for i in range(15)], dtype=np.int64)
    bl_m = np.full(15, 1.30000, dtype=np.float64)
    bc_m = np.full(15, 1.30000, dtype=np.float64)
    ac_m = np.full(15, 1.30010, dtype=np.float64)
    ah_m = np.full(15, 1.30010, dtype=np.float64)
    # 22:05 UTC (next Prague day 2024-10-16): -$200 from reset anchor $9,800 -> 2.00% daily DD (4.00% static)
    bl_m[10] = 1.29800
    deals_mid = [
        {
            "utc_ts": t_pre_mid - 3600,
            "symbol": "GBPUSD",
            "direction": "in",
            "side": "buy",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 10000.0,
        },
        {
            "utc_ts": t_pre_mid - 1800,
            "symbol": "GBPUSD",
            "direction": "out",
            "side": "sell",
            "volume": 1.0,
            "price": 1.29800,
            "balance": 9800.0,
        },
        {
            "utc_ts": t_pre_mid,
            "symbol": "GBPUSD",
            "direction": "in",
            "side": "buy",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 9800.0,
        },
        {
            "utc_ts": t_pre_mid + 12 * 60,
            "symbol": "GBPUSD",
            "direction": "out",
            "side": "sell",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 9800.0,
        },
    ]
    res_mid = s71.reconstruct_intraday_equity_dd_curve(
        deals_mid,
        m1_bars={"GBPUSD": {"ts": mins_mid, "bl": bl_m, "bc": bc_m, "ac": ac_m, "ah": ah_m}},
        start_balance_usd=10000.0,
        initial_balance_usd=10000.0,
        include_daily_series=True,
    )
    assert res_mid["trading_days_evaluated"] == 2
    assert res_mid["worst_intraday_daily_dd_adverse_pct"] == pytest.approx(2.0, abs=1e-4)
    assert res_mid["worst_intraday_static_dd_adverse_pct"] == pytest.approx(4.0, abs=1e-4)

    # Scenario 4: Holdout 2025+ M1 bar rejected fail-closed
    holdout_ts = np.array([int(datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC).timestamp())], dtype=np.int64)
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        s71.reconstruct_intraday_equity_dd_curve(
            deals_pass,
            m1_bars={
                "GBPUSD": {
                    "ts": holdout_ts,
                    "bl": np.array([1.25]),
                    "bc": np.array([1.25]),
                    "ac": np.array([1.2501]),
                    "ah": np.array([1.2501]),
                }
            },
        )


@pytest.mark.local_cache
@pytest.mark.skipif(
    not (STEP7_1_SCRIPT.exists() and M1_CACHE_DIR.exists() and STEP6_RAW_DIR.exists()),
    reason="Local M1 Bid/Ask cache or Layer-2 Step 6/7.1 data absent in clean CI checkout",
)
def test_reconstruct_intraday_equity_dd_curve_real_m1_cache_2024_09_to_12_under_5pct() -> None:
    s71 = _load_step7_1_module()

    shared_m1 = s71.load_m1_bidask_cache(
        ["USDJPY", "GBPUSD", "EURJPY", "US100.cash"],
        start_utc_ts=s71.START_4M_TS,
        end_utc_ts=s71.HOLDOUT_CUTOFF_UTC_TS,
        cache_dir=M1_CACHE_DIR,
    )
    for sym, arrs in shared_m1.items():
        assert len(arrs["ts"]) > 100_000, f"Expected full 4M M1 coverage for {sym}"
        assert int(arrs["ts"][-1]) < s71.HOLDOUT_CUTOFF_UTC_TS

    for cid in ("S6_STD_P1_C10_NEWS_ON", "S6_STD_P2_C10_NEWS_ON"):
        gt_bundle = s71._extract_step6_gt_maps(cid)
        curve = s71.reconstruct_intraday_equity_dd_curve(
            gt_bundle["gt_deals"],
            m1_bars=shared_m1,
            start_balance_usd=10000.0,
            initial_balance_usd=10000.0,
            tester_utc_offset_h=2,
            start_utc_ts=s71.START_4M_TS,
            end_utc_ts=s71.HOLDOUT_CUTOFF_UTC_TS,
        )
        assert curve["holdout_rows_analysed"] == 0
        assert curve["order_send_count"] == 0
        assert curve["max_bar_utc_ts"] is not None
        assert curve["max_bar_utc_ts"] < s71.HOLDOUT_CUTOFF_UTC_TS
        assert curve["m1_bars_evaluated"] > 50_000
        assert curve["worst_intraday_daily_dd_adverse_pct"] < 5.0
        assert curve["worst_intraday_daily_dd_close_pct"] < 5.0
        assert curve["breached_5pct_daily_intraday"] is False
        assert curve["passes_daily_dd_limit"] is True
        assert curve["worst_intraday_static_dd_adverse_pct"] < 10.0
        assert curve["breached_10pct_static_intraday"] is False
        # Cross-verify reconstructed peak-to-trough close-M1 equity DD agrees closely with MT5 real-tick HTML report
        htm_eq_dd = float(gt_bundle["parsed_htm"]["equity_dd_pct"])
        assert abs(curve["worst_intraday_peak_to_trough_eq_dd_close_pct"] - htm_eq_dd) < 0.25


@pytest.mark.local_cache
@pytest.mark.skipif(
    not STEP7_1_SCRIPT.exists(),
    reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout",
)
def test_step7_1_2255_flat_target_pass_preserved() -> None:
    s71 = _load_step7_1_module()
    deals = [
        {"server_ts": 1731300000, "direction": "in", "balance": 10000.00},
        {"server_ts": 1731310000, "direction": "out", "balance": 10100.00},
        {"server_ts": 1731386400, "direction": "in", "balance": 10100.00},
        {"server_ts": 1731396400, "direction": "out", "balance": 10200.00},
        {"server_ts": 1731472800, "direction": "in", "balance": 10200.00},
        {"server_ts": 1731482800, "direction": "out", "balance": 10330.00},
        {"server_ts": 1731647307, "direction": "in", "balance": 10328.97},
        {"server_ts": 1731692005, "direction": "in", "balance": 10328.57},
        {"server_ts": 1731693600, "direction": "out", "balance": 10504.77},
        {"server_ts": 1731711300, "direction": "out", "balance": 10593.54},
    ]
    res = s71._compute_phase_target_pass(deals, 10500.0)
    assert res["passed"] is True
    assert res["open_positions"] == 0
    assert res["iso_server"] == "2024-11-15 22:55:00"
    assert res["earlier_nonflat_target_crossing_ignored"]["open_positions"] == 1


@pytest.mark.local_cache
@pytest.mark.skipif(
    not STEP7_1_SCRIPT.exists(),
    reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout",
)
def test_reconstruct_intraday_dd_prague_midnight_reset_with_rollover_bar_gap() -> None:
    s71 = _load_step7_1_module()

    # 2024-10-15 CEST (UTC+2): Prague midnight is 2024-10-15 22:00:00 UTC.
    # Day 1 wins +$400 (anchor=10000, bal=10400); new BUY opens at 21:59:30 UTC;
    # 21:59:00 bar is absent so M1 bars begin at 22:00:00 UTC (already Day 2 Prague!).
    t_win_open = int(datetime(2024, 10, 15, 18, 0, 0, tzinfo=UTC).timestamp())
    t_win_close = int(datetime(2024, 10, 15, 19, 0, 0, tzinfo=UTC).timestamp())
    t_pre_mid = int(datetime(2024, 10, 15, 21, 59, 30, tzinfo=UTC).timestamp())
    t_mid = int(datetime(2024, 10, 15, 22, 0, 0, tzinfo=UTC).timestamp())

    # M1 bars start strictly at 22:00:00 UTC (missing 21:59:00 rollover bar!)
    mins = np.array([t_mid + 60 * i for i in range(10)], dtype=np.int64)
    bl = np.full(10, 1.30000, dtype=np.float64)
    bc = np.full(10, 1.30000, dtype=np.float64)
    ac = np.full(10, 1.30010, dtype=np.float64)
    ah = np.full(10, 1.30010, dtype=np.float64)
    bl[5] = 1.29450  # -$550 from Day-2 anchor 10400 -> true 5.50% daily DD breach!

    deals = [
        {
            "utc_ts": t_win_open,
            "symbol": "GBPUSD",
            "direction": "in",
            "side": "buy",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 10000.0,
        },
        {
            "utc_ts": t_win_close,
            "symbol": "GBPUSD",
            "direction": "out",
            "side": "sell",
            "volume": 1.0,
            "price": 1.30400,
            "balance": 10400.0,
        },
        {
            "utc_ts": t_pre_mid,
            "symbol": "GBPUSD",
            "direction": "in",
            "side": "buy",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 10400.0,
        },
        {
            "utc_ts": t_mid + 8 * 60,
            "symbol": "GBPUSD",
            "direction": "out",
            "side": "sell",
            "volume": 1.0,
            "price": 1.30000,
            "balance": 10400.0,
        },
    ]
    res = s71.reconstruct_intraday_equity_dd_curve(
        deals,
        m1_bars={"GBPUSD": {"ts": mins, "bl": bl, "bc": bc, "ac": ac, "ah": ah}},
        start_balance_usd=10000.0,
        initial_balance_usd=10000.0,
    )
    assert res["worst_intraday_daily_dd_adverse_pct"] == pytest.approx(5.5, abs=1e-4)
    assert res["breached_5pct_daily_intraday"] is True
    assert res["passes_daily_dd_limit"] is False
    assert res["worst_intraday_daily_dd_point"]["prague_day"] == "2024-10-16"
    assert res["worst_intraday_daily_dd_point"]["day_anchor_usd"] == 10400.0


@pytest.mark.local_cache
@pytest.mark.skipif(
    not STEP7_1_SCRIPT.exists(),
    reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout",
)
def test_reconstruct_intraday_dd_eurjpy_rejects_future_usdjpy_lookahead() -> None:
    s71 = _load_step7_1_module()

    t0 = int(datetime(2024, 10, 15, 10, 0, 0, tzinfo=UTC).timestamp())
    ej_ts = np.array([t0, t0 + 60, t0 + 120], dtype=np.int64)
    # USDJPY starts 10 minutes in the FUTURE -> must fail closed, never clamp -1 -> 0!
    uj_future_ts = np.array([t0 + 600], dtype=np.int64)

    deals = [
        {
            "utc_ts": t0,
            "symbol": "EURJPY",
            "direction": "in",
            "side": "sell",
            "volume": 1.0,
            "price": 160.00,
            "balance": 10000.0,
        },
        {
            "utc_ts": t0 + 180,
            "symbol": "EURJPY",
            "direction": "out",
            "side": "buy",
            "volume": 1.0,
            "price": 160.00,
            "balance": 10000.0,
        },
    ]
    with pytest.raises(ValueError, match="CAUSALITY_VIOLATION"):
        s71.reconstruct_intraday_equity_dd_curve(
            deals,
            m1_bars={
                "EURJPY": {
                    "ts": ej_ts,
                    "bl": np.array([160.0, 160.0, 160.0]),
                    "bc": np.array([160.0, 160.0, 160.0]),
                    "ac": np.array([160.02, 160.30, 160.02]),
                    "ah": np.array([160.02, 160.30, 160.02]),
                },
                "USDJPY": {
                    "ts": uj_future_ts,
                    "bl": np.array([150.0]),
                    "bc": np.array([150.0]),
                    "bh": np.array([150.0]),
                    "ac": np.array([150.02]),
                    "ah": np.array([150.02]),
                },
            },
        )


@pytest.mark.local_cache
@pytest.mark.skipif(
    not STEP7_1_SCRIPT.exists(),
    reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout",
)
def test_reconstruct_intraday_dd_empty_deals_still_enforces_2025_holdout_lock() -> None:
    s71 = _load_step7_1_module()

    holdout_ts = np.array([int(datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC).timestamp())], dtype=np.int64)
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        s71.reconstruct_intraday_equity_dd_curve(
            [],
            m1_bars={
                "GBPUSD": {
                    "ts": holdout_ts,
                    "bl": np.array([1.25]),
                    "bc": np.array([1.25]),
                    "ac": np.array([1.2501]),
                    "ah": np.array([1.2501]),
                }
            },
        )

    pre_ts = np.array([int(datetime(2024, 12, 30, 12, 0, 0, tzinfo=UTC).timestamp())], dtype=np.int64)
    ok_empty = s71.reconstruct_intraday_equity_dd_curve(
        [],
        m1_bars={
            "GBPUSD": {
                "ts": pre_ts,
                "bl": np.array([1.25]),
                "bc": np.array([1.25]),
                "ac": np.array([1.2501]),
                "ah": np.array([1.2501]),
            }
        },
    )
    assert ok_empty["holdout_rows_analysed"] == 0
    assert ok_empty["deals_processed"] == 0
    assert ok_empty["worst_intraday_daily_dd_adverse_pct"] == 0.0
    assert ok_empty["passes_daily_dd_limit"] is True
