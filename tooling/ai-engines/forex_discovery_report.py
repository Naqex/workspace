"""Reconcile a completed development batch with its non-portfolio signal screen."""
import argparse
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json
from pathlib import Path

from strategy_evidence import inspect
from forex_time_fit import ledger_diagnostics,V2
from forex_h4_pilot import reconcile
from forex_signal_screen import SCREEN_SOURCE_FILES
from trading_workspace_v2.forex_pilot_risk import ForexPilotSnapshot


def build_report(batch,screen_path):
    read=lambda path:json.loads(Path(path).read_bytes())
    terminal=read(batch/'batch-terminal.json');screen=read(screen_path)
    if terminal['status']!='completed_verified':raise ValueError('batch not verified')
    if screen.get('schema')!='forex-h4-flat-feasibility-screen-v1' or screen.get('portfolio_simulated') is not False:
        raise ValueError('unsupported feasibility screen')
    if set(screen.get('source_files',{}))!=set(SCREEN_SOURCE_FILES):
        raise ValueError('screen source pins missing or unsupported')
    rows=[];groups={}
    for worker in terminal['workers']:
        folder=Path(worker['result_dir']);manifest=read(folder/'manifest.json')
        dossier=inspect(folder,source_root=V2)
        if dossier['source_drift'] or dossier['unavailable_sources'] or not dossier['protocol_content_verified']:
            raise ValueError('source/protocol drift')
        if manifest.get('prop_profile'):
            raise ValueError('discovery report does not aggregate phase-reset accounts')
        if (manifest['inputs']!=screen['inputs'] or manifest['research_protocol']['sha256']!=screen['protocol_sha256']):
            raise ValueError('screen/batch input or protocol differs')
        matching=[row for row in screen['rows'] if row['candidate']==manifest['candidate']]
        if len(matching)!=1:raise ValueError('missing or duplicate candidate probe')
        probe=matching[0]
        for name,digest in screen['source_files'].items():
            if hashlib.sha256((V2/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('screen source drift')
        for scenario in manifest['scenarios']:
            name=scenario['name'];state=ForexPilotSnapshot.model_validate(read(folder/(name+'-checkpoint.json')))
            accounting=reconcile(state,Decimal(scenario['slippage']))
            diagnostic=ledger_diagnostics(state);e=state.execution
            row=dict(worker=worker['worker'],candidate=manifest['candidate'],scenario=name,
                starting_balance_usd=str(e.starting_balance),net_equity_usd=str(e.equity-e.starting_balance),
                balance_delta_usd=str(e.balance-e.starting_balance),floating_usd=str(e.floating_pl),
                closed_trades=diagnostic['closed_trades'],entries=sum(x['kind']=='market_fill' for x in e.ledger),
                accounting=accounting,diagnostics=diagnostic,
                open_position=e.position is not None,pending_entry=e.pending_market_order is not None,
                screen_reason=probe['reason'],flat_entry_opportunities=probe['flat_entry_opportunities'],
                source_revision=manifest['source_revision'],source_drift=False,firm_qualification='not_evaluated')
            rows.append(row);groups.setdefault(worker['worker'],[]).append(row)
    decisions={}
    for worker,values in groups.items():
        if len(values)!=2 or {v['scenario'] for v in values}!={'reference','cost-stress'}:
            raise ValueError('incomplete cost scenarios')
        decisions[worker]=('inconclusive_insufficient_fills' if any(v['entries']==0 for v in values) else
            'no_promotion_cost_screen' if any(Decimal(v['net_equity_usd'])<=0 for v in values) else
            'inconclusive_eligible_for_further_review')
    return dict(schema='forex-discovery-report-v1',created_at_utc=datetime.now(timezone.utc).isoformat(),rows=rows,
        decisions=decisions,screen_sha256=hashlib.sha256(screen_path.read_bytes()).hexdigest(),
        batch_terminal_sha256=hashlib.sha256((batch/'batch-terminal.json').read_bytes()).hexdigest(),
        screen_is_portfolio=False,source_files_pinned=True,clean_oos=False,
        broker_calls=0,model_calls=0,promotion_authorized=False)


def render(report):
    lines=['# Discovery: kết quả development sau đối soát','',
        'USD mô phỏng; gồm floating, không ép đóng cuối mẫu. Phí chuẩn/cao là hai kịch bản khai báo.',
        'Flat probes không là lệnh thực, lợi nhuận hoặc pass quỹ; ledger DD không là full tick drawdown.','',
        '| Bản | Phí | Net equity USD | Lệnh đóng | Floating USD | DD ledger USD | Quyết định |',
        '|---|---|---:|---:|---:|---:|---|']
    for row in report['rows']:
        lines.append('| '+' | '.join([row['worker'],row['scenario'],row['net_equity_usd'],str(row['closed_trades']),
            row['floating_usd'],row['diagnostics']['ledger_event_max_drawdown_usd'],report['decisions'][row['worker']]])+' |')
    lines.extend(['','Dữ liệu selection đã dùng, không OOS/edge/prop qualification hoặc broker authority.',
        'Giữ cả bản không đạt; không tăng lot, sửa tham số hoặc bỏ phí để đổi verdict.',''])
    return '\n'.join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--screen',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists() or args.output.with_suffix('.md').exists():raise ValueError('report output already exists')
    report=build_report(args.batch,args.screen)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    with args.output.with_suffix('.md').open('x',encoding='utf-8') as stream:stream.write(render(report))
    print(json.dumps(dict(rows=len(report['rows']),decisions=report['decisions'],promotion_authorized=False)))


if __name__=='__main__':main()
