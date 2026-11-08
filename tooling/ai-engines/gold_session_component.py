"""Registered gold session price/cost probes; no account sizing or broker authority."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from multiasset_monthly_input import number

CANDIDATES=('gold_asia_00_08_buy_r054_v1','gold_london_1030_1500_sell_r055_v1')


def schedules(years):
    if (not years or len(set(years))!=len(years)
            or any(type(y) is not int or not 2010<=y<=2024 for y in years)):
        raise ValueError('registered_gold_years_holdout_closed')
    result=[]
    for year in sorted(years):
        day=date(year,1,1)
        while day.year==year:
            if day.weekday()<5:
                for candidate,zone,start,stop,side in [
                    (CANDIDATES[0],timezone.utc,(0,0),(8,0),'BUY'),
                    (CANDIDATES[1],ZoneInfo('Europe/London'),(10,30),(15,0),'SELL')]:
                    local=datetime(day.year,day.month,day.day,tzinfo=zone)
                    entry=int(local.replace(hour=start[0],minute=start[1]).timestamp()*1000)
                    exit_at=int(local.replace(hour=stop[0],minute=stop[1]).timestamp()*1000)
                    result.append(dict(candidate=candidate,day=day.isoformat(),side=side,
                        decision_ms=entry-60000,entry_ms=entry,exit_ms=exit_at))
            day+=timedelta(days=1)
    return result


def observation(point,target):
    result=dict(schema='gold-session-source-observation-v1',instrument='XAUUSD',target_ms=target,
        source_bar_open_ms=target,known_at_upper_bound_ms=target+60000,quote_timestamp_interval_ms=[target,target+60000],
        observation_basis='source_M1_bid_only',price_unit='USD_per_troy_ounce',bid=None,ask=None,observed_ask=False,
        clean_oos=False,execution_authorized=False,executable_tick_proven=False,status='missing_exact_endpoint')
    if point is None:return result
    if point['time_ms']!=target or point.get('ask') is not None:raise ValueError('source_endpoint_or_invented_Ask')
    result.update(bid=str(number(point['bid'],D('.001'))),source_sequence=point['source_sequence'],status='observed_bid_only')
    return result


def evaluate(specs,points,*,cost_function,progress=None):
    result=[]
    for index,spec in enumerate(specs):
        if progress and index%500==0:progress(index)
        if not spec['decision_ms']<spec['entry_ms']<spec['exit_ms']:raise ValueError('causal_session_order')
        entry=observation(points.get(spec['entry_ms']),spec['entry_ms'])
        exit_at=observation(points.get(spec['exit_ms']),spec['exit_ms'])
        row=dict(**spec,entry=entry,exit=exit_at,status='unresolved_missing_endpoint',views={})
        if entry['bid'] is not None and exit_at['bid'] is not None:
            row['status']='resolved_price_proxy_not_account'
            for view,side in [('primary',spec['side']),('opposite_control','SELL' if spec['side']=='BUY' else 'BUY')]:
                outcomes={}
                for scenario,spread,slip in [('reference',D('.5'),D('.1')),('stress',D(1),D('.2'))]:
                    model=dict(version='gold-session-declared-'+scenario,spread_basis='bid_ask_embedded',
                        commission_per_side_account='0',commission_per_side_per_quantity_account='2.5',minimum_fee_account='0',
                        slippage_price_per_side=str(slip),financing_account='0',quote_to_account_rate='1',account_ccy='USD',rounding_decimals=2)
                    outcomes[scenario]=cost_function(model,side,D('.01'),D(100),D(entry['bid']),D(entry['bid'])+spread,
                        D(exit_at['bid']),D(exit_at['bid'])+spread)
                row['views'][view]=dict(side=side,continuous_lots='.01',underlying_ounces='1',outcomes=outcomes)
        result.append(row)
    return result


def summarize(rows,years):
    summary=[];priorities={}
    for candidate in CANDIDATES:
        for view in ('primary','opposite_control'):
            for scenario in ('reference','stress'):
                for year in years:
                    group=[r for r in rows if r['candidate']==candidate and r['day'].startswith(str(year))]
                    costs=[r['views'][view]['outcomes'][scenario] for r in group if r['views']]
                    values=[D(str(v['net_account'])) for v in costs];positive=sorted((v for v in values if v>0),reverse=True)
                    summary.append(dict(candidate=candidate,view=view,scenario=scenario,year=year,planned=len(group),resolved=len(costs),
                        unresolved=len(group)-len(costs),gross_sum=str(sum((D(str(v['gross_account'])) for v in costs),D(0))),
                        net_sum=str(sum(values,D(0))),mean=str(sum(values,D(0))/len(values)) if values else None,
                        positive=sum(v>0 for v in values),negative=sum(v<0 for v in values),zero=sum(v==0 for v in values),
                        minimum=str(min(values)) if values else None,maximum=str(max(values)) if values else None,
                        top5_positive_share=str(sum(positive[:5],D(0))/sum(positive,D(0))) if positive else None))
        stress=[r for r in summary if r['candidate']==candidate and r['view']=='primary' and r['scenario']=='stress']
        blocks=[dict(first=lo,last=lo+2,net_sum=str(sum((D(r['net_sum']) for r in stress if lo<=r['year']<=lo+2),D(0)))) for lo in (2010,2013,2016,2019,2022)]
        priorities[candidate]=dict(blocks=blocks,positive_stress_years=sum(D(r['net_sum'])>0 for r in stress),
            retained=(years==list(range(2010,2025)) and all(r['resolved']>=200 for r in stress)
                and sum(D(r['net_sum'])>0 for r in stress)>=10 and all(D(b['net_sum'])>0 for b in blocks)
                and sum((D(r['net_sum']) for r in stress),D(0))>0))
    return summary,priorities
