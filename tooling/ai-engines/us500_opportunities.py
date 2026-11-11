"""Registered signal census only; no orders, exits, positions, sizing or PnL."""
from collections import Counter, deque
from datetime import datetime
from fractions import Fraction as F
from statistics import median
from zoneinfo import ZoneInfo

import us500_multiframe as parent
from us500_frequency_audit import classify, PROBES
from us500_ma_reclaim import CONFIG, ReclaimPolicy
from review_us500_strategy_fit import maximum_zero_run


def reclaim(prepared, *, retry=False):
    policy = ReclaimPolicy(CONFIG)
    counts = Counter()
    days = {}
    for e in prepared['snapshots'].values():
        if e['slot'] in range(30, 271, 15):
            same_day = policy.day == e['day']
            if same_day and policy.arm:
                reason = 'managing_arm'
            else:
                reason = classify(e, PROBES[2], attempted=policy.attempted if same_day else False)
                if reason in ('BUY', 'SELL'):
                    reason = 'eligible_arm'
            counts[reason] += 1
            days.setdefault(reason, set()).add(e['day'])
        before = len(policy.events)
        policy.event(e)
        added = policy.events[before:]
        if retry and any(x['kind'] in ('expire', 'cancel_trend', 'cancel_gap') for x in added):
            # The event already returned; a retry can only arm on a later bar.
            policy.attempted = False
    terminals = Counter(x['kind'] for x in policy.events)
    if policy.arm or terminals['arm'] != sum(terminals[k] for k in ('confirm', 'expire', 'cancel_trend', 'cancel_gap')):
        raise ValueError('opportunity_reclaim_terminal_census')
    return dict(events=policy.events, counts=dict(counts), terminal_counts=dict(terminals),
                unique_days_by_reason={k: len(v) for k, v in days.items()})


def triggers(prepared, mode):
    if mode not in ('FP07', 'FP08'):
        raise ValueError('registered_trigger_only')
    history = deque(maxlen=20)
    last_side = None
    last_day = None
    counts = Counter()
    days = {}
    events = []
    for e in prepared['snapshots'].values():
        m = e['m15']
        if last_day != e['day']:
            last_side = None
            last_day = e['day']
        if not m:
            if e['slot'] % 15 == 0:
                history.clear()
                last_side = None
            reason = 'missing_m15'
        else:
            if m['previous'] is None:
                history.clear()
                last_side = None
            side = None
            reason = 'no_trigger'
            if mode == 'FP07':
                if len(history) < 20 or m['atr'] <= 0:
                    reason = 'not_ready'
                else:
                    upper = max(x['high'] for x in history)
                    lower = min(x['low'] for x in history)
                    if F(m['close']) > F(upper) + F('0.1') * F(m['atr']):
                        side = 'BUY'
                    elif F(m['close']) < F(lower) - F('0.1') * F(m['atr']):
                        side = 'SELL'
                    if side and side != last_side:
                        reason = side
                    elif side:
                        reason = 'same_breakout_episode'
                    last_side = side
            else:
                previous = m['previous']
                if not previous or 80 not in m['means'] or 80 not in previous['means']:
                    reason = 'not_ready'
                elif previous['day'] != e['day']:
                    reason = 'previous_session'
                else:
                    now = m['means'][20] - m['means'][80]
                    old = previous['means'][20] - previous['means'][80]
                    if old <= 0 < now:
                        reason = 'BUY'
                    elif old >= 0 > now:
                        reason = 'SELL'
            history.append(m)
        if e['slot'] not in range(30, 331, 15):
            continue
        if not e['full_session']:
            reason = 'short_session'
        elif e['blocked']:
            reason = 'causal_gap_block'
        if reason in ('BUY', 'SELL'):
            events.append(dict(kind='confirm', t=e['t'], side=reason))
            reason = 'confirmed_signal'
        counts[reason] += 1
        days.setdefault(reason, set()).add(e['day'])
    return dict(events=events, counts=dict(counts), unique_days_by_reason={k: len(v) for k, v in days.items()})


def cadence(sessions, events, pairs):
    """Keep every calendar period; first/day selection precedes quote availability."""
    signals = [e for e in events if e['kind'] == 'confirm']
    stamps = [e['t'] for e in signals]
    if stamps != sorted(set(stamps)):
        raise ValueError('opportunity_duplicate_or_unordered_signal')
    zone = ZoneInfo('America/New_York')
    first = {}
    all_available = 0
    for signal in signals:
        day = datetime.fromtimestamp(signal['t'] // 1000, zone).date().isoformat()
        if day not in sessions:
            raise ValueError('opportunity_signal_off_calendar')
        first.setdefault(day, signal)
        all_available += signal['t'] in pairs and signal['t'] + parent.M in pairs
    daily = Counter({d: 0 for d in sessions})
    weekly = Counter({datetime.fromisoformat(d).date().isocalendar()[:2]: 0 for d in sessions})
    years = sorted({datetime.fromisoformat(d).year for d in sessions})
    monthly = {f'{y}-{m:02}': 0 for y in years for m in range(1, 13)}
    quarterly = {f'{y}-Q{q}': 0 for y in years for q in range(1, 5)}
    for day, signal in first.items():
        if signal['t'] not in pairs or signal['t'] + parent.M not in pairs:
            continue
        date = datetime.fromisoformat(day).date()
        daily[day] = 1
        weekly[date.isocalendar()[:2]] += 1
        monthly[day[:7]] += 1
        quarterly[f'{date.year}-Q{(date.month - 1) // 3 + 1}'] += 1
    total = sum(daily.values())
    if not (total == sum(weekly.values()) == sum(monthly.values()) == sum(quarterly.values())):
        raise ValueError('opportunity_period_census')
    return dict(raw_signals=len(signals), raw_exact_quote_available=all_available,
        first_signals_per_day=len(first), first_signal_exact_quote_available=total,
        scheduled_sessions=len(daily), per_five_sessions=total / len(daily) * 5 if daily else None,
        zero_weeks=sum(n == 0 for n in weekly.values()), iso_weeks=len(weekly),
        weekly_distribution=dict(sorted(Counter(weekly.values()).items())),
        monthly=monthly, quarterly=quarterly, month_median=median(monthly.values()) if monthly else None,
        max_no_signal_sessions=maximum_zero_run(daily.values()), daily=daily,
        scope='first_signal_per_day_quote_availability_not_position_admitted_or_executed_trades')
