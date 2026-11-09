from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import sys,tempfile,unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from multiasset_monthly_input import schedules,record,sparse_ticks
from sealed_m1_review import cash_sessions


class MonthlyInputTests(unittest.TestCase):
    def test_common_clock_dst_and_early_close(self):
        root=Path(__file__).resolve().parents[1]/'fixtures'
        specs=schedules(cash_sessions(json.loads((root/'nyse-2024.json').read_text())))
        for month,role,wanted in [('2024-01','rebalance_observation','2024-01-02 15:00'),
                                  ('2024-06','rebalance_observation','2024-06-03 14:00'),
                                  ('2024-11','signal_close','2024-11-29 18:00')]:
            s=next(s for s in specs if s['month']==month and s['role']==role)
            self.assertEqual(datetime.fromtimestamp(s['target_ms']/1000,timezone.utc).strftime('%Y-%m-%d %H:%M'),wanted)
        with self.assertRaisesRegex(ValueError,'holdout'):schedules({'2025-01-02':[1]})

    def test_quote_before_after_guards_do_not_fill_stale_or_future(self):
        s=dict(month='2024-01',role='signal_close',target_ms=120000)
        q=dict(time_ms=119999,bid='1.1',ask='1.10001')
        valid=record('EURUSD',s,q,basis='observed_tick')
        self.assertEqual(valid['status'],'observed_bid_ask')
        self.assertEqual(valid['known_at_ms'],120000)
        for at in (120000,59000,121000):
            r=record('EURUSD',s,{**q,'time_ms':at},basis='observed_tick')
            self.assertEqual(r['status'],'missing_or_stale');self.assertIsNone(r['bid'])
        s['role']='rebalance_observation'
        self.assertEqual(record('EURUSD',s,{**q,'time_ms':120000},basis='observed_tick')['status'],'observed_bid_ask')

    def test_gold_does_not_invent_ask_or_actual_quote_timestamp(self):
        s=dict(month='2024-01',role='signal_close',target_ms=120000)
        r=record('XAUUSD',s,dict(time_ms=60000,bid='2000.001'),basis='source_M1_bid_only')
        self.assertIsNone(r['ask']);self.assertFalse(r['observed_ask']);self.assertNotIn('quote_time_ms',r)
        self.assertEqual(r['known_at_upper_bound_ms'],120000)
        with self.assertRaisesRegex(ValueError,'side_contract'):
            record('XAUUSD',s,dict(time_ms=60000,bid='2000.001',ask='2000.501'),basis='source_M1_bid_only')

    def test_sparse_reader_selects_last_strict_before_and_first_after_without_price_peek(self):
        lines=['DateTime,Bid,Ask,Volume\n','20240102 14:59:59.000,1.10000,1.10001,0\n',
               '20240102 15:00:00.000,1.20000,1.20001,0\n','20240102 15:00:30.000,1.30000,1.30001,0\n']
        at=int(datetime(2024,1,2,15,tzinfo=timezone.utc).timestamp()*1000)
        specs=[dict(month='2024-01',role='signal_close',target_ms=at),
               dict(month='2024-01',role='rebalance_observation',target_ms=at+1000)]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ticks.csv';p.write_text(''.join(lines),encoding='utf8');sha=hashlib.sha256(p.read_bytes()).hexdigest()
            rows,proof=sparse_ticks(p,sha,specs,first_day='20240101',last_day='20241231',expected_count=3)
            self.assertEqual([r['bid'] for r in rows],['1.10000','1.30000'])
            self.assertEqual(proof['raw_rows'],3)
            with self.assertRaisesRegex(ValueError,'hash_or_census'):
                sparse_ticks(p,'0'*64,specs,first_day='20240101',last_day='20241231',expected_count=3)

    def test_missing_source_remains_unknown_and_no_fill_authority(self):
        s=dict(month='2024-01',role='rebalance_observation',target_ms=120000)
        r=record('US500',s,None,basis='source_M1_bid_ask')
        self.assertEqual(r['status'],'missing_or_stale');self.assertIsNone(r['bid']);self.assertFalse(r['execution_authorized'])
        r=record('XAUUSD',s,dict(time_ms=120000,bid='2000'),basis='source_M1_bid_only')
        self.assertEqual(r['known_at_upper_bound_ms'],180000);self.assertFalse(r['executable_tick_proven'])
        with self.assertRaisesRegex(ValueError,'basis'):record('US500',s,None,basis='invented')


if __name__=='__main__':unittest.main()
