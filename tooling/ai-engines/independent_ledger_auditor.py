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


def source_off_kind(at, asset, spec):
    """Own scalar calendar interpretation; no producer session helper."""
    utc = datetime.fromtimestamp(int(at)/1000, timezone.utc)
    local = utc.astimezone(ZoneInfo("America/New_York"))
    minute = local.hour*60+local.minute
    if asset == "US500":
        if local.weekday()==5 or local.weekday()==4 and minute>=975 or local.weekday()==6 and minute<1080:
            return "WEEKEND"
        if 975<=minute<1080:return "DAILY_BREAK"
    if (local.weekday() == 5 or local.weekday() == 4 and minute >= 1020 or
            local.weekday() == 6 and minute < (1080 if asset == "XAUUSD" else 1020)):
        return "WEEKEND"
    row = spec.get("session_events", {}).get(utc.date().isoformat(), {})
    if row.get("kind") == "CLOSED":
        return "DECLARED_HOLIDAY"
    if row.get("flat_utc") and utc.strftime("%H:%M") >= row["flat_utc"] and local.hour < 18:
        return "DECLARED_EARLY_GUARD"
    if asset == "XAUUSD" and 1020 <= minute < 1080:
        return "DAILY_BREAK"
    return None


def audit_trade(trade, source, spec, flats):
    """source=(timestamps, original integer OHLC rows), independently traversed."""
    times, bars = source
    step, scale = int(spec["step"]), D(str(spec["scale"]))
    entry, exit_at = int(trade["entry_time"]), int(trade["exit_time"])
    errors = []
    limit = expected_deadline(trade, flats)
    gap_scenario = spec.get("gap_policy") == "V13_NEXT_QUOTE"
    uncertain_gaps = []
    if gap_scenario:
        if source_off_kind(limit, trade["symbol"], spec) == "DAILY_BREAK":
            local = datetime.fromtimestamp(limit/1000, timezone.utc).astimezone(ZoneInfo("America/New_York"))
            limit = int(local.replace(hour=18, minute=0, second=0, microsecond=0).timestamp()*1000)
        scheduled = limit
        target_index = bisect_left(times, limit)
        if target_index < len(times):
            limit = int(times[target_index])
        if "scheduled_deadline" in trade and trade["scheduled_deadline"] != scheduled:
            errors.append("SCHEDULED_DEADLINE")
        if "effective_deadline" in trade and trade["effective_deadline"] != limit:
            errors.append("DEFERRED_DEADLINE")
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
        if t+step-1 > min(exit_at, limit) and not (gap_scenario and t == exit_at):
            break
        row = bars[i]
        if i > start and int(times[i])-int(times[i-1]) > step:
            unknown = False
            for missing in range(int(times[i-1])+step, int(times[i]), step):
                if gap_scenario:
                    if source_off_kind(missing, trade["symbol"], spec) is None:
                        unknown = True
                    continue
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
            if unknown:
                uncertain_gaps.append((int(times[i-1]), t))
            if "UNOBSERVED_PATH_GAP" in errors:
                break
        stop = protected_price if protected_at is not None and t >= protected_at else natural_stop
        adverse = D(int(row["bl" if sign == 1 else "ah"]))/scale
        favorable = D(int(row["bh" if sign == 1 else "al"]))/scale
        opening = D(int(row["bo" if sign == 1 else "ao"]))/scale
        opening_hit = opening <= stop if sign == 1 else opening >= stop
        if gap_scenario and opening_hit:
            expected_hit = (t, opening, "PROTECT" if stop != natural_stop else "SL")
            break
        # The endpoint open supplies no high/low information from the coming minute.
        if gap_scenario and t+step-1 > min(exit_at, limit):
            break
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
    if gap_scenario and "source_uncertain" in trade and bool(trade["source_uncertain"]) != bool(uncertain_gaps):
        errors.append("SOURCE_UNCERTAINTY_LABEL")
    return dict(passed=not errors, errors=errors, net_usd=str(amount["net"]),
                first_hit=expected_hit, protection_time=protected_at,
                uncertain_gaps=uncertain_gaps, source_complete=not uncertain_gaps,
                execution_scenario=gap_scenario)


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


