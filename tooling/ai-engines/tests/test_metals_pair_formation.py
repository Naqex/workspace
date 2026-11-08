from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import metals_pair_formation as study


def fixture(year=2018):
    books={(s,p):[] for s in study.SYMBOLS for p in ('bid','ask')}
    for i,day in enumerate(study.cash_sessions(study.calendar_for(year))):
        at=int(datetime.fromisoformat(day).replace(hour=16,tzinfo=timezone.utc).timestamp()*1000)
        for (s,p),rows in books.items():
            price=(D(1000) if s=='xauusd' else D(15))+D(i)/100+(D('.002') if p=='ask' else D(0))
            rows.append(dict(timestamp=at,open=float(price),high=float(price+D('.01')),
                             low=float(price-D('.01')),close=float(price+D('.005')),volume=0))
    return books


class MetalsFormationTests(unittest.TestCase):
    def test_frozen_dates_side_roles_known_after_close(self):
        books=fixture();sample=study.formation_sample(books,2018)
        self.assertTrue(sample['source_admitted'])
        self.assertEqual(sample['expected_dates'],len(study.cash_sessions(study.calendar_for(2018))))
        self.assertTrue(all(r['known_at_msc']==r['source_time_msc']+3600000 for r in sample['census']))
        first=sample['samples'][0]
        self.assertEqual((first['xauusd_bid_close'],first['xagusd_bid_close']),('1000.005','15.005'))
        self.assertFalse(sample['execution_authorized'])

    def test_missing_or_crossed_registered_date_keeps_census_and_blocks_stats(self):
        books=fixture();expected=study.formation_sample(books,2018)['expected_dates']
        books['xagusd','ask'].pop(10)
        sample=study.formation_sample(books,2018)
        self.assertFalse(sample['source_admitted']);self.assertEqual(len(sample['census']),expected)
        self.assertEqual(sample['missing'][0]['absent'],['xagusd-ask'])
        self.assertEqual(study.diagnose_sample(sample)['status'],'inconclusive_missing_registered_dates_no_statistics')
        books=fixture();books['xauusd','ask'][10]['close']=books['xauusd','bid'][10]['close']-.001
        sample=study.formation_sample(books,2018)
        self.assertFalse(sample['source_admitted']);self.assertEqual(sample['missing'][0]['crossed'],['xauusd'])

    def test_scope_grid_order_and_holdout_are_not_repaired(self):
        for mode in ('year','grid','order'):
            books=fixture()
            if mode=='year':books['xauusd','bid'][0]['timestamp']=1735689600000
            elif mode=='grid':books['xauusd','bid'][0]['close']=1000.0051
            else:books['xauusd','bid'].reverse()
            with self.assertRaises(ValueError):study.formation_sample(books,2018)
        with self.assertRaisesRegex(ValueError,'unregistered'):study.formation_sample({},2025)
        with self.assertRaisesRegex(ValueError,'unregistered'):study.diagnose_sample({'year':2025,'source_admitted':True})
        books=fixture();books['xagusd','bid']=books.pop(('xauusd','bid'))
        with self.assertRaisesRegex(ValueError,'identity_census'):study.formation_sample(books,2018)


if __name__=='__main__':unittest.main()
