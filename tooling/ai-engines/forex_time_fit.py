"""Read sealed causal horizon snapshots; do not infer a two-phase prop pass."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

V2=Path(__file__).resolve().parents[2]/'projects/trader/foundation_v2'
sys.path[:0]=[str(V2),str(V2/'scripts')]
from forex_h4_pilot import reconcile, scenario_binding
from trading_workspace_v2.forex_pilot_risk import ForexPilotSnapshot


def inspect_horizons(directory, manifest, scenario):
    """Verify seals and independently reconcile each saved account state."""
    path=Path(directory)/(scenario+'-horizons.json')
    seal=json.loads((Path(directory)/(scenario+'-completed.json')).read_bytes())
    if (seal.get('binding_sha256')!=scenario_binding(manifest)
            or seal.get('run_id')!=manifest['run_id']
            or seal.get('scenario')!=scenario
            or seal.get('artifact_sha256',{}).get(path.name)!=hashlib.sha256(path.read_bytes()).hexdigest()):
        raise ValueError('horizon artifact seal mismatch')
    rows=json.loads(path.read_bytes())
    expected=manifest['horizon_cutoffs']
    if not isinstance(rows,list) or [r['cutoff_msc'] for r in rows]!=expected:
        raise ValueError('horizon snapshots differ from declared cutoffs')
    slip=next(s['slippage'] for s in manifest['scenarios'] if s['name']==scenario)
    output=[]
    for row in rows:
        state=ForexPilotSnapshot.model_validate(row['checkpoint'])
        e=state.execution; cutoff=row['cutoff_msc']
        if (state.risk.last_tick is None or state.risk.last_tick.time_msc>=cutoff
                or state.risk.last_tick.model_dump(mode='json')!=row['last_observed_tick']
                or row.get('qualification')!='historical_snapshot_not_full_prop_lifecycle'
                or row.get('promotion_authorized') is not False):
            raise ValueError('horizon snapshot scope or quote boundary invalid')
        for event in e.ledger:
            if (event['virtual_time_utc']*1000>cutoff
                    or event.get('details',{}).get('time_msc',0)>=cutoff):
                raise ValueError('future event inside horizon snapshot')
        if any(d['time_msc']>cutoff for d in row['decisions']):
            raise ValueError('future decision inside horizon snapshot')
        accounting=reconcile(state,Decimal(slip))
        if row['accounting']!=accounting:
            raise ValueError('horizon accounting differs from recalculation')
        initial=e.starting_balance
        if initial<=0: raise ValueError('invalid starting balance denominator')
        entry_days={datetime.fromtimestamp(event['details']['time_msc']/1000,timezone.utc)
            .astimezone(ZoneInfo('Europe/Prague')).date().isoformat()
            for event in e.ledger if event['kind']=='market_fill'}
        output.append(dict(cutoff_utc=datetime.fromtimestamp(cutoff/1000,timezone.utc).isoformat(),
            starting_balance_usd=str(initial),balance_usd=str(e.balance),equity_usd=str(e.equity),
            balance_delta_usd=str(e.balance-initial),equity_delta_usd=str(e.equity-initial),
            floating_pl_usd=str(e.floating_pl),observed_ticks=state.risk.observed_ticks,
            entry_fills=sum(event['kind']=='market_fill' for event in e.ledger),
            closed_trades=sum(event['kind']=='protective_fill' for event in e.ledger),
            entry_days_prague=len(entry_days),open_position=e.position is not None,
            pending_entry=e.pending_market_order is not None,
            minimum_observed_equity_usd=str(state.risk.minimum_observed_equity),
            internal_risk_stops=len(state.risk.stops),internal_overall_halted=state.risk.overall_stopped,
            last_quote_time_msc=state.risk.last_tick.time_msc,
            boundary_quote_age_ms=cutoff-state.risk.last_tick.time_msc,
            internal_risk_is_firm_rule=False,full_prop_time_to_pass='not_evaluated',
            strategy_edge='not_established',promotion_authorized=False,
            independent_accounting=accounting['independent_accounting']))
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    terminal=json.loads((args.batch/'batch-terminal.json').read_bytes())
    if terminal['status']!='completed_verified': raise ValueError('batch not complete')
    # Full dossier validation stays at its existing owner.
    from strategy_evidence import inspect
    rows=[]
    for worker in terminal['workers']:
        folder=Path(worker['result_dir'])
        dossier=inspect(folder,source_root=V2)
        if dossier['source_drift'] or dossier['unavailable_sources']: raise ValueError('run source changed')
        manifest=json.loads((folder/'manifest.json').read_bytes())
        for scenario in manifest['scenarios']:
            for row in inspect_horizons(folder,manifest,scenario['name']):
                rows.append(dict(worker=worker['worker'],candidate=manifest['candidate'],
                    scenario=scenario['name'],**row))
    report=dict(schema='forex-time-fit-horizon-report-v1',rows=rows,
        study_role='historical_robustness_prior_exposure_unverified',
        horizons_are_independent_trials=False,prop_qualification='not_established',
        broker_calls=0,model_calls=0,promotion_authorized=False)
    with args.output.open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
    print(json.dumps(dict(rows=len(rows),report=str(args.output),promotion_authorized=False)))

if __name__=='__main__': main()