def bridge_screen(side,level,before,after,minutes,sigma,adjacent_range,envelope,*,first=None,end=None):
    """Conditional source envelope or diffusion diagnostic, never a market bound."""
    from math import exp,isfinite,log,sqrt
    if side not in (-1,1) or minutes<=0:raise ValueError("invalid_bridge_contract")
    d0,d1=side*(before-level),side*(after-level)
    minimum=min(d0,d1)
    envelope_ok=(envelope.get("available") and envelope.get("complete_export_assumption") and
        not envelope.get("derived_from_gappy_M1",True) and
        envelope.get("origin") in ("RECORDED_NATIVE_TICK_ENVELOPE","PROVIDER_NATIVE_HTF") and
        first is not None and end is not None and envelope.get("first",end)<=first and
        envelope.get("end",first)>=end)
    extreme=envelope.get("bid_low") if side==1 else envelope.get("ask_high")
    exclusion=bool(envelope_ok and extreme is not None and side*(extreme-level)>0 and minimum>0)
    valid_sigma=sigma is not None and isfinite(sigma) and sigma>0
    threshold=3*sigma*sqrt(minutes) if valid_sigma else None
    log_p=-2*d0*d1/(sigma*sigma*minutes) if valid_sigma and minimum>0 else (0. if minimum<=0 else None)
    probability=exp(max(log_p,-745)) if log_p is not None else None
    low_risk=minimum>0 and valid_sigma and minimum>threshold and minimum>2*adjacent_range
    status=("ENDPOINT_TOUCH_OR_BEYOND_STOP" if minimum<=0 else
        "SOURCE_ENVELOPE_EXCLUDES_SL" if exclusion else "MODEL_LOW_RISK" if low_risk else "AMBIGUOUS")
    return dict(status=status,signed_distances=[d0,d1],minimum_distance=minimum,
        sigma_threshold=threshold,adjacent_threshold=2*adjacent_range,
        model_log_hit_probability=log_p,model_hit_probability=probability,
        conditional_source_exclusion=exclusion,market_certificate=False,
        deterministic_bound=False,positive_model_tail=bool(valid_sigma and minimum>0),
        model_assumptions="constant estimated sigma, continuous Gaussian bridge; jumps/feed omissions not bounded")


