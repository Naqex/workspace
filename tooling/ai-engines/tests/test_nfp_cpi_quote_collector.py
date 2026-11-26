"""Comprehensive unit tests for hardened read-only QUOTE_ONLY NFP/CPI collector & Demo RO probe (`OrderSend = 0`)."""

from __future__ import annotations

import ast
import csv
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
OPS_CLOUD = ROOT / "tooling/ai-engines/ops_cloud"
if str(OPS_CLOUD) not in sys.path:
    sys.path.insert(0, str(OPS_CLOUD))

import nfp_cpi_quote_collector as qc  # noqa: E402

PROBE_SCRIPT = (
    ROOT
    / "private_vault/strategies/step7-astra-r10-closures-20261126/step7_2_demo_ro_hydration_probe.py"
)
STEP7_1_SCRIPT = (
    ROOT
    / "private_vault/strategies/step7-astra-r10-closures-20261126/step7_1_l0_lot_divergence_audit.py"
)


def _load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location("step7_2_demo_ro_hydration_probe", PROBE_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_step7_1_module() -> Any:
    spec = importlib.util.spec_from_file_location("step7_1_l0_lot_divergence_audit", STEP7_1_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeMT5:
    """Offline mock of MetaTrader5 module (ZERO MT5 process launch, OrderSend = 0)."""

    COPY_TICKS_ALL = 0

    def __init__(
        self,
        *,
        login: int = 990001,
        server: str = "FTMO-Demo",
        connected: bool = True,
        trade_allowed: bool = False,
        positions_total: Any = 0,
        orders_total: Any = 0,
        symbols: tuple[str, ...] = qc.ALL8_SYMBOLS,
        initial_ticks: dict[str, dict[str, Any]] | None = None,
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
        tk = self._initial_ticks.get(symbol)
        if tk is None:
            return None
        return SimpleNamespace(**tk)

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


# ---------------------------------------------------------------------------
# 1. Static OrderSend = 0 & schema invariants
# ---------------------------------------------------------------------------


def test_collector_contains_zero_order_send_calls() -> None:
    src = (OPS_CLOUD / "nfp_cpi_quote_collector.py").read_text(encoding="utf-8")
    assert "mt5.order_send(" not in src
    assert "mt5.order_check(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"order_send", "order_check"}
        if isinstance(node, ast.Name):
            assert node.id not in {"order_send", "order_check"}
    assert qc.RECORD_TIER == "QUOTE_ONLY"
    assert qc.ORDER_SEND_COUNT == 0
    assert len(qc.CSV_COLUMNS) == 23


# ---------------------------------------------------------------------------
# 2. Strict exact red-news calendar verification (OTHER_EVENT rejected!)
# ---------------------------------------------------------------------------


def test_red_news_calendar_contains_dec_2026_nfp_and_cpi() -> None:
    chk = qc.verify_red_news_calendar(ROOT / "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv")
    assert chk["ok"] is True
    assert chk["found"]["US_NFP_20261204"] is True
    assert chk["found"]["US_CPI_20261210"] is True


def test_red_news_calendar_rejects_other_event_at_exact_same_timestamp(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad_red_news.csv"
    bad_csv.write_text(
        "utc_ts,ccy,event\n"
        "1796391000,USD,OTHER_EVENT\n"
        "1796909400,USD,US_CPI\n",
        encoding="utf-8",
    )
    chk = qc.verify_red_news_calendar(bad_csv)
    assert chk["ok"] is False
    assert chk["found"]["US_NFP_20261204"] is False
    assert chk["found"]["US_CPI_20261210"] is True

    # Prefix-extended fake code must also fail exact equality
    bad_prefix_csv = tmp_path / "bad_prefix_red_news.csv"
    bad_prefix_csv.write_text(
        "utc_ts,ccy,event\n"
        "1796391000,USD,US_NFP_FAKE\n"
        "1796909400,USD,US_CPI\n",
        encoding="utf-8",
    )
    chk2 = qc.verify_red_news_calendar(bad_prefix_csv)
    assert chk2["ok"] is False
    assert chk2["found"]["US_NFP_20261204"] is False


# ---------------------------------------------------------------------------
# 3. Event-appropriate default duration_sec (1200.0 vs 5.0)
# ---------------------------------------------------------------------------


def test_default_duration_sec_per_event_and_cli() -> None:
    assert qc.default_duration_sec("US_NFP_20261204") == 1200.0
    assert qc.default_duration_sec("US_CPI_20261210") == 1200.0
    assert qc.default_duration_sec("SMOKE_PREFLIGHT") == 5.0

    parser = qc.build_arg_parser()
    assert parser.parse_args(["--event", "US_NFP_20261204"]).duration_sec is None
    assert parser.parse_args(["--event", "US_CPI_20261210"]).duration_sec is None
    assert parser.parse_args(["--event", "SMOKE_PREFLIGHT"]).duration_sec is None


# ---------------------------------------------------------------------------
# 4. Fail-closed preflight guards (NTP, calendar, login/server, connected, flat/unknown)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_ntp",
    [
        {"ok": False, "offset_ms": -1363.62, "ntp_host": "time.cloudflare.com"},
        {"ok": False, "offset_ms": 1000.0, "ntp_host": "time.cloudflare.com"},
        {"ok": True, "offset_ms": 1000.0, "ntp_host": "time.cloudflare.com"},
        {"ok": True, "offset_ms": -1000.0, "ntp_host": "time.cloudflare.com"},
        {"ok": False, "offset_ms": None, "ntp_host": "time.cloudflare.com"},
        {"ok": True, "offset_ms": None, "ntp_host": "time.cloudflare.com"},
    ],
)
def test_ntp_drift_or_none_aborts_live_capture_and_offline_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], bad_ntp: dict[str, Any]
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: bad_ntp)
    fake_mt5 = FakeMT5()

    with pytest.raises(RuntimeError, match="PREFLIGHT_ABORT_NTP"):
        qc.run_live_capture(
            terminal_exe=tmp_path / "terminal64.exe",
            event_id="US_NFP_20261204",
            out_csv=tmp_path / "out.csv",
            red_news_csv=cal,
            expected_login=990001,
            expected_server="FTMO-Demo",
            mt5_module=fake_mt5,
        )
    assert fake_mt5.initialized is False  # Aborted before even initializing MT5

    rc = qc.main(["--event", "US_NFP_20261204", "--red-news-csv", str(cal), "--preflight-offline-only"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["preflight_ok"] is False
    assert payload["resolved_duration_sec"] == 1200.0
    assert any("NTP_DRIFT_FAILED" in r for r in payload["fail_reasons"])


def test_offline_preflight_passes_when_calendar_and_ntp_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": -14.2})
    rc = qc.main(["--event", "US_CPI_20261210", "--red-news-csv", str(cal), "--preflight-offline-only"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["preflight_ok"] is True
    assert payload["resolved_duration_sec"] == 1200.0


def test_calendar_failure_aborts_live_capture_before_mt5_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_cal = tmp_path / "bad_cal.csv"
    bad_cal.write_text("utc_ts,ccy,event\n1796391000,USD,OTHER_EVENT\n", encoding="utf-8")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 5.0})
    fake_mt5 = FakeMT5()
    with pytest.raises(RuntimeError, match="PREFLIGHT_ABORT_CALENDAR"):
        qc.run_live_capture(
            terminal_exe=tmp_path / "terminal64.exe",
            event_id="US_NFP_20261204",
            out_csv=tmp_path / "out.csv",
            red_news_csv=bad_cal,
            expected_login=990001,
            expected_server="FTMO-Demo",
            mt5_module=fake_mt5,
        )
    assert fake_mt5.initialized is False


@pytest.mark.parametrize(
    ("run_kwargs", "err_match"),
    [
        ({"expected_login": None, "expected_server": "FTMO-Demo"}, "EXPECTED_LOGIN_REQUIRED"),
        ({"expected_login": 0, "expected_server": "FTMO-Demo"}, "EXPECTED_LOGIN_REQUIRED"),
        ({"expected_login": 990001, "expected_server": None}, "EXPECTED_SERVER_REQUIRED"),
        ({"expected_login": 990001, "expected_server": "   "}, "EXPECTED_SERVER_REQUIRED"),
    ],
)
def test_missing_or_empty_expected_login_server_aborts_before_mt5_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_kwargs: dict[str, Any], err_match: str
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 2.0})
    fake_mt5 = FakeMT5()
    with pytest.raises(RuntimeError, match=err_match):
        qc.run_live_capture(
            terminal_exe=tmp_path / "terminal64.exe",
            event_id="SMOKE_PREFLIGHT",
            out_csv=tmp_path / "out.csv",
            red_news_csv=cal,
            mt5_module=fake_mt5,
            **run_kwargs,
        )
    assert fake_mt5.initialized is False


def test_cli_requires_expected_login_and_server_for_live_capture(tmp_path: Path) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    with pytest.raises(SystemExit, match="expected-login"):
        qc.main([
            "--event", "SMOKE_PREFLIGHT",
            "--terminal-exe", str(tmp_path / "terminal64.exe"),
            "--out-csv", str(tmp_path / "out.csv"),
            "--red-news-csv", str(cal),
        ])


@pytest.mark.parametrize(
    ("mt5_kwargs", "run_kwargs", "err_match"),
    [
        ({"login": 990002, "server": "FTMO-Demo"}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "LOGIN_MISMATCH"),
        ({"login": 990001, "server": "Wrong-Server"}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "SERVER_MISMATCH"),
        ({"connected": False}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "DISCONNECTED"),
        ({"trade_allowed": True}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "TRADE_ALLOWED"),
        ({"positions_total": None, "orders_total": 0}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "UNKNOWN_ACCOUNT_STATE"),
        ({"positions_total": 0, "orders_total": None}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "UNKNOWN_ACCOUNT_STATE"),
        ({"positions_total": 1, "orders_total": 0}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "NON_FLAT"),
        ({"positions_total": 0, "orders_total": 2}, {"expected_login": 990001, "expected_server": "FTMO-Demo"}, "NON_FLAT"),
    ],
)
def test_fail_closed_login_server_connected_and_flat_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mt5_kwargs: dict[str, Any],
    run_kwargs: dict[str, Any],
    err_match: str,
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 8.0})
    fake_mt5 = FakeMT5(**mt5_kwargs)
    with pytest.raises(RuntimeError, match=err_match):
        qc.run_live_capture(
            terminal_exe=tmp_path / "terminal64.exe",
            event_id="SMOKE_PREFLIGHT",
            out_csv=tmp_path / "out.csv",
            red_news_csv=cal,
            mt5_module=fake_mt5,
            connect_wait_attempts=1,
            connect_wait_sleep_s=0.0,
            **run_kwargs,
        )
    assert fake_mt5.shutdown_called is True


