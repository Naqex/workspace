from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from candle_source_provenance import explicit_candles

class HourlySourceTests(unittest.TestCase):
    def payload(self):
        return dict(timestamp=0,shift=3600000,multiplier=.00001,open=1.1,high=1.1,low=1.1,close=1.1,
            times=[0,2],opens=[0,10],highs=[5,10],lows=[-5,10],closes=[2,10],volumes=[0,3])
    def test_hourly_is_opt_in_and_does_not_invent_missing_or_discard_zero_volume(self):
        payload=self.payload()
        with self.assertRaisesRegex(ValueError,'M1_clock'):explicit_candles(payload)
        rows=explicit_candles(payload,duration_ms=3600000)
        self.assertEqual(list(rows),[0,7200000]);self.assertEqual(rows[0]['volume'],0)
        self.assertEqual(str(rows[7200000]['open']),'1.10010')
    def test_wrong_duration_mixed_clock_or_price_is_rejected(self):
        for value in [1,600000,True]:
            with self.assertRaisesRegex(ValueError,'duration'):explicit_candles(self.payload(),duration_ms=value)
        payload=self.payload();payload['timestamp']=60000
        with self.assertRaisesRegex(ValueError,'clock'):explicit_candles(payload,duration_ms=3600000)
        payload=self.payload();payload['lows'][0]=100
        with self.assertRaisesRegex(ValueError,'bounds'):explicit_candles(payload,duration_ms=3600000)

if __name__=='__main__':unittest.main()
