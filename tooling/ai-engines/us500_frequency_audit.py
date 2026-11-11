"""Frequency-only pullback diagnostics. No orders, sizing or PnL computation."""
from collections import Counter
from decimal import Decimal as D
from fractions import Fraction as F

import us500_multiframe as parent


PROBES = (
    dict(id='FP00', common=True, touch=False, late=False),
    dict(id='FP01', common=False, touch=False, late=False),
    dict(id='FP02', common=False, touch=False, late=True),
    dict(id='FP03', common=False, touch=True, late=False),
    dict(id='FP04', common=False, touch=True, late=True),
)


def classify(e, probe, *, fast=20, slow=80, attempted=False):
    """Exclusive arm-stage reasons; clock and units are cash-session minute slots."""
    if not e['full_session']:
        return 'short_session'
    if e['blocked']:
        return 'causal_gap_block'
    m=e['m15']
    if not m:
        return 'missing_m15'
    previous=m['previous']
    if probe['common'] and not e['ready']:
        return 'not_ready'
    if not previous or slow not in m['means'] or slow not in previous['means']:
        return 'not_ready'
    if attempted:
        return 'attempt_consumed'
    side=parent.direction(m,fast,slow)
    if not side or parent.direction(previous,fast,slow)!=side:
        return 'no_stable_trend'
    if previous['day']!=e['day']:
        return 'previous_session'
    sign=1 if side=='BUY' else -1
    if sign*(previous['close']-previous['means'][fast])<=0:
        return 'previous_close_wrong_side'
    price=m['low' if side=='BUY' else 'high'] if probe['touch'] else m['close']
    if sign*(price-m['means'][fast])>0:
        return 'no_pullback'
    if m['atr']<=0:
        return 'invalid_atr'
    return side


def audit(prepared, pairs, probe, *, fast=20, slow=80):
    counts, day_reasons=Counter(),{}
    events=[]
    day=None
    attempted=False
    arm=None
    allowed=range(30,271,15) if probe['late'] else (30,45,60,75)
    cutoff=330 if probe['late'] else 90
    pending=None
    for e in prepared['snapshots'].values():
        if day!=e['day']:
            day=e['day']
            attempted=False
            arm=None
            pending=None
        # A future gap is not read to decide a signal; exact-open check occurs
        # only after the declared fill clock has been reached.
        if pending and e['t']>=pending['t']+parent.M:
            fill_t=pending['t']+parent.M
            if fill_t in pairs and pending['t'] in pairs:
                counts['exact_fill_available']+=1
            else:
                counts['exact_fill_unavailable']+=1
            pending=None
        if arm:
            if e['blocked']:
                events.append(dict(kind='cancel_gap',t=e['t'],arm_time=arm['t']))
                counts['cancel_gap']+=1
                arm=None
            elif e['m15']:
                if parent.direction(e['m15'],fast,slow)!=arm['side']:
                    events.append(dict(kind='cancel_trend',t=e['t'],arm_time=arm['t']))
                    counts['cancel_trend']+=1
                    arm=None
                else:
                    sign=1 if arm['side']=='BUY' else -1
                    beyond=sign*(F(e['m15']['close'])-F(arm['level'])-sign*F('0.1')*F(arm['atr']))>0
                    if arm['t']<e['t']<=arm['expiry'] and beyond:
                        events.append(dict(kind='confirm',t=e['t'],side=arm['side'],arm_time=arm['t']))
                        counts['confirm']+=1
                        pending=dict(t=e['t'])
                        arm=None
            if arm and e['t']>=arm['expiry']:
                events.append(dict(kind='expire',t=e['t'],arm_time=arm['t']))
                counts['expire']+=1
                arm=None
        if e['slot'] not in allowed:
            continue
        reason=classify(e,probe,fast=fast,slow=slow,attempted=attempted)
        key='eligible_arm' if reason in ('BUY','SELL') else reason
        counts['arm_slots']+=1
        counts[key]+=1
        day_reasons.setdefault(key,set()).add(day)
        if reason not in ('BUY','SELL'):
            continue
        attempted=True
        m=e['m15']
        arm=dict(t=e['t'],side=reason,level=m['high'] if reason=='BUY' else m['low'],atr=m['atr'],
                 expiry=min(e['t']+60*parent.M,e['t']+(cutoff-e['slot'])*parent.M))
        events.append(dict(kind='arm',**arm))
        counts['arm']+=1
    if pending:
        fill_t=pending['t']+parent.M
        counts['exact_fill_available' if fill_t in pairs and pending['t'] in pairs else 'exact_fill_unavailable']+=1
    terminal=sum(counts[k] for k in ('confirm','expire','cancel_gap','cancel_trend'))
    if arm or counts['arm']!=terminal:
        raise ValueError('frequency_attempt_terminal_census')
    if counts['confirm']!=counts['exact_fill_available']+counts['exact_fill_unavailable']:
        raise ValueError('frequency_exact_fill_census')
    buckets=('short_session','causal_gap_block','missing_m15','not_ready','attempt_consumed','no_stable_trend',
             'previous_session','previous_close_wrong_side','no_pullback','invalid_atr','eligible_arm')
    if counts['arm_slots']!=sum(counts[k] for k in buckets):
        raise ValueError('frequency_arm_bucket_census')
    return dict(probe=probe,fast=fast,slow=slow,counts=dict(counts),events=events,
                unique_days_by_reason={k:len(v) for k,v in day_reasons.items()},
                scope='confirmed_signals_not_executed_or_profitable_trades')


def parent_trace(prepared,config):
    policy=parent.Policy(config)
    for e in prepared['snapshots'].values():
        policy.event(e)
    return [{k:v for k,v in e.items() if k in ('kind','t','side')} for e in policy.events if e['kind'] in ('arm','confirm')]


def trace(result):
    return [{k:v for k,v in e.items() if k in ('kind','t','side')} for e in result['events'] if e['kind'] in ('arm','confirm')]
