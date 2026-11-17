"""Three registered Development-only structural ablations, no later selection."""
import subprocess
from prop_v23_common import *
from prop_v21_forensics import Context,marked_metrics
from quant_core.sleeve_ablation import weakest_sleeve,admitted
from quant_core.trade_forensics_classifier import summarize,concentration


def register():
    files=[PROTOCOL,*Path('tooling/ai-engines').glob('prop_v23_*.py'),Path('tooling/ai-engines/quant_core/sleeve_ablation.py')]
    save('registration.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        code={str(p):sha(p) for p in files},Development=[FIRST,DEV_END],ablations=3,F5_transfers=3,
        V22_report_sha256=sha('planning/research/EXHAUSTION-H1-ALIGN-V22-RESULTS-20261117.json'),
        V21_report_sha256=sha('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json'),
        later_history_already_exposed=True,global_top10_known_before_registration=True))


def run():
    for p,digest in read(JOB/'registration.json')['code'].items():
        if sha(p)!=digest:raise ValueError('V23_registration_code_drift:'+p)
    context=Context(True);rows=unpack('Dev-OLHC-forensics',V21)
    target=weakest_sleeve(rows)
    profiles=[dict(name='A1_DROP_WEAKEST',drop_id=target),dict(name='A2_F3_EXHAUSTION90'),dict(name='A2_F4_EXHAUSTION90')]
    save('profiles-before-outcomes.json',dict(profiles=profiles,weakest=target,criterion='Dev mean NetR/trade, lexical tie break'))
    totals=[];cases=[]
    global_top={r['trade_key'] for r in read(V21/'Full-forensics-summary.json')['OLHC']['concentration']['top10']}
    dev_top={r['trade_key'] for r in concentration(rows)['top10']}
    old=read(V21/'Dev-forensics-summary.json')
    for identity in sorted({r['id'] for r in rows}):
        r=[r for r in rows if r['id']==identity]
        trades=[t for t in read(V19/'Dev-OLHC-PRIMARY-trades.json') if t['id']==identity]
        totals.append(dict(id=identity,summary=summarize(r),metrics=marked_metrics(trades,context,'OLHC'),
            winrate=sum(v['net_R']>0 for v in r)/len(r),mean_R=sum(v['net_R'] for v in r)/len(r),
            ExGlobalTop10_R=sum(v['net_R'] for v in r if v['trade_key'] not in global_top),
            ExDevTop10_R=sum(v['net_R'] for v in r if v['trade_key'] not in dev_top)))
    save('Dev-sleeve-summary.json',dict(rows=totals,global_top10_from_prior_exposed_V21=True,used_for_A1_selection='Dev mean only'))
    for p in profiles:
        outcomes=[]
        for tag in ('OLHC','OHLC'):
            records=read(V19/f'Dev-{tag}-PRIMARY-trades.json');original=unpack(f'Dev-{tag}-forensics',V21)
            d={r['trade_key']:r for r in original}
            kept=[t for t in records if admitted(t,d[f"{t['id']}@{t['entry_msc']}"]['day_range_ATR'],p)]
            keys={f"{t['id']}@{t['entry_msc']}" for t in kept};chosen=[r for r in original if r['trade_key'] in keys]
            m=marked_metrics(kept,context,tag);base=old[tag]['metrics'];reasons=[]
            if m['net_R']<=base['net_R']+1e-8:reasons.append('NET_NOT_HIGHER')
            if m['equity_R_DD']>=base['equity_R_DD']-1e-8:reasons.append('EQUITY_DD_NOT_LOWER')
            if m['worst_daily_R']>base['worst_daily_R']+1e-8:reasons.append('DAILY_LOSS_INCREASE')
            clusters=[sum(r['net_R'] for r in chosen if lo<=r['year']<=hi) for lo,hi in ((2018,2020),(2021,2023))]
            if min(clusters)<=0:reasons.append('DUAL_CLUSTER_FAIL')
            outcomes.append(dict(order=tag,base=base,candidate=m,taxonomy=summarize(chosen),concentration=concentration(chosen),
                cluster_R=clusters,retained=len(chosen),top10_retained=sum(k in keys for k in dev_top),passed=not reasons,reasons=reasons))
        cases.append(dict(profile=p,cases=outcomes,passed=all(r['passed'] for r in outcomes)))
    attribution=[]
    for identity in sorted({r['id'] for r in rows}):
        reject=[r for r in rows if r['id']==identity and r['family'] in ('F3','F4') and (r['day_range_ATR'] is None or r['day_range_ATR']>.9)]
        attribution.append(dict(id=identity,rejected=len(reject),avoided_loss_R=-sum(r['net_R'] for r in reject if r['net_R']<=0),
            lost_winner_R=sum(r['net_R'] for r in reject if r['net_R']>0),L3_loss_R=-sum(r['net_R'] for r in reject if r['label']=='L3')))
    save('Dev-ablation-results.json',dict(cases=cases,V22_A_attribution=attribution))
    event('V23_ablation_complete',passing=[r['profile']['name'] for r in cases if r['passed']])


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('register','run'));a=p.parse_args();globals()[a.stage]()
