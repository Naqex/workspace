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
    if manifest.get('prop_profile'):
        prop_path=Path(directory)/(scenario+'-prop-path.json')
        if seal.get('artifact_sha256',{}).get(prop_path.name)!=hashlib.sha256(prop_path.read_bytes()).hexdigest():
            raise ValueError('prop path artifact seal mismatch')
        if json.loads(prop_path.read_bytes()) != dict(**rows[-1].get('prop_path',{}),
                completed_phase_accounts=rows[-1].get('completed_phase_accounts',[])):
            raise ValueError('final prop path differs from terminal horizon')
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
        if manifest.get('prop_profile'):
            # Completed phases have their own cash ledgers. Validate the whole
            # calendar across those ledgers; never charge an archived fee again.
            tail_adjustments=[]
        else:
            state,tail_adjustments=complete_quote_free_financing_tail(state,manifest,scenario,cutoff)
        if tail_adjustments: reconcile(state,Decimal(slip))
        e=state.execution
        initial=e.starting_balance
        if initial<=0: raise ValueError('invalid starting balance denominator')
        entry_days={datetime.fromtimestamp(event['details']['time_msc']/1000,timezone.utc)
            .astimezone(ZoneInfo('Europe/Prague')).date().isoformat()
            for event in e.ledger if event['kind']=='market_fill'}
        prop = inspect_prop_observation(row,manifest,state,cutoff,Decimal(slip),scenario) if manifest.get('prop_profile') else None
        diagnostics=ledger_diagnostics(state)
        if prop:
            path=prop['path']
            if (Decimal(path['maximum_drawdown'])<Decimal(diagnostics['ledger_event_max_drawdown_usd'])
                    or Decimal(path['minimum_equity'])!=state.risk.minimum_observed_equity
                    or prop['qualifying_days']!=len(entry_days)):
                raise ValueError('tick/ledger risk or entry-day observations disagree')
            if path['first_breach'] is None and any(Decimal(path[key])<0 for key in
                    ('minimum_daily_headroom','minimum_overall_headroom')):
                raise ValueError('negative prop headroom without breach evidence')
        output.append(dict(cutoff_utc=datetime.fromtimestamp(cutoff/1000,timezone.utc).isoformat(),
            starting_balance_usd=str(initial),balance_usd=str(e.balance),equity_usd=str(e.equity),
            balance_delta_usd=str(e.balance-initial),equity_delta_usd=str(e.equity-initial),
            floating_pl_usd=str(e.floating_pl),observed_ticks=prop['observed_ticks'] if prop else state.risk.observed_ticks,
            entry_fills=sum(event['kind']=='market_fill' for event in e.ledger),
            closed_trades=sum(event['kind']=='protective_fill' for event in e.ledger),
            entry_days_prague=len(entry_days),open_position=e.position is not None,
            pending_entry=e.pending_market_order is not None,
            minimum_observed_equity_usd=str(state.risk.minimum_observed_equity),
            internal_risk_stops=len(state.risk.stops),internal_overall_halted=state.risk.overall_stopped,
            last_quote_time_msc=state.risk.last_tick.time_msc,
            boundary_quote_age_ms=cutoff-state.risk.last_tick.time_msc,
            internal_risk_is_firm_rule=False,
            full_prop_time_to_pass='declared_subset_only_not_full_firm_rules' if prop else 'not_evaluated',
            strategy_edge='not_established',promotion_authorized=False,
            independent_accounting=accounting['independent_accounting'],
            observation_basis='sealed_raw_plus_declared_quote_free_cash_tail' if tail_adjustments else 'sealed_raw',
            raw_sealed_equity_delta_usd=str(raw_state.execution.equity-raw_state.execution.starting_balance),
            raw_sealed_balance_delta_usd=str(raw_state.execution.balance-raw_state.execution.starting_balance),
            derived_financing_tail=tail_adjustments,
            diagnostics=diagnostics,**({'prop_path':prop,
                'balance_scope':'active_phase_account_not_sum_of_challenge_profits'} if prop else {})))
    return output


