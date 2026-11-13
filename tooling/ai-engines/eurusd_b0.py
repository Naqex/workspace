"""Frozen EURUSD B0 signal machine and conditional observed-tick diagnostic."""
from bisect import bisect_left
from collections import Counter, deque
from dataclasses import dataclass
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from statistics import median

from eurusd_b0_source import MINUTE, session

R0_CENTS = 15_000
INITIAL_CENTS = 5_000_000
GRID = D('.00001')


def bind_native(root):
    from forex_study_batch import configure_source_root
    configure_source_root(root)
    global InstrumentSpec, CostModel, calculate_round_trip_cost, size_for_market_stop
    from trading_workspace_v2.retained import InstrumentSpec, CostModel, calculate_round_trip_cost
    from trading_workspace_v2.research_market import size_for_market_stop


def market(scenario):
    if scenario not in ('reference', 'stress'):
        raise ValueError('B0_unregistered_cost_scenario')
    instrument = InstrumentSpec.from_mapping(dict(instrument_id='EURUSD', asset_class='fx',
        base_ccy='EUR', quote_ccy='USD', account_ccy='USD', contract_size='100000',
        tick_size=str(GRID), pip_size='.0001', quantity_min='.01', quantity_step='.01',
        effective_from_utc='2022-01-01T00:00:00Z'))
    model = CostModel.from_mapping(dict(version='B0-declared-'+scenario+'-v1',
        spread_basis='bid_ask_embedded', commission_per_side_account='0',
        commission_per_side_per_quantity_account='2.50', minimum_fee_account='0',
        slippage_price_per_side='0' if scenario == 'reference' else '.00002',
        financing_account='0', quote_to_account_rate='1', account_ccy='USD', rounding_decimals=2))
    return instrument, model


