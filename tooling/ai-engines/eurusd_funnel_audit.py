"""Observe saved B0 setup fates on Development only; no simulated orders/PnL."""
from collections import Counter
from decimal import Decimal as D
from statistics import median

from eurusd_b0_source import MINUTE, session


def minimum_distance_units(spread):
    """Solve the frozen cost cap with its native integer lot-floor, not a new SL."""
    if type(spread) is not int or spread < 0:
        raise ValueError('invalid_observed_spread_units')
    maximum_steps = 1800//(spread+9)
    if maximum_steps < 1:
        return None
    return max(1, 15000//(maximum_steps+1)-9)


def fate(setup, feature_map, zone_high, zone_low, cutoff):
    side = setup['side']
    buffer = D(setup['buffer_units'])
    edge = D(zone_high if side == 'BUY' else zone_low)
    for i in range(1, 5):
        at = setup['at']+i*15*MINUTE
        if at >= cutoff:
            return dict(reason='setup_cutoff_cancelled', at=at)
        f = feature_map.get(at)
        if f is None:
            return dict(reason='setup_gap_cancelled', at=at)
        if f['bias'] != side:
            return dict(reason='setup_bias_cancelled', at=at)
        _, o, h, l, c, _ = f['bar']
        if D(l) <= edge+buffer and D(h) >= edge-buffer:
            reclaim = D(c) > edge+buffer if side == 'BUY' else D(c) < edge-buffer
            body = c > o if side == 'BUY' else c < o
            reason = 'pre_cost_confirmed_signals' if reclaim and body else 'first_touch_not_confirmed'
            detail = ('confirmed' if reclaim and body else 'close_reclaim_failed_only' if body
                      else 'body_direction_failed_only' if reclaim else 'both_reclaim_and_body_failed')
            return dict(reason=reason, at=at, touch=True, trigger_detail=detail)
    return dict(reason='setup_expired', at=setup['at']+4*15*MINUTE)


def no_setup_reason(day, features, high, low):
    clocks = session(day)
    bars = Counter()
    for at in range(clocks[8]+15*MINUTE, clocks[11], 15*MINUTE):
        f = features.get(at)
        if f is None or f['atr_before'] is None:
            bars['feature_unavailable'] += 1
            continue
        close = D(f['bar'][4])
        buffer = f['atr_before']/10
        direction = 'BUY' if close > D(high)+buffer else 'SELL' if close < D(low)-buffer else None
        if direction is None:
            bars['no_geometric_breakout'] += 1
        elif f['bias'] is None:
            bars['neutral_or_unavailable_bias'] += 1
        elif direction != f['bias']:
            bars['opposite_bias'] += 1
        else:
            raise ValueError('aligned_breakout_missing_from_saved_setups')
    if bars['neutral_or_unavailable_bias'] and bars['opposite_bias']:
        label = 'mixed_neutral_and_opposite_bias'
    elif bars['neutral_or_unavailable_bias']:
        label = 'neutral_or_unavailable_bias_only'
    elif bars['opposite_bias']:
        label = 'opposite_bias_only'
    elif bars['no_geometric_breakout']:
        label = 'no_geometric_breakout'
    else:
        label = 'all_features_unavailable'
    return label, dict(bars)


def audit_days(days, features, year):
    if year not in (2022, 2023) or any(not d['day'].startswith(str(year)+'-') for d in days):
        raise ValueError('EURUSD_diagnostic_Development_only_2024_closed')
    zone_rows, setups, rejects, accepted = [], [], [], []
    totals, expected, stages, no_setup = Counter(), Counter(), Counter(), Counter()
    triggers = Counter()
    for day in days:
        expected.update(day['counters'])
        if not day['counters'].get('valid_zones'):
            continue
        label = day['day']
        clocks = session(label)
        zone_bars = [features[at]['bar'] for at in range(clocks[7]+15*MINUTE, clocks[8]+1, 15*MINUTE)]
        high, low = max(b[2] for b in zone_bars), min(b[3] for b in zone_bars)
        events = [e for e in day['events'] if e['kind'] == 'setup']
        fates = []
        for event in events:
            f = fate(event, features, high, low, clocks[11])
            row = {'day': label, **event, **f}
            row['breakout_msc'] = event['at']
            row['outcome_msc'] = f['at']
            fates.append(row)
            setups.append(row)
            totals['bias_breakouts'] += 1
            totals[f['reason']] += 1
            if f.get('touch'):
                totals['first_touches'] += 1
                triggers[f['trigger_detail']] += 1
            if f['reason'] == 'pre_cost_confirmed_signals':
                matching = [i for i in day['intents'] if i['breakout_msc'] == event['at']
                            and i['decision_msc'] == f['at'] and i['side'] == event['side']]
                if len(matching) != 1:
                    raise ValueError('reconstructed_trigger_saved_intent_mismatch')
        confirmed = sum(f['reason'] == 'pre_cost_confirmed_signals' for f in fates)
        touched = sum(bool(f.get('touch')) for f in fates)
        if confirmed:
            stage = 'confirmation_reached'
        elif touched:
            stage = 'touch_reached_no_confirmation'
        elif events:
            stage = 'bias_breakout_reached_no_admitted_touch'
        else:
            stage = 'no_admitted_bias_breakout'
        reason, bars = (no_setup_reason(label, features, high, low) if not events else (None, None))
        if reason:
            no_setup[reason] += 1
        stages[stage] += 1
        zone_rows.append(dict(day=label, stage=stage, setup_count=len(events),
            first_touches=touched, confirmations=confirmed, no_setup_reason=reason,
            no_setup_bar_counts=bars, setup_fates=dict(Counter(f['reason'] for f in fates))))
        for intent in day['intents']:
            row = dict(intent)
            if intent['status'] == 'friction_cap_rejected':
                s = intent['entry_ask_units']-intent['entry_bid_units']
                d = intent['distance_units']
                steps = 15000//(d+10)
                if steps != intent['lot_steps'] or steps*(s+9) <= 1800:
                    raise ValueError('saved_cost_rejection_does_not_match_frozen_arithmetic')
                minimum = minimum_distance_units(s)
                if minimum is None or d >= minimum:
                    raise ValueError('threshold_does_not_explain_saved_rejection')
                row.update(entry_spread_units=s, minimum_admissible_sl_pips=minimum/10,
                           sl_shortfall_pips=(minimum-d)/10)
                rejects.append(row)
            elif intent['status'] == 'accepted':
                accepted.append(row)
            else:
                raise ValueError('unregistered_other_intent_status')
    for key in ('bias_breakouts', 'first_touches', 'pre_cost_confirmed_signals',
                'first_touch_not_confirmed', 'setup_expired', 'setup_cutoff_cancelled',
                'setup_bias_cancelled', 'setup_gap_cancelled'):
        if totals[key] != expected[key]:
            raise ValueError('saved_setup_counter_parity:'+key)
    if (sum(stages.values()) != expected['valid_zones'] or len(rejects) != expected['friction_cap_rejected']
            or len(accepted) != expected['filled_entries']):
        raise ValueError('zone_or_intent_census_mismatch')
    summary = dict(year=year, valid_zones=len(zone_rows), exclusive_zone_stages=dict(stages),
        no_setup_subtypes=dict(no_setup), setup_fates=dict(totals), trigger_details=dict(triggers),
        confirmed_signal_events=totals['pre_cost_confirmed_signals'],
        confirmed_unique_zones=stages['confirmation_reached'],
        zones_without_confirmation=len(zone_rows)-stages['confirmation_reached'],
        cost_rejected_events=len(rejects), filled_events=len(accepted),
        cost_rejected_sl_pips=dict(count=len(rejects), median=median(r['natural_sl_pips'] for r in rejects),
                                  minimum=min(r['natural_sl_pips'] for r in rejects), maximum=max(r['natural_sl_pips'] for r in rejects)),
        cost_required_sl_pips=dict(median=median(r['minimum_admissible_sl_pips'] for r in rejects),
                                  minimum=min(r['minimum_admissible_sl_pips'] for r in rejects),
                                  maximum=max(r['minimum_admissible_sl_pips'] for r in rejects)),
        saved_B0_counter_parity=True, new_strategy_backtests=0, pnl_computed=False)
    return dict(summary=summary, zones=zone_rows, setups=setups, rejected_intents=rejects,
                accepted_intents=accepted)
