"""Separate rational-cost and direct-tick annual audit of frozen A validation."""
from collections import Counter
from pathlib import Path
import json

from eurusd_b0_source import digest,write_json
from xau_a_validation_source import Quotes,Calendar,END,HOUR
from xau_h1_execution_review import money_parts,rounded_cents,oracle_book


def review(root,calendar):
    root=Path(root);cfg=json.loads((root/'execution-binding.json').read_bytes())
    for p,sha in cfg['pins'].items():
        if digest(p)!=sha:raise ValueError('source_changed_during_run:'+p)
    result=json.loads((root/'result.json').read_bytes());trades=json.loads((root/'trades.json').read_bytes())
    manifest=json.loads((root/'binary-manifest.json').read_bytes());quotes=Quotes(manifest);cal=Calendar(calendar)
    for r in manifest.values():
        assert digest(r['path'])==r['sha256']
    paths=bridges=tick_marks=0;books=[]
    for t in trades:
        at=t['entry_msc'];end,deadline_reason=cal.deadline(at)
        assert at<END and t['exit_msc']<END and end==t['deadline_msc']
        entry,index=quotes.endpoint(t['decision_msc'])
        assert list(entry)==t['entry_quote'] and index==t['entry_quote_index']
        sign=1 if t['side']=='BUY' else -1
        found=None
        for q,index in quotes.interval(at,end+60000):
            px=q[1] if sign==1 else q[2]
            if q[0]>=end:found=(deadline_reason,px,q[0],index);break
            if sign*(px-t['stop_units'])<=0:found=('SL',px,q[0],index);break
        assert found==(t['reason'],t['exit_price_units'],t['exit_msc'],t['exit_quote_index'])
        for risk in (150,200):
            q=risk*1000//abs(t['entry_price_units']-t['stop_units'])
            for cell in ('SYM_FLAT','ASYM_FLAT'):
                p=money_parts(dict(t,ounces=q),cell);e=t['sizing_costs'][str(risk)][cell]
                for name,want in [('net_usd',p['net']),('gross_usd',p['gross']),
                    ('commission_usd',sum(p['commission'])),('slippage_usd',sum(p['slip'])),
                    ('swap_usd',sum(v for _,v in p['swaps']))]:
                    assert rounded_cents(str(e[name]))==want,(t['signal_id'],risk,cell,name)
                bridges+=1
        paths+=1
        if paths%50==0:print(json.dumps(dict(stage='path_and_cost_oracle',paths=paths)),flush=True)
    class Reader:
        def hour(self,at):return quotes.hour(at)[0]
    for risk in (150,200):
        for year in (2022,2023,2024):
            subset=[dict(t,ounces=risk*1000//abs(t['entry_price_units']-t['stop_units']))
                for t in trades if t['day'].startswith(str(year))]
            got,n=oracle_book(subset,Reader(),year,cells=('SYM_FLAT','ASYM_FLAT'));tick_marks+=n
            for cell,v in got.items():
                want=next(r for r in result['annual'] if (r['year'],r['risk_usd'],r['cell'])==(year,risk,cell))
                assert abs(v['cash_usd']-(want['balance_usd']-50000))<1e-6
                assert abs(v['dd_usd']-want['max_R_DD']*risk)<1e-6,(year,risk,cell,v,want)
                assert abs(v['daily_usd']-want['worst_daily_loss_pct']*500)<1e-6,(year,risk,cell,v,want)
            books.append(dict(year=year,risk=risk,oracle=got,tick_marks=n))
            print(json.dumps(dict(stage='direct_tick_annual_books',books=len(books),tick_marks=tick_marks)),flush=True)
    assert len(result['rolling'])==144
    assert len({(r['start_msc'],r['risk_usd'],r['cell']) for r in result['rolling']})==144
    for r in result['rolling']:
        assert [p['phase'] for p in r['phase_passes']]==list(range(1,len(r['phase_passes'])+1))
        assert all(p['at']>=r['start_msc'] and p['at']<END and p['days']>=4 for p in r['phase_passes'])
        assert r['native_terminal_checks']==len(r['phase_passes'])+int(r['first_breach'] is not None)
        assert r['floating_usd']==0 or r['first_breach'] is not None
    write_json(root/'arithmetic-review.json',dict(status='SELF_AUDIT_PASSED_NOT_INDEPENDENT_REVIEW',
        path_checks=paths,rational_cost_bridges=bridges,books=books,direct_tick_marks=tick_marks,
        rolling_cases_checked=144,reviewer_sha256=digest(__file__),
        result_sha256=digest(root/'result.json'),trades_sha256=digest(root/'trades.json'),
        prices2025_2026_read=False,broker_calls=0))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('calendar');a=p.parse_args();review(a.root,a.calendar)