def features(m15, h1):
    """Indicator maps indexed by knowledge time; never include the breakout TR."""
    closes, means = deque(maxlen=20), deque(maxlen=4)
    bias = {}
    for t, o, h, l, c, minutes in h1:
        if minutes != 60:
            continue
        closes.append(D(c))
        if len(closes) == 20:
            mean = sum(closes)/20
            means.append(mean)
            if len(means) == 4:
                bias[t+60*MINUTE] = ('BUY' if c > mean and mean > means[0] else
                                    'SELL' if c < mean and mean < means[0] else None)
    previous, atr, seed, out = None, None, [], {}
    for row in m15:
        t, o, h, l, c, minutes = row
        if minutes != 15:
            continue
        tr = D(h-l) if previous is None else D(max(h-l, abs(h-previous), abs(l-previous)))
        at = t+15*MINUTE
        out[at] = dict(bar=row, atr_before=atr, bias=bias.get(at//(60*MINUTE)*(60*MINUTE)))
        if atr is None:
            seed.append(tr)
            if len(seed) == 14:
                atr = sum(seed)/14
        else:
            atr = (13*atr+tr)/14
        previous = c
    return out


def natural_stop(side, low, high, buffer):
    return int((D(low)-buffer).to_integral_value(rounding=ROUND_FLOOR) if side == 'BUY'
               else (D(high)+buffer).to_integral_value(rounding=ROUND_CEILING))


def admission(side, stop, bid, ask, cash_cents):
    entry = ask if side == 'BUY' else bid
    distance = (entry-stop) if side == 'BUY' else (stop-entry)
    result = dict(entry_units=entry, natural_stop_units=stop, distance_units=distance,
                  natural_sl_pips=distance/10, status='invalid_natural_stop')
    if distance <= 0 or (side == 'BUY' and bid <= stop) or (side == 'SELL' and ask >= stop):
        return result
    instrument, stress = market('stress')
    quantity = size_for_market_stop(D(distance)*GRID, instrument=instrument, model=stress, budget=D(150))
    if quantity is None or quantity > 50:
        return dict(result, status='quantity_rejected')
    steps = int(quantity*100)
    planned_f = D(steps*(ask-bid+9))  # cents: one 1e-5 move/lot = 1 USD
    result.update(lot_steps=steps, quantity_lots=float(quantity), r_price_usd=distance*steps/100,
                  planned_stress_friction_r0=float(planned_f/R0_CENTS),
                  planned_stress_stop_r0=(distance+9)*steps/R0_CENTS)
    if planned_f > D('.12')*R0_CENTS:
        return dict(result, status='friction_cap_rejected')
    margin = D(entry)*GRID*100000*quantity/30
    result['margin_usd'] = float(margin)
    if margin*100 > cash_cents-R0_CENTS:
        return dict(result, status='margin_rejected')
    return dict(result, status='accepted', take_units=entry+(2*distance if side == 'BUY' else -2*distance))


def protection(position, bid, ask):
    side, stop, take = position['side'], position['natural_stop_units'], position['take_units']
    price = bid if side == 'BUY' else ask
    if (price <= stop if side == 'BUY' else price >= stop):
        return price, 'stop_loss'
    if (price >= take if side == 'BUY' else price <= take):
        return take, 'take_profit'
    return None


@dataclass
class Account:
    cash: int = INITIAL_CENTS
    peak: int = INITIAL_CENTS
    min_equity: int = INITIAL_CENTS
    max_dd: int = 0
    max_liquidation_dd: int = 0
    liquidation_peak: int = INITIAL_CENTS
    worst_daily_loss: int = 0
    worst_liquidation_daily_loss: int = 0
    worst_daily_witness: dict | None = None
    max_dd_witness: dict | None = None

    def mark(self, equity, liquidation, anchor, at):
        self.peak = max(self.peak, equity)
        self.min_equity = min(self.min_equity, equity)
        self.liquidation_peak = max(self.liquidation_peak, liquidation)
        if self.peak-equity > self.max_dd:
            self.max_dd = self.peak-equity
            self.max_dd_witness = dict(at=at, peak_usd=self.peak/100, equity_usd=equity/100)
        self.max_liquidation_dd = max(self.max_liquidation_dd, self.liquidation_peak-liquidation)
        if anchor-equity > self.worst_daily_loss:
            self.worst_daily_loss = anchor-equity
            self.worst_daily_witness = dict(at=at, daily_anchor_usd=anchor/100, equity_usd=equity/100)
        self.worst_liquidation_daily_loss = max(self.worst_liquidation_daily_loss, anchor-liquidation)


def run_day(day, feature_map, quotes, account, scenario):
    clocks = session(day)
    counts = Counter(days=1)
    intents, trades, events = [], [], []
    zone_bars = [feature_map.get(at) for at in range(clocks[7]+15*MINUTE, clocks[8]+1, 15*MINUTE)]
    if any(v is None for v in zone_bars):
        counts['invalid_zone_missing_m15'] += 1
        return dict(day=day, counters=dict(counts), intents=intents, trades=trades, events=events)
    counts['valid_zones'] += 1
    high = max(v['bar'][2] for v in zone_bars)
    low = min(v['bar'][3] for v in zone_bars)
    times = [q[0] for q in quotes]
    index, pending, position = 0, None, None
    last_exit = -1
    anchor = account.cash
    fee_per_lot = 5 if scenario == 'reference' else 9

    def mark(q):
        if position is None:
            return
        at, seq, bid, ask = q
        price = bid if position['side'] == 'BUY' else ask
        gross = (price-position['entry_units'])*(1 if position['side'] == 'BUY' else -1)*position['lot_steps']
        equity = position['base_cash_cents']+gross-position['entry_debit_cents']
        liquidation = position['base_cash_cents']+gross-fee_per_lot*position['lot_steps']
        account.mark(equity, liquidation, anchor, at)

    def close(q, price, reason):
        nonlocal position, last_exit
        at, seq, bid, ask = q
        steps = position['lot_steps']
        gross = (price-position['entry_units'])*(1 if position['side'] == 'BUY' else -1)*steps
        fees = fee_per_lot*steps
        net = gross-fees
        instrument, model = market(scenario)
        # TP has no improvement; keep the observed opposite-side spread for the matched benchmark.
        exit_bid = price if position['side'] == 'BUY' else bid+(price-ask)
        exit_ask = price if position['side'] == 'SELL' else ask+(price-bid)
        native = calculate_round_trip_cost(model, position['side'], D(steps)/100, instrument.contract_size,
                    D(position['entry_bid_units'])*GRID, D(position['entry_ask_units'])*GRID,
                    D(exit_bid)*GRID, D(exit_ask)*GRID)
        if D(str(native['net_account'])) != D(net)/100 or D(str(native['gross_account'])) != D(gross)/100:
            raise ValueError('B0_native_accounting_parity')
        spread_drag_cents = D(steps)*(position['entry_ask_units']-position['entry_bid_units']+ask-bid)/2
        direction = 1 if position['side'] == 'BUY' else -1
        observed_exit = bid if direction == 1 else ask
        limit_drag_cents = (observed_exit-price)*direction*steps
        mid_gross_cents = D(direction*steps)*(bid+ask-position['entry_bid_units']-position['entry_ask_units'])/2
        if mid_gross_cents-spread_drag_cents-limit_drag_cents != gross:
            raise ValueError('B0_matched_mid_spread_limit_decomposition')
        account.cash = position['base_cash_cents']+net
        account.mark(account.cash, account.cash, anchor, at)
        trade = {**position, 'exit_msc': at, 'exit_sequence': seq, 'exit_units': price,
            'exit_bid_observed_units': bid, 'exit_ask_observed_units': ask, 'exit_reason': reason,
            'gross_after_spread_usd': gross/100, 'commission_usd': 5*steps/100,
            'slippage_usd': (fee_per_lot-5)*steps/100, 'conditional_financing_usd': 0,
            'conditional_net_usd': net/100, 'net_r0': net/R0_CENTS,
            'realized_spread_drag_usd': float(spread_drag_cents/100),
            'matched_observed_mid_gross_usd': float(mid_gross_cents/100),
            'tp_limit_no_improvement_drag_usd': limit_drag_cents/100,
            'realized_friction_r0': float((spread_drag_cents+fees)/R0_CENTS),
            'native_accounting_reconciled': True, 'holding_minutes': (at-position['entry_msc'])/MINUTE}
        trades.append(trade)
        last_exit = at
        position = None

    def advance(until):
        nonlocal index, position
        if position is None:
            index = bisect_left(times, until, lo=index)
            return
        while index < len(quotes) and quotes[index][0] < until:
            q = quotes[index]
            if position is not None:
                gap = q[0]-position['last_path_msc']
                position['max_active_quote_gap_ms'] = max(position['max_active_quote_gap_ms'], gap)
                if gap > MINUTE:
                    position['path_complete_under_60s_policy'] = False
                position['last_path_msc'] = q[0]
                hit = protection(position, q[2], q[3])
                if hit:
                    close(q, *hit)
                elif q[0] >= clocks[12]:
                    close(q, q[2] if position['side'] == 'BUY' else q[3], 'session_cutoff')
                else:
                    mark(q)
            index += 1
            if position is None:
                index = bisect_left(times, until, lo=index)
                break

    def trigger(p, feature, at):
        nonlocal position, index
        counts['pre_cost_confirmed_signals'] += 1
        row = dict(day=day, side=p['side'], breakout_msc=p['breakout_msc'], decision_msc=at,
                   buffer_units=str(p['buffer']), zone_high_units=high, zone_low_units=low,
                   news_checked=False, target_calendar_verified=False,
                   strict_admission='BLOCKED_BY_CALENDAR', scenario=scenario)
        if index >= len(quotes) or quotes[index][0]-at > MINUTE:
            row['status'] = 'entry_quote_unavailable'
            intents.append(row)
            counts[row['status']] += 1
            return
        q = quotes[index]
        stop = natural_stop(p['side'], feature['bar'][3], feature['bar'][2], p['buffer'])
        admitted = admission(p['side'], stop, q[2], q[3], account.cash)
        row.update(admitted, entry_msc=q[0], entry_sequence=q[1], entry_bid_units=q[2], entry_ask_units=q[3])
        intents.append(row)
        if row['status'] != 'accepted':
            counts[row['status']] += 1
            return
        counts['filled_entries'] += 1
        steps = row['lot_steps']
        entry_debit = int((D(fee_per_lot*steps)/2).to_integral_value(rounding=ROUND_HALF_UP))
        position = dict(row, base_cash_cents=account.cash, entry_debit_cents=entry_debit,
                        last_path_msc=q[0], max_active_quote_gap_ms=0,
                        path_complete_under_60s_policy=True)
        mark(q)

    for at in range(clocks[8], clocks[11]+1, 15*MINUTE):
        advance(at)
        f = feature_map.get(at)
        if at >= clocks[11]:
            if pending:
                counts['setup_cutoff_cancelled'] += 1
            pending = None
            continue
        if position is not None or counts['filled_entries'] >= 2 or at <= last_exit:
            continue
        if f is None:
            counts['missing_signal_bar'] += 1
            if pending:
                counts['setup_gap_cancelled'] += 1
                pending = None
            continue
        t, o, h, l, c, _ = f['bar']
        if pending:
            pending['waited'] += 1
            p = pending
            if f['bias'] != p['side']:
                counts['setup_bias_cancelled'] += 1
                pending = None
                continue
            edge = D(high if p['side'] == 'BUY' else low)
            touch = D(l) <= edge+p['buffer'] and D(h) >= edge-p['buffer']
            if touch:
                counts['first_touches'] += 1
                confirmed = (D(c) > edge+p['buffer'] and c > o if p['side'] == 'BUY'
                             else D(c) < edge-p['buffer'] and c < o)
                pending = None
                if confirmed:
                    trigger(p, f, at)
                else:
                    counts['first_touch_not_confirmed'] += 1
                continue
            if p['waited'] >= 4:
                counts['setup_expired'] += 1
                pending = None
            continue
        # 08:00 close is the zone's final bar, not an 08:00-session breakout.
        if t < clocks[8] or f['atr_before'] is None or f['bias'] is None:
            continue
        buffer = f['atr_before']/10
        breakout = (D(c) > D(high)+buffer if f['bias'] == 'BUY' else D(c) < D(low)-buffer)
        if breakout:
            counts['bias_breakouts'] += 1
            pending = dict(side=f['bias'], breakout_msc=at, buffer=buffer, waited=0)
            events.append(dict(kind='setup', at=at, side=f['bias'], buffer_units=str(buffer)))
    advance(clocks[12]+5*MINUTE)
    if position is not None:
        counts['unresolved_position'] += 1
        events.append(dict(kind='unresolved_position', position=position))
    counts['path_flagged_trades'] = sum(not t['path_complete_under_60s_policy'] for t in trades)
    return dict(day=day, counters=dict(counts), intents=intents, trades=trades, events=events,
                end_cash_usd=account.cash/100, open_position=position,
                prague_daily_anchor_usd=anchor/100)


def distribution(values):
    if not values:
        return dict(count=0, median=None, p90=None, maximum=None)
    v = sorted(values)
    def q(p):
        x = (len(v)-1)*p
        lo = int(x)
        return v[lo]+(v[min(lo+1, len(v)-1)]-v[lo])*(x-lo)
    return dict(count=len(v), median=median(v), p90=q(.9), maximum=max(v))


def summarize(year, scenario, days, account):
    counts = Counter()
    for day in days:
        counts.update(day['counters'])
    intents = [i for d in days for i in d['intents']]
    trades = [t for d in days for t in d['trades']]
    n, lots = len(trades), sum(t['lot_steps'] for t in trades)/100
    gross = sum(round(t['gross_after_spread_usd']*100) for t in trades)/100
    net = sum(round(t['conditional_net_usd']*100) for t in trades)/100
    if account.cash != INITIAL_CENTS+round(net*100):
        raise ValueError('B0_annual_cash_reconciliation')
    by_month = {str(m).zfill(2): sum(t['day'][5:7] == str(m).zfill(2) for t in trades) for m in range(1, 13)}
    return dict(year=year, role='development' if year < 2024 else 'historical_validation_previously_exposed',
        scenario=scenario, counters=dict(counts), closed_trades=n,
        buy_trades=sum(t['side'] == 'BUY' for t in trades), sell_trades=sum(t['side'] == 'SELL' for t in trades),
        natural_sl_pips_pre_admission=distribution([i['natural_sl_pips'] for i in intents if 'natural_sl_pips' in i]),
        natural_sl_pips_filled=distribution([t['natural_sl_pips'] for t in trades]),
        planned_stress_friction_r0=distribution([t['planned_stress_friction_r0'] for t in trades]),
        realized_friction_r0=distribution([t['realized_friction_r0'] for t in trades]),
        realized_friction_cap_exceedances=sum(t['realized_friction_r0'] > .12 for t in trades),
        cost_rejection_rate=counts['friction_cap_rejected']/counts['pre_cost_confirmed_signals'] if counts['pre_cost_confirmed_signals'] else None,
        sum_lots=lots, gross_after_spread_usd=gross, gross_after_spread_usd_per_lot=gross/lots if lots else None,
        commission_usd=sum(round(t['commission_usd']*100) for t in trades)/100,
        slippage_usd=sum(round(t['slippage_usd']*100) for t in trades)/100,
        conditional_net_usd=net, annual_net_r0=net/150, mean_net_r0=net/150/n if n else None,
        max_entries_day=max((d['counters'].get('filled_entries', 0) for d in days), default=0),
        active_trade_days=len({t['day'] for t in trades}), monthly_filled_entries=by_month,
        zero_trade_months=sum(v == 0 for v in by_month.values()),
        worst_daily_loss_usd=account.worst_daily_loss/100,
        worst_daily_loss_pct=account.worst_daily_loss/INITIAL_CENTS*100,
        worst_liquidation_daily_loss_pct=account.worst_liquidation_daily_loss/INITIAL_CENTS*100,
        max_equity_dd_usd=account.max_dd/100, max_cumulative_r_dd=account.max_dd/R0_CENTS,
        max_liquidation_r_dd=account.max_liquidation_dd/R0_CENTS,
        static_initial_loss_usd=max(0, INITIAL_CENTS-account.min_equity)/100,
        minimum_equity_usd=account.min_equity/100, peak_equity_usd=account.peak/100,
        daily_witness=account.worst_daily_witness, dd_witness=account.max_dd_witness,
        strict_news_admitted_trades=None, strict_net_usd=None, news_checked=False,
        target_calendar_verified=False, prop_qualified=False,
        interpretation='conditional_observed_tick_economics_not_funded_qualification')
