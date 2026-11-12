"""TC01 causal recurring-clock component. No account, stop, engine or broker."""
from collections import Counter, deque
from fractions import Fraction as F

M = 60000
LOOKBACK = 20


def signals(sessions, pairs):
    history = deque(maxlen=LOOKBACK)
    events, reasons, days = [], Counter(), []
    for day, stamps in sessions.items():
        if len(stamps) != 390:
            reasons['short_session'] += 1
            days.append(dict(day=day, reason='short_session'))
            continue
        decision = stamps[0] + 30*M
        if len(history) < LOOKBACK:
            reason = 'warmup'
        elif any(x is None for x in history):
            reason = 'history_endpoint_missing'
        elif decision-M not in pairs:
            reason = 'decision_availability_missing'
        else:
            score = sum(history, F(0))/LOOKBACK
            reason = 'BUY' if score > 0 else 'SELL' if score < 0 else 'zero_score'
            if reason in ('BUY', 'SELL'):
                events.append(dict(kind='confirm', t=decision, side=reason, day=day,
                                   score_numerator=str(score.numerator), score_denominator=str(score.denominator)))
        reasons[reason] += 1
        days.append(dict(day=day, reason=reason))
        # Current target becomes training data only after today's decision.
        a, b = pairs.get(decision+M), pairs.get(decision+31*M)
        history.append(F(str(b[0]['open']))/F(str(a[0]['open']))-1 if a and b else None)
    return dict(events=events, reasons=dict(reasons), days=days)


def endpoint(signal, pairs, slip):
    t = signal['t']
    a, b = pairs.get(t+M), pairs.get(t+31*M)
    row = dict(day=signal['day'], decision=t, entry=t+M, exit=t+31*M, side=signal['side'],
               missing_held_minutes=sum(at not in pairs for at in range(t+M, t+32*M, M)))
    if not a or not b:
        return dict(row, known=False, gross_bidask=None, midpoint_benchmark=None, spread_debit=None, net=None)
    ab, aa, bb, ba = (F(str(x['open'])) for x in (a[0],a[1],b[0],b[1]))
    if signal['side'] not in ('BUY','SELL') or aa<ab or ba<bb or min(ab,aa,bb,ba)<=0:
        raise ValueError('component_side_or_quotes')
    sign = 1 if signal['side']=='BUY' else -1
    gross = bb-aa if sign==1 else ab-ba
    mid = sign*((bb+ba)/2-(ab+aa)/2)
    spread = (aa-ab+ba-bb)/2
    net = gross-2*F(slip)
    if mid-spread != gross:
        raise ValueError('component_spread_bridge')
    return dict(row, known=True, gross_bidask=gross, midpoint_benchmark=mid,
                spread_debit=spread, net=net)


def aggregate(rows):
    known = [r for r in rows if r['known']]
    def total(field):
        return sum((r[field] for r in known), F(0))
    return dict(planned=len(rows), known=len(known), unknown=len(rows)-len(known),
                net=total('net') if len(known)==len(rows) else None, known_net=total('net'),
                gross_bidask=total('gross_bidask'), midpoint_benchmark=total('midpoint_benchmark'),
                spread_debit=total('spread_debit'),
                known_rows_with_interior_gap=sum(r['missing_held_minutes']>0 for r in known))


def priority(annual):
    # Fraction values stay unrounded until presentation.
    if any(r['TC01']['net'] is None for r in annual):
        return 'inconclusive_endpoint_missing'
    totals={k:sum((r[k]['net'] for r in annual),F(0)) for k in ('TC01','BUY','SELL')}
    passed=(totals['TC01']>0 and sum(r['TC01']['net']>0 for r in annual)>=2
            and totals['TC01']>max(totals['BUY'],totals['SELL']))
    return 'eligible_component_next_stage_review' if passed else 'park_exact_component'