def test_cli_returns_exit_2_on_login_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 3.0})
    monkeypatch.setitem(sys.modules, "MetaTrader5", FakeMT5(login=990002, server="FTMO-Demo"))
    out_json = tmp_path / "abort.json"
    rc = qc.main([
        "--event", "SMOKE_PREFLIGHT",
        "--terminal-exe", str(tmp_path / "terminal64.exe"),
        "--out-csv", str(tmp_path / "out.csv"),
        "--out-json", str(out_json),
        "--red-news-csv", str(cal),
        "--expected-login", "990001",
        "--expected-server", "FTMO-Demo",
    ])
    assert rc == 2
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["status"] == "ABORTED_FAIL_CLOSED"
    assert "LOGIN_MISMATCH" in payload["error"]
    assert capsys.readouterr().out.strip()


# ---------------------------------------------------------------------------
# 5. Same-millisecond tick preservation (3 price jumps in EXACT same time_msc!)
# ---------------------------------------------------------------------------


def test_same_millisecond_three_price_jumps_captured_zero_drops_zero_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel_ts = qc.EVENTS["US_NFP_20261204"]["release_utc_ts"]  # 1796391000
    srv_off_ms = 2 * 3600 * 1000
    t_burst = (rel_ts + 1) * 1000 + srv_off_ms  # Exact same time_msc for 3 price jumps!

    # Poll 1 has 2 ticks in t_burst; Poll 2 re-returns those 2 + a 3rd jump in the SAME t_burst;
    # Poll 3 re-returns all 3 (must emit 0 duplicates!).
    j1 = {"time_msc": t_burst, "bid": 21000.00, "ask": 21001.00, "flags": 6}
    j2 = {"time_msc": t_burst, "bid": 21005.00, "ask": 21007.00, "flags": 6}
    j3 = {"time_msc": t_burst, "bid": 21012.50, "ask": 21016.00, "flags": 6}

    init_ticks = _make_base_ticks(rel_ts, srv_off_ms, offset_sec=1)
    init_ticks["US100.cash"] = dict(j1)

    poll_batches: dict[str, list[list[dict[str, Any]]]] = {}
    for sym in qc.ALL8_SYMBOLS:
        if sym == "US100.cash":
            poll_batches[sym] = [[j1, j2], [j1, j2, j3], [j1, j2, j3]]
        else:
            poll_batches[sym] = [[init_ticks[sym]], [init_ticks[sym]], [init_ticks[sym]]]

    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": -10.0})

    # Controlled virtual clock: 3 poll iterations covering t=0.0, 0.2, 0.4 -> exits at 0.5
    clock_vals = iter([
        float(rel_ts + 1),       # now_utc_ms for srv_minus_utc_ms
        float(rel_ts + 1),       # t_end base
        float(rel_ts + 1.05),    # iter 1 recv_ms
        float(rel_ts + 1.10),    # iter 1 end check (< t_end)
        float(rel_ts + 1.20),    # iter 2 recv_ms
        float(rel_ts + 1.25),    # iter 2 end check (< t_end)
        float(rel_ts + 1.40),    # iter 3 recv_ms
        float(rel_ts + 1.60),    # iter 3 end check (>= t_end -> break)
    ])
    monkeypatch.setattr(qc.time, "time", lambda: next(clock_vals, float(rel_ts + 2.0)))
    monkeypatch.setattr(qc.time, "sleep", lambda _s: None)

    fake_mt5 = FakeMT5(initial_ticks=init_ticks, poll_batches=poll_batches)
    out_csv = tmp_path / "nfp_burst.csv"
    rep = qc.run_live_capture(
        terminal_exe=tmp_path / "terminal64.exe",
        event_id="US_NFP_20261204",
        out_csv=out_csv,
        duration_sec=0.5,
        red_news_csv=cal,
        expected_login=990001,
        expected_server="FTMO-Demo",
        mt5_module=fake_mt5,
        poll_sleep_sec=0.0,
        connect_wait_attempts=1,
        connect_wait_sleep_s=0.0,
    )

    # Single-second burst for US_NFP_20261204 MUST NOT pass as COMPLETE (Astra R11 Q2a: requires all 3 phases + >=300s span!)
    assert rep["window_complete"] is False
    assert rep["status"] == "INCOMPLETE_MISSING_DATA"
    assert set(rep["completeness"]["missing_pre_event_symbols"]) == set(qc.CORE4_SYMBOLS)
    assert set(rep["completeness"]["missing_post_normalize_symbols"]) == set(qc.CORE4_SYMBOLS)
    assert any("INSUFFICIENT_WINDOW_ELAPSED_SPAN" in r for r in rep["completeness"]["reasons"])
    assert rep["order_send_count"] == 0
    assert rep["same_ms_order_unrecoverable_count"] == 0

    with out_csv.open("r", encoding="utf-8", newline="") as f:
        us100_rows = [r for r in csv.DictReader(f) if r["symbol"] == "US100.cash"]

    # EXACTLY 3 rows (all 3 jumps preserved, 0 dropped, 0 duplicated!)
    assert len(us100_rows) == 3
    assert [int(r["server_tick_msc"]) for r in us100_rows] == [t_burst, t_burst, t_burst]
    assert [float(r["bid"]) for r in us100_rows] == [21000.0, 21005.0, 21012.5]
    assert [float(r["ask"]) for r in us100_rows] == [21001.0, 21007.0, 21016.0]
    assert [int(r["inter_tick_gap_ms"]) for r in us100_rows] == [0, 0, 0]
    assert [float(r["delta_bid_pts"]) for r in us100_rows] == [0.0, 500.0, 750.0]
    assert [float(r["delta_ask_pts"]) for r in us100_rows] == [0.0, 600.0, 900.0]
    assert all(r["window_phase"] == "IMPACT_CORE" for r in us100_rows)
    assert rep["summary"]["symbols"]["US100.cash"]["tick_count"] == 3
    assert rep["summary"]["symbols"]["US100.cash"]["max_1tick_jump_pts"] == 900.0


