"""Exact three-sleeve, mean-constrained variance fit; no outcome search grid."""
from itertools import product
import numpy as np


def constrained_minimum_variance(daily_pnl):
    x = np.asarray(daily_pnl, dtype=float)
    if x.ndim != 2 or x.shape[1] != 3 or len(x) < 100 or not np.isfinite(x).all():
        raise ValueError("three_finite_daily_sleeve_series_required")
    mu = x.mean(axis=0)
    cov = np.cov(x, rowvar=False)
    target = float(mu.sum())
    if target <= 0 or np.linalg.eigvalsh(cov).min() <= 0:
        return dict(eligible=False, reason="NONPOSITIVE_MEAN_OR_NON_PD_COVARIANCE")
    candidates = []
    for states in product((-1, 0, 1), repeat=3):
        free = np.flatnonzero(np.array(states) == 0)
        fixed = np.flatnonzero(np.array(states) != 0)
        w = np.array([.25 if s == -1 else 2. if s == 1 else 0. for s in states])
        if len(free):
            a = cov[np.ix_(free, free)]
            rhs = -cov[np.ix_(free, fixed)] @ w[fixed] if len(fixed) else np.zeros(len(free))
            kkt = np.block([[a, mu[free, None]], [mu[None, free], np.zeros((1, 1))]])
            right = np.r_[rhs, target - mu[fixed] @ w[fixed]]
            try:
                solution = np.linalg.solve(kkt, right)
            except np.linalg.LinAlgError:
                continue
            w[free] = solution[:-1]
        if (np.any(w < .25 - 1e-10) or np.any(w > 2 + 1e-10) or
                abs(float(mu @ w) - target) > 1e-8):
            continue
        w = np.clip(w, .25, 2)
        candidates.append((float(w @ cov @ w), w, states))
    if not candidates:
        raise ValueError("all_ones_feasible_but_solver_found_none")
    variance, weights, active = min(candidates, key=lambda r: (r[0], tuple(r[1])))
    equal = float(np.ones(3) @ cov @ np.ones(3))
    if variance > equal + 1e-7:
        raise ValueError("minimum_variance_worse_than_feasible_incumbent")
    return dict(eligible=True, weights=weights.tolist(), means=mu.tolist(), covariance=cov.tolist(),
                target_mean=target, weighted_mean=float(mu @ weights),
                equal_variance=equal, weighted_variance=variance, active_set=list(active),
                feasible_active_sets=len(candidates), analytic_sets_checked=27,
                no_ridge_shrinkage_or_outcome_selected_hyperparameter=True)
