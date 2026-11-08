from datetime import datetime,timezone
from pathlib import Path
import sys,unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')]
from gold_session_component import schedules,observation,evaluate,summarize,CANDIDATES
from trading_workspace_v2.semantics.data_costs import calculate_round_trip_cost


class GoldSessionTests(unittest.TestCase):
    def test_DST_weekdays_and_holdout(self):
        specs=schedules([2024])
        for day,expected in [('2024-01-02','10:30'),('2024-06-03','09:30')]:
            row=next(s for s in specs if s['day']==day and s['candidate']==CANDIDATES[1])
            self.assertEqual(datetime.fromtimestamp(row['entry_ms']/1000,timezone.utc).strftime('%H:%M'),expected)
        self.assertFalse(any(s['day']=='2024-01-06' for s in specs))
        self.assertEqual(len(specs),524)
        with self.assertRaisesRegex(ValueError,'holdout'):schedules([2025])
    def test_exact_source_side_and_missing(self):
        self.assertIsNone(observation(None,1000)['bid'])
        for point in [dict(time_ms=999,bid='2000'),dict(time_ms=1000,bid='2000',ask='2001')]:
            with self.assertRaisesRegex(ValueError,'endpoint_or_invented'):observation(point,1000)
        point=observation(dict(time_ms=1000,bid='2000',source_sequence=1),1000)
        self.assertIsNone(point['ask']);self.assertFalse(point['executable_tick_proven'])
    def test_hand_cost_and_opposite_identity_and_missing_census(self):
        specs=schedules([2024])[:2];one=specs[0]
        points={one['entry_ms']:dict(time_ms=one['entry_ms'],bid='2000',source_sequence=1),
                one['exit_ms']:dict(time_ms=one['exit_ms'],bid='2001',source_sequence=2)}
        rows=evaluate(specs,points,cost_function=calculate_round_trip_cost)
        primary=rows[0]['views']['primary']['outcomes'];control=rows[0]['views']['opposite_control']['outcomes']
        self.assertEqual(primary['reference']['net_account'],.25)
        self.assertEqual(control['reference']['net_account'],-1.75)
        self.assertAlmostEqual(primary['stress']['net_account']+control['stress']['net_account'],-2.9)
        self.assertEqual(rows[1]['status'],'unresolved_missing_endpoint');self.assertFalse(rows[1]['views'])
        summary,priority=summarize(rows,[2024])
        self.assertEqual(len(summary),8);self.assertFalse(any(p['retained'] for p in priority.values()))


if __name__=='__main__':unittest.main()
