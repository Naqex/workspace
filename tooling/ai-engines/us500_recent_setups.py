"""Eight frozen closed-bar setup recipes, separate from execution authority."""
from collections import deque,Counter
from decimal import Decimal as D
from fractions import Fraction as F
import us500_opportunities as original
import us500_multiframe as core

CODES=tuple(f'RS{i:02}' for i in range(1,9))
ECONOMIC=('RS01','RS02','RS03','RS07')


def signals(prepared):
    output={k:[] for k in CODES};history=deque(maxlen=20)
    channel=original.triggers(prepared,'FP07')['events']
    output['RS01']=[dict(e,atr=prepared['snapshots'][e['t']]['m15']['atr']) for e in channel]
    reclaim=original.ReclaimPolicy(original.CONFIG)
    for e in prepared['snapshots'].values():reclaim.event(e)
    output['RS06']=[e for e in reclaim.events if e['kind']=='confirm']
    channel_by_t={e['t']:e for e in channel}
    day=None; prior=None;daybars=[];daygood=True;orb=None;broken=None;retest=None;retest_used=False;band_side=None
    def emit(code,e,side,atr=None):
        output[code].append(dict(kind='confirm',t=e['t'],side=side,atr=atr if atr is not None else e['m15']['atr']))
    for e in prepared['snapshots'].values():
        if day!=e['day']:
            if day is not None:
                prior=(dict(high=max(b['high'] for b in daybars),low=min(b['low'] for b in daybars),
                    close=daybars[-1]['close'],atr=daybars[-1]['atr']) if daygood and len(daybars)==26 else None)
            day=e['day'];daybars=[];daygood=True;orb=None;broken=None;retest=None;retest_used=False;band_side=None
        m=e['m15']
        if e['blocked'] or not e['full_session']:daygood=False
        if not m:
            if e['slot']%15==0:history.clear();band_side=None
            continue
        if m['previous'] is None:history.clear();band_side=None
        # All levels below are computed before appending the current closed bar.
        mean=sd=None
        if len(history)==20:
            closes=[b['close'] for b in history];mean=sum(closes,D(0))/20
            sd=(sum(((x-mean)**2 for x in closes),D(0))/20).sqrt()
        if e['slot']==15:orb=dict(high=m['high'],low=m['low'],opening=m['open'])
        if e['full_session'] and not e['blocked'] and m['atr']>0:
            if e['slot'] in range(30,331,15):
                if prior:
                    if F(m['close'])>F(prior['high'])+F('0.1')*F(m['atr']):emit('RS03',e,'BUY')
                    elif F(m['close'])<F(prior['low'])-F('0.1')*F(m['atr']):emit('RS03',e,'SELL')
                if mean is not None and sd and sd>0:
                    now='LOW' if m['close']<mean-2*sd else 'HIGH' if m['close']>mean+2*sd else None
                    if band_side=='LOW' and now is None and m['close']<mean:emit('RS07',e,'BUY')
                    if band_side=='HIGH' and now is None and m['close']>mean:emit('RS07',e,'SELL')
                if retest:
                    sign=1 if retest['side']=='BUY' else -1;level=retest['level'];pad=D('.1')*retest['atr']
                    touch=m['low']<=level+pad if sign==1 else m['high']>=level-pad
                    if e['t']>retest['expiry']:retest=None
                    elif e['t']>retest['t'] and touch and sign*(m['close']-level)>pad:
                        emit('RS02',e,retest['side'],retest['atr']);retest=None
                    elif e['t'] in channel_by_t and channel_by_t[e['t']]['side']!=retest['side']:retest=None
                if not retest_used and e['slot']<=270 and e['t'] in channel_by_t and len(history)==20:
                    side=channel_by_t[e['t']]['side'];retest_used=True
                    retest=dict(side=side,t=e['t'],level=max(b['high'] for b in history) if side=='BUY' else min(b['low'] for b in history),
                        atr=m['atr'],expiry=min(e['t']+60*core.M,e['t']+(330-e['slot'])*core.M))
            if orb and e['slot'] in range(30,91,15):
                side='BUY' if m['close']>orb['high'] else 'SELL' if m['close']<orb['low'] else None
                if side:emit('RS04',e,side)
                if broken and e['t']>broken['t'] and orb['low']<=m['close']<=orb['high']:
                    emit('RS05',e,'SELL' if broken['side']=='BUY' else 'BUY');broken=None
                if broken is None and side:broken=dict(side=side,t=e['t'])
            if e['slot']==15 and prior and prior['atr']>0 and orb:
                gap=orb['opening']-prior['close']
                if abs(gap)>=D('.25')*prior['atr'] and gap*(m['close']-orb['opening'])<0:
                    emit('RS08',e,'SELL' if gap>0 else 'BUY')
        if mean is not None and sd and sd>0:
            band_side='LOW' if m['close']<mean-2*sd else 'HIGH' if m['close']>mean+2*sd else None
        history.append(m);daybars.append(m)
    # Freeze first trigger before any future quote or account admission checks.
    for code,events in output.items():
        seen=set();first=[]
        for ev in events:
            day=prepared['snapshots'][ev['t']]['day']
            if day in seen:continue
            seen.add(day);first.append(ev)
        output[code]=first
    return output


class FrozenPolicy:
    def __init__(self,config,by_time):
        self.code=config['id'];self.by_time=by_time;self.events=[]
    def event(self,e,*,active=None,pending=False):
        if pending:return None
        m=e['m15']
        mean_exit=(self.code=='RS07' and active and m and 20 in m['means'] and
            (1 if active=='BUY' else -1)*(m['close']-m['means'][20])>=0)
        if active:
            if e['slot']==360 or mean_exit:
                d=dict(action='exit',t=e['t'],reason='mean_reached' if mean_exit else 'session_flat')
                self.events.append(dict(kind='exit_decision',**d));return d
            return None
        ev=self.by_time.get(e['t'])
        if ev:
            d=dict(ev,action='entry',level=m['close'])
            self.events.append(dict(d,kind='confirm'));return d
        return None