def test_full_three_phase_300s_plus_nfp_window_passes_as_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel_ts = qc.EVENTS["US_NFP_20261204"]["release_utc_ts"]
    srv_off_ms = 2 * 3600 * 1000
    pre_ticks = _make_base_ticks(rel_ts, srv_off_ms, offset_sec=-120)     # PRE_EVENT
    imp_ticks = _make_base_ticks(rel_ts, srv_off_ms, offset_sec=5)        # IMPACT_CORE
    post_ticks = _make_base_ticks(rel_ts, srv_off_ms, offset_sec=360)     # POST_NORMALIZE (span = 480s >= 300s!)

    poll_batches = {
        sym: [[pre_ticks[sym]], [imp_ticks[sym]], [post_ticks[sym]]]
        for sym in qc.ALL8_SYMBOLS
    }
    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 5.0})
    clock_vals = iter([
        float(rel_ts - 120),
        float(rel_ts - 120),
        float(rel_ts - 119),
        float(rel_ts - 118),
        float(rel_ts + 5),
        float(rel_ts + 6),
        float(rel_ts + 360),
        float(rel_ts + 400),
    ])
    monkeypatch.setattr(qc.time, "time", lambda: next(clock_vals, float(rel_ts + 500)))
    monkeypatch.setattr(qc.time, "sleep", lambda _s: None)

    fake_mt5 = FakeMT5(initial_ticks=pre_ticks, poll_batches=poll_batches)
    rep = qc.run_live_capture(
        terminal_exe=tmp_path / "terminal64.exe",
        event_id="US_NFP_20261204",
        out_csv=tmp_path / "nfp_complete.csv",
        duration_sec=500.0,
        red_news_csv=cal,
        expected_login=990001,
        expected_server="FTMO-Demo",
        mt5_module=fake_mt5,
        poll_sleep_sec=0.0,
        connect_wait_attempts=1,
        connect_wait_sleep_s=0.0,
    )
    assert rep["window_complete"] is True
    assert rep["status"] == "COMPLETE"
    assert rep["completeness"]["window_elapsed_span_sec"] == 480.0
    assert rep["completeness"]["missing_pre_event_symbols"] == []
    assert rep["completeness"]["missing_impact_core_symbols"] == []
    assert rep["completeness"]["missing_post_normalize_symbols"] == []
    assert rep["completeness"]["short_span_core4_symbols"] == []


