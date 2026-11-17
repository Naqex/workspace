"""Shared USD account on interleaved admitted instrument ticks.

The existing Account owns lifecycle, resets, loss rules and rewards. This
adapter supplies instrument units, paired quote valuation and shared budgets.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import numpy as np

from prop_campaign_accounts import Account, stats, utc, CAPITAL, PRAGUE
from prop_portfolio_policy import requested_risk, within_open_risk_cap
from prop_campaign_source import START, END, FINAL, HOUR, DAY
from prop_campaign_exits import funding_rate
from xau_h1_execution import cents, commission
from xau_h1_stage0_scan import funding_events

ASSETS = ("XAUUSD", "EURUSD")
THREE_ASSETS = (*ASSETS, "GBPUSD")
FIELDS = {"XAUUSD": ("b0", "a0"), "EURUSD": ("b1", "a1")}
VALUE = {"XAUUSD": 1, "EURUSD": 10, "GBPUSD": 10}  # milli-USD / price grid / quantity step
SLIP = {"XAUUSD": 200, "EURUSD": 20, "GBPUSD": 20}
JOINT = np.dtype([("t", "<i8")] + [(n, "<i4") for n in ("b0", "a0", "b1", "a1")])
MINUTE = 60000


def checked_assets(assets):
    assets = tuple(assets)
    if assets not in (ASSETS, THREE_ASSETS):
        raise ValueError("unregistered_asset_order")
    return assets


def quote_fields(assets):
    return {asset: (f"b{i}", f"a{i}") for i, asset in enumerate(assets)}


def joint_dtype(assets=ASSETS, provenance=False):
    assets = checked_assets(assets)
    fields = [("t", "<i8")] + [
        (name, "<i4") for pair in quote_fields(assets).values() for name in pair]
    if provenance:
        fields += [("event_asset", "<i4"), ("event_ordinal", "<i8")]
        fields += [(f"{name}{i}", "<i8") for i in range(len(assets))
                   for name in ("quote_t", "quote_hour", "quote_ordinal")]
    return np.dtype(fields)


def merged_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


class QuoteAgeCoverage:
    """Sparse source gaps, intersected with actual accepted holdings after replay."""
    def __init__(self, assets):
        self.assets = assets
        self.last = {}
        self.gaps = {asset: [] for asset in assets}

    def observe(self, asset, hour, ticks):
        if not len(ticks):
            return
        previous = self.last.get(asset)
        times = ticks["t"]
        if previous and int(times[0]) < previous["last_quote_msc"]:
            raise ValueError("coverage_source_time_reversed")
        if previous and int(times[0]) - previous["last_quote_msc"] > MINUTE:
            self.gaps[asset].append(dict(previous, end_msc=int(times[0])))
        for i in np.flatnonzero(np.diff(times) > MINUTE):
            self.gaps[asset].append(dict(
                last_quote_msc=int(times[i]), source_hour=hour,
                source_ordinal=int(i), end_msc=int(times[i + 1])))
        self.last[asset] = dict(last_quote_msc=int(times[-1]), source_hour=hour,
                                source_ordinal=len(ticks) - 1)

    def finish(self, end):
        for asset, previous in self.last.items():
            if end - previous["last_quote_msc"] > MINUTE:
                self.gaps[asset].append(dict(previous, end_msc=end))

    def account(self, account, trades):
        cap = min(account.end, account.breach["at"]) if account.breach else account.end
        holdings = {asset: [] for asset in self.assets}
        for accepted in account.accepted:
            trade = trades[accepted["trade"]]
            holdings[trade["asset"]].append(
                (accepted["at"], min(trade["exit_msc"], cap)))
        result, all_held, all_unknown = {}, [], []
        for asset, intervals in holdings.items():
            held = merged_intervals(intervals)
            all_held.extend(held)
            duration = sum(end - start for start, end in held)
            over60 = unknown = 0
            unknown_intervals = []
            for gap in self.gaps[asset]:
                for start, end in held:
                    left, right = max(start, gap["last_quote_msc"] + MINUTE), min(end, gap["end_msc"])
                    over60 += max(0, right - left)
                    left = max(start, gap["last_quote_msc"] + 15 * MINUTE)
                    if right > left:
                        unknown += right - left
                        unknown_intervals.append(dict(
                            start_msc=left, end_msc=right, duration_ms=right - left,
                            last_quote_msc=gap["last_quote_msc"],
                            source_hour=gap["source_hour"], source_ordinal=gap["source_ordinal"]))
                        all_unknown.append((left, right))
            if not 0 <= unknown <= over60 <= duration:
                raise ValueError("quote_age_duration_bridge")
            result[asset] = dict(
                held_ms=duration, fresh_ms=duration - over60,
                middle_ms=over60 - unknown, unknown_ms=unknown,
                unknown_fraction=unknown / duration if duration else 0,
                unknown_intervals=unknown_intervals)
        wall_held = sum(b - a for a, b in merged_intervals(all_held))
        wall_unknown = sum(b - a for a, b in merged_intervals(all_unknown))
        return dict(
            assets=result, held_wall_ms=wall_held, unknown_wall_ms=wall_unknown,
            elapsed_held_ms=wall_held, unknown_over_15min_ms=wall_unknown,
            path_complete=wall_unknown == 0,
            unknown_wall_fraction=wall_unknown / wall_held if wall_held else 0,
            status="DATA_PATH_INCOMPLETE" if wall_unknown else "OBSERVED_SOURCE_AGE_WITHIN_15_MIN",
            scheduled_closures_exempted=False, observed_quotes_only=True)


def quantity_steps(trade, risk):
    value = VALUE[trade["asset"]] * abs(trade["entry_price_units"] - trade["stop_units"])
    quantity = int(risk * 1000) // value
    if not 1 <= quantity <= (5000 if trade["asset"] == "XAUUSD" else 100000):
        raise ValueError("position_grid")
    return quantity


def entry_exit_fee(trade, price, quantity):
    if trade["asset"] == "XAUUSD":
        return cents(commission(price, quantity)) * 10
    return cents(Decimal(quantity) * Decimal(".025")) * 10


def funding_step(trade, model):
    if trade["asset"] == "XAUUSD":
        return int(round(funding_rate(trade["side"], model) * 1000))
    return -400  # declared -$40 / lot; one quantity step = .01 lot


def rounded_cent_milli(value):
    return (1 if value >= 0 else -1) * ((abs(value) + 5) // 10) * 10


def trade_money(trade, quantity, model, risk):
    sign = 1 if trade["side"] == "BUY" else -1
    gross = rounded_cent_milli(sign * quantity * VALUE[trade["asset"]] *
                               (trade["exit_price_units"] - trade["entry_price_units"]))
    fees = sum(entry_exit_fee(trade, price, quantity) for price in (
        trade["entry_price_units"], trade["exit_price_units"]))
    slippage = quantity * SLIP[trade["asset"]] * 2
    swap = quantity * funding_step(trade, model) * sum(
        e["multiplier"] for e in funding_events(trade["entry_msc"], trade["exit_msc"]))
    net = gross - fees - slippage + swap
    return dict(gross_usd=gross / 1000, commission_usd=fees / 1000,
                slippage_usd=slippage / 1000, swap_usd=swap / 1000,
                net_usd=net / 1000, net_R=net / (risk * 1000))


class PortfolioAccount(Account):
    def __init__(self, *args, include_satellite=True, scaled=False, assets=ASSETS,
                 included_assets=None, fixed_asset_risk=None, track_quote_age=False,
                 common_risk_usd=150, **kwargs):
        super().__init__(*args, **kwargs)
        self.assets = checked_assets(assets)
        self.fields = quote_fields(self.assets)
        self.included_assets = tuple(self.assets if included_assets is None else included_assets)
        if (not self.included_assets or
                self.included_assets != tuple(a for a in self.assets if a in self.included_assets)):
            raise ValueError("unregistered_included_assets")
        if fixed_asset_risk is not None:
            if (scaled or set(fixed_asset_risk) != set(self.assets) or
                    any(type(v) not in (int, float) or not np.isfinite(v) or v <= 0
                        for v in fixed_asset_risk.values())):
                raise ValueError("invalid_fixed_asset_risk")
            fixed_asset_risk = dict(fixed_asset_risk)
        if type(common_risk_usd) not in (int, float) or not np.isfinite(common_risk_usd) or common_risk_usd <= 0:
            raise ValueError("invalid_common_risk")
        self.fixed_asset_risk = fixed_asset_risk
        self.track_quote_age = track_quote_age
        self.common_risk_usd = common_risk_usd
        self.include_satellite = include_satellite
        self.scaled = scaled
        self.day_halt = False
        self.risk_buckets = Counter()
        self.maximum_stop_exposure = 0
        self.rejection_records = []
        self.quote_age_marks = []
        self.quote_age_coverage = None
        self.breach_snapshot = None

    def open_entry_fee(self, trade, quantity):
        return entry_exit_fee(trade, trade["entry_price_units"], quantity)

    def quote_provenance(self, at, quote, assets):
        if not assets:
            return {}
        if quote is None:
            raise ValueError("missing_open_mark")
        result = {}
        for asset in sorted(set(assets), key=self.assets.index):
            rank = self.assets.index(asset)
            bid, ask = (int(quote[f]) for f in self.fields[asset])
            stamp, hour, ordinal = (int(quote[f"{name}{rank}"])
                                    for name in ("quote_t", "quote_hour", "quote_ordinal"))
            if (not 0 < bid <= ask or stamp < 0 or stamp > int(quote["t"]) or
                    int(quote["t"]) > at or hour != stamp // HOUR * HOUR or ordinal < 0):
                raise ValueError("held_quote_provenance_invalid_or_future")
            if (stamp == int(quote["t"]) and
                    (rank, ordinal) > (int(quote["event_asset"]), int(quote["event_ordinal"]))):
                raise ValueError("held_quote_future_same_millisecond")
            result[asset] = dict(
                quote_msc=stamp, age_ms=at - stamp, source_hour=hour,
                source_ordinal=ordinal, bid_units=bid, ask_units=ask)
        return result

    def reject(self, reason, at, i, trades, quote, **state):
        self.rejected[reason] += 1
        if self.fixed_asset_risk is not None:
            self.rejection_records.append(dict(
                trade=i, at=at, reason=reason, phase=self.phase, asset=trades[i]["asset"],
                state=dict(balance_milli_usd=self.balance,
                           equity_milli_usd=self.balance + self.floating(trades, quote),
                           daily_anchor_milli_usd=self.anchor, gate_msc=self.gate,
                           active_trades=sorted(self.active), **state)))

    def check(self, at, floating):
        previous = self.breach
        super().check(at, floating)
        if self.breach and previous is None:
            positions = [dict(
                trade=i, asset=self._trades[i]["asset"], quantity_steps=q,
                risk_usd=risk, accrued_milli_usd=self.accrued[i],
                entry_fee_milli_usd=self.open_entry_fee(self._trades[i], q))
                for i, (q, risk) in sorted(self.active.items())]
            self.breach_snapshot = dict(
                at=at, phase=self.phase, balance_milli_usd=self.balance,
                daily_anchor_milli_usd=self.anchor, floating_milli_usd=self.float,
                equity_milli_usd=self.balance + self.float,
                phase_dd_milli_usd=self.phase_dd, phase_daily_milli_usd=self.phase_daily,
                positions=positions,
                quotes=self.quote_provenance(at, self.last_quote, [r["asset"] for r in positions])
                if self.track_quote_age else None,
                liquidated=False)

    def floating(self, trades, quote):
        value = 0
        for i, (q, _) in self.active.items():
            t = trades[i]
            if quote is None:
                raise ValueError("missing_open_mark")
            field = self.fields[t["asset"]][0 if t["side"] == "BUY" else 1]
            price = int(quote[field])
            if price <= 0:
                raise ValueError("active_asset_quote_unknown")
            sign = 1 if t["side"] == "BUY" else -1
            value += (sign * q * VALUE[t["asset"]] *
                      (price - t["entry_price_units"])
                      - q * SLIP[t["asset"]] + self.accrued[i])
        return value

    def reserve_floor(self, trades, new_id, q, entry_fee):
        value = self.balance - entry_fee
        positions = dict(self.active)
        positions[new_id] = (q, 0)
        for i, (size, _) in positions.items():
            t = trades[i]
            end = t.get("deadline_msc")
            if type(end) is not int or end < t["entry_msc"]:
                raise ValueError("missing_prelocked_funding_horizon")
            sign = 1 if t["side"] == "BUY" else -1
            value += sign * size * VALUE[t["asset"]] * (
                t["stop_units"] - t["entry_price_units"])
            value -= size * SLIP[t["asset"]] * 2
            value -= entry_exit_fee(t, t["stop_units"], size)
            value += min(0, funding_step(t, self.cell)) * size * sum(
                e["multiplier"] for e in funding_events(t["entry_msc"], end))
        return value

    def action(self, kind, at, i, trades, quote, mult=0):
        if at < self.start or at >= self.end or self.breach:
            return
        self._trades = trades
        self.last_quote = quote
        if self.track_quote_age:
            held_assets = [trades[k]["asset"] for k in self.active]
            if kind == "entry" and trades[i]["asset"] in self.included_assets:
                held_assets.append(trades[i]["asset"])
            marks = self.quote_provenance(at, quote, held_assets)
            if marks:
                self.quote_age_marks.append(dict(at=at, kind=kind, trade=i, assets=marks))
        if kind == "reset":
            self.day_halt = False
            self.daily_marks.append([at, self.balance + self.floating(trades, quote)])
            if self.track_quote_age and self.active:
                self.stale_resets.append(dict(at=at, assets=marks, active=len(self.active)))
            self.anchor = self.balance
            if self.rolling:
                self.reward(at)
        elif kind == "entry":
            t = trades[i]
            if t["asset"] not in self.included_assets:
                self.reject("ASSET_NOT_IN_SYSTEM", at, i, trades, quote)
                return
            if t["role"] == "SATELLITE" and not self.include_satellite:
                self.reject("SYSTEM_HAS_NO_SATELLITE", at, i, trades, quote)
                return
            if t["decision_msc"] < self.start or t["decision_msc"] <= self.gate:
                self.reject("PRESTART_OR_PHASE_GATE", at, i, trades, quote)
                return
            if any(trades[k]["asset"] == t["asset"] and
                   trades[k]["decision_msc"] == t["decision_msc"] for k in self.active):
                self.reject("ASSET_DECISION_COLLISION", at, i, trades, quote)
                return
            if self.day_halt or self.balance - self.anchor <= -1000000:
                self.day_halt = True
                self.reject("DAILY_REALIZED_2PCT_HALT", at, i, trades, quote)
                return
            equity = self.balance + self.floating(trades, quote)
            weight = t.get("regime_weight", 1) if self.scaled else 1
            risk = (self.fixed_asset_risk[t["asset"]] if self.fixed_asset_risk is not None
                    else requested_risk(self.phase, equity, t["role"], weight))
            try:
                q = quantity_steps(t, risk)
            except ValueError:
                self.reject("LOT_GRID_MIN_MAX", at, i, trades, quote, risk_usd=risk)
                return
            old_risk = sum(
                size * VALUE[trades[k]["asset"]] *
                abs(trades[k]["entry_price_units"] - trades[k]["stop_units"])
                for k, (size, _) in self.active.items())
            new_risk = q * VALUE[t["asset"]] * abs(t["entry_price_units"] - t["stop_units"])
            if not within_open_risk_cap(old_risk, new_risk):
                self.reject("OPEN_STOP_RISK_1PCT_CAP", at, i, trades, quote,
                            risk_usd=risk, prior_stop_risk_milli_usd=old_risk,
                            new_stop_risk_milli_usd=new_risk)
                return
            fee = entry_exit_fee(t, t["entry_price_units"], q)
            projected = self.reserve_floor(trades, i, q, fee)
            if projected <= 46500000:
                self.reject("INTERNAL_STATIC_7PCT_RESERVE", at, i, trades, quote,
                            risk_usd=risk, projected_stop_milli_usd=projected)
                return
            if projected < max(self.anchor - 2500000, 45000000):
                self.reject("SHARED_STOP_RESERVE", at, i, trades, quote,
                            risk_usd=risk, projected_stop_milli_usd=projected)
                return
            state = dict(
                balance_milli_usd=self.balance, equity_milli_usd=equity,
                daily_anchor_milli_usd=self.anchor, role=t["role"], weight=weight,
                risk_usd=risk, prior_stop_risk_milli_usd=old_risk,
                new_stop_risk_milli_usd=new_risk, projected_stop_milli_usd=projected,
            )
            self.balance -= fee
            self.active[i] = (q, risk)
            self.accrued[i] = 0
            self.accepted.append(dict(
                trade=i, at=at, phase=self.phase, risk_usd=risk,
                ounces=q, quantity_steps=q, asset=t["asset"], risk_state=state,
            ))
            self.risk_buckets[str(risk)] += 1
            self.maximum_stop_exposure = max(self.maximum_stop_exposure, old_risk + new_risk)
            self.phase_days.add(utc(at).astimezone(PRAGUE).date().isoformat())
            self.max_concurrency = max(self.max_concurrency, len(self.active))
            if self.phase == 3 and self.funded_first is None:
                self.funded_first = at
        elif kind == "swap":
            if i in self.active:
                self.accrued[i] += self.active[i][0] * funding_step(trades[i], self.cell) * mult
        elif kind == "exit":
            if i not in self.active:
                return
            q, risk = self.active.pop(i)
            self.accrued.pop(i)
            t = trades[i]
            money = trade_money(t, q, self.cell, risk)
            self.balance += (int(round(money["net_usd"] * 1000))
                             + entry_exit_fee(t, t["entry_price_units"], q))
            self.closed.append(dict(trade=i, at=at, phase=self.phase,
                                    risk_usd=risk, net_usd=money["net_usd"],
                                    net_R=money["net_R"], costs=money))
        self.check(at, self.floating(trades, quote))
        if self.balance - self.anchor <= -1000000:
            self.day_halt = True
        if kind == "exit" and self.rolling and not self.breach:
            self.reward(at)

    def segment(self, rows, trades, cache):
        if not self.active or self.breach or not len(rows):
            return
        if self.track_quote_age:
            for asset in {trades[i]["asset"] for i in self.active}:
                validation_key = ("provenance_checked", asset)
                if validation_key in cache:
                    continue
                rank = self.assets.index(asset)
                stamps = rows[f"quote_t{rank}"]
                bid, ask = (rows[name] for name in self.fields[asset])
                if (np.any(stamps < 0) or np.any(stamps > rows["t"]) or
                        np.any(rows[f"quote_hour{rank}"] != stamps // HOUR * HOUR) or
                        np.any(rows[f"quote_ordinal{rank}"] < 0) or
                        np.any(bid <= 0) or np.any(ask < bid)):
                    raise ValueError("held_quote_provenance_invalid_or_future")
                same = stamps == rows["t"]
                if np.any(same & (
                        (rank > rows["event_asset"]) |
                        ((rank == rows["event_asset"]) &
                         (rows[f"quote_ordinal{rank}"] > rows["event_ordinal"])))):
                    raise ValueError("held_quote_future_same_millisecond")
                cache[validation_key] = True
        key = tuple(sorted((i, q) for i, (q, _) in self.active.items()))
        if key not in cache:
            values = np.zeros(len(rows), dtype="int64")
            for i, q in key:
                t = trades[i]
                buy = t["side"] == "BUY"
                field = self.fields[t["asset"]][0 if buy else 1]
                if np.any(rows[field] <= 0):
                    raise ValueError("held_asset_missing_joint_quote")
                values += (1 if buy else -1) * q * VALUE[t["asset"]] * (
                    rows[field].astype("int64") - t["entry_price_units"])
            cache[key] = (stats(values), values)
        summary, values = cache[key]
        offset = self.balance + sum(self.accrued.values()) - sum(
            q * SLIP[trades[i]["asset"]] for i, (q, _) in self.active.items())
        if self.rolling and offset + summary["low"] < max(self.anchor - 2500000, 45000000):
            index = int(np.flatnonzero(offset + values < max(
                self.anchor - 2500000, 45000000))[0])
            part = stats(values[:index + 1])
            self.metrics(offset + part["low"], offset + part["high"], part["dd"])
            self._trades = trades
            self.last_quote = rows[index]
            self.check(int(rows["t"][index]), offset + int(values[index]) - self.balance)
            return
        self.metrics(offset + summary["low"], offset + summary["high"], summary["dd"])
        self.float = offset + summary["last"] - self.balance

    def dump(self):
        if self.active and not self.breach:
            raise ValueError("portfolio_cutoff_not_flat")
        row = super().dump()
        row.update(include_satellite=self.include_satellite,
                   risk_buckets=dict(self.risk_buckets),
                   maximum_open_stop_risk_pct=self.maximum_stop_exposure / 500000,
                   policy="fixed_asset_risk_joint_ticks" if self.fixed_asset_risk is not None
                   else "V3_balanced_joint_ticks", d1_scaled=self.scaled,
                   assets=list(self.assets), included_assets=list(self.included_assets),
                   fixed_asset_risk=self.fixed_asset_risk,
                   portfolio_common_R=row["net_usd"] / self.common_risk_usd,
                   equity_DD_common_R=self.dd / (1000 * self.common_risk_usd),
                   common_risk_usd=self.common_risk_usd,
                   rejection_records=self.rejection_records,
                   quote_age_marks=self.quote_age_marks,
                   quote_age_coverage=self.quote_age_coverage,
                   breach_snapshot=self.breach_snapshot,
                   accounting_model="legacy_accrued_funding_until_exit_one_leg_float_slip",
                   reward_model="legacy_30day_80pct_flat_proxy_resets_anchor",
                   target_specs_news_margin_and_forward_verified=False)
        return row


def joint_hour(readers, hour, last, *, assets=ASSETS, provenance=False):
    assets = checked_assets(assets)
    fields = quote_fields(assets)
    dtype = joint_dtype(assets, provenance)
    chunks = []
    for asset_index, asset in enumerate(assets):
        reader = readers[asset]
        if hour not in reader.files:
            continue
        ticks = reader.hour(hour)
        if len(ticks):
            if (np.any(ticks["t"] < hour) or np.any(ticks["t"] >= hour + HOUR) or
                    np.any(np.diff(ticks["t"]) < 0) or np.any(ticks["b"] <= 0) or
                    np.any(ticks["a"] < ticks["b"])):
                raise ValueError("joint_native_quote_schema")
            chunks.append((asset_index, ticks))
    if not chunks:
        return np.empty(0, dtype=dtype), [np.array([], dtype="int64") for _ in assets]
    times = np.concatenate([v["t"] for _, v in chunks])
    instruments = np.concatenate([np.full(len(v), a) for a, v in chunks])
    ordinals = np.concatenate([np.arange(len(v)) for _, v in chunks])
    bid = np.concatenate([v["b"] for _, v in chunks])
    ask = np.concatenate([v["a"] for _, v in chunks])
    order = np.lexsort((ordinals, instruments, times))
    instruments, times, ordinals, bid, ask = [v[order] for v in (instruments, times, ordinals, bid, ask)]
    result = np.empty(len(times), dtype=dtype)
    result["t"] = times
    if provenance:
        result["event_asset"] = instruments
        result["event_ordinal"] = ordinals
    maps = []
    for a, asset in enumerate(assets):
        source = np.flatnonzero(instruments == a)
        maps.append(source)
        indices = np.maximum.accumulate(np.where(instruments == a, np.arange(len(times)), -1))
        known = indices >= 0
        for name, values in zip(fields[asset], (bid, ask)):
            result[name] = last[name] if last is not None else 0
            result[name][known] = values[indices[known]]
        if provenance:
            for name, values in (
                    (f"quote_t{a}", times),
                    (f"quote_hour{a}", times // HOUR * HOUR),
                    (f"quote_ordinal{a}", ordinals)):
                result[name] = last[name] if last is not None else -1
                result[name][known] = values[indices[known]]
    return result, maps


def prague_midnights(start, end):
    day = utc(start).astimezone(PRAGUE).date()
    final_day = utc(end).astimezone(PRAGUE).date()
    while day <= final_day:
        at = int(datetime(day.year, day.month, day.day, tzinfo=PRAGUE).timestamp() * 1000)
        if start <= at < end:
            yield at
        day += timedelta(days=1)


def replay(trades, readers, accounts, end=FINAL, progress=None, *, assets=ASSETS):
    assets = checked_assets(assets)
    if set(readers) != set(assets) or any(account.assets != assets for account in accounts):
        raise ValueError("account_reader_asset_mismatch")
    if assets == THREE_ASSETS and (end > END or any(getattr(r, "cutoff", END) > END for r in readers.values())):
        raise ValueError("three_asset_Development_cutoff")
    provenance = any(account.track_quote_age for account in accounts)
    coverage = QuoteAgeCoverage(assets) if provenance else None
    for account in accounts:
        account._trades = trades
    if not trades:
        if coverage is not None:
            for account in accounts:
                account.quote_age_coverage = coverage.account(account, trades)
        return [dict(account.dump(), joint_tick_marks=0) for account in accounts]
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        if (t["asset"] not in assets or not START <= t["decision_msc"] <= t["entry_msc"] <= t["exit_msc"] < end or
                t["entry_quote_index"] < 0 or t["exit_quote_index"] < 0):
            raise ValueError("trade_outside_replay_scope")
        a = assets.index(t["asset"])
        actions[(t["entry_msc"], a, t["entry_quote_index"])].append(("entry", i, 0))
        actions[(t["exit_msc"], a, t["exit_quote_index"])].append(("exit", i, 0))
        for f in funding_events(t["entry_msc"], t["exit_msc"]):
            actions[(f["at"], -1, -1)].append(("swap", i, f["multiplier"]))
    for at in prague_midnights(START, end):
        actions[(at, -1, -1)].append(("reset", None, 0))
    keys = sorted(actions)
    cursor = 0
    last = None
    active = set()
    ticks_seen = 0
    priority = {"reset": 0, "swap": 1, "exit": 2, "entry": 3}

    def consume(rows):
        nonlocal last, ticks_seen
        if not len(rows):
            return
        caches = {}
        for account in accounts:
            lo = int(rows["t"].searchsorted(account.start))
            hi = int(rows["t"].searchsorted(account.end))
            if hi > lo:
                account.segment(rows[lo:hi], trades, caches.setdefault((lo, hi), {}))
        last = rows[-1]
        if active:
            ticks_seen += len(rows)

    first = min(t["entry_msc"] for t in trades) // HOUR * HOUR
    for hour in range(first, end, HOUR):
        for i in active:
            reader = readers[trades[i]["asset"]]
            if hour not in reader.files:
                raise ValueError("held_asset_tick_hour_unadmitted")
        if coverage is not None:
            for asset in assets:
                if hour in readers[asset].files:
                    coverage.observe(asset, hour, readers[asset].hour(hour))
        rows, maps = joint_hour(readers, hour, last, assets=assets, provenance=provenance)
        j = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            key = keys[cursor]
            at, asset, ordinal = key
            if asset >= 0 and not 0 <= ordinal < len(maps[asset]):
                raise ValueError("joint_tick_ordinal_missing")
            cut = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][ordinal])
            consume(rows[j:cut])
            if asset >= 0:
                if rows["t"][cut] != at:
                    raise ValueError("joint_tick_ordinal")
                last = rows[cut]
                for account in accounts:
                    if account.start <= at < account.end and not account.breach:
                        account.last_quote = last
                        if account.track_quote_age:
                            account.quote_provenance(at, last, [trades[k]["asset"] for k in account.active])
                        account.check(at, account.floating(trades, last))
            for kind, i, mult in sorted(
                    actions[key], key=lambda r: (
                        priority[r[0]], trades[r[1]]["role"] == "SATELLITE"
                        if r[1] is not None else False)):
                for account in accounts:
                    account.action(kind, at, i, trades, last, mult)
                if kind == "entry":
                    active.add(i)
                elif kind == "exit":
                    active.remove(i)
            j = cut
            cursor += 1
        consume(rows[j:])
        if progress is not None and hour % (1000 * HOUR) == 0:
            progress("joint_tick_replay", hour=utc(hour).isoformat(), ticks=ticks_seen)
    if active:
        raise ValueError("joint_tick_replay_not_flat")
    if coverage is not None:
        coverage.finish(end)
        for account in accounts:
            if account.track_quote_age:
                account.quote_age_coverage = coverage.account(account, trades)
    return [dict(account.dump(), joint_tick_marks=ticks_seen) for account in accounts]
