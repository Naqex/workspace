from pathlib import Path
import sys,unittest
import json,tempfile
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

    def test_recovery_requires_exact_reviewed_source_and_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);pins={'policy.py':'new','same.py':'same'}
            r.core.save(root/'manifest.json',dict(stage='development',codes=['RS01'],years=[2022],
                source_pins={'policy.py':'old','same.py':'same'}))
            rows=[row('RS01',2022,'1')];r.core.save(root/'completed-books.json',rows)
            contract=dict(parent_manifest_sha256=r.core.digest(root/'manifest.json'),
                completed_sha256=r.core.digest(root/'completed-books.json'),
                source_deltas={'policy.py':dict(old='old',new='new')},
                reason='trace_kind_only_no_economic_rule_change')
            path=root/'contract.json';r.core.save(path,contract)
            self.assertEqual(len(r.recovery(root,path,pins,'development',['RS01'],(2022,))),1)
            with self.assertRaisesRegex(ValueError,'reuse_unreviewed_source_drift'):
                r.recovery(root,path,dict(pins,unexpected='changed'),'development',['RS01'],(2022,))
            with self.assertRaisesRegex(ValueError,'reuse_scope_drift'):
                r.recovery(root,path,pins,'confirm',['RS01'],(2022,))
            r.core.save(root/'completed-books.json',[])
            with self.assertRaisesRegex(ValueError,'reuse_completed_binding'):
                r.recovery(root,path,pins,'development',['RS01'],(2022,))

    def test_reuse_checks_bytes_signals_and_source_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);name='2022-RS01-stress';record=dict(events=[],cadence={})
            r.core.save(root/'manifest.json',{});r.core.save(root/(name+'.json'),{'preserved':True})
            r.core.save(root/(name+'-review.json'),{});r.core.save(root/'input-2022.json',{'binding':'original'})
            r.core.save(root/'2022-RS01-signals.json',record)
            r.core.save(root/(name+'-seal.json'),dict(book_sha256=r.core.digest(root/(name+'.json')),
                review_sha256=r.core.digest(root/(name+'-review.json')),manifest_sha256=r.core.digest(root/'manifest.json')))
            saved=r.reuse_book(root,name,row('RS01',2022,'1'),{'binding':'original'},record)
            self.assertTrue(saved['preserved'])
            with self.assertRaisesRegex(ValueError,'reuse_input_drift'):
                r.reuse_book(root,name,row('RS01',2022,'1'),{'binding':'changed'},record)
            with self.assertRaisesRegex(ValueError,'reuse_signal_drift'):
                r.reuse_book(root,name,row('RS01',2022,'1'),{'binding':'original'},dict(events=[1]))
            r.core.save(root/(name+'.json'),{'changed':True})
            with self.assertRaisesRegex(ValueError,'reuse_seal_drift'):
                r.reuse_book(root,name,row('RS01',2022,'1'),{'binding':'original'},record)


if __name__=='__main__':unittest.main()
