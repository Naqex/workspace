from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fx_pair_formation as study


def fixture():
    books={(symbol,side):[] for symbol in study.SYMBOLS for side in ('bid','ask')}
    for day in study.expected_dates(2018):
        stamp=int(day.replace(hour=16).timestamp()*1000)
        for (symbol,side),rows in books.items():
            p=1.2 if symbol=='gbpusd' else .8
            p+=.0002 if side=='ask' else 0
            rows.append(dict(timestamp=stamp,open=round(p,5),high=round(p+.001,5),low=round(p-.001,5),close=round(p,5)))
    return books


class FormationTests(unittest.TestCase):
    def test_exact_dates_knownat_and_no_holdout(self):
        result=study.formation_sample(fixture(),2018)
        self.assertTrue(result['source_admitted'])
        self.assertEqual(result['expected_dates'],259)
        self.assertTrue(all(r['known_at_msc']-r['source_time_msc']==3600000 for r in result['samples']))
        for year in [2019,2022,2025]:
            with self.subTest(year=year),self.assertRaisesRegex(ValueError,'unregistered'):study.expected_dates(year)

    def test_missing_registered_date_never_silently_dropped_for_fit(self):
        books=fixture();books['gbpusd','ask'].pop(7)
        result=study.formation_sample(books,2018)
        self.assertFalse(result['source_admitted'])
        self.assertEqual(len(result['census']),259)
        self.assertEqual(result['missing'][0]['absent'],['gbpusd-ask'])
        self.assertEqual(study.diagnose_sample(result)['status'],'inconclusive_missing_registered_dates_no_statistics')

    def test_wrong_clock_grid_duplicate_and_crossed_are_guarded(self):
        for mode in ['clock','grid','duplicate','crossed']:
            books=fixture();rows=books['audusd','ask']
            if mode=='clock':rows[0]['timestamp']+=1
            if mode=='grid':rows[0]['close']+=.000001
            if mode=='duplicate':rows.insert(0,deepcopy(rows[0]))
            if mode=='crossed':
                for key in ['open','close']:rows[0][key]=.7999
            with self.subTest(mode=mode):
                if mode=='crossed':self.assertFalse(study.formation_sample(books,2018)['source_admitted'])
                else:
                    with self.assertRaises(ValueError):study.formation_sample(books,2018)

    def test_fixed_statistical_method_on_known_synthetic_cases(self):
        import numpy as np
        from statsmodels.tsa.stattools import coint
        rng=np.random.default_rng(971)
        x=np.cumsum(rng.normal(size=500))
        y=1.6*x+rng.normal(scale=.3,size=500)+3
        r=study.diagnose(y,x)
        self.assertAlmostEqual(r['beta'],1.6,places=2)
        self.assertLess(r['coint_pvalue'],.001)
        self.assertEqual(r['coint_tstat'],coint(y,x,trend='c',maxlag=1,autolag=None,return_results=False)[0])
        independent=np.cumsum(rng.normal(size=500))
        self.assertGreater(study.diagnose(independent,x)['coint_pvalue'],.05)
        self.assertFalse(r['strategy_simulated'])

    def test_degenerate_short_and_nonfinite_are_not_low_p_winners(self):
        import numpy as np
        x=np.arange(300,dtype=float)
        for y,other in [(x*2+1,x),(np.ones(300),x),(x[:50],x[:50]),(np.full(300,np.nan),x)]:
            with self.subTest(kind=str(y[:2])),self.assertRaises(ValueError):study.diagnose(y,other)


if __name__=='__main__':unittest.main()