def audit_duration_censorship(trades,claimed):
    """Own medians/counters; no assertion that all removed trades are winners."""
    groups={}
    for label,flag in (("NO_UNKNOWN_GAP",False),("UNKNOWN_GAP",True)):
        rows=[t for t in trades if bool(t["source_uncertain"])==flag]
        v=sorted((t["exit_msc"]-t["entry_msc"])/3600000 for t in rows)
        middle=(v[(len(v)-1)//2]+v[len(v)//2])/2 if v else None
        wins=sum(t["reference"]["SYM"]["net_R"]>0 for t in rows)
        losses=sum(t["reference"]["SYM"]["net_R"]<0 for t in rows)
        c=claimed[label]
        if (len(rows),middle,wins,losses)!=(c["trades"],c["median_hours"],c["wins"],c["losses"]):
            raise ValueError("duration_censorship_counter_or_median")
        groups[label]=dict(trades=len(rows),median_hours=middle,wins=wins,losses=losses)
    return dict(passed=True,groups=groups,causal_proof=False,ex_post_selection=True)


def v14_parts(t, quantity, model):
    """Own Decimal cash legs at actual lot size, never producer money()."""
    gold=t["asset"]=="XAUUSD"
    q=quantity
    row=dict(symbol=t["asset"],direction=t["side"],lots=str(D(q)/(100 if gold else 100)),
        entry_price=str(D(t["entry_price_units"])/(1000 if gold else 100000)),
        exit_price=str(D(t["exit_price_units"])/(1000 if gold else 100000)),
        entry_time=t["entry_msc"],exit_time=t["exit_msc"],reason=t["reason"])
    legs=cash_legs(row,model[:4].replace("_",""),dict(contract=100 if gold else 100000))
    return {k:int(v*1000) for k,v in legs.items() if k!="carry"} | {
        "carry":{at:int(v*1000) for at,v in legs["carry"]}}


def audit_v14_path(t,bars,events,cutoff,*,scheduled_override=None):
    """Scalar first passage over the declared four-point M1 ordering."""
    errors=[];times=bars["t"];gold=t["asset"]=="XAUUSD"
    scale=1000 if t["asset"] in ("XAUUSD","US500") else 100000
    contract=100 if gold else 1 if t["asset"]=="US500" else 100000
    entry=t["entry_msc"];sign=1 if t["side"]=="BUY" else -1
    horizon=t["id"].split("|")[-2]
    flats=[int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp()*1000)+
        (int(r["flat_utc"][:2])*60+int(r["flat_utc"][3:]))*60000
        for d,r in events.items() if r.get("flat_utc")]
    utc_entry=datetime.fromtimestamp(entry/1000,timezone.utc)
    friday=(utc_entry+timedelta(days=(4-utc_entry.weekday())%7)).replace(hour=20,minute=30,second=0,microsecond=0)
    if friday.timestamp()*1000<=entry:friday+=timedelta(days=7)
    flats.append(int(friday.timestamp()*1000))
    row=dict(symbol=t["asset"],direction=t["side"],entry_time=entry,exit_time=entry,
        entry_price=str(D(t["entry_price_units"])/scale),exit_price=str(D(t["entry_price_units"])/scale),
        lots="1",reason="MARKET",horizon=horizon)
    spec=dict(contract=contract,session_events=events)
    scheduled=expected_deadline(row,flats)
    if source_off_kind(scheduled,t["asset"],spec)=="DAILY_BREAK":
        local=datetime.fromtimestamp(scheduled/1000,timezone.utc).astimezone(ZoneInfo("America/New_York"))
        scheduled=int(local.replace(hour=18,minute=0,second=0,microsecond=0).timestamp()*1000)
    if scheduled_override is not None:scheduled=int(scheduled_override)
    if scheduled!=t["deadline_msc"]:errors.append("DEADLINE")
    endpoint=bisect_left(times,scheduled)
    end=int(times[endpoint]) if endpoint<len(times) else scheduled
    end=min(end,cutoff-1)
    start=bisect_left(times,entry)
    if start>=len(times) or times[start]!=entry:return dict(passed=False,errors=["ENTRY_SOURCE"])
    p0=t["entry_price_units"];stop=t["stop_units"];natural=D(str(t["natural"]))
    if p0!=int(bars[start]["ao" if sign==1 else "bo"]):errors.append("ENTRY_PRICE")
    trigger=None;protect=None;hit=None;previous=None
    names="olhc" if t["order"]=="OPEN_LOW_HIGH_CLOSE" else "ohlc"
    for j in range(start,bisect_right(times,end)):
        bar=bars[j];at=int(times[j]);level=protect if trigger is not None and at>=trigger else stop
        for offset,name in zip((0,20000,40000,59999),names):
            now=at+offset
            if now>end:break
            px=int(bar[("b" if sign==1 else "a")+name])
            reason=("PROTECT" if level!=stop else "SL") if sign*(px-level)<=0 else None
            target=p0+sign*3*abs(p0-stop)
            if not reason and t["mode"]=="P2" and sign*(px-target)>=0:reason="TP";level=target
            if reason:
                if not offset or previous is None:
                    fill=level if reason=="TP" else min(px,level) if sign==1 else max(px,level)
                    when=now
                else:
                    before,old=previous
                    den=abs(px-old);numerator=abs(level-old)*(now-before)
                    when=before+max(1,(numerator+den-1)//den) if den else now
                    fill=level
                hit=(when,fill,reason);break
            previous=(now,px)
        if hit:break
        if t["mode"]=="P1" and trigger is None and at+59999<=end:
            favorable=int(bar["bh" if sign==1 else "al"])
            mark=dict(row,exit_time=at+59999,exit_price=str(D(favorable)/scale))
            value=cash_legs(mark,"SYM",spec)["net"]/contract
            if value>=D("1.5")*natural:
                trigger=at+60000
                mark["exit_price"]=row["entry_price"]
                drag=-cash_legs(mark,"SYM",spec)["net"]/contract
                candidate=(D(p0)+sign*(D(".15")*natural+drag)*scale).to_integral_value(
                    rounding="ROUND_CEILING" if sign==1 else "ROUND_FLOOR")
                for _ in range(128):
                    mark["exit_price"]=str(candidate/scale)
                    if cash_legs(mark,"SYM",spec)["net"]/contract>=D(".15")*natural:break
                    candidate+=sign
                for _ in range(128):
                    mark["exit_price"]=str((candidate-sign)/scale)
                    if cash_legs(mark,"SYM",spec)["net"]/contract<D(".15")*natural:break
                    candidate-=sign
                protect=int(candidate)
    if hit is None:
        if scheduled>=cutoff:hit=(cutoff,t["exit_price_units"],"RIGHT_CENSORED")
        elif endpoint<len(times):
            hit=(int(times[endpoint]),int(bars[endpoint]["bo" if sign==1 else "ao"]),"HORIZON")
        else:errors.append("MISSING_ENDPOINT")
    if hit!=(t["exit_msc"],t["exit_price_units"],t["reason"]):errors.append("FIRST_PASSAGE")
    if (t["activation_time"],t["protection_price"] if t["activation_time"] is not None else None)!=(trigger,protect):
        errors.append("PROTECTION")
    uncertain=False
    for j in range(start+1,bisect_right(times,min(t["exit_msc"],cutoff-1))):
        if int(times[j])-int(times[j-1])>60000:
            if any(source_off_kind(at,t["asset"],spec) is None for at in
                   range(int(times[j-1])+60000,int(times[j]),60000)):
                uncertain=True
    if uncertain!=t["source_uncertain"]:errors.append("SOURCE_UNCERTAINTY_LABEL")
    if not t["censored"]:
        cash_row=dict(row,exit_time=t["exit_msc"],
            exit_price=str(D(t["exit_price_units"])/scale),reason=t["reason"])
        for model,claimed in t["reference"].items():
            legs=cash_legs(cash_row,model,spec)
            for name,key in (("gross","gross"),("commission","commission"),("slippage","slippage"),
                             ("funding","swap"),("net","net")):
                if abs(float(legs[key]/contract)-claimed[name])>1e-9:
                    errors.append("REFERENCE_"+model+"_"+name)
            if abs(float(legs["net"]/contract/natural)-claimed["net_R"])>1e-9:
                errors.append("REFERENCE_NET_R")
    return dict(passed=not errors,errors=errors,entry=entry,exit=t["exit_msc"],first_hit=hit,
        scope="conditional M1 ordering, fixed Ask proxy; missing extrema remain unknown")


class V14LedgerOracle:
    """Separate cash/equity/admission oracle; consumes original scenario quotes.

    This is an audit, not a second producer or a different feed/person. Events
    claimed by the producer are checked, including missing/invalid phase passes.
    """
    def __init__(self,expected,trades):
        self.e=expected
        self.trades=[dict(t) for t in trades]
        for c in expected["closed"]:
            self.trades[c["trade"]].update(c.get("execution_override",{}))
        self.accepted={r["trade"]:r for r in expected["accepted"]}
        self.closed={r["trade"]:r for r in expected["closed"]}
        self.open={};self.parts={};self.carry={}
        self.cash=self.anchor=self.peak=50000000
        self.phase=3 if expected["standalone_funded"] else 1
        self.dd=self.daily=self.static=0
        self.coeff=[0]*4;self.basis=0
        self.days=set();self.halt=False;self.gate=expected["start_msc"]-1
        self.first_funded=self.last_reward=None
        self.harvest="NORMAL";self.pending={};self.breach=None
        self.entries=self.exits=self.rejects=self.passes=self.rewards=0

    def floating(self,quote):
        gross=sum(c*int(quote[n]) for c,n in zip(self.coeff,("b0","a0","b1","a1"))) if self.open else 0
        return gross-self.basis+sum(self.carry.values())-sum(
            q*(200 if self.trades[i]["asset"]=="XAUUSD" else 10) for i,q in self.open.items())

    def measure(self,values,times):
        import numpy as np
        if not len(values) or self.breach:return
        equities=values+self.cash-self.basis+sum(self.carry.values())-sum(
            q*(200 if self.trades[i]["asset"]=="XAUUSD" else 10) for i,q in self.open.items())
        bad=np.flatnonzero(equities<=max(self.anchor-2500000,45000000)) if self.e["rolling"] else []
        if len(bad):
            k=int(bad[0]);equities=equities[:k+1]
            self.breach=dict(at=int(times[k]),equity=int(equities[-1]))
        peaks=np.maximum.accumulate(np.r_[self.peak,equities])
        self.dd=max(self.dd,int(np.max(peaks[1:]-equities)))
        self.daily=max(self.daily,self.anchor-int(equities.min()))
        self.static=max(self.static,50000000-int(equities.min()))
        self.peak=int(peaks[-1])

    def point(self,at,quote):
        import numpy as np
        value=sum(c*int(quote[n]) for c,n in zip(self.coeff,("b0","a0","b1","a1"))) if self.open else 0
        self.measure(np.array([value],dtype="int64"),np.array([at]))
        self.observe(at)

    def segment(self,rows,cache):
        import numpy as np
        if not self.open or self.breach or not len(rows):return
        key=tuple(self.coeff)
        if key not in cache:
            v=np.zeros(len(rows),dtype="int64")
            for c,n in zip(key,("b0","a0","b1","a1")):
                if c:v+=c*rows[n].astype("int64")
            cache[key]=v
        self.measure(cache[key],rows["t"])

    def observe(self,at):
        if self.phase!=3 or self.first_funded is None or not self.e["rolling"]:return
        due=(self.last_reward if self.last_reward is not None else self.first_funded)+14*DAY
        if self.cash>=51000000 and self.harvest!="PROFIT_LOCK_IDLE":
            self.harvest="PROFIT_LOCK_IDLE"
            for i in self.open:self.pending.setdefault(i,(at,"PROFIT_LOCK_IDLE"))
        elif self.cash>=50500000 and at>=due-48*HOUR and self.harvest=="NORMAL":
            self.harvest="PRE_PAYOUT_FREEZE"

    def reserve(self,i,q):
        t=self.trades[i];p=v14_parts(t,q,self.e["cell"])
        value=self.cash+p["entry_charge"]
        for k,size in [*self.open.items(),(i,q)]:
            old=self.trades[k];gold=old["asset"]=="XAUUSD"
            sign=1 if old["side"]=="BUY" else -1
            px=D(old["stop_units"])/(1000 if gold else 100000)
            fee=cent(px*size*D(".000007")) if gold else cent(D(size)*D(".035"))
            value+=sign*size*(1 if gold else 10)*(old["stop_units"]-old["entry_price_units"])
            value-=int(fee*1000)+size*(200 if gold else 10)
            rate=(-400 if self.e["cell"].startswith("SYM") else -450 if sign==1 else -50) if gold else -400
            value+=min(0,rate)*size*sum(m for _,m in swap_events(
                old["entry_msc"],old["deadline_msc"],old["asset"]))
        return value

    def requested_risk(self,equity):
        risk=(200,175,125)[self.phase-1] if self.e["rolling"] else 150
        if self.e["rolling"]:
            risk=min(risk,90) if equity<=47000000 else min(risk,150) if equity<=48000000 else risk
        return risk

    def policy_limits(self):
        return 800000,46000000

    def entry(self,i,at,quote):
        t=self.trades[i];a=self.accepted.get(i);rolling=self.e["rolling"]
        equity=self.cash+self.floating(quote)
        risk=self.requested_risk(equity)
        value=1 if t["asset"]=="XAUUSD" else 10
        q=int(D(str(risk))*1000)//(value*abs(t["entry_price_units"]-t["stop_units"]))
        reason=None
        if rolling:
            if self.harvest!="NORMAL":reason="HARVEST"
            elif t["decision_msc"]<self.e["start_msc"] or t["decision_msc"]<=self.gate:reason="GATE"
            elif any(self.trades[k]["asset"]==t["asset"] and
                     self.trades[k]["decision_msc"]==t["decision_msc"] for k in self.open):reason="COLLISION"
            elif self.halt or self.cash-self.anchor<=-1000000:reason="HALT"
        elif t["decision_msc"]<self.e["start_msc"]:reason="PRESTART"
        if not 1<=q<=(5000 if t["asset"]=="XAUUSD" else 100000):reason=reason or "LOT"
        prior=sum(size*(1 if self.trades[k]["asset"]=="XAUUSD" else 10)*abs(
            self.trades[k]["entry_price_units"]-self.trades[k]["stop_units"]) for k,size in self.open.items())
        new=q*value*abs(t["entry_price_units"]-t["stop_units"])
        projected=self.reserve(i,q) if q else 0
        cap,floor=self.policy_limits()
        if rolling and prior+new>cap:reason=reason or "CAP"
        if rolling and (projected<=floor or projected<max(self.anchor-2500000,45000000)):
            reason=reason or "RESERVE"
        if bool(a)!=(reason is None):raise ValueError(f"V14_audit_admission:{i}:{reason}:{self.e['start_msc']}")
        if a is None:self.rejects+=1;return
        if (a["risk_usd"],a["quantity_steps"],a["phase"])!=(risk,q,self.phase):
            raise ValueError("V14_audit_quantity_phase")
        if rolling:
            for field,v in (("balance_milli_usd",self.cash),("equity_milli_usd",equity),
                ("daily_anchor_milli_usd",self.anchor),("projected_stop_milli_usd",projected),
                ("prior_stop_risk_milli_usd",prior),("new_stop_risk_milli_usd",new)):
                if a["risk_state"][field]!=v:raise ValueError("V14_audit_risk_state:"+field)
        self.parts[i]=v14_parts(t,q,self.e["cell"]);self.open[i]=q;self.carry[i]=0
        self.cash+=self.parts[i]["entry_charge"]
        field=(0 if t["asset"]=="XAUUSD" else 2)+(t["side"]=="SELL")
        sign=1 if t["side"]=="BUY" else -1
        self.coeff[field]+=sign*q*value;self.basis+=sign*q*value*t["entry_price_units"]
        if rolling:
            self.days.add(datetime.fromtimestamp(at/1000,timezone.utc).astimezone(ZoneInfo("Europe/Prague")).date())
        if self.phase==3 and self.first_funded is None:self.first_funded=at
        self.entries+=1

    def action(self,kind,i,at,quote,extra=None):
        if not self.e["start_msc"]<=at<self.e["end_msc"] or self.breach:return
        if kind=="reset":self.anchor=self.cash;self.halt=False
        elif kind=="session_flat":
            self.observe(at)
            if self.harvest=="PRE_PAYOUT_FREEZE":
                for k in self.open:self.pending.setdefault(k,(at,"PRE_PAYOUT_SESSION_CLOSE"))
            return
        elif kind=="entry":self.entry(i,at,quote)
        elif kind=="swap" and i in self.open:self.carry[i]+=self.parts[i]["carry"][at]
        elif kind=="exit" and i in self.open:
            t=self.trades[i];p=self.parts[i];q=self.open.pop(i);self.carry.pop(i)
            if "execution_override" in self.closed[i]:
                request=self.pending.get(i)
                if not request or request[1]!=t["reason"] or not request[0]<at:
                    raise ValueError("V14_audit_unrequested_liquidation")
            self.pending.pop(i,None)
            self.cash+=p["net"]-p["entry_charge"]
            field=(0 if t["asset"]=="XAUUSD" else 2)+(t["side"]=="SELL")
            sign=1 if t["side"]=="BUY" else -1;value=1 if t["asset"]=="XAUUSD" else 10
            self.coeff[field]-=sign*q*value;self.basis-=sign*q*value*t["entry_price_units"]
            c=self.closed[i]
            if int(cent(c["net_usd"])*1000)!=p["net"]:raise ValueError("V14_audit_cash_legs")
            if c["phase"]!=self.phase:raise ValueError("V14_audit_close_phase")
            self.exits+=1
            if (self.e["rolling"] and self.phase<3 and not self.open and len(self.days)>=4
                    and self.cash>=50000000+(5000000 if self.phase==1 else 2500000)
                    and not any(r["at"]==at and r["phase"]==self.phase for r in self.e["phase_passes"])):
                raise ValueError("V14_audit_missing_pass")
        elif kind=="pass":
            if (self.open or len(self.days)<4 or self.phase>=3 or
                self.cash<50000000+(5000000 if self.phase==1 else 2500000) or
                extra["phase"]!=self.phase or extra["days"]!=len(self.days) or
                int(cent(extra["balance_usd"])*1000)!=self.cash):
                raise ValueError("V14_audit_invalid_pass")
            self.phase+=1;self.cash=self.anchor=self.peak=50000000
            self.days=set();self.gate=at;self.passes+=1
        elif kind=="reward":
            since=self.last_reward if self.last_reward is not None else self.first_funded
            removed=int(cent(extra["gross_removed_usd"])*1000)
            trader=(removed*80//100)//10*10
            if (self.phase!=3 or self.open or since is None or at-since<14*DAY or
                removed<20000 or self.cash-50000000!=removed or
                int(cent(extra["trader_usd"])*1000)!=trader or
                int(cent(extra["firm_usd"])*1000)+trader!=removed):
                raise ValueError("V14_audit_payout_cash_bridge")
            self.cash-=removed;self.anchor=self.peak=50000000
            self.last_reward=at;self.gate=at;self.harvest="NORMAL";self.pending.clear();self.rewards+=1
        self.point(at,quote)
        if self.cash-self.anchor<=-1000000:self.halt=True

    def finish(self):
        e=self.e
        for v,name in ((self.dd,"peak_dd_pct"),(self.daily,"worst_daily_loss_pct"),(self.static,"static_loss_pct")):
            if abs(v-e[name]*500000)>1e-5:raise ValueError("V14_audit_equity:"+name+":"+str((v,e[name]*500000,e["start_msc"])))
        if (self.open!={p["trade"]:p["quantity"] for p in e["open_positions"]} or
            self.cash!=int(cent(e["balance_usd"])*1000) or self.phase!=e["phase"] or
            bool(self.breach)!=bool(e["first_breach"]) or self.entries!=len(e["accepted"]) or
            self.exits!=len(e["closed"]) or self.passes!=len(e["phase_passes"]) or self.rewards!=len(e["payouts"])):
            raise ValueError("V14_audit_terminal")
        if self.breach and self.breach["at"]!=e["first_breach"]["at"]:raise ValueError("V14_audit_first_breach")
        return dict(start=e["start_msc"],model=e["cell"],entries=self.entries,exits=self.exits,
            rejected=self.rejects,passes=self.passes,payouts=self.rewards,cash_bridge=True,
            dd_milli=self.dd,daily_milli=self.daily,static_milli=self.static)


class V15LedgerOracle(V14LedgerOracle):
    """Independent risk arithmetic; old lifecycle/cash oracle remains the owner."""
    def __init__(self,*args):
        super().__init__(*args)
        self.cushion_active=False;self.seen_phase=self.phase

    def observe(self,at):
        if self.seen_phase!=self.phase:
            self.seen_phase=self.phase;self.cushion_active=False
        if self.e.get("cushion") and self.phase==1:
            if self.cash<=50000000:self.cushion_active=False
            if self.cash>=51500000:self.cushion_active=True
        super().observe(at)

    def requested_risk(self,equity):
        if not self.e["policy"].startswith("V15"):return super().requested_risk(equity)
        risk=D((200,175,125)[self.phase-1])*D(str(self.e["V15_factor"]))
        if self.e.get("cushion") and self.phase==1 and self.cushion_active and equity>50000000:
            risk+=min(D(self.cash-50000000)/1000/5,D(250))
        if equity<=46500000:risk=min(risk,D(75))
        elif equity<=47500000:risk=min(risk,D(150))
        return float(risk)

    def policy_limits(self):
        return (1000000,45800000) if self.e["policy"].startswith("V15") else super().policy_limits()

    def entry(self,i,at,quote):
        if self.e.get("sleeve_id") and self.trades[i]["id"]!=self.e["sleeve_id"]:return
        return super().entry(i,at,quote)


def audit_tick_continuity(ticks,first,end,side,stop,proof):
    """Recorded absence and feed continuity are distinct claims."""
    if side not in (-1,1) or first>=end:raise ValueError("tick_interval_contract")
    previous=None;count=0;hit=False
    for at,bid,ask in ticks:
        if previous is not None and at<previous or bid<=0 or ask<bid:
            raise ValueError("tick_order_or_quote_side")
        previous=at
        if first<=at<end:
            count+=1
            hit|=bid<=stop if side==1 else ask>=stop
    continuity=(proof.get("complete_interval") and proof.get("unfiltered_quotes") and
        proof.get("sequence_checked") and proof.get("missing_sequence_count")==0 and
        proof.get("first",end)<=first and proof.get("end",first)>=end)
    return dict(recorded_quotes=count,recorded_SL_hit=hit,
        status="RECORDED_SL_HIT" if hit else "TICK_VERIFIED_NO_SL_IN_DECLARED_FEED" if continuity
            else "RECORDED_ZERO_TICKS_CONTINUITY_UNKNOWN" if not count else "RECORDED_NO_SL_CONTINUITY_UNKNOWN",
        declared_feed_continuity=bool(continuity),market_or_broker_guarantee=False)


def v16_causal_cutoff(entry,parent_deadline,asset,events):
    """Separate calendar arithmetic; no producer schedule or future price access."""
    day=entry//DAY*DAY
    date=datetime.fromtimestamp(entry/1000,timezone.utc)
    limit=day+73800000
    row=events.get(date.date().isoformat(),{})
    clock=row.get("flat_utc")
    if clock:
        h,m=map(int,clock.split(":"));limit=min(limit,day+(h*60+m)*60000)
    if asset=="US500":
        local=date.astimezone(ZoneInfo("America/New_York")).replace(hour=16,minute=0,second=0,microsecond=0)
        limit=min(limit,int(local.timestamp()*1000))
    return min(parent_deadline,limit)


class V17LedgerOracle(V15LedgerOracle):
    """Own tier/lot-budget and reserved-cap arithmetic over the V14 cash oracle."""
    def __init__(self,*args):
        super().__init__(*args)
        self.target=None
        if self.e.get("tiers") is None or any(w not in (1.,.6) for w in self.e["tiers"].values()):
            raise ValueError("V17_oracle_unregistered_tiers")
        expected=(self.e.get("total_stop_cap_usd"),self.e.get("swing_stop_cap_usd"),
            self.e.get("intraday_reserved_stop_usd"),self.e.get("daily_reserved_loss_usd"))
        if expected!=(1000,400,600,1200):raise ValueError("V17_oracle_bucket_contract")

    def requested_risk(self,equity):
        if self.target is None:raise ValueError("V17_oracle_missing_target")
        risk=D((200,175,125)[self.phase-1])*D("1.5")
        if self.e.get("cushion") and self.phase==1 and self.cushion_active and equity>50000000:
            risk+=min(D(self.cash-50000000)/1000/5,D(250))
        if equity<=46500000:risk=min(risk,D(75))
        elif equity<=47500000:risk=min(risk,D(150))
        tier=D(str(self.e["tiers"][self.trades[self.target]["id"]]))
        return float((risk*tier*1000).to_integral_value(rounding="ROUND_FLOOR")/1000)

    def policy_limits(self):
        t=self.trades[self.target]
        cap=1000000
        if t["deadline_msc"]//DAY!=t["entry_msc"]//DAY:
            intraday=0
            for i,q in self.open.items():
                old=self.trades[i]
                if old["deadline_msc"]//DAY==old["entry_msc"]//DAY:
                    intraday+=q*(1 if old["asset"]=="XAUUSD" else 10)*abs(
                        old["entry_price_units"]-old["stop_units"])
            cap=min(cap,400000+intraday)
        return cap,max(45800000,self.anchor-1200000)

    def entry(self,i,at,quote):
        self.target=i
        return super().entry(i,at,quote)
