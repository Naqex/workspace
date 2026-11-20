"""Pass 7 native H1 scout. USDJPY M1 admission is tracked separately via QDM CLI."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import correlation

import pass5_usdjpy_tokyo as tokyo

ASSETS = ('EURJPY', 'EURUSD', 'GBPUSD')
PARENT = '268f3a4'
PROTOCOL = '9b806c22ce98f8e70d2907a9ab7f0eddadb706a3'
PROTOCOL_FILE = 'PASS7-USDJPY-FULL-M1-EQUITY-AND-FX-SCOUT-PROTOCOL-20261120.md'


def scout_cost(asset, spec):
    pip = .01 if asset == 'EURJPY' else .0001
    commission = spec['commission_usd_per_lot_roundtrip']
    contract = spec['spec']['trade_contract_size']
    if commission != 5 or contract != 100000:
        raise ValueError(f'Unregistered FX cost: {asset}')
    spread = spec['spread']['median'] * pip
    # Pass 5's Costs.spread is expressed on its original USDJPY price grid.
    return pip, tokyo.Costs(spread/tokyo.PIP, commission, contract)


def quote_cash(entry_mid, exit_mid, side, *, cost, pip, quote_per_usd=1.):
    unit = cost.contract / quote_per_usd
    gross = side*(exit_mid-entry_mid)*unit
    spread = cost.spread*unit
    slippage = 2*cost.slip_pips_per_side*pip*unit
    friction = spread + cost.commission_usd + slippage
    return dict(gross=gross, spread=spread, commission=cost.commission_usd,
                slippage=slippage, swap=0., cost=friction, net=gross-friction,
                cost_pips=friction/(unit*pip), gross_pips=gross/(unit*pip),
                net_pips=(gross-friction)/(unit*pip))


def admitted(summary):
    scale = summary['friction_scale']
    return (summary['pass_stage0'] and scale is not None
            and scale['median_cost_over_median_stop_pct'] <= 12
            and scale['pass_share_at_12pct'] >= .5)


def paired_loss_correlation(rows, jpy):
    reference = {x['day']: x['net_R'] for x in jpy}
    overlaps = [(reference[x['day']],x['net_R']) for x in rows if x['day'] in reference]
    result = {}
    for name, cohort in (('all', overlaps), ('USDJPY_negative', [x for x in overlaps if x[0] < 0])):
        a,b = zip(*cohort) if cohort else ((),())
        result[name] = dict(n=len(cohort), pearson=correlation(a,b) if min(len(set(a)),len(set(b))) > 1 else None)
    return result


def scout(asset, hourly, daily, costs, jpy_hourly, jpy_closed):
    pip, recipe = scout_cost(asset, costs)
    conversion = (lambda at: jpy_hourly[at].o) if asset == 'EURJPY' else lambda _: 1.
    def value(at, start, end, direction):
        return quote_cash(start, end, direction, cost=recipe, pip=pip, quote_per_usd=conversion(at))
    def stop_risk(at, event):
        return event['natural_stop_pips'] * pip * recipe.contract / conversion(at)

    clock, atr = tokyo.atr_checkpoints(daily)
    coverage = defaultdict(Counter)
    events = []
    for day in range(tokyo.START, tokyo.STOP, tokyo.DAY):
        d = tokyo.date(day)
        if d.weekday() >= 5:
            continue
        c = coverage[d.year]
        c['weekdays'] += 1
        status, dual, event = tokyo.run_day(day, hourly, clock, atr, recipe, pip=pip, value_at=value)
        c[status] += 1
        if dual is not None:
            c['has_box_activation'] += 1
            c['any_dual_touch'] += int(dual)
        if event is not None:
            events.append(event)
    horizons = {h: tokyo.evaluate(events,h) for h in tokyo.HORIZONS}
    ready = [h for h,z in horizons.items() if admitted(z)]
    rows = []
    missing_conversion = 0
    if ready:
        for event in events:
            try:
                rows.append(tokyo.sl_trade(event,hourly,recipe,stop_risk_usd=stop_risk,value_at=value))
            except KeyError:
                missing_conversion += 1
    return dict(decision='PROMOTE_TO_PASS8_M1_CHECK' if ready else 'REJECTED_AT_STAGE0',
                valued_events=len(events), coverage=coverage, pip=pip,
                spread_pips=recipe.spread/pip, commission_usd_per_lot=recipe.commission_usd,
                slippage_pips_per_side=recipe.slip_pips_per_side, horizons=horizons,
                promoted_horizons=ready,
                sl_active=tokyo.sl_summary(rows) if rows else None,
                sl_conversion_missing=missing_conversion if ready else None,
                correlation_with_pass5=paired_loss_correlation(rows,jpy_closed) if rows else None), events, rows


def run(jobs, output):
    lock_path = tokyo.ROOT/'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json'
    if tokyo.sha(lock_path) != tokyo.LOCK_SHA:
        raise ValueError('Holdout lock drift')
    lock = tokyo.read(lock_path)
    if tokyo.sha(tokyo.AUDIT) != lock['audit_sha256']:
        raise ValueError('Target cost audit binding drift')
    fees = tokyo.read(tokyo.AUDIT)['symbols']
    folder = jobs/'bottleneck2-monfri-20261119/development'
    parent = jobs/'pass5-usdjpy-tokyo-box-20261120'
    closed_path = parent/'verified/sl_active_ledger.json'
    if tokyo.sha(closed_path) != tokyo.read(parent/'manifest.json')['files']['verified/sl_active_ledger.json']['sha256']:
        raise ValueError('Pass 5 SL ledger drift')
    jpy_closed = tokyo.read(closed_path)
    jpy = tokyo.load_sealed(folder,'H1',lock['series']['USDJPY']['H1'])
    output.mkdir(exist_ok=False)
    result = dict(schema='pass7-native-fx-scout-v1', protocol_commit=PROTOCOL, parent=PARENT,
                  holdout_lock_sha256=tokyo.LOCK_SHA, holdout_price_files_read=0, order_send_count=0,
                  input_sha256={'USDJPY':{'H1':lock['series']['USDJPY']['H1']['development_sha256']}},
                  scout={})
    for asset in ASSETS:
        series = lock['series'][asset]
        hourly, daily = (tokyo.load_sealed(folder,f,series[f],asset=asset) for f in ('H1','D1'))
        result['input_sha256'][asset] = {f: series[f]['development_sha256'] for f in ('H1','D1')}
        agg, events, sl = scout(asset,hourly,daily,fees[asset],jpy,jpy_closed)
        result['scout'][asset] = agg
        tokyo.write(output/f'{asset}-stage0-events.json',events)
        if sl:
            tokyo.write(output/f'{asset}-sl-active.json',sl)
        print(asset,agg['decision'],len(events),agg['promoted_horizons'],flush=True)
    tokyo.write(output/'fx-scout.json',result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.jobs, args.output)
