"""Read-only FTMO capture and causal paper execution. Never submits broker orders."""
from datetime import datetime, timezone
from decimal import Decimal
from collections import Counter
import hashlib
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

ALLOW_LIVE_ORDER_SEND = False
PRAGUE = ZoneInfo("Europe/Prague")
ASSETS = ("XAUUSD", "EURUSD")
MINUTE = 60000


class AdapterError(ValueError):
    pass


def account_hash(login, server):
    return hashlib.sha256(f"{login}|{server}".encode()).hexdigest()


def verify_account(account, binding):
    if type(account.get("trade_mode")) is not int or account["trade_mode"] != 0:
        raise AdapterError("VERIFIED_DEMO_ACCOUNT_REQUIRED")
    if (account.get("server") != binding["server"] or
            account_hash(account.get("login"), account.get("server")) != binding["account_hash"] or
            account.get("currency") != "USD"):
        raise AdapterError("ACCOUNT_BINDING_MISMATCH")
    return dict(account_hash=binding["account_hash"], server=binding["server"],
                trade_mode="DEMO", currency="USD", execution_capability=False)


def validate_spec(asset, spec):
    expected = 100 if asset == "XAUUSD" else 100000
    for key in ("trade_contract_size", "volume_min", "volume_step", "volume_max", "point", "trade_tick_size"):
        if not math.isfinite(float(spec.get(key, 0))) or spec[key] <= 0:
            raise AdapterError("INCOMPLETE_SYMBOL_SPEC")
    if spec["trade_contract_size"] != expected or spec["volume_min"] != .01 or spec["volume_step"] != .01:
        raise AdapterError("SYMBOL_CONTRACT_DIFFERS_FROM_FROZEN_ENGINE")
    for key in ("swap_long", "swap_short", "swap_mode", "trade_stops_level", "trade_freeze_level"):
        if key not in spec or not math.isfinite(float(spec[key])):
            raise AdapterError("INCOMPLETE_SWAP_OR_STOP_SPEC")
    if spec["trade_stops_level"] < 0 or spec["trade_freeze_level"] < 0:
        raise AdapterError("NEGATIVE_STOP_OR_FREEZE_LEVEL")
    return spec


def prague_midnight(at):
    local = datetime.fromtimestamp(at / 1000, timezone.utc).astimezone(PRAGUE)
    return int(local.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)


def daily_guard(mark, now, maximum_loss_pct=2.2):
    if (mark is None or not mark.get("history_query_complete") or
            mark.get("midnight_msc") != prague_midnight(now) or
            not 0 <= now - mark.get("known_at_msc", -1) <= 60000):
        return "DAILY_ANCHOR_OR_ACCOUNT_MARK_UNKNOWN"
    for key in ("equity", "midnight_balance", "initial_balance"):
        if not math.isfinite(float(mark.get(key, float("nan")))):
            return "ACCOUNT_MARK_NONFINITE"
    if mark["initial_balance"] <= 0 or mark["midnight_balance"] <= 0:
        return "ACCOUNT_CAPITAL_INVALID"
    limit = mark["midnight_balance"] - mark["initial_balance"] * maximum_loss_pct / 100
    return "DAILY_2P2_HALT" if mark["equity"] <= limit else None


def calendar_known(calendar, now):
    return (isinstance(calendar, dict) and calendar.get("known_at_msc", now + 1) <= now and
            calendar.get("from_msc", now + 1) <= now < calendar.get("to_msc", -1) and
            calendar.get("coverage_complete") is True and bool(calendar.get("source")))


def news_guard(news, now, asset, phase, *, simulate_funded_rules=True):
    if phase not in ("CHALLENGE", "VERIFICATION", "FREE_TRIAL", "FUNDED_STANDARD"):
        return "PROGRAM_PHASE_UNKNOWN"
    if phase in ("CHALLENGE", "VERIFICATION", "FREE_TRIAL") and not simulate_funded_rules:
        return None
    if not calendar_known(news, now):
        return "RESTRICTED_NEWS_COVERAGE_UNKNOWN"
    for event in news.get("events", []):
        if event.get("known_at_msc", news["known_at_msc"]) > now:
            continue
        if asset in event["assets"] and abs(now - event["at_msc"]) <= 120000:
            return "RESTRICTED_NEWS_2MIN"
    return None


def session_deadline(at, holidays):
    if not calendar_known(holidays, at):
        raise AdapterError("HOLIDAY_SESSION_COVERAGE_UNKNOWN")
    day = at // 86400000 * 86400000
    date = datetime.fromtimestamp(at / 1000, timezone.utc)
    row = holidays.get("days", {}).get(date.date().isoformat(), {})
    if date.weekday() >= 5 or row.get("closed"):
        return day
    flat = day + 73800000
    if row.get("flat_utc"):
        h, m = map(int, row["flat_utc"].split(":"))
        if not 0 <= h < 24 or not 0 <= m < 60:
            raise AdapterError("INVALID_EARLY_CLOSE_CLOCK")
        flat = min(flat, day + (h * 60 + m) * MINUTE)
    return flat


