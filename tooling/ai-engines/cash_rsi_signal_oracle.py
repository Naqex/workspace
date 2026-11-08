"""Independent rational-arithmetic oracle for the registered cash RSI/IBS policy."""
from fractions import Fraction as F


def expected_decision(history, current):
    if current is None:
        return 'EXIT', None
    width = current['high']-current['low']
    ibs = (current['close']-current['low'])/width if width>0 else None
    closes = [day['close'] if day else None for day in (history+[current])[-4:]]
    rsi = None
    if len(closes)==4 and all(c is not None for c in closes):
        changes=[closes[i]-closes[i-1] for i in range(1,4)]
        gains=sum((x for x in changes if x>0),F(0))
        losses=-sum((x for x in changes if x<0),F(0))
        rsi=F(100) if not losses else F(100)*gains/(gains+losses)
    if (ibs is not None and ibs>F(1,2)) or (rsi is not None and rsi>40):
        return 'EXIT',None
    days=(history+[current])[-15:]
    if rsi is None or rsi>=10 or ibs is None or ibs>F(1,2) or len(days)!=15 or any(d is None for d in days):
        return None,None
    tr=[]
    for previous,day in zip(days,days[1:]):
        tr.append(max(day['high']-day['low'],abs(day['high']-previous['close']),abs(day['low']-previous['close'])))
    distance=sum(tr,F(0))*F(3,28)
    return ('BUY',distance) if distance>0 else (None,None)


def oracle_plans(sessions,pairs):
    history=[]
    plans={}
    for _,stamps in sessions.items():
        current=None
        if all(at in pairs for at in stamps):
            bids=[pairs[at][0] for at in stamps]
            current=dict(high=max(F(str(row['high'])) for row in bids),
                         low=min(F(str(row['low'])) for row in bids),close=F(str(bids[-1]['close'])))
        side,distance=expected_decision(history,current)
        if side:
            plans[stamps[-1]+60000]=dict(side=side,distance=distance)
        history.append(current)
    return plans
