import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_consumption import audit,day


class ConsumptionTests(unittest.TestCase):
    def test_forex_ranges_are_exported_without_quotes_outcomes_or_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            value=dict(schema='forex-h4-development-v1',candidate='eurusd-h4-test',
                inputs={'development':dict(first_day='20230101',last_day='20230331')},
                quotes=[dict(first_day='20990101',last_day='20991231',bid='private-price')],
                results=[dict(pnl='private-pnl')],password='do-not-export')
            (root/'manifest.json').write_text(json.dumps(value))
            report=audit([root])
            windows=report['records'][0]['windows']
            self.assertEqual([(w['first_day'],w['last_day']) for w in windows],[('20230101','20230331')])
            for secret in ('private-price','private-pnl','do-not-export','2099'):
                self.assertNotIn(secret,json.dumps(report))
            self.assertFalse(report['absence_of_records_proves_unseen'])

    def test_missing_or_unreadable_evidence_stays_explicitly_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'manifest.json').write_text('{broken')
            report=audit([root,root/'missing'])
            self.assertCountEqual([r['reason'] for r in report['review_required']],
                                  ['unreadable_metadata','missing_root'])
            self.assertFalse(report['absence_of_records_proves_unseen'])

    def test_dates_handle_calendar_days_seconds_and_milliseconds(self):
        self.assertEqual(day(20230101),'20230101')
        self.assertEqual(day(1672531200),'20230101')
        self.assertEqual(day(1672531200000),'20230101')
        self.assertIsNone(day('20230230'))

    def test_directory_walk_failure_is_recorded_as_a_coverage_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            def denied(root, **kwargs):
                kwargs['onerror'](PermissionError(13,'access denied',str(root/'private')))
                return iter(())
            with patch('research_consumption.os.walk',side_effect=denied):
                report=audit([directory])
            self.assertEqual(report['review_required'][0]['reason'],'unreadable_directory')
            self.assertFalse(report['absence_of_records_proves_unseen'])

    def test_planned_registration_is_not_reported_as_an_executed_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'registration.json').write_text(json.dumps(dict(
                schema='forex-historical-study-registration-v1',
                window=dict(first_day='20230101',last_day='20230331'))))
            record=audit([root])['records'][0]
            self.assertEqual(record['kind'],'planned_registration_not_proof_of_price_exposure')


if __name__=='__main__': unittest.main()
