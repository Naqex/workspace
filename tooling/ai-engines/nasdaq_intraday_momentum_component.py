"""Causal first-to-last-half NASDAQ price probe, not an account or execution book."""
from decimal import Decimal as D
from fractions import Fraction as F
import time

from index_close_momentum import plans_for
from fomc_price_component import observation
from nasdaq_h4_study import SCENARIOS, DAY

MINUTE = 60000
CANDIDATE = 'nasdaq-cash-firstlast30-price-component-v1'


def oracle_sides(sessions, pairs):
    """Rational arithmetic using only earlier session ranges and known first-half Close."""
    previous, history, sides = None, [], {}
    for day, stamps in sessions.items():
        first = pairs.get(stamps[29]) if len(stamps)==390 else None
        window = history[-14:]
        ready = len(window)==14 and all(x is not None for x in window) and sum(window)>0
        side = None
        if ready and previous is not None and first is not None:
            change = F(str(first[0]['close']))-previous
            side = 'BUY' if change>0 else 'SELL' if change<0 else None
        sides[day] = side
        tr = None
        if previous is not None and all(at in pairs for at in stamps):
            hi=max(F(str(pairs[t][0]['high'])) for t in stamps)
            lo=min(F(str(pairs[t][0]['low'])) for t in stamps)
            tr=max(hi-lo,abs(hi-previous),abs(lo-previous))
        history.append(tr)
        last=pairs.get(stamps[-1])
        previous=F(str(last[0]['close'])) if last is not None else None
    return sides


def prepare(sessions,pairs,*,start,end):
    if (type(start) is not int or type(end) is not int or start%DAY or end%DAY
            or end<=start or end>1735689600000):
        raise ValueError('component_window_or_holdout_closed')
    if not sessions or list(sessions)!=sorted(set(sessions)):
        raise ValueError('unordered_cash_calendar')
    for stamps in sessions.values():
        if len(stamps) not in (210,390) or stamps!=list(range(stamps[0],stamps[0]+len(stamps)*MINUTE,MINUTE)):
            raise ValueError('registered_cash_session_shape')
    plans=plans_for(sessions,pairs)
    oracle=oracle_sides(sessions,pairs)
    specs=[]
    for day,stamps in sessions.items():
        if not start<=stamps[0]<end:
            continue
        side=plans.get(stamps[-30],{}).get('side') if len(stamps)==390 else None
        if side!=oracle[day]:
            raise ValueError('independent_momentum_signal_mismatch')
        regular=len(stamps)==390
        specs.append(dict(candidate=CANDIDATE,session=day,year=int(day[:4]),signal_side=side,
            planned_trade=side is not None,status='planned_price_component' if side else 'regular_unready_or_flat' if regular else 'calendar_halfday_skipped',
            signal_known_at_ms=stamps[29]+MINUTE if regular else None,
            decision_ms=stamps[-30] if regular else None,entry_ms=stamps[-30]+MINUTE if regular else None,
            exit_decision_ms=stamps[-2] if regular else None,exit_ms=stamps[-2]+MINUTE if regular else None))
    return specs


