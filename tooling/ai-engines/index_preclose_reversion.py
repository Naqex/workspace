"""Causal two-minute preclose adaptation; no end-of-day information leakage."""
from collections import deque
from datetime import datetime,timezone
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path

import cash_rsi_signal_oracle as oracle
import index_noise_study as core
import index_m1_book as book
from index_daily_reversion import rsi3

CANDIDATE='us500-cash-preclose2-cutler3-10-40-ibs05-atr14x1p5-r025-v1'


def bar_for(stamps,pairs):
    if not stamps or any(t not in pairs for t in stamps):return None
    rows=[pairs[t][0]for t in stamps]
    return dict(high=max(D(str(r['high']))for r in rows),low=min(D(str(r['low']))for r in rows),close=D(str(rows[-1]['close'])))


def plans_for(sessions,pairs):
    plans={};history=[];trs=deque(maxlen=14);closes=deque(maxlen=4);previous=None
    for _,stamps in sessions.items():
        current=bar_for(stamps[:-2],pairs)
        decision=stamps[-2]
        ibs=(current['close']-current['low'])/(current['high']-current['low'])if current and current['high']>current['low']else None
        indicator=rsi3([*closes,current['close']if current else None][-4:])
        partial_tr=max(current['high']-current['low'],abs(current['high']-previous),abs(current['low']-previous))if current and previous is not None else None
        tr_window=[*trs,partial_tr][-14:]
        atr=sum(tr_window,D(0))/14 if len(tr_window)==14 and all(t is not None for t in tr_window)else None
        side=None;distance=None
        if current is None or (ibs is not None and ibs>D('.5'))or(indicator is not None and indicator>40):side='EXIT'
        elif indicator is not None and indicator<10 and ibs is not None and ibs<=D('.5')and atr is not None and atr>0:
            side='BUY';distance=atr*D('1.5')
        rational_current={k:F(v)for k,v in current.items()}if current else None
        expected,expected_distance=oracle.expected_decision(history,rational_current)
        if side!=expected or (side=='BUY'and abs(float(distance)-float(expected_distance))>1e-10):
            raise ValueError('preclose_independent_signal_oracle_mismatch')
        if side:plans[decision]=dict(side=side,distance=distance,basis='partial_cash_prefix_before_last2minutes')
        # These two minutes belong only to future decisions, never this day's signal.
        full=bar_for(stamps,pairs)
        history.append({k:F(v)for k,v in full.items()}if full else None)
        tr=max(full['high']-full['low'],abs(full['high']-previous),abs(full['low']-previous))if full and previous is not None else None
        trs.append(tr);previous=full['close']if full else None;closes.append(previous)
    return plans


def simulate(sessions,pairs,*,slippage,null_control=False,progress=None,deadline=None):
    year=int(next(iter(sessions))[:4])
    return book.simulate(pairs,plans_for(sessions,pairs),candidate=CANDIDATE,slippage=slippage,
        funding_per_lot=D(1)if slippage==D('.25')else D(2),null_control=null_control,
        progress=progress,deadline=deadline,
        end_time_msc=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000))


if __name__=='__main__':
    import index_daily_reversion as daily
    core.main(candidate=CANDIDATE,simulator=simulate,include_extended=True,
        additional_sources=[Path(__file__),Path(book.__file__),Path(oracle.__file__),Path(daily.__file__)],
        study_metadata=dict(funding_reference_usd_per_lot_per_calendar_day='1',funding_stress_usd_per_lot_per_calendar_day='2',cash_bid_daily_signal=True,progress_unit='M1_bars'))
