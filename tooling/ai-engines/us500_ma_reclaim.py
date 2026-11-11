"""One registered M15 trend-pullback hypothesis; native execution stays shared."""
from collections import Counter
from decimal import Decimal as D
from fractions import Fraction as F

import us500_multiframe as parent
from us500_frequency_audit import classify, PROBES
import review_us500_multiframe as accounting

CONFIG=dict(id='R123',lane='A',fast=20,slow=80,k='0.1',version='us500-ma-reclaim-v1',exit_slot=360)


class ReclaimPolicy:
    def __init__(self,config):
        if any(config.get(k)!=v for k,v in CONFIG.items() if k!='id'):
            raise ValueError('registered_reclaim_config_only')
        self.config=config
        self.day=None
        self.attempted=False
        self.arm=None
        self.events=[]

    def event(self,e,*,active=None,pending=False):
        if self.day!=e['day']:
            self.day,self.attempted,self.arm=e['day'],False,None
        m=e['m15']
        if active:
            if not pending and (e['slot']==360 or (m and parent.direction(m,20,80)!=active)):
                return dict(action='exit',t=e['t'],reason='session_flat' if e['slot']==360 else 'trend_lost')
            return None
        if pending:
            return None
        if e['blocked']:
            if self.arm:
                self.events.append(dict(kind='cancel_gap',t=e['t'],arm_time=self.arm['t']))
            self.arm=None
            return None
        if self.arm:
            arm=self.arm
            if m and parent.direction(m,20,80)!=arm['side']:
                self.events.append(dict(kind='cancel_trend',t=e['t'],arm_time=arm['t']))
                self.arm=None
                return None
            sign=1 if arm['side']=='BUY' else -1
            if m and arm['t']<e['t']<=arm['expiry']:
                threshold=F(m['means'][20])+sign*F('0.1')*F(arm['atr'])
                if sign*(F(m['close'])-threshold)>0:
                    self.arm=None
                    decision=dict(action='entry',t=e['t'],side=arm['side'],atr=arm['atr'],level=arm['level'],
                        arm_time=arm['t'],expiry=arm['expiry'],threshold=str(threshold),
                        confirmation_ma=m['means'][20],confirmation='closed_fast_MA_reclaim')
                    self.events.append(dict(kind='confirm',**decision))
                    return decision
            if e['t']>=arm['expiry']:
                self.events.append(dict(kind='expire',t=e['t'],arm_time=arm['t']))
                self.arm=None
            return None
        if e['slot'] not in range(30,271,15):
            return None
        side=classify(e,PROBES[2],attempted=self.attempted)
        if side not in ('BUY','SELL'):
            return None
        self.attempted=True
        self.arm=dict(t=e['t'],side=side,atr=m['atr'],level=m['means'][20],
                      expiry=min(e['t']+60*parent.M,e['t']+(330-e['slot'])*parent.M))
        self.events.append(dict(kind='arm',**self.arm))
        return None


def frequency(prepared,pairs):
    policy=ReclaimPolicy(CONFIG)
    for e in prepared['snapshots'].values():
        policy.event(e)
    counts=Counter(e['kind'] for e in policy.events)
    confirms=[e for e in policy.events if e['kind']=='confirm']
    available=sum(e['t'] in pairs and e['t']+parent.M in pairs for e in confirms)
    if counts['arm']!=sum(counts[x] for x in ('confirm','expire','cancel_gap','cancel_trend')):
        raise ValueError('reclaim_frequency_terminal_census')
    return dict(config=CONFIG,events=policy.events,counts=dict(counts),exact_fill_available=available,
                exact_fill_unavailable=len(confirms)-available,scope='signals_not_native_trades_or_edge')


def review(result,prepared,pairs):
    """Separate closed-bar conditions/first confirmation and exit clock checks."""
    checked=accounting.inspect(result,pairs)
    arms={}
    seen_days=set()
    confirms={}
    for ev in result['policy_events']:
        if ev['kind']=='arm':
            e=prepared['snapshots'][ev['t']]
            m=e['m15']
            prev=m['previous'] if m else None
            sign=1 if ev['side']=='BUY' else -1
            if (e['day'] in seen_days or not e['full_session'] or e['blocked'] or e['slot'] not in range(30,271,15)
                or not prev or prev['day']!=e['day'] or 80 not in prev['means'] or 80 not in m['means']):
                raise ValueError('review_reclaim_arm_clock_readiness')
            if (sign*(m['means'][20]-m['means'][80])<=0 or sign*(prev['means'][20]-prev['means'][80])<=0
                or sign*(prev['close']-prev['means'][20])<=0 or sign*(m['close']-m['means'][20])>0
                or D(str(ev['atr']))!=m['atr'] or D(str(ev['level']))!=m['means'][20]):
                raise ValueError('review_reclaim_arm_conditions')
            if ev['expiry']!=min(ev['t']+60*parent.M,ev['t']+(330-e['slot'])*parent.M):
                raise ValueError('review_reclaim_expiry')
            seen_days.add(e['day'])
            arms[ev['t']]=ev
        elif ev['kind']=='confirm':
            arm=arms.get(ev['arm_time'])
            if not arm or ev['t']<=arm['t'] or ev['t']>arm['expiry'] or arm['side']!=ev['side']:
                raise ValueError('review_reclaim_confirm_clock')
            sign=1 if arm['side']=='BUY' else -1
            first=None
            for t,e in prepared['snapshots'].items():
                if t<=arm['t']:continue
                if t>ev['t']:break
                if e['blocked']:
                    raise ValueError('review_reclaim_confirm_after_gap')
                m=e['m15']
                if not m:continue
                if sign*(m['means'][20]-m['means'][80])<=0:
                    raise ValueError('review_reclaim_confirm_after_trend_loss')
                threshold=F(m['means'][20])+sign*F('0.1')*F(str(arm['atr']))
                if sign*(F(m['close'])-threshold)>0:
                    first=(t,threshold,m['means'][20])
                    break
            if first!=(ev['t'],F(ev['threshold']),D(str(ev['confirmation_ma']))):
                raise ValueError('review_reclaim_first_confirmation')
            confirms[ev['t']]=ev
    for trade in result['trades']:
        decision=trade['decision']
        if decision['t'] not in confirms or decision['side']!=confirms[decision['t']]['side']:
            raise ValueError('review_reclaim_trade_signal_binding')
        sign=1 if trade['side']=='BUY' else -1
        scheduled=None
        for t,e in prepared['snapshots'].items():
            if t<=trade['entry_time']:continue
            m=e['m15']
            if t-parent.M not in pairs:
                continue
            lost=m and (20 not in m['means'] or 80 not in m['means'] or sign*(m['means'][20]-m['means'][80])<=0)
            if e['slot']==360 or lost:
                scheduled=(t+parent.M,'session_flat' if e['slot']==360 else 'trend_lost')
                break
        if scheduled is None:
            raise ValueError('review_reclaim_missing_scheduled_exit')
        exit_ns=trade['exit_ns']
        expected_ns=scheduled[0]*1000000+1
        if trade['reason']=='stop':
            if exit_ns>expected_ns and scheduled[0] in pairs:
                raise ValueError('review_reclaim_stop_after_missed_exit')
        elif (exit_ns,trade['reason'])!=(expected_ns,scheduled[1]):
            raise ValueError('review_reclaim_scheduled_exit_clock')
    return dict(checked,signal_review='closed_bar_arm_first_confirm_exit_clock_checked',
                arms=len(arms),confirms=len(confirms),independent_human_review=False)
