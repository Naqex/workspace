"""R056 finite coarse research wrapper; native risk/prop qualification is separate."""
from datetime import datetime, timezone
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from copy import deepcopy

from trading_workspace_v2.forex_h4 import size_for_stop
from trading_workspace_v2.forex_pilot_risk import _stop_at_fill
from trading_workspace_v2.execution_semantics import protective_exit_for_bar
from trading_workspace_v2.semantics.data_costs import calculate_round_trip_cost

CANDIDATE='eurusd-pre-ecb-session-rms20x2-r025-r056-v1'
HOUR=3600000


def plans(events):
    """Current event prices/status are deliberately never consulted for entry eligibility."""
    result=[]
    for index,event in enumerate(events):
        target=event['entry_target_ms'];decision=target-1
        row=dict(day=event['day'],decision_ms=decision,entry_target_ms=target,exit_target_ms=event['exit_target_ms'],
                 status='unavailable_history',distance=None,history=[])
        prior=events[max(0,index-20):index]
        if len(prior)==20:
            changes=[]
            for point in prior:
                entry,exit_at=point['entry'],point['exit']
                if (entry is None or exit_at is None
                        or not 0<=entry['time_msc']-point['entry_target_ms']<=60000
                        or not 0<=exit_at['time_msc']-point['exit_target_ms']<=60000):
                    break
                if not entry['time_msc']<exit_at['time_msc']<decision:raise ValueError('future_history_or_source_order')
                a=(D(entry['bid'])+D(entry['ask']))/2;b=(D(exit_at['bid'])+D(exit_at['ask']))/2
                changes.append(b-a);row['history'].append(dict(day=point['day'],entry_mid=str(a),exit_mid=str(b),
                    known_at_ms=exit_at['time_msc'],entry_target_ms=point['entry_target_ms'],exit_target_ms=point['exit_target_ms']))
            if len(changes)==20:
                distance=2*(sum((x*x for x in changes),D(0))/20).sqrt()
                if distance.is_finite() and distance>0:row.update(status='ready',distance=str(distance))
        result.append(row)
    return result