def test_same_ms_cursor_snapshot_b_before_range_a_b_emits_a_and_flags_order_unrecoverable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cur = qc.SameMsTickCursor(1000)
    tk_a = {"time_msc": 1500, "bid": 1.1000, "ask": 1.1002, "flags": 6}
    tk_b = {"time_msc": 1500, "bid": 1.1005, "ask": 1.1007, "flags": 6}
    tk_c = {"time_msc": 1500, "bid": 1.1010, "ask": 1.1013, "flags": 6}

    # Poll 1: fallback snapshot sees B first
    out1 = cur.consume_snapshot(tk_b)
    assert out1 == [(1500, 1.1005, 1.1007, 6)]
    assert cur.same_ms_order_unrecoverable_count == 0

    # Poll 2: range query returns [A, B] at exact same time_msc -> MUST emit A (not drop!), NOT dupe B, and flag unrecoverable order!
    with caplog.at_level("WARNING", logger=qc.__name__):
        out2 = cur.consume_batch([tk_a, tk_b])
    assert out2 == [(1500, 1.1000, 1.1002, 6)]
    assert cur.same_ms_order_unrecoverable_count == 1
    assert len(cur.same_ms_order_unrecoverable_events) == 1
    assert cur.same_ms_order_unrecoverable_events[0]["had_snapshot_fallback"] is True
    assert any("SAME_MS_ORDER_UNRECOVERABLE" in rec.message for rec in caplog.records)

    # Poll 3: range returns [A, B, C] -> MUST emit ONLY C (zero dupes, no spurious extra flag!)
    out3 = cur.consume_batch([tk_a, tk_b, tk_c])
    assert out3 == [(1500, 1.1010, 1.1013, 6)]
    assert cur.same_ms_order_unrecoverable_count == 1

    # Poll 4: range repeats [A, B, C] -> emits nothing!
    assert cur.consume_batch([tk_a, tk_b, tk_c]) == []


# ---------------------------------------------------------------------------
# 6. Post-capture window completeness check (missing IMPACT_CORE -> exit 2!)
# ---------------------------------------------------------------------------


def test_missing_impact_core_marks_incomplete_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel_ts = qc.EVENTS["US_NFP_20261204"]["release_utc_ts"]
    srv_off_ms = 2 * 3600 * 1000
    # All ticks are at -120s (PRE_EVENT only -> ZERO IMPACT_CORE coverage!)
    pre_ticks = _make_base_ticks(rel_ts, srv_off_ms, offset_sec=-120)
    poll_batches = {sym: [[tk]] for sym, tk in pre_ticks.items()}

    cal = _write_valid_calendar(tmp_path / "cal.csv")
    monkeypatch.setattr(qc, "measure_ntp_offset_ms", lambda *a, **k: {"ok": True, "offset_ms": 4.0})
    clock_vals = iter([
        float(rel_ts - 120),
        float(rel_ts - 120),
        float(rel_ts - 120),
        float(rel_ts - 110),
    ])
    monkeypatch.setattr(qc.time, "time", lambda: next(clock_vals, float(rel_ts - 100)))
    monkeypatch.setattr(qc.time, "sleep", lambda _s: None)
    monkeypatch.setitem(sys.modules, "MetaTrader5", FakeMT5(initial_ticks=pre_ticks, poll_batches=poll_batches))

    out_csv = tmp_path / "incomplete_nfp.csv"
    out_json = tmp_path / "incomplete_nfp.json"
    rc = qc.main([
        "--event", "US_NFP_20261204",
        "--terminal-exe", str(tmp_path / "terminal64.exe"),
        "--out-csv", str(out_csv),
        "--out-json", str(out_json),
        "--duration-sec", "1.0",
        "--red-news-csv", str(cal),
        "--expected-login", "990001",
        "--expected-server", "FTMO-Demo",
    ])
    assert rc == 2
    rep = json.loads(out_json.read_text(encoding="utf-8"))
    assert rep["window_complete"] is False
    assert rep["status"] == "INCOMPLETE_MISSING_DATA"
    assert set(rep["completeness"]["missing_impact_core_symbols"]) == set(qc.CORE4_SYMBOLS)


# ---------------------------------------------------------------------------
# 7. Existing tick-row schema & summary coverage
# ---------------------------------------------------------------------------


