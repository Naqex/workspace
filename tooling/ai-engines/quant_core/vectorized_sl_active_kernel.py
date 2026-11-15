"""Batched first passage on observed bars; no synthetic fills in missing paths."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import numpy as np
from quant_core.vectorized_stage0_scanner import DAY, HOUR, funding_multipliers

BLOCK = 64


def money(asset, model, side, p0, px, entry, exit_at, reason):
    """Per underlying unit, preserving V11 fee units and each leg's rounding."""
    scale = 1000 if asset in ("XAUUSD", "US500") else 100000
    p0, px = np.asarray(p0) / scale, np.asarray(px) / scale
    side, entry, exit_at = map(np.asarray, (side, entry, exit_at))
    if np.any(exit_at < entry) or model not in ("SYM", "ASYM"):
        raise ValueError("cost_clock_or_model")
    tp = np.asarray(reason) == "TP"
    if asset == "XAUUSD":
        fee0, feex = (np.floor(p * .000007 * 10000 + .5 + 1e-9) / 10000 for p in (p0, px))
        slip0 = np.full(p0.shape, .2)
        slipx = np.where(tp & (model == "ASYM"), 0., .2)
        mult = funding_multipliers(entry, exit_at)
        swap = np.where(side == 1, -.4 if model == "SYM" else -.45,
                        -.4 if model == "SYM" else -.05) * mult
    elif asset == "US500":
        fee0, feex = np.full(p0.shape, .5), np.full(p0.shape, .5)
        slip0 = np.full(p0.shape, .75)
        slipx = np.where(tp & (model == "ASYM"), 0., .75)
        swap = -2. * (exit_at // DAY - entry // DAY)
    elif asset in ("EURUSD", "GBPUSD", "AUDUSD"):
        fee0, feex = np.full(p0.shape, .000035), np.full(p0.shape, .000035)
        slip0 = np.full(p0.shape, .00001)
        slipx = np.where(tp & (model == "ASYM"), 0., .00001)
        swap = -.0004 * funding_multipliers(entry, exit_at)
    else:
        raise ValueError("asset_cost_not_admitted")
    gross = side * (px - p0)
    if asset == "US500":
        gross = np.sign(gross)*np.floor(abs(gross)*100+.5+1e-8)/100
    net = gross - fee0 - feex - slip0 - slipx + swap
    return dict(gross=gross, commission=fee0+feex, slippage=slip0+slipx, funding=swap,
                net=net, entry_cost=fee0+slip0)


def net_level(asset, side, p0, natural, entry, when, target):
    """Conservative integer quote giving the requested SYM net liquidation R."""
    scale = 1000 if asset in ("XAUUSD", "US500") else 100000
    side, p0, natural = map(np.asarray, (side, p0, natural))
    reason = np.full(len(p0), "MARKET")
    base = money(asset, "SYM", side, p0, p0, entry, when, reason)["net"]
    estimate = p0 + side * (target * natural - base) * scale
    level = np.where(side == 1, np.ceil(estimate-1e-7), np.floor(estimate+1e-7)).astype("int64")
    # Only Gold's exit commission varies with px; adjust exactly on the quote grid.
    for _ in range(16):
        net = money(asset, "SYM", side, p0, level, entry, when, reason)["net"]
        bad = net + 1e-12 < target * natural
        if asset == "US500":
            previous = money(asset, "SYM", side, p0, level-side, entry, when, reason)["net"]
            lower = ~bad & (previous+1e-12 >= target*natural)
            if not bad.any() and not lower.any():
                return level
            level += side*(bad.astype("int64")-lower.astype("int64"))
            continue
        if not bad.any():
            return level
        level[bad] += side[bad]
    raise ValueError("net_level_did_not_converge")


class PathIndex:
    """64-bar extrema blocks bound memory; exact bars resolve first-passage fills."""
    def __init__(self, bars, *, asset, step=60000, closed_days=()):
        if step not in (60000, HOUR) or not len(bars) or np.any(np.diff(bars["t"]) <= 0):
            raise ValueError("path_index_schema")
        self.bars, self.asset, self.step = bars, asset, step
        self.extrema = {}
        for name, up in (("bh", True), ("bl", False), ("ah", True), ("al", False)):
            a = bars[name].astype("int64")
            padding = (-len(a)) % BLOCK
            pad = np.iinfo("int64").min if up else np.iinfo("int64").max
            x = np.pad(a, (0, padding), constant_values=pad).reshape(-1, BLOCK)
            self.extrema[name] = x.max(axis=1) if up else x.min(axis=1)
        closed = set(closed_days)
        gaps = np.flatnonzero(np.diff(bars["t"]) > step) + 1
        unexpected = np.zeros(len(bars), dtype="int64")
        audit = []
        ny = ZoneInfo("America/New_York")
        def off(at):
            d = datetime.fromtimestamp(int(at)/1000, timezone.utc)
            if d.date().isoformat() in closed:
                return True
            local = d.astimezone(ny)
            minute = local.hour*60+local.minute
            friday_close = 975 if asset == "US500" else 1020
            sunday_open = 1080 if asset in ("US500", "XAUUSD") else 1020
            if (local.weekday() == 5 or local.weekday() == 4 and minute >= friday_close or
                    local.weekday() == 6 and minute < sunday_open):
                return True
            return ((asset == "XAUUSD" and 17*60 <= minute < 18*60) or
                    (asset == "US500" and 16*60+15 <= minute < 18*60))
        for i in gaps:
            first, end = int(bars["t"][i-1])+step, int(bars["t"][i])
            # Every missing bar is checked; no >15-minute threshold hides smaller gaps.
            scheduled = all(off(at) for at in range(first, end, step))
            unexpected[i] = not scheduled
            audit.append(dict(before=int(bars["t"][i-1]), after=end,
                              missing=(end-first)//step, scheduled=scheduled))
        self.bad_prefix = np.cumsum(unexpected)
        self.audit = dict(rows=len(bars), step=step, gaps=len(audit),
                          unexpected_gaps=int(unexpected.sum()), gap_records=audit,
                          path_model="M1_BAR" if step == 60000 else "CONSERVATIVE_H1_BAR")

    def first(self, starts, ends, level, *, side, favorable=False):
        starts, ends, level, side = map(np.asarray, (starts, ends, level, side))
        result = ends.astype("int64").copy()
        for sign in (1, -1):
            use = np.flatnonzero((side == sign) & (starts < ends))
            name = ("bh" if sign == 1 else "al") if favorable else ("bl" if sign == 1 else "ah")
            up = (favorable and sign == 1) or (not favorable and sign == -1)
            data, ext = self.bars[name], self.extrema[name]
            for offset in range(0, len(use), 512):
                take = use[offset:offset+512]
                lo, hi, threshold = starts[take], ends[take], level[take]
                head = np.minimum(hi, ((lo+BLOCK-1)//BLOCK)*BLOCK)
                tail = np.maximum(head, hi//BLOCK*BLOCK)
                found = hi.copy()
                def scan(begin, stop):
                    idx = begin[:, None] + np.arange(BLOCK)
                    valid = idx < stop[:, None]
                    px = data[np.minimum(idx, len(data)-1)]
                    hit = valid & ((px >= threshold[:, None]) if up else (px <= threshold[:, None]))
                    return np.where(hit.any(axis=1), begin + hit.argmax(axis=1), hi)
                found = np.minimum(found, scan(lo, head))
                b0, b1 = head//BLOCK, tail//BLOCK
                width = int(np.max(b1-b0, initial=0))
                if width:
                    block = b0[:, None] + np.arange(width)
                    valid = block < b1[:, None]
                    px = ext[np.minimum(block, len(ext)-1)]
                    hit = valid & ((px >= threshold[:, None]) if up else (px <= threshold[:, None]))
                    candidate = np.where(hit.any(axis=1), (b0+hit.argmax(axis=1))*BLOCK, hi)
                    found = np.minimum(found, scan(candidate, np.minimum(candidate+BLOCK, hi)))
                found = np.minimum(found, scan(tail, hi))
                result[take] = found
        return result

    def complete(self, starts, exits):
        starts, exits = np.asarray(starts), np.asarray(exits)
        return self.bad_prefix[exits] == self.bad_prefix[starts]


def replay(index, m, mode):
    if mode not in ("P0", "P1", "P2"):
        raise ValueError("unregistered_path_mode")
    b, step = index.bars, index.step
    at, end = np.asarray(m["entry_at"]), np.asarray(m["deadline"])
    side, p0, stop = (np.asarray(m[n]) for n in ("side", "entry_price", "stop"))
    natural = np.asarray(m["natural"])
    n = len(at)
    starts = b["t"].searchsorted(at)
    safe_starts = np.minimum(starts, len(b)-1)
    exit_indices = b["t"].searchsorted(end)
    safe_end = np.minimum(exit_indices, len(b)-1)
    endpoint_ok = ((exit_indices < len(b)) & (b["t"][safe_end] >= end) &
                   (b["t"][safe_end]-end <= 60000))
    limit = np.where(endpoint_ok, b["t"][safe_end], end)
    # A partial H1 bar extending past a 20:30 deadline is never read as a full path.
    ends = b["t"].searchsorted(limit-step, side="right")
    ends = np.maximum(ends, starts)
    weekday = (at//DAY+3)%7
    base = ((starts < len(b)) & (b["t"][safe_starts] == at) & (natural > 0) &
            (end >= at) & (at-np.asarray(m["at"]) <= 60000) & (at >= np.asarray(m["at"])) &
            (weekday < 5) & ~((weekday == 4) & (at%DAY >= int(20.5*HOUR))))
    old_hit = index.first(safe_starts, ends, stop, side=side)
    hit = old_hit.copy()
    reason = np.full(n, "HORIZON", dtype="<U16")
    reason[hit < ends] = "SL"
    price_level = stop.copy()
    activation = np.full(n, -1, dtype="int64")
    protect = np.zeros(n, dtype="int64")
    if mode == "P1" and n:
        first_roll = at//DAY*DAY + (0 if index.asset == "US500" else 22*HOUR)
        first_roll = np.where(first_roll <= at, first_roll+DAY, first_roll)
        for period in range(7):
            begin = at if period == 0 else first_roll+(period-1)*DAY
            finish = np.minimum(limit, first_roll+period*DAY)
            begin = np.minimum(begin, finish)
            s = np.maximum(safe_starts, b["t"].searchsorted(begin))
            e = np.minimum(ends, b["t"].searchsorted(finish-step, side="right"))
            e = np.maximum(s, e)
            threshold = net_level(index.asset, side, p0, natural, at,
                                  np.maximum(at, begin+step-1), 1.5)
            trigger = index.first(s, e, threshold, side=side, favorable=True)
            choose = (activation < 0) & (trigger < e) & (trigger < old_hit)
            activation[choose] = trigger[choose]
        selected = activation >= 0
        if selected.any():
            when = np.maximum(at, b["t"][np.maximum(activation, 0)]+step-1)
            protect = net_level(index.asset, side, p0, natural, at, when, .15)
            s = np.where(selected, activation+1, ends)
            protected_hit = index.first(s, ends, protect, side=side)
            use = selected & (protected_hit < ends)
            hit[use] = protected_hit[use]
            price_level[use] = protect[use]
            reason[use] = "PROTECT"
    elif mode == "P2":
        scale = 1000 if index.asset in ("XAUUSD", "US500") else 100000
        target = p0 + side*3*np.abs(p0-stop)
        tp_hit = index.first(safe_starts, ends, target, side=side, favorable=True)
        use = (tp_hit < old_hit) & (tp_hit < ends)  # Stop wins same-bar ties.
        hit[use], price_level[use], reason[use] = tp_hit[use], target[use], "TP"
    stopped = hit < ends
    path_last = np.where(stopped, hit, safe_end)
    path_last = np.minimum(path_last, len(b)-1)
    observed = index.complete(safe_starts, path_last)
    # A H1 endpoint can be missing even though an earlier observed stop is known.
    valid = base & observed & (stopped | endpoint_ok)
    quote = np.where(side == 1, b["bo"][path_last], b["ao"][path_last])
    stop_fill = np.where(side == 1, np.minimum(quote, price_level), np.maximum(quote, price_level))
    fill = np.where(stopped, np.where(reason == "TP", price_level, stop_fill), quote)
    exit_at = np.where(stopped, b["t"][path_last]+step-1, b["t"][safe_end])
    exit_at = np.maximum(exit_at, at)
    result = dict(mode=mode, valid=valid, reason=reason, exit_at=exit_at, exit_price=fill,
                  path_gap=~observed, activation_index=activation, protection_price=protect,
                  entry_index=safe_starts, exit_index=path_last, model={})
    for model in ("SYM", "ASYM"):
        value = money(index.asset, model, side, p0, fill, at, exit_at, reason)
        value["net_R"] = np.divide(value["net"], natural, out=np.zeros(n), where=natural>0)
        result["model"][model] = value
    return result


def daily_mtm(index, m, result, model, days):
    """Daily liquidation marks; entry/exit costs are charged on their actual legs."""
    out = np.zeros(len(days))
    b = index.bars
    valid = np.flatnonzero(result["valid"] & m["admitted"])
    if not len(valid):
        return out
    start, end = m["entry_at"][valid], result["exit_at"][valid]
    side, p0, natural = (m[k][valid] for k in ("side", "entry_price", "natural"))
    previous = np.zeros(len(valid))
    for offset in range(8):
        day = start//DAY+offset
        cutoff = np.minimum((day+1)*DAY, end)
        active = (day <= end//DAY) & (cutoff >= start)
        close = cutoff == end
        ix = np.clip(b["t"].searchsorted(cutoff), 0, len(b)-1)
        exact = b["t"][ix] == cutoff
        prior = np.maximum(0, ix-1)
        mark = np.where(side == 1, np.where(exact, b["bo"][ix], b["bc"][prior]),
                        np.where(exact, b["ao"][ix], b["ac"][prior]))
        price = np.where(close, result["exit_price"][valid], mark)
        value = money(index.asset, model, side, p0, price, start, np.maximum(cutoff, start),
                      result["reason"][valid])
        floating = side*(price-p0)/(1000 if index.asset in ("XAUUSD","US500") else 100000)
        if index.asset == "US500":
            floating = np.sign(floating)*np.floor(abs(floating)*100+.5+1e-8)/100
        net = np.where(close, value["net"], floating-value["entry_cost"]+value["funding"])
        current = net/natural
        pos = days.searchsorted(day)
        good = active & (pos < len(days)) & (days[np.minimum(pos, len(days)-1)] == day)
        np.add.at(out, pos[good], (current-previous)[good])
        previous[active] = current[active]
    return out