def inspect_prop_observation(row,manifest,state,cutoff,slippage,scenario):
    from trading_workspace_v2.prop_session import PhaseStateSnapshot,ChallengeAttemptSnapshot
    from trading_workspace_v2.forex_financing import FinancingTerms
    packet=row.get('prop_path',{})
    if packet.get('profile')!=manifest['prop_profile']:
        raise ValueError('prop observation profile mismatch')
    active=packet['active']
    phase=PhaseStateSnapshot.model_validate(active['phase'])
    attempt=ChallengeAttemptSnapshot.model_validate(active['attempt'])
    accounts=row.get('completed_phase_accounts',[])
    expected=list(range(1,phase.phase_index))
    if ([p['phase_index'] for p in accounts]!=expected
            or [p['phase_index'] for p in packet.get('completed_phases',[])]!=expected
            or phase.profile_hash!=manifest['prop_profile']['profile_hash']
            or attempt.profile_hash!=phase.profile_hash or active['status']!=attempt.status
            or phase.phase_index!=active['phase_index']
            or Decimal(active['account_balance_usd'])!=state.execution.balance
            or Decimal(active['account_equity_usd'])!=state.execution.equity
            or phase.initial_balance!=state.execution.starting_balance
            or int(phase.virtual_time_utc.timestamp()*1000)>=cutoff
            or active['last_observation_time_msc']>=cutoff):
        raise ValueError('prop observation phase/account boundary mismatch')
    count=state.risk.observed_ticks
    ledgers=[state.execution.ledger]
    for account in accounts:
        previous=ForexPilotSnapshot.model_validate(account['checkpoint'])
        if (previous.execution.position is not None or previous.execution.pending_market_order is not None
                or previous.risk.last_tick is None or previous.risk.last_tick.time_msc>=cutoff
                or any(e['virtual_time_utc']*1000>cutoff for e in previous.execution.ledger)):
            raise ValueError('completed prop phase is not flat')
        if reconcile(previous,slippage)!=account['accounting']:
            raise ValueError('completed prop phase accounting mismatch')
        count+=previous.risk.observed_ticks
        ledgers.append(previous.execution.ledger)
    calendar=next(s['financing_calendar'] for s in manifest['scenarios'] if s['name']==scenario)
    expected={t['event_id']:FinancingTerms.model_validate(t) for t in calendar if t['scheduled_time_msc']<cutoff}
    seen=set()
    for ledger in ledgers:
        for event in ledger:
            if event['kind']!='financing': continue
            term=FinancingTerms.model_validate(event['details']['financing_terms'])
            if term.event_id in seen or expected.get(term.event_id)!=term:
                raise ValueError('prop financing calendar differs across phase accounts')
            seen.add(term.event_id)
    if seen!=set(expected):
        raise ValueError('prop evaluation omitted calendar cash; post-hoc repair is not allowed')
    if type(active['observed_ticks']) is not int or active['observed_ticks']!=count:
        raise ValueError('prop tick coverage mismatch')
    path=active['path']
    values=[Decimal(path[k]) for k in ('peak_equity','minimum_equity','maximum_drawdown')]
    if (not all(v.is_finite() for v in values) or values[2]<0
            or values[0]<state.execution.equity or values[1]>state.execution.equity
            or any(event['time_msc']>=cutoff for event in packet.get('milestones',[]))):
        raise ValueError('invalid prop equity path or future milestone')
    return active


