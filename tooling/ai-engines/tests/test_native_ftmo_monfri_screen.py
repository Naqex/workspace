"""Regression fixtures for timing, gap precedence and fixed-book overlap."""

import unittest
from datetime import datetime, timezone

from native_ftmo_monfri_screen import crossing, daily_limit, friday_limit, select


def stamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


class NativeFtmoMonfriTests(unittest.TestCase):
    def test_friday_and_daily_boundary(self):
        self.assertEqual(friday_limit(stamp('2024-07-02T13:00:00')), stamp('2024-07-05T23:00:00'))
        self.assertEqual(daily_limit(stamp('2024-07-02T13:00:00')), stamp('2024-07-02T23:00:00'))
        self.assertEqual(daily_limit(stamp('2024-01-02T13:00:00')), stamp('2024-01-02T22:00:00'))

    def test_ambiguous_bar_stops_first_and_short_uses_ask(self):
        self.assertEqual(crossing(1,100,90,110,95,105,1), ('SL', 95, False))
        self.assertEqual(crossing(-1,100,90,104,105,95,1), ('SL', 104, False))
        self.assertEqual(crossing(-1,105,90,110,105,95,1), ('SL_GAP', 105, True))

    def test_same_asset_d1_priority_and_lot_floor(self):
        ordinary = dict(asset='EURUSD',entry=0,exit=2,decision=0,initial_risk=501,margin=1000)
        h4, daily = [ordinary | {'frame': f} for f in ('H4','D1')]
        impossible = ordinary | {'asset':'XAUUSD','frame':'H4','initial_risk':5001}
        chosen, skips = select([h4,daily,impossible],10000)
        self.assertEqual([(r['frame'],r['lots']) for r in chosen], [('D1',.09)])
        self.assertEqual(skips, {'ONE_POSITION_PER_ASSET':1,'LOT_FLOOR_OR_MARGIN':1})