def test_build_tick_row_and_phase_classification(tmp_path: Path) -> None:
    rel_ts = qc.EVENTS["US_NFP_20261204"]["release_utc_ts"]  # 1796391000
    srv_off_ms = 2 * 3600 * 1000
    r1 = qc.build_tick_row(
        event_id="US_NFP_20261204",
        release_utc_ts=rel_ts,
        server_tick_msc=(rel_ts - 60) * 1000 + srv_off_ms,
        server_minus_utc_ms=srv_off_ms,
        local_recv_msc=(rel_ts - 60) * 1000 + 50,
        ntp_offset_ms=-12.5,
        account_alias="DEMO_SECONDARY",
        server="FTMO-Demo",
        symbol="US100.cash",
        bid=21000.00,
        ask=21001.50,
        point=0.01,
        tick_flags=6,
        prev_tick=None,
    )
    assert r1["window_phase"] == "PRE_EVENT"
    assert r1["spread_pts"] == 150.0
    assert r1["order_send_count"] == 0

    r2 = qc.build_tick_row(
        event_id="US_NFP_20261204",
        release_utc_ts=rel_ts,
        server_tick_msc=(rel_ts + 2) * 1000 + srv_off_ms,
        server_minus_utc_ms=srv_off_ms,
        local_recv_msc=(rel_ts + 2) * 1000 + 80,
        ntp_offset_ms=-12.5,
        account_alias="DEMO_SECONDARY",
        server="FTMO-Demo",
        symbol="US100.cash",
        bid=21010.00,
        ask=21014.00,
        point=0.01,
        tick_flags=6,
        prev_tick=r1,
    )
    assert r2["window_phase"] == "IMPACT_CORE"
    assert r2["spread_pts"] == 400.0
    assert r2["delta_bid_pts"] == 1000.0
    assert r2["inter_tick_gap_ms"] == 62000

    out_csv = tmp_path / "sample.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(qc.CSV_COLUMNS))
        w.writeheader()
        w.writerow(r1)
        w.writerow(r2)
    summ = qc.summarize_captured_csv(out_csv)
    assert summ["total_rows"] == 2
    assert summ["symbols"]["US100.cash"]["spread_max_pts"] == 400.0
    assert summ["symbols"]["US100.cash"]["max_1tick_jump_pts"] == 1250.0
    assert summ["symbols"]["US100.cash"]["phase_counts"] == {
        "PRE_EVENT": 1,
        "IMPACT_CORE": 1,
        "POST_NORMALIZE": 0,
    }


# ---------------------------------------------------------------------------
# 8. Step 7.2 Demo RO Hydration & Restart Probe Verifier Tests (Layer-2 probe)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PROBE_SCRIPT.exists(), reason="Layer-2 private_vault probe absent in clean Layer-1 checkout")
@pytest.mark.local_cache
def test_demo_ro_probe_mql5_source_is_strictly_read_only() -> None:
    probe = _load_probe_module()
    probe.assert_probe_source_read_only(probe.MQL5_PROBE_SOURCE)
    assert "script_show_inputs" not in probe.MQL5_PROBE_SOURCE
    code_only = "\n".join(line.split("//")[0] for line in probe.MQL5_PROBE_SOURCE.splitlines())
    assert "OrderSend" not in code_only
    assert "OrderCheck" not in code_only
    assert "CTrade" not in code_only


