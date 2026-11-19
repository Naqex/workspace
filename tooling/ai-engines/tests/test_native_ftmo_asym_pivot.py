from datetime import datetime, timezone
import unittest

import numpy as np

from native_ftmo_asym_pivot import path, rsi_two, top2, wall_to_utc
from native_ftmo_monfri_screen import DAY, Intent, Market


def stamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


class NativeFtmoAsymTests(unittest.TestCase):
    def test_only_closed_moves_seed_rsi(self):
        x = rsi_two(np.asarray([100.,102.,101.,100.]))
        self.assertTrue(np.isnan(x[1]))
        self.assertAlmostEqual(x[2],200/3)

    def test_server_clock_uses_dst_in_utc(self):
        self.assertEqual(wall_to_utc(stamp('2024-07-05T23:00:00')).hour,20)
        self.assertEqual(wall_to_utc(stamp('2024-01-05T22:00:00')).hour,20)

    def test_d1_only_closes_friday_open_and_posts_thursday_swap(self):
        thursday = stamp('2024-07-04T00:00:00')
        feed = dict(t=np.asarray([thursday,thursday+DAY]),o=[100.,102.],l=[99.,101.],h=[101.,103.],c=[100.,102.])
        spec = dict(trade_contract_size=1,margin_estimates_usd={'1.0':[2.,2.]},
                    swap_long=-10,swap_short=-10,point=.01,swap_rollover3days=5)
        m = Market('US500.cash',feed,dict(spec=spec,spread={'median':.6}),None)
        row, reason = path(m,Intent('US500.cash','ASYM_A','D1',thursday,1,5.),'Base-Real',False,exit_ma=[101.,101.])
        self.assertIsNone(reason)
        self.assertEqual(row['exit'],thursday+DAY)
        self.assertAlmostEqual(row['swap'],-.1)
        self.assertAlmostEqual(row['net'],1.3)

    def test_concentration_subtracts_only_the_two_largest_winners(self):
        rows = [{'net': value, 'lots': 1.} for value in (40., 120., -50., 90.)]
        result = top2(rows, 10000)
        self.assertAlmostEqual(result['top2_gross_winner_share'], 210. / 250.)
        self.assertAlmostEqual(result['net_R_without_top2'], -0.2)