def evaluate(sessions,pairs,*,start,end,market_function,cost_function,progress=None,deadline=None):
    began,cpu=time.perf_counter(),time.process_time()
    specs=prepare(sessions,pairs,start=start,end=end)
    output=[]
    for i,spec in enumerate(specs):
        if i%32==0:
            if deadline is not None and time.perf_counter()>deadline:
                raise TimeoutError('momentum_component_deadline')
            if progress:progress(i,len(specs))
        row=dict(**spec,entry=None,exit=None,outcomes={},path_expected_minutes=None,path_observed_minutes=None,
                 clean_oos=False,account_simulated=False,execution_authorized=False,broker_calls=0,model_calls=0)
        if spec['planned_trade']:
            if not spec['signal_known_at_ms']<spec['decision_ms']<spec['entry_ms']<spec['exit_decision_ms']<spec['exit_ms']:
                raise ValueError('momentum_causal_clock')
            entry=observation(pairs.get(spec['entry_ms']),spec['entry_ms'],duration_ms=MINUTE)
            exit_at=observation(pairs.get(spec['exit_ms']),spec['exit_ms'],duration_ms=MINUTE)
            path=list(range(spec['entry_ms'],spec['exit_ms'],MINUTE))
            row.update(entry=entry,exit=exit_at,path_expected_minutes=len(path),
                       path_observed_minutes=sum(t in pairs for t in path),status='unresolved_endpoint')
            if entry['bid'] is not None and exit_at['bid'] is not None:
                row['status']='resolved_price_component_not_account'
                for scenario in SCENARIOS:
                    instrument,model,_=market_function(scenario)
                    if instrument.instrument_id!='USATECH.IDX/USD' or instrument.contract_size!=1:
                        raise ValueError('momentum_research_geometry_identity')
                    row['outcomes'][scenario]={}
                    for role,side in [('primary',spec['signal_side']),('always_long_control','BUY')]:
                        costs=cost_function(model,side,D(1),instrument.contract_size,
                            D(entry['bid']),D(entry['ask']),D(exit_at['bid']),D(exit_at['ask']))
                        row['outcomes'][scenario][role]=dict(side=side,costs=costs,
                            net_usd_per_research_unit=str(costs['net_account']),planned_funding_usd='0')
        output.append(row)
    return dict(rows=output,wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu)


def summarize(rows,expected_sessions):
    if set(expected_sessions)!={2019,2022} or any(not v or len(v)!=len(set(v)) for v in expected_sessions.values()):
        raise ValueError('registered_two_year_session_census')
    expected=[(year,day) for year in [2019,2022] for day in expected_sessions[year]]
    if [(r['year'],r['session']) for r in rows]!=expected:
        raise ValueError('missing_or_repeated_session_rows')
    for row in rows:
        if (row['candidate']!=CANDIDATE or row['execution_authorized'] is not False or row['account_simulated'] is not False
                or row['clean_oos'] is not False or row['broker_calls']!=0 or row['model_calls']!=0):
            raise ValueError('component_identity_or_authority')
        if bool(row['outcomes']) and (not row['planned_trade'] or set(row['outcomes'])!=set(SCENARIOS)):
            raise ValueError('outcome_without_registered_trade')
    summary=[];gates=[]
    for year in [2019,2022]:
        group=[r for r in rows if r['year']==year]
        planned=[r for r in group if r['planned_trade']]
        resolved=[r for r in planned if r['outcomes']]
        for scenario in SCENARIOS:
            nets={}
            for role in ['primary','always_long_control']:
                values=[D(r['outcomes'][scenario][role]['net_usd_per_research_unit']) for r in resolved]
                positive=[v for v in values if v>0]
                nets[role]=sum(values,D(0))
                summary.append(dict(year=year,scenario=scenario,role=role,cash_sessions=len(group),
                    calendar_skipped=sum(r['status']=='calendar_halfday_skipped' for r in group),planned=len(planned),
                    resolved=len(resolved),unresolved=len(planned)-len(resolved),known_net_usd_per_research_unit=str(nets[role]),
                    positive=sum(v>0 for v in values),negative=sum(v<0 for v in values),
                    largest_positive_share=str(max(positive)/sum(positive)) if positive else None,
                    missing_path_windows=sum(r['path_observed_minutes']!=r['path_expected_minutes'] for r in resolved)))
            delta=nets['primary']-nets['always_long_control']
            summary.append(dict(year=year,scenario=scenario,role='paired_difference',planned=len(planned),resolved=len(resolved),
                unresolved=len(planned)-len(resolved),known_net_usd_per_research_unit=str(delta)))
            if scenario=='stress':
                gates.append(dict(year=year,retained=len(planned)>=100 and len(resolved)*100>=len(planned)*98 and nets['primary']>0 and delta>0))
        summary.append(dict(year=year,role='null_no_exposure',planned=len(planned),entries=0,known_net_usd_per_research_unit='0'))
    return dict(candidate=CANDIDATE,summary=summary,year_gates=gates,
        retained_for_further_research=all(g['retained'] for g in gates),scope='price_component_not_account_policy',
        clean_oos=False,account_simulated=False,execution_authorized=False,broker_calls=0,model_calls=0)