@pytest.mark.skipif(not PROBE_SCRIPT.exists(), reason="Layer-2 private_vault probe absent in clean Layer-1 checkout")
@pytest.mark.local_cache
def test_verify_hydration_against_statement_utc_d1_ny_parity_and_negative_cases() -> None:
    probe = _load_probe_module()

    # Choose a UTC timestamp where UTC day, Broker D1 day (UTC+2), AND NY day (UTC-5) ALL DIFFER!
    # 2026-11-26 22:30:00 UTC:
    #   - UTC day      = 2026-11-26 00:00:00 UTC (1795651200)
    #   - Broker +2h   = 2026-11-27 00:30:00 SRV -> D1 bar = 2026-11-27 00:00:00 (1795737600)
    #   - Deal for E4 at 2026-11-26 02:15:00 UTC = 2026-11-25 21:15:00 EST -> NY day = 2026-11-25 00:00:00 (1795564800)!
    srv_off = 2 * 3600
    now_utc = 1795732200  # 2026-11-26 22:30:00 UTC
    srv_now = now_utc + srv_off  # 2026-11-27 00:30:00 SRV
    d1_bar_27 = 1795737600  # 2026-11-27 00:00:00 SRV
    d1_bars = {"USDJPY": d1_bar_27, "GBPUSD": d1_bar_27, "EURJPY": d1_bar_27}

    e1_utc = 1795665600  # 2026-11-26 04:00:00 UTC -> UTC day = 1795651200
    e2_utc = 1795731000  # 2026-11-26 22:10:00 UTC -> SRV = 2026-11-27 00:10:00 >= d1_bar_27 -> D1 = 1795737600
    e4_utc = 1795659300  # 2026-11-26 02:15:00 UTC -> EST = 2026-11-25 21:15:00 -> NY day = 1795564800

    stmt_deals = [
        {"ticket": 1001, "magic": 20261122, "symbol": "USDJPY",     "deal_time": e1_utc + srv_off, "entry": 0, "type": 0},
        {"ticket": 1002, "magic": 20261123, "symbol": "USDJPY",     "deal_time": e2_utc + srv_off, "entry": 0, "type": 1},
        {"ticket": 1003, "magic": 20261124, "symbol": "US100.cash", "deal_time": e4_utc + srv_off, "entry": 0, "type": 0},
        # DEAL_ENTRY_OUT (entry=1) should be matched in 48h set, NOT mutate m_tradedDay
        {"ticket": 1004, "magic": 20261125, "symbol": "GBPUSD",     "deal_time": e2_utc + srv_off, "entry": 1, "type": 0},
    ]

    expected_days = probe.compute_expected_traded_days(
        stmt_deals,
        now_utc=now_utc,
        server_now=srv_now,
        d1_bar_times=d1_bars,
    )
    assert expected_days[0] == 1795651200  # E1 -> UTC day (2026-11-26)
    assert expected_days[1] == 1795737600  # E2 -> Broker D1 day (2026-11-27)
    assert expected_days[2] == 0           # E3 -> only DEAL_ENTRY_OUT, not IN
    assert expected_days[3] == 1795564800  # E4 -> NY day (2026-11-25)
    assert expected_days[4:] == [0, 0, 0, 0]

    def _mk_receipt(phase: int, days: list[int], deals: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
        rec: dict[str, Any] = {
            "phase": phase,
            "pid": 10000 + phase,
            "login": 990001,
            "server": "FTMO-Demo",
            "is_tester": False,
            "terminal_connected": True,
            "terminal_trade_allowed": False,
            "mql_trade_allowed": False,
            "order_send_count": 0,
            "positions_total": 0,
            "orders_total": 0,
            "now_utc": now_utc,
            "server_now": srv_now,
            "d1_bar_times": dict(d1_bars),
            "history_select_48h_ok": True,
            "hydrate_returned": True,
            "is_hydrated_flag": True,
            "hydrated_traded_days": list(days),
            "deals_48h": [dict(d) for d in deals],
            "day_anchor_gv_existed_before": (phase == 2),
            "day_anchor_bal": 10000.0,
        }
        rec.update(overrides)
        return rec

    # Positive case: exact match across UTC / Broker D1 / NY and PID1 -> PID2
    p1 = _mk_receipt(1, expected_days, stmt_deals)
    p2 = _mk_receipt(2, expected_days, stmt_deals)
    res_ok = probe.verify_hydration_against_statement(stmt_deals, p1, p2, 990001, "FTMO-Demo")
    assert res_ok["ok"] is True
    assert res_ok["verdict"] == probe.VERDICT_HYDRATION_VERIFIED
    assert res_ok["strategy_magic_deals_48h_count"] == 3

    # Negative 1: Wrong engine session day (e.g. using UTC day instead of NY day for E4 idx=3!)
    bad_ny_days = list(expected_days)
    bad_ny_days[3] = 1795651200  # Wrong: UTC day instead of NY day 1795564800
    res_bad_day = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, bad_ny_days, stmt_deals), _mk_receipt(2, bad_ny_days, stmt_deals), 990001, "FTMO-Demo"
    )
    assert res_bad_day["ok"] is False
    assert res_bad_day["verdict"] == probe.VERDICT_FAILED
    assert "per_engine_session_day_exact_match_across_restart" in res_bad_day["failed_checks"]
    assert res_bad_day["session_day_mismatches"][0]["engine_id"] == "E4_US100_SESS40"

    # Negative 2: Missing ticket in Phase 2
    res_missing_tk = probe.verify_hydration_against_statement(
        stmt_deals, p1, _mk_receipt(2, expected_days, stmt_deals[:-1]), 990001, "FTMO-Demo"
    )
    assert res_missing_tk["ok"] is False
    assert "deal_ticket_magic_symbol_time_exact_match" in res_missing_tk["failed_checks"]
    assert len(res_missing_tk["deal_diff"]["missing_in_phase2"]) == 1

    # Negative 3: Wrong magic on a deal
    tampered_magic = [dict(d) for d in stmt_deals]
    tampered_magic[0]["magic"] = 99999999
    res_bad_magic = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, expected_days, tampered_magic), p2, 990001, "FTMO-Demo"
    )
    assert res_bad_magic["ok"] is False
    assert "deal_ticket_magic_symbol_time_exact_match" in res_bad_magic["failed_checks"]

    # Negative 4: Wrong server / trading enabled / non-flat / unknown positions
    res_wrong_srv = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, expected_days, stmt_deals, server="Other-Demo"), p2, 990001, "FTMO-Demo"
    )
    assert res_wrong_srv["ok"] is False
    assert "login_and_server_exact_match" in res_wrong_srv["failed_checks"]

    res_trade_on = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, expected_days, stmt_deals, terminal_trade_allowed=True), p2, 990001, "FTMO-Demo"
    )
    assert res_trade_on["ok"] is False
    assert "trading_locked_and_zero_order_send" in res_trade_on["failed_checks"]

    res_non_flat = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, expected_days, stmt_deals, positions_total=None), p2, 990001, "FTMO-Demo"
    )
    assert res_non_flat["ok"] is False
    assert "flat_account_verified" in res_non_flat["failed_checks"]

    # Astra honesty rule: 0 strategy-magic deals in 48h -> CONNECTIVITY_AND_HISTORY_READ_ONLY_NO_STRAT_DEALS_48H
    zero_days = [0] * 8
    other_deals = [{"ticket": 2001, "magic": 0, "symbol": "", "deal_time": srv_now - 3600, "entry": 0, "type": 2}]
    res_no_strat = probe.verify_hydration_against_statement(
        other_deals, _mk_receipt(1, zero_days, other_deals), _mk_receipt(2, zero_days, other_deals), 990001, "FTMO-Demo"
    )
    assert res_no_strat["ok"] is True
    assert res_no_strat["verdict"] == probe.VERDICT_NO_STRAT_DEALS_48H
    assert res_no_strat["strategy_magic_hydration_exercised"] is False

    # Negative 5: Broker D1 engine (E2 idx=1) wrongly hydrated with UTC day instead of Broker D1 day
    bad_d1_days = list(expected_days)
    bad_d1_days[1] = 1795651200  # Wrong: UTC day instead of Broker D1 1795737600
    res_bad_d1 = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, bad_d1_days, stmt_deals), _mk_receipt(2, bad_d1_days, stmt_deals), 990001, "FTMO-Demo"
    )
    assert res_bad_d1["ok"] is False
    assert res_bad_d1["session_day_mismatches"][0]["engine_id"] == "E2_USDJPY_EXP80"

    # Negative 6: Phase1 != Phase2 hydration drift across restart & missing d1_bar_times fail-closed
    res_drift = probe.verify_hydration_against_statement(
        stmt_deals, p1, _mk_receipt(2, zero_days, stmt_deals), 990001, "FTMO-Demo"
    )
    assert res_drift["ok"] is False
    assert "per_engine_session_day_exact_match_across_restart" in res_drift["failed_checks"]

    res_no_d1_bars = probe.verify_hydration_against_statement(
        stmt_deals, _mk_receipt(1, expected_days, stmt_deals, d1_bar_times={}), p2, 990001, "FTMO-Demo"
    )
    assert res_no_d1_bars["ok"] is False
    assert "per_engine_session_day_exact_match_across_restart" in res_no_d1_bars["failed_checks"]


