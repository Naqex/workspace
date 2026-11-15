from pathlib import Path
import sys
import unittest
from decimal import Decimal
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_v9 import structural_stop, generate, deadline, gates, NAMES, HOUR, DAY
from quant_core.ftmo_execution_and_calendar import gold_calendar
from prop_campaign_source import stamp


class V9Tests(unittest.TestCase):
    def test_structural_stop_uses_four_known_bars_and_prior_atr(self):
        hm = {k * HOUR: [k * HOUR, 10000, 12000 + k, 9000 - k, 11000, 60] for k in range(4)}
        f = dict(bar=hm[3 * HOUR], atr_before=Decimal(1000))
        self.assertEqual(structural_stop(f, hm, True), 8897)
        self.assertEqual(structural_stop(f, hm, False), 12103)
        del hm[0]
        self.assertIsNone(structural_stop(f, hm, True))

    def test_prefix_signal_causality_with_nonempty_census(self):
        first = stamp("2022-01-03")
        random = np.random.default_rng(431)
        hours = []
        price = 1800000
        for k in range(24 * 45):
            close = price + int(random.integers(-10000, 10000))
            hours.append([first + k * HOUR, price, max(price, close) + 3000,
                          min(price, close) - 3000, close, 60])
            price = close
        cal = gold_calendar(first, first + 46 * DAY)
        all_rows = generate(hours, first, first + 45 * DAY, cal)
        cut = first + 30 * DAY
        prefix = generate([r for r in hours if r[0] < cut], first, cut, cal)
        self.assertGreater(len(prefix), 0)
        self.assertEqual(prefix, [r for r in all_rows if r["decision_msc"] < cut])
        self.assertTrue(all(len([r for r in prefix if r["id"] == n and r["day"] == t["day"]]) == 1
                            for n in NAMES for t in prefix if t["id"] == n))

    def test_day_deadline_clamps_to_holiday_instead_of_claiming_zero_swap(self):
        first, end = stamp("2023-01-01"), stamp("2024-01-01")
        cal = gold_calendar(first, end)
        r = dict(entry_msc=stamp("2023-11-24T09:00:00"), horizon="DAY")
        at, why = deadline(r, cal)
        self.assertLess(at, stamp("2023-11-24T20:30:00"))
        self.assertEqual(why, "HOLIDAY_FLAT")

    def test_no_markout_winner_when_one_development_year_is_negative(self):
        rows = []
        for name in NAMES:
            for y in (2019, 2020, 2022, 2023):
                values = {m: dict(mean_net_per_oz=-.1 if y == 2019 else 1,
                                  mean_gross_per_oz=2) for m in ("SYM_FLAT", "ASYM_ORDER")}
                rows.append(dict(candidate=name, year=y, raw=100, admitted=100,
                                 retention_pct=100, scale_ratio=.1, median_friction=.7,
                                 primary="DAY", markouts={"DAY": dict(observed=100, **values)}))
        self.assertTrue(all(not r["eligible"] for r in gates(rows).values()))

    def test_eurusd_proxy_units_and_roundtrip_costs(self):
        from prop_v9_eurusd import measure
        from quant_core.market_data_store import BAR
        first = stamp("2023-01-03")
        bars = np.zeros(2, dtype=BAR)
        bars["t"] = [first + 9 * HOUR, first + 20 * HOUR + HOUR // 2]
        bars["bo"] = [110000, 110100]
        bars["ao"] = bars["bo"] + 10
        raw = [dict(side="BUY", decision_msc=int(bars["t"][0]), stop_units=109800, horizon="DAY")]
        row = measure(raw, bars, gold_calendar(first, first + DAY))[0]
        self.assertEqual(row["natural_sl_pips"], 21)
        self.assertEqual(row["gross_USD_per_lot"], 90)
        self.assertEqual(row["net_USD_per_lot"], 81)
        self.assertEqual(row["net_pips"], 8.1)
