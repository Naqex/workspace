"""Independent integer SMA / high-precision Wilder oracle; no execution imports.

This verifies decisions conditional on a recorded position path. It does not
validate that path's stop fills, fees, margin or broker executability.
"""
from collections import defaultdict
from decimal import Decimal, localcontext

HOUR = 3600
H4 = 4 * HOUR


def completed_h4(hours):
    """Input prices are integer Bid ticks (0.001); partial hours stay observed."""
    groups = defaultdict(list)
    previous = None
    for at, prices in hours:
        if type(at) is not int or at % HOUR or (previous is not None and at <= previous):
            raise ValueError('unordered or unaligned source hour')
        if (len(prices) != 4 or any(type(p) is not int or p <= 0 for p in prices)
                or not prices[2] <= min(prices[0], prices[3]) <= max(prices[0], prices[3]) <= prices[1]):
            raise ValueError('invalid integer OHLC')
        groups[at // H4 * H4].append((at, prices))
        previous = at
    bars, excluded = [], []
    for start, rows in groups.items():
        if [at for at, _ in rows] != [start + i * HOUR for i in range(4)]:
            excluded.append(start)
            continue
        p = [prices for _, prices in rows]
        bars.append((start, (p[0][0], max(x[1] for x in p), min(x[2] for x in p), p[-1][3])))
    return bars, excluded


def indicator_trace(bars):
    closes, true_ranges, result = [], [], []
    atr = None
    previous = None
    with localcontext() as ctx:
        ctx.prec = 80
        for at, (_, high, low, close) in bars:
            if type(at) is not int or at % H4 or (previous is not None and at <= previous):
                raise ValueError('unordered or unaligned H4')
            tr = max(high-low, abs(high-closes[-1]), abs(low-closes[-1])) if closes else high-low
            true_ranges.append(tr)
            if len(true_ranges) == 14:
                atr = Decimal(sum(true_ranges)) / Decimal(14000)
            elif len(true_ranges) > 14:
                atr = atr * (Decimal(13)/14) + Decimal(tr)/14000
            closes.append(close)
            difference = 4*sum(closes[-20:])-sum(closes[-80:]) if len(closes) >= 80 else None
            result.append(dict(at=at, difference=difference, distance=2*atr if atr is not None else None))
            previous = at
    return result


def signal(previous, current, side):
    if side not in (None, 'BUY', 'SELL'):
        raise ValueError('unknown recorded side')
    if current is None:
        return None
    if (side == 'BUY' and current <= 0) or (side == 'SELL' and current >= 0):
        return 'EXIT'
    if side is None and previous is not None:
        if previous <= 0 < current:
            return 'BUY'
        if previous >= 0 > current:
            return 'SELL'
    return None


def review_decisions(trace, sides, actual, *, start, end, slippage):
    expected = []
    previous = None
    with localcontext() as ctx:
        ctx.prec = 80
        for point in trace:
            at, difference, distance = point['at'], point['difference'], point['distance']
            if start <= at < end:
                if at not in sides:
                    raise ValueError('missing conditional position state')
                action = signal(previous, difference, sides[at])
                if action in ('BUY', 'SELL') and (distance is None or distance <= 0):
                    action = None
                if action:
                    item = dict(time_msc=(at+H4)*1000, signal=action, stop_distance=str(distance), status='queued')
                    if action != 'EXIT':
                        per_lot = (distance+Decimal('.001')+2*slippage)*100+5
                        steps = int(Decimal(125)/per_lot/Decimal('.01'))
                        item['quantity'] = str(Decimal(steps)/100) if steps else None
                        if not steps:
                            item['status'] = 'skipped_minimum_lot'
                    expected.append(item)
            previous = difference
    if len(expected) != len(actual):
        raise ValueError('missing or extra decision')
    for want, got in zip(expected, actual):
        if set(want) != set(got):
            raise ValueError('decision schema differs')
        for key in want:
            if key == 'stop_distance':
                value = Decimal(got[key])
                if not value.is_finite() or abs(value-Decimal(want[key])) > Decimal('1e-23'):
                    raise ValueError('ATR distance differs')
            elif key == 'quantity' and want[key] is not None:
                if Decimal(want[key]) != Decimal(got[key]):
                    raise ValueError('risk quantity differs')
            elif want[key] != got[key]:
                raise ValueError('decision '+key+' differs')
    return dict(decisions=len(expected), bars=sum(start <= p['at'] < end for p in trace),
                no_signal=sum(start <= p['at'] < end for p in trace)-len(expected))
