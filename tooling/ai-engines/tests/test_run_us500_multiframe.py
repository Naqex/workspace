from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_us500_multiframe as runner
import test_us500_multiframe as fixtures


class AdmissionTests(unittest.TestCase):
    def test_full_cash_session_not_152_minute_opening_subset(self):
        start=fixtures.event(0,100)['t']
        stamps=list(range(start,start+390*60000,60000))
        rows={t:dict(timestamp=t,open=100,high=101,low=99,close=100,volume=0) for t in stamps}
        import tempfile,json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'source-observation-proof.json').write_text('{}')
            with patch.object(runner,'digest',return_value=runner.PROOFS[2022]),patch.object(runner,'admitted_calendar',return_value=({},{})),patch.object(runner,'cash_sessions',return_value={'2022-01-04':stamps}),patch.object(runner,'load_year_side',return_value=dict(rows=rows,bindings={})):
                sessions,pairs,admission=runner.load_year(root,2022,lambda *a,**kw:None)
            self.assertEqual(len(pairs),390)
            self.assertIn(stamps[-1],pairs)
            self.assertEqual(admission['missing_minutes'],0)

    def test_reserved_year_never_reads_files(self):
        with self.assertRaisesRegex(ValueError,'registered_development'):
            runner.load_year(Path('does-not-exist'),2025,lambda *a,**kw:None)

    def test_protocol_and_source_pin_census(self):
        root=Path(__file__).resolve().parents[3]
        pins=runner.source_pins(root/'planning/research/US500-MULTIFRAME-PROTOCOL-20261111.md')
        self.assertEqual(len(pins),10)
        self.assertTrue(all(len(v)==64 for v in pins.values()))


if __name__=='__main__':
    unittest.main()
