"""Exactly three F5 transfers and truthful H1 price-versus-session diagnosis."""
import numpy as np
from datetime import datetime,timezone
from prop_v23_common import *
from prop_v12_campaign import load_bars
from prop_v15_evidence import bars_for
from prop_v12_signals import rejection_recipes
from prop_v21_development import measure,screen
from prop_v16_paths import CausalFlatSchedule
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_sl_active_kernel import PathIndex,replay
from quant_core.gap_aware_execution import GapAwarePathIndex,replay_gap_aware
from quant_core.exhaustion_gate import resolution_cutoff

DAY,HOUR=86400000,3600000


class FXResearchCalendar:
    """Declared FX weekday scenario, distinct from Gold holiday restrictions."""
    def cutoff(self,entry,asset):return entry//DAY*DAY+20*HOUR
    def off_kind(self,at,asset):
        d=datetime.fromtimestamp(int(at)/1000,timezone.utc)
        if d.weekday()>=5:return 'WEEKEND'
        if (d.month,d.day) in ((1,1),(12,25)):return 'DECLARED_FX_HOLIDAY'
        return None
    def allowed(self,at):return self.off_kind(at,'FX') is None and at%DAY<20*HOUR


def h1_diagnosis():
    rows=read(V22/'independent-audit.json')['H1_missing'];out=[];summary={}
    old_schedule=CausalFlatSchedule(gold_calendar(FIRST,DEV_END).events.values())
    index=read(ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json')
    for asset in ('GBPUSD','AUDUSD'):
        bars=load_bars(asset,index);n=exact=0
        for r in [r for r in rows if r['asset']==asset]:
            d=datetime.fromtimestamp(r['decision']/1000,timezone.utc);i,j=bars['t'].searchsorted([r['decision'],r['deadline']])
            entry=int(bars['t'][i])==r['decision'];endpoint=int(bars['t'][j])==r['deadline']
            assert entry and endpoint
            out.append(dict(**r,date=d.date().isoformat(),entry_exact=entry,endpoint_exact=endpoint,
                prior_off_kind=old_schedule.off_kind(r['decision'],asset),prior_calendar=old_schedule.events.get(d.date().isoformat()),
                diagnosis='ENTRY_CALENDAR_REJECTION_NOT_MISSING_PRICE',new_price_rows_added=0,
                target_account_permission='UNVERIFIED_UNLESS_DATE_SPECIFIC_NOTICE'))
        for case in [r for r in read(V22/'H1-behavioral-results.json')['rows'] if r['asset']==asset]:
            name=asset+'-'+case['recipe'].replace(':','_')+'-H1-raw';m=unpack(name,V22)
            ix=bars['t'].searchsorted(m['deadline']);safe=np.minimum(ix,len(bars)-1)
            available=(ix<len(bars))&(bars['t'][safe]==m['deadline'])
            assert available.all();n+=len(available);exact+=int(available.sum())
            per_year=[]
            for year in range(2018,2024):
                use=(np.array(m['years'])==year)&available
                per_year.append(dict(year=year,count=int(use.sum()),net_R=float((np.array(m['net'])[use]/np.array(m['natural'])[use]).sum()),
                    mean_net_pips=float(np.array(m['net'])[use].mean()*1e4) if use.any() else None))
            # Corrected availability, counterfactual weekday model only. No new fills.
            compressed(asset+'-'+case['recipe'].replace(':','_')+'-calendar-diagnostic',dict(price_available=available,
                annual=per_year,source_manifest_sha256=sha(V22/(name+'-manifest.json')),target_sessions_certified=False))
        summary[asset]=dict(observations=n,exact_endpoints=exact,coverage_pct=100*exact/n,prior_invalid_rows=6,
            actual_missing_endpoints=0,eligibility_not_certified=True)
    save('H1-calendar-diagnosis.json',dict(rows=out,summary=summary,source_prices_modified=0,
        V22_coverage_interpretation_corrected=True,early_close_needed_to_create_prices=False))
    event('V23_H1_calendar_diagnosed',actual_missing=0,calendar_rejections=len(out))


def transfers():
    source=read(ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json');out=[]
    for asset in ('GBPUSD','AUDUSD','XAUUSD'):
        hourly=asset!='XAUUSD';bars=load_bars(asset,source) if hourly else bars_for(asset,True)
        calendar=FXResearchCalendar() if hourly else gold_calendar(FIRST,DEV_END)
        schedule=calendar if hourly else CausalFlatSchedule(calendar.events.values())
        candidates=rejection_recipes(bars,asset,FIRST,DEV_END,calendar,native=hourly)
        recipe=next(r for r in candidates if r['config']['tf']=='H4' and r['config']['n']==5)
        assert recipe['config']==dict(family='F5',tf='H4',n=5,adx=25,buffer=.1)
        m=measure(recipe,bars,asset,schedule,hourly=hourly)
        r=screen(m);r['kind']='F5_EXACT_TRANSFER';r['data_resolution']='H1' if hourly else 'M1'
        r['cluster_net_R']=[float((m['net'][m['ok']&(m['years']>=lo)&(m['years']<=hi)]/
            m['natural'][m['ok']&(m['years']>=lo)&(m['years']<=hi)]).sum()) for lo,hi in ((2018,2020),(2021,2023))]
        r['dual_cluster_positive']=min(r['cluster_net_R'])>0
        r['cost_only_retention']=float((m['ratio']<=.12).mean()) if len(m['ratio']) else 0
        r['exact_intrahour_path_certified']=False
        if r['stage0_passed']:
            m['_index']=PathIndex(bars,asset=asset,step=HOUR) if hourly else GapAwarePathIndex(bars,asset=asset,schedule=schedule)
            result=replay(m['_index'],m,'P0') if hourly else replay_gap_aware(m['_index'],m,'P0')
            use=m['admitted']&result['valid'];net=result['model']['SYM']['net_R']
            cl=[float(net[use&(m['years']>=lo)&(m['years']<=hi)].sum()) for lo,hi in ((2018,2020),(2021,2023))]
            r['SL_active']=dict(trades=int(use.sum()),cluster_R=cl,net_R=float(net[use].sum()),
                unresolved=int((m['admitted']&~result['valid']).sum()),source_uncertain=int((use&result.get('source_uncertain',result['path_gap'])).sum()),
                target_account_qualified=False)
            r['remaining_gate']='H1_INTRAHOUR_PATH_MISSING' if hourly else 'COMPOSITE_ACCOUNT_REPLAY_REQUIRED'
            del m['_index']
        compressed(asset+'-F5-raw',m);out.append(r)
        event('V23_F5_transfer',asset=asset,raw=r['raw'],dual_positive=r['dual_cluster_positive'],stage0=r['stage0_passed'])
    save('F5-transfer-results.json',dict(rows=out,recipes=3,parameter_search=False))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('h1_diagnosis','transfers'));a=p.parse_args();globals()[a.stage]()
