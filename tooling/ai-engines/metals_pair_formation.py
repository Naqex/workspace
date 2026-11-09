"""Fixed XAU/XAG source sample; economic policy and execution remain absent."""
from datetime import datetime,timezone
from decimal import Decimal as D
import math

import fx_pair_formation
from nasdaq_cash_calendar import calendar_for
from sealed_m1_review import cash_sessions

SYMBOLS=('xauusd','xagusd')
HOUR=3600000


def formation_sample(books, year):
    if type(year) is not int or year not in (2018,2021):
        raise ValueError('unregistered_metals_formation_year')
    if set(books)!={(s,p) for s in SYMBOLS for p in ('bid','ask')}:
        raise ValueError('metals_source_identity_census')
    lower=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1000)
    upper=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000)
    indexed={}
    for identity,rows in books.items():
        index={};previous=-1
        for row in rows:
            at=row['timestamp']
            if type(at) is not int or not lower<=at<upper or at%HOUR or at<=previous:
                raise ValueError('metals_source_scope_or_H1_order')
            values={k:D(str(row[k])) for k in ('open','high','low','close')}
            if any(not p.is_finite() or p<=0 or p%D('.001') for p in values.values()):
                raise ValueError('metals_source_price_grid')
            if not values['low']<=min(values['open'],values['close'])<=max(values['open'],values['close'])<=values['high']:
                raise ValueError('metals_source_OHLC')
            index[at]=values;previous=at
        indexed[identity]=index
    census=[];samples=[];missing=[]
    for day in cash_sessions(calendar_for(year)):
        at=int(datetime.fromisoformat(day).replace(hour=16,tzinfo=timezone.utc).timestamp()*1000)
        absent=[s+'-'+p for s in SYMBOLS for p in ('bid','ask') if at not in indexed[s,p]]
        crossed=[s for s in SYMBOLS if all(at in indexed[s,p] for p in ('bid','ask'))
                 and any(indexed[s,'ask'][at][k]<indexed[s,'bid'][at][k] for k in ('open','close'))]
        row=dict(date=day,source_time_msc=at,known_at_msc=at+HOUR,absent=absent,crossed=crossed)
        census.append(row)
        if absent or crossed:
            missing.append(row)
        else:
            samples.append(dict(**row,xauusd_bid_close=str(indexed['xauusd','bid'][at]['close']),
                                xagusd_bid_close=str(indexed['xagusd','bid'][at]['close'])))
    return dict(year=year,expected_dates=len(census),observed_pairs=len(samples),
                source_admitted=not missing and len(samples)>=240,missing=missing,census=census,samples=samples,
                sample_basis='16UTC_H1Close_known17UTC_frozen_US_cash_business_dates_not_metals_calendar',
                clean_oos=False,strategy_simulated=False,execution_authorized=False,broker_calls=0)


def diagnose_sample(sample):
    if type(sample.get('year')) is not int or sample['year'] not in (2018,2021):
        raise ValueError('unregistered_metals_formation_year')
    if not sample['source_admitted']:
        return dict(status='inconclusive_missing_registered_dates_no_statistics',retained_for_economic_design=False)
    rows=sample['samples']
    result=fx_pair_formation.diagnose([math.log(float(r['xauusd_bid_close'])) for r in rows],
                                    [math.log(float(r['xagusd_bid_close'])) for r in rows])
    legacy=result.pop('legs')
    result['legs']={'xauusd':legacy['gbpusd'],'xagusd':legacy['audusd']}
    result['orientation']={'y':'ln(XAU_USD_BidClose)','x':'ln(XAG_USD_BidClose)'}
    result['legacy_helper_labels']={'gbpusd':'xauusd_y','audusd':'xagusd_x'}
    return result
