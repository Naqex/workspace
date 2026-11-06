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


def complete_quote_free_financing_tail(state, manifest, scenario, cutoff):
    """Derive unposted cash events after the last ledger mark; never replay prices."""
    from trading_workspace_v2.forex_financing import FinancingTerms, apply_forex_financing
    calendar=next(item for item in manifest['scenarios'] if item['name']==scenario).get('financing_calendar',[])
    applied={event['details']['financing_terms']['event_id'] for event in state.execution.ledger
             if event['kind']=='financing'}
    missing=[FinancingTerms.model_validate(item) for item in calendar
             if item['scheduled_time_msc']<cutoff and item['event_id'] not in applied]
    if not missing: return state, []
    if not state.execution.ledger or state.risk.last_tick is None:
        raise ValueError('no quote anchor for financing tail')
    boundary=state.execution.ledger[-1]['virtual_time_utc']*1000
    if any(terms.scheduled_time_msc<boundary for terms in missing):
        raise ValueError('missing financing inside executed history; tail derivation cannot repair it')
    derived=state.model_copy(deep=True)
    adjustments=[]
    for terms in missing:
        before=derived.execution.balance
        derived=apply_forex_financing(derived,terms)
        adjustments.append(dict(event_id=terms.event_id,scheduled_time_msc=terms.scheduled_time_msc,
                                balance_delta_usd=str(derived.execution.balance-before)))
    return derived, adjustments