@pytest.mark.skipif(not PROBE_SCRIPT.exists(), reason="Layer-2 private_vault probe absent in clean Layer-1 checkout")
@pytest.mark.local_cache
def test_demo_ro_probe_all8_engines_and_ny_dst_boundaries() -> None:
    probe = _load_probe_module()
    # Verify exact NY DST switch dates matching Naqex_Signals_7E.mqh:325-336
    # 2026-03-08 06:59 UTC (before 2nd Sun Mar 07:00 UTC) -> EST (-5); 07:00 UTC -> EDT (-4)
    assert probe.new_york_utc_offset_hours(1772953140) == -5
    assert probe.new_york_utc_offset_hours(1772953200) == -4
    # 2026-11-01 05:59 UTC (before 1st Sun Nov 06:00 UTC) -> EDT (-4); 06:00 UTC -> EST (-5)
    assert probe.new_york_utc_offset_hours(1793512740) == -4
    assert probe.new_york_utc_offset_hours(1793512800) == -5

    # Verify all 8 engines (E1..E7 + S6) map to exact day kinds (UTC / BROKER_D1 / NY)
    srv_off = 3 * 3600  # Summer UTC+3 server
    now_utc = 1781650800  # 2026-06-16 23:00:00 UTC -> SRV = 2026-06-17 02:00:00
    srv_now = now_utc + srv_off
    d1_jun17 = 1781654400  # 2026-06-17 00:00:00 SRV
    d1_bars = {"USDJPY": d1_jun17, "GBPUSD": d1_jun17, "EURJPY": d1_jun17}
    deal_utc_early = 1781575200  # 2026-06-16 02:00:00 UTC -> EDT = 2026-06-15 22:00 -> NY day = 2026-06-15 (1781481600)
    deal_utc_late = 1781647200   # 2026-06-16 22:00:00 UTC -> SRV = 2026-06-17 01:00 >= d1_jun17

    all8_deals = [
        {"ticket": 1, "magic": 20261122, "symbol": "USDJPY",     "deal_time": deal_utc_early + srv_off, "entry": 0, "type": 0},  # E1 UTC -> Jun16
        {"ticket": 2, "magic": 20261123, "symbol": "USDJPY",     "deal_time": deal_utc_late + srv_off,  "entry": 0, "type": 0},  # E2 D1  -> Jun17
        {"ticket": 3, "magic": 20261125, "symbol": "GBPUSD",     "deal_time": deal_utc_late + srv_off,  "entry": 0, "type": 1},  # E3 D1  -> Jun17
        {"ticket": 4, "magic": 20261124, "symbol": "US100.cash", "deal_time": deal_utc_early + srv_off, "entry": 0, "type": 0},  # E4 NY  -> Jun15
        {"ticket": 5, "magic": 20261126, "symbol": "US100.cash", "deal_time": deal_utc_early + srv_off, "entry": 0, "type": 1},  # E5 NY  -> Jun15
        {"ticket": 6, "magic": 20261128, "symbol": "EURJPY",     "deal_time": deal_utc_late + srv_off,  "entry": 0, "type": 0},  # E6 D1  -> Jun17
        {"ticket": 7, "magic": 20261129, "symbol": "USDJPY",     "deal_time": deal_utc_early + srv_off, "entry": 0, "type": 1},  # E7 NY  -> Jun15
        {"ticket": 8, "magic": 20261127, "symbol": "EURUSD",     "deal_time": deal_utc_early + srv_off, "entry": 0, "type": 0},  # S6 UTC -> Jun16
    ]
    exp = probe.compute_expected_traded_days(all8_deals, now_utc=now_utc, server_now=srv_now, d1_bar_times=d1_bars)
    utc_jun16 = 1781568000
    ny_jun15 = 1781481600
    assert exp == [utc_jun16, d1_jun17, d1_jun17, ny_jun15, ny_jun15, d1_jun17, ny_jun15, utc_jun16]


def test_same_ms_cursor_handles_numpy_structured_ticks_and_repeated_quotes() -> None:
    np = pytest.importorskip("numpy")
    dt = np.dtype([("time_msc", "<i8"), ("bid", "<f8"), ("ask", "<f8"), ("flags", "<u4")])
    cur = qc.SameMsTickCursor(1000)
    b1 = np.array([(1500, 1.1000, 1.1002, 6), (1500, 1.1005, 1.1008, 6)], dtype=dt)
    b2 = np.array([(1500, 1.1000, 1.1002, 6), (1500, 1.1005, 1.1008, 6), (1500, 1.1010, 1.1014, 6), (1501, 1.1012, 1.1015, 6)], dtype=dt)
    out1 = cur.consume_batch(b1)
    out2 = cur.consume_batch(b2)
    out3 = cur.consume_batch(b2)
    assert len(out1) == 2
    assert len(out2) == 2
    assert [t[0] for t in out2] == [1500, 1501]
    assert out2[0][1] == 1.1010
    assert out3 == []


@pytest.mark.skipif(not PROBE_SCRIPT.exists(), reason="Layer-2 private_vault probe absent in clean Layer-1 checkout")
@pytest.mark.local_cache
def test_demo_ro_probe_shadow_s6_only_never_grants_core7_verdict() -> None:
    probe = _load_probe_module()
    srv_off = 2 * 3600
    now_utc = 1795732200
    srv_now = now_utc + srv_off
    d1_bar_27 = 1795737600
    d1_bars = {"USDJPY": d1_bar_27, "GBPUSD": d1_bar_27, "EURJPY": d1_bar_27}
    s6_utc = 1795665600

    # ONLY shadow S6 (magic 20261127) deal exists in 48h — ZERO Core7 strategy deals!
    shadow_only_deals = [
        {"ticket": 5001, "magic": 20261127, "symbol": "EURUSD", "deal_time": s6_utc + srv_off, "entry": 0, "type": 0},
    ]
    exp_days = probe.compute_expected_traded_days(
        shadow_only_deals, now_utc=now_utc, server_now=srv_now, d1_bar_times=d1_bars
    )
    assert exp_days[:7] == [0] * 7
    assert exp_days[7] == 1795651200

    def _mk_r(phase: int) -> dict[str, Any]:
        return {
            "phase": phase,
            "pid": 20000 + phase,
            "login": 990001,
            "server": "FTMO-Demo",
            "is_tester": False,
            "terminal_connected": True,
            "terminal_trade_allowed": False,
            "mql_trade_allowed": False,
            "order_send_count": 0,
            "positions_total": 0,
            "orders_total": 0,
            "now_utc": now_utc,
            "server_now": srv_now,
            "d1_bar_times": dict(d1_bars),
            "history_select_48h_ok": True,
            "hydrate_returned": True,
            "is_hydrated_flag": True,
            "hydrated_traded_days": list(exp_days),
            "deals_48h": [dict(d) for d in shadow_only_deals],
            "day_anchor_gv_existed_before": (phase == 2),
            "day_anchor_bal": 10000.0,
        }

    res = probe.verify_hydration_against_statement(shadow_only_deals, _mk_r(1), _mk_r(2), 990001, "FTMO-Demo")
    assert res["ok"] is True
    assert res["verdict"] == probe.VERDICT_SHADOW_S6_ONLY_48H
    assert res["verdict"] != probe.VERDICT_HYDRATION_VERIFIED
    assert res["core7_strategy_magic_deals_48h_count"] == 0
    assert res["shadow_s6_deals_48h_count"] == 1
    assert res["core7_hydration_verified"] is False
    assert res["strategy_magic_hydration_exercised"] is False
    assert res["shadow_s6_only_48h"] is True


