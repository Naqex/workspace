"""Unit & integration tests for `ftmo_demo_calibration_probe.py` (100% mocked MT5, ZERO terminal launch).

Covers ALL 6 fail-closed safety locks, adverse slippage sign conventions (BUY & SELL, entry,
time exit, real SL hit), `--dry-run` default (`OrderSend = 0`), `--execute-demo-1515343318-calibration`
live demo lifecycle, 5s spread JSONL schema compatibility with `prop_challenge_tracker.py`,
session tagging (`ASIA / LONDON / NY_OVERLAP / NY_AFTERNOON`), and `--summarize` Realized
Friction Multiplier & Dev M1 (`< 2025-01-01`, `holdout_rows_analysed = 0`) comparison.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
EXPORTS_DIR = AI_ENGINES / "exports"
for _p in (AI_ENGINES, EXPORTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ftmo_demo_calibration_probe as probe  # noqa: E402
from quant_factory import prop_challenge_tracker as pct  # noqa: E402


# ---------------------------------------------------------------------------
# Deterministic Mock MetaTrader5 SDK (ZERO real MT5 calls!)
# ---------------------------------------------------------------------------
class MockClock:
    def __init__(self, start_utc: datetime) -> None:
        self.now = start_utc

    def __call__(self) -> datetime:
        return self.now

    def sleep(self, sec: float) -> None:
        self.now = self.now + timedelta(seconds=float(sec))


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_CONTEST = 1
    ACCOUNT_TRADE_MODE_REAL = 2
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    TRADE_RETCODE_DONE = 10009
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1
    DEAL_REASON_SL = 4

    def __init__(
        self,
        *,
        login: int = 1515343318,
        server: str = "FTMO-Demo",
        trade_mode: int = 0,
        data_path: str | None = None,
        slip_pts_by_side: dict[str, float] | None = None,
        trigger_sl_on_trade_seq: set[int] | None = None,
        initial_positions: list[Any] | None = None,
        positions_returns_none: bool = False,
    ) -> None:
        self.login = login
        self.server = server
        self.trade_mode = trade_mode
        self.data_path = data_path or str(ROOT / ".runtime/ftmo-demo-portable-1515343318")
        self.slip_pts_by_side = slip_pts_by_side or {"BUY": 1.0, "SELL": 1.0}
        self.trigger_sl_on_trade_seq = trigger_sl_on_trade_seq or set()
        self.positions: list[Any] = list(initial_positions or [])
        self.positions_returns_none = positions_returns_none
        self.deals: list[Any] = []
        self.order_send_calls: list[dict[str, Any]] = []
        self.initialized = False
        self.shutdown_called = False
        self._next_ticket = 500001
        self._open_count = 0

        self.quotes: dict[str, dict[str, Any]] = {
            "USDJPY": {"bid": 155.000, "ask": 155.006, "point": 0.001, "digits": 3, "spread": 6, "filling_mode": 3, "trade_stops_level": 0},
            "GBPUSD": {"bid": 1.30000, "ask": 1.30007, "point": 0.00001, "digits": 5, "spread": 7, "filling_mode": 3, "trade_stops_level": 0},
            "EURJPY": {"bid": 168.000, "ask": 168.010, "point": 0.001, "digits": 3, "spread": 10, "filling_mode": 3, "trade_stops_level": 0},
            "US100.cash": {"bid": 21000.00, "ask": 21001.45, "point": 0.01, "digits": 2, "spread": 145, "filling_mode": 3, "trade_stops_level": 0},
        }

    def initialize(self, path=None, login=None, password=None, server=None, portable=True, timeout=30000) -> bool:
        self.initialized = True
        return True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def last_error(self):
        return (0, "OK")

    def account_info(self):
        return SimpleNamespace(
            login=self.login,
            server=self.server,
            trade_mode=self.trade_mode,
            currency="USD",
            balance=10000.0,
            equity=10000.0,
            profit=0.0,
            margin=0.0,
            margin_free=10000.0,
            leverage=30,
            trade_allowed=True,
            trade_expert=True,
        )

    def terminal_info(self):
        return SimpleNamespace(
            connected=True,
            trade_allowed=True,
            tradeapi_disabled=False,
            build=6230,
            data_path=self.data_path,
            path=self.data_path,
        )

    def symbol_select(self, sym: str, enable: bool) -> bool:
        return sym in self.quotes

    def symbol_info(self, sym: str):
        q = self.quotes.get(sym)
        if not q:
            return None
        return SimpleNamespace(**q)

    def symbol_info_tick(self, sym: str):
        q = self.quotes.get(sym)
        if not q:
            return None
        return SimpleNamespace(bid=q["bid"], ask=q["ask"], time=1795520000)

    def positions_get(self, symbol: str | None = None, ticket: int | None = None):
        if self.positions_returns_none:
            return None
        # Optionally simulate broker SL hit on next poll for configured trade sequences
        if self.positions and self._open_count in self.trigger_sl_on_trade_seq:
            pos = self.positions.pop(0)
            q = self.quotes[pos.symbol]
            pt = q["point"]
            # Adverse fill past SL by 2 broker points
            sl_fill = (pos.sl - 2.0 * pt) if pos.type == 0 else (pos.sl + 2.0 * pt)
            sl_fill = round(sl_fill, q["digits"])
            deal_tk = self._next_ticket
            self._next_ticket += 1
            comm = 0.0 if pos.symbol == "US100.cash" else -0.025
            self.deals.append(
                SimpleNamespace(
                    ticket=deal_tk,
                    order=deal_tk + 1000,
                    position_id=pos.ticket,
                    symbol=pos.symbol,
                    entry=self.DEAL_ENTRY_OUT,
                    reason=self.DEAL_REASON_SL,
                    price=sl_fill,
                    commission=comm,
                    fee=0.0,
                    swap=0.0,
                    profit=-1.20,
                )
            )
            return []
        res = list(self.positions)
        if symbol is not None:
            res = [p for p in res if p.symbol == symbol]
        if ticket is not None:
            res = [p for p in res if p.ticket == ticket]
        return res

    def history_deals_get(self, ticket: int | None = None, position: int | None = None):
        if ticket is not None:
            return [d for d in self.deals if d.ticket == ticket]
        if position is not None:
            return [d for d in self.deals if d.position_id == position]
        return list(self.deals)

    def order_send(self, req: dict[str, Any]):
        self.order_send_calls.append(dict(req))
        sym = req["symbol"]
        q = self.quotes[sym]
        pt = q["point"]
        is_buy = int(req["type"]) == self.ORDER_TYPE_BUY
        slip_pts = float(self.slip_pts_by_side["BUY" if is_buy else "SELL"])
        # Adverse fill: BUY fills higher, SELL fills lower
        fill_px = (req["price"] + slip_pts * pt) if is_buy else (req["price"] - slip_pts * pt)
        fill_px = round(fill_px, q["digits"])

        deal_tk = self._next_ticket
        self._next_ticket += 1
        comm = 0.0 if sym == "US100.cash" else -0.025  # $2.50/lot per side = $0.025 for 0.01 lot

        if "position" in req:
            pos_id = int(req["position"])
            self.positions = [p for p in self.positions if p.ticket != pos_id]
            self.deals.append(
                SimpleNamespace(
                    ticket=deal_tk,
                    order=deal_tk + 1000,
                    position_id=pos_id,
                    symbol=sym,
                    entry=self.DEAL_ENTRY_OUT,
                    reason=0,
                    price=fill_px,
                    commission=comm,
                    fee=0.0,
                    swap=0.0,
                    profit=0.15,
                )
            )
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, deal=deal_tk, order=deal_tk + 1000, price=fill_px, comment="OK")

        # Entry fill
        self._open_count += 1
        pos_id = deal_tk
        self.positions.append(
            SimpleNamespace(
                ticket=pos_id,
                symbol=sym,
                magic=int(req["magic"]),
                type=0 if is_buy else 1,
                volume=float(req["volume"]),
                price_open=fill_px,
                sl=float(req["sl"]),
                tp=float(req.get("tp", 0.0)),
                profit=0.0,
                swap=0.0,
            )
        )
        self.deals.append(
            SimpleNamespace(
                ticket=deal_tk,
                order=deal_tk + 1000,
                position_id=pos_id,
                symbol=sym,
                entry=self.DEAL_ENTRY_IN,
                reason=0,
                price=fill_px,
                commission=comm,
                fee=0.0,
                swap=0.0,
                profit=0.0,
            )
        )
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, deal=deal_tk, order=deal_tk + 1000, price=fill_px, comment="OK")


def _write_env(path: Path, *, login: str = "1515343318", password: str = "SuperSecretDemoPass!99", server: str = "FTMO-Demo", term: Path | None = None) -> Path:
    t = term or (path.parent / "src_mt5/terminal64.exe")
    t.parent.mkdir(parents=True, exist_ok=True)
    if not t.exists():
        t.write_bytes(b"FAKE_BIN")
    path.write_text(
        f"FTMO_MT5_LOGIN={login}\n"
        f"FTMO_MT5_PASSWORD={password}\n"
        f"FTMO_MT5_SERVER={server}\n"
        f"FTMO_MT5_TERMINAL_PATH={t}\n",
        encoding="utf-8",
    )
    return path


def _write_news(path: Path, rows: list[tuple[int, str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc_ts", "ccy", "event"])
        for ts, ccy, ev in rows:
            w.writerow([ts, ccy, ev])
    return path


def _synthetic_dev_baselines() -> dict[str, Any]:
    return {
        "holdout_lock_sha256": probe.EXPECTED_HOLDOUT_LOCK_SHA,
        "holdout_rows_analysed": 0,
        "dev_m1_max_utc": "2024-12-31T23:59:00+00:00",
        "by_symbol": {
            "USDJPY": {
                "cache_asset": "USDJPY",
                "dev_rows": 2600000,
                "dev_median_mid": 130.0,
                "sessions": {s: {"rows": 500000, "median_spread_px": 0.004, "median_spread_pts": 4.0, "p90_spread_pts": 8.0, "median_spread_bps": 0.34, "p90_spread_bps": 0.68} for s in (*probe.SESSION_ORDER, "OVERALL")},
                "dev_1x_budget": {"spread_rt_bps": 0.34, "commission_rt_bps": 0.50, "base_slip_rt_bps": 0.31, "stress_slip_rt_bps": 0.69, "total_1x_rt_bps": 1.15, "total_stress_rt_bps": 1.53, "tracker_budget_rt_bps": 2.60},
            },
            "GBPUSD": {
                "cache_asset": "GBPUSD",
                "dev_rows": 2600000,
                "dev_median_mid": 1.27,
                "sessions": {s: {"rows": 500000, "median_spread_px": 0.00009, "median_spread_pts": 9.0, "p90_spread_pts": 15.0, "median_spread_bps": 0.71, "p90_spread_bps": 1.18} for s in (*probe.SESSION_ORDER, "OVERALL")},
                "dev_1x_budget": {"spread_rt_bps": 0.71, "commission_rt_bps": 0.39, "base_slip_rt_bps": 0.31, "stress_slip_rt_bps": 0.71, "total_1x_rt_bps": 1.41, "total_stress_rt_bps": 1.81, "tracker_budget_rt_bps": 3.00},
            },
            "EURJPY": {
                "cache_asset": "EURJPY",
                "dev_rows": 2600000,
                "dev_median_mid": 140.0,
                "sessions": {s: {"rows": 500000, "median_spread_px": 0.007, "median_spread_pts": 7.0, "p90_spread_pts": 12.0, "median_spread_bps": 0.56, "p90_spread_bps": 0.96} for s in (*probe.SESSION_ORDER, "OVERALL")},
                "dev_1x_budget": {"spread_rt_bps": 0.56, "commission_rt_bps": 0.46, "base_slip_rt_bps": 0.29, "stress_slip_rt_bps": 0.64, "total_1x_rt_bps": 1.31, "total_stress_rt_bps": 1.66, "tracker_budget_rt_bps": 3.00},
            },
            "US100.cash": {
                "cache_asset": "US100",
                "dev_rows": 2350000,
                "dev_median_mid": 14000.0,
                "sessions": {s: {"rows": 400000, "median_spread_px": 3.07, "median_spread_pts": 307.0, "p90_spread_pts": 500.0, "median_spread_bps": 2.20, "p90_spread_bps": 3.50} for s in (*probe.SESSION_ORDER, "OVERALL")},
                "dev_1x_budget": {"spread_rt_bps": 2.20, "commission_rt_bps": 0.00, "base_slip_rt_bps": 1.43, "stress_slip_rt_bps": 2.86, "total_1x_rt_bps": 3.63, "total_stress_rt_bps": 5.06, "tracker_budget_rt_bps": 4.50},
            },
        },
    }


# ---------------------------------------------------------------------------
# Tests: Lock 1 (Env Credentials & Password Redaction)
# ---------------------------------------------------------------------------
def test_lock1_credentials_loader_and_password_redaction(tmp_path: Path) -> None:
    secret = "TopSecretFtmoTrialPassword#2026"
    env_ok = _write_env(tmp_path / "ok.env", login="1515343318", password=secret, server="FTMO-Demo")
    creds = probe.load_ftmo_trial_env(env_ok)
    assert creds.login == 1515343318
    assert creds.server == "FTMO-Demo"
    assert creds.secret_password() == secret
    # Password MUST NEVER appear in repr, str, or safe dict
    assert secret not in repr(creds)
    assert secret not in str(creds)
    assert secret not in json.dumps(creds.to_safe_dict())

    # Rejects primary demo 1515343166
    env_166 = _write_env(tmp_path / "bad166.env", login="1515343166", password=secret, server="FTMO-Demo")
    with pytest.raises(probe.SafetyLockError, match="LOCK_1_FORBIDDEN_LOGIN"):
        probe.load_ftmo_trial_env(env_166)

    # Rejects wrong server
    env_srv = _write_env(tmp_path / "badsrv.env", login="1515343318", password=secret, server="Exness-Real")
    with pytest.raises(probe.SafetyLockError, match="LOCK_1_UNEXPECTED_SERVER"):
        probe.load_ftmo_trial_env(env_srv)

    # Rejects missing password
    env_nopw = _write_env(tmp_path / "nopw.env", login="1515343318", password="", server="FTMO-Demo")
    with pytest.raises(probe.SafetyLockError, match="LOCK_1_MISSING_REQUIRED_KEY"):
        probe.load_ftmo_trial_env(env_nopw)


# ---------------------------------------------------------------------------
# Tests: Lock 2 (Demo Mode, Exact Login 1515343318, Server, Path & Concurrency)
# ---------------------------------------------------------------------------
def test_lock2_rejects_non_demo_primary_login_wrong_server_and_paths() -> None:
    # Rejects Real account (trade_mode=2) and Contest (trade_mode=1)
    for bad_mode in (FakeMT5.ACCOUNT_TRADE_MODE_REAL, FakeMT5.ACCOUNT_TRADE_MODE_CONTEST):
        acc = FakeMT5(login=1515343318, server="FTMO-Demo", trade_mode=bad_mode).account_info()
        with pytest.raises(probe.SafetyLockError, match="LOCK_2_NOT_DEMO_ACCOUNT"):
            probe.validate_calibration_account(acc, demo_trade_mode=0)

    # Rejects login 1515343166 (NEVER touch primary Free Trial Demo!)
    acc_166 = FakeMT5(login=1515343166, server="FTMO-Demo", trade_mode=0).account_info()
    with pytest.raises(probe.SafetyLockError, match="LOCK_2_FORBIDDEN_PRIMARY_DEMO_LOGIN"):
        probe.validate_calibration_account(acc_166, demo_trade_mode=0)

    # Rejects arbitrary other login
    acc_other = FakeMT5(login=999999999, server="FTMO-Demo", trade_mode=0).account_info()
    with pytest.raises(probe.SafetyLockError, match="LOCK_2_UNEXPECTED_LOGIN"):
        probe.validate_calibration_account(acc_other, demo_trade_mode=0)

    # Rejects non-FTMO-Demo server
    acc_srv = FakeMT5(login=1515343318, server="FTMO-Server3", trade_mode=0).account_info()
    with pytest.raises(probe.SafetyLockError, match="LOCK_2_UNEXPECTED_SERVER"):
        probe.validate_calibration_account(acc_srv, demo_trade_mode=0)

    # Rejects forbidden Exness & 1515343166 terminal paths
    for bad_path in (
        Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"),
        Path.home() / "AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075",
        ROOT / ".runtime/ftmo-demo-portable-1515343166",
    ):
        with pytest.raises(probe.SafetyLockError, match="LOCK_2_FORBIDDEN_TERMINAL_PATH"):
            probe.assert_safe_portable_path(bad_path)

    # Rejects launching when another terminal64.exe is already running
    with pytest.raises(probe.SafetyLockError, match="LOCK_2_CONCURRENT_TERMINAL64_RUNNING"):
        probe.assert_no_concurrent_mt5(process_lister=lambda: ['"terminal64.exe","12345","Console","1","250,000 K"'])


# ---------------------------------------------------------------------------
# Tests: Lock 3 (Volume == 0.01, Max 1 Open Pos, Max 28 Total, Mandatory SL)
# ---------------------------------------------------------------------------
def test_lock3_volume_concurrency_trade_cap_and_mandatory_sl() -> None:
    mt5 = FakeMT5()
    now = datetime(2026, 11, 25, 10, 0, 0, tzinfo=timezone.utc)
    far_news = [{"utc_ts": int(now.timestamp()) + 86_400, "ccy": "USD", "event": "US_NFP"}]

    # Rejects any volume != 0.01
    for bad_vol in (0.0, -0.01, 0.02, 0.10, 1.0, float("nan")):
        with pytest.raises(probe.SafetyLockError, match="LOCK_3_VOLUME_LOCK_BREACH"):
            probe.validate_fixed_volume(bad_vol)

    # Blocks 2nd concurrent open position
    existing_pos = [SimpleNamespace(ticket=1, symbol="USDJPY", magic=probe.PROBE_MAGIC, type=0, volume=0.01, sl=154.8)]
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_MAX_OPEN_POSITIONS_BREACH"):
        probe.assert_all_entry_locks(
            acc=mt5.account_info(),
            demo_trade_mode=0,
            symbol="GBPUSD",
            side="BUY",
            volume=0.01,
            entry_price=1.30007,
            sl_price=1.29807,
            point=0.00001,
            stops_level_pts=0,
            open_positions=existing_pos,
            total_trades_opened=1,
            per_symbol_counts={"USDJPY": 1},
            now_utc=now,
            hold_sec=180,
            news_events=far_news,
        )

    # Fail-closed when positions_get() returns None
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_POSITIONS_GET_RETURNED_NONE"):
        probe.assert_all_entry_locks(
            acc=mt5.account_info(),
            demo_trade_mode=0,
            symbol="GBPUSD",
            side="BUY",
            volume=0.01,
            entry_price=1.30007,
            sl_price=1.29807,
            point=0.00001,
            stops_level_pts=0,
            open_positions=None,
            total_trades_opened=0,
            per_symbol_counts={},
            now_utc=now,
            hold_sec=180,
            news_events=far_news,
        )

    # Blocks trade #29 (max_total_trades == 28) and 8th trade on same symbol
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_MAX_TOTAL_TRADES_REACHED"):
        probe.assert_all_entry_locks(
            acc=mt5.account_info(), demo_trade_mode=0, symbol="USDJPY", side="BUY", volume=0.01,
            entry_price=155.006, sl_price=154.806, point=0.001, stops_level_pts=0, open_positions=[],
            total_trades_opened=28, per_symbol_counts={"USDJPY": 6}, now_utc=now, hold_sec=180, news_events=far_news,
        )
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_MAX_SYMBOL_TRADES_REACHED"):
        probe.assert_all_entry_locks(
            acc=mt5.account_info(), demo_trade_mode=0, symbol="USDJPY", side="BUY", volume=0.01,
            entry_price=155.006, sl_price=154.806, point=0.001, stops_level_pts=0, open_positions=[],
            total_trades_opened=10, per_symbol_counts={"USDJPY": 7}, now_utc=now, hold_sec=180, news_events=far_news,
        )

    # Mandatory hard SL checks: missing/0, wrong side, out of calibration range
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_MISSING_OR_ZERO_SL"):
        probe.validate_mandatory_sl(symbol="USDJPY", side="BUY", entry_price=155.006, sl_price=0.0, point=0.001)
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_WRONG_SIDE_SL"):
        probe.validate_mandatory_sl(symbol="USDJPY", side="BUY", entry_price=155.006, sl_price=155.206, point=0.001)
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_SL_OUT_OF_CALIBRATION_BAND"):
        probe.validate_mandatory_sl(symbol="US100.cash", side="SELL", entry_price=21000.0, sl_price=21005.0, point=0.01)

    # Valid FX 20 pips & US100 60 index pts PASS
    assert probe.validate_mandatory_sl(symbol="USDJPY", side="BUY", entry_price=155.006, sl_price=154.806, point=0.001) == 154.806
    assert probe.validate_mandatory_sl(symbol="US100.cash", side="SELL", entry_price=21000.0, sl_price=21060.0, point=0.01) == 21060.0

    # Schedule invariant check: 28 trades = 7 x 4 core symbols, 14 BUY + 14 SELL, hold 180-360s, gap 120-180s
    sched = probe.build_calibration_schedule()
    assert len(sched) == 28
    assert sum(1 for x in sched if x.side == "BUY") == 14
    assert sum(1 for x in sched if x.side == "SELL") == 14
    for sym in probe.CORE_SYMBOLS:
        assert sum(1 for x in sched if x.symbol == sym) == 7
    assert all(180 <= x.hold_sec <= 360 and 120 <= x.gap_sec <= 180 and x.volume == 0.01 for x in sched)


# ---------------------------------------------------------------------------
# Tests: Lock 4 (Red-News +-300s Calendar, Real 492-row CSV)
# ---------------------------------------------------------------------------
def test_lock4_red_news_blocking_and_real_492_row_csv() -> None:
    real_events = probe.load_red_news_calendar(probe.DEFAULT_NEWS_CSV)
    assert len(real_events) == 492

    t0 = 1795520000
    events = [
        {"utc_ts": t0, "ccy": "USD", "event": "US_CPI"},
        {"utc_ts": t0 + 7200, "ccy": "EUR", "event": "ECB_RATE"},
    ]

    # Exact +-300s boundaries block USD pairs (USDJPY, GBPUSD, US100.cash), NOT EURJPY!
    for delta in (-300, -120, 0, 120, 300):
        assert probe.find_blocking_red_news("USDJPY", t0 + delta, events) is not None
        assert probe.find_blocking_red_news("GBPUSD", t0 + delta, events) is not None
        assert probe.find_blocking_red_news("US100.cash", t0 + delta, events) is not None
        assert probe.find_blocking_red_news("EURJPY", t0 + delta, events) is None

    # Outside +-300s without hold overlap is clear
    assert probe.find_blocking_red_news("USDJPY", t0 + 301, events, hold_lookahead_sec=0) is None
    # Approaching event within hold_lookahead + 300s IS blocked so open trade never sits through news
    assert probe.find_blocking_red_news("USDJPY", t0 - 450, events, hold_lookahead_sec=240) is not None
    # EUR event blocks EURJPY only
    assert probe.find_blocking_red_news("EURJPY", t0 + 7200, events) is not None
    assert probe.find_blocking_red_news("GBPUSD", t0 + 7200, events) is None


# ---------------------------------------------------------------------------
# Tests: Lock 5 (Hard-Flatten & Stop Entries Before 20:55 UTC)
# ---------------------------------------------------------------------------
def test_lock5_hard_flatten_before_2055_utc(tmp_path: Path) -> None:
    assert probe.is_past_flatten_cutoff(datetime(2026, 11, 25, 20, 54, 0, tzinfo=timezone.utc)) is False
    assert probe.is_past_flatten_cutoff(datetime(2026, 11, 25, 20, 55, 0, tzinfo=timezone.utc)) is True
    assert probe.is_past_flatten_cutoff(datetime(2026, 11, 25, 21, 30, 0, tzinfo=timezone.utc)) is True
    # Entry at 20:52 UTC with 240s hold would cross 20:55 UTC -> blocked!
    assert probe.is_past_flatten_cutoff(datetime(2026, 11, 25, 20, 52, 0, tzinfo=timezone.utc), hold_lookahead_sec=240) is True

    # Live hold test: trade enters at 20:51 UTC with 180s hold (ends 20:54 < 20:55),
    # then a second trade cannot enter at 20:55+ UTC; also test active position flattening at 20:55 UTC!
    clock = MockClock(datetime(2026, 11, 25, 20, 51, 30, tzinfo=timezone.utc))
    mt5 = FakeMT5()
    far_news = [{"utc_ts": int(clock.now.timestamp()) + 86_400, "ccy": "USD", "event": "US_NFP"}]
    fills_csv = tmp_path / "fills.csv"
    spread_log = tmp_path / "spreads.jsonl"

    # Trade 1 enters at 20:51:30 with 180s hold (20:54:30) and 120s gap (crosses 20:55 UTC) -> Trade 2 MUST NOT open!
    sched = [
        probe.PlannedCalibrationTrade(seq=1, symbol="USDJPY", side="BUY", volume=0.01, sl_units=20.0, hold_sec=180, gap_sec=120),
        probe.PlannedCalibrationTrade(seq=2, symbol="GBPUSD", side="SELL", volume=0.01, sl_units=20.0, hold_sec=180, gap_sec=120),
    ]
    runner = probe.CalibrationProbeRunner(
        mt5=mt5,
        execute_live=True,
        news_events=far_news,
        spread_log_path=spread_log,
        fills_csv_path=fills_csv,
        sample_interval_sec=30,
        max_trades=2,
        clock_fn=clock,
        sleep_fn=clock.sleep,
    )
    res = runner.run_calibration(schedule=sched)
    assert res["live_entries_filled"] == 1
    assert res["live_exits_filled"] == 1
    assert res["blocked_cutoff_count"] >= 1
    assert len(mt5.positions) == 0


# ---------------------------------------------------------------------------
# Tests: Adverse Slippage Sign Convention (BUY & SELL)
# ---------------------------------------------------------------------------
def test_adverse_slippage_sign_for_buy_and_sell() -> None:
    # BUY: fill > expected_ask -> POSITIVE adverse slippage
    pts_b, bps_b = probe.compute_adverse_slippage(deal_side="BUY", expected_price=155.000, fill_price=155.015, point=0.001)
    assert pts_b == pytest.approx(15.0)
    assert bps_b > 0.0

    # BUY: fill < expected_ask -> NEGATIVE (favorable price improvement)
    pts_bi, bps_bi = probe.compute_adverse_slippage(deal_side="BUY", expected_price=155.000, fill_price=154.995, point=0.001)
    assert pts_bi == pytest.approx(-5.0)
    assert bps_bi < 0.0

    # SELL: fill < expected_bid -> POSITIVE adverse slippage
    pts_s, bps_s = probe.compute_adverse_slippage(deal_side="SELL", expected_price=1.30000, fill_price=1.29980, point=0.00001)
    assert pts_s == pytest.approx(20.0)
    assert bps_s > 0.0

    # SELL: fill > expected_bid -> NEGATIVE (favorable price improvement)
    pts_si, bps_si = probe.compute_adverse_slippage(deal_side="SELL", expected_price=1.30000, fill_price=1.30010, point=0.00001)
    assert pts_si == pytest.approx(-10.0)
    assert bps_si < 0.0


# ---------------------------------------------------------------------------
# Tests: Lock 6 (`--dry-run` sends 0 orders) & Live Execution + SL_HIT + Spread Schema
# ---------------------------------------------------------------------------
def test_lock6_dry_run_default_sends_zero_orders_and_spread_schema_matches_tracker(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / "trial.env")
    news_csv = _write_news(tmp_path / "news.csv", [(1795600000, "USD", "NFP")])
    spread_log = tmp_path / "spreads.jsonl"
    fills_csv = tmp_path / "fills.csv"
    portable_dir = tmp_path / "portable-1515343318"
    clock = MockClock(datetime(2026, 11, 25, 9, 30, 0, tzinfo=timezone.utc))
    mt5 = FakeMT5(data_path=str(portable_dir))

    # Default CLI invocation (NO --execute-demo-1515343318-calibration flag!) MUST be dry-run with OrderSend == 0!
    rc = probe.main(
        [
            "--env-file", str(env_file),
            "--news-csv", str(news_csv),
            "--spread-log", str(spread_log),
            "--fills-csv", str(fills_csv),
            "--portable-dir", str(portable_dir),
            "--max-trades", "4",
        ],
        mt5_mod=mt5,
        process_lister=lambda: [],
        clock_fn=clock,
        sleep_fn=clock.sleep,
    )
    assert rc == 0
    assert len(mt5.order_send_calls) == 0, "Default CLI MUST send 0 orders!"
    assert mt5.shutdown_called is True

    # Spread JSONL MUST parse cleanly with prop_challenge_tracker.py & match expected schema!
    rows = pct.load_spread_log_rows(spread_log)
    assert len(rows) >= 5  # initial + 4 dry-run cycles
    for row in rows:
        assert row["schema"] == "naqex-mt5-live-telemetry-v1"
        assert row["order_send_count"] == 0
        assert row["session"] in probe.SESSION_ORDER
        assert row["account"]["login"] == 1515343318
        assert row["account"]["server"] == "FTMO-Demo"
        assert row["account"]["trade_mode"] == "ACCOUNT_TRADE_MODE_DEMO"
        assert set(row["quotes"].keys()) == set(probe.CORE_SYMBOLS)
        for sym in probe.CORE_SYMBOLS:
            q = row["quotes"][sym]
            assert q["available"] is True
            assert q["ask"] > q["bid"] > 0.0
            assert q["spread_pts"] > 0.0 and q["spread_bps"] > 0.0

    # prop_challenge_tracker.evaluate_prop_challenge ingests the spread log cleanly
    tracker_res = pct.evaluate_prop_challenge(
        profile_id="ftmo_swing_10k",
        exec_audit_csv=tmp_path / "missing_audit.csv",
        spread_log_jsonl=spread_log,
        news_csv=news_csv,
        heartbeat_json=tmp_path / "missing_hb.json",
    )
    assert tracker_res["summary"]["spread_log_rows"] == len(rows)

    # Session tagging checks across all 4 sessions
    assert probe.tag_session_utc(datetime(2026, 11, 25, 2, 0, tzinfo=timezone.utc)) == "ASIA"
    assert probe.tag_session_utc(datetime(2026, 11, 25, 22, 30, tzinfo=timezone.utc)) == "ASIA"
    assert probe.tag_session_utc(datetime(2026, 11, 25, 9, 15, tzinfo=timezone.utc)) == "LONDON"
    assert probe.tag_session_utc(datetime(2026, 11, 25, 14, 0, tzinfo=timezone.utc)) == "NY_OVERLAP"
    assert probe.tag_session_utc(datetime(2026, 11, 25, 18, 45, tzinfo=timezone.utc)) == "NY_AFTERNOON"


def test_explicit_execute_flag_and_summarize_realized_friction_multiplier(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / "trial.env")
    news_csv = _write_news(tmp_path / "news.csv", [(1795600000, "USD", "NFP")])
    spread_log = tmp_path / "spreads.jsonl"
    fills_csv = tmp_path / "fills.csv"
    summary_json = tmp_path / "friction_summary.json"
    portable_dir = tmp_path / "portable-1515343318"
    clock = MockClock(datetime(2026, 11, 25, 13, 0, 0, tzinfo=timezone.utc))  # NY_OVERLAP

    # Simulate 4 core trades (1 per symbol): trade #2 (GBPUSD SELL) triggers real broker SL_HIT!
    mt5 = FakeMT5(
        data_path=str(portable_dir),
        slip_pts_by_side={"BUY": 1.5, "SELL": 1.5},
        trigger_sl_on_trade_seq={2},
    )
    rc = probe.main(
        [
            "--execute-demo-1515343318-calibration",
            "--env-file", str(env_file),
            "--news-csv", str(news_csv),
            "--spread-log", str(spread_log),
            "--fills-csv", str(fills_csv),
            "--portable-dir", str(portable_dir),
            "--sample-interval-sec", "60",
            "--max-trades", "4",
        ],
        mt5_mod=mt5,
        process_lister=lambda: [],
        clock_fn=clock,
        sleep_fn=clock.sleep,
    )
    assert rc == 0
    assert len(mt5.positions) == 0
    # 4 entries + 3 time exits (trade #2 exited by broker SL_HIT) = 7 order_send calls, ALL 0.01 lot
    assert len(mt5.order_send_calls) == 7
    assert all(abs(c["volume"] - 0.01) < 1e-9 for c in mt5.order_send_calls)

    # Summarize offline using synthetic baselines (also verify real hot-m1-cache holdout=0 below!)
    summary = probe.summarize_calibration_and_spreads(
        spread_log_path=spread_log,
        fills_csv_path=fills_csv,
        summary_json_path=summary_json,
        dev_m1_baselines=_synthetic_dev_baselines(),
    )
    assert summary_json.is_file()
    assert summary["order_send_count"] == 0
    assert summary["holdout_rows_analysed"] == 0
    assert summary["compliance"]["zero_swap_ok"] is True
    assert summary["compliance"]["cutoff_ok"] is True
    assert summary["portfolio_core4"]["symbols_with_live_fills"] == 4
    assert summary["portfolio_core4"]["realized_friction_multiplier_p50"] > 0.0
    assert summary["portfolio_core4"]["realized_friction_multiplier_p90"] >= summary["portfolio_core4"]["realized_friction_multiplier_p50"]

    # GBPUSD recorded 1 real SL_HIT exit with positive adverse slippage!
    gbp_rf = summary["realized_friction_by_symbol"]["GBPUSD"]
    assert gbp_rf["sl_exits"] == 1
    assert gbp_rf["sl_adverse_slip_p50_bps"] > 0.0
    assert gbp_rf["commission_rt_p50_bps"] > 0.0

    # US100.cash has 0 commission & live spread ratio < 1.0 vs Dev M1
    us100_sp = summary["spread_vs_dev_m1"]["US100.cash"]["NY_OVERLAP"]
    assert us100_sp["live_samples"] > 0
    assert us100_sp["live_to_dev_spread_ratio_bps"] < 1.0


@pytest.mark.local_cache
def test_real_hot_m1_cache_baselines_enforce_zero_holdout() -> None:
    """Verify real `.runtime/hot-m1-cache` baseline loader reads strictly < 2025-01-01 (`holdout_rows_analysed == 0`)."""
    if not (probe.DEFAULT_HOT_M1_CACHE / "manifest.json").is_file():
        pytest.skip("Local .runtime/hot-m1-cache not present")
    base = probe.compute_dev_m1_spread_baselines(verify_sha=False)
    assert base["holdout_rows_analysed"] == 0
    assert base["holdout_lock_sha256"] == probe.EXPECTED_HOLDOUT_LOCK_SHA
    assert base["dev_m1_max_utc"] is not None and base["dev_m1_max_utc"] < "2025-01-01"
    for sym in probe.CORE_SYMBOLS:
        s_ov = base["by_symbol"][sym]["sessions"]["OVERALL"]
        assert s_ov["rows"] > 2_000_000
        assert s_ov["median_spread_bps"] > 0.0
        assert base["by_symbol"][sym]["dev_1x_budget"]["total_1x_rt_bps"] > s_ov["median_spread_bps"]


def test_cli_hard_guards_spread_only_midhold_flatten_and_resume_cap(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path / "trial.env")
    news_csv = _write_news(tmp_path / "news.csv", [(1795600000, "USD", "NFP")])
    spread_log = tmp_path / "spreads.jsonl"
    fills_csv = tmp_path / "fills.csv"
    portable_dir = tmp_path / "portable-1515343318"

    # 1. Mutually exclusive CLI flags (--dry-run + --execute-demo-1515343318-calibration) rejected!
    with pytest.raises(SystemExit) as exc_info:
        probe.main(["--dry-run", "--execute-demo-1515343318-calibration"])
    assert exc_info.value.code == 2

    # 2. --max-trades > 28 rejected fail-closed!
    with pytest.raises(probe.SafetyLockError, match="LOCK_3_INVALID_MAX_TRADES"):
        probe.main(["--max-trades", "29"])

    # 3. --spread-only logs exact samples with OrderSend == 0
    clock = MockClock(datetime(2026, 11, 25, 11, 0, 0, tzinfo=timezone.utc))
    mt5 = FakeMT5(data_path=str(portable_dir))
    rc = probe.main(
        [
            "--spread-only",
            "--max-samples", "3",
            "--sample-interval-sec", "5",
            "--env-file", str(env_file),
            "--news-csv", str(news_csv),
            "--spread-log", str(spread_log),
            "--portable-dir", str(portable_dir),
        ],
        mt5_mod=mt5,
        process_lister=lambda: [],
        clock_fn=clock,
        sleep_fn=clock.sleep,
    )
    assert rc == 0
    assert len(mt5.order_send_calls) == 0
    assert len(pct.load_spread_log_rows(spread_log)) == 3

    # 4. Mid-hold pre-flatten when clock hits 20:55 UTC (e.g. if clock jumps during hold)
    class JumpClock:
        def __init__(self) -> None:
            self.calls = 0
            self.t = datetime(2026, 11, 25, 20, 48, 0, tzinfo=timezone.utc)

        def __call__(self) -> datetime:
            return self.t

        def sleep(self, sec: float) -> None:
            self.calls += 1
            if self.calls == 1:
                # Jump to 20:55:00 UTC while holding position!
                self.t = datetime(2026, 11, 25, 20, 55, 0, tzinfo=timezone.utc)
            else:
                self.t += timedelta(seconds=sec)

    jc = JumpClock()
    mt5_jump = FakeMT5(data_path=str(portable_dir))
    far_news = [{"utc_ts": int(jc.t.timestamp()) + 86_400, "ccy": "USD", "event": "NFP"}]
    runner_j = probe.CalibrationProbeRunner(
        mt5=mt5_jump,
        execute_live=True,
        news_events=far_news,
        spread_log_path=tmp_path / "sp_jump.jsonl",
        fills_csv_path=tmp_path / "fills_jump.csv",
        sample_interval_sec=30,
        max_trades=2,
        clock_fn=jc,
        sleep_fn=jc.sleep,
    )
    res_j = runner_j.run_calibration(
        schedule=[
            probe.PlannedCalibrationTrade(seq=1, symbol="USDJPY", side="BUY", volume=0.01, sl_units=20.0, hold_sec=180, gap_sec=120),
            probe.PlannedCalibrationTrade(seq=2, symbol="GBPUSD", side="SELL", volume=0.01, sl_units=20.0, hold_sec=180, gap_sec=120),
        ]
    )
    assert res_j["live_entries_filled"] == 1
    assert res_j["live_exits_filled"] == 1
    assert len(mt5_jump.positions) == 0
    rows_j = list(csv.DictReader((tmp_path / "fills_jump.csv").open("r", encoding="utf-8")))
    assert rows_j[-1]["exit_reason"] == "PRE_FLATTEN_UTC_CUTOFF"
    assert float(rows_j[-1]["swap_usd"]) == 0.0

    # 5. Restart resume cap: if CSV already has 28 live entries, 0 new orders are sent!
    for idx in range(28):
        sym = probe.CORE_SYMBOLS[idx % 4]
        probe.append_fill_csv(
            fills_csv,
            {
                "utc_ts": 1795520000 + idx * 60,
                "symbol": sym,
                "leg": "ENTRY",
                "retcode": 10009,
                "dry_run": False,
            },
        )
    mt5_cap = FakeMT5(data_path=str(portable_dir))
    runner_cap = probe.CalibrationProbeRunner(
        mt5=mt5_cap,
        execute_live=True,
        news_events=far_news,
        spread_log_path=tmp_path / "sp_cap.jsonl",
        fills_csv_path=fills_csv,
        sample_interval_sec=5,
        max_trades=28,
        clock_fn=MockClock(datetime(2026, 11, 25, 10, 0, 0, tzinfo=timezone.utc)),
        sleep_fn=lambda _s: None,
    )
    res_cap = runner_cap.run_calibration()
    assert res_cap["order_send_count"] == 0
    assert res_cap["live_entries_filled"] == 0


def test_market_execution_zero_res_price_resolves_from_position_and_deal(tmp_path: Path) -> None:
    """FTMO Market Execution may return retcode=10009 with res.price==0.0 & res.deal==0; verify clean resolution."""
    class MarketExecMT5(FakeMT5):
        def order_send(self, req: dict[str, Any]):
            res = super().order_send(req)
            if "position" not in req:
                # Simulate FTMO market execution returning price=0.0, deal=0 on order_send response
                return SimpleNamespace(retcode=res.retcode, deal=0, order=res.order, price=0.0, comment="MarketExec")
            return res

    mt5 = MarketExecMT5()
    clock = MockClock(datetime(2026, 11, 25, 10, 40, 0, tzinfo=timezone.utc))
    far_news = [{"utc_ts": int(clock.now.timestamp()) + 86_400, "ccy": "USD", "event": "NFP"}]
    fills_csv = tmp_path / "me_fills.csv"
    runner = probe.CalibrationProbeRunner(
        mt5=mt5,
        execute_live=True,
        news_events=far_news,
        spread_log_path=tmp_path / "me_sp.jsonl",
        fills_csv_path=fills_csv,
        sample_interval_sec=60,
        max_trades=1,
        clock_fn=clock,
        sleep_fn=clock.sleep,
    )
    res = runner.run_calibration(
        schedule=[probe.PlannedCalibrationTrade(seq=1, symbol="USDJPY", side="BUY", volume=0.01, sl_units=20.0, hold_sec=180, gap_sec=120)]
    )
    assert res["live_entries_filled"] == 1
    assert res["live_exits_filled"] == 1
    rows = list(csv.DictReader(fills_csv.open("r", encoding="utf-8")))
    assert len(rows) == 2
    assert float(rows[0]["fill_price"]) > 150.0
    assert float(rows[0]["commission_usd"]) == pytest.approx(-0.025)
    assert float(rows[1]["fill_price"]) > 150.0


def test_lookup_deal_details_waits_for_delayed_exit_deal_never_returns_entry_deal() -> None:
    """Regression: delayed MT5 history sync on close must NEVER return DEAL_ENTRY_IN as EXIT deal."""
    entry_deal = SimpleNamespace(ticket=1001, order=2001, position_id=555, entry=0, price=1.30751, profit=0.0, commission=-0.03, swap=0.0)
    exit_deal = SimpleNamespace(ticket=1002, order=2002, position_id=555, entry=1, price=1.30720, profit=0.31, commission=-0.03, swap=0.0)

    class DelayedHistoryMT5:
        def __init__(self) -> None:
            self.calls = 0

        def history_deals_get(self, ticket=None, order=None, position=None):
            self.calls += 1
            # First 3 polls only show DEAL_ENTRY_IN; exit deal appears on poll 4+
            if position == 555:
                return [entry_deal] if self.calls <= 3 else [entry_deal, exit_deal]
            return []

    mt5 = DelayedHistoryMT5()
    got = probe._lookup_deal_details(
        mt5,
        deal_ticket=0,
        order_ticket=2002,
        position_id=555,
        expected_entry_type=1,
        sleep_fn=lambda _s: None,
    )
    assert got is not None
    assert got.ticket == 1002
    assert got.entry == 1
    assert got.price == pytest.approx(1.30720)



