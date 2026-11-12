from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_us500_recent_screen as r


def row(code,year,net):return dict(code=code,year=year,scenario='stress',metrics=dict(sides=dict(combined=dict(net_usd=net)),rejections=0))


class RecentScreenTests(unittest.TestCase):
    def test_selection_never_ranks_unknown_modeled_profit(self):
        rows=[row(c,2025,None) for c in r.study.ECONOMIC]
        self.assertEqual(r.select(rows)['codes'],['RS01','RS07'])
        self.assertTrue(r.select(rows)['diagnostics_only'])

    def test_selection_prefers_development_positive_then_recent_net(self):
        rows=[row(c,2025,str(i*100)) for i,c in enumerate(r.study.ECONOMIC)]
        rows += [row('RS01',y,'1') for y in (2022,2023,2024)]
        result=r.select(rows)
        self.assertEqual(result['codes'],['RS01'])
        self.assertFalse(result['diagnostics_only'])

    def test_recent_reader_rejects_other_years_before_io(self):
        for y in (2024,2027):
            with self.assertRaisesRegex(ValueError,'registered_recent_year'):
                r.recent_year(Path('not_read'),y,lambda *a,**k:None)


if __name__=='__main__':unittest.main()
