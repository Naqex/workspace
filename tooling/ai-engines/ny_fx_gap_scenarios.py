"""Source-bound conditional gap assumptions, never broker/exact-price authority."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal as D
from pathlib import Path
import hashlib,json

MINUTE=60000
HOUR=3600000


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def require(value,label):
    if not value:raise ValueError(label)


@dataclass(frozen=True)
class GapMinute:
    at: int
    bid_low: D
    bid_high: D
    ask_low: D
    ask_high: D

    def __post_init__(self):
        prices=(self.bid_low,self.bid_high,self.ask_low,self.ask_high)
        require(type(self.at) is int and self.at%MINUTE==0 and 0<=self.at<1735689600000,'gap_clock')
        require(all(p.is_finite() and p>0 and p%D('.00001')==0 for p in prices),'gap_grid')
        require(self.bid_low<=self.bid_high and self.ask_low<=self.ask_high,'gap_envelope')


@dataclass(frozen=True)
class GapScenario:
    mode: str
    minutes: tuple[GapMinute,...]

    def __post_init__(self):
        require(self.mode in ('observed_events','adverse_envelope'),'unregistered_gap_scenario')
        require(isinstance(self.minutes,tuple) and all(isinstance(p,GapMinute) for p in self.minutes),'typed_gap_proofs')
        require(len({p.at for p in self.minutes})==len(self.minutes),'duplicate_gap_proof')

    def action(self,at,pair,position,*,intent,scheduled):
        proof=next((p for p in self.minutes if p.at==at),None)
        if proof is None or intent is not None or scheduled:return None
        if pair is not None and any(r is not None for r in pair):return None
        result=dict(action='conditional_no_observed_event',price=None)
        if self.mode=='adverse_envelope':
            extreme=proof.bid_low if position['side']=='BUY' else proof.ask_high
            if (position['side']=='BUY' and extreme<=position['stop']) or (position['side']=='SELL' and extreme>=position['stop']):
                result.update(action='conditional_gap_adverse_envelope',price=extreme)
        return result


def admit_minutes(tick_root,h1_root,pairs,year):
    """Rebind original sources; absence in this archive only supports stated assumptions."""
    tick_root,h1_root=Path(tick_root),Path(h1_root)
    result,review,config=(read(tick_root/n) for n in ('result.json','review.json','config.json'))
    require(digest(tick_root/'result.json')==review['result_sha256'],'tick_review_binding')
    require(result['strategySimulated'] is False and result['executionAuthorized'] is False
            and result['holdoutRead'] is False and result['brokerCalls']==0,'tick_scope')
    require(len(result['hours'])==len(config['requests'])==10 and not review['differences']
            and review['patchable_missing_minutes']==0 and review['unresolved_missing_minutes']==10,'ten_silence_hours')
    hresult,hreview=read(h1_root/'result.json'),read(h1_root/'review.json')
    require(digest(h1_root/'result.json')==hreview['result_sha256'],'H1_review_binding')
    envelopes=[]
    for side in ('bid','ask'):
        path=h1_root/f'{year}-eurusd-{side}.json'
        seal=next(s for s in hresult['books'] if s['id']==f'{year}-eurusd-{side}')
        require(digest(path)==seal['sha256'],'H1_book_seal')
        envelopes.append({r['timestamp']:r for r in read(path)})
    admitted=[];bindings={str(tick_root/n):digest(tick_root/n) for n in ('result.json','review.json','config.json')}
    bindings.update({str(h1_root/n):digest(h1_root/n) for n in ('result.json','review.json')})
    for request,seal,quality in zip(config['requests'],result['hours'],review['hours']):
        require(request['id']==seal['id']==quality['hour'] and request['instrument']=='eurusd','tick_source_identity')
        if not request['id'].startswith(str(year)):continue
        path=tick_root/(seal['id']+'.json');proof_path=tick_root/(seal['id']+'-proof.json')
        require(digest(path)==seal['sha256'] and digest(proof_path)==seal['proofSha256'],'tick_hour_seals')
        proof=read(proof_path);raw=Path(proof['rawPath'])
        require(digest(raw)==proof['sha256']==seal['rawSha256'],'tick_raw_seal')
        bindings.update({str(p):digest(p) for p in (path,proof_path,raw)})
        ticks=read(path);require(len(ticks)==seal['rows'] and ticks,'tick_count')
        hour=ticks[0]['timestamp']//HOUR*HOUR
        require(all(hour<=t['timestamp']<hour+HOUR for t in ticks),'tick_hour_clock')
        require(all(c['exact'] for c in quality['common_M1_checks']),'common_M1_conflict')
        groups=defaultdict(list)
        for t in ticks:groups[t['timestamp']//MINUTE*MINUTE].append(t)
        for at,rows in groups.items():
            pair=pairs.get(at);require(pair is not None and all(r is not None for r in pair),'common_M1_absence')
            for side,key in enumerate(('bidPrice','askPrice')):
                prices=[D(str(r[key])) for r in rows]
                wanted=dict(open=prices[0],high=max(prices),low=min(prices),close=prices[-1])
                require(all(D(str(pair[side][k]))==v for k,v in wanted.items()),'common_M1_prices')
        for at in quality['missing_cash_minutes_without_ticks']:
            require(hour<=at<hour+HOUR and at not in groups,'gap_has_tick')
            pair=pairs.get(at);require(pair is None or all(r is None for r in pair),'gap_has_M1')
            bounds=[r[hour] for r in envelopes]
            for side,key in enumerate(('bidPrice','askPrice')):
                require(D(str(bounds[side]['low']))<=min(D(str(t[key])) for t in ticks)
                    and D(str(bounds[side]['high']))>=max(D(str(t[key])) for t in ticks),'H1_excludes_tick')
            admitted.append(GapMinute(at,*[D(str(bounds[i][k])) for i,k in ((0,'low'),(0,'high'),(1,'low'),(1,'high'))]))
    require(len(admitted)==(4 if year==2019 else 6 if year==2022 else -1),'registered_year_gap_census')
    for side in ('bid','ask'):
        p=h1_root/f'{year}-eurusd-{side}.json';bindings[str(p)]=digest(p)
    return tuple(admitted),bindings
