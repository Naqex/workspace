from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eia_release_dates import release_dates


def link(day, *, host=''):
    return f'<a href="{host}/petroleum/supply/weekly/archive/{day[:4]}/{day}/wpsr_{day}.php">{int(day[-2:])}</a>'


class EIAReleaseDatesTests(unittest.TestCase):
    def test_duplicate_reports_are_one_event_without_invented_time(self):
        got=release_dates(link('2019_01_04')+link('2022_06_29')*2)
        self.assertEqual((got['source_link_occurrences'],got['unique_release_dates'],got['duplicate_date_occurrences']),(3,2,1))
        self.assertEqual(got['events'][0]['weekday'],'Friday')
        self.assertEqual(got['events'][1]['archive_link_occurrences'],2)
        self.assertTrue(all(e['actual_release_time_et'] is None and not e['trading_eligibility_verified'] for e in got['events']))

    def test_other_years_are_not_market_holdout_or_registered_events(self):
        got=release_dates(link('2019_01_04')+link('2022_01_05')+link('2025_01_02'))
        self.assertEqual(len(got['events']),2)
        self.assertFalse(got['holdout_prices_read'])

    def test_bad_origin_inconsistent_date_and_invalid_date_rejected(self):
        base=link('2019_01_04')+link('2022_01_05')
        for wrong in (link('2022_02_30'),link('2022_01_05',host='https://example.com'),
                      link('2022_01_05').replace('wpsr_2022_01_05','wpsr_2022_01_06')):
            with self.subTest(wrong=wrong),self.assertRaises(ValueError):release_dates(base+wrong)

    def test_missing_year_and_unregistered_scope_rejected(self):
        with self.assertRaises(ValueError):release_dates(link('2019_01_04'))
        with self.assertRaises(ValueError):release_dates('',years=(2023,2024))

    def test_delayed_data_path_uses_verified_release_date_and_visible_label(self):
        delayed='<a href="/petroleum/supply/weekly/archive/2022/2022_06_17_data/wpsr_2022_06_17_data.php">29</a>'
        got=release_dates(link('2019_01_04')+delayed+link('2022_06_29'))
        event=got['events'][1]
        self.assertEqual(event['release_date'],'2022-06-29')
        self.assertEqual(len(event['source_urls']),2)
        self.assertNotIn('2022-06-17',[e['release_date'] for e in got['events']])
        with self.assertRaises(ValueError):release_dates(link('2019_01_04')+delayed.replace('>29<','>17<'))


if __name__=='__main__':unittest.main()
