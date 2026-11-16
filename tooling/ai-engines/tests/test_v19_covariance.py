import unittest
import numpy as np
from quant_core.asymmetric_covariance_optimizer import constrained_minimum_variance


class CovarianceFitTests(unittest.TestCase):
    def book(self):
        centered = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)
        return np.tile(centered, (50, 1)) * [2, 1, 3] + 1

    def test_known_box_constrained_solution_not_inverse_volatility(self):
        r = constrained_minimum_variance(self.book())
        self.assertTrue(r["eligible"])
        np.testing.assert_allclose(r["weights"], [9 / 13, 2, 4 / 13], atol=1e-12)
        self.assertAlmostEqual(r["target_mean"], r["weighted_mean"])
        self.assertLess(r["weighted_variance"], r["equal_variance"])

    def test_free_gradient_and_active_upper_bound_satisfy_KKT(self):
        r = constrained_minimum_variance(self.book())
        cov, w = np.array(r["covariance"]), np.array(r["weights"])
        gradient = cov @ w
        self.assertAlmostEqual(gradient[0], gradient[2])
        self.assertLess(gradient[1], gradient[0])
        self.assertEqual(r["active_set"], [0, 1, 0])
        self.assertEqual(r["analytic_sets_checked"], 27)

    def test_singular_or_nonpositive_mean_is_not_regularized_to_force_fit(self):
        self.assertFalse(constrained_minimum_variance(np.ones((200, 3)))["eligible"])
        self.assertFalse(constrained_minimum_variance(self.book() - 10)["eligible"])

    def test_invalid_data_cannot_silently_enter_weight_fit(self):
        for values in (np.zeros((20, 3)), np.zeros((200, 4)), np.full((200, 3), np.nan)):
            with self.assertRaises(ValueError):
                constrained_minimum_variance(values)


if __name__ == "__main__":
    unittest.main()
