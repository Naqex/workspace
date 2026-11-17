"""Full entry anatomy only after committed Dev decision; no new Full child backtest."""
import json
import subprocess
import numpy as np
from prop_v22_common import *
from prop_v22_development import snapshot
from prop_v21_forensics import Context
from quant_core.exhaustion_gate import accept


def run():
    frozen=read(JOB/'Development-decision.json')
    assert json.loads(subprocess.check_output(['git','show','HEAD:'+FREEZE.as_posix()]))==frozen
    assert frozen['selected'] is None
    c=Context(False);cache={};trades=read(V19/'Full-OLHC-PRIMARY-trades.json')
    forensic=unpack('Full-OLHC-forensics',V21);lookup={r['trade_key']:r for r in forensic}
    rows=[]
    for t in trades:
        r=snapshot(t,c,cache);f=lookup[r['trade_key']]
        r.update(net_R=f['net_R'],label=f['label'],MFE_R=f['MFE_R'],MAE_R=f['MAE_R'],
            source_provisional=f['provisional'],open_path_unknown=f['open_path_unknown'],
            G_L3_A_accept=accept(r,'G_L3_A',frozen['thresholds']),
            G_L3_B_accept=accept(r,'G_L3_B',frozen['thresholds']))
        assert r['day_range_ATR']==f['day_range_ATR']
        rows.append(r)
    top=sorted([r for r in rows if r['net_R']>0],key=lambda r:(-r['net_R'],r['trade_key']))[:10]
    devtop=sorted([r for r in rows if r['net_R']>0 and r['year']<=2023],key=lambda r:(-r['net_R'],r['trade_key']))[:10]
    l3=[r for r in rows if r['label']=='L3'];assert len(l3)==45
    def stats(rs):
        def median(key):
            v=[r[key] for r in rs if r[key] is not None]
            return float(np.median(v)) if v else None
        return dict(count=len(rs),net_R=sum(r['net_R'] for r in rs),median_range_ATR=median('day_range_ATR'),
            median_edge_distance=median('edge_distance'),median_body_H4_ATR=median('signal_body_H4_ATR'),
            median_signal_range_H4_ATR=median('signal_range_H4_ATR'),provisional=sum(r['source_provisional'] for r in rs))
    grouped={}
    for period,dev in (('2018-2023',True),('2024-2026YTD',False)):
        for label,rs in (('GlobalTop10',top),('DevOnlyTop10',devtop),('L3',l3)):
            for asset in sorted({r['id'] for r in rows}):
                selected=[r for r in rs if r['id']==asset and (r['year']<=2023)==dev]
                if selected:grouped[period+' / '+label+' / '+asset]=stats(selected)
    compressed('Full-entry-anatomy',rows)
    save('anatomy-summary.json',dict(top10=top,Dev_top10=devtop,L3=l3,groups=grouped,
        canonical_trades=494,source_provisional=sum(r['source_provisional'] for r in rows),
        full_child_backtest_performed=False,Dev_decision_unchanged=True,freeze_sha256=sha(FREEZE)))
    event('V22_full_anatomy_complete',rows=len(rows),top10=len(top),L3=len(l3))


if __name__=='__main__':run()
