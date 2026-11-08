import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from candle_source_provenance import explicit_candles,inspect_expansion


def fixture():
    raw=dict(timestamp=0,shift=60000,multiplier=.01,open=100,high=100,low=100,close=100,
             times=[2,1,3],opens=[0,100,100],highs=[0,100,100],lows=[0,100,100],closes=[0,100,100],volumes=[1,0,2])
    native=[dict(timestamp=i*60000,open=p,high=p,low=p,close=p,volume=v)
            for i,p,v in [(0,100,0),(1,100,0),(2,100,1),(3,101,0),(4,101,0),(5,101,0),(6,102,2)]]
    return raw,native


class SourceProvenanceTests(unittest.TestCase):
    def test_initial_and_internal_padding_are_not_source_observations(self):
        raw,native=fixture()
        result=inspect_expansion(raw,native)
        self.assertEqual(result['padding_stamps'],[0,60000,240000,300000])
        self.assertEqual([r['timestamp'] for r in result['explicit_rows']],[120000,180000,360000])
        self.assertIs(result['explicit_rows'][0],native[2])

    def test_explicit_zero_volume_moving_candle_is_preserved(self):
        raw,native=fixture()
        result=inspect_expansion(raw,native)
        self.assertEqual(result['explicit_rows'][1]['volume'],0)
        self.assertEqual(result['explicit_rows'][1]['close'],101)
        raw['opens'][1]=raw['highs'][1]=raw['lows'][1]=raw['closes'][1]=0
        raw['opens'][2]=raw['highs'][2]=raw['lows'][2]=raw['closes'][2]=200
        native[3].update(open=100,high=100,low=100,close=100)
        native[4].update(open=100,high=100,low=100,close=100)
        native[5].update(open=100,high=100,low=100,close=100)
        self.assertEqual(len(inspect_expansion(raw,native)['explicit_rows']),3)

    def test_tampered_actual_or_padding_price_and_filtered_export_fail(self):
        raw,native=fixture()
        for at in [0,3]:
            changed=copy.deepcopy(native);changed[at]['close']=99
            with self.subTest(at=at),self.assertRaises(ValueError):inspect_expansion(raw,changed)
        with self.assertRaises(ValueError):inspect_expansion(raw,native[2:])

    def test_duplicate_or_fractional_time_and_column_mismatch_fail(self):
        raw,_=fixture()
        for changes in [dict(times=[2,0,3]),dict(times=[2,1.5,3]),dict(volumes=[1]),dict(multiplier=0),dict(shift=3600000)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):explicit_candles(dict(raw,**changes))

    def test_actual_volume_and_base_grid_are_bound(self):
        raw,native=fixture()
        native[2]['volume']=0
        with self.assertRaises(ValueError):inspect_expansion(raw,native)
        raw['open']=100.001
        with self.assertRaises(ValueError):explicit_candles(raw)

    def test_source_base_float_noise_matches_native_integer_normalization(self):
        raw,native=fixture()
        raw['high']=raw['close']=100.00000000000001
        self.assertEqual(len(inspect_expansion(raw,native)['explicit_rows']),3)

    def test_empty_source_cannot_explain_present_rows(self):
        raw,native=fixture()
        for key in ['times','opens','highs','lows','closes','volumes']:raw[key]=[]
        for key in ['open','high','low','close']:raw[key]=0
        self.assertEqual(inspect_expansion(raw,[])['explicit_rows'],[])
        with self.assertRaises(ValueError):inspect_expansion(raw,native)

    def test_paired_subset_does_not_invent_missing_side_rows_or_misbind_padding(self):
        raw,native=fixture()
        subset=[native[0],native[4],native[6]]
        with self.assertRaises(ValueError):inspect_expansion(raw,subset)
        result=inspect_expansion(raw,subset,require_complete=False)
        self.assertEqual(result['explicit_rows'],[native[6]])
        self.assertEqual(result['unrepresented_explicit_rows'],2)
        self.assertEqual(result['padding_stamps'],[0,240000])
        changed=copy.deepcopy(subset);changed[1]['close']=100
        with self.assertRaises(ValueError):inspect_expansion(raw,changed,require_complete=False)


if __name__=='__main__':unittest.main()
