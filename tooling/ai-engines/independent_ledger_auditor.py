"""Standalone Decimal ledger oracle. No Quant Core, producer PnL or DD imports."""
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

D = Decimal
CENT = D(".01")
DAY = 86400000
HOUR = 3600000


def cent(value):
    return D(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def swap_events(entry, exit_at, asset):
    result = []
    first, last = int(entry)//DAY, int(exit_at)//DAY
    for day in range(first, last+1):
        at = day*DAY+(0 if asset == "US500" else 22*HOUR)
        weekday = datetime.fromtimestamp(day*86400, timezone.utc).weekday()
        if entry < at <= exit_at and (asset == "US500" or weekday < 5):
            result.append((at, 3 if asset != "US500" and weekday == 2 else 1))
    return result


def cash_legs(trade, model, spec):
    lots, p0, px = (D(str(trade[n])) for n in ("lots", "entry_price", "exit_price"))
    sign = 1 if trade["direction"] == "BUY" else -1
    contract = D(str(spec["contract"]))
    asset = trade["symbol"]
    if model not in ("SYM", "ASYM") or lots <= 0:
        raise ValueError("unregistered_model_or_lots")
    if asset == "XAUUSD":
        fee0, feex = (cent(p*contract*lots*D(".000007")) for p in (p0, px))
        slip0 = cent(D(".20")*contract*lots)
        slipx = D(0) if model == "ASYM" and trade["reason"] == "TP" else slip0
        swap = D("-40") if model == "SYM" else D("-45" if sign == 1 else "-5")
    elif asset == "US500":
        fee0 = feex = cent(D(".5")*lots)
        slip0 = cent(D(".75")*lots)
        slipx = D(0) if model == "ASYM" and trade["reason"] == "TP" else slip0
        swap = D("-2")
    elif asset in ("EURUSD", "GBPUSD", "AUDUSD"):
        fee0 = feex = cent(D("3.5")*lots)
        slip0 = cent(lots)
        slipx = D(0) if model == "ASYM" and trade["reason"] == "TP" else slip0
        swap = D("-40")
    else:
        raise ValueError("asset_cost_missing")
    carry = [(at, cent(swap*lots*weight)) for at, weight in
             swap_events(trade["entry_time"], trade["exit_time"], asset)]
    gross = cent(sign*(px-p0)*contract*lots)
    net = gross-fee0-feex-slip0-slipx+sum((v for _, v in carry), D(0))
    return dict(gross=gross, commission=fee0+feex, slippage=slip0+slipx,
                swap=sum((v for _, v in carry), D(0)), net=net,
                entry_charge=-fee0-slip0, exit_credit=gross-feex-slipx, carry=carry)


def expected_deadline(trade, flats):
    entry, horizon = trade["entry_time"], trade["horizon"]
    future = [t for t in flats if t > entry]
    if not future:
        raise ValueError("calendar_future_missing")
    target = min(future)
    if horizon == "DAY":
        target = min(target, entry//DAY*DAY+int(20.5*HOUR))
    elif horizon in ("24H", "48H"):
        target = min(target, entry+int(horizon[:-1])*HOUR)
    elif horizon != "FRIDAY":
        raise ValueError("horizon_missing")
    if trade["symbol"] == "US500":
        local = datetime.fromtimestamp(target/1000, timezone.utc).astimezone(ZoneInfo("America/New_York"))
        if 975 <= local.hour*60+local.minute < 1080:
            target = int(local.replace(hour=16, minute=0, second=0, microsecond=0).timestamp()*1000)
    return target


def audit_trade(trade, source, spec, flats):
    """source=(timestamps, original integer OHLC rows), independently traversed."""
    times, bars = source
    step, scale = int(spec["step"]), D(str(spec["scale"]))
    entry, exit_at = int(trade["entry_time"]), int(trade["exit_time"])
    errors = []
    limit = expected_deadline(trade, flats)
    if entry > limit or exit_at > limit+60000 or exit_at < entry:
        errors.append("CALENDAR_OR_CLOCK")
    utc_entry = datetime.fromtimestamp(entry/1000, timezone.utc)
    if (utc_entry.weekday() >= 5 or utc_entry.weekday() == 4 and entry%DAY >= int(20.5*HOUR)
            or any(t//DAY == entry//DAY and t <= entry for t in flats)):
        errors.append("ENTRY_AFTER_SESSION_FLAT")
    sign = 1 if trade["direction"] == "BUY" else -1
    p0, natural_stop = D(str(trade["entry_price"])), D(str(trade["sl_price"]))
    natural = sign*(p0-natural_stop)
    start = bisect_left(times, entry)
    if start >= len(times) or times[start] != entry:
        return dict(passed=False, errors=errors+["ENTRY_SOURCE_MISSING"])
    own_entry = D(int(bars[start]["ao" if sign == 1 else "bo"]))/scale
    if p0 != own_entry:
        errors.append("ENTRY_PRICE")
    mode = trade["mode"]
    protected_at, protected_price = None, None
    expected_hit = None
    for i in range(start, bisect_right(times, min(exit_at, limit))):
        t = int(times[i])
        if t+step-1 > min(exit_at, limit):
            break
        row = bars[i]
        if i > start and int(times[i])-int(times[i-1]) > step:
            for missing in range(int(times[i-1])+step, int(times[i]), step):
                utc = datetime.fromtimestamp(missing/1000, timezone.utc)
                local = utc.astimezone(ZoneInfo("America/New_York"))
                minute = local.hour*60+local.minute
                asset = trade["symbol"]
                end_week = 975 if asset == "US500" else 1020
                start_week = 1080 if asset in ("XAUUSD", "US500") else 1020
                off = (utc.date().isoformat() in spec.get("closed_days", ()) or
                       local.weekday() == 5 or local.weekday() == 4 and minute >= end_week or
                       local.weekday() == 6 and minute < start_week or
                       asset == "XAUUSD" and 1020 <= minute < 1080 or
                       asset == "US500" and 975 <= minute < 1080)
                if not off:
                    errors.append("UNOBSERVED_PATH_GAP")
                    break
            if "UNOBSERVED_PATH_GAP" in errors:
                break
        stop = protected_price if protected_at is not None and t >= protected_at else natural_stop
        adverse = D(int(row["bl" if sign == 1 else "ah"]))/scale
        favorable = D(int(row["bh" if sign == 1 else "al"]))/scale
        opening = D(int(row["bo" if sign == 1 else "ao"]))/scale
        stop_hit = adverse <= stop if sign == 1 else adverse >= stop
        if stop_hit:
            fill = min(opening, stop) if sign == 1 else max(opening, stop)
            expected_hit = (t+step-1, fill, "PROTECT" if stop != natural_stop else "SL")
            break
        if mode == "P2" and sign*(favorable-p0) >= 3*natural:
            expected_hit = (t+step-1, p0+sign*3*natural, "TP")
            break
        if mode == "P1" and protected_at is None:
            mark = dict(trade, lots="1", exit_time=t+step-1, exit_price=str(favorable), reason="MARKET")
            value = cash_legs(mark, "SYM", spec)["net"]/D(str(spec["contract"]))
            if value >= D("1.5")*natural:
                protected_at = t+step
                # Exact independent quote-grid search at activation time.
                mark.update(exit_price=str(p0))
                drag = -cash_legs(mark, "SYM", spec)["net"]/D(str(spec["contract"]))
                candidate = p0+sign*(D(".15")*natural+drag)
                candidate = (candidate*scale).to_integral_value(rounding="ROUND_CEILING" if sign == 1 else "ROUND_FLOOR")/scale
                for _ in range(64):
                    mark.update(exit_price=str(candidate))
                    if cash_legs(mark, "SYM", spec)["net"]/D(str(spec["contract"])) >= D(".15")*natural:
                        protected_price = candidate
                        break
                    candidate += sign/scale
                if protected_price is None:
                    errors.append("PROTECTION_SEARCH")
                    break
                for _ in range(64):
                    mark["exit_price"] = str(protected_price-sign/scale)
                    if cash_legs(mark,"SYM",spec)["net"]/D(str(spec["contract"])) < D(".15")*natural:
                        break
                    protected_price -= sign/scale
    if expected_hit:
        if (exit_at, D(str(trade["exit_price"])), trade["reason"]) != expected_hit:
            errors.append("MISSED_OR_WRONG_FIRST_HIT")
    elif trade["reason"] != "HORIZON":
        errors.append("STOP_OR_TP_WITHOUT_WITNESS")
    else:
        j = bisect_left(times, limit)
        if j >= len(times) or times[j]-limit > 60000:
            errors.append("HORIZON_QUOTE_MISSING")
        elif exit_at != times[j] or D(str(trade["exit_price"])) != D(int(bars[j]["bo" if sign == 1 else "ao"]))/scale:
            errors.append("HORIZON_FILL")
    claimed = trade.get("protection_time")
    if claimed is not None and claimed != protected_at:
        errors.append("PROTECTION_TIMING")
    amount = cash_legs(trade, trade.get("cost_model", "SYM"), spec)
    for key in ("gross", "commission", "slippage", "swap", "net"):
        if key+"_usd" in trade and cent(trade[key+"_usd"]) != amount[key]:
            errors.append("CASH_"+key.upper())
    return dict(passed=not errors, errors=errors, net_usd=str(amount["net"]),
                first_hit=expected_hit, protection_time=protected_at)


def audit_equity(trades, observations, specs, *, initial="50000", model="SYM"):
    """Cent account audit from raw quote snapshots, with explicit midnight coverage."""
    initial = cent(initial)
    events = {}
    for trade in trades:
        legs = cash_legs(trade, model, specs[trade["symbol"]])
        for at, amount in [(trade["entry_time"], legs["entry_charge"]),
                           (trade["exit_time"], legs["exit_credit"]), *legs["carry"]]:
            events[at] = events.get(at, D(0))+amount
    points = sorted(observations, key=lambda x: x["at"])
    if not points or len({p["at"] for p in points}) != len(points):
        raise ValueError("quote_snapshots_missing_or_duplicate")
    tz = ZoneInfo("Europe/Prague")
    first_day = datetime.fromtimestamp(points[0]["at"]/1000, timezone.utc).astimezone(tz).date()
    last_day = datetime.fromtimestamp(points[-1]["at"]/1000, timezone.utc).astimezone(tz).date()
    observed = {p["at"] for p in points}
    day = first_day+timedelta(days=1)
    while day <= last_day:
        midnight = int(datetime.combine(day, datetime.min.time(), tz).timestamp()*1000)
        if midnight not in observed:
            raise ValueError("Prague_midnight_quote_missing")
        day += timedelta(days=1)
    cash, anchor, peak = initial, initial, initial
    worst_daily = worst_static = peak_to_valley = D(0)
    daily_witness = static_witness = None
    event_times = sorted(events)
    cursor, current_day = 0, first_day
    for snapshot in points:
        at = snapshot["at"]
        date = datetime.fromtimestamp(at/1000, timezone.utc).astimezone(tz).date()
        while cursor < len(event_times) and event_times[cursor] < at:
            cash += events[event_times[cursor]];cursor += 1
        if date != current_day:
            anchor, current_day = cash, date
        while cursor < len(event_times) and event_times[cursor] == at:
            cash += events[event_times[cursor]];cursor += 1
        floating = D(0)
        for trade in trades:
            if trade["entry_time"] <= at < trade["exit_time"]:
                bid, ask = snapshot["quotes"][trade["symbol"]]
                sign = 1 if trade["direction"] == "BUY" else -1
                px = D(str(bid if sign == 1 else ask))
                floating += cent(sign*(px-D(str(trade["entry_price"]))) *
                                 D(str(trade["lots"]))*D(str(specs[trade["symbol"]]["contract"])))
        equity = cash+floating
        daily_loss, static_loss = max(D(0), anchor-equity), max(D(0), initial-equity)
        if daily_loss > worst_daily:
            worst_daily, daily_witness = daily_loss, at
        if static_loss > worst_static:
            worst_static, static_witness = static_loss, at
        peak = max(peak, equity)
        peak_to_valley = max(peak_to_valley, peak-equity)
    return dict(final_balance=str(cash), worst_daily_usd=str(worst_daily),
        worst_static_usd=str(worst_static), peak_to_valley_usd=str(peak_to_valley),
        daily_witness=daily_witness, static_witness=static_witness,
        daily_breach=worst_daily >= initial*D(".05"),
        static_breach=worst_static >= initial*D(".10"),
        anchor="midnight Europe/Prague balance; costs and floating included",
        scope="provided raw quote snapshots; not unobserved intrabar path")
