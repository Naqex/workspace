"""Read-only B0 source/fill and integer-cash audit; no research variants."""
from bisect import bisect_left
from collections import Counter
from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path
import sys

from eurusd_b0_source import MINUTE, digest, read_session, session, write_json


def review(config_path):
    cfg = json.loads(Path(config_path).read_bytes())
    out, root = Path(cfg['output']), Path(cfg['workspace'])
    result = json.loads((out/'result.json').read_bytes())
    if result['config_sha256'] != digest(config_path):
        raise ValueError('review_config_binding')
    for name, expected in cfg['source_pins'].items():
        assert digest(root/name) == expected, name
    rows, checked = [], Counter()
    for source in cfg['sources'][1:]:
        prepared = Path(cfg['prepared'])/source['first_day']
        seal = json.loads((prepared/'seal.json').read_bytes())
        for record in seal['files']:
            assert digest(prepared/record['name']) == record['sha256']
        bars = json.loads((prepared/'bars.json').read_bytes())
        maps = {width: {r[0]: r for r in bars[name]} for width, name in ((15, 'm15'), (60, 'h1'))}
        year = int(source['first_day'][:4])
        scenarios = {}
        for scenario in ('reference', 'stress'):
            d = json.loads((out/str(year)/(scenario+'-details.json')).read_bytes())
            summary = json.loads((out/str(year)/(scenario+'-summary.json')).read_bytes())
            counts, cash, peak, maxdd, dayloss, minimum = Counter(), 5_000_000, 5_000_000, 0, 0, 5_000_000
            def mark(eq, anchor):
                nonlocal peak, maxdd, dayloss, minimum
                peak = max(peak, eq)
                maxdd = max(maxdd, peak-eq)
                dayloss = max(dayloss, anchor-eq)
                minimum = min(minimum, eq)
            signatures = []
            for day in d['days']:
                counts.update(day['counters'])
                label = day['day']
                qs = read_session(prepared/(label+'.ticks')) if (prepared/(label+'.ticks')).exists() else []
                times = [q[0] for q in qs]
                clock = session(label)
                if scenario == 'reference':
                    for width, mapping in maps.items():
                        for at in range(clock[7], clock[12], width*MINUTE):
                            a, b = bisect_left(times, at), bisect_left(times, at+width*MINUTE)
                            points = qs[a:b]
                            if not points:
                                assert at not in mapping
                                continue
                            prices = [q[2] for q in points]
                            actual = [at, prices[0], max(prices), min(prices), prices[-1],
                                      len({q[0]//MINUTE for q in points})]
                            assert mapping[at] == actual, ('bar', label, width, at)
                            checked['same_source_session_bar_parity'] += 1
                anchor = cash
                assert len(day['trades']) <= 2
                for trade in day['trades']:
                    side = 1 if trade['side'] == 'BUY' else -1
                    steps = trade['lot_steps']
                    entry = bisect_left(times, trade['decision_msc'])
                    q = qs[entry]
                    assert (q[0], q[1], q[2], q[3]) == (trade['entry_msc'], trade['entry_sequence'],
                        trade['entry_bid_units'], trade['entry_ask_units'])
                    assert trade['decision_msc'] <= q[0] <= trade['decision_msc']+MINUTE
                    assert trade['entry_units'] == (q[3] if side == 1 else q[2])
                    assert cash == trade['base_cash_cents']
                    stop = trade['natural_stop_units']
                    distance = abs(trade['entry_units']-stop)
                    assert trade['take_units'] == trade['entry_units']+side*2*distance
                    assert steps*(q[3]-q[2]+9) <= 1800
                    assert (distance+10)*steps <= 15000  # native stress cost + one-grid reserve
                    if steps < 5000:
                        assert (distance+10)*(steps+1) > 15000
                    fee = (5 if scenario == 'reference' else 9)*steps
                    debit = int((D(fee)/2).to_integral_value(rounding=ROUND_HALF_UP))
                    assert debit == trade['entry_debit_cents']
                    mark(cash+(q[2]-q[3])*steps-debit, anchor)
                    exit_i = next(i for i in range(entry, len(qs)) if qs[i][1] == trade['exit_sequence'])
                    for quote in qs[entry:exit_i]:
                        at, seq, bid, ask = quote
                        price = bid if side == 1 else ask
                        assert side*(price-stop) > 0, ('earlier_SL', label)
                        assert side*(price-trade['take_units']) < 0, ('earlier_TP', label)
                        assert at < clock[12], ('earlier_cutoff', label)
                        mark(cash+side*(price-trade['entry_units'])*steps-debit, anchor)
                        checked['observed_equity_marks'] += 1
                    at, seq, bid, ask = qs[exit_i]
                    price = bid if side == 1 else ask
                    if side*(price-stop) <= 0:
                        expected_price, reason = price, 'stop_loss'
                    elif side*(price-trade['take_units']) >= 0:
                        expected_price, reason = trade['take_units'], 'take_profit'
                    else:
                        assert at >= clock[12]
                        expected_price, reason = price, 'session_cutoff'
                    assert (at, expected_price, reason) == (trade['exit_msc'], trade['exit_units'], trade['exit_reason'])
                    gross = side*(expected_price-trade['entry_units'])*steps
                    assert gross == round(trade['gross_after_spread_usd']*100)
                    assert gross-fee == round(trade['conditional_net_usd']*100)
                    # Verify the full mid -> spread -> limit -> explicit cost bridge.
                    assert abs(trade['matched_observed_mid_gross_usd']-trade['realized_spread_drag_usd']-
                        trade['tp_limit_no_improvement_drag_usd']-trade['gross_after_spread_usd']) < 1e-8
                    assert trade['news_checked'] is False and trade['target_calendar_verified'] is False
                    cash += gross-fee
                    mark(cash, anchor)
                    signatures.append((label, trade['entry_sequence'], trade['exit_sequence'], steps, stop, trade['take_units']))
                    checked['trade_cash_fill_cost_parity'] += 1
                assert cash == round(day['end_cash_usd']*100) if 'end_cash_usd' in day else not day['trades']
            assert cash-5_000_000 == round(summary['conditional_net_usd']*100)
            assert maxdd == round(summary['max_equity_dd_usd']*100)
            assert dayloss == round(summary['worst_daily_loss_usd']*100)
            assert minimum == round(summary['minimum_equity_usd']*100)
            assert dict(counts) == summary['counters']
            assert summary['strict_net_usd'] is None and summary['prop_qualified'] is False
            scenarios[scenario] = signatures
            rows.append(dict(year=year, scenario=scenario, cash_dd_daily_parity=True, trades=len(signatures)))
        assert scenarios['reference'] == scenarios['stress'], 'fee_scenarios_changed_decisions_or_sizes'
    receipt = dict(schema='eurusd-b0-review-v1', status='passed_scoped_self_review',
        config_sha256=digest(config_path), result_sha256=digest(out/'result.json'),
        review_source_sha256=digest(__file__), checks=dict(checked), rows=rows,
        independent_agent_review=False, independent_feed=False, full_native_replay_parity=False,
        strict_news_and_target_calendar_qualification=False, opened_2025_2026=False)
    write_json(out/'review.json', receipt)
    return receipt


if __name__ == '__main__':
    print(json.dumps(review(sys.argv[1]), indent=2))
