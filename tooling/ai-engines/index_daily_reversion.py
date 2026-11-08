"""Two frozen daily equity reversion adaptations, sharing the same M1 book."""
from collections import deque
from decimal import Decimal as D
from pathlib import Path
from datetime import datetime,timezone
import sys

import index_noise_study as core
import index_m1_book as book
import cash_rsi_signal_oracle as signal_oracle

IBS = 'us500-d1-ibs02-hold-atr14x1p5-r025-v1'
RSI = 'us500-d1-cutler3-10-40-ibs05-atr14x1p5-r025-v1'


def rsi3(closes):
    if len(closes)!=4 or any(c is None for c in closes):
        return None
    changes = [b-a for a,b in zip(closes,closes[1:])]
    gain = sum((max(v,D(0)) for v in changes),D(0))
    loss = sum((max(-v,D(0)) for v in changes),D(0))
    return D(100) if not loss else D(100)-D(100)/(1+gain/loss)


def plans_for(sessions,pairs,candidate):
    if candidate not in (IBS,RSI):
        raise ValueError('unknown_daily_reversion_policy')
    trs, closes = deque(maxlen=14), deque(maxlen=4)
    previous_close = None
    plans = {}
    for day, stamps in sessions.items():
        known = all(t in pairs for t in stamps)
        bar = None
        if known:
            bids = [pairs[t][0] for t in stamps]
            high = max(D(str(b['high'])) for b in bids)
            low = min(D(str(b['low'])) for b in bids)
            close = D(str(bids[-1]['close']))
            bar = dict(high=high,low=low,close=close)
        close = bar['close'] if bar else None
        tr = max(bar['high']-bar['low'],abs(bar['high']-previous_close),abs(bar['low']-previous_close)) if bar and previous_close is not None else None
        trs.append(tr)
        closes.append(close)
        decision_time = stamps[-1]+60000
        ibs = (close-bar['low'])/(bar['high']-bar['low']) if bar and bar['high']>bar['low'] else None
        indicator = rsi3(list(closes))
        atr = sum(trs,D(0))/14 if len(trs)==14 and all(v is not None for v in trs) else None
        if bar is None:
            plans[decision_time] = dict(side='EXIT',basis='incomplete_daily_data_safety_exit')
        elif candidate==IBS and ibs is not None and ibs>D('.2'):
            plans[decision_time] = dict(side='EXIT',basis='ibs_above_entry_bucket')
        elif candidate==RSI and ((ibs is not None and ibs>D('.5')) or (indicator is not None and indicator>40)):
            plans[decision_time] = dict(side='EXIT',basis='cutler3_or_ibs_exit')
        elif ibs is not None and atr and atr>0:
            enter = ibs<=D('.2') if candidate==IBS else indicator is not None and indicator<10 and ibs<=D('.5')
            if enter:
                plans[decision_time] = dict(side='BUY',distance=atr*D('1.5'),basis='cash_bid_daily_ibs_rsi')
        previous_close = close
    return plans


def simulator(candidate):
    def run(sessions,pairs,*,slippage,null_control=False,progress=None,deadline=None):
        plans = plans_for(sessions,pairs,candidate)
        if candidate==RSI:
            expected=signal_oracle.oracle_plans(sessions,pairs)
            if set(plans)!=set(expected) or any(plans[t]['side']!=expected[t]['side'] or
                (plans[t]['side']=='BUY' and abs(float(plans[t]['distance'])-float(expected[t]['distance']))>1e-10)
                for t in plans):
                raise ValueError('cash_RSI_independent_signal_oracle_mismatch')
        return book.simulate(pairs,plans,candidate=candidate,slippage=slippage,
            funding_per_lot=D(1) if slippage==D('.25') else D(2),null_control=null_control,
            progress=progress,deadline=deadline,
            end_time_msc=int(datetime(int(next(iter(sessions))[:4])+1,1,1,tzinfo=timezone.utc).timestamp()*1000))
    return run


if __name__=='__main__':
    candidate = sys.argv[1]
    if candidate not in (IBS,RSI):
        raise ValueError('unregistered_policy')
    del sys.argv[1]
    core.main(candidate=candidate,simulator=simulator(candidate),include_extended=True,
        additional_sources=[Path(__file__),Path(book.__file__),Path(signal_oracle.__file__)],
        study_metadata=dict(funding_reference_usd_per_lot_per_calendar_day='1',
                            funding_stress_usd_per_lot_per_calendar_day='2',cash_bid_daily_signal=True,
                            progress_unit='M1_bars'))