def ledger_diagnostics(state):
    """Describe a validated pilot ledger; event-mark drawdown is not tick drawdown."""
    execution = state.execution
    entries, fees, closed, months, closed_ids = {}, {}, [], {}, set()
    peak = execution.starting_balance
    drawdown = Decimal(0)
    peak_time = state.risk.start_time_msc
    underwater_span = 0
    underwater = False
    for event in execution.ledger:
        kind, details = event['kind'], event['details']
        if kind not in {'price_mark', 'market_fill', 'protective_fill', 'financing', 'order_rejected'}:
            raise ValueError('unsupported pilot diagnostic event')
        equity = Decimal(str(event['equity']))
        when = event['virtual_time_utc'] * 1000
        if equity >= peak:
            if underwater: underwater_span = max(underwater_span, when-peak_time)
            peak, peak_time = equity, when
            underwater = False
        else:
            underwater = True
            drawdown = max(drawdown, peak-equity)
            underwater_span = max(underwater_span, when-peak_time)
        if kind == 'market_fill':
            position = details['position_id']
            if position in entries:
                raise ValueError('duplicate diagnostic position entry')
            entries[position] = event
            month = datetime.fromtimestamp(details['time_msc']/1000, timezone.utc).strftime('%Y-%m')
            months[month] = months.get(month, 0)+1
        elif kind == 'financing':
            position = (details.get('open_position') or {}).get('position_id')
            debit = Decimal(str(details['debit_account']))
            if position is None:
                if debit != 0: raise ValueError('nonzero financing without a position')
            else:
                if position not in entries: raise ValueError('financing without a diagnostic entry')
                fees[position] = fees.get(position, Decimal(0))+debit
        elif kind == 'protective_fill':
            position = details['position_id']
            if position not in entries or position in closed_ids:
                raise ValueError('closing fill without a unique diagnostic entry')
            closed_ids.add(position)
            entry = entries[position]
            net = Decimal(str(details['net_pnl']))-fees.get(position, Decimal(0))
            closed.append(dict(position_id=position,
                entry_time_msc=entry['details']['time_msc'], exit_time_msc=details['time_msc'],
                entry_fill_price=entry['details']['fill_price'], exit_fill_price=details['fill_price'],
                initial_stop_loss=(entry['details'].get('open_position') or {}).get('stop_loss'),
                side=details['side'], quantity=details['quantity'], exit_reason=details['reason'],
                modeled_cost_breakdown=details.get('cost_breakdown'),
                net_before_timed_financing_usd=str(details['net_pnl']),
                timed_financing_usd=str(fees.get(position, Decimal(0))), net_usd=str(net),
                research_budget_r=str(net/state.limits.per_trade_loss)))
    open_id = execution.position.position_id if execution.position is not None else None
    if set(entries)-closed_ids != ({open_id} if open_id else set()):
        raise ValueError('diagnostic open/closed positions do not reconcile')
    open_financing = fees.get(open_id, Decimal(0)) if open_id else Decimal(0)
    values = [Decimal(row['net_usd']) for row in closed]
    net_closed = sum(values, Decimal(0))
    if net_closed-open_financing != execution.balance-execution.starting_balance:
        raise ValueError('diagnostic closed net and open financing differ from cash balance')
    wins, losses = [v for v in values if v>0], [v for v in values if v<0]
    profit, loss = sum(wins, Decimal(0)), -sum(losses, Decimal(0))
    average_win = profit/len(wins) if wins else None
    average_loss = loss/len(losses) if losses else None
    streak = longest = 0
    for value in values:
        streak = streak+1 if value<0 else 0
        longest = max(longest, streak)
    ratio = lambda a,b: str(a/b) if b else None
    return dict(closed_trades=len(values), wins=len(wins), losses=len(losses),
        flat_trades=len(values)-len(wins)-len(losses), win_rate_fraction=ratio(Decimal(len(wins)),len(values)),
        net_closed_pl_usd=str(net_closed), open_position_financing_usd=str(open_financing),
        mean_closed_net_usd=ratio(net_closed,len(values)),
        average_win_usd=str(average_win) if average_win is not None else None,
        average_loss_usd=str(average_loss) if average_loss is not None else None,
        realized_average_win_loss_ratio=ratio(average_win,average_loss) if average_win is not None else None,
        profit_factor=ratio(profit,loss), longest_closed_loss_streak=longest,
        top1_share_of_positive_net=ratio(max(wins),profit) if wins else None,
        top3_share_of_positive_net=ratio(sum(sorted(wins,reverse=True)[:3],Decimal(0)),profit),
        entry_fills_by_utc_month=months, research_budget_usd=str(state.limits.per_trade_loss),
        ledger_event_max_drawdown_usd=str(drawdown),
        max_observed_ledger_underwater_span_ms=underwater_span,
        ledger_underwater_at_end=underwater,
        risk_path_coverage='ledger_events_not_all_ticks_not_firm_drawdown',
        profit_concentration_scope='descriptive_not_portfolio_without_top_trades',
        win_rate_denominator='all_closed_positions_including_flat_excluding_open',
        trade_validity_classification='not_independently_audited', trades=closed)


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
        raw_state=state
        state,tail_adjustments=complete_quote_free_financing_tail(state,manifest,scenario,cutoff)
        if tail_adjustments: reconcile(state,Decimal(slip))
        e=state.execution
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
            independent_accounting=accounting['independent_accounting'],
            observation_basis='sealed_raw_plus_declared_quote_free_cash_tail' if tail_adjustments else 'sealed_raw',
            raw_sealed_equity_delta_usd=str(raw_state.execution.equity-raw_state.execution.starting_balance),
            raw_sealed_balance_delta_usd=str(raw_state.execution.balance-raw_state.execution.starting_balance),
            derived_financing_tail=tail_adjustments,
            diagnostics=ledger_diagnostics(state)))
    return output


