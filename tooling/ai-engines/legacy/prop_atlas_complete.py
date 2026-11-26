"""Frozen composition release and V2 account lifecycle, no new search."""
from datetime import datetime,timezone
from pathlib import Path
from prop_atlas_core import JOB,V1,PARENT,event,carry_path
from prop_campaign_source import START,END,FINAL,Prices,read,write_json,digest,stamp
from prop_campaign_accounts import annual,replay
from prop_atlas_policy import RiskV2


def freeze():
    atlas=read(JOB/'atlas-stage0.json');core=read(JOB/'core-decision.json')
    if atlas['survivors']:
        raise ValueError('stage1_required_before_freeze:'+','.join(atlas['survivors']))
    # No survivors means no SL backtests, correlation fitting, or artificial
    # portfolio of individually ineligible signals.
    write_json(JOB/'composition-freeze.json',dict(core=core['selected'],sleeves=[],
        stage1_status='NOT_RUN_NO_STAGE0_SURVIVORS',correlation=None,
        utc=datetime.now(timezone.utc).isoformat(),selection_cutoff=END,
        atlas_sha256=digest(JOB/'atlas-stage0.json'),
        core_decision_sha256=digest(JOB/'core-decision.json'),
        source_resolution_sha256=digest(JOB/'resolved-endpoint-review.json'),
        policy_sha256=digest('tooling/ai-engines/prop_atlas_policy.py'),
        protocol_sha256=digest('planning/research/PROP-ATLAS-V2-PROTOCOL-20261114.md'),
        prices2024_used_in_selection=False,prices2025_2026_read=False))
    event('composition_frozen',core=core['selected'],sleeves=[])


def phase3():
    f=read(JOB/'composition-freeze.json')
    if f['selection_cutoff']!=END or f['sleeves']:
        raise ValueError('unhandled_composition_not_silently_ignored')
    if f['policy_sha256']!=digest('tooling/ai-engines/prop_atlas_policy.py'):
        raise ValueError('policy_changed_after_development_freeze')
    write_json(JOB/'validation-release.json',dict(composition_sha256=digest(JOB/'composition-freeze.json'),
        utc=datetime.now(timezone.utc).isoformat(),price_end_exclusive=FINAL,
        no2025_2026=True))
    manifest=read(PARENT/'attempt-2/binary-manifest.json')
    p=Prices(manifest,FINAL)
    for cell in ('SYM_FLAT','ASYM_FLAT'):
        baseline=read(V1/f'frozen-system-{cell}-trades.json')
        if f['core']=='A0':
            trades=baseline
            a=read(V1/f'frozen-system-{cell}-annual.json')
            source='PINNED_IDENTICAL_ALPHA_PR79_ANNUAL_REUSED'
        else:
            dev=read(JOB/f'core-{cell}-dev.json')
            val=[carry_path(t,f['core'],cell,p) for t in baseline if t['day'].startswith('2024')]
            if any(t.get('exit_policy_unknown') for t in val):raise ValueError('validation_carry_path_unknown')
            trades=dev+val;a=annual(trades,p,cell,years=(2022,2023,2024))
            source='FROZEN_CARRY_CORE_VALIDATED_NO_RESELECTION'
        write_json(JOB/f'system-{cell}-trades.json',trades)
        write_json(JOB/f'annual-{cell}.json',dict(rows=a,source=source))
        cases=[RiskV2(stamp(f'{year}-{month:02d}-01'),FINAL,cell,rolling=True)
               for year in (2022,2023,2024) for month in range(1,13)]
        result=replay(trades,p,cases)
        for c in result:
            d=datetime.fromtimestamp(c['start_msc']/1000,timezone.utc)
            c.update(start_year=d.year,start_month=d.month)
        write_json(JOB/f'lifecycle-{cell}.json',result)
        write_json(JOB/f'continuous-{cell}.json',dict(same_as_monthly_start='2022-01-01',
            independent_case=False,result=result[0]))
        event('V2_lifecycle_completed',cell=cell,starts=len(result),
            step1=sum(len(c['phase_passes'])>0 for c in result),
            both=sum(len(c['phase_passes'])==2 for c in result),
            payouts=sum(len(c['payouts']) for c in result),
            worst_static_pct=max(c['static_loss_pct'] for c in result))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('freeze','phase3'))
    a=p.parse_args();globals()[a.stage]()
