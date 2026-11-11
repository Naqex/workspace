"""Independent Fraction/Decimal execution replay over native ledger (no engine import)."""
from collections import Counter
from decimal import Decimal as D, ROUND_HALF_EVEN
from fractions import Fraction as F

M=60000
NS=60000000000


def inspect(result, pairs):
    cash=D(10000)
    slip=D(str(result['slippage']))
    seen=set()
    for trade in result['trades']:
        side=trade['side']
        sign=1 if side=='BUY' else -1
        t=trade['entry_time']
        decision=trade['decision']
        if t!=decision['t']+M or t in seen:
            raise ValueError('review_entry_clock_duplicate')
        seen.add(t)
        pair=pairs[t]
        entry=D(str(pair[1 if side=='BUY' else 0]['open']))+sign*slip
        stop=D(str(trade['stop']))
        qty=D(str(trade['quantity']))
        if entry!=D(str(trade['entry'])) or qty<D('.01') or qty>D(50) or qty%D('.01'):
            raise ValueError('review_entry_side_grid')
        atr=D(str(decision['atr']))
        if not 2*atr<=abs(entry-stop)<2*atr+D('.001'):
            raise ValueError('review_stop_anchor_outward_grid')
        if not F(0)<(abs(F(entry)-F(stop))+F(slip))*F(qty)<=25:
            raise ValueError('review_risk_budget')
        if D(str(trade['planned_risk']))!=(abs(entry-stop)+slip)*qty:
            raise ValueError('review_planned_risk')
        if entry*qty/10>cash:
            raise ValueError('review_margin')
        exit_ns=trade['exit_ns']
        end=exit_ns//1000000
        phase=exit_ns%NS
        exit_minute=(end//M)*M
        if phase==NS-2:
            exit_minute=(end//M)*M
        missing=[x for x in range(t,exit_minute+1,M) if x not in pairs]
        if missing and not trade['unresolved']:
            raise ValueError('review_missing_path_masked')
        expected=None
        # First protective crossing precedes scheduled exit at its exact open.
        for at in range(t,exit_minute+1,M):
            pair=pairs.get(at)
            if not pair:
                continue
            row=pair[0 if side=='BUY' else 1]
            opened=D(str(row['open']))
            if sign*(opened-stop)<=0:
                expected=(opened-sign*slip,at*1000000+1,'stop')
                break
            if at==exit_minute and trade['reason']!='stop':
                expected=(opened-sign*slip,at*1000000+1,trade['reason'])
                break
            extreme=D(str(row['low' if side=='BUY' else 'high']))
            if sign*(extreme-stop)<=0:
                expected=(stop-sign*slip,(at+M)*1000000-2,'stop')
                break
        if expected!=(D(str(trade['exit'])),exit_ns,trade['reason']):
            raise ValueError('review_first_stop_or_scheduled_fill')
        net=(F(str(trade['exit']))-F(entry))*F(qty)*sign
        if net!=F(str(trade['net'])):
            raise ValueError('review_fraction_net')
        cash_net=D(str(trade['net'])).quantize(D('.01'),rounding=ROUND_HALF_EVEN)
        if cash_net!=D(str(trade['cash_net'])):
            raise ValueError('review_money_rounding')
        cash+=cash_net
    native_realized=[D(str(x)) for x in result['native_realized']]
    if len(native_realized)!=len(result['trades']) or any(abs(a-D(str(t['cash_net'])))>D('.01') for a,t in zip(native_realized,result['trades'])):
        raise ValueError('review_native_per_position_money')
    if abs(D(10000)+sum(native_realized,D(0))-D(str(result['native_cash'])))>D('.01'):
        raise ValueError('review_native_cash')
    if cash!=D(str(result['decimal_cash'])):
        raise ValueError('review_decimal_cash')
    if len(result['fills'])!=2*len(result['trades'])+(1 if result['position'] else 0):
        raise ValueError('review_fill_census')
    if any(D(str(fill['commission'])) for fill in result['fills']):
        raise ValueError('review_zero_commission')
    if result['native_open_positions']!=int(result['position'] is not None):
        raise ValueError('review_position_census')
    if not result['position'] and result['native_open_orders']:
        raise ValueError('review_dangling_orders')
    if result['null'] and (result['fills'] or D(str(result['native_cash']))!=10000):
        raise ValueError('review_null')
    return dict(status='verified_execution_cash_only',trades=len(result['trades']),fills=len(result['fills']),
                unresolved=sum(t['unresolved'] for t in result['trades'])+int(result['position'] is not None),
                native_cash=str(result['native_cash']),full_tick_path_verified=False)


def metrics(result):
    rows={}
    for side in ('BUY','SELL','combined'):
        trades=[t for t in result['trades'] if side=='combined' or t['side']==side]
        known=[t for t in trades if not t['unresolved']]
        unresolved=len(trades)-len(known)+int(result['position'] is not None and (side=='combined' or result['position']['side']==side))
        net=sum((D(str(t['cash_net'])) for t in trades),D(0))
        rows[side]=dict(trades=len(trades),unresolved=unresolved,net_usd=None if unresolved else str(net),
                        modeled_closed_net_usd=str(net),known_closed_net_usd=str(sum((D(str(t['cash_net'])) for t in known),D(0))),
                        wins=sum(D(str(t['net']))>0 for t in known),known_trades=len(known),
                        slippage_usd=str(sum((2*D(str(result['slippage']))*D(str(t['quantity'])) for t in known),D(0))),
                        commission_usd='0',reasons=dict(Counter(t['reason'] for t in trades)))
    return dict(sides=rows,endpoint_equity_dd_usd=str(result['endpoint_equity_dd']),
                full_intraminute_equity_dd_usd=None,prop_qualified=False,
                events=dict(Counter(e['kind'] for e in result['policy_events'])),rejections=len(result['rejections']))
