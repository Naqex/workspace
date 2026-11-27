"""As-observed trade valuation and conservative FTMO 2-Step replay."""

import json
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from math import floor, isfinite
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from quant_core.market_data_store import Checksums, MarketDataStore
from quant_core.native_paths import PathGuard, read_bounded

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "planning/research"
SWING_REPORT = "SWING-10K-AUDIT-MULTIWEEK-AND-WIN-TAXONOMY-20261120.json"
STANDARD_REPORT = "FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.json"
LOCK_SHA = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"
STOP = 1735689600000
MINUTE = 60000
PRAGUE, NY = ZoneInfo("Europe/Prague"), ZoneInfo("America/New_York")
FX = {
    "EUR": ("EURUSD", False),
    "GBP": ("GBPUSD", False),
    "AUD": ("AUDUSD", False),
    "NZD": ("NZDUSD", False),
    "JPY": ("USDJPY", True),
    "CAD": ("USDCAD", True),
    "CHF": ("USDCHF", True),
}
BALANCES = {"Swing": (10000, 25000), "Standard": (10000, 50000)}
STANDARD_SHA = "09d1a66b5bbb46032ca8dfd7294b40a7d98424a3dd155ac9561cc5fe9c25dc32"
SWING_SHA = "ac949d2a2129f3650b5414c9369509057aecf0f399f226c1f79d7226acafa6f9"
SWING_FULL_ARCHIVE_SHA = "803352fbf00d7af15719033c9b0aa5b3140bca0d0cfa7235d01caa2e7b95f4a3"


def utc_time(ms):
    return datetime.fromtimestamp(ms / 1000, UTC)


def bar_path_scope(trade):
    for at, date in ((trade.open_time, trade.open_date), (trade.close_time, trade.close_date)):
        if (at is not None and at >= STOP) or (at is None and date and date >= "2025-01-01"):
            return "bar_path_skipped_holdout_lock"
    return "bar_path_development_eligible" if trade.has_execution_clock else "bar_path_unknown_trade_clock"


def check_lock():
    b = (RESEARCH / "NATIVE_FTMO_HOLDOUT_LOCK.json").read_bytes()
    if sha256(b).hexdigest() != LOCK_SHA:
        raise ValueError("HOLDOUT_LOCK_CHANGED")


def normalized_digest(blob):
    return sha256(blob.replace(b"\r\n", b"\n")).hexdigest()


@lru_cache(maxsize=1)
def profiles():
    check_lock()
    std_blob = (RESEARCH / STANDARD_REPORT).read_bytes()
    swing_blob = (RESEARCH / SWING_REPORT).read_bytes()
    if (normalized_digest(std_blob), normalized_digest(swing_blob)) != (STANDARD_SHA, SWING_SHA):
        raise ValueError("TARGET_COST_PROFILE_SHA_DRIFT")
    standard = json.loads(std_blob)["symbols"]
    swing = json.loads(swing_blob)["account_audit"]["symbols"]
    result = {"Swing": {}, "Standard": {}}
    for symbol, a in standard.items():
        if symbol not in swing:
            raise ValueError("TARGET_SPEC_SYMBOL_MISMATCH")
        w = swing[symbol]
        refs = {
            "Standard": a["spec"]["margin_estimates_usd"]["1.0"],
            "Swing": [w["swing_margin"]["sides"][side]["margin_100_usd"] for side in ("BUY", "SELL")],
        }
        for name in result:
            native = {**a["spec"], **w["swing_fields"]} if name == "Swing" else a["spec"]
            if name == "Swing":
                mid = (w["swing_margin"]["bid"] + w["swing_margin"]["ask"]) / 2
            else:
                mid = (a["spec"]["bid"] + a["spec"]["ask"]) / 2
            denom = mid if symbol in ("XAUUSD", "US500.cash") else 1.0
            currency = native["currency_margin"]
            if currency != "USD":
                ref, invert = FX[currency]
                q = standard[ref]["spec"] if name == "Standard" else swing[ref]["swing_margin"]
                ref_mid = (q["bid"] + q["ask"]) / 2
                denom = 1 / ref_mid if invert else ref_mid
            scale = 0.01 if symbol.endswith("JPY") else 1 if symbol in ("XAUUSD", "US500.cash") else 0.0001
            result[name][symbol] = {
                **native,
                "margin_per_reference": max(refs[name]) / denom,
                "spread_price_proxy": a["spread"]["median"] * scale,
            }
    binding = {
        "Standard": {"commit": "36f1535", "sha256_lf": normalized_digest(std_blob), "reference": STANDARD_REPORT},
        "Swing": {"commit": "8fd77ef", "sha256_lf": normalized_digest(swing_blob), "reference": SWING_REPORT},
    }
    return result, binding


