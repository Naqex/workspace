"""Frozen XAU A0 observed-tick adapter with per-leg notional fees in USD cents."""
from bisect import bisect_left
from collections import Counter
from decimal import Decimal as D

from eurusd_b0 import Account

R0=15000
INITIAL=5000000
GRID=D('.001')
C=D(100)
RATE=D('.000007')
HOUR=3600000


def bind_native(root):
    from forex_study_batch import configure_source_root
    configure_source_root(root)
    global InstrumentSpec, CostModel, size_for_market_stop
    from trading_workspace_v2.retained import InstrumentSpec, CostModel
    from trading_workspace_v2.research_market import size_for_market_stop


def round_div(n,d):
    return (1 if n>=0 else -1)*((abs(n)+d//2)//d)


def commission_cents(price_units,steps):
    return round_div(7*steps*price_units,10000000)


def admission(candidate,bid,ask):
    side=candidate['side'];stop=candidate['stop_units']
    entry=ask if side=='BUY' else bid
    distance=(entry-stop) if side=='BUY' else (stop-entry)
    row=dict(candidate,entry_units=entry,entry_bid_units=bid,entry_ask_units=ask,
             natural_sl_usd_per_oz=distance/1000)
    if distance<=0 or (bid<=stop if side=='BUY' else ask>=stop):
        return dict(row,status='invalid_natural_stop')
    take=entry+(2*distance if side=='BUY' else -2*distance)
    bound_price=D(max(entry,stop,take))*GRID
    instrument=InstrumentSpec.from_mapping(dict(instrument_id='XAUUSD',asset_class='metal',base_ccy='XAU',
        quote_ccy='USD',account_ccy='USD',contract_size='100',tick_size='.001',pip_size='.1',
        quantity_min='.01',quantity_step='.01',effective_from_utc='2022-01-01T00:00:00Z'))
    model=CostModel.from_mapping(dict(version='XAU-A0-entry-commission-bound-v1',spread_basis='bid_ask_embedded',
        commission_per_side_account='0',commission_per_side_per_quantity_account=str(C*RATE*bound_price),
        minimum_fee_account='0',slippage_price_per_side='.20',financing_account='0',quote_to_account_rate='1',
        account_ccy='USD',rounding_decimals=2))
    quantity=size_for_market_stop(D(distance)*GRID,instrument=instrument,model=model,budget=D('149.98'))
    if quantity is None or quantity>50:
        return dict(row,status='quantity_rejected')
    steps=int(quantity*100)
    fees=(2*C*RATE*bound_price+D(40))*quantity+D('.02')
    friction=D(ask-bid)*GRID*C*quantity+fees
    planned=D(distance)*GRID*C*quantity+fees
    if planned>D(150):
        raise ValueError('XAU_planned_stress_stop_budget_exceeded')
    row.update(take_units=take,lot_steps=steps,quantity_lots=float(quantity),r_price_usd=distance*steps/1000,
        planned_stress_friction_r0=float(friction/D(150)),planned_stress_risk_usd=float(planned),
        margin_usd=float(D(entry)*GRID*C*quantity/10))
    return dict(row,status='friction_cap_rejected' if friction>D(18) else 'cost_admitted')


def protection(position,bid,ask):
    sign=1 if position['side']=='BUY' else -1
    price=bid if sign==1 else ask
    if sign*(price-position['stop_units'])<=0:return price,'SL'
    if sign*(price-position['take_units'])>=0:return position['take_units'],'TP_2R'
    return None


def run_day(day,candidates,quotes,accounts):
    clock=quotes[0][0]//86400000*86400000 if quotes else int(candidates[0]['decision_msc']//86400000*86400000)
    session_close=clock+18*HOUR
    times=[q[0] for q in quotes]
    index=0;position=None;last_exit=-1
    counts=Counter(raw_signals=len(candidates));intents=[];trades=[]
    anchors={s:a.cash for s,a in accounts.items()}

    def mark(q):
        if position is None:return
        at,bid,ask=q;sign=1 if position['side']=='BUY' else -1;price=bid if sign==1 else ask
        gross=round_div(sign*(price-position['entry_units'])*position['lot_steps'],10)
        position['mfe_price_units']=max(position['mfe_price_units'],sign*(price-position['entry_units']))
        position['mae_price_units']=min(position['mae_price_units'],sign*(price-position['entry_units']))
        for scenario,a in accounts.items():
            entry_debit=position['entry_debits'][scenario]
            exit_debit=commission_cents(price,position['lot_steps'])+(20*position['lot_steps'] if scenario=='stress' else 0)
            equity=position['base_cash'][scenario]+gross-entry_debit
            a.mark(equity,equity-exit_debit,anchors[scenario],at)

    def close(q,price,reason):
        nonlocal position,last_exit
        at,bid,ask=q;steps=position['lot_steps'];sign=1 if position['side']=='BUY' else -1
        position['mfe_price_units']=max(position['mfe_price_units'],sign*(price-position['entry_units']))
        position['mae_price_units']=min(position['mae_price_units'],sign*(price-position['entry_units']))
        gross=round_div(sign*(price-position['entry_units'])*steps,10)
        entry_comm=commission_cents(position['entry_units'],steps);exit_comm=commission_cents(price,steps)
        results={}
        for scenario,a in accounts.items():
            slip=40*steps if scenario=='stress' else 0
            net=gross-entry_comm-exit_comm-slip
            a.cash=position['base_cash'][scenario]+net
            a.mark(a.cash,a.cash,anchors[scenario],at)
            results[scenario]=dict(gross_after_spread_usd=gross/100,commission_usd=(entry_comm+exit_comm)/100,
                slippage_usd=slip/100,conditional_net_usd=net/100,net_r0=net/R0)
        trade={**position,'exit_msc':at,'exit_ordinal':index,'exit_units':price,'exit_bid_units':bid,'exit_ask_units':ask,
            'exit_reason':reason,'holding_minutes':(at-position['entry_msc'])/60000,'results':results,
            'conditional_financing_usd':0,'news_checked':False,'target_calendar_verified':False}
        trades.append(trade);last_exit=at;position=None

    def advance(until):
        nonlocal index
        if position is None:
            index=bisect_left(times,until,lo=index);return
        while index<len(quotes) and quotes[index][0]<until:
            q=quotes[index]
            if position is not None:
                gap=q[0]-position['last_path_msc']
                position['max_quote_gap_ms']=max(position['max_quote_gap_ms'],gap)
                if gap>60000:position['path_gap_gt60s']=True
                position['last_path_msc']=q[0]
                hit=protection(position,q[1],q[2])
                if hit:close(q,*hit)
                elif q[0]>=position['deadline_msc']:
                    reason='TIME_STOP_2H' if position['time_stop_msc']<=session_close else 'SESSION_CLOSE_1800'
                    close(q,q[1] if position['side']=='BUY' else q[2],reason)
                else:mark(q)
            index+=1
            if position is None:
                index=bisect_left(times,until,lo=index);break

    for candidate in candidates:
        at=candidate['decision_msc'];advance(at)
        if index>=len(quotes) or quotes[index][0]-at>60000 or quotes[index][0]>=clock+16*HOUR:
            counts['entry_quote_unavailable']+=1;intents.append(dict(candidate,status='entry_quote_unavailable'));continue
        quote=quotes[index];row=admission(candidate,quote[1],quote[2]);row['entry_msc']=quote[0]
        if row['status']!='cost_admitted':
            counts[row['status']]+=1;intents.append(row);continue
        counts['cost_admitted']+=1
        reason=('daily_cap_rejected' if counts['filled_entries']>=2 else
                'position_active_rejected' if position is not None else
                'wait_new_bar_rejected' if at<=last_exit else
                'margin_rejected' if row['margin_usd']*100>min(a.cash for a in accounts.values())-R0 else None)
        if reason:
            row['status']=reason;counts[reason]+=1;intents.append(row);continue
        row['status']='accepted';intents.append(row);counts['filled_entries']+=1
        steps=row['lot_steps'];entry_comm=commission_cents(row['entry_units'],steps)
        debits={s:entry_comm+(20*steps if s=='stress' else 0) for s in accounts}
        position={**row,'base_cash':{s:a.cash for s,a in accounts.items()},'entry_debits':debits,
            'entry_ordinal':index,'last_path_msc':quote[0],'max_quote_gap_ms':0,'path_gap_gt60s':False,
            'time_stop_msc':quote[0]+2*HOUR,'deadline_msc':min(quote[0]+2*HOUR,session_close),
            'mfe_price_units':0,'mae_price_units':0}
        for s,a in accounts.items():a.cash-=debits[s]
        mark(quote)
    advance(session_close+60000)
    counts['path_flagged_trades']=sum(t['path_gap_gt60s'] for t in trades)
    return dict(day=day,counters=dict(counts),intents=intents,trades=trades,unresolved_position=position,
        cash={s:a.cash for s,a in accounts.items()},anchors=anchors)
