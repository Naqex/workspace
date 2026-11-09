from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import eurusd_post_fomc_component as study
import fixing_clock_probe as costs


def fixture():
    p = {}
    for s in study.schedules():
        p[s['entry_ms']] = (dict(timestamp=s['entry_ms'], open='1.10000'),dict(timestamp=s['entry_ms'], open='1.10010'))
        p[s['exit_ms']] = (dict(timestamp=s['exit_ms'], open='1.09900'),dict(timestamp=s['exit_ms'], open='1.09910'))
    return p


class PostFomcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): costs.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_calendar_DST_known_and_no_rollover(self):
        rows = study.schedules();self.assertEqual(len(rows),32)
        for r in rows:
            self.assertLess(r['calendar_publication_ms'],r['decision_ms'])
            self.assertEqual(r['exit_ms']-r['entry_ms'],718*60000)
            self.assertEqual(datetime.fromtimestamp(r['entry_ms']/1000,study.NY).strftime('%H:%M'),'02:01')
            self.assertEqual(datetime.fromtimestamp(r['exit_ms']/1000,study.NY).strftime('%H:%M'),'13:59')
        self.assertEqual(datetime.fromtimestamp(rows[0]['entry_ms']/1000,timezone.utc).strftime('%H:%M'),'07:01')
        self.assertEqual(datetime.fromtimestamp(rows[8]['entry_ms']/1000,timezone.utc).strftime('%H:%M'),'06:01')

    def test_costs_entry_bid_exit_ask_null_and_units(self):
        r = study.evaluate(study.prepare(fixture()))[0]['outcomes']
        self.assertEqual(r['reference']['primary']['net_usd_per_research_unit'],'85.0')
        self.assertEqual(r['stress']['primary']['net_usd_per_research_unit'],'81.0')
        self.assertEqual(r['stress']['opposite_control']['net_usd_per_research_unit'],'-119.0')
        self.assertEqual(r['stress']['null']['net_usd_per_research_unit'],'0')

    def test_missing_crossed_offgrid_and_interior_gap_scope(self):
        for mode in ('missing','crossed'):
            p=fixture();s=study.schedules()[0]
            if mode=='missing': del p[s['exit_ms']]
            else:p[s['exit_ms']][1]['open']='1'
            r=study.evaluate(study.prepare(p))[0]
            self.assertFalse(r['outcomes']['stress']['primary']['resolved']);self.assertTrue(r['outcomes']['stress']['null']['resolved'])
        p=fixture();s=study.schedules()[0];p[s['entry_ms']][0]['open']='1.100001'
        with self.assertRaises(ValueError): study.prepare(p)
        r=study.prepare(fixture())[0];self.assertTrue(r['endpoints_resolved']);self.assertEqual(r['holding_paired_source_minutes'],2)

    def test_census_future_quote_cannot_change_schedule_and_gate(self):
        p=fixture();before=study.prepare(p);s=study.schedules()[0];p[s['exit_ms']][0]['open']='1.20000';p[s['exit_ms']][1]['open']='1.20010'
        after=study.prepare(p)
        for key in ('entry_ms','exit_ms','decision_ms','calendar_publication_ms'):self.assertEqual(before[0][key],after[0][key])
        rows=study.evaluate(before);report=study.summarize(rows);self.assertEqual(len(report['books']),24)
        self.assertFalse(report['retained_for_risk_review']);self.assertFalse(report['execution_authorized'])
        with self.assertRaises(ValueError):study.evaluate(before[:-1])
        with self.assertRaises(ValueError):study.summarize(list(reversed(rows)))


if __name__=='__main__':unittest.main()