@pytest.mark.skipif(not PROBE_SCRIPT.exists(), reason="Layer-2 private_vault probe absent in clean Layer-1 checkout")
@pytest.mark.local_cache
def test_demo_ro_capture_statement_aligned_48h_bounds_and_none_history_raises(tmp_path: Path) -> None:
    probe = _load_probe_module()
    captured_bounds: list[tuple[int, int]] = []

    class FakeStmtMT5:
        def __init__(self, *, history_return: Any, server_time: int = 1795739400) -> None:
            self._history_return = history_return
            self._server_time = server_time
            self.shutdown_called = False

        def initialize(self, path: str, portable: bool = True) -> bool:
            return True

        def shutdown(self) -> None:
            self.shutdown_called = True

        def last_error(self) -> tuple[int, str]:
            return (-2, "Simulated history_deals_get failure")

        def terminal_info(self) -> Any:
            return SimpleNamespace(connected=True, trade_allowed=False)

        def account_info(self) -> Any:
            return SimpleNamespace(login=990001, server="FTMO-Demo", balance=10000.0, equity=10000.0)

        def positions_total(self) -> int:
            return 0

        def orders_total(self) -> int:
            return 0

        def symbol_select(self, symbol: str, enable: bool) -> bool:
            return True

        def symbol_info_tick(self, symbol: str) -> Any:
            return SimpleNamespace(time=self._server_time, time_msc=self._server_time * 1000)

        def history_deals_get(self, dt_from: Any, dt_to: Any) -> Any:
            captured_bounds.append((int(dt_from.timestamp()), int(dt_to.timestamp())))
            return self._history_return

    # (a) None return from history_deals_get MUST raise hard RuntimeError (NEVER coerced to empty tuple!)
    mt5_none = FakeStmtMT5(history_return=None)
    with pytest.raises(RuntimeError, match="HISTORY_DEALS_GET_FAILED"):
        probe._capture_python_statement(
            tmp_path, 990001, "FTMO-Demo", mt5_module=mt5_none, connect_wait_attempts=1, connect_wait_sleep_s=0.0
        )
    assert mt5_none.shutdown_called is True
    assert captured_bounds[-1] == (1795739400 - 48 * 3600, 1795739400 + 60)

    # (b) Legitimate empty tuple () succeeds and records exact aligned broker-server 48h bounds (NO +4h skew!)
    mt5_empty = FakeStmtMT5(history_return=())
    meta, deals = probe._capture_python_statement(
        tmp_path, 990001, "FTMO-Demo", mt5_module=mt5_empty, connect_wait_attempts=1, connect_wait_sleep_s=0.0
    )
    assert deals == []
    assert meta["server_now"] == 1795739400
    assert meta["window_server_from"] == 1795739400 - 48 * 3600
    assert meta["window_server_to"] == 1795739400 + 60


@pytest.mark.skipif(not STEP7_1_SCRIPT.exists(), reason="Layer-2 private_vault Step 7.1 script absent in clean Layer-1 checkout")
@pytest.mark.local_cache
def test_step7_1_phase_target_pass_requires_zero_open_positions() -> None:
    s71 = _load_step7_1_module()
    # 4 distinct trading days; at deal #8 (18:00), balance crosses 10504.77 while 1 position (0.16 lot) is STILL open;
    # only at deal #9 (22:55) is open_positions == 0 with balance 10593.54!
    deals = [
        {"server_ts": 1731300000, "direction": "in",  "balance": 10000.00},
        {"server_ts": 1731310000, "direction": "out", "balance": 10100.00},
        {"server_ts": 1731386400, "direction": "in",  "balance": 10100.00},
        {"server_ts": 1731396400, "direction": "out", "balance": 10200.00},
        {"server_ts": 1731472800, "direction": "in",  "balance": 10200.00},
        {"server_ts": 1731482800, "direction": "out", "balance": 10330.00},
        {"server_ts": 1731647307, "direction": "in",  "balance": 10328.97},  # Day 4 open #1
        {"server_ts": 1731692005, "direction": "in",  "balance": 10328.57},  # Day 4 open #2 (open_positions=2)
        {"server_ts": 1731693600, "direction": "out", "balance": 10504.77},  # 18:00 close #1 -> open_positions=1 (MUST NOT PASS!)
        {"server_ts": 1731711300, "direction": "out", "balance": 10593.54},  # 22:55 close #2 -> open_positions=0 (PASS!)
    ]
    res = s71._compute_phase_target_pass(deals, 10500.0)
    assert res["passed"] is True
    assert res["deal_idx"] == 9
    assert res["open_positions"] == 0
    assert res["balance_usd"] == 10593.54
    assert res["iso_server"] == "2024-11-15 22:55:00"
    assert res["earlier_nonflat_target_crossing_ignored"]["deal_idx"] == 8
    assert res["earlier_nonflat_target_crossing_ignored"]["open_positions"] == 1

    # If the last position never closes, phase MUST NOT pass!
    res_still_open = s71._compute_phase_target_pass(deals[:-1], 10500.0)
    assert res_still_open["passed"] is False
    assert res_still_open["final_open_positions"] == 1