class SessionBook:
    def __init__(self,plan,scenario,funding_terms):
        if scenario not in ('reference','stress'):raise ValueError('unknown_scenario')
        self.scenario=scenario;self.slip=D(0) if scenario=='reference' else D('.00002')
        self.model=dict(version='r056-declared-'+scenario,spread_basis='bid_ask_embedded',
            commission_per_side_account='0',commission_per_side_per_quantity_account='2.5',minimum_fee_account='0',
            slippage_price_per_side=str(self.slip),financing_account='0',quote_to_account_rate='1',account_ccy='USD',rounding_decimals=2)
        self.plan=plan;self.cursor=0;self.balance=D(10000);self.position=None;self.trades=[];self.decisions=[];self.funding=[]
        self.calendar=iter(funding_terms);self.upcoming=next(self.calendar,None)
        self.day=None;self.anchor=D(10000);self.daily_halt=False;self.overall_halt=False;self.first_cash_breach=None
        self.previous=None;self.last=None;self.minimum_bound=D(10000);self.peak=D(10000);self.endpoint_dd=D(0)
        self.bound_daily_flags=[];self.bound_overall_flags=[];self.year_rows=[];self.year_start=D(10000)

    def _day(self,at):
        day=datetime.fromtimestamp(at/1000,timezone.utc).astimezone(ZoneInfo('Europe/Prague')).date().isoformat()
        if day!=self.day:self.day=day;self.anchor=self.balance;self.daily_halt=False

    def _cash(self,amount,at):
        self._day(at);self.balance+=amount
        if self.balance<=self.anchor-100:self.daily_halt=True
        if self.balance<=9500:
            self.overall_halt=True
            if self.first_cash_breach is None:self.first_cash_breach=dict(time_ms=at,balance=str(self.balance))

    def _costs(self,bid,ask):
        p=self.position
        return calculate_round_trip_cost(self.model,'SELL',D(p['quantity']),D(100000),D(p['entry_bid']),D(p['entry_ask']),bid,ask)

    def _net(self,bid,ask):return D(str(self._costs(bid,ask)['net_account'])) if self.position else D(0)

    def _close(self,price,reason,hour,at_open):
        p=self.position;costs=self._costs(price,price);value=D(str(costs['net_account']))
        interval=[hour.first_time_msc,hour.first_time_msc] if at_open else [hour.first_time_msc,hour.last_time_msc]
        at=interval[-1];self._cash(value,at)
        self.trades.append(dict(**p,exit_time_ms=hour.first_time_msc if at_open else None,exit_interval_ms=interval,
            exit_fill=str(price),reason=reason,costs=costs,price_net=str(value),net=str(value-D(p['funding'])),
            exit_basis='observed_first_Ask' if at_open else 'modeled_H1_stop_level_not_first_crossing',
            scheduled_exit_delay_ms=max(0,hour.first_time_msc-p['exit_target_ms']) if reason=='scheduled_exit' else None))
        self.position=None

    def apply(self,hour):
        at=hour.mid.timestamp*1000;first=hour.first_time_msc
        if self.previous is not None and at<=self.previous:raise ValueError('hours_not_increasing')
        while self.upcoming is not None and self.upcoming.scheduled_time_msc<=first:
            terms=self.upcoming
            if self.position:
                from decimal import ROUND_HALF_UP
                debit=(terms.debit_sell_usd_per_lot*D(self.position['quantity'])*terms.multiplier).quantize(D('.01'),rounding=ROUND_HALF_UP)
                self._cash(-debit,terms.scheduled_time_msc);self.position['funding']=str(D(self.position['funding'])+debit)
                self.funding.append(dict(time_ms=terms.scheduled_time_msc,position_id=self.position['id'],debit=str(debit),multiplier=terms.multiplier))
            self.upcoming=next(self.calendar,None)
        self._day(first)
        if self.position:
            if self.previous is not None and at-self.previous>HOUR:self.position['missing_hour_intervals'].append([self.previous+HOUR,at])
            opening=dict(open=hour.ask[0],high=hour.ask[0],low=hour.ask[0],close=hour.ask[0])
            hit=protective_exit_for_bar(side='SELL',bar=opening,stop_loss=D(self.position['stop']),take_profit=None,spread_price=0,tick_size=D('.00001'),allow_open_gap=True)
            if hit:self._close(hit['exit_price'],'stop_gap',hour,True)
            elif first>=self.position['exit_target_ms']:self._close(hour.ask[0],'scheduled_exit',hour,True)
        while self.cursor<len(self.plan) and self.plan[self.cursor]['entry_target_ms']<=at:
            plan=self.plan[self.cursor];self.cursor+=1
            decision={k:v for k,v in plan.items() if k!='history'}
            if plan['status']!='ready':reason='unavailable_history'
            elif self.overall_halt:reason='cash_overall_halt'
            elif self.daily_halt:reason='daily_cash_halt'
            elif self.position:reason='position_still_open'
            elif not 0<=first-plan['entry_target_ms']<=60000:reason='missing_or_late_entry'
            else:
                distance=D(plan['distance']);quantity=size_for_stop(distance,slippage=self.slip,budget=D(25))
                stop=_stop_at_fill('SELL',hour.bid[0],distance,D('.00001'))
                if quantity is None:reason='minimum_lot'
                elif quantity>50:raise ValueError('quantity_over50')
                elif hour.bid[0]*quantity*100000/30>10000:reason='margin_fixed_start'
                else:
                    planned=(stop-hour.bid[0]+2*self.slip)*quantity*100000+5*quantity
                    if planned>25:raise ValueError('planned_risk_over25')
                    reason='opened'
                    self.position=dict(id=f'{self.scenario}-{len(self.decisions)+1}',day=plan['day'],entry_time_ms=first,
                        entry_sequence=hour.first_sequence,entry_bid=str(hour.bid[0]),entry_ask=str(hour.ask[0]),quantity=str(quantity),
                        distance=str(distance),stop=str(stop),planned_risk=str(planned),exit_target_ms=plan['exit_target_ms'],
                        funding='0',missing_hour_intervals=[],decision_ms=plan['decision_ms'])
                    decision.update(quantity=str(quantity),stop=str(stop),planned_risk=str(planned))
            decision['outcome']=reason;self.decisions.append(decision)
        if self.position:
            # The high may happen after a modeled stop: a diagnostic bound, not actual equity at that time.
            bound=self.balance+self._net(hour.bid[1],hour.ask[1]);self.minimum_bound=min(self.minimum_bound,bound)
            if bound<=self.anchor-100:self.bound_daily_flags.append(dict(hour_ms=at,equity_bound=str(bound)))
            if bound<=9500:self.bound_overall_flags.append(dict(hour_ms=at,equity_bound=str(bound)))
            hit=protective_exit_for_bar(side='SELL',bar=dict(zip(('open','high','low','close'),hour.ask)),
                stop_loss=D(self.position['stop']),take_profit=None,spread_price=0,tick_size=D('.00001'),allow_open_gap=True)
            if hit:self._close(hit['exit_price'],'stop_loss',hour,hit['at_open'])
        equity=self.balance+self._net(hour.bid[3],hour.ask[3]);self.peak=max(self.peak,equity)
        self.endpoint_dd=max(self.endpoint_dd,(self.peak-equity)/self.peak)
        self.previous=at;self.last=hour

    def seal_year(self,year):
        equity=self.balance+self._net(self.last.bid[3],self.last.ask[3])
        self.year_rows.append(dict(year=year,starting_equity=str(self.year_start),ending_equity=str(equity),net=str(equity-self.year_start),
            balance=str(self.balance),floating=str(equity-self.balance),open_position=deepcopy(self.position)))
        self.year_start=equity

    def result(self):
        if self.cursor<len(self.plan):
            # A future target with no observed hour is not silently admitted as a trade.
            for p in self.plan[self.cursor:]:self.decisions.append(dict(day=p['day'],entry_target_ms=p['entry_target_ms'],outcome='no_observed_entry_before_eof'))
        floating=self._net(self.last.bid[3],self.last.ask[3]);equity=self.balance+floating
        finance=sum((D(f['debit']) for f in self.funding),D(0));realized=sum((D(t['price_net']) for t in self.trades),D(0))
        if self.balance!=10000+realized-finance:raise ValueError('cash_accounting')
        return dict(candidate=CANDIDATE,scenario=self.scenario,status='completed_coarse_research_not_native_account',
            starting_balance='10000',balance=str(self.balance),floating=str(floating),ending_equity=str(equity),net=str(equity-10000),
            funding=str(finance),trades=self.trades,decisions=self.decisions,funding_events=self.funding,years=self.year_rows,
            open_position=self.position,first_cash_breach=self.first_cash_breach,cash_overall_halted=self.overall_halt,
            minimum_H1_conservative_equity_bound=str(self.minimum_bound),daily_bound_flags=self.bound_daily_flags,
            overall_bound_flags=self.bound_overall_flags,hour_endpoint_drawdown_fraction=str(self.endpoint_dd),
            last_mark_time_ms=self.last.last_time_msc,prop_evaluated=False,clean_oos=False,challenge_qualified=False,execution_authorized=False)
