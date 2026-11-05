import unittest

from golden_event_parity import semantic_equal


class GoldenEventParityTests(unittest.TestCase):
    def test_money_scale_is_semantically_equal(self):
        self.assertTrue(semantic_equal({"floating_pl": "-0.30"}, {"floating_pl": "-0.3"}))

    def test_unknown_string_is_not_normalized(self):
        self.assertFalse(semantic_equal({"event_id": "1.20"}, {"event_id": "1.2"}))

    def test_event_order_and_kind_still_matter(self):
        left = [{"kind": "price_mark", "equity": "100.00"}, {"kind": "market_fill"}]
        right = [{"kind": "market_fill"}, {"kind": "price_mark", "equity": "100"}]
        self.assertFalse(semantic_equal(left, right))


if __name__ == "__main__":
    unittest.main()
