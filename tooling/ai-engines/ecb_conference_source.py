"""Registered ECB source roles and quote presence; no signals, returns or fills."""
from bisect import bisect_left
from datetime import datetime
from zoneinfo import ZoneInfo

DATES=('2019-01-24','2019-09-12','2022-02-03','2022-09-08')
ZONE=ZoneInfo('Europe/Berlin')
MINUTE=60000
HOUR=3600000


def roles(day):
    if day not in DATES:
        raise ValueError('unregistered_ECB_source_date')
    new=day>='2022-07-21'
    start=datetime.fromisoformat(day).replace(hour=14,minute=45 if new else 30,tzinfo=ZONE)
    at=int(start.timestamp()*1000)
    return dict(day=day,conference_ms=at,pre=(at-15*MINUTE,at-5*MINUTE),
                post=(at+70*MINUTE,at+80*MINUTE),decision_ms=at+80*MINUTE,
                entry_not_before_ms=at+81*MINUTE,entry_expiry_ms=at+82*MINUTE)


def hours():
    result=set()
    for day in DATES:
        r=roles(day)
        for lo,hi in (r['pre'],r['post']):
            result.update(range(lo//HOUR*HOUR,(hi-1)//HOUR*HOUR+HOUR,HOUR))
        result.update(range(r['entry_not_before_ms']//HOUR*HOUR,r['entry_expiry_ms']//HOUR*HOUR+HOUR,HOUR))
    return sorted(result)


def validate_timestamps(stamps):
    if any(type(t) is not int or t<0 for t in stamps) or any(b<a for a,b in zip(stamps,stamps[1:])):
        raise ValueError('source_quote_timestamp_order_type')


def window_coverage(stamps,lo,hi):
    validate_timestamps(stamps)
    if type(lo)is not int or type(hi)is not int or hi-lo!=10*MINUTE or lo%MINUTE:
        raise ValueError('registered_ten_minute_window_required')
    values=stamps[bisect_left(stamps,lo):bisect_left(stamps,hi)]
    present=len({(t-lo)//MINUTE for t in values})
    if not values:
        return dict(quotes=0,populated_minutes=0,first_ms=None,last_ms=None,max_gap_ms=hi-lo,admitted=False)
    gap=max(values[0]-lo,hi-values[-1],max((b-a for a,b in zip(values,values[1:])),default=0))
    return dict(quotes=len(values),populated_minutes=present,first_ms=values[0],last_ms=values[-1],max_gap_ms=gap,
                admitted=present>=9 and values[0]<lo+MINUTE and values[-1]>=hi-MINUTE and gap<=2*MINUTE)


def availability(day,stamps):
    validate_timestamps(stamps)
    r=roles(day);pre=window_coverage(stamps,*r['pre']);post=window_coverage(stamps,*r['post'])
    i=bisect_left(stamps,r['entry_not_before_ms'])
    entry=stamps[i] if i<len(stamps) and stamps[i]<=r['entry_expiry_ms'] else None
    return dict(day=day,pre=pre,post=post,entry_locator_ms=entry,
                admitted=pre['admitted'] and post['admitted'] and entry is not None)