def render_report(report):
    """Readable view of verified observations; no independent task state."""
    months=report.get('horizon_months',[3,6,12])
    if months not in ([3,6],[3,6,12]) or any(type(value) is not int for value in months):
        raise ValueError('unsupported report horizons')
    groups={}
    for row in report['rows']:
        key=(row['cutoff_utc'],row['scenario'])
        group=groups.setdefault(row['worker'],{})
        if key in group: raise ValueError('duplicate horizon observation')
        group[key]=row
    prop_mode=bool(report['rows']) and all('prop_path' in row for row in report['rows'])
    lines=['# So sánh chiến lược theo '+'/'.join(map(str,months))+' tháng','',
        'Equity delta USD, gồm lãi/lỗ đang mở. Mỗi ô: phí chuẩn / phí cao.',
        'Đây là historical robustness; các horizon lồng nhau, chưa phải clean OOS hoặc pass quỹ.','',
        'Số đã đối soát gồm phí lịch đã đăng ký trước cutoff nhưng sau quote cuối, nếu còn thiếu.',
        'JSON giữ số raw đã seal và từng điều chỉnh; không sửa artifact gốc hoặc giả có quote mới.','',
        '| Ứng viên | '+' | '.join(f'{count} tháng' for count in months)+' | Screen phí cuối mẫu |',
        '|---|'+'---:|'*len(months)+'---|']
    if prop_mode:
        lines[2]='Equity delta USD của tài khoản vòng hiện tại, gồm lãi/lỗ mở; không cộng lợi nhuận các vòng đã reset. Mỗi ô: phí chuẩn / phí cao.'
        lines[5]='Runner đã post phí trước cutoff; prop observation không chấp nhận sửa bù cash hậu kiểm.'
        lines[8]=lines[8].replace('Screen phí cuối mẫu','Đánh giá')
    expected_dates=sorted({row['cutoff_utc'] for row in report['rows']})
    for worker,group in groups.items():
        dates=sorted({date for date,_ in group})
        if (len(dates)!=len(months) or dates!=expected_dates
                or set(group)!={(date,scenario) for date in dates for scenario in ('reference','cost-stress')}):
            raise ValueError('incomplete horizon/scenario observations')
        cells=[]
        for date in dates:
            amounts=[Decimal(group[date,scenario]['equity_delta_usd']) for scenario in ('reference','cost-stress')]
            if not all(value.is_finite() for value in amounts): raise ValueError('nonfinite horizon equity')
            cells.append(' / '.join(f'{value:+.2f}' for value in amounts))
        annual=[group[dates[-1],scenario] for scenario in ('reference','cost-stress')]
        if prop_mode:
            screen='Quan sát lifecycle theo profile khai báo; chưa qualification'
        elif any(row['observed_ticks']<=0 or row['entry_fills']==0 for row in annual):
            screen='Chưa đủ mẫu giao dịch'
        elif any(Decimal(row['equity_delta_usd'])<=0 for row in annual):
            screen='Không promote: chưa đạt screen phí'
        else:
            screen='Dương cả hai mức phí; chưa đủ để chọn'
        lines.append('| '+' | '.join([worker,*cells,screen])+' |')
    if prop_mode:
        lines.extend(['','## Tick risk và lifecycle khai báo','',
            '| Ứng viên | Cutoff UTC | Phí | Vòng | Trạng thái | Tick maxDD USD | Đệm daily nhỏ nhất USD | Ngày giao dịch |',
            '|---|---|---|---:|---|---:|---:|---:|'])
        for row in report['rows']:
            p=row['prop_path']; path=p['path']
            status={'running':'chưa đạt tại cutoff','phase_passed':'đạt vòng, chưa chuyển vòng',
                    'completed_pass':'đạt profile mô phỏng','failed_breach':'vi phạm profile mô phỏng'}.get(p['status'],p['status'])
            cells=[row['worker'],row['cutoff_utc'],row['scenario'],str(p['phase_index']),status,
                f"{Decimal(path['maximum_drawdown']):.2f}",
                f"{Decimal(path['minimum_daily_headroom']):.2f}" if path['minimum_daily_headroom'] is not None else 'N/A',
                str(p['qualifying_days'])]
            lines.append('| '+' | '.join(cells)+' |')
        lines.extend(['','MaxDD đo pre/post-fill mỗi quote và cash event của vòng hiện tại. Profile evaluation dừng ở terminal event; DD account vẫn được ghi.',
            'Reset/cash dùng quote cuối đã quan sát, không bịa giá nửa đêm. Không có min sample thì không tự coi edge đạt.'])
    if report['rows'] and all('diagnostics' in row for row in report['rows']):
        lines.extend(['', '## Chẩn đoán cuối mẫu của vòng hiện tại' if prop_mode else '## Chẩn đoán cuối mẫu', '',
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
        ('Đã nối lifecycle theo declared profile; OOS, historical broker realism, exceptions/inactivity/payout vẫn chưa chứng minh.' if prop_mode else
         'Còn phải đánh giá độ bền ngoài mẫu, drawdown/tail risk và full phase 1 → reset → phase 2.'),
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
    months=None
    for worker in terminal['workers']:
        folder=Path(worker['result_dir'])
        dossier=inspect(folder,source_root=V2)
        if dossier['source_drift'] or dossier['unavailable_sources']: raise ValueError('run source changed')
        manifest=json.loads((folder/'manifest.json').read_bytes())
        registered_months=json.loads((folder/'study-registration.json').read_bytes())['horizon_months']
        if months is not None and months!=registered_months:
            raise ValueError('workers have different registered horizons')
        months=registered_months
        for scenario in manifest['scenarios']:
            for row in inspect_horizons(folder,manifest,scenario['name']):
                rows.append(dict(worker=worker['worker'],candidate=manifest['candidate'],
                    scenario=scenario['name'],**row))
    report=dict(schema='forex-time-fit-horizon-report-v1',rows=rows,horizon_months=months,
        report_method='sealed_prop_path_lifecycle_v1' if any('prop_path' in row for row in rows) else
            'sealed_observations_with_explicit_quote_free_calendar_tail_v1',
        reporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        study_role='historical_robustness_prior_exposure_unverified',
        horizons_are_independent_trials=False,prop_qualification='not_established',
        broker_calls=0,model_calls=0,promotion_authorized=False)
    markdown=render_report(report)
    with args.output.open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
    with args.output.with_suffix('.md').open('x',encoding='utf-8') as f: f.write(markdown)
    print(json.dumps(dict(rows=len(rows),report=str(args.output),promotion_authorized=False)))

if __name__=='__main__': main()
