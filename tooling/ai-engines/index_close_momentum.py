"""First-to-last cash-half-hour momentum adaptation; no optimization grid."""
from collections import deque
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path

import index_noise_study as core
import index_m1_book as book

CANDIDATE='us500-cash-firstlast30-atr14quarter-r025-v1'


def plans_for(sessions,pairs):
    plans={};trs=deque(maxlen=14);previous=None
    for _,stamps in sessions.items():
        cash_open=stamps[0]
        plans[cash_open]=dict(side='EXIT',basis='cash_open_recovery_exit')
        if len(stamps)==390:
            first=pairs.get(stamps[29])
            atr=sum(trs,D(0))/14 if len(trs)==14 and all(x is not None for x in trs)else None
            if previous is not None and first is not None and atr is not None and atr>0:
                at10=D(str(first[0]['close']))
                side='BUY'if at10>previous else'SELL'if at10<previous else None
                if side:
                    plans[stamps[-30]]=dict(side=side,distance=atr*D('.25'),basis='prior_cash_close_to_10NY')
            plans[stamps[-2]]=dict(side='EXIT',basis='registered_1558_decision_1559_fill')
        # Today's range is appended only after all today's decisions are fixed.
        if all(at in pairs for at in stamps):
            rows=[pairs[at][0]for at in stamps]
            high=max(D(str(r['high']))for r in rows);low=min(D(str(r['low']))for r in rows)
            tr=max(high-low,abs(high-previous),abs(low-previous))if previous is not None else None
        else:tr=None
        trs.append(tr)
        last=pairs.get(stamps[-1]);previous=D(str(last[0]['close']))if last else None
    return plans


def simulate(sessions,pairs,*,slippage,null_control=False,progress=None,deadline=None,
             cost_scenario=core.LEGACY_COST_SCENARIO):
    year=int(next(iter(sessions))[:4])
    return book.simulate(pairs,plans_for(sessions,pairs),candidate=CANDIDATE,slippage=slippage,
        cost_scenario=cost_scenario,
        funding_per_lot=D(1)if slippage==D('.25')else D(2),null_control=null_control,
        progress=progress,deadline=deadline,
        end_time_msc=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000))


if __name__=='__main__':
    core.main(candidate=CANDIDATE,simulator=simulate,include_extended=True,
        additional_sources=[Path(__file__),Path(book.__file__)],
        study_metadata=dict(funding_reference_usd_per_lot_per_calendar_day='1',
                            funding_stress_usd_per_lot_per_calendar_day='2',
                            cash_bid_daily_signal=True,progress_unit='M1_bars'))
