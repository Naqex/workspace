"""Five operational Bot Lab scenarios; all prices are synthetic and pre-lock."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import numpy as np

from bot_live_leaderboard import BOTH, REJECTED, SWING, UNKNOWN, audit_batch, write_results
from quant_core.ftmo_track_replay import STOP, Market
from quant_core.live_trade_log import normalize

FIXTURES=Path(__file__).parent/'fixtures'/'bot_live_batch'


def millis(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()*1000)


def fixture_inputs(directory):
    files=sorted(FIXTURES.glob('*.csv'))
    assert len(files)==5
    a,b=millis('2024-02-02T21:00'),millis('2024-02-04T22:00')
    start,end=millis('2024-01-01T00:00'),millis('2027-01-01T00:00')
    calendar={'source':'SYNTHETIC_TEST','valid_from_utc_msc':start,'valid_to_utc_msc':end,
              'breaks_by_symbol':{'EURUSD':[[a,b]],'USDJPY':[]}}
    news={'source':'SYNTHETIC_TEST','valid_from_utc_msc':start,'valid_to_utc_msc':end,
          'restricted_news_by_symbol':{'EURUSD':[],'USDJPY':[]}}
    t=set()
    for file in files:
        trades,_=normalize(file.read_bytes(),'.csv')
        for q in trades:
            if q.close_time<STOP:
                t.update(z for z in range(q.open_time,q.close_time+60000,60000) if not a<=z<b)
    folder=directory/'eurusd'
    folder.mkdir()
    times=sorted(t)
    values=[]
    grid_start=millis('2024-02-16T08:00')
    for at in times:
        minutes=(at-grid_start)//60000
        values.append(110000-25*minutes if 0<=minutes<6 else 109300 if 6<=minutes<=15 else 110000)
    contents={'times':np.asarray(times,dtype='<i8')//1000}
    contents.update({k:np.asarray(values,dtype='<i4')+delta for k,delta in
                     (('o',0),('h',120),('l',-10),('c',0))})
    hashes={}
    for name,value in contents.items():
        path=folder/(name+'.bin')
        raw=value.tobytes()
        path.write_bytes(raw)
        hashes[path.name]=sha256(raw).hexdigest()
    (folder/'manifest.json').write_text(json.dumps({'files':hashes,'rows':len(times),'raw_sha256':'synthetic'}))
    binding=directory/'market.json'
    binding.write_text(json.dumps({'EURUSD':{'path':str(folder),'scale':100000,'bar_seconds':60,
                                             'time_basis':'UTC','scope':'DEVELOPMENT'}}))
    for name,content in (('calendar',calendar),('news',news)):
        (directory/(name+'.json')).write_text(json.dumps(content))
    return files,binding,calendar,news


class RecordingMarket(Market):
    def __init__(self,binding):
        super().__init__(binding)
        self.requests=[]

    def bars(self,symbol,first,end):
        if not first < end <= STOP or symbol != 'EURUSD':
            raise AssertionError('Post-lock local access attempted')
        self.requests.append((symbol,first,end))
        return super().bars(symbol,first,end)


class BatchDryRunTests(unittest.TestCase):
    def test_five_fixtures_have_expected_ranked_status_and_lock(self):
        td=TemporaryDirectory()
        self.addCleanup(td.cleanup)
        directory=Path(td.name)
        files,bindings,calendar,news=fixture_inputs(directory)
        market=RecordingMarket(bindings)
        self.addCleanup(market.close)
        leads,pl=audit_batch(files,market,calendar,news)
        rows={Path(r['file']).stem:r for r in leads}
        self.assertEqual({k:v['status'] for k,v in rows.items()},
            {'clean_swing_and_standard':BOTH,'clean_swing_survivor':SWING,
             'hidden_martingale_trap':REJECTED,'hidden_grid_ftmo_breach':REJECTED,
             'mixed_holdout_date_log':UNKNOWN})
        standard=rows['clean_swing_survivor']['standard']['failed']
        self.assertIn('STANDARD_LONG_MARKET_BREAK',{x['code'] for x in standard})
        self.assertEqual({'HIDDEN_MARTINGALE_LOT_ESCALATION'},
                         {x['code'] for x in rows['hidden_martingale_trap']['confirmed_rejections']})
        self.assertTrue({'HIDDEN_GRID_AVERAGING_DOWN','FTMO_RULE_BREACH_SIM'} <=
                        {x['code'] for x in rows['hidden_grid_ftmo_breach']['confirmed_rejections']})
        mixed=rows['mixed_holdout_date_log']
        self.assertEqual(mixed['path_scope']['bar_path_skipped_holdout_lock'],2)
        self.assertEqual(mixed['bar_path_skipped_rows'],[2,3])
        self.assertEqual(mixed['log_only_after_lock']['exact_clock_trades'],2)
        self.assertEqual(mixed['log_only_after_lock']['session_dna']['open_time']['hour_utc'],{8:2})
        scenarios=mixed['profile_sim']['Swing']
        self.assertTrue(all(x['normalized_trades']==3 and x['net_usd']>0 for x in scenarios))
        self.assertTrue(all(x['status']=='UNKNOWN_INTRADAY_COVERAGE_OR_RISK' for x in scenarios))
        self.assertTrue(market.requests)
        self.assertTrue(all(x[2]<=STOP for x in market.requests))
        self.assertEqual(len(pl),2)
        self.assertTrue(all(x['audited_ftmo_symbol_trade_share']==1 for x in pl))
        self.assertTrue(all(x['winrate']==1 for x in pl))
        out=directory/'result'
        write_results(out,leads,pl)
        self.assertEqual(len(list(out.glob('*'))),4)
        saved=json.loads((out/'FTMO_LIVE_CANDIDATE_LEADERBOARD.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['records'][0]['rank'],1)
        self.assertEqual(saved['order_send_count'],0)

    def test_funded_standard_needs_mapped_news_and_uses_preregistered_window(self):
        td=TemporaryDirectory()
        self.addCleanup(td.cleanup)
        directory=Path(td.name)
        files,binding,cal,news=fixture_inputs(directory)
        file=next(p for p in files if p.stem=='clean_swing_and_standard')
        market=RecordingMarket(binding)
        self.addCleanup(market.close)
        r,_=audit_batch([file],market,cal)
        self.assertEqual(r[0]['status'],SWING)
        self.assertEqual(r[0]['standard']['news']['status'],'UNKNOWN_RESTRICTED_NEWS_COVERAGE')
        news['restricted_news_by_symbol']['EURUSD']=[millis('2024-02-05T13:01')]
        r,_=audit_batch([file],market,cal,news)
        self.assertEqual(r[0]['status'],SWING)
        self.assertEqual(r[0]['standard']['news']['flagged_rows'],[1])