def read_json_file(path, limit=4 * 1024 * 1024):
    if Path(path).suffix.lower() != ".json":
        raise ValueError("JSON_BINDING_REQUIRED")
    return json.loads(read_bounded(Path(path), limit))


class Market:
    """Open only checksummed UTC M1 stores proven to end before the holdout."""

    def __init__(self, binding=None):
        self.items = read_json_file(binding) if binding else {}
        self.stores = {}
        self.checks = Checksums()
        self.guard = PathGuard()
        self._bid_cache: OrderedDict[tuple[Any, Any], float | None] = OrderedDict()

    def close(self):
        self.stores.clear()
        self._bid_cache.clear()

    def store(self, symbol):
        spec = self.items.get(symbol)
        if not spec:
            return None
        if symbol in self.stores:
            return self.stores[symbol]
        if spec.get("time_basis") != "UTC" or spec.get("bar_seconds") != 60 or spec.get("scope") != "DEVELOPMENT":
            raise ValueError("EXPLICIT_UTC_M1_DEVELOPMENT_BINDING_REQUIRED")
        folder = Path(spec["path"])
        manifest = read_json_file(folder / "manifest.json")
        t, _ = self.guard.admit(folder / "times.bin")
        self.checks.verify(t, manifest["files"]["times.bin"])
        times = np.memmap(t, mode="r", dtype="<i8")
        if not len(times) or np.any(times >= STOP // 1000) or np.any(np.diff(times) <= 0) or np.any(times % 60):
            raise ValueError("STORE_CLOCK_OUTSIDE_OR_MALFORMED_DEVELOPMENT")
        scale = float(spec["scale"])
        if not isfinite(scale) or scale <= 0:
            raise ValueError("POSITIVE_STORE_PRICE_SCALE_REQUIRED")
        for name in ("o", "h", "l", "c"):
            self.guard.admit(folder / (name + ".bin"))
        store = MarketDataStore(folder, self.checks)
        self.stores[symbol] = (store, scale)
        return self.stores[symbol]

    def bars(self, symbol, first, end):
        if not 0 <= first < end <= STOP:
            return None
        item = self.store(symbol)
        if not item:
            return None
        store, scale = item
        return store.bars(first, end), scale

    def bid(self, symbol, at):
        key = (symbol, at)
        if key in self._bid_cache:
            self._bid_cache.move_to_end(key)
            return self._bid_cache[key]
        if not 0 <= at < STOP:
            result = None
        else:
            first = at // MINUTE * MINUTE
            obs = self.bars(symbol, first, first + MINUTE)
            result = None if obs is None or not len(obs[0]) else float(obs[0]["bo"][0]) / obs[1]
        self._bid_cache[key] = result
        if len(self._bid_cache) > 32768:
            self._bid_cache.popitem(last=False)
        return result

    def usd(self, currency, at, symbol, price):
        if currency == "USD":
            return 1.0
        if currency not in FX:
            return None
        pair, invert = FX[currency]
        ref = price if symbol == pair else self.bid(pair, at)
        return (1 / ref if invert else ref) if ref else None


class LogOnlyMarket(Market):
    def bid(self, symbol, at):
        return None


def commission(symbol, spec, price):
    if symbol == "US500.cash":
        return 0.0
    if symbol == "XAUUSD":
        return price * spec["trade_contract_size"] * 0.000007
    return 2.5


def rollovers(start, end, triple):
    day = utc_time(start).astimezone(NY).date()
    last = utc_time(end).astimezone(NY).date()
    while day <= last:
        at = int(datetime(day.year, day.month, day.day, 17, tzinfo=NY).timestamp() * 1000)
        if start < at < end and day.weekday() < 5:
            yield at, 3 if day.weekday() + 1 == triple else 1
        day += timedelta(days=1)


def markable(trade):
    return trade.has_execution_clock and trade.open_time < trade.close_time and trade.direction and trade.open_price


def position(trade, spec, market):
    if not markable(trade) or trade.close_price is None or not spec:
        return None
    start, end = trade.open_time, trade.close_time
    op, cl = trade.open_price, trade.close_price
    side = 1 if trade.direction == "BUY" else -1
    quote = spec["currency_profit"]
    cs = spec["trade_contract_size"]
    close_usd = market.usd(quote, end, trade.symbol, cl)
    if close_usd is None:
        return None
    open_comm = commission(trade.symbol, spec, op)
    close_comm = commission(trade.symbol, spec, cl)
    gross = side * (cl - op) * cs * close_usd
    funding = {}
    term = spec["swap_long" if side == 1 else "swap_short"]
    if spec["swap_mode"] != 1:
        return None
    for at, mult in rollovers(start, end, spec["swap_rollover3days"]):
        # A funding conversion uses the price at the rollover. USD-quoted
        # instruments do not need a separate quote to post points.
        mark = market.bid(trade.symbol, at) if quote != "USD" and quote in FX and FX[quote][0] == trade.symbol else op
        rate = market.usd(quote, at, trade.symbol, mark) if mark is not None else None
        if rate is None:
            return None
        funding[at] = term * spec["point"] * cs * rate * mult
    risk = None
    if trade.initial_sl and side * (op - trade.initial_sl) > 0:
        ir = market.usd(quote, start, trade.symbol, op)
        if ir is not None:
            risk = abs(op - trade.initial_sl) * cs * ir + open_comm + commission(trade.symbol, spec, trade.initial_sl)
    if trade.symbol in ("XAUUSD", "US500.cash"):
        margin = spec["margin_per_reference"] * op
    else:
        ir = market.usd(spec["currency_margin"], start, trade.symbol, op)
        margin = spec["margin_per_reference"] * ir if ir is not None else None
    return dict(
        gross=gross,
        open_commission=open_comm,
        close_commission=close_comm,
        rolls=funding,
        swap=sum(funding.values()),
        net=gross - open_comm - close_comm + sum(funding.values()),
        margin=margin,
        risk=risk,
        side=side,
    )


def mark_pnl(t, spec, market, side, at, bid):
    price = bid + (spec["spread_price_proxy"] if side == -1 else 0.0)
    usd = market.usd(spec["currency_profit"], at, t.symbol, price)
    if usd is None:
        return None
    return side * (price - t.open_price) * spec["trade_contract_size"] * usd


def calendar_covers(calendar, trade, field="breaks_by_symbol"):
    return bool(
        calendar
        and trade.has_execution_clock
        and trade.symbol in calendar[field]
        and calendar["valid_from_utc_msc"] <= trade.open_time <= trade.close_time <= calendar["valid_to_utc_msc"]
    )


def observe_path(t, spec, market, p, calendar=None):
    if p is None or not t.has_execution_clock or not 0 <= t.open_time < t.close_time < STOP:
        return None
    first = (t.open_time // MINUTE + 1) * MINUTE
    edge = t.close_time // MINUTE * MINUTE
    source = market.bars(t.symbol, first, edge) if first < edge else None
    if source is None:
        return None
    rows, scale = source
    if calendar is not None and calendar_covers(calendar, t):
        for start, end in calendar["breaks_by_symbol"][t.symbol]:
            # Treat only fully closed minutes as covered by a known break.
            begin = max(first, (start + MINUTE - 1) // MINUTE * MINUTE)
            finish = min(edge, end // MINUTE * MINUTE)
            if begin < finish:
                rows = rows[(rows["t"] < begin) | (rows["t"] >= finish)]
    expected = (edge - first) // MINUTE
    if calendar is not None and calendar_covers(calendar, t):
        for start, end in calendar["breaks_by_symbol"][t.symbol]:
            begin = max(first, (start + MINUTE - 1) // MINUTE * MINUTE)
            finish = min(edge, end // MINUTE * MINUTE)
            expected -= max(0, (finish - begin) // MINUTE)
    complete = len(rows) == expected
    all_marks = {}
    favourable = []
    adverse = []
    for row in rows:
        at = int(row["t"])
        marks = [mark_pnl(t, spec, market, p["side"], at, float(row[field]) / scale) for field in ("bo", "bl", "bh")]
        if None in marks:
            complete = False
            continue
        all_marks[at] = marks[0]
        ante = sum(x for when, x in p["rolls"].items() if when <= at) - p["open_commission"]
        best_field = "bh" if p["side"] == 1 else "bl"
        worst_field = "bl" if p["side"] == 1 else "bh"
        favourable.append((at, max(marks[1:]) + ante - commission(t.symbol, spec, float(row[best_field]) / scale)))
        adverse.append(min(marks[1:]) + ante - commission(t.symbol, spec, float(row[worst_field]) / scale))
    best = max([*favourable, (t.close_time, p["net"])], key=lambda x: (x[1], -x[0]))
    worst = min([*adverse, p["net"]])
    return dict(
        marks=all_marks,
        complete=complete and len(all_marks) == expected,
        observed=len(all_marks),
        expected=expected,
        mfe=max(0.0, best[1]),
        mae=max(0.0, -worst),
        peak_hours=(best[0] - t.open_time) / 3600000 if best[1] > 0 else None,
    )


def sessions(path):
    if path is None:
        return None
    payload = read_json_file(path)
    start, end = payload["valid_from_utc_msc"], payload["valid_to_utc_msc"]
    if not isinstance(start, int) or not isinstance(end, int) or start >= end or not payload.get("source"):
        raise ValueError("SESSION_BREAK_BINDING_INVALID")
    for windows in payload["breaks_by_symbol"].values():
        last = start
        for a, b in windows:
            if not last <= a < b <= end:
                raise ValueError("UNSORTED_OR_UNBOUND_SESSION_BREAK")
            last = b
    return payload


def calendar_warnings(trades, calendar, supported):
    assessed = 0
    long_break = []
    weekend_proxy = []
    for t in trades:
        if not t.has_execution_clock or t.open_time >= t.close_time or t.symbol not in supported:
            continue
        if calendar_covers(calendar, t):
            assessed += 1
            for a, b in calendar["breaks_by_symbol"][t.symbol]:
                if b - a > 2 * 3600000 and t.open_time < a < t.close_time:
                    long_break.append(dict(row=t.row, symbol=t.symbol, break_start_msc=a, break_end_msc=b))
                    break
            continue
        start = utc_time(t.open_time)
        sat = start.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=(5 - start.weekday()) % 7)
        if sat < start:
            sat += timedelta(days=7)
        if int(sat.timestamp() * 1000) < t.close_time:
            weekend_proxy.append(t.row)
    return dict(
        status="FUNDED_STANDARD_LONG_BREAK_OBSERVED"
        if long_break
        else "NO_LONG_BREAK_OBSERVED"
        if trades and assessed == len(trades)
        else "UNKNOWN_HISTORICAL_CALENDAR_OR_CLOCK",
        assessed=assessed,
        breaches=long_break,
        weekend_proxy_rows=weekend_proxy,
        applies_to="FUNDED_STANDARD",
        swing_exception=True,
    )


@dataclass(frozen=True)
class Sized:
    trade: object
    position: dict
    path: dict | None
    lots: float


def size(t, p, path, spec, balance, fraction):
    if p is None or p["risk"] is None or p["risk"] <= 0:
        return None, "INITIAL_STOP_OR_VALUATION_UNKNOWN"
    step = spec["volume_step"]
    lot = min(spec["volume_max"], floor(balance * fraction / p["risk"] / step + 1e-10) * step)
    if lot < spec["volume_min"]:
        return None, "TARGET_MIN_LOT_EXCEEDS_RISK"
    return Sized(t, p, path, round(lot, 10)), None


def replay(trades, prepared, specs, balance, fraction):
    marks = defaultdict(list)
    events = defaultdict(list)
    missing = defaultdict(int)
    sized = []
    for t in trades:
        p, path = prepared[t.row]
        x, reason = size(t, p, path, specs.get(t.symbol), balance, fraction)
        if not x:
            missing[reason] += 1
            continue
        sized.append(x)
        events[t.open_time].append(("open", x, 0.0))
        events[t.close_time].append(("close", x, 0.0))
        for when, value in p["rolls"].items():
            events[when].append(("swap", x, value))
        if path:
            for when, value in path["marks"].items():
                marks[when].append((t.row, value))
    targets = len(sized)
    active = {}
    cash = float(balance)
    anchor = cash
    day = None
    equity_points = 0
    daily = overall = peak_margin = 0.0
    cash_daily = cash_overall = 0.0
    margin_points = 0
    unvalued = 0
    worst_day_at = worst_overall_at = None
    for at in sorted(marks.keys() | events.keys()):
        current_day = utc_time(at).astimezone(PRAGUE).date()
        if day != current_day:
            day = current_day
            anchor = cash
        for action, x, value in sorted(events[at], key=lambda p: ("close", "swap", "open").index(p[0])):
            t, p, lots = x.trade, x.position, x.lots
            if action == "close":
                cash += (p["gross"] - p["close_commission"]) * lots
                del active[t.row]
            elif action == "swap":
                cash += value * lots
            else:
                active[t.row] = x
                cash -= p["open_commission"] * lots
        cash_daily = max(cash_daily, (anchor - cash) / balance)
        cash_overall = max(cash_overall, (balance - cash) / balance)
        market_marks = dict(marks[at])
        # At entry the fill price gives exactly zero fill-to-fill unrealized
        # PnL before the quoted liquidation spread, which remains unknown.
        if any(key not in market_marks for key in active):
            unvalued += 1
            continue
        equity_points += 1
        eq = cash + sum(market_marks[k] * x.lots for k, x in active.items())
        if (delta := (anchor - eq) / balance) > daily:
            daily, worst_day_at = delta, at
        if (delta := (balance - eq) / balance) > overall:
            overall, worst_overall_at = delta, at
        if all(x.position["margin"] is not None for x in active.values()) and eq > 0:
            margin_points += bool(active)
            peak_margin = max(peak_margin, sum(x.position["margin"] * x.lots for x in active.values()) / eq)
    # Admission requirements use independent native estimates at reported fills.
    # Track a sum even where floating equity cannot be valued at those exact times.
    req_events = defaultdict(float)
    for x in sized:
        if x.position["margin"] is not None:
            req = x.position["margin"] * x.lots
            req_events[x.trade.open_time] += req
            req_events[x.trade.close_time] -= req
    margin_req = peak_req = 0.0
    for when in sorted(req_events):
        margin_req += req_events[when]
        peak_req = max(peak_req, margin_req)
    observed = bool(equity_points)
    day_breach = observed and daily > 0.05 + 1e-12
    overall_breach = observed and overall > 0.10 + 1e-12
    complete = bool(trades) and targets == len(trades) and all(x.path and x.path["complete"] for x in sized)
    status = (
        ("BREACH_AT_MODELED_MARK" if complete else "BREACH_INDICATION_OBSERVED_COHORT")
        if day_breach or overall_breach
        else ("NO_BREACH_AT_SAMPLED_MARKS" if complete else "UNKNOWN_INTRADAY_COVERAGE_OR_RISK")
    )
    return dict(
        status=status,
        capital_usd=balance,
        risk_per_trade_pct=fraction * 100,
        normalized_trades=targets,
        excluded=dict(missing),
        equity_mark_points=equity_points,
        unvalued_event_points=unvalued,
        closed_balance_observations=sum(1 for _, xs in events.items() if any(action == "close" for action, _, _ in xs)),
        known_entry_margin_trades=sum(x.position["margin"] is not None for x in sized),
        daily_loss_pct=max(0.0, daily) * 100 if observed else None,
        maximum_loss_pct=max(0.0, overall) * 100 if observed else None,
        cash_only_daily_loss_pct=100 * cash_daily if targets else None,
        cash_only_static_loss_pct=100 * cash_overall if targets else None,
        daily_breach_observed=bool(day_breach),
        overall_breach_observed=bool(overall_breach),
        worst_daily_at_msc=worst_day_at,
        worst_overall_at_msc=worst_overall_at,
        net_usd=cash - balance if targets else None,
        peak_margin_usd=peak_req if req_events else None,
        peak_margin_pct_initial=100 * peak_req / balance if req_events else None,
        margin_peak_pct_available_equity=100 * peak_margin if margin_points else None,
        margin_scope="INITIAL_REQUIREMENTS_AT_REPORTED_FILLS_PLUS_OBSERVED_EQUITY_MARKS",
        margin_prudential_50pct_exceeded=(peak_req > 0.5 * balance or peak_margin > 0.5) if req_events else None,
        margin_100pct_exceeded_at_equity_mark=(peak_margin > 1.0) if margin_points else None,
    )