def render_report(report):
    """Readable view of verified observations; no independent task state."""
    groups={}
    for row in report['rows']:
        key=(row['cutoff_utc'],row['scenario'])
        group=groups.setdefault(row['worker'],{})
        if key in group: raise ValueError('duplicate horizon observation')
        group[key]=row
    lines=['# So sánh chiến lược theo 3/6/12 tháng','',
        'Equity delta USD, gồm lãi/lỗ đang mở. Mỗi ô: phí chuẩn / phí cao.',
        'Đây là historical robustness; các horizon lồng nhau, chưa phải clean OOS hoặc pass quỹ.','',
        'Số đã đối soát gồm phí lịch đã đăng ký trước cutoff nhưng sau quote cuối, nếu còn thiếu.',
        'JSON giữ số raw đã seal và từng điều chỉnh; không sửa artifact gốc hoặc giả có quote mới.','',
        '| Ứng viên | 3 tháng | 6 tháng | 12 tháng | Screen phí cả năm |',
        '|---|---:|---:|---:|---|']
    for worker,group in groups.items():
        dates=sorted({date for date,_ in group})
        if len(dates)!=3 or set(group)!={(date,scenario) for date in dates for scenario in ('reference','cost-stress')}:
            raise ValueError('incomplete horizon/scenario observations')
        cells=[]
        for date in dates:
            amounts=[Decimal(group[date,scenario]['equity_delta_usd']) for scenario in ('reference','cost-stress')]
            if not all(value.is_finite() for value in amounts): raise ValueError('nonfinite horizon equity')
            cells.append(' / '.join(f'{value:+.2f}' for value in amounts))
        annual=[group[dates[-1],scenario] for scenario in ('reference','cost-stress')]
        if any(row['observed_ticks']<=0 or row['entry_fills']==0 for row in annual):
            screen='Chưa đủ mẫu giao dịch'
        elif any(Decimal(row['equity_delta_usd'])<=0 for row in annual):
            screen='Không promote: chưa đạt screen phí'
        else:
            screen='Dương cả hai mức phí; chưa đủ để chọn'
        lines.append('| '+' | '.join([worker,*cells,screen])+' |')
    if report['rows'] and all('diagnostics' in row for row in report['rows']):
        lines.extend(['', '## Chẩn đoán cuối năm', '',
            'Mỗi ô: phí chuẩn / phí cao. Thắng/thua đã gán phí qua đêm cho từng vị thế đóng.', '',
            '| Ứng viên | Lệnh đóng | Win rate | Lời/lỗ trung bình USD | DD tại ledger USD | Chuỗi thua dài nhất |',
            '|---|---:|---:|---:|---:|---:|'])
        for worker,group in groups.items():
            date=max(date for date,_ in group)
            values=[group[date,scenario]['diagnostics'] for scenario in ('reference','cost-stress')]
            cells=[]
            for key in ('closed_trades','win_rate_fraction','mean_closed_net_usd',
                        'ledger_event_max_drawdown_usd','longest_closed_loss_streak'):
                def display(value):
                    if value is None: return 'N/A'
                    if key=='win_rate_fraction': return f'{Decimal(value)*100:.1f}%'
                    return f'{Decimal(value):.2f}' if key.endswith('_usd') else str(value)
                cells.append(' / '.join(display(value[key]) for value in values))
            lines.append('| '+' | '.join([worker,*cells])+' |')
        lines.extend(['', 'DD ở đây chỉ đo tại các event trong ledger, có thể bỏ lỡ đáy giữa các tick;',
            'chưa là max drawdown đầy đủ hoặc chứng nhận luật quỹ. Win rate không là tiêu chí thắng cuộc.',
            'R trong JSON là PnL chia ngân sách risk, không đồng nhất planned TP/SL hoặc actual stop-risk.'])
    lines.extend(['',
        'Screen chỉ áp dụng phiên bản/cost/window đang thử; không kết luận cả họ chiến lược vô dụng.',
        'Không tăng lot, sửa tham số hoặc gọi các horizon là mẫu độc lập để cải thiện kết quả.',
        'Còn phải đánh giá độ bền ngoài mẫu, drawdown/tail risk và full phase 1 → reset → phase 2.',
        'Nến/quotes theo UTC; phanh ngày nội bộ reset Europe/Prague. Ngân sách nội bộ chưa là luật quỹ đầy đủ.',
        'Phí lịch sử và coverage còn giới hạn; chưa có quyền tự promote/gửi lệnh.',''])
    return '\n'.join(lines)


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
        report_method='sealed_observations_with_explicit_quote_free_calendar_tail_v1',
        reporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        study_role='historical_robustness_prior_exposure_unverified',
        horizons_are_independent_trials=False,prop_qualification='not_established',
        broker_calls=0,model_calls=0,promotion_authorized=False)
    markdown=render_report(report)
    with args.output.open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
    with args.output.with_suffix('.md').open('x',encoding='utf-8') as f: f.write(markdown)
    print(json.dumps(dict(rows=len(rows),report=str(args.output),promotion_authorized=False)))

if __name__=='__main__': main()