def reconcile_fills(expected, actual):
    wanted = {r["intent_id"]: r for r in expected}
    if len(wanted) != len(expected):
        raise AdapterError("DUPLICATE_EXPECTED_INTENT")
    groups = {}
    deal_counts = Counter(r["deal_id"] for r in actual)
    for r in actual:
        groups.setdefault(r["intent_id"], []).append(r)
    result = []
    for identity in sorted(wanted.keys() | groups.keys()):
        e, fills = wanted.get(identity), groups.get(identity, [])
        if e is None:
            result.append(dict(intent_id=identity, status="UNEXPECTED_FILL"))
            continue
        if not fills:
            result.append(dict(intent_id=identity, status="NO_ACTUAL_FILL_SLIPPAGE_UNMEASURED"))
            continue
        ids = [f["deal_id"] for f in fills]
        if any(deal_counts[v] > 1 for v in ids):
            result.append(dict(intent_id=identity, status="DUPLICATE_DEAL_ID"))
            continue
        compatible = all((f["asset"], f["side"], f.get("leg", "ENTRY")) ==
                         (e["asset"], e["side"], e.get("leg", "ENTRY")) for f in fills)
        if not compatible or any(f["volume"] <= 0 for f in fills):
            result.append(dict(intent_id=identity, status="ASSET_SIDE_LEG_OR_VOLUME_MISMATCH"))
            continue
        if any(not math.isfinite(float(f["price"])) or
               not math.isfinite(float(f["volume"])) or f["filled_at_msc"] < e["requested_at_msc"] for f in fills):
            result.append(dict(intent_id=identity, status="INVALID_PRICE_VOLUME_OR_FILL_BEFORE_REQUEST"))
            continue
        volume = sum(Decimal(str(f["volume"])) for f in fills)
        average = sum(Decimal(str(f["price"])) * Decimal(str(f["volume"])) for f in fills) / volume
        sign = 1 if e["side"] == "BUY" else -1
        if e.get("leg", "ENTRY") == "EXIT":
            sign = -sign
        result.append(dict(intent_id=identity,
            status="MATCHED" if volume == Decimal(str(e["volume"])) else "PARTIAL_OR_EXCESS_VOLUME",
            volume=float(volume), weighted_fill_price=float(average),
            adverse_slippage_price_units=float(sign * (average - Decimal(str(e["price"])))),
            latency_ms=[f["filled_at_msc"] - e["requested_at_msc"] for f in fills],
            commission=sum(f.get("commission", 0) for f in fills),
            swap=sum(f.get("swap", 0) for f in fills), fee=sum(f.get("fee", 0) for f in fills)))
    return result


class FileBridge:
    """Recorded native bridge pages are data, never embedded instructions/code."""
    def __init__(self, path):
        self.bundle = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if self.bundle.get("schema") != "ftmo-readonly-bridge-v1":
            raise AdapterError("BRIDGE_SCHEMA")

    def account(self):
        return self.bundle["account"]

    def spec(self, asset):
        return self.bundle["specs"][asset]

    def ticks(self, asset, first, end):
        return [r for r in self.bundle["ticks"] if r["asset"] == asset and first <= r["time_msc"] < end]

    def account_mark(self, observed_at, initial_balance):
        return self.bundle.get("broker_daily_mark")


class NativeMT5Reader:
    """Explicit attachment to a running terminal; no login(), selection or orders."""
    def __init__(self, terminal_path):
        if sys.platform != "win32":
            raise AdapterError("NATIVE_MT5_WINDOWS_REQUIRED")
        requested = str(Path(terminal_path).resolve()).casefold()
        command = ["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | "
                   "Select-Object -ExpandProperty ExecutablePath | ConvertTo-Json -Compress"]
        raw = subprocess.check_output(command, text=True, encoding="utf-8").strip()
        paths = json.loads(raw) if raw else []
        paths = paths if isinstance(paths, list) else [paths]
        if requested not in {str(Path(p).resolve()).casefold() for p in paths if p}:
            raise AdapterError("REQUESTED_TERMINAL_NOT_ALREADY_RUNNING")
        self.sdk = importlib.import_module("MetaTrader5")
        if not self.sdk.initialize(path=str(Path(terminal_path).resolve()), timeout=10000):
            raise AdapterError("MT5_READONLY_ATTACH_FAILED")

    def account(self):
        value = self.sdk.account_info()
        if value is None:
            raise AdapterError("MT5_ACCOUNT_INFO_UNAVAILABLE")
        return value._asdict()

    def spec(self, asset):
        value = self.sdk.symbol_info(asset)
        if value is None:
            raise AdapterError("MT5_SYMBOL_UNAVAILABLE")
        return value._asdict()

    def ticks(self, asset, first, end):
        rows = self.sdk.copy_ticks_range(asset, datetime.fromtimestamp(first / 1000, timezone.utc),
            datetime.fromtimestamp((end - 1) / 1000, timezone.utc), self.sdk.COPY_TICKS_ALL)
        if rows is None:
            raise AdapterError("MT5_TICK_QUERY_FAILED")
        return [dict(asset=asset, time_msc=int(r["time_msc"]), bid=float(r["bid"]), ask=float(r["ask"]),
                     flags=int(r["flags"])) for r in rows if first <= r["time_msc"] < end]

    def close(self):
        self.sdk.shutdown()

    def hourly(self, asset, now, count=1000):
        rows = self.sdk.copy_rates_from_pos(asset, self.sdk.TIMEFRAME_H1, 0, count)
        if rows is None:
            raise AdapterError("MT5_H1_WARMUP_QUERY_FAILED")
        scale = 1000 if asset == "XAUUSD" else 100000
        out = []
        for r in rows:
            at = int(r["time"]) * 1000
            if at + 3600000 > now:
                continue
            values = [Decimal(str(float(r[k]))) * scale for k in ("open", "high", "low", "close")]
            if any(v != v.to_integral_value() for v in values):
                raise AdapterError("NATIVE_H1_OUTSIDE_FROZEN_PRICE_GRID")
            out.append(dict(zip(("t", "bo", "bh", "bl", "bc"), (at, *map(int, values)))))
        return out

    def closed_minutes(self, asset, now):
        rows = self.sdk.copy_rates_from_pos(asset, self.sdk.TIMEFRAME_M1, 0, 40)
        if rows is None:
            raise AdapterError("MT5_RECENT_M1_QUERY_FAILED")
        return [int(r["time"]) * 1000 for r in rows if int(r["time"]) * 1000 + MINUTE <= now]

    def account_mark(self, observed_at, initial_balance):
        snapshot = self.account()
        midnight = prague_midnight(observed_at)
        deals = self.sdk.history_deals_get(datetime.fromtimestamp(midnight / 1000, timezone.utc),
                                           datetime.fromtimestamp(observed_at / 1000, timezone.utc))
        if deals is None:
            return None
        cashflows = sum(sum(Decimal(str(getattr(r, k, 0))) for k in ("profit", "commission", "swap", "fee"))
                       for r in deals)
        return dict(known_at_msc=observed_at, midnight_msc=midnight, history_query_complete=True,
                    midnight_balance=float(Decimal(str(snapshot["balance"])) - cashflows),
                    equity=snapshot["equity"], initial_balance=initial_balance,
                    anchor_source="balance minus recorded broker deal cashflows since Prague midnight")


