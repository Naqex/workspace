"""Matched-trade arithmetic for one registered pre-ECB parent, not a backtest."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from fractions import Fraction as F
import hashlib
from pathlib import Path
import time
import traceback
from zoneinfo import ZoneInfo

from forex_screen_diagnostics import cost_diagnostic, decimal
from forex_study_batch import read, save, digest

CANDIDATE = 'eurusd-h1-pre-ecb02ny-14berlin-atr14x1p5-r025-v1'
YEARS = (2019, 2022)


def fraction(value):
    if isinstance(value,F):return value
    if isinstance(value,str) and '/' in value:
        try:return F(value)
        except (ValueError,ZeroDivisionError) as error:raise ValueError('invalid exact fraction') from error
    return F(decimal(value))


def factorial(rows):
    if not rows:
        return dict(status='inconclusive_empty_common_mask', trades=0)
    quantities = [fraction(r['quantity']) for r in rows]
    if any(q <= 0 or (q*100).denominator != 1 for q in quantities):
        raise ValueError('invalid lot quantity')
    no_stop = [fraction(r['no_stop_unit_usd']) for r in rows]
    original = [fraction(r['parent_unit_usd']) for r in rows]
    total_lots = sum(quantities, F(0)); average = total_lots/len(rows)
    a, b = average*sum(no_stop), average*sum(original)
    c = sum((q*r for q,r in zip(quantities,no_stop)),F(0))
    d = sum((q*r for q,r in zip(quantities,original)),F(0))
    fields = dict(total_lots=total_lots, mean_lots=average,
        equal_lot_no_stop_usd=a, equal_lot_parent_usd=b,
        observed_lots_no_stop_usd=c, observed_lots_parent_usd=d,
        weighting_without_stop_usd=c-a, stop_at_observed_weights_usd=d-c,
        stop_at_equal_weights_usd=b-a, weighting_after_parent_exit_usd=d-b,
        interaction_usd=d-c-b+a,
        unweighted_no_stop_mean_pips=sum(no_stop)/len(rows)/10,
        lot_weighted_no_stop_mean_pips=c/total_lots/10,
        unweighted_parent_mean_pips=sum(original)/len(rows)/10,
        lot_weighted_parent_mean_pips=d/total_lots/10)
    assert a+(c-a)+(d-c) == a+(b-a)+(d-b) == d
    return dict(status='matched_arithmetic_only', trades=len(rows), exact={k:str(v) for k,v in fields.items()},
        display={k:str((Decimal(v.numerator)/Decimal(v.denominator)).quantize(Decimal('.01')))
                 for k,v in fields.items()}, mean_lot_is_executable_policy=False,
        counterfactual_is_account_backtest=False, promotion_authorized=False)


def match_book(row, events, scenario):
    slip = '0' if scenario == 'reference' else '.00002'
    if row['candidate'] != CANDIDATE or row['scenario'] != scenario or scenario not in ('reference','cost-stress'):
        raise ValueError('parent_identity')
    cost_diagnostic(row, slippage=slip, commission_per_side='2.50')
    if (row['open_position'] is not None or row['pending_entry'] or row['pending_action'] is not None
            or decimal(row['financing_debit_usd']) != 0 or decimal(row['floating_usd']) != 0):
        raise ValueError('outside_flat_unfunded_attribution_scope')
    index = {e['day']:e for e in events}
    if len(index) != len(events):
        raise ValueError('duplicate_component_day')
    matched, excluded, seen = [], [], set()
    for trade in row['trades']:
        day = datetime.fromtimestamp(trade['entry_time_msc']/1000,timezone.utc).astimezone(
            ZoneInfo('America/New_York')).date().isoformat()
        if day in seen or trade['side'] != 'SELL' or day not in index:
            raise ValueError('duplicate_or_foreign_parent_entry')
        seen.add(day); e = index[day]
        if not e['entry_eligible']:
            excluded.append(dict(day=day, reason='component_entry_unavailable', parent_net_usd=trade['net_usd']))
            continue
        quote = e['quotes']['entry']
        if (trade['entry_time_msc'] != quote['time_msc'] or decimal(trade['entry_fill']) != decimal(quote['bid'])):
            raise ValueError('parent_component_entry_mismatch')
        baseline = e['views']['baseline_1400']
        if baseline['status'] != 'resolved':
            excluded.append(dict(day=day, reason='component_exit_unavailable', parent_net_usd=trade['net_usd']))
            continue
        q = fraction(trade['quantity'])
        unit = baseline['outcomes']['reference' if scenario == 'reference' else 'stress']['net_usd_per_standard_lot']
        original = fraction(trade['price_net_usd'])/q
        matched.append(dict(day=day, quantity=trade['quantity'], no_stop_unit_usd=unit,
            parent_unit_usd=str(original), parent_net_usd=trade['net_usd'],
            entry_time_msc=trade['entry_time_msc'], entry_fill=trade['entry_fill'],
            parent_exit_interval_msc=trade['exit_interval_msc'], parent_exit_fill=trade['exit_fill'],
            parent_reason=trade['reason'], endpoint_time_msc=e['quotes']['exit_1400']['time_msc']))
    answer = factorial(matched)
    if answer['trades']:
        matched_net = F(answer['exact']['observed_lots_parent_usd'])
    else:
        matched_net = F(0)
    excluded_net = sum((fraction(r['parent_net_usd']) for r in excluded),F(0))
    if matched_net+excluded_net != fraction(row['net_equity_usd']):
        raise ValueError('common_mask_partition_does_not_reconcile')
    answer.update(matched=matched, excluded=excluded, excluded_parent_net_usd=str(excluded_net),
        full_parent_net_usd=row['net_equity_usd'], parent_fills=row['entry_fills'],
        component_entry_eligible=sum(e['entry_eligible'] for e in events))
    return answer


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('catalogue','component','protocol','fixtures','output'):
        p.add_argument('--'+name,required=True,type=Path)
    args = p.parse_args(argv)
    args.output.mkdir(exist_ok=False)
    began = time.perf_counter()
    def progress(phase,**more):
        if phase not in ('failed','completed_matched_attribution'):
            if (args.output/'CANCEL').exists():raise InterruptedError('owner_cancelled')
            if time.perf_counter()-began>180:raise TimeoutError('attribution_deadline')
        state=dict(phase=phase,wall_seconds=time.perf_counter()-began,**more)
        save(args.output/'progress.json',state)
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:
            import json
            stream.write(json.dumps(state)+'\n')
        print(state,flush=True)
    try:
        fixtures=read(args.fixtures)
        if fixtures.get('status')!='passed' or fixtures.get('tool_sha256')!=digest(Path(__file__)):
            raise ValueError('fixtures_not_bound')
        review,link=read(args.component/'review-result.json'),read(args.component/'linkage-review.json')
        component_sha=digest(args.component/'result.json')
        if (review['status']!='completed_raw_and_arithmetic_review'
                or link['status']!='completed_event_source_linkage_review'
                or review['numerical_result_sha256']!=component_sha or link['numerical_result_sha256']!=component_sha
                or review['raw_selected_rows_verified']!=link['unique_source_rows_required']):
            raise ValueError('component_review_binding')
        pins={str(q):digest(q) for q in [Path(__file__),Path(__file__).with_name('forex_screen_diagnostics.py'),
            Path(__file__).with_name('forex_study_batch.py'),args.protocol,args.fixtures,args.catalogue/'config.json',
            args.component/'result.json',args.component/'manifest.json',args.component/'review-result.json',
            args.component/'linkage-review.json']}
        for name,sha in link['pins'].items():
            if digest(Path(name))!=sha:raise ValueError('component_quote_or_proof_drift')
            pins[name]=sha
        manifest=read(args.component/'manifest.json')
        books=[]
        for year in YEARS:
            path=args.catalogue/str(year)/'result.json'; seal_path=path.parent/'completed.json'
            seal=read(seal_path); result=read(path)
            if (seal['result_sha256']!=digest(path) or seal['config_sha256']!=digest(args.catalogue/'config.json')
                    or result['config_sha256']!=seal['config_sha256']
                    or result['source_files']!=read(args.catalogue/'config.json')['source_files']):
                raise ValueError('parent_seal_or_source_binding')
            pins[str(path)],pins[str(seal_path)]=digest(path),digest(seal_path)
            events=read(args.component/f'{year}-events.json')
            for scenario in ('reference','cost-stress'):
                candidates=[r for r in result['rows'] if r['candidate']==CANDIDATE and r['scenario']==scenario and r['year']==year]
                if len(candidates)!=1:raise ValueError('missing_or_duplicate_parent_book')
                books.append((year,scenario,candidates[0],events))
        save(args.output/'manifest.json',dict(pins=pins,created_at_utc=datetime.now(timezone.utc).isoformat(),
            scope='observed_lot_matched_trade_arithmetic_no_account_backtest'))
        for name in pins:
            source=Path(name)
            if source.suffix=='.py':
                destination=args.output/'source-snapshot'/source.name
                destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(source.read_bytes())
        rows=[];samples=[]
        for year,scenario,parent,events in books:
            progress('attribute_book',year=year,scenario=scenario)
            answer=match_book(parent,events,scenario)
            answer.update(year=year,scenario=scenario)
            rows.append(answer)
            if scenario=='reference':
                stop_rows=sorted((r for r in answer['matched'] if r['parent_reason']=='stop_loss'),key=lambda r:r['entry_time_msc'])[:4]
                for r in stop_rows:
                    e=next(e for e in events if e['day']==r['day'])
                    decisions=[d for d in parent['decisions'] if d['time_msc']==e['clocks']['entry'] and d['signal']=='SELL']
                    if len(decisions)!=1 or decimal(decisions[0]['quantity'])!=decimal(r['quantity']):
                        raise ValueError('sample_entry_decision_binding')
                    stop=((decimal(r['entry_fill'])+decimal(decisions[0]['stop_distance']))/Decimal('.00001')).to_integral_value(
                        rounding=ROUND_CEILING)*Decimal('.00001')
                    samples.append(dict(**r,year=year,stop_loss=str(stop),deadline=e['clocks']['exit_1400']))
        if any(digest(Path(name))!=sha for name,sha in pins.items()):raise ValueError('source_or_input_drift')
        save(args.output/'result.json',dict(status='completed_matched_attribution',rows=rows,
            raw_stop_sample=samples,raw_datasets=manifest['datasets'],manifest_sha256=digest(args.output/'manifest.json'),
            wall_seconds=time.perf_counter()-began,simulation_calls=0,broker_calls=0,model_calls=0,
            promotion_authorized=False,challenge_qualified=False,clean_oos=False))
        progress('completed_matched_attribution',books=len(rows),sampled_stops=len(samples))
    except BaseException as error:
        save(args.output/'failure.json',dict(error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        progress('failed')
        raise


if __name__=='__main__':main()
