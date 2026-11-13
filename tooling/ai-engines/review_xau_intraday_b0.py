"""Second arithmetic/path implementation; consumes frozen A0 only, never reselects trades."""
from bisect import bisect_left
from collections import Counter
from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path
import struct
import sys

from eurusd_b0_source import digest, write_json

RECORD=struct.Struct('<qii')


def cents(value):
    return int(value.quantize(D('.01'),rounding=ROUND_HALF_UP)*100)


def review(config_path):
    if sys.flags.optimize:raise ValueError('audit_requires_assertions')
    cfg=json.loads(Path(config_path).read_bytes());out=Path(cfg['output']);study=Path(cfg['study'])
    result=json.loads((out/'result.json').read_bytes())
    assert result['config_sha256']==digest(config_path)
    for name,sha in cfg['pins'].items():assert digest(Path(cfg['snapshot'])/name)==sha,name
    checked=Counter();receipts=[]
    tick_view=study/cfg['tick_view']
    seal=json.loads((tick_view/'seal.json').read_bytes())
    assert digest(tick_view/'seal.json')==cfg['tick_seal_sha256']
    hours={r['at']:r for r in seal['hours']}
    for year in cfg['years']:
        details=json.loads((out/f'{year}-details.json').read_bytes())
        assert not details['censored'],'unresolved_year_needs_partial_audit'
        cash={s:5_000_000 for s in ('reference','stress')}
        peak=dict(cash);minimum=dict(cash);dd={s:0 for s in cash};daily={s:0 for s in cash}
        counts=Counter();trades=[]
        def mark(s,equity,anchor):
            peak[s]=max(peak[s],equity);minimum[s]=min(minimum[s],equity)
            dd[s]=max(dd[s],peak[s]-equity);daily[s]=max(daily[s],anchor-equity)
        for day in details['days']:
            counts.update(day['counters']);trades.extend(day['trades'])
            assert len(day['trades'])<=2
            assert len(day['intents'])==day['counters']['raw_signals']
            assert Counter(i['status'] for i in day['intents'])['accepted']==len(day['trades'])
            for intent in day['intents']:
                if intent['status']=='friction_cap_rejected':assert intent['planned_stress_friction_r0']>.12
                if intent['status'] in ('accepted','daily_cap_rejected','position_active_rejected','wait_new_bar_rejected','margin_rejected'):
                    assert intent['planned_stress_friction_r0']<=.12
            anchors=dict(cash);quotes=[]
            needed=sorted({i['decision_msc']//3_600_000*3_600_000+n*3_600_000 for i in day['intents'] for n in range(3)})
            for hour in needed:
                path=tick_view/f'{hour}.ticks'
                assert digest(path)==hours[hour]['binary_sha256']
                quotes.extend(RECORD.iter_unpack(path.read_bytes()))
            times=[q[0] for q in quotes]
            previous_exit=-1
            for t in day['trades']:
                entry=t['entry_ordinal'];exit_i=t['exit_ordinal'];q=quotes[entry]
                assert entry==bisect_left(times,t['decision_msc'])
                assert t['decision_msc']>previous_exit
                assert tuple(q)==(t['entry_msc'],t['entry_bid_units'],t['entry_ask_units'])
                assert t['decision_msc']<=q[0]<=t['decision_msc']+60_000
                assert 9*3_600_000<q[0]%86_400_000<16*3_600_000
                sign=1 if t['side']=='BUY' else -1
                assert t['entry_units']==(q[2] if sign==1 else q[1])
                distance=sign*(t['entry_units']-t['stop_units'])
                assert distance>0 and t['take_units']==t['entry_units']+sign*2*distance
                assert t['planned_stress_risk_usd']<=150 and t['planned_stress_friction_r0']<=.12
                assert 1<=t['lot_steps']<=5000
                lots=D(t['lot_steps'])/100
                entry_fee=cents(D(t['entry_units'])/1000*100*lots*D('.000007'))
                base=dict(cash)
                assert base==t['base_cash']
                previous_at=q[0];maxgap=0
                for i in range(entry,exit_i+1):
                    at,bid,ask=quotes[i];price=bid if sign==1 else ask
                    maxgap=max(maxgap,at-previous_at);previous_at=at
                    stop=sign*(price-t['stop_units'])<=0
                    take=sign*(price-t['take_units'])>=0
                    timeout=at>=t['deadline_msc']
                    if i<exit_i:
                        assert not(stop or take or timeout),('earlier_exit',year,t['day'],i)
                        gross=cents(D(sign*(price-t['entry_units']))/1000*100*lots)
                        for s in cash:
                            debit=entry_fee+(20*t['lot_steps'] if s=='stress' else 0)
                            assert debit==t['entry_debits'][s]
                            mark(s,base[s]+gross-debit,anchors[s])
                        checked['floating_quote_marks']+=1
                    else:
                        expected_price,reason=(price,'SL') if stop else (t['take_units'],'TP_2R') if take else (
                            price,'TIME_STOP_2H' if t['time_stop_msc']<=at//86_400_000*86_400_000+18*3_600_000 else 'SESSION_CLOSE_1800')
                        assert stop or take or timeout
                        assert (t['exit_msc'],t['exit_bid_units'],t['exit_ask_units'])==(at,bid,ask)
                        assert (t['exit_units'],t['exit_reason'])==(expected_price,reason)
                assert maxgap==t['max_quote_gap_ms']
                assert (maxgap>60_000)==t['path_gap_gt60s']
                exit_fee=cents(D(t['exit_units'])/1000*100*lots*D('.000007'))
                gross=cents(D(sign*(t['exit_units']-t['entry_units']))/1000*100*lots)
                for s in cash:
                    slip=40*t['lot_steps'] if s=='stress' else 0
                    v=t['results'][s];net=gross-entry_fee-exit_fee-slip
                    assert (round(v['gross_after_spread_usd']*100),round(v['commission_usd']*100),round(v['slippage_usd']*100),round(v['conditional_net_usd']*100))==(gross,entry_fee+exit_fee,slip,net)
                    cash[s]+=net;mark(s,cash[s],anchors[s])
                    checked['scenario_trade_cash_bridges']+=1
                assert t['holding_minutes']<=(120+1) or t['path_gap_gt60s']
                assert t['exit_msc']%86_400_000<18*3_600_000+60_000
                previous_exit=t['exit_msc']
            assert cash==day['cash']
        for s in cash:
            row=next(r for r in result['rows'] if r['year']==year and r['scenario']==s)
            assert row['filled_trades']==len(trades)
            assert round(row['conditional_net_usd']*100)==cash[s]-5_000_000
            assert round(row['observed_equity_max_dd_usd']*100)==dd[s]
            assert round(row['observed_worst_daily_loss_usd']*100)==daily[s]
            assert round(row['minimum_equity_usd']*100)==minimum[s]
            assert sum(r['trades'] for r in row['exit_breakdown'])==len(trades)
            assert sum(r['trades'] for r in row['side_breakdown'])==len(trades)
            for group in ('exit_breakdown','side_breakdown'):
                assert sum(round(r['net_usd']*100) for r in row[group])==cash[s]-5_000_000
            assert sum(row['monthly_fills'].values())==len(trades)
            receipts.append(dict(year=year,scenario=s,trades=len(trades),cash_cents=cash[s],max_equity_dd_cents=dd[s],worst_daily_loss_cents=daily[s]))
    receipt=dict(status='PASS',kind='separate_arithmetic_path_self_audit_not_independent_agent_review',
        result_sha256=digest(out/'result.json'),code_sha256=digest(__file__),checks=dict(checked),rows=receipts)
    write_json(out/'arithmetic-path-review.json',receipt)
    return receipt


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args()
    print(json.dumps(review(a.config)))
