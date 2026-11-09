"""Bounded quote-to-bar oracle; matching one fixture does not certify a whole feed."""
from decimal import Decimal as D


def aggregate_ticks(ticks, *, start_msc, end_msc, price_grid):
    if type(start_msc) is not int or type(end_msc) is not int or start_msc>=end_msc:
        raise ValueError('invalid_quote_interval')
    grid=D(str(price_grid))
    if not grid.is_finite() or grid<=0 or not ticks:
        raise ValueError('invalid_quote_grid_or_empty')
    sides={'bid':[],'ask':[]}
    previous=-1
    for tick in ticks:
        at=tick['timestamp']
        if type(at)is not int or not start_msc<=at<end_msc or at<previous:
            raise ValueError('quote_scope_or_order')
        bid,ask=D(str(tick['bidPrice'])),D(str(tick['askPrice']))
        if any(not x.is_finite() or x<=0 or x%grid for x in (bid,ask)) or ask<bid:
            raise ValueError('quote_price_grid_or_spread')
        sides['bid'].append(bid);sides['ask'].append(ask);previous=at
    return {side:dict(open=prices[0],high=max(prices),low=min(prices),close=prices[-1])
            for side,prices in sides.items()}


def require_contains_quotes(bar, quote_ohlc):
    """A larger bar must contain every observed quote; endpoints need not match."""
    low,high=D(str(bar['low'])),D(str(bar['high']))
    if low>quote_ohlc['low'] or high<quote_ohlc['high']:
        raise ValueError('source_bar_excludes_observed_quote_extrema')


def require_exact_ohlc(bar, quote_ohlc):
    if any(D(str(bar[k]))!=quote_ohlc[k] for k in ('open','high','low','close')):
        raise ValueError('source_bar_not_exact_quote_ohlc')