def collect(reader, binding, first, end, *, observed_at):
    if not 0 < end - first <= 86400000 or end > observed_at:
        raise AdapterError("CAPTURE_INTERVAL_NOT_PAST_OR_TOO_LONG")
    identity = verify_account(reader.account(), binding)
    specs, ticks, distributions = {}, [], {}
    for asset in ASSETS:
        specs[asset] = validate_spec(asset, reader.spec(asset))
        rows = reader.ticks(asset, first, end)
        last = first
        by_hour = {}
        for r in rows:
            if (not first <= r["time_msc"] < end or r["time_msc"] < last or
                    not all(math.isfinite(float(r[k])) for k in ("bid", "ask")) or
                    r["bid"] <= 0 or r["ask"] < r["bid"]):
                raise AdapterError("UNORDERED_OR_INVALID_QUOTE")
            last = r["time_msc"]
            ticks.append({k: r[k] for k in ("asset", "time_msc", "bid", "ask")})
            by_hour.setdefault(r["time_msc"] // 3600000 % 24, []).append(r["ask"] - r["bid"])
        import numpy as np
        distributions[asset] = {str(h): dict(count=len(v), min=min(v), median=float(np.median(v)),
            p95=float(np.percentile(v, 95)), max=max(v), unit="price difference") for h, v in by_hour.items()}
    ticks.sort(key=lambda r: (r["time_msc"], ASSETS.index(r["asset"])))
    if verify_account(reader.account(), binding) != identity:
        raise AdapterError("ACCOUNT_CHANGED_DURING_CAPTURE")
    mark = reader.account_mark(observed_at, 50000) if hasattr(reader, "account_mark") else None
    return dict(schema="ftmo-readonly-capture-v19", binding=identity, from_msc=first, to_msc=end,
                observed_at_msc=observed_at, specs=specs, ticks=ticks, spread_by_UTC_hour=distributions,
                broker_daily_mark=mark,
                execution_capability=False, slippage_measured=False,
                commission_schedule="not implied by symbol_info; requires deal reconciliation",
                source_coverage="recorded broker/bridge quotes; absence is not a continuity certificate")


def signals_from_closed_hours(hourly, asset, now, calendar):
    """Reuse the frozen native H1/H4/D1 generators, including first-event/day."""
    import numpy as np
    from quant_core.native_hourly_source import native_recipes
    from prop_v12_signals import rejection_recipes
    if len(hourly) < 400 or np.any(np.diff(hourly["t"]) <= 0):
        raise AdapterError("SIGNAL_WARMUP_OR_HOURLY_ORDER")
    if int(hourly["t"][-1]) + 3600000 > now:
        raise AdapterError("UNFINISHED_H1_BAR")
    first = now // 86400000 * 86400000
    if asset == "EURUSD":
        recipes = rejection_recipes(hourly, asset, first, now + 1, calendar, native=True)
        wanted = {"F5:tf=H4:n=5:adx=25:buffer=0.1": ("DAY", "P0")}
    else:
        recipes = native_recipes(hourly, asset, first, now + 1, calendar)
        wanted = {"F3:compression=BB:n=60:quantile=0.1:multiple=1": ("48H", "P0"),
                  "F4:hour=15:impulse=1:timing=MONTH:multiple=1": ("24H", "P1")}
    result = []
    for r in recipes:
        if r["id"] not in wanted:
            continue
        horizon, mode = wanted[r["id"]]
        for at, side, stop in zip(r["at"], r["side"], r["stop"]):
            identity = asset + "|" + r["id"] + "|" + horizon + "|" + mode
            result.append(dict(id=identity, asset=asset, side="BUY" if side == 1 else "SELL",
                decision_msc=int(at), stop_units=int(stop), mode=mode,
                intent_id=hashlib.sha256(f"{identity}|{int(at)}".encode()).hexdigest()))
    return result


class ShadowPaper:
    """One private paper account; actual broker positions are never modified."""
    def __init__(self, plan, start, end):
        from prop_v18_costs import FrictionAccount
        from prop_v19_accounts import V19Account
        self.plan = plan
        self.trades, self.quotes, self.intents, self.expected, self.log = [], {}, {}, [], []
        self.last_time, self.day, self.mark = start - 1, None, None
        self.closed_minute, self.minute_close = {}, {}
        for times in plan.get("closed_M1_times", {}).values():
            if any(t % MINUTE or t + MINUTE > start for t in times):
                raise AdapterError("FUTURE_OR_UNALIGNED_INITIAL_M1_HISTORY")
        if plan["policy"] == "V19":
            from prop_v19_common import FREEZE, read
            if plan["profile"] != read(FREEZE)["selected_profile"]:
                raise AdapterError("SHADOW_PROFILE_DIFFERS_FROM_FROZEN_V19")
            self.account = V19Account(start, end, "SYM_FLAT", rolling=True, friction_pct=100,
                                      profile=plan["profile"])
        elif plan["policy"] == "V16":
            class GuardedV16(FrictionAccount):
                @property
                def internal_floor_milli(self):
                    return max(45800000, self.anchor - 1100000)
            self.account = GuardedV16(start, end, "SYM_FLAT", rolling=True, friction_pct=100)
        else:
            raise AdapterError("UNREGISTERED_PAPER_POLICY")

    def emit(self, kind, at, **fields):
        self.log.append(dict(kind=kind, known_at_msc=at, **fields))

    def offer(self, intent, known_at):
        if intent["decision_msc"] > known_at or known_at < self.last_time:
            raise AdapterError("FUTURE_SIGNAL_DECISION")
        if intent["intent_id"] in self.intents:
            original = {k: v for k, v in self.intents[intent["intent_id"]].items() if k not in ("offered_at", "consumed")}
            if original != intent:
                raise AdapterError("EXISTING_SIGNAL_INTENT_CHANGED")
        else:
            self.intents[intent["intent_id"]] = dict(intent, offered_at=known_at, consumed=False)
            self.emit("PAPER_INTENT", known_at, **intent)

    def paired(self, at, source):
        q = dict(t=at, src=ASSETS.index(source), ordinal=len(self.log))
        for i, asset in enumerate(ASSETS):
            old = self.quotes.get(asset)
            q["b" + str(i)] = old["bid_units"] if old else 0
            q["a" + str(i)] = old["ask_units"] if old else 0
        return q

    def close(self, i, now, quote, reason):
        if i not in self.account.active:
            return
        t = self.trades[i]
        field = ("b" if t["side"] == "BUY" else "a") + str(ASSETS.index(t["asset"]))
        if news_guard(self.plan["news"], now, t["asset"], self.plan["phase"]):
            self.emit("RESTRICTED_NEWS_EXIT_CONFLICT", now, trade=i, reason=reason)
        t.update(exit_msc=now, exit_price_units=quote[field], reason=reason, exit_quote_index=quote["ordinal"])
        quantity = self.account.active[i][0]
        self.account.action("exit", now, i, self.trades, quote)
        identity = t["intent_id"] + ":EXIT"
        self.expected.append(dict(intent_id=identity, asset=t["asset"], side=t["side"], leg="EXIT",
            volume=quantity / 100, price=t["exit_price_units"] / t["scale"], requested_at_msc=now))
        self.emit("PAPER_EXIT", now, trade=i, reason=reason, price_units=t["exit_price_units"])

    def advance(self, row):
        """One observed tick; known-at time is the execution clock, never backdated."""
        import numpy as np
        from prop_v18_costs import cost_bindings
        from quant_core.vectorized_sl_active_kernel import money, net_level
        asset, at = row["asset"], row["known_at_msc"]
        source_at = row["time_msc"]
        if asset not in ASSETS or at < self.last_time or source_at > at:
            raise AdapterError("QUOTE_ASSET_OR_CAUSAL_ORDER")
        if (not all(math.isfinite(float(row[k])) for k in ("bid", "ask")) or
                row["bid"] <= 0 or row["ask"] < row["bid"]):
            raise AdapterError("INVALID_PAPER_QUOTE")
        scale = 1000 if asset == "XAUUSD" else 100000
        old = self.quotes.get(asset)
        if old and source_at < old["source_msc"]:
            raise AdapterError("OUT_OF_ORDER_SOURCE_TICK")
        values = [Decimal(str(row[k])) * scale for k in ("bid", "ask")]
        if any(v != v.to_integral_value() for v in values):
            raise AdapterError("QUOTE_OUTSIDE_FROZEN_PRICE_GRID")
        bid, ask = map(int, values)
        self.quotes[asset] = dict(bid_units=bid, ask_units=ask, known_at_msc=at, source_msc=source_at)
        self.last_time = at
        quote = self.paired(at, asset)
        with cost_bindings(100):
            self.account._trades = self.trades
            day = prague_midnight(at)
            if self.day != day:
                self.account.action("reset", at, None, self.trades, quote)
                self.day = day
            # Arm P1 only after the prior M1 closes; current-minute extrema are never used.
            previous = self.minute_close.get(asset)
            if previous and source_at // MINUTE > previous["source_msc"] // MINUTE:
                contiguous = source_at // MINUTE == previous["source_msc"] // MINUTE + 1
                if contiguous:
                    times = self.plan.setdefault("closed_M1_times", {}).setdefault(asset, [])
                    times.append(previous["source_msc"] // MINUTE * MINUTE)
                    self.plan["closed_M1_times"][asset] = sorted(set(times))[-1000:]
                for i in list(self.account.active):
                    t = self.trades[i]
                    if (not contiguous or t["asset"] != asset or t["mode"] != "P1" or
                            t.get("activation_time") is not None):
                        continue
                    side = np.array([1 if t["side"] == "BUY" else -1])
                    close_px = previous["bid_units"] if side[0] == 1 else previous["ask_units"]
                    value = money(asset, "SYM", side, [t["entry_price_units"]], [close_px],
                                  [t["entry_msc"]], [at], ["MARKET"])["net"][0]
                    if value >= 1.5 * t["natural"]:
                        level = net_level(asset, side, np.array([t["entry_price_units"]]),
                            np.array([t["natural"]]), np.array([t["entry_msc"]]), np.array([at]), .15)
                        t.update(activation_time=at, protection_price=int(level[0]))
                        grid = Decimal(str(self.plan["specs"][asset]["trade_tick_size"]))
                        if Decimal(int(level[0])) / t["scale"] % grid:
                            self.emit("PAPER_ONLY_NONEXECUTABLE_PROTECTION_LEVEL", at, trade=i, level=int(level[0]))
                        self.emit("P1_ARMED_AFTER_CLOSED_M1", at, trade=i, level=int(level[0]))
            self.minute_close[asset] = dict(self.quotes[asset])
            for i in list(self.account.active):
                t = self.trades[i]
                if t["asset"] != asset:
                    continue
                level = t.get("protection_price") if t.get("activation_time") is not None else t["stop_units"]
                px = bid if t["side"] == "BUY" else ask
                stopped = px <= level if t["side"] == "BUY" else px >= level
                reason = "PROTECT" if t.get("activation_time") is not None else "SL"
                if stopped:
                    self.close(i, at, quote, reason)
                    continue
                news_exit = any(asset in e["assets"] and e.get("known_at_msc", 0) <= at and
                                e["at_msc"] - 150000 <= at <= e["at_msc"] + 120000
                                for e in self.plan["news"].get("events", []))
                timeout = old is not None and source_at - old["source_msc"] > 2 * MINUTE
                paper_equity = self.account.balance + self.account.floating(self.trades, quote)
                paper_halt = paper_equity <= self.account.anchor - 1100000
                unknown = not calendar_known(self.plan["news"], at) or not calendar_known(self.plan["holidays"], at)
                if at >= t["deadline_msc"] or timeout or news_exit or paper_halt or unknown or daily_guard(self.mark, at) == "DAILY_2P2_HALT":
                    if at > t["deadline_msc"] + 60000:
                        self.emit("SESSION_FLAT_LATE_QUOTE", at, trade=i, deadline=t["deadline_msc"])
                    self.close(i, at, quote, "FEED_TIMEOUT_NEXT_QUOTE" if timeout else
                               "GUARD_CALENDAR_UNKNOWN" if unknown else
                               "NEWS_PRE_FLAT" if news_exit else "DAILY_SAFETY_FLAT" if paper_halt or
                               daily_guard(self.mark, at) == "DAILY_2P2_HALT" else "SESSION_CLOSE")
            self.account.check(at, self.account.floating(self.trades, quote))
            self.account.observe_policy(at, self.account.balance + self.account.floating(self.trades, quote))
            # Native harvester requests are filled only at a later quote of that asset.
            for i, (after, reason) in list(self.account.pending.items()):
                if self.trades[i]["asset"] == asset and at > after:
                    self.close(i, at, quote, reason)
            for identity, intent in self.intents.items():
                if intent["consumed"] or intent["asset"] != asset:
                    continue
                if source_at < intent["offered_at"]:
                    continue
                intent["consumed"] = True
                reason = self.entry_reason(intent, at, row)
                if reason:
                    self.emit("PAPER_REJECT", at, intent_id=identity, reason=reason)
                    continue
                entry = ask if intent["side"] == "BUY" else bid
                deadline = session_deadline(at, self.plan["holidays"])
                t = dict(intent, entry_msc=at, entry_price_units=entry, scale=scale,
                    deadline_msc=deadline, role="CORE", regime_weight=1, d1_gate=True,
                    natural=abs(entry - intent["stop_units"]) / scale,
                    spread_units=ask - bid, activation_time=None, protection_price=None,
                    censored=False, entry_quote_index=quote["ordinal"])
                self.trades.append(t)
                i = len(self.trades) - 1
                from prop_v15_accounts import exact_quantity
                self.account._trades = self.trades
                if hasattr(self.account, "current_request"):
                    self.account.current_request = i
                try:
                    risk = self.account.risk_request(self.account.balance + self.account.floating(self.trades, quote), "CORE", 1)
                    quantity = exact_quantity(t, risk)
                except ValueError:
                    self.emit("PAPER_REJECT", at, intent_id=identity, reason="BROKER_LOT_GRID_OR_RISK")
                    continue
                finally:
                    if hasattr(self.account, "current_request"):
                        self.account.current_request = None
                if quantity / 100 > self.plan["specs"][asset]["volume_max"]:
                    self.emit("PAPER_REJECT", at, intent_id=identity, reason="BROKER_MAX_VOLUME")
                    continue
                before = len(self.account.accepted)
                self.account.action("entry", at, i, self.trades, quote)
                if len(self.account.accepted) == before:
                    self.emit("PAPER_RISK_REJECT", at, intent_id=identity, reasons=dict(self.account.rejected))
                    continue
                q = self.account.active[i][0]
                self.expected.append(dict(intent_id=identity, asset=asset, side=t["side"], leg="ENTRY",
                    volume=q / 100, price=entry / scale, requested_at_msc=at))
                self.emit("PAPER_ENTRY", at, intent_id=identity, volume=q / 100,
                          risk_usd=self.account.active[i][1], price_units=entry)
        with cost_bindings(100):
            self.emit("PAPER_EQUITY", at, balance_USD=self.account.balance / 1000,
                      equity_USD=(self.account.balance + self.account.floating(self.trades, quote)) / 1000)

    def entry_reason(self, intent, now, tick):
        from prop_v19_paths import preceding_continuity
        from types import SimpleNamespace
        import numpy as np
        asset = intent["asset"]
        if not 0 <= now - intent["decision_msc"] <= 60000:
            return "SIGNAL_ENTRY_WINDOW_EXPIRED"
        if now - tick["time_msc"] > 2000:
            return "STALE_EXECUTION_QUOTE"
        reason = daily_guard(self.mark, now)
        if reason:
            return reason
        if self.account.balance + self.account.floating(self.trades, self.paired(now, asset)) <= self.account.anchor - 1100000:
            return "PAPER_DAILY_2P2_HALT"
        reason = news_guard(self.plan["news"], now, asset, self.plan["phase"])
        if reason:
            return reason
        try:
            if now >= session_deadline(now, self.plan["holidays"]):
                return "SESSION_CLOSED_OR_CUTOFF"
        except AdapterError as exc:
            return str(exc)
        for i in self.account.active:
            held = self.trades[i]["asset"]
            if now - self.quotes[held]["known_at_msc"] > 2 * MINUTE:
                return "OTHER_ACTIVE_ASSET_QUOTE_STALE"
        if self.plan["policy"] == "V19":
            known = self.plan.get("closed_M1_times", {}).get(asset, [])
            schedule = SimpleNamespace(off_kind=lambda at, symbol: None)
            if not preceding_continuity(np.asarray(known, dtype="int64"), intent["decision_msc"], schedule, asset):
                return "PRECEDING_M1_DISCONTINUITY"
        spec = validate_spec(asset, self.plan["specs"][asset])
        mode = spec.get("trade_mode")
        if mode is not None and mode != 4 and mode != (1 if intent["side"] == "BUY" else 2):
            return "BROKER_SYMBOL_DIRECTION_DISABLED"
        quote = self.quotes[asset]
        entry = quote["ask_units"] if intent["side"] == "BUY" else quote["bid_units"]
        distance = (entry - intent["stop_units"]) * (1 if intent["side"] == "BUY" else -1)
        scale = 1000 if asset == "XAUUSD" else 100000
        if distance <= 0 or distance / scale < spec["trade_stops_level"] * spec["point"]:
            return "NATURAL_SL_INVALID_OR_TOO_CLOSE"
        if Decimal(intent["stop_units"]) / scale % Decimal(str(spec["trade_tick_size"])) != 0:
            return "NATURAL_SL_OFF_BROKER_TICK_GRID"
        from quant_core.vectorized_sl_active_kernel import money
        sign = np.array([1 if intent["side"] == "BUY" else -1])
        exit_px = quote["bid_units"] if sign[0] == 1 else quote["ask_units"]
        friction = -money(asset, "SYM", sign, [entry], [exit_px], [now], [now], ["MARKET"])["net"][0]
        if friction / (distance / scale) > .15:
            return "FRICTION_OVER_15PCT_OF_NATURAL_SL"
        return None

    def report(self):
        from prop_v18_costs import cost_bindings
        with cost_bindings(100):
            account = self.account.dump()
        return dict(schema="ftmo-shadow-paper-v19", mode="SHADOW_PAPER", execution_capability=False,
            research_program="inherited 50k two-step +10/+5; not actual Free Trial completion rules",
            policy=self.plan["policy"], account=account, log=self.log,
            expected_fills=self.expected, broker_orders_sent=0, slippage_measured=False,
            broker_execution_ready=False, historical_news_overlay_parity_certified=False)


def reduce_bridge(bundle, plan):
    import numpy as np
    verify_account(bundle["account"], plan["binding"])
    paper = ShadowPaper(plan, plan["from_msc"], plan["to_msc"])
    last_known, seen = plan["from_msc"], set()
    for ordinal, r in enumerate(bundle["events"]):
        known = r.get("known_at_msc")
        if known is None and isinstance(r.get("mark"), dict):
            known = r["mark"].get("known_at_msc")
        if not isinstance(known, int) or known < last_known or not plan["from_msc"] <= known < plan["to_msc"]:
            raise AdapterError("EVENT_KNOWN_AT_OR_CAPTURE_FENCE")
        last_known = known
        identity = r.get("record_id", str(ordinal))
        if identity in seen:
            raise AdapterError("DUPLICATE_BRIDGE_RECORD")
        seen.add(identity)
        if r["kind"] == "account_mark":
            paper.mark = r["mark"]
        elif r["kind"] == "signal":
            paper.offer(r["intent"], known)
        elif r["kind"] == "quote":
            paper.advance(r)
        elif r["kind"] == "closed_M1":
            times = r["times"]
            if any(t % MINUTE or t + MINUTE > known for t in times):
                raise AdapterError("FUTURE_OR_UNALIGNED_CLOSED_M1")
            previous = paper.plan.setdefault("closed_M1_times", {}).setdefault(r["asset"], [])
            paper.plan["closed_M1_times"][r["asset"]] = sorted(set(previous + times))[-1000:]
        elif r["kind"] == "closed_hours":
            dtype = [(k, "<i8") for k in ("t", "bo", "bh", "bl", "bc")]
            hours = np.array([tuple(v[k] for k, _ in dtype) for v in r["rows"]], dtype=dtype)
            if (np.any(hours["t"] % 3600000) or np.any(hours["bl"] <= 0) or
                    np.any(hours["bl"] > np.minimum(hours["bo"], hours["bc"])) or
                    np.any(hours["bh"] < np.maximum(hours["bo"], hours["bc"]))):
                raise AdapterError("INVALID_NATIVE_H1_SIGNAL_OHLC")
            class Calendar:
                def allowed(self, at):
                    try:
                        return at < session_deadline(at, paper.plan["holidays"])
                    except AdapterError:
                        return False
            intents = signals_from_closed_hours(hours, r["asset"], known, Calendar())
            for intent in intents:
                paper.offer(intent, known)
            paper.emit("NATIVE_CLOSED_HOURS_CONSUMED", known, asset=r["asset"],
                       bars=len(hours), signals=len(intents), source=r["source"])
        else:
            raise AdapterError("UNSUPPORTED_BRIDGE_EVENT")
        paper.last_time = known
    result = paper.report()
    result["fill_reconciliation"] = reconcile_fills(result["expected_fills"], bundle.get("external_fills", []))
    return result


def new_live_ticks(rows, previous_boundary):
    """Re-query inclusive last millisecond and retain every ordered duplicate."""
    if not previous_boundary:
        return rows
    at, saved = previous_boundary
    boundary = [r for r in rows if r["time_msc"] == at]
    signature = lambda r: (r["time_msc"], r["bid"], r["ask"], r.get("flags", 0))
    if [signature(r) for r in boundary[:len(saved)]] != saved:
        raise AdapterError("LIVE_CAPTURE_BOUNDARY_HISTORY_REVISED")
    return boundary[len(saved):] + [r for r in rows if r["time_msc"] > at]


def known_hour_seed(seed_spec, native_hours, now):
    """Keep a complete source-bound seed; never silently restart Wilder state."""
    path = Path(seed_spec["path"])
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != seed_spec["sha256"]:
        raise AdapterError("SIGNAL_SEED_CHECKSUM_MISMATCH")
    seed = json.loads(payload)
    if (seed.get("schema") != "v16-closed-hour-seed-v1" or seed.get("first") != 1509494400000 or
            not seed.get("rows") or seed["rows"][0]["t"] != seed["first"]):
        raise AdapterError("SIGNAL_SEED_ORIGIN_NOT_CANONICAL")
    if seed.get("known_at_msc", now + 1) > now or any(r["t"] + 3600000 > now for r in seed["rows"]):
        raise AdapterError("FUTURE_SIGNAL_SEED")
    by_time = {r["t"]: r for r in seed["rows"]}
    if len(by_time) != len(seed["rows"]) or sorted(by_time) != [r["t"] for r in seed["rows"]]:
        raise AdapterError("SIGNAL_SEED_DUPLICATE_OR_ORDER")
    for r in native_hours:
        if r["t"] in by_time and by_time[r["t"]] != r:
            raise AdapterError("BROKER_H1_SEED_OVERLAP_DIVERGENCE")
        by_time[r["t"]] = r
    return [by_time[t] for t in sorted(by_time)]


def run_native_shadow(reader, plan, output, *, max_seconds=60, poll_seconds=2, clock=None, sleeper=None):
    import time
    clock = clock or (lambda: int(time.time() * 1000))
    sleeper = sleeper or time.sleep
    if not 1 <= max_seconds <= 3600 or not 1 <= poll_seconds <= 10:
        raise AdapterError("BOUNDED_SHADOW_DURATION_OR_POLL_REQUIRED")
    now = clock()
    if not plan["from_msc"] <= now < plan["to_msc"]:
        raise AdapterError("NATIVE_SHADOW_OUTSIDE_OWNER_CAPTURE_WINDOW")
    verify_account(reader.account(), plan["binding"])
    if not all(asset in plan.get("signal_seeds", {}) for asset in ASSETS):
        raise AdapterError("CANONICAL_SIGNAL_SEEDS_REQUIRED_FOR_NATIVE_SHADOW")
    plan = dict(plan, from_msc=now, closed_M1_times={})
    for asset in ASSETS:
        plan["specs"][asset] = validate_spec(asset, reader.spec(asset))
        plan["closed_M1_times"][asset] = reader.closed_minutes(asset, now)
    with (output / "effective-paper-plan.json").open("x", encoding="utf-8") as f:
        json.dump({k: plan[k] for k in ("policy", "profile", "phase", "from_msc", "to_msc",
                                       "binding", "specs", "news", "holidays", "closed_M1_times", "signal_seeds") if k in plan}, f, indent=2)
    paper = ShadowPaper(plan, now, plan["to_msc"])
    boundary = {}
    last_hour, ordinal = None, 0
    deadline = min(plan["to_msc"], now + max_seconds * 1000)
    with (output / "native-shadow-events.jsonl").open("x", encoding="utf-8") as journal:
        def accept(event):
            nonlocal ordinal
            event["record_id"] = f"native:{ordinal}"
            ordinal += 1
            journal.write(json.dumps(event) + "\n")
            journal.flush()
        while now < deadline:
            verify_account(reader.account(), plan["binding"])
            paper.mark = reader.account_mark(now, 50000)
            accept(dict(kind="account_mark", known_at_msc=now, mark=paper.mark))
            if last_hour != now // 3600000:
                for asset in ASSETS:
                    hourly = known_hour_seed(plan["signal_seeds"][asset], reader.hourly(asset, now), now)
                    event = dict(kind="closed_hours", known_at_msc=now, asset=asset, rows=hourly,
                                 source="NATIVE_MT5_CLOSED_H1_BID")
                    accept(event)
                    import numpy as np
                    dtype = [(k, "<i8") for k in ("t", "bo", "bh", "bl", "bc")]
                    frame = np.array([tuple(r[k] for k, _ in dtype) for r in hourly], dtype=dtype)
                    class Calendar:
                        def allowed(self, at):
                            try:
                                return at < session_deadline(at, plan["holidays"])
                            except AdapterError:
                                return False
                    intents = signals_from_closed_hours(frame, asset, now, Calendar())
                    for intent in intents:
                        paper.offer(intent, now)
                    paper.emit("NATIVE_CLOSED_HOURS_CONSUMED", now, asset=asset,
                               bars=len(hourly), signals=len(intents), source=event["source"])
                last_hour = now // 3600000
            incoming = []
            for asset in ASSETS:
                first = boundary[asset][0] if asset in boundary else now
                rows = reader.ticks(asset, first, now + 1)
                incoming.extend(new_live_ticks(rows, boundary.get(asset)))
                if rows:
                    at = rows[-1]["time_msc"]
                    boundary[asset] = (at, [(r["time_msc"], r["bid"], r["ask"], r.get("flags", 0))
                                           for r in rows if r["time_msc"] == at])
            for r in sorted(incoming, key=lambda q: (q["time_msc"], ASSETS.index(q["asset"]))):
                event = dict(r, kind="quote", known_at_msc=now)
                accept(event)
                paper.advance(event)
            sleeper(min(poll_seconds, max(0, (deadline - now) / 1000)))
            now = clock()
    result = paper.report()
    result.update(mode="LIVE_SHADOW_PAPER", source_cross_asset_order="timestamp then fixed asset order",
                  actual_broker_orders=0, source_events=str(output / "native-shadow-events.jsonl"),
                  restart_requires_replay_and_binding_review=True)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("READ_ONLY", "SHADOW_PAPER"), nargs="?", default="READ_ONLY")
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attach-running-terminal", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=60)
    parser.add_argument("--poll-seconds", type=int, default=2)
    args = parser.parse_args()
    plan = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    args.output.mkdir(parents=True, exist_ok=False)
    reader = None
    try:
        if args.mode == "READ_ONLY":
            if args.bridge:
                reader = FileBridge(args.bridge)
            elif args.attach_running_terminal:
                reader = NativeMT5Reader(plan["terminal_path"])
            else:
                raise AdapterError("EXPLICIT_BRIDGE_OR_RUNNING_TERMINAL_REQUIRED")
            import time
            observed = int(time.time() * 1000) if isinstance(reader, NativeMT5Reader) else plan["observed_at_msc"]
            result = collect(reader, plan["binding"], plan["from_msc"], plan["to_msc"], observed_at=observed)
        else:
            if args.bridge is not None and not args.attach_running_terminal:
                result = reduce_bridge(FileBridge(args.bridge).bundle, plan)
            elif args.bridge is None and args.attach_running_terminal:
                reader = NativeMT5Reader(plan["terminal_path"])
                result = run_native_shadow(reader, plan, args.output,
                    max_seconds=args.max_seconds, poll_seconds=args.poll_seconds)
            else:
                raise AdapterError("EXPLICIT_BRIDGE_OR_RUNNING_TERMINAL_REQUIRED")
        with (args.output / "report.json").open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(dict(mode=args.mode, execution_capability=False, report=str(args.output / "report.json"))))
        return 0
    except AdapterError as exc:
        with (args.output / "failure.json").open("x", encoding="utf-8") as f:
            json.dump(dict(reason=str(exc), execution_capability=False), f)
        print(json.dumps(dict(error=str(exc), execution_capability=False)))
        return 2
    finally:
        if isinstance(reader, NativeMT5Reader):
            reader.close()


if __name__ == "__main__":
    raise SystemExit(main())
