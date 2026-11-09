"""Frozen monthly CFD trend adaptation; shared M1 execution, no fitted thresholds."""
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal as D

import index_m1_book as book
import index_noise_study as core


CANDIDATE = 'us500-cash-mom12-monthly-atr14x1p5-r025-v1'
BENCHMARK = 'us500-cash-monthly-long-benchmark-atr14x1p5-r025-v1'


def prepare(sessions, pairs, *, always_long=False):
    plans = {}
    observations = []
    months, ranges = deque(maxlen=13), deque(maxlen=14)
    previous_close = None
    days = list(sessions)
    previous_month = None
    for index, day in enumerate(days):
        stamps = sessions[day]
        month = day[:7]
        if month != previous_month:
            atr = sum(ranges, D(0))/14 if len(ranges) == 14 and all(v is not None for v in ranges) else None
            ordinals = [int(m[:4])*12+int(m[5:])-1 for m, _ in months]
            current_ordinal = int(month[:4])*12+int(month[5:])-1
            valid = (len(months) == 13 and all(value is not None for _, value in months)
                     and ordinals == list(range(current_ordinal-13, current_ordinal))
                     and atr is not None and atr > 0)
            side, distance = 'EXIT', None
            if valid:
                change = months[-1][1]-months[0][1]
                side = 'BUY' if always_long or change > 0 else 'SELL' if change < 0 else 'EXIT'
                if side != 'EXIT':
                    distance = atr*D('1.5')
            plans[stamps[0]] = dict(side=side, distance=distance,
                basis='prior13_cash_month_endpoints_and14_completed_cash_TR')
            observations.append(dict(month=month, signal_input_eligible=valid,
                history_month_count=len(months), missing_month_closes=[m for m, close in months if close is None],
                past_atr_ready=atr is not None and atr > 0,
                historical_fill_minute_present=stamps[0]+60000 in pairs))
        # No observation from today's cash session participates in its open decision.
        last = pairs.get(stamps[-1])
        close = D(str(last[0]['close'])) if last is not None else None
        if all(stamp in pairs for stamp in stamps) and previous_close is not None:
            high = max(D(str(pairs[stamp][0]['high'])) for stamp in stamps)
            low = min(D(str(pairs[stamp][0]['low'])) for stamp in stamps)
            tr = max(high-low, abs(high-previous_close), abs(low-previous_close))
        else:
            tr = None
        ranges.append(tr)
        previous_close = close
        if index+1 == len(days) or days[index+1][:7] != month:
            months.append((month, close))
        previous_month = month
    return plans, observations


def plans_for(sessions, pairs, *, always_long=False):
    return prepare(sessions, pairs, always_long=always_long)[0]


def input_coverage(observations):
    years = sorted({int(row['month'][:4]) for row in observations})
    evaluated = {}
    # The first calendar year is reserved for monthly signal warmup.
    for year in years[1:]:
        current = [row for row in observations if int(row['month'][:4]) == year]
        evaluated[str(year)] = dict(calendar_months_observed=len(current),
            signal_eligible_months=sum(row['signal_input_eligible'] for row in current),
            eligible_months_with_fill_quote=sum(row['signal_input_eligible'] and row['historical_fill_minute_present'] for row in current))
    unusable = [year for year, row in evaluated.items() if row['eligible_months_with_fill_quote'] == 0]
    return dict(evaluation_years=evaluated, unusable_evaluation_years=unusable,
        admitted=bool(evaluated) and not unusable,
        limits='Fill coverage is a retrospective input audit, never a condition on the earlier trading signal.')


def simulate(sessions, pairs, *, slippage, always_long=False, null_control=False,
             progress=None, deadline=None, cost_scenario=core.LEGACY_COST_SCENARIO):
    final_year = int(next(reversed(sessions))[:4])
    plans, observations = prepare(sessions, pairs, always_long=always_long)
    coverage = input_coverage(observations)
    if not coverage['admitted']:
        raise ValueError('monthly_input_has_unusable_evaluation_year')
    result = book.simulate(pairs, plans,
        cost_scenario=cost_scenario,
        candidate=BENCHMARK if always_long else CANDIDATE, slippage=slippage,
        funding_per_lot=D(1) if slippage == D('.25') else D(2),
        null_control=null_control, progress=progress, deadline=deadline,
        end_time_msc=int(datetime(final_year+1, 1, 1, tzinfo=timezone.utc).timestamp()*1000))
    result['signal_input_coverage'] = coverage
    return result
