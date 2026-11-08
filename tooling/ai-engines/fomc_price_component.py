"""Frozen scheduled-event NASDAQ source-price probe; no account policy or orders."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from nasdaq_h4_study import HOUR, DAY, GRID, SCENARIOS

DATES = {
    2019: ('2019-01-30','2019-03-20','2019-05-01','2019-06-19','2019-07-31','2019-09-18','2019-10-30','2019-12-11'),
    2022: ('2022-01-26','2022-03-16','2022-05-04','2022-06-15','2022-07-27','2022-09-21','2022-11-02','2022-12-14'),
}
PUBLICATIONS = {2019:'2018-05-25T16:00:00+00:00',2022:'2021-06-04T15:00:00+00:00'}
CANDIDATE = 'nasdaq-pre-fomc-14prev-13event-NY-price-component-v1'


def schedules(years):
    if not years or len(set(years))!=len(years) or any(type(y) is not int or y not in DATES for y in years):
        raise ValueError('unregistered_FOMC_year_holdout_closed')
    ny=ZoneInfo('America/New_York')
    result=[]
    for year in sorted(years):
        publication=int(datetime.fromisoformat(PUBLICATIONS[year]).timestamp()*1000)
        for event in DATES[year]:
            day=date.fromisoformat(event)
            announcement=int(datetime(day.year,day.month,day.day,14,tzinfo=ny).timestamp()*1000)
            for role,shift in [('primary',0),('matched_week_control',7)]:
                finish=day-timedelta(days=shift);begin=finish-timedelta(days=1)
                entry=int(datetime(begin.year,begin.month,begin.day,14,tzinfo=ny).timestamp()*1000)
                exit_at=int(datetime(finish.year,finish.month,finish.day,13,tzinfo=ny).timestamp()*1000)
                result.append(dict(candidate=CANDIDATE,year=year,event=event,role=role,side='BUY',
                    calendar_publication_ms=publication,decision_ms=entry-HOUR,entry_ms=entry,exit_ms=exit_at,
                    announcement_ms=announcement))
    return result


def observation(pair,target):
    result=dict(source_instrument='USATECH.IDX/USD',source_bar_open_ms=target,
        quote_timestamp_interval_ms=[target,target+HOUR],known_at_upper_bound_ms=target+HOUR,
        basis='source_separate_side_H1_Open_proxy',bid=None,ask=None,status='missing_exact_hour',
        executable_tick_proven=False,broker_spec_verified=False,execution_authorized=False)
    if pair is None:return result
    if len(pair)!=2 or any(row['timestamp']!=target for row in pair):
        raise ValueError('FOMC_endpoint_side_clock')
    bid,ask=(D(str(row['open'])) for row in pair)
    if any(not p.is_finite() or p<=0 or p%GRID for p in (bid,ask)):
        raise ValueError('FOMC_endpoint_source_grid')
    if ask<bid:
        result['status']='crossed_endpoint';return result
    result.update(bid=str(bid),ask=str(ask),status='observed_separate_side_proxy')
    return result


def evaluate(specs,pairs,*,market_function,cost_function):
    expected=schedules(sorted({s['year'] for s in specs}))
    if specs!=expected:
        raise ValueError('FOMC_unregistered_calendar_or_recipe')
    output=[]
    for spec in specs:
        begin,finish=spec['entry_ms'],spec['exit_ms']
        if not spec['calendar_publication_ms']<spec['decision_ms']<begin<finish or finish-begin!=23*HOUR:
            raise ValueError('FOMC_causality_or_holding_interval')
        if spec['role']=='primary' and finish+HOUR>spec['announcement_ms']:
            raise ValueError('FOMC_exit_interval_reaches_announcement')
        entry=observation(pairs.get(begin),begin);exit_at=observation(pairs.get(finish),finish)
        path=list(range(begin,finish,HOUR))
        missing=[t for t in path if t not in pairs]
        row=dict(**spec,entry=entry,exit=exit_at,path_expected_hours=len(path),path_observed_hours=len(path)-len(missing),
            missing_path_hours=missing,status='unresolved_endpoint',outcomes={},
            clean_oos=False,account_simulated=False,broker_calls=0,execution_authorized=False)
        if entry['bid'] is not None and exit_at['bid'] is not None:
            row['status']='resolved_price_component_not_account'
            for scenario in SCENARIOS:
                instrument,model,rate=market_function(scenario)
                if instrument.instrument_id!='USATECH.IDX/USD' or instrument.contract_size!=1:
                    raise ValueError('FOMC_research_geometry_identity')
                costs=cost_function(model,'BUY',D(1),instrument.contract_size,
                    D(entry['bid']),D(entry['ask']),D(exit_at['bid']),D(exit_at['ask']))
                at=begin//DAY*DAY+22*HOUR
                if at<=begin:at+=DAY
                funding=[]
                while at<=finish:
                    debit=(D(entry['ask'])*rate/365).quantize(D('.01'),rounding=ROUND_HALF_UP)
                    funding.append(dict(time_msc=at,debit_usd=str(debit)));at+=DAY
                total=sum((D(f['debit_usd']) for f in funding),D(0))
                row['outcomes'][scenario]=dict(costs=costs,funding_events=funding,funding_usd=str(total),
                    net_usd_per_research_unit=str(D(str(costs['net_account']))-total))
        output.append(row)
    return output


def summarize(rows,years):
    expected=schedules(years)
    if len(rows)!=len(expected) or any(any(row.get(k)!=v for k,v in spec.items()) for row,spec in zip(rows,expected)):
        raise ValueError('FOMC_missing_or_changed_registered_rows')
    summary=[];retained=[]
    for year in sorted(years):
        group=[r for r in rows if r['year']==year]
        by_key={(r['event'],r['role']):r for r in group}
        common=[e for e in DATES[year] if all(by_key[e,role]['outcomes'] for role in ['primary','matched_week_control'])]
        for scenario in SCENARIOS:
            nets={}
            for role in ['primary','matched_week_control']:
                current=[by_key[e,role] for e in DATES[year]]
                values=[D(r['outcomes'][scenario]['net_usd_per_research_unit']) for r in current if r['outcomes']]
                net=sum(values,D(0));nets[role]=net
                positive=sorted([v for v in values if v>0],reverse=True)
                summary.append(dict(year=year,scenario=scenario,role=role,planned=8,resolved=len(values),unresolved=8-len(values),
                    net_usd_per_research_unit=str(net),positive=sum(v>0 for v in values),negative=sum(v<0 for v in values),
                    funding_usd=str(sum((D(r['outcomes'][scenario]['funding_usd']) for r in current if r['outcomes']),D(0))),
                    top_positive_share=str(positive[0]/sum(positive)) if positive else None,
                    holding_windows_with_missing_hours=sum(bool(r['missing_path_hours']) for r in current)))
            primary=sum((D(by_key[e,'primary']['outcomes'][scenario]['net_usd_per_research_unit']) for e in common),D(0))
            control=sum((D(by_key[e,'matched_week_control']['outcomes'][scenario]['net_usd_per_research_unit']) for e in common),D(0))
            summary.append(dict(year=year,scenario=scenario,role='paired_difference',planned=8,resolved=len(common),unresolved=8-len(common),
                net_usd_per_research_unit=str(primary-control)))
            if scenario=='stress':
                retained.append(dict(year=year,retained=len(common)>=7 and nets['primary']>0 and primary-control>0))
    return dict(summary=summary,year_gates=retained,retained_for_risk_wrapper_review=all(v['retained'] for v in retained),
        candidate=CANDIDATE,scope='price_component_not_account_policy',clean_oos=False,account_simulated=False,
        broker_calls=0,execution_authorized=False)
